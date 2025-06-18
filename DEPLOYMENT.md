# MCP Server Scalable Deployment Guide

This guide covers how to deploy the MCP (Model Context Protocol) server in a scalable way using FastAPI wrapper, Docker, and Kubernetes.

## 🏗️ Architecture Overview

### Current Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Load Balancer │────│  FastAPI Wrapper │────│   MCP Server    │
│     (Nginx)     │    │    (Port 3000)   │    │   (Port 8000)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Scalable Architecture
```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │     (Nginx)     │
                    └─────────┬───────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────▼──────┐ ┌────────▼────────┐ ┌─────▼─────────┐
    │ MCP Instance │ │ MCP Instance    │ │ MCP Instance  │
    │   1 (3001)   │ │   2 (3002)     │ │   3 (3003)    │
    └──────────────┘ └─────────────────┘ └───────────────┘
```

## 🚀 Quick Start

### 1. Docker Compose (Recommended for Development)

```bash
# Start all services
./deploy.sh docker up

# Stop services
./deploy.sh docker down

# View logs
./deploy.sh docker logs
```

### 2. Kubernetes (Production)

```bash
# Deploy to K8s cluster
./deploy.sh k8s up

# Check status
./deploy.sh k8s status

# Scale manually
kubectl scale deployment mcp-server --replicas=5 -n mcp-server

# Delete deployment
./deploy.sh k8s down
```

### 3. Local Development

```bash
# Run locally
./deploy.sh local start

# Stop
./deploy.sh local stop
```

## 📋 Prerequisites

### For Docker Deployment
- Docker 20.10+
- Docker Compose 2.0+

### For Kubernetes Deployment
- kubectl configured with cluster access
- Kubernetes cluster 1.19+
- Sufficient resources (minimum 3 nodes recommended)

### For Local Development
- Python 3.11+
- pip

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | development | Set to `production` for production settings |
| `FASTAPI_PORT` | 3000 | FastAPI wrapper port |
| `MCP_PORT` | 8000 | MCP protocol port |
| `FASTAPI_HOST` | 0.0.0.0 | FastAPI bind host |
| `MCP_HOST` | 0.0.0.0 | MCP protocol bind host |
| `SERVICE_NAME` | mcp-server | Service name for identification |
| `VERSION` | 1.0.0 | Service version |

### Port Configuration

| Service | Port | Description |
|---------|------|-------------|
| Nginx Load Balancer | 80 | HTTP API access |
| Nginx MCP Proxy | 8080 | MCP protocol access |
| FastAPI Wrapper | 3000 | Direct API access |
| MCP Protocol | 8000 | Direct MCP access |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000* | Monitoring dashboard |

*Note: Grafana conflicts with FastAPI port in single-host deployment

## 🐳 Docker Deployment Details

### Services Included

1. **mcp-server-1,2,3**: Three MCP server instances
2. **nginx**: Load balancer with health checks
3. **redis**: Shared caching (optional)
4. **prometheus**: Metrics collection
5. **grafana**: Monitoring dashboard

### Volumes

- `mcp-data-{1,2,3}`: Persistent data for each instance
- `mcp-logs-{1,2,3}`: Log storage for each instance
- `redis-data`: Redis persistence
- `prometheus-data`: Prometheus metrics storage
- `grafana-data`: Grafana configuration

### Health Checks

All services include comprehensive health checks:
- **Liveness**: Service is running
- **Readiness**: Service can accept traffic
- **Startup**: Service has completed initialization

## ☸️ Kubernetes Deployment Details

### Resources

- **Namespace**: `mcp-server`
- **Deployments**: `mcp-server`, `nginx-loadbalancer`
- **Services**: Load balancer and cluster IP services
- **ConfigMaps**: Configuration management
- **PVC**: Persistent storage
- **HPA**: Horizontal Pod Autoscaler

### Scaling

#### Manual Scaling
```bash
kubectl scale deployment mcp-server --replicas=5 -n mcp-server
```

#### Automatic Scaling (HPA)
- **Min Replicas**: 3
- **Max Replicas**: 10
- **CPU Target**: 70%
- **Memory Target**: 80%

#### Resource Limits
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## 📊 Monitoring and Observability

### Health Check Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | General health status |
| `/health/live` | Kubernetes liveness probe |
| `/health/ready` | Kubernetes readiness probe |
| `/metrics` | Prometheus metrics |
| `/config` | Current configuration |

### Metrics Collection

**FastAPI Wrapper Metrics**:
- Uptime
- Request counts
- Error rates
- Response times

**MCP Server Metrics**:
- Tool execution counts
- Authorization requests
- Security violations
- Rate limit hits

### Log Aggregation

Logs are structured with JSON format and include:
- Timestamp
- Log level
- Service name
- Request ID
- User context
- Error details

## 🔒 Security Features

### Network Security
- Services run on internal networks
- Nginx proxy for external access
- Rate limiting on API endpoints
- Request size limits

### Application Security
- Non-root containers
- Read-only root filesystems where possible
- Security context constraints
- Resource limits

### Access Control
- Admin endpoints protected
- Authorization required for sensitive operations
- Audit logging for all operations

## 🚦 Load Balancing

### Nginx Configuration
- **Algorithm**: Least connections
- **Health Checks**: Active health monitoring
- **Failover**: Automatic failover on failure
- **Rate Limiting**: Configurable rate limits
- **Compression**: Gzip compression enabled

### Kubernetes Load Balancing
- **Service Type**: LoadBalancer for external access
- **Session Affinity**: None (stateless)
- **Health Checks**: Integrated with K8s probes

## 🔧 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check what's using port 8000
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

#### Docker Issues
```bash
# Check container logs
docker-compose logs mcp-server-1

# Restart specific service
docker-compose restart mcp-server-1

# Check container health
docker-compose ps
```

#### Kubernetes Issues
```bash
# Check pod status
kubectl get pods -n mcp-server

# Check pod logs
kubectl logs deployment/mcp-server -n mcp-server

# Describe pod for events
kubectl describe pod <pod-name> -n mcp-server

# Check service endpoints
kubectl get endpoints -n mcp-server
```

### Performance Tuning

#### Resource Allocation
```bash
# Monitor resource usage
kubectl top pods -n mcp-server
kubectl top nodes

# Adjust resource limits
kubectl patch deployment mcp-server -n mcp-server -p '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","resources":{"limits":{"memory":"1Gi","cpu":"1000m"}}}]}}}}'
```

#### Scaling Optimization
```bash
# Monitor HPA status
kubectl get hpa -n mcp-server

# Adjust HPA thresholds
kubectl patch hpa mcp-server-hpa -n mcp-server --type='merge' -p='{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":50}}}]}}'
```

## 📈 Capacity Planning

### Resource Requirements

**Per Instance**:
- **CPU**: 250m-500m
- **Memory**: 256Mi-512Mi
- **Storage**: 1Gi-10Gi

**For 1000 concurrent users**:
- **Instances**: 5-10
- **Total CPU**: 2.5-5 cores
- **Total Memory**: 2.5-5Gi
- **Network**: 100Mbps

### Scaling Guidelines

1. **Monitor metrics**: Use Prometheus/Grafana
2. **Set alerts**: CPU >80%, Memory >85%, Errors >5%
3. **Scale proactively**: Before resource exhaustion
4. **Test scaling**: Regular load testing

## 🔄 CI/CD Integration

### Docker Build
```bash
# Build production image
docker build --target production -t mcp-server:v1.0.0 .

# Push to registry
docker tag mcp-server:v1.0.0 your-registry/mcp-server:v1.0.0
docker push your-registry/mcp-server:v1.0.0
```

### Kubernetes Deployment
```bash
# Update image in deployment
kubectl set image deployment/mcp-server mcp-server=your-registry/mcp-server:v1.0.1 -n mcp-server

# Check rollout status
kubectl rollout status deployment/mcp-server -n mcp-server

# Rollback if needed
kubectl rollout undo deployment/mcp-server -n mcp-server
```

## 📞 Support

For issues or questions:
1. Check logs first: `./deploy.sh [platform] logs`
2. Review health endpoints: `curl http://localhost/health`
3. Monitor metrics: Check Prometheus/Grafana
4. Check resource usage: `kubectl top pods` or `docker stats`

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MCP Protocol Specification](https://github.com/modelcontextprotocol/python-sdk)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Nginx Load Balancing](https://nginx.org/en/docs/http/load_balancing.html)