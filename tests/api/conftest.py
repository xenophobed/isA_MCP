"""
API layer test configuration and fixtures.

Layer 1: API Contract Tests (E2E)
- Tests HTTP contracts, status codes
- Runs against real MCP server
- No mocks (integration with real services)
"""
import pytest
from typing import AsyncGenerator
import os


@pytest.fixture
async def authenticated_mcp_client(mcp_client) -> AsyncGenerator:
    """
    MCP client with authentication headers.

    Automatically adds API key to all requests.
    """
    api_key = os.getenv("TEST_MCP_API_KEY", "test_api_key_12345")
    mcp_client.headers["Authorization"] = f"Bearer {api_key}"
    yield mcp_client


@pytest.fixture
async def admin_mcp_client(mcp_client) -> AsyncGenerator:
    """
    MCP client with admin privileges.

    For testing admin-only endpoints.
    """
    admin_key = os.getenv("TEST_ADMIN_API_KEY", "admin_api_key_12345")
    mcp_client.headers["Authorization"] = f"Bearer {admin_key}"
    mcp_client.headers["X-Admin-Access"] = "true"
    yield mcp_client


class MCPProtocolHelper:
    """Helper class for MCP JSON-RPC 2.0 protocol."""

    def __init__(self, client):
        self.client = client
        self.request_id = 0

    async def send_request(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC 2.0 request."""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        response = await self.client.post("/", json=payload)
        return response.json()

    async def initialize(self) -> dict:
        """Initialize MCP connection."""
        return await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test_client", "version": "1.0.0"}
        })

    async def list_tools(self) -> dict:
        """List available tools."""
        return await self.send_request("tools/list", {})

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool."""
        return await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

    async def list_prompts(self) -> dict:
        """List available prompts."""
        return await self.send_request("prompts/list", {})

    async def get_prompt(self, name: str, arguments: dict = None) -> dict:
        """Get a prompt."""
        return await self.send_request("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })

    async def list_resources(self) -> dict:
        """List available resources."""
        return await self.send_request("resources/list", {})

    async def read_resource(self, uri: str) -> dict:
        """Read a resource."""
        return await self.send_request("resources/read", {
            "uri": uri
        })


@pytest.fixture
def mcp_protocol(mcp_client) -> MCPProtocolHelper:
    """Provide MCP protocol helper."""
    return MCPProtocolHelper(mcp_client)


@pytest.fixture
def authenticated_protocol(authenticated_mcp_client) -> MCPProtocolHelper:
    """Provide authenticated MCP protocol helper."""
    return MCPProtocolHelper(authenticated_mcp_client)


# ═══════════════════════════════════════════════════════════════
# Expected Response Schemas
# ═══════════════════════════════════════════════════════════════

TOOL_SCHEMA = {
    "type": "object",
    "required": ["name", "description", "inputSchema"],
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "inputSchema": {"type": "object"}
    }
}

PROMPT_SCHEMA = {
    "type": "object",
    "required": ["name", "description"],
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "arguments": {"type": "array"}
    }
}

RESOURCE_SCHEMA = {
    "type": "object",
    "required": ["uri", "name"],
    "properties": {
        "uri": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "mimeType": {"type": "string"}
    }
}

ERROR_SCHEMA = {
    "type": "object",
    "required": ["code", "message"],
    "properties": {
        "code": {"type": "integer"},
        "message": {"type": "string"},
        "data": {"type": "object"}
    }
}


@pytest.fixture
def expected_schemas():
    """Provide expected response schemas for validation."""
    return {
        "tool": TOOL_SCHEMA,
        "prompt": PROMPT_SCHEMA,
        "resource": RESOURCE_SCHEMA,
        "error": ERROR_SCHEMA
    }
