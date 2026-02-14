"""
Unit tests for vector repository overflow detection and retry logic.

Tests the reliability improvements in PR #31:
- Point ID overflow detection
- Qdrant retry logic with exponential backoff
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from services.vector_service.vector_repository import (
    VectorRepository,
    _retry_qdrant,
    _MAX_ITEMS_PER_TYPE,
    _OVERFLOW_WARNING_THRESHOLD,
)


class TestPointIDOverflow:
    """Test point ID overflow detection (#16)."""

    def test_overflow_at_max_items(self):
        """Point ID should raise ValueError at 1M items."""
        repo = VectorRepository(
            qdrant_client=MagicMock(),
            collection_name="test",
            embedding_dimension=1536,
        )

        # Should raise at exactly 1M
        with pytest.raises(ValueError, match="Point ID overflow.*exceeds max"):
            repo._compute_point_id("tool", _MAX_ITEMS_PER_TYPE)

        # Should raise above 1M
        with pytest.raises(ValueError, match="Point ID overflow"):
            repo._compute_point_id("tool", _MAX_ITEMS_PER_TYPE + 1)

    def test_no_overflow_below_max(self):
        """Point IDs below 1M should work fine."""
        repo = VectorRepository(
            qdrant_client=MagicMock(),
            collection_name="test",
            embedding_dimension=1536,
        )

        # Should work at 999,999
        point_id = repo._compute_point_id("tool", _MAX_ITEMS_PER_TYPE - 1)
        assert point_id == 999_999  # tool offset is 0

    def test_warning_at_threshold(self, caplog):
        """Should warn at 900K items (90% capacity)."""
        repo = VectorRepository(
            qdrant_client=MagicMock(),
            collection_name="test",
            embedding_dimension=1536,
        )

        with caplog.at_level("WARNING"):
            repo._compute_point_id("tool", _OVERFLOW_WARNING_THRESHOLD)

        assert "approaching limit" in caplog.text.lower()
        assert "900000" in caplog.text or "900,000" in caplog.text

    def test_offset_calculation(self):
        """Verify offset calculation for different types."""
        repo = VectorRepository(
            qdrant_client=MagicMock(),
            collection_name="test",
            embedding_dimension=1536,
        )

        # tool: offset 0
        assert repo._compute_point_id("tool", 42) == 42

        # prompt: offset 1M
        assert repo._compute_point_id("prompt", 42) == 1_000_042

        # resource: offset 2M
        assert repo._compute_point_id("resource", 42) == 2_000_042


class TestQdrantRetry:
    """Test Qdrant retry logic with exponential backoff (#16)."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Operation succeeding on first try should not retry."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await _retry_qdrant(success_func, "test operation")
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Should retry on transient failures with exponential backoff."""
        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient failure")
            return "success"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await _retry_qdrant(flaky_func, "test operation", max_retries=3)

        assert result == "success"
        assert call_count == 3
        # Check exponential backoff delays: 0.5s, 1.0s
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 0.5  # First retry delay
        assert mock_sleep.call_args_list[1][0][0] == 1.0  # Second retry delay

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Should raise last exception after all retries exhausted."""
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError(f"Failure {call_count}")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ConnectionError, match="Failure 3"):
                await _retry_qdrant(always_fails, "test operation", max_retries=3)

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_different_exceptions(self):
        """Should retry on any exception type."""
        call_count = 0

        async def multi_exception_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First failure")
            elif call_count == 2:
                raise RuntimeError("Second failure")
            return "success"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await _retry_qdrant(multi_exception_func, "test", max_retries=3)

        assert result == "success"
        assert call_count == 3


class TestVectorOperationsWithRetry:
    """Test that delete and upsert operations use retry logic."""

    @pytest.mark.asyncio
    async def test_delete_vector_retries_on_failure(self):
        """delete_vector should retry on Qdrant failures."""
        mock_client = AsyncMock()
        # Fail twice, then succeed
        mock_client.delete_points.side_effect = [
            ConnectionError("Fail 1"),
            ConnectionError("Fail 2"),
            "operation_id_123",
        ]

        repo = VectorRepository(
            qdrant_client=mock_client,
            collection_name="test",
            embedding_dimension=1536,
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await repo.delete_vector(42)

        assert result is True
        assert mock_client.delete_points.call_count == 3

    @pytest.mark.asyncio
    async def test_upsert_vector_retries_on_failure(self):
        """upsert_vector should retry on Qdrant failures."""
        mock_client = AsyncMock()
        # Fail once, then succeed
        mock_client.upsert_points.side_effect = [
            ConnectionError("Transient failure"),
            "operation_id_456",
        ]

        repo = VectorRepository(
            qdrant_client=mock_client,
            collection_name="test",
            embedding_dimension=1536,
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await repo.upsert_vector(
                item_id=42,
                item_type="tool",
                embedding=[0.1] * 1536,
                metadata={"name": "test_tool"},
            )

        assert result is True
        assert mock_client.upsert_points.call_count == 2
