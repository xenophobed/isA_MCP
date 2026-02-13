"""
Meta-Tools for Dynamic Tool Discovery and Execution

These tools implement the "discover → execute" pattern for tools, prompts, and resources:

TOOLS:
1. discover() - Search for tools/prompts/resources using hierarchical search
2. get_tool_schema() - Get full schema for a tool before executing
3. execute() - Execute a discovered tool by name
4. list_skills() - List all skill categories

PROMPTS:
5. list_prompts() - List all available prompts
6. get_prompt() - Get a prompt with rendered arguments

RESOURCES:
7. list_resources() - List all available resources
8. read_resource() - Read a resource by URI

This pattern forces Claude to search first, reducing the cognitive load
of choosing from 89+ tools and ensuring the right tool is selected.

Usage:
    # Tools
    1. discover("schedule a meeting") → returns matching tools with scores
    2. get_tool_schema("create_calendar_event") → returns input schema
    3. execute("create_calendar_event", {"title": "Meeting", ...}) → runs tool

    # Prompts
    4. list_prompts() → returns all available prompts
    5. get_prompt("rag_reason_prompt", {"query": "..."}) → returns rendered prompt

    # Resources
    6. list_resources() → returns all available resources
    7. read_resource("knowledge://stats/global") → returns resource content
"""

import json
import logging
import urllib.parse
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Global references (set during registration)
_mcp_server: Optional[FastMCP] = None  # External MCP (what Claude sees)
_internal_mcp: Optional[FastMCP] = None  # Internal MCP (has all tools for execution)
_search_service = None


async def _get_search_service():
    """Get the hierarchical search service."""
    global _search_service
    if _search_service is None:
        from services.search_service.hierarchical_search_service import HierarchicalSearchService

        _search_service = HierarchicalSearchService()
    return _search_service


async def _get_unified_search():
    """Get the unified meta search service."""
    from services.search_service.unified_meta_search import UnifiedMetaSearch

    return UnifiedMetaSearch()


def register_discovery_tools(mcp: FastMCP, internal_mcp: Optional[FastMCP] = None):
    """Register discovery meta-tools with the MCP server.

    Args:
        mcp: The external MCP server (what Claude sees)
        internal_mcp: Optional internal MCP with all tools (for meta_tools_only mode).
                     If provided, execute() will call tools from internal_mcp.
                     If None, execute() calls tools from mcp directly.
    """
    global _mcp_server, _internal_mcp
    _mcp_server = mcp
    _internal_mcp = internal_mcp

    @mcp.tool()
    async def discover(
        query: str, item_type: Optional[str] = None, limit: int = 5
    ) -> Dict[str, Any]:
        """
        🔍 UNIFIED SEARCH - Search across tools, prompts, resources, AND skills.

        With 89+ tools and multiple skills available, this hierarchical search
        helps you find the best match using semantic similarity.

        Args:
            query: Natural language description of what you want to do
                   Examples: "schedule a meeting", "test driven development", "deploy to kubernetes"
            item_type: Filter by type - "tool", "prompt", "resource", or "skill" (optional, None=all)
            limit: Maximum number of results to return (default: 5)

        Returns:
            {
                "matches": [
                    {
                        "name": "tdd",
                        "type": "skill",
                        "source": "vibe",
                        "description": "Test-Driven Development workflow...",
                        "score": 0.85
                    },
                    {
                        "name": "create_calendar_event",
                        "type": "tool",
                        "source": "internal",
                        "description": "Create a new calendar event",
                        "score": 0.82,
                        "skill": "calendar-management"
                    },
                    ...
                ],
                "skills_matched": ["testing", "calendar-management"],
                "total_found": 5
            }

        For tools: use get_tool_schema(name), then execute(name, params)
        For skills: use read_resource("skill://vibe/{name}") to get skill content
        """
        try:
            from services.search_service.unified_meta_search import UnifiedMetaSearch, EntityType

            unified_search = await _get_unified_search()

            # Map item_type string to EntityType list
            entity_types = None
            if item_type:
                type_map = {
                    "tool": [EntityType.TOOL],
                    "prompt": [EntityType.PROMPT],
                    "resource": [EntityType.RESOURCE],
                    "skill": [EntityType.SKILL],
                }
                entity_types = type_map.get(item_type)

            result = await unified_search.search(
                query=query,
                entity_types=entity_types,
                limit=limit,
                skill_limit=3,
                skill_threshold=0.4,
                entity_threshold=0.3,
                include_schemas=False,
                use_hierarchical=True,
            )

            matches = [
                {
                    "name": e.name,
                    "type": e.entity_type.value,
                    "source": e.source,
                    "description": (
                        e.description[:100] + "..." if len(e.description) > 100 else e.description
                    ),
                    "score": round(e.score, 3),
                    "skill": e.primary_skill_id,
                    "uri": e.uri,  # For skills/resources
                }
                for e in result.entities
            ]

            skills_matched = [s.id for s in result.matched_skill_categories]

            logger.info(f"discover('{query}') → {len(matches)} matches via skills {skills_matched}")

            return {
                "matches": matches,
                "skills_matched": skills_matched,
                "total_found": len(matches),
                "by_type": result.metadata.get("results_by_type", {}),
                "hint": "For tools: get_tool_schema() then execute(). For skills: read_resource(uri)",
            }

        except Exception as e:
            logger.error(f"discover() failed: {e}")
            return {"error": str(e), "matches": [], "total_found": 0}

    @mcp.tool()
    async def get_tool_schema(tool_name: str) -> Dict[str, Any]:
        """
        📋 GET TOOL SCHEMA - See the input/output format for a tool.

        Use this after discover() to understand what parameters a tool needs
        before calling execute().

        Args:
            tool_name: The exact name of the tool (from discover results)

        Returns:
            {
                "name": "create_calendar_event",
                "description": "Create a new calendar event",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Event title"},
                        "start_time": {"type": "string", "format": "date-time"},
                        ...
                    },
                    "required": ["title", "start_time"]
                }
            }
        """
        try:
            # Use internal MCP if available (meta_tools_only mode), otherwise external MCP
            target_mcp = _internal_mcp if _internal_mcp is not None else _mcp_server
            if target_mcp is None:
                return {"error": "MCP server not initialized"}

            # Get all tools from target MCP server
            tools = await target_mcp.list_tools()

            # Find the requested tool
            for tool in tools:
                if tool.name == tool_name:
                    return {
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": (
                            tool.inputSchema if hasattr(tool, "inputSchema") else tool.input_schema
                        ),
                    }

            # Tool not found - suggest discovery
            return {
                "error": f"Tool '{tool_name}' not found",
                "hint": "Use discover(query) to find available tools",
            }

        except Exception as e:
            logger.error(f"get_tool_schema() failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def execute(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        ▶️ EXECUTE TOOL - Run a discovered tool with parameters.

        Use this after discover() and get_tool_schema() to execute the tool.

        Args:
            tool_name: The exact name of the tool to execute
            parameters: Dictionary of parameters matching the tool's input schema

        Returns:
            The result from the tool execution, or an error message.

        Example:
            execute("create_calendar_event", {
                "title": "Team Meeting",
                "start_time": "2024-01-15T10:00:00",
                "duration_minutes": 60
            })
        """
        try:
            # Use internal MCP if available (meta_tools_only mode), otherwise external MCP
            target_mcp = _internal_mcp if _internal_mcp is not None else _mcp_server
            if target_mcp is None:
                return {"error": "MCP server not initialized"}

            # Get the tool manager to call the tool
            tool_manager = target_mcp._tool_manager

            # Check if tool exists
            tools = await target_mcp.list_tools()
            tool_exists = any(t.name == tool_name for t in tools)

            if not tool_exists:
                return {
                    "error": f"Tool '{tool_name}' not found",
                    "hint": "Use discover(query) to find available tools",
                }

            # Execute the tool using the tool manager
            # The tool manager handles the actual invocation
            result = await tool_manager.call_tool(tool_name, parameters)

            logger.info(f"execute('{tool_name}') completed successfully")

            # Handle different result types
            if hasattr(result, "content"):
                # MCP ToolResult format
                content = result.content
                if isinstance(content, list) and len(content) > 0:
                    # Extract text from TextContent
                    if hasattr(content[0], "text"):
                        try:
                            return json.loads(content[0].text)
                        except json.JSONDecodeError:
                            return {"result": content[0].text}
                return {"result": str(content)}
            elif isinstance(result, dict):
                return result
            else:
                return {"result": str(result)}

        except Exception as e:
            logger.error(f"execute('{tool_name}') failed: {e}")
            return {
                "error": str(e),
                "tool_name": tool_name,
                "hint": "Check parameters match the schema from get_tool_schema()",
            }

    @mcp.tool()
    async def list_skills() -> Dict[str, Any]:
        """
        📚 LIST ALL SKILL CATEGORIES - See what domains of tools are available.

        Skills are high-level categories that group related tools.
        Use this to understand what capabilities exist before searching.

        Returns:
            {
                "skills": [
                    {"id": "calendar-management", "name": "Calendar Management", "tool_count": 9},
                    {"id": "web-search", "name": "Web Search", "tool_count": 6},
                    ...
                ],
                "total_skills": 15,
                "total_tools": 89
            }
        """
        try:
            from services.skill_service.skill_repository import SkillRepository
            from core.config import get_settings

            settings = get_settings()
            repo = SkillRepository(
                host=settings.infrastructure.postgres_grpc_host,
                port=settings.infrastructure.postgres_grpc_port,
            )

            skills = await repo.list_skills(is_active=True, limit=100)

            skill_list = [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "description": s.get("description", "")[:100],
                    "tool_count": s.get("tool_count", 0),
                }
                for s in skills
            ]

            total_tools = sum(s.get("tool_count", 0) for s in skills)

            return {
                "skills": skill_list,
                "total_skills": len(skill_list),
                "total_tools": total_tools,
                "hint": "Use discover(query) to find tools within a skill domain",
            }

        except Exception as e:
            logger.error(f"list_skills() failed: {e}")
            return {"error": str(e), "skills": []}

    # =========================================================================
    # PROMPT META-TOOLS
    # =========================================================================

    @mcp.tool()
    async def list_prompts() -> Dict[str, Any]:
        """
        📝 LIST ALL PROMPTS - See available prompt templates.

        Prompts are pre-defined templates for common tasks like RAG, analysis, etc.

        Returns:
            {
                "prompts": [
                    {
                        "name": "rag_reason_prompt",
                        "description": "RAG reasoning prompt for knowledge synthesis",
                        "arguments": [{"name": "query", "required": true}, ...]
                    },
                    ...
                ],
                "total_prompts": 50
            }
        """
        try:
            # Use internal MCP if available (meta_tools_only mode)
            target_mcp = _internal_mcp if _internal_mcp is not None else _mcp_server
            if target_mcp is None:
                return {"error": "MCP server not initialized"}

            prompts = await target_mcp.list_prompts()

            prompt_list = [
                {
                    "name": p.name,
                    "description": p.description or "",
                    "arguments": [
                        {
                            "name": arg.name,
                            "description": arg.description or "",
                            "required": arg.required if hasattr(arg, "required") else False,
                        }
                        for arg in (p.arguments or [])
                    ],
                }
                for p in prompts
            ]

            logger.info(f"list_prompts() → {len(prompt_list)} prompts")

            return {
                "prompts": prompt_list,
                "total_prompts": len(prompt_list),
                "hint": "Use get_prompt(name, arguments) to render a prompt",
            }

        except Exception as e:
            logger.error(f"list_prompts() failed: {e}")
            return {"error": str(e), "prompts": []}

    @mcp.tool()
    async def get_prompt(prompt_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        📄 GET PROMPT - Render a prompt template with arguments.

        Use this after list_prompts() to get a fully rendered prompt.

        Args:
            prompt_name: The exact name of the prompt
            arguments: Dictionary of arguments to render into the prompt

        Returns:
            {
                "name": "rag_reason_prompt",
                "messages": [
                    {
                        "role": "user",
                        "content": "Based on the following context..."
                    }
                ]
            }

        Example:
            get_prompt("rag_reason_prompt", {
                "query": "What is machine learning?",
                "context": "Machine learning is a subset of AI..."
            })
        """
        try:
            # Use internal MCP if available (meta_tools_only mode)
            target_mcp = _internal_mcp if _internal_mcp is not None else _mcp_server
            if target_mcp is None:
                return {"error": "MCP server not initialized"}

            # Get the prompt manager
            prompt_manager = target_mcp._prompt_manager

            # Render the prompt with arguments
            messages = await prompt_manager.render_prompt(prompt_name, arguments)

            logger.info(f"get_prompt('{prompt_name}') completed successfully")

            # Format the response
            formatted_messages = []
            for msg in messages:
                content = msg.content
                # Handle different content types
                if hasattr(content, "text"):
                    content_text = content.text
                elif isinstance(content, str):
                    content_text = content
                else:
                    content_text = str(content)

                formatted_messages.append(
                    {"role": msg.role if hasattr(msg, "role") else "user", "content": content_text}
                )

            return {"name": prompt_name, "messages": formatted_messages}

        except Exception as e:
            logger.error(f"get_prompt('{prompt_name}') failed: {e}")
            return {
                "error": str(e),
                "prompt_name": prompt_name,
                "hint": "Use list_prompts() to see available prompts and their arguments",
            }

    # =========================================================================
    # RESOURCE META-TOOLS
    # =========================================================================

    @mcp.tool()
    async def list_resources() -> Dict[str, Any]:
        """
        📂 LIST ALL RESOURCES - See available data resources.

        Resources provide access to knowledge bases, configs, and data.

        Returns:
            {
                "resources": [
                    {
                        "uri": "knowledge://stats/global",
                        "name": "Global Knowledge Stats",
                        "description": "Statistics about the knowledge base",
                        "mime_type": "application/json"
                    },
                    ...
                ],
                "total_resources": 15
            }
        """
        try:
            # Use internal MCP if available (meta_tools_only mode)
            target_mcp = _internal_mcp if _internal_mcp is not None else _mcp_server
            if target_mcp is None:
                return {"error": "MCP server not initialized"}

            resources = await target_mcp.list_resources()

            resource_list = [
                {
                    "uri": str(r.uri),
                    "name": r.name,
                    "description": r.description or "",
                    "mime_type": r.mimeType if hasattr(r, "mimeType") else "application/json",
                }
                for r in resources
            ]

            logger.info(f"list_resources() → {len(resource_list)} resources")

            return {
                "resources": resource_list,
                "total_resources": len(resource_list),
                "hint": "Use read_resource(uri) to get resource content",
            }

        except Exception as e:
            logger.error(f"list_resources() failed: {e}")
            return {"error": str(e), "resources": []}

    @mcp.tool()
    async def read_resource(uri: str) -> Dict[str, Any]:
        """
        📖 READ RESOURCE - Get content from a resource by URI.

        Use this after list_resources() to read resource data.

        Args:
            uri: The resource URI (e.g., "knowledge://stats/global")

        Returns:
            {
                "uri": "knowledge://stats/global",
                "content": { ... },
                "mime_type": "application/json"
            }

        Example:
            read_resource("knowledge://stats/global")
            read_resource("guardrail://config/pii")
        """
        try:
            # Use internal MCP if available (meta_tools_only mode)
            target_mcp = _internal_mcp if _internal_mcp is not None else _mcp_server
            if target_mcp is None:
                return {"error": "MCP server not initialized"}

            # Get the resource manager
            resource_manager = target_mcp._resource_manager

            # Try to get the resource - first with original URI
            resource = None
            try:
                resource = await resource_manager.get_resource(uri)
            except ValueError:
                # If not found, try URL-encoding path segments for template resources
                # This handles URIs like vibe://skill/cdd/guides/prd/design.md
                # which need the path encoded as prd%2Fdesign.md
                if "/guides/" in uri or "/templates/" in uri or "/scripts/" in uri:
                    # Split URI and encode the last path segment
                    parts = uri.rsplit("/", 1)
                    if len(parts) == 2:
                        base, path = parts
                        # Find where the path starts after guides/templates/scripts
                        for segment in ["/guides/", "/templates/", "/scripts/"]:
                            if segment in uri:
                                prefix, suffix = uri.split(segment, 1)
                                encoded_suffix = urllib.parse.quote(suffix, safe="")
                                encoded_uri = f"{prefix}{segment}{encoded_suffix}"
                                try:
                                    resource = await resource_manager.get_resource(encoded_uri)
                                    logger.info(f"Found resource with encoded URI: {encoded_uri}")
                                except ValueError:
                                    pass
                                break

            if resource is None:
                return {
                    "error": f"Resource '{uri}' not found",
                    "hint": "Use list_resources() to see available resource URIs. For paths with slashes, they are auto-encoded.",
                }

            logger.info(f"read_resource('{uri}') completed successfully")

            # Get the content by calling the resource function if it's callable
            if hasattr(resource, "fn") and callable(resource.fn):
                import asyncio

                content = resource.fn()
                if asyncio.iscoroutine(content):
                    content = await content
            elif hasattr(resource, "text"):
                content = resource.text
            else:
                content = str(resource)

            # Try to parse JSON content
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    pass

            mime_type = resource.mimeType if hasattr(resource, "mimeType") else "application/json"

            return {
                "uri": uri,
                "name": resource.name if hasattr(resource, "name") else uri,
                "content": content,
                "mime_type": mime_type,
            }

        except Exception as e:
            logger.error(f"read_resource('{uri}') failed: {e}")
            return {
                "error": str(e),
                "uri": uri,
                "hint": "Use list_resources() to see available resource URIs",
            }

    logger.debug(
        "✅ Discovery meta-tools registered: discover, get_tool_schema, execute, list_skills, list_prompts, get_prompt, list_resources, read_resource"
    )
