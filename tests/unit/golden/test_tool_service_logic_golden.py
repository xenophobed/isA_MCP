"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of the ToolService business logic.
If these tests fail, it means behavior has changed unexpectedly.

Service Under Test: services/tool_service/tool_service.py

Focus: Business logic validation and rules (NOT database operations)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.tools
class TestToolServiceValidationGolden:
    """
    Golden tests for ToolService validation rules - DO NOT MODIFY.

    Tests business logic:
    - Required field validation
    - Duplicate detection
    - Identifier type handling
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        repo = AsyncMock()
        repo.get_tool_by_id = AsyncMock(return_value=None)
        repo.get_tool_by_name = AsyncMock(return_value=None)
        repo.create_tool = AsyncMock(return_value={'id': 1, 'name': 'test_tool'})
        repo.list_tools = AsyncMock(return_value=[])
        repo.update_tool = AsyncMock(return_value=True)
        repo.delete_tool = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def tool_service(self, mock_repository):
        """Create ToolService with mocked repository."""
        from services.tool_service.tool_service import ToolService
        service = ToolService(repository=mock_repository)
        return service

    # ═══════════════════════════════════════════════════════════════
    # Registration Validation
    # ═══════════════════════════════════════════════════════════════

    async def test_register_tool_requires_name(self, tool_service):
        """
        CURRENT BEHAVIOR: Tool registration requires 'name' field.
        Raises ValueError if name is missing or empty.
        """
        with pytest.raises(ValueError) as exc_info:
            await tool_service.register_tool({})

        assert "name" in str(exc_info.value).lower()

    async def test_register_tool_requires_non_empty_name(self, tool_service):
        """
        CURRENT BEHAVIOR: Empty string name is rejected.
        """
        with pytest.raises(ValueError) as exc_info:
            await tool_service.register_tool({'name': ''})

        assert "name" in str(exc_info.value).lower()

    async def test_register_tool_rejects_duplicate_name(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Cannot register tool with existing name.
        """
        # Tool already exists
        mock_repository.get_tool_by_name.return_value = {'id': 1, 'name': 'existing_tool'}

        with pytest.raises(ValueError) as exc_info:
            await tool_service.register_tool({'name': 'existing_tool'})

        assert "already exists" in str(exc_info.value).lower()

    async def test_register_tool_checks_existing_before_create(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Checks for existing tool before creating.
        """
        mock_repository.get_tool_by_name.return_value = None
        mock_repository.create_tool.return_value = {'id': 1, 'name': 'new_tool'}

        await tool_service.register_tool({'name': 'new_tool'})

        # Should check existing first
        mock_repository.get_tool_by_name.assert_called_once_with('new_tool')
        mock_repository.create_tool.assert_called_once()

    async def test_register_tool_returns_created_tool(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns created tool data with id.
        """
        expected_tool = {'id': 42, 'name': 'my_tool', 'description': 'Test'}
        mock_repository.get_tool_by_name.return_value = None
        mock_repository.create_tool.return_value = expected_tool

        result = await tool_service.register_tool({'name': 'my_tool', 'description': 'Test'})

        assert result == expected_tool
        assert 'id' in result

    # ═══════════════════════════════════════════════════════════════
    # Identifier Resolution
    # ═══════════════════════════════════════════════════════════════

    async def test_get_tool_by_int_uses_id_lookup(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Integer identifier uses get_tool_by_id.
        """
        mock_repository.get_tool_by_id.return_value = {'id': 1, 'name': 'tool'}

        await tool_service.get_tool(1)

        mock_repository.get_tool_by_id.assert_called_once_with(1)
        mock_repository.get_tool_by_name.assert_not_called()

    async def test_get_tool_by_str_uses_name_lookup(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: String identifier uses get_tool_by_name.
        """
        mock_repository.get_tool_by_name.return_value = {'id': 1, 'name': 'my_tool'}

        await tool_service.get_tool('my_tool')

        mock_repository.get_tool_by_name.assert_called_once_with('my_tool')
        mock_repository.get_tool_by_id.assert_not_called()

    async def test_get_tool_rejects_invalid_identifier_type(self, tool_service):
        """
        CURRENT BEHAVIOR: Non-int/str identifier raises ValueError.
        """
        with pytest.raises(ValueError) as exc_info:
            await tool_service.get_tool(3.14)  # float not allowed

        assert "int" in str(exc_info.value).lower() or "str" in str(exc_info.value).lower()

    async def test_get_tool_returns_none_when_not_found(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns None when tool doesn't exist.
        """
        mock_repository.get_tool_by_name.return_value = None

        result = await tool_service.get_tool('nonexistent')

        assert result is None

    # ═══════════════════════════════════════════════════════════════
    # Update Validation
    # ═══════════════════════════════════════════════════════════════

    async def test_update_tool_requires_existing_tool(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Cannot update non-existent tool.
        """
        mock_repository.get_tool_by_name.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await tool_service.update_tool('nonexistent', {'description': 'new'})

        assert "not found" in str(exc_info.value).lower()

    async def test_update_tool_name_checks_duplicate(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Renaming tool checks for name collision.
        """
        # Existing tool to update
        mock_repository.get_tool_by_name.side_effect = [
            {'id': 1, 'name': 'old_name'},  # First call: find tool to update
            {'id': 2, 'name': 'new_name'},  # Second call: check new name exists
        ]

        with pytest.raises(ValueError) as exc_info:
            await tool_service.update_tool('old_name', {'name': 'new_name'})

        assert "already exists" in str(exc_info.value).lower()

    # ═══════════════════════════════════════════════════════════════
    # Delete Validation
    # ═══════════════════════════════════════════════════════════════

    async def test_delete_tool_requires_existing_tool(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Cannot delete non-existent tool.
        """
        mock_repository.get_tool_by_name.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await tool_service.delete_tool('nonexistent')

        assert "not found" in str(exc_info.value).lower()

    async def test_delete_tool_returns_success_bool(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns boolean indicating success.
        """
        mock_repository.get_tool_by_name.return_value = {'id': 1, 'name': 'tool'}
        mock_repository.delete_tool.return_value = True

        result = await tool_service.delete_tool('tool')

        assert isinstance(result, bool)
        assert result is True


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.tools
class TestToolServiceBusinessLogicGolden:
    """
    Golden tests for ToolService business operations - DO NOT MODIFY.
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        repo = AsyncMock()
        repo.get_tool_by_id = AsyncMock(return_value=None)
        repo.get_tool_by_name = AsyncMock(return_value=None)
        repo.list_tools = AsyncMock(return_value=[])
        repo.increment_call_count = AsyncMock(return_value=True)
        repo.get_tool_statistics = AsyncMock(return_value={})
        repo.search_tools = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def tool_service(self, mock_repository):
        """Create ToolService with mocked repository."""
        from services.tool_service.tool_service import ToolService
        return ToolService(repository=mock_repository)

    # ═══════════════════════════════════════════════════════════════
    # List Tools
    # ═══════════════════════════════════════════════════════════════

    async def test_list_tools_default_active_only(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: list_tools defaults to active_only=True.
        """
        await tool_service.list_tools()

        call_kwargs = mock_repository.list_tools.call_args
        assert call_kwargs.kwargs.get('is_active') is True

    async def test_list_tools_can_include_inactive(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Can explicitly include inactive tools.
        """
        await tool_service.list_tools(active_only=False)

        call_kwargs = mock_repository.list_tools.call_args
        assert call_kwargs.kwargs.get('is_active') is None

    async def test_list_tools_supports_category_filter(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Can filter by category.
        """
        await tool_service.list_tools(category='intelligence')

        call_kwargs = mock_repository.list_tools.call_args
        assert call_kwargs.kwargs.get('category') == 'intelligence'

    async def test_list_tools_supports_pagination(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Supports limit and offset parameters.
        """
        await tool_service.list_tools(limit=50, offset=10)

        call_kwargs = mock_repository.list_tools.call_args
        assert call_kwargs.kwargs.get('limit') == 50
        assert call_kwargs.kwargs.get('offset') == 10

    # ═══════════════════════════════════════════════════════════════
    # Deprecation
    # ═══════════════════════════════════════════════════════════════

    async def test_deprecate_tool_sets_deprecated_flag(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: deprecate_tool sets is_deprecated to True.
        """
        mock_repository.get_tool_by_name.return_value = {'id': 1, 'name': 'tool'}
        mock_repository.update_tool.return_value = True
        mock_repository.get_tool_by_id.return_value = {'id': 1, 'name': 'tool', 'is_deprecated': True}

        await tool_service.deprecate_tool('tool')

        # Check update was called with deprecation flag
        call_args = mock_repository.update_tool.call_args
        assert call_args[0][1].get('is_deprecated') is True

    async def test_deprecate_tool_default_message(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Provides default deprecation message.
        """
        mock_repository.get_tool_by_name.return_value = {'id': 1, 'name': 'tool'}
        mock_repository.update_tool.return_value = True
        mock_repository.get_tool_by_id.return_value = {'id': 1, 'name': 'tool', 'is_deprecated': True}

        await tool_service.deprecate_tool('tool')

        call_args = mock_repository.update_tool.call_args
        assert 'deprecation_message' in call_args[0][1]

    # ═══════════════════════════════════════════════════════════════
    # Statistics
    # ═══════════════════════════════════════════════════════════════

    async def test_record_tool_call_requires_existing_tool(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns False for unknown tool (no error raised).
        """
        mock_repository.get_tool_by_name.return_value = None

        result = await tool_service.record_tool_call('unknown', True, 100)

        assert result is False

    async def test_record_tool_call_passes_metrics(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Passes success and response_time to repository.
        """
        mock_repository.get_tool_by_name.return_value = {'id': 1, 'name': 'tool'}

        await tool_service.record_tool_call('tool', True, 250)

        mock_repository.increment_call_count.assert_called_once_with(1, True, 250)

    async def test_get_statistics_returns_none_for_unknown_tool(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns None for non-existent tool.
        """
        mock_repository.get_tool_by_name.return_value = None

        result = await tool_service.get_tool_statistics('unknown')

        assert result is None

    # ═══════════════════════════════════════════════════════════════
    # Popular Tools
    # ═══════════════════════════════════════════════════════════════

    async def test_get_popular_tools_sorts_by_call_count(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns tools sorted by call_count descending.
        """
        mock_repository.list_tools.return_value = [
            {'id': 1, 'name': 'low', 'call_count': 10},
            {'id': 2, 'name': 'high', 'call_count': 100},
            {'id': 3, 'name': 'mid', 'call_count': 50},
        ]

        result = await tool_service.get_popular_tools(limit=3)

        assert result[0]['name'] == 'high'
        assert result[1]['name'] == 'mid'
        assert result[2]['name'] == 'low'

    async def test_get_popular_tools_respects_limit(self, tool_service, mock_repository):
        """
        CURRENT BEHAVIOR: Returns at most 'limit' tools.
        """
        mock_repository.list_tools.return_value = [
            {'id': i, 'name': f'tool_{i}', 'call_count': i} for i in range(10)
        ]

        result = await tool_service.get_popular_tools(limit=3)

        assert len(result) == 3
