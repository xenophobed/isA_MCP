"""
Aggregator Tools - MCP Tool Registration for Server Aggregation.

Exposes aggregator service functionality as MCP tools.
"""

from typing import Any, Dict, List, Optional
import logging

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class AggregatorTools(BaseTool):
    """
    MCP tools for managing external MCP server aggregation.

    Provides tools for:
    - Adding and removing external servers
    - Listing connected servers and tools
    - Searching across aggregated tools
    - Health checking
    """

    def __init__(self, aggregator_service=None):
        """
        Initialize AggregatorTools.

        Args:
            aggregator_service: AggregatorService instance
        """
        super().__init__()
        self._service = aggregator_service

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of MCP tool definitions."""
        return [
            {
                "name": "add_mcp_server",
                "description": "Register and connect a new external MCP server. "
                "Supports SSE, STDIO, and HTTP transports. "
                "After connection, the server's tools become available.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Unique server name (lowercase, no spaces)",
                            "pattern": "^[a-z][a-z0-9_-]*$",
                        },
                        "transport_type": {
                            "type": "string",
                            "enum": ["sse", "stdio", "http"],
                            "description": "Server transport type",
                        },
                        "connection_config": {
                            "type": "object",
                            "description": "Transport-specific configuration",
                            "properties": {
                                "url": {"type": "string", "description": "Server URL (for SSE)"},
                                "base_url": {
                                    "type": "string",
                                    "description": "Base URL (for HTTP)",
                                },
                                "command": {
                                    "type": "string",
                                    "description": "Command to run (for STDIO)",
                                },
                                "args": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Command arguments (for STDIO)",
                                },
                                "headers": {"type": "object", "description": "HTTP headers"},
                            },
                        },
                        "description": {"type": "string", "description": "Server description"},
                        "auto_connect": {
                            "type": "boolean",
                            "default": True,
                            "description": "Connect immediately after registration",
                        },
                        "health_check_url": {
                            "type": "string",
                            "description": "Optional health check endpoint URL",
                        },
                    },
                    "required": ["name", "transport_type", "connection_config"],
                },
            },
            {
                "name": "remove_mcp_server",
                "description": "Disconnect and remove an external MCP server. "
                "All tools from this server will become unavailable.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_name": {
                            "type": "string",
                            "description": "Name of the server to remove",
                        },
                        "server_id": {
                            "type": "string",
                            "description": "UUID of the server to remove (alternative to name)",
                        },
                    },
                },
            },
            {
                "name": "list_mcp_servers",
                "description": "List all registered external MCP servers with their status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["connected", "disconnected", "error", "unhealthy"],
                            "description": "Filter by connection status",
                        },
                        "include_tools": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include tool list for each server",
                        },
                    },
                },
            },
            {
                "name": "search_aggregated_tools",
                "description": "Search for tools across all connected external servers. "
                "Returns matching tools with relevance scores.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (natural language)",
                        },
                        "server_filter": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Limit search to specific servers",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum number of results",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "aggregator_health",
                "description": "Check health status of connected external servers.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_name": {
                            "type": "string",
                            "description": "Check specific server (optional)",
                        },
                        "reconnect_unhealthy": {
                            "type": "boolean",
                            "default": False,
                            "description": "Attempt to reconnect unhealthy servers",
                        },
                    },
                },
            },
            {
                "name": "connect_mcp_server",
                "description": "Connect to a registered but disconnected server.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_name": {
                            "type": "string",
                            "description": "Name of the server to connect",
                        },
                        "server_id": {
                            "type": "string",
                            "description": "UUID of the server to connect (alternative)",
                        },
                    },
                },
            },
            {
                "name": "disconnect_mcp_server",
                "description": "Disconnect from a server without removing it.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_name": {
                            "type": "string",
                            "description": "Name of the server to disconnect",
                        },
                        "server_id": {
                            "type": "string",
                            "description": "UUID of the server to disconnect (alternative)",
                        },
                    },
                },
            },
            {
                "name": "refresh_server_tools",
                "description": "Re-discover tools from a connected server.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_name": {
                            "type": "string",
                            "description": "Name of the server to refresh",
                        },
                        "server_id": {
                            "type": "string",
                            "description": "UUID of the server to refresh (alternative)",
                        },
                    },
                },
            },
            {
                "name": "execute_external_tool",
                "description": "Execute a tool on an external MCP server. "
                "Use namespaced tool name (e.g., 'github-mcp.search_issues').",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Namespaced tool name (server.tool_name)",
                        },
                        "arguments": {
                            "type": "object",
                            "description": "Tool arguments as key-value pairs",
                        },
                    },
                },
            },
        ]

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an aggregator tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self._service:
            return {
                "content": [{"type": "text", "text": "Aggregator service not initialized"}],
                "isError": True,
            }

        try:
            if name == "add_mcp_server":
                return await self._add_server(arguments)
            elif name == "remove_mcp_server":
                return await self._remove_server(arguments)
            elif name == "list_mcp_servers":
                return await self._list_servers(arguments)
            elif name == "search_aggregated_tools":
                return await self._search_tools(arguments)
            elif name == "aggregator_health":
                return await self._health_check(arguments)
            elif name == "connect_mcp_server":
                return await self._connect_server(arguments)
            elif name == "disconnect_mcp_server":
                return await self._disconnect_server(arguments)
            elif name == "refresh_server_tools":
                return await self._refresh_tools(arguments)
            elif name == "execute_external_tool":
                return await self._execute_external_tool(arguments)
            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                    "isError": True,
                }

        except Exception as e:
            import traceback

            logger.error(f"Aggregator tool {name} failed: {e}")
            logger.error(traceback.format_exc())
            return {
                "content": [{"type": "text", "text": f"Error: {type(e).__name__}: {str(e)}"}],
                "isError": True,
            }

    async def _add_server(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new MCP server."""
        server = await self._service.register_server(args)
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Server '{server['name']}' registered successfully.\n"
                    f"ID: {server['id']}\n"
                    f"Status: {server['status'].value if hasattr(server['status'], 'value') else server['status']}\n"
                    f"Tools: {server.get('tool_count', 0)}",
                }
            ],
            "isError": False,
        }

    async def _remove_server(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Remove an MCP server."""
        server_id = args.get("server_id")
        server_name = args.get("server_name")

        if not server_id and server_name:
            # Look up by name
            servers = await self._service.list_servers()
            for s in servers:
                if s["name"] == server_name:
                    server_id = s["id"]
                    break

        if not server_id:
            return {"content": [{"type": "text", "text": "Server not found"}], "isError": True}

        await self._service.remove_server(server_id)
        return {
            "content": [{"type": "text", "text": f"Server removed successfully"}],
            "isError": False,
        }

    async def _list_servers(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List MCP servers."""
        from tests.contracts.aggregator.data_contract import ServerStatus

        status_filter = args.get("status")
        if status_filter:
            status_filter = ServerStatus(status_filter)

        servers = await self._service.list_servers(status=status_filter)

        if not servers:
            return {
                "content": [{"type": "text", "text": "No servers registered"}],
                "isError": False,
            }

        lines = ["Registered MCP Servers:"]
        for s in servers:
            status = s["status"].value if hasattr(s["status"], "value") else s["status"]
            lines.append(f"\n- {s['name']} ({status})")
            lines.append(f"  ID: {s['id']}")
            lines.append(f"  Tools: {s.get('tool_count', 0)}")

            if args.get("include_tools") and s.get("tool_count", 0) > 0:
                # Would need to query tools from tool_repository
                pass

        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    async def _search_tools(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search aggregated tools."""
        query = args["query"]
        server_filter = args.get("server_filter")
        limit = args.get("limit", 10)

        results = await self._service.search_tools(
            query=query, server_filter=server_filter, limit=limit
        )

        if not results:
            return {
                "content": [{"type": "text", "text": f"No tools found for: {query}"}],
                "isError": False,
            }

        lines = [f"Found {len(results)} tools for '{query}':"]
        for r in results:
            payload = r.get("payload", {})
            lines.append(f"\n- {payload.get('name', r.get('id'))}")
            lines.append(f"  Server: {payload.get('source_server_name', 'unknown')}")
            lines.append(f"  Score: {r.get('score', 0):.2f}")

        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    async def _health_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check aggregator health."""
        server_name = args.get("server_name")
        server_id = None

        if server_name:
            servers = await self._service.list_servers()
            for s in servers:
                if s["name"] == server_name:
                    server_id = s["id"]
                    break

        if args.get("reconnect_unhealthy"):
            results = await self._service.reconnect_unhealthy()
            reconnected = sum(1 for v in results.values() if v)
            return {
                "content": [
                    {"type": "text", "text": f"Reconnected {reconnected}/{len(results)} servers"}
                ],
                "isError": False,
            }

        health = await self._service.health_check(server_id)

        if isinstance(health, list):
            lines = [f"Health status for {len(health)} servers:"]
            for h in health:
                status = "healthy" if h.get("is_healthy") else "unhealthy"
                lines.append(f"\n- {h['server_name']}: {status}")
                if h.get("consecutive_failures", 0) > 0:
                    lines.append(f"  Failures: {h['consecutive_failures']}")
        else:
            status = "healthy" if health.get("is_healthy") else "unhealthy"
            lines = [f"Server {health['server_name']}: {status}"]
            if health.get("consecutive_failures", 0) > 0:
                lines.append(f"Consecutive failures: {health['consecutive_failures']}")

        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    async def _connect_server(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to a server."""
        server_id = args.get("server_id")
        server_name = args.get("server_name")

        if not server_id and server_name:
            servers = await self._service.list_servers()
            for s in servers:
                if s["name"] == server_name:
                    server_id = s["id"]
                    break

        if not server_id:
            return {"content": [{"type": "text", "text": "Server not found"}], "isError": True}

        success = await self._service.connect_server(server_id)
        return {
            "content": [
                {"type": "text", "text": f"Connection {'successful' if success else 'failed'}"}
            ],
            "isError": not success,
        }

    async def _disconnect_server(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Disconnect from a server."""
        server_id = args.get("server_id")
        server_name = args.get("server_name")

        if not server_id and server_name:
            servers = await self._service.list_servers()
            for s in servers:
                if s["name"] == server_name:
                    server_id = s["id"]
                    break

        if not server_id:
            return {"content": [{"type": "text", "text": "Server not found"}], "isError": True}

        success = await self._service.disconnect_server(server_id)
        return {
            "content": [
                {"type": "text", "text": f"Disconnection {'successful' if success else 'failed'}"}
            ],
            "isError": not success,
        }

    async def _refresh_tools(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh tools from a server."""
        server_id = args.get("server_id")
        server_name = args.get("server_name")

        if not server_id and server_name:
            servers = await self._service.list_servers()
            for s in servers:
                if s["name"] == server_name:
                    server_id = s["id"]
                    break

        if not server_id:
            return {"content": [{"type": "text", "text": "Server not found"}], "isError": True}

        tools = await self._service.discover_tools(server_id)
        return {
            "content": [{"type": "text", "text": f"Discovered {len(tools)} tools"}],
            "isError": False,
        }

    async def _execute_external_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on an external server."""
        tool_name = args.get("tool_name")
        arguments = args.get("arguments", {})

        if not tool_name:
            return {"content": [{"type": "text", "text": "tool_name is required"}], "isError": True}

        # Parse namespaced name to get server
        if "." not in tool_name:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Invalid tool name '{tool_name}'. Use format: server.tool_name",
                    }
                ],
                "isError": True,
            }

        try:
            result = await self._service.execute_tool(tool_name, arguments)
            return result
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Execution failed: {str(e)}"}],
                "isError": True,
            }


# Global aggregator tools instance
_aggregator_tools: Optional[AggregatorTools] = None


def register_aggregator_tools(mcp_server, aggregator_service):
    """
    Register aggregator tools with MCP server.

    Args:
        mcp_server: MCP server instance
        aggregator_service: AggregatorService instance
    """
    global _aggregator_tools
    _aggregator_tools = AggregatorTools(aggregator_service)

    @mcp_server.tool()
    async def add_mcp_server(
        name: str,
        transport_type: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
        description: Optional[str] = None,
        auto_connect: bool = True,
    ) -> Dict[str, Any]:
        """
        🔌 ADD EXTERNAL MCP SERVER - Register a new MCP server for tool aggregation.

        Supports STDIO (local process) and SSE (HTTP streaming) transports.

        Args:
            name: Unique name for the server (e.g., "github-mcp")
            transport_type: "STDIO" for local process, "SSE" for HTTP streaming
            command: For STDIO - command to run (e.g., "npx")
            args: For STDIO - command arguments (e.g., ["-y", "@modelcontextprotocol/server-github"])
            url: For SSE - server URL
            description: Optional server description
            auto_connect: Connect immediately after adding (default: True)

        Returns:
            Server registration details including ID and discovered tools count
        """
        connection_config = {}
        if transport_type.upper() == "STDIO":
            connection_config = {"command": command, "args": args or []}
        elif transport_type.upper() == "SSE":
            connection_config = {"url": url}

        return await _aggregator_tools.execute(
            "add_mcp_server",
            {
                "name": name,
                "description": description,
                "transport_type": transport_type.upper(),
                "connection_config": connection_config,
                "auto_connect": auto_connect,
            },
        )

    @mcp_server.tool()
    async def remove_mcp_server(server_id: str) -> Dict[str, Any]:
        """
        🗑️ REMOVE MCP SERVER - Unregister an external MCP server.

        This will disconnect the server and remove all its tools from the registry.

        Args:
            server_id: The UUID of the server to remove

        Returns:
            Confirmation of removal
        """
        return await _aggregator_tools.execute("remove_mcp_server", {"server_id": server_id})

    @mcp_server.tool()
    async def list_mcp_servers() -> Dict[str, Any]:
        """
        📋 LIST MCP SERVERS - Show all registered external MCP servers.

        Returns:
            List of servers with their status, tool counts, and connection info
        """
        return await _aggregator_tools.execute("list_mcp_servers", {})

    @mcp_server.tool()
    async def connect_mcp_server(server_id: str) -> Dict[str, Any]:
        """
        🔗 CONNECT TO MCP SERVER - Establish connection to a registered server.

        Args:
            server_id: The UUID of the server to connect

        Returns:
            Connection status and discovered tools
        """
        return await _aggregator_tools.execute("connect_mcp_server", {"server_id": server_id})

    @mcp_server.tool()
    async def disconnect_mcp_server(server_id: str) -> Dict[str, Any]:
        """
        🔌 DISCONNECT MCP SERVER - Close connection to a server (keeps registration).

        Args:
            server_id: The UUID of the server to disconnect

        Returns:
            Disconnection confirmation
        """
        return await _aggregator_tools.execute("disconnect_mcp_server", {"server_id": server_id})

    @mcp_server.tool()
    async def refresh_server_tools(server_id: str) -> Dict[str, Any]:
        """
        🔄 REFRESH SERVER TOOLS - Re-discover tools from a connected server.

        Use this after the external server has been updated with new tools.

        Args:
            server_id: The UUID of the server to refresh

        Returns:
            Updated tool count and list
        """
        return await _aggregator_tools.execute("refresh_server_tools", {"server_id": server_id})

    @mcp_server.tool()
    async def execute_external_tool(
        tool_name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        ▶️ EXECUTE EXTERNAL TOOL - Run a tool on an external MCP server.

        Use namespaced tool names from discover results (e.g., 'github-mcp.search_issues').

        Args:
            tool_name: Namespaced tool name (server.tool_name)
            arguments: Tool arguments as key-value pairs

        Returns:
            Tool execution result from the external server
        """
        return await _aggregator_tools.execute(
            "execute_external_tool", {"tool_name": tool_name, "arguments": arguments or {}}
        )

    logger.info("Registered 7 aggregator tools for external MCP server management")
