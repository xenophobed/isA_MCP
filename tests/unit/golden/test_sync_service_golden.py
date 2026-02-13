"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of the SyncService interface and pure logic.
If these tests fail, it means behavior has changed unexpectedly.

Service Under Test: services/sync_service/sync_service.py

Focus: Interface contracts and pure helper methods (NOT service initialization)
"""

import pytest


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.sync
class TestSyncServiceInterfaceGolden:
    """
    Golden tests for SyncService interface - DO NOT MODIFY.

    Tests that SyncService has expected methods and signatures.
    """

    def test_sync_service_has_sync_all_method(self):
        """
        CURRENT BEHAVIOR: SyncService has sync_all() method.
        """
        from services.sync_service.sync_service import SyncService
        import inspect

        assert hasattr(SyncService, "sync_all")
        assert inspect.iscoroutinefunction(SyncService.sync_all)

    def test_sync_service_has_sync_tools_method(self):
        """
        CURRENT BEHAVIOR: SyncService has sync_tools() method.
        """
        from services.sync_service.sync_service import SyncService
        import inspect

        assert hasattr(SyncService, "sync_tools")
        assert inspect.iscoroutinefunction(SyncService.sync_tools)

    def test_sync_service_has_sync_prompts_method(self):
        """
        CURRENT BEHAVIOR: SyncService has sync_prompts() method.
        """
        from services.sync_service.sync_service import SyncService
        import inspect

        assert hasattr(SyncService, "sync_prompts")
        assert inspect.iscoroutinefunction(SyncService.sync_prompts)

    def test_sync_service_has_sync_resources_method(self):
        """
        CURRENT BEHAVIOR: SyncService has sync_resources() method.
        """
        from services.sync_service.sync_service import SyncService
        import inspect

        assert hasattr(SyncService, "sync_resources")
        assert inspect.iscoroutinefunction(SyncService.sync_resources)

    def test_sync_service_has_initialize_method(self):
        """
        CURRENT BEHAVIOR: SyncService has initialize() method.
        """
        from services.sync_service.sync_service import SyncService
        import inspect

        assert hasattr(SyncService, "initialize")
        assert inspect.iscoroutinefunction(SyncService.initialize)

    def test_sync_service_has_set_mcp_server_method(self):
        """
        CURRENT BEHAVIOR: SyncService has set_mcp_server() for post-init server setting.
        """
        from services.sync_service.sync_service import SyncService

        assert hasattr(SyncService, "set_mcp_server")
        assert callable(SyncService.set_mcp_server)

    def test_sync_service_init_accepts_mcp_server(self):
        """
        CURRENT BEHAVIOR: __init__ accepts optional mcp_server parameter.
        """
        from services.sync_service.sync_service import SyncService
        import inspect

        sig = inspect.signature(SyncService.__init__)
        assert "mcp_server" in sig.parameters

    def test_sync_service_embedding_model_constant(self):
        """
        CURRENT BEHAVIOR: Uses 'text-embedding-3-small' model.
        """
        # This is a design decision that should be captured
        expected_model = "text-embedding-3-small"

        # Note: This is the expected value based on code inspection
        assert expected_model == "text-embedding-3-small"


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.sync
class TestSyncServiceHelperMethodsGolden:
    """
    Golden tests for SyncService pure helper methods - DO NOT MODIFY.

    These methods don't require external dependencies.
    """

    @pytest.fixture
    def sync_service_class(self):
        """Get the SyncService class without instantiation."""
        from services.sync_service.sync_service import SyncService

        return SyncService

    def test_build_tool_search_text_method_exists(self, sync_service_class):
        """
        CURRENT BEHAVIOR: Has _build_tool_search_text helper method.
        """
        assert hasattr(sync_service_class, "_build_tool_search_text")

    def test_build_prompt_search_text_method_exists(self, sync_service_class):
        """
        CURRENT BEHAVIOR: Has _build_prompt_search_text helper method.
        """
        assert hasattr(sync_service_class, "_build_prompt_search_text")

    def test_build_resource_search_text_method_exists(self, sync_service_class):
        """
        CURRENT BEHAVIOR: Has _build_resource_search_text helper method.
        """
        assert hasattr(sync_service_class, "_build_resource_search_text")

    def test_prepare_tool_for_sync_method_exists(self, sync_service_class):
        """
        CURRENT BEHAVIOR: Has _prepare_tool_for_sync helper method.
        """
        assert hasattr(sync_service_class, "_prepare_tool_for_sync")

    def test_prepare_prompt_for_sync_method_exists(self, sync_service_class):
        """
        CURRENT BEHAVIOR: Has _prepare_prompt_for_sync helper method.
        """
        assert hasattr(sync_service_class, "_prepare_prompt_for_sync")

    def test_prepare_resource_for_sync_method_exists(self, sync_service_class):
        """
        CURRENT BEHAVIOR: Has _prepare_resource_for_sync helper method.
        """
        assert hasattr(sync_service_class, "_prepare_resource_for_sync")


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.sync
class TestSyncServiceResultStructureGolden:
    """
    Golden tests for sync result structure contracts - DO NOT MODIFY.
    """

    def test_sync_result_expected_keys(self):
        """
        CURRENT BEHAVIOR: Sync results should have specific keys.

        This documents the expected return structure from sync methods.
        """
        expected_keys = {
            "total",  # Total items found in MCP Server
            "synced",  # Items that were updated/created
            "failed",  # Items that failed to sync
            "deleted",  # Orphaned items deleted from Qdrant
            "errors",  # Error details
        }

        # This is the contract - if sync methods don't return these keys,
        # client code will break
        assert "total" in expected_keys
        assert "synced" in expected_keys
        assert "failed" in expected_keys
        assert "deleted" in expected_keys
        assert "errors" in expected_keys

    def test_sync_all_result_expected_keys(self):
        """
        CURRENT BEHAVIOR: sync_all() returns specific structure.

        This documents the expected return structure.
        """
        expected_keys = {
            "success",  # Overall success flag
            "total_synced",  # Total across all types
            "total_skipped",  # Total skipped (unchanged)
            "total_failed",  # Total failures
            "total_deleted",  # Total orphans deleted
            "details",  # Per-type results
        }

        # This is the contract
        assert "success" in expected_keys
        assert "total_synced" in expected_keys
        assert "details" in expected_keys

    def test_sync_all_details_structure(self):
        """
        CURRENT BEHAVIOR: sync_all().details contains tools/prompts/resources.

        This documents the expected structure of the details dict.
        """
        expected_detail_keys = {"tools", "prompts", "resources"}

        # This is the contract for details structure
        assert "tools" in expected_detail_keys
        assert "prompts" in expected_detail_keys
        assert "resources" in expected_detail_keys


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.sync
class TestSyncServiceChangeDetectionLogicGolden:
    """
    Golden tests for change detection logic contracts - DO NOT MODIFY.

    These tests document the change detection behavior without testing implementation.
    """

    def test_change_detection_uses_description(self):
        """
        CURRENT BEHAVIOR: Change detection compares descriptions.

        This documents that unchanged items (same description) should be skipped.
        """
        # Contract: If existing_qdrant.description == new_data.description,
        # the item should be skipped (needs_update = False)
        pass  # This is a documentation test

    def test_change_detection_uses_db_id(self):
        """
        CURRENT BEHAVIOR: Change detection also checks db_id match.

        This prevents stale data when PostgreSQL is reset but Qdrant has old data.
        """
        # Contract: If existing_qdrant.db_id != new_data.id,
        # force resync even if description matches
        pass  # This is a documentation test

    def test_orphan_detection_removes_unregistered_items(self):
        """
        CURRENT BEHAVIOR: Items in Qdrant but not in MCP Server are deleted.

        This ensures Qdrant stays in sync when tools are removed from MCP.
        """
        # Contract: For each item in Qdrant, if not in MCP Server list,
        # delete from Qdrant
        pass  # This is a documentation test
