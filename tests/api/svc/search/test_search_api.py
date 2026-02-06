"""
Search Service API Tests

API endpoint tests for the Hierarchical Search Service.
Tests the HTTP interface for search operations.

Requirements:
    - Running MCP server
    - TEST_MCP_URL environment variable set
"""
import pytest
import httpx

from tests.contracts.search.data_contract import (
    SearchTestDataFactory,
    HierarchicalSearchRequestContract,
    HierarchicalSearchResponseContract,
    HierarchicalSearchRequestBuilder,
    SearchItemType,
    SearchStrategy,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
async def api_client(test_config):
    """Create async HTTP client for API tests."""
    async with httpx.AsyncClient(
        base_url=test_config.get("mcp_url", "http://localhost:8081"),
        timeout=30.0
    ) as client:
        yield client


# ═══════════════════════════════════════════════════════════════
# POST /api/v1/search - Hierarchical Search
# ═══════════════════════════════════════════════════════════════

@pytest.mark.api
@pytest.mark.search
class TestHierarchicalSearchAPI:
    """API tests for POST /api/v1/search."""

    @pytest.mark.asyncio
    async def test_search_returns_200(self, api_client):
        """Test that search returns 200 OK with valid query."""
        request_data = SearchTestDataFactory.make_search_request(
            query="schedule a meeting"
        ).model_dump()

        response = await api_client.post("/api/v1/search", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "tools" in data
        assert "matched_skills" in data
        assert "metadata" in data

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_422(self, api_client):
        """Test that empty query returns 422 Validation Error."""
        request_data = {"query": "", "limit": 5}
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_query_too_long_returns_422(self, api_client):
        """Test that query > 1000 chars returns 422."""
        request_data = {"query": "a" * 1001}
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_invalid_threshold_returns_422(self, api_client):
        """Test that invalid threshold returns 422."""
        request_data = {"query": "test", "skill_threshold": 1.5}  # > 1.0
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_limit_too_high_returns_422(self, api_client):
        """Test that limit > 50 returns 422."""
        request_data = {"query": "test", "limit": 100}
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_with_item_type_filter(self, api_client):
        """Test that item_type filter works."""
        request_data = {
            "query": "schedule meeting",
            "item_type": "tool",
        }
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 200
        data = response.json()
        # All results should be tools
        assert all(t["type"] == "tool" for t in data["tools"])

    @pytest.mark.asyncio
    async def test_search_direct_strategy(self, api_client):
        """Test that direct strategy bypasses skills."""
        request_data = {
            "query": "test query",
            "strategy": "direct",
        }
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["strategy_used"] == "direct"
        assert data["matched_skills"] == []

    @pytest.mark.asyncio
    async def test_search_without_schemas(self, api_client):
        """Test that include_schemas=false skips schema loading."""
        request_data = {
            "query": "test query",
            "include_schemas": False,
        }
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 200
        data = response.json()
        # Schemas should be null
        for tool in data["tools"]:
            assert tool.get("input_schema") is None

    @pytest.mark.asyncio
    async def test_search_response_structure(self, api_client):
        """Test that response matches contract structure."""
        request_data = {"query": "test query"}
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 200
        data = response.json()
        # Validate against contract
        validated = HierarchicalSearchResponseContract(**data)
        assert validated.query == "test query"

    @pytest.mark.asyncio
    async def test_search_includes_metadata(self, api_client):
        """Test that response includes timing metadata."""
        request_data = {"query": "test query"}
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 200
        data = response.json()
        metadata = data["metadata"]
        assert "strategy_used" in metadata
        assert "skill_ids_used" in metadata
        assert "stage1_skill_count" in metadata
        assert "total_time_ms" in metadata
        assert metadata["total_time_ms"] >= 0


# ═══════════════════════════════════════════════════════════════
# GET /api/v1/search/skills - Search Skills Only
# ═══════════════════════════════════════════════════════════════

@pytest.mark.api
@pytest.mark.search
class TestSearchSkillsAPI:
    """API tests for GET /api/v1/search/skills."""

    @pytest.mark.asyncio
    async def test_skill_search_returns_200(self, api_client):
        """Test that skill-only search returns 200 OK."""
        response = await api_client.get(
            "/api/v1/search/skills",
            params={"query": "calendar scheduling"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_skill_search_respects_limit(self, api_client):
        """Test that skill search respects limit parameter."""
        response = await api_client.get(
            "/api/v1/search/skills",
            params={"query": "test", "limit": 2}
        )
        assert response.status_code == 200
        assert len(response.json()) <= 2

    @pytest.mark.asyncio
    async def test_skill_search_respects_threshold(self, api_client):
        """Test that skill search respects threshold parameter."""
        response = await api_client.get(
            "/api/v1/search/skills",
            params={"query": "test", "threshold": 0.8}
        )
        assert response.status_code == 200
        # All scores should be >= threshold
        for skill in response.json():
            assert skill["score"] >= 0.8


# ═══════════════════════════════════════════════════════════════
# GET /api/v1/search/tools - Search Tools Only
# ═══════════════════════════════════════════════════════════════

@pytest.mark.api
@pytest.mark.search
class TestSearchToolsAPI:
    """API tests for GET /api/v1/search/tools."""

    @pytest.mark.asyncio
    async def test_tool_search_returns_200(self, api_client):
        """Test that tool search returns 200 OK."""
        response = await api_client.get(
            "/api/v1/search/tools",
            params={"query": "create event"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_tool_search_with_skill_filter(self, api_client):
        """Test that tool search can filter by skill IDs."""
        response = await api_client.get(
            "/api/v1/search/tools",
            params={
                "query": "create",
                "skill_ids": "calendar-management,search-retrieval"
            }
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_tool_search_with_item_type(self, api_client):
        """Test that tool search can filter by item type."""
        response = await api_client.get(
            "/api/v1/search/tools",
            params={"query": "test", "item_type": "tool"}
        )
        assert response.status_code == 200
        for item in response.json():
            assert item["type"] == "tool"


# ═══════════════════════════════════════════════════════════════
# Error Handling Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.api
@pytest.mark.search
class TestSearchErrorHandling:
    """API tests for search error handling."""

    @pytest.mark.asyncio
    async def test_missing_query_returns_422(self, api_client):
        """Test that missing query returns 422."""
        response = await api_client.post("/api/v1/search", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_strategy_returns_422(self, api_client):
        """Test that invalid strategy value returns 422."""
        request_data = {"query": "test", "strategy": "invalid_strategy"}
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_item_type_returns_422(self, api_client):
        """Test that invalid item_type returns 422."""
        request_data = {"query": "test", "item_type": "invalid_type"}
        response = await api_client.post("/api/v1/search", json=request_data)
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Performance Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.api
@pytest.mark.search
@pytest.mark.slow
class TestSearchAPIPerformance:
    """API tests for search performance."""

    @pytest.mark.asyncio
    async def test_search_response_time_under_1s(self, api_client):
        """Test that search API responds under 1 second."""
        import time

        request_data = {"query": "schedule a meeting"}

        start = time.time()
        response = await api_client.post("/api/v1/search", json=request_data)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 2.0  # Under 2 seconds (allowing for network latency)

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, api_client):
        """Test that API handles concurrent searches."""
        import asyncio

        async def make_search(query):
            return await api_client.post(
                "/api/v1/search",
                json={"query": query}
            )

        queries = ["schedule meeting", "query data", "send email", "read file", "search web"]

        responses = await asyncio.gather(*[make_search(q) for q in queries])

        assert all(r.status_code == 200 for r in responses)
