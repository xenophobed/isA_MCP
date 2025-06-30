# isA_MCP - AI-Powered Smart MCP Server

## 🎯 Project Overview

**isA_MCP** is a sophisticated AI-powered Smart MCP (Model Context Protocol) Server that has evolved into an intelligent, enterprise-grade platform with comprehensive service integrations and automated capability discovery.

### 🤖 Key Features

- 🧠 **AI-Powered Tool Selection** - Intelligent tool recommendation based on natural language queries
- 📊 **Data Analytics Suite** - Complete 5-step data processing workflow with LLM-powered SQL generation
- 🕸️ **Advanced Web Services** - Modern web scraping with anti-detection and JavaScript execution
- 🛍️ **E-commerce Integration** - Full Shopify integration with cart and checkout management
- 📚 **RAG & Document Analytics** - Retrieval-augmented generation with multi-format document processing
- 🖼️ **AI Image Generation** - Image creation and transformation capabilities
- 🧮 **Memory Management** - Persistent information storage with intelligent retrieval
- 🔐 **Enterprise Security** - Multi-level authorization with audit logging
- 🐳 **Production-Ready** - Docker cluster deployment with load balancing

## 🏗️ System Architecture

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
    
    subgraph "AI Core"
        AD[Auto Discovery]
        TS[Tool Selector]
        PS[Prompt Selector]
    end
    
    subgraph "Services Layer"
        DA[Data Analytics]
        WS[Web Services]
        RAG[RAG Service]
        SH[Shopify]
        IM[Image Gen]
        MEM[Memory]
        EV[Event Sourcing]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL/Supabase)]
        MY[(MySQL)]
        SS[(SQL Server)]
        VEC[(Vector Store)]
    end
    
    LB --> S1
    LB --> S2
    LB --> S3
    
    S1 --> AD
    S2 --> AD
    S3 --> AD
    
    AD --> TS
    AD --> PS
    
    TS --> DA
    TS --> WS
    TS --> RAG
    TS --> SH
    TS --> IM
    TS --> MEM
    TS --> EV
    
    DA --> PG
    DA --> MY
    DA --> SS
    RAG --> VEC
    WS --> PG
```

## 🚀 Quick Start

### Requirements

- **Python 3.11+**
- **Docker & Docker Compose**
- **PostgreSQL 14+** (with pgvector extension)
- **Redis 6+** (for caching and sessions)

### Installation

1. **Clone the repository:**
```bash
git clone <repository_url>
cd isA_MCP
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Environment setup:**
```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your database credentials and API keys
```

4. **Database setup:**
```bash
# Start PostgreSQL with pgvector extension
docker-compose up -d postgres
```

5. **Start the Smart MCP Server:**

**Option A: Single Server (Development)**
```bash
python smart_mcp_server.py
```

**Option B: Production Cluster**
```bash
# Start complete cluster with load balancer
docker-compose up -d
# Access via http://localhost:8081
```

**Option C: Railway Deployment**
```bash
# One-click deployment to Railway
railway up
```

## 🛠️ Services & Capabilities

### 📊 Data Analytics Service
**Complete 5-Step Data Processing Workflow**
- **Step 1**: Metadata extraction from databases (PostgreSQL, MySQL, SQL Server) and files
- **Step 2**: Semantic enrichment with business entity identification
- **Step 3**: Embedding generation and vector storage (pgvector)
- **Step 4**: Natural language query matching using semantic similarity
- **Step 5**: LLM-powered SQL generation with fallback strategies
- **Tools**: `data_sourcing`, `data_query`

### 🕸️ Web Services Platform
**Modern Web Scraping with AI Enhancement**
- Multi-provider search integration (Brave API)
- Playwright browser automation with stealth capabilities
- LLM-powered content extraction with predefined schemas
- AI-enhanced filtering and relevance scoring
- Human behavior simulation for anti-detection
- **Tools**: `scrape_webpage`, `scrape_multiple_pages`, `extract_page_links`, `search_page_content`

### 📚 RAG & Document Analytics
**Intelligent Document Processing**
- Supabase pgvector integration for vector storage
- Multi-format document processing (PDF, DOC, DOCX, PPT, PPTX, TXT)
- Quick RAG question-answering for documents
- Multi-collection support with user isolation
- **Tools**: `search_rag_documents`, `add_rag_documents`, `quick_rag_question`

### 🛍️ Shopify E-commerce Integration
**Complete E-commerce Workflow**
- Product search and catalog management
- Shopping cart operations and management
- Checkout and payment processing (test environment)
- Customer profile and shipping address management
- **Tools**: `search_products`, `add_to_cart`, `view_cart`, `start_checkout`, `process_payment`

### 🖼️ AI Image Generation
**Creative AI Services**
- AI image creation with custom prompts
- Image-to-image transformation capabilities
- File-based image generation and storage
- **Tools**: `generate_image`, `generate_image_to_file`, `image_to_image`

### 🧮 Memory Management System
**Persistent Information Storage**
- Categorized memory storage with keyword tagging
- Intelligent memory retrieval and search
- Secure memory deletion with authorization
- **Tools**: `remember`, `forget`, `update_memory`, `search_memories`

### 🔄 Event Sourcing & Background Tasks
**Asynchronous Processing**
- Background task creation and lifecycle management
- Event-driven architecture support
- Task monitoring and control (pause/resume/delete)
- **Tools**: `create_background_task`, `list_background_tasks`, `pause_background_task`

### 🔐 Security & Administration
**Enterprise-Grade Security**
- Multi-level authorization (LOW, MEDIUM, HIGH)
- JWT-based authentication with bcrypt password hashing
- Comprehensive audit logging and monitoring
- Human-in-the-loop interaction workflows
- **Tools**: `request_authorization`, `check_security_status`, `get_audit_log`

## 🤖 AI-Powered Features

### Auto-Discovery System
The Smart MCP Server automatically discovers and registers all available tools, prompts, and resources:

```python
# Auto-discovery extracts metadata from docstrings and function signatures
from core.auto_discovery import AutoDiscovery

discovery = AutoDiscovery()
tools = await discovery.discover_tools()  # Finds all MCP tools
prompts = await discovery.discover_prompts()  # Extracts prompts
resources = await discovery.discover_resources()  # Identifies resources
```

### AI Tool Selection
Intelligent tool recommendation based on natural language queries:

```python
from core.ai_selectors import ToolSelector

selector = ToolSelector()
# Natural language query gets matched to appropriate tools
tools = await selector.select_tools("I need to analyze sales data from my database")
# Returns: ['data_sourcing', 'data_query'] with confidence scores
```

## 📚 API Documentation

### Data Analytics API
```python
# Extract database metadata and create embeddings
await client.call_tool("data_sourcing", {
    "connection_string": "postgresql://user:pass@host:5432/db",
    "tables": ["sales", "customers"]
})

# Query data using natural language
await client.call_tool("data_query", {
    "query": "Show me top 10 customers by revenue this month",
    "connection_string": "postgresql://user:pass@host:5432/db"
})
```

### Web Services API
```python
# Advanced web scraping with AI extraction
await client.call_tool("scrape_webpage", {
    "url": "https://example.com",
    "extraction_schema": {
        "products": ["name", "price", "description"]
    },
    "use_stealth": True
})

# Multi-page scraping with pagination
await client.call_tool("scrape_multiple_pages", {
    "base_url": "https://example.com/products",
    "max_pages": 10,
    "extraction_schema": {"products": ["name", "price"]}
})
```

### RAG & Document Analytics API
```python
# Quick document Q&A
await client.call_tool("quick_rag_question", {
    "file_path": "/path/to/document.pdf",
    "question": "What are the key findings in this report?"
})

# Add documents to RAG collection
await client.call_tool("add_rag_documents", {
    "collection_name": "company_docs",
    "documents": ["Document content..."],
    "metadatas": [{"source": "report.pdf"}]
})

# Search RAG documents
await client.call_tool("search_rag_documents", {
    "collection_name": "company_docs",
    "query": "quarterly results",
    "n_results": 5
})
```

### Shopify E-commerce API
```python
# Search products
await client.call_tool("search_products", {
    "query": "wireless headphones",
    "limit": 10
})

# Add to cart and checkout
await client.call_tool("add_to_cart", {
    "product_id": "12345",
    "quantity": 2
})

await client.call_tool("start_checkout", {
    "cart_id": "cart_123"
})
```

### Memory Management API
```python
# Store information with categories
await client.call_tool("remember", {
    "key": "customer_preferences",
    "value": "Prefers email notifications",
    "category": "customer_data",
    "keywords": ["email", "notifications", "preferences"]
})

# Search memories
await client.call_tool("search_memories", {
    "query": "customer email preferences"
})
```

## 🧪 Testing & Quality Assurance

### Comprehensive Test Suite
The project includes 40+ test files covering all major components:

```bash
# Run all tests
pytest

# Run specific service tests
pytest tests/test_data_analytics_service.py
pytest tests/test_web_services.py
pytest tests/test_rag_operations.py
pytest tests/test_shopify_integration.py

# Run performance benchmarks
pytest tests/test_performance.py -v
```

### Test Coverage Areas
- ✅ **Data Analytics**: Complete 5-step workflow testing
- ✅ **Web Services**: Scraping, extraction, and anti-detection
- ✅ **RAG & Documents**: Multi-format processing and Q&A
- ✅ **E-commerce**: Shopping cart and checkout workflows
- ✅ **Security**: Authentication, authorization, and audit logging
- ✅ **AI Features**: Tool selection and auto-discovery
- ✅ **Integration**: End-to-end service interactions

### Performance Metrics
- **AI Tool Selection**: <200ms response time
- **Web Scraping Success Rate**: 95%+
- **Database Query Performance**: <500ms average
- **Memory Usage per Container**: ~500MB
- **Docker Container Startup**: <30 seconds

## 📝 Development Standards

- **Code Quality**: PEP 8 compliance with type annotations
- **Testing**: Comprehensive unit and integration tests
- **Architecture**: Async-first with proper error handling
- **Security**: Multi-level authorization and audit logging
- **Documentation**: Complete docstrings and API documentation
- **Performance**: Optimized for production workloads

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Errors**
```bash
# Check PostgreSQL status
docker-compose ps postgres

# Verify pgvector extension
psql -h localhost -U postgres -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

2. **AI Tool Selection Issues**
```bash
# Check if embeddings are properly generated
python -c "from core.auto_discovery import AutoDiscovery; print(AutoDiscovery().get_tool_embeddings())"
```

3. **Web Scraping Failures**
```bash
# Check Playwright browser installation
playwright install chromium

# Verify anti-detection settings
python -c "from tools.services.web_services.browser_manager import BrowserManager; BrowserManager().test_stealth()"
```

4. **Memory Issues in Production**
```bash
# Monitor container memory usage
docker stats

# Check Redis cache status
redis-cli ping
```

## 🚀 Deployment Options

### Development (Local)
```bash
# Single server for development
python smart_mcp_server.py

# Access at http://localhost:4321
```

### Production (Docker Cluster)
```bash
# Start complete cluster with load balancer
docker-compose up -d

# 3 Smart MCP servers + Nginx load balancer
# Access at http://localhost:8081
```

### Cloud Deployment (Railway)
```bash
# One-click deployment to Railway
railway up

# Automatic SSL, scaling, and monitoring
# Cost: $10-25/month
```

### Manual Docker Build
```bash
# Build production image
docker build -f Dockerfile.production -t isa-mcp:latest .

# Run with environment variables
docker run -d \
  -p 4321:4321 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  isa-mcp:latest
```

## 📊 Performance & Monitoring

### Health Monitoring
```bash
# Check cluster health
curl http://localhost:8081/health

# Individual server health
curl http://localhost:4321/health
curl http://localhost:4322/health
curl http://localhost:4323/health
```

### Metrics Collection
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Performance dashboards
- **Audit Logging**: Security and compliance tracking
- **Load Balancer Stats**: Request distribution and response times

### Production Readiness Checklist
- ✅ Docker cluster with load balancing
- ✅ Health monitoring and automatic failover
- ✅ Security: JWT auth, bcrypt passwords, audit logs
- ✅ Performance: <200ms AI tool selection, 95%+ uptime
- ✅ Testing: 40+ test files, integration tests
- ✅ Documentation: Complete API docs and deployment guides

## 🌟 Key Differentiators

1. **AI-Powered Intelligence**: Unlike traditional MCP servers, provides intelligent tool selection
2. **Enterprise Architecture**: Production-grade cluster deployment with monitoring
3. **Comprehensive Integration**: 35+ tools across 11 service categories
4. **Modern Web Platform**: Advanced scraping with anti-detection capabilities
5. **Extensible Design**: Modular architecture for easy service addition

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests before submitting
pytest

# Run linting
flake8 --config .flake8
black --check .
```

## 🔗 Links & Resources

- **MCP Protocol**: [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- **FastMCP**: [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- **Supabase**: [PostgreSQL with pgvector](https://supabase.com/docs/guides/database/extensions/pgvector)
- **Railway**: [Railway Deployment Platform](https://railway.app/)

## 📄 License

**MIT License** - see [LICENSE](LICENSE) file for details.

---

**Status**: 🟢 **Production Ready** | **Version**: 2.0.0 | **Last Updated**: 2024-12-30
