"""
Skill Service TDD Tests

Test-Driven Development tests for the Skill Service.
All tests reference business rules from tests/contracts/skill/logic_contract.md
and use data structures from tests/contracts/skill/data_contract.py.

TDD Status: GREEN PHASE - Implementation complete, tests being enabled.
"""
import pytest
import json
from datetime import datetime, timezone
from typing import List
from pydantic import ValidationError

# Import contracts
from tests.contracts.skill.data_contract import (
    SkillTestDataFactory,
    SkillCategoryCreateRequestContract,
    ToolClassificationRequestContract,
    ToolClassificationResponseContract,
    SkillCategoryResponseContract,
    SkillAssignmentContract,
    SkillCategoryBuilder,
    ToolClassificationBuilder,
    AssignmentSource,
    SkillStatus,
)

# Service imports - will be available once service is implemented
# For now, tests that need these will skip if import fails
try:
    from services.skill_service import SkillService, SkillRepository
    from tests.component.mocks.skill_mocks import (
        MockSkillRepository,
        MockAsyncQdrantClient,
        MockModelClient,
    )
    SERVICE_AVAILABLE = True
except ImportError as e:
    # Service not yet available or path issue - tests will be skipped
    SkillService = None
    SkillRepository = None
    MockSkillRepository = None
    MockAsyncQdrantClient = None
    MockModelClient = None
    SERVICE_AVAILABLE = False
    import warnings
    warnings.warn(f"SkillService not available for testing: {e}")


# ═══════════════════════════════════════════════════════════════
# Contract Validation Tests (Data Contract)
# These tests validate that the data contracts themselves work correctly
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.unit
class TestDataContractValidation:
    """Test that data contracts validate input correctly."""

    def test_valid_skill_category_request(self):
        """Test that valid skill category request is accepted."""
        skill = SkillTestDataFactory.make_skill_category(
            id="calendar_management",
            name="Calendar Management",
            description="Tools for managing calendars, events, and scheduling",
        )
        assert skill.id == "calendar_management"
        assert skill.name == "Calendar Management"
        assert skill.is_active is True

    def test_invalid_skill_id_format_rejected(self):
        """Test that skill ID starting with number is rejected."""
        invalid_data = SkillTestDataFactory.make_invalid_skill_invalid_id_format()
        with pytest.raises(ValidationError) as exc:
            SkillCategoryCreateRequestContract(**invalid_data)
        assert "pattern" in str(exc.value).lower() or "id" in str(exc.value).lower()

    def test_invalid_skill_id_with_spaces_rejected(self):
        """Test that skill ID with spaces is rejected."""
        invalid_data = SkillTestDataFactory.make_invalid_skill_id_with_spaces()
        with pytest.raises(ValidationError):
            SkillCategoryCreateRequestContract(**invalid_data)

    def test_invalid_skill_short_description_rejected(self):
        """Test that description < 10 chars is rejected."""
        invalid_data = SkillTestDataFactory.make_invalid_skill_short_description()
        with pytest.raises(ValidationError) as exc:
            SkillCategoryCreateRequestContract(**invalid_data)
        assert "description" in str(exc.value).lower()

    def test_keywords_normalized_to_lowercase(self):
        """Test that keywords are normalized to lowercase."""
        skill = SkillTestDataFactory.make_skill_category(
            id="test_skill",
            name="Test Skill",
            description="A test skill description that is long enough",
            keywords=["CALENDAR", "Event", "Schedule"],
        )
        assert skill.keywords == ["calendar", "event", "schedule"]

    def test_builder_pattern_creates_valid_skill(self):
        """Test SkillCategoryBuilder creates valid request."""
        skill = (
            SkillCategoryBuilder()
            .with_id("calendar_management")
            .with_name("Calendar Management")
            .with_description("Tools for managing calendars and events")
            .with_keywords(["calendar", "event"])
            .with_examples(["create_event", "list_events"])
            .with_parent_domain("productivity")
            .build()
        )
        assert skill.id == "calendar_management"
        assert "calendar" in skill.keywords
        assert skill.parent_domain == "productivity"

    def test_classification_response_sorted_by_confidence(self):
        """Test that classification response sorts assignments by confidence."""
        response = ToolClassificationResponseContract(
            tool_id=1,
            tool_name="test_tool",
            assignments=[
                SkillAssignmentContract(skill_id="skill_a", confidence=0.6),
                SkillAssignmentContract(skill_id="skill_b", confidence=0.9),
                SkillAssignmentContract(skill_id="skill_c", confidence=0.7),
            ],
            primary_skill_id="skill_b",
            classification_timestamp=datetime.now(timezone.utc),
        )
        # Should be sorted descending by confidence
        assert response.assignments[0].skill_id == "skill_b"
        assert response.assignments[0].confidence == 0.9
        assert response.assignments[1].skill_id == "skill_c"
        assert response.assignments[2].skill_id == "skill_a"

    def test_seed_skills_all_valid(self):
        """Test that all seed skills from factory are valid."""
        seed_skills = SkillTestDataFactory.get_seed_skills()
        assert len(seed_skills) >= 5  # At least 5 seed skills
        for skill in seed_skills:
            # Each should be a valid contract
            assert isinstance(skill, SkillCategoryCreateRequestContract)
            assert len(skill.description) >= 10
            assert skill.is_active is True


# ═══════════════════════════════════════════════════════════════
# Fixtures for Skill Service Testing
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_skill_repository():
    """Provide mock skill repository for testing."""
    if not SERVICE_AVAILABLE:
        pytest.skip("SkillService not available - check import path")
    return MockSkillRepository()


@pytest.fixture
def mock_skill_qdrant():
    """Provide mock Qdrant client for skill testing."""
    if not SERVICE_AVAILABLE:
        pytest.skip("SkillService not available - check import path")
    return MockAsyncQdrantClient()


@pytest.fixture
def mock_skill_model():
    """Provide mock model client for skill testing."""
    if not SERVICE_AVAILABLE:
        pytest.skip("SkillService not available - check import path")
    return MockModelClient()


@pytest.fixture
def skill_service(mock_skill_repository, mock_skill_qdrant, mock_skill_model):
    """Provide SkillService with mocked dependencies."""
    if not SERVICE_AVAILABLE:
        pytest.skip("SkillService not available - check import path")
    service = SkillService(
        repository=mock_skill_repository,
        qdrant_client=mock_skill_qdrant,
        model_client=mock_skill_model
    )
    return service


# ═══════════════════════════════════════════════════════════════
# BR-001: Skill Category Creation
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
class TestBR001SkillCategoryCreation:
    """
    BR-001: Skill Category Creation

    Given: Valid skill category request from admin
    When: Admin creates a new skill category
    Then:
    - Skill ID validated (lowercase, starts with letter, underscores allowed)
    - Skill record created in mcp.skill_categories table
    - Initial embedding generated from description
    - Skill upserted to Qdrant mcp_skills collection
    - tool_count initialized to 0
    """

    @pytest.mark.asyncio
    async def test_create_skill_category_success(self, skill_service, mock_skill_repository):
        """Test successful skill category creation."""
        # Arrange
        skill_data = {
            "id": "calendar_management",
            "name": "Calendar Management",
            "description": "Tools for managing calendars, events, and scheduling",
            "keywords": ["calendar", "event", "schedule"],
            "examples": ["create_event", "list_events"],
        }

        # Act
        result = await skill_service.create_skill_category(skill_data)

        # Assert
        assert result["id"] == "calendar_management"
        assert result["tool_count"] == 0
        assert result["is_active"] is True
        assert result["name"] == "Calendar Management"

        # Verify repository was called
        calls = mock_skill_repository.get_calls("create_skill_category")
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_create_skill_duplicate_id_returns_error(
        self, skill_service, mock_skill_repository
    ):
        """Test that duplicate skill ID raises ValueError."""
        # Arrange - create skill first
        skill_data = {
            "id": "calendar_management",
            "name": "Calendar Management",
            "description": "Tools for managing calendars, events, and scheduling",
        }
        await skill_service.create_skill_category(skill_data)

        # Act & Assert - try to create duplicate
        with pytest.raises(ValueError) as exc:
            await skill_service.create_skill_category(skill_data)
        assert "already exists" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_skill_generates_embedding(
        self, skill_service, mock_skill_model
    ):
        """Test that creating a skill generates description embedding."""
        # Arrange
        skill_data = {
            "id": "test_skill",
            "name": "Test Skill",
            "description": "Tools for managing calendars and events",
        }

        # Act
        await skill_service.create_skill_category(skill_data)

        # Verify embedding was requested
        embedding_calls = mock_skill_model.embeddings._calls
        assert len(embedding_calls) >= 1


# Remaining BR-001 tests (skipped for future GREEN phase work)
@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
class TestBR001SkillCategoryCreationLegacy:
    """Legacy placeholder tests - to be migrated."""

    @pytest.mark.asyncio
    async def test_create_skill_category_success_legacy(
        self, mock_db_pool, mock_qdrant_client, mock_model_client
    ):
        """Test successful skill category creation - legacy format."""
        pytest.skip("Migrated to TestBR001SkillCategoryCreation.test_create_skill_category_success")

        # Arrange
        request = SkillTestDataFactory.make_skill_category(
            id="calendar_management",
            name="Calendar Management",
            description="Tools for managing calendars, events, and scheduling",
            keywords=["calendar", "event", "schedule"],
            examples=["create_event", "list_events"],
        )

        # Act
        # service = SkillService(db_pool=mock_db_pool, qdrant=mock_qdrant_client, model=mock_model_client)
        # result = await service.create_skill_category(request)

        # Assert
        # assert result.id == "calendar_management"
        # assert result.tool_count == 0
        # assert result.is_active is True

        # Verify embedding was generated
        # embedding_calls = mock_model_client.get_calls("embedding")
        # assert len(embedding_calls) == 1

        # Verify upserted to Qdrant
        # assert "mcp_skills" in mock_qdrant_client.collections

    @pytest.mark.asyncio
    async def test_create_skill_duplicate_id_returns_409(
        self, mock_db_pool, mock_qdrant_client, mock_model_client
    ):
        """Test that duplicate skill ID returns 409 Conflict."""
        pytest.skip("Skill service not yet implemented - TDD RED phase")

        # Arrange - skill already exists
        # mock_db_pool.set_response("fetchrow", {"id": "calendar_management"})

        # request = SkillTestDataFactory.make_skill_category(id="calendar_management")
        # service = SkillService(db_pool=mock_db_pool, qdrant=mock_qdrant_client, model=mock_model_client)

        # Act & Assert
        # with pytest.raises(SkillAlreadyExistsError) as exc:
        #     await service.create_skill_category(request)
        # assert "already exists" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_skill_generates_embedding(
        self, mock_db_pool, mock_qdrant_client, mock_model_client
    ):
        """Test that creating a skill generates description embedding."""
        pytest.skip("Skill service not yet implemented - TDD RED phase")

        # request = SkillTestDataFactory.make_skill_category(
        #     description="Tools for managing calendars and events"
        # )
        # service = SkillService(db_pool=mock_db_pool, qdrant=mock_qdrant_client, model=mock_model_client)
        # await service.create_skill_category(request)

        # Verify embedding was generated with description
        # calls = mock_model_client.get_calls("embedding")
        # assert "calendars and events" in calls[0]["params"]["text"]


# ═══════════════════════════════════════════════════════════════
# BR-002: Tool Classification (LLM)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
class TestBR002ToolClassification:
    """
    BR-002: Tool Classification (LLM)

    Given: Tool to be classified with name and description
    When: Classification is requested
    Then:
    - LLM receives tool info + available skill categories
    - LLM returns 1-3 skill assignments with confidence scores
    - Assignments with confidence >= 0.5 are saved
    - Primary skill = highest confidence assignment
    """

    @pytest.mark.asyncio
    async def test_classify_tool_returns_assignments(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that tool classification returns skill assignments."""
        # Arrange - seed a skill category first
        await mock_skill_repository.create_skill_category({
            "id": "calendar-management",
            "name": "Calendar Management",
            "description": "Tools for managing calendars and events",
        })

        # Mock LLM response for classification
        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "calendar-management", "confidence": 0.95, "reasoning": "Creates calendar events"},
            ],
            "primary_skill_id": "calendar-management",
            "suggested_new_skill": None,
        }))

        # Act
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="create_calendar_event",
            tool_description="Create a new event on the calendar with title and time"
        )

        # Assert
        assert len(result["assignments"]) >= 1
        assert result["assignments"][0]["skill_id"] == "calendar-management"
        assert result["assignments"][0]["confidence"] >= 0.5
        assert result["primary_skill_id"] == "calendar-management"

    @pytest.mark.asyncio
    async def test_classify_tool_max_3_assignments(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that classification returns max 3 skill assignments."""
        # Arrange - seed multiple skills
        for i in range(5):
            await mock_skill_repository.create_skill_category({
                "id": f"skill_{i}",
                "name": f"Skill {i}",
                "description": f"Description for skill {i}",
            })

        # Mock LLM returning 5 assignments
        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": f"skill_{i}", "confidence": 0.9 - i * 0.1, "reasoning": f"Reason {i}"}
                for i in range(5)
            ],
            "primary_skill_id": "skill_0",
            "suggested_new_skill": None,
        }))

        # Act
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="test_tool",
            tool_description="A tool that does many things"
        )

        # Assert - should be limited to 3
        assert len(result["assignments"]) <= 3

    @pytest.mark.asyncio
    async def test_classify_tool_filters_low_confidence(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that assignments with confidence < 0.5 are filtered out."""
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "calendar-management",
            "name": "Calendar Management",
            "description": "Tools for calendars",
        })

        # Mock LLM returning low confidence
        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "calendar-management", "confidence": 0.3, "reasoning": "Maybe related"},
            ],
            "primary_skill_id": None,
            "suggested_new_skill": None,
        }))

        # Act
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="random_tool",
            tool_description="A tool that does random things"
        )

        # Assert - low confidence assignment filtered out
        assert len(result["assignments"]) == 0

    @pytest.mark.asyncio
    async def test_classify_tool_suggests_new_skill_when_no_match(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that LLM suggests new skill when no existing skill matches."""
        # Arrange - no matching skills
        await mock_skill_repository.create_skill_category({
            "id": "calendar-management",
            "name": "Calendar Management",
            "description": "Calendar tools only",
        })

        # Mock LLM suggesting new skill
        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [],
            "primary_skill_id": None,
            "suggested_new_skill": {
                "name": "Video Processing",
                "description": "Tools for processing and editing video content",
                "reasoning": "Tool handles video, no existing category",
            },
        }))

        # Act
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="video_editor",
            tool_description="Edit and process video files"
        )

        # Assert
        assert result["suggested_new_skill"] is not None
        assert result["suggested_new_skill"]["name"] == "Video Processing"

        # Verify suggestion was stored
        suggestions = mock_skill_repository.get_calls("create_suggestion")
        assert len(suggestions) == 1

    @pytest.mark.asyncio
    async def test_classify_tool_skips_already_classified_with_human_override(
        self, skill_service, mock_skill_repository
    ):
        """Test that tools with human override are skipped."""
        # Arrange - tool already has human override assignment
        await mock_skill_repository.create_skill_category({
            "id": "calendar-management",
            "name": "Calendar Management",
            "description": "Calendar tools",
        })
        await mock_skill_repository.create_assignment(
            tool_id=1,
            skill_id="calendar-management",
            confidence=1.0,
            is_primary=True,
            source="human_override"
        )

        # Act
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="test_tool",
            tool_description="Test tool"
        )

        # Assert - skipped, returns existing
        assert result.get("skipped") is True
        assert result["assignments"][0]["skill_id"] == "calendar-management"

    @pytest.mark.asyncio
    async def test_classify_tool_force_reclassify(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that force_reclassify overrides existing classification."""
        # Arrange - tool already classified
        await mock_skill_repository.create_skill_category({
            "id": "old-skill",
            "name": "Old Skill",
            "description": "Old skill category",
        })
        await mock_skill_repository.create_skill_category({
            "id": "new-skill",
            "name": "New Skill",
            "description": "New skill category",
        })
        await mock_skill_repository.create_assignment(
            tool_id=1,
            skill_id="old-skill",
            confidence=0.9,
            is_primary=True,
            source="llm_auto"
        )

        # Mock LLM returning new assignment
        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "new-skill", "confidence": 0.95, "reasoning": "Better match"},
            ],
            "primary_skill_id": "new-skill",
            "suggested_new_skill": None,
        }))

        # Act with force_reclassify
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="test_tool",
            tool_description="Test tool",
            force_reclassify=True
        )

        # Assert - new classification applied
        assert result["primary_skill_id"] == "new-skill"
        assert result.get("skipped") is not True


# ═══════════════════════════════════════════════════════════════
# BR-003: Skill Assignment Storage
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
class TestBR003SkillAssignmentStorage:
    """
    BR-003: Skill Assignment Storage

    Given: Classification result with skill assignments
    When: Assignments are stored
    Then:
    - Old assignments for tool deleted (if re-classifying)
    - New assignments created in mcp.tool_skill_assignments table
    - Tool vector payload updated with skill_ids[] array
    """

    @pytest.mark.asyncio
    async def test_store_assignments_creates_records(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that assignments are stored in database."""
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "test-skill",
            "name": "Test Skill",
            "description": "A test skill category",
        })

        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "test-skill", "confidence": 0.9, "reasoning": "Matches"},
            ],
            "primary_skill_id": "test-skill",
            "suggested_new_skill": None,
        }))

        # Act
        await skill_service.classify_tool(
            tool_id=42,
            tool_name="test_tool",
            tool_description="A test tool"
        )

        # Assert - verify assignment was created
        calls = mock_skill_repository.get_calls("create_assignment")
        assert len(calls) == 1
        assert calls[0]["args"]["tool_id"] == 42
        assert calls[0]["args"]["skill_id"] == "test-skill"

    @pytest.mark.asyncio
    async def test_store_assignments_replaces_existing(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that re-classification replaces existing assignments."""
        # Arrange - create skill and existing assignment
        await mock_skill_repository.create_skill_category({
            "id": "old-skill",
            "name": "Old Skill",
            "description": "Old skill",
        })
        await mock_skill_repository.create_skill_category({
            "id": "new-skill",
            "name": "New Skill",
            "description": "New skill",
        })
        await mock_skill_repository.create_assignment(
            tool_id=1,
            skill_id="old-skill",
            confidence=0.8,
            is_primary=True,
            source="llm_auto"
        )

        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "new-skill", "confidence": 0.95, "reasoning": "Better match"},
            ],
            "primary_skill_id": "new-skill",
            "suggested_new_skill": None,
        }))

        # Act - force reclassify
        await skill_service.classify_tool(
            tool_id=1,
            tool_name="test_tool",
            tool_description="Test",
            force_reclassify=True
        )

        # Assert - old assignments deleted
        delete_calls = mock_skill_repository.get_calls("delete_assignments_for_tool")
        assert len(delete_calls) >= 1

    @pytest.mark.asyncio
    async def test_store_assignments_increments_tool_count(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that skill tool_count is incremented on assignment."""
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "test-skill",
            "name": "Test Skill",
            "description": "A test skill",
        })

        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "test-skill", "confidence": 0.9, "reasoning": "Match"},
            ],
            "primary_skill_id": "test-skill",
            "suggested_new_skill": None,
        }))

        # Act
        await skill_service.classify_tool(
            tool_id=1,
            tool_name="test",
            tool_description="Test tool"
        )

        # Assert - tool count incremented
        increment_calls = mock_skill_repository.get_calls("increment_tool_count")
        assert len(increment_calls) >= 1
        assert increment_calls[0]["args"]["skill_id"] == "test-skill"


# ═══════════════════════════════════════════════════════════════
# BR-004: Skill Embedding Generation (Aggregated)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
class TestBR004SkillEmbeddingGeneration:
    """
    BR-004: Skill Embedding Generation

    Given: Skill with assigned tools
    When: Skill embedding is updated
    Then:
    - Compute weighted average of tool embeddings (weight = confidence)
    - Normalize resulting vector
    - Upsert to Qdrant mcp_skills collection
    """

    @pytest.mark.asyncio
    async def test_skill_embedding_generated_on_creation(
        self, skill_service, mock_skill_model
    ):
        """Test that skill embedding is generated when skill is created."""
        # Arrange
        skill_data = {
            "id": "test_embedding_skill",
            "name": "Test Embedding Skill",
            "description": "A skill to test embedding generation",
        }

        # Act
        await skill_service.create_skill_category(skill_data)

        # Assert - embedding was generated
        embedding_calls = mock_skill_model.embeddings._calls
        assert len(embedding_calls) >= 1
        assert "embedding generation" in embedding_calls[0]["input"] or len(embedding_calls[0]["input"]) > 0

    @pytest.mark.asyncio
    async def test_skill_embedding_updated_on_description_change(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that skill embedding is updated when description changes."""
        # Arrange - create skill first
        await mock_skill_repository.create_skill_category({
            "id": "update_test_skill",
            "name": "Update Test",
            "description": "Original description",
        })

        # Clear previous embedding calls
        mock_skill_model.embeddings._calls.clear()

        # Act - update description
        await skill_service.update_skill_category(
            skill_id="update_test_skill",
            updates={"description": "New updated description for the skill"}
        )

        # Assert - new embedding generated
        embedding_calls = mock_skill_model.embeddings._calls
        assert len(embedding_calls) >= 1

    @pytest.mark.asyncio
    async def test_skill_embedding_triggered_after_tool_assignment(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that skill embedding is triggered when tool is assigned."""
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "embed-trigger-skill",
            "name": "Embed Trigger Skill",
            "description": "Skill for testing embedding trigger",
        })

        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "embed-trigger-skill", "confidence": 0.9, "reasoning": "Match"},
            ],
            "primary_skill_id": "embed-trigger-skill",
            "suggested_new_skill": None,
        }))

        # Clear previous calls
        mock_skill_model.embeddings._calls.clear()

        # Act - classify tool (triggers embedding update)
        await skill_service.classify_tool(
            tool_id=1,
            tool_name="test_tool",
            tool_description="Test tool"
        )

        # Assert - embedding was triggered (may be called multiple times)
        # The service calls _trigger_skill_embedding_update after assignment
        embedding_calls = mock_skill_model.embeddings._calls
        assert len(embedding_calls) >= 1


# ═══════════════════════════════════════════════════════════════
# BR-006: Manual Assignment Override
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
class TestBR006ManualAssignmentOverride:
    """
    BR-006: Manual Assignment Override

    Given: Admin manually assigns tool to skills
    When: Manual assignment is created
    Then:
    - Source = human_manual or human_override
    - Overwrites any LLM assignments
    - Prevents re-classification on next sync
    """

    @pytest.mark.asyncio
    async def test_manual_assignment_overwrites_llm(
        self, skill_service, mock_skill_repository
    ):
        """Test that manual assignment replaces LLM assignments."""
        # Arrange - create skills and LLM assignment
        await mock_skill_repository.create_skill_category({
            "id": "llm-assigned-skill",
            "name": "LLM Assigned",
            "description": "Originally assigned by LLM",
        })
        await mock_skill_repository.create_skill_category({
            "id": "manual-skill",
            "name": "Manual Skill",
            "description": "Manually assigned skill",
        })
        await mock_skill_repository.create_assignment(
            tool_id=1,
            skill_id="llm-assigned-skill",
            confidence=0.8,
            is_primary=True,
            source="llm_auto"
        )

        # Act - manual assignment
        result = await skill_service.assign_tool_to_skills(
            tool_id=1,
            skill_ids=["manual-skill"],
            primary_skill_id="manual-skill",
            source="human_override"
        )

        # Assert
        assert len(result) == 1
        assert result[0]["skill_id"] == "manual-skill"
        assert result[0]["source"] == "human_override"

        # Verify old assignments were deleted
        delete_calls = mock_skill_repository.get_calls("delete_assignments_for_tool")
        assert len(delete_calls) >= 1

    @pytest.mark.asyncio
    async def test_manual_assignment_sets_correct_source(
        self, skill_service, mock_skill_repository
    ):
        """Test that manual assignments have source=human_manual."""
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "manual-test-skill",
            "name": "Manual Test Skill",
            "description": "Skill for manual assignment test",
        })

        # Act
        result = await skill_service.assign_tool_to_skills(
            tool_id=1,
            skill_ids=["manual-test-skill"],
            primary_skill_id="manual-test-skill",
            source="human_manual"
        )

        # Assert
        assert result[0]["source"] == "human_manual"
        assert result[0]["confidence"] == 1.0  # Human assignments have full confidence

    @pytest.mark.asyncio
    async def test_manual_assignment_requires_valid_skill(
        self, skill_service, mock_skill_repository
    ):
        """Test that manual assignment fails for non-existent skill."""
        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await skill_service.assign_tool_to_skills(
                tool_id=1,
                skill_ids=["nonexistent-skill"],
                primary_skill_id="nonexistent-skill"
            )
        assert "not found" in str(exc.value)


# ═══════════════════════════════════════════════════════════════
# BR-007: Skill Listing and Filtering
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
class TestBR007SkillListingFiltering:
    """
    BR-007: Skill Listing and Filtering

    Given: Request to list skill categories
    When: User queries skills
    Then:
    - Returns all skills matching filter criteria
    - Supports filtering by is_active, parent_domain
    - Returns tool_count for each skill
    """

    @pytest.mark.asyncio
    async def test_list_skills_returns_active_by_default(
        self, skill_service, mock_skill_repository
    ):
        """Test that list_skills returns only active skills by default."""
        # Arrange - create active and inactive skills
        await mock_skill_repository.create_skill_category({
            "id": "active-skill",
            "name": "Active Skill",
            "description": "An active skill",
            "is_active": True,
        })
        # Directly modify to set inactive
        mock_skill_repository.skills["inactive-skill"] = {
            "id": "inactive-skill",
            "name": "Inactive Skill",
            "description": "An inactive skill",
            "is_active": False,
            "tool_count": 0,
        }

        # Act
        result = await skill_service.list_skills()

        # Assert - only active returned by default
        assert len(result) == 1
        assert result[0]["id"] == "active-skill"

    @pytest.mark.asyncio
    async def test_list_skills_filters_by_parent_domain(
        self, skill_service, mock_skill_repository
    ):
        """Test that skills can be filtered by parent_domain."""
        # Arrange - create skills in different domains
        await mock_skill_repository.create_skill_category({
            "id": "productivity-skill",
            "name": "Productivity Skill",
            "description": "A productivity skill",
            "parent_domain": "productivity",
        })
        await mock_skill_repository.create_skill_category({
            "id": "development-skill",
            "name": "Development Skill",
            "description": "A development skill",
            "parent_domain": "development",
        })

        # Act - filter by productivity
        result = await skill_service.list_skills(parent_domain="productivity")

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "productivity-skill"

    @pytest.mark.asyncio
    async def test_list_skills_includes_tool_count(
        self, skill_service, mock_skill_repository
    ):
        """Test that each skill includes tool_count."""
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "counted-skill",
            "name": "Counted Skill",
            "description": "A skill with tool count",
        })
        # Increment tool count
        await mock_skill_repository.increment_tool_count("counted-skill", 5)

        # Act
        result = await skill_service.list_skills()

        # Assert
        assert len(result) == 1
        assert "tool_count" in result[0]
        assert result[0]["tool_count"] == 5

    @pytest.mark.asyncio
    async def test_list_skills_with_pagination(
        self, skill_service, mock_skill_repository
    ):
        """Test that list_skills supports pagination."""
        # Arrange - create multiple skills
        for i in range(5):
            await mock_skill_repository.create_skill_category({
                "id": f"skill_{i:02d}",
                "name": f"Skill {i}",
                "description": f"Description for skill {i}",
            })

        # Act - get second page
        result = await skill_service.list_skills(limit=2, offset=2)

        # Assert
        assert len(result) == 2


# ═══════════════════════════════════════════════════════════════
# BR-008: Get Tools by Skill
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
class TestBR008GetToolsBySkill:
    """
    BR-008: Get Tools by Skill

    Given: Valid skill_id
    When: User requests tools for a skill
    Then:
    - Returns all tools assigned to the skill
    - Includes assignment metadata (confidence, is_primary)
    - Sorted by confidence DESC
    """

    @pytest.mark.asyncio
    async def test_get_tools_by_skill_success(
        self, skill_service, mock_skill_repository
    ):
        """Test successful retrieval of tools by skill."""
        # Arrange - create skill with tool assignments
        await mock_skill_repository.create_skill_category({
            "id": "tools-skill",
            "name": "Tools Skill",
            "description": "A skill with tools",
        })
        await mock_skill_repository.create_assignment(
            tool_id=1,
            skill_id="tools-skill",
            confidence=0.9,
            is_primary=True,
            source="llm_auto"
        )
        await mock_skill_repository.create_assignment(
            tool_id=2,
            skill_id="tools-skill",
            confidence=0.7,
            is_primary=False,
            source="llm_auto"
        )

        # Act
        result = await skill_service.get_tools_by_skill("tools-skill")

        # Assert
        assert len(result) == 2
        # Sorted by confidence DESC
        assert result[0]["confidence"] >= result[1]["confidence"]

    @pytest.mark.asyncio
    async def test_get_tools_by_skill_not_found(
        self, skill_service, mock_skill_repository
    ):
        """Test that unknown skill_id raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await skill_service.get_tools_by_skill("nonexistent-skill")
        assert "not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_tools_by_skill_empty_returns_empty_list(
        self, skill_service, mock_skill_repository
    ):
        """Test that skill with no tools returns empty list."""
        # Arrange - create skill without assignments
        await mock_skill_repository.create_skill_category({
            "id": "empty-skill",
            "name": "Empty Skill",
            "description": "A skill with no tools",
        })

        # Act
        result = await skill_service.get_tools_by_skill("empty-skill")

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_tools_by_skill_with_pagination(
        self, skill_service, mock_skill_repository
    ):
        """Test that get_tools_by_skill supports pagination."""
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "paginated-skill",
            "name": "Paginated Skill",
            "description": "Skill for pagination test",
        })
        for i in range(5):
            await mock_skill_repository.create_assignment(
                tool_id=i + 1,
                skill_id="paginated-skill",
                confidence=0.9 - i * 0.1,
                is_primary=(i == 0),
                source="llm_auto"
            )

        # Act - get with limit
        result = await skill_service.get_tools_by_skill("paginated-skill", limit=3)

        # Assert
        assert len(result) == 3


# ═══════════════════════════════════════════════════════════════
# Edge Cases (from logic_contract.md)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
class TestEdgeCases:
    """Edge case tests from logic contract EC-XXX."""

    @pytest.mark.asyncio
    async def test_EC001_concurrent_classification_last_write_wins(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """
        EC-001: Concurrent Classification

        Scenario: Same tool classified by multiple sync processes
        Expected: Last write wins, no duplicates
        """
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "concurrent-skill",
            "name": "Concurrent Skill",
            "description": "Skill for concurrent test",
        })

        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "concurrent-skill", "confidence": 0.9, "reasoning": "Match"},
            ],
            "primary_skill_id": "concurrent-skill",
            "suggested_new_skill": None,
        }))

        # Act - classify twice (simulating concurrent)
        await skill_service.classify_tool(
            tool_id=1,
            tool_name="test",
            tool_description="Test"
        )
        await skill_service.classify_tool(
            tool_id=1,
            tool_name="test",
            tool_description="Test",
            force_reclassify=True
        )

        # Assert - should have exactly one assignment (last write wins)
        assignments = await mock_skill_repository.get_assignments_for_tool(1)
        assert len(assignments) == 1

    @pytest.mark.asyncio
    async def test_EC003_llm_hallucination_rejected(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """
        EC-003: LLM Hallucination

        Scenario: LLM returns non-existent skill_id
        Expected: Assignment rejected, skill_id validated
        """
        # Arrange - only create one skill
        await mock_skill_repository.create_skill_category({
            "id": "real-skill",
            "name": "Real Skill",
            "description": "A real skill",
        })

        # Mock LLM returning hallucinated skill_id
        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "hallucinated-skill", "confidence": 0.99, "reasoning": "Made up"},
                {"skill_id": "real-skill", "confidence": 0.7, "reasoning": "Actually exists"},
            ],
            "primary_skill_id": "hallucinated-skill",
            "suggested_new_skill": None,
        }))

        # Act
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="test",
            tool_description="Test tool"
        )

        # Assert - hallucinated skill filtered out, only real skill remains
        skill_ids = [a["skill_id"] for a in result["assignments"]]
        assert "hallucinated-skill" not in skill_ids
        assert "real-skill" in skill_ids

    @pytest.mark.asyncio
    async def test_EC006_very_long_tool_description_truncated(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """
        EC-006: Very Long Tool Description

        Scenario: Tool description > 10000 chars
        Expected: Classification works with truncated description
        """
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "long-desc-skill",
            "name": "Long Desc Skill",
            "description": "Skill for long description test",
        })

        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "long-desc-skill", "confidence": 0.8, "reasoning": "Match"},
            ],
            "primary_skill_id": "long-desc-skill",
            "suggested_new_skill": None,
        }))

        # Very long description
        long_description = "A" * 15000

        # Act - should not fail
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="long_tool",
            tool_description=long_description
        )

        # Assert - classification succeeded
        assert result["primary_skill_id"] == "long-desc-skill"

    @pytest.mark.asyncio
    async def test_EC007_empty_assignments_list(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """
        EC-007: LLM returns empty assignments

        Scenario: LLM cannot match any skill
        Expected: Empty assignments returned, suggestion may be created
        """
        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "unrelated-skill",
            "name": "Unrelated Skill",
            "description": "Completely unrelated skill",
        })

        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [],
            "primary_skill_id": None,
            "suggested_new_skill": None,
        }))

        # Act
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="unique_tool",
            tool_description="A very unique tool"
        )

        # Assert
        assert len(result["assignments"]) == 0
        assert result["primary_skill_id"] is None


# ═══════════════════════════════════════════════════════════════
# Performance Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.skill
@pytest.mark.slow
class TestPerformanceSLAs:
    """Performance tests based on SLAs from logic contract."""

    @pytest.mark.asyncio
    async def test_create_skill_under_100ms(
        self, skill_service, mock_skill_repository
    ):
        """Test that create_skill completes in < 100ms (target p95)."""
        import time

        skill_data = {
            "id": "perf_test_skill",
            "name": "Performance Test Skill",
            "description": "A skill for performance testing",
        }

        start = time.perf_counter()
        await skill_service.create_skill_category(skill_data)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        # With mocks, should be well under 100ms
        assert elapsed < 100, f"create_skill took {elapsed:.2f}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_list_skills_under_50ms(
        self, skill_service, mock_skill_repository
    ):
        """Test that list_skills completes in < 50ms (target p95)."""
        import time

        # Seed some skills
        for i in range(10):
            await mock_skill_repository.create_skill_category({
                "id": f"perf_skill_{i}",
                "name": f"Perf Skill {i}",
                "description": f"Performance skill {i}",
            })

        start = time.perf_counter()
        await skill_service.list_skills()
        elapsed = (time.perf_counter() - start) * 1000  # ms

        # With mocks, should be well under 50ms
        assert elapsed < 50, f"list_skills took {elapsed:.2f}ms, expected < 50ms"

    @pytest.mark.asyncio
    async def test_classify_tool_completes(
        self, skill_service, mock_skill_repository, mock_skill_model
    ):
        """Test that classify_tool completes successfully (LLM mocked)."""
        import time

        # Arrange
        await mock_skill_repository.create_skill_category({
            "id": "perf-classify-skill",
            "name": "Perf Classify Skill",
            "description": "Skill for classification perf test",
        })

        mock_skill_model.set_completion_response(json.dumps({
            "assignments": [
                {"skill_id": "perf-classify-skill", "confidence": 0.9, "reasoning": "Match"},
            ],
            "primary_skill_id": "perf-classify-skill",
            "suggested_new_skill": None,
        }))

        start = time.perf_counter()
        result = await skill_service.classify_tool(
            tool_id=1,
            tool_name="perf_tool",
            tool_description="Performance test tool"
        )
        elapsed = (time.perf_counter() - start) * 1000  # ms

        # With mocked LLM, should complete quickly
        assert result is not None
        assert elapsed < 1000, f"classify_tool took {elapsed:.2f}ms"
