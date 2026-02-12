# Quick Start

## Startup Flow

```
Start main.py
  ↓
Auto-Discovery scans the `tools/` directory
  ↓
Parses Python files, extracts `@mcp.tool()` decorators
  ↓
Registers 88+ tools with FastMCP
  ↓
Sync Service synchronizes tools with PostgreSQL
  ↓
Generates embeddings via the Model Service
  ↓
Stores vectors and metadata in Qdrant
  ↓
Service Ready
```

## Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (for infrastructure)
- **PostgreSQL 14+** (with `pgvector` extension)
- **Qdrant** (vector database)
- **Redis 6+** (cache)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd isA_MCP
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp deployment/.env.template .env
   vim .env
   ```

4. **Start infrastructure (with Docker):**
   ```bash
   docker-compose -f deployment/dev/docker-compose.yml up -d postgres qdrant redis
   ```

5. **Run the MCP server:**
   ```bash
   # Development mode (with hot-reload)
   python main.py
   # Server runs at http://localhost:8081

   # Production mode (with Uvicorn)
   uvicorn main:app --host 0.0.0.0 --port 8081
   ```

## Verify Installation

```bash
curl http://localhost:8081/health

# Expected output:
# {
#   "status": "healthy",
#   "service": "Smart MCP Server",
#   "capabilities": {
#     "tools": 88,
#     "prompts": 50,
#     "resources": 9
#   }
# }
```

## Next Steps

- [Client Usage Guide](./guidance/quickstart.md) -- Full MCP client code with examples
- [Core Concepts](./concepts.md) -- Architecture diagrams and service flows
- [Configuration](./guidance/configuration.md) -- Detailed server configuration
- [Environment Variables](./env/README.md) -- Full environment variable reference
