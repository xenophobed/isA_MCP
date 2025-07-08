# Deployment Guide

This comprehensive guide covers all deployment options for isA_MCP, from local development to production-ready clusters.

## 🎯 Deployment Overview

isA_MCP supports multiple deployment strategies to fit different use cases:

- **🔧 Local Development** - Single server for development and testing
- **🐳 Docker Cluster** - Production-ready cluster with load balancing
- **☁️ Railway Cloud** - One-click cloud deployment
- **🏢 Enterprise** - Advanced production configurations

## 🏗️ Architecture Options

### Development Architecture
```mermaid
graph TB
    DEV[Development Server :4321]
    DB[(Local PostgreSQL)]
    REDIS[(Local Redis)]
    NEO[(Local Neo4j)]
    
    DEV --> DB
    DEV --> REDIS
    DEV --> NEO
```

### Production Cluster Architecture
```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx Load Balancer :8081]
    end
    
    subgraph "Smart MCP Cluster"
        S1[Smart MCP Server :4321]
        S2[Smart MCP Server :4322]
        S3[Smart MCP Server :4323]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL Cluster)]
        REDIS[(Redis Cluster)]
        NEO[(Neo4j Cluster)]
    end
    
    LB --> S1
    LB --> S2
    LB --> S3
    
    S1 --> PG
    S1 --> REDIS
    S1 --> NEO
    
    S2 --> PG
    S2 --> REDIS
    S2 --> NEO
    
    S3 --> PG
    S3 --> REDIS
    S3 --> NEO
```

### Cloud Architecture
```mermaid
graph TB
    subgraph "Railway Cloud"
        APP[isA_MCP Service]
        PG[(Managed PostgreSQL)]
        REDIS[(Managed Redis)]
    end
    
    subgraph "External Services"
        NEO[(Neo4j Aura)]
        ISA[ISA Model API]
    end
    
    CLIENT[Client Applications] --> APP
    APP --> PG
    APP --> REDIS
    APP --> NEO
    APP --> ISA
```

## 🚀 Quick Start Options

### Option 1: One-Click Development
```bash
# Clone and start development server
git clone <repository_url>
cd isA_MCP
pip install -r requirements.txt
python smart_mcp_server.py

# Access at http://localhost:4321
```

### Option 2: Docker Cluster (Recommended for Production)
```bash
# Start complete cluster with load balancer
docker-compose up -d

# Access via load balancer at http://localhost:8081
# Individual servers: 4321, 4322, 4323
```

### Option 3: Railway Cloud Deployment
```bash
# One-click deployment to Railway
railway up

# Automatic SSL, scaling, and monitoring
# Cost: $10-25/month
```

## 📋 Deployment Checklist

### Pre-Deployment Requirements
- [ ] **Python 3.11+** installed
- [ ] **Docker & Docker Compose** (for container deployment)
- [ ] **PostgreSQL 14+** with pgvector extension
- [ ] **Redis 6+** for caching
- [ ] **Neo4j 5.0+** for graph analytics (optional)
- [ ] **Environment variables** configured
- [ ] **SSL certificates** (for production)
- [ ] **Domain name** configured (for production)

### Configuration Checklist
- [ ] Database connections tested
- [ ] Environment variables set
- [ ] Security settings configured
- [ ] Monitoring enabled
- [ ] Backup strategy implemented
- [ ] Log rotation configured
- [ ] Health checks working

### Post-Deployment Validation
- [ ] Health endpoints responding
- [ ] All tools discoverable
- [ ] Database connectivity verified
- [ ] AI services responding
- [ ] Load balancer distributing requests
- [ ] Monitoring collecting metrics
- [ ] Logs being generated
- [ ] SSL certificates valid

## 🔧 Configuration Quick Reference

### Essential Environment Variables
```bash
# Core Configuration
ENV=production
MCP_PORT=4321
DATABASE_URL=postgresql://user:pass@host:5432/db
ISA_API_URL=http://localhost:8082

# Security
JWT_SECRET_KEY=your-secret-key
REQUIRE_AUTH=true

# Neo4j (Optional)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# External Services
BRAVE_TOKEN=your-brave-search-token
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
```

### Docker Compose Services
```yaml
services:
  smart-mcp-1:
    image: isa-mcp:latest
    ports: ["4321:4321"]
    
  smart-mcp-2:
    image: isa-mcp:latest
    ports: ["4322:4321"]
    
  smart-mcp-3:
    image: isa-mcp:latest
    ports: ["4323:4321"]
    
  nginx:
    image: nginx:alpine
    ports: ["8081:80"]
    
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: isa_mcp
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
```

## 📊 Performance Expectations

### Development Environment
- **Memory Usage**: ~500MB
- **CPU Usage**: ~10-20%
- **Startup Time**: <30 seconds
- **Response Time**: <200ms (tool selection)
- **Concurrent Users**: 10-20

### Production Cluster
- **Memory Usage**: ~1.5GB (3 servers + load balancer)
- **CPU Usage**: ~30-50% under load
- **Startup Time**: <60 seconds (full cluster)
- **Response Time**: <100ms (with load balancing)
- **Concurrent Users**: 100+ per server
- **Throughput**: 1000+ requests/second

### Cloud Deployment
- **Scaling**: Auto-scaling based on CPU/Memory
- **Availability**: 99.9% uptime SLA
- **Response Time**: <150ms (including network latency)
- **Global CDN**: Available in multiple regions
- **Backup**: Automated daily backups

## 🔍 Health Monitoring

### Health Check Endpoints
```bash
# Primary health check
curl http://localhost:8081/health

# Individual server health
curl http://localhost:4321/health
curl http://localhost:4322/health
curl http://localhost:4323/health

# Detailed health with metrics
curl http://localhost:8081/health?detailed=true
```

### Expected Health Response
```json
{
  "status": "healthy",
  "service": "Smart MCP Server",
  "version": "2.0.0",
  "uptime": "2h 34m 12s",
  "tools_registered": 35,
  "ai_selectors_active": 3,
  "database_connected": true,
  "memory_usage_mb": 487,
  "cpu_usage_percent": 15.3
}
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Port Conflicts
```bash
# Check if ports are in use
lsof -i :4321
lsof -i :8081

# Solution: Change ports in configuration
export MCP_PORT=4325
```

#### 2. Database Connection Errors
```bash
# Test database connection
psql postgresql://user:pass@host:5432/database

# Check PostgreSQL status
docker-compose ps postgres

# View database logs
docker-compose logs postgres
```

#### 3. Load Balancer Issues
```bash
# Check Nginx configuration
nginx -t

# View load balancer logs
docker-compose logs nginx

# Test upstream servers
curl http://localhost:4321/health
curl http://localhost:4322/health
curl http://localhost:4323/health
```

#### 4. Memory Issues
```bash
# Monitor memory usage
docker stats

# Check for memory leaks
ps aux | grep python | awk '{print $4}'

# Restart services if needed
docker-compose restart
```

### Performance Optimization
- **Database Connection Pooling**: Adjust pool size based on load
- **Redis Caching**: Configure appropriate TTL values
- **Load Balancer Tuning**: Optimize worker processes and connections
- **Container Resources**: Set appropriate memory and CPU limits

---

**Next Steps:**
- [Local Development](local.md) - Set up local development environment
- [Docker Deployment](docker.md) - Container-based deployment
- [Railway Cloud](railway.md) - Cloud deployment guide
- [Production Setup](production.md) - Enterprise production configuration