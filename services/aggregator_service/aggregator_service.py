"""
Aggregator Service - Main service for MCP Server Aggregation.

Coordinates server registration, connection management, tool discovery,
and request routing for external MCP servers.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

from .domain import ServerTransportType, ServerStatus

from .server_registry import ServerRegistry
from .session_manager import SessionManager
from .tool_aggregator import ToolAggregator
from .request_router import RequestRouter

logger = logging.getLogger(__name__)


class AggregatorService:
    """
    Main service for aggregating external MCP servers.

    Provides unified interface for:
    - Server registration and lifecycle management
    - Tool discovery and aggregation
    - Request routing to external servers
    - Health monitoring
    """

    def __init__(
        self,
        server_registry=None,
        session_manager=None,
        tool_repository=None,
        vector_repository=None,
        skill_classifier=None,
        model_client=None,
        db_pool=None,
    ):
        """
        Initialize AggregatorService.

        Args:
            server_registry: ServerRegistry instance or mock
            session_manager: SessionManager instance or mock
            tool_repository: Tool repository for storage
            vector_repository: Vector repository for embeddings
            skill_classifier: SkillClassifier for tool classification
            model_client: Model client for embeddings
            db_pool: Optional database pool for new registry
        """
        # Use provided dependencies or create new ones
        self._registry = server_registry or ServerRegistry(db_pool=db_pool)
        self._session_mgr = session_manager or SessionManager(server_registry=self._registry)
        self._tool_repo = tool_repository
        self._vector_repo = vector_repository
        self._skill_classifier = skill_classifier
        self._model_client = model_client

        # Create tool aggregator
        self._tool_aggregator = ToolAggregator(
            session_manager=self._session_mgr,
            server_registry=self._registry,
            tool_repository=self._tool_repo,
            vector_repository=self._vector_repo,
            skill_classifier=self._skill_classifier,
            model_client=self._model_client,
        )

        # Create request router
        self._router = RequestRouter(
            session_manager=self._session_mgr,
            server_registry=self._registry,
            tool_repository=self._tool_repo,
        )

        # Health monitoring state
        self._health_failures: Dict[str, int] = {}  # server_id -> consecutive failures
        self._max_consecutive_failures = 3
        self._health_check_interval = 30.0  # seconds

    # =========================================================================
    # Server Registration (BR-001)
    # =========================================================================

    async def register_server(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new external MCP server.

        Args:
            config: Server configuration containing:
                - name: Unique server name
                - transport_type: sse, stdio, or http
                - connection_config: Transport-specific config
                - auto_connect: Whether to connect immediately
                - health_check_url: Optional health endpoint

        Returns:
            Created server record

        Raises:
            ValueError: If validation fails or name exists
        """
        # Validate and normalize transport type
        transport_type = config.get("transport_type")
        if isinstance(transport_type, str):
            transport_type = ServerTransportType(transport_type)
        config["transport_type"] = transport_type

        # Register in database
        server = await self._registry.add(config)

        logger.info(f"Registered server: {server['name']} ({server['id']})")

        # Auto-connect if requested
        if config.get("auto_connect", False):
            try:
                await self.connect_server(server["id"])
            except Exception as e:
                logger.warning(f"Auto-connect failed for {server['name']}: {e}")
                # Server is registered but not connected - this is OK

        return server

    # =========================================================================
    # Server Connection (BR-002)
    # =========================================================================

    async def connect_server(self, server_id: str) -> bool:
        """
        Connect to an external MCP server.

        Args:
            server_id: Server UUID

        Returns:
            True if connected successfully

        Raises:
            ValueError: If server not found
        """
        server = await self._registry.get(server_id)
        if not server:
            raise ValueError(f"Server not found: {server_id}")

        # Check if already connected AND has active session
        if server["status"] == ServerStatus.CONNECTED:
            existing_session = await self._session_mgr.get_session(server_id)
            if existing_session:
                logger.debug(f"Server already connected with active session: {server['name']}")
                return True
            else:
                logger.info(
                    f"Server status is CONNECTED but no session exists, reconnecting: {server['name']}"
                )

        try:
            # Create session
            await self._session_mgr.connect(
                {
                    "id": server_id,
                    "transport_type": server["transport_type"],
                    "connection_config": server["connection_config"],
                }
            )

            # Trigger tool discovery
            try:
                await self.discover_tools(server_id)
            except Exception as e:
                logger.warning(f"Tool discovery failed for {server['name']}: {e}")
                # Connection succeeded even if discovery failed

            logger.info(f"Connected to server: {server['name']}")
            return True

        except Exception as e:
            logger.error(f"Connection failed for {server['name']}: {e}")
            await self._registry.update_status(server_id, ServerStatus.ERROR, str(e))
            return False

    # =========================================================================
    # Tool Discovery (BR-003)
    # =========================================================================

    async def discover_tools(self, server_id: str = None) -> List[Dict[str, Any]]:
        """
        Discover tools from external servers.

        Args:
            server_id: Optional specific server ID, or None for all connected

        Returns:
            List of discovered tools
        """
        if server_id:
            return await self._tool_aggregator.discover_tools(server_id)
        else:
            return await self._tool_aggregator.aggregate_tools()

    # =========================================================================
    # Skill Classification (BR-004)
    # =========================================================================

    async def classify_tool(self, tool_id: int) -> Dict[str, Any]:
        """
        Classify a tool into skill categories.

        Args:
            tool_id: Tool database ID

        Returns:
            Classification result with assignments
        """
        return await self._tool_aggregator._classify_tool(tool_id)

    # =========================================================================
    # Request Routing & Execution (BR-005)
    # =========================================================================

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any], server_id: str = None
    ) -> Dict[str, Any]:
        """
        Execute a tool on an external server.

        Args:
            tool_name: Namespaced or original tool name
            arguments: Tool arguments
            server_id: Optional explicit server ID

        Returns:
            Tool execution result
        """
        return await self._router.route_and_execute(
            tool_name=tool_name, arguments=arguments, server_id=server_id
        )

    # =========================================================================
    # Health Monitoring (BR-006)
    # =========================================================================

    async def health_check(self, server_id: str = None) -> Any:
        """
        Perform health check on servers.

        Args:
            server_id: Optional specific server ID, or None for all

        Returns:
            Health status (dict for single server, list for all)
        """
        if server_id:
            return await self._health_check_single(server_id)
        else:
            return await self._health_check_all()

    async def _health_check_single(self, server_id: str) -> Dict[str, Any]:
        """Health check a single server."""
        server = await self._registry.get(server_id)
        if not server:
            raise ValueError(f"Server not found: {server_id}")

        now = datetime.now(timezone.utc)
        is_healthy = False

        if server["status"] == ServerStatus.CONNECTED:
            # Try session health check
            is_healthy = await self._session_mgr.health_check(server_id)

        # Update failure tracking
        if is_healthy:
            self._health_failures[server_id] = 0
        else:
            self._health_failures[server_id] = self._health_failures.get(server_id, 0) + 1

        consecutive_failures = self._health_failures.get(server_id, 0)

        # Update last health check time
        await self._registry.update_last_health_check(server_id)

        # If too many failures, mark as unhealthy
        if consecutive_failures >= self._max_consecutive_failures:
            if server["status"] == ServerStatus.CONNECTED:
                await self._registry.update_status(
                    server_id,
                    ServerStatus.DEGRADED,
                    f"Health check failed {consecutive_failures} times",
                )

        return {
            "server_id": server_id,
            "server_name": server["name"],
            "status": server["status"],
            "is_healthy": is_healthy,
            "consecutive_failures": consecutive_failures,
            "last_check": now,
            "health_check_url": server.get("health_check_url"),
        }

    async def _health_check_all(self) -> List[Dict[str, Any]]:
        """Health check all connected servers."""
        servers = await self._registry.list(status=ServerStatus.CONNECTED)
        results = []

        for server in servers:
            try:
                result = await self._health_check_single(server["id"])
                results.append(result)
            except Exception as e:
                logger.error(f"Health check failed for {server['name']}: {e}")
                results.append(
                    {
                        "server_id": server["id"],
                        "server_name": server["name"],
                        "status": server["status"],
                        "is_healthy": False,
                        "error": str(e),
                    }
                )

        return results

    # =========================================================================
    # Server Disconnection (BR-007)
    # =========================================================================

    async def disconnect_server(self, server_id: str) -> bool:
        """
        Disconnect from an external server.

        Args:
            server_id: Server UUID

        Returns:
            True if disconnected (or already disconnected)
        """
        server = await self._registry.get(server_id)
        if not server:
            raise ValueError(f"Server not found: {server_id}")

        if server["status"] == ServerStatus.DISCONNECTED:
            logger.debug(f"Server already disconnected: {server['name']}")
            return True

        # Disconnect session
        await self._session_mgr.disconnect(server_id)

        # Update status
        await self._registry.update_status(server_id, ServerStatus.DISCONNECTED)

        logger.info(f"Disconnected from server: {server['name']}")
        return True

    # =========================================================================
    # Server Removal (BR-008)
    # =========================================================================

    async def remove_server(self, server_id: str) -> bool:
        """
        Remove a server and all its tools.

        Args:
            server_id: Server UUID

        Returns:
            True if removed

        Raises:
            ValueError: If server not found
        """
        server = await self._registry.get(server_id)
        if not server:
            raise ValueError(f"Server not found: {server_id}")

        # Disconnect first if connected
        if server["status"] == ServerStatus.CONNECTED:
            await self.disconnect_server(server_id)

        # Delete tools
        await self._tool_aggregator.remove_server_tools(server_id)

        # Remove from registry
        await self._registry.remove(server_id)

        # Clean up health tracking
        self._health_failures.pop(server_id, None)

        logger.info(f"Removed server: {server['name']}")
        return True

    # =========================================================================
    # State & Queries
    # =========================================================================

    async def get_state(self) -> Dict[str, Any]:
        """
        Get current aggregator state.

        Returns:
            State dict with server and tool counts
        """
        all_servers = await self._registry.list()
        connected = [s for s in all_servers if s["status"] == ServerStatus.CONNECTED]
        disconnected = [s for s in all_servers if s["status"] == ServerStatus.DISCONNECTED]
        error = [
            s for s in all_servers if s["status"] in (ServerStatus.ERROR, ServerStatus.DEGRADED)
        ]

        total_tools = sum(s.get("tool_count", 0) for s in all_servers)

        return {
            "total_servers": len(all_servers),
            "connected_servers": len(connected),
            "disconnected_servers": len(disconnected),
            "error_servers": len(error),
            "total_tools": total_tools,
            "servers": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "status": (
                        s["status"].value if isinstance(s["status"], ServerStatus) else s["status"]
                    ),
                    "tool_count": s.get("tool_count", 0),
                }
                for s in all_servers
            ],
        }

    async def list_servers(
        self, status: ServerStatus = None, org_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        List registered servers.

        Args:
            status: Optional status filter
            org_id: Optional organization ID for tenant filtering

        Returns:
            List of server records
        """
        return await self._registry.list(status=status, org_id=org_id)

    async def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a server by ID.

        Args:
            server_id: Server UUID

        Returns:
            Server record or None
        """
        return await self._registry.get(server_id)

    async def search_tools(
        self, query: str, server_filter: List[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search aggregated tools.

        Args:
            query: Search query
            server_filter: Optional server name filter
            limit: Maximum results

        Returns:
            List of matching tools
        """
        return await self._tool_aggregator.search_tools(
            query=query, server_filter=server_filter, limit=limit
        )

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start_health_monitor(self) -> asyncio.Task:
        """
        Start background health monitoring.

        Returns:
            Health monitor task
        """

        async def _monitor_loop():
            while True:
                try:
                    await self.health_check()
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(self._health_check_interval)

        task = asyncio.create_task(_monitor_loop())
        logger.info("Started health monitor")
        return task

    async def reconnect_unhealthy(self) -> Dict[str, bool]:
        """
        Attempt to reconnect unhealthy servers.

        Returns:
            Dict mapping server_id to reconnect success
        """
        results = {}
        unhealthy = await self._registry.list(status=ServerStatus.DEGRADED)
        error = await self._registry.list(status=ServerStatus.ERROR)

        for server in unhealthy + error:
            try:
                success = await self.connect_server(server["id"])
                results[server["id"]] = success
            except Exception as e:
                logger.error(f"Reconnect failed for {server['name']}: {e}")
                results[server["id"]] = False

        return results
