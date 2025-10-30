#!/usr/bin/env python3
"""
Simple RAG Service - 传统向量检索RAG实现

使用:
- Qdrant 存储向量
- ISA Model 生成 embeddings 和 LLM 响应
- 直接使用 isa_common.QdrantClient（无中间层）
"""

import os
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

# 直接使用 isa_common.QdrantClient
try:
    from isa_common.qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None

logger = logging.getLogger(__name__)


class SimpleRAGService(BaseRAGService):
    """Simple RAG服务实现 - 传统向量检索

    存储架构:
    - Qdrant: 存储文本向量和元数据
    """

    def __init__(self, config: RAGConfig):
        super().__init__(config)

        # 初始化 Qdrant 客户端（Simple RAG 只需要 Qdrant）
        self.qdrant_client: Optional[QdrantClient] = None
        self.qdrant_collection = os.getenv('QDRANT_COLLECTION', 'user_knowledge')
        self._init_qdrant()

        self.logger.info("Simple RAG Service initialized")

    def _init_qdrant(self):
        """初始化 Qdrant 客户端（直接使用 isa_common）"""
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
                    self.logger.info(f"✅ Collection '{self.qdrant_collection}' exists with {collection_info.get('points_count', 0)} points")
                else:
                    # Collection doesn't exist, create it
                    self.logger.warning(f"Collection '{self.qdrant_collection}' not found, creating...")
                    result = self.qdrant_client.create_collection(
                        collection_name=self.qdrant_collection,
                        vector_size=vector_dim,
                        distance='Cosine'
                    )
                    if result:
                        self.logger.info(f"✅ Created collection '{self.qdrant_collection}'")
                    else:
                        self.logger.error(f"Failed to create collection '{self.qdrant_collection}'")
                        self.qdrant_client = None
            except Exception as e:
                self.logger.error(f"Collection check/create failed: {e}")
                # Don't fail completely, collection might exist but check failed
                self.logger.warning("Continuing with Qdrant client, assuming collection exists")

        except Exception as e:
            self.logger.error(f"Qdrant initialization failed: {e}")
            self.qdrant_client = None
    
    # ========== 实现抽象方法 (使用 Pydantic 模型) ==========

    async def store(self, request: RAGStoreRequest) -> RAGResult:
        """
        存储内容到 Qdrant

        Args:
            request: 存储请求（Pydantic 验证）

        Returns:
            RAGResult 包含存储统计信息
        """
        start_time = time.time()

        self.logger.info(f"{'='*80}")
        self.logger.info(f"▶▶▶ SimpleRAGService.store() CALLED ◀◀◀")
        self.logger.info(f"user_id={request.user_id}, content_length={len(request.content)}")
        self.logger.info(f"qdrant_client available: {self.qdrant_client is not None}")
        self.logger.info(f"{'='*80}")

        try:
            # 1. 分块文本
            self.logger.info("→ Step 1: Chunking text...")
            chunks = self._chunk_text(request.content)
            self.logger.info(f"✓ Chunked into {len(chunks)} chunks")

            if not chunks:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Failed to chunk text'},
                    mode_used=RAGMode.SIMPLE,
                    processing_time=time.time() - start_time,
                    error='Failed to chunk text'
                )

            # 2. 为每个块生成 embedding 并存储到 Qdrant
            self.logger.info(f"→ Step 2: Generating embeddings and storing {len(chunks)} chunks...")
            stored_count = 0
            for i, chunk_data in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                chunk_text = chunk_data['text']

                # 生成 embedding
                self.logger.info(f"  → Chunk {i+1}/{len(chunks)}: Generating embedding...")
                embedding = await self._generate_embedding(chunk_text)
                if not embedding:
                    self.logger.warning(f"  ✗ Failed to generate embedding for chunk {chunk_data['id']}")
                    continue
                self.logger.info(f"  ✓ Embedding generated (dim={len(embedding)})")

                # 准备 payload
                payload = {
                    'user_id': request.user_id,
                    'text': chunk_text,
                    'chunk_id': chunk_data['id'],
                    'start_pos': chunk_data['start_pos'],
                    'end_pos': chunk_data['end_pos'],
                    'stored_at': datetime.now().isoformat(),
                    **(request.metadata or {})
                }

                # 存储到 Qdrant
                if self.qdrant_client:
                    try:
                        self.logger.info(f"  → Upserting to Qdrant collection '{self.qdrant_collection}'...")
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
                            self.logger.info(f"  ✅ Stored chunk {i+1} to Qdrant (operation_id={operation_id})")
                        else:
                            self.logger.warning(f"  ✗ Upsert returned None for chunk {i+1}")

                    except Exception as e:
                        self.logger.error(f"  ✗ Qdrant storage failed for chunk {i+1}: {e}")
                else:
                    self.logger.error(f"  ✗ Qdrant client not available! Cannot store chunk {i+1}")

            result = RAGResult(
                success=True,
                content=f"Stored {stored_count}/{len(chunks)} chunks",
                sources=[],
                metadata={
                    'chunks_processed': stored_count,
                    'total_chunks': len(chunks),
                    'content_length': len(request.content)
                },
                mode_used=RAGMode.SIMPLE,
                processing_time=time.time() - start_time
            )

            self.logger.info(f"✅ SimpleRAGService.store() completed: {stored_count}/{len(chunks)} chunks stored in {time.time() - start_time:.2f}s")
            return result

        except Exception as e:
            self.logger.error(f"Store failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.SIMPLE,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def retrieve(self, request: RAGRetrieveRequest) -> RAGResult:
        """
        从 Qdrant 检索相关内容

        Args:
            request: 检索请求（Pydantic 验证）

        Returns:
            RAGResult 包含检索到的 sources
        """
        start_time = time.time()

        try:
            # 1. 生成查询 embedding
            query_embedding = await self._generate_embedding(request.query)
            if not query_embedding:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Failed to generate query embedding'},
                    mode_used=RAGMode.SIMPLE,
                    processing_time=time.time() - start_time,
                    error='Failed to generate query embedding'
                )

            # 2. 从 Qdrant 检索
            if not self.qdrant_client:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Qdrant client not available'},
                    mode_used=RAGMode.SIMPLE,
                    processing_time=time.time() - start_time,
                    error='Qdrant client not available'
                )

            top_k = request.top_k or self.config.top_k

            # 构建过滤条件 (使用正确的 isa_common API 格式: field + keyword)
            filter_conditions = None
            if request.filters:
                filter_conditions = {'must': [
                    {'field': 'user_id', 'match': {'keyword': request.user_id}}
                ]}
                # 添加其他过滤条件
                for key, value in request.filters.items():
                    filter_conditions['must'].append({
                        'field': key,
                        'match': {'keyword': value}
                    })
            else:
                filter_conditions = {'must': [
                    {'field': 'user_id', 'match': {'keyword': request.user_id}}
                ]}

            # 执行搜索 (使用 isa_common API)
            search_results = self.qdrant_client.search_with_filter(
                collection_name=self.qdrant_collection,
                vector=query_embedding,
                filter_conditions=filter_conditions,
                limit=top_k
            )

            # 3. 转换为 RAGSource
            sources = []
            if search_results:  # Handle None return
                for result in search_results:
                    sources.append(RAGSource(
                        text=result.get('payload', {}).get('text', ''),
                        score=result.get('score', 0.0),
                        metadata=result.get('payload', {})
                    ))

            return RAGResult(
                success=True,
                content="",
                sources=sources,
                metadata={
                    'total_results': len(sources),
                    'retrieval_method': 'vector_similarity'
                },
                mode_used=RAGMode.SIMPLE,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Retrieve failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.SIMPLE,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def generate(self, request: RAGGenerateRequest) -> RAGResult:
        """
        使用 LLM 生成响应

        Args:
            request: 生成请求（Pydantic 验证）

        Returns:
            RAGResult 包含生成的响应
        """
        start_time = time.time()

        try:
            # 1. 获取 sources（从 request 或执行检索）
            sources = []
            if request.retrieval_sources:
                # 从 dict 转换为 RAGSource
                for source_dict in request.retrieval_sources:
                    if isinstance(source_dict, dict):
                        sources.append(RAGSource(**source_dict))
                    else:
                        sources.append(source_dict)
            else:
                # 执行检索
                retrieval_result = await self.retrieve(
                    RAGRetrieveRequest(
                        query=request.query,
                        user_id=request.user_id,
                        top_k=self.config.top_k,
                        options=request.options
                    )
                )

                if not retrieval_result.success:
                    return retrieval_result

                sources = retrieval_result.sources

            # 2. 构建上下文
            use_citations = request.options.get('use_citations', True) if request.options else True
            context_text = self._build_context(sources, use_citations=use_citations)

            # 3. 使用 LLM 生成响应
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

            response_text = await self._generate_response(prompt)

            if not response_text:
                return RAGResult(
                    success=False,
                    content="",
                    sources=sources,
                    metadata={'error': 'Failed to generate response'},
                    mode_used=RAGMode.SIMPLE,
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
                    'use_citations': use_citations
                },
                mode_used=RAGMode.SIMPLE,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Generate failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.SIMPLE,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    def get_capabilities(self) -> Dict[str, Any]:
        """获取Simple RAG能力"""
        return {
            'name': 'Simple RAG',
            'description': '传统向量检索RAG',
            'features': [
                '向量相似度检索',
                '文档分块',
                '简单上下文构建',
                '增强混合搜索',
                '可选重排序'
            ],
            'best_for': [
                '简单问答',
                '事实查询',
                '快速检索',
                '基础文档搜索'
            ],
            'complexity': 'low',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'processing_speed': 'fast',
            'resource_usage': 'low'
        }
