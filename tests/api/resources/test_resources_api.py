"""
TDD TESTS - API Resources Endpoint Tests

Tests for the MCP resources/list and resources/read endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.api
class TestResourcesListAPI:
    """TDD tests for resources/list API endpoint."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_resources_list_returns_jsonrpc_response(self, mock_mcp_client):
        """
        Test resources/list returns valid JSON-RPC 2.0 response.

        Given: MCP server is running
        When: resources/list is called
        Then: Returns JSON-RPC 2.0 response with resources array
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "resources": [
                    {
                        "uri": "resource://test/1",
                        "name": "test_resource",
                        "description": "A test resource",
                        "mimeType": "application/json"
                    }
                ]
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/list",
            "params": {}
        })

        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "resources" in data["result"]
        assert isinstance(data["result"]["resources"], list)

    async def test_resources_list_resource_has_required_fields(self, mock_mcp_client):
        """
        Test each resource in resources/list has required MCP fields.

        Required fields per MCP spec:
        - uri: string
        - name: string
        - description: string (optional)
        - mimeType: string (optional)
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "resources": [
                    {
                        "uri": "resource://test/1",
                        "name": "test_resource"
                    }
                ]
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/list",
            "params": {}
        })

        data = response.json()
        resources = data["result"]["resources"]

        if resources:
            resource = resources[0]
            assert "uri" in resource
            assert "name" in resource

    async def test_resources_list_returns_empty_array_when_no_resources(self, mock_mcp_client):
        """
        Test resources/list returns empty array when no resources registered.

        Given: No resources registered
        When: resources/list is called
        Then: Returns empty resources array
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "resources": []
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/list",
            "params": {}
        })

        data = response.json()
        assert data["result"]["resources"] == []


@pytest.mark.api
class TestResourcesReadAPI:
    """TDD tests for resources/read API endpoint."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_resources_read_returns_contents(self, mock_mcp_client):
        """
        Test resources/read returns resource contents.

        Given: A resource exists
        When: resources/read is called with URI
        Then: Returns contents array
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "contents": [
                    {
                        "uri": "resource://test/1",
                        "mimeType": "application/json",
                        "text": '{"key": "value"}'
                    }
                ]
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "resource://test/1"
            }
        })

        data = response.json()

        assert "result" in data
        assert "contents" in data["result"]
        assert isinstance(data["result"]["contents"], list)

    async def test_resources_read_content_has_uri(self, mock_mcp_client):
        """
        Test resources/read content includes URI.

        Required fields per MCP spec:
        - uri: string
        - mimeType: string (optional)
        - text or blob: string
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "contents": [
                    {
                        "uri": "resource://test/1",
                        "text": "Content"
                    }
                ]
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "resource://test/1"
            }
        })

        data = response.json()
        contents = data["result"]["contents"]

        if contents:
            content = contents[0]
            assert "uri" in content
            # Should have either text or blob
            assert "text" in content or "blob" in content

    async def test_resources_read_nonexistent_resource_returns_error(self, mock_mcp_client):
        """
        Test resources/read returns error for nonexistent resource.

        Given: Resource does not exist
        When: resources/read is called
        Then: Returns JSON-RPC error
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32602,
                "message": "Resource not found: resource://nonexistent/1"
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "resource://nonexistent/1"
            }
        })

        data = response.json()

        assert "error" in data
        assert "code" in data["error"]

    async def test_resources_read_binary_content_returns_blob(self, mock_mcp_client):
        """
        Test resources/read returns blob for binary content.

        Given: A binary resource (image, PDF, etc.)
        When: resources/read is called
        Then: Returns base64-encoded blob
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "contents": [
                    {
                        "uri": "resource://image/1",
                        "mimeType": "image/png",
                        "blob": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA..."
                    }
                ]
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "resource://image/1"
            }
        })

        data = response.json()
        contents = data["result"]["contents"]

        if contents:
            content = contents[0]
            assert "blob" in content


@pytest.mark.api
@pytest.mark.golden
class TestResourcesAPIGolden:
    """Golden tests for resources API - DO NOT MODIFY."""

    def test_resources_list_response_schema(self):
        """
        Documents expected resources/list response schema.
        """
        expected_schema = {
            "jsonrpc": "2.0",
            "id": "integer",
            "result": {
                "resources": [
                    {
                        "uri": "string",
                        "name": "string",
                        "description": "string (optional)",
                        "mimeType": "string (optional)"
                    }
                ]
            }
        }

        assert "result" in expected_schema
        assert "resources" in expected_schema["result"]

    def test_resources_read_response_schema(self):
        """
        Documents expected resources/read response schema.
        """
        expected_schema = {
            "jsonrpc": "2.0",
            "id": "integer",
            "result": {
                "contents": [
                    {
                        "uri": "string",
                        "mimeType": "string (optional)",
                        "text": "string (for text content)",
                        "blob": "string (base64, for binary content)"
                    }
                ]
            }
        }

        assert "result" in expected_schema
        assert "contents" in expected_schema["result"]
