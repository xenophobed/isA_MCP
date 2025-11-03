#!/usr/bin/env python3
"""
RAPTOR RAG Service - 层次化文档组织RAG实现

迁移到新架构:
- Qdrant 存储向量（支持层次化元数据）
- ISA Model 生成 embeddings 和 LLM 响应
- 使用 isa_common.QdrantClient 和 core.config
- Pydantic 验证请求/响应
"""

import os
import logging
import time
import uuid
import numpy as np
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

# 使用配置系统
try:
    from core.config.infra_config import InfraConfig
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    InfraConfig = None

logger = logging.getLogger(__name__)


class RAPTORRAGService(BaseRAGService):
    """RAPTOR RAG服务实现 - 层次化文档组织

    存储架构:
    - Qdrant: 存储多层次向量（叶节点、摘要节点、根节点）
    - 元数据标记层级 (level: 0=leaf, 1=summary, 2=root)
    - 支持树结构关联 (tree_id, parent, children)
    """

    def __init__(self, config: RAGConfig):
        super().__init__(config)

        # 初始化 Qdrant 客户端
        self.qdrant_client: Optional[QdrantClient] = None
        self.qdrant_collection = os.getenv('QDRANT_COLLECTION', 'user_knowledge')
        self._init_qdrant()

        # RAPTOR 特定配置
        self.cluster_threshold = float(os.getenv('RAPTOR_CLUSTER_THRESHOLD', '0.8'))
        self.max_summary_length = int(os.getenv('RAPTOR_MAX_SUMMARY_LENGTH', '500'))

        self.logger.info("RAPTOR RAG Service initialized")

    def _init_qdrant(self):
        """初始化 Qdrant 客户端（直接使用 isa_common）"""
        if not QDRANT_AVAILABLE:
            self.logger.warning("Qdrant not available")
            return

        try:
            # 优先使用配置系统，回退到环境变量
            if CONFIG_AVAILABLE:
                config = InfraConfig.from_env()
                host = config.qdrant_grpc_host
                port = config.qdrant_grpc_port
            else:
                host = os.getenv('QDRANT_HOST', 'localhost')
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
                    # Create collection
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
                self.logger.warning("Continuing with Qdrant client, assuming collection exists")

        except Exception as e:
            self.logger.error(f"Qdrant initialization failed: {e}")
            self.qdrant_client = None

    # ========== 实现抽象方法 (使用 Pydantic 模型) ==========

    async def store(self, request: RAGStoreRequest) -> RAGResult:
        """
        存储内容到 Qdrant - 构建层次化树结构

        Args:
            request: 存储请求（Pydantic 验证）

        Returns:
            RAGResult 包含层次化树统计信息
        """
        start_time = time.time()

        self.logger.info(f"{'='*80}")
        self.logger.info(f"▶▶▶ RAPTORRAGService.store() CALLED ◀◀◀")
        self.logger.info(f"user_id={request.user_id}, content_length={len(request.content)}")
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
                    mode_used=RAGMode.RAPTOR,
                    processing_time=time.time() - start_time,
                    error='Failed to chunk text'
                )

            # 2. 构建层次化树
            self.logger.info(f"→ Step 2: Building hierarchical tree...")
            tree_structure = await self._build_hierarchical_tree(chunks, request.user_id, request.metadata)
            self.logger.info(f"✓ Built tree with {len(tree_structure['levels'])} levels, {tree_structure['total_nodes']} nodes")

            # 3. 存储层次化数据到 Qdrant
            self.logger.info(f"→ Step 3: Storing {tree_structure['total_nodes']} hierarchical nodes...")
            stored_count = await self._store_hierarchical_data(tree_structure, request.user_id)
            self.logger.info(f"✓ Stored {stored_count} nodes to Qdrant")

            return RAGResult(
                success=True,
                content=f"Stored {stored_count}/{tree_structure['total_nodes']} hierarchical nodes across {len(tree_structure['levels'])} levels",
                sources=[],
                metadata={
                    'tree_id': tree_structure['tree_id'],
                    'tree_levels': len(tree_structure['levels']),
                    'total_nodes': tree_structure['total_nodes'],
                    'stored_nodes': stored_count,
                    'leaf_nodes': len(tree_structure['levels'][0]) if tree_structure['levels'] else 0
                },
                mode_used=RAGMode.RAPTOR,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"RAPTOR store failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.RAPTOR,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def retrieve(self, request: RAGRetrieveRequest) -> RAGResult:
        """
        从 Qdrant 检索相关内容 - 层次化检索

        Args:
            request: 检索请求（Pydantic 验证）

        Returns:
            RAGResult 包含多层次检索结果
        """
        start_time = time.time()

        try:
            # 1. 在摘要层搜索
            self.logger.info("→ Searching summary level...")
            summary_results = await self._search_level(request.query, request.user_id, level=1, top_k=request.top_k)
            self.logger.info(f"✓ Summary level: {len(summary_results)} results")

            # 2. 在详细层搜索
            self.logger.info("→ Searching detail level...")
            detail_results = await self._search_level(request.query, request.user_id, level=0, top_k=request.top_k)
            self.logger.info(f"✓ Detail level: {len(detail_results)} results")

            # 3. 合并和排序结果
            combined_sources = await self._merge_hierarchical_results(summary_results, detail_results)
            self.logger.info(f"✓ Merged to {len(combined_sources)} total results")

            return RAGResult(
                success=True,
                content="",
                sources=combined_sources[:request.top_k],  # Limit to top_k after merge
                metadata={
                    'retrieval_method': 'hierarchical_raptor',
                    'summary_matches': len(summary_results),
                    'detail_matches': len(detail_results),
                    'tree_levels_searched': 2
                },
                mode_used=RAGMode.RAPTOR,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"RAPTOR retrieve failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.RAPTOR,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def generate(self, request: RAGGenerateRequest) -> RAGResult:
        """
        使用 LLM 生成响应 - 层次化上下文

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

            # 2. 构建层次化上下文
            use_citations = request.options.get('use_citations', True) if request.options else True
            context_text = self._build_context(sources, use_citations=use_citations)

            # 3. 使用 LLM 生成响应
            additional_context = request.context or ""
            additional_context = f"Hierarchical Tree Structure: Results from multiple abstraction levels. {additional_context}"

            if use_citations:
                prompt = f"""You are an AI assistant that provides accurate answers with inline citations. When you reference information from the provided hierarchical sources, immediately insert the citation number in square brackets after the relevant statement.

SOURCES (Multi-level Tree):
{context_text}

CITATION RULES:
1. When you use information from a source, insert [1], [2], etc. immediately after the statement
2. Place citations naturally within sentences, not at the end of responses
3. Multiple sources can support the same claim: [1][2]
4. Only cite sources that directly support your statements
5. Consider both high-level summaries and detailed information

CONTEXT: {additional_context}

USER QUESTION: {request.query}

Please provide a comprehensive answer with proper inline citations, leveraging both summary and detailed information."""
            else:
                prompt = f"""Based on the following hierarchical context (containing both summaries and details), please answer the user's question accurately and comprehensively.

Context:
{context_text}

Additional Context: {additional_context}

User Question: {request.query}

Please provide a helpful response based on the hierarchical context provided."""

            response_text = await self._generate_response(prompt)

            if not response_text:
                return RAGResult(
                    success=False,
                    content="",
                    sources=sources,
                    metadata={'error': 'Failed to generate response'},
                    mode_used=RAGMode.RAPTOR,
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
                    'hierarchical_levels': 2
                },
                mode_used=RAGMode.RAPTOR,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"RAPTOR generate failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.RAPTOR,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    def get_capabilities(self) -> Dict[str, Any]:
        """获取RAPTOR RAG能力"""
        return {
            'name': 'RAPTOR RAG',
            'description': '层次化文档组织RAG',
            'features': [
                '层次化树结构',
                '多级摘要',
                '复杂推理支持',
                '层次化检索',
                '文档聚类',
                'Inline Citations'
            ],
            'best_for': [
                '长文档分析',
                '复杂推理',
                '多层次信息检索',
                '文档结构理解'
            ],
            'complexity': 'high',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'processing_speed': 'medium',
            'resource_usage': 'high'
        }

    # ========== RAPTOR 特定实现 ==========

    async def _build_hierarchical_tree(self, chunks: List[Dict], user_id: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """构建层次化树结构"""
        tree_id = str(uuid.uuid4())
        levels = []

        # 叶节点层 (原始chunks)
        self.logger.info("  → Building leaf level...")
        leaf_nodes = []
        for i, chunk_data in enumerate(chunks):
            chunk_text = chunk_data['text']

            # 生成 embedding
            embedding = await self._generate_embedding(chunk_text)
            if embedding:
                node_id = str(uuid.uuid4())
                leaf_nodes.append({
                    'node_id': node_id,
                    'text': chunk_text,
                    'embedding': embedding,
                    'level': 0,
                    'parent': None,
                    'chunk_id': chunk_data['id'],
                    'start_pos': chunk_data['start_pos'],
                    'end_pos': chunk_data['end_pos']
                })

        levels.append(leaf_nodes)
        self.logger.info(f"  ✓ Leaf level: {len(leaf_nodes)} nodes")

        # 摘要层 (聚类和摘要)
        if len(leaf_nodes) > 1:
            self.logger.info("  → Building summary level...")
            summary_nodes = await self._create_summary_level(leaf_nodes, tree_id)
            if summary_nodes:
                levels.append(summary_nodes)
                self.logger.info(f"  ✓ Summary level: {len(summary_nodes)} nodes")

        # 根节点层 (最高层摘要)
        if len(levels) > 1 and len(levels[-1]) > 1:
            self.logger.info("  → Building root level...")
            root_nodes = await self._create_root_level(levels[-1], tree_id)
            if root_nodes:
                levels.append(root_nodes)
                self.logger.info(f"  ✓ Root level: {len(root_nodes)} nodes")

        return {
            'tree_id': tree_id,
            'levels': levels,
            'total_nodes': sum(len(level) for level in levels)
        }

    async def _store_hierarchical_data(self, tree_structure: Dict[str, Any], user_id: str) -> int:
        """存储层次化数据到 Qdrant"""
        stored_count = 0

        if not self.qdrant_client:
            self.logger.error("Qdrant client not available")
            return stored_count

        try:
            for level_idx, level_nodes in enumerate(tree_structure['levels']):
                for node in level_nodes:
                    # 准备 payload
                    payload = {
                        'user_id': user_id,
                        'text': node['text'],
                        'level': level_idx,
                        'tree_id': tree_structure['tree_id'],
                        'parent': node.get('parent'),
                        'children': node.get('children', []),
                        'raptor_mode': True,
                        'stored_at': datetime.now().isoformat()
                    }

                    # 添加叶节点特定字段
                    if level_idx == 0:
                        payload.update({
                            'chunk_id': node.get('chunk_id'),
                            'start_pos': node.get('start_pos'),
                            'end_pos': node.get('end_pos')
                        })

                    # 存储到 Qdrant
                    try:
                        operation_id = self.qdrant_client.upsert_points(
                            self.qdrant_collection,
                            [{
                                'id': node['node_id'],
                                'vector': node['embedding'],
                                'payload': payload
                            }]
                        )

                        if operation_id:
                            stored_count += 1

                    except Exception as e:
                        self.logger.error(f"Failed to store node {node['node_id']}: {e}")

            return stored_count

        except Exception as e:
            self.logger.error(f"Failed to store hierarchical data: {e}")
            return stored_count

    async def _create_summary_level(self, leaf_nodes: List[Dict], tree_id: str) -> List[Dict]:
        """创建摘要层"""
        # 聚类相似节点
        clusters = await self._cluster_nodes(leaf_nodes)
        self.logger.info(f"    → Clustered into {len(clusters)} groups")

        summary_nodes = []
        for i, cluster in enumerate(clusters):
            # 生成摘要
            cluster_texts = [node['text'] for node in cluster]
            summary_text = await self._generate_summary(cluster_texts)

            # 生成摘要的 embedding
            summary_embedding = await self._generate_embedding(summary_text)

            if summary_embedding:
                node_id = str(uuid.uuid4())
                summary_nodes.append({
                    'node_id': node_id,
                    'text': summary_text,
                    'embedding': summary_embedding,
                    'level': 1,
                    'children': [node['node_id'] for node in cluster],
                    'tree_id': tree_id
                })

                # 更新子节点的 parent 引用
                for node in cluster:
                    node['parent'] = node_id

        return summary_nodes

    async def _create_root_level(self, summary_nodes: List[Dict], tree_id: str) -> List[Dict]:
        """创建根节点层"""
        # 生成最高层摘要
        summary_texts = [node['text'] for node in summary_nodes]
        root_text = await self._generate_summary(summary_texts)

        # 生成根节点的 embedding
        root_embedding = await self._generate_embedding(root_text)

        if root_embedding:
            node_id = str(uuid.uuid4())

            # 更新子节点的 parent 引用
            for node in summary_nodes:
                node['parent'] = node_id

            return [{
                'node_id': node_id,
                'text': root_text,
                'embedding': root_embedding,
                'level': 2,
                'children': [node['node_id'] for node in summary_nodes],
                'tree_id': tree_id
            }]

        return []

    async def _cluster_nodes(self, nodes: List[Dict]) -> List[List[Dict]]:
        """聚类节点 - 基于嵌入相似度"""
        clusters = []
        used_nodes = set()

        for i, node in enumerate(nodes):
            if i in used_nodes:
                continue

            cluster = [node]
            used_nodes.add(i)

            for j, other_node in enumerate(nodes[i+1:], i+1):
                if j in used_nodes:
                    continue

                # 计算相似度
                similarity = self._cosine_similarity(node['embedding'], other_node['embedding'])
                if similarity > self.cluster_threshold:
                    cluster.append(other_node)
                    used_nodes.add(j)

            clusters.append(cluster)

        return clusters

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    async def _generate_summary(self, texts: List[str]) -> str:
        """生成摘要 - 使用 LLM"""
        try:
            combined_text = "\n\n".join(texts)

            prompt = f"""Please generate a concise summary of the following texts. The summary should capture the key information and main themes.

TEXTS:
{combined_text}

Generate a summary (max {self.max_summary_length} characters):"""

            summary = await self._generate_response(prompt)

            if summary and len(summary) > self.max_summary_length:
                summary = summary[:self.max_summary_length] + "..."

            return summary or combined_text[:self.max_summary_length] + "..."

        except Exception as e:
            self.logger.warning(f"Summary generation failed: {e}, using truncation")
            combined_text = " ".join(texts)
            return combined_text[:self.max_summary_length] + "..." if len(combined_text) > self.max_summary_length else combined_text

    async def _search_level(self, query: str, user_id: str, level: int, top_k: int) -> List[RAGSource]:
        """在特定层级搜索"""
        try:
            if not self.qdrant_client:
                return []

            # 1. 生成查询 embedding
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                return []

            # 2. 构建过滤条件
            # Note: Filtering by level causes issues due to type mismatch (int vs float in Qdrant)
            # Filtering by boolean raptor_mode also causes "Malformed Match condition" errors
            # Solution: Filter only by user_id, then post-filter by level in Python
            filter_conditions = {
                'must': [
                    {'field': 'user_id', 'match': {'keyword': user_id}}
                ]
            }

            # 3. 执行搜索 (fetch more since we'll post-filter by level)
            search_results = self.qdrant_client.search_with_filter(
                collection_name=self.qdrant_collection,
                vector=query_embedding,
                filter_conditions=filter_conditions,
                limit=top_k * 3  # Get more results since we post-filter by level
            )

            # 4. 转换为 RAGSource (with post-filtering by level)
            sources = []
            if search_results:
                for result in search_results:
                    payload = result.get('payload', {})

                    # Post-filter by level (since Qdrant filter has type issues)
                    result_level = payload.get('level')
                    if result_level is not None and int(result_level) == level:
                        sources.append(RAGSource(
                            text=payload.get('text', ''),
                            score=result.get('score', 0.0),
                            metadata={
                                **payload,
                                'search_level': 'summary' if level == 1 else 'detail'
                            }
                        ))

                        # Stop once we have enough results
                        if len(sources) >= top_k:
                            break

            return sources

        except Exception as e:
            self.logger.error(f"Level {level} search failed: {e}")
            return []

    async def _merge_hierarchical_results(self, summary_results: List[RAGSource], detail_results: List[RAGSource]) -> List[RAGSource]:
        """合并层次化结果 - 按相似度排序"""
        # 合并结果
        all_results = summary_results + detail_results

        # 按相似度排序
        return sorted(all_results, key=lambda x: x.score, reverse=True)
