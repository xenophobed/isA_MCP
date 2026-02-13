"""
Skill Service API Tests

API endpoint tests for the Skill Service.
Tests the HTTP interface for skill management operations.

Requirements:
    - Running MCP server
    - TEST_MCP_URL environment variable set
"""

import pytest
import httpx

from tests.contracts.skill.data_contract import (
    SkillTestDataFactory,
)

# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def api_client(test_config):
    """Create async HTTP client for API tests."""
    async with httpx.AsyncClient(
        base_url=test_config.get("mcp_url", "http://localhost:8081"), timeout=30.0
    ) as client:
        yield client


@pytest.fixture
async def created_skill(api_client):
    """Create a skill for testing and clean up after."""
    skill_data = SkillTestDataFactory.make_skill_category(
        id="api_test_skill",
        name="API Test Skill",
        description="A skill created for API testing purposes",
    ).model_dump()

    response = await api_client.post("/api/v1/skills", json=skill_data)
    if response.status_code == 201:
        yield response.json()
        # Cleanup
        await api_client.delete("/api/v1/skills/api_test_skill")
    else:
        pytest.skip("Could not create test skill")


# ═══════════════════════════════════════════════════════════════
# POST /api/v1/skills - Create Skill Category
# ═══════════════════════════════════════════════════════════════


@pytest.mark.api
@pytest.mark.skill
class TestCreateSkillAPI:
    """API tests for POST /api/v1/skills."""

    @pytest.mark.asyncio
    async def test_create_skill_returns_201(self, api_client):
        """Test that creating a skill returns 201 Created."""
        skill_data = SkillTestDataFactory.make_skill_category(
            id="create_test_skill",
            name="Create Test Skill",
            description="A skill for testing creation purposes only",
        ).model_dump()

        response = await api_client.post("/api/v1/skills", json=skill_data)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "create_test_skill"

        # Cleanup
        await api_client.delete("/api/v1/skills/create_test_skill")

    @pytest.mark.asyncio
    async def test_create_skill_duplicate_returns_409(self, api_client, created_skill):
        """Test that creating duplicate skill returns 409 Conflict."""
        skill_data = SkillTestDataFactory.make_skill_category(
            id=created_skill["id"],  # Same ID
            name="Duplicate Skill",
            description="Trying to create duplicate skill for testing",
        ).model_dump()

        response = await api_client.post("/api/v1/skills", json=skill_data)

        assert response.status_code == 409
        assert "already exists" in response.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_create_skill_invalid_id_returns_422(self, api_client):
        """Test that invalid skill ID returns 422 Validation Error."""
        invalid_data = SkillTestDataFactory.make_invalid_skill_invalid_id_format()
        response = await api_client.post("/api/v1/skills", json=invalid_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_skill_short_description_returns_422(self, api_client):
        """Test that short description returns 422 Validation Error."""
        invalid_data = SkillTestDataFactory.make_invalid_skill_short_description()
        response = await api_client.post("/api/v1/skills", json=invalid_data)
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# GET /api/v1/skills - List Skills
# ═══════════════════════════════════════════════════════════════


@pytest.mark.api
@pytest.mark.skill
class TestListSkillsAPI:
    """API tests for GET /api/v1/skills."""

    @pytest.mark.asyncio
    async def test_list_skills_returns_200(self, api_client):
        """Test that listing skills returns 200 OK."""
        response = await api_client.get("/api/v1/skills")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_skills_filters_by_active(self, api_client, created_skill):
        """Test that skills can be filtered by is_active."""
        response = await api_client.get("/api/v1/skills", params={"is_active": "true"})
        assert response.status_code == 200
        skills = response.json()
        assert all(s.get("is_active", True) for s in skills)

    @pytest.mark.asyncio
    async def test_list_skills_filters_by_domain(self, api_client):
        """Test that skills can be filtered by parent_domain."""
        response = await api_client.get("/api/v1/skills", params={"parent_domain": "productivity"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_skills_respects_pagination(self, api_client):
        """Test that pagination parameters are respected."""
        response = await api_client.get("/api/v1/skills", params={"limit": 5, "offset": 0})
        assert response.status_code == 200
        assert len(response.json()) <= 5


# ═══════════════════════════════════════════════════════════════
# GET /api/v1/skills/{skill_id} - Get Skill
# ═══════════════════════════════════════════════════════════════


@pytest.mark.api
@pytest.mark.skill
class TestGetSkillAPI:
    """API tests for GET /api/v1/skills/{skill_id}."""

    @pytest.mark.asyncio
    async def test_get_skill_returns_200(self, api_client, created_skill):
        """Test that getting a skill by ID returns 200 OK."""
        response = await api_client.get(f"/api/v1/skills/{created_skill['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_skill["id"]

    @pytest.mark.asyncio
    async def test_get_skill_not_found_returns_404(self, api_client):
        """Test that unknown skill ID returns 404 Not Found."""
        response = await api_client.get("/api/v1/skills/nonexistent_skill_xyz")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════
# GET /api/v1/skills/{skill_id}/tools - Get Tools in Skill
# ═══════════════════════════════════════════════════════════════


@pytest.mark.api
@pytest.mark.skill
class TestGetToolsInSkillAPI:
    """API tests for GET /api/v1/skills/{skill_id}/tools."""

    @pytest.mark.asyncio
    async def test_get_tools_returns_200(self, api_client, created_skill):
        """Test that getting tools in a skill returns 200 OK."""
        response = await api_client.get(f"/api/v1/skills/{created_skill['id']}/tools")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_tools_skill_not_found_returns_404(self, api_client):
        """Test that unknown skill ID returns 404."""
        response = await api_client.get("/api/v1/skills/nonexistent_xyz/tools")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_tools_empty_skill_returns_empty_list(self, api_client, created_skill):
        """Test that skill with no tools returns empty list."""
        response = await api_client.get(f"/api/v1/skills/{created_skill['id']}/tools")
        assert response.status_code == 200
        assert response.json() == []


# ═══════════════════════════════════════════════════════════════
# POST /api/v1/skills/classify - Classify Tool
# ═══════════════════════════════════════════════════════════════


@pytest.mark.api
@pytest.mark.skill
class TestClassifyToolAPI:
    """API tests for POST /api/v1/skills/classify."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_classify_tool_returns_200(self, api_client, created_skill):
        """Test that classifying a tool returns 200 OK."""
        classify_request = {
            "tool_id": 1,
            "tool_name": "create_event",
            "tool_description": "Create a calendar event with specified date and time",
        }
        response = await api_client.post("/api/v1/skills/classify", json=classify_request)
        assert response.status_code == 200
        data = response.json()
        assert "assignments" in data
        assert "primary_skill_id" in data

    @pytest.mark.asyncio
    async def test_classify_tool_missing_fields_returns_422(self, api_client):
        """Test that missing required fields returns 422."""
        incomplete_request = {"tool_name": "test"}  # Missing tool_id, tool_description
        response = await api_client.post("/api/v1/skills/classify", json=incomplete_request)
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# GET /api/v1/skills/suggestions - List Pending Suggestions
# ═══════════════════════════════════════════════════════════════


@pytest.mark.api
@pytest.mark.skill
class TestSkillSuggestionsAPI:
    """API tests for skill suggestion endpoints."""

    @pytest.mark.asyncio
    async def test_list_suggestions_returns_200(self, api_client):
        """Test that listing suggestions returns 200 OK."""
        response = await api_client.get("/api/v1/skills/suggestions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_approve_suggestion_creates_skill(self, api_client):
        """Test that approving a suggestion creates the skill."""
        pytest.skip("Approve suggestion endpoint not yet implemented")

    @pytest.mark.asyncio
    async def test_reject_suggestion_removes_it(self, api_client):
        """Test that rejecting a suggestion removes it."""
        pytest.skip("Reject suggestion endpoint not yet implemented")
