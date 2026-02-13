"""
Aggregator Service API Tests

API endpoint tests for the MCP Server Aggregator.
Tests the HTTP interface for aggregator operations.

Requirements:
    - Running MCP server
    - TEST_MCP_URL environment variable set
"""

import pytest
import httpx
import uuid

from tests.contracts.aggregator.data_contract import (
    AggregatorTestDataFactory,
    ServerRegistrationRequestContract,
    ServerRecordContract,
    ServerTransportType,
    ServerStatus,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def api_client(test_config):
    """Create async HTTP client for API tests."""
    async with httpx.AsyncClient(
        base_url=test_config.get("mcp_url", "http://localhost:8081"), timeout=30.0
    ) as client:
        yield client


@pytest.fixture
async def created_server(api_client):
    """Create a server for testing and clean up after."""
    server_data = AggregatorTestDataFactory.make_sse_server_registration(
        name=f"api-test-server-{uuid.uuid4().hex[:8]}",
        auto_connect=False,
    ).model_dump()

    # Convert enum to string for JSON
    server_data["transport_type"] = server_data["transport_type"].value

    response = await api_client.post("/api/v1/aggregator/servers", json=server_data)
    if response.status_code == 201:
        server = response.json()
        yield server
        # Cleanup
        await api_client.delete(f"/api/v1/aggregator/servers/{server['id']}")
    else:
        pytest.skip(f"Could not create test server: {response.text}")


# ============================================================================
# POST /api/v1/aggregator/servers - Register Server
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestRegisterServerAPI:
    """API tests for POST /api/v1/aggregator/servers."""

    @pytest.mark.asyncio
    async def test_register_server_returns_201(self, api_client):
        """Test that registering a server returns 201 Created."""
        server_data = AggregatorTestDataFactory.make_sse_server_registration(
            name=f"register-test-{uuid.uuid4().hex[:8]}",
            auto_connect=False,
        ).model_dump()
        server_data["transport_type"] = server_data["transport_type"].value

        response = await api_client.post("/api/v1/aggregator/servers", json=server_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == server_data["name"]
        assert "id" in data

        # Cleanup
        await api_client.delete(f"/api/v1/aggregator/servers/{data['id']}")

    @pytest.mark.asyncio
    async def test_register_duplicate_server_returns_409(self, api_client, created_server):
        """Test that registering duplicate server returns 409 Conflict."""
        server_data = AggregatorTestDataFactory.make_sse_server_registration(
            name=created_server["name"],  # Same name
            auto_connect=False,
        ).model_dump()
        server_data["transport_type"] = server_data["transport_type"].value

        response = await api_client.post("/api/v1/aggregator/servers", json=server_data)

        assert response.status_code == 409
        assert "already exists" in response.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_register_server_invalid_name_returns_422(self, api_client):
        """Test that invalid server name returns 422 Validation Error."""
        invalid_data = {
            "name": "123-invalid",  # Starts with number
            "transport_type": "sse",
            "connection_config": {"url": "https://example.com/sse"},
        }
        response = await api_client.post("/api/v1/aggregator/servers", json=invalid_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_stdio_server(self, api_client):
        """Test registering STDIO server."""
        server_data = AggregatorTestDataFactory.make_stdio_server_registration(
            name=f"stdio-test-{uuid.uuid4().hex[:8]}",
        ).model_dump()
        server_data["transport_type"] = server_data["transport_type"].value

        response = await api_client.post("/api/v1/aggregator/servers", json=server_data)

        assert response.status_code == 201
        data = response.json()
        assert data["transport_type"] == "stdio"

        # Cleanup
        await api_client.delete(f"/api/v1/aggregator/servers/{data['id']}")


# ============================================================================
# GET /api/v1/aggregator/servers - List Servers
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestListServersAPI:
    """API tests for GET /api/v1/aggregator/servers."""

    @pytest.mark.asyncio
    async def test_list_servers_returns_200(self, api_client):
        """Test that listing servers returns 200 OK."""
        response = await api_client.get("/api/v1/aggregator/servers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_servers_filters_by_status(self, api_client, created_server):
        """Test that servers can be filtered by status."""
        response = await api_client.get(
            "/api/v1/aggregator/servers", params={"status": "disconnected"}
        )
        assert response.status_code == 200
        servers = response.json()
        for server in servers:
            assert server["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_list_servers_includes_created(self, api_client, created_server):
        """Test that created server appears in list."""
        response = await api_client.get("/api/v1/aggregator/servers")
        assert response.status_code == 200
        servers = response.json()
        server_ids = [s["id"] for s in servers]
        assert created_server["id"] in server_ids


# ============================================================================
# GET /api/v1/aggregator/servers/{id} - Get Server
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestGetServerAPI:
    """API tests for GET /api/v1/aggregator/servers/{id}."""

    @pytest.mark.asyncio
    async def test_get_server_returns_200(self, api_client, created_server):
        """Test that getting a server by ID returns 200 OK."""
        response = await api_client.get(f"/api/v1/aggregator/servers/{created_server['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_server["id"]
        assert data["name"] == created_server["name"]

    @pytest.mark.asyncio
    async def test_get_server_not_found_returns_404(self, api_client):
        """Test that unknown server ID returns 404 Not Found."""
        fake_id = str(uuid.uuid4())
        response = await api_client.get(f"/api/v1/aggregator/servers/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# DELETE /api/v1/aggregator/servers/{id} - Remove Server
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestRemoveServerAPI:
    """API tests for DELETE /api/v1/aggregator/servers/{id}."""

    @pytest.mark.asyncio
    async def test_remove_server_returns_204(self, api_client):
        """Test that removing a server returns 204 No Content."""
        # Create server to remove
        server_data = AggregatorTestDataFactory.make_sse_server_registration(
            name=f"remove-test-{uuid.uuid4().hex[:8]}",
            auto_connect=False,
        ).model_dump()
        server_data["transport_type"] = server_data["transport_type"].value

        create_response = await api_client.post("/api/v1/aggregator/servers", json=server_data)
        server_id = create_response.json()["id"]

        # Remove it
        response = await api_client.delete(f"/api/v1/aggregator/servers/{server_id}")
        assert response.status_code in (200, 204)

        # Verify removed
        get_response = await api_client.get(f"/api/v1/aggregator/servers/{server_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_nonexistent_server_returns_404(self, api_client):
        """Test that removing non-existent server returns 404."""
        fake_id = str(uuid.uuid4())
        response = await api_client.delete(f"/api/v1/aggregator/servers/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# POST /api/v1/aggregator/servers/{id}/connect - Connect Server
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestConnectServerAPI:
    """API tests for POST /api/v1/aggregator/servers/{id}/connect."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_connect_server_returns_200(self, api_client, created_server):
        """Test that connecting a server returns 200 OK."""
        response = await api_client.post(
            f"/api/v1/aggregator/servers/{created_server['id']}/connect"
        )
        # May return 200 (success) or 503 (server unreachable)
        assert response.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_connect_nonexistent_server_returns_404(self, api_client):
        """Test that connecting non-existent server returns 404."""
        fake_id = str(uuid.uuid4())
        response = await api_client.post(f"/api/v1/aggregator/servers/{fake_id}/connect")
        assert response.status_code == 404


# ============================================================================
# POST /api/v1/aggregator/servers/{id}/disconnect - Disconnect Server
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestDisconnectServerAPI:
    """API tests for POST /api/v1/aggregator/servers/{id}/disconnect."""

    @pytest.mark.asyncio
    async def test_disconnect_server_returns_200(self, api_client, created_server):
        """Test that disconnecting a server returns 200 OK."""
        response = await api_client.post(
            f"/api/v1/aggregator/servers/{created_server['id']}/disconnect"
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_disconnect_already_disconnected_is_idempotent(self, api_client, created_server):
        """Test that disconnecting already disconnected server succeeds."""
        # Disconnect twice
        await api_client.post(f"/api/v1/aggregator/servers/{created_server['id']}/disconnect")
        response = await api_client.post(
            f"/api/v1/aggregator/servers/{created_server['id']}/disconnect"
        )
        assert response.status_code == 200


# ============================================================================
# GET /api/v1/aggregator/tools - List Aggregated Tools
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestListToolsAPI:
    """API tests for GET /api/v1/aggregator/tools."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_200(self, api_client):
        """Test that listing tools returns 200 OK."""
        response = await api_client.get("/api/v1/aggregator/tools")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_tools_filters_by_server(self, api_client, created_server):
        """Test that tools can be filtered by server."""
        response = await api_client.get(
            "/api/v1/aggregator/tools", params={"server_id": created_server["id"]}
        )
        assert response.status_code == 200


# ============================================================================
# POST /api/v1/aggregator/search - Search Tools
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestSearchToolsAPI:
    """API tests for POST /api/v1/aggregator/search."""

    @pytest.mark.asyncio
    async def test_search_tools_returns_200(self, api_client):
        """Test that searching tools returns 200 OK."""
        response = await api_client.post(
            "/api/v1/aggregator/search", json={"query": "create issue"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_search_tools_with_server_filter(self, api_client, created_server):
        """Test searching with server filter."""
        response = await api_client.post(
            "/api/v1/aggregator/search",
            json={"query": "test", "server_filter": [created_server["name"]]},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_tools_missing_query_returns_422(self, api_client):
        """Test that missing query returns 422."""
        response = await api_client.post("/api/v1/aggregator/search", json={})
        assert response.status_code == 422


# ============================================================================
# POST /api/v1/aggregator/execute - Execute Tool
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestExecuteToolAPI:
    """API tests for POST /api/v1/aggregator/execute."""

    @pytest.mark.asyncio
    async def test_execute_tool_missing_name_returns_422(self, api_client):
        """Test that missing tool name returns 422."""
        response = await api_client.post("/api/v1/aggregator/execute", json={"arguments": {}})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool_returns_404(self, api_client):
        """Test that executing non-existent tool returns 404."""
        response = await api_client.post(
            "/api/v1/aggregator/execute",
            json={"tool_name": "nonexistent-server.fake_tool", "arguments": {}},
        )
        assert response.status_code in (404, 400)


# ============================================================================
# GET /api/v1/aggregator/health - Health Check
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
class TestHealthCheckAPI:
    """API tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_aggregator_health_returns_200(self, api_client):
        """Test that aggregator health check returns 200 OK."""
        response = await api_client.get("/api/v1/aggregator/health")
        assert response.status_code == 200
        data = response.json()
        assert "total_servers" in data

    @pytest.mark.asyncio
    async def test_server_health_returns_200(self, api_client, created_server):
        """Test that server-specific health check returns 200."""
        response = await api_client.get(f"/api/v1/aggregator/servers/{created_server['id']}/health")
        assert response.status_code == 200
        data = response.json()
        assert "server_id" in data


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.api
@pytest.mark.aggregator
@pytest.mark.slow
class TestAggregatorIntegration:
    """Integration tests for full aggregator workflows."""

    @pytest.mark.asyncio
    async def test_full_server_lifecycle(self, api_client):
        """Test complete server lifecycle: register, connect, disconnect, remove."""
        # 1. Register
        server_data = AggregatorTestDataFactory.make_sse_server_registration(
            name=f"lifecycle-test-{uuid.uuid4().hex[:8]}",
            auto_connect=False,
        ).model_dump()
        server_data["transport_type"] = server_data["transport_type"].value

        create_response = await api_client.post("/api/v1/aggregator/servers", json=server_data)
        assert create_response.status_code == 201
        server = create_response.json()

        # 2. Verify in list
        list_response = await api_client.get("/api/v1/aggregator/servers")
        assert server["id"] in [s["id"] for s in list_response.json()]

        # 3. Disconnect (idempotent)
        disconnect_response = await api_client.post(
            f"/api/v1/aggregator/servers/{server['id']}/disconnect"
        )
        assert disconnect_response.status_code == 200

        # 4. Remove
        remove_response = await api_client.delete(f"/api/v1/aggregator/servers/{server['id']}")
        assert remove_response.status_code in (200, 204)

        # 5. Verify removed
        get_response = await api_client.get(f"/api/v1/aggregator/servers/{server['id']}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_state_endpoint_reflects_servers(self, api_client, created_server):
        """Test that state endpoint reflects registered servers."""
        response = await api_client.get("/api/v1/aggregator/health")
        assert response.status_code == 200
        data = response.json()
        assert data["total_servers"] >= 1
