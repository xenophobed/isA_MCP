"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of ResourceService and ResourceRepository.
If these tests fail, it means behavior has changed unexpectedly.

Service Under Test: services/resource_service/resource_service.py
Repository Under Test: services/resource_service/resource_repository.py
"""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.resources
class TestResourceServiceGolden:
    """
    Golden tests for ResourceService - DO NOT MODIFY.

    Unique features compared to Tool/Prompt services:
    - Multi-identifier: ID or URI (not name)
    - Access control: owner_id, is_public, allowed_users
    - Access tracking: access_count, last_accessed_at
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository with all required methods."""
        repo = AsyncMock()
        repo.get_resource_by_id = AsyncMock(return_value=None)
        repo.get_resource_by_uri = AsyncMock(return_value=None)
        repo.create_resource = AsyncMock(return_value={"id": 1, "uri": "resource://test/1"})
        repo.update_resource = AsyncMock(return_value=True)
        repo.delete_resource = AsyncMock(return_value=True)
        repo.list_resources = AsyncMock(return_value=[])
        repo.search_resources = AsyncMock(return_value=[])
        repo.increment_access_count = AsyncMock(return_value=True)
        repo.grant_access = AsyncMock(return_value=True)
        repo.revoke_access = AsyncMock(return_value=True)
        repo.check_user_access = AsyncMock(return_value=False)  # Add missing method
        return repo

    @pytest.fixture
    def resource_service(self, mock_repository):
        """Create ResourceService with mocked repository."""
        from services.resource_service.resource_service import ResourceService

        return ResourceService(repository=mock_repository)

    # ═══════════════════════════════════════════════════════════════
    # Registration Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_register_resource_requires_uri(self, resource_service):
        """
        CURRENT BEHAVIOR: register_resource raises ValueError if uri is missing.
        """
        with pytest.raises(ValueError) as exc_info:
            await resource_service.register_resource({"name": "test_resource"})

        assert "uri" in str(exc_info.value).lower()

    async def test_register_resource_requires_name(self, resource_service):
        """
        CURRENT BEHAVIOR: register_resource raises ValueError if name is missing.
        """
        with pytest.raises(ValueError) as exc_info:
            await resource_service.register_resource({"uri": "resource://test/1"})

        assert "name" in str(exc_info.value).lower()

    async def test_register_resource_detects_duplicate_uri(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: register_resource raises ValueError for duplicate URIs.
        """
        mock_repository.get_resource_by_uri.return_value = {"id": 1, "uri": "resource://existing/1"}

        with pytest.raises(ValueError):
            await resource_service.register_resource(
                {"uri": "resource://existing/1", "name": "test"}
            )

    async def test_register_resource_success(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: register_resource returns created resource on success.
        """
        mock_repository.get_resource_by_uri.return_value = None
        mock_repository.create_resource.return_value = {
            "id": 1,
            "uri": "resource://new/1",
            "name": "new_resource",
        }

        result = await resource_service.register_resource(
            {"uri": "resource://new/1", "name": "new_resource"}
        )

        assert result["id"] == 1
        assert result["uri"] == "resource://new/1"
        mock_repository.create_resource.assert_called_once()

    # ═══════════════════════════════════════════════════════════════
    # Get Resource Polymorphism (ID or URI)
    # ═══════════════════════════════════════════════════════════════

    async def test_get_resource_by_integer_id(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: Integer identifier calls get_resource_by_id.
        """
        expected = {"id": 1, "uri": "resource://test/1"}
        mock_repository.get_resource_by_id.return_value = expected

        result = await resource_service.get_resource(1)

        mock_repository.get_resource_by_id.assert_called_once_with(1)
        assert result == expected

    async def test_get_resource_by_uri_string(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: String identifier calls get_resource_by_uri.
        """
        expected = {"id": 1, "uri": "resource://test/1"}
        mock_repository.get_resource_by_uri.return_value = expected

        result = await resource_service.get_resource("resource://test/1")

        mock_repository.get_resource_by_uri.assert_called_once_with("resource://test/1")
        assert result == expected

    async def test_get_resource_invalid_identifier_type(self, resource_service):
        """
        CURRENT BEHAVIOR: Non-int/str identifier raises ValueError.
        """
        with pytest.raises(ValueError) as exc_info:
            await resource_service.get_resource([1, 2, 3])

        assert "identifier" in str(exc_info.value).lower()

    # ═══════════════════════════════════════════════════════════════
    # Access Control - Service delegates to Repository
    # ═══════════════════════════════════════════════════════════════

    async def test_check_access_delegates_to_repository(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: check_access delegates to repository.check_user_access.
        """
        mock_repository.check_user_access.return_value = True

        result = await resource_service.check_access("resource://public/1", "any_user")

        assert result is True
        mock_repository.check_user_access.assert_called_once_with("resource://public/1", "any_user")

    async def test_check_access_returns_false_when_denied(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: check_access returns False when repository denies access.
        """
        mock_repository.check_user_access.return_value = False

        result = await resource_service.check_access("resource://private/1", "unauthorized_user")

        assert result is False

    async def test_grant_access_requires_existing_resource(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: grant_access raises ValueError if resource not found.
        """
        mock_repository.get_resource_by_id.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await resource_service.grant_access(999, "new_user")

        assert "not found" in str(exc_info.value).lower()

    async def test_grant_access_calls_repository(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: grant_access calls repository.grant_access with resource ID.
        """
        mock_repository.get_resource_by_id.return_value = {
            "id": 1,
            "uri": "resource://test/1",
            "allowed_users": [],
        }
        mock_repository.grant_access.return_value = True

        result = await resource_service.grant_access(1, "new_user")

        assert result is True
        mock_repository.grant_access.assert_called_once_with(1, "new_user")

    async def test_revoke_access_requires_existing_resource(
        self, resource_service, mock_repository
    ):
        """
        CURRENT BEHAVIOR: revoke_access raises ValueError if resource not found.
        """
        mock_repository.get_resource_by_id.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await resource_service.revoke_access(999, "some_user")

        assert "not found" in str(exc_info.value).lower()

    async def test_revoke_access_calls_repository(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: revoke_access calls repository.revoke_access with resource ID.
        """
        mock_repository.get_resource_by_id.return_value = {
            "id": 1,
            "uri": "resource://test/1",
            "allowed_users": ["user_to_remove"],
        }
        mock_repository.revoke_access.return_value = True

        result = await resource_service.revoke_access(1, "user_to_remove")

        assert result is True
        mock_repository.revoke_access.assert_called_once_with(1, "user_to_remove")

    # ═══════════════════════════════════════════════════════════════
    # Access Tracking
    # ═══════════════════════════════════════════════════════════════

    async def test_record_resource_access_increments_count(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: record_resource_access increments access_count.
        """
        mock_repository.get_resource_by_id.return_value = {"id": 1, "uri": "resource://test/1"}
        mock_repository.increment_access_count.return_value = True

        result = await resource_service.record_resource_access(1)

        assert result is True
        mock_repository.increment_access_count.assert_called_once_with(1)

    async def test_record_resource_access_returns_false_for_unknown(
        self, resource_service, mock_repository
    ):
        """
        CURRENT BEHAVIOR: record_resource_access returns False for unknown resource.
        """
        mock_repository.get_resource_by_id.return_value = None

        result = await resource_service.record_resource_access(999)

        assert result is False
        mock_repository.increment_access_count.assert_not_called()

    # ═══════════════════════════════════════════════════════════════
    # Update and Delete
    # ═══════════════════════════════════════════════════════════════

    async def test_update_resource_requires_existing(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: update_resource raises ValueError if resource not found.
        """
        mock_repository.get_resource_by_id.return_value = None

        with pytest.raises(ValueError):
            await resource_service.update_resource(999, {"name": "new_name"})

    async def test_update_resource_checks_uri_uniqueness(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: update_resource validates new URI is unique.
        """
        mock_repository.get_resource_by_id.return_value = {"id": 1, "uri": "resource://old/1"}
        mock_repository.get_resource_by_uri.return_value = {"id": 2, "uri": "resource://existing/1"}

        with pytest.raises(ValueError) as exc_info:
            await resource_service.update_resource(1, {"uri": "resource://existing/1"})

        assert "exists" in str(exc_info.value).lower()

    async def test_delete_resource_soft_deletes(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: delete_resource performs soft delete via repository.
        """
        mock_repository.get_resource_by_id.return_value = {"id": 1, "uri": "resource://test/1"}
        mock_repository.delete_resource.return_value = True

        result = await resource_service.delete_resource(1)

        assert result is True
        mock_repository.delete_resource.assert_called_once_with(1)

    # ═══════════════════════════════════════════════════════════════
    # User Resources Aggregation
    # ═══════════════════════════════════════════════════════════════

    async def test_get_user_resources_combines_sources(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: get_user_resources returns owned + public + allowed resources.
        Deduplicates by ID.
        """
        # First call: owned resources
        # Second call: public resources
        # Third call: all resources for allowed check
        mock_repository.list_resources.side_effect = [
            [{"id": 1, "uri": "resource://owned/1", "owner_id": "user_123"}],  # owned
            [{"id": 2, "uri": "resource://public/1", "is_public": True}],  # public
            [  # all resources
                {"id": 1, "uri": "resource://owned/1", "owner_id": "user_123", "allowed_users": []},
                {"id": 2, "uri": "resource://public/1", "is_public": True, "allowed_users": []},
                {"id": 3, "uri": "resource://shared/1", "allowed_users": ["user_123"]},
            ],
        ]

        result = await resource_service.get_user_resources("user_123", limit=10)

        assert isinstance(result, list)
        # Should contain 3 unique resources
        assert len(result) == 3

    async def test_get_user_resources_deduplicates(self, resource_service, mock_repository):
        """
        CURRENT BEHAVIOR: get_user_resources deduplicates by ID.
        """
        # Same resource appears in multiple lists
        mock_repository.list_resources.side_effect = [
            [{"id": 1, "uri": "resource://test/1"}],  # owned
            [{"id": 1, "uri": "resource://test/1"}],  # also public
            [{"id": 1, "uri": "resource://test/1", "allowed_users": []}],  # in all
        ]

        result = await resource_service.get_user_resources("user_123", limit=10)

        # Should be deduplicated to single resource
        assert len(result) == 1


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.resources
class TestResourceRepositoryGolden:
    """
    Golden tests for ResourceRepository interface contracts - DO NOT MODIFY.

    Key behaviors:
    - URI uniqueness validation
    - allowed_users as PostgreSQL array
    - Multi-source access control queries
    """

    def test_repository_interface_methods(self):
        """
        CURRENT BEHAVIOR: Repository exposes standard CRUD + access control methods.
        """
        from services.resource_service.resource_repository import ResourceRepository

        # Verify expected methods exist
        assert hasattr(ResourceRepository, "get_resource_by_id")
        assert hasattr(ResourceRepository, "get_resource_by_uri")
        assert hasattr(ResourceRepository, "create_resource")
        assert hasattr(ResourceRepository, "update_resource")
        assert hasattr(ResourceRepository, "delete_resource")
        assert hasattr(ResourceRepository, "list_resources")

    def test_uri_field_documented_as_unique(self):
        """
        CURRENT BEHAVIOR: URI has UNIQUE constraint in database schema.
        Repository enforces: CREATE UNIQUE INDEX ON resources(uri)
        """
        # This is a documentation/contract test - actual constraint in DB
        pass

    def test_allowed_users_documented_as_array(self):
        """
        CURRENT BEHAVIOR: allowed_users is stored as text[] PostgreSQL array.
        Allows efficient: WHERE $1 = ANY(allowed_users)
        """
        # This is a documentation/contract test - actual type in DB
        pass
