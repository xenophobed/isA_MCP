#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Digital Tools - Simplified 3-Function RAG Interface
Simple, unified interface for RAG operations

Replaces the complex 16-function interface with just 3 essential functions:
1. store_knowledge - Universal storage (text, documents, images)
2. search_knowledge - Universal search with all options  
3. knowledge_response - Universal RAG response generation
"""

import json
from typing import Dict, List, Any, Optional, Union
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.data_analytics_service.services.digital_service import (
    get_digital_analytics_service,
    DigitalAnalyticsService
)
from core.logging import get_logger

logger = get_logger(__name__)

class DigitalTool(BaseTool):
    """Simplified digital analytics tool with 3 core functions"""
    
    def __init__(self):
        super().__init__()
        self.analytics_service = get_digital_analytics_service()

def register_digital_tools(mcp: FastMCP):
    """Register simplified 3-function digital tools"""
    digital_tool = DigitalTool()
    
    @mcp.tool()
    async def store_knowledge(
        user_id: str,
        content: str,
        content_type: str = "text",
        metadata: dict = None,
        options: dict = None
    ) -> str:
        """
        Universal knowledge storage - handles text, documents, and images
        
        This is the unified storage interface for all content types in the knowledge base.
        
        Keywords: store, save, add, knowledge, document, image, text
        Category: core_knowledge
        
        Args:
            user_id: User identifier for knowledge isolation
            content: Content to store (text/document content, or image file path)
            content_type: Type of content - "text", "document", "image"
            metadata: Additional metadata as dict (e.g. {"source": "manual", "topic": "AI"})
            options: Storage options as dict (e.g. {"chunk_size": 400, "overlap": 50, "model": "gpt-4o-mini"})
        
        Examples:
            # Store text
            store_knowledge(user_id="user1", content="Python is a programming language", content_type="text")
            
            # Store document with chunking
            store_knowledge(user_id="user1", content="Long document...", content_type="document", 
                          options={"chunk_size": 400, "overlap": 50})
            
            # Store image
            store_knowledge(user_id="user1", content="/path/to/image.jpg", content_type="image",
                          options={"model": "gpt-4o-mini", "description_prompt": "Describe this image"})
        """
        try:
            metadata = metadata or {}
            options = options or {}
            
            # Route to appropriate storage method based on content_type
            if content_type == "text":
                result = await digital_tool.analytics_service.store_knowledge(
                    user_id, content, metadata
                )
                
            elif content_type == "document":
                chunk_size = options.get("chunk_size", 400)
                overlap = options.get("overlap", 50)
                result = await digital_tool.analytics_service.add_document(
                    user_id, content, chunk_size, overlap, metadata
                )
                
            elif content_type == "image":
                model = options.get("model", "gpt-4o-mini")
                description_prompt = options.get("description_prompt", 
                    "Describe this image in detail, including objects, scene, colors, composition, and any text visible.")
                result = await digital_tool.analytics_service.store_image(
                    user_id, content, metadata, description_prompt, model
                )
                
            else:
                return digital_tool.create_response(
                    "error", "store_knowledge", {},
                    f"Unsupported content_type: {content_type}. Use 'text', 'document', or 'image'"
                )
            
            return digital_tool.create_response(
                "success" if result.get('success') else "error",
                "store_knowledge", 
                {**result, "content_type": content_type},
                result.get('error') if not result.get('success') else None
            )
            
        except Exception as e:
            return digital_tool.create_response(
                "error", "store_knowledge", {},
                f"Storage failed: {str(e)}"
            )
    
    @mcp.tool()
    async def search_knowledge(
        user_id: str,
        query: str,
        search_options: dict = None
    ) -> str:
        """
        Universal knowledge search - handles all search types and modes
        
        This is the unified search interface supporting semantic, hybrid, and filtered search.
        
        Keywords: search, find, query, semantic, similarity, retrieve
        Category: core_knowledge
        
        Args:
            user_id: User identifier for knowledge isolation  
            query: Search query text
            search_options: Search configuration as dict with options:
                - top_k: Number of results (default: 5)
                - enable_rerank: Enable reranking for quality (default: False)
                - search_mode: "semantic", "hybrid", "lexical" (default: "hybrid")
                - content_types: ["text", "image"] - filter by content type
                - return_format: "results", "context", "list" - output format
                - knowledge_id: Specific item ID to retrieve
        
        Examples:
            # Basic search
            search_knowledge(user_id="user1", query="machine learning")
            
            # High-quality search with reranking
            search_knowledge(user_id="user1", query="AI algorithms", 
                           search_options={"top_k": 10, "enable_rerank": True})
            
            # Image-only search
            search_knowledge(user_id="user1", query="red car",
                           search_options={"content_types": ["image"]})
            
            # Get specific item
            search_knowledge(user_id="user1", query="", 
                           search_options={"knowledge_id": "uuid-123"})
        """
        try:
            search_options = search_options or {}
            
            # Extract search parameters
            top_k = search_options.get("top_k", 5)
            enable_rerank = search_options.get("enable_rerank", False)
            search_mode = search_options.get("search_mode", "hybrid")
            content_types = search_options.get("content_types", ["text", "image"])
            return_format = search_options.get("return_format", "results")
            knowledge_id = search_options.get("knowledge_id")
            
            # Handle specific item retrieval
            if knowledge_id:
                result = await digital_tool.analytics_service.get_knowledge_item(user_id, knowledge_id)
                return digital_tool.create_response(
                    "success" if result.get('success') else "error",
                    "search_knowledge", result,
                    result.get('error') if not result.get('success') else None
                )
            
            # Handle content type filtering
            if content_types == ["image"]:
                # Image-only search
                result = await digital_tool.analytics_service.search_images(
                    user_id, query, top_k, enable_rerank, search_mode
                )
            elif content_types == ["text"]:
                # Text-only search  
                result = await digital_tool.analytics_service.search_knowledge(
                    user_id, query, top_k, enable_rerank, search_mode
                )
            else:
                # Mixed search (default)
                result = await digital_tool.analytics_service.search_knowledge(
                    user_id, query, top_k, enable_rerank, search_mode
                )
            
            # Handle return format
            if return_format == "context":
                # Convert to context format
                if result.get('success') and result.get('search_results'):
                    contexts = []
                    for item in result['search_results']:
                        contexts.append({
                            'text': item.get('text', ''),
                            'score': item.get('relevance_score', 0),
                            'metadata': item.get('metadata', {})
                        })
                    result = {
                        'success': True,
                        'query': query,
                        'contexts': contexts,
                        'context_count': len(contexts),
                        'retrieval_method': result.get('search_method', 'hybrid_search')
                    }
            elif return_format == "list":
                # Convert to simple list format
                if result.get('success') and result.get('search_results'):
                    items = []
                    for item in result['search_results']:
                        items.append({
                            'knowledge_id': item.get('knowledge_id'),
                            'text': item.get('text', ''),
                            'metadata': item.get('metadata', {}),
                            'created_at': item.get('created_at', '')
                        })
                    result = {
                        'success': True,
                        'user_id': user_id,
                        'items': items,
                        'total': len(items)
                    }
            
            return digital_tool.create_response(
                "success" if result.get('success') else "error",
                "search_knowledge", 
                {**result, "search_options_used": search_options},
                result.get('error') if not result.get('success') else None
            )
            
        except Exception as e:
            return digital_tool.create_response(
                "error", "search_knowledge", {},
                f"Search failed: {str(e)}"
            )
    
    @mcp.tool()
    async def knowledge_response(
        user_id: str,
        query: str,
        response_options: dict = None
    ) -> str:
        """
        Universal RAG response generation - handles all RAG modes and contexts
        
        This is the unified response generation interface supporting all RAG modes and multimodal context.
        
        Keywords: generate, answer, RAG, response, intelligent, context
        Category: core_knowledge
        
        Args:
            user_id: User identifier for knowledge isolation
            query: User question or query for response generation  
            response_options: Response configuration as dict with options:
                - rag_mode: "simple", "raptor", "self_rag", "crag", "plan_rag", "hm_rag", "graph" (default: "simple")
                - context_limit: Max context items (default: 3)
                - include_images: Include image context (default: True)
                - enable_citations: Include inline citations (default: True)
                - modes: ["simple", "crag"] - for hybrid multi-mode query
                - recommend_mode: Auto-recommend best mode (default: False)
        
        Examples:
            # Basic RAG response
            knowledge_response(user_id="user1", query="What is machine learning?")
            
            # High-quality response with advanced RAG
            knowledge_response(user_id="user1", query="Complex analysis needed", 
                             response_options={"rag_mode": "crag", "context_limit": 5})
            
            # Multimodal response including images
            knowledge_response(user_id="user1", query="What cars do I have photos of?",
                             response_options={"include_images": True, "context_limit": 4})
            
            # Multi-mode comparison
            knowledge_response(user_id="user1", query="Detailed analysis",
                             response_options={"modes": ["simple", "self_rag", "crag"]})
            
            # Auto-recommend best mode
            knowledge_response(user_id="user1", query="Complex reasoning task",
                             response_options={"recommend_mode": True})
        """
        try:
            response_options = response_options or {}
            
            # Extract response parameters
            rag_mode = response_options.get("rag_mode", "simple")
            context_limit = response_options.get("context_limit", 3)
            include_images = response_options.get("include_images", True)
            enable_citations = response_options.get("enable_citations", True)
            modes = response_options.get("modes")
            recommend_mode = response_options.get("recommend_mode", False)
            
            # Handle mode recommendation
            if recommend_mode:
                recommendation = await digital_tool.analytics_service.recommend_mode(query, user_id)
                if recommendation.get('success'):
                    rag_mode = recommendation.get('recommended_mode', 'simple')
                    logger.info(f"Auto-recommended mode: {rag_mode}")
            
            # Handle multi-mode query
            if modes and len(modes) > 1:
                result = await digital_tool.analytics_service.hybrid_query(user_id, query, modes)
                return digital_tool.create_response(
                    "success" if result.get('success') else "error",
                    "knowledge_response", 
                    {**result, "response_type": "hybrid_multi_mode", "response_options_used": response_options},
                    result.get('error') if not result.get('success') else None
                )
            
            # Handle multimodal response
            if include_images:
                result = await digital_tool.analytics_service.generate_image_rag_response(
                    user_id, query, context_limit, include_images, rag_mode
                )
                response_type = "multimodal_rag"
            else:
                # Text-only response
                result = await digital_tool.analytics_service.query_with_mode(
                    user_id, query, rag_mode, context_limit=context_limit
                )
                response_type = "text_rag"
            
            # Ensure citations are enabled if requested
            if result.get('success') and enable_citations:
                if 'result' in result and isinstance(result['result'], dict):
                    result['result']['inline_citations_enabled'] = True
                elif 'inline_citations_enabled' not in result:
                    result['inline_citations_enabled'] = enable_citations
            
            return digital_tool.create_response(
                "success" if result.get('success') else "error",
                "knowledge_response",
                {**result, "response_type": response_type, "rag_mode_used": rag_mode, "response_options_used": response_options},
                result.get('error') if not result.get('success') else None
            )
            
        except Exception as e:
            return digital_tool.create_response(
                "error", "knowledge_response", {},
                f"Response generation failed: {str(e)}"
            )
    
    # Utility function for service status
    @mcp.tool()
    async def get_service_status() -> str:
        """
        Get current status and capabilities of the Digital Analytics Service
        
        Keywords: status, health, capabilities, info
        Category: system_info
        """
        try:
            service = get_digital_analytics_service()
            
            # Get service stats
            status = await service.get_service_stats()
            
            # Get RAG capabilities  
            capabilities = await service.get_rag_capabilities()
            
            combined_status = {
                "service_status": status,
                "rag_capabilities": capabilities.get('capabilities', {}) if capabilities.get('success') else {},
                "simplified_interface": {
                    "core_functions": ["store_knowledge", "search_knowledge", "knowledge_response"],
                    "supported_content_types": ["text", "document", "image"],
                    "supported_rag_modes": ["simple", "raptor", "self_rag", "crag", "plan_rag", "hm_rag", "graph"],
                    "version": "simplified_v1.0"
                }
            }
            
            return json.dumps(combined_status, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    print("✅ Digital Tools registered: 3 core functions + 1 utility")
    print("📍 Core functions: store_knowledge, search_knowledge, knowledge_response")
    print("🔧 Utility: get_service_status")