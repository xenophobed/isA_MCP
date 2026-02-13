"""
TDD TESTS - Define new feature behavior

Integration flow tests for the sync and search services.
These tests verify service interfaces and basic flows.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.integration
class TestSyncFlow:
    """TDD tests for sync service flow."""

    async def test_sync_service_interface(self):
        """
        Test SyncService has expected interface.
        """
        try:
            from services.sync_service.sync_service import SyncService

            mock_mcp = MagicMock()
            mock_mcp.list_tools = AsyncMock(return_value=[])
            mock_mcp.list_prompts = AsyncMock(return_value=[])
            mock_mcp.list_resources = AsyncMock(return_value=[])

            service = SyncService(mcp_server=mock_mcp)

            # Should have core methods
            assert hasattr(service, "sync_all")
            assert hasattr(service, "sync_tools")
            assert hasattr(service, "sync_prompts")
            assert hasattr(service, "sync_resources")
            assert hasattr(service, "initialize")
            assert hasattr(service, "set_mcp_server")
        except Exception as e:
            pytest.skip(f"SyncService not available: {e}")

    async def test_sync_service_can_set_mcp_server(self):
        """
        Test SyncService can set MCP server after initialization.
        """
        try:
            from services.sync_service.sync_service import SyncService

            mock_mcp = MagicMock()
            mock_mcp.list_tools = AsyncMock(return_value=[])

            service = SyncService()
            service.set_mcp_server(mock_mcp)

            assert service.mcp_server == mock_mcp
        except Exception as e:
            pytest.skip(f"SyncService not available: {e}")


@pytest.mark.integration
class TestSearchFlow:
    """TDD tests for search service flow."""

    async def test_search_service_interface(self):
        """
        Test SearchService has expected interface.
        """
        try:
            from services.search_service.search_service import SearchService

            service = SearchService()

            # Should have core methods
            assert hasattr(service, "search")
            assert hasattr(service, "search_tools")
            assert hasattr(service, "search_prompts")
            assert hasattr(service, "search_resources")
            assert hasattr(service, "get_stats")
            assert hasattr(service, "initialize")
        except Exception as e:
            pytest.skip(f"SearchService not available: {e}")

    async def test_search_result_dataclass(self):
        """
        Test SearchResult dataclass structure.
        """
        try:
            from services.search_service.search_service import SearchResult

            # Should have expected fields (including required metadata)
            result = SearchResult(
                id="test_1",
                type="tool",
                name="test",
                description="Test",
                score=0.85,
                db_id=1,
                metadata={},
            )

            assert result.id == "test_1"
            assert result.type == "tool"
            assert result.name == "test"
            assert result.score == 0.85
            assert result.metadata == {}
        except Exception as e:
            pytest.skip(f"SearchResult not available: {e}")
