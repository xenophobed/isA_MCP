# Server Aggregation

Connect to external MCP servers and aggregate their tools.

## Overview

The MCP Server Aggregator enables ISA MCP to:

1. Connect to multiple external MCP servers (STDIO, SSE, HTTP)
2. Aggregate tools into a unified registry
3. Apply skill-based classification to external tools
4. Route tool calls to the appropriate backend server
5. Monitor health and handle connection lifecycle

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       ISA MCP PLATFORM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   AGGREGATOR SERVICE                      │  │
│  │                                                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │  Server    │  │   Tool     │  │   Skill    │         │  │
│  │  │  Registry  │  │ Aggregator │  │ Classifier │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  │                                                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │  Request   │  │   Health   │  │  Session   │         │  │
│  │  │  Router    │  │  Monitor   │  │  Manager   │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│          ┌───────────────────┼───────────────────┐              │
│          ▼                   ▼                   ▼              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │  GitHub MCP    │  │   Slack MCP    │  │  Custom MCP    │   │
│  │    (STDIO)     │  │     (SSE)      │  │    (HTTP)      │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Adding External Servers

### Register Server

```python
# Via API
import aiohttp

async def add_mcp_server():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8081/api/v1/aggregator/servers",
            json={
                "name": "github-mcp",
                "description": "GitHub MCP Server for repository operations",
                "transport_type": "SSE",
                "connection_config": {
                    "url": "https://github-mcp.example.com/sse",
                    "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"}
                },
                "auto_connect": True,
                "health_check_url": "https://github-mcp.example.com/health"
            }
        ) as response:
            return await response.json()
```

### Via MCP Tool

```python
result = await client.call_and_parse("add_mcp_server", {
    "name": "github-mcp",
    "transport_type": "SSE",
    "connection_config": {
        "url": "https://github-mcp.example.com/sse"
    },
    "auto_connect": True
})

print(f"Server ID: {result['data']['id']}")
print(f"Status: {result['data']['status']}")
```

### Transport Types

| Type | Connection Config | Use Case |
|------|-------------------|----------|
| `STDIO` | `command`, `args`, `env` | Local processes |
| `SSE` | `url`, `headers` | Server-Sent Events |
| `HTTP` | `base_url`, `headers` | REST API |

#### STDIO Example

```json
{
  "name": "local-tools",
  "transport_type": "STDIO",
  "connection_config": {
    "command": "python",
    "args": ["-m", "my_mcp_server"],
    "env": {"DEBUG": "true"}
  }
}
```

#### SSE Example

```json
{
  "name": "remote-tools",
  "transport_type": "SSE",
  "connection_config": {
    "url": "https://api.example.com/mcp/sse",
    "headers": {
      "Authorization": "Bearer token123"
    }
  }
}
```

#### HTTP Example

```json
{
  "name": "http-tools",
  "transport_type": "HTTP",
  "connection_config": {
    "base_url": "https://api.example.com/mcp",
    "headers": {
      "X-API-Key": "key123"
    }
  }
}
```

## Tool Discovery

When a server connects, its tools are automatically discovered and indexed.

### Discovery Flow

```
1. Connect to server
2. Call tools/list
3. For each tool:
   - Apply namespacing (server.tool_name)
   - Generate embedding
   - Classify into skills (async)
   - Store in PostgreSQL
   - Index in Qdrant
```

### Tool Namespacing

External tools are namespaced to avoid collisions:

```
Server: github-mcp
Original Tool: create_issue
Namespaced: github-mcp.create_issue

Server: gitlab-mcp
Original Tool: create_issue
Namespaced: gitlab-mcp.create_issue
```

### Listing Aggregated Tools

```python
result = await client.call_and_parse("list_mcp_servers", {})

for server in result['data']['servers']:
    print(f"\n{server['name']} ({server['status']})")
    print(f"  Tools: {server['tool_count']}")
```

## Tool Execution

Call tools on external servers through the unified interface.

### By Namespaced Name

```python
result = await client.call_and_parse("github-mcp.create_issue", {
    "repo": "owner/repo",
    "title": "Bug report",
    "body": "Description of the bug"
})
```

### Via Routing

```python
# The router resolves the server from the tool name
result = await client.call_and_parse("execute_external_tool", {
    "tool_name": "github-mcp.create_issue",
    "arguments": {
        "repo": "owner/repo",
        "title": "Bug report"
    }
})

# Response includes routing metadata
print(f"Routed to: {result['metadata']['routed_to']}")
print(f"Routing time: {result['metadata']['routing_time_ms']}ms")
print(f"Execution time: {result['metadata']['execution_time_ms']}ms")
```

## Searching Aggregated Tools

Search across internal and external tools.

```python
async with aiohttp.ClientSession() as session:
    async with session.post(
        "http://localhost:8081/api/v1/search",
        json={
            "query": "create a GitHub issue",
            "include_external": True,
            "server_filter": ["github-mcp", "jira-mcp"],
            "limit": 10
        }
    ) as response:
        results = await response.json()

for tool in results['tools']:
    print(f"{tool['name']}")
    print(f"  Source: {tool['source_server']['name']}")
    print(f"  Skills: {tool['skill_ids']}")
```

## Health Monitoring

Servers are monitored for health automatically.

### Server Status Values

| Status | Description |
|--------|-------------|
| `CONNECTED` | Server connected and healthy |
| `DEGRADED` | Server connected but elevated errors |
| `DISCONNECTED` | Server intentionally disconnected |
| `ERROR` | Server unreachable or failing health checks |
| `CONNECTING` | Connection in progress |

### Health Check Configuration

```json
{
  "name": "github-mcp",
  "health_check_url": "https://github-mcp.example.com/health",
  "health_check_interval": 30,
  "failure_threshold": 3
}
```

### Checking Health

```python
# Get server status
result = await client.call_and_parse("get_server_status", {
    "server_id": "uuid-1234"
})

print(f"Status: {result['data']['status']}")
print(f"Last check: {result['data']['last_health_check']}")
print(f"Error: {result['data'].get('error_message')}")
```

### Via API

```bash
# Check all servers
curl http://localhost:8081/api/v1/aggregator/servers

# Check specific server
curl http://localhost:8081/api/v1/aggregator/servers/{server_id}
```

## Connection Management

### Connect Server

```python
result = await client.call_and_parse("connect_mcp_server", {
    "server_id": "uuid-1234"
})
```

### Disconnect Server

```python
result = await client.call_and_parse("disconnect_mcp_server", {
    "server_id": "uuid-1234"
})
# Pending requests complete or timeout (30s)
```

### Remove Server

```python
result = await client.call_and_parse("remove_mcp_server", {
    "server_id": "uuid-1234"
})
# Server and all its tools are deleted
```

## Skill Classification

External tools are automatically classified into skills.

### Classification Process

1. LLM analyzes tool name and description
2. Assigns to 1-3 skill categories
3. Calculates confidence scores
4. Determines primary skill

### Classification Result

```json
{
  "tool_name": "github-mcp.create_issue",
  "skill_ids": ["issue_tracking", "code_management"],
  "primary_skill_id": "issue_tracking",
  "confidence_scores": {
    "issue_tracking": 0.92,
    "code_management": 0.75
  },
  "is_classified": true
}
```

### Unclassified Tools

If classification fails, tools remain searchable via direct search:

```python
# Unclassified tools have is_classified=false
# They're still found via semantic search
results = await search("create github issue")
```

## Error Handling

### Server Unavailable

```python
try:
    result = await client.call_and_parse("github-mcp.create_issue", {...})
except Exception as e:
    if "503" in str(e) or "unavailable" in str(e).lower():
        # Server is disconnected
        print("GitHub MCP server is unavailable")
        # Could try reconnecting or use fallback
```

### Tool Not Found

```python
result = await client.call_and_parse("unknown-server.tool", {...})

if result.get('status') == 'error':
    if '404' in result.get('error', ''):
        print("Tool or server not found")
```

## Performance Targets

| Operation | Target |
|-----------|--------|
| Server registration | < 2s |
| Tool discovery | < 5s per server |
| Classification | < 3s per tool |
| Routing overhead | < 50ms |
| Health check | < 5s timeout |

## API Reference

### POST /api/v1/aggregator/servers

Register new server.

```json
{
  "name": "string",
  "description": "string",
  "transport_type": "STDIO|SSE|HTTP",
  "connection_config": {...},
  "auto_connect": true,
  "health_check_url": "string"
}
```

### GET /api/v1/aggregator/servers

List all servers.

### GET /api/v1/aggregator/servers/{id}

Get server details.

### POST /api/v1/aggregator/servers/{id}/connect

Connect to server.

### POST /api/v1/aggregator/servers/{id}/disconnect

Disconnect from server.

### DELETE /api/v1/aggregator/servers/{id}

Remove server.

## MCP Tools

| Tool | Description |
|------|-------------|
| `add_mcp_server` | Register and connect server |
| `remove_mcp_server` | Remove server |
| `list_mcp_servers` | List all servers |
| `connect_mcp_server` | Connect to server |
| `disconnect_mcp_server` | Disconnect from server |
| `get_server_status` | Get server health |
| `search_aggregated_tools` | Search external tools |

## Next Steps

- [Search Guide](./search.md) - Searching aggregated tools
- [Quick Start](./quickstart.md) - Basic client setup
