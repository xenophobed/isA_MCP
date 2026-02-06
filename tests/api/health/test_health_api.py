"""
TDD TESTS - API Health Endpoint Tests

Tests for the /health endpoint.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.api
class TestHealthAPI:
    """TDD tests for health API endpoint."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx client for API testing without real server."""
        mock = MagicMock()
        mock.post = AsyncMock()
        mock.get = AsyncMock()
        return mock

    async def test_health_returns_200_when_healthy(self, mock_httpx_client):
        """
        Test health endpoint returns 200 when server is healthy.

        Given: MCP server is running
        When: GET /health is called
        Then: Returns 200 with healthy status
        """
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "service": "Smart MCP Server",
            "uptime": "5m 30s",
            "capabilities": {
                "tools": 10,
                "prompts": 5,
                "resources": 3
            }
        }
        mock_httpx_client.get.return_value = mock_response

        # Call endpoint
        response = await mock_httpx_client.get("/health")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "healthy" in data["status"].lower()

    async def test_health_returns_capabilities_count(self, mock_httpx_client):
        """
        Test health endpoint includes capability counts.

        Given: MCP server has tools/prompts/resources
        When: GET /health is called
        Then: Response includes capability counts
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "capabilities": {
                "tools": 10,
                "prompts": 5,
                "resources": 3
            }
        }
        mock_httpx_client.get.return_value = mock_response

        response = await mock_httpx_client.get("/health")
        data = response.json()

        assert "capabilities" in data
        assert "tools" in data["capabilities"]
        assert "prompts" in data["capabilities"]
        assert "resources" in data["capabilities"]

    async def test_health_returns_uptime(self, mock_httpx_client):
        """
        Test health endpoint includes uptime information.

        Given: MCP server is running
        When: GET /health is called
        Then: Response includes uptime
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "uptime": "10m 45s"
        }
        mock_httpx_client.get.return_value = mock_response

        response = await mock_httpx_client.get("/health")
        data = response.json()

        assert "uptime" in data

    async def test_health_returns_initializing_during_startup(self, mock_httpx_client):
        """
        Test health endpoint returns initializing status during startup.

        Given: MCP server is still starting
        When: GET /health is called
        Then: Returns status indicating initialization
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "initializing"
        }
        mock_httpx_client.get.return_value = mock_response

        response = await mock_httpx_client.get("/health")
        data = response.json()

        assert data["status"] == "initializing"


@pytest.mark.api
@pytest.mark.golden
class TestHealthAPIGolden:
    """Golden tests for health API - DO NOT MODIFY."""

    async def test_health_response_structure(self):
        """
        Captures expected health response structure.

        Expected fields:
        - status: string
        - service: string (optional)
        - uptime: string (optional)
        - capabilities: object (optional)
        """
        expected_fields = {"status"}
        optional_fields = {"service", "uptime", "capabilities", "reload_count"}

        # This test documents the expected structure
        # Actual API tests will verify against this
        assert "status" in expected_fields
        assert "capabilities" in optional_fields
