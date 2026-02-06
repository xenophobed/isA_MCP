# MCP Server Aggregator - Product Requirements Document (PRD)

**Meta MCP Server for External Server Aggregation**

This document defines user stories, requirements, and acceptance criteria for the MCP Server Aggregator feature.

---

## Table of Contents

1. [Overview](#overview)
2. [Epic: Server Aggregation](#epic-server-aggregation)
3. [User Stories](#user-stories)
4. [Non-Functional Requirements](#non-functional-requirements)
5. [Acceptance Criteria Summary](#acceptance-criteria-summary)

---

## Overview

### Problem Statement

Organizations using MCP face integration challenges:

1. **Fragmented Tool Landscape**: Multiple MCP servers from different teams/vendors
2. **No Unified Discovery**: Each server requires separate discovery
3. **Manual Integration**: Connection management is manual and error-prone
4. **No Classification**: External tools lack skill-based organization
5. **Health Blind Spots**: No centralized monitoring of server health

### Solution

Implement an **MCP Server Aggregator** that:

1. Connects to multiple external MCP servers (STDIO, SSE, HTTP)
2. Aggregates tools into a unified registry
3. Applies skill-based classification to external tools
4. Routes tool calls to the appropriate backend server
5. Monitors health and handles connection lifecycle

### Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| External servers supported | 0 | 10+ concurrent |
| Tool discovery latency | N/A | < 5s per server |
| Routing latency overhead | N/A | < 50ms |
| Classification success rate | N/A | > 95% |
| Connection uptime | N/A | > 99.9% |

---

## Epic: Server Aggregation

### Epic ID: AG

**Description**: Enable ISA MCP to connect to and aggregate multiple external MCP servers, providing unified tool discovery and intelligent routing.

### Epic Scope

| In Scope | Out of Scope |
|----------|--------------|
| STDIO, SSE, HTTP transports | Custom transport implementations |
| Automatic tool discovery | Tool modification/proxying |
| Skill-based classification | Custom classification rules UI |
| Health monitoring | Advanced load balancing |
| Connection lifecycle management | Cross-server transactions |
| Tool name collision handling | Tool composition/chaining |

---

## User Stories

### AG-US1: Add External MCP Server

**Story ID**: AG-US1
**Priority**: P0 (Must Have)
**Status**: Pending

**As a** Platform Administrator
**I want** to register and connect to an external MCP server
**So that** its tools become available through the ISA MCP platform

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | Given valid server config (name, transport_type, endpoint), the server is registered in ServerRegistry | Pending |
| AC2 | Given transport_type=STDIO, connection established via standard input/output | Pending |
| AC3 | Given transport_type=SSE, connection established via Server-Sent Events | Pending |
| AC4 | Given transport_type=HTTP, connection established via HTTP endpoint | Pending |
| AC5 | Given auto_connect=true, connection established immediately after registration | Pending |
| AC6 | Given invalid config (missing required fields), return 422 Validation Error | Pending |
| AC7 | Given duplicate server name, return 409 Conflict | Pending |
| AC8 | Server registration completes within 2 seconds | Pending |

#### API Contract

**Request**:
```json
POST /api/v1/aggregator/servers
{
  "name": "github-mcp",
  "description": "GitHub MCP Server for repository operations",
  "transport_type": "SSE",
  "connection_config": {
    "url": "https://github-mcp.example.com/sse",
    "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"}
  },
  "auto_connect": true,
  "health_check_url": "https://github-mcp.example.com/health"
}
```

**Response**:
```json
{
  "id": "uuid-1234",
  "name": "github-mcp",
  "status": "CONNECTING",
  "transport_type": "SSE",
  "registered_at": "2025-01-08T10:00:00Z"
}
```

---

### AG-US2: Unified Tool Discovery Across Servers

**Story ID**: AG-US2
**Priority**: P0 (Must Have)
**Status**: Pending

**As an** MCP Client
**I want** to search for tools across all connected external servers
**So that** I can find the right tool regardless of which server provides it

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | Given a search query, results include tools from all connected servers | Pending |
| AC2 | Each tool result includes `source_server` field with server name and ID | Pending |
| AC3 | Tools from disconnected servers are excluded from results | Pending |
| AC4 | Given `server_filter` parameter, results limited to specified servers | Pending |
| AC5 | Aggregated tool count matches sum of tools from all connected servers | Pending |
| AC6 | Search latency < 150ms for 10 servers with 100 tools each | Pending |
| AC7 | Results sorted by relevance score, not by server | Pending |

#### API Contract

**Request**:
```json
POST /api/v1/search
{
  "query": "create a GitHub issue",
  "include_external": true,
  "server_filter": ["github-mcp", "jira-mcp"],
  "limit": 10
}
```

**Response**:
```json
{
  "query": "create a GitHub issue",
  "tools": [
    {
      "id": "1",
      "name": "github-mcp.create_issue",
      "original_name": "create_issue",
      "description": "Create a new GitHub issue",
      "score": 0.95,
      "source_server": {
        "id": "uuid-1234",
        "name": "github-mcp",
        "status": "CONNECTED"
      },
      "skill_ids": ["code_management", "issue_tracking"],
      "primary_skill_id": "issue_tracking"
    }
  ],
  "metadata": {
    "servers_searched": 2,
    "total_tools_searched": 45
  }
}
```

---

### AG-US3: Automatic Skill Classification for External Tools

**Story ID**: AG-US3
**Priority**: P0 (Must Have)
**Status**: Pending

**As a** Platform Administrator
**I want** external tools to be automatically classified into skill categories
**So that** they integrate with the existing hierarchical search system

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | When tools are discovered from external server, LLM classification triggered | Pending |
| AC2 | Each tool assigned to 1-3 skill categories with confidence scores | Pending |
| AC3 | Primary skill determined (highest confidence >= 0.5) | Pending |
| AC4 | If classification fails, tool marked `is_classified=false` and searchable via direct search | Pending |
| AC5 | Skill embeddings updated after classification | Pending |
| AC6 | Classification completes within 3 seconds per tool | Pending |
| AC7 | Batch classification for server with 50+ tools completes within 60 seconds | Pending |
| AC8 | If new skill needed, suggestion queued for review | Pending |

#### Classification Flow

```
External Tool       LLM Classifier        Skill Assignments
     |                    |                      |
     | name, description  |                      |
     |------------------->|                      |
     |                    | analyze + match      |
     |                    |--------------------->|
     |                    |                      | update vector index
     |                    |                      | update skill embeddings
```

---

### AG-US4: Tool Execution Routing

**Story ID**: AG-US4
**Priority**: P0 (Must Have)
**Status**: Pending

**As an** MCP Client
**I want** to execute tools from external servers through ISA MCP
**So that** I can use a single interface for all tool invocations

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | Given namespaced tool name (server.tool), request routed to correct server | Pending |
| AC2 | Given original tool name + server_id, request routed correctly | Pending |
| AC3 | If source server disconnected, return 503 Service Unavailable with server info | Pending |
| AC4 | Tool parameters passed through unchanged to backend server | Pending |
| AC5 | Tool response returned unchanged to client | Pending |
| AC6 | Routing overhead < 50ms | Pending |
| AC7 | If tool not found, return 404 Not Found | Pending |
| AC8 | Concurrent calls to same server handled correctly | Pending |

#### API Contract

**Request**:
```json
POST /api/v1/tools/call
{
  "name": "github-mcp.create_issue",
  "arguments": {
    "repo": "owner/repo",
    "title": "Bug report",
    "body": "Description of the bug"
  }
}
```

**Response**:
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
    "routing_time_ms": 12.5,
    "execution_time_ms": 450.2
  }
}
```

---

### AG-US5: Server Health Monitoring

**Story ID**: AG-US5
**Priority**: P1 (Should Have)
**Status**: Pending

**As a** Platform Administrator
**I want** to monitor the health of connected external servers
**So that** I can proactively address connectivity issues

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | Health checks run at configurable interval (default: 30s) | Pending |
| AC2 | Health check calls server's health_check_url if configured | Pending |
| AC3 | If no health_check_url, health inferred from last successful message | Pending |
| AC4 | Server status updated based on health check result | Pending |
| AC5 | If 3 consecutive health checks fail, server marked ERROR | Pending |
| AC6 | Health status visible via GET /api/v1/aggregator/servers | Pending |
| AC7 | Health metrics exposed for monitoring (response time, error rate) | Pending |
| AC8 | Health check timeout = 5 seconds | Pending |

#### Server Status Values

| Status | Description |
|--------|-------------|
| CONNECTED | Server connected and healthy |
| DEGRADED | Server connected but elevated errors |
| DISCONNECTED | Server intentionally disconnected |
| ERROR | Server unreachable or failing health checks |
| CONNECTING | Connection in progress |

---

### AG-US6: Dynamic Server Connect/Disconnect

**Story ID**: AG-US6
**Priority**: P1 (Should Have)
**Status**: Pending

**As a** Platform Administrator
**I want** to connect and disconnect servers at runtime
**So that** I can manage server lifecycle without platform restart

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | POST /api/v1/aggregator/servers/{id}/connect establishes connection | Pending |
| AC2 | POST /api/v1/aggregator/servers/{id}/disconnect closes connection gracefully | Pending |
| AC3 | On disconnect, pending requests complete or timeout (30s) | Pending |
| AC4 | On disconnect, server tools marked unavailable in search | Pending |
| AC5 | On reconnect, tools re-discovered and re-indexed | Pending |
| AC6 | DELETE /api/v1/aggregator/servers/{id} removes server and all its tools | Pending |
| AC7 | Server removal triggers skill embedding recalculation | Pending |

#### Lifecycle API

**Connect**:
```json
POST /api/v1/aggregator/servers/{id}/connect
Response: {"status": "CONNECTING", "message": "Connection initiated"}
```

**Disconnect**:
```json
POST /api/v1/aggregator/servers/{id}/disconnect
Response: {"status": "DISCONNECTED", "pending_requests": 0}
```

---

### AG-US7: Tool Name Collision Handling

**Story ID**: AG-US7
**Priority**: P1 (Should Have)
**Status**: Pending

**As a** Platform Administrator
**I want** tool name collisions across servers to be handled automatically
**So that** each tool remains uniquely addressable

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | All external tools namespaced as `{server_name}.{tool_name}` | Pending |
| AC2 | Original tool name preserved in `original_name` field | Pending |
| AC3 | Search returns namespaced name but displays original for clarity | Pending |
| AC4 | Tool call accepts either namespaced or original+server_id | Pending |
| AC5 | List tools API groups by server for visibility | Pending |
| AC6 | If server renamed, tool namespaces updated automatically | Pending |
| AC7 | Internal ISA tools not namespaced (no prefix) | Pending |

#### Namespacing Example

```
Server: github-mcp
Original Tool: create_issue
Namespaced: github-mcp.create_issue

Server: gitlab-mcp
Original Tool: create_issue
Namespaced: gitlab-mcp.create_issue
```

---

## Non-Functional Requirements

### Performance Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **NFR-P1**: Server registration latency | < 2s | API response time |
| **NFR-P2**: Tool discovery per server | < 5s | Time to index all tools |
| **NFR-P3**: Aggregated search latency | < 150ms | 10 servers, 100 tools each |
| **NFR-P4**: Routing overhead | < 50ms | Time added by routing layer |
| **NFR-P5**: Classification per tool | < 3s | LLM classification time |
| **NFR-P6**: Health check interval | 30s | Configurable |

### Reliability Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **NFR-R1**: Connection uptime | > 99.9% | Per server availability |
| **NFR-R2**: Reconnection success | > 95% | Auto-reconnect attempts |
| **NFR-R3**: Graceful degradation | 100% | Other servers unaffected by one failure |
| **NFR-R4**: No message loss | 100% | During reconnection |

### Scalability Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **NFR-S1**: Concurrent servers | 20+ | Active connections |
| **NFR-S2**: Tools per server | 1000+ | Indexed tools |
| **NFR-S3**: Total aggregated tools | 10,000+ | Across all servers |
| **NFR-S4**: Concurrent tool calls | 100+ req/s | Routed requests |

### Security Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **NFR-SEC1**: Credential storage | Encrypted | Server credentials encrypted at rest |
| **NFR-SEC2**: Connection encryption | TLS 1.2+ | For SSE/HTTP transports |
| **NFR-SEC3**: Token refresh | Automatic | OAuth tokens refreshed before expiry |
| **NFR-SEC4**: Audit logging | Complete | All server operations logged |

---

## Acceptance Criteria Summary

### Must Pass Before Release

| Story | Critical AC | Status |
|-------|-------------|--------|
| AG-US1 | AC1, AC2, AC3, AC4, AC5 | Pending |
| AG-US2 | AC1, AC2, AC5, AC6 | Pending |
| AG-US3 | AC1, AC2, AC3, AC5 | Pending |
| AG-US4 | AC1, AC2, AC4, AC5, AC6 | Pending |
| AG-US5 | AC1, AC4, AC5, AC6 | Pending |
| AG-US6 | AC1, AC2, AC4, AC5 | Pending |
| AG-US7 | AC1, AC2, AC4 | Pending |

### Quality Gates

| Gate | Criteria | Target |
|------|----------|--------|
| **Unit Tests** | Coverage on business logic | > 80% |
| **Component Tests** | Service-level integration | > 70% |
| **Integration Tests** | End-to-end flows | All happy paths |
| **Performance Tests** | Latency SLAs | All NFR-P* met |

---

## Related Documents

- [Domain - Business Context](../domain/aggregator_service.md)
- [Design - Architecture](../design/aggregator_service.md)
- [Data Contract](../../tests/contracts/aggregator/data_contract.py)
- [Logic Contract](../../tests/contracts/aggregator/logic_contract.md)
- [System Contract](../../tests/contracts/aggregator/system_contract.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-01-08
**Owner**: ISA MCP Team
