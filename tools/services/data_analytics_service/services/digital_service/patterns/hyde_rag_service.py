#!/usr/bin/env python3
"""
HyDE RAG Service - Hypothetical Document Embeddings

核心思想：
1. 用户查询 → 生成假设性答案（hypothetical document）
2. 用假设答案的embedding检索，而不是用原始查询
3. 假设答案和真实文档更语义相似，检索更准确

适用场景：
- 用户查询和文档用词不匹配
- 抽象/poorly-worded 查询
- 跨领域知识检索

优势：
- 提升语义匹配度 15-25%
- 处理歧义查询
- 无需额外训练

论文：Precise Zero-Shot Dense Retrieval without Relevance Labels (2022)
"""

import os
import time
from typing import Dict, Any, List, Optional

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


class HyDERAGService(BaseRAGService):
    """
    HyDE RAG 服务 - 假设文档嵌入

    核心流程:
    1. 接收用户查询
    2. 用 LLM 生成假设性答案（模拟"完美答案"）
    3. 用假设答案的 embedding 检索真实文档
    4. 基于检索结果生成最终答案
    """

    def __init__(self, config: RAGConfig):
        super().__init__(config)

        # Initialize Qdrant
        self.qdrant_client: Optional[QdrantClient] = None
        self.qdrant_collection = os.getenv('QDRANT_COLLECTION', 'user_knowledge')
        self._init_qdrant()

        # HyDE config
        self.hyde_model = config.extra_config.get('hyde_model', 'gpt-4.1-nano') if config.extra_config else 'gpt-4.1-nano'
        self.num_hypotheses = config.extra_config.get('num_hypotheses', 1) if config.extra_config else 1  # 可生成多个假设文档

        self.logger.info(f"✅ HyDE RAG Service initialized (model={self.hyde_model}, hypotheses={self.num_hypotheses})")

    def _init_qdrant(self):
        """初始化 Qdrant 客户端"""
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
            except Exception as e:
                self.logger.error(f"Collection check failed: {e}")

        except Exception as e:
            self.logger.error(f"Qdrant initialization failed: {e}")
            self.qdrant_client = None

    async def store(self, request: RAGStoreRequest) -> RAGResult:
        """
        存储内容（与 Simple RAG 相同）

        HyDE 只改进检索，存储逻辑不变
        """
        start_time = time.time()
        try:
            if not self.qdrant_client:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={},
                    mode_used=RAGMode.HYDE,
                    processing_time=time.time() - start_time,
                    error="Qdrant client not available"
                )

            # Process document into chunks
            chunks = self._chunk_text(request.content)
            stored_count = 0

            for chunk_data in chunks:
                chunk_text = chunk_data['text']
                chunk_id = chunk_data['id']

                # Generate embedding
                embedding = await self._generate_embedding(chunk_text)
                if not embedding:
                    self.logger.warning(f"Failed to generate embedding for chunk {chunk_id}")
                    continue

                # Prepare payload
                payload = {
                    'user_id': request.user_id,
                    'text': chunk_text,
                    'chunk_id': chunk_data['chunk_index'],
                    'start_pos': chunk_data['start'],
                    'end_pos': chunk_data['end'],
                    'stored_at': chunk_data['timestamp'],
                    'rag_mode': 'hyde'
                }

                # Add metadata
                if request.metadata:
                    payload.update(request.metadata)

                # Upsert to Qdrant
                try:
                    self.qdrant_client.upsert_points(
                        self.qdrant_collection,
                        [{
                            'id': chunk_id,
                            'vector': embedding,
                            'payload': payload
                        }]
                    )
                    stored_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to upsert chunk {chunk_id}: {e}")

            return RAGResult(
                success=True,
                content=f"Stored {stored_count}/{len(chunks)} chunks",
                sources=[],
                metadata={'chunks_stored': stored_count, 'total_chunks': len(chunks)},
                mode_used=RAGMode.HYDE,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Store failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={},
                mode_used=RAGMode.HYDE,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def retrieve(self, request: RAGRetrieveRequest) -> RAGResult:
        """
        检索 - HyDE 核心逻辑

        流程:
        1. 生成假设文档（hypothetical document）
        2. 用假设文档的 embedding 检索
        3. 返回检索结果
        """
        start_time = time.time()
        try:
            if not self.qdrant_client:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={},
                    mode_used=RAGMode.HYDE,
                    processing_time=time.time() - start_time,
                    error="Qdrant client not available"
                )

            # Step 1: Generate hypothetical document
            self.logger.info(f"🔮 Generating hypothetical document for query: '{request.query}'")
            hypothetical_doc = await self._generate_hypothetical_document(request.query)

            if not hypothetical_doc:
                self.logger.warning("Failed to generate hypothetical document, falling back to query embedding")
                # Fallback to direct query embedding
                query_embedding = await self._generate_embedding(request.query)
            else:
                self.logger.info(f"✅ Generated hypothetical doc ({len(hypothetical_doc)} chars)")
                # Use hypothetical document embedding
                query_embedding = await self._generate_embedding(hypothetical_doc)

            if not query_embedding:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={},
                    mode_used=RAGMode.HYDE,
                    processing_time=time.time() - start_time,
                    error="Failed to generate embedding"
                )

            # Step 2: Search with hypothetical document embedding
            filter_conditions = {'user_id': request.user_id}
            search_results = self.qdrant_client.search_with_filter(
                collection_name=self.qdrant_collection,
                vector=query_embedding,
                filter_conditions=filter_conditions,
                limit=request.top_k
            )

            # Convert to RAGSource
            sources = []
            for result in search_results:
                payload = result.get('payload', {})
                score = result.get('score', 0.0)

                source = RAGSource(
                    text=payload.get('text', ''),
                    score=score,
                    metadata=payload
                )
                sources.append(source)

            self.logger.info(f"✅ HyDE retrieval: {len(sources)} results")

            return RAGResult(
                success=True,
                content="",
                sources=sources,
                metadata={
                    'hypothetical_document': hypothetical_doc if hypothetical_doc else None,
                    'hypothetical_doc_length': len(hypothetical_doc) if hypothetical_doc else 0,
                    'retrieval_method': 'hyde_embedding',
                    'fallback_to_query': not hypothetical_doc
                },
                mode_used=RAGMode.HYDE,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Retrieve failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={},
                mode_used=RAGMode.HYDE,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def generate(self, request: RAGGenerateRequest) -> RAGResult:
        """
        生成答案（基于HyDE检索的结果）
        """
        start_time = time.time()
        try:
            # Get sources (from request or retrieve with HyDE)
            if request.retrieval_sources:
                sources = [
                    RAGSource(**s) if isinstance(s, dict) else s
                    for s in request.retrieval_sources
                ]
                retrieval_metadata = {}
            else:
                # Retrieve with HyDE
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
                retrieval_metadata = retrieval.metadata

            # Build context
            use_citations = request.options.get('use_citations', True) if request.options else True
            context_text = self._build_context(sources, use_citations=use_citations)

            # Generate response
            prompt = f"""Based on the following sources (retrieved via HyDE - hypothetical document embeddings), provide a comprehensive answer.

SOURCES:
{context_text}

QUESTION: {request.query}

Please provide a detailed answer with proper citations."""

            response_text = await self._generate_response(prompt, model="gpt-4.1-nano")

            if not response_text:
                return RAGResult(
                    success=False,
                    content="",
                    sources=sources,
                    metadata={'error': 'Failed to generate response'},
                    mode_used=RAGMode.HYDE,
                    processing_time=time.time() - start_time,
                    error='Failed to generate response'
                )

            return RAGResult(
                success=True,
                content=response_text,
                sources=sources,
                metadata={
                    'context_length': len(context_text),
                    'sources_count': len(sources),
                    'use_citations': use_citations,
                    'hyde_enabled': True,
                    **retrieval_metadata  # Include HyDE retrieval metadata
                },
                mode_used=RAGMode.HYDE,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Generate failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.HYDE,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def _generate_hypothetical_document(self, query: str) -> Optional[str]:
        """
        生成假设文档

        给定用户查询，生成一个假设性的"完美答案"
        这个假设答案会更接近知识库中真实文档的语义
        """
        prompt = f"""Given the following question, write a comprehensive, detailed answer as if you were an expert responding to this question.
Write in a style similar to how information would appear in a knowledge base or documentation.

Question: {query}

Write a detailed answer (2-3 paragraphs):"""

        try:
            hypothetical_doc = await self._generate_response(
                prompt,
                model=self.hyde_model,
                temperature=0.7,  # 稍高温度以获得更自然的文档
                max_tokens=300  # 限制长度，避免过长
            )

            if not hypothetical_doc:
                self.logger.warning("Failed to generate hypothetical document")
                return None

            return hypothetical_doc.strip()

        except Exception as e:
            self.logger.error(f"Hypothetical document generation failed: {e}")
            return None
