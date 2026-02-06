"""
Mock for Qdrant vector database client.

Provides a mock implementation of Qdrant client
for testing vector operations without a real Qdrant instance.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import uuid


@dataclass
class MockPoint:
    """Represents a vector point in Qdrant."""
    id: str
    vector: List[float]
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MockScoredPoint:
    """Represents a search result with score."""
    id: str
    score: float
    payload: Dict[str, Any] = field(default_factory=dict)
    vector: Optional[List[float]] = None


@dataclass
class MockCollectionInfo:
    """Collection information."""
    name: str
    vectors_count: int = 0
    points_count: int = 0
    status: str = "green"
    config: Dict[str, Any] = field(default_factory=dict)


class MockQdrantClient:
    """
    Mock for Qdrant vector database client.

    Provides in-memory storage for testing vector operations.

    Example usage:
        client = MockQdrantClient()
        await client.create_collection("test", vectors_config={"size": 1536})
        await client.upsert("test", [
            MockPoint(id="1", vector=[0.1]*1536, payload={"name": "test"})
        ])
        results = await client.search("test", query_vector=[0.1]*1536, limit=10)
    """

    def __init__(self):
        self.collections: Dict[str, MockCollectionInfo] = {}
        self.points: Dict[str, List[MockPoint]] = {}
        self._closed = False

    async def create_collection(
        self,
        collection_name: str,
        vectors_config: Dict[str, Any] = None,
        **kwargs
    ) -> bool:
        """Create a new collection."""
        if collection_name in self.collections:
            raise ValueError(f"Collection {collection_name} already exists")

        self.collections[collection_name] = MockCollectionInfo(
            name=collection_name,
            config=vectors_config or {"size": 1536, "distance": "Cosine"}
        )
        self.points[collection_name] = []
        return True

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        if collection_name in self.collections:
            del self.collections[collection_name]
            del self.points[collection_name]
            return True
        return False

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        return collection_name in self.collections

    async def get_collection(self, collection_name: str) -> MockCollectionInfo:
        """Get collection information."""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} not found")

        info = self.collections[collection_name]
        info.points_count = len(self.points.get(collection_name, []))
        info.vectors_count = info.points_count
        return info

    async def upsert(
        self,
        collection_name: str,
        points: List[MockPoint],
        **kwargs
    ) -> Dict[str, Any]:
        """Insert or update points."""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} not found")

        collection_points = self.points[collection_name]

        for point in points:
            # Convert dict to MockPoint if needed
            if isinstance(point, dict):
                point = MockPoint(
                    id=point.get("id", str(uuid.uuid4())),
                    vector=point.get("vector", []),
                    payload=point.get("payload", {})
                )

            # Remove existing point with same ID
            collection_points = [p for p in collection_points if p.id != point.id]
            collection_points.append(point)

        self.points[collection_name] = collection_points

        return {"status": "completed", "operation_id": str(uuid.uuid4())}

    async def search(
        self,
        collection_name: str,
        query_vector: List[float] = None,
        query_text: str = None,
        limit: int = 10,
        score_threshold: float = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        filter: Dict[str, Any] = None,
        **kwargs
    ) -> List[MockScoredPoint]:
        """Search for similar vectors."""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} not found")

        points = self.points.get(collection_name, [])

        # If no query vector and query_text provided, generate mock results
        if query_vector is None and query_text:
            # Simple mock: return all points with decreasing scores
            results = []
            for i, point in enumerate(points[:limit]):
                score = 1.0 - (i * 0.1)  # Decreasing scores
                results.append(MockScoredPoint(
                    id=point.id,
                    score=max(0.1, score),
                    payload=point.payload if with_payload else {},
                    vector=point.vector if with_vectors else None
                ))
            return results

        # Calculate cosine similarity for actual vector search
        results = []
        for point in points:
            if query_vector:
                score = self._cosine_similarity(query_vector, point.vector)
            else:
                score = 0.5  # Default score

            if score_threshold and score < score_threshold:
                continue

            # Apply filter if provided
            if filter and not self._matches_filter(point.payload, filter):
                continue

            results.append(MockScoredPoint(
                id=point.id,
                score=score,
                payload=point.payload if with_payload else {},
                vector=point.vector if with_vectors else None
            ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    async def retrieve(
        self,
        collection_name: str,
        ids: List[str],
        with_payload: bool = True,
        with_vectors: bool = False,
        **kwargs
    ) -> List[MockPoint]:
        """Retrieve points by IDs."""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} not found")

        points = self.points.get(collection_name, [])
        results = []

        for point in points:
            if point.id in ids:
                result = MockPoint(
                    id=point.id,
                    vector=point.vector if with_vectors else [],
                    payload=point.payload if with_payload else {}
                )
                results.append(result)

        return results

    async def delete(
        self,
        collection_name: str,
        points_selector: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Delete points from collection."""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} not found")

        if points_selector and "points" in points_selector:
            ids_to_delete = set(points_selector["points"])
            self.points[collection_name] = [
                p for p in self.points[collection_name]
                if p.id not in ids_to_delete
            ]

        return {"status": "completed"}

    async def count(self, collection_name: str, **kwargs) -> Dict[str, int]:
        """Count points in collection."""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} not found")

        return {"count": len(self.points.get(collection_name, []))}

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _matches_filter(self, payload: Dict, filter: Dict) -> bool:
        """Check if payload matches filter criteria."""
        # Simple filter matching
        for key, value in filter.items():
            if key not in payload:
                return False
            if payload[key] != value:
                return False
        return True

    def close(self) -> None:
        """Close the client."""
        self._closed = True

    def is_closed(self) -> bool:
        """Check if client is closed."""
        return self._closed

    # Sync versions for compatibility
    def create_collection_sync(self, *args, **kwargs):
        """Synchronous create collection."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.create_collection(*args, **kwargs)
        )

    def search_sync(self, *args, **kwargs):
        """Synchronous search."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.search(*args, **kwargs)
        )
