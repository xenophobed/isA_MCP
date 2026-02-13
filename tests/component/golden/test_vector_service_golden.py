"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of VectorRepository.
If these tests fail, it means behavior has changed unexpectedly.

Service Under Test: services/vector_service/vector_repository.py
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.search
class TestVectorRepositoryGolden:
    """
    Golden tests for VectorRepository - DO NOT MODIFY.

    Key characteristics:
    - Uses AsyncQdrantClient (gRPC) from isa_common
    - Collection: mcp_unified_search
    - Vector dimension: 1536 (text-embedding-3-small)
    - Distance metric: Cosine
    """

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create mock Qdrant client with all required methods."""
        client = AsyncMock()
        # Collection management
        client.list_collections = AsyncMock(return_value=[])
        client.create_collection = AsyncMock(return_value=True)
        client.delete_collection = AsyncMock(return_value=True)
        client.get_collection_info = AsyncMock(
            return_value={"points_count": 100, "status": "green"}
        )
        client.create_field_index = AsyncMock(return_value=True)

        # Point operations
        client.upsert_points = AsyncMock(return_value="operation_123")
        client.delete_points = AsyncMock(return_value="operation_456")
        client.search_with_filter = AsyncMock(return_value=[])
        client.scroll = AsyncMock(return_value={"points": [], "next_offset": None})

        return client

    @pytest.fixture
    def vector_repository(self, mock_qdrant_client):
        """Create VectorRepository with mocked Qdrant client."""
        with patch(
            "services.vector_service.vector_repository.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ):
            from services.vector_service.vector_repository import VectorRepository

            repo = VectorRepository(host="localhost", port=6334)
            return repo

    # ═══════════════════════════════════════════════════════════════
    # Collection Management
    # ═══════════════════════════════════════════════════════════════

    async def test_ensure_collection_creates_if_not_exists(
        self, vector_repository, mock_qdrant_client
    ):
        """
        CURRENT BEHAVIOR: ensure_collection creates collection if it doesn't exist.
        """
        mock_qdrant_client.list_collections.return_value = []

        await vector_repository.ensure_collection()

        mock_qdrant_client.create_collection.assert_called_once()

    async def test_ensure_collection_idempotent(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: ensure_collection is idempotent (safe to call multiple times).
        """
        # Collection already exists
        mock_qdrant_client.list_collections.return_value = ["mcp_unified_search"]

        await vector_repository.ensure_collection()

        mock_qdrant_client.create_collection.assert_not_called()

    # ═══════════════════════════════════════════════════════════════
    # Vector Dimension Validation
    # ═══════════════════════════════════════════════════════════════

    async def test_upsert_vector_validates_dimension_1536(
        self, vector_repository, mock_qdrant_client
    ):
        """
        CURRENT BEHAVIOR: upsert_vector validates vector dimension is exactly 1536.
        """
        valid_vector = [0.1] * 1536
        mock_qdrant_client.upsert_points.return_value = "operation_123"

        result = await vector_repository.upsert_vector(
            item_id=1,
            item_type="tool",
            name="test_tool",
            description="Test description",
            embedding=valid_vector,
            db_id=1,
            is_active=True,
            metadata={},
        )

        assert result is True
        mock_qdrant_client.upsert_points.assert_called_once()

    async def test_upsert_vector_rejects_wrong_dimension(
        self, vector_repository, mock_qdrant_client
    ):
        """
        CURRENT BEHAVIOR: upsert_vector returns False for wrong dimension vectors.
        """
        invalid_vector = [0.1] * 512  # Wrong size

        result = await vector_repository.upsert_vector(
            item_id=1,
            item_type="tool",
            name="test_tool",
            description="Test description",
            embedding=invalid_vector,
            db_id=1,
            is_active=True,
            metadata={},
        )

        assert result is False
        mock_qdrant_client.upsert_points.assert_not_called()

    # ═══════════════════════════════════════════════════════════════
    # Payload Structure
    # ═══════════════════════════════════════════════════════════════

    async def test_upsert_vector_payload_structure(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: Payload includes type, name, description, db_id, is_active, metadata.
        """
        mock_qdrant_client.upsert_points.return_value = "operation_123"

        await vector_repository.upsert_vector(
            item_id=1,
            item_type="tool",
            name="test_tool",
            description="Test description",
            embedding=[0.1] * 1536,
            db_id=42,
            is_active=True,
            metadata={"category": "intelligence"},
        )

        mock_qdrant_client.upsert_points.assert_called_once()
        call_args = mock_qdrant_client.upsert_points.call_args

        # Verify collection name
        assert call_args[0][0] == "mcp_unified_search"

        # Verify point structure
        points = call_args[0][1]
        assert len(points) == 1
        point = points[0]
        assert point["id"] == 42  # _compute_point_id("tool", 42) = TYPE_OFFSETS["tool"](0) + 42
        assert "vector" in point
        assert len(point["vector"]) == 1536

        # Verify payload fields
        payload = point["payload"]
        assert payload["type"] == "tool"
        assert payload["name"] == "test_tool"
        assert payload["description"] == "Test description"
        assert payload["db_id"] == 42
        assert payload["is_active"] is True
        assert payload["metadata"] == {"category": "intelligence"}

    # ═══════════════════════════════════════════════════════════════
    # Search Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_search_vectors_with_type_filter(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: search_vectors filters by item_type using must conditions.
        """
        mock_qdrant_client.search_with_filter.return_value = [
            {
                "id": "1",
                "score": 0.95,
                "payload": {"type": "tool", "name": "test", "description": "desc", "db_id": 1},
            }
        ]

        result = await vector_repository.search_vectors(
            query_embedding=[0.1] * 1536, item_type="tool", limit=10, score_threshold=0.5
        )

        assert isinstance(result, list)
        assert len(result) == 1
        mock_qdrant_client.search_with_filter.assert_called_once()

        # Verify search was called with filter_conditions containing type filter
        call_kwargs = mock_qdrant_client.search_with_filter.call_args[1]
        assert "filter_conditions" in call_kwargs
        assert call_kwargs["filter_conditions"]["must"][0]["field"] == "type"

    async def test_search_vectors_applies_score_threshold(
        self, vector_repository, mock_qdrant_client
    ):
        """
        CURRENT BEHAVIOR: Results below score_threshold are filtered out.
        """
        mock_qdrant_client.search_with_filter.return_value = [
            {"id": "1", "score": 0.9, "payload": {"type": "tool", "name": "high", "db_id": 1}},
            {"id": "2", "score": 0.4, "payload": {"type": "tool", "name": "low", "db_id": 2}},
        ]

        result = await vector_repository.search_vectors(
            query_embedding=[0.1] * 1536, item_type="tool", limit=10, score_threshold=0.5
        )

        # Only high score result should be returned
        assert len(result) == 1
        assert result[0]["name"] == "high"
        assert result[0]["score"] == 0.9

    async def test_search_vectors_returns_structured_results(
        self, vector_repository, mock_qdrant_client
    ):
        """
        CURRENT BEHAVIOR: Returns list of dicts with id, type, name, description, db_id, score, metadata.
        """
        mock_qdrant_client.search_with_filter.return_value = [
            {
                "id": "1",
                "score": 0.95,
                "payload": {
                    "type": "tool",
                    "name": "test_tool",
                    "description": "A test tool",
                    "db_id": 42,
                    "is_active": True,
                    "metadata": {"category": "utility"},
                },
            }
        ]

        result = await vector_repository.search_vectors(
            query_embedding=[0.1] * 1536, limit=10, score_threshold=0.5
        )

        assert len(result) == 1
        item = result[0]
        assert item["id"] == "1"
        assert item["type"] == "tool"
        assert item["name"] == "test_tool"
        assert item["description"] == "A test tool"
        assert item["db_id"] == 42
        assert item["score"] == 0.95
        assert item["metadata"] == {"category": "utility"}

    async def test_search_vectors_rejects_wrong_dimension(
        self, vector_repository, mock_qdrant_client
    ):
        """
        CURRENT BEHAVIOR: Returns empty list for wrong dimension query vector.
        """
        result = await vector_repository.search_vectors(
            query_embedding=[0.1] * 512, limit=10, score_threshold=0.5  # Wrong dimension
        )

        assert result == []
        mock_qdrant_client.search_with_filter.assert_not_called()

    # ═══════════════════════════════════════════════════════════════
    # Delete Operations
    # ═══════════════════════════════════════════════════════════════

    async def test_delete_vector_by_id(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: delete_vector removes point by ID.
        """
        mock_qdrant_client.delete_points.return_value = "operation_456"

        result = await vector_repository.delete_vector("1")

        assert result is True
        mock_qdrant_client.delete_points.assert_called_once_with("mcp_unified_search", [1])

    async def test_delete_vector_returns_false_on_failure(
        self, vector_repository, mock_qdrant_client
    ):
        """
        CURRENT BEHAVIOR: delete_vector returns False when Qdrant returns None.
        """
        mock_qdrant_client.delete_points.return_value = None

        result = await vector_repository.delete_vector("1")

        assert result is False

    async def test_delete_multiple_vectors(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: delete_multiple_vectors batch deletes and returns count.
        """
        mock_qdrant_client.delete_points.return_value = "operation_789"

        result = await vector_repository.delete_multiple_vectors([1, 2, 3])

        assert result == 3
        mock_qdrant_client.delete_points.assert_called_once()

    async def test_delete_multiple_vectors_empty_list(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: delete_multiple_vectors returns 0 for empty list.
        """
        result = await vector_repository.delete_multiple_vectors([])

        assert result == 0
        mock_qdrant_client.delete_points.assert_not_called()

    # ═══════════════════════════════════════════════════════════════
    # Get All By Type
    # ═══════════════════════════════════════════════════════════════

    async def test_get_all_by_type_handles_pagination(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: get_all_by_type scrolls through all results with pagination.
        """
        # First scroll returns results and offset
        mock_qdrant_client.scroll.side_effect = [
            {
                "points": [{"id": "1", "payload": {"type": "tool", "name": "tool1", "db_id": 1}}],
                "next_offset": "offset_1",
            },
            {"points": [], "next_offset": None},
        ]

        result = await vector_repository.get_all_by_type("tool")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "tool1"

    async def test_get_all_by_type_empty_collection(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: Returns empty list for empty collection.
        """
        mock_qdrant_client.scroll.return_value = {"points": [], "next_offset": None}

        result = await vector_repository.get_all_by_type("tool")

        assert result == []

    # ═══════════════════════════════════════════════════════════════
    # Statistics
    # ═══════════════════════════════════════════════════════════════

    async def test_get_stats_returns_collection_info(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: get_stats returns collection, total_points, vector_dimension, distance_metric, status.
        """
        mock_qdrant_client.get_collection_info.return_value = {
            "points_count": 1000,
            "status": "green",
        }

        result = await vector_repository.get_stats()

        assert isinstance(result, dict)
        assert result["collection"] == "mcp_unified_search"
        assert result["total_points"] == 1000
        assert result["vector_dimension"] == 1536
        assert result["distance_metric"] == "Cosine"
        assert result["status"] == "green"

    async def test_get_stats_handles_error(self, vector_repository, mock_qdrant_client):
        """
        CURRENT BEHAVIOR: get_stats returns error dict on failure.
        """
        mock_qdrant_client.get_collection_info.return_value = None

        result = await vector_repository.get_stats()

        assert "error" in result

    # ═══════════════════════════════════════════════════════════════
    # Clear Collection
    # ═══════════════════════════════════════════════════════════════

    async def test_clear_collection_drops_and_recreates(
        self, vector_repository, mock_qdrant_client
    ):
        """
        CURRENT BEHAVIOR: clear_collection drops collection and recreates it.
        """
        mock_qdrant_client.delete_collection.return_value = True
        mock_qdrant_client.create_collection.return_value = True

        result = await vector_repository.clear_collection()

        assert result is True
        mock_qdrant_client.delete_collection.assert_called_once_with("mcp_unified_search")
        mock_qdrant_client.create_collection.assert_called_once()
