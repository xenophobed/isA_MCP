# isA MCP - Deployment Configuration

## Overview

TDD/CDD AI Agent driven development mode with two environments:

| Environment | Purpose | Where | Tests |
|------------|---------|-------|-------|
| **dev** | Local development | Local venv | unit, component |
| **test** | K8s testing | Kind K8s + port-forward | integration, api, smoke |

## Directory Structure

```
deployment/
├── README.md              # This file
├── environments/          # Environment configurations
│   ├── dev.env           # Local development
│   └── test.env          # K8s testing
├── k8s/                   # Kubernetes deployment
│   ├── Dockerfile.mcp    # MCP service Dockerfile
│   ├── kustomization.yaml
│   ├── mcp-configmap.yaml
│   ├── mcp-deployment.yaml
│   └── mcp-service.yaml
└── requirements/          # Python dependencies
    ├── base.txt          # Core dependencies
    └── dev.txt           # Development dependencies
```

## K8s Environment Details

### Cluster & Namespace

| Item | Value | Description |
|-----|-----|------|
| **Cluster** | `kind-isa-cloud-local` | Kind local K8s cluster |
| **Namespace** | `isa-cloud-staging` | Deployment namespace |
| **Context** | `kind-isa-cloud-local` | kubectl default context |

### Architecture

```
                                ┌─────────────────────────────────────┐
                                │         Kind K8s Cluster            │
                                │       (kind-isa-cloud-local)        │
                                │                                     │
External                        │   ┌─────────────────────────────┐   │
────────►  Port 8000  ─────────►│   │    APISIX Gateway           │   │
(Smoke Tests)                   │   │    (API Gateway + LB)       │   │
                                │   └──────────┬──────────────────┘   │
                                │              │                      │
                                │   ┌──────────▼──────────────────┐   │
                                │   │    Consul                    │   │
                                │   │    (Service Discovery)       │   │
                                │   └──────────┬──────────────────┘   │
                                │              │                      │
                                │   ┌──────────▼──────────────────┐   │
                                │   │    MCP Service               │   │
                                │   │    (Port 8300)               │   │
                                │   └─────────────────────────────┘   │
                                │                                     │
Port-Forward                    │   ┌─────────────────────────────┐   │
────────►  8300  ──────────────►│   │    Direct Service Access    │   │
(Integration/API Tests)         │   │    (bypass gateway)         │   │
                                │   └─────────────────────────────┘   │
                                │                                     │
                                └─────────────────────────────────────┘
```

### MCP Service Ports

| Service | Port | Description |
|---------|------|-------------|
| MCP Server | 8300 | Main MCP service |
| Health | 8300/health | Health check endpoint |

## Quick Start

### Environment 1: Local Development

```bash
# 1. Create virtual environment
uv venv .venv
source .venv/bin/activate

# 2. Install dependencies
uv pip install -r deployment/requirements/dev.txt

# 3. Load dev environment
source deployment/environments/dev.env

# 4. Run MCP server
python main.py

# 5. Run tests (no infrastructure needed)
pytest tests/unit -v
pytest tests/component -v
```

### Environment 2: K8s Testing

```bash
# 1. Verify K8s context
kubectl config current-context  # Should be: kind-isa-cloud-local

# 2. Deploy to K8s
kubectl apply -k deployment/k8s/

# 3. Port-forward infrastructure
kubectl port-forward -n isa-cloud-staging svc/isa-postgres-grpc 50061:50061 &
kubectl port-forward -n isa-cloud-staging svc/qdrant 6333:6333 &
kubectl port-forward -n isa-cloud-staging svc/redis 6379:6379 &

# 4. Port-forward MCP service
kubectl port-forward -n isa-cloud-staging svc/mcp 8300:8300 &

# 5. Load test environment
source deployment/environments/test.env

# 6. Run tests
pytest tests/integration -v
pytest tests/api -v
./tests/smoke/mcp/smoke_test.sh
```

## Configuration Files

### environments/dev.env

Local development configuration:
- Uses localhost URLs
- Debug mode enabled
- No authentication required

### environments/test.env

K8s test configuration:
- Uses K8s service URLs
- Port-forwarded connections
- Test authentication tokens

### requirements/base.txt

Core dependencies required for MCP server:
- MCP SDK
- FastAPI + Uvicorn
- Database clients (PostgreSQL, Qdrant)
- AI/ML libraries

### requirements/dev.txt

Development dependencies:
- pytest and plugins
- Code formatting (black, ruff)
- Type checking (mypy)

## Building Docker Images

```bash
# Build MCP image
docker build -f deployment/k8s/Dockerfile.mcp -t mcp-service:latest .

# Push to registry (if needed)
docker tag mcp-service:latest your-registry/mcp-service:latest
docker push your-registry/mcp-service:latest
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   lsof -i :8300
   kill -9 <PID>
   ```

2. **K8s context wrong**
   ```bash
   kubectl config use-context kind-isa-cloud-local
   ```

3. **Pod not starting**
   ```bash
   kubectl logs -n isa-cloud-staging deployment/mcp
   kubectl describe pod -n isa-cloud-staging -l app=mcp
   ```
