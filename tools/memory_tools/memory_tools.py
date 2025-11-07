#!/usr/bin/env python3
"""
Memory Tools for MCP Server
Simple MCP tool wrappers around memory microservice HTTP client
"""

import json
from typing import Optional, List
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from tools.base_tool import BaseTool

from .memory_client import get_memory_client

logger = get_logger(__name__)
tools = BaseTool()


def register_memory_tools(mcp: FastMCP):
    """Register memory tools that call memory microservice via HTTP"""

    security_manager = get_security_manager()

    # ========== CORE STORAGE TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_factual_memory(
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> str:
        """Store factual memory from dialog content using AI extraction

        Args:
            user_id: User identifier
            dialog_content: Dialog content to extract facts from
            importance_score: Importance score (0.0-1.0)
        """
        try:
            client = get_memory_client()

            result = await client.store_factual_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="store_factual_memory",
                data=result
            )

        except Exception as e:
            logger.error(f"Error storing factual memory: {e}")
            return tools.create_response(
                status="error",
                action="store_factual_memory",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_episodic_memory(
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> str:
        """Store episodic memory from dialog content using AI extraction

        Args:
            user_id: User identifier
            dialog_content: Dialog content to extract episodes from
            importance_score: Importance score (0.0-1.0)
        """
        try:
            client = get_memory_client()

            result = await client.store_episodic_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="store_episodic_memory",
                data=result
            )

        except Exception as e:
            logger.error(f"Error storing episodic memory: {e}")
            return tools.create_response(
                status="error",
                action="store_episodic_memory",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_semantic_memory(
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> str:
        """Store semantic memory from dialog content using AI extraction

        Args:
            user_id: User identifier
            dialog_content: Dialog content to extract concepts from
            importance_score: Importance score (0.0-1.0)
        """
        try:
            client = get_memory_client()

            result = await client.store_semantic_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="store_semantic_memory",
                data=result
            )

        except Exception as e:
            logger.error(f"Error storing semantic memory: {e}")
            return tools.create_response(
                status="error",
                action="store_semantic_memory",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_procedural_memory(
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> str:
        """Store procedural memory from dialog content using AI extraction

        Args:
            user_id: User identifier
            dialog_content: Dialog content to extract procedures from
            importance_score: Importance score (0.0-1.0)
        """
        try:
            client = get_memory_client()

            result = await client.store_procedural_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="store_procedural_memory",
                data=result
            )

        except Exception as e:
            logger.error(f"Error storing procedural memory: {e}")
            return tools.create_response(
                status="error",
                action="store_procedural_memory",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_working_memory(
        user_id: str,
        dialog_content: str,
        ttl_seconds: int = 3600,
        importance_score: float = 0.5
    ) -> str:
        """Store working memory from dialog content

        Args:
            user_id: User identifier
            dialog_content: Dialog content for working memory
            ttl_seconds: Time to live in seconds (default 1 hour)
            importance_score: Importance score (0.0-1.0)
        """
        try:
            client = get_memory_client()

            result = await client.store_working_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                ttl_seconds=ttl_seconds,
                importance_score=importance_score
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="store_working_memory",
                data=result
            )

        except Exception as e:
            logger.error(f"Error storing working memory: {e}")
            return tools.create_response(
                status="error",
                action="store_working_memory",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_session_message(
        user_id: str,
        session_id: str,
        message_content: str,
        message_type: str = "human",
        role: str = "user"
    ) -> str:
        """Store session message

        Args:
            user_id: User identifier
            session_id: Session identifier
            message_content: Message content
            message_type: Message type (default "human")
            role: Role (default "user")
        """
        try:
            client = get_memory_client()

            result = await client.store_session_message(
                user_id=user_id,
                session_id=session_id,
                message_content=message_content,
                message_type=message_type,
                role=role
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="store_session_message",
                data=result
            )

        except Exception as e:
            logger.error(f"Error storing session message: {e}")
            return tools.create_response(
                status="error",
                action="store_session_message",
                data={"user_id": user_id, "session_id": session_id},
                error_message=str(e)
            )

    # ========== CORE SEARCH TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_memories(
        user_id: str,
        query: str,
        memory_types: Optional[List[str]] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.4
    ) -> str:
        """Search across memory types using semantic similarity

        Universal search endpoint that can search across all memory types or specific ones.
        If memory_types is not specified, searches all types (factual, episodic, semantic, procedural, working, session).

        Args:
            user_id: User identifier
            query: Search query
            memory_types: Optional list of memory types to search (e.g., ["factual", "semantic"])
            top_k: Maximum number of results per type
            similarity_threshold: Minimum similarity score (0.0-1.0), default 0.4
        """
        try:
            client = get_memory_client()

            result = await client.search_memories(
                user_id=user_id,
                query=query,
                memory_types=memory_types,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )

            return tools.create_response(
                status="success",
                action="search_memories",
                data=result
            )

        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return tools.create_response(
                status="error",
                action="search_memories",
                data={"user_id": user_id, "query": query},
                error_message=str(e)
            )

    # ========== FACTUAL MEMORY SEARCH TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_facts_by_subject(
        user_id: str,
        subject: str,
        limit: int = 10
    ) -> str:
        """Search facts by subject"""
        try:
            client = get_memory_client()

            result = await client.search_facts_by_subject(user_id, subject, limit)

            return tools.create_response(
                status="success",
                action="search_facts_by_subject",
                data=result
            )

        except Exception as e:
            logger.error(f"Error searching facts by subject: {e}")
            return tools.create_response(
                status="error",
                action="search_facts_by_subject",
                data={"user_id": user_id, "subject": subject},
                error_message=str(e)
            )

    # ========== EPISODIC MEMORY SEARCH TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_episodes_by_event_type(
        user_id: str,
        event_type: str,
        limit: int = 10
    ) -> str:
        """Search episodic memories by event type

        Args:
            user_id: User identifier
            event_type: Type of event (e.g., "meeting", "celebration", "travel")
            limit: Maximum number of results (1-100, default 10)
        """
        try:
            client = get_memory_client()

            result = await client.search_episodes_by_event_type(user_id, event_type, limit)

            return tools.create_response(
                status="success",
                action="search_episodes_by_event_type",
                data=result
            )

        except Exception as e:
            logger.error(f"Error searching episodes by event type: {e}")
            return tools.create_response(
                status="error",
                action="search_episodes_by_event_type",
                data={"user_id": user_id, "event_type": event_type},
                error_message=str(e)
            )

    # ========== SEMANTIC MEMORY SEARCH TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_concepts_by_category(
        user_id: str,
        category: str,
        limit: int = 10
    ) -> str:
        """Search semantic concepts by category

        Args:
            user_id: User identifier
            category: Category to search (e.g., "technology", "science", "business")
            limit: Maximum number of results (1-100, default 10)
        """
        try:
            client = get_memory_client()

            result = await client.search_concepts_by_category(user_id, category, limit)

            return tools.create_response(
                status="success",
                action="search_concepts_by_category",
                data=result
            )

        except Exception as e:
            logger.error(f"Error searching concepts by category: {e}")
            return tools.create_response(
                status="error",
                action="search_concepts_by_category",
                data={"user_id": user_id, "category": category},
                error_message=str(e)
            )

    # ========== SESSION MEMORY TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def get_session_context(
        user_id: str,
        session_id: str,
        include_summaries: bool = True,
        max_recent_messages: int = 5
    ) -> str:
        """Get comprehensive session context"""
        try:
            client = get_memory_client()

            result = await client.get_session_context(
                user_id=user_id,
                session_id=session_id,
                include_summaries=include_summaries,
                max_recent_messages=max_recent_messages
            )

            return tools.create_response(
                status="success",
                action="get_session_context",
                data=result
            )

        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return tools.create_response(
                status="error",
                action="get_session_context",
                data={"user_id": user_id, "session_id": session_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def summarize_session(
        user_id: str,
        session_id: str,
        force_update: bool = False,
        compression_level: str = "medium"
    ) -> str:
        """Summarize session conversation intelligently"""
        try:
            client = get_memory_client()

            result = await client.summarize_session(
                user_id=user_id,
                session_id=session_id,
                force_update=force_update,
                compression_level=compression_level
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="summarize_session",
                data=result
            )

        except Exception as e:
            logger.error(f"Error summarizing session: {e}")
            return tools.create_response(
                status="error",
                action="summarize_session",
                data={"user_id": user_id, "session_id": session_id},
                error_message=str(e)
            )

    # ========== WORKING MEMORY TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def get_active_working_memories(
        user_id: str
    ) -> str:
        """Get active working memories"""
        try:
            client = get_memory_client()

            result = await client.get_active_working_memories(user_id)

            return tools.create_response(
                status="success",
                action="get_active_working_memories",
                data=result
            )

        except Exception as e:
            logger.error(f"Error getting active working memories: {e}")
            return tools.create_response(
                status="error",
                action="get_active_working_memories",
                data={"user_id": user_id},
                error_message=str(e)
            )

    # ========== UTILITY TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def get_memory_statistics(
        user_id: str
    ) -> str:
        """Get memory statistics for a user"""
        try:
            client = get_memory_client()

            stats = await client.get_memory_statistics(user_id)

            return tools.create_response(
                status="success",
                action="get_memory_statistics",
                data=stats
            )

        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return tools.create_response(
                status="error",
                action="get_memory_statistics",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def memory_health_check(
    ) -> str:
        """Check memory service health status"""
        try:
            client = get_memory_client()

            health = await client.health_check()

            return tools.create_response(
                status="success",
                action="memory_health_check",
                data=health
            )

        except Exception as e:
            logger.error(f"Error checking memory service health: {e}")
            return tools.create_response(
                status="error",
                action="memory_health_check",
                data={},
                error_message=str(e)
            )
