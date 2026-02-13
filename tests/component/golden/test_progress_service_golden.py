"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of ProgressManager.
If these tests fail, it means behavior has changed unexpectedly.

Service Under Test: services/progress_service/progress_manager.py
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.mark.golden
@pytest.mark.component
class TestProgressManagerGolden:
    """
    Golden tests for ProgressManager - DO NOT MODIFY.

    Key characteristics:
    - Uses Redis for storage with in-memory fallback
    - Progress values clamped to [0, 100]
    - Cancelled operations skip updates
    - Timestamps in ISO format
    - Separate result storage for large data
    """

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        client = AsyncMock()
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.setex = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=True)
        client.keys = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def progress_manager(self, mock_redis_client):
        """Create ProgressManager with mocked Redis - in-memory mode."""
        with patch("services.progress_service.progress_manager.REDIS_CLIENT_AVAILABLE", False):
            from services.progress_service.progress_manager import ProgressManager

            manager = ProgressManager()
            # Force in-memory mode for testing
            manager._use_redis = False
            manager._memory_store = {}
            return manager

    # ═══════════════════════════════════════════════════════════════
    # Operation Lifecycle - In-Memory Mode
    # ═══════════════════════════════════════════════════════════════

    async def test_start_operation_creates_progress_data(self, progress_manager):
        """
        CURRENT BEHAVIOR: start_operation creates ProgressData with status=RUNNING, progress=0.
        """
        result = await progress_manager.start_operation(
            operation_id="op_123", metadata={"task": "processing"}
        )

        assert result is not None
        assert result.operation_id == "op_123"
        assert result.status.value == "running"
        assert result.progress == 0
        assert result.started_at is not None

    async def test_complete_operation_sets_status_completed(self, progress_manager):
        """
        CURRENT BEHAVIOR: complete_operation sets status=COMPLETED, progress=100.
        """
        # First create operation
        await progress_manager.start_operation("op_123", {})

        # Then complete it
        result = await progress_manager.complete_operation(
            operation_id="op_123", result={"output": "success"}, message="Done"
        )

        assert result is not None
        assert result.status.value == "completed"
        assert result.progress == 100
        assert result.completed_at is not None

    async def test_fail_operation_sets_status_failed(self, progress_manager):
        """
        CURRENT BEHAVIOR: fail_operation sets status=FAILED with error message.
        """
        # First create operation
        await progress_manager.start_operation("op_123", {})

        result = await progress_manager.fail_operation(
            operation_id="op_123", error="Something went wrong", message="Failed"
        )

        assert result is not None
        assert result.status.value == "failed"
        assert result.error == "Something went wrong"
        assert result.completed_at is not None

    async def test_cancel_operation_sets_status_cancelled(self, progress_manager):
        """
        CURRENT BEHAVIOR: cancel_operation sets status=CANCELLED.
        """
        await progress_manager.start_operation("op_123", {})

        result = await progress_manager.cancel_operation("op_123")

        assert result is not None
        assert result.status.value == "cancelled"

    # ═══════════════════════════════════════════════════════════════
    # Progress Update Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_update_progress_clamps_to_100(self, progress_manager):
        """
        CURRENT BEHAVIOR: Progress values > 100 are clamped to 100.
        """
        await progress_manager.start_operation("op_123", {})

        result = await progress_manager.update_progress(
            operation_id="op_123", progress=150, message="Almost done"  # Over 100
        )

        assert result.progress == 100  # Clamped

    async def test_update_progress_clamps_to_0(self, progress_manager):
        """
        CURRENT BEHAVIOR: Progress values < 0 are clamped to 0.
        """
        await progress_manager.start_operation("op_123", {})

        result = await progress_manager.update_progress(
            operation_id="op_123", progress=-10, message="Resetting"  # Below 0
        )

        assert result.progress == 0  # Clamped

    # ═══════════════════════════════════════════════════════════════
    # Timestamp Management
    # ═══════════════════════════════════════════════════════════════

    async def test_timestamps_in_iso_format(self, progress_manager):
        """
        CURRENT BEHAVIOR: Timestamps are stored in ISO 8601 format.
        """
        result = await progress_manager.start_operation("op_123", {})

        # started_at should be ISO format string
        assert result.started_at is not None
        # Verify format: YYYY-MM-DDTHH:MM:SS...
        if isinstance(result.started_at, str):
            datetime.fromisoformat(result.started_at.replace("Z", "+00:00"))

    # ═══════════════════════════════════════════════════════════════
    # Get Progress / Result
    # ═══════════════════════════════════════════════════════════════

    async def test_get_progress_returns_none_if_not_found(self, progress_manager):
        """
        CURRENT BEHAVIOR: get_progress returns None for non-existent operation.
        """
        result = await progress_manager.get_progress("nonexistent")
        assert result is None

    async def test_get_progress_returns_data_if_exists(self, progress_manager):
        """
        CURRENT BEHAVIOR: get_progress returns ProgressData for existing operation.
        """
        await progress_manager.start_operation("op_123", {"task": "test"})

        result = await progress_manager.get_progress("op_123")

        assert result is not None
        assert result.operation_id == "op_123"

    # ═══════════════════════════════════════════════════════════════
    # List Operations
    # ═══════════════════════════════════════════════════════════════

    async def test_list_operations_returns_list(self, progress_manager):
        """
        CURRENT BEHAVIOR: list_operations returns a list.
        """
        await progress_manager.start_operation("op_1", {})
        await progress_manager.start_operation("op_2", {})

        result = await progress_manager.list_operations(limit=10)

        assert isinstance(result, list)

    # ═══════════════════════════════════════════════════════════════
    # In-Memory Fallback
    # ═══════════════════════════════════════════════════════════════

    async def test_fallback_to_memory_when_redis_unavailable(self):
        """
        CURRENT BEHAVIOR: Falls back to in-memory dict when Redis is unavailable.
        """
        with patch("services.progress_service.progress_manager.REDIS_CLIENT_AVAILABLE", False):
            from services.progress_service.progress_manager import ProgressManager

            manager = ProgressManager()
            manager._use_redis = False  # Force in-memory mode

            result = await manager.start_operation("op_123", {})

            assert result is not None
            assert result.operation_id == "op_123"


@pytest.mark.golden
@pytest.mark.component
class TestProgressDataGolden:
    """
    Golden tests for ProgressData dataclass - DO NOT MODIFY.
    """

    def test_progress_data_structure(self):
        """
        CURRENT BEHAVIOR: ProgressData has specific fields.
        """
        from services.progress_service.progress_manager import ProgressData, OperationStatus

        data = ProgressData(
            operation_id="op_123",
            status=OperationStatus.RUNNING,
            progress=50.0,
            total=100,
            current=50,
            message="Processing",
            started_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:01:00",
            completed_at=None,
            metadata={"task": "import"},
            error=None,
        )

        assert data.operation_id == "op_123"
        assert data.status == OperationStatus.RUNNING
        assert data.progress == 50.0
        assert data.total == 100
        assert data.current == 50
        assert data.message == "Processing"
        assert data.error is None

    def test_progress_data_to_dict(self):
        """
        CURRENT BEHAVIOR: to_dict() converts status to string value.
        """
        from services.progress_service.progress_manager import ProgressData, OperationStatus

        data = ProgressData(operation_id="op_123", status=OperationStatus.RUNNING, progress=50.0)

        result = data.to_dict()

        assert isinstance(result, dict)
        assert result["status"] == "running"  # String value, not enum


@pytest.mark.golden
@pytest.mark.component
class TestOperationStatusGolden:
    """
    Golden tests for OperationStatus enum - DO NOT MODIFY.
    """

    def test_operation_status_values(self):
        """
        CURRENT BEHAVIOR: OperationStatus has specific values.
        """
        from services.progress_service.progress_manager import OperationStatus

        assert OperationStatus.PENDING.value == "pending"
        assert OperationStatus.RUNNING.value == "running"
        assert OperationStatus.COMPLETED.value == "completed"
        assert OperationStatus.FAILED.value == "failed"
        assert OperationStatus.CANCELLED.value == "cancelled"

    def test_operation_status_is_string_enum(self):
        """
        CURRENT BEHAVIOR: OperationStatus inherits from str, Enum.
        """
        from services.progress_service.progress_manager import OperationStatus

        status = OperationStatus.RUNNING
        assert isinstance(status, str)
        assert status == "running"
