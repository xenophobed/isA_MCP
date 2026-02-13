#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Digital Knowledge Resources - MCP Resource Registration

Handles MCP resource registration and management for digital analytics and RAG services.
Provides resource discovery and access control for knowledge base items, documents, and analytics resources.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import json
import uuid

logger = logging.getLogger(__name__)


class DigitalKnowledgeResources:
    """
    MCP Resource Manager for Digital Analytics and RAG resources.

    Features:
    - Knowledge base item registration
    - Document chunk resource management
    - User permission and isolation
    - Resource discovery and search
    - Analytics resource tracking
    - Access control for digital resources
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Digital Knowledge Resources.

        Args:
            config: Resource manager configuration
        """
        self.config = config or {}
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.user_resource_map: Dict[str, Set[str]] = {}
        self.document_chunks: Dict[str, List[str]] = {}  # document_id -> chunk_ids
        self.resource_types = {
            "knowledge_item",
            "document_chunk",
            "rag_session",
            "analytics_report",
            "embedding_collection",
        }

        logger.debug("Digital Knowledge Resources initialized")

    async def register_knowledge_item(
        self, knowledge_id: str, user_id: str, knowledge_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Register a new knowledge base item as an MCP resource.

        Args:
            knowledge_id: Unique knowledge identifier
            user_id: User ID who owns the knowledge
            knowledge_data: Knowledge metadata and information

        Returns:
            Dict containing registration result
        """
        try:
            # Create MCP resource entry for knowledge item
            mcp_resource = {
                "resource_id": knowledge_id,
                "user_id": user_id,
                "type": "knowledge_item",
                "address": f"mcp://rag/{user_id}/{knowledge_id}",
                "registered_at": datetime.now().isoformat(),
                "text_preview": knowledge_data.get("text_preview", ""),
                "text_length": knowledge_data.get("text_length", 0),
                "embedding_model": knowledge_data.get("embedding_model", "unknown"),
                "metadata": knowledge_data.get("metadata", {}),
                "source_file": knowledge_data.get("source_file"),
                "chunk_index": knowledge_data.get("chunk_index", 0),
                "document_id": knowledge_data.get("document_id"),
                "access_permissions": {
                    "owner": user_id,
                    "read_access": [user_id],
                    "write_access": [user_id],
                },
                "capabilities": ["search", "retrieve", "rag_context"],
            }

            # Store resource
            self.resources[knowledge_id] = mcp_resource

            # Update user resource mapping
            if user_id not in self.user_resource_map:
                self.user_resource_map[user_id] = set()
            self.user_resource_map[user_id].add(knowledge_id)

            # Track document chunks if applicable
            document_id = knowledge_data.get("document_id")
            if document_id:
                if document_id not in self.document_chunks:
                    self.document_chunks[document_id] = []
                self.document_chunks[document_id].append(knowledge_id)

            logger.info(f"Knowledge item registered: {knowledge_id} for user {user_id}")

            return {
                "success": True,
                "resource_id": knowledge_id,
                "mcp_address": mcp_resource["address"],
                "user_id": user_id,
                "type": "knowledge_item",
            }

        except Exception as e:
            logger.error(f"Knowledge item registration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "resource_id": knowledge_id,
                "user_id": user_id,
            }

    async def register_rag_session(
        self, session_id: str, user_id: str, session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Register a RAG session as an MCP resource.

        Args:
            session_id: Unique session identifier
            user_id: User ID who owns the session
            session_data: Session metadata and information

        Returns:
            Dict containing registration result
        """
        try:
            # Create MCP resource entry for RAG session
            mcp_resource = {
                "resource_id": session_id,
                "user_id": user_id,
                "type": "rag_session",
                "address": f"mcp://rag_session/{user_id}/{session_id}",
                "registered_at": datetime.now().isoformat(),
                "query": session_data.get("query", ""),
                "context_used": session_data.get("context_used", 0),
                "response_length": session_data.get("response_length", 0),
                "knowledge_items_used": session_data.get("knowledge_items_used", []),
                "metadata": session_data.get("metadata", {}),
                "access_permissions": {
                    "owner": user_id,
                    "read_access": [user_id],
                    "write_access": [user_id],
                },
                "capabilities": ["replay", "analyze", "export"],
            }

            # Store resource
            self.resources[session_id] = mcp_resource

            # Update user resource mapping
            if user_id not in self.user_resource_map:
                self.user_resource_map[user_id] = set()
            self.user_resource_map[user_id].add(session_id)

            logger.info(f"RAG session registered: {session_id} for user {user_id}")

            return {
                "success": True,
                "resource_id": session_id,
                "mcp_address": mcp_resource["address"],
                "user_id": user_id,
                "type": "rag_session",
            }

        except Exception as e:
            logger.error(f"RAG session registration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "resource_id": session_id,
                "user_id": user_id,
            }

    async def get_resource(self, resource_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get resource information with permission check.

        Args:
            resource_id: Resource identifier
            user_id: User requesting the resource

        Returns:
            Dict containing resource information
        """
        try:
            if resource_id not in self.resources:
                return {"success": False, "error": "Resource not found", "resource_id": resource_id}

            resource = self.resources[resource_id]

            # Check read permissions
            if user_id not in resource["access_permissions"]["read_access"]:
                return {
                    "success": False,
                    "error": "Access denied",
                    "resource_id": resource_id,
                    "user_id": user_id,
                }

            return {"success": True, "resource": resource, "user_id": user_id}

        except Exception as e:
            logger.error(f"Get resource failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "resource_id": resource_id,
                "user_id": user_id,
            }

    async def get_user_resources(
        self, user_id: str, resource_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all resources for a specific user, optionally filtered by type.

        Args:
            user_id: User identifier
            resource_type: Optional resource type filter

        Returns:
            Dict containing user's resources
        """
        try:
            user_resources = []

            if user_id in self.user_resource_map:
                for resource_id in self.user_resource_map[user_id]:
                    if resource_id in self.resources:
                        resource = self.resources[resource_id]

                        # Apply type filter if specified
                        if resource_type and resource["type"] != resource_type:
                            continue

                        # Create resource summary
                        resource_summary = {
                            "resource_id": resource_id,
                            "type": resource["type"],
                            "address": resource["address"],
                            "registered_at": resource["registered_at"],
                            "capabilities": resource.get("capabilities", []),
                        }

                        # Add type-specific information
                        if resource["type"] == "knowledge_item":
                            resource_summary.update(
                                {
                                    "text_preview": resource.get("text_preview", ""),
                                    "text_length": resource.get("text_length", 0),
                                    "embedding_model": resource.get("embedding_model", ""),
                                    "chunk_index": resource.get("chunk_index", 0),
                                    "document_id": resource.get("document_id"),
                                }
                            )
                        elif resource["type"] == "rag_session":
                            resource_summary.update(
                                {
                                    "query": resource.get("query", ""),
                                    "context_used": resource.get("context_used", 0),
                                    "knowledge_items_used": resource.get(
                                        "knowledge_items_used", []
                                    ),
                                }
                            )

                        user_resources.append(resource_summary)

            return {
                "success": True,
                "user_id": user_id,
                "resource_type_filter": resource_type,
                "resource_count": len(user_resources),
                "resources": user_resources,
            }

        except Exception as e:
            logger.error(f"Get user resources failed: {e}")
            return {"success": False, "error": str(e), "user_id": user_id}

    async def get_document_chunks(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get all chunk resources for a specific document.

        Args:
            document_id: Document identifier
            user_id: User requesting the chunks

        Returns:
            Dict containing document chunk resources
        """
        try:
            if document_id not in self.document_chunks:
                return {
                    "success": True,
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunks": [],
                    "chunk_count": 0,
                }

            chunk_resources = []
            chunk_ids = self.document_chunks[document_id]

            for chunk_id in chunk_ids:
                if chunk_id in self.resources:
                    resource = self.resources[chunk_id]

                    # Check permissions
                    if user_id in resource["access_permissions"]["read_access"]:
                        chunk_resources.append(
                            {
                                "resource_id": chunk_id,
                                "address": resource["address"],
                                "chunk_index": resource.get("chunk_index", 0),
                                "text_preview": resource.get("text_preview", ""),
                                "text_length": resource.get("text_length", 0),
                                "registered_at": resource["registered_at"],
                            }
                        )

            return {
                "success": True,
                "document_id": document_id,
                "user_id": user_id,
                "chunks": chunk_resources,
                "chunk_count": len(chunk_resources),
            }

        except Exception as e:
            logger.error(f"Get document chunks failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id,
                "user_id": user_id,
            }

    async def delete_resource(self, resource_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a resource with permission check.

        Args:
            resource_id: Resource identifier
            user_id: User requesting deletion

        Returns:
            Dict containing deletion result
        """
        try:
            if resource_id not in self.resources:
                return {"success": False, "error": "Resource not found", "resource_id": resource_id}

            resource = self.resources[resource_id]

            # Check write permissions
            if user_id not in resource["access_permissions"]["write_access"]:
                return {
                    "success": False,
                    "error": "Access denied",
                    "resource_id": resource_id,
                    "user_id": user_id,
                }

            # Remove from document chunks mapping if applicable
            document_id = resource.get("document_id")
            if document_id and document_id in self.document_chunks:
                if resource_id in self.document_chunks[document_id]:
                    self.document_chunks[document_id].remove(resource_id)
                if not self.document_chunks[document_id]:
                    del self.document_chunks[document_id]

            # Remove from resources
            del self.resources[resource_id]

            # Remove from user mapping
            if user_id in self.user_resource_map:
                self.user_resource_map[user_id].discard(resource_id)

            logger.info(f"Resource deleted: {resource_id} by user {user_id}")

            return {"success": True, "resource_id": resource_id, "user_id": user_id}

        except Exception as e:
            logger.error(f"Delete resource failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "resource_id": resource_id,
                "user_id": user_id,
            }

    async def search_resources(
        self, user_id: str, query: str, resource_type: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search resources by query and type.

        Args:
            user_id: User identifier
            query: Search query
            resource_type: Optional resource type filter
            limit: Maximum number of results

        Returns:
            Dict containing search results
        """
        try:
            matching_resources = []
            query_lower = query.lower()

            for resource_id, resource in self.resources.items():
                # Check if user has read access
                if user_id not in resource["access_permissions"]["read_access"]:
                    continue

                # Type filter
                if resource_type and resource["type"] != resource_type:
                    continue

                # Search in resource content
                search_matches = []

                # Search in text preview for knowledge items
                if resource["type"] == "knowledge_item":
                    text_preview = resource.get("text_preview", "").lower()
                    if query_lower in text_preview:
                        search_matches.append("text_content")

                # Search in query for RAG sessions
                if resource["type"] == "rag_session":
                    session_query = resource.get("query", "").lower()
                    if query_lower in session_query:
                        search_matches.append("session_query")

                # Search in metadata
                metadata_text = json.dumps(resource.get("metadata", {}), ensure_ascii=False).lower()
                if query_lower in metadata_text:
                    search_matches.append("metadata")

                # Search in resource ID and address
                if query_lower in resource_id.lower() or query_lower in resource["address"].lower():
                    search_matches.append("identifier")

                if search_matches:
                    matching_resources.append(
                        {
                            "resource_id": resource_id,
                            "address": resource["address"],
                            "type": resource["type"],
                            "registered_at": resource["registered_at"],
                            "search_matches": search_matches,
                            "text_preview": resource.get("text_preview", "")[:100],
                            "metadata": resource.get("metadata", {}),
                            "is_owner": resource["access_permissions"]["owner"] == user_id,
                        }
                    )

                # Limit results
                if len(matching_resources) >= limit:
                    break

            return {
                "success": True,
                "user_id": user_id,
                "query": query,
                "resource_type_filter": resource_type,
                "matching_resources": matching_resources,
                "result_count": len(matching_resources),
                "limit_applied": len(matching_resources) >= limit,
            }

        except Exception as e:
            logger.error(f"Search resources failed: {e}")
            return {"success": False, "error": str(e), "user_id": user_id, "query": query}

    async def get_resource_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get analytics about user's digital resources.

        Args:
            user_id: User identifier

        Returns:
            Dict containing resource analytics
        """
        try:
            if user_id not in self.user_resource_map:
                return {
                    "success": True,
                    "user_id": user_id,
                    "analytics": {
                        "total_resources": 0,
                        "resource_types": {},
                        "knowledge_stats": {},
                        "document_stats": {},
                        "rag_session_stats": {},
                    },
                }

            user_resource_ids = self.user_resource_map[user_id]
            analytics = {
                "total_resources": len(user_resource_ids),
                "resource_types": {},
                "knowledge_stats": {
                    "total_items": 0,
                    "total_text_length": 0,
                    "avg_text_length": 0,
                    "embedding_models": {},
                    "documents": 0,
                },
                "document_stats": {
                    "total_documents": len(self.document_chunks),
                    "total_chunks": 0,
                    "avg_chunks_per_document": 0,
                },
                "rag_session_stats": {
                    "total_sessions": 0,
                    "total_queries": 0,
                    "avg_context_used": 0,
                },
            }

            knowledge_text_lengths = []
            context_usage = []

            for resource_id in user_resource_ids:
                if resource_id in self.resources:
                    resource = self.resources[resource_id]
                    resource_type = resource["type"]

                    # Count resource types
                    analytics["resource_types"][resource_type] = (
                        analytics["resource_types"].get(resource_type, 0) + 1
                    )

                    # Knowledge item analytics
                    if resource_type == "knowledge_item":
                        analytics["knowledge_stats"]["total_items"] += 1
                        text_length = resource.get("text_length", 0)
                        analytics["knowledge_stats"]["total_text_length"] += text_length
                        knowledge_text_lengths.append(text_length)

                        embedding_model = resource.get("embedding_model", "unknown")
                        analytics["knowledge_stats"]["embedding_models"][embedding_model] = (
                            analytics["knowledge_stats"]["embedding_models"].get(embedding_model, 0)
                            + 1
                        )

                        if resource.get("document_id"):
                            analytics["knowledge_stats"]["documents"] += 1

                    # RAG session analytics
                    elif resource_type == "rag_session":
                        analytics["rag_session_stats"]["total_sessions"] += 1
                        analytics["rag_session_stats"]["total_queries"] += 1
                        context_used = resource.get("context_used", 0)
                        context_usage.append(context_used)

            # Calculate averages
            if knowledge_text_lengths:
                analytics["knowledge_stats"]["avg_text_length"] = sum(knowledge_text_lengths) / len(
                    knowledge_text_lengths
                )

            if context_usage:
                analytics["rag_session_stats"]["avg_context_used"] = sum(context_usage) / len(
                    context_usage
                )

            # Document chunk statistics
            user_document_chunks = 0
            user_documents = set()
            for doc_id, chunk_ids in self.document_chunks.items():
                # Check if any chunks belong to this user
                user_chunks_in_doc = [cid for cid in chunk_ids if cid in user_resource_ids]
                if user_chunks_in_doc:
                    user_documents.add(doc_id)
                    user_document_chunks += len(user_chunks_in_doc)

            analytics["document_stats"]["total_documents"] = len(user_documents)
            analytics["document_stats"]["total_chunks"] = user_document_chunks
            if user_documents:
                analytics["document_stats"]["avg_chunks_per_document"] = user_document_chunks / len(
                    user_documents
                )

            return {"success": True, "user_id": user_id, "analytics": analytics}

        except Exception as e:
            logger.error(f"Get resource analytics failed: {e}")
            return {"success": False, "error": str(e), "user_id": user_id}

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global resource statistics."""
        try:
            stats = {
                "total_resources": len(self.resources),
                "total_users": len(self.user_resource_map),
                "resource_types": {},
                "resources_per_user": {},
                "total_documents": len(self.document_chunks),
                "total_chunks": sum(len(chunks) for chunks in self.document_chunks.values()),
                "supported_types": list(self.resource_types),
            }

            # Count resource types
            for resource in self.resources.values():
                resource_type = resource["type"]
                stats["resource_types"][resource_type] = (
                    stats["resource_types"].get(resource_type, 0) + 1
                )

            # Count resources per user
            for user_id, resource_ids in self.user_resource_map.items():
                stats["resources_per_user"][str(user_id)] = len(resource_ids)

            return stats

        except Exception as e:
            logger.error(f"Get global stats failed: {e}")
            return {"error": str(e)}


# Global instance
digital_knowledge_resources = DigitalKnowledgeResources()

# ============================================================================
# MCP RESOURCE REGISTRATION
# ============================================================================


def register_digital_resource(mcp):
    """
    Register digital knowledge resources with MCP server

    Exposes user knowledge base, RAG sessions, and digital analytics
    resources for agent access.
    """
    from mcp.server.fastmcp import FastMCP

    @mcp.resource("knowledge://stats/global")
    def get_knowledge_stats() -> str:
        """
        Get global knowledge base statistics

        Provides overview of registered knowledge items, users, and resource types.

        Keywords: knowledge, statistics, overview, analytics, global
        Category: knowledge
        """
        stats = digital_knowledge_resources.get_global_stats()
        return json.dumps(
            {
                "description": "Global Knowledge Base Statistics",
                "stats": stats,
                "usage": "Use to understand available knowledge resources",
            },
            indent=2,
        )

    @mcp.resource("knowledge://user/{user_id}/resources")
    def get_user_resources(user_id: str) -> str:
        """
        Get knowledge resources for a specific user

        Lists all knowledge items, documents, and RAG sessions owned by the user.

        Keywords: knowledge, user, resources, personal, knowledge-base
        Category: knowledge
        """
        user_resources = digital_knowledge_resources.get_user_resources(user_id)

        if not user_resources.get("success"):
            return json.dumps(
                {"error": user_resources.get("error", "User not found"), "user_id": user_id},
                indent=2,
            )

        return json.dumps(
            {
                "description": f"Knowledge resources for user {user_id}",
                "user_id": user_id,
                "total_resources": user_resources["total_resources"],
                "resources": user_resources["resources"],
                "usage": "These are the knowledge items available for this user",
            },
            indent=2,
        )

    @mcp.resource("knowledge://types/supported")
    def get_supported_types() -> str:
        """
        Get supported knowledge resource types

        Lists all types of knowledge resources that can be registered and accessed.

        Keywords: knowledge, types, supported, capabilities, resource-types
        Category: knowledge
        """
        return json.dumps(
            {
                "description": "Supported Knowledge Resource Types",
                "types": list(digital_knowledge_resources.resource_types),
                "details": {
                    "knowledge_item": "Individual knowledge base entries with embeddings",
                    "document_chunk": "Chunked document sections for RAG",
                    "rag_session": "Active RAG conversation sessions",
                    "analytics_report": "Digital analytics reports",
                    "embedding_collection": "Collections of semantic embeddings",
                },
                "usage": "Reference these types when working with knowledge resources",
            },
            indent=2,
        )

    logger.debug("Registered digital knowledge resources")


# Export for auto-discovery
__all__ = ["DigitalKnowledgeResources", "digital_knowledge_resources", "register_digital_resource"]
