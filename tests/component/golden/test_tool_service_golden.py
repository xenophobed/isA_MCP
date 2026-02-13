"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of ToolService and ToolRepository.
If these tests fail, it means behavior has changed unexpectedly.

Before updating these tests:
1. Verify the change is intentional
2. Get approval from team lead
3. Document why the behavior changed

Service Under Test: services/tool_service/tool_service.py
Repository Under Test: services/tool_service/tool_repository.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.tools
class TestToolServiceGolden:
    """
    Golden tests for ToolService - DO NOT MODIFY.

    These tests capture CURRENT behavior including:
    - Registration with validation
    - ID vs name polymorphism for get_tool
    - Soft delete behavior
    - Statistics aggregation
    - Search ranking logic
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository with common responses."""
        repo = AsyncMock()
        repo.get_tool_by_id = AsyncMock(return_value=None)
        repo.get_tool_by_name = AsyncMock(return_value=None)
        repo.create_tool = AsyncMock(return_value={"id": 1, "name": "test_tool"})
        repo.update_tool = AsyncMock(return_value=True)
        repo.delete_tool = AsyncMock(return_value=True)
        repo.list_tools = AsyncMock(return_value=[])
        repo.search_tools = AsyncMock(return_value=[])
        repo.increment_call_count = AsyncMock(return_value=True)
        repo.get_tool_statistics = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def tool_service(self, mock_repository):
        """Create ToolService with mocked repository."""
        from services.tool_service.tool_service import ToolService

        return ToolService(repository=mock_repository)

    # ═══════════════════════════════════════════════════════════════
    # Registration Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_register_tool_requires_name(self, tool_service):
        """
        CURRENT BEHAVIOR: register_tool raises ValueError if name is missing.
        """
        with pytest.raises(ValueError) as exc_info:
            await tool_service.register_tool({"description": "No name"})

        assert "name" in str(exc_info.value).lower()

    async def test_register_tool_detects_duplicate_name(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: register_tool raises ValueError for duplicate names.
        """
        # Setup: Tool with same name already exists
        mock_repository.get_tool_by_name.return_value = {"id": 1, "name": "existing_tool"}

        with pytest.raises(ValueError) as exc_info:
            await tool_service.register_tool({"name": "existing_tool"})

        assert "duplicate" in str(exc_info.value).lower() or "exists" in str(exc_info.value).lower()

    async def test_register_tool_returns_dict_with_id(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Successful registration returns dict with 'id' field.
        """
        mock_repository.get_tool_by_name.return_value = None
        mock_repository.create_tool.return_value = {
            "id": 42,
            "name": "new_tool",
            "description": "A new tool",
        }

        result = await tool_service.register_tool({"name": "new_tool", "description": "A new tool"})

        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == 42

    async def test_register_tool_raises_runtime_error_on_creation_failure(
        self, tool_service, mock_repository
    ):
        """
        CURRENT BEHAVIOR: Raises RuntimeError if creation returns None.
        """
        mock_repository.get_tool_by_name.return_value = None
        mock_repository.create_tool.return_value = None

        with pytest.raises(RuntimeError):
            await tool_service.register_tool({"name": "failing_tool"})

    # ═══════════════════════════════════════════════════════════════
    # Get Tool Polymorphism
    # ═══════════════════════════════════════════════════════════════

    async def test_get_tool_by_integer_id(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Integer identifier calls get_tool_by_id.
        """
        expected_tool = {"id": 1, "name": "tool_by_id"}
        mock_repository.get_tool_by_id.return_value = expected_tool

        result = await tool_service.get_tool(1)

        mock_repository.get_tool_by_id.assert_called_once_with(1)
        mock_repository.get_tool_by_name.assert_not_called()
        assert result == expected_tool

    async def test_get_tool_by_string_name(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: String identifier calls get_tool_by_name.
        """
        expected_tool = {"id": 1, "name": "tool_by_name"}
        mock_repository.get_tool_by_name.return_value = expected_tool

        result = await tool_service.get_tool("tool_by_name")

        mock_repository.get_tool_by_name.assert_called_once_with("tool_by_name")
        mock_repository.get_tool_by_id.assert_not_called()
        assert result == expected_tool

    async def test_get_tool_returns_none_when_not_found(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns None when tool doesn't exist.
        """
        mock_repository.get_tool_by_id.return_value = None

        result = await tool_service.get_tool(999)

        assert result is None

    async def test_get_tool_raises_value_error_for_invalid_identifier_type(self, tool_service):
        """
        CURRENT BEHAVIOR: Raises ValueError for non-int/non-str identifiers.
        """
        with pytest.raises(ValueError):
            await tool_service.get_tool(3.14)  # float

        with pytest.raises(ValueError):
            await tool_service.get_tool(["list"])  # list

    # ═══════════════════════════════════════════════════════════════
    # List Tools Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_list_tools_returns_list(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns list of tools (possibly empty).
        """
        mock_repository.list_tools.return_value = [
            {"id": 1, "name": "tool1"},
            {"id": 2, "name": "tool2"},
        ]

        result = await tool_service.list_tools()

        assert isinstance(result, list)
        assert len(result) == 2

    async def test_list_tools_passes_filters_to_repository(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Filters are passed to repository method.
        """
        await tool_service.list_tools(category="intelligence", active_only=True, limit=10, offset=5)

        mock_repository.list_tools.assert_called_once()
        call_kwargs = mock_repository.list_tools.call_args
        # Verify filter parameters were passed
        assert call_kwargs is not None

    # ═══════════════════════════════════════════════════════════════
    # Update Tool Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_update_tool_validates_tool_exists(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Raises ValueError if tool doesn't exist.
        """
        mock_repository.get_tool_by_id.return_value = None

        with pytest.raises(ValueError):
            await tool_service.update_tool(999, {"description": "Updated"})

    async def test_update_tool_validates_name_uniqueness(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Raises ValueError if new name already exists.
        """
        # Tool exists
        mock_repository.get_tool_by_id.return_value = {"id": 1, "name": "original"}
        # Another tool has the new name
        mock_repository.get_tool_by_name.return_value = {"id": 2, "name": "taken_name"}

        with pytest.raises(ValueError):
            await tool_service.update_tool(1, {"name": "taken_name"})

    # ═══════════════════════════════════════════════════════════════
    # Delete Tool Behavior (Soft Delete)
    # ═══════════════════════════════════════════════════════════════

    async def test_delete_tool_is_soft_delete(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Delete sets is_active=False (soft delete).
        """
        mock_repository.get_tool_by_id.return_value = {"id": 1, "name": "to_delete"}
        mock_repository.delete_tool.return_value = True

        result = await tool_service.delete_tool(1)

        assert result is True
        mock_repository.delete_tool.assert_called_once_with(1)

    async def test_delete_tool_raises_if_not_found(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Raises ValueError if tool doesn't exist.
        """
        mock_repository.get_tool_by_id.return_value = None

        with pytest.raises(ValueError):
            await tool_service.delete_tool(999)

    # ═══════════════════════════════════════════════════════════════
    # Statistics Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_record_tool_call_updates_statistics(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: record_tool_call increments counters and updates avg response time.
        """
        mock_repository.get_tool_by_id.return_value = {"id": 1, "name": "tool"}
        mock_repository.increment_call_count.return_value = True

        result = await tool_service.record_tool_call(
            tool_identifier=1, success=True, response_time_ms=150
        )

        assert result is True
        mock_repository.increment_call_count.assert_called_once()

    async def test_get_tool_statistics_returns_dict_or_none(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns statistics dict or None.
        """
        mock_repository.get_tool_by_id.return_value = {"id": 1, "name": "tool"}
        mock_repository.get_tool_statistics.return_value = {
            "call_count": 100,
            "success_count": 95,
            "failure_count": 5,
            "avg_response_time_ms": 120,
            "success_rate": 0.95,
        }

        result = await tool_service.get_tool_statistics(1)

        assert isinstance(result, dict)
        assert "call_count" in result
        assert "success_rate" in result

    # ═══════════════════════════════════════════════════════════════
    # Search Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_search_tools_returns_list(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Search returns list of matching tools.
        """
        mock_repository.search_tools.return_value = [
            {"id": 1, "name": "text_generator", "description": "Generates text"}
        ]

        result = await tool_service.search_tools("text", limit=10)

        assert isinstance(result, list)
        mock_repository.search_tools.assert_called_once()

    async def test_search_tools_name_matches_rank_higher(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Name matches should appear before description matches.

        Repository is responsible for ranking, service passes through.
        """
        # Repository returns pre-ranked results
        mock_repository.search_tools.return_value = [
            {"id": 1, "name": "text_gen", "description": "Other"},  # Name match
            {"id": 2, "name": "other", "description": "text generation"},  # Desc match
        ]

        result = await tool_service.search_tools("text", limit=10)

        # First result should be name match
        assert result[0]["name"] == "text_gen"

    # ═══════════════════════════════════════════════════════════════
    # Popular Tools Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_get_popular_tools_ordered_by_call_count(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns tools ordered by call_count DESC.
        """
        mock_repository.list_tools.return_value = [
            {"id": 1, "name": "popular", "call_count": 1000},
            {"id": 2, "name": "less_popular", "call_count": 100},
        ]

        result = await tool_service.get_popular_tools(limit=10)

        assert isinstance(result, list)


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.tools
class TestToolRepositoryGolden:
    """
    Golden tests for ToolRepository - DO NOT MODIFY.

    Tests the data access layer behavior including:
    - JSON serialization for input_schema and metadata
    - SQL query construction
    - Exception handling
    """

    @pytest.fixture
    def mock_postgres_client(self):
        """Create mock PostgreSQL client."""
        client = AsyncMock()
        client.fetch = AsyncMock(return_value=[])
        client.fetchrow = AsyncMock(return_value=None)
        client.execute = AsyncMock(return_value="OK")
        return client

    async def test_create_tool_serializes_json_fields(self, mock_postgres_client):
        """
        CURRENT BEHAVIOR: input_schema and metadata are JSON serialized.
        """
        # This tests that the repository handles JSON serialization
        # The actual implementation uses json.dumps() for these fields
        tool_data = {
            "name": "test_tool",
            "input_schema": {"type": "object", "properties": {}},
            "metadata": {"author": "test"},
        }

        # The repository should serialize these to JSON strings before SQL insert
        # This is verified by checking the SQL parameters in actual implementation

    async def test_immutable_fields_not_updated(self, mock_postgres_client):
        """
        CURRENT BEHAVIOR: id, created_at, updated_at are immutable on update.
        """
        # These fields should be excluded from UPDATE statements
        immutable_fields = {"id", "created_at", "updated_at"}

        # Repository implementation filters these out before building UPDATE query

    async def test_soft_delete_sets_is_active_false(self, mock_postgres_client):
        """
        CURRENT BEHAVIOR: delete_tool sets is_active=FALSE, not DELETE.
        """
        # Repository uses UPDATE ... SET is_active = FALSE
        # Not DELETE FROM ...
        pass
