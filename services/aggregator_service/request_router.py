"""
Request Router - Routes tool execution requests to appropriate external servers.

Handles namespacing resolution, server lookup, and request forwarding.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import logging

from tests.contracts.aggregator.data_contract import (
    ServerStatus,
    RoutingStrategy,
)

logger = logging.getLogger(__name__)


class RoutingContext:
    """Context for a routed request."""

    def __init__(
        self,
        tool_name: str,
        original_name: str,
        server_id: str,
        server_name: str,
        arguments: Dict[str, Any],
        strategy: RoutingStrategy = RoutingStrategy.NAMESPACE_RESOLVED
    ):
        self.tool_name = tool_name
        self.original_name = original_name
        self.server_id = server_id
        self.server_name = server_name
        self.arguments = arguments
        self.strategy = strategy
        self.created_at = datetime.now(timezone.utc)
        self.execution_started_at: Optional[datetime] = None
        self.execution_completed_at: Optional[datetime] = None


class RequestRouter:
    """
    Routes tool execution requests to external MCP servers.

    Responsibilities:
    - Parse namespaced tool names
    - Resolve target server
    - Forward requests to external servers
    - Handle timeouts and errors
    """

    def __init__(
        self,
        session_manager=None,
        server_registry=None,
        tool_repository=None
    ):
        """
        Initialize RequestRouter.

        Args:
            session_manager: SessionManager for MCP communication
            server_registry: ServerRegistry for server lookups
            tool_repository: Tool repository for tool metadata
        """
        self._session_manager = session_manager
        self._server_registry = server_registry
        self._tool_repo = tool_repository
        self._execution_timeout = 60.0  # seconds
        self._retry_on_disconnect = True

    async def route(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_id: str = None
    ) -> RoutingContext:
        """
        Resolve routing context for a tool execution request.

        Args:
            tool_name: Namespaced or original tool name
            arguments: Tool arguments
            server_id: Optional explicit server ID

        Returns:
            RoutingContext with resolved target

        Raises:
            ValueError: If tool or server not found
            RuntimeError: If server unavailable
        """
        # Determine strategy and resolve target
        if server_id:
            # Explicit server ID routing
            return await self._route_explicit(tool_name, arguments, server_id)
        elif "." in tool_name:
            # Namespaced name routing
            return await self._route_namespaced(tool_name, arguments)
        else:
            # Search-based routing (find tool across servers)
            return await self._route_search(tool_name, arguments)

    async def _route_explicit(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_id: str
    ) -> RoutingContext:
        """Route with explicit server ID."""
        server = await self._server_registry.get(server_id)
        if not server:
            raise ValueError(f"Server not found: {server_id}")

        if server["status"] != ServerStatus.CONNECTED:
            raise RuntimeError(f"Server unavailable: {server['name']} ({server['status']})")

        # Get original name from tool if available
        original_name = tool_name
        if self._tool_repo:
            tool = await self._tool_repo.get_tool_by_name(tool_name, server_id)
            if tool:
                original_name = tool.get("original_name", tool_name)

        return RoutingContext(
            tool_name=tool_name,
            original_name=original_name,
            server_id=server_id,
            server_name=server["name"],
            arguments=arguments,
            strategy=RoutingStrategy.EXPLICIT_SERVER
        )

    async def _route_namespaced(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> RoutingContext:
        """Route by parsing namespaced name."""
        # Parse namespaced name - only first dot separates server from tool
        parts = tool_name.split(".", 1)
        server_name = parts[0]
        original_name = parts[1] if len(parts) > 1 else tool_name

        # Find server by name
        server = await self._server_registry.get_by_name(server_name)
        if not server:
            raise ValueError(f"Server not found: {server_name}")

        if server["status"] != ServerStatus.CONNECTED:
            raise RuntimeError(f"Server unavailable: {server_name} ({server['status']})")

        return RoutingContext(
            tool_name=tool_name,
            original_name=original_name,
            server_id=server["id"],
            server_name=server_name,
            arguments=arguments,
            strategy=RoutingStrategy.NAMESPACE_RESOLVED
        )

    async def _route_search(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> RoutingContext:
        """Route by searching for tool across servers."""
        if not self._tool_repo:
            raise ValueError(f"Tool not found: {tool_name}")

        # Search for tool by name
        tool = await self._tool_repo.get_tool_by_name(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        server_id = tool["source_server_id"]
        server = await self._server_registry.get(server_id)

        if not server:
            raise ValueError(f"Server not found for tool: {tool_name}")

        if server["status"] != ServerStatus.CONNECTED:
            raise RuntimeError(
                f"Server unavailable: {server['name']} ({server['status']})"
            )

        return RoutingContext(
            tool_name=tool_name,
            original_name=tool.get("original_name", tool_name),
            server_id=server_id,
            server_name=server["name"],
            arguments=arguments,
            strategy=RoutingStrategy.FALLBACK
        )

    async def execute(self, context: RoutingContext) -> Dict[str, Any]:
        """
        Execute a routed tool request.

        Args:
            context: RoutingContext with resolved target

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If execution fails
        """
        context.execution_started_at = datetime.now(timezone.utc)

        try:
            # Call tool on external server
            result = await asyncio.wait_for(
                self._session_manager.call_tool(
                    server_id=context.server_id,
                    tool_name=context.original_name,
                    arguments=context.arguments
                ),
                timeout=self._execution_timeout
            )

            context.execution_completed_at = datetime.now(timezone.utc)

            return {
                "content": result.get("content", []),
                "is_error": result.get("isError", False),
                "execution_time_ms": (
                    context.execution_completed_at - context.execution_started_at
                ).total_seconds() * 1000,
                "server_id": context.server_id,
                "server_name": context.server_name,
                "tool_name": context.tool_name,
                "original_name": context.original_name,
            }

        except asyncio.TimeoutError:
            logger.error(
                f"Timeout executing {context.tool_name} on {context.server_name}"
            )
            raise RuntimeError(
                f"Tool execution timed out after {self._execution_timeout}s"
            )

        except Exception as e:
            logger.error(
                f"Error executing {context.tool_name} on {context.server_name}: {e}"
            )

            # Check if server disconnected
            if self._retry_on_disconnect:
                server = await self._server_registry.get(context.server_id)
                if server and server["status"] != ServerStatus.CONNECTED:
                    raise RuntimeError(
                        f"Server disconnected during execution: {context.server_name}"
                    )

            raise RuntimeError(f"Tool execution failed: {e}")

    async def route_and_execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_id: str = None
    ) -> Dict[str, Any]:
        """
        Convenience method to route and execute in one call.

        Args:
            tool_name: Namespaced or original tool name
            arguments: Tool arguments
            server_id: Optional explicit server ID

        Returns:
            Tool execution result
        """
        context = await self.route(tool_name, arguments, server_id)
        return await self.execute(context)

    async def validate_tool_exists(
        self,
        tool_name: str,
        server_id: str = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if a tool exists and is available.

        Args:
            tool_name: Tool name to check
            server_id: Optional server filter

        Returns:
            Tuple of (exists, tool_data)
        """
        if not self._tool_repo:
            return False, None

        tool = await self._tool_repo.get_tool_by_name(tool_name, server_id)
        if not tool:
            return False, None

        # Check server status
        server = await self._server_registry.get(tool["source_server_id"])
        if not server or server["status"] != ServerStatus.CONNECTED:
            return True, {**tool, "available": False}

        return True, {**tool, "available": True}
