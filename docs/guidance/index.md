# ISA MCP Platform

Enterprise-grade Model Context Protocol (MCP) Server with intelligent tool discovery.

## Overview

ISA MCP is a unified platform for registering, discovering, and invoking MCP tools with skill-based hierarchical search.

### Core Value Propositions

| Value | Description |
|-------|-------------|
| **Unified Registry** | Single API for all tools, multi-server aggregation |
| **Intelligent Discovery** | Skill-based routing, semantic search |
| **Context Optimization** | Minimal context output, lazy loading |
| **Full Lifecycle** | Register → Discover → Invoke → Monitor |

## Platform Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ISA MCP PLATFORM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    TOOLS     │  │   PROMPTS    │  │  RESOURCES   │          │
│  │     88+      │  │     50       │  │      9       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    SERVICES                               │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │  │
│  │  │ Tool   │ │ Search │ │ Skill  │ │  HIL   │ │Progress│ │  │
│  │  │Service │ │Service │ │Service │ │Service │ │Service │ │  │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   AGGREGATOR                              │  │
│  │          Connect to External MCP Servers                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Skill-Based Search

Tools are classified into skills for efficient discovery:

```
Skills (6 Categories)
├── Productivity (calendar, task, note, time)
├── Communication (email, messaging, notifications)
├── Data (query, analysis, visualization, export)
├── File (operations, documents, media, cloud)
├── Integration (API, webhooks, third-party)
└── System (config, monitoring, security, admin)
```

### 2. Semantic Search

Find tools using natural language:

```python
# Search for tools by intent
results = await search("schedule a meeting with John")
# Returns: create_event, send_invite, check_availability
```

### 3. Human-in-the-Loop (HIL)

Four interaction patterns:

| Method | Use Case |
|--------|----------|
| Authorization | Approve/reject actions |
| Input | Collect user credentials or data |
| Review | Review and edit content |
| Combined | Input + authorization together |

### 4. Progress Tracking

Real-time progress via SSE streaming or HTTP polling.

### 5. Server Aggregation

Connect to external MCP servers (GitHub, Slack, custom) and aggregate their tools.

## MCP Components

### Tools

Executable functions exposed via MCP protocol.

```python
# Example tool call
result = await client.call_tool("get_weather", {"city": "Tokyo"})
```

### Prompts

Reusable text templates for AI workflows.

```python
# Get a prompt with arguments
prompt = await client.get_prompt("rag_search", {
    "query": "What is AI?",
    "context": "Learning about AI"
})
```

### Resources

Static and dynamic data sources.

```python
# Read a resource
content = await client.read_resource("guardrail://config/pii")
```

## Service Types

| Service | Responsibility |
|---------|----------------|
| **ToolService** | Tool CRUD operations |
| **PromptService** | Template and dynamic prompts |
| **ResourceService** | Static and dynamic resources |
| **SearchService** | Hierarchical search, skill routing |
| **SkillService** | Classification, assignment, embedding |
| **SyncService** | MCP server sync, index updates |
| **AggregatorService** | External server management |

## Getting Started

- [Quick Start](./quickstart) - Installation and basic usage
- [Configuration](./configuration) - Server configuration
- [Tools](./tools) - Creating and using tools
- [Prompts](./prompts) - Creating and using prompts
- [Resources](./resources) - Creating and using resources
- [Skills](./skills) - Skill-based classification

## Platform Features

- [Search Guide](./search) - Tool discovery and semantic search
- [HIL Guide](./hil) - Human-in-the-loop interaction
- [Progress Guide](./progress) - Progress tracking and streaming
- [Aggregator Guide](./aggregator) - External MCP servers

## Security & Operations

- [Security](./security) - Authentication, authorization, and tenant isolation
- [Multi-Tenant](./multi-tenant) - Organization scoping and data segregation
- [Reliability](./reliability) - Infrastructure reliability and best practices
- [Git Workflow](./git-workflow) - Development process

## API Endpoints

Base URL: `http://localhost:8081`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp` | POST | MCP JSON-RPC endpoint |
| `/health` | GET | Server health check |
| `/search` | POST | Semantic search |
| `/progress/{id}/stream` | GET | SSE progress stream |
| `/api/v1/skills/*` | - | Skill management |
| `/api/v1/aggregator/*` | - | Server aggregation |

## Related Documentation

- [Domain Model](../domain/README.md) - Business context
- [Design Docs](../design/) - Technical architecture
- [PRD](../prd/README.md) - Requirements
