#!/usr/bin/env python3
"""
Memory Tools for MCP Server
Simple MCP tool wrappers around memory_service.py core functionality
Only includes methods that actually exist in memory_service.py
"""

import json
from typing import Optional, List
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from tools.base_tool import BaseTool

from tools.services.memory_service.memory_service import memory_service
from tools.services.memory_service.models import MemorySearchQuery

logger = get_logger(__name__)
tools = BaseTool()


def register_memory_tools(mcp: FastMCP):
    """Register memory tools that match memory_service.py exactly"""

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
        """Store factual memory from dialog content
        
        Args:
            user_id: User identifier
            dialog_content: Dialog content to extract facts from
            importance_score: Importance score (0.0-1.0)
        """
        try:
            tools.reset_billing()
            
            result = await memory_service.store_factual_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )
            
            return tools.create_response(
                status="success" if result.success else "error",
                action="store_factual_memory",
                data={
                    "memory_id": result.memory_id,
                    "message": result.message,
                    "operation": result.operation,
                    "data": result.data
                }
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
        episode_date: Optional[str] = None,
        importance_score: float = 0.5
    ) -> str:
        """Store episodic memory from dialog content
        
        Args:
            user_id: User identifier
            dialog_content: Dialog content to extract episodes from
            episode_date: Optional ISO date string
            importance_score: Importance score (0.0-1.0)
        """
        try:
            tools.reset_billing()
            
            # Convert episode_date string to datetime if provided
            parsed_date = None
            if episode_date:
                parsed_date = datetime.fromisoformat(episode_date.replace('Z', '+00:00'))
            
            result = await memory_service.store_episodic_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                episode_date=parsed_date,
                importance_score=importance_score
            )
            
            return tools.create_response(
                status="success" if result.success else "error",
                action="store_episodic_memory",
                data={
                    "memory_id": result.memory_id,
                    "message": result.message,
                    "operation": result.operation
                }
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
        """Store semantic memory from dialog content
        
        Args:
            user_id: User identifier
            dialog_content: Dialog content to extract concepts from
            importance_score: Importance score (0.0-1.0)
        """
        try:
            tools.reset_billing()
            
            result = await memory_service.store_semantic_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )
            
            return tools.create_response(
                status="success" if result.success else "error",
                action="store_semantic_memory",
                data={
                    "memory_id": result.memory_id,
                    "message": result.message,
                    "operation": result.operation
                }
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
        """Store procedural memory from dialog content
        
        Args:
            user_id: User identifier
            dialog_content: Dialog content to extract procedures from
            importance_score: Importance score (0.0-1.0)
        """
        try:
            tools.reset_billing()
            
            result = await memory_service.store_procedural_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )
            
            return tools.create_response(
                status="success" if result.success else "error",
                action="store_procedural_memory",
                data={
                    "memory_id": result.memory_id,
                    "message": result.message,
                    "operation": result.operation
                }
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
            tools.reset_billing()
            
            result = await memory_service.store_working_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                current_task_context=None,
                ttl_seconds=ttl_seconds,
                importance_score=importance_score
            )
            
            return tools.create_response(
                status="success" if result.success else "error",
                action="store_working_memory",
                data={
                    "memory_id": result.memory_id,
                    "message": result.message,
                    "operation": result.operation
                }
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
        role: str = "user",
        importance_score: float = 0.5
    ) -> str:
        """Store session message
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            message_content: Message content
            message_type: Message type (default "human")
            role: Role (default "user")
            importance_score: Importance score (0.0-1.0)
        """
        try:
            tools.reset_billing()
            
            result = await memory_service.store_session_message(
                user_id=user_id,
                session_id=session_id,
                message_content=message_content,
                message_type=message_type,
                role=role,
                importance_score=importance_score
            )
            
            return tools.create_response(
                status="success" if result.success else "error",
                action="store_session_message",
                data={
                    "memory_id": result.memory_id,
                    "message": result.message,
                    "operation": result.operation
                }
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
        top_k: int = 10
    ) -> str:
        """Search across memory types using semantic similarity
        
        Args:
            user_id: User identifier
            query: Search query
            memory_types: Optional list of memory types to search
            top_k: Maximum number of results
        """
        try:
            tools.reset_billing()
            
            # Convert memory types from strings to enums if provided
            parsed_types = None
            if memory_types:
                from tools.services.memory_service.models import MemoryType
                parsed_types = []
                for mt in memory_types:
                    if hasattr(MemoryType, mt.upper()):
                        parsed_types.append(getattr(MemoryType, mt.upper()))
            
            search_query = MemorySearchQuery(
                user_id=user_id,
                query=query,
                memory_types=parsed_types,
                top_k=top_k
            )
            
            results = await memory_service.search_memories(search_query)
            
            # Convert results to JSON serializable format
            serialized_results = []
            for result in results:
                serialized_results.append({
                    "memory_id": result.memory_id,
                    "memory_type": result.memory_type,
                    "content": result.content,
                    "similarity_score": result.similarity_score,
                    "rank": result.rank,
                    "metadata": result.metadata
                })
            
            return tools.create_response(
                status="success",
                action="search_memories",
                data={
                    "query": query,
                    "total_results": len(serialized_results),
                    "results": serialized_results
                }
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
            tools.reset_billing()
            
            results = await memory_service.search_facts_by_subject(user_id, subject, limit)
            
            serialized_results = []
            for fact in results:
                serialized_results.append({
                    "id": fact.id,
                    "subject": fact.subject,
                    "predicate": fact.predicate,
                    "object_value": fact.object_value,
                    "fact_type": fact.fact_type,
                    "confidence": fact.confidence,
                    "content": fact.content
                })
            
            return tools.create_response(
                status="success",
                action="search_facts_by_subject",
                data={
                    "subject": subject,
                    "total_results": len(serialized_results),
                    "results": serialized_results
                }
            )
            
        except Exception as e:
            logger.error(f"Error searching facts by subject: {e}")
            return tools.create_response(
                status="error",
                action="search_facts_by_subject",
                data={"user_id": user_id, "subject": subject},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_facts_by_type(
        user_id: str,
        fact_type: str,
        limit: int = 10
    ) -> str:
        """Search facts by fact type"""
        try:
            tools.reset_billing()
            
            results = await memory_service.search_facts_by_fact_type(user_id, fact_type, limit)
            
            serialized_results = []
            for fact in results:
                serialized_results.append({
                    "id": fact.id,
                    "subject": fact.subject,
                    "predicate": fact.predicate,
                    "object_value": fact.object_value,
                    "fact_type": fact.fact_type,
                    "confidence": fact.confidence,
                    "content": fact.content
                })
            
            return tools.create_response(
                status="success",
                action="search_facts_by_type",
                data={
                    "fact_type": fact_type,
                    "total_results": len(serialized_results),
                    "results": serialized_results
                }
            )
            
        except Exception as e:
            logger.error(f"Error searching facts by type: {e}")
            return tools.create_response(
                status="error",
                action="search_facts_by_type",
                data={"user_id": user_id, "fact_type": fact_type},
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
        """Search concepts by category"""
        try:
            tools.reset_billing()
            
            results = await memory_service.search_concepts_by_category(user_id, category, limit)
            
            serialized_results = []
            for concept in results:
                serialized_results.append({
                    "id": concept.id,
                    "concept_type": concept.concept_type,
                    "category": concept.category,
                    "definition": concept.definition,
                    "properties": concept.properties,
                    "content": concept.content
                })
            
            return tools.create_response(
                status="success",
                action="search_concepts_by_category",
                data={
                    "category": category,
                    "total_results": len(serialized_results),
                    "results": serialized_results
                }
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
            tools.reset_billing()
            
            result = await memory_service.get_session_context(
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

    # ========== WORKING MEMORY TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def get_active_working_memories(
        user_id: str
    ) -> str:
        """Get active working memories"""
        try:
            tools.reset_billing()
            
            results = await memory_service.get_active_working_memories(user_id)
            
            serialized_results = []
            for memory in results:
                serialized_results.append({
                    "id": memory.id,
                    "content": memory.content,
                    "priority": memory.priority,
                    "context_type": memory.context_type,
                    "expires_at": memory.expires_at.isoformat() if memory.expires_at else None,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None
                })
            
            return tools.create_response(
                status="success",
                action="get_active_working_memories",
                data={
                    "total_results": len(serialized_results),
                    "results": serialized_results
                }
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
            tools.reset_billing()
            
            stats = await memory_service.get_memory_statistics(user_id)
            
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