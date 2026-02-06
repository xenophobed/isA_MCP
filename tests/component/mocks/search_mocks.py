"""
Mock implementations for HierarchicalSearchService component tests.

Provides in-memory mocks for:
- Qdrant client (skill and tool collections)
- Database pool (schema loading)
- Model client (embeddings)
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import uuid


class MockQdrantSearchClient:
    """
    Mock Qdrant client for search operations.

    Supports:
    - Separate collections for skills and tools
    - Filter conditions
    - Score-based results
    """

    def __init__(self):
        self.collections: Dict[str, List[Dict[str, Any]]] = {
            "mcp_skills": [],
            "mcp_unified_search": [],
        }
        self._calls: List[Dict[str, Any]] = []

    def _record_call(self, method: str, **kwargs):
        """Record method call for verification."""
        self._calls.append({"method": method, **kwargs})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls, optionally filtered by method."""
        if method:
            return [c for c in self._calls if c.get("method") == method]
        return self._calls

    def seed_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        score: float = 0.8,
        tool_count: int = 5,
        is_active: bool = True
    ):
        """Add a skill to the mock collection."""
        self.collections["mcp_skills"].append({
            "id": skill_id,
            "score": score,
            "payload": {
                "id": skill_id,
                "name": name,
                "description": description,
                "tool_count": tool_count,
                "is_active": is_active,
            }
        })

    def seed_tool(
        self,
        tool_id: str,
        db_id: int,
        name: str,
        description: str,
        score: float = 0.7,
        skill_ids: List[str] = None,
        primary_skill_id: str = None,
        item_type: str = "tool",
        is_active: bool = True
    ):
        """Add a tool to the mock collection."""
        self.collections["mcp_unified_search"].append({
            "id": tool_id,
            "score": score,
            "payload": {
                "db_id": db_id,
                "name": name,
                "description": description,
                "type": item_type,
                "skill_ids": skill_ids or [],
                "primary_skill_id": primary_skill_id,
                "is_active": is_active,
            }
        })

    async def search_with_filter(
        self,
        collection_name: str,
        vector: List[float],
        filter_conditions: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        with_payload: bool = True,
        with_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """Mock search with filter."""
        self._record_call(
            "search_with_filter",
            collection_name=collection_name,
            filter_conditions=filter_conditions,
            limit=limit
        )

        collection = self.collections.get(collection_name, [])

        # Apply filters
        results = []
        for item in collection:
            payload = item.get("payload", {})

            # Check is_active filter
            if filter_conditions:
                must_conditions = filter_conditions.get("must", [])
                passes_filter = True

                for condition in must_conditions:
                    field = condition.get("field")
                    match = condition.get("match", {})

                    if "keyword" in match:
                        if payload.get(field) != match["keyword"]:
                            passes_filter = False
                            break

                    if "any" in match:
                        # skill_ids contains any of the matched skills
                        item_skill_ids = payload.get(field, [])
                        if not any(sid in item_skill_ids for sid in match["any"]):
                            passes_filter = False
                            break

                if not passes_filter:
                    continue

            results.append(item)

        # Sort by score descending and limit
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]


class MockDbPool:
    """
    Mock PostgreSQL pool for schema loading.
    """

    def __init__(self):
        self.schemas: Dict[int, Dict[str, Any]] = {}
        self._calls: List[Dict[str, Any]] = []

    def seed_schema(
        self,
        db_id: int,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        annotations: Optional[Dict[str, Any]] = None
    ):
        """Add schema data for a tool."""
        self.schemas[db_id] = {
            "id": db_id,
            "input_schema": input_schema or {"type": "object"},
            "output_schema": output_schema,
            "annotations": annotations,
        }

    async def query(self, sql: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Mock query execution."""
        self._calls.append({"sql": sql, "params": params})

        # Return schemas for requested IDs
        if params:
            return [self.schemas[db_id] for db_id in params if db_id in self.schemas]
        return []

    def get_calls(self) -> List[Dict[str, Any]]:
        """Get recorded calls."""
        return self._calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockVectorRepository:
    """
    Mock VectorRepository for search operations.
    """

    def __init__(self):
        self._client: Optional[MockQdrantSearchClient] = None
        self._calls: List[Dict[str, Any]] = []

    def set_client(self, client: MockQdrantSearchClient):
        """Set the mock Qdrant client."""
        self._client = client

    async def search(
        self,
        query_vector: List[float],
        collection_name: str = "mcp_unified_search",
        limit: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Mock vector search."""
        self._calls.append({
            "method": "search",
            "collection_name": collection_name,
            "limit": limit,
            "filter_conditions": filter_conditions
        })

        if self._client:
            return await self._client.search_with_filter(
                collection_name=collection_name,
                vector=query_vector,
                filter_conditions=filter_conditions,
                limit=limit
            )
        return []


@dataclass
class MockEmbeddingData:
    """Mock embedding data."""
    embedding: List[float]


@dataclass
class MockEmbeddingResponse:
    """Mock embedding response."""
    data: List[MockEmbeddingData]


class MockEmbeddings:
    """Mock embeddings interface."""

    def __init__(self):
        self._calls: List[Dict[str, Any]] = []
        self._embedding_size = 1536

    async def create(
        self,
        input: str,
        model: str = "text-embedding-3-small"
    ) -> MockEmbeddingResponse:
        """Create embedding."""
        self._calls.append({"input": input, "model": model})
        # Return deterministic embedding based on input hash
        embedding = [0.1] * self._embedding_size
        return MockEmbeddingResponse(data=[MockEmbeddingData(embedding=embedding)])


class MockSearchModelClient:
    """
    Mock model client for search operations.
    """

    def __init__(self):
        self.embeddings = MockEmbeddings()
        self._calls: List[Dict[str, Any]] = []

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls."""
        all_calls = self._calls + [
            {"method": "embeddings.create", **c} for c in self.embeddings._calls
        ]
        if method:
            return [c for c in all_calls if method in c.get("method", "")]
        return all_calls
