#!/usr/bin/env python3
"""
Qdrant Vector Database Implementation

Uses isa_common.qdrant_client for production-ready vector operations.
Implements BaseVectorDB interface with full support for:
- Semantic search via embeddings
- Multi-tenant filtering
- Payload management
- Batch operations
- Pagination
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import uuid4

from .base_vector_db import BaseVectorDB, SearchResult, VectorSearchConfig, SearchMode

# Import from isa_common package
try:
    from isa_common.qdrant_client import QdrantClient

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None

logger = logging.getLogger(__name__)


class QdrantVectorDB(BaseVectorDB):
    """
    Qdrant vector database implementation using isa_common client.

    Features:
    - High-performance vector search
    - Multi-tenant isolation via filters
    - Payload management without re-embedding
    - Snapshot support for backup/restore
    - Field indexes for fast filtering

    Configuration:
        host: str = 'localhost'
        port: int = 50062  (gRPC port)
        collection_name: str = 'user_knowledge'
        vector_dimension: int = 1536
        distance_metric: str = 'Cosine'  (or 'Euclid', 'Dot', 'Manhattan')
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Qdrant vector database.

        Args:
            config: Database configuration
                - host: Qdrant server host
                - port: Qdrant gRPC port (default: 50062)
                - collection_name: Collection name
                - vector_dimension: Vector size
                - distance_metric: Distance metric (Cosine, Euclid, Dot, Manhattan)
        """
        super().__init__(config)

        if not QDRANT_AVAILABLE:
            raise ImportError(
                "isa_common package not available. "
                "Install it from isA_Cloud/isA_common:\n"
                "  cd /path/to/isA_Cloud\n"
                "  pip install -e isA_common"
            )

        # Extract configuration
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 50062)
        self.collection_name = self.config.get("collection_name", "user_knowledge")
        self.vector_dimension = self.config.get("vector_dimension", 1536)
        self.distance_metric = self.config.get("distance_metric", "Cosine")

        # Initialize client
        self.client = None
        self._init_client()

        # Ensure collection exists
        self._ensure_collection()

        # Create field indexes for common filters
        self._create_indexes()

    def _init_client(self):
        """Initialize Qdrant client"""
        try:
            self.client = QdrantClient(
                host=self.host, port=self.port, user_id="intelligence-service"
            )

            # Test connection
            health = self.client.health_check()
            if health and health.get("healthy"):
                logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
            else:
                logger.warning("Qdrant health check returned unhealthy status")

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise

    def _ensure_collection(self):
        """Ensure collection exists with proper configuration"""
        try:
            # Check if collection exists
            collections = self.client.list_collections()

            if self.collection_name not in collections:
                # Create collection
                self.client.create_collection(
                    self.collection_name, self.vector_dimension, distance=self.distance_metric
                )
                logger.info(
                    f"Created collection '{self.collection_name}' with {self.vector_dimension}D vectors"
                )
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")

        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise

    def _create_indexes(self):
        """Create field indexes for common filter fields"""
        try:
            # Index user_id for multi-tenant filtering
            self.client.create_field_index(self.collection_name, "user_id", "keyword")

            # Index metadata fields if needed
            # Can add more indexes based on usage patterns
            logger.info("Created field indexes for filtering")

        except Exception as e:
            # Indexes may already exist, log warning but don't fail
            logger.debug(f"Index creation skipped: {e}")

    async def store_vector(
        self,
        id: str,
        text: str,
        embedding: List[float],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store a text with its embedding.

        Args:
            id: Unique identifier
            text: Original text content
            embedding: Vector embedding
            user_id: User identifier for isolation
            metadata: Additional metadata

        Returns:
            Success status
        """
        try:
            # Validate vector dimension
            if len(embedding) != self.vector_dimension:
                logger.error(
                    f"Vector dimension mismatch: expected {self.vector_dimension}, got {len(embedding)}"
                )
                return False

            # Build payload
            payload = {"user_id": user_id, "text": text, "id": id}

            # Add metadata if provided
            if metadata:
                payload.update(metadata)

            # Upsert point
            points = [{"id": id, "vector": embedding, "payload": payload}]

            operation_id = self.client.upsert_points(self.collection_name, points)

            if operation_id:
                logger.debug(f"Stored vector {id} for user {user_id}")
                return True
            else:
                logger.error(f"Failed to store vector {id}")
                return False

        except Exception as e:
            logger.error(f"Failed to store vector: {e}")
            return False

    async def search_vectors(
        self, query_embedding: List[float], user_id: str, config: VectorSearchConfig
    ) -> List[SearchResult]:
        """
        Search vectors using semantic similarity.

        Args:
            query_embedding: Query vector
            user_id: User identifier for filtering
            config: Search configuration

        Returns:
            List of search results
        """
        try:
            # Validate vector dimension
            if len(query_embedding) != self.vector_dimension:
                logger.error(
                    f"Query vector dimension mismatch: expected {self.vector_dimension}, got {len(query_embedding)}"
                )
                return []

            # Build filter conditions for user isolation
            filter_conditions = {"must": [{"field": "user_id", "match": {"keyword": user_id}}]}

            # Add additional metadata filters if provided
            if config.filter_metadata:
                for field, value in config.filter_metadata.items():
                    filter_conditions["must"].append({"field": field, "match": {"keyword": value}})

            # Perform filtered search
            results = self.client.search_with_filter(
                self.collection_name,
                query_embedding,
                filter_conditions=filter_conditions,
                limit=config.top_k,
                with_payload=True,
                with_vectors=config.include_embeddings,
            )

            # Convert to SearchResult objects
            search_results = []
            for result in results:
                payload = result.get("payload", {})

                search_result = SearchResult(
                    id=str(result.get("id")),
                    text=payload.get("text", ""),
                    score=result.get("score", 0.0),
                    semantic_score=result.get("score", 0.0),
                    metadata=payload,
                    embedding=result.get("vector") if config.include_embeddings else None,
                )
                search_results.append(search_result)

            logger.debug(f"Found {len(search_results)} results for user {user_id}")
            return search_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def search_text(
        self, query_text: str, user_id: str, config: VectorSearchConfig
    ) -> List[SearchResult]:
        """
        Search text using lexical/BM25 search.

        Note: Qdrant doesn't have built-in full-text search.
        This is a placeholder that returns empty results.
        For hybrid search, combine with a separate full-text engine.

        Args:
            query_text: Query text
            user_id: User identifier for filtering
            config: Search configuration

        Returns:
            Empty list (full-text search not supported natively)
        """
        logger.warning(
            "Qdrant doesn't support lexical search natively. Use hybrid mode with external FTS."
        )
        return []

    async def delete_vector(self, id: str, user_id: str) -> bool:
        """
        Delete a vector by ID.

        Args:
            id: Vector identifier
            user_id: User identifier for access control

        Returns:
            Success status
        """
        try:
            # Verify ownership before deletion
            vector = await self.get_vector(id, user_id)
            if not vector:
                logger.warning(f"Vector {id} not found or not owned by user {user_id}")
                return False

            # Delete point
            operation_id = self.client.delete_points(self.collection_name, [id])

            if operation_id:
                logger.debug(f"Deleted vector {id} for user {user_id}")
                return True
            else:
                logger.error(f"Failed to delete vector {id}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete vector: {e}")
            return False

    async def get_vector(self, id: str, user_id: str) -> Optional[SearchResult]:
        """
        Get a specific vector by ID.

        Args:
            id: Vector identifier
            user_id: User identifier for access control

        Returns:
            Search result or None if not found
        """
        try:
            # Use scroll to retrieve specific point
            result = self.client.scroll(
                self.collection_name, limit=1, with_payload=True, with_vectors=False
            )

            if result and result.get("points"):
                for point in result["points"]:
                    if str(point["id"]) == id:
                        payload = point.get("payload", {})

                        # Check user ownership
                        if payload.get("user_id") != user_id:
                            return None

                        return SearchResult(
                            id=str(point["id"]),
                            text=payload.get("text", ""),
                            score=1.0,
                            metadata=payload,
                        )

            return None

        except Exception as e:
            logger.error(f"Failed to get vector: {e}")
            return None

    async def list_vectors(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[SearchResult]:
        """
        List vectors for a user with pagination.

        Args:
            user_id: User identifier
            limit: Maximum results to return
            offset: Results offset for pagination

        Returns:
            List of search results
        """
        try:
            # Calculate offset_id from offset (simplified pagination)
            offset_id = None
            if offset > 0:
                # First scroll to offset position
                temp_result = self.client.scroll(
                    self.collection_name, limit=offset, with_payload=True, with_vectors=False
                )
                if temp_result and temp_result.get("next_offset"):
                    offset_id = temp_result["next_offset"]

            # Scroll with filter
            result = self.client.scroll(
                self.collection_name,
                limit=limit,
                offset_id=offset_id,
                with_payload=True,
                with_vectors=False,
            )

            if not result or not result.get("points"):
                return []

            # Filter by user_id and convert to SearchResult
            search_results = []
            for point in result["points"]:
                payload = point.get("payload", {})

                # Filter by user
                if payload.get("user_id") != user_id:
                    continue

                search_result = SearchResult(
                    id=str(point["id"]), text=payload.get("text", ""), score=1.0, metadata=payload
                )
                search_results.append(search_result)

            logger.debug(f"Listed {len(search_results)} vectors for user {user_id}")
            return search_results

        except Exception as e:
            logger.error(f"Failed to list vectors: {e}")
            return []

    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get database statistics.

        Args:
            user_id: Optional user filter

        Returns:
            Statistics dictionary
        """
        try:
            # Get collection info
            info = self.client.get_collection_info(self.collection_name)

            if not info:
                return {"error": "Failed to get collection info"}

            stats = {
                "collection": self.collection_name,
                "total_points": info.get("points_count", 0),
                "vector_dimension": self.vector_dimension,
                "distance_metric": self.distance_metric,
                "status": info.get("status", "unknown"),
                "segments_count": info.get("segments_count", 0),
            }

            # If user_id provided, count user-specific vectors
            if user_id:
                # Use scroll to count user vectors (not efficient for large datasets)
                user_count = 0
                offset_id = None

                while True:
                    result = self.client.scroll(
                        self.collection_name,
                        limit=100,
                        offset_id=offset_id,
                        with_payload=True,
                        with_vectors=False,
                    )

                    if not result or not result.get("points"):
                        break

                    for point in result["points"]:
                        payload = point.get("payload", {})
                        if payload.get("user_id") == user_id:
                            user_count += 1

                    if not result.get("next_offset"):
                        break

                    offset_id = result["next_offset"]

                stats["user_points"] = user_count

            return stats

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    def __del__(self):
        """Cleanup on deletion"""
        if self.client:
            try:
                # Close client if it has a close method
                if hasattr(self.client, "close"):
                    self.client.close()
            except Exception:
                pass
