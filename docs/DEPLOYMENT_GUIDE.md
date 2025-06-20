# MCP Server Multi-Port Deployment Guide

This guide explains how to deploy the MCP (Model Context Protocol) server across multiple ports with load balancing and high availability.

## 🏗️ Architecture Overview

The deployment consists of:
- **3 MCP Server instances** running on ports 8001, 8002, 8003
- **Nginx load balancer** distributing traffic across servers
- **Health monitoring** for each server instance
- **Multiple deployment options**: Docker, systemd, or process manager

## 📁 Key Files

| File | Description |
|------|-------------|
| `multi_mcp_server.py` | Main MCP server with health endpoints |
| `docker-compose.yml` | Docker deployment configuration |
| `Dockerfile` | Container image definition |
| `nginx.conf` | Load balancer configuration |
| `manage-mcp.sh` | Process manager script |
| `start-mcp-servers.sh` | Systemd service installer |
| `setup-deployment.sh` | Comprehensive setup script |

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Install dependencies and setup everything
./setup-deployment.sh --all

# Check deployment status
./setup-deployment.sh --status
```

### Option 2: Docker Compose

```bash
# Start all services with Docker
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Option 3: Systemd Services

```bash
# Install as system services (requires sudo)
sudo ./start-mcp-servers.sh

# Check service status
sudo systemctl status mcp-server-8001 mcp-server-8002 mcp-server-8003
```

### Option 4: Process Manager

```bash
# Start with process manager
./manage-mcp.sh start

# Check status
./manage-mcp.sh status

# Stop servers
./manage-mcp.sh stop
```

## 🔧 Manual Setup Steps

### 1. Install Dependencies

```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y curl openssl nginx docker.io docker-compose
```

### 2. Create Directories

```bash
mkdir -p logs pids data ssl
```

### 3. Generate SSL Certificates (Development)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### 4. Test Single Server

```bash
# Test server startup
python3 multi_mcp_server.py --port 8888

# In another terminal, test health endpoint
curl http://localhost:8888/health
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build images
docker-compose build

# Start services in background
docker-compose up -d

# Scale services if needed
docker-compose up -d --scale mcp-server-1=2
```

### Docker Commands

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f mcp-server-1

# Restart specific service
docker-compose restart mcp-server-2

# Stop all services
docker-compose down

# Remove everything including volumes
docker-compose down -v --remove-orphans
```

## 🔧 Systemd Deployment

### Installation

```bash
# Install services (requires sudo)
sudo ./start-mcp-servers.sh
```

### Management Commands

```bash
# Check status
sudo systemctl status mcp-server-8001 mcp-server-8002 mcp-server-8003

# Start/Stop individual services
sudo systemctl start mcp-server-8001
sudo systemctl stop mcp-server-8002
sudo systemctl restart mcp-server-8003

# Enable/Disable auto-start
sudo systemctl enable mcp-server-8001
sudo systemctl disable mcp-server-8002

# View logs
sudo journalctl -u mcp-server-8001 -f
sudo journalctl -u mcp-server-8002 --since "1 hour ago"
```

## 📊 Process Manager Deployment

### Commands

```bash
# Start all servers
./manage-mcp.sh start

# Stop all servers
./manage-mcp.sh stop

# Restart all servers
./manage-mcp.sh restart

# Check status with health checks
./manage-mcp.sh status
```

### Log Files

```bash
# View logs
tail -f logs/server-8001.log
tail -f logs/server-8002.log
tail -f logs/server-8003.log

# Monitor all logs
tail -f logs/server-*.log
```

## 🔍 Monitoring and Health Checks

### Health Endpoints

```bash
# Check individual servers
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health

# Check through load balancer
curl http://localhost/health        # HTTP
curl -k https://localhost/health    # HTTPS
```

### MCP Endpoints

```bash
# Access MCP through load balancer
curl http://localhost/mcp
curl -k https://localhost/mcp

# Direct access to servers
curl http://localhost:8001/mcp
curl http://localhost:8002/mcp
curl http://localhost:8003/mcp
```

### Nginx Status

```bash
# Check nginx configuration
sudo nginx -t

# Reload nginx configuration
sudo nginx -s reload

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 🛠️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVER_ID` | Unique server identifier | `mcp-server-{port}` |
| `PORT` | Server port number | From command line |
| `PYTHONPATH` | Python module path | `/opt/mcp-server` |

### Nginx Configuration

Edit `nginx.conf` to customize:
- Domain names
- SSL certificates
- Rate limiting
- Upstream servers

### Docker Configuration

Edit `docker-compose.yml` to customize:
- Port mappings
- Environment variables
- Volume mounts
- Resource limits

## 🚦 Load Balancing

### Nginx Upstream Configuration

```nginx
upstream mcp_backend {
    least_conn;                                    # Load balancing method
    server mcp-server-1:8001 max_fails=3 fail_timeout=30s;
    server mcp-server-2:8002 max_fails=3 fail_timeout=30s;
    server mcp-server-3:8003 max_fails=3 fail_timeout=30s;
}
```

### Load Balancing Methods

- `least_conn`: Route to server with fewest active connections
- `ip_hash`: Route based on client IP hash
- `round_robin`: Default, route requests in sequence

## 🔒 Security Features

### Rate Limiting

```nginx
# MCP endpoints: 10 requests per second
limit_req_zone $binary_remote_addr zone=mcp_limit:10m rate=10r/s;

# Health endpoints: 1 request per second
limit_req_zone $binary_remote_addr zone=health_limit:10m rate=1r/s;
```

### SSL/TLS Configuration

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
```

### Systemd Security

```ini
# Security settings in systemd services
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/mcp-server/logs /opt/mcp-server/pids
```

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find process using port
   lsof -i :8001
   
   # Kill process
   kill -9 <PID>
   ```

2. **Permission Denied**
   ```bash
   # Check file permissions
   ls -la multi_mcp_server.py
   
   # Make executable
   chmod +x multi_mcp_server.py
   ```

3. **Module Not Found**
   ```bash
   # Install dependencies
   pip3 install -r requirements.txt
   
   # Check Python path
   python3 -c "import sys; print(sys.path)"
   ```

4. **Health Check Fails**
   ```bash
   # Check server logs
   tail -f logs/server-8001.log
   
   # Test direct connection
   telnet localhost 8001
   ```

### Log Analysis

```bash
# Check for errors
grep -i error logs/server-*.log

# Monitor real-time logs
tail -f logs/server-*.log | grep -i "error\|warning"

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Performance Tuning

```bash
# Check system resources
top
htop
iotop

# Monitor network connections
netstat -tulpn | grep :800

# Check disk space
df -h
du -sh logs/
```

## 📈 Scaling

### Horizontal Scaling

1. **Add More Servers**
   ```yaml
   # In docker-compose.yml
   mcp-server-4:
     build: .
     command: python multi_mcp_server.py --port 8004
     ports:
       - "8004:8004"
   ```

2. **Update Nginx Configuration**
   ```nginx
   upstream mcp_backend {
       least_conn;
       server mcp-server-1:8001;
       server mcp-server-2:8002;
       server mcp-server-3:8003;
       server mcp-server-4:8004;  # Add new server
   }
   ```

### Vertical Scaling

```yaml
# In docker-compose.yml
services:
  mcp-server-1:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

## 🔄 Backup and Recovery

### Backup Data

```bash
# Backup configuration
tar -czf mcp-backup-$(date +%Y%m%d).tar.gz \
    *.py *.yml *.conf requirements.txt ssl/ logs/

# Backup database (if using)
cp memory.db memory.db.backup
```

### Recovery

```bash
# Restore from backup
tar -xzf mcp-backup-20240101.tar.gz

# Restore services
./setup-deployment.sh --all
```

## 📞 Support

### Useful Commands Summary

```bash
# Setup and deployment
./setup-deployment.sh --help
./setup-deployment.sh --all
./setup-deployment.sh --status

# Docker management
docker-compose up -d
docker-compose ps
docker-compose logs -f
docker-compose down

# Process management
./manage-mcp.sh start|stop|restart|status

# Systemd management
sudo systemctl status mcp-server-8001
sudo journalctl -u mcp-server-8001 -f

# Health checks
curl http://localhost:8001/health
curl http://localhost/health

# Nginx management
sudo nginx -t
sudo nginx -s reload
```

### Getting Help

1. Check the logs first
2. Verify network connectivity
3. Test individual components
4. Review configuration files
5. Check system resources

---

**Note**: This deployment is configured for development/testing. For production use, ensure proper SSL certificates, security hardening, and monitoring solutions are in place. 