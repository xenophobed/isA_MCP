"""
Hierarchical Search Service - Skill-based two-stage semantic search.

Implements:
- Stage 1: Query skills collection to find relevant skill categories
- Stage 2: Search tools filtered by matched skill IDs
- Stage 3: Enrich results with full schemas from PostgreSQL
"""
import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import json
import re

from core.config import get_settings
from core.clients.model_client import get_model_client
from services.vector_service.vector_repository import VectorRepository

logger = logging.getLogger(__name__)


def _parse_skill_ids(value) -> List[str]:
    """
    Parse skill_ids from various formats returned by Qdrant.

    Handles:
    - Already a list: ['web-api', 'search']
    - Go-style string: "[web-api search-retrieval data-analysis]"
    - JSON string: '["web-api", "search"]'
    - Empty/None: returns []

    Returns:
        List of skill ID strings
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if not isinstance(value, str):
        return []

    value = value.strip()
    if not value:
        return []

    # Try JSON parse first
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Handle Go-style format: "[item1 item2 item3]"
    if value.startswith('[') and value.endswith(']'):
        inner = value[1:-1].strip()
        if inner:
            # Split by whitespace
            return inner.split()

    # Single value
    return [value]


class SearchStrategy(str, Enum):
    """Search strategy options."""
    HIERARCHICAL = "hierarchical"  # Skill -> Tools (default)
    DIRECT = "direct"  # Skip skill layer
    HYBRID = "hybrid"  # Parallel skill + direct


@dataclass
class SkillMatch:
    """A matched skill from Stage 1."""
    id: str
    name: str
    description: str
    score: float
    tool_count: int


@dataclass
class ToolMatch:
    """A matched tool from Stage 2."""
    id: str
    db_id: int
    type: str
    name: str
    description: str
    score: float
    skill_ids: List[str] = field(default_factory=list)
    primary_skill_id: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    annotations: Optional[Dict[str, Any]] = None


@dataclass
class SearchMetadata:
    """Search execution metadata."""
    strategy_used: str
    skill_ids_used: Optional[List[str]]
    stage1_skill_count: int
    stage2_candidate_count: int
    final_count: int
    query_embedding_time_ms: float
    skill_search_time_ms: float
    tool_search_time_ms: float
    schema_load_time_ms: float
    total_time_ms: float


@dataclass
class HierarchicalSearchResult:
    """Complete search result."""
    query: str
    tools: List[ToolMatch]
    matched_skills: List[SkillMatch]
    metadata: SearchMetadata


class HierarchicalSearchService:
    """
    Hierarchical search service with skill-based routing.

    Flow:
    1. Generate query embedding (reused for both stages)
    2. Stage 1: Search skills collection, get top skill_limit skills
    3. Stage 2: Search tools filtered by matched skill IDs
    4. Stage 3: Load full schemas from PostgreSQL
    """

    def __init__(
        self,
        vector_repository: Optional[VectorRepository] = None,
        model_client=None,
        db_pool=None,
        qdrant_client=None
    ):
        """
        Initialize the hierarchical search service.

        Args:
            vector_repository: Optional VectorRepository for tools
            model_client: Optional model client for embeddings
            db_pool: Optional PostgreSQL pool for schema loading
            qdrant_client: Optional Qdrant client (for testing)
        """
        self._vector_repository = vector_repository
        self._model_client = model_client
        self._db_pool = db_pool
        self._qdrant_client = qdrant_client
        self._skill_collection = "mcp_skills"
        self._tool_collection = "mcp_unified_search"
        self._settings = get_settings()

    async def _get_vector_repository(self) -> VectorRepository:
        """Get or create vector repository."""
        if self._vector_repository is None:
            self._vector_repository = VectorRepository()
        return self._vector_repository

    async def _get_model_client(self):
        """Get or create model client."""
        if self._model_client is None:
            self._model_client = await get_model_client()
        return self._model_client

    async def _get_db_pool(self):
        """Get or create database pool."""
        if self._db_pool is None:
            from isa_common import AsyncPostgresClient
            settings = get_settings()
            self._db_pool = AsyncPostgresClient(
                host=settings.infrastructure.postgres_grpc_host,
                port=settings.infrastructure.postgres_grpc_port,
                user_id="mcp-search-service"
            )
        return self._db_pool

    async def search(
        self,
        query: str,
        item_type: Optional[str] = None,
        limit: int = 5,
        skill_limit: int = 3,
        skill_threshold: float = 0.4,
        tool_threshold: float = 0.3,
        include_schemas: bool = True,
        strategy: str = "hierarchical"
    ) -> HierarchicalSearchResult:
        """
        Perform hierarchical search.

        Args:
            query: Natural language search query
            item_type: Filter by type (tool/prompt/resource), None=all
            limit: Maximum tools to return
            skill_limit: Maximum skills to match in Stage 1
            skill_threshold: Minimum similarity for skill matching
            tool_threshold: Minimum similarity for tool matching
            include_schemas: Whether to load full schemas
            strategy: Search strategy (hierarchical/direct/hybrid)

        Returns:
            HierarchicalSearchResult with tools, skills, and metadata
        """
        total_start = time.time()

        # Validate query
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if len(query) > 1000:
            raise ValueError("Query cannot exceed 1000 characters")

        # Initialize timing
        embedding_time = 0.0
        skill_search_time = 0.0
        tool_search_time = 0.0
        schema_load_time = 0.0

        matched_skills: List[SkillMatch] = []
        skill_ids_used: Optional[List[str]] = None
        strategy_used = strategy

        try:
            # Step 0: Generate query embedding (reused for all stages)
            embed_start = time.time()
            query_embedding = await self._generate_embedding(query)
            embedding_time = (time.time() - embed_start) * 1000

            if strategy == "direct":
                # Direct search - skip skill layer
                skill_search_time = 0.0
            else:
                # Stage 1: Search skills
                skill_start = time.time()
                matched_skills = await self._search_skills(
                    query_embedding=query_embedding,
                    limit=skill_limit,
                    threshold=skill_threshold
                )
                skill_search_time = (time.time() - skill_start) * 1000

                # Extract skill IDs for filtering
                if matched_skills:
                    skill_ids_used = [s.id for s in matched_skills]
                else:
                    # No skills matched - fallback to direct search
                    logger.warning("No skills matched, falling back to direct search")
                    skill_ids_used = None

            # Stage 2: Search tools with skill filter
            tool_start = time.time()
            stage2_candidates = await self._search_tools(
                query_embedding=query_embedding,
                skill_ids=skill_ids_used,
                item_type=item_type,
                limit=limit * 2,  # Fetch more to account for filtering
                threshold=tool_threshold
            )
            tool_search_time = (time.time() - tool_start) * 1000

            # Limit results
            tools = stage2_candidates[:limit]

            # Stage 3: Load schemas if requested
            schema_start = time.time()
            if include_schemas and tools:
                tools = await self._enrich_with_schemas(tools)
            schema_load_time = (time.time() - schema_start) * 1000

            # Calculate total time
            total_time = (time.time() - total_start) * 1000

            # Build metadata
            metadata = SearchMetadata(
                strategy_used=strategy_used,
                skill_ids_used=skill_ids_used,
                stage1_skill_count=len(matched_skills),
                stage2_candidate_count=len(stage2_candidates),
                final_count=len(tools),
                query_embedding_time_ms=embedding_time,
                skill_search_time_ms=skill_search_time,
                tool_search_time_ms=tool_search_time,
                schema_load_time_ms=schema_load_time,
                total_time_ms=total_time
            )

            logger.info(
                f"Hierarchical search completed: "
                f"{len(matched_skills)} skills -> {len(tools)} tools in {total_time:.1f}ms"
            )

            return HierarchicalSearchResult(
                query=query,
                tools=tools,
                matched_skills=matched_skills,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Hierarchical search failed: {e}")
            raise

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        model_client = await self._get_model_client()
        response = await model_client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    async def _get_qdrant_client(self):
        """Get or create Qdrant client."""
        if self._qdrant_client is not None:
            return self._qdrant_client
        from isa_common import AsyncQdrantClient
        settings = get_settings()
        return AsyncQdrantClient(
            host=settings.infrastructure.qdrant_grpc_host,
            port=settings.infrastructure.qdrant_grpc_port,
            user_id="mcp-search-service"
        )

    async def _search_skills(
        self,
        query_embedding: List[float],
        limit: int,
        threshold: float
    ) -> List[SkillMatch]:
        """
        Search the skills collection (Stage 1).

        Args:
            query_embedding: Query vector
            limit: Maximum skills to return
            threshold: Minimum similarity score

        Returns:
            List of matched skills
        """
        try:
            client = await self._get_qdrant_client()

            # Build filter for active skills
            filter_conditions = {
                "must": [
                    {"field": "is_active", "match": {"boolean": True}}
                ]
            }

            # Search skills collection
            results = await client.search_with_filter(
                collection_name=self._skill_collection,
                vector=query_embedding,
                filter_conditions=filter_conditions,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            # Filter by threshold and convert to SkillMatch
            matches = []
            for result in results or []:
                score = result.get("score", 0.0)
                if score >= threshold:
                    payload = result.get("payload", {})
                    matches.append(SkillMatch(
                        id=payload.get("id", str(result.get("id"))),
                        name=payload.get("name", "Unknown"),
                        description=payload.get("description", ""),
                        score=score,
                        tool_count=payload.get("tool_count", 0)
                    ))

            logger.debug(f"Skill search found {len(matches)} matches above threshold {threshold}")
            return matches

        except Exception as e:
            logger.error(f"Skill search failed: {e}")
            return []

    async def _search_tools(
        self,
        query_embedding: List[float],
        skill_ids: Optional[List[str]],
        item_type: Optional[str],
        limit: int,
        threshold: float
    ) -> List[ToolMatch]:
        """
        Search the tools collection with optional skill filter (Stage 2).

        Args:
            query_embedding: Query vector
            skill_ids: Skill IDs to filter by (None = no filter)
            item_type: Item type filter (tool/prompt/resource)
            limit: Maximum results
            threshold: Minimum similarity score

        Returns:
            List of matched tools
        """
        try:
            vector_repo = await self._get_vector_repository()

            # Build filter conditions
            filter_conditions = {"must": []}

            # Add skill filter if provided
            # Note: Filter by primary_skill_id because skill_ids is stored as string
            # due to gRPC serialization. primary_skill_id is a string field.
            if skill_ids:
                filter_conditions["should"] = [
                    {"field": "primary_skill_id", "match": {"keyword": skill_id}}
                    for skill_id in skill_ids
                ]

            # Add type filter if provided
            if item_type:
                filter_conditions["must"].append({
                    "field": "type",
                    "match": {"keyword": item_type}
                })

            # Add active filter
            filter_conditions["must"].append({
                "field": "is_active",
                "match": {"boolean": True}
            })

            # Get client (uses injected mock in tests)
            client = await self._get_qdrant_client()

            # Search with filter
            results = await client.search_with_filter(
                collection_name=self._tool_collection,
                vector=query_embedding,
                filter_conditions=filter_conditions if filter_conditions["must"] else None,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            # Filter by threshold and convert to ToolMatch
            matches = []
            for result in results or []:
                score = result.get("score", 0.0)
                if score >= threshold:
                    payload = result.get("payload", {})
                    matches.append(ToolMatch(
                        id=str(result.get("id")),
                        db_id=payload.get("db_id", 0),
                        type=payload.get("type", "tool"),
                        name=payload.get("name", "Unknown"),
                        description=payload.get("description", ""),
                        score=score,
                        skill_ids=_parse_skill_ids(payload.get("skill_ids")),
                        primary_skill_id=payload.get("primary_skill_id"),
                    ))

            # Sort by score descending
            matches.sort(key=lambda x: x.score, reverse=True)

            logger.debug(f"Tool search found {len(matches)} matches above threshold {threshold}")
            return matches

        except Exception as e:
            logger.error(f"Tool search failed: {e}")
            return []

    async def _enrich_with_schemas(
        self,
        tools: List[ToolMatch]
    ) -> List[ToolMatch]:
        """
        Load full schemas from PostgreSQL for matched tools (Stage 3).

        Args:
            tools: Tools to enrich

        Returns:
            Tools with schemas loaded
        """
        if not tools:
            return tools

        try:
            db_pool = await self._get_db_pool()
            settings = get_settings()

            # Collect db_ids
            db_ids = [t.db_id for t in tools if t.db_id]
            if not db_ids:
                return tools

            # Query for schemas
            placeholders = ", ".join([f"${i+1}" for i in range(len(db_ids))])
            query = f"""
                SELECT id, input_schema, output_schema, annotations
                FROM {settings.db_schema}.tools
                WHERE id IN ({placeholders})
            """

            async with db_pool:
                rows = await db_pool.query(query, params=db_ids)

            # Build lookup
            schema_lookup = {
                row["id"]: row
                for row in (rows or [])
            }

            # Enrich tools
            for tool in tools:
                if tool.db_id in schema_lookup:
                    row = schema_lookup[tool.db_id]
                    tool.input_schema = row.get("input_schema")
                    tool.output_schema = row.get("output_schema")
                    tool.annotations = row.get("annotations")

            return tools

        except Exception as e:
            logger.error(f"Schema enrichment failed: {e}")
            # Return tools without schemas rather than failing
            return tools

    async def search_skills_only(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.4,
        include_inactive: bool = False
    ) -> List[SkillMatch]:
        """
        Search only the skills collection.

        Args:
            query: Search query
            limit: Maximum results
            threshold: Minimum similarity
            include_inactive: Include inactive skills

        Returns:
            List of matched skills
        """
        embedding = await self._generate_embedding(query)
        return await self._search_skills(
            query_embedding=embedding,
            limit=limit,
            threshold=threshold
        )

    async def search_tools_only(
        self,
        query: str,
        skill_ids: Optional[List[str]] = None,
        item_type: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.3
    ) -> List[ToolMatch]:
        """
        Search only the tools collection.

        Args:
            query: Search query
            skill_ids: Optional skill IDs to filter by
            item_type: Optional type filter
            limit: Maximum results
            threshold: Minimum similarity

        Returns:
            List of matched tools
        """
        embedding = await self._generate_embedding(query)
        return await self._search_tools(
            query_embedding=embedding,
            skill_ids=skill_ids,
            item_type=item_type,
            limit=limit,
            threshold=threshold
        )

    def to_dict(self, result: HierarchicalSearchResult) -> Dict[str, Any]:
        """
        Convert search result to dictionary for API response.

        Args:
            result: Search result to convert

        Returns:
            Dictionary representation
        """
        return {
            "query": result.query,
            "tools": [
                {
                    "id": t.id,
                    "db_id": t.db_id,
                    "type": t.type,
                    "name": t.name,
                    "description": t.description,
                    "score": t.score,
                    "skill_ids": t.skill_ids,
                    "primary_skill_id": t.primary_skill_id,
                    "input_schema": t.input_schema,
                    "output_schema": t.output_schema,
                    "annotations": t.annotations,
                }
                for t in result.tools
            ],
            "matched_skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "score": s.score,
                    "tool_count": s.tool_count,
                }
                for s in result.matched_skills
            ],
            "metadata": {
                "strategy_used": result.metadata.strategy_used,
                "skill_ids_used": result.metadata.skill_ids_used,
                "stage1_skill_count": result.metadata.stage1_skill_count,
                "stage2_candidate_count": result.metadata.stage2_candidate_count,
                "final_count": result.metadata.final_count,
                "query_embedding_time_ms": result.metadata.query_embedding_time_ms,
                "skill_search_time_ms": result.metadata.skill_search_time_ms,
                "tool_search_time_ms": result.metadata.tool_search_time_ms,
                "schema_load_time_ms": result.metadata.schema_load_time_ms,
                "total_time_ms": result.metadata.total_time_ms,
            }
        }
