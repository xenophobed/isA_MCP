#!/usr/bin/env python3
"""
Graph RAG Service - 知识图谱增强RAG实现

基于统一BaseRAGService基类，集成knowledge_service的图功能。
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base.base_rag_service import BaseRAGService, RAGResult, RAGMode, RAGConfig

logger = logging.getLogger(__name__)

class GraphRAGService(BaseRAGService):
    """Graph RAG服务实现 - 知识图谱增强RAG"""
    
    def __init__(self, config: RAGConfig):
        super().__init__(config)
        self.mode = RAGMode.GRAPH
        self.logger.info("Graph RAG Service initialized")
        
        # 初始化图相关组件
        self._init_graph_components()
    
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
            
            # 降级到传统文档处理
            self.logger.warning("Graph processing not available, falling back to traditional")
            document_result = await self.add_document(
                user_id=user_id,
                document=content,
                chunk_size=self.config.chunk_size,
                overlap=self.config.overlap,
                metadata=metadata
            )
            
            if not document_result['success']:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': document_result.get('error')},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error=document_result.get('error')
                )
            
            return RAGResult(
                success=True,
                content=f"Processed {document_result['stored_chunks']} chunks (fallback mode)",
                sources=document_result.get('chunks', []),
                metadata={
                    'chunks_processed': document_result['stored_chunks'],
                    'total_chunks': document_result['total_chunks'],
                    'document_length': document_result['document_length'],
                    'graph_fallback': True
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
            
            # 降级到传统搜索 + citation
            self.logger.warning("Graph query not available, falling back to traditional search")
            search_result = await self.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=self.config.top_k,
                enable_rerank=self.config.enable_rerank,
                search_mode="hybrid",
                use_enhanced_search=True
            )
            
            if not search_result['success'] or not search_result['search_results']:
                return RAGResult(
                    success=False,
                    content="No relevant context found",
                    sources=[],
                    metadata={'search_method': search_result.get('search_method', 'unknown')},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error=search_result.get('error', 'No relevant context found')
                )
            
            # 构建上下文（默认启用citation格式）
            context_text = self._build_context_with_citations(search_result['search_results'])
            
            # 生成响应（使用真正的LLM）
            response = await self._generate_response_with_llm(
                query=query, 
                context=context_text, 
                additional_context=f"Graph RAG Fallback: Using traditional search due to graph unavailability. {context}" if context else "Graph RAG Fallback: Using traditional search due to graph unavailability.",
                use_citations=True
            )
            
            return RAGResult(
                success=True,
                content=response,
                sources=search_result['search_results'],
                metadata={
                    'retrieval_method': 'graph_rag_fallback',
                    'context_length': len(context_text),
                    'sources_count': len(search_result['search_results']),
                    'search_method': search_result.get('search_method', 'unknown'),
                    'reranking_used': search_result.get('reranking_used', False),
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

    async def store(self,
                   content: str,
                   user_id: str,
                   content_type: str = "text",
                   metadata: Optional[Dict[str, Any]] = None,
                   options: Optional[Dict[str, Any]] = None) -> RAGResult:
        """Store content"""
        return await self.process_document(content, user_id, metadata)

    async def retrieve(self,
                      query: str,
                      user_id: str,
                      top_k: int = 5,
                      filters: Optional[Dict[str, Any]] = None,
                      options: Optional[Dict[str, Any]] = None) -> RAGResult:
        """Retrieve relevant content"""
        start_time = time.time()
        try:
            search_result = await self.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=top_k or self.config.top_k,
                enable_rerank=self.config.enable_rerank,
                search_mode="hybrid"
            )

            if not search_result['success']:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error=search_result.get('error')
                )

            return RAGResult(
                success=True,
                content="",
                sources=search_result['search_results'],
                metadata={'total_results': len(search_result['search_results'])},
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
        except Exception as e:
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def generate(self,
                      query: str,
                      user_id: str,
                      context: Optional[str] = None,
                      retrieval_result: Optional[RAGResult] = None,
                      options: Optional[Dict[str, Any]] = None) -> RAGResult:
        """Generate response from retrieved context"""
        start_time = time.time()
        try:
            if retrieval_result and retrieval_result.sources:
                sources = retrieval_result.sources
            else:
                retrieval = await self.retrieve(query, user_id, options=options)
                if not retrieval.success:
                    return retrieval
                sources = retrieval.sources

            # Build context
            context_text = self._build_context_with_citations(sources)

            # Generate with LLM
            response = await self._generate_response_with_llm(query, context_text, context)

            return RAGResult(
                success=True,
                content=response,
                sources=sources,
                metadata={'context_length': len(context_text)},
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
        except Exception as e:
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error=str(e)
            )
