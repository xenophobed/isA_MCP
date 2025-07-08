# isA_MCP Documentation

Welcome to the comprehensive documentation for **isA_MCP** - an AI-powered Smart MCP (Model Context Protocol) Server that has evolved into an intelligent, enterprise-grade platform with comprehensive service integrations and automated capability discovery.

## 🎯 What is isA_MCP?

isA_MCP is a sophisticated, production-ready MCP server that provides:

- **🧠 AI-Powered Tool Selection** - Intelligent tool recommendation based on natural language queries
- **📊 Comprehensive Data Analytics** - Complete 5-step data processing workflow with LLM-powered SQL generation
- **🕸️ Advanced Web Services** - Modern web scraping with anti-detection and JavaScript execution
- **🧩 Graph Analytics** - Entity extraction, relationship mapping, and Neo4j integration
- **🛍️ E-commerce Integration** - Full Shopify integration with cart and checkout management
- **📚 RAG & Document Analytics** - Retrieval-augmented generation with multi-format document processing
- **🖼️ AI Image Generation** - Image creation and transformation capabilities
- **🧮 Memory Management** - Persistent information storage with intelligent retrieval
- **🔐 Enterprise Security** - Multi-level authorization with audit logging
- **🐳 Production-Ready** - Docker cluster deployment with load balancing

## 🚀 Quick Navigation

### 👋 New to isA_MCP?
Start with our [Getting Started Guide](getting-started/README.md) to set up your development environment and run your first queries.

### 🏗️ Want to understand the architecture?
Explore our [System Architecture](architecture/README.md) documentation to understand how all components work together.

### 🔧 Looking for specific services?
Browse our detailed service documentation:
- [Graph Analytics](services/graph-analytics/README.md) - Entity extraction and knowledge graphs
- [Data Analytics](services/data-analytics/README.md) - SQL generation and database analysis  
- [Web Services](services/web-services/README.md) - Intelligent web scraping
- [RAG & Documents](services/rag/README.md) - Document processing and Q&A
- [E-commerce](services/ecommerce/README.md) - Shopify integration
- [Image Generation](services/image-generation/README.md) - AI image creation

### 🚀 Ready to deploy?
Check out our [Deployment Guide](deployment/README.md) for local, Docker, and cloud deployment options.

### 💻 Need API references?
Visit our comprehensive [API Documentation](api/README.md) for detailed endpoint specifications.

### 🧪 Want to contribute?
Read our [Developer Guide](development/README.md) to understand our development standards and contribution process.

## 🌟 Key Features Highlights

### Intelligent Tool Selection
```python
# Natural language query automatically selects the right tools
query = "I need to analyze sales data from my database"
# Result: Automatically selects ['data_sourcing', 'data_query'] tools
```

### Complete Data Analytics Pipeline
```python
# 5-step workflow: Metadata → Semantic → Embedding → Query → SQL
await client.call_tool("data_query", {
    "query": "Show me top 10 customers by revenue this month",
    "connection_string": "postgresql://user:pass@host:5432/db"
})
```

### Advanced Web Scraping
```python
# AI-powered content extraction with anti-detection
await client.call_tool("scrape_webpage", {
    "url": "https://example.com",
    "extraction_schema": {"products": ["name", "price", "description"]},
    "use_stealth": True
})
```

### Graph Analytics
```python
# Extract entities and relationships from documents
await client.call_tool("graph_build_knowledge", {
    "source_content": "Research paper content...",
    "extract_entities": True,
    "extract_relations": True
})
```

## 📊 System Overview

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
        GA[Graph Analytics]
        WS[Web Services]
        RAG[RAG Service]
        SH[Shopify]
        IM[Image Gen]
        MEM[Memory]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL)]
        NEO[(Neo4j)]
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
    TS --> GA
    TS --> WS
    TS --> RAG
    TS --> SH
    TS --> IM
    TS --> MEM
    
    DA --> PG
    GA --> NEO
    RAG --> VEC
```

## 🎯 Use Cases

### Business Intelligence
- **Data Analytics**: Connect to multiple databases, generate insights with natural language queries
- **Document Analysis**: Process reports, contracts, and presentations with RAG capabilities
- **Market Research**: Scrape competitor data and analyze trends

### AI-Powered Automation
- **Content Generation**: Create and transform images with AI
- **Web Automation**: Extract structured data from websites with intelligent filtering
- **Knowledge Management**: Build knowledge graphs from documents and text

### E-commerce Operations
- **Product Management**: Search, add to cart, and process orders through Shopify integration
- **Customer Intelligence**: Store and retrieve customer preferences and behavior data
- **Inventory Analysis**: Connect to e-commerce databases for sales and inventory insights

## 📈 Performance & Scale

- **AI Tool Selection**: <200ms response time
- **Web Scraping Success Rate**: 95%+
- **Database Query Performance**: <500ms average
- **Memory Usage per Container**: ~500MB
- **Docker Container Startup**: <30 seconds
- **Concurrent Users**: 100+ per server instance

## 🔗 Quick Links

- [Installation Guide](getting-started/installation.md)
- [API Reference](api/tools.md)
- [Deployment Options](deployment/README.md)
- [Troubleshooting](user-guide/troubleshooting.md)
- [Contributing](development/contributing.md)

---

**Ready to get started?** Continue to the [Getting Started Guide](getting-started/README.md) to begin your journey with isA_MCP.