# MCP Server Aggregator - Domain Documentation

**Meta MCP Server for Aggregating External MCP Servers**

This document provides the domain knowledge foundation for the MCP Server Aggregator feature, covering business context, domain entities, use cases, and relationships.

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Domain Entities](#domain-entities)
3. [Entity Relationships](#entity-relationships)
4. [Use Cases](#use-cases)
5. [Business Scenarios](#business-scenarios)
6. [Glossary](#glossary)

---

## Feature Overview

### What is the MCP Server Aggregator?

The MCP Server Aggregator is a **Meta MCP Server** that enables the ISA MCP platform to connect to and aggregate multiple external MCP servers, providing:

- **Multi-Server Connectivity**: Connect to external MCP servers via STDIO, SSE, or HTTP transports
- **Unified Tool Discovery**: Single interface to discover tools from all connected servers
- **Skill-Based Classification**: Automatically classify external tools into the existing skill taxonomy
- **Intelligent Routing**: Route tool invocations to the appropriate backend server
- **Health Monitoring**: Track server health and connection status

### Core Value Propositions

```
+-----------------------------------------------------------------------------+
|                      MCP SERVER AGGREGATOR VALUE                             |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +----------------+  +----------------+  +----------------+  +------------+  |
|  |   MULTI-SERVER |  |    UNIFIED     |  |   AUTOMATIC    |  |  HEALTH    |  |
|  |   AGGREGATION  |  |   DISCOVERY    |  |  CLASSIFICATION|  | MONITORING |  |
|  +----------------+  +----------------+  +----------------+  +------------+  |
|  | Connect to     |  | Single API for |  | LLM classifies |  | Track      |  |
|  | multiple MCP   |  | all tools      |  | external tools |  | server     |  |
|  | servers        |  | across servers |  | into skills    |  | status     |  |
|  +----------------+  +----------------+  +----------------+  +------------+  |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### Problem Statement

As organizations adopt MCP, they often have:

1. **Multiple MCP Servers**: Different teams or vendors provide separate MCP servers
2. **Fragmented Discovery**: No single interface to find tools across servers
3. **Manual Integration**: Each server requires separate connection handling
4. **No Classification**: External tools lack skill-based organization
5. **Connection Management**: No centralized health monitoring

### Solution

The Aggregator provides a **unified gateway** that:

1. Manages connections to multiple external MCP servers
2. Aggregates tools from all servers into a single registry
3. Applies skill-based classification to external tools
4. Routes tool calls to the correct backend server
5. Monitors health and handles failover

---

## Domain Entities

### 1. External MCP Server

An external MCP server is a third-party or remote MCP implementation that the Aggregator connects to.

```
ExternalMCPServer
+---------------------+
| id                  | Unique identifier (UUID)
| name                | Human-readable name (e.g., "GitHub MCP Server")
| description         | Server purpose description
| transport_type      | STDIO | SSE | HTTP
| connection_config   | Transport-specific configuration
| status              | CONNECTED | DISCONNECTED | ERROR | CONNECTING
| health_check_url    | Optional health endpoint
| last_health_check   | Timestamp of last health check
| tool_count          | Number of tools from this server
| registered_at       | When server was registered
| connected_at        | When connection was established
+---------------------+
```

### 2. Aggregated Tool

A tool discovered from an external MCP server, enhanced with source tracking and namespacing.

```
AggregatedTool
+---------------------+
| id                  | Internal tool ID
| source_server_id    | Reference to external server
| original_name       | Tool name from source server
| namespaced_name     | Prefixed name (server_name.tool_name)
| description         | Tool description
| input_schema        | JSON Schema for parameters
| skill_ids           | Assigned skill categories
| primary_skill_id    | Primary skill assignment
| is_classified       | Whether LLM classification completed
| discovered_at       | When tool was discovered
| last_synced_at      | Last sync timestamp
+---------------------+
```

### 3. Server Session

Represents an active connection session to an external MCP server.

```
ServerSession
+---------------------+
| session_id          | Unique session identifier
| server_id           | Reference to external server
| transport           | Active transport instance
| connected_at        | Connection timestamp
| last_activity       | Last message timestamp
| message_count       | Total messages exchanged
| error_count         | Errors since connection
| capabilities        | Server-reported capabilities
+---------------------+
```

### 4. Routing Context

Information used to route a tool call to the correct backend server.

```
RoutingContext
+---------------------+
| tool_name           | Requested tool name
| resolved_server_id  | Target server ID
| original_tool_name  | De-namespaced tool name
| session_id          | Active session to use
| routing_strategy    | How routing was determined
| fallback_servers    | Alternative servers if primary fails
+---------------------+
```

### 5. Aggregator State

Current state of the aggregator including all connected servers and tools.

```
AggregatorState
+---------------------+
| total_servers       | Number of registered servers
| connected_servers   | Number of active connections
| total_tools         | Total aggregated tools
| classified_tools    | Tools with skill assignments
| pending_servers     | Servers waiting to connect
| error_servers       | Servers in error state
| last_sync           | Last full sync timestamp
+---------------------+
```

---

## Entity Relationships

### Entity Relationship Diagram

```
+-------------------+       1:N       +-------------------+
| ExternalMCPServer |---------------->| AggregatedTool    |
+-------------------+                 +-------------------+
        |                                     |
        | 1:1                                 | N:M
        v                                     v
+-------------------+                 +-------------------+
| ServerSession     |                 | SkillCategory     |
+-------------------+                 | (from skill svc)  |
        |                             +-------------------+
        | 1:N
        v
+-------------------+
| RoutingContext    |
+-------------------+
```

### Relationship Rules

| Relationship | Cardinality | Description |
|-------------|-------------|-------------|
| Server -> Tools | 1:N | Each server provides multiple tools |
| Server -> Session | 1:1 | One active session per server |
| Tool -> Skills | N:M | Tools can have multiple skill assignments |
| Session -> Routing | 1:N | Session handles multiple routing decisions |

---

## Use Cases

### UC-1: Add External MCP Server

**Actor**: Platform Administrator
**Goal**: Register and connect to a new external MCP server

```
Administrator                         Aggregator
     |                                     |
     | 1. Register server config           |
     |------------------------------------>|
     |                                     |
     |                          2. Validate config
     |                          3. Establish connection
     |                          4. Discover tools
     |                          5. Classify tools
     |                                     |
     | 6. Return connection status         |
     |<------------------------------------|
```

**Preconditions**:
- Server config is valid (transport type, endpoint)
- Network connectivity exists
- Server is MCP-compliant

**Postconditions**:
- Server registered in ServerRegistry
- Session established (if auto-connect enabled)
- Tools discovered and indexed
- Tools classified into skills

---

### UC-2: Unified Tool Discovery

**Actor**: MCP Client
**Goal**: Find tools across all connected servers

```
Client                                 Aggregator
    |                                      |
    | 1. Search query                      |
    |------------------------------------->|
    |                                      |
    |                           2. Search skills
    |                           3. Filter by skills
    |                           4. Include source server
    |                                      |
    | 5. Aggregated results                |
    |<-------------------------------------|
```

**Preconditions**:
- At least one server connected
- Tools have been discovered

**Postconditions**:
- Results include tools from all connected servers
- Each tool indicates its source server
- Results sorted by relevance

---

### UC-3: Execute Aggregated Tool

**Actor**: MCP Client
**Goal**: Invoke a tool from an external server

```
Client                                 Aggregator                    External Server
    |                                      |                               |
    | 1. Tool call request                 |                               |
    |------------------------------------->|                               |
    |                           2. Resolve routing                         |
    |                           3. Get session                             |
    |                                      |                               |
    |                                      | 4. Forward call               |
    |                                      |------------------------------>|
    |                                      |                               |
    |                                      | 5. Response                   |
    |                                      |<------------------------------|
    |                                      |                               |
    | 6. Tool result                       |                               |
    |<-------------------------------------|                               |
```

**Preconditions**:
- Tool exists in aggregated registry
- Source server is connected
- Session is active

**Postconditions**:
- Request forwarded to correct server
- Response returned to client
- Metrics updated

---

### UC-4: Handle Server Disconnect

**Actor**: System
**Goal**: Gracefully handle server disconnection

```
External Server                        Aggregator
       |                                    |
       | 1. Connection lost                 |
       |--------X-------------------------->|
       |                                    |
       |                         2. Detect disconnect
       |                         3. Mark server ERROR
       |                         4. Mark tools unavailable
       |                         5. Schedule reconnect
       |                                    |
```

**Preconditions**:
- Server was previously connected
- Connection interrupted

**Postconditions**:
- Server status updated to ERROR
- Associated tools marked unavailable
- Reconnection scheduled
- Clients notified (if subscribed)

---

## Business Scenarios

### Scenario 1: Multi-Provider Tool Aggregation

**Description**: Enterprise uses multiple MCP servers from different vendors

```
                          +------------------+
                          |   ISA MCP        |
                          |   Aggregator     |
                          +--------+---------+
                                   |
         +-------------------------+-------------------------+
         |                         |                         |
         v                         v                         v
+------------------+     +------------------+     +------------------+
| GitHub MCP       |     | Slack MCP        |     | Custom Internal  |
| Server           |     | Server           |     | MCP Server       |
+------------------+     +------------------+     +------------------+
| - list_repos     |     | - send_message   |     | - query_db       |
| - create_issue   |     | - list_channels  |     | - run_report     |
| - search_code    |     | - upload_file    |     | - trigger_job    |
+------------------+     +------------------+     +------------------+
```

**Client Query**: "I need to create a GitHub issue and notify the team on Slack"

**Aggregator Response**:
1. Stage 1: Match skills `[code_management, communication]`
2. Stage 2: Find tools from GitHub MCP (`create_issue`) and Slack MCP (`send_message`)
3. Return both tools with their source servers

---

### Scenario 2: Tool Name Collision Handling

**Description**: Multiple servers provide tools with the same name

```
Server A: search_tool                Server B: search_tool
     |                                    |
     v                                    v
+-----------------------------------------+
|         Aggregator Namespacing          |
+-----------------------------------------+
| server_a.search_tool                    |
| server_b.search_tool                    |
+-----------------------------------------+
```

**Resolution**:
- Tools namespaced with server prefix: `{server_name}.{tool_name}`
- Original names preserved for routing
- Skill classification applied to each independently

---

### Scenario 3: Dynamic Server Connect/Disconnect

**Description**: Servers can be added/removed at runtime

```
Timeline:
T0: Servers [A, B] connected, 10 tools available
T1: Server C added, tools discovered, classified -> 15 tools
T2: Server A disconnected (maintenance) -> 8 tools
T3: Server A reconnects, tools restored -> 15 tools
```

**Behavior**:
- Tool registry dynamically updated
- Skill embeddings recalculated
- Search results reflect current availability
- No downtime for other servers

---

### Scenario 4: Health-Based Routing

**Description**: Route to healthy servers when primary is degraded

```
                        Aggregator
                            |
         +------------------+------------------+
         |                                     |
    Server A                              Server B
    (DEGRADED)                            (HEALTHY)
         |                                     |
         v                                     v
    Primary for                           Fallback for
    "data_analysis"                       "data_analysis"
```

**Routing Logic**:
1. Check primary server health
2. If degraded/error, check fallbacks
3. Route to first healthy server
4. Log routing decision for observability

---

## Glossary

### Domain Terms

| Term | Definition |
|------|------------|
| **Aggregator** | Meta MCP server that connects to multiple backend MCP servers |
| **External Server** | Third-party MCP server connected via the Aggregator |
| **Aggregated Tool** | Tool from external server, indexed in Aggregator |
| **Namespacing** | Prefixing tool names with server identifier to avoid collisions |
| **Transport** | Connection protocol (STDIO, SSE, HTTP) |
| **Session** | Active connection to an external server |

### Technical Terms

| Term | Definition |
|------|------------|
| **ClientSession** | MCP SDK class for managing client connections |
| **ClientSessionGroup** | MCP SDK class for managing multiple sessions |
| **STDIO** | Standard Input/Output transport for local processes |
| **SSE** | Server-Sent Events transport for HTTP streaming |
| **HTTP** | Standard HTTP transport with request/response |
| **Health Check** | Periodic probe to verify server availability |

### Platform Terms

| Term | Definition |
|------|------------|
| **ServerRegistry** | Component that manages server registrations |
| **ToolAggregator** | Component that collects and indexes tools |
| **SkillClassifier** | LLM-based tool classification (existing) |
| **RequestRouter** | Component that routes calls to backend servers |
| **HealthMonitor** | Component that tracks server health |

---

## Related Documents

- [PRD - User Stories & Requirements](../prd/aggregator_service.md)
- [Design - Architecture & Components](../design/aggregator_service.md)
- [Data Contract](../../tests/contracts/aggregator/data_contract.py)
- [Logic Contract](../../tests/contracts/aggregator/logic_contract.md)
- [System Contract](../../tests/contracts/aggregator/system_contract.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-01-08
**Owner**: ISA MCP Team
