# Aggregator Service Logic Contract

**Business Rules and Specifications for MCP Server Aggregator Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for aggregator service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Algorithms](#algorithms)
4. [API Contracts](#api-contracts)
5. [Performance SLAs](#performance-slas)
6. [Edge Cases](#edge-cases)

---

## Business Rules

### BR-001: Server Registration

**Given**: Valid server registration request from admin
**When**: Admin registers a new external MCP server
**Then**:
- Server name validated (lowercase, starts with letter, hyphens/underscores allowed)
- Connection config validated based on transport type
- Server record created in `mcp.external_servers` table
- Status set to `DISCONNECTED` initially
- If `auto_connect=true`, connection attempt initiated

**Validation Rules**:
- `name`: Required, format `^[a-z][a-z0-9_-]*$`, max 255 chars, unique
- `transport_type`: Required, one of `STDIO`, `SSE`, `HTTP`
- `connection_config`: Required, must contain transport-specific fields
- `description`: Optional, max 1000 chars
- `health_check_url`: Optional, valid URL format

**Transport-Specific Config Requirements**:

| Transport | Required Fields | Optional Fields |
|-----------|----------------|-----------------|
| STDIO | `command` | `args`, `env` |
| SSE | `url` | `headers` |
| HTTP | `base_url` | `headers` |

**Edge Cases**:
- Duplicate name -> **409 Conflict** `{"detail": "Server already exists: {name}"}`
- Invalid name format -> **422 Validation Error**
- Missing config field -> **422 Validation Error**

---

### BR-002: Server Connection

**Given**: Registered server with valid configuration
**When**: Connection is requested (auto or manual)
**Then**:
- Status changes to `CONNECTING`
- Transport created based on `transport_type`
- MCP ClientSession established
- If successful: status -> `CONNECTED`, `connected_at` updated
- If failed: status -> `ERROR`, `error_message` populated
- Tool discovery triggered on successful connection

**Connection Steps**:
1. Create transport (STDIO/SSE/HTTP)
2. Initialize ClientSession with transport
3. Call `session.connect()`
4. Update server status
5. Trigger tool discovery

**Timeout Rules**:
- Connection timeout: 30 seconds
- Retry on failure: 3 attempts with exponential backoff (1s, 2s, 4s)

**Edge Cases**:
- Server already connected -> Idempotent (return success)
- Network unreachable -> Status `ERROR`, retry scheduled
- Invalid credentials -> Status `ERROR`, log security warning

---

### BR-003: Tool Discovery

**Given**: Connected external MCP server
**When**: Tool discovery is triggered
**Then**:
- Call `tools/list` on external server
- For each tool:
  - Apply namespacing: `{server_name}.{tool_name}`
  - Store in `mcp.tools` with `source_server_id`, `original_name`
  - Generate embedding for tool
  - Index in Qdrant with server metadata
  - Queue for skill classification
- Update `mcp.external_servers.tool_count`

**Namespacing Rules**:
- Format: `{server_name}.{original_tool_name}`
- Server name from registration (lowercase)
- Original name preserved in `original_name` field
- Internal ISA tools NOT namespaced

**Tool Storage**:
```sql
INSERT INTO mcp.tools (
    name,           -- Namespaced name
    original_name,  -- Original from server
    description,
    input_schema,
    source_server_id,
    is_external,
    is_classified
) VALUES ($1, $2, $3, $4, $5, TRUE, FALSE)
```

**Edge Cases**:
- Server returns empty tool list -> Log warning, set `tool_count=0`
- Duplicate tool name from same server -> Update existing
- Tool with same namespaced name from different server -> Impossible (namespace includes server)

---

### BR-004: Skill Classification for External Tools

**Given**: Aggregated tool from external server
**When**: Classification is triggered
**Then**:
- Same classification process as internal tools (BR-002 in skill contract)
- LLM assigns 1-3 skill categories with confidence scores
- Assignments with confidence >= 0.5 saved
- Primary skill determined
- Tool updated with `skill_ids`, `primary_skill_id`, `is_classified=true`
- Qdrant payload updated
- Skill embeddings updated

**Classification Rules**:
- Same rules as internal tools
- External tools use same skill schema
- Classification runs asynchronously (don't block discovery)
- Failed classification -> `is_classified=false`, tool still searchable

**Batch Classification**:
- For servers with 50+ tools: batch processing with concurrency limit (5)
- Target: 50 tools classified within 60 seconds

---

### BR-005: Request Routing

**Given**: Tool execution request for aggregated tool
**When**: Request is processed
**Then**:
- Parse tool name to extract server and original name
- Resolve target server
- Verify server status is `CONNECTED`
- Get active session
- Forward request to external server
- Return response to client

**Name Resolution**:
1. If `server_id` provided explicitly -> Use directly
2. If namespaced name (`server.tool`) -> Parse and resolve
3. If original name only -> Lookup in tools table

**Routing Decision**:
```python
def resolve_route(tool_name: str, server_id: Optional[str]) -> RoutingContext:
    if server_id:
        return RoutingContext(strategy=EXPLICIT_SERVER)

    if "." in tool_name:
        server_name, original_name = tool_name.split(".", 1)
        server = lookup_by_name(server_name)
        return RoutingContext(strategy=NAMESPACE_RESOLVED)

    tool = lookup_tool_by_name(tool_name)
    return RoutingContext(strategy=LOOKUP_RESOLVED)
```

**Error Handling**:
- Server disconnected -> **503 Service Unavailable** with server info
- Session not found -> Attempt reconnect, then 503 if still failed
- Tool not found -> **404 Not Found**
- Execution error -> Forward error from external server

---

### BR-006: Health Monitoring

**Given**: Connected external servers
**When**: Health check interval elapsed (default: 30s)
**Then**:
- For each connected server:
  - If `health_check_url` configured: HTTP GET with 5s timeout
  - Otherwise: ping session (call `tools/list`)
- Update `last_health_check` timestamp
- Track consecutive failures

**Health Status Transitions**:
- 1 failure: Status remains `CONNECTED`, log warning
- 2 failures: Status -> `DEGRADED`
- 3+ failures: Status -> `ERROR`, reconnection scheduled

**Health Metrics**:
- `response_time_ms`: Health check latency
- `consecutive_failures`: Count since last success
- `last_error`: Most recent error message

**Edge Cases**:
- Health check timeout -> Count as failure
- Server returns 5xx -> Count as failure
- Server returns 4xx -> Log warning, don't count as failure (config issue)

---

### BR-007: Server Disconnection

**Given**: Connected server
**When**: Disconnect requested (manual or error-triggered)
**Then**:
- Wait for pending requests to complete (timeout: 30s)
- Close session gracefully
- Update status to `DISCONNECTED`
- Mark server's tools as unavailable in search results
- Do NOT delete tools (they remain for reconnection)

**Pending Request Handling**:
- If `force=true`: Cancel pending requests immediately
- If `force=false`: Wait up to 30s for completion
- Requests in flight when timeout reached -> Return 503 to clients

**Tool Availability**:
- Tools remain in database and Qdrant
- Filter condition added: `source_server.status = CONNECTED`
- On reconnection: tools become available again

---

### BR-008: Server Removal

**Given**: Registered server (connected or not)
**When**: Admin deletes server
**Then**:
- If connected: disconnect first (BR-007)
- Delete all server's tools from PostgreSQL (cascade)
- Delete all server's tools from Qdrant
- Delete server record
- Recalculate affected skill embeddings

**Cascade Delete**:
```sql
DELETE FROM mcp.external_servers WHERE id = $1;
-- ON DELETE CASCADE removes related tools
```

**Skill Embedding Update**:
- Identify skills that had tools from this server
- Recalculate embeddings for affected skills
- If skill now empty (0 tools), use description embedding

---

### BR-009: Tool Name Collision Prevention

**Given**: Multiple servers with tools having same original name
**When**: Tools are discovered
**Then**:
- Namespacing prevents collision: `{server_name}.{tool_name}`
- Each tool uniquely identifiable
- Search returns all matching tools with server info
- User can choose which server's tool to invoke

**Example**:
```
Server A: search_tool -> a-server.search_tool
Server B: search_tool -> b-server.search_tool
```

**Search Behavior**:
- Query "search tool" returns both with their servers
- Results include `source_server` object for clarity
- Client must specify which to invoke

---

## State Machines

### Server Lifecycle State Machine

```
                                  +---------+
                                  |  START  |
                                  +----+----+
                                       |
                                       | register_server()
                                       v
+-------+                        +------------+
| ERROR |<-------- error --------|DISCONNECTED|<------------+
+---+---+                        +-----+------+             |
    |                                  |                    |
    | reconnect()                      | connect()          | disconnect()
    |                                  v                    |
    |                           +------------+              |
    +-------------------------->| CONNECTING |              |
                                +-----+------+              |
                                      |                     |
                                      | success             |
                                      v                     |
+----------+                    +-----------+               |
| DEGRADED |<-- health_fail x2 -| CONNECTED |---------------+
+----+-----+                    +-----+-----+
     |                                |
     | health_fail x3                 | health_ok
     v                                |
+-------+                             |
| ERROR |<----------------------------+
+-------+     health_fail x3
```

**Valid Transitions**:

| From | To | Trigger |
|------|-----|---------|
| - | DISCONNECTED | register_server() |
| DISCONNECTED | CONNECTING | connect() |
| CONNECTING | CONNECTED | connection success |
| CONNECTING | ERROR | connection failure |
| CONNECTED | DISCONNECTED | disconnect() |
| CONNECTED | DEGRADED | 2 health failures |
| CONNECTED | ERROR | 3+ health failures |
| DEGRADED | CONNECTED | health check success |
| DEGRADED | ERROR | 3+ total health failures |
| ERROR | CONNECTING | reconnect() |

**Behavior by State**:

| State | Tool Discovery | Tool Execution | Search Inclusion |
|-------|---------------|----------------|------------------|
| DISCONNECTED | No | No | No |
| CONNECTING | No | No | No |
| CONNECTED | Yes | Yes | Yes |
| DEGRADED | No | Yes (with warning) | Yes |
| ERROR | No | No | No |

---

### Tool Classification State Machine

```
+--------------+
| DISCOVERED   | <- Initial state after discovery
+------+-------+
       |
       | queue_classification()
       v
+--------------+
| CLASSIFYING  |
+------+-------+
       |
       +--------+--------+
       |                 |
       | success         | failure
       v                 v
+-----------+     +---------------+
| CLASSIFIED |    | UNCLASSIFIED  |
+-----------+     +---------------+
       |                 |
       | reclassify()    | retry()
       |                 |
       +--------+--------+
                |
                v
         +--------------+
         | CLASSIFYING  |
         +--------------+
```

---

## Algorithms

### Namespacing Algorithm

```python
def namespace_tool(server_name: str, tool_name: str) -> str:
    """
    Create namespaced tool name.

    Args:
        server_name: Registered server name (already lowercase)
        tool_name: Original tool name from server

    Returns:
        Namespaced name: "{server_name}.{tool_name}"
    """
    return f"{server_name}.{tool_name}"

def parse_namespaced_name(namespaced: str) -> Tuple[str, str]:
    """
    Parse namespaced name into server and tool.

    Args:
        namespaced: Full namespaced name

    Returns:
        Tuple of (server_name, original_tool_name)

    Raises:
        ValueError if not a valid namespaced name
    """
    if "." not in namespaced:
        raise ValueError(f"Not a namespaced name: {namespaced}")

    parts = namespaced.split(".", 1)
    return parts[0], parts[1]
```

### Health Check Algorithm

```python
async def check_server_health(server: ServerRecord) -> HealthResult:
    """
    Check health of a single server.

    Priority:
    1. Use health_check_url if configured
    2. Fall back to session ping

    Returns:
        HealthResult with status and metrics
    """
    start_time = time.time()

    try:
        if server.health_check_url:
            # HTTP health check
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    server.health_check_url,
                    timeout=HEALTH_CHECK_TIMEOUT
                ) as response:
                    is_healthy = response.status == 200
        else:
            # Session ping
            session = get_session(server.id)
            await session.call_tool("tools/list", {})
            is_healthy = True

        response_time = (time.time() - start_time) * 1000

        return HealthResult(
            healthy=is_healthy,
            response_time_ms=response_time,
            error=None
        )

    except Exception as e:
        return HealthResult(
            healthy=False,
            response_time_ms=None,
            error=str(e)
        )
```

### Routing Resolution Algorithm

```python
async def resolve_route(
    tool_name: str,
    server_id: Optional[str] = None
) -> RoutingContext:
    """
    Resolve routing for tool execution.

    Resolution order:
    1. Explicit server_id
    2. Parse namespaced name
    3. Lookup by original name (ambiguous if multiple)
    """
    # Method 1: Explicit server ID
    if server_id:
        server = await get_server(server_id)
        if not server:
            raise ServerNotFoundError(server_id)
        return RoutingContext(
            resolved_server_id=server_id,
            original_tool_name=tool_name,
            strategy=RoutingStrategy.EXPLICIT_SERVER
        )

    # Method 2: Parse namespaced name
    if "." in tool_name:
        server_name, original_name = tool_name.split(".", 1)
        server = await get_server_by_name(server_name)
        if server:
            return RoutingContext(
                resolved_server_id=server.id,
                original_tool_name=original_name,
                strategy=RoutingStrategy.NAMESPACE_RESOLVED
            )

    # Method 3: Lookup by name
    tools = await find_tools_by_original_name(tool_name)
    if not tools:
        raise ToolNotFoundError(tool_name)
    if len(tools) > 1:
        raise AmbiguousToolError(tool_name, [t.source_server_id for t in tools])

    return RoutingContext(
        resolved_server_id=tools[0].source_server_id,
        original_tool_name=tool_name,
        strategy=RoutingStrategy.LOOKUP_RESOLVED
    )
```

---

## API Contracts

### POST /api/v1/aggregator/servers
**Register External Server**

**Request**: `application/json`
```json
{
  "name": "github-mcp",
  "description": "GitHub MCP Server",
  "transport_type": "SSE",
  "connection_config": {
    "url": "https://github-mcp.example.com/sse",
    "headers": {"Authorization": "Bearer ${TOKEN}"}
  },
  "health_check_url": "https://github-mcp.example.com/health",
  "auto_connect": true
}
```

**Success Response**: `201 Created`
```json
{
  "id": "uuid-1234",
  "name": "github-mcp",
  "status": "CONNECTING",
  "transport_type": "SSE",
  "tool_count": 0,
  "registered_at": "2025-01-08T10:00:00Z"
}
```

**Error Responses**:
- `409 Conflict`: Server name already exists
- `422 Validation Error`: Invalid request data

---

### GET /api/v1/aggregator/servers
**List External Servers**

**Query Parameters**:
- `status`: Filter by status (optional)
- `include_tools`: Include tool list (optional, default: false)

**Success Response**: `200 OK`
```json
[
  {
    "id": "uuid-1234",
    "name": "github-mcp",
    "status": "CONNECTED",
    "tool_count": 15,
    "last_health_check": "2025-01-08T10:30:00Z"
  }
]
```

---

### GET /api/v1/aggregator/servers/{id}
**Get Server Details**

**Success Response**: `200 OK`
```json
{
  "id": "uuid-1234",
  "name": "github-mcp",
  "description": "GitHub MCP Server",
  "transport_type": "SSE",
  "status": "CONNECTED",
  "health_check_url": "https://github-mcp.example.com/health",
  "last_health_check": "2025-01-08T10:30:00Z",
  "tool_count": 15,
  "registered_at": "2025-01-08T10:00:00Z",
  "connected_at": "2025-01-08T10:00:05Z"
}
```

**Error Responses**:
- `404 Not Found`: Server not found

---

### POST /api/v1/aggregator/servers/{id}/connect
**Connect to Server**

**Success Response**: `200 OK`
```json
{
  "status": "CONNECTING",
  "message": "Connection initiated"
}
```

**Error Responses**:
- `404 Not Found`: Server not found
- `409 Conflict`: Server already connected

---

### POST /api/v1/aggregator/servers/{id}/disconnect
**Disconnect from Server**

**Request** (optional):
```json
{
  "force": false
}
```

**Success Response**: `200 OK`
```json
{
  "status": "DISCONNECTED",
  "pending_requests": 0
}
```

---

### DELETE /api/v1/aggregator/servers/{id}
**Remove Server**

**Success Response**: `204 No Content`

**Error Responses**:
- `404 Not Found`: Server not found

---

### GET /api/v1/aggregator/servers/{id}/tools
**List Server Tools**

**Success Response**: `200 OK`
```json
[
  {
    "id": "1",
    "name": "github-mcp.create_issue",
    "original_name": "create_issue",
    "description": "Create GitHub issue",
    "skill_ids": ["code_management"],
    "is_classified": true
  }
]
```

---

### GET /api/v1/aggregator/state
**Get Aggregator State**

**Success Response**: `200 OK`
```json
{
  "total_servers": 5,
  "connected_servers": 4,
  "disconnected_servers": 0,
  "error_servers": 1,
  "total_tools": 125,
  "classified_tools": 120,
  "unclassified_tools": 5,
  "last_sync": "2025-01-08T10:00:00Z"
}
```

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Server registration | < 2s | < 5s |
| Server connection | < 10s | < 30s |
| Tool discovery (per server) | < 5s | < 15s |
| Classification (per tool) | < 3s | < 10s |
| Search (with external) | < 150ms | < 300ms |
| Tool execution routing | < 50ms | < 100ms |
| Health check | < 5s | < 10s |

### Throughput Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Server registrations | 10/min | Admin operations |
| Concurrent connections | 20+ | Active sessions |
| Tool executions | 100 req/s | Routed requests |
| Health checks | 10/s | Parallel checks |

### Resource Limits

| Resource | Limit |
|----------|-------|
| Max servers | 50 |
| Max tools per server | 1000 |
| Max total tools | 10,000 |
| Max concurrent sessions | 50 |
| Connection timeout | 30s |
| Health check timeout | 5s |
| Request timeout | 60s |

---

## Edge Cases

### EC-001: Connection During Maintenance

**Scenario**: Server is temporarily down for maintenance
**Expected**: Connection fails, status ERROR, auto-retry scheduled
**Solution**: Exponential backoff retry (1s, 2s, 4s, 8s, max 5 attempts)

---

### EC-002: Tool Name Contains Dot

**Scenario**: External server has tool named "api.v2.create"
**Expected**: Namespacing still works correctly
**Solution**: Only first dot separates server from tool name
- Input: `server-a.api.v2.create`
- Parsed: server=`server-a`, tool=`api.v2.create`

---

### EC-003: Server Disconnects During Tool Execution

**Scenario**: Connection lost while tool call in progress
**Expected**: Client receives 503 with partial error info
**Solution**:
- Detect disconnection
- Return 503 Service Unavailable
- Include context about what was in progress
- Schedule reconnection

---

### EC-004: Duplicate Tool Registration

**Scenario**: Same server registered twice (different process)
**Expected**: Second registration fails with 409
**Solution**: Database unique constraint on server name

---

### EC-005: Health Check URL Returns Non-200

**Scenario**: Health endpoint returns 500 or other error
**Expected**: Count as health failure
**Solution**: Only 200 is considered healthy

---

### EC-006: Large Tool Discovery

**Scenario**: Server returns 500+ tools
**Expected**: Discovery completes without timeout
**Solution**:
- Batch processing for large tool sets
- Progress tracking
- Classification queued in batches of 10

---

### EC-007: Concurrent Tool Executions to Same Server

**Scenario**: Multiple clients call tools on same server simultaneously
**Expected**: All requests handled correctly
**Solution**:
- Session is thread-safe
- No request interleaving
- Queue if needed (transport-dependent)

---

### EC-008: Server Renamed

**Scenario**: Admin wants to rename registered server
**Expected**: Namespaced tool names must be updated
**Solution**:
- API does not support rename (delete + re-add)
- Or: Update all tool names atomically

---

### EC-009: Classification Service Unavailable

**Scenario**: LLM service down during tool discovery
**Expected**: Tools discovered but unclassified
**Solution**:
- `is_classified=false` for all tools
- Tools searchable via direct search
- Retry classification when service recovers

---

### EC-010: Session Stale After Network Glitch

**Scenario**: Network briefly interrupted, session might be stale
**Expected**: Detect and reconnect automatically
**Solution**:
- Health check detects stale session
- Trigger reconnection
- Queue pending requests

---

## Test Coverage Requirements

All tests MUST cover:

- Business Rules (BR-XXX success scenarios)
- State transitions (valid and invalid)
- All transport types (STDIO, SSE, HTTP)
- Namespacing and routing logic
- Health check scenarios
- Error handling (503, 404, 409)
- Edge cases (EC-XXX scenarios)
- Performance within SLAs
- Concurrent operations

---

**Version**: 1.0.0
**Last Updated**: 2025-01-08
**Owner**: ISA MCP Team
