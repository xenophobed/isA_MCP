# Configuration

Server configuration and infrastructure setup for ISA MCP.

## Overview

The platform uses `config/init.yaml` for service initialization and dependency configuration.

## Service Configuration

### MCP Server

```yaml
mcp_service:
  port: 8081              # External port
  internal_port: 8300     # Internal port
  description: "Model Context Protocol service"
  depends_on:
    - postgres_grpc
    - qdrant
    - redis
```

### Auto-Discovery

```yaml
auto_discovery:
  enabled: true
  scan_interval_seconds: 300  # Re-scan every 5 minutes
  paths:
    tools: "tools/"
    prompts: "prompts/"
    resources: "resources/"
  patterns:
    tools: "*.py"
    prompts: "*.py"
    resources: "*.py"
  exclude:
    - "__pycache__"
    - "*.pyc"
    - "base_*.py"
```

## Infrastructure Dependencies

### PostgreSQL

```yaml
postgres_grpc:
  port: 50061
  schemas:
    - mcp
  tables:
    - tool_executions    # Tool execution logs
    - prompt_templates   # Custom prompts
    - resource_cache     # Resource metadata
```

### Qdrant (Vector Store)

```yaml
qdrant:
  http: 6333
  grpc: 6334
  collections:
    - name: "mcp_tool_embeddings"
      vector_size: 1536
      distance: "Cosine"
    - name: "mcp_prompt_embeddings"
      vector_size: 1536
    - name: "mcp_document_embeddings"
      on_disk: true
```

### Redis (Cache)

```yaml
redis:
  port: 6379
  key_prefixes:
    - "mcp:tool:"       # Tool response cache
    - "mcp:prompt:"     # Prompt cache
    - "mcp:resource:"   # Resource cache
    - "mcp:embedding:"  # Embedding cache
    - "mcp:session:"    # Session state
    - "mcp:rate:"       # Rate limiting
```

### MinIO (Object Storage)

```yaml
minio:
  port: 9000
  buckets:
    - name: "mcp-resources"
      versioning: true
    - name: "mcp-cache"
      lifecycle:
        expiration_days: 30
    - name: "mcp-exports"
      lifecycle:
        expiration_days: 90
```

## Startup Order

```yaml
startup_order:
  - tier: 1
    description: "Core Infrastructure"
    services: [postgres, redis, qdrant, minio]

  - tier: 2
    description: "gRPC Gateways"
    services: [postgres_grpc, redis_grpc, qdrant_grpc]

  - tier: 3
    description: "MCP Service"
    services: [mcp]
```

## Health Checks

```yaml
health_checks:
  default_timeout_seconds: 5
  default_interval_seconds: 30
  default_failure_threshold: 3

  mcp_specific:
    tool_discovery:
      check: "count_registered_tools > 0"
    prompt_discovery:
      check: "count_registered_prompts > 0"
    resource_discovery:
      check: "count_registered_resources > 0"
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_PORT` | Server port | `8081` |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `QDRANT_HOST` | Qdrant host | `localhost` |
| `REDIS_HOST` | Redis host | `localhost` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Running the Server

### Development

```bash
cd /path/to/isA_MCP
python main.py
```

### With Custom Port

```bash
MCP_PORT=9000 python main.py
```

### Docker

```bash
docker-compose up -d
```

## Directory Structure

```
isA_MCP/
├── config/
│   └── init.yaml          # Main configuration
├── tools/                  # Auto-discovered tools
├── prompts/                # Auto-discovered prompts
├── resources/              # Auto-discovered resources
├── services/
│   └── skill_service/     # Skill management
├── core/
│   ├── auto_discovery.py  # Discovery logic
│   ├── security.py        # Security management
│   └── config.py          # Config loading
└── main.py                # Entry point
```

## Adding External MCP Servers

See [Server Aggregation](./aggregator) for connecting to external MCP servers.

```python
result = await client.call_tool("add_mcp_server", {
    "name": "external-server",
    "transport_type": "SSE",
    "connection_config": {
        "url": "https://external.example.com/sse"
    },
    "auto_connect": True
})
```

## Regenerating Init Scripts

```bash
python -m scripts.generate_init
```

This generates initialization scripts based on `config/init.yaml`.

## Next Steps

- [Quick Start](./quickstart) - Getting started
- [Server Aggregation](./aggregator) - External servers
- [Tools](./tools) - Creating tools
