"""
Multi-Tenancy Tests for Skill Service.

Tests org_id isolation and is_global flag functionality for:
- Skill category CRUD operations
- Tool-skill assignments
- Skill suggestions

TDD Layer: Component Tests (Layer 2)
Dependency: MockSkillRepository (mocked dependencies)
"""

import pytest
from typing import Any, Dict

from services.skill_service.skill_service import SkillService
from tests.component.mocks.skill_mocks import (
    MockSkillRepository,
    MockAsyncQdrantClient,
    MockModelClient,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_repository():
    """Create a mock skill repository."""
    return MockSkillRepository()


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    return MockAsyncQdrantClient()


@pytest.fixture
def mock_model_client():
    """Create a mock model client."""
    return MockModelClient()


@pytest.fixture
def skill_service(mock_repository, mock_qdrant_client, mock_model_client):
    """Create skill service with mocks."""
    return SkillService(
        repository=mock_repository,
        qdrant_client=mock_qdrant_client,
        model_client=mock_model_client,
    )


def make_skill_data(skill_id: str, name: str = None, description: str = None) -> Dict[str, Any]:
    """Helper to create skill data."""
    return {
        "id": skill_id,
        "name": name or f"Skill {skill_id}",
        "description": description or f"This is a description for {skill_id} skill category",
        "keywords": ["test", skill_id],
    }


# =============================================================================
# Test Classes: Organization Isolation
# =============================================================================


class TestOrgIsolationListSkills:
    """Test org isolation when listing skills."""

    async def test_org_sees_global_plus_own_skills(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """An org should see global skills AND their own org-specific skills."""
        # Create global skill
        await mock_repository.create_skill_category(
            make_skill_data("global_skill"),
            org_id=None,
            is_global=True,
        )

        # Create org-specific skill for org-1
        await mock_repository.create_skill_category(
            make_skill_data("org1_skill"),
            org_id="org-1",
            is_global=False,
        )

        # Create org-specific skill for org-2
        await mock_repository.create_skill_category(
            make_skill_data("org2_skill"),
            org_id="org-2",
            is_global=False,
        )

        # List skills for org-1
        skills = await skill_service.list_skills(org_id="org-1")

        skill_ids = [s["id"] for s in skills]
        assert "global_skill" in skill_ids
        assert "org1_skill" in skill_ids
        assert "org2_skill" not in skill_ids

    async def test_org_cannot_see_other_orgs_private_skills(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """An org should not see another org's private skills."""
        # Create private skill for org-2
        await mock_repository.create_skill_category(
            make_skill_data("private_skill"),
            org_id="org-2",
            is_global=False,
        )

        # List skills for org-1
        skills = await skill_service.list_skills(org_id="org-1")

        skill_ids = [s["id"] for s in skills]
        assert "private_skill" not in skill_ids


class TestOrgIsolationGetSkill:
    """Test org isolation when getting a single skill."""

    async def test_can_get_own_org_skill(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """An org should be able to get their own skill."""
        await mock_repository.create_skill_category(
            make_skill_data("my_skill"),
            org_id="org-1",
            is_global=False,
        )

        skill = await skill_service.get_skill("my_skill", org_id="org-1")
        assert skill is not None
        assert skill["id"] == "my_skill"

    async def test_cannot_get_other_org_private_skill(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """An org should not be able to get another org's private skill."""
        await mock_repository.create_skill_category(
            make_skill_data("other_skill"),
            org_id="org-2",
            is_global=False,
        )

        skill = await skill_service.get_skill("other_skill", org_id="org-1")
        assert skill is None

    async def test_can_get_global_skill_from_any_org(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """Any org should be able to get a global skill."""
        await mock_repository.create_skill_category(
            make_skill_data("global_skill"),
            org_id=None,
            is_global=True,
        )

        skill = await skill_service.get_skill("global_skill", org_id="org-1")
        assert skill is not None
        assert skill["id"] == "global_skill"


class TestOrgIsolationCreateSkill:
    """Test org isolation when creating skills."""

    async def test_skill_created_with_org_id(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """Skills should be created with the provided org_id."""
        skill = await skill_service.create_skill_category(
            make_skill_data("new_skill"),
            org_id="org-1",
            is_global=False,
        )

        assert skill["org_id"] == "org-1"
        assert skill["is_global"] is False

    async def test_global_skill_created_with_is_global_true(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """Global skills should have is_global=True."""
        skill = await skill_service.create_skill_category(
            make_skill_data("global_skill"),
            org_id=None,
            is_global=True,
        )

        assert skill["org_id"] is None
        assert skill["is_global"] is True


class TestOrgIsolationUpdateSkill:
    """Test org isolation when updating skills."""

    async def test_can_update_own_org_skill(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """An org should be able to update their own skill."""
        await mock_repository.create_skill_category(
            make_skill_data("my_skill"),
            org_id="org-1",
            is_global=False,
        )

        updated = await skill_service.update_skill_category(
            "my_skill",
            {"description": "Updated description for my skill"},
            org_id="org-1",
        )

        assert updated is not None
        assert updated["description"] == "Updated description for my skill"

    async def test_cannot_update_other_org_skill(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """An org should not be able to update another org's skill."""
        await mock_repository.create_skill_category(
            make_skill_data("other_skill"),
            org_id="org-2",
            is_global=False,
        )

        with pytest.raises(ValueError, match="Skill not found"):
            await skill_service.update_skill_category(
                "other_skill",
                {"description": "Hacked description"},
                org_id="org-1",
            )


class TestOrgIsolationDeleteSkill:
    """Test org isolation when deleting skills."""

    async def test_can_delete_own_org_skill(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """An org should be able to delete their own skill."""
        await mock_repository.create_skill_category(
            make_skill_data("my_skill"),
            org_id="org-1",
            is_global=False,
        )

        success = await skill_service.delete_skill_category(
            "my_skill",
            org_id="org-1",
        )

        assert success is True

    async def test_cannot_delete_other_org_skill(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """An org should not be able to delete another org's skill."""
        await mock_repository.create_skill_category(
            make_skill_data("other_skill"),
            org_id="org-2",
            is_global=False,
        )

        success = await skill_service.delete_skill_category(
            "other_skill",
            org_id="org-1",
        )

        assert success is False


# =============================================================================
# Test Classes: Backward Compatibility
# =============================================================================


class TestBackwardCompatibilityNoOrgId:
    """Test backward compatibility when no org_id is provided."""

    async def test_list_skills_shows_only_global_when_no_org_id(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """Without org_id, list_skills should only return global skills."""
        # Create global skill
        await mock_repository.create_skill_category(
            make_skill_data("global_skill"),
            org_id=None,
            is_global=True,
        )

        # Create org-specific skill
        await mock_repository.create_skill_category(
            make_skill_data("org_skill"),
            org_id="org-1",
            is_global=False,
        )

        # List skills without org_id
        skills = await skill_service.list_skills()

        skill_ids = [s["id"] for s in skills]
        assert "global_skill" in skill_ids
        assert "org_skill" not in skill_ids

    async def test_get_skill_returns_only_global_when_no_org_id(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """Without org_id, get_skill should only return global skills."""
        # Create org-specific skill
        await mock_repository.create_skill_category(
            make_skill_data("org_skill"),
            org_id="org-1",
            is_global=False,
        )

        # Try to get without org_id
        skill = await skill_service.get_skill("org_skill")
        assert skill is None


# =============================================================================
# Test Classes: Global Skills
# =============================================================================


class TestGlobalSkillsVisibleToAll:
    """Test that global skills are visible to all orgs."""

    async def test_global_skills_visible_across_orgs(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """Global skills should be visible to any org."""
        await mock_repository.create_skill_category(
            make_skill_data("global_skill"),
            org_id=None,
            is_global=True,
        )

        # Check visibility from different orgs
        for org_id in ["org-1", "org-2", "org-3"]:
            skills = await skill_service.list_skills(org_id=org_id)
            skill_ids = [s["id"] for s in skills]
            assert "global_skill" in skill_ids

    async def test_global_skills_created_by_org_visible_to_others(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """A global skill created by one org should be visible to others."""
        await mock_repository.create_skill_category(
            make_skill_data("shared_skill"),
            org_id="org-1",  # Created by org-1
            is_global=True,  # But marked as global
        )

        # Check visibility from org-2
        skills = await skill_service.list_skills(org_id="org-2")
        skill_ids = [s["id"] for s in skills]
        assert "shared_skill" in skill_ids


# =============================================================================
# Test Classes: Assignment Isolation
# =============================================================================


class TestAssignmentIsolation:
    """Test org isolation for tool-skill assignments."""

    async def test_assignments_created_with_org_id(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """Assignments should be created with the provided org_id."""
        # Create a global skill first
        await mock_repository.create_skill_category(
            make_skill_data("test_skill"),
            org_id=None,
            is_global=True,
        )

        # Create assignment with org_id
        assignments = await skill_service.assign_tool_to_skills(
            tool_id=1,
            skill_ids=["test_skill"],
            primary_skill_id="test_skill",
            org_id="org-1",
            is_global=False,
        )

        assert len(assignments) == 1
        assert assignments[0]["org_id"] == "org-1"
        assert assignments[0]["is_global"] is False

    async def test_org_specific_assignments_isolated(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """Org-specific assignments should be isolated."""
        # Create skill
        await mock_repository.create_skill_category(
            make_skill_data("test_skill"),
            org_id=None,
            is_global=True,
        )

        # Create org-1 assignment
        await mock_repository.create_assignment(
            tool_id=1,
            skill_id="test_skill",
            confidence=0.9,
            org_id="org-1",
            is_global=False,
        )

        # Create org-2 assignment
        await mock_repository.create_assignment(
            tool_id=2,
            skill_id="test_skill",
            confidence=0.8,
            org_id="org-2",
            is_global=False,
        )

        # Get assignments for org-1
        org1_assignments = await mock_repository.get_assignments_for_skill(
            "test_skill", org_id="org-1"
        )
        org1_tool_ids = [a["tool_id"] for a in org1_assignments]
        assert 1 in org1_tool_ids
        assert 2 not in org1_tool_ids

    async def test_global_assignments_visible_to_all(
        self, skill_service: SkillService, mock_repository: MockSkillRepository
    ):
        """Global assignments should be visible to all orgs."""
        # Create skill
        await mock_repository.create_skill_category(
            make_skill_data("test_skill"),
            org_id=None,
            is_global=True,
        )

        # Create global assignment
        await mock_repository.create_assignment(
            tool_id=1,
            skill_id="test_skill",
            confidence=0.9,
            org_id=None,
            is_global=True,
        )

        # Check visibility from different orgs
        for org_id in ["org-1", "org-2"]:
            assignments = await mock_repository.get_assignments_for_skill(
                "test_skill", org_id=org_id
            )
            tool_ids = [a["tool_id"] for a in assignments]
            assert 1 in tool_ids


# =============================================================================
# Test Classes: Suggestion Isolation
# =============================================================================


class TestSuggestionIsolation:
    """Test org isolation for skill suggestions."""

    async def test_suggestions_created_with_org_id(
        self, mock_repository: MockSkillRepository
    ):
        """Suggestions should be created with org_id."""
        suggestion = await mock_repository.create_suggestion(
            suggested_name="New Skill",
            suggested_description="A newly suggested skill category",
            source_tool_id=1,
            source_tool_name="test_tool",
            reasoning="This tool needs a new skill",
            org_id="org-1",
        )

        assert suggestion["org_id"] == "org-1"

    async def test_list_suggestions_filtered_by_org(
        self, mock_repository: MockSkillRepository
    ):
        """Suggestions should be filtered by org_id."""
        # Create suggestion for org-1
        await mock_repository.create_suggestion(
            suggested_name="Org1 Skill",
            suggested_description="A skill suggested by org-1",
            source_tool_id=1,
            source_tool_name="tool1",
            reasoning="reason",
            org_id="org-1",
        )

        # Create suggestion for org-2
        await mock_repository.create_suggestion(
            suggested_name="Org2 Skill",
            suggested_description="A skill suggested by org-2",
            source_tool_id=2,
            source_tool_name="tool2",
            reasoning="reason",
            org_id="org-2",
        )

        # List suggestions for org-1
        org1_suggestions = await mock_repository.list_suggestions(org_id="org-1")
        names = [s["suggested_name"] for s in org1_suggestions]
        assert "Org1 Skill" in names
        assert "Org2 Skill" not in names

    async def test_list_suggestions_without_org_id_shows_all(
        self, mock_repository: MockSkillRepository
    ):
        """Without org_id, list_suggestions should show all (admin view)."""
        # Create suggestions for different orgs
        await mock_repository.create_suggestion(
            suggested_name="Org1 Skill",
            suggested_description="A skill suggested by org-1",
            source_tool_id=1,
            source_tool_name="tool1",
            reasoning="reason",
            org_id="org-1",
        )

        await mock_repository.create_suggestion(
            suggested_name="Org2 Skill",
            suggested_description="A skill suggested by org-2",
            source_tool_id=2,
            source_tool_name="tool2",
            reasoning="reason",
            org_id="org-2",
        )

        # List all suggestions (admin view)
        all_suggestions = await mock_repository.list_suggestions()
        names = [s["suggested_name"] for s in all_suggestions]
        assert "Org1 Skill" in names
        assert "Org2 Skill" in names


# =============================================================================
# Test Classes: Audit Logging
# =============================================================================


class TestAuditLogging:
    """Test that operations log org_id for audit purposes."""

    async def test_create_skill_logs_org_id(
        self, skill_service: SkillService, caplog
    ):
        """Creating a skill should log org_id."""
        import logging

        with caplog.at_level(logging.INFO):
            await skill_service.create_skill_category(
                make_skill_data("audit_skill"),
                org_id="org-1",
                user_id="user-123",
            )

        assert any("org_id=org-1" in record.message for record in caplog.records)

    async def test_delete_skill_logs_org_id(
        self, skill_service: SkillService, mock_repository: MockSkillRepository, caplog
    ):
        """Deleting a skill should log org_id."""
        import logging

        # Create skill first
        await mock_repository.create_skill_category(
            make_skill_data("delete_skill"),
            org_id="org-1",
            is_global=False,
        )

        with caplog.at_level(logging.INFO):
            await skill_service.delete_skill_category(
                "delete_skill",
                org_id="org-1",
                user_id="user-123",
            )

        assert any("org_id=org-1" in record.message for record in caplog.records)
