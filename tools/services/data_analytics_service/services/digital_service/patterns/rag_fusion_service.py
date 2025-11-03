#!/usr/bin/env python3
"""
RAG Fusion Service - Multi-Query RAG with RRF

基于 RAG Fusion 论文实现：
1. 查询重写：生成多个查询变体
2. 并行检索：对每个查询独立检索
3. RRF 融合：使用 Reciprocal Rank Fusion 合并结果
4. 统一生成：基于融合后的上下文生成答案

优势：
- 提升召回率 20-30%
- 鲁棒性强（不依赖单一查询）
- 复用 Web Search 的 RRF 引擎
"""

import os
import asyncio
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict

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

# Import RRF engine from web services
from tools.services.web_services.services.deep_search.result_fusion import ResultFusionEngine
from tools.services.web_services.services.deep_search.models import SearchStrategy

# Qdrant client
try:
    from isa_common.qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None


class RAGFusionService(BaseRAGService):
    """
    RAG Fusion 服务 - 多查询 + RRF 融合

    核心流程:
    1. 生成查询变体（query rewriting）
    2. 并行检索所有变体
    3. RRF 融合结果
    4. 基于融合结果生成答案
    """

    def __init__(self, config: RAGConfig):
        super().__init__(config)

        # Initialize Qdrant
        self.qdrant_client: Optional[QdrantClient] = None
        self.qdrant_collection = os.getenv('QDRANT_COLLECTION', 'user_knowledge')
        self._init_qdrant()

        # Initialize RRF engine (reuse from web services)
        self.rrf_engine = ResultFusionEngine(k=60)

        # Fusion config
        self.num_queries = config.extra_config.get('num_queries', 3) if config.extra_config else 3
        self.fusion_weight_strategy = config.extra_config.get('fusion_weight', 'equal') if config.extra_config else 'equal'

        self.logger.info(f"✅ RAG Fusion Service initialized (num_queries={self.num_queries})")

    def _init_qdrant(self):
        """初始化 Qdrant 客户端（与其他 RAG 服务相同）"""
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
        存储内容（复用 Simple RAG 的存储逻辑）

        RAG Fusion 主要改进检索和生成，存储逻辑与 Simple RAG 相同
        """
        start_time = time.time()
        try:
            if not self.qdrant_client:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={},
                    mode_used=RAGMode.RAG_FUSION,
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
                    'rag_mode': 'rag_fusion'
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
                mode_used=RAGMode.RAG_FUSION,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Store failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={},
                mode_used=RAGMode.RAG_FUSION,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def retrieve(self, request: RAGRetrieveRequest) -> RAGResult:
        """
        检索 - RAG Fusion 核心逻辑

        流程:
        1. 生成查询变体
        2. 并行检索所有查询
        3. RRF 融合结果
        """
        start_time = time.time()
        try:
            if not self.qdrant_client:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={},
                    mode_used=RAGMode.RAG_FUSION,
                    processing_time=time.time() - start_time,
                    error="Qdrant client not available"
                )

            # Step 1: Generate query variants
            self.logger.info(f"🔄 Generating {self.num_queries} query variants for: '{request.query}'")
            query_variants = await self._generate_query_variants(
                request.query,
                num_variants=self.num_queries - 1  # -1 because we include original
            )

            # Include original query
            all_queries = [request.query] + query_variants
            self.logger.info(f"📝 Query variants: {all_queries}")

            # Step 2: Parallel retrieval for all queries
            self.logger.info(f"🔍 Performing parallel retrieval for {len(all_queries)} queries")
            retrieval_tasks = [
                self._retrieve_single_query(query, request.user_id, request.top_k)
                for query in all_queries
            ]
            all_results = await asyncio.gather(*retrieval_tasks)

            # Step 3: RRF Fusion
            self.logger.info("🔗 Fusing results with RRF")
            fused_sources = self._fuse_results_with_rrf(all_queries, all_results)

            # Limit to top_k after fusion
            fused_sources = fused_sources[:request.top_k]

            self.logger.info(
                f"✅ Fusion complete: {len(fused_sources)} unique results "
                f"from {sum(len(r) for r in all_results)} total results"
            )

            return RAGResult(
                success=True,
                content="",
                sources=fused_sources,
                metadata={
                    'num_queries': len(all_queries),
                    'query_variants': all_queries,
                    'total_results_before_fusion': sum(len(r) for r in all_results),
                    'results_after_fusion': len(fused_sources),
                    'fusion_method': 'reciprocal_rank_fusion'
                },
                mode_used=RAGMode.RAG_FUSION,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Retrieve failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={},
                mode_used=RAGMode.RAG_FUSION,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def generate(self, request: RAGGenerateRequest) -> RAGResult:
        """
        生成答案（基于融合后的上下文）
        """
        start_time = time.time()
        try:
            # Get sources (from request or retrieve)
            if request.retrieval_sources:
                sources = [
                    RAGSource(**s) if isinstance(s, dict) else s
                    for s in request.retrieval_sources
                ]
            else:
                # Retrieve with RAG Fusion
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

            # Build context
            use_citations = request.options.get('use_citations', True) if request.options else True
            context_text = self._build_context(sources, use_citations=use_citations)

            # Generate response
            prompt = f"""Based on the following sources (retrieved via multi-query fusion), provide a comprehensive answer.

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
                    mode_used=RAGMode.RAG_FUSION,
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
                    'fusion_enabled': True
                },
                mode_used=RAGMode.RAG_FUSION,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Generate failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.RAG_FUSION,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def _generate_query_variants(self, query: str, num_variants: int = 2) -> List[str]:
        """
        生成查询变体

        使用 LLM 生成同义但表达不同的查询
        """
        prompt = f"""Generate {num_variants} alternative versions of the following query.
Each version should ask the same question but use different wording, synonyms, or perspectives.

Original query: {query}

Generate {num_variants} variants (one per line):"""

        try:
            response = await self._generate_response(
                prompt,
                model="gpt-4.1-nano",
                temperature=0.7,
                max_tokens=200
            )

            if not response:
                self.logger.warning("Failed to generate query variants, using original only")
                return []

            # Parse variants (one per line)
            variants = [line.strip() for line in response.strip().split('\n') if line.strip()]
            variants = [v.lstrip('0123456789.-) ') for v in variants]  # Remove numbering
            variants = variants[:num_variants]  # Limit to requested number

            return variants

        except Exception as e:
            self.logger.error(f"Query variant generation failed: {e}")
            return []

    async def _retrieve_single_query(
        self,
        query: str,
        user_id: str,
        top_k: int
    ) -> List[RAGSource]:
        """
        单个查询的检索
        """
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                return []

            # Search in Qdrant
            filter_conditions = {'user_id': user_id}
            search_results = self.qdrant_client.search_with_filter(
                collection_name=self.qdrant_collection,
                vector=query_embedding,
                filter_conditions=filter_conditions,
                limit=top_k
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

            return sources

        except Exception as e:
            self.logger.error(f"Single query retrieval failed: {e}")
            return []

    def _fuse_results_with_rrf(
        self,
        queries: List[str],
        results: List[List[RAGSource]]
    ) -> List[RAGSource]:
        """
        使用 RRF 融合多个查询的结果

        复用 Web Search 的 RRF 引擎
        """
        # Convert to RRF engine format
        # Group by unique text (as URL equivalent)
        text_to_data = defaultdict(lambda: {
            'scores': [],
            'ranks': [],
            'source': None
        })

        for query_idx, query_results in enumerate(results):
            for rank, source in enumerate(query_results, start=1):
                text_key = source.text  # Use text as unique key

                # RRF score contribution
                rrf_score = 1.0 / (60 + rank)  # k=60

                text_to_data[text_key]['scores'].append(rrf_score)
                text_to_data[text_key]['ranks'].append(rank)

                # Keep first occurrence
                if text_to_data[text_key]['source'] is None:
                    text_to_data[text_key]['source'] = source

        # Create fused results
        fused_sources = []
        for text, data in text_to_data.items():
            # Sum RRF scores
            fusion_score = sum(data['scores'])

            # Get original source
            source = data['source']

            # Update metadata with fusion info
            source.metadata['fusion_score'] = fusion_score
            source.metadata['appeared_in_queries'] = len(data['scores'])
            source.metadata['average_rank'] = sum(data['ranks']) / len(data['ranks'])

            # Use fusion score as final score
            source.score = fusion_score

            fused_sources.append(source)

        # Sort by fusion score
        fused_sources.sort(key=lambda x: x.score, reverse=True)

        return fused_sources
