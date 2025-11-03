#!/usr/bin/env python3
"""
Graph RAG Service - 知识图谱增强RAG实现

基于统一BaseRAGService基类，集成knowledge_service的图功能。
"""

import asyncio
import logging
import time
import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base.base_rag_service import BaseRAGService
from ..base.rag_models import (
    RAGMode,
    RAGConfig,
    RAGResult,
    RAGSource,
    RAGStoreRequest,
    RAGRetrieveRequest,
    RAGGenerateRequest
)

# Qdrant for fallback
try:
    from isa_common.qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None

logger = logging.getLogger(__name__)

class GraphRAGService(BaseRAGService):
    """Graph RAG服务实现 - 知识图谱增强RAG"""

    def __init__(self, config: RAGConfig):
        super().__init__(config)
        self.mode = RAGMode.GRAPH
        self.logger.info("Graph RAG Service initialized")

        # 初始化 Qdrant 作为降级方案
        self.qdrant_client: Optional[QdrantClient] = None
        self.qdrant_collection = os.getenv('QDRANT_COLLECTION', 'user_knowledge')
        self._init_qdrant_fallback()

        # 初始化图相关组件
        self._init_graph_components()

    def _init_qdrant_fallback(self):
        """初始化 Qdrant 作为降级方案"""
        if not QDRANT_AVAILABLE:
            self.logger.warning("Qdrant not available for fallback")
            return

        try:
            host = os.getenv('QDRANT_HOST', 'localhost')
            port = int(os.getenv('QDRANT_PORT', '50062'))

            self.qdrant_client = QdrantClient(host=host, port=port, user_id='graph-rag-fallback')
            self.logger.info(f"✅ Qdrant fallback initialized: {host}:{port}")

            # 确保 collection 存在
            try:
                collection_info = self.qdrant_client.get_collection_info(self.qdrant_collection)
                if not collection_info:
                    vector_dim = int(os.getenv('VECTOR_DIMENSION', '1536'))
                    self.qdrant_client.create_collection(
                        collection_name=self.qdrant_collection,
                        vector_size=vector_dim,
                        distance='Cosine'
                    )
                    self.logger.info(f"✅ Created collection '{self.qdrant_collection}'")
            except Exception as e:
                self.logger.warning(f"Collection check/create warning: {e}")

        except Exception as e:
            self.logger.error(f"Qdrant fallback initialization failed: {e}")
            self.qdrant_client = None
    
    def _init_graph_components(self):
        """初始化图组件"""
        try:
            from .graph_rag.graph_constructor import GraphConstructor
            from .graph_rag.neo4j_client import Neo4jClient
            from .graph_rag.neo4j_store import Neo4jStore
            from .graph_rag.knowledge_retriever import GraphRAGRetriever
            
            # Initialize components with proper dependency chain
            self.neo4j_client = Neo4jClient({})
            self.graph_constructor = GraphConstructor({})
            self.neo4j_store = Neo4jStore(self.neo4j_client)
            self.graph_retriever = GraphRAGRetriever(self.neo4j_client)  # Needs neo4j_client
            
            self.graph_initialized = True
            self.logger.info("✅ Graph components initialized successfully")
            
        except Exception as e:
            self.logger.warning(f"Graph components initialization failed: {e}")
            self.logger.warning(f"Error details: {str(e)}")
            self.graph_initialized = False
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """处理文档 - 构建知识图谱"""
        start_time = time.time()
        
        try:
            if self.graph_initialized:
                # 直接使用迁移过来的图组件进行处理
                try:
                    # 使用正确的方法签名（不带extraction_options）
                    knowledge_graph = await self.graph_constructor.construct_from_text(
                        text=content,
                        source_metadata={
                            'user_id': user_id,
                            'source_file': metadata.get('source', 'text_input') if metadata else 'text_input',
                            **((metadata or {}))
                        }
                    )
                    
                    if knowledge_graph:
                        # 构建Neo4j存储格式
                        graph_data_for_storage = self.graph_constructor.export_for_neo4j_storage(knowledge_graph)
                        
                        # 存储到Neo4j
                        store_result = await self.neo4j_store.store_knowledge_graph(
                            graph_data_for_storage,
                            user_id=user_id
                        )
                        
                        return RAGResult(
                            success=True,
                            content=f"Processed {len(knowledge_graph.nodes)} entities and {len(knowledge_graph.edges)} relationships",
                            sources=[],
                            metadata={
                                'graph_processing_used': True,
                                'entities_count': len(knowledge_graph.nodes),
                                'relationships_count': len(knowledge_graph.edges),
                                'neo4j_stored': store_result.get('success', False)
                            },
                            mode_used=self.mode,
                            processing_time=time.time() - start_time
                        )
                        
                except Exception as graph_error:
                    self.logger.warning(f"Graph processing failed: {graph_error}")
                    # 继续到降级处理
            
            # 降级到传统文档处理 (使用 Qdrant)
            self.logger.warning("Graph processing not available, falling back to Qdrant storage")

            if not self.qdrant_client:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Both graph and Qdrant fallback unavailable'},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error='Storage unavailable'
                )

            # 分块
            chunks = self._chunk_text(content)

            # 生成 embeddings 并存储到 Qdrant
            stored_count = 0
            for i, chunk in enumerate(chunks):
                embedding = await self._generate_embedding(chunk['text'])
                if not embedding:
                    continue

                point = {
                    'id': str(uuid.uuid4()),
                    'vector': embedding,
                    'payload': {
                        'user_id': user_id,
                        'text': chunk['text'],
                        'chunk_index': i,
                        'content_type': 'text',
                        'created_at': datetime.now().isoformat(),
                        **(metadata or {})
                    }
                }

                try:
                    self.qdrant_client.upsert_points(self.qdrant_collection, [point])
                    stored_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to store chunk {i}: {e}")

            return RAGResult(
                success=True,
                content=f"Processed {stored_count}/{len(chunks)} chunks (Qdrant fallback)",
                sources=[],
                metadata={
                    'chunks_processed': stored_count,
                    'total_chunks': len(chunks),
                    'graph_fallback': True,
                    'fallback_method': 'qdrant'
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Graph RAG document processing failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def query(self, 
                   query: str, 
                   user_id: str,
                   context: Optional[str] = None) -> RAGResult:
        """查询处理 - 图RAG检索"""
        start_time = time.time()
        
        try:
            if self.graph_initialized:
                # 直接使用图组件进行查询
                try:
                    # 使用图检索器进行GraphRAG查询
                    retrieval_results = await self.graph_retriever.retrieve(
                        query=query,
                        top_k=self.config.top_k,
                        similarity_threshold=0.7,
                        include_graph_context=True,
                        search_modes=["entities", "documents", "attributes", "relations"]
                    )
                    
                    if retrieval_results:
                        # 将RetrievalResult对象转换为标准sources格式
                        graph_sources = []
                        for result in retrieval_results:
                            source = {
                                'text': result.content,
                                'relevance_score': result.score,
                                'metadata': result.metadata,
                                'source_id': result.source_id
                            }
                            graph_sources.append(source)
                        
                        if graph_sources:
                            citation_context = self._build_context_with_citations(graph_sources)
                            
                            # 生成响应
                            response = await self._generate_response_with_llm(
                                query=query,
                                context=citation_context,
                                additional_context=f"Graph Knowledge Context: Retrieved from knowledge graph. {context}" if context else "Graph Knowledge Context: Retrieved from knowledge graph.",
                                use_citations=True
                            )
                            
                            return RAGResult(
                                success=True,
                                content=response,
                                sources=graph_sources,
                                metadata={
                                    'graph_rag_used': True,
                                    'entities_found': len([r for r in retrieval_results if r.entity_context]),
                                    'relationships_found': sum(len(r.graph_context.get('paths', [])) for r in retrieval_results),
                                    'search_method': 'graph_rag'
                                },
                                mode_used=self.mode,
                                processing_time=time.time() - start_time
                            )
                            
                except Exception as graph_error:
                    self.logger.warning(f"Graph query failed: {graph_error}")
                    # 继续到降级处理
            
            # 降级到 Qdrant 搜索
            self.logger.warning("Graph query not available, falling back to Qdrant search")

            if not self.qdrant_client:
                return RAGResult(
                    success=False,
                    content="Search unavailable",
                    sources=[],
                    metadata={'error': 'Both graph and Qdrant fallback unavailable'},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error='Search unavailable'
                )

            # 生成 query embedding
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                return RAGResult(
                    success=False,
                    content="Failed to generate query embedding",
                    sources=[],
                    metadata={'error': 'Embedding generation failed'},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error='Embedding generation failed'
                )

            # 从 Qdrant 搜索
            try:
                search_results = self.qdrant_client.search_with_filter(
                    collection_name=self.qdrant_collection,
                    vector=query_embedding,
                    filter_conditions={'must': [{'field': 'user_id', 'match': {'keyword': user_id}}]},
                    limit=self.config.top_k
                )
            except Exception as e:
                self.logger.error(f"Qdrant search failed: {e}")
                search_results = []

            if not search_results:
                return RAGResult(
                    success=False,
                    content="No relevant context found",
                    sources=[],
                    metadata={'search_method': 'qdrant_fallback'},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error='No relevant context found'
                )

            # 转换为 RAGSource 对象
            sources = [
                RAGSource(
                    text=result['payload']['text'],
                    score=result['score'],
                    metadata=result['payload']
                )
                for result in search_results
            ]

            # 构建上下文
            use_citations = True  # Default to using citations
            context_text = self._build_context(sources, use_citations=use_citations)

            # 构建 prompt (与 SimpleRAG 一致)
            prompt = f"""You are an AI assistant that provides accurate answers with inline citations. When you reference information from the provided sources, immediately insert the citation number in square brackets after the relevant statement.

SOURCES:
{context_text}

CITATION RULES:
1. When you use information from a source, insert [1], [2], etc. immediately after the statement
2. Place citations naturally within sentences, not at the end of responses
3. Multiple sources can support the same claim: [1][2]
4. Only cite sources that directly support your statements

USER QUESTION: {query}

Please provide a comprehensive answer with proper inline citations."""

            # 生成响应
            response = await self._generate_response(prompt)

            return RAGResult(
                success=True,
                content=response,
                sources=sources,
                metadata={
                    'retrieval_method': 'qdrant_fallback',
                    'context_length': len(context_text),
                    'sources_count': len(sources),
                    'search_method': 'qdrant',
                    'graph_fallback': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Graph RAG query failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取Graph RAG能力"""
        return {
            'name': 'Graph RAG',
            'description': '知识图谱增强RAG',
            'features': [
                '知识图谱构建',
                '实体关系提取',
                '图结构检索',
                'Neo4j存储',
                '语义推理',
                'Inline Citations支持'
            ],
            'best_for': [
                '复杂关系查询',
                '实体关系分析',
                '知识图谱构建',
                '多跳推理',
                '结构化知识'
            ],
            'complexity': 'high',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'supports_graph': True,
            'processing_speed': 'medium',
            'resource_usage': 'high',
            'graph_initialized': self.graph_initialized
        }

    # ==================== New Interface Methods ====================

    async def store(self, request: RAGStoreRequest) -> RAGResult:
        """Store content (unified interface)"""
        return await self.process_document(
            content=request.content if isinstance(request.content, str) else str(request.content),
            user_id=request.user_id,
            metadata=request.metadata
        )

    async def retrieve(self, request: RAGRetrieveRequest) -> RAGResult:
        """Retrieve relevant content (unified interface)"""
        start_time = time.time()

        # Generate query embedding
        query_embedding = await self._generate_embedding(request.query)
        if not query_embedding:
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': 'Failed to generate embedding'},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error='Failed to generate embedding'
            )

        # Try graph retrieval first if available
        if self.graph_initialized:
            try:
                retrieval_results = await self.graph_retriever.retrieve(
                    query=request.query,
                    top_k=request.top_k or self.config.top_k,
                    similarity_threshold=0.7,
                    include_graph_context=True,
                    search_modes=["entities", "documents", "attributes", "relations"]
                )

                if retrieval_results:
                    sources = [{
                        'text': r.content,
                        'relevance_score': r.score,
                        'metadata': r.metadata,
                        'source_id': r.source_id
                    } for r in retrieval_results]

                    return RAGResult(
                        success=True,
                        content="",
                        sources=sources,
                        metadata={'total_results': len(sources), 'retrieval_method': 'graph'},
                        mode_used=self.mode,
                        processing_time=time.time() - start_time
                    )
            except Exception as e:
                self.logger.warning(f"Graph retrieval failed: {e}")

        # Fallback to Qdrant
        if not self.qdrant_client:
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': 'No retrieval backend available'},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error='No retrieval backend available'
            )

        try:
            search_results = self.qdrant_client.search_with_filter(
                collection_name=self.qdrant_collection,
                vector=query_embedding,
                filter_conditions={'must': [{'field': 'user_id', 'match': {'keyword': request.user_id}}]},
                limit=request.top_k or self.config.top_k
            )

            sources = [{
                'text': r['payload']['text'],
                'relevance_score': r['score'],
                'metadata': r['payload'],
                'knowledge_id': r['id']
            } for r in search_results]

            return RAGResult(
                success=True,
                content="",
                sources=sources,
                metadata={'total_results': len(sources), 'retrieval_method': 'qdrant_fallback'},
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
        except Exception as e:
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def generate(self, request: RAGGenerateRequest) -> RAGResult:
        """Generate response from retrieved context (unified interface)"""
        start_time = time.time()

        try:
            # Get sources - either from request or retrieve
            if request.retrieval_sources:
                sources = request.retrieval_sources
            else:
                retrieve_request = RAGRetrieveRequest(
                    query=request.query,
                    user_id=request.user_id
                )
                retrieval = await self.retrieve(retrieve_request)
                if not retrieval.success:
                    return retrieval
                sources = retrieval.sources

            if not sources:
                return RAGResult(
                    success=False,
                    content="No sources available for generation",
                    sources=[],
                    metadata={},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error='No sources available'
                )

            # Convert sources to RAGSource objects
            rag_sources = [
                RAGSource(
                    text=s.get('text', '') if isinstance(s, dict) else str(s),
                    score=s.get('relevance_score', 0.0) if isinstance(s, dict) else 0.0,
                    metadata=s.get('metadata', {}) if isinstance(s, dict) else {}
                )
                for s in sources
            ]

            # Build context
            use_citations = request.options.get('use_citations', True) if request.options else True
            context_text = self._build_context(rag_sources, use_citations=use_citations)

            # Build prompt (same as SimpleRAG for consistency)
            if use_citations:
                prompt = f"""You are an AI assistant that provides accurate answers with inline citations. When you reference information from the provided sources, immediately insert the citation number in square brackets after the relevant statement.

SOURCES:
{context_text}

CITATION RULES:
1. When you use information from a source, insert [1], [2], etc. immediately after the statement
2. Place citations naturally within sentences, not at the end of responses
3. Multiple sources can support the same claim: [1][2]
4. Only cite sources that directly support your statements

USER QUESTION: {request.query}

Please provide a comprehensive answer with proper inline citations."""
            else:
                prompt = f"""Based on the following context, please answer the user's question accurately and comprehensively.

Context:
{context_text}

User Question: {request.query}

Please provide a helpful response based on the context provided."""

            # Generate response
            response = await self._generate_response(prompt)

            return RAGResult(
                success=True,
                content=response,
                sources=sources,
                metadata={'context_length': len(context_text), 'sources_count': len(sources)},
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
        except Exception as e:
            self.logger.error(f"Generate failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error=str(e)
            )
