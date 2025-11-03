#!/usr/bin/env python3
"""
Self-RAG Service - 自我反思RAG实现

基于CRAG架构，添加自我反思和迭代refinement功能。
使用Qdrant + ISA Model。
"""

import os
import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base.base_rag_service import BaseRAGService
from ..base.rag_models import (
    RAGMode,
    RAGConfig,
    RAGStoreRequest,
    RAGRetrieveRequest,
    RAGGenerateRequest,
    RAGResult,
    RAGSource
)

# Qdrant client
try:
    from isa_common.qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None

logger = logging.getLogger(__name__)

class SelfRAGService(BaseRAGService):
    """
    Self-RAG服务实现 - 自我反思RAG

    核心特性:
    1. 自动存储和检索 (基于 Qdrant)
    2. 自我评估响应质量
    3. 迭代refinement
    """

    def __init__(self, config: RAGConfig):
        super().__init__(config)

        # 初始化 Qdrant 客户端 (复用 CRAG 的实现)
        self.qdrant_client: Optional[QdrantClient] = None
        self.qdrant_collection = os.getenv('QDRANT_COLLECTION', 'user_knowledge')
        self._init_qdrant()

        self.logger.info("✅ Self-RAG Service initialized with Qdrant")

    def _init_qdrant(self):
        """初始化 Qdrant 客户端 (与 CRAG 相同)"""
        if not QDRANT_AVAILABLE:
            self.logger.warning("Qdrant not available")
            return

        try:
            host = os.getenv('QDRANT_HOST', 'isa-qdrant-grpc')
            port = int(os.getenv('QDRANT_PORT', '50062'))
            vector_dim = int(os.getenv('VECTOR_DIMENSION', '1536'))

            self.qdrant_client = QdrantClient(host=host, port=port)
            self.logger.info(f"✅ Qdrant initialized: {host}:{port}")

            # Ensure collection exists
            try:
                collection_info = self.qdrant_client.get_collection_info(self.qdrant_collection)
                if collection_info:
                    self.logger.info(f"✅ Collection '{self.qdrant_collection}' exists")
                else:
                    self.logger.warning(f"Collection '{self.qdrant_collection}' not found, creating...")
                    result = self.qdrant_client.create_collection(
                        collection_name=self.qdrant_collection,
                        vector_size=vector_dim,
                        distance='Cosine'
                    )
                    if result:
                        self.logger.info(f"✅ Created collection '{self.qdrant_collection}'")
                    else:
                        self.logger.error(f"Failed to create collection")
                        self.qdrant_client = None
            except Exception as e:
                self.logger.error(f"Collection check/create failed: {e}")
                self.logger.warning("Continuing with Qdrant client, assuming collection exists")

        except Exception as e:
            self.logger.error(f"Qdrant initialization failed: {e}")
            self.qdrant_client = None

    async def process_document(self,
                             content: str,
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """处理文档 - 使用Qdrant存储，添加自我反思标记"""
        start_time = time.time()

        try:
            # 1. 分块文本
            chunks = self._chunk_text(content)
            self.logger.info(f"Chunked into {len(chunks)} chunks")

            if not chunks:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Failed to chunk text'},
                    mode_used=RAGMode.SELF_RAG,
                    processing_time=time.time() - start_time,
                    error='Failed to chunk text'
                )

            # 2. 为每个块生成 embedding 并存储到 Qdrant
            stored_count = 0
            for i, chunk_data in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                chunk_text = chunk_data['text']

                # 生成 embedding
                embedding = await self._generate_embedding(chunk_text)
                if not embedding:
                    self.logger.warning(f"Failed to generate embedding for chunk {chunk_data['id']}")
                    continue

                # 准备 payload (包含 self-rag 标记)
                payload = {
                    'user_id': user_id,
                    'text': chunk_text,
                    'chunk_id': chunk_data['id'],
                    'start_pos': chunk_data['start_pos'],
                    'end_pos': chunk_data['end_pos'],
                    'stored_at': datetime.now().isoformat(),
                    'self_rag_mode': True,  # Self-RAG特性
                    'reflection_enabled': True,  # Self-RAG特性
                    **(metadata or {})
                }

                # 存储到 Qdrant
                if self.qdrant_client:
                    try:
                        operation_id = self.qdrant_client.upsert_points(
                            self.qdrant_collection,
                            [{
                                'id': chunk_id,
                                'vector': embedding,
                                'payload': payload
                            }]
                        )

                        if operation_id:
                            stored_count += 1
                            self.logger.info(f"Stored chunk {i+1} with self-rag metadata")
                        else:
                            self.logger.warning(f"Upsert returned None for chunk {i+1}")

                    except Exception as e:
                        self.logger.error(f"Qdrant storage failed for chunk {i+1}: {e}")
                else:
                    self.logger.error(f"Qdrant client not available!")

            return RAGResult(
                success=True,
                content=f"Stored {stored_count}/{len(chunks)} chunks with self-reflection",
                sources=[],
                metadata={
                    'chunks_processed': stored_count,
                    'total_chunks': len(chunks),
                    'content_length': len(content),
                    'self_rag_mode': True,
                    'reflection_enabled': True
                },
                mode_used=RAGMode.SELF_RAG,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Self-RAG document processing failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.SELF_RAG,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def query(self, 
                   query: str, 
                   user_id: str,
                   context: Optional[str] = None) -> RAGResult:
        """查询处理 - 带自我反思的生成"""
        start_time = time.time()
        
        try:
            # 1. 检索相关文档
            retrieved_docs = await self._retrieve_documents(query, user_id)
            
            # 2. 生成初始响应
            initial_response = await self._generate_initial_response(query, retrieved_docs)
            
            # 3. 自我反思和修正
            final_response = await self._self_reflect_and_refine(query, initial_response, retrieved_docs)
            
            return RAGResult(
                success=True,
                content=final_response,
                sources=retrieved_docs,
                metadata={
                    'retrieval_method': 'self_rag',
                    'reflection_steps': 1,
                    'initial_response_length': len(initial_response),
                    'self_reflection_used': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Self-RAG query failed: {e}")
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
        """获取Self-RAG能力"""
        return {
            'name': 'Self-RAG',
            'description': '自我反思RAG',
            'features': [
                '自我评估',
                '质量修正',
                '减少幻觉',
                '响应反思',
                '质量保证'
            ],
            'best_for': [
                '高质量回答',
                '准确性要求高',
                '减少错误',
                '复杂推理'
            ],
            'complexity': 'medium',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'processing_speed': 'medium',
            'resource_usage': 'medium',
            'self_reflection': True
        }
    
    async def _retrieve_documents(self, query: str, user_id: str) -> List[Dict[str, Any]]:
        """检索文档"""
        try:
            # 获取用户知识库
            result = self.supabase.table(self.table_name)\
                                 .select('id, text, metadata, created_at')\
                                 .eq('user_id', user_id)\
                                 .eq('metadata->>self_rag_mode', 'true')\
                                 .execute()
            
            if not result.data:
                return []
            
            # 提取文本进行搜索
            texts = [item['text'] for item in result.data]
            from tools.services.intelligence_service.language.embedding_generator import search
            search_results = await search(query, texts, top_k=self.config.top_k)
            
            # 匹配结果
            context_items = []
            for text, similarity_score in search_results:
                for item in result.data:
                    if item['text'] == text:
                        context_items.append({
                            'knowledge_id': item['id'],
                            'text': text,
                            'similarity_score': similarity_score,
                            'metadata': item['metadata'],
                            'created_at': item['created_at']
                        })
                        break
            
            return context_items
            
        except Exception as e:
            self.logger.error(f"Self-RAG document retrieval failed: {e}")
            return []
    
    async def _generate_initial_response(self, query: str, docs: List[Dict]) -> str:
        """生成初始响应 - 现在支持inline citations!"""
        if not docs:
            return f"I don't have enough information to answer '{query}' accurately."
        
        # 使用基类的统一citation方法
        try:
            citation_context = self._build_context_with_citations(docs[:3])
            
            response = await self._generate_response_with_llm(
                query=query,
                context=citation_context,
                additional_context="Self-RAG Initial Response: This is the first generation before self-reflection.",
                use_citations=True
            )
            
            self.logger.info("✅ Self-RAG initial response generated with inline citations")
            return response
            
        except Exception as e:
            self.logger.warning(f"Self-RAG citation generation failed: {e}, falling back to traditional")
            # 降级到传统格式
            context_texts = []
            for i, doc in enumerate(docs[:3]):
                context_texts.append(f"Source {i+1}: {doc['text']}")
            context = "\n\n".join(context_texts)
            return f"Based on the available information, here's my initial response to '{query}':\n\n{context[:300]}..."
    
    async def _self_reflect_and_refine(self, query: str, response: str, docs: List[Dict]) -> str:
        """自我反思和修正"""
        try:
            # 1. 反思响应质量
            quality_assessment = await self._assess_response_quality(query, response, docs)
            
            # 2. 如果需要修正，进行修正
            if quality_assessment['needs_improvement']:
                refined_response = await self._refine_response(query, response, docs, quality_assessment)
                return refined_response
            else:
                return response
                
        except Exception as e:
            self.logger.error(f"Self-reflection failed: {e}")
            return response
    
    async def _assess_response_quality(self, query: str, response: str, docs: List[Dict]) -> Dict[str, Any]:
        """评估响应质量"""
        # 简化的质量评估
        quality_indicators = {
            'has_relevant_info': any(doc['similarity_score'] > 0.7 for doc in docs),
            'response_length': len(response) > 50,
            'mentions_sources': any('Source' in response for _ in docs),
            'answers_question': any(word in response.lower() for word in query.lower().split()[:3])
        }
        
        quality_score = sum(quality_indicators.values()) / len(quality_indicators)
        needs_improvement = quality_score < 0.6
        
        return {
            'quality_score': quality_score,
            'needs_improvement': needs_improvement,
            'indicators': quality_indicators
        }
    
    async def _refine_response(self, query: str, response: str, docs: List[Dict], quality_assessment: Dict) -> str:
        """修正响应"""
        # 基于质量评估结果进行修正
        improvements = []
        
        if not quality_assessment['indicators']['has_relevant_info']:
            improvements.append("I need to find more relevant information.")
        
        if not quality_assessment['indicators']['response_length']:
            improvements.append("I should provide more detailed information.")
        
        if not quality_assessment['indicators']['mentions_sources']:
            improvements.append("I should reference the sources more clearly.")
        
        if not quality_assessment['indicators']['answers_question']:
            improvements.append("I should better address the specific question.")
        
        # 生成修正后的响应
        refined_parts = [response]
        if improvements:
            refined_parts.append(f"\n\nReflection: {', '.join(improvements)}")
            refined_parts.append(f"\nRefined response: Let me provide a more comprehensive answer to '{query}' based on the available sources.")

        return "\n".join(refined_parts)

    # ==================== New Interface Methods (Pydantic) ====================

    async def store(self, request: RAGStoreRequest) -> RAGResult:
        """
        Store content using Self-RAG strategy

        Args:
            request: Storage request (Pydantic validated)

        Returns:
            RAGResult with storage statistics
        """
        return await self.process_document(
            request.content,
            request.user_id,
            request.metadata
        )

    async def retrieve(self, request: RAGRetrieveRequest) -> RAGResult:
        """
        Retrieve with Qdrant (similar to CRAG but without quality filtering)

        Args:
            request: Retrieval request (Pydantic validated)

        Returns:
            RAGResult with retrieved sources
        """
        start_time = time.time()
        try:
            # 1. Generate query embedding
            query_embedding = await self._generate_embedding(request.query)
            if not query_embedding:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Failed to generate query embedding'},
                    mode_used=RAGMode.SELF_RAG,
                    processing_time=time.time() - start_time,
                    error='Failed to generate query embedding'
                )

            # 2. Search Qdrant
            if not self.qdrant_client:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Qdrant client not available'},
                    mode_used=RAGMode.SELF_RAG,
                    processing_time=time.time() - start_time,
                    error='Qdrant client not available'
                )

            top_k = request.top_k or self.config.top_k

            # Build filter conditions
            filter_conditions = {'must': [
                {'field': 'user_id', 'match': {'keyword': request.user_id}}
            ]}
            if request.filters:
                for key, value in request.filters.items():
                    filter_conditions['must'].append({
                        'field': key,
                        'match': {'keyword': value}
                    })

            # Execute search
            search_results = self.qdrant_client.search_with_filter(
                collection_name=self.qdrant_collection,
                vector=query_embedding,
                filter_conditions=filter_conditions,
                limit=top_k
            )

            # 3. Convert to RAGSource objects
            sources = []
            if search_results:
                for result in search_results:
                    if result is None:
                        continue
                    payload = result.get('payload', {}) or {}
                    similarity_score = result.get('score', 0.0)
                    text = payload.get('text', '') or ''

                    sources.append(RAGSource(
                        text=text,
                        score=similarity_score,
                        metadata=payload
                    ))

            return RAGResult(
                success=True,
                content="",
                sources=sources,
                metadata={
                    'total_results': len(sources),
                    'self_rag_mode': True
                },
                mode_used=RAGMode.SELF_RAG,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Self-RAG retrieve failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.SELF_RAG,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def generate(self, request: RAGGenerateRequest) -> RAGResult:
        """
        Generate with self-reflection

        Self-RAG特性:
        - 生成初始响应
        - 自我评估质量
        - 迭代refinement
        - 质量保证

        Args:
            request: Generation request (Pydantic validated)

        Returns:
            RAGResult with refined response
        """
        start_time = time.time()
        try:
            # 1. Get sources (from request or retrieve)
            sources = []
            if request.retrieval_sources:
                # Convert dict to RAGSource if needed
                for source_dict in request.retrieval_sources:
                    if isinstance(source_dict, dict):
                        sources.append(RAGSource(**source_dict))
                    else:
                        sources.append(source_dict)
            else:
                # Retrieve sources
                retrieval = await self.retrieve(
                    RAGRetrieveRequest(
                        query=request.query,
                        user_id=request.user_id,
                        top_k=self.config.top_k,
                        options=request.options
                    )
                )
                if not retrieval.success:
                    return retrieval
                sources = retrieval.sources

            # 2. Generate initial response with citations
            use_citations = request.options.get('use_citations', True) if request.options else True
            context_text = self._build_context(sources, use_citations=use_citations)

            initial_prompt = f"""Based on the following sources, provide a comprehensive answer to the question.

SOURCES:
{context_text}

QUESTION: {request.query}

Please provide a detailed answer."""

            self.logger.info(f"🔍 Self-RAG calling LLM with prompt length: {len(initial_prompt)} chars, {len(sources)} sources")
            self.logger.info(f"🔍 Context preview: {context_text[:200]}...")
            initial_response = await self._generate_response(initial_prompt, model="gpt-4.1-nano")
            self.logger.info(f"✅ Self-RAG LLM call completed, response length: {len(initial_response) if initial_response else 0}")

            if not initial_response:
                return RAGResult(
                    success=False,
                    content="",
                    sources=sources,
                    metadata={'error': 'Failed to generate initial response'},
                    mode_used=RAGMode.SELF_RAG,
                    processing_time=time.time() - start_time,
                    error='Failed to generate initial response'
                )

            # 3. Self-RAG特性: 自我评估和refinement
            self.logger.info(f"Initial response generated ({len(initial_response)} chars), starting self-reflection...")

            assessment = await self._assess_response_quality_simple(request.query, initial_response, sources)

            if assessment['needs_improvement']:
                self.logger.info(f"Response needs improvement (score={assessment['quality_score']:.2f}), refining...")
                refined_response = await self._refine_response_simple(
                    request.query,
                    initial_response,
                    sources,
                    assessment
                )
                refinement_performed = True
            else:
                self.logger.info(f"Response quality acceptable (score={assessment['quality_score']:.2f})")
                refined_response = initial_response
                refinement_performed = False

            return RAGResult(
                success=True,
                content=refined_response,
                sources=sources,
                metadata={
                    'self_reflection_used': True,
                    'refinement_performed': refinement_performed,
                    'quality_score': assessment['quality_score'],
                    'initial_response_length': len(initial_response),
                    'final_response_length': len(refined_response),
                    'use_citations': use_citations
                },
                mode_used=RAGMode.SELF_RAG,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Self-RAG generate failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.SELF_RAG,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def _assess_response_quality_simple(self, query: str, response: str, sources: List[RAGSource]) -> Dict[str, Any]:
        """简化的质量评估"""
        quality_indicators = {
            'has_relevant_sources': any(s.score > 0.5 for s in sources),
            'response_length_ok': len(response) > 50,
            'answers_query': any(word.lower() in response.lower() for word in query.split()[:5])
        }

        quality_score = sum(quality_indicators.values()) / len(quality_indicators)
        needs_improvement = quality_score < 0.7

        return {
            'quality_score': quality_score,
            'needs_improvement': needs_improvement,
            'indicators': quality_indicators
        }

    async def _refine_response_simple(
        self,
        query: str,
        initial_response: str,
        sources: List[RAGSource],
        assessment: Dict[str, Any]
    ) -> str:
        """简化的refinement"""
        try:
            context_text = self._build_context(sources, use_citations=True)

            refine_prompt = f"""The initial response needs improvement. Please provide a better answer.

ORIGINAL QUESTION: {query}

INITIAL RESPONSE:
{initial_response}

AVAILABLE SOURCES:
{context_text}

IMPROVEMENT NEEDED:
- Quality score: {assessment['quality_score']:.2f} (target: 0.7+)
- Issues: {', '.join([k for k, v in assessment['indicators'].items() if not v])}

Please provide an improved, more comprehensive response that addresses these issues."""

            refined = await self._generate_response(refine_prompt, model="gpt-4.1-nano")
            return refined if refined else initial_response

        except Exception as e:
            self.logger.error(f"Refinement failed: {e}")
            return initial_response
