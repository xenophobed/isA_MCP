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
import traceback
from typing import Dict, List, Any, Optional, Union
from mcp.server.fastmcp import FastMCP, Context
from tools.base_tool import BaseTool
from tools.services.data_analytics_service.services.digital_service import (
    get_digital_analytics_service,
    DigitalAnalyticsService
)
from tools.services.data_analytics_service.services.digital_service.base.rag_models import (
    RAGStoreRequest, RAGRetrieveRequest, RAGGenerateRequest
)
from tools.services.data_analytics_service.tools.context import DigitalAssetProgressReporter
from core.logging import get_logger

logger = get_logger(__name__)

class DigitalTool(BaseTool):
    """Simplified digital analytics tool with 3 core functions + universal progress tracking"""

    def __init__(self):
        super().__init__()
        self.analytics_service = get_digital_analytics_service()
        self.progress_reporter = DigitalAssetProgressReporter(self)

def register_digital_tools(mcp: FastMCP):
    """Register simplified 3-function digital tools"""
    digital_tool = DigitalTool()
    
    @mcp.tool()
    async def store_knowledge(
        user_id: str,
        content: str,
        content_type: str = "text",
        metadata: dict = None,
        options: dict = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Universal knowledge storage - handles text, documents, and images
        
        This is the unified storage interface for all content types in the knowledge base.
        
        Keywords: store, save, add, knowledge, document, image, text
        Category: core_knowledge
        
        Args:
            user_id: User identifier for knowledge isolation
            content: Content to store (text/document content, file path for image/pdf)
            content_type: Type of content - "text", "document", "image", "pdf"
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

            # Store PDF with multimodal processing
            store_knowledge(user_id="user1", content="/path/to/document.pdf", content_type="pdf",
                          options={"enable_vlm_analysis": True, "enable_minio_upload": True, "max_pages": 14})
        """
        try:
            metadata = metadata or {}
            options = options or {}

            # Log start
            await digital_tool.log_info(ctx, f"Starting {content_type} storage for user {user_id}")

            # Route to appropriate storage method based on content_type
            if content_type == "text":
                # Simple 4-stage progress for text
                await digital_tool.progress_reporter.report_stage(ctx, "processing", "text")
                await digital_tool.progress_reporter.report_stage(ctx, "extraction", "text")
                await digital_tool.progress_reporter.report_stage(ctx, "embedding", "text")

                # Use RAG Factory for text storage (aligned with architecture)
                from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

                rag_mode = options.get('rag_mode', 'simple')  # Default to simple for text
                rag_service = get_rag_service(mode=rag_mode, config=options)

                # Create RAGStoreRequest using new Pydantic model
                store_request = RAGStoreRequest(
                    content=content,
                    user_id=user_id,
                    content_type="text",
                    metadata=metadata
                )

                await digital_tool.log_info(ctx, f"[TRACE] About to call {type(rag_service).__name__}.store()")
                await digital_tool.log_info(ctx, f"[TRACE] Request: user={user_id}, content_len={len(content)}")

                rag_result = await rag_service.store(store_request)

                await digital_tool.log_info(ctx, f"[TRACE] RAG store() returned: success={rag_result.success}")
                await digital_tool.log_info(ctx, f"[TRACE] RAG result content: {rag_result.content}")

                result = {
                    'success': rag_result.success,
                    'error': rag_result.error if not rag_result.success else None
                }

                await digital_tool.progress_reporter.report_stage(ctx, "storing", "text")

            elif content_type == "document":
                # 4-stage progress for document chunking
                await digital_tool.progress_reporter.report_stage(ctx, "processing", "document")
                await digital_tool.progress_reporter.report_stage(ctx, "extraction", "document")
                await digital_tool.progress_reporter.report_stage(ctx, "embedding", "document")

                # Use RAG Factory for document storage (aligned with architecture)
                from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

                rag_mode = options.get('rag_mode', 'simple')
                rag_service = get_rag_service(mode=rag_mode, config=options)

                # Create RAGStoreRequest using new Pydantic model
                store_request = RAGStoreRequest(
                    content=content,
                    user_id=user_id,
                    content_type="document",
                    metadata=metadata
                )
                rag_result = await rag_service.store(store_request)

                result = {
                    'success': rag_result.success,
                    'error': rag_result.error if not rag_result.success else None
                }

                await digital_tool.progress_reporter.report_stage(ctx, "storing", "document")

            elif content_type == "image":
                # 4-stage progress for image with VLM
                await digital_tool.progress_reporter.report_stage(ctx, "processing", "image")
                await digital_tool.progress_reporter.report_stage(ctx, "extraction", "image", "VLM analysis")
                await digital_tool.progress_reporter.report_stage(ctx, "embedding", "image")

                # Use RAG Factory for image storage (aligned with architecture)
                from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

                rag_mode = options.get('rag_mode', 'simple')
                rag_service = get_rag_service(mode=rag_mode, config=options)

                # Create RAGStoreRequest using new Pydantic model
                store_request = RAGStoreRequest(
                    content=content,
                    user_id=user_id,
                    content_type="image",
                    metadata=metadata
                )
                rag_result = await rag_service.store(store_request)

                result = {
                    'success': rag_result.success,
                    'error': rag_result.error if not rag_result.success else None
                }

                await digital_tool.progress_reporter.report_stage(ctx, "storing", "image")

            elif content_type == "pdf":
                # Detailed 4-stage progress for PDF multimodal processing
                # Stage 1: Processing - Extract PDF pages
                await digital_tool.progress_reporter.report_stage(ctx, "processing", "pdf", "extracting pages")

                # Use RAG Factory to get service (defaults to custom for PDF)
                from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

                # Extract RAG config from options
                rag_mode = options.get('rag_mode', 'simple')  # Default to simple
                rag_config = {
                    'enable_vlm_analysis': options.get('enable_vlm_analysis', True),
                    'enable_minio_upload': options.get('enable_minio_upload', True),
                    'max_pages': options.get('max_pages'),
                    'max_concurrent_pages': options.get('max_concurrent_pages', 2),
                    'chunking_strategy': options.get('chunking_strategy', 'page'),
                    'chunk_size': options.get('chunk_size', 800),
                    'chunk_overlap': options.get('chunk_overlap', 100),
                    'top_k_results': options.get('top_k_results', 5)
                }

                rag_service = get_rag_service(mode=rag_mode, config=rag_config)

                # Stage 2: AI Extraction - VLM analysis of pages
                await digital_tool.progress_reporter.report_stage(ctx, "extraction", "pdf", "VLM page analysis")

                # Create RAGStoreRequest using new Pydantic model
                store_request = RAGStoreRequest(
                    content=content,  # content is the PDF file path
                    user_id=user_id,
                    content_type="pdf",
                    metadata=metadata
                )
                rag_result = await rag_service.store(store_request)

                # Convert RAGResult to dict format for progress tracking
                result = {
                    'success': rag_result.success,
                    'pages_processed': len(rag_result.sources) if rag_result.sources else 0,
                    'total_photos': rag_result.metadata.get('images_stored', 0) if rag_result.metadata else 0,
                    'error': rag_result.error if not rag_result.success else None
                }

                # Stage 3: Embedding
                if rag_result.success:
                    total_pages = result['pages_processed']
                    await digital_tool.progress_reporter.report_stage(
                        ctx, "embedding", "pdf",
                        details={"pages": total_pages}
                    )

                    # Stage 4: Storing - MinIO + Vector DB
                    await digital_tool.progress_reporter.report_storage_progress(
                        ctx, "pdf", "minio", "uploading"
                    )
                    await digital_tool.progress_reporter.report_storage_progress(
                        ctx, "pdf", "vector_db", "indexing"
                    )

                    # Add ingestion method to result
                    result['ingestion_method'] = f'{rag_mode}_rag_multimodal'

                    # Report completion
                    await digital_tool.progress_reporter.report_complete(ctx, "pdf", {
                        "pages": total_pages,
                        "photos": result['total_photos']
                    })

            else:
                return digital_tool.create_response(
                    "error", "store_knowledge", {},
                    f"Unsupported content_type: {content_type}. Use 'text', 'document', 'image', or 'pdf'"
                )
            
            # Add context info and completion log
            if result.get('success'):
                await digital_tool.log_info(ctx, f"{content_type} storage completed successfully")

            return digital_tool.create_response(
                "success" if result.get('success') else "error",
                "store_knowledge",
                {
                    **result,
                    "content_type": content_type,
                    "context": digital_tool.extract_context_info(ctx, user_id)
                },
                result.get('error') if not result.get('success') else None
            )

        except Exception as e:
            # Log full traceback to identify exact error location
            full_traceback = traceback.format_exc()
            await digital_tool.log_error(ctx, f"Storage failed: {str(e)}\n\nFull traceback:\n{full_traceback}")
            logger.error(f"Storage failed with full traceback:\n{full_traceback}")
            return digital_tool.create_response(
                "error", "store_knowledge",
                {"context": digital_tool.extract_context_info(ctx, user_id)},
                f"Storage failed: {str(e)}"
            )
    
    @mcp.tool()
    async def search_knowledge(
        user_id: str,
        query: str,
        search_options: dict = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
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
                - content_types: ["text", "image", "pdf"] - filter by content type
                - content_type: "text", "image", "pdf" - filter for specific type
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

            # PDF-only search with multimodal results
            search_knowledge(user_id="user1", query="how to create customer",
                           search_options={"content_type": "pdf", "top_k": 5})

            # Get specific item
            search_knowledge(user_id="user1", query="",
                           search_options={"knowledge_id": "uuid-123"})
        """
        try:
            search_options = search_options or {}

            # Log search start
            await digital_tool.log_info(ctx, f"Starting search for query: '{query}' (user: {user_id})")

            # Extract search parameters
            top_k = search_options.get("top_k", 5)
            enable_rerank = search_options.get("enable_rerank", False)
            search_mode = search_options.get("search_mode", "hybrid")
            content_types = search_options.get("content_types", ["text", "image"])
            content_type = search_options.get("content_type")  # Single content type filter
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

            # Handle PDF-specific search
            if content_type == "pdf" or content_types == ["pdf"]:
                # Use RAG Factory for PDF search
                from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

                logger.info(f"🔍 PDF search: user_id={user_id}, query={query}, top_k={top_k}")
                rag_mode = search_options.get('rag_mode', 'simple')
                rag_service = get_rag_service(mode=rag_mode, config=search_options)

                # Create RAGRetrieveRequest using new Pydantic model
                retrieve_request = RAGRetrieveRequest(
                    query=query,
                    user_id=user_id,
                    top_k=top_k,
                    filters={"content_type": "pdf"}
                )
                rag_result = await rag_service.retrieve(retrieve_request)
                logger.info(f"📊 RAG result: success={rag_result.success}, pages={len(rag_result.sources) if rag_result.sources else 0}")

                # Format response to match standard search format
                if rag_result.success:
                    search_results = []
                    for page in rag_result.sources:
                        # Convert RAGSource Pydantic model to dict
                        page_dict = page.dict() if hasattr(page, 'dict') else page
                        search_results.append({
                            'text': page_dict.get('text'),
                            'page_number': page_dict.get('page_number'),
                            'page_summary': page_dict.get('page_summary'),
                            'photo_urls': page_dict.get('photo_urls', []),
                            'num_photos': len(page_dict.get('photo_urls', [])),
                            'relevance_score': page_dict.get('similarity_score', page_dict.get('score', 0.0)),
                            'metadata': page_dict.get('metadata', {}),
                            'content_type': 'pdf',
                            'is_pdf_content': True
                        })

                    result = {
                        'success': True,
                        'search_results': search_results,
                        'total_results': len(search_results),
                        'total_photos': rag_result.metadata.get('total_photos', 0) if rag_result.metadata else 0,
                        'search_method': f'{rag_mode}_rag_multimodal',
                        'query': query
                    }

            # Handle content type filtering
            elif content_types == ["image"]:
                # Image-only search
                result = await digital_tool.analytics_service.search_images(
                    user_id, query, top_k, enable_rerank, search_mode
                )
            elif content_types == ["text"]:
                # Text-only search - Use RAG Factory
                from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

                logger.info(f"🔍 Text search using RAG service: user_id={user_id}, query={query}")
                rag_mode = search_options.get('rag_mode', 'simple')
                rag_service = get_rag_service(mode=rag_mode, config=search_options)

                # Create RAGRetrieveRequest using new Pydantic model
                retrieve_request = RAGRetrieveRequest(
                    query=query,
                    user_id=user_id,
                    top_k=top_k
                )
                rag_result = await rag_service.retrieve(retrieve_request)

                # Convert RAGResult format to standard search format
                if rag_result.success:
                    search_results = []
                    for page in rag_result.sources:
                        # Convert RAGSource Pydantic model to dict
                        page_dict = page.dict() if hasattr(page, 'dict') else page
                        search_results.append({
                            'text': page_dict.get('text'),
                            'relevance_score': page_dict.get('similarity_score', page_dict.get('score', 0.0)),
                            'metadata': page_dict.get('metadata', {}),
                            'content_type': 'text'
                        })
                    result = {
                        'success': True,
                        'search_results': search_results,
                        'total_results': len(search_results),
                        'search_method': f'{rag_mode}_rag_unified',
                        'query': query
                    }
                else:
                    result = {'success': False, 'error': rag_result.error}
            else:
                # Mixed search (default) - Use RAG Factory for all content
                from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

                logger.info(f"🔍 Mixed search using RAG service: user_id={user_id}, query={query}")
                rag_mode = search_options.get('rag_mode', 'simple')
                rag_service = get_rag_service(mode=rag_mode, config=search_options)

                # Create RAGRetrieveRequest using new Pydantic model
                retrieve_request = RAGRetrieveRequest(
                    query=query,
                    user_id=user_id,
                    top_k=top_k
                )
                rag_result = await rag_service.retrieve(retrieve_request)

                # Convert RAGResult format to standard search format
                if rag_result.success:
                    search_results = []
                    for page in rag_result.sources:
                        # Convert RAGSource Pydantic model to dict
                        page_dict = page.dict() if hasattr(page, 'dict') else page
                        search_results.append({
                            'text': page_dict.get('text'),
                            'page_number': page_dict.get('page_number'),
                            'page_summary': page_dict.get('page_summary'),
                            'photo_urls': page_dict.get('photo_urls') or [],
                            'num_photos': len(page_dict.get('photo_urls') or []),
                            'relevance_score': page_dict.get('similarity_score', page_dict.get('score', 0.0)),
                            'metadata': page_dict.get('metadata') or {},
                            'content_type': (page_dict.get('metadata') or {}).get('content_type', 'mixed'),
                            'is_pdf_content': page_dict.get('page_number') is not None
                        })
                    result = {
                        'success': True,
                        'search_results': search_results,
                        'total_results': len(search_results),
                        'total_photos': rag_result.metadata.get('total_photos', 0) if rag_result.metadata else 0,
                        'search_method': f'{rag_mode}_rag_unified',
                        'query': query
                    }
                else:
                    result = {'success': False, 'error': rag_result.error}
            
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
            
            # Log completion
            if result.get('success'):
                total_results = result.get('total_results', result.get('total', 0))
                await digital_tool.log_info(ctx, f"Search completed: {total_results} results found")

            return digital_tool.create_response(
                "success" if result.get('success') else "error",
                "search_knowledge",
                {
                    **result,
                    "search_options_used": search_options,
                    "context": digital_tool.extract_context_info(ctx, user_id)
                },
                result.get('error') if not result.get('success') else None
            )

        except Exception as e:
            # Log full traceback to identify exact error location
            full_traceback = traceback.format_exc()
            await digital_tool.log_error(ctx, f"Search failed: {str(e)}\n\nFull traceback:\n{full_traceback}")
            logger.error(f"Search failed with full traceback:\n{full_traceback}")
            return digital_tool.create_response(
                "error", "search_knowledge",
                {"context": digital_tool.extract_context_info(ctx, user_id)},
                f"Search failed: {str(e)}"
            )
    
    @mcp.tool()
    async def knowledge_response(
        user_id: str,
        query: str,
        response_options: dict = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
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
                - use_pdf_context: Use PDF-aware RAG pipeline (default: False)
                - auto_detect_pdf: Auto-detect PDF content and route to CustomRAG (default: True)
        
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

            # PDF-aware RAG with image references
            knowledge_response(user_id="user1", query="How to create new customer in CRM?",
                             response_options={"use_pdf_context": True, "context_limit": 5})
        """
        try:
            response_options = response_options or {}

            # Stage 1/4 (25%): Query Analysis
            await digital_tool.progress_reporter.report_stage(
                ctx, "processing", "query", "Analyzing query",
                pipeline_type="generation"
            )
            await digital_tool.log_info(ctx, f"Starting RAG response for query: '{query}' (user: {user_id})")

            # Extract response parameters
            rag_mode = response_options.get("rag_mode", "simple")
            context_limit = response_options.get("context_limit", 3)
            include_images = response_options.get("include_images", True)
            enable_citations = response_options.get("enable_citations", True)
            modes = response_options.get("modes")
            recommend_mode = response_options.get("recommend_mode", False)
            use_pdf_context = response_options.get("use_pdf_context", False)
            auto_detect_pdf = response_options.get("auto_detect_pdf", True)

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

            # Auto-detect PDF content if enabled
            if not use_pdf_context and auto_detect_pdf:
                # Quick search to check if results contain PDF content
                search_result = await digital_tool.analytics_service.search_knowledge(
                    user_id=user_id,
                    query=query,
                    top_k=1
                )

                if search_result.get('success') and search_result.get('search_results'):
                    first_result = search_result['search_results'][0]
                    metadata = first_result.get('metadata', {})
                    record_type = metadata.get('record_type', metadata.get('content_type'))

                    # Auto-enable PDF RAG if content is from PDF
                    if record_type in ['page', 'text_chunk']:
                        use_pdf_context = True
                        logger.info(f"Auto-detected PDF content, using CustomRAG pipeline")

            # Handle PDF-aware RAG
            if use_pdf_context:
                from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

                # Get RAG service (default to custom for PDF)
                selected_rag_mode = options.get('rag_mode', 'simple')
                rag_service = get_rag_service(mode=selected_rag_mode, config=response_options)

                # Stage 2/4 (50%): Context Retrieval - Search knowledge base
                await digital_tool.progress_reporter.report_stage(
                    ctx, "retrieval", "query", f"Searching knowledge base (top {context_limit})",
                    pipeline_type="generation"
                )

                # 1. Retrieve with RAG service (preserves photo_urls)
                rag_retrieval = await rag_service.retrieve(
                    query=query,
                    user_id=user_id,
                    top_k=context_limit * 2,  # Get more for better coverage
                    options=response_options
                )

                if not rag_retrieval.success:
                    return digital_tool.create_response(
                        "error",
                        "knowledge_response",
                        {'success': False, 'error': rag_retrieval.error},
                        rag_retrieval.error
                    )

                # Stage 3/4 (75%): Context Preparation - Prepare and rank context
                pages_found = len(rag_retrieval.sources) if rag_retrieval.sources else 0
                await digital_tool.progress_reporter.report_stage(
                    ctx, "preparation", "query", f"Preparing {pages_found} context items",
                    pipeline_type="generation"
                )

                # 2. Generate with RAG service (includes image references)
                # Stage 4/4 (100%): AI Generation - Generate response
                await digital_tool.progress_reporter.report_stage(
                    ctx, "generation", "query", f"Generating response (mode: {selected_rag_mode})",
                    pipeline_type="generation"
                )

                # Create RAGGenerateRequest using new Pydantic model
                # Convert RAGResult sources to dict format for generate request
                retrieval_sources = [s.dict() if hasattr(s, 'dict') else s for s in (rag_retrieval.sources or [])]

                generate_request = RAGGenerateRequest(
                    query=query,
                    user_id=user_id,
                    retrieval_sources=retrieval_sources,
                    options={
                        'model': response_options.get('model', 'gpt-4o-mini'),
                        'temperature': response_options.get('temperature', 0.3),
                        'provider': response_options.get('provider', 'yyds')
                    }
                )
                rag_generation = await rag_service.generate(generate_request)

                # Format response
                if rag_generation.success:
                    # Extract sources metadata from RAGResult
                    sources_metadata = rag_generation.metadata.get('sources', {}) if rag_generation.metadata else {}
                    result = {
                        'success': True,
                        'response': rag_generation.content,
                        'answer': rag_generation.content,  # Alias for compatibility
                        'sources': sources_metadata,
                        'page_count': sources_metadata.get('page_count', pages_found),
                        'photo_count': sources_metadata.get('photo_count', 0),
                        'page_sources': rag_generation.sources or [],
                        'context_used': rag_generation.metadata.get('context_used') if rag_generation.metadata else None,
                        'response_type': 'pdf_multimodal_rag',
                        'rag_mode_used': selected_rag_mode,
                        'inline_citations_enabled': True,  # Images are cited in answer
                        'response_options_used': response_options
                    }

                    return digital_tool.create_response(
                        "success",
                        "knowledge_response",
                        result
                    )
                else:
                    return digital_tool.create_response(
                        "error",
                        "knowledge_response",
                        generation_result,
                        generation_result.get('error')
                    )

            # Handle standard text/multimodal response using RAG factory
            from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

            # Get RAG service based on selected mode
            rag_service = get_rag_service(mode=rag_mode, config=response_options)

            # Stage 2/4 (50%): Context Retrieval
            await digital_tool.progress_reporter.report_stage(
                ctx, "retrieval", "query", f"Retrieving context (limit: {context_limit})",
                pipeline_type="generation"
            )

            # 1. Retrieve with RAG service
            retrieve_request = RAGRetrieveRequest(
                query=query,
                user_id=user_id,
                top_k=context_limit,
                options=response_options
            )
            rag_retrieval = await rag_service.retrieve(retrieve_request)

            if not rag_retrieval.success:
                return digital_tool.create_response(
                    "error",
                    "knowledge_response",
                    {'success': False, 'error': rag_retrieval.error},
                    rag_retrieval.error
                )

            # Stage 3/4 (75%): Context Preparation
            sources_found = len(rag_retrieval.sources) if rag_retrieval.sources else 0
            await digital_tool.progress_reporter.report_stage(
                ctx, "preparation", "query", f"Preparing {sources_found} context items",
                pipeline_type="generation"
            )

            # Stage 4/4 (100%): AI Generation
            await digital_tool.progress_reporter.report_stage(
                ctx, "generation", "query", f"Generating with {rag_mode} mode",
                pipeline_type="generation"
            )

            # 2. Generate with RAG service
            # Convert RAGResult sources to dict format for generate request
            retrieval_sources = [s.dict() if hasattr(s, 'dict') else s for s in (rag_retrieval.sources or [])]

            generate_request = RAGGenerateRequest(
                query=query,
                user_id=user_id,
                retrieval_sources=retrieval_sources,
                options={
                    'model': response_options.get('model', 'gpt-4o-mini'),
                    'temperature': response_options.get('temperature', 0.3),
                    'provider': response_options.get('provider', 'yyds'),
                    'use_citations': enable_citations
                }
            )
            rag_generation = await rag_service.generate(generate_request)

            # Format response
            if rag_generation.success:
                # Build sources list for response
                text_sources = []
                for source in (rag_generation.sources or []):
                    source_dict = source.dict() if hasattr(source, 'dict') else source
                    text_sources.append({
                        'text': source_dict.get('text', ''),
                        'score': source_dict.get('score', 0.0),
                        'metadata': source_dict.get('metadata', {})
                    })

                result = {
                    'success': True,
                    'response': rag_generation.content,
                    'answer': rag_generation.content,  # Alias for compatibility
                    'context_items': len(text_sources),
                    'text_sources': text_sources,
                    'image_sources': [],  # No images in text-only mode
                    'metadata': rag_generation.metadata or {},
                    'inline_citations_enabled': enable_citations,
                }
                response_type = "text_rag"
            else:
                return digital_tool.create_response(
                    "error",
                    "knowledge_response",
                    {'success': False, 'error': rag_generation.error},
                    rag_generation.error
                )

            # Ensure citations are enabled if requested
            if result.get('success') and enable_citations:
                if 'result' in result and isinstance(result['result'], dict):
                    result['result']['inline_citations_enabled'] = True
                elif 'inline_citations_enabled' not in result:
                    result['inline_citations_enabled'] = enable_citations

            # Log completion
            if result.get('success'):
                response_len = len(result.get('response', result.get('answer', '')))
                await digital_tool.log_info(ctx, f"RAG response generated ({response_len} chars, mode: {rag_mode})")

                # Report completion with summary
                await digital_tool.progress_reporter.report_complete(
                    ctx,
                    "query",
                    {"response_length": response_len, "rag_mode": rag_mode, "context_limit": context_limit}
                )

            return digital_tool.create_response(
                "success" if result.get('success') else "error",
                "knowledge_response",
                {
                    **result,
                    "response_type": response_type,
                    "rag_mode_used": rag_mode,
                    "response_options_used": response_options,
                    "context": digital_tool.extract_context_info(ctx, user_id)
                },
                result.get('error') if not result.get('success') else None
            )

        except Exception as e:
            # Log full traceback to identify exact error location
            full_traceback = traceback.format_exc()
            await digital_tool.log_error(ctx, f"Response generation failed: {str(e)}\n\nFull traceback:\n{full_traceback}")
            logger.error(f"Response generation failed with full traceback:\n{full_traceback}")
            return digital_tool.create_response(
                "error", "knowledge_response",
                {"context": digital_tool.extract_context_info(ctx, user_id)},
                f"Response generation failed: {str(e)}"
            )
    
    # Utility function for service status
    @mcp.tool()
    async def get_service_status() -> Dict[str, Any]:
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
                    "supported_content_types": ["text", "document", "image", "pdf"],
                    "supported_rag_modes": ["simple", "raptor", "self_rag", "crag", "plan_rag", "hm_rag", "graph", "custom_rag"],
                    "pdf_multimodal_features": {
                        "vlm_analysis": True,
                        "minio_storage": True,
                        "page_level_processing": True,
                        "hybrid_chunking": True,
                        "image_url_preservation": True
                    },
                    "version": "simplified_v1.1_pdf"
                }
            }

            return combined_status

        except Exception as e:
            return {"error": str(e)}

    print("✅ Digital Tools registered: 3 core functions + 1 utility")
    print("📍 Core functions: store_knowledge, search_knowledge, knowledge_response")
    print("📄 Content types: text, document, image, pdf (with multimodal support)")
    print("🔧 Utility: get_service_status")