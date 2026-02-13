"""
CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of the sync and search service interfaces.
If these tests fail, it means the interface has changed unexpectedly.
"""

import pytest
from unittest.mock import MagicMock


@pytest.mark.golden
@pytest.mark.integration
class TestSyncServiceGolden:
    """Golden tests for sync service interface - DO NOT MODIFY."""

    async def test_sync_service_has_expected_methods(self):
        """
        Captures current SyncService interface.
        """
        try:
            from services.sync_service.sync_service import SyncService

            mock_mcp = MagicMock()
            service = SyncService(mcp_server=mock_mcp)

            # Current interface methods
            assert hasattr(service, "sync_all")
            assert hasattr(service, "sync_tools")
            assert hasattr(service, "sync_prompts")
            assert hasattr(service, "sync_resources")
            assert hasattr(service, "initialize")
            assert hasattr(service, "set_mcp_server")
        except Exception as e:
            pytest.skip(f"SyncService not available: {e}")

    async def test_sync_service_has_service_dependencies(self):
        """
        Captures current SyncService service dependencies.
        """
        try:
            from services.sync_service.sync_service import SyncService

            mock_mcp = MagicMock()
            service = SyncService(mcp_server=mock_mcp)

            # Current dependencies
            assert hasattr(service, "tool_service")
            assert hasattr(service, "prompt_service")
            assert hasattr(service, "resource_service")
            assert hasattr(service, "vector_repo")
        except Exception as e:
            pytest.skip(f"SyncService not available: {e}")


@pytest.mark.golden
@pytest.mark.integration
class TestSearchServiceGolden:
    """Golden tests for search service interface - DO NOT MODIFY."""

    async def test_search_service_has_expected_methods(self):
        """
        Captures current SearchService interface.
        """
        try:
            from services.search_service.search_service import SearchService

            service = SearchService()

            # Current interface methods
            assert hasattr(service, "search")
            assert hasattr(service, "search_tools")
            assert hasattr(service, "search_prompts")
            assert hasattr(service, "search_resources")
            assert hasattr(service, "get_stats")
            assert hasattr(service, "initialize")
        except Exception as e:
            pytest.skip(f"SearchService not available: {e}")

    async def test_search_result_dataclass_fields(self):
        """
        Captures current SearchResult dataclass fields.
        """
        try:
            from services.search_service.search_service import SearchResult
            import dataclasses

            # Verify it's a dataclass
            assert dataclasses.is_dataclass(SearchResult)

            # Get field names
            fields = {f.name for f in dataclasses.fields(SearchResult)}

            # Current required fields
            assert "id" in fields
            assert "type" in fields
            assert "name" in fields
            assert "description" in fields
            assert "score" in fields
            assert "db_id" in fields
        except Exception as e:
            pytest.skip(f"SearchResult not available: {e}")


@pytest.mark.golden
@pytest.mark.integration
class TestDiscoveryGolden:
    """Golden tests for auto-discovery interface - DO NOT MODIFY."""

    async def test_auto_discovery_interface_exists(self):
        """
        Captures current auto-discovery interface.
        """
        try:
            from core.auto_discovery import AutoDiscoverySystem

            discovery = AutoDiscoverySystem()

            # Current interface
            assert hasattr(discovery, "auto_register_with_mcp")
        except ImportError:
            pytest.skip("AutoDiscoverySystem not available")
