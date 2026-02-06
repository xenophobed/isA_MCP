"""
isA MCP - AI-powered Model Context Protocol management CLI and client library.

Usage as CLI:
    isa_mcp skill install remotion-dev/skills
    isa_mcp skill search video
    isa_mcp server add my-server --url http://localhost:8082
    isa_mcp sync
    isa_mcp tools discover "calendar"

Usage as Library:
    from isa_mcp import MCPClient, AsyncMCPClient

    # Synchronous client
    client = MCPClient("http://localhost:8081")
    result = client.search("calendar tools")

    # Async client
    async with AsyncMCPClient("http://localhost:8081") as client:
        result = await client.search("calendar tools")

Install:
    pip install isa-mcp
"""

from .mcp_client import (
    MCPClient,
    AsyncMCPClient,
    MCPClientError,
    MCPConnectionError,
    MCPToolError,
    SearchResult,
    ToolMatch,
)

__all__ = [
    # Client classes
    "MCPClient",
    "AsyncMCPClient",
    # Exceptions
    "MCPClientError",
    "MCPConnectionError",
    "MCPToolError",
    # Data classes
    "SearchResult",
    "ToolMatch",
]

__version__ = "1.0.0"
