# Deployment

ISA MCP is Kubernetes-ready with health checks, horizontal scaling, and configurable resource limits.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_AGGREGATOR_ENABLED` | No | true | Enable aggregator |
| `MCP_AGGREGATOR_MAX_SERVERS` | No | 50 | Max external servers |
| `MCP_AGGREGATOR_HEALTH_INTERVAL` | No | 30 | Health check interval (s) |
| `MCP_AGGREGATOR_CONNECTION_TIMEOUT` | No | 30 | Connection timeout (s) |
| `MCP_AGGREGATOR_REQUEST_TIMEOUT` | No | 60 | Request timeout (s) |
| `MCP_CREDENTIAL_KEY` | Yes | - | Credential encryption key |

For the full environment variable reference, see [env/README.md](./env/README.md).

## Required Services

- PostgreSQL (gRPC: 50061)
- Qdrant (gRPC: 50055)
- Model Service (for embeddings)
- Redis (for caching, optional)

## Kubernetes Configuration

### Health Checks

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

## See Also

- [Full Deployment Guide](../deployment/README.md) -- Docker, Helm, and K8s setup
- [Environment Configuration](./env/README.md) -- All env vars and profiles
- [Configuration Overview](./configuration.md)
