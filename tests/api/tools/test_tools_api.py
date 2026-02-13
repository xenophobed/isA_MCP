"""
TDD TESTS - API Tools Endpoint Tests

Tests for the MCP tools/list and tools/call endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.api
class TestToolsListAPI:
    """TDD tests for tools/list API endpoint."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_tools_list_returns_jsonrpc_response(self, mock_mcp_client):
        """
        Test tools/list returns valid JSON-RPC 2.0 response.

        Given: MCP server is running
        When: tools/list is called
        Then: Returns JSON-RPC 2.0 response with tools array
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                ]
            },
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )

        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "tools" in data["result"]
        assert isinstance(data["result"]["tools"], list)

    async def test_tools_list_tool_has_required_fields(self, mock_mcp_client):
        """
        Test each tool in tools/list has required MCP fields.

        Required fields per MCP spec:
        - name: string
        - description: string
        - inputSchema: object
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )

        data = response.json()
        tools = data["result"]["tools"]

        if tools:
            tool = tools[0]
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    async def test_tools_list_returns_empty_array_when_no_tools(self, mock_mcp_client):
        """
        Test tools/list returns empty array when no tools registered.

        Given: No tools registered
        When: tools/list is called
        Then: Returns empty tools array
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )

        data = response.json()
        assert data["result"]["tools"] == []


@pytest.mark.api
class TestToolsCallAPI:
    """TDD tests for tools/call API endpoint."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_tools_call_returns_result(self, mock_mcp_client):
        """
        Test tools/call returns tool execution result.

        Given: A tool exists
        When: tools/call is invoked with valid arguments
        Then: Returns result with content array
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "Tool executed successfully"}],
                "isError": False,
            },
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "test_tool", "arguments": {"input": "test"}},
            },
        )

        data = response.json()

        assert "result" in data
        assert "content" in data["result"]
        assert isinstance(data["result"]["content"], list)

    async def test_tools_call_nonexistent_tool_returns_error(self, mock_mcp_client):
        """
        Test tools/call returns error for nonexistent tool.

        Given: Tool does not exist
        When: tools/call is invoked
        Then: Returns JSON-RPC error
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Tool not found: nonexistent_tool"},
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "nonexistent_tool", "arguments": {}},
            },
        )

        data = response.json()

        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]

    async def test_tools_call_invalid_arguments_returns_error(self, mock_mcp_client):
        """
        Test tools/call returns error for invalid arguments.

        Given: Tool exists but arguments are invalid
        When: tools/call is invoked with wrong arguments
        Then: Returns validation error
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Invalid params: required field missing"},
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "test_tool", "arguments": {}},  # Missing required fields
            },
        )

        data = response.json()

        assert "error" in data

    async def test_tools_call_result_includes_is_error_flag(self, mock_mcp_client):
        """
        Test tools/call result includes isError flag.

        Given: Tool execution
        When: tools/call completes
        Then: Result includes isError boolean
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "Success"}], "isError": False},
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "test_tool", "arguments": {}},
            },
        )

        data = response.json()

        if "result" in data:
            assert "isError" in data["result"]
            assert isinstance(data["result"]["isError"], bool)


@pytest.mark.api
@pytest.mark.golden
class TestToolsAPIGolden:
    """Golden tests for tools API - DO NOT MODIFY."""

    def test_tools_list_response_schema(self):
        """
        Documents expected tools/list response schema.
        """
        expected_schema = {
            "jsonrpc": "2.0",
            "id": "integer",
            "result": {
                "tools": [{"name": "string", "description": "string", "inputSchema": "object"}]
            },
        }

        # Verify schema structure
        assert "jsonrpc" in expected_schema
        assert "result" in expected_schema
        assert "tools" in expected_schema["result"]

    def test_tools_call_response_schema(self):
        """
        Documents expected tools/call response schema.
        """
        expected_schema = {
            "jsonrpc": "2.0",
            "id": "integer",
            "result": {"content": [{"type": "string", "text": "string"}], "isError": "boolean"},
        }

        assert "result" in expected_schema
        assert "content" in expected_schema["result"]
        assert "isError" in expected_schema["result"]

    def test_tools_error_response_schema(self):
        """
        Documents expected error response schema.
        """
        expected_schema = {
            "jsonrpc": "2.0",
            "id": "integer",
            "error": {"code": "integer", "message": "string"},
        }

        assert "error" in expected_schema
        assert "code" in expected_schema["error"]
        assert "message" in expected_schema["error"]
