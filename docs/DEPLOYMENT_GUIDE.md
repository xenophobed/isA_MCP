# 🚀 Smart MCP Server Docker Cluster Deployment Guide

This guide explains how to deploy the Smart MCP Server cluster with AI-powered tool selection, load balancing, and comprehensive monitoring.

## 🏗️ Architecture Overview

The Smart MCP deployment consists of:
- **3 Smart MCP Server instances** running on ports 4321, 4322, 4323
- **Nginx load balancer** with intelligent request distribution (Port 8081)
- **AI-powered tool selection** using embedding-based similarity matching
- **Comprehensive web scraping** with Playwright and anti-detection
- **Health monitoring** and performance metrics
- **Docker cluster** with automatic scaling and recovery

## 📁 Key Files

| File | Description |
|------|-------------|
| `smart_server.py` | AI-powered Smart MCP server with tool selection |
| `docker-compose.smart.yml` | Smart cluster deployment configuration |
| `Dockerfile.smart` | Container image with Playwright dependencies |
| `deployment/nginx.smart.conf` | Load balancer for Smart MCP cluster |
| `start_smart_cluster.sh` | One-click cluster startup script |
| `test_docker_cluster.py` | Comprehensive cluster testing suite |

## 🚀 Quick Start

### Option 1: One-Click Deployment (Recommended)

```bash
# Make startup script executable
chmod +x start_smart_cluster.sh

# Start the complete Smart MCP cluster
./start_smart_cluster.sh

# Test the cluster
python test_docker_cluster.py
```

### Option 2: Manual Docker Compose

```bash
# Start Smart MCP cluster
docker-compose -f docker-compose.smart.yml up -d

# Check service status
docker-compose -f docker-compose.smart.yml ps

# View logs
docker-compose -f docker-compose.smart.yml logs -f
```

### Option 3: Development Mode

```bash
# Single Smart MCP server for development
python smart_server.py --port 4321

# Test AI tool selection
curl -X POST http://localhost:4321/analyze \
  -H "Content-Type: application/json" \
  -d '{"request": "scrape website for product information"}'
```

## 🔧 Prerequisites and Setup

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y curl docker.io docker-compose-plugin
```

### 2. Environment Configuration

Create `.env.local` file:
```bash
# Core API Keys
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1

# Shopify Integration
SHOPIFY_STORE_DOMAIN=example.myshopify.com
SHOPIFY_STOREFRONT_ACCESS_TOKEN=your-token-here
SHOPIFY_ADMIN_API_KEY=your-admin-key-here

# Image Generation
REPLICATE_API_TOKEN=your-replicate-token-here

# Communication Tools
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=your-twilio-phone
```

### 3. Create Required Directories

```bash
mkdir -p logs screenshots deployment/ssl
```

## 🐳 Docker Cluster Deployment

### Smart MCP Cluster Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Nginx Load Balancer                      │
│                    (Port 8081)                              │
│               ┌─────────────────────────┐                   │
│               │ /mcp     - MCP Protocol │                   │
│               │ /analyze - AI Tool Rec  │                   │
│               │ /stats   - Statistics   │                   │
│               │ /health  - Health Check │                   │
│               └─────────────────────────┘                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼───┐    ┌────▼───┐    ┌────▼───┐
   │Smart-1 │    │Smart-2 │    │Smart-3 │
   │Port    │    │Port    │    │Port    │
   │4321    │    │4322    │    │4323    │
   │        │    │        │    │        │
   │AI Tools│    │AI Tools│    │AI Tools│
   │Web Scrp│    │Web Scrp│    │Web Scrp│
   │Shopify │    │Shopify │    │Shopify │
   │Memory  │    │Memory  │    │Memory  │
   └────────┘    └────────┘    └────────┘
```

### Build and Start Cluster

```bash
# Build images with all dependencies
docker-compose -f docker-compose.smart.yml build

# Start cluster in background
docker-compose -f docker-compose.smart.yml up -d

# Wait for services to initialize
sleep 30

# Check cluster health
curl http://localhost:8081/health
```

### Container Management

```bash
# View running containers
docker-compose -f docker-compose.smart.yml ps

# View logs for specific service
docker-compose -f docker-compose.smart.yml logs -f smart-mcp-server-1

# Restart specific service
docker-compose -f docker-compose.smart.yml restart smart-mcp-server-2

# Scale services (if needed)
docker-compose -f docker-compose.smart.yml up -d --scale smart-mcp-server-1=2

# Stop cluster
docker-compose -f docker-compose.smart.yml down

# Remove everything including volumes
docker-compose -f docker-compose.smart.yml down -v --remove-orphans
```

## 🔍 Smart MCP Endpoints

### Load Balancer Endpoints (Port 8081)

```bash
# Health check
curl http://localhost:8081/health

# Server statistics
curl http://localhost:8081/stats

# AI tool analysis
curl -X POST http://localhost:8081/analyze \
  -H "Content-Type: application/json" \
  -d '{"request": "generate an image of a sunset"}'

# MCP protocol endpoint
curl -X POST http://localhost:8081/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'
```

### Direct Server Access

```bash
# Access individual servers
curl http://localhost:4321/health
curl http://localhost:4322/health
curl http://localhost:4323/health

# Test AI tool selection on specific server
curl -X POST http://localhost:4321/analyze \
  -H "Content-Type: application/json" \
  -d '{"request": "scrape website content"}'
```

## 🧪 Testing and Validation

### Comprehensive Cluster Testing

```bash
# Run full test suite
python test_docker_cluster.py
```

Expected output:
```
🚀 Smart MCP Server Docker Cluster Test Suite
==================================================
🏥 Testing Health Checks...
  ✅ http://localhost:4321/health - Status: healthy
  ✅ http://localhost:4322/health - Status: healthy  
  ✅ http://localhost:4323/health - Status: healthy
  ✅ http://localhost:8081/health - Status: healthy

✅ Health Check Results: 4/4 servers healthy

🧠 Testing AI Tool Selection...
  🎯 'scrape website for product information' -> ['scrape_webpage', 'get_product_details', 'get_scraper_status']
  🎯 'remember important user data' -> ['remember', 'get_user_info', 'forget']
  🎯 'generate an image of a sunset' -> ['generate_image_to_file', 'generate_image', 'image_to_image']

🕸️ Testing Web Scraper Integration...
  📋 Found 6 web scraper tools:
      • scrape_webpage
      • scrape_multiple_pages
      • extract_page_links

🎯 Overall Result: ✅ CLUSTER WORKING
```

### Manual Testing

```bash
# Test specific functionalities
curl -X POST http://localhost:8081/analyze \
  -H "Content-Type: application/json" \
  -d '{"request": "scrape website for news"}'

curl -X POST http://localhost:8081/analyze \
  -H "Content-Type: application/json" \
  -d '{"request": "remember user preferences"}'

curl -X POST http://localhost:8081/analyze \
  -H "Content-Type: application/json" \
  -d '{"request": "search shopify products"}'
```

## 📊 Monitoring and Health Checks

### Service Health Monitoring

```bash
# Check all services
./start_smart_cluster.sh && sleep 10
python test_docker_cluster.py

# Individual health checks
curl http://localhost:4321/health | jq '.server_status'
curl http://localhost:4322/health | jq '.server_status'
curl http://localhost:4323/health | jq '.server_status'
```

### Performance Metrics

```bash
# Get server statistics
curl http://localhost:8081/stats | jq '.'

# Check loaded tools
curl http://localhost:8081/health | jq '.server_status.loaded_tools'

# Monitor tool selector status
curl http://localhost:8081/health | jq '.server_status.tool_selector_ready'
```

### Log Analysis

```bash
# View Smart server logs
docker-compose -f docker-compose.smart.yml logs smart-mcp-server-1 | tail -50

# Monitor all servers
docker-compose -f docker-compose.smart.yml logs -f

# Check nginx logs
docker-compose -f docker-compose.smart.yml logs smart-nginx
```

## 🔧 Configuration

### Smart Server Configuration

The Smart MCP servers support AI-powered tool selection with the following features:

**Tool Categories Supported:**
- `web`: Web scraping and content extraction
- `memory`: Information storage and retrieval  
- `image`: AI image generation and processing
- `shopify`: E-commerce and product management
- `admin`: System administration and monitoring
- `client`: User interaction and communication
- `event`: Background task and event management
- `weather`: Weather data and forecasts

**AI Tool Selection:**
- Uses OpenAI embeddings for semantic similarity
- Caches embedding results for performance
- Returns top 3 most relevant tools
- Supports natural language tool requests

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings | - | ✅ |
| `SHOPIFY_STORE_DOMAIN` | Shopify store domain | - | Optional |
| `SHOPIFY_STOREFRONT_ACCESS_TOKEN` | Shopify API token | - | Optional |
| `REPLICATE_API_TOKEN` | Replicate API for image generation | - | Optional |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | - | Optional |

### Load Balancer Configuration

The nginx load balancer (`deployment/nginx.smart.conf`) provides:

- **Session Affinity**: Uses `ip_hash` for MCP persistent connections
- **Rate Limiting**: 20 requests/second for Smart MCP endpoints
- **Health Checks**: Automatic failover for unhealthy servers
- **SSE Support**: Proper handling of Server-Sent Events
- **Extended Timeouts**: 24-hour timeouts for AI processing

## 🚦 Load Balancing and Scaling

### Nginx Configuration

```nginx
upstream smart_mcp_backend {
    ip_hash;  # Session affinity for MCP connections
    server smart-mcp-server-1:4321 max_fails=1 fail_timeout=5s;
    server smart-mcp-server-2:4322 max_fails=1 fail_timeout=5s;
    server smart-mcp-server-3:4323 max_fails=1 fail_timeout=5s;
}
```

### Horizontal Scaling

Add more servers to the cluster:

```yaml
# In docker-compose.smart.yml
smart-mcp-server-4:
  build: 
    context: .
    dockerfile: Dockerfile.smart
  command: python smart_server.py --port 4324
  ports:
    - "4324:4324"
  # ... same configuration as other servers
```

Update nginx upstream:
```nginx
server smart-mcp-server-4:4324 max_fails=1 fail_timeout=5s;
```

### Vertical Scaling

```yaml
# Resource limits for containers
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

## 🔒 Security Features

### Built-in Security

- **Authorization Levels**: LOW, MEDIUM, HIGH security requirements
- **Rate Limiting**: Nginx-based request throttling
- **Security Headers**: CORS, XSS protection, content type validation
- **SSL/TLS Ready**: HTTPS configuration templates included

### Production Security Checklist

```bash
# 1. Use proper SSL certificates
cp your-cert.pem deployment/ssl/cert.pem
cp your-key.pem deployment/ssl/key.pem

# 2. Update nginx configuration for HTTPS
# Edit deployment/nginx.smart.conf

# 3. Set secure environment variables
export OPENAI_API_KEY="secure-key-here"
export SHOPIFY_STOREFRONT_ACCESS_TOKEN="secure-token-here"

# 4. Enable firewall rules
sudo ufw allow 8081/tcp
sudo ufw deny 4321:4323/tcp  # Block direct access to servers
```

## 🐛 Troubleshooting

### Common Issues

1. **Port Conflicts (8081 already in use)**
   ```bash
   # Find process using port 8081
   lsof -i :8081
   
   # Stop conflicting service
   docker-compose down
   
   # Or change port in docker-compose.smart.yml
   ```

2. **Build Failures**
   ```bash
   # Check dependency conflicts
   docker-compose -f docker-compose.smart.yml build --no-cache
   
   # View build logs
   docker-compose -f docker-compose.smart.yml logs
   ```

3. **Health Check Failures**
   ```bash
   # Check individual server logs
   docker-compose -f docker-compose.smart.yml logs smart-mcp-server-1
   
   # Test direct connection
   curl http://localhost:4321/health
   ```

4. **AI Tool Selection Not Working**
   ```bash
   # Check OpenAI API key
   echo $OPENAI_API_KEY
   
   # Test embeddings directly
   curl -X POST http://localhost:4321/analyze \
     -H "Content-Type: application/json" \
     -d '{"request": "test"}'
   ```

### Debug Commands

```bash
# Full cluster status
docker-compose -f docker-compose.smart.yml ps

# Check resource usage
docker stats

# Network troubleshooting
docker network ls
docker network inspect isa_mcp_smart-mcp-network

# Volume inspection
docker volume ls | grep smart
```

## 📈 Performance Optimization

### Caching Configuration

The Smart MCP servers include built-in caching:
- **Embedding Cache**: Caches OpenAI embedding results
- **Tool Selection Cache**: Caches similar requests
- **Web Scraping Cache**: Caches scraped content

### Performance Monitoring

```bash
# Monitor response times
time curl http://localhost:8081/analyze \
  -X POST -H "Content-Type: application/json" \
  -d '{"request": "scrape website"}'

# Check memory usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Monitor tool usage patterns
curl http://localhost:8081/stats | jq '.tool_usage'
```

## 🔄 Backup and Recovery

### Configuration Backup

```bash
# Backup entire configuration
tar -czf smart-mcp-backup-$(date +%Y%m%d).tar.gz \
    smart_server.py \
    docker-compose.smart.yml \
    Dockerfile.smart \
    deployment/ \
    test_docker_cluster.py \
    start_smart_cluster.sh \
    requirements.txt \
    .env.local

# Backup volumes
docker run --rm -v isa_mcp_smart-screenshots-1:/data \
    -v $(pwd):/backup alpine \
    tar czf /backup/screenshots-backup.tar.gz /data
```

### Disaster Recovery

```bash
# Stop cluster
docker-compose -f docker-compose.smart.yml down

# Restore from backup
tar -xzf smart-mcp-backup-20240101.tar.gz

# Rebuild and restart
docker-compose -f docker-compose.smart.yml build --no-cache
docker-compose -f docker-compose.smart.yml up -d

# Verify functionality
python test_docker_cluster.py
```

## 📞 Support and Maintenance

### Health Monitoring Script

```bash
#!/bin/bash
# health-monitor.sh
while true; do
    echo "$(date): Checking Smart MCP Cluster Health"
    python test_docker_cluster.py > health-$(date +%Y%m%d-%H%M).log
    if [ $? -eq 0 ]; then
        echo "✅ Cluster healthy"
    else
        echo "❌ Cluster issues detected - check logs"
    fi
    sleep 300  # Check every 5 minutes
done
```

### Useful Commands Reference

```bash
# Deployment
./start_smart_cluster.sh                    # Start cluster
docker-compose -f docker-compose.smart.yml up -d  # Manual start
python test_docker_cluster.py              # Test cluster

# Monitoring
curl http://localhost:8081/health           # Health check
curl http://localhost:8081/stats            # Statistics
docker-compose -f docker-compose.smart.yml logs -f  # Logs

# Management
docker-compose -f docker-compose.smart.yml restart  # Restart
docker-compose -f docker-compose.smart.yml down     # Stop
docker-compose -f docker-compose.smart.yml ps       # Status
```

---

## 🎯 Next Steps

1. **Production Deployment**: Configure SSL, monitoring, and backups
2. **Custom Tools**: Add domain-specific tools with Keywords/Category metadata
3. **Advanced AI**: Implement custom embedding models or fine-tuning
4. **Monitoring**: Set up Prometheus/Grafana for advanced metrics
5. **Integration**: Connect with existing systems and workflows

**Status**: ✅ Smart MCP Cluster Ready for Production

The Smart MCP Server cluster provides AI-powered tool selection, comprehensive web scraping, and enterprise-grade reliability. Perfect for applications requiring intelligent tool recommendation and modern web interaction capabilities.