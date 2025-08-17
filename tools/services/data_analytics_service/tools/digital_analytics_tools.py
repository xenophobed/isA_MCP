#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Digital Analytics and RAG Tools
Knowledge management and retrieval tools based on BaseTool
"""

import json
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.data_analytics_service.services.digital_analytics_service import get_digital_analytics_service
from core.logging import get_logger

logger = get_logger(__name__)

class DigitalAnalyticsTool(BaseTool):
    """Digital analytics tool for knowledge management and RAG operations using unified service"""
    
    def __init__(self):
        super().__init__()
        self.analytics_service = get_digital_analytics_service()
    
    async def store_knowledge(
        self,
        user_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store text as knowledge with embedding generation
        
        Args:
            user_id: User identifier
            text: Text content to store
            metadata: Optional metadata for the knowledge item
        """
        try:
            result = await self.analytics_service.store_knowledge(user_id, text, metadata)
            
            return self.create_response(
                "success" if result['success'] else "error",
                "store_knowledge",
                result,
                result.get('error') if not result['success'] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "store_knowledge",
                {},
                f"Knowledge storage failed: {str(e)}"
            )
    
    async def search_knowledge(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        enable_rerank: bool = False
    ) -> str:
        """
        Search user's knowledge base with optional reranking
        
        Args:
            user_id: User identifier
            query: Search query
            top_k: Number of results to return
            enable_rerank: Enable reranking for better relevance
        """
        try:
            result = await self.analytics_service.search_knowledge(
                user_id, query, top_k, enable_rerank
            )
            
            return self.create_response(
                "success" if result['success'] else "error",
                "search_knowledge",
                result,
                result.get('error') if not result['success'] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "search_knowledge",
                {},
                f"Knowledge search failed: {str(e)}"
            )
    
    async def generate_rag_response(
        self,
        user_id: str,
        query: str,
        context_limit: int = 3
    ) -> str:
        """
        Generate response using RAG pipeline
        
        Args:
            user_id: User identifier
            query: User query
            context_limit: Maximum context items to use
        """
        try:
            result = await self.analytics_service.generate_rag_response(
                user_id, query, context_limit
            )
            
            return self.create_response(
                "success" if result['success'] else "error",
                "generate_rag_response",
                result,
                result.get('error') if not result['success'] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "generate_rag_response",
                {},
                f"RAG response generation failed: {str(e)}"
            )
    
    async def add_document(
        self,
        user_id: str,
        document: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add document with automatic chunking
        
        Args:
            user_id: User identifier
            document: Document text to add
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
            metadata: Metadata for all chunks
        """
        try:
            result = await self.analytics_service.add_document(
                user_id, document, chunk_size, overlap, metadata
            )
            
            return self.create_response(
                "success" if result['success'] else "error",
                "add_document",
                result,
                result.get('error') if not result['success'] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "add_document",
                {},
                f"Document addition failed: {str(e)}"
            )
    
    async def list_user_knowledge(self, user_id: str) -> str:
        """
        List all knowledge items for a user
        
        Args:
            user_id: User identifier
        """
        try:
            result = await self.analytics_service.list_user_knowledge(user_id)
            
            return self.create_response(
                "success" if result['success'] else "error",
                "list_user_knowledge",
                result,
                result.get('error') if not result['success'] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "list_user_knowledge",
                {},
                f"Knowledge listing failed: {str(e)}"
            )
    
    async def get_knowledge_item(
        self,
        user_id: str,
        knowledge_id: str
    ) -> str:
        """
        Get specific knowledge item
        
        Args:
            user_id: User identifier
            knowledge_id: Knowledge item identifier
        """
        try:
            result = await self.analytics_service.get_knowledge_item(user_id, knowledge_id)
            
            return self.create_response(
                "success" if result['success'] else "error",
                "get_knowledge_item",
                result,
                result.get('error') if not result['success'] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "get_knowledge_item",
                {},
                f"Knowledge retrieval failed: {str(e)}"
            )
    
    async def delete_knowledge_item(
        self,
        user_id: str,
        knowledge_id: str
    ) -> str:
        """
        Delete a knowledge item
        
        Args:
            user_id: User identifier
            knowledge_id: Knowledge item identifier
        """
        try:
            result = await self.analytics_service.delete_knowledge_item(user_id, knowledge_id)
            
            return self.create_response(
                "success" if result['success'] else "error",
                "delete_knowledge_item",
                result,
                result.get('error') if not result['success'] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "delete_knowledge_item",
                {},
                f"Knowledge deletion failed: {str(e)}"
            )
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        top_k: int = 5
    ) -> str:
        """
        Retrieve relevant context for a query
        
        Args:
            user_id: User identifier
            query: Search query
            top_k: Number of context items to return
        """
        try:
            result = await self.analytics_service.retrieve_context(user_id, query, top_k)
            
            return self.create_response(
                "success" if result['success'] else "error",
                "retrieve_context",
                result,
                result.get('error') if not result['success'] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "retrieve_context",
                {},
                f"Context retrieval failed: {str(e)}"
            )


def register_digital_analytics_tools(mcp: FastMCP):
    """Register digital analytics and RAG tools"""
    digital_tool = DigitalAnalyticsTool()
    
    @mcp.tool()
    async def store_knowledge(
        user_id: str,
        text: str,
        metadata: str = "{}"  # JSON string
    ) -> str:
        """
        Store text as knowledge with automatic embedding generation and MCP registration
        
        This tool stores text content in a user's personal knowledge base with vector embeddings for semantic search.
        
        Keywords: store, knowledge, embedding, save, add, memory
        Category: knowledge_management
        
        Args:
            user_id: User identifier for knowledge isolation
            text: Text content to store in the knowledge base
            metadata: Additional metadata as JSON string (e.g., {"source": "book", "topic": "AI"})
        """
        try:
            metadata_dict = json.loads(metadata) if metadata != "{}" else {}
        except json.JSONDecodeError:
            metadata_dict = {"raw_metadata": metadata}
        
        return await digital_tool.store_knowledge(user_id, text, metadata_dict)
    
    @mcp.tool()
    async def search_knowledge(
        user_id: str,
        query: str,
        top_k: int = 5,
        enable_rerank: bool = False
    ) -> str:
        """
        Search user's knowledge base with semantic similarity and optional reranking
        
        This tool performs semantic search across a user's knowledge base to find relevant content.
        
        Keywords: search, find, query, semantic, knowledge, similarity
        Category: knowledge_management
        
        Args:
            user_id: User identifier for knowledge isolation
            query: Search query to find relevant knowledge
            top_k: Number of top results to return (default: 5)
            enable_rerank: Enable reranking for improved relevance scoring (default: False)
        """
        return await digital_tool.search_knowledge(user_id, query, top_k, enable_rerank)
    
    @mcp.tool()
    async def generate_rag_response(
        user_id: str,
        query: str,
        context_limit: int = 3
    ) -> str:
        """
        Generate response using RAG (Retrieval-Augmented Generation) pipeline
        
        This tool retrieves relevant context from the user's knowledge base and generates informed responses.
        
        Keywords: generate, RAG, response, answer, context, intelligent
        Category: knowledge_management
        
        Args:
            user_id: User identifier for knowledge isolation
            query: User question or query for response generation
            context_limit: Maximum number of context items to use (default: 3)
        """
        return await digital_tool.generate_rag_response(user_id, query, context_limit)
    
    @mcp.tool()
    async def add_document(
        user_id: str,
        document: str,
        chunk_size: int = 400,
        overlap: int = 50,
        metadata: str = "{}"  # JSON string
    ) -> str:
        """
        Add long document with automatic chunking and storage
        
        This tool processes long documents by splitting them into manageable chunks with embeddings.
        
        Keywords: document, add, chunk, process, long_text, split
        Category: knowledge_management
        
        Args:
            user_id: User identifier for knowledge isolation
            document: Long document text to process and store
            chunk_size: Size of each text chunk in characters (default: 400)
            overlap: Character overlap between chunks (default: 50)
            metadata: Document metadata as JSON string (e.g., {"title": "Manual", "author": "John"})
        """
        try:
            metadata_dict = json.loads(metadata) if metadata != "{}" else {}
        except json.JSONDecodeError:
            metadata_dict = {"raw_metadata": metadata}
        
        return await digital_tool.add_document(user_id, document, chunk_size, overlap, metadata_dict)
    
    @mcp.tool()
    async def list_user_knowledge(user_id: str) -> str:
        """
        List all knowledge items for a user with previews and metadata
        
        This tool provides an overview of all stored knowledge items for a specific user.
        
        Keywords: list, knowledge, overview, inventory, user_data
        Category: knowledge_management
        
        Args:
            user_id: User identifier for knowledge isolation
        """
        return await digital_tool.list_user_knowledge(user_id)
    
    @mcp.tool()
    async def get_knowledge_item(
        user_id: str,
        knowledge_id: str
    ) -> str:
        """
        Get complete details of a specific knowledge item
        
        This tool retrieves full information about a specific knowledge item including metadata and MCP address.
        
        Keywords: get, knowledge, details, item, specific, retrieve
        Category: knowledge_management
        
        Args:
            user_id: User identifier for knowledge isolation
            knowledge_id: Unique identifier of the knowledge item
        """
        return await digital_tool.get_knowledge_item(user_id, knowledge_id)
    
    @mcp.tool()
    async def delete_knowledge_item(
        user_id: str,
        knowledge_id: str
    ) -> str:
        """
        Delete a specific knowledge item and its MCP registration
        
        This tool permanently removes a knowledge item from the user's knowledge base.
        
        Keywords: delete, remove, knowledge, item, cleanup
        Category: knowledge_management
        
        Args:
            user_id: User identifier for knowledge isolation
            knowledge_id: Unique identifier of the knowledge item to delete
        """
        return await digital_tool.delete_knowledge_item(user_id, knowledge_id)
    
    @mcp.tool()
    async def retrieve_context(
        user_id: str,
        query: str,
        top_k: int = 5
    ) -> str:
        """
        Retrieve relevant context items for a query without generating responses
        
        This tool finds and returns relevant knowledge items that match a query for context building.
        
        Keywords: context, retrieve, relevant, similarity, background
        Category: knowledge_management
        
        Args:
            user_id: User identifier for knowledge isolation
            query: Query to find relevant context for
            top_k: Number of relevant context items to return (default: 5)
        """
        return await digital_tool.retrieve_context(user_id, query, top_k)
    
    @mcp.tool()
    async def get_analytics_service_status() -> str:
        """
        Get current status and configuration of the Digital Analytics Service
        
        This tool provides information about the analytics service configuration and health status.
        
        Keywords: status, health, configuration, service, analytics
        Category: system_info
        """
        service = get_digital_analytics_service()
        status = await service.get_service_stats()
        
        return json.dumps(status, indent=2, ensure_ascii=False)
    
    print("Digital Analytics and RAG tools registered successfully")