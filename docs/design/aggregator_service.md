# MCP Server Aggregator - Design Document

**Technical Architecture for External MCP Server Aggregation**

This document outlines the technical design for the MCP Server Aggregator, enabling ISA MCP to connect to and aggregate multiple external MCP servers.

---

## Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Domain | [docs/domain/aggregator_service.md](../domain/aggregator_service.md) | Business context, entities |
| PRD | [docs/prd/aggregator_service.md](../prd/aggregator_service.md) | User stories, requirements |
| Data Contract | [tests/contracts/aggregator/data_contract.py](../../tests/contracts/aggregator/data_contract.py) | Pydantic schemas |
| Logic Contract | [tests/contracts/aggregator/logic_contract.md](../../tests/contracts/aggregator/logic_contract.md) | Business rules |
| System Contract | [tests/contracts/aggregator/system_contract.md](../../tests/contracts/aggregator/system_contract.md) | API contracts |

---

## Overview

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Session Management | MCP SDK ClientSessionGroup | Standard SDK for managing multiple sessions |
| Transport Support | STDIO, SSE, HTTP | Cover all common MCP transport types |
| Namespacing Strategy | `{server_name}.{tool_name}` | Avoid collisions while preserving original names |
| Classification | Existing SkillClassifier | Reuse LLM classification infrastructure |
| Health Monitoring | Active probing + passive inference | Comprehensive health detection |
| Persistence | PostgreSQL + Qdrant | Consistent with existing infrastructure |

---

## Architecture

### High-Level Architecture

```
+-----------------------------------------------------------------------------+
|                              ISA MCP PLATFORM                                |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +---------------------------+     +----------------------------------+      |
|  |      MCP Clients          |     |        Internal Tools            |      |
|  |   (Claude, etc.)          |     |     (88+ existing tools)         |      |
|  +------------+--------------+     +----------------+-----------------+      |
|               |                                     |                        |
|               +----------------+--------------------+                        |
|                                |                                             |
|                                v                                             |
|  +-----------------------------------------------------------------------+  |
|  |                        AGGREGATOR SERVICE                              |  |
|  |                                                                        |  |
|  |  +----------------+  +----------------+  +------------------+          |  |
|  |  | ServerRegistry |  | ToolAggregator |  | SkillClassifier  |          |  |
|  |  +----------------+  +----------------+  | (existing)       |          |  |
|  |  | - Register     |  | - Discover     |  +------------------+          |  |
|  |  | - Connect      |  | - Index        |  | - Classify       |          |  |
|  |  | - Disconnect   |  | - Namespace    |  | - Assign skills  |          |  |
|  |  +----------------+  +----------------+  +------------------+          |  |
|  |                                                                        |  |
|  |  +----------------+  +----------------+  +------------------+          |  |
|  |  | RequestRouter  |  | HealthMonitor  |  | SessionManager   |          |  |
|  |  +----------------+  +----------------+  +------------------+          |  |
|  |  | - Resolve      |  | - Check health |  | - ClientSession  |          |  |
|  |  | - Forward      |  | - Update status|  | - SessionGroup   |          |  |
|  |  | - Handle errors|  | - Reconnect    |  | - Lifecycle      |          |  |
|  |  +----------------+  +----------------+  +------------------+          |  |
|  |                                                                        |  |
|  +-----------------------------------------------------------------------+  |
|                                |                                             |
|          +--------------------|--------------------+                         |
|          |                    |                    |                         |
|          v                    v                    v                         |
|  +----------------+   +----------------+   +----------------+                |
|  | External MCP   |   | External MCP   |   | External MCP   |                |
|  | Server (STDIO) |   | Server (SSE)   |   | Server (HTTP)  |                |
|  | - github-mcp   |   | - slack-mcp    |   | - custom-api   |                |
|  +----------------+   +----------------+   +----------------+                |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### Component Architecture

```
+-----------------------------------------------------------------------------+
|                         AGGREGATOR SERVICE COMPONENTS                        |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +----------------------------------+  +----------------------------------+  |
|  |         ServerRegistry           |  |         ToolAggregator           |  |
|  +----------------------------------+  +----------------------------------+  |
|  | Responsibilities:                |  | Responsibilities:                |  |
|  | - Store server configurations    |  | - Discover tools from servers    |  |
|  | - Manage server lifecycle        |  | - Apply namespacing              |  |
|  | - Track connection status        |  | - Index tools in PostgreSQL      |  |
|  |                                  |  | - Generate embeddings            |  |
|  | Methods:                         |  | - Update Qdrant                  |  |
|  | - register_server()              |  |                                  |  |
|  | - get_server()                   |  | Methods:                         |  |
|  | - list_servers()                 |  | - discover_tools()               |  |
|  | - update_status()                |  | - aggregate_tool()               |  |
|  | - remove_server()                |  | - remove_server_tools()          |  |
|  +----------------------------------+  +----------------------------------+  |
|                                                                              |
|  +----------------------------------+  +----------------------------------+  |
|  |         SessionManager           |  |         RequestRouter            |  |
|  +----------------------------------+  +----------------------------------+  |
|  | Responsibilities:                |  | Responsibilities:                |  |
|  | - Manage MCP ClientSessions      |  | - Resolve tool to server         |  |
|  | - Handle transport setup         |  | - Forward tool calls             |  |
|  | - Session lifecycle              |  | - Handle routing errors          |  |
|  |                                  |  | - Track routing metrics          |  |
|  | Methods:                         |  |                                  |  |
|  | - create_session()               |  | Methods:                         |  |
|  | - get_session()                  |  | - resolve_route()                |  |
|  | - close_session()                |  | - execute_tool()                 |  |
|  | - reconnect()                    |  | - handle_error()                 |  |
|  +----------------------------------+  +----------------------------------+  |
|                                                                              |
|  +----------------------------------+  +----------------------------------+  |
|  |         HealthMonitor            |  |      SkillClassifier (Existing)  |  |
|  +----------------------------------+  +----------------------------------+  |
|  | Responsibilities:                |  | Responsibilities:                |  |
|  | - Periodic health checks         |  | - Classify tools via LLM         |  |
|  | - Update server status           |  | - Assign skill categories        |  |
|  | - Trigger reconnection           |  | - Update skill embeddings        |  |
|  | - Emit health events             |  |                                  |  |
|  |                                  |  | (Reuses existing skill service   |  |
|  | Methods:                         |  |  infrastructure)                 |  |
|  | - check_health()                 |  |                                  |  |
|  | - start_monitoring()             |  |                                  |  |
|  | - stop_monitoring()              |  |                                  |  |
|  +----------------------------------+  +----------------------------------+  |
|                                                                              |
+-----------------------------------------------------------------------------+
```

---

## Data Flow

### Server Registration Flow

```
Administrator                 AggregatorService              Database
     |                              |                            |
     | 1. POST /servers             |                            |
     | {name, transport, config}    |                            |
     |----------------------------->|                            |
     |                              |                            |
     |           2. Validate config |                            |
     |                              |                            |
     |                              | 3. Insert server record    |
     |                              |--------------------------->|
     |                              |                            |
     |          4. Create session   |                            |
     |                              |                            |
     |          5. Connect to       |                            |
     |             external server  |                            |
     |                              |                            |
     |          6. Discover tools   |                            |
     |                              |                            |
     |          7. Classify tools   |                            |
     |                              |                            |
     |                              | 8. Store tools             |
     |                              |--------------------------->|
     |                              |                            |
     |                              | 9. Update Qdrant           |
     |                              |                            |
     | 10. Return {server, tools}   |                            |
     |<-----------------------------|                            |
```

### Tool Discovery Flow

```
SessionManager                  ExternalServer               ToolAggregator
      |                              |                            |
      | 1. tools/list                |                            |
      |----------------------------->|                            |
      |                              |                            |
      | 2. {tools: [...]}            |                            |
      |<-----------------------------|                            |
      |                                                           |
      | 3. For each tool:                                         |
      |------------------------------------------------------>   |
      |                                                           |
      |                              4. Apply namespacing          |
      |                              5. Generate embedding         |
      |                              6. Classify into skills       |
      |                              7. Store in PostgreSQL        |
      |                              8. Index in Qdrant            |
      |                                                           |
      | 9. Discovery complete                                     |
      |<------------------------------------------------------|   |
```

### Tool Execution Flow

```
Client              RequestRouter         SessionManager       ExternalServer
   |                     |                      |                    |
   | 1. Call tool        |                      |                    |
   | {name: "srv.tool"}  |                      |                    |
   |------------------->|                      |                    |
   |                     |                      |                    |
   |  2. Parse namespace |                      |                    |
   |  3. Resolve server  |                      |                    |
   |                     |                      |                    |
   |                     | 4. Get session       |                    |
   |                     |--------------------->|                    |
   |                     |                      |                    |
   |                     | 5. Session           |                    |
   |                     |<---------------------|                    |
   |                     |                      |                    |
   |                     | 6. Forward call      |                    |
   |                     |----------------------------------------->|
   |                     |                      |                    |
   |                     | 7. Tool response     |                    |
   |                     |<-----------------------------------------|
   |                     |                      |                    |
   | 8. Return response  |                      |                    |
   |<--------------------|                      |                    |
```

### Health Monitoring Flow

```
HealthMonitor               ServerRegistry              SessionManager
      |                          |                            |
      | 1. Get servers           |                            |
      |------------------------->|                            |
      |                          |                            |
      | 2. Server list           |                            |
      |<-------------------------|                            |
      |                                                       |
      | 3. For each server:                                   |
      |                                                       |
      |                          | 4. Check health_url        |
      |                          | OR                         |
      |                          | 5. Ping session            |
      |                          |--------------------------->|
      |                          |                            |
      |                          | 6. Health status           |
      |                          |<---------------------------|
      |                          |                            |
      | 7. Update server status  |                            |
      |------------------------->|                            |
      |                          |                            |
      | 8. If unhealthy 3x:      |                            |
      |    trigger reconnect     |                            |
      |                          |--------------------------->|
```

---

## Database Schema

### PostgreSQL Tables

```sql
-- External MCP Servers
CREATE TABLE mcp.external_servers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    transport_type VARCHAR(32) NOT NULL,  -- STDIO, SSE, HTTP
    connection_config JSONB NOT NULL,     -- Transport-specific config
    health_check_url TEXT,
    status VARCHAR(32) DEFAULT 'DISCONNECTED',
    last_health_check TIMESTAMP,
    tool_count INTEGER DEFAULT 0,
    error_message TEXT,
    registered_at TIMESTAMP DEFAULT NOW(),
    connected_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for status queries
CREATE INDEX idx_external_servers_status ON mcp.external_servers(status);

-- Aggregated Tools (extends existing tools table)
ALTER TABLE mcp.tools ADD COLUMN IF NOT EXISTS source_server_id UUID
    REFERENCES mcp.external_servers(id) ON DELETE CASCADE;
ALTER TABLE mcp.tools ADD COLUMN IF NOT EXISTS original_name VARCHAR(255);
ALTER TABLE mcp.tools ADD COLUMN IF NOT EXISTS is_external BOOLEAN DEFAULT FALSE;
ALTER TABLE mcp.tools ADD COLUMN IF NOT EXISTS is_classified BOOLEAN DEFAULT FALSE;

-- Index for server-based queries
CREATE INDEX idx_tools_source_server ON mcp.tools(source_server_id)
    WHERE source_server_id IS NOT NULL;

-- Server connection history (for debugging)
CREATE TABLE mcp.server_connection_history (
    id SERIAL PRIMARY KEY,
    server_id UUID REFERENCES mcp.external_servers(id) ON DELETE CASCADE,
    event_type VARCHAR(32) NOT NULL,  -- CONNECTED, DISCONNECTED, ERROR, RECONNECT
    details JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### Qdrant Collection Update

```python
# Extended payload for aggregated tools
TOOLS_COLLECTION_PAYLOAD_EXTENSION = {
    # Existing fields...
    "source_server_id": "keyword",     # UUID of source server
    "source_server_name": "keyword",   # Server name for display
    "original_name": "text",           # Original tool name
    "is_external": "bool",             # True for aggregated tools
    "is_classified": "bool",           # Classification status
}
```

---

## Component Design

### 1. ServerRegistry

```python
class ServerRegistry:
    """
    Manages registration and lifecycle of external MCP servers.
    """

    def __init__(self, db_pool, event_emitter=None):
        self._db_pool = db_pool
        self._event_emitter = event_emitter
        self._servers: Dict[str, ServerConfig] = {}

    async def register_server(
        self,
        name: str,
        transport_type: ServerTransportType,
        connection_config: Dict[str, Any],
        description: Optional[str] = None,
        health_check_url: Optional[str] = None,
        auto_connect: bool = True
    ) -> ServerRecord:
        """
        Register a new external MCP server.

        Args:
            name: Unique server identifier
            transport_type: STDIO, SSE, or HTTP
            connection_config: Transport-specific configuration
            description: Human-readable description
            health_check_url: Optional health endpoint
            auto_connect: Connect immediately after registration

        Returns:
            ServerRecord with server details

        Raises:
            DuplicateServerError: If server name already exists
            ValidationError: If config is invalid
        """
        # Validate config based on transport type
        self._validate_config(transport_type, connection_config)

        # Check for duplicate
        existing = await self._get_server_by_name(name)
        if existing:
            raise DuplicateServerError(f"Server already exists: {name}")

        # Insert into database
        server = await self._insert_server(
            name=name,
            transport_type=transport_type,
            connection_config=connection_config,
            description=description,
            health_check_url=health_check_url
        )

        # Emit registration event
        if self._event_emitter:
            await self._event_emitter.emit("server.registered", server)

        return server

    async def update_status(
        self,
        server_id: str,
        status: ServerStatus,
        error_message: Optional[str] = None
    ) -> None:
        """Update server connection status."""
        await self._db_pool.execute(
            """
            UPDATE mcp.external_servers
            SET status = $1,
                error_message = $2,
                updated_at = NOW(),
                connected_at = CASE WHEN $1 = 'CONNECTED' THEN NOW() ELSE connected_at END
            WHERE id = $3
            """,
            status.value, error_message, server_id
        )

        # Emit status change event
        if self._event_emitter:
            await self._event_emitter.emit("server.status_changed", {
                "server_id": server_id,
                "status": status.value
            })

    async def list_servers(
        self,
        status_filter: Optional[ServerStatus] = None,
        include_tools: bool = False
    ) -> List[ServerRecord]:
        """List all registered servers with optional filtering."""
        query = "SELECT * FROM mcp.external_servers"
        params = []

        if status_filter:
            query += " WHERE status = $1"
            params.append(status_filter.value)

        query += " ORDER BY name"

        rows = await self._db_pool.fetch(query, *params)
        return [ServerRecord(**row) for row in rows]

    async def remove_server(self, server_id: str) -> None:
        """Remove server and cascade delete its tools."""
        # Tools will be deleted via ON DELETE CASCADE
        await self._db_pool.execute(
            "DELETE FROM mcp.external_servers WHERE id = $1",
            server_id
        )
```

### 2. SessionManager

```python
class SessionManager:
    """
    Manages MCP client sessions to external servers.
    Uses MCP SDK ClientSession and ClientSessionGroup.
    """

    def __init__(self, server_registry: ServerRegistry):
        self._server_registry = server_registry
        self._sessions: Dict[str, ClientSession] = {}
        self._transports: Dict[str, Transport] = {}

    async def create_session(self, server_id: str) -> ClientSession:
        """
        Create and connect a session to an external server.

        Args:
            server_id: ID of registered server

        Returns:
            Active ClientSession

        Raises:
            ServerNotFoundError: If server not registered
            ConnectionError: If connection fails
        """
        server = await self._server_registry.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server not found: {server_id}")

        # Create transport based on type
        transport = await self._create_transport(server)

        # Create MCP client session
        session = ClientSession(transport)

        try:
            # Initialize connection
            await session.connect()

            # Store session
            self._sessions[server_id] = session
            self._transports[server_id] = transport

            # Update server status
            await self._server_registry.update_status(
                server_id,
                ServerStatus.CONNECTED
            )

            return session

        except Exception as e:
            await self._server_registry.update_status(
                server_id,
                ServerStatus.ERROR,
                str(e)
            )
            raise ConnectionError(f"Failed to connect: {e}")

    async def _create_transport(self, server: ServerRecord) -> Transport:
        """Create transport based on server configuration."""
        config = server.connection_config

        if server.transport_type == ServerTransportType.STDIO:
            return StdioTransport(
                command=config["command"],
                args=config.get("args", []),
                env=config.get("env", {})
            )

        elif server.transport_type == ServerTransportType.SSE:
            return SSETransport(
                url=config["url"],
                headers=config.get("headers", {})
            )

        elif server.transport_type == ServerTransportType.HTTP:
            return HTTPTransport(
                base_url=config["base_url"],
                headers=config.get("headers", {})
            )

        raise ValueError(f"Unknown transport type: {server.transport_type}")

    async def get_session(self, server_id: str) -> Optional[ClientSession]:
        """Get active session for server."""
        return self._sessions.get(server_id)

    async def close_session(self, server_id: str) -> None:
        """Close session and cleanup resources."""
        session = self._sessions.pop(server_id, None)
        transport = self._transports.pop(server_id, None)

        if session:
            await session.close()
        if transport:
            await transport.close()

        await self._server_registry.update_status(
            server_id,
            ServerStatus.DISCONNECTED
        )

    async def reconnect(self, server_id: str) -> ClientSession:
        """Close existing session and create new one."""
        await self.close_session(server_id)
        return await self.create_session(server_id)
```

### 3. ToolAggregator

```python
class ToolAggregator:
    """
    Discovers and aggregates tools from external MCP servers.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        tool_repository: ToolRepository,
        skill_classifier: SkillClassifier,
        vector_repository: VectorRepository
    ):
        self._session_manager = session_manager
        self._tool_repo = tool_repository
        self._skill_classifier = skill_classifier
        self._vector_repo = vector_repository

    async def discover_tools(self, server_id: str) -> List[AggregatedTool]:
        """
        Discover and index all tools from an external server.

        Args:
            server_id: Server to discover from

        Returns:
            List of discovered and indexed tools
        """
        session = await self._session_manager.get_session(server_id)
        if not session:
            raise SessionNotFoundError(f"No session for server: {server_id}")

        server = await self._server_registry.get_server(server_id)

        # Call tools/list on external server
        response = await session.call_tool("tools/list", {})
        external_tools = response.get("tools", [])

        aggregated_tools = []

        for ext_tool in external_tools:
            # Create aggregated tool with namespacing
            tool = await self._aggregate_tool(
                server=server,
                tool_data=ext_tool
            )
            aggregated_tools.append(tool)

        # Update server tool count
        await self._server_registry.update_tool_count(
            server_id,
            len(aggregated_tools)
        )

        return aggregated_tools

    async def _aggregate_tool(
        self,
        server: ServerRecord,
        tool_data: Dict[str, Any]
    ) -> AggregatedTool:
        """
        Process a single tool from external server.
        """
        original_name = tool_data["name"]
        namespaced_name = f"{server.name}.{original_name}"

        # Store in PostgreSQL
        tool_id = await self._tool_repo.create_tool(
            name=namespaced_name,
            description=tool_data.get("description", ""),
            input_schema=tool_data.get("inputSchema", {}),
            source_server_id=server.id,
            original_name=original_name,
            is_external=True
        )

        # Generate embedding
        embedding_text = f"{namespaced_name}: {tool_data.get('description', '')}"
        embedding = await self._generate_embedding(embedding_text)

        # Index in Qdrant
        await self._vector_repo.upsert_tool(
            tool_id=tool_id,
            name=namespaced_name,
            description=tool_data.get("description", ""),
            embedding=embedding,
            metadata={
                "source_server_id": str(server.id),
                "source_server_name": server.name,
                "original_name": original_name,
                "is_external": True,
                "is_classified": False
            }
        )

        # Queue for classification (async)
        await self._queue_classification(tool_id)

        return AggregatedTool(
            id=tool_id,
            namespaced_name=namespaced_name,
            original_name=original_name,
            source_server_id=server.id,
            description=tool_data.get("description", ""),
            input_schema=tool_data.get("inputSchema", {}),
            is_classified=False
        )

    async def _queue_classification(self, tool_id: int) -> None:
        """Queue tool for async skill classification."""
        # Classification runs in background
        asyncio.create_task(
            self._classify_tool(tool_id)
        )

    async def _classify_tool(self, tool_id: int) -> None:
        """Classify tool using existing skill classifier."""
        try:
            tool = await self._tool_repo.get_tool(tool_id)

            result = await self._skill_classifier.classify_tool(
                tool_id=tool_id,
                tool_name=tool["name"],
                tool_description=tool["description"],
                input_schema_summary=self._summarize_schema(tool["input_schema"])
            )

            # Update tool with classification
            await self._tool_repo.update_tool(
                tool_id=tool_id,
                skill_ids=result.skill_ids,
                primary_skill_id=result.primary_skill_id,
                is_classified=True
            )

            # Update Qdrant
            await self._vector_repo.update_tool_skills(
                tool_id=tool_id,
                skill_ids=result.skill_ids,
                primary_skill_id=result.primary_skill_id
            )

        except Exception as e:
            logger.error(f"Classification failed for tool {tool_id}: {e}")
            # Tool remains searchable but unclassified

    async def remove_server_tools(self, server_id: str) -> int:
        """Remove all tools from a server."""
        # Get tool IDs for Qdrant cleanup
        tool_ids = await self._tool_repo.get_tool_ids_by_server(server_id)

        # Remove from Qdrant
        for tool_id in tool_ids:
            await self._vector_repo.delete_tool(tool_id)

        # Remove from PostgreSQL (cascade handles this)
        return len(tool_ids)
```

### 4. RequestRouter

```python
class RequestRouter:
    """
    Routes tool execution requests to the appropriate external server.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        server_registry: ServerRegistry,
        tool_repository: ToolRepository
    ):
        self._session_manager = session_manager
        self._server_registry = server_registry
        self._tool_repo = tool_repository

    async def resolve_route(
        self,
        tool_name: str,
        server_id: Optional[str] = None
    ) -> RoutingContext:
        """
        Resolve routing for a tool call.

        Args:
            tool_name: Namespaced or original tool name
            server_id: Optional explicit server ID

        Returns:
            RoutingContext with routing decision

        Raises:
            ToolNotFoundError: If tool doesn't exist
            ServerUnavailableError: If server is not connected
        """
        # Parse namespaced name
        if "." in tool_name and not server_id:
            server_name, original_name = tool_name.split(".", 1)
            server = await self._server_registry.get_server_by_name(server_name)
            if server:
                server_id = server.id
                tool_name = original_name

        # Look up tool
        tool = await self._tool_repo.get_tool_by_name(tool_name, server_id)
        if not tool:
            raise ToolNotFoundError(f"Tool not found: {tool_name}")

        # Check server status
        server = await self._server_registry.get_server(tool["source_server_id"])
        if server.status != ServerStatus.CONNECTED:
            raise ServerUnavailableError(
                f"Server unavailable: {server.name}",
                server_id=server.id,
                server_name=server.name,
                status=server.status
            )

        # Get session
        session = await self._session_manager.get_session(server.id)
        if not session:
            raise SessionNotFoundError(f"No active session for: {server.name}")

        return RoutingContext(
            tool_name=tool["original_name"],
            resolved_server_id=server.id,
            original_tool_name=tool["original_name"],
            session=session,
            routing_strategy="namespace_resolved"
        )

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_id: Optional[str] = None
    ) -> ToolResult:
        """
        Execute a tool on an external server.

        Args:
            tool_name: Namespaced or original tool name
            arguments: Tool arguments
            server_id: Optional explicit server ID

        Returns:
            ToolResult from external server
        """
        start_time = time.time()

        # Resolve routing
        routing_start = time.time()
        context = await self.resolve_route(tool_name, server_id)
        routing_time = (time.time() - routing_start) * 1000

        try:
            # Forward to external server
            exec_start = time.time()
            response = await context.session.call_tool(
                context.original_tool_name,
                arguments
            )
            exec_time = (time.time() - exec_start) * 1000

            return ToolResult(
                content=response.get("content", []),
                is_error=response.get("isError", False),
                metadata={
                    "routed_to": context.resolved_server_id,
                    "routing_time_ms": routing_time,
                    "execution_time_ms": exec_time
                }
            )

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(
                content=[{"type": "text", "text": str(e)}],
                is_error=True,
                metadata={
                    "routed_to": context.resolved_server_id,
                    "routing_time_ms": routing_time,
                    "error": str(e)
                }
            )
```

### 5. HealthMonitor

```python
class HealthMonitor:
    """
    Monitors health of connected external servers.
    """

    def __init__(
        self,
        server_registry: ServerRegistry,
        session_manager: SessionManager,
        check_interval: int = 30,
        failure_threshold: int = 3
    ):
        self._server_registry = server_registry
        self._session_manager = session_manager
        self._check_interval = check_interval
        self._failure_threshold = failure_threshold
        self._failure_counts: Dict[str, int] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start health monitoring loop."""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                servers = await self._server_registry.list_servers(
                    status_filter=ServerStatus.CONNECTED
                )

                for server in servers:
                    await self._check_server_health(server)

                await asyncio.sleep(self._check_interval)

            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _check_server_health(self, server: ServerRecord) -> bool:
        """
        Check health of a single server.

        Returns:
            True if healthy, False otherwise
        """
        is_healthy = False

        try:
            if server.health_check_url:
                # HTTP health check
                is_healthy = await self._http_health_check(
                    server.health_check_url
                )
            else:
                # Ping via session
                is_healthy = await self._session_health_check(server.id)

            if is_healthy:
                self._failure_counts[server.id] = 0
                await self._server_registry.update_last_health_check(server.id)
            else:
                await self._handle_health_failure(server)

        except Exception as e:
            logger.warning(f"Health check failed for {server.name}: {e}")
            await self._handle_health_failure(server)

        return is_healthy

    async def _http_health_check(self, url: str, timeout: int = 5) -> bool:
        """Perform HTTP health check."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    return response.status == 200
        except Exception:
            return False

    async def _session_health_check(self, server_id: str) -> bool:
        """Check health via session ping."""
        session = await self._session_manager.get_session(server_id)
        if not session:
            return False

        try:
            # Send ping or list tools as health check
            await session.call_tool("tools/list", {})
            return True
        except Exception:
            return False

    async def _handle_health_failure(self, server: ServerRecord) -> None:
        """Handle a health check failure."""
        self._failure_counts[server.id] = self._failure_counts.get(server.id, 0) + 1

        if self._failure_counts[server.id] >= self._failure_threshold:
            # Mark server as ERROR
            await self._server_registry.update_status(
                server.id,
                ServerStatus.ERROR,
                f"Failed {self._failure_threshold} consecutive health checks"
            )

            # Attempt reconnection
            try:
                await self._session_manager.reconnect(server.id)
                self._failure_counts[server.id] = 0
            except Exception as e:
                logger.error(f"Reconnection failed for {server.name}: {e}")
```

---

## Integration Points

### With Existing Skill Service

```python
# ToolAggregator reuses existing SkillClassifier
from services.skill_service.skill_classifier import SkillClassifier

class ToolAggregator:
    def __init__(self, ..., skill_classifier: SkillClassifier):
        # Same classifier used for internal and external tools
        self._skill_classifier = skill_classifier
```

### With Existing Search Service

```python
# HierarchicalSearchService extended to include external tools
class HierarchicalSearchService:
    async def search(
        self,
        query: str,
        include_external: bool = True,  # New parameter
        server_filter: Optional[List[str]] = None,  # New parameter
        ...
    ) -> HierarchicalSearchResult:
        # Search now includes aggregated tools
        # Filter conditions include is_external and source_server_id
```

### With Existing Vector Service

```python
# VectorRepository extended with new fields
class VectorRepository:
    async def upsert_tool(
        self,
        tool_id: int,
        name: str,
        description: str,
        embedding: List[float],
        metadata: Dict[str, Any]  # Includes source_server_id, is_external
    ) -> None:
        # Standard upsert with extended metadata
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)
1. Database schema updates
2. ServerRegistry implementation
3. SessionManager with transport support
4. Basic connect/disconnect flow

### Phase 2: Tool Aggregation (Week 2-3)
1. ToolAggregator implementation
2. Tool discovery flow
3. Namespacing logic
4. Vector indexing

### Phase 3: Request Routing (Week 3-4)
1. RequestRouter implementation
2. Tool execution flow
3. Error handling
4. Metrics collection

### Phase 4: Health & Classification (Week 4-5)
1. HealthMonitor implementation
2. Skill classification integration
3. Reconnection logic
4. Status management

### Phase 5: Integration & Testing (Week 5-6)
1. Search service integration
2. API endpoints
3. Integration tests
4. Performance testing

---

## Performance Considerations

### Expected Latencies

| Operation | Target | Notes |
|-----------|--------|-------|
| Server registration | < 2s | Database + validation |
| Tool discovery | < 5s/server | Depends on tool count |
| Classification | < 3s/tool | LLM dependent |
| Routing overhead | < 50ms | Parse + lookup |
| Health check | < 5s | HTTP timeout |

### Optimization Strategies

1. **Connection Pooling**: Reuse HTTP connections for SSE/HTTP transports
2. **Batch Classification**: Process multiple tools in parallel
3. **Caching**: Cache routing decisions for frequently used tools
4. **Lazy Loading**: Don't load full tool schemas until needed

---

## TDD Development Plan

### Contract-Driven Development

| Component | Data Contract | Logic Contract |
|-----------|---------------|----------------|
| Aggregator | [data_contract.py](../../tests/contracts/aggregator/data_contract.py) | [logic_contract.md](../../tests/contracts/aggregator/logic_contract.md) |

### Test Layers

```
tests/
├── unit/
│   └── services/
│       └── aggregator/
│           ├── test_server_registry_unit.py
│           ├── test_tool_aggregator_unit.py
│           └── test_request_router_unit.py
├── component/
│   └── services/
│       └── aggregator/
│           ├── test_aggregator_service_tdd.py
│           └── mocks/
│               ├── mock_mcp_server.py
│               └── mock_session.py
├── integration/
│   └── services/
│       └── aggregator/
│           └── test_aggregator_integration.py
└── api/
    └── services/
        └── aggregator/
            └── test_aggregator_api.py
```

---

**Version**: 1.0.0
**Last Updated**: 2025-01-08
**Owner**: ISA MCP Team
