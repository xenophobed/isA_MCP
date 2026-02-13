#!/usr/bin/env python3
"""
Graph RAG Tools for MCP Server

Provides file metadata graph capabilities for agents to query relationships
between files, patterns, templates, skills, and documentation.

Migrated from isA_Vibe/src/agents/mcp_servers/graph_rag/

Architecture: MCP Tools -> GraphStore -> DigitalServiceClient -> Digital Service API

Environment:
    DIGITAL_SERVICE_URL: Digital Service URL (default: http://localhost:8084/api/v1/digital)
    NEO4J_HOST: Neo4j host (default: localhost)
    NEO4J_PORT: Neo4j Bolt port (default: 7687)
"""

import json
import os
from typing import Any, Optional, Dict, List
from enum import Enum

from mcp.server.fastmcp import FastMCP
from core.logging import get_logger
from tools.base_tool import BaseTool

logger = get_logger(__name__)
tools = BaseTool()


# =============================================================================
# Enums (from contracts.py)
# =============================================================================


class EntityType(str, Enum):
    FILE = "FILE"
    TEMPLATE = "TEMPLATE"
    PATTERN = "PATTERN"
    DOCS = "DOCS"
    PACKAGE = "PACKAGE"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"
    AGENT = "AGENT"
    SKILL = "SKILL"


class RelationType(str, Enum):
    USES_TEMPLATE = "USES_TEMPLATE"
    USES_PATTERN = "USES_PATTERN"
    DOCUMENTED_IN = "DOCUMENTED_IN"
    DEPENDS_ON = "DEPENDS_ON"
    USED_BY = "USED_BY"
    RELIES_ON_PACKAGE = "RELIES_ON_PACKAGE"
    RELIES_ON_SERVICE = "RELIES_ON_SERVICE"
    USES_SKILL = "USES_SKILL"
    GENERATES = "GENERATES"
    CREATED_BY = "CREATED_BY"


# =============================================================================
# Digital Service Client (simplified from digital_client.py)
# =============================================================================

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None


def parse_sse_response(text: str) -> dict:
    """Parse SSE response and extract final result."""
    result = {}
    for line in text.strip().split("\n"):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if data.get("type") == "result":
                    result = data.get("data", {})
                elif data.get("type") == "progress":
                    pass
                else:
                    result = data
            except json.JSONDecodeError:
                pass
    if not result:
        try:
            result = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


class GraphRAGClient:
    """Client for Digital Analytics Service (Graph RAG)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_id: str = "graph_rag_mcp",
        collection_name: str = "codebase_metadata",
        timeout: float = 30.0,
    ):
        self.base_url = base_url or os.getenv(
            "DIGITAL_SERVICE_URL", "http://localhost:8084/api/v1/digital"
        )
        self.user_id = user_id
        self.collection_name = collection_name
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._index_stats = {"files_indexed": 0, "relations_extracted": 0}

    async def _get_client(self) -> "httpx.AsyncClient":
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx not installed. Install with: pip install httpx")
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> Dict[str, Any]:
        """Check Digital Service health."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/status")
            if response.status_code == 200:
                result = response.json()
                return {
                    "healthy": result.get("success", False),
                    "digital_service_connected": True,
                    "base_url": self.base_url,
                    "capabilities": result.get("capabilities", {}),
                }
            return {
                "healthy": False,
                "digital_service_connected": True,
                "base_url": self.base_url,
                "error": response.text,
            }
        except Exception as e:
            return {
                "healthy": False,
                "digital_service_connected": False,
                "base_url": self.base_url,
                "error": str(e),
            }

    async def store_file_metadata(self, file_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Store file metadata in Graph RAG."""
        content_parts = [
            f"File: {file_meta.get('name', '')}",
            f"Path: {file_meta.get('path', '')}",
            f"Type: {file_meta.get('extension', '')} ({file_meta.get('language', 'unknown')})",
        ]
        for key in ["template", "pattern", "skill", "agent", "layer", "component"]:
            if file_meta.get(key):
                content_parts.append(f"{key.title()}: {file_meta[key]}")

        content = "\n".join(content_parts)
        metadata = {"entity_type": "FILE", "domain": "codebase", **file_meta}

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/store",
                json={
                    "user_id": self.user_id,
                    "content": content,
                    "content_type": "text",
                    "mode": "graph",
                    "collection_name": self.collection_name,
                    "metadata": metadata,
                },
            )
            if response.status_code == 200:
                result = parse_sse_response(response.text)
                self._index_stats["files_indexed"] += 1
                return {"success": True, "path": file_meta.get("path"), "response": result}
            return {"success": False, "path": file_meta.get("path"), "error": response.text}
        except Exception as e:
            return {"success": False, "path": file_meta.get("path"), "error": str(e)}

    async def store_relation(
        self,
        source_path: str,
        target_path: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store a relationship between two files."""
        content = f"Relationship: {source_path} --[{relation_type}]--> {target_path}"
        metadata = {
            "entity_type": "RELATION",
            "relation_type": relation_type,
            "source_path": source_path,
            "target_path": target_path,
            "properties": properties or {},
        }

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/store",
                json={
                    "user_id": self.user_id,
                    "content": content,
                    "content_type": "text",
                    "mode": "graph",
                    "collection_name": f"{self.collection_name}_relations",
                    "metadata": metadata,
                },
            )
            if response.status_code == 200:
                self._index_stats["relations_extracted"] += 1
                return {
                    "success": True,
                    "relation_type": relation_type,
                    "source": source_path,
                    "target": target_path,
                }
            return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def search_files(
        self, query: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 10
    ) -> Dict[str, Any]:
        """Search files using Graph RAG."""
        search_query = query
        if filters:
            filter_parts = []
            for key in ["pattern", "skill", "template", "layer", "extension"]:
                if filters.get(key):
                    filter_parts.append(f"{key}:{filters[key]}")
            if filter_parts:
                search_query = f"{query} {' '.join(filter_parts)}"

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/search",
                json={
                    "user_id": self.user_id,
                    "query": search_query,
                    "search_options": {
                        "rag_mode": "graph",
                        "top_k": top_k,
                        "collection_name": self.collection_name,
                    },
                },
            )
            if response.status_code == 200:
                result = parse_sse_response(response.text) or {"sources": []}
                files = []
                for source in result.get("sources", []):
                    meta = source.get("metadata", {})
                    if meta.get("entity_type") == "FILE":
                        files.append(
                            {
                                "path": meta.get("path"),
                                "name": meta.get("name"),
                                "score": source.get("score", 0),
                                "pattern": meta.get("pattern"),
                                "skill": meta.get("skill"),
                                "template": meta.get("template"),
                            }
                        )
                return {"success": True, "query": query, "files": files, "total_count": len(files)}
            return {"success": False, "query": query, "error": response.text}
        except Exception as e:
            return {"success": False, "query": query, "error": str(e)}

    async def find_related_files(
        self, file_path: str, relation_type: Optional[str] = None, max_hops: int = 2
    ) -> Dict[str, Any]:
        """Find files related to the given file."""
        query = f"Find files related to {file_path}"
        if relation_type:
            query += f" through {relation_type} relationship"

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/search",
                json={
                    "user_id": self.user_id,
                    "query": query,
                    "search_options": {
                        "rag_mode": "graph",
                        "top_k": 20,
                        "collection_name": self.collection_name,
                        "options": {
                            "use_neo4j": True,
                            "max_hops": max_hops,
                            "seed_path": file_path,
                        },
                    },
                },
            )
            if response.status_code == 200:
                result = parse_sse_response(response.text) or {"sources": []}
                related = []
                for source in result.get("sources", []):
                    meta = source.get("metadata", {})
                    if meta.get("path") and meta.get("path") != file_path:
                        related.append(
                            {
                                "path": meta.get("path"),
                                "name": meta.get("name"),
                                "relation": "related",
                                "score": source.get("score", 0),
                            }
                        )
                return {
                    "success": True,
                    "file": file_path,
                    "related": related,
                    "count": len(related),
                }
            return {"success": False, "file": file_path, "error": response.text}
        except Exception as e:
            return {"success": False, "file": file_path, "error": str(e)}

    async def get_file_context(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive context for a file using RAG."""
        query = f"Describe the file {file_path}, its purpose, dependencies, and relationships"

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/response",
                json={
                    "user_id": self.user_id,
                    "query": query,
                    "response_options": {
                        "rag_mode": "graph",
                        "context_limit": 5,
                        "enable_citations": True,
                        "collection_name": self.collection_name,
                    },
                },
            )
            if response.status_code == 200:
                result = parse_sse_response(response.text) or {}
                return {
                    "success": True,
                    "file": file_path,
                    "context": result.get("response", ""),
                    "citations": result.get("citations", []),
                }
            return {"success": False, "file": file_path, "error": response.text}
        except Exception as e:
            return {"success": False, "file": file_path, "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        return {
            "files_indexed": self._index_stats.get("files_indexed", 0),
            "relations_extracted": self._index_stats.get("relations_extracted", 0),
        }


# Global client instance
_graph_client: Optional[GraphRAGClient] = None


def get_graph_client() -> GraphRAGClient:
    """Get or create graph RAG client."""
    global _graph_client
    if _graph_client is None:
        _graph_client = GraphRAGClient()
    return _graph_client


# =============================================================================
# Tool Registration
# =============================================================================


def register_graph_rag_tools(mcp: FastMCP):
    """Register Graph RAG tools with the MCP server."""

    @mcp.tool()
    async def graph_rag_health_check() -> dict:
        """Check Graph RAG service health and Digital Service connectivity

        Returns:
            Dict with health status, connectivity info, and capabilities
        """
        try:
            client = get_graph_client()
            result = await client.health_check()

            return tools.create_response(
                status="success" if result.get("healthy") else "error",
                action="graph_rag_health_check",
                data=result,
            )
        except Exception as e:
            logger.error(f"Error in graph_rag_health_check: {e}")
            return tools.create_response(
                status="error", action="graph_rag_health_check", data={}, error_message=str(e)
            )

    @mcp.tool()
    async def graph_rag_index_codebase(
        root_path: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        extract_imports: bool = True,
    ) -> dict:
        """Index a codebase directory and extract file relationships

        Args:
            root_path: Root directory path to index
            include_patterns: Glob patterns to include (default: ['**/*.py', '**/*.yaml', '**/*.md'])
            exclude_patterns: Patterns to exclude (default: ['__pycache__', '.git', 'node_modules', '.venv'])
            extract_imports: Extract import relationships from Python files

        Returns:
            Dict with indexing results, file count, and relation count
        """
        import asyncio
        import ast
        import hashlib
        from pathlib import Path

        try:
            client = get_graph_client()
            include_patterns = include_patterns or ["**/*.py", "**/*.yaml", "**/*.md"]
            exclude_patterns = exclude_patterns or ["__pycache__", ".git", "node_modules", ".venv"]

            root = Path(root_path)
            if not root.exists():
                return tools.create_response(
                    status="error",
                    action="graph_rag_index_codebase",
                    data={"root_path": root_path},
                    error_message=f"Path does not exist: {root_path}",
                )

            # Collect files
            all_files = []
            for pattern in include_patterns:
                all_files.extend(root.glob(pattern))

            # Filter exclusions
            def should_exclude(path):
                path_str = str(path)
                return any(excl in path_str for excl in exclude_patterns)

            all_files = [f for f in all_files if not should_exclude(f)]
            total_files = len(all_files)

            # Language detection
            lang_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".json": "json",
                ".md": "markdown",
                ".sql": "sql",
                ".sh": "shell",
            }

            files_indexed = 0
            relations_extracted = 0
            errors = []

            for file_path in all_files:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]

                    # Extract imports for Python files
                    imports = []
                    packages = []
                    if extract_imports and file_path.suffix == ".py":
                        try:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        imports.append(alias.name)
                                elif isinstance(node, ast.ImportFrom):
                                    if node.module:
                                        imports.append(node.module)
                        except SyntaxError:
                            pass

                        # Known external packages
                        known_packages = {
                            "numpy",
                            "pandas",
                            "fastapi",
                            "flask",
                            "pydantic",
                            "httpx",
                            "requests",
                            "redis",
                            "neo4j",
                            "asyncio",
                        }
                        packages = [
                            imp.split(".")[0]
                            for imp in imports
                            if imp.split(".")[0] in known_packages
                        ]

                    # Store file metadata
                    file_meta = {
                        "path": str(file_path),
                        "name": file_path.name,
                        "extension": file_path.suffix,
                        "language": lang_map.get(file_path.suffix.lower(), "unknown"),
                        "checksum": checksum,
                        "imports": imports[:20],
                        "packages": list(set(packages)),
                    }

                    result = await client.store_file_metadata(file_meta)
                    if result.get("success"):
                        files_indexed += 1

                        # Store package relations
                        for pkg in packages:
                            rel_result = await client.store_relation(
                                str(file_path), pkg, "RELIES_ON_PACKAGE", {"package": pkg}
                            )
                            if rel_result.get("success"):
                                relations_extracted += 1
                    else:
                        errors.append(f"{file_path}: {result.get('error')}")

                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")

            return tools.create_response(
                status="success" if len(errors) == 0 else "partial",
                action="graph_rag_index_codebase",
                data={
                    "root_path": root_path,
                    "total_files": total_files,
                    "files_indexed": files_indexed,
                    "relations_extracted": relations_extracted,
                    "errors": errors[:10],
                    "error_count": len(errors),
                },
            )

        except Exception as e:
            logger.error(f"Error in graph_rag_index_codebase: {e}")
            return tools.create_response(
                status="error",
                action="graph_rag_index_codebase",
                data={"root_path": root_path},
                error_message=str(e),
            )

    @mcp.tool()
    async def graph_rag_register_file(
        path: str,
        template_name: Optional[str] = None,
        pattern_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        skill_name: Optional[str] = None,
        doc_paths: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Register a file with its metadata (template, pattern, skill, docs)

        Args:
            path: File path to register
            template_name: Template used to generate this file
            pattern_name: Pattern this file implements
            agent_name: Agent that created this file
            skill_name: Skill used to create this file
            doc_paths: Paths to related documentation
            metadata: Additional metadata (layer, component, etc.)

        Returns:
            Dict with registration result
        """
        from pathlib import Path

        try:
            client = get_graph_client()
            file_path = Path(path)

            lang_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".json": "json",
                ".md": "markdown",
                ".sql": "sql",
                ".sh": "shell",
            }

            file_meta = {
                "path": str(file_path),
                "name": file_path.name,
                "extension": file_path.suffix,
                "language": lang_map.get(file_path.suffix.lower(), "unknown"),
                "template": template_name,
                "pattern": pattern_name,
                "agent": agent_name,
                "skill": skill_name,
                "doc_paths": doc_paths or [],
                "layer": metadata.get("layer") if metadata else None,
                "component": metadata.get("component") if metadata else None,
            }

            result = await client.store_file_metadata(file_meta)

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="graph_rag_register_file",
                data={"path": path, "registered": result.get("success", False)},
                error_message=result.get("error") if not result.get("success") else None,
            )

        except Exception as e:
            logger.error(f"Error in graph_rag_register_file: {e}")
            return tools.create_response(
                status="error",
                action="graph_rag_register_file",
                data={"path": path},
                error_message=str(e),
            )

    @mcp.tool()
    async def graph_rag_add_relation(
        source_path: str, target_path: str, relation_type: str, properties: Optional[dict] = None
    ) -> dict:
        """Add a relationship between two entities

        Args:
            source_path: Source entity path or name
            target_path: Target entity path or name
            relation_type: Type of relationship (USES_TEMPLATE, USES_PATTERN, DEPENDS_ON, etc.)
            properties: Additional relation properties

        Returns:
            Dict with relation creation result
        """
        try:
            # Validate relation type
            valid_types = [rt.value for rt in RelationType]
            if relation_type not in valid_types:
                return tools.create_response(
                    status="error",
                    action="graph_rag_add_relation",
                    data={"source": source_path, "target": target_path},
                    error_message=f"Invalid relation_type. Must be one of: {valid_types}",
                )

            client = get_graph_client()
            result = await client.store_relation(
                source_path, target_path, relation_type, properties
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="graph_rag_add_relation",
                data={
                    "source": source_path,
                    "target": target_path,
                    "relation_type": relation_type,
                    "created": result.get("success", False),
                },
                error_message=result.get("error") if not result.get("success") else None,
            )

        except Exception as e:
            logger.error(f"Error in graph_rag_add_relation: {e}")
            return tools.create_response(
                status="error",
                action="graph_rag_add_relation",
                data={"source": source_path, "target": target_path},
                error_message=str(e),
            )

    @mcp.tool()
    async def graph_rag_find_dependents(
        file_path: str, depth: int = 1, include_transitive: bool = False
    ) -> dict:
        """Find files that depend on the given file

        Args:
            file_path: File path to find dependents of
            depth: Traversal depth (default: 1, max: 5)
            include_transitive: Include transitive dependents

        Returns:
            Dict with file path and list of dependent files
        """
        try:
            client = get_graph_client()
            depth = min(max(depth, 1), 5)
            max_hops = depth if include_transitive else 1

            result = await client.find_related_files(file_path, "imported_by", max_hops)

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="graph_rag_find_dependents",
                data={
                    "file": file_path,
                    "dependents": result.get("related", []),
                    "count": result.get("count", 0),
                },
                error_message=result.get("error") if not result.get("success") else None,
            )

        except Exception as e:
            logger.error(f"Error in graph_rag_find_dependents: {e}")
            return tools.create_response(
                status="error",
                action="graph_rag_find_dependents",
                data={"file": file_path},
                error_message=str(e),
            )

    @mcp.tool()
    async def graph_rag_find_dependencies(
        file_path: str, include_packages: bool = True, include_services: bool = True, depth: int = 1
    ) -> dict:
        """Find what a file depends on (other files, packages, services)

        Args:
            file_path: File path to find dependencies of
            include_packages: Include external package dependencies
            include_services: Include external service dependencies
            depth: Traversal depth (default: 1)

        Returns:
            Dict with file dependencies categorized by type
        """
        try:
            client = get_graph_client()
            depth = min(max(depth, 1), 5)

            result = await client.find_related_files(file_path, "depends_on", depth)

            related = result.get("related", [])
            files = [
                r for r in related if r.get("relation") in ["imports", "depends_on", "imported_by"]
            ]
            packages = (
                [r for r in related if r.get("relation") == "uses_package"]
                if include_packages
                else []
            )
            services = (
                [r for r in related if r.get("relation") == "uses_service"]
                if include_services
                else []
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="graph_rag_find_dependencies",
                data={
                    "file": file_path,
                    "files": files,
                    "packages": packages,
                    "services": services,
                },
                error_message=result.get("error") if not result.get("success") else None,
            )

        except Exception as e:
            logger.error(f"Error in graph_rag_find_dependencies: {e}")
            return tools.create_response(
                status="error",
                action="graph_rag_find_dependencies",
                data={"file": file_path},
                error_message=str(e),
            )

    @mcp.tool()
    async def graph_rag_search_files(
        query: Optional[str] = None,
        pattern: Optional[str] = None,
        template: Optional[str] = None,
        skill: Optional[str] = None,
        layer: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Search files by pattern, template, skill, or query

        Args:
            query: Search query (searches path and name)
            pattern: Filter by pattern name
            template: Filter by template name
            skill: Filter by skill name
            layer: Filter by CDD layer (domain, prd, design, etc.)
            limit: Maximum results (default: 50)

        Returns:
            Dict with matching files and metadata
        """
        try:
            client = get_graph_client()
            limit = min(limit, 500)

            filters = {}
            if pattern:
                filters["pattern"] = pattern
            if template:
                filters["template"] = template
            if skill:
                filters["skill"] = skill
            if layer:
                filters["layer"] = layer

            search_query = query or "*"
            result = await client.search_files(search_query, filters if filters else None, limit)

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="graph_rag_search_files",
                data={
                    "query": query,
                    "filters": filters,
                    "matches": result.get("files", []),
                    "total_count": result.get("total_count", 0),
                },
                error_message=result.get("error") if not result.get("success") else None,
            )

        except Exception as e:
            logger.error(f"Error in graph_rag_search_files: {e}")
            return tools.create_response(
                status="error",
                action="graph_rag_search_files",
                data={"query": query},
                error_message=str(e),
            )

    @mcp.tool()
    async def graph_rag_get_file_metadata(
        file_path: str, include_relations: bool = True, include_docs: bool = True
    ) -> dict:
        """Get comprehensive metadata for a file including all relationships

        Args:
            file_path: File path to get metadata for
            include_relations: Include all relationships
            include_docs: Include related documentation

        Returns:
            Dict with file metadata, relations, and context
        """
        try:
            client = get_graph_client()
            result = await client.get_file_context(file_path)

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="graph_rag_get_file_metadata",
                data={
                    "file": file_path,
                    "context": result.get("context", ""),
                    "citations": result.get("citations", []),
                },
                error_message=result.get("error") if not result.get("success") else None,
            )

        except Exception as e:
            logger.error(f"Error in graph_rag_get_file_metadata: {e}")
            return tools.create_response(
                status="error",
                action="graph_rag_get_file_metadata",
                data={"file": file_path},
                error_message=str(e),
            )

    @mcp.tool()
    async def graph_rag_get_stats() -> dict:
        """Get graph statistics (node counts, edge counts by type)

        Returns:
            Dict with graph statistics
        """
        try:
            client = get_graph_client()
            health = await client.health_check()
            stats = client.get_stats()

            return tools.create_response(
                status="success",
                action="graph_rag_get_stats",
                data={
                    "files_indexed": stats.get("files_indexed", 0),
                    "relations_extracted": stats.get("relations_extracted", 0),
                    "digital_service_healthy": health.get("healthy", False),
                    "capabilities": health.get("capabilities", {}),
                },
            )

        except Exception as e:
            logger.error(f"Error in graph_rag_get_stats: {e}")
            return tools.create_response(
                status="error", action="graph_rag_get_stats", data={}, error_message=str(e)
            )

    @mcp.tool()
    async def graph_rag_query_relations(
        entity_path: Optional[str] = None,
        relation_type: Optional[str] = None,
        direction: str = "both",
        limit: int = 100,
    ) -> dict:
        """Query relationships in the graph

        Args:
            entity_path: Entity path to query from
            relation_type: Filter by relation type
            direction: Relation direction (outgoing, incoming, both)
            limit: Maximum results (default: 100)

        Returns:
            Dict with entity, dependents, dependencies, and count
        """
        try:
            if not entity_path:
                return tools.create_response(
                    status="error",
                    action="graph_rag_query_relations",
                    data={},
                    error_message="entity_path is required for query_relations",
                )

            client = get_graph_client()
            limit = min(limit, 1000)

            # Get dependents and dependencies
            dependents_result = await client.find_related_files(entity_path, "imported_by", 1)
            deps_result = await client.find_related_files(entity_path, "depends_on", 1)

            dependents = dependents_result.get("related", [])[:limit]
            dependencies = deps_result.get("related", [])[:limit]

            return tools.create_response(
                status="success",
                action="graph_rag_query_relations",
                data={
                    "entity": entity_path,
                    "dependents": dependents,
                    "dependencies": dependencies,
                    "count": len(dependents) + len(dependencies),
                },
            )

        except Exception as e:
            logger.error(f"Error in graph_rag_query_relations: {e}")
            return tools.create_response(
                status="error",
                action="graph_rag_query_relations",
                data={"entity": entity_path},
                error_message=str(e),
            )

    logger.debug("Registered 10 Graph RAG tools")
