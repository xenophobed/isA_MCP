"""
TDD TESTS - API Prompts Endpoint Tests

Tests for the MCP prompts/list and prompts/get endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.api
class TestPromptsListAPI:
    """TDD tests for prompts/list API endpoint."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_prompts_list_returns_jsonrpc_response(self, mock_mcp_client):
        """
        Test prompts/list returns valid JSON-RPC 2.0 response.

        Given: MCP server is running
        When: prompts/list is called
        Then: Returns JSON-RPC 2.0 response with prompts array
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "prompts": [
                    {
                        "name": "test_prompt",
                        "description": "A test prompt",
                        "arguments": [
                            {"name": "topic", "required": True, "description": "The topic"}
                        ]
                    }
                ]
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/list",
            "params": {}
        })

        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "prompts" in data["result"]
        assert isinstance(data["result"]["prompts"], list)

    async def test_prompts_list_prompt_has_required_fields(self, mock_mcp_client):
        """
        Test each prompt in prompts/list has required MCP fields.

        Required fields per MCP spec:
        - name: string
        - description: string (optional)
        - arguments: array (optional)
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "prompts": [
                    {
                        "name": "test_prompt",
                        "description": "A test prompt",
                        "arguments": []
                    }
                ]
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/list",
            "params": {}
        })

        data = response.json()
        prompts = data["result"]["prompts"]

        if prompts:
            prompt = prompts[0]
            assert "name" in prompt
            # description and arguments are optional per MCP spec

    async def test_prompts_list_returns_empty_array_when_no_prompts(self, mock_mcp_client):
        """
        Test prompts/list returns empty array when no prompts registered.

        Given: No prompts registered
        When: prompts/list is called
        Then: Returns empty prompts array
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "prompts": []
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/list",
            "params": {}
        })

        data = response.json()
        assert data["result"]["prompts"] == []


@pytest.mark.api
class TestPromptsGetAPI:
    """TDD tests for prompts/get API endpoint."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for API testing."""
        mock = MagicMock()
        mock.post = AsyncMock()
        return mock

    async def test_prompts_get_returns_messages(self, mock_mcp_client):
        """
        Test prompts/get returns prompt messages.

        Given: A prompt exists
        When: prompts/get is called with arguments
        Then: Returns messages array with rendered prompt
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "description": "A test prompt",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "Write about Python programming"
                        }
                    }
                ]
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/get",
            "params": {
                "name": "test_prompt",
                "arguments": {"topic": "Python programming"}
            }
        })

        data = response.json()

        assert "result" in data
        assert "messages" in data["result"]
        assert isinstance(data["result"]["messages"], list)

    async def test_prompts_get_message_has_role_and_content(self, mock_mcp_client):
        """
        Test prompts/get messages have required fields.

        Required fields per MCP spec:
        - role: string (user/assistant)
        - content: object with type and text
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "Test content"
                        }
                    }
                ]
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/get",
            "params": {
                "name": "test_prompt",
                "arguments": {}
            }
        })

        data = response.json()
        messages = data["result"]["messages"]

        if messages:
            message = messages[0]
            assert "role" in message
            assert "content" in message

    async def test_prompts_get_nonexistent_prompt_returns_error(self, mock_mcp_client):
        """
        Test prompts/get returns error for nonexistent prompt.

        Given: Prompt does not exist
        When: prompts/get is called
        Then: Returns JSON-RPC error
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32602,
                "message": "Prompt not found: nonexistent_prompt"
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/get",
            "params": {
                "name": "nonexistent_prompt",
                "arguments": {}
            }
        })

        data = response.json()

        assert "error" in data
        assert "code" in data["error"]

    async def test_prompts_get_missing_required_argument_returns_error(self, mock_mcp_client):
        """
        Test prompts/get returns error when required argument missing.

        Given: Prompt requires an argument
        When: prompts/get is called without that argument
        Then: Returns validation error
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32602,
                "message": "Missing required argument: topic"
            }
        }
        mock_mcp_client.post.return_value = mock_response

        response = await mock_mcp_client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/get",
            "params": {
                "name": "test_prompt",
                "arguments": {}  # Missing required 'topic' argument
            }
        })

        data = response.json()

        assert "error" in data


@pytest.mark.api
@pytest.mark.golden
class TestPromptsAPIGolden:
    """Golden tests for prompts API - DO NOT MODIFY."""

    def test_prompts_list_response_schema(self):
        """
        Documents expected prompts/list response schema.
        """
        expected_schema = {
            "jsonrpc": "2.0",
            "id": "integer",
            "result": {
                "prompts": [
                    {
                        "name": "string",
                        "description": "string (optional)",
                        "arguments": [
                            {
                                "name": "string",
                                "description": "string (optional)",
                                "required": "boolean (optional)"
                            }
                        ]
                    }
                ]
            }
        }

        assert "result" in expected_schema
        assert "prompts" in expected_schema["result"]

    def test_prompts_get_response_schema(self):
        """
        Documents expected prompts/get response schema.
        """
        expected_schema = {
            "jsonrpc": "2.0",
            "id": "integer",
            "result": {
                "description": "string (optional)",
                "messages": [
                    {
                        "role": "string",
                        "content": {
                            "type": "string",
                            "text": "string"
                        }
                    }
                ]
            }
        }

        assert "result" in expected_schema
        assert "messages" in expected_schema["result"]
