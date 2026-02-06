#!/usr/bin/env python3
"""
Digital Analytics Tools for MCP Server
MCP tool wrappers around digital analytics microservice HTTP client with SSE progress tracking
Provides RAG-based knowledge management with support for text, PDF, and image content
"""

import json
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from tools.base_tool import BaseTool

from .digital_client import get_digital_client

logger = get_logger(__name__)
tools = BaseTool()


def register_digital_tools(mcp: FastMCP):
    """Register digital analytics tools that call data microservice via HTTP with SSE progress"""

    security_manager = get_security_manager()

    # ========== DIGITAL ANALYTICS STORE TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def digital_store_text(
        user_id: str,
        content: str,
        mode: str = "simple",
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store text content to knowledge base with RAG support

        Stores text content to vector database for later retrieval and RAG operations.
        Supports 7 different RAG modes for various use cases.

        Args:
            user_id: User identifier for organizing content
            content: Text content to store
            mode: RAG mode to use (default "simple")
                Available modes:
                - "simple": Basic vector retrieval (fastest)
                - "crag": Corrective RAG with error correction
                - "self_rag": Self-reflective RAG for complex reasoning
                - "hyde": Hypothetical Document Embeddings for fuzzy queries
                - "raptor": Recursive abstractive processing for long documents
                - "graph_rag": Graph-based knowledge retrieval
                - "rag_fusion": Multi-query fusion for better recall
            collection_name: Collection name for organizing content (optional)
            metadata: Additional metadata as JSON dict (optional)

        Returns:
            JSON string containing:
            - success: Whether storage was successful
            - message: Status message (e.g., "Stored 5 chunks")
            - progress_history: List of progress updates during storage

        Examples:
            # Store simple text
            digital_store_text(
                user_id="alice",
                content="Docker is a containerization platform..."
            )

            # Store with specific mode and collection
            digital_store_text(
                user_id="alice",
                content="Technical documentation about Kubernetes",
                mode="raptor",
                collection_name="tech_docs"
            )

            # Store with metadata
            digital_store_text(
                user_id="alice",
                content="Research findings on AI safety",
                mode="simple",
                collection_name="research",
                metadata={"category": "ai_safety", "date": "2025-01-15"}
            )
        """
        try:
            client = get_digital_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_result = None

            async for message in client.store(
                user_id=user_id,
                content=content,
                content_type="text",
                mode=mode,
                collection_name=collection_name,
                metadata=metadata
            ):
                # Track progress
                if message.get('type') == 'progress':
                    progress_updates.append({
                        'progress': message.get('progress', 0),
                        'message': message.get('message', '')
                    })

                # Capture final result
                if message.get('type') == 'result':
                    final_result = message.get('data', {})

            # Return formatted response with progress history
            return tools.create_response(
                status="success" if final_result and final_result.get('success') else "error",
                action="digital_store_text",
                data={
                    "user_id": user_id,
                    "mode": mode,
                    "collection_name": collection_name,
                    "success": final_result.get('success') if final_result else False,
                    "message": final_result.get('message') if final_result else "No result received",
                    "progress_history": progress_updates
                }
            )

        except Exception as e:
            logger.error(f"Error in digital_store_text: {e}")
            return tools.create_response(
                status="error",
                action="digital_store_text",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def digital_store_pdf(
        user_id: str,
        pdf_url: str,
        mode: str = "simple",
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store PDF document to knowledge base with automatic text extraction

        Downloads and processes PDF documents, extracting text content and storing
        it in the knowledge base for RAG operations.

        Args:
            user_id: User identifier
            pdf_url: URL of the PDF document to store
            mode: RAG mode (default "simple")
                - "raptor": Recommended for long research papers
                - "simple": Fast storage for shorter documents
            collection_name: Collection name (optional, e.g., "research_papers")
            metadata: Additional metadata like title, author, source (optional)

        Returns:
            JSON string containing:
            - success: Whether PDF was processed and stored
            - message: Details about chunks stored
            - progress_history: Progress through download, extraction, and storage

        Examples:
            # Store research paper
            digital_store_pdf(
                user_id="researcher",
                pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
                mode="raptor",
                collection_name="papers",
                metadata={"title": "Attention Is All You Need", "source": "arxiv"}
            )

            # Store documentation
            digital_store_pdf(
                user_id="dev",
                pdf_url="https://example.com/api-docs.pdf",
                collection_name="api_docs"
            )
        """
        try:
            client = get_digital_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_result = None

            async for message in client.store(
                user_id=user_id,
                content=pdf_url,
                content_type="pdf",
                mode=mode,
                collection_name=collection_name,
                metadata=metadata
            ):
                # Track progress
                if message.get('type') == 'progress':
                    progress_updates.append({
                        'progress': message.get('progress', 0),
                        'message': message.get('message', '')
                    })

                # Capture final result
                if message.get('type') == 'result':
                    final_result = message.get('data', {})

            # Return formatted response
            return tools.create_response(
                status="success" if final_result and final_result.get('success') else "error",
                action="digital_store_pdf",
                data={
                    "user_id": user_id,
                    "pdf_url": pdf_url,
                    "mode": mode,
                    "collection_name": collection_name,
                    "success": final_result.get('success') if final_result else False,
                    "message": final_result.get('message') if final_result else "No result received",
                    "progress_history": progress_updates
                }
            )

        except Exception as e:
            logger.error(f"Error in digital_store_pdf: {e}")
            return tools.create_response(
                status="error",
                action="digital_store_pdf",
                data={"user_id": user_id, "pdf_url": pdf_url},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def digital_store_image(
        user_id: str,
        image_url: str,
        mode: str = "simple",
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store image to knowledge base with automatic visual analysis

        Processes image URLs using vision models to extract visual information,
        generating descriptions that are stored for semantic search.

        Args:
            user_id: User identifier
            image_url: URL of the image to store
            mode: RAG mode (default "simple")
            collection_name: Collection name (optional, e.g., "product_images")
            metadata: Additional metadata like category, tags (optional)

        Returns:
            JSON string containing:
            - success: Whether image was processed and stored
            - message: Details about visual analysis
            - progress_history: Progress through download, analysis, and storage

        Examples:
            # Store product image
            digital_store_image(
                user_id="designer",
                image_url="https://example.com/product.jpg",
                collection_name="products",
                metadata={"category": "electronics", "product_id": "12345"}
            )

            # Store visual inspiration
            digital_store_image(
                user_id="artist",
                image_url="https://images.unsplash.com/photo-12345",
                collection_name="inspiration"
            )
        """
        try:
            client = get_digital_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_result = None

            async for message in client.store(
                user_id=user_id,
                content=image_url,
                content_type="image",
                mode=mode,
                collection_name=collection_name,
                metadata=metadata
            ):
                # Track progress
                if message.get('type') == 'progress':
                    progress_updates.append({
                        'progress': message.get('progress', 0),
                        'message': message.get('message', '')
                    })

                # Capture final result
                if message.get('type') == 'result':
                    final_result = message.get('data', {})

            # Return formatted response
            return tools.create_response(
                status="success" if final_result and final_result.get('success') else "error",
                action="digital_store_image",
                data={
                    "user_id": user_id,
                    "image_url": image_url,
                    "mode": mode,
                    "collection_name": collection_name,
                    "success": final_result.get('success') if final_result else False,
                    "message": final_result.get('message') if final_result else "No result received",
                    "progress_history": progress_updates
                }
            )

        except Exception as e:
            logger.error(f"Error in digital_store_image: {e}")
            return tools.create_response(
                status="error",
                action="digital_store_image",
                data={"user_id": user_id, "image_url": image_url},
                error_message=str(e)
            )

    # ========== DIGITAL ANALYTICS SEARCH TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def digital_search(
        user_id: str,
        query: str,
        mode: str = "simple",
        collection_name: Optional[str] = None,
        top_k: int = 5,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Search knowledge base for relevant content

        Performs semantic search across stored content using vector similarity.
        Returns the most relevant chunks with relevance scores.

        Args:
            user_id: User identifier
            query: Search query in natural language
            mode: RAG mode (default "simple")
                - "simple": Fast vector search
                - "rag_fusion": Multi-query fusion for better recall
                - "hyde": Generate hypothetical documents for fuzzy matching
                - "graph_rag": Graph-based traversal for relationships
            collection_name: Specific collection to search (optional)
            top_k: Number of results to return (default 5, max 20)
            options: Mode-specific options as JSON dict (optional)
                Examples:
                - For "rag_fusion": {"num_queries": 3, "fusion_weight": "equal"}
                - For "crag": {"relevance_threshold": 0.7}

        Returns:
            JSON string containing:
            - success: Whether search completed
            - query: The search query
            - sources: List of relevant chunks with text, score, and metadata
            - metadata: Search metadata (e.g., fusion details)

        Examples:
            # Basic search
            digital_search(
                user_id="alice",
                query="What is Docker?",
                collection_name="tech_docs"
            )

            # Fuzzy search with HyDE
            digital_search(
                user_id="alice",
                query="containerization concepts",
                mode="hyde",
                top_k=3
            )

            # Multi-query fusion for comprehensive results
            digital_search(
                user_id="alice",
                query="Kubernetes architecture",
                mode="rag_fusion",
                options={"num_queries": 5}
            )
        """
        try:
            client = get_digital_client()

            result = await client.search(
                user_id=user_id,
                query=query,
                mode=mode,
                collection_name=collection_name,
                top_k=top_k,
                options=options
            )

            # Return formatted response
            return tools.create_response(
                status="success" if result.get('success') else "error",
                action="digital_search",
                data={
                    "user_id": user_id,
                    "query": query,
                    "mode": mode,
                    "collection_name": collection_name,
                    "sources": result.get('sources', []),
                    "metadata": result.get('metadata', {}),
                    "num_results": len(result.get('sources', []))
                }
            )

        except Exception as e:
            logger.error(f"Error in digital_search: {e}")
            return tools.create_response(
                status="error",
                action="digital_search",
                data={"user_id": user_id, "query": query},
                error_message=str(e)
            )

    # ========== DIGITAL ANALYTICS RESPONSE TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def digital_response(
        user_id: str,
        query: str,
        mode: str = "simple",
        collection_name: Optional[str] = None,
        top_k: int = 5,
        use_citations: bool = True
    ) -> str:
        """Generate AI response based on knowledge base content

        Performs RAG (Retrieval-Augmented Generation) to answer queries using
        stored knowledge. Retrieves relevant context and generates natural
        language responses.

        Args:
            user_id: User identifier
            query: Question or request in natural language
            mode: RAG mode (default "simple")
                - "simple": Basic RAG (fastest)
                - "crag": Corrective RAG with accuracy checks
                - "self_rag": Self-reflective for complex reasoning
                - "raptor": Best for questions about long documents
            collection_name: Specific collection to use (optional)
            top_k: Number of context chunks to use (default 5)
            use_citations: Include source citations in response (default True)

        Returns:
            JSON string containing:
            - success: Whether generation completed
            - query: The original query
            - response: Generated natural language answer
            - context_used: Number of chunks used for context
            - citations: Source citations if requested
            - progress_history: Progress through retrieval and generation

        Examples:
            # Basic question answering
            digital_response(
                user_id="alice",
                query="What are the benefits of Docker?",
                collection_name="tech_docs"
            )

            # Complex reasoning with self-reflection
            digital_response(
                user_id="alice",
                query="Compare Docker and Kubernetes for microservices",
                mode="self_rag",
                top_k=8
            )

            # Long document understanding
            digital_response(
                user_id="researcher",
                query="Summarize the transformer architecture",
                mode="raptor",
                collection_name="papers",
                use_citations=True
            )
        """
        try:
            client = get_digital_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_result = None

            options = {"use_citations": use_citations}

            async for message in client.generate_response(
                user_id=user_id,
                query=query,
                mode=mode,
                collection_name=collection_name,
                top_k=top_k,
                options=options
            ):
                # Track progress
                if message.get('type') == 'progress':
                    progress_updates.append({
                        'progress': message.get('progress', 0),
                        'message': message.get('message', '')
                    })

                # Capture final result
                if message.get('type') == 'result':
                    final_result = message.get('data', {})

            # Return formatted response
            return tools.create_response(
                status="success" if final_result and final_result.get('success') else "error",
                action="digital_response",
                data={
                    "user_id": user_id,
                    "query": query,
                    "mode": mode,
                    "response": final_result.get('response') if final_result else None,
                    "context_used": final_result.get('context_used', 0) if final_result else 0,
                    "citations": final_result.get('citations', []) if final_result else [],
                    "progress_history": progress_updates
                }
            )

        except Exception as e:
            logger.error(f"Error in digital_response: {e}")
            return tools.create_response(
                status="error",
                action="digital_response",
                data={"user_id": user_id, "query": query},
                error_message=str(e)
            )

    # ========== UTILITY TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def digital_service_health_check() -> str:
        """Check digital analytics service health status

        Verifies that the digital analytics service is running and accessible.
        Useful for debugging and monitoring service availability.

        Returns:
            JSON string containing:
            - status: Service status ("healthy" or error message)
            - service_url: URL of the service being used
            - response_time: Time taken to respond (ms)

        Example:
            digital_service_health_check()
        """
        try:
            client = get_digital_client()

            import time
            start_time = time.time()
            health = await client.health_check()
            response_time = (time.time() - start_time) * 1000

            return tools.create_response(
                status="success",
                action="digital_service_health_check",
                data={
                    "status": "healthy",
                    "service_url": client.service_url or "not discovered yet",
                    "response_time_ms": round(response_time, 2),
                    "health_data": health
                }
            )

        except Exception as e:
            logger.error(f"Error checking digital service health: {e}")
            return tools.create_response(
                status="error",
                action="digital_service_health_check",
                data={},
                error_message=str(e)
            )
