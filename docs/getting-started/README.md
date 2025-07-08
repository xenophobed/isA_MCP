# Getting Started

Welcome to isA_MCP! This guide will help you get up and running with the AI-powered Smart MCP Server in just a few minutes.

## 🎯 What You'll Learn

By the end of this guide, you'll have:
- ✅ isA_MCP installed and running locally
- ✅ Successfully connected to the server
- ✅ Made your first AI-powered tool calls
- ✅ Understanding of the basic architecture

## 📋 Prerequisites

Before you begin, ensure you have:

### Required Software
- **Python 3.11+** - Download from [python.org](https://python.org)
- **Git** - For cloning the repository
- **Docker & Docker Compose** - For database and production deployment

### Recommended Tools
- **Visual Studio Code** - With Python extension
- **PostgreSQL client** - For database inspection
- **Postman or curl** - For API testing

### System Requirements
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space
- **Network**: Internet connection for downloading dependencies

## 🚀 Installation Options

Choose the installation method that best fits your needs:

### Option 1: Quick Start (Recommended for first-time users)
```bash
# Clone the repository
git clone <repository_url>
cd isA_MCP

# Install dependencies
pip install -r requirements.txt

# Start with minimal setup
python smart_mcp_server.py
```

### Option 2: Docker Development Environment
```bash
# Clone and start with Docker
git clone <repository_url>
cd isA_MCP

# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Install Python dependencies
pip install -r requirements.txt

# Start the server
python smart_mcp_server.py
```

### Option 3: Full Production Cluster
```bash
# Clone the repository
git clone <repository_url>
cd isA_MCP

# Start complete cluster
docker-compose up -d

# Access via load balancer at http://localhost:8081
```

## ⚡ Quick Start Guide

### 1. Clone and Install
```bash
git clone <repository_url>
cd isA_MCP
pip install -r requirements.txt
```

### 2. Basic Configuration
Create a `.env` file or use the default configuration:
```bash
# Copy example environment
cp deployment/dev/.env.example .env

# Edit with your preferences (optional for quick start)
nano .env
```

### 3. Start the Server
```bash
# Start the Smart MCP Server
python smart_mcp_server.py

# You should see:
# ✅ Smart MCP Server started successfully
# 🌐 Server running at http://localhost:4321
# 🤖 AI Tool Discovery completed: 35+ tools registered
```

### 4. Verify Installation
Open a new terminal and test the connection:
```bash
# Check server health
curl http://localhost:4321/health

# Expected response:
# {"status": "healthy", "version": "2.0.0", "tools": 35}
```

### 5. Make Your First Tool Call
```python
import asyncio
from mcp import ClientSession

async def test_first_call():
    # Connect to the server
    session = ClientSession("stdio")
    
    # List available tools
    tools = await session.list_tools()
    print(f"Available tools: {len(tools.tools)}")
    
    # Make a simple memory call
    result = await session.call_tool("remember", {
        "key": "first_test",
        "value": "Hello isA_MCP!",
        "category": "testing"
    })
    
    print(f"Result: {result}")

# Run the test
asyncio.run(test_first_call())
```

## 🧪 Testing Your Installation

### Test 1: Basic Tool Discovery
```bash
python -c "
from core.auto_discovery import AutoDiscovery
discovery = AutoDiscovery()
tools = discovery.discover_tools()
print(f'✅ Discovered {len(tools)} tools')
"
```

### Test 2: AI Tool Selection
```bash
python -c "
from tools.core.tool_selector import ToolSelector
selector = ToolSelector()
result = selector.select_tools('I need to analyze data')
print(f'✅ AI selected tools: {result}')
"
```

### Test 3: Database Connection (if using Docker)
```bash
python -c "
from core.database.supabase_client import get_supabase_client
client = get_supabase_client()
print('✅ Database connection successful')
"
```

## 🔧 Configuration Basics

### Environment Variables
Key configuration options in `.env`:

```bash
# Server Configuration
MCP_PORT=4321
DEBUG=false

# Database (optional for basic usage)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

# AI Services
ISA_API_URL=http://localhost:8082

# Neo4j (for Graph Analytics)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

### Service Configuration
Enable/disable specific services:
```python
# In smart_mcp_server.py
ENABLED_SERVICES = [
    'memory',           # Memory management
    'data_analytics',   # Database analytics
    'web_services',     # Web scraping
    'graph_analytics',  # Graph analysis
    'image_generation', # AI image creation
    'rag_documents',    # Document Q&A
    'shopify',          # E-commerce
]
```

## 🎯 Next Steps

Now that you have isA_MCP running, explore these key features:

### 1. **Learn the Core Services**
- [Data Analytics](../services/data-analytics/README.md) - Database analysis and SQL generation
- [Web Services](../services/web-services/README.md) - Intelligent web scraping
- [Graph Analytics](../services/graph-analytics/README.md) - Entity and relationship extraction
- [RAG Documents](../services/rag/README.md) - Document question-answering

### 2. **Try Advanced Features**
- **AI Tool Selection**: Let the system choose the right tools for your queries
- **Multi-database Integration**: Connect to PostgreSQL, MySQL, and SQL Server
- **Intelligent Web Scraping**: Extract structured data with AI assistance
- **Knowledge Graph Building**: Create graphs from your documents

### 3. **Explore the API**
- [API Documentation](../api/README.md) - Complete API reference
- [Tool Endpoints](../api/tools.md) - Individual tool specifications
- [Authentication](../api/authentication.md) - Security and access control

### 4. **Deploy to Production**
- [Docker Deployment](../deployment/docker.md) - Container-based deployment
- [Railway Cloud](../deployment/railway.md) - One-click cloud deployment
- [Production Setup](../deployment/production.md) - Enterprise deployment

## 🆘 Getting Help

### Common Issues
1. **Import Errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`
2. **Port Conflicts**: Change `MCP_PORT` in `.env` if port 4321 is in use
3. **Database Connections**: Check Docker containers with `docker-compose ps`

### Resources
- [Troubleshooting Guide](../user-guide/troubleshooting.md)
- [FAQ](../resources/faq.md)
- [GitHub Issues](https://github.com/your-repo/issues)

### Community
- **Documentation**: This comprehensive guide
- **Examples**: Check the `/examples` directory
- **Tests**: Review `/tests` for usage patterns

---

**Ready for more?** Continue to [Configuration](configuration.md) to customize your setup, or jump to [Quick Start](quick-start.md) for hands-on examples.