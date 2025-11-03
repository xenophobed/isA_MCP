"""
Vector Repository - Qdrant vector database operations
Handles all vector storage and retrieval for MCP search
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import uuid4

logger = logging.getLogger(__name__)


class VectorRepository:
    """
    Vector repository for Qdrant operations

    Responsibilities:
    - Create and manage Qdrant collections
    - Store vectors with metadata
    - Search vectors by similarity
    - Delete vectors
    """

    def __init__(self, host='isa-qdrant-grpc', port=50062):
        """Initialize vector repository"""
        self.collection_name = 'mcp_unified_search'
        self.vector_dimension = 1536  # text-embedding-3-small
        self.distance_metric = 'Cosine'

        # Initialize Qdrant client
        try:
            from isa_common.qdrant_client import QdrantClient
            self.client = QdrantClient(
                host=host,
                port=port,
                user_id='mcp-vector-service'
            )
            logger.info(f"Connected to Qdrant at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise

    async def ensure_collection(self):
        """
        Ensure collection exists with proper configuration
        Call this during initialization
        """
        try:
            # Check if collection exists
            collections = self.client.list_collections()

            if self.collection_name not in collections:
                # Create collection
                self.client.create_collection(
                    self.collection_name,
                    self.vector_dimension,
                    distance=self.distance_metric
                )
                logger.info(f"Created collection '{self.collection_name}'")

                # Create field indexes
                await self._create_indexes()
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    async def _create_indexes(self):
        """Create field indexes for filtering"""
        try:
            # Index for type filtering (tool/prompt/resource)
            self.client.create_field_index(
                self.collection_name,
                'type',
                'keyword'
            )

            # Index for active status filtering
            self.client.create_field_index(
                self.collection_name,
                'is_active',
                'keyword'
            )

            logger.info("Created field indexes for filtering")

        except Exception as e:
            logger.warning(f"Index creation failed (may already exist): {e}")

    async def upsert_vector(
        self,
        item_id: int,  # Must be integer for Qdrant
        item_type: str,
        name: str,
        description: str,
        embedding: List[float],
        db_id: int,
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Insert or update a vector

        Args:
            item_id: Unique integer identifier (use PostgreSQL ID)
            item_type: Type of item ('tool', 'prompt', 'resource')
            name: Item name
            description: Item description
            embedding: Vector embedding (1536 dimensions)
            db_id: PostgreSQL database ID
            is_active: Whether item is active
            metadata: Additional metadata

        Returns:
            Success status
        """
        try:
            # Validate vector dimension
            if len(embedding) != self.vector_dimension:
                logger.error(f"Vector dimension mismatch: expected {self.vector_dimension}, got {len(embedding)}")
                return False

            # Build payload
            payload = {
                'type': item_type,
                'name': name,
                'description': description,
                'db_id': db_id,
                'is_active': is_active
            }

            # Add metadata if provided
            if metadata:
                payload['metadata'] = metadata

            # Upsert point
            points = [{
                'id': item_id,
                'vector': embedding,
                'payload': payload
            }]

            with self.client:
                operation_id = self.client.upsert_points(self.collection_name, points)

            if operation_id:
                logger.debug(f"Upserted vector: {item_id} ({item_type})")
                return True
            else:
                logger.error(f"Failed to upsert vector: {item_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to upsert vector: {e}")
            return False

    async def search_vectors(
        self,
        query_embedding: List[float],
        item_type: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search vectors by similarity

        Args:
            query_embedding: Query vector
            item_type: Filter by type ('tool', 'prompt', 'resource')
            limit: Maximum results to return
            score_threshold: Minimum similarity score

        Returns:
            List of search results with scores and metadata
        """
        try:
            logger.info(f"🔎 [VectorRepo] Starting vector search...")
            logger.info(f"   Collection: {self.collection_name}")
            logger.info(f"   Type filter: {item_type}")
            logger.info(f"   Limit: {limit}, Threshold: {score_threshold}")

            # Validate vector dimension
            if len(query_embedding) != self.vector_dimension:
                logger.error(f"❌ [VectorRepo] Dimension mismatch: expected {self.vector_dimension}, got {len(query_embedding)}")
                return []
            logger.info(f"✅ [VectorRepo] Vector dimension validated: {self.vector_dimension}D")

            # Build filter conditions
            filter_conditions = None

            # Add type filter if specified
            if item_type:
                filter_conditions = {
                    'must': [
                        {'field': 'type', 'match': {'keyword': item_type}}
                    ]
                }
                logger.info(f"🔧 [VectorRepo] Applied type filter: {item_type}")

            # Perform search
            logger.info(f"🔌 [VectorRepo] Connecting to Qdrant...")
            try:
                with self.client:
                    logger.info(f"📡 [VectorRepo] Sending search request to Qdrant...")
                    results = self.client.search_with_filter(
                        self.collection_name,
                        query_embedding,
                        filter_conditions=filter_conditions,
                        limit=limit,
                        with_payload=True,
                        with_vectors=False
                    )
                    logger.info(f"✅ [VectorRepo] Qdrant responded with {len(results) if results else 0} results")
            except Exception as e:
                logger.error(f"❌ [VectorRepo] Qdrant search request failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return []

            # Filter by score threshold and format results
            if results:
                all_scores = [r.get('score', 0) for r in results]
                logger.info(f"📊 [VectorRepo] Score distribution:")
                logger.info(f"   All scores: {all_scores}")
                logger.info(f"   Max: {max(all_scores):.4f}, Min: {min(all_scores):.4f}, Avg: {sum(all_scores)/len(all_scores):.4f}")
                logger.info(f"   Threshold: {score_threshold}")
            else:
                logger.warning(f"⚠️  [VectorRepo] Qdrant returned empty results!")
                return []

            search_results = []
            filtered_count = 0
            for idx, result in enumerate(results):
                score = result.get('score', 0.0)
                payload = result.get('payload', {})
                name = payload.get('name', 'unknown')

                if score >= score_threshold:
                    logger.debug(f"   ✅ [{idx}] {name}: score={score:.4f} (PASS)")
                    payload = result.get('payload', {})

                    search_results.append({
                        'id': str(result.get('id')),
                        'type': payload.get('type'),
                        'name': payload.get('name'),
                        'description': payload.get('description'),
                        'db_id': payload.get('db_id'),
                        'score': score,
                        'metadata': payload.get('metadata', {})
                    })
                else:
                    logger.debug(f"   ❌ [{idx}] {name}: score={score:.4f} < {score_threshold} (FILTERED)")
                    filtered_count += 1

            logger.info(f"✅ [VectorRepo] Results after filtering: {len(search_results)} passed, {filtered_count} filtered")
            return search_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def delete_vector(self, item_id: str) -> bool:
        """
        Delete a vector by ID

        Args:
            item_id: Vector identifier

        Returns:
            Success status
        """
        try:
            with self.client:
                operation_id = self.client.delete_points(self.collection_name, [item_id])

            if operation_id:
                logger.info(f"Deleted vector: {item_id}")
                return True
            else:
                logger.error(f"Failed to delete vector: {item_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete vector: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics

        Returns:
            Statistics dictionary
        """
        try:
            with self.client:
                info = self.client.get_collection_info(self.collection_name)

            if not info:
                return {'error': 'Failed to get collection info'}

            return {
                'collection': self.collection_name,
                'total_points': info.get('points_count', 0),
                'vector_dimension': self.vector_dimension,
                'distance_metric': self.distance_metric,
                'status': info.get('status', 'unknown')
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'error': str(e)}

    async def get_all_by_type(self, item_type: str) -> List[Dict[str, Any]]:
        """
        Get all vectors of a specific type from Qdrant

        Args:
            item_type: Type to filter ('tool', 'prompt', 'resource')

        Returns:
            List of vector metadata
        """
        try:
            # Build filter conditions for isa_common QdrantClient
            filter_conditions = {
                'must': [
                    {'field': 'type', 'match': {'keyword': item_type}}
                ]
            }

            # Scroll through all points of this type
            items = []
            offset_id = None

            while True:
                with self.client:
                    result = self.client.scroll(
                        collection_name=self.collection_name,
                        filter_conditions=filter_conditions,
                        limit=1000,  # Page size
                        offset_id=offset_id,
                        with_payload=True,
                        with_vectors=False
                    )

                if not result or 'points' not in result:
                    break

                points = result['points']
                if not points:
                    break

                # Extract metadata from points
                for point in points:
                    items.append({
                        'id': point['id'],
                        'name': point['payload'].get('name'),
                        'description': point['payload'].get('description', ''),
                        'type': point['payload'].get('type'),
                        'db_id': point['payload'].get('db_id'),
                        'is_active': point['payload'].get('is_active'),
                        'metadata': point['payload'].get('metadata', {})
                    })

                # Check for next page
                offset_id = result.get('next_offset')
                if not offset_id:
                    break

            logger.debug(f"Retrieved {len(items)} items of type '{item_type}' from Qdrant")
            return items

        except Exception as e:
            logger.error(f"Failed to get items by type '{item_type}': {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def delete_multiple_vectors(self, item_ids: List[int]) -> int:
        """
        Delete multiple vectors by IDs

        Args:
            item_ids: List of vector identifiers

        Returns:
            Number of successfully deleted vectors
        """
        if not item_ids:
            return 0

        try:
            with self.client:
                operation_id = self.client.delete_points(
                    self.collection_name,
                    item_ids
                )

            if operation_id:
                logger.info(f"Deleted {len(item_ids)} vectors")
                return len(item_ids)
            else:
                logger.error(f"Failed to delete vectors")
                return 0

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return 0

    async def clear_collection(self) -> bool:
        """
        Clear all vectors from collection (for testing/reset)

        Returns:
            Success status
        """
        try:
            # Delete and recreate collection
            with self.client:
                self.client.delete_collection(self.collection_name)
                self.client.create_collection(
                    self.collection_name,
                    self.vector_dimension,
                    distance=self.distance_metric
                )
            await self._create_indexes()

            logger.info(f"Cleared collection: {self.collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
