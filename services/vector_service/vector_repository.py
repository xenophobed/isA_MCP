"""
Vector Repository - Qdrant vector database operations
Handles all vector storage and retrieval for MCP search
"""

import logging
from typing import Any, Dict, List, Optional

from core.config.infra_config import InfraConfig
from isa_common import AsyncQdrantClient

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

    # Type offsets to ensure unique Qdrant point IDs across different item types
    # Each type gets a 1M range to prevent ID collisions
    TYPE_OFFSETS = {
        "tool": 0,  # IDs 0 - 999,999
        "prompt": 1_000_000,  # IDs 1,000,000 - 1,999,999
        "resource": 2_000_000,  # IDs 2,000,000 - 2,999,999
    }

    def _compute_point_id(self, item_type: str, db_id: int) -> int:
        """Compute unique Qdrant point ID from type and PostgreSQL ID."""
        offset = self.TYPE_OFFSETS.get(item_type, 0)
        return offset + db_id

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """Initialize vector repository"""
        self.collection_name = "mcp_unified_search"
        self.vector_dimension = 1536  # text-embedding-3-small
        self.distance_metric = "Cosine"

        # Load config from environment
        infra_config = InfraConfig.from_env()

        # Use provided host/port or fall back to config
        host = host or infra_config.qdrant_grpc_host
        port = port or infra_config.qdrant_grpc_port

        # Initialize Qdrant client
        try:
            self.client = AsyncQdrantClient(host=host, port=port, user_id="mcp-vector-service")
            logger.debug(f"Connected to Qdrant at {host}:{port}")
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
            collections = await self.client.list_collections()

            if self.collection_name not in collections:
                # Create collection
                await self.client.create_collection(
                    self.collection_name,
                    self.vector_dimension,
                    distance=self.distance_metric,
                )
                logger.debug(f"Created collection '{self.collection_name}'")

                # Create field indexes
                await self._create_indexes()
            else:
                logger.debug(f"Collection '{self.collection_name}' already exists")

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    async def _create_indexes(self):
        """Create field indexes for filtering"""
        try:
            # Index for type filtering (tool/prompt/resource)
            await self.client.create_field_index(self.collection_name, "type", "keyword")

            # Index for active status filtering
            await self.client.create_field_index(self.collection_name, "is_active", "keyword")

            # Multi-tenant indexes
            await self.client.create_field_index(self.collection_name, "org_id", "keyword")
            await self.client.create_field_index(self.collection_name, "is_global", "keyword")

            logger.info("Created field indexes for filtering")

        except Exception as e:
            logger.warning(f"Index creation failed (may already exist): {e}")

    async def upsert_vector(
        self,
        item_type: str,
        name: str,
        description: str,
        embedding: List[float],
        db_id: int,
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        item_id: Optional[int] = None,  # Deprecated: point_id computed from type+db_id
    ) -> bool:
        """
        Insert or update a vector

        Args:
            item_type: Type of item ('tool', 'prompt', 'resource')
            name: Item name
            description: Item description
            embedding: Vector embedding (1536 dimensions)
            db_id: PostgreSQL database ID
            is_active: Whether item is active
            metadata: Additional metadata
            item_id: Deprecated - ignored, point_id is computed from item_type + db_id

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
            payload = {
                "type": item_type,
                "name": name,
                "description": description,
                "db_id": db_id,
                "is_active": is_active,
            }

            # Add metadata if provided
            if metadata:
                # Promote org_id and is_global to top-level payload for Qdrant filtering
                if "org_id" in metadata:
                    payload["org_id"] = metadata.pop("org_id")
                if "is_global" in metadata:
                    payload["is_global"] = metadata.pop("is_global")
                payload["metadata"] = metadata

            # Compute unique point ID using type offset to prevent collisions
            point_id = self._compute_point_id(item_type, db_id)

            # Upsert point
            points = [{"id": point_id, "vector": embedding, "payload": payload}]

            logger.debug(
                f"🔧 [VectorRepo] Upserting point: ID={point_id} (db_id={db_id}), type={item_type}, name={name}"
            )
            logger.debug(f"   Payload keys: {list(payload.keys())}")
            logger.debug(f"   Vector dimension: {len(embedding)}")

            operation_id = await self.client.upsert_points(self.collection_name, points)

            logger.debug(f"   Qdrant operation_id: {operation_id}")

            if operation_id:
                logger.debug(
                    f"✅ [VectorRepo] Upserted vector: point_id={point_id} db_id={db_id} ({item_type}) - operation_id: {operation_id}"
                )
                return True
            else:
                logger.error(
                    f"❌ [VectorRepo] Failed to upsert vector: point_id={point_id} db_id={db_id} ({item_type}) - Qdrant returned None"
                )
                logger.error(
                    f"   Point data: point_id={point_id}, db_id={db_id}, type={item_type}, name={name}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ [VectorRepo] Exception during upsert: {e}")
            logger.error(f"   Point data: db_id={db_id}, type={item_type}, name={name}")
            import traceback

            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False

    async def upsert_tool(
        self,
        tool_id: int,
        name: str,
        description: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Convenience method to upsert a tool vector.

        Used by ToolAggregator to index external tools.

        Args:
            tool_id: PostgreSQL tool ID
            name: Tool name (namespaced)
            description: Tool description
            embedding: Vector embedding
            metadata: Additional metadata (source_server_id, is_external, etc.)

        Returns:
            Success status
        """
        return await self.upsert_vector(
            item_type="tool",
            name=name,
            description=description,
            embedding=embedding,
            db_id=tool_id,
            is_active=True,
            metadata=metadata,
        )

    async def update_tool_skills(
        self,
        tool_id: int,
        skill_ids: List[str],
        primary_skill_id: Optional[str] = None,
    ) -> bool:
        """
        Update tool skills in Qdrant payload.

        Called after skill classification completes.

        Args:
            tool_id: PostgreSQL tool ID
            skill_ids: List of assigned skill IDs
            primary_skill_id: Primary skill assignment

        Returns:
            Success status
        """
        point_id = self._compute_point_id("tool", tool_id)
        return await self.update_payload(
            item_id=point_id,
            payload_updates={
                "skill_ids": skill_ids,
                "primary_skill_id": primary_skill_id,
                "is_classified": len(skill_ids) > 0,
            },
        )

    async def delete_tool(self, tool_id: int) -> bool:
        """
        Delete a tool vector by its PostgreSQL ID.

        Args:
            tool_id: PostgreSQL tool ID

        Returns:
            Success status
        """
        point_id = self._compute_point_id("tool", tool_id)
        return await self.delete_vector(point_id)

    async def search_vectors(
        self,
        query_embedding: List[float],
        item_type: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.5,
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
            # Note: Channel health checking is now handled automatically in
            # AsyncBaseGRPCClient._ensure_connected() - no manual reconnect needed
            # See BR-002 in isa_common/tests/contracts/grpc_client/logic_contract.md

            logger.info("🔎 [VectorRepo] Starting vector search...")
            logger.info(f"   Collection: {self.collection_name}")
            logger.info(f"   Type filter: {item_type}")
            logger.info(f"   Limit: {limit}, Threshold: {score_threshold}")

            # Validate vector dimension
            if len(query_embedding) != self.vector_dimension:
                logger.error(
                    f"❌ [VectorRepo] Dimension mismatch: expected {self.vector_dimension}, got {len(query_embedding)}"
                )
                return []
            logger.info(f"✅ [VectorRepo] Vector dimension validated: {self.vector_dimension}D")

            # Build filter conditions
            filter_conditions = None

            # Add type filter if specified
            if item_type:
                filter_conditions = {"must": [{"field": "type", "match": {"keyword": item_type}}]}
                logger.info(f"🔧 [VectorRepo] Applied type filter: {item_type}")

            # Perform search
            logger.info("🔌 [VectorRepo] Connecting to Qdrant...")
            try:
                logger.info("📡 [VectorRepo] Sending search request to Qdrant...")
                results = await self.client.search_with_filter(
                    self.collection_name,
                    query_embedding,
                    filter_conditions=filter_conditions,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False,
                )
                logger.info(
                    f"✅ [VectorRepo] Qdrant responded with {len(results) if results else 0} results"
                )
            except Exception as e:
                logger.error(f"❌ [VectorRepo] Qdrant search request failed: {e}")
                import traceback

                logger.error(traceback.format_exc())
                return []

            # Filter by score threshold and format results
            if results:
                all_scores = [r.get("score", 0) for r in results]
                logger.info("📊 [VectorRepo] Score distribution:")
                logger.info(f"   All scores: {all_scores}")
                logger.info(
                    f"   Max: {max(all_scores):.4f}, Min: {min(all_scores):.4f}, Avg: {sum(all_scores) / len(all_scores):.4f}"
                )
                logger.info(f"   Threshold: {score_threshold}")
            else:
                logger.warning("⚠️  [VectorRepo] Qdrant returned empty results!")
                return []

            search_results = []
            filtered_count = 0
            for idx, result in enumerate(results):
                score = result.get("score", 0.0)
                payload = result.get("payload", {})
                name = payload.get("name", "unknown")

                if score >= score_threshold:
                    logger.debug(f"   ✅ [{idx}] {name}: score={score:.4f} (PASS)")
                    payload = result.get("payload", {})

                    search_results.append(
                        {
                            "id": str(result.get("id")),
                            "type": payload.get("type"),
                            "name": payload.get("name"),
                            "description": payload.get("description"),
                            "db_id": payload.get("db_id"),
                            "score": score,
                            "metadata": payload.get("metadata", {}),
                        }
                    )
                else:
                    logger.debug(
                        f"   ❌ [{idx}] {name}: score={score:.4f} < {score_threshold} (FILTERED)"
                    )
                    filtered_count += 1

            logger.info(
                f"✅ [VectorRepo] Results after filtering: {len(search_results)} passed, {filtered_count} filtered"
            )
            return search_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def delete_vector(self, item_id: int) -> bool:
        """
        Delete a vector by ID

        Args:
            item_id: Vector identifier (integer point ID)

        Returns:
            Success status
        """
        try:
            # Ensure item_id is an integer for Qdrant
            point_id = int(item_id) if not isinstance(item_id, int) else item_id

            operation_id = await self.client.delete_points(self.collection_name, [point_id])

            if operation_id:
                logger.info(f"Deleted vector: {point_id}")
                return True
            else:
                logger.error(f"Failed to delete vector: {point_id}")
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
            info = await self.client.get_collection_info(self.collection_name)

            if not info:
                return {"error": "Failed to get collection info"}

            return {
                "collection": self.collection_name,
                "total_points": info.get("points_count", 0),
                "vector_dimension": self.vector_dimension,
                "distance_metric": self.distance_metric,
                "status": info.get("status", "unknown"),
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

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
            filter_conditions = {"must": [{"field": "type", "match": {"keyword": item_type}}]}

            # Scroll through all points of this type
            items = []
            offset_id = None

            while True:
                result = await self.client.scroll(
                    collection_name=self.collection_name,
                    filter_conditions=filter_conditions,
                    limit=1000,  # Page size
                    offset_id=offset_id,
                    with_payload=True,
                    with_vectors=False,
                )

                if not result or "points" not in result:
                    break

                points = result["points"]
                if not points:
                    break

                # Extract metadata from points
                for point in points:
                    items.append(
                        {
                            "id": point["id"],
                            "name": point["payload"].get("name"),
                            "description": point["payload"].get("description", ""),
                            "type": point["payload"].get("type"),
                            "db_id": point["payload"].get("db_id"),
                            "is_active": point["payload"].get("is_active"),
                            "metadata": point["payload"].get("metadata", {}),
                            "primary_skill_id": point["payload"].get("primary_skill_id"),
                            "skill_ids": point["payload"].get("skill_ids", []),
                        }
                    )

                # Check for next page
                offset_id = result.get("next_offset")
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
            operation_id = await self.client.delete_points(self.collection_name, item_ids)

            if operation_id:
                logger.info(f"Deleted {len(item_ids)} vectors")
                return len(item_ids)
            else:
                logger.error("Failed to delete vectors")
                return 0

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return 0

    async def update_payload(
        self,
        item_id: int,
        payload_updates: Dict[str, Any],
    ) -> bool:
        """
        Update specific payload fields for a vector.

        Used by BR-002 Tool Classification to add skill_ids and primary_skill_id
        to tool payloads after LLM classification.

        Args:
            item_id: Vector identifier (PostgreSQL ID)
            payload_updates: Dictionary of payload fields to update

        Returns:
            Success status
        """
        try:
            operation_id = await self.client.update_payload(
                collection_name=self.collection_name,
                ids=[item_id],
                payload=payload_updates,
            )

            if operation_id:
                logger.debug(f"Updated payload for vector: {item_id}")
                return True
            else:
                logger.error(f"Failed to update payload for vector: {item_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update payload: {e}")
            return False

    async def clear_collection(self) -> bool:
        """
        Clear all vectors from collection (for testing/reset)

        Returns:
            Success status
        """
        try:
            # Delete and recreate collection
            await self.client.delete_collection(self.collection_name)
            await self.client.create_collection(
                self.collection_name,
                self.vector_dimension,
                distance=self.distance_metric,
            )
            await self._create_indexes()

            logger.info(f"Cleared collection: {self.collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
