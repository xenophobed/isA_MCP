"""
Session Manager - MCP ClientSession management for external servers.

Handles connection lifecycle, transport creation, and session pooling.

Key Design:
- Sessions are kept alive by storing context managers and NOT exiting them
- Supports STDIO, SSE, HTTP, and STREAMABLE_HTTP transports
- Proper cleanup on disconnect via manual __aexit__ calls
"""

import asyncio
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

from tests.contracts.aggregator.data_contract import (
    ServerTransportType,
    ServerStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class ManagedConnection:
    """
    Holds all resources for a managed MCP connection.

    Stores the context manager to prevent it from being garbage collected,
    which would close the underlying transport.
    """

    server_id: str
    transport_type: ServerTransportType
    context_manager: Any  # The async context manager (keeps transport alive)
    read_stream: Any  # MemoryObjectReceiveStream
    write_stream: Any  # MemoryObjectSendStream
    session: Any  # ClientSession
    session_context: Any  # ClientSession context manager (for proper cleanup)
    connected_at: datetime
    get_session_id: Optional[Any] = None  # For streamable HTTP
    background_task: Optional[asyncio.Task] = None  # For STDIO: keeps context alive


class SessionManager:
    """
    Manages MCP client sessions to external servers.

    Handles transport creation (STDIO, SSE, STREAMABLE_HTTP) and session lifecycle.

    Key improvement: Sessions are kept alive by storing the context managers
    and only calling __aexit__ during explicit disconnect.
    """

    def __init__(self, server_registry=None):
        """
        Initialize SessionManager.

        Args:
            server_registry: ServerRegistry for updating server status
        """
        self._server_registry = server_registry
        self._sessions: Dict[str, Any] = {}  # server_id -> ClientSession
        self._connections: Dict[str, ManagedConnection] = {}  # server_id -> ManagedConnection
        self._connection_timeout = 30.0  # seconds
        self._retry_attempts = 3
        self._retry_delays = [1.0, 2.0, 4.0]  # exponential backoff

    @staticmethod
    async def _cancel_task(task: asyncio.Task, description: str = "task") -> None:
        """Cancel an asyncio task and wait for it to complete."""
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"Background {description} cancelled")
            except Exception as e:
                logger.warning(f"Error awaiting {description} cancellation: {e}")

    async def connect(self, config: Dict[str, Any]) -> Any:
        """
        Connect to an external server and return session.

        Args:
            config: Server configuration with id, transport_type, connection_config

        Returns:
            Active ClientSession

        Raises:
            ConnectionError: If connection fails after retries
        """
        server_id = config.get("id")
        transport_type = config.get("transport_type")
        connection_config = config.get("connection_config", {})

        # Normalize transport_type
        if isinstance(transport_type, str):
            transport_type = ServerTransportType(transport_type)

        logger.info(f"Connecting to server {server_id} via {transport_type}")

        # Update status to CONNECTING
        if self._server_registry:
            await self._server_registry.update_status(server_id, ServerStatus.CONNECTING)

        last_error = None

        for attempt in range(self._retry_attempts):
            try:
                # Create transport and session
                session = await self._create_session(server_id, transport_type, connection_config)

                # Store session for quick access
                self._sessions[server_id] = session

                # Update status to CONNECTED
                if self._server_registry:
                    await self._server_registry.update_status(server_id, ServerStatus.CONNECTED)

                logger.info(f"Connected to server {server_id}")
                return session

            except Exception as e:
                last_error = e
                logger.warning(f"Connection attempt {attempt + 1} failed for {server_id}: {e}")

                # Clean up any partial connection
                await self._cleanup_connection(server_id)

                if attempt < self._retry_attempts - 1:
                    await asyncio.sleep(self._retry_delays[attempt])

        # All attempts failed
        error_msg = f"Failed to connect after {self._retry_attempts} attempts: {last_error}"
        logger.error(f"Connection failed for {server_id}: {error_msg}")

        if self._server_registry:
            await self._server_registry.update_status(
                server_id, ServerStatus.ERROR, str(last_error)
            )

        raise ConnectionError(error_msg)

    async def _create_session(
        self, server_id: str, transport_type: ServerTransportType, connection_config: Dict[str, Any]
    ) -> Any:
        """
        Create transport and session based on transport type.

        Key design: We manually enter context managers and store them,
        rather than using 'async with' which would exit immediately.
        """
        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client
            from mcp.client.sse import sse_client
            from mcp.client.streamable_http import streamablehttp_client

            if transport_type == ServerTransportType.STDIO:
                return await self._create_stdio_session(
                    server_id, connection_config, stdio_client, ClientSession
                )

            elif transport_type == ServerTransportType.SSE:
                return await self._create_sse_session(
                    server_id, connection_config, sse_client, ClientSession
                )

            elif transport_type == ServerTransportType.STREAMABLE_HTTP:
                return await self._create_streamable_http_session(
                    server_id, connection_config, streamablehttp_client, ClientSession
                )

            elif transport_type == ServerTransportType.HTTP:
                # HTTP transport uses streamable_http under the hood
                # Treat it as an alias for STREAMABLE_HTTP
                logger.info(f"HTTP transport mapped to STREAMABLE_HTTP for {server_id}")
                return await self._create_streamable_http_session(
                    server_id, connection_config, streamablehttp_client, ClientSession
                )

            else:
                raise ValueError(f"Unsupported transport type: {transport_type}")

        except ImportError as e:
            logger.warning(f"MCP SDK import failed: {e}, using mock session")
            return self._create_mock_session(server_id)

    async def _create_stdio_session(
        self, server_id: str, connection_config: Dict[str, Any], stdio_client, ClientSession
    ) -> Any:
        """
        Create STDIO transport session with proper lifecycle management.

        STDIO sessions require a persistent background task because the MCP SDK's
        stdio_client uses an anyio task group for stdin/stdout handling. If that
        task group's parent task ends, the streams close.

        Solution: Run the entire stdio context in a background asyncio.Task that
        stays alive until explicitly cancelled during disconnect.
        """
        import os
        from mcp.client.stdio import StdioServerParameters

        command = connection_config["command"]
        args = connection_config.get("args", [])
        config_env = connection_config.get("env")

        # Inherit current process environment, then overlay any configured env vars
        # This ensures STDIO processes can access tokens like GITHUB_PERSONAL_ACCESS_TOKEN
        env = dict(os.environ)
        if config_env:
            env.update(config_env)

        # Create StdioServerParameters for the stdio_client
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
        )

        # Use events to communicate between background task and caller
        ready_event = asyncio.Event()
        error_holder: List[Exception] = []
        session_holder: List[Any] = []
        connection_holder: List[ManagedConnection] = []

        async def run_stdio_session():
            """Background task that keeps the STDIO session alive."""
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    # Create and initialize session within the context
                    session = ClientSession(read_stream, write_stream)

                    async with session:
                        # Initialize the MCP protocol
                        await asyncio.wait_for(
                            session.initialize(), timeout=self._connection_timeout
                        )

                        # Store session for caller
                        session_holder.append(session)

                        # Create managed connection (task will be added after)
                        conn = ManagedConnection(
                            server_id=server_id,
                            transport_type=ServerTransportType.STDIO,
                            context_manager=None,  # Context is managed by this task
                            read_stream=read_stream,
                            write_stream=write_stream,
                            session=session,
                            session_context=None,  # Context is managed by this task
                            connected_at=datetime.now(timezone.utc),
                            background_task=None,  # Will be set after task creation
                        )
                        connection_holder.append(conn)

                        # Signal that session is ready
                        ready_event.set()

                        # Keep the context alive indefinitely
                        # This task will be cancelled during disconnect
                        try:
                            while True:
                                await asyncio.sleep(3600)  # Sleep for an hour, repeat
                        except asyncio.CancelledError:
                            logger.info(f"STDIO session task cancelled for {server_id}")
                            raise

            except asyncio.CancelledError:
                raise  # Re-raise to properly exit
            except Exception as e:
                error_holder.append(e)
                ready_event.set()  # Signal even on error so caller doesn't hang
                raise

        # Start the background task
        background_task = asyncio.create_task(run_stdio_session())

        # Wait for session to be ready (or error)
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=self._connection_timeout + 5)
        except asyncio.TimeoutError:
            await self._cancel_task(background_task, f"STDIO session for {server_id}")
            raise TimeoutError(f"STDIO session creation timed out for {server_id}")

        # Check for errors
        if error_holder:
            await self._cancel_task(background_task, f"STDIO session for {server_id}")
            raise error_holder[0]

        # Get the session and connection
        if not session_holder or not connection_holder:
            await self._cancel_task(background_task, f"STDIO session for {server_id}")
            raise RuntimeError("STDIO session creation failed: no session returned")

        session = session_holder[0]
        conn = connection_holder[0]
        conn.background_task = background_task

        # Store the managed connection
        self._connections[server_id] = conn

        logger.info(f"STDIO session created for {server_id} (background task running)")
        return session

    async def _create_sse_session(
        self, server_id: str, connection_config: Dict[str, Any], sse_client, ClientSession
    ) -> Any:
        """Create SSE transport session with proper lifecycle management."""
        url = connection_config["url"]
        headers = connection_config.get("headers", {})
        timeout = connection_config.get("timeout", 30)

        # Create the context manager
        transport_cm = sse_client(url, headers=headers, timeout=timeout)

        # Manually enter the transport context
        read_stream, write_stream = await transport_cm.__aenter__()

        try:
            # Create and initialize session
            session = ClientSession(read_stream, write_stream)
            session_cm = session

            await session_cm.__aenter__()

            try:
                await asyncio.wait_for(session.initialize(), timeout=self._connection_timeout)
            except Exception:
                # Clean up session context if initialization fails
                await session_cm.__aexit__(*sys.exc_info())
                raise

            self._connections[server_id] = ManagedConnection(
                server_id=server_id,
                transport_type=ServerTransportType.SSE,
                context_manager=transport_cm,
                read_stream=read_stream,
                write_stream=write_stream,
                session=session,
                session_context=session_cm,
                connected_at=datetime.now(timezone.utc),
            )

            logger.info(f"SSE session created for {server_id}")
            return session

        except Exception as e:
            await transport_cm.__aexit__(type(e), e, e.__traceback__)
            raise

    async def _create_streamable_http_session(
        self,
        server_id: str,
        connection_config: Dict[str, Any],
        streamablehttp_client,
        ClientSession,
    ) -> Any:
        """Create Streamable HTTP transport session with proper lifecycle management."""
        # Support both 'url' and 'base_url' for flexibility
        url = connection_config.get("url") or connection_config.get("base_url")
        if not url:
            raise ValueError("STREAMABLE_HTTP requires 'url' or 'base_url' in connection_config")

        headers = connection_config.get("headers", {})
        timeout = connection_config.get("timeout", 30)
        sse_read_timeout = connection_config.get("sse_read_timeout", 300)

        # Create the context manager
        transport_cm = streamablehttp_client(
            url=url, headers=headers, timeout=timeout, sse_read_timeout=sse_read_timeout
        )

        # Manually enter the transport context
        # streamablehttp_client yields (read_stream, write_stream, get_session_id)
        read_stream, write_stream, get_session_id = await transport_cm.__aenter__()

        try:
            # Create and initialize session
            session = ClientSession(read_stream, write_stream)
            session_cm = session

            await session_cm.__aenter__()

            try:
                await asyncio.wait_for(session.initialize(), timeout=self._connection_timeout)
            except Exception:
                # Clean up session context if initialization fails
                await session_cm.__aexit__(*sys.exc_info())
                raise

            self._connections[server_id] = ManagedConnection(
                server_id=server_id,
                transport_type=ServerTransportType.STREAMABLE_HTTP,
                context_manager=transport_cm,
                read_stream=read_stream,
                write_stream=write_stream,
                session=session,
                session_context=session_cm,
                connected_at=datetime.now(timezone.utc),
                get_session_id=get_session_id,
            )

            session_id = get_session_id() if get_session_id else None
            logger.info(
                f"Streamable HTTP session created for {server_id} (session_id: {session_id})"
            )
            return session

        except Exception as e:
            await transport_cm.__aexit__(type(e), e, e.__traceback__)
            raise

    def _create_mock_session(self, server_id: str) -> Any:
        """Create a mock session for testing when MCP SDK is unavailable."""

        class MockCompatibleSession:
            """Mock-compatible session for testing."""

            def __init__(self, server_id: str):
                self.server_id = server_id
                self._connected = True

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                self._connected = False

            async def initialize(self) -> Dict[str, Any]:
                return {"protocolVersion": "2024-11-05"}

            async def list_tools(self):
                """Return mock tools result."""

                class MockToolsResult:
                    tools = []

                return MockToolsResult()

            async def call_tool(self, name: str, arguments: Dict) -> Any:
                """Return mock tool result."""

                class MockToolResult:
                    content = []
                    isError = False

                return MockToolResult()

            async def close(self) -> None:
                self._connected = False

            @property
            def is_connected(self) -> bool:
                return self._connected

        session = MockCompatibleSession(server_id)

        # Store as managed connection (without real transport)
        self._connections[server_id] = ManagedConnection(
            server_id=server_id,
            transport_type=ServerTransportType.HTTP,  # placeholder
            context_manager=None,
            read_stream=None,
            write_stream=None,
            session=session,
            session_context=session,
            connected_at=datetime.now(timezone.utc),
        )

        logger.debug(f"Mock session created for {server_id}")
        return session

    async def _cleanup_connection(self, server_id: str) -> None:
        """Clean up a connection's resources."""
        conn = self._connections.pop(server_id, None)
        self._sessions.pop(server_id, None)

        if not conn:
            return

        # For STDIO connections, cancel the background task (this closes contexts)
        if conn.background_task:
            logger.info(f"Cancelling STDIO background task for {server_id}")
            await self._cancel_task(conn.background_task, f"STDIO session for {server_id}")
            return  # Background task handles all cleanup for STDIO

        # For non-STDIO connections, manually exit context managers
        if conn.session_context:
            try:
                await conn.session_context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing session context for {server_id}: {e}")

        if conn.context_manager:
            try:
                await conn.context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing transport for {server_id}: {e}")

    async def disconnect(self, server_id: str) -> bool:
        """
        Disconnect from an external server.

        Args:
            server_id: Server UUID

        Returns:
            True if disconnected, False if not connected
        """
        if server_id not in self._connections and server_id not in self._sessions:
            logger.debug(f"Server {server_id} not connected")
            return False

        await self._cleanup_connection(server_id)

        if self._server_registry:
            await self._server_registry.update_status(server_id, ServerStatus.DISCONNECTED)

        logger.info(f"Disconnected from server {server_id}")
        return True

    async def get_session(self, server_id: str) -> Optional[Any]:
        """
        Get an active session for a server.

        Args:
            server_id: Server UUID

        Returns:
            ClientSession or None if not connected
        """
        return self._sessions.get(server_id)

    async def reconnect(self, server_id: str, config: Dict[str, Any]) -> Any:
        """
        Close existing session and create new one.

        Args:
            server_id: Server UUID
            config: Server configuration

        Returns:
            New active ClientSession
        """
        await self.disconnect(server_id)
        return await self.connect(config)

    async def list_tools(self, server_id: str = None) -> List[Dict[str, Any]]:
        """
        List tools from connected servers.

        Args:
            server_id: Optional server ID to get tools from

        Returns:
            List of tool definitions
        """
        all_tools = []

        if server_id:
            session = self._sessions.get(server_id)
            if session:
                try:
                    result = await session.list_tools()
                    # Handle both dict and object responses
                    if hasattr(result, "tools"):
                        tools = result.tools
                    else:
                        tools = result.get("tools", [])

                    # Convert Tool objects to dicts
                    for tool in tools:
                        if hasattr(tool, "name"):
                            all_tools.append(
                                {
                                    "name": tool.name,
                                    "description": tool.description or "",
                                    "inputSchema": (
                                        tool.inputSchema if hasattr(tool, "inputSchema") else {}
                                    ),
                                }
                            )
                        else:
                            all_tools.append(tool)
                except Exception as e:
                    logger.error(f"Error listing tools from {server_id}: {e}")
        else:
            for sid, session in self._sessions.items():
                try:
                    result = await session.list_tools()
                    if hasattr(result, "tools"):
                        tools = result.tools
                    else:
                        tools = result.get("tools", [])

                    for tool in tools:
                        if hasattr(tool, "name"):
                            all_tools.append(
                                {
                                    "name": tool.name,
                                    "description": tool.description or "",
                                    "inputSchema": (
                                        tool.inputSchema if hasattr(tool, "inputSchema") else {}
                                    ),
                                    "server_id": sid,
                                }
                            )
                        else:
                            tool["server_id"] = sid
                            all_tools.append(tool)
                except Exception as e:
                    logger.error(f"Error listing tools from {sid}: {e}")

        return all_tools

    async def call_tool(
        self, server_id: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a tool on an external server.

        Args:
            server_id: Server UUID
            tool_name: Original tool name (not namespaced)
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If session not found or call fails
        """
        session = self._sessions.get(server_id)
        if not session:
            raise RuntimeError(f"No active session for server: {server_id}")

        try:
            result = await session.call_tool(tool_name, arguments)

            # Normalize result to dict
            if hasattr(result, "content"):
                return {
                    "content": (
                        [
                            {"type": c.type, "text": getattr(c, "text", str(c))}
                            for c in result.content
                        ]
                        if result.content
                        else []
                    ),
                    "isError": getattr(result, "isError", False),
                }
            return result
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else repr(e)
            logger.error(
                f"Tool call failed for {tool_name} on {server_id}: "
                f"[{error_type}] {error_msg}\n{traceback.format_exc()}"
            )
            raise RuntimeError(f"Tool call failed: [{error_type}] {error_msg}") from e

    async def health_check(self, server_id: str) -> bool:
        """
        Check health of a server by pinging the session.

        Args:
            server_id: Server UUID

        Returns:
            True if healthy, False otherwise
        """
        session = self._sessions.get(server_id)
        if not session:
            return False

        try:
            # Try to list tools as a health check
            await session.list_tools()
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {server_id}: {e}")
            return False

    def is_connected(self, server_id: str) -> bool:
        """
        Check if server is currently connected.

        Args:
            server_id: Server UUID

        Returns:
            True if connected, False otherwise
        """
        if server_id not in self._sessions:
            return False

        conn = self._connections.get(server_id)
        if conn and conn.session:
            if hasattr(conn.session, "is_connected"):
                return conn.session.is_connected

        return True

    def get_connected_servers(self) -> List[str]:
        """
        Get list of connected server IDs.

        Returns:
            List of server UUIDs
        """
        return list(self._sessions.keys())

    def get_connection_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed connection info for a server.

        Args:
            server_id: Server UUID

        Returns:
            Connection info dict or None
        """
        conn = self._connections.get(server_id)
        if not conn:
            return None

        return {
            "server_id": conn.server_id,
            "transport_type": conn.transport_type.value,
            "connected_at": conn.connected_at.isoformat(),
            "session_id": conn.get_session_id() if conn.get_session_id else None,
        }
