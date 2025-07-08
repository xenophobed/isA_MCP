# System Architecture

isA_MCP is built with a modern, scalable architecture that combines AI intelligence with enterprise-grade reliability. This document provides a comprehensive overview of the system's design principles, components, and data flow.

## 🏗️ Architecture Overview

The system follows a layered architecture pattern with clear separation of concerns:

```mermaid
graph TB
    subgraph "Client Layer"
        CLI[CLI Clients]
        API[API Clients]
        SDK[SDK Integrations]
    end
    
    subgraph "Load Balancer & Gateway"
        LB[Nginx Load Balancer]
        GW[API Gateway]
    end
    
    subgraph "Smart MCP Cluster"
        S1[MCP Server 1]
        S2[MCP Server 2]
        S3[MCP Server 3]
    end
    
    subgraph "AI Intelligence Layer"
        AD[Auto Discovery]
        TS[Tool Selector]
        PS[Prompt Selector]
        RS[Resource Selector]
    end
    
    subgraph "Service Layer"
        DA[Data Analytics Service]
        GA[Graph Analytics Service]
        WS[Web Services]
        RAG[RAG Service]
        MEM[Memory Service]
        IMG[Image Generation]
        SHOP[Shopify Service]
        EVT[Event Sourcing]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL + pgvector)]
        NEO[(Neo4j Graph DB)]
        REDIS[(Redis Cache)]
        FILES[(File Storage)]
    end
    
    subgraph "External Integrations"
        ISA[ISA Model API]
        BRAVE[Brave Search]
        SHOPIFY[Shopify API]
        OPENAI[OpenAI API]
    end
    
    CLI --> LB
    API --> LB
    SDK --> LB
    
    LB --> GW
    GW --> S1
    GW --> S2
    GW --> S3
    
    S1 --> AD
    S2 --> AD
    S3 --> AD
    
    AD --> TS
    AD --> PS
    AD --> RS
    
    TS --> DA
    TS --> GA
    TS --> WS
    TS --> RAG
    TS --> MEM
    TS --> IMG
    TS --> SHOP
    TS --> EVT
    
    DA --> PG
    GA --> NEO
    WS --> REDIS
    RAG --> PG
    MEM --> PG
    IMG --> FILES
    SHOP --> REDIS
    EVT --> PG
    
    DA --> ISA
    GA --> ISA
    WS --> BRAVE
    IMG --> ISA
    SHOP --> SHOPIFY
```

## 🎯 Design Principles

### 1. **AI-First Architecture**
- **Intelligent Tool Selection**: Natural language queries automatically map to appropriate tools
- **Context-Aware Processing**: Services understand and adapt to query context
- **Adaptive Workflows**: System learns from usage patterns to optimize performance

### 2. **Microservices Design**
- **Service Isolation**: Each service is independently deployable and scalable
- **Clear Boundaries**: Well-defined interfaces between components
- **Fault Tolerance**: Failure in one service doesn't affect others

### 3. **Scalability & Performance**
- **Horizontal Scaling**: Add more server instances as needed
- **Load Balancing**: Distribute requests across multiple servers
- **Caching Strategy**: Multi-layer caching for optimal performance

### 4. **Enterprise Security**
- **Multi-Level Authorization**: LOW, MEDIUM, HIGH security levels
- **Audit Logging**: Comprehensive tracking of all operations
- **JWT Authentication**: Secure token-based authentication

## 🧩 Core Components

### Smart MCP Server Core
```python
class SmartMCPServer:
    """
    Main server orchestrating all services and AI components
    """
    def __init__(self):
        self.auto_discovery = AutoDiscovery()
        self.tool_selector = ToolSelector()
        self.security_manager = SecurityManager()
        self.service_registry = ServiceRegistry()
```

**Responsibilities:**
- Tool registration and discovery
- Request routing and load balancing
- Security enforcement and audit logging
- Service lifecycle management

### AI Intelligence Layer

#### Auto Discovery System
```python
class AutoDiscovery:
    """
    Automatically discovers and registers tools, prompts, and resources
    """
    async def discover_tools(self) -> Dict[str, ToolMetadata]:
        # Scans codebase for MCP tools
        # Extracts metadata from docstrings
        # Generates embeddings for semantic search
```

#### Tool Selector
```python
class ToolSelector:
    """
    AI-powered tool selection based on natural language queries
    """
    async def select_tools(self, query: str) -> List[ToolRecommendation]:
        # Analyzes query semantics
        # Matches against tool embeddings
        # Returns ranked tool recommendations
```

### Service Layer Architecture

Each service follows the same architectural pattern:

```python
class BaseService:
    """Base class for all services"""
    def __init__(self, service_name: str):
        self.isa_client = get_isa_client()
        self.security_manager = get_security_manager()
        self.billing_tracker = BillingTracker()
    
    async def call_isa_with_billing(self, ...):
        # Unified ISA API calling with cost tracking
        
    def create_service_response(self, ...):
        # Standardized response format with billing info
```

## 📊 Data Flow Architecture

### 1. Request Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant LoadBalancer
    participant MCPServer
    participant ToolSelector
    participant Service
    participant ISA_API
    participant Database

    Client->>LoadBalancer: Natural Language Query
    LoadBalancer->>MCPServer: Route to Available Server
    MCPServer->>ToolSelector: Analyze Query Intent
    ToolSelector-->>MCPServer: Recommended Tools + Confidence
    MCPServer->>Service: Execute Selected Tool
    Service->>ISA_API: LLM Processing (if needed)
    ISA_API-->>Service: AI Response + Billing
    Service->>Database: Store/Retrieve Data
    Database-->>Service: Data Response
    Service-->>MCPServer: Service Response + Billing
    MCPServer-->>LoadBalancer: Formatted Response
    LoadBalancer-->>Client: Final Response + Metadata
```

### 2. Data Analytics Workflow

```mermaid
graph LR
    A[Natural Query] --> B[Query Analysis]
    B --> C[Tool Selection]
    C --> D[Data Sourcing]
    D --> E[Metadata Extraction]
    E --> F[Semantic Enrichment]
    F --> G[Embedding Generation]
    G --> H[Query Matching]
    H --> I[SQL Generation]
    I --> J[Execution & Results]
    
    subgraph "Step 1-2"
        D
        E
    end
    
    subgraph "Step 3"
        F
        G
    end
    
    subgraph "Step 4-5"
        H
        I
        J
    end
```

### 3. Web Services Pipeline

```mermaid
graph TD
    A[Web Request] --> B[Browser Manager]
    B --> C[Stealth Configuration]
    C --> D[Page Loading]
    D --> E[Content Detection]
    E --> F[Element Analysis]
    F --> G[AI Extraction]
    G --> H[Content Filtering]
    H --> I[Response Formatting]
    
    subgraph "Anti-Detection"
        C
        style C fill:#ff9999
    end
    
    subgraph "AI Processing"
        G
        style G fill:#99ccff
    end
```

## 🔧 Service Architecture Details

### Data Analytics Service
```python
class DataAnalyticsService(BaseService):
    """
    5-step data processing workflow
    """
    components:
        - MetadataExtractor: Database schema analysis
        - SemanticEnricher: Business entity identification  
        - EmbeddingStorage: Vector storage with pgvector
        - QueryMatcher: Natural language to SQL intent
        - SQLExecutor: Query generation and execution
```

### Graph Analytics Service
```python
class GraphAnalyticsService(BaseService):
    """
    Entity extraction and relationship mapping
    """
    components:
        - EntityExtractor: Named entity recognition
        - RelationExtractor: Relationship identification
        - Neo4jClient: Graph database operations
        - KnowledgeGraph: Graph construction and querying
```

### Web Services Platform
```python
class WebServicesManager:
    """
    Intelligent web scraping and automation
    """
    components:
        - BrowserManager: Playwright automation with stealth
        - DetectionEngine: Element identification strategies
        - ExtractionEngine: Content extraction with AI
        - FilteringEngine: Relevance scoring and filtering
```

## 🗄️ Data Layer Design

### PostgreSQL + pgvector
```sql
-- Core tables for data analytics
CREATE TABLE metadata_cache (
    id SERIAL PRIMARY KEY,
    table_name TEXT,
    columns JSONB,
    embeddings vector(1536)
);

-- Memory system tables
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    key TEXT,
    value TEXT,
    category TEXT,
    keywords TEXT[],
    embeddings vector(1536)
);
```

### Neo4j Graph Database
```cypher
// Entity and relationship storage
CREATE (e:Entity {
    id: $entity_id,
    type: $entity_type,
    canonical_form: $name,
    confidence: $confidence
})

CREATE (r:Relation {
    type: $relation_type,
    confidence: $confidence
})-[:CONNECTS]->(source:Entity)-[:TO]->(target:Entity)
```

### Redis Caching Strategy
```python
# Multi-layer caching
cache_layers = {
    'tool_embeddings': 3600,      # 1 hour
    'web_sessions': 1800,         # 30 minutes  
    'query_results': 600,         # 10 minutes
    'metadata_cache': 7200,       # 2 hours
}
```

## 🔐 Security Architecture

### Authentication & Authorization
```python
class SecurityManager:
    """
    Multi-level security enforcement
    """
    security_levels = {
        'LOW': ['get_weather', 'search_memories'],
        'MEDIUM': ['remember', 'data_query'], 
        'HIGH': ['forget', 'admin_functions']
    }
    
    async def authorize_tool(self, tool_name: str, user_context: dict):
        # Check security level requirements
        # Validate JWT tokens
        # Log audit events
```

### Audit Logging
```python
class AuditLogger:
    """
    Comprehensive operation tracking
    """
    async def log_operation(self, 
                           user_id: str,
                           tool_name: str, 
                           parameters: dict,
                           result: dict,
                           billing_info: dict):
        # Store in audit_logs table
        # Include security context
        # Track billing information
```

## 📈 Performance Characteristics

### Benchmarks
- **Tool Selection Response**: < 200ms
- **Web Scraping Success Rate**: 95%+
- **Database Query Average**: < 500ms  
- **Memory Usage per Container**: ~500MB
- **Startup Time**: < 30 seconds

### Scalability Metrics
- **Concurrent Users per Server**: 100+
- **Requests per Second**: 1,000+
- **Horizontal Scaling**: Linear scaling up to 10+ instances
- **Database Connections**: Pool size 10-50 per service

### Monitoring & Observability
- **Health Checks**: `/health` endpoint on all services
- **Metrics Collection**: Prometheus integration
- **Distributed Tracing**: Request correlation across services
- **Performance Profiling**: Built-in performance monitoring

## 🔄 Deployment Architecture

### Development Environment
```yaml
# Single server instance
smart_mcp_server.py
├── Auto Discovery
├── All Services  
├── SQLite/PostgreSQL
└── File-based storage
```

### Production Cluster
```yaml
# Load-balanced cluster
nginx_load_balancer:8081
├── smart_mcp_server_1:4321
├── smart_mcp_server_2:4322  
├── smart_mcp_server_3:4323
├── postgresql_cluster
├── neo4j_cluster
└── redis_cluster
```

### Cloud Deployment
```yaml
# Railway/Docker deployment
services:
  - smart_mcp_server (auto-scaling)
  - postgresql (managed)
  - redis (managed)
  - neo4j (managed)
```

---

**Next Steps:**
- [Core Components](core-components.md) - Detailed component specifications
- [Service Layer](service-layer.md) - Individual service architectures  
- [Data Layer](data-layer.md) - Database design and data flow
- [Security Model](security-model.md) - Security implementation details