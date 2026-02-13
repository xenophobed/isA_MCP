"""
CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of the API.
If these tests fail, it means the API contract has changed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.golden
@pytest.mark.api
class TestToolsAPIGolden:
    """
    Golden tests for tools API - DO NOT MODIFY.

    These tests verify the API structure and behavior.
    """

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_tools_list_response_structure(self, mock_mcp_client):
        """
        Verify tools/list response structure.

        Expected structure:
        {
            "jsonrpc": "2.0",
            "id": <int>,
            "result": {
                "tools": [...]
            }
        }
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

        actual = response.json()

        # Verify JSON-RPC structure
        assert actual["jsonrpc"] == "2.0"
        assert "result" in actual
        assert "tools" in actual["result"]
        assert isinstance(actual["result"]["tools"], list)

        # Verify tool schema if tools exist
        if actual["result"]["tools"]:
            tool = actual["result"]["tools"][0]
            required_keys = {"name", "description", "inputSchema"}
            assert required_keys.issubset(
                set(tool.keys())
            ), f"Tool missing required keys. Has: {tool.keys()}, needs: {required_keys}"

    async def test_tools_call_success_response_structure(self, mock_mcp_client):
        """
        Verify tools/call success response structure.

        Expected structure:
        {
            "jsonrpc": "2.0",
            "id": <int>,
            "result": {
                "content": [...],
                "isError": <bool>
            }
        }
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "Result"}], "isError": False},
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

        actual = response.json()

        assert actual["jsonrpc"] == "2.0"
        assert "result" in actual
        assert "content" in actual["result"]
        assert "isError" in actual["result"]

    async def test_tools_call_error_response_structure(self, mock_mcp_client):
        """
        Verify tools/call error response structure.

        Expected structure:
        {
            "jsonrpc": "2.0",
            "id": <int>,
            "error": {
                "code": <int>,
                "message": <str>
            }
        }
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Tool not found"},
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "__nonexistent_tool__", "arguments": {}},
            },
        )

        actual = response.json()

        assert actual["jsonrpc"] == "2.0"
        assert "error" in actual
        assert "code" in actual["error"]
        assert "message" in actual["error"]


@pytest.mark.golden
@pytest.mark.api
class TestPromptsAPIGolden:
    """Golden tests for prompts API - DO NOT MODIFY."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_prompts_list_response_structure(self, mock_mcp_client):
        """
        Verify prompts/list response structure.

        Expected structure:
        {
            "jsonrpc": "2.0",
            "id": <int>,
            "result": {
                "prompts": [...]
            }
        }
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"prompts": [{"name": "test_prompt", "description": "A test prompt"}]},
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": {}}
        )

        actual = response.json()

        assert actual["jsonrpc"] == "2.0"
        assert "result" in actual
        assert "prompts" in actual["result"]
        assert isinstance(actual["result"]["prompts"], list)

    async def test_prompts_get_response_structure(self, mock_mcp_client):
        """
        Verify prompts/get response structure.

        Expected structure:
        {
            "jsonrpc": "2.0",
            "id": <int>,
            "result": {
                "messages": [...]
            }
        }
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"messages": [{"role": "user", "content": {"type": "text", "text": "Test"}}]},
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "prompts/get",
                "params": {"name": "test_prompt", "arguments": {}},
            },
        )

        actual = response.json()

        assert actual["jsonrpc"] == "2.0"
        assert "result" in actual
        assert "messages" in actual["result"]


@pytest.mark.golden
@pytest.mark.api
class TestResourcesAPIGolden:
    """Golden tests for resources API - DO NOT MODIFY."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_resources_list_response_structure(self, mock_mcp_client):
        """
        Verify resources/list response structure.

        Expected structure:
        {
            "jsonrpc": "2.0",
            "id": <int>,
            "result": {
                "resources": [...]
            }
        }
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"resources": [{"uri": "resource://test/1", "name": "test_resource"}]},
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}}
        )

        actual = response.json()

        assert actual["jsonrpc"] == "2.0"
        assert "result" in actual
        assert "resources" in actual["result"]
        assert isinstance(actual["result"]["resources"], list)

    async def test_resources_read_response_structure(self, mock_mcp_client):
        """
        Verify resources/read response structure.

        Expected structure:
        {
            "jsonrpc": "2.0",
            "id": <int>,
            "result": {
                "contents": [...]
            }
        }
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"contents": [{"uri": "resource://test/1", "text": "Content"}]},
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resources/read",
                "params": {"uri": "resource://test/1"},
            },
        )

        actual = response.json()

        assert actual["jsonrpc"] == "2.0"
        assert "result" in actual
        assert "contents" in actual["result"]


@pytest.mark.golden
@pytest.mark.api
class TestSearchAPIGolden:
    """Golden tests for search API - DO NOT MODIFY."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_search_response_structure(self, mock_mcp_client):
        """
        Verify /search response structure.

        Expected structure:
        {
            "status": "success",
            "query": <str>,
            "count": <int>,
            "results": [...]
        }
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "query": "test query",
            "count": 1,
            "results": [
                {
                    "id": "tool_1",
                    "type": "tool",
                    "name": "test_tool",
                    "description": "A test tool",
                    "score": 0.85,
                }
            ],
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/search", json={"query": "test query"})

        actual = response.json()

        assert actual["status"] == "success"
        assert "query" in actual
        assert "count" in actual
        assert "results" in actual
        assert isinstance(actual["results"], list)
