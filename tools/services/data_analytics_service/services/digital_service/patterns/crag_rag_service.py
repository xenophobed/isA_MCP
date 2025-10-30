#!/usr/bin/env python3
"""
CRAG RAG Service - Corrective Retrieval-Augmented Generation

Implements quality assessment and correction strategies:
- CORRECT: High-quality retrieval → Use directly
- AMBIGUOUS: Medium-quality → Refine and re-retrieve
- INCORRECT: Low-quality → Fallback strategies

使用 Qdrant + ISA Model (新架构)
"""

import os
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

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


class QualityLevel(str, Enum):
    """检索质量等级"""
    CORRECT = "correct"       # 高质量 (score >= 0.7)
    AMBIGUOUS = "ambiguous"   # 中等质量 (0.4 <= score < 0.7)
    INCORRECT = "incorrect"   # 低质量 (score < 0.4)


class CRAGRAGService(BaseRAGService):
    """CRAG RAG服务 - 带质量评估和纠正的检索增强生成

    核心特性:
    1. 三级质量评估 (CORRECT/AMBIGUOUS/INCORRECT)
    2. 动态纠正策略
    3. 质量感知的响应生成
    """

    def __init__(self, config: RAGConfig):
        super().__init__(config)

        # Quality thresholds
        self.quality_threshold_high = 0.7   # CORRECT threshold
        self.quality_threshold_low = 0.4    # INCORRECT threshold

        # 初始化 Qdrant 客户端 (复用 Simple RAG 的成功实现)
        self.qdrant_client: Optional[QdrantClient] = None
        self.qdrant_collection = os.getenv('QDRANT_COLLECTION', 'user_knowledge')
        self._init_qdrant()

        self.logger.info("✅ CRAG RAG Service initialized with quality assessment")

    def _init_qdrant(self):
        """初始化 Qdrant 客户端 (与 Simple RAG 相同)"""
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

    # ========== Phase 1: Store & Retrieve with Pydantic + Qdrant ==========

    async def store(self, request: RAGStoreRequest) -> RAGResult:
        """
        存储内容到 Qdrant (与 Simple RAG 相同，但添加质量预评估)

        Args:
            request: 存储请求 (Pydantic 验证)

        Returns:
            RAGResult 包含存储统计信息
        """
        start_time = time.time()

        self.logger.info(f"{'='*80}")
        self.logger.info(f"▶▶▶ CRAGRAGService.store() CALLED ◀◀◀")
        self.logger.info(f"user_id={request.user_id}, content_length={len(request.content)}")
        self.logger.info(f"{'='*80}")

        try:
            # 1. 分块文本 (使用基类方法)
            self.logger.info("→ Step 1: Chunking text...")
            chunks = self._chunk_text(request.content)
            self.logger.info(f"✓ Chunked into {len(chunks)} chunks")

            if not chunks:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Failed to chunk text'},
                    mode_used=RAGMode.CRAG,
                    processing_time=time.time() - start_time,
                    error='Failed to chunk text'
                )

            # 2. 为每个块生成 embedding 并存储到 Qdrant (带质量预评估)
            self.logger.info(f"→ Step 2: Storing {len(chunks)} chunks with quality pre-assessment...")
            stored_count = 0
            quality_scores = []

            for i, chunk_data in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                chunk_text = chunk_data['text']

                # CRAG特性: 预评估块质量
                quality_score = await self._assess_chunk_quality(chunk_text)
                quality_scores.append(quality_score)

                self.logger.info(f"  → Chunk {i+1}/{len(chunks)}: Quality={quality_score:.2f}")

                # 生成 embedding
                embedding = await self._generate_embedding(chunk_text)
                if not embedding:
                    self.logger.warning(f"  ✗ Failed to generate embedding for chunk {chunk_data['id']}")
                    continue

                # 准备 payload (包含质量分数)
                payload = {
                    'user_id': request.user_id,
                    'text': chunk_text,
                    'chunk_id': chunk_data['id'],
                    'start_pos': chunk_data['start_pos'],
                    'end_pos': chunk_data['end_pos'],
                    'stored_at': datetime.now().isoformat(),
                    'quality_score': quality_score,  # CRAG特性
                    'quality_assessed': True,        # CRAG特性
                    **(request.metadata or {})
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
                            self.logger.info(f"  ✅ Stored chunk {i+1} (quality={quality_score:.2f})")
                        else:
                            self.logger.warning(f"  ✗ Upsert returned None for chunk {i+1}")

                    except Exception as e:
                        self.logger.error(f"  ✗ Qdrant storage failed for chunk {i+1}: {e}")
                else:
                    self.logger.error(f"  ✗ Qdrant client not available!")

            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

            result = RAGResult(
                success=True,
                content=f"Stored {stored_count}/{len(chunks)} chunks",
                sources=[],
                metadata={
                    'chunks_processed': stored_count,
                    'total_chunks': len(chunks),
                    'content_length': len(request.content),
                    'average_quality': avg_quality,  # CRAG特性
                    'quality_assessed': True         # CRAG特性
                },
                mode_used=RAGMode.CRAG,
                processing_time=time.time() - start_time
            )

            self.logger.info(f"✅ CRAGRAGService.store() completed: {stored_count}/{len(chunks)} chunks (avg quality={avg_quality:.2f})")
            return result

        except Exception as e:
            self.logger.error(f"Store failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.CRAG,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def retrieve(self, request: RAGRetrieveRequest) -> RAGResult:
        """
        从 Qdrant 检索并评估质量

        CRAG特性: 检索后立即评估质量,分类为 CORRECT/AMBIGUOUS/INCORRECT

        Args:
            request: 检索请求 (Pydantic 验证)

        Returns:
            RAGResult 包含质量评估的 sources
        """
        start_time = time.time()

        self.logger.info(f"{'='*80}")
        self.logger.info(f"▶▶▶ CRAGRAGService.retrieve() CALLED ◀◀◀")
        self.logger.info(f"query={request.query}, user_id={request.user_id}")
        self.logger.info(f"{'='*80}")

        try:
            # 1. 生成查询 embedding
            query_embedding = await self._generate_embedding(request.query)
            if not query_embedding:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Failed to generate query embedding'},
                    mode_used=RAGMode.CRAG,
                    processing_time=time.time() - start_time,
                    error='Failed to generate query embedding'
                )

            # 2. 从 Qdrant 检索 (获取更多结果用于质量评估)
            if not self.qdrant_client:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': 'Qdrant client not available'},
                    mode_used=RAGMode.CRAG,
                    processing_time=time.time() - start_time,
                    error='Qdrant client not available'
                )

            top_k = request.top_k or self.config.top_k
            # CRAG: 检索更多结果用于质量评估和过滤
            retrieval_top_k = top_k * 2

            # 构建过滤条件
            filter_conditions = {'must': [
                {'field': 'user_id', 'match': {'keyword': request.user_id}}
            ]}
            if request.filters:
                for key, value in request.filters.items():
                    filter_conditions['must'].append({
                        'field': key,
                        'match': {'keyword': value}
                    })

            # 执行搜索
            search_results = self.qdrant_client.search_with_filter(
                collection_name=self.qdrant_collection,
                vector=query_embedding,
                filter_conditions=filter_conditions,
                limit=retrieval_top_k
            )

            # 3. CRAG特性: 质量评估和分类
            # Handle None return from Qdrant (defensive)
            assessed_sources = []
            quality_stats = {'correct': 0, 'ambiguous': 0, 'incorrect': 0}

            if not search_results:  # Handles None and empty list
                self.logger.warning("No search results found")
                return RAGResult(
                    success=True,
                    content="",
                    sources=[],
                    metadata={'total_results': 0},
                    mode_used=RAGMode.CRAG,
                    processing_time=time.time() - start_time
                )

            self.logger.info(f"→ Assessing quality of search results...")

            # Count results (avoid len() calls for safety)
            results_count = 0
            for result in search_results:
                results_count += 1
                # Handle None result items defensively
                if result is None:
                    self.logger.warning("Skipping None result from search")
                    continue

                payload = result.get('payload', {}) or {}
                similarity_score = result.get('score', 0.0)

                # Get text and handle None case
                if payload is None:
                    payload = {}
                text = payload.get('text', '') or ''

                # 评估质量
                quality_assessment = await self._assess_result_quality(
                    request.query,
                    text,
                    similarity_score
                )

                # 分类
                quality_level = self._classify_quality(quality_assessment['overall_score'])
                quality_stats[quality_level.value] += 1

                self.logger.info(
                    f"  Result: score={similarity_score:.3f}, "
                    f"quality={quality_assessment['overall_score']:.3f}, "
                    f"level={quality_level.value}"
                )

                # 创建 RAGSource 并添加质量信息
                source = RAGSource(
                    text=text,  # Use already-validated text
                    score=similarity_score,
                    metadata={
                        **payload,
                        'quality_assessment': quality_assessment,
                        'quality_level': quality_level.value
                    }
                )
                assessed_sources.append(source)

            # 4. CRAG特性: 过滤低质量结果
            # 只保留 CORRECT 和 AMBIGUOUS，丢弃 INCORRECT
            filtered_sources = [
                s for s in assessed_sources
                if s.metadata.get('quality_level') != QualityLevel.INCORRECT
            ]

            # 如果过滤后没有结果，保留最好的几个
            if not filtered_sources:
                self.logger.warning("All results marked INCORRECT, keeping top results anyway")
                filtered_sources = assessed_sources[:top_k]

            # 按质量评分排序并返回 top_k
            filtered_sources.sort(
                key=lambda s: s.metadata.get('quality_assessment', {}).get('overall_score', 0),
                reverse=True
            )
            final_sources = filtered_sources[:top_k]

            self.logger.info(
                f"✅ Retrieved {len(final_sources)}/{results_count} after quality filtering "
                f"(CORRECT={quality_stats['correct']}, "
                f"AMBIGUOUS={quality_stats['ambiguous']}, "
                f"INCORRECT={quality_stats['incorrect']})"
            )

            return RAGResult(
                success=True,
                content="",
                sources=final_sources,
                metadata={
                    'total_results': len(final_sources),
                    'initial_results': results_count,
                    'filtered_out': results_count - len(final_sources),
                    'quality_stats': quality_stats,
                    'retrieval_method': 'crag_quality_filtered'
                },
                mode_used=RAGMode.CRAG,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Retrieve failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.CRAG,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    # ========== Quality Assessment Methods ==========

    async def _assess_chunk_quality(self, text: str) -> float:
        """
        评估文档块质量 (存储时使用)

        简化评估基于:
        - 长度 (更长通常更完整)
        - 完整性 (以句号结尾)
        - 信息密度 (词数)
        """
        factors = {
            'length': min(len(text) / 200, 1.0),
            'completeness': 1.0 if text.strip().endswith('.') else 0.7,
            'density': min(len(text.split()) / 50, 1.0)
        }

        return sum(factors.values()) / len(factors)

    async def _assess_result_quality(
        self,
        query: str,
        text: str,
        similarity_score: float
    ) -> Dict[str, float]:
        """
        评估检索结果质量 (检索时使用)

        返回详细的质量评估
        """
        # 1. 相关性 (基于 similarity score)
        relevance_score = similarity_score

        # 2. 完整性 (query terms coverage)
        completeness_score = await self._assess_completeness(query, text)

        # 3. 准确性 (基于文本特征)
        accuracy_score = await self._assess_accuracy(text)

        # 综合评分 (加权平均)
        overall_score = (
            relevance_score * 0.5 +      # 相关性权重最高
            completeness_score * 0.3 +   # 完整性次之
            accuracy_score * 0.2         # 准确性指示
        )

        return {
            'relevance_score': relevance_score,
            'completeness_score': completeness_score,
            'accuracy_score': accuracy_score,
            'overall_score': overall_score
        }

    async def _assess_completeness(self, query: str, text: str) -> float:
        """评估完整性 - query terms 在 text 中的覆盖率"""
        # Handle None values defensively
        if query is None:
            query = ""
        if text is None:
            text = ""

        query_terms = set(query.lower().split())
        text_terms = set(text.lower().split())

        if not query_terms:
            return 0.0

        overlap = len(query_terms.intersection(text_terms))
        return min(overlap / len(query_terms), 1.0)

    async def _assess_accuracy(self, text: str) -> float:
        """评估准确性 - 基于文本质量指标"""
        # Handle None value defensively
        if text is None:
            text = ""

        accuracy_indicators = {
            'has_facts': any(word in text.lower() for word in
                           ['according to', 'research shows', 'studies', 'data']),
            'has_sources': any(word in text.lower() for word in
                             ['source:', 'reference:', 'cited', 'from']),
            'is_detailed': len(text.split()) > 50,
            'has_structure': any(char in text for char in ['1.', '2.', '•', '-'])
        }

        return sum(accuracy_indicators.values()) / len(accuracy_indicators)

    def _classify_quality(self, overall_score: float) -> QualityLevel:
        """分类质量等级"""
        if overall_score >= self.quality_threshold_high:
            return QualityLevel.CORRECT
        elif overall_score >= self.quality_threshold_low:
            return QualityLevel.AMBIGUOUS
        else:
            return QualityLevel.INCORRECT

    # ========== Placeholder for Phase 2 & 3 ==========

    async def generate(self, request: RAGGenerateRequest) -> RAGResult:
        """
        生成响应 (Phase 3 will implement)

        Currently: Basic placeholder
        """
        start_time = time.time()

        # Placeholder: Will implement in Phase 3
        return RAGResult(
            success=False,
            content="",
            sources=[],
            metadata={'error': 'generate() not yet implemented in Phase 1'},
            mode_used=RAGMode.CRAG,
            processing_time=time.time() - start_time,
            error='generate() not yet implemented in Phase 1'
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """获取CRAG RAG能力"""
        return {
            'name': 'CRAG RAG',
            'description': 'Corrective RAG with quality assessment',
            'features': [
                'Quality assessment (CORRECT/AMBIGUOUS/INCORRECT)',
                'Dynamic filtering',
                'Quality-aware retrieval',
                'Noise reduction',
                'Result refinement'
            ],
            'best_for': [
                'Large-scale retrieval',
                'High quality requirements',
                'Noisy data',
                'Precision-critical queries'
            ],
            'complexity': 'medium',
            'supports_rerank': True,
            'supports_hybrid': True,
            'processing_speed': 'medium',
            'resource_usage': 'medium',
            'quality_assessment': True,
            'phase': 'phase1_store_retrieve_only'
        }
