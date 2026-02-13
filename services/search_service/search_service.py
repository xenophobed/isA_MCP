"""
Search Service - Simplified semantic search

职责：
- 只负责搜索，不负责同步
- 使用 Qdrant 进行向量搜索
- 返回结构化的搜索结果
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""

    id: str  # 唯一标识
    type: str  # tool/prompt/resource
    name: str  # 名称
    description: str  # 描述
    score: float  # 相似度得分 (0-1)
    db_id: int  # PostgreSQL ID
    metadata: Dict[str, Any]  # 额外元数据
    inputSchema: Optional[Dict[str, Any]] = None  # Tool input schema (for tool calling)
    outputSchema: Optional[Dict[str, Any]] = None  # Tool output schema
    annotations: Optional[Dict[str, Any]] = None  # MCP annotations


class SearchService:
    """
    简化的搜索服务

    核心流程：
    1. 接收用户查询
    2. 生成 query embedding
    3. Qdrant 语义搜索
    4. 返回结果
    """

    def __init__(self):
        """Initialize search service"""
        from services.vector_service import VectorRepository
        from tools.intelligent_tools.language.embedding_generator import EmbeddingGenerator
        from services.tool_service.tool_repository import ToolRepository
        from services.prompt_service.prompt_repository import PromptRepository
        from services.resource_service.resource_repository import ResourceRepository

        self.vector_repo = VectorRepository()
        self.embedding_gen = EmbeddingGenerator()

        # Add repositories to fetch full schemas
        self.tool_repo = ToolRepository()
        self.prompt_repo = PromptRepository()
        self.resource_repo = ResourceRepository()

        logger.info("SearchService initialized")

    async def initialize(self):
        """Initialize search service"""
        try:
            await self.vector_repo.ensure_collection()
            logger.info("SearchService ready")
        except Exception as e:
            logger.error(f"Failed to initialize SearchService: {e}")
            raise

    async def search(
        self,
        query: str,
        item_type: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.3,  # Reasonable threshold for description-only embeddings
    ) -> List[SearchResult]:
        """
        搜索工具/提示词/资源

        Args:
            query: 用户查询（自然语言）
            item_type: 过滤类型 ('tool', 'prompt', 'resource', None=全部)
            limit: 返回结果数量
            score_threshold: 最低相似度阈值（默认 0.3）

        Returns:
            搜索结果列表（按相似度排序）
        """
        try:
            logger.info(f"🔍 [SearchService] Starting search for: '{query}'")
            logger.info(
                f"   Parameters: type={item_type}, limit={limit}, threshold={score_threshold}"
            )

            # 1. 生成 query embedding
            logger.info(f"📝 [SearchService] Step 1: Generating query embedding...")
            try:
                query_embedding = await self.embedding_gen.embed_single(query)
                logger.info(
                    f"✅ [SearchService] Embedding generated: {len(query_embedding)}D vector"
                )
                logger.debug(f"   First 5 values: {query_embedding[:5]}")
            except Exception as e:
                logger.error(f"❌ [SearchService] Embedding generation failed: {e}")
                raise

            # 2. Qdrant 语义搜索
            logger.info(f"🔎 [SearchService] Step 2: Searching Qdrant...")
            try:
                results = await self.vector_repo.search_vectors(
                    query_embedding=query_embedding,
                    item_type=item_type,
                    limit=limit,
                    score_threshold=score_threshold,
                )
                logger.info(f"✅ [SearchService] Qdrant returned {len(results)} raw results")
                if results:
                    logger.info(f"   Top 3 scores: {[r.get('score', 0) for r in results[:3]]}")
                else:
                    logger.warning(f"⚠️  [SearchService] No results from Qdrant!")
            except Exception as e:
                logger.error(f"❌ [SearchService] Qdrant search failed: {e}")
                raise

            # 3. 转换为 SearchResult 对象并获取完整 schema
            logger.info(f"📦 [SearchService] Step 3: Enriching results with full schemas...")
            search_results = []
            for i, r in enumerate(results):
                try:
                    item_type = r["type"]
                    db_id = r["db_id"]

                    # Fetch full schema from PostgreSQL based on type
                    inputSchema = None
                    outputSchema = None
                    annotations = None

                    if item_type == "tool" and db_id:
                        tool_data = await self.tool_repo.get_tool_by_id(db_id)
                        if tool_data:
                            inputSchema = tool_data.get("input_schema")
                            outputSchema = tool_data.get("output_schema")
                            annotations = tool_data.get("annotations")
                            logger.debug(
                                f"   ✅ Fetched schema for tool '{r['name']}' (id={db_id})"
                            )
                        else:
                            logger.warning(
                                f"   ⚠️  Tool '{r['name']}' not found in PostgreSQL (id={db_id})"
                            )
                    elif item_type == "prompt" and db_id:
                        prompt_data = await self.prompt_repo.get_prompt_by_id(db_id)
                        if prompt_data:
                            # Prompts may have different schema structure
                            annotations = prompt_data.get("annotations")
                    elif item_type == "resource" and db_id:
                        resource_data = await self.resource_repo.get_resource_by_id(db_id)
                        if resource_data:
                            annotations = resource_data.get("annotations")

                    search_results.append(
                        SearchResult(
                            id=r["id"],
                            type=r["type"],
                            name=r["name"],
                            description=r["description"],
                            score=r["score"],
                            db_id=r["db_id"],
                            metadata=r.get("metadata", {}),
                            inputSchema=inputSchema,
                            outputSchema=outputSchema,
                            annotations=annotations,
                        )
                    )
                except Exception as e:
                    logger.error(f"   Failed to enrich result {i}: {e}, data: {r}")

            logger.info(f"✅ [SearchService] Final result: {len(search_results)} items")
            for i, r in enumerate(search_results[:3]):
                has_schema = "✓" if r.inputSchema else "✗"
                logger.info(
                    f"   {i+1}. {r.name} ({r.type}): score={r.score:.3f}, schema={has_schema}"
                )

            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def search_tools(
        self, query: str, limit: int = 10, score_threshold: float = 0.3
    ) -> List[SearchResult]:
        """
        只搜索工具

        Args:
            query: 用户查询
            limit: 返回结果数量
            score_threshold: 最低相似度阈值（默认 0.3）

        Returns:
            工具搜索结果
        """
        return await self.search(
            query=query, item_type="tool", limit=limit, score_threshold=score_threshold
        )

    async def search_prompts(
        self, query: str, limit: int = 10, score_threshold: float = 0.5
    ) -> List[SearchResult]:
        """只搜索提示词"""
        return await self.search(
            query=query, item_type="prompt", limit=limit, score_threshold=score_threshold
        )

    async def search_resources(
        self, query: str, limit: int = 10, score_threshold: float = 0.5
    ) -> List[SearchResult]:
        """只搜索资源"""
        return await self.search(
            query=query, item_type="resource", limit=limit, score_threshold=score_threshold
        )

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取搜索服务统计信息

        Returns:
            统计信息
        """
        return await self.vector_repo.get_stats()
