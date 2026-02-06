# Aggregator Service System Contract

**API Contracts, Integration Points, and System-Level Specifications**

This document defines the system-level contracts for the MCP Server Aggregator, including API specifications, integration points, error handling, and deployment requirements.

---

## Table of Contents

1. [API Contract](#api-contract)
2. [Integration Points](#integration-points)
3. [Error Handling Contract](#error-handling-contract)
4. [Security Contract](#security-contract)
5. [Monitoring Contract](#monitoring-contract)
6. [Deployment Contract](#deployment-contract)

---

## API Contract

### Base URL

```
/api/v1/aggregator
```

### Authentication

All endpoints require authentication via the existing ISA MCP auth middleware.

```http
Authorization: Bearer <token>
```

### Content Type

All requests and responses use `application/json`.

---

### Endpoints

#### 1. Server Management

##### POST /servers - Register External Server

**Request**:
```http
POST /api/v1/aggregator/servers
Content-Type: application/json

{
  "name": "github-mcp",
  "description": "GitHub MCP Server for repository operations",
  "transport_type": "SSE",
  "connection_config": {
    "url": "https://github-mcp.example.com/sse",
    "headers": {
      "Authorization": "Bearer ${GITHUB_TOKEN}"
    }
  },
  "health_check_url": "https://github-mcp.example.com/health",
  "auto_connect": true
}
```

**Response - Success (201)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "github-mcp",
  "description": "GitHub MCP Server for repository operations",
  "transport_type": "SSE",
  "status": "CONNECTING",
  "health_check_url": "https://github-mcp.example.com/health",
  "tool_count": 0,
  "registered_at": "2025-01-08T10:00:00Z",
  "connected_at": null
}
```

**Response - Duplicate (409)**:
```json
{
  "detail": "Server already exists: github-mcp",
  "error_code": "SERVER_ALREADY_EXISTS"
}
```

**Response - Validation Error (422)**:
```json
{
  "detail": [
    {
      "loc": ["body", "connection_config", "url"],
      "msg": "SSE transport requires 'url' in connection_config",
      "type": "value_error"
    }
  ]
}
```

---

##### GET /servers - List All Servers

**Request**:
```http
GET /api/v1/aggregator/servers?status=CONNECTED&include_tools=false
```

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| status | string | No | - | Filter by status |
| include_tools | bool | No | false | Include tool list |
| limit | int | No | 100 | Max results |
| offset | int | No | 0 | Pagination offset |

**Response - Success (200)**:
```json
{
  "servers": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "github-mcp",
      "description": "GitHub MCP Server",
      "transport_type": "SSE",
      "status": "CONNECTED",
      "tool_count": 15,
      "last_health_check": "2025-01-08T10:30:00Z",
      "registered_at": "2025-01-08T10:00:00Z",
      "connected_at": "2025-01-08T10:00:05Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

---

##### GET /servers/{id} - Get Server Details

**Request**:
```http
GET /api/v1/aggregator/servers/550e8400-e29b-41d4-a716-446655440000
```

**Response - Success (200)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "github-mcp",
  "description": "GitHub MCP Server for repository operations",
  "transport_type": "SSE",
  "connection_config": {
    "url": "https://github-mcp.example.com/sse"
  },
  "status": "CONNECTED",
  "health_check_url": "https://github-mcp.example.com/health",
  "last_health_check": "2025-01-08T10:30:00Z",
  "tool_count": 15,
  "error_message": null,
  "registered_at": "2025-01-08T10:00:00Z",
  "connected_at": "2025-01-08T10:00:05Z",
  "updated_at": "2025-01-08T10:30:00Z"
}
```

**Response - Not Found (404)**:
```json
{
  "detail": "Server not found: 550e8400-e29b-41d4-a716-446655440000",
  "error_code": "SERVER_NOT_FOUND"
}
```

---

##### POST /servers/{id}/connect - Connect to Server

**Request**:
```http
POST /api/v1/aggregator/servers/550e8400-e29b-41d4-a716-446655440000/connect
```

**Response - Success (200)**:
```json
{
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CONNECTING",
  "message": "Connection initiated"
}
```

**Response - Already Connected (200)**:
```json
{
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CONNECTED",
  "message": "Server already connected"
}
```

---

##### POST /servers/{id}/disconnect - Disconnect from Server

**Request**:
```http
POST /api/v1/aggregator/servers/550e8400-e29b-41d4-a716-446655440000/disconnect
Content-Type: application/json

{
  "force": false
}
```

**Response - Success (200)**:
```json
{
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "DISCONNECTED",
  "pending_requests": 0,
  "message": "Server disconnected successfully"
}
```

**Response - Pending Requests (200)**:
```json
{
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "DISCONNECTING",
  "pending_requests": 3,
  "message": "Waiting for 3 pending requests to complete"
}
```

---

##### DELETE /servers/{id} - Remove Server

**Request**:
```http
DELETE /api/v1/aggregator/servers/550e8400-e29b-41d4-a716-446655440000
```

**Response - Success (204)**:
No content.

**Response - Not Found (404)**:
```json
{
  "detail": "Server not found: 550e8400-e29b-41d4-a716-446655440000",
  "error_code": "SERVER_NOT_FOUND"
}
```

---

#### 2. Tool Management

##### GET /servers/{id}/tools - List Server Tools

**Request**:
```http
GET /api/v1/aggregator/servers/550e8400-e29b-41d4-a716-446655440000/tools
```

**Response - Success (200)**:
```json
{
  "tools": [
    {
      "id": "1",
      "name": "github-mcp.create_issue",
      "original_name": "create_issue",
      "description": "Create a new GitHub issue",
      "skill_ids": ["code_management", "issue_tracking"],
      "primary_skill_id": "issue_tracking",
      "is_classified": true,
      "discovered_at": "2025-01-08T10:00:10Z"
    }
  ],
  "total": 15,
  "classified": 15,
  "unclassified": 0
}
```

---

##### POST /servers/{id}/tools/refresh - Refresh Tools

**Request**:
```http
POST /api/v1/aggregator/servers/550e8400-e29b-41d4-a716-446655440000/tools/refresh
```

**Response - Success (202)**:
```json
{
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "REFRESHING",
  "message": "Tool discovery initiated"
}
```

---

#### 3. Aggregator State

##### GET /state - Get Aggregator State

**Request**:
```http
GET /api/v1/aggregator/state
```

**Response - Success (200)**:
```json
{
  "total_servers": 5,
  "connected_servers": 4,
  "disconnected_servers": 0,
  "error_servers": 1,
  "connecting_servers": 0,
  "total_tools": 125,
  "classified_tools": 120,
  "unclassified_tools": 5,
  "last_sync": "2025-01-08T10:00:00Z",
  "health_check_interval_seconds": 30,
  "uptime_seconds": 86400
}
```

---

#### 4. Health

##### GET /health - Health Check

**Request**:
```http
GET /api/v1/aggregator/health
```

**Response - Healthy (200)**:
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "qdrant": "ok",
    "sessions": "ok"
  },
  "servers": {
    "total": 5,
    "connected": 4,
    "error": 1
  }
}
```

**Response - Degraded (200)**:
```json
{
  "status": "degraded",
  "checks": {
    "database": "ok",
    "qdrant": "ok",
    "sessions": "degraded"
  },
  "servers": {
    "total": 5,
    "connected": 2,
    "error": 3
  },
  "issues": [
    "3 servers in error state"
  ]
}
```

---

### Extended Search API

The existing search API is extended to support external servers:

##### POST /api/v1/search - Aggregated Search

**Request**:
```http
POST /api/v1/search
Content-Type: application/json

{
  "query": "create a GitHub issue",
  "item_type": "tool",
  "include_external": true,
  "server_filter": ["github-mcp"],
  "limit": 10,
  "skill_threshold": 0.4,
  "tool_threshold": 0.3,
  "include_schemas": true,
  "strategy": "hierarchical"
}
```

**New Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| include_external | bool | No | true | Include external server tools |
| server_filter | string[] | No | null | Limit to specific servers |

**Response - Success (200)**:
```json
{
  "query": "create a GitHub issue",
  "tools": [
    {
      "id": "1",
      "db_id": 1,
      "type": "tool",
      "name": "github-mcp.create_issue",
      "original_name": "create_issue",
      "description": "Create a new GitHub issue",
      "score": 0.95,
      "skill_ids": ["code_management", "issue_tracking"],
      "primary_skill_id": "issue_tracking",
      "source_server": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "github-mcp",
        "status": "CONNECTED"
      },
      "input_schema": {
        "type": "object",
        "properties": {
          "repo": {"type": "string"},
          "title": {"type": "string"},
          "body": {"type": "string"}
        },
        "required": ["repo", "title"]
      }
    }
  ],
  "matched_skills": [...],
  "metadata": {
    "strategy_used": "hierarchical",
    "servers_searched": 3,
    "external_tools_count": 45,
    "total_time_ms": 125.5
  }
}
```

---

### Extended Tool Execution API

##### POST /api/v1/tools/call - Execute Tool

**Request**:
```http
POST /api/v1/tools/call
Content-Type: application/json

{
  "name": "github-mcp.create_issue",
  "arguments": {
    "repo": "owner/repo",
    "title": "Bug report",
    "body": "Description of the bug"
  }
}
```

**Alternative with explicit server**:
```json
{
  "name": "create_issue",
  "arguments": {...},
  "server_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response - Success (200)**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"issue_number\": 123, \"url\": \"https://github.com/owner/repo/issues/123\"}"
    }
  ],
  "isError": false,
  "metadata": {
    "routed_to": "github-mcp",
    "server_id": "550e8400-e29b-41d4-a716-446655440000",
    "routing_time_ms": 12.5,
    "execution_time_ms": 450.2,
    "total_time_ms": 462.7
  }
}
```

**Response - Server Unavailable (503)**:
```json
{
  "detail": "Server unavailable: github-mcp",
  "error_code": "SERVER_UNAVAILABLE",
  "server": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "github-mcp",
    "status": "ERROR"
  }
}
```

---

## Integration Points

### 1. Database Integration

**PostgreSQL Schema**: `mcp`

**Tables Used**:
- `mcp.external_servers` - Server registrations
- `mcp.tools` - Extended with external tool fields
- `mcp.server_connection_history` - Connection events

**Connection**:
```python
# Uses existing PostgreSQL client
from isa_common import AsyncPostgresClient

postgres_client = AsyncPostgresClient(
    host=settings.infrastructure.postgres_grpc_host,
    port=settings.infrastructure.postgres_grpc_port,  # 50061
    user_id="mcp-aggregator-service"
)
```

---

### 2. Vector Database Integration

**Qdrant Collection**: `mcp_unified_search`

**Extended Payload Fields**:
```json
{
  "source_server_id": "uuid",
  "source_server_name": "string",
  "original_name": "string",
  "is_external": true,
  "is_classified": true
}
```

**Connection**:
```python
# Uses existing Qdrant client
from isa_common import AsyncQdrantClient

qdrant_client = AsyncQdrantClient(
    host=settings.infrastructure.qdrant_grpc_host,
    port=settings.infrastructure.qdrant_grpc_port,
    user_id="mcp-aggregator-service"
)
```

---

### 3. Skill Service Integration

**Reuses Existing Components**:
- `SkillClassifier` - For tool classification
- `SkillRepository` - For skill lookups
- Skill embedding updates

**Integration Pattern**:
```python
from services.skill_service.skill_classifier import SkillClassifier

class ToolAggregator:
    def __init__(self, skill_classifier: SkillClassifier):
        self._skill_classifier = skill_classifier

    async def classify_external_tool(self, tool_id: int):
        # Same classification as internal tools
        result = await self._skill_classifier.classify_tool(...)
```

---

### 4. Search Service Integration

**Extended HierarchicalSearchService**:
```python
class HierarchicalSearchService:
    async def search(
        self,
        query: str,
        include_external: bool = True,  # New
        server_filter: List[str] = None,  # New
        ...
    ):
        # Adds filter for external tools if needed
        if not include_external:
            filter_conditions["must"].append({
                "field": "is_external",
                "match": {"value": False}
            })

        if server_filter:
            filter_conditions["should"] = [
                {"field": "source_server_name", "match": {"keyword": name}}
                for name in server_filter
            ]
```

---

### 5. MCP SDK Integration

**Client Session Management**:
```python
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

# STDIO transport
async with stdio_client(command, args) as (read, write):
    session = ClientSession(read, write)
    await session.initialize()

# SSE transport
async with sse_client(url, headers) as (read, write):
    session = ClientSession(read, write)
    await session.initialize()
```

---

## Error Handling Contract

### Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "context": {
    "additional": "information"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SERVER_NOT_FOUND` | 404 | Server ID does not exist |
| `SERVER_ALREADY_EXISTS` | 409 | Duplicate server name |
| `SERVER_UNAVAILABLE` | 503 | Server not connected |
| `SERVER_CONNECTION_FAILED` | 503 | Failed to establish connection |
| `TOOL_NOT_FOUND` | 404 | Tool does not exist |
| `TOOL_AMBIGUOUS` | 400 | Multiple tools match, need server_id |
| `SESSION_NOT_FOUND` | 503 | No active session for server |
| `ROUTING_FAILED` | 500 | Failed to resolve routing |
| `EXECUTION_FAILED` | 502 | External server returned error |
| `HEALTH_CHECK_FAILED` | 503 | Health check failed |
| `CLASSIFICATION_FAILED` | 500 | Tool classification failed |
| `VALIDATION_ERROR` | 422 | Request validation failed |

### Retry Behavior

| Error Code | Retry | Strategy |
|------------|-------|----------|
| `SERVER_UNAVAILABLE` | Yes | Exponential backoff |
| `SERVER_CONNECTION_FAILED` | Yes | 3 attempts, backoff |
| `SESSION_NOT_FOUND` | Yes | Reconnect once |
| `EXECUTION_FAILED` | No | Return to client |
| `ROUTING_FAILED` | No | Return to client |

---

## Security Contract

### Credential Storage

**Encryption**:
- `connection_config` encrypted at rest using AES-256
- Encryption key from environment: `MCP_CREDENTIAL_KEY`

**Secrets in Config**:
- Use `${VARIABLE}` syntax for environment variable substitution
- Never log raw credentials
- Mask credentials in API responses

**Example**:
```json
{
  "connection_config": {
    "headers": {
      "Authorization": "Bearer ${GITHUB_TOKEN}"
    }
  }
}
```

### Transport Security

| Transport | Security |
|-----------|----------|
| STDIO | Local process, OS security |
| SSE | TLS 1.2+ required |
| HTTP | TLS 1.2+ required |

### Audit Logging

All server operations logged:
```json
{
  "event": "server.registered",
  "server_id": "uuid",
  "server_name": "github-mcp",
  "actor": "user@example.com",
  "timestamp": "2025-01-08T10:00:00Z",
  "ip_address": "192.168.1.1"
}
```

---

## Monitoring Contract

### Metrics Exposed

**Prometheus Metrics**:

```prometheus
# Server metrics
mcp_aggregator_servers_total{status="connected"} 4
mcp_aggregator_servers_total{status="error"} 1

# Tool metrics
mcp_aggregator_tools_total 125
mcp_aggregator_tools_classified 120

# Request metrics
mcp_aggregator_routing_duration_seconds_bucket{le="0.05"} 1000
mcp_aggregator_routing_duration_seconds_bucket{le="0.1"} 1050

mcp_aggregator_execution_duration_seconds_bucket{server="github-mcp",le="1"} 500

# Health metrics
mcp_aggregator_health_check_duration_seconds{server="github-mcp"} 0.045
mcp_aggregator_health_check_failures_total{server="github-mcp"} 2
```

### Health Endpoint

```http
GET /api/v1/aggregator/health
```

Returns aggregated health status of all components.

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Connected servers | < 80% | < 50% |
| Routing latency p95 | > 75ms | > 100ms |
| Health check failures | 2 consecutive | 3 consecutive |
| Unclassified tools | > 20% | > 50% |

---

## Deployment Contract

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_AGGREGATOR_ENABLED` | No | true | Enable aggregator |
| `MCP_AGGREGATOR_MAX_SERVERS` | No | 50 | Max external servers |
| `MCP_AGGREGATOR_HEALTH_INTERVAL` | No | 30 | Health check interval (s) |
| `MCP_AGGREGATOR_CONNECTION_TIMEOUT` | No | 30 | Connection timeout (s) |
| `MCP_AGGREGATOR_REQUEST_TIMEOUT` | No | 60 | Request timeout (s) |
| `MCP_CREDENTIAL_KEY` | Yes | - | Credential encryption key |

### Dependencies

**Required Services**:
- PostgreSQL (gRPC: 50061)
- Qdrant (gRPC: 50055)
- Model Service (for embeddings)
- Redis (for caching, optional)

**Health Check**:
```yaml
livenessProbe:
  httpGet:
    path: /api/v1/aggregator/health
    port: 8081
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /api/v1/aggregator/health
    port: 8081
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 500m | 2000m |
| Memory | 512Mi | 2Gi |

### Scaling

- Horizontal scaling supported
- Session affinity recommended for WebSocket connections
- Shared PostgreSQL for state consistency

---

**Version**: 1.0.0
**Last Updated**: 2025-01-08
**Owner**: ISA MCP Team
