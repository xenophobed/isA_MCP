# Configuration Reference

This document provides comprehensive reference for configuring isA_MCP, including environment variables, service settings, and deployment options.

## 🔧 Configuration Overview

isA_MCP uses a centralized configuration system with the following hierarchy:

1. **Environment Variables** (`deployment/dev/.env`) - Base configuration
2. **Core Config** (`core/config.py`) - Centralized settings management  
3. **Service Access** (`base_service.py`, `base_tool.py`) - Configuration consumption

```mermaid
graph LR
    A[.env Files] --> B[core/config.py]
    B --> C[BaseService]
    B --> D[BaseTool]
    B --> E[Individual Services]
    
    subgraph "Configuration Sources"
        A
    end
    
    subgraph "Central Management"
        B
    end
    
    subgraph "Consumers"
        C
        D
        E
    end
```

## 📁 Environment Files

### Development Environment
```bash
# deployment/dev/.env
ENV=development
DEBUG=true
PYTHONPATH=.
PYTHONUNBUFFERED=1
```

### Production Environment
```bash
# deployment/production/.env
ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

### Testing Environment
```bash
# deployment/test/.env
ENV=test
DEBUG=true
DATABASE_URL=postgresql://test:test@localhost:5432/test_db
```

## 🏗️ Core System Configuration

### Server Settings
```bash
# MCP Server Configuration
MCP_HOST=0.0.0.0                    # Server bind address
MCP_PORT=4321                       # Server port
MCP_SERVER_NAME="isA_MCP Server"    # Server display name
MCP_REQUIRE_AUTH=false              # Enable authentication

# Load Balancer (Production)
NGINX_PORT=8081                     # Load balancer port
NGINX_WORKERS=3                     # Number of server instances
```

### Database Configuration
```bash
# PostgreSQL (Primary Database)
DATABASE_URL=postgresql://user:password@host:5432/database
DB_SCHEMA=dev                       # Database schema

# Supabase (Development)
SUPABASE_LOCAL_URL=http://127.0.0.1:54321
SUPABASE_LOCAL_ANON_KEY=your_anon_key
SUPABASE_LOCAL_SERVICE_ROLE_KEY=your_service_key
SUPABASE_PWD=postgres

# Supabase (Production)
SUPABASE_CLOUD_URL=https://your-project.supabase.co
SUPABASE_CLOUD_ANON_KEY=your_cloud_anon_key
SUPABASE_CLOUD_SERVICE_ROLE_KEY=your_cloud_service_key

# Neo4j (Graph Database)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Redis (Caching)
REDIS_URL=redis://localhost:6379
```

### Authentication & Security
```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# Encryption
ENCRYPTION_KEY=your-32-character-encryption-key

# Security Levels
MCP_SECURITY_REQUIRE_AUTHORIZATION=true
MCP_SECURITY_AUTO_APPROVE_LOW=true
MCP_SECURITY_AUTO_APPROVE_MEDIUM=false

# Rate Limiting
RATE_LIMIT_PER_HOUR=1000
MAX_WORKERS=4
```

## 🤖 AI Service Configuration

### ISA Model Integration
```bash
# ISA API Configuration
ISA_API_URL=http://localhost:8082    # ISA Model API endpoint
ISA_TIMEOUT=30                       # Request timeout in seconds
ISA_MAX_RETRIES=3                   # Maximum retry attempts
ISA_RETRY_DELAY=1.0                 # Delay between retries
```

### External AI APIs
```bash
# OpenAI
OPENAI_API_KEY=sk-your-openai-key
OPENAI_API_BASE=https://api.openai.com/v1

# Replicate
REPLICATE_API_TOKEN=r8_your-replicate-token

# Hugging Face
HF_TOKEN=hf_your-huggingface-token

# RunPod
RUNPOD_API_KEY=rpa_your-runpod-key
```

## 📊 Service-Specific Configuration

### Data Analytics Service
```bash
# Data Analytics Configuration
DATA_ANALYTICS_MAX_CONNECTIONS=10   # Database connection pool
DATA_ANALYTICS_QUERY_TIMEOUT=30     # Query timeout in seconds
DATA_ANALYTICS_CACHE_TTL=3600       # Cache time-to-live
DATA_ANALYTICS_MAX_ROWS=10000       # Maximum result rows
DATA_ANALYTICS_ENABLE_EXPLAIN=true  # Enable query explanation

# Embedding Configuration
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=100
```

### Graph Analytics Service
```bash
# LLM Configuration for Graph Analytics
GRAPH_MAX_TOKENS=4000               # Maximum tokens per LLM call
GRAPH_TEMPERATURE=0.1               # LLM temperature for consistency
GRAPH_DEFAULT_CONFIDENCE=0.8        # Default confidence threshold

# Text Processing Configuration
GRAPH_LONG_TEXT_THRESHOLD=50000     # Threshold for long text processing
GRAPH_CHUNK_SIZE=100000             # Chunk size for large documents
GRAPH_CHUNK_OVERLAP=5000            # Overlap between chunks

# Processing Configuration
GRAPH_MAX_CONCURRENT=5              # Maximum concurrent extractions
GRAPH_BATCH_SIZE=10                 # Batch size for processing

# Similarity and Search Configuration
GRAPH_SIMILARITY_THRESHOLD=0.7      # Vector similarity threshold
GRAPH_EMBEDDING_DIMENSION=1536      # Embedding vector dimension

# Performance and Logging
GRAPH_DEBUG=false                   # Enable debug logging
GRAPH_PERF_LOG=true                # Enable performance logging
GRAPH_SLOW_THRESHOLD=5.0           # Slow operation threshold (seconds)
GRAPH_MAX_RETRIES=3                # Maximum retry attempts
GRAPH_RETRY_DELAY=1.0              # Delay between retries (seconds)
GRAPH_ENABLE_FALLBACK=true         # Enable fallback processing
```

### Web Services Configuration
```bash
# Browser Configuration
WEB_BROWSER_TYPE=chromium           # chromium, firefox, webkit
WEB_HEADLESS=true                  # Run browser in headless mode
WEB_STEALTH_MODE=true              # Enable anti-detection
WEB_USER_AGENT=Custom Bot 1.0      # Custom user agent

# Performance Settings
WEB_PAGE_TIMEOUT=30000             # Page load timeout (ms)
WEB_NAVIGATION_TIMEOUT=10000       # Navigation timeout (ms)
WEB_MAX_CONCURRENT=3               # Maximum concurrent browsers
WEB_POOL_SIZE=5                    # Browser pool size

# Anti-Detection Settings
WEB_RANDOM_DELAYS=true             # Random delays between actions
WEB_MIN_DELAY=1000                 # Minimum delay (ms)
WEB_MAX_DELAY=3000                 # Maximum delay (ms)
WEB_VIEWPORT_WIDTH=1920            # Browser viewport width
WEB_VIEWPORT_HEIGHT=1080           # Browser viewport height

# Proxy Configuration
WEB_PROXY_ENABLED=false            # Enable proxy usage
WEB_PROXY_TYPE=http                # http, socks5
WEB_PROXY_HOST=proxy.example.com   # Proxy host
WEB_PROXY_PORT=8080                # Proxy port
WEB_PROXY_ROTATION=true            # Enable proxy rotation
```

### RAG & Document Processing
```bash
# Document Processing
RAG_CHUNK_SIZE=1000                # Text chunk size
RAG_CHUNK_OVERLAP=200              # Chunk overlap
RAG_MAX_FILE_SIZE=50MB             # Maximum file size
RAG_SUPPORTED_FORMATS=pdf,docx,txt,pptx  # Supported file formats

# Vector Storage
RAG_COLLECTION_PREFIX=isa_mcp      # Collection name prefix
RAG_EMBEDDING_MODEL=text-embedding-ada-002
RAG_EMBEDDING_DIMENSION=1536
RAG_SIMILARITY_THRESHOLD=0.7

# Search Configuration
RAG_MAX_RESULTS=10                 # Maximum search results
RAG_RERANK_ENABLED=true           # Enable result re-ranking
RAG_INCLUDE_METADATA=true         # Include metadata in results
```

### E-commerce (Shopify) Configuration
```bash
# Shopify API Configuration
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_STOREFRONT_ACCESS_TOKEN=your-storefront-token
SHOPIFY_ADMIN_API_KEY=shpat_your-admin-key
SHOPIFY_API_VERSION=2024-01       # API version

# Cart Configuration
SHOPIFY_CART_TIMEOUT=3600         # Cart timeout in seconds
SHOPIFY_MAX_CART_ITEMS=100        # Maximum items per cart
SHOPIFY_CURRENCY=USD              # Default currency

# Product Search
SHOPIFY_SEARCH_LIMIT=50           # Default search result limit
SHOPIFY_INCLUDE_VARIANTS=true     # Include product variants
SHOPIFY_INCLUDE_IMAGES=true       # Include product images
```

### Memory System Configuration
```bash
# Memory Storage
MEMORY_MAX_ENTRIES=10000          # Maximum memory entries per user
MEMORY_MAX_VALUE_SIZE=10KB        # Maximum value size
MEMORY_DEFAULT_TTL=365            # Default TTL in days
MEMORY_AUTO_CLEANUP=true          # Enable automatic cleanup

# Search Configuration
MEMORY_SEARCH_LIMIT=50            # Default search result limit
MEMORY_SIMILARITY_THRESHOLD=0.7   # Similarity threshold
MEMORY_AUTO_KEYWORDS=true         # Auto-generate keywords
MEMORY_MAX_KEYWORDS=20            # Maximum keywords per entry
```

### Image Generation Configuration
```bash
# Image Generation
IMAGE_DEFAULT_SIZE=1024x1024      # Default image size
IMAGE_DEFAULT_QUALITY=high        # Default quality (standard, high, ultra)
IMAGE_MAX_BATCH_SIZE=5           # Maximum batch generation
IMAGE_OUTPUT_FORMAT=PNG          # Default output format

# File Storage
IMAGE_STORAGE_PATH=/app/images    # Image storage directory
IMAGE_MAX_FILE_SIZE=10MB         # Maximum file size
IMAGE_CLEANUP_ENABLED=true       # Enable automatic cleanup
IMAGE_CLEANUP_AGE_DAYS=30        # Cleanup files older than X days
```

## 🔍 Search & Discovery Configuration
```bash
# Search APIs
BRAVE_TOKEN=BSA_your-brave-search-token
SEARCH_DEFAULT_LIMIT=10           # Default search result limit
SEARCH_TIMEOUT=5                  # Search timeout in seconds

# Tool Discovery
AUTO_DISCOVERY_ENABLED=true       # Enable automatic tool discovery
TOOL_EMBEDDING_CACHE_TTL=86400    # Tool embedding cache TTL
TOOL_METADATA_REFRESH=3600        # Metadata refresh interval
```

## 📋 Logging & Monitoring Configuration

### Logging Settings
```bash
# Log Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=mcp_server.log          # Log file path
LOG_MAX_SIZE=10MB                # Maximum log file size
LOG_BACKUP_COUNT=5               # Number of backup files
LOG_FORMAT=structured            # structured, simple

# Performance Logging
PERF_LOG_ENABLED=true            # Enable performance logging
PERF_LOG_THRESHOLD=1000          # Log operations slower than X ms
PERF_LOG_INCLUDE_PARAMS=false    # Include parameters in perf logs

# Audit Logging
AUDIT_LOG_ENABLED=true           # Enable audit logging
AUDIT_LOG_INCLUDE_SUCCESS=true   # Log successful operations
AUDIT_LOG_INCLUDE_PARAMS=true    # Include parameters in audit logs
```

### Monitoring & Metrics
```bash
# Prometheus Metrics
METRICS_ENABLED=true             # Enable metrics collection
METRICS_PORT=9090                # Metrics endpoint port
METRICS_PATH=/metrics            # Metrics endpoint path

# Health Checks
HEALTH_CHECK_ENABLED=true        # Enable health check endpoint
HEALTH_CHECK_INTERVAL=30         # Health check interval (seconds)
HEALTH_CHECK_TIMEOUT=5           # Health check timeout (seconds)

# Alerting
ALERT_EMAIL_ENABLED=false        # Enable email alerts
ALERT_EMAIL_SMTP_HOST=smtp.gmail.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_USERNAME=alerts@yourcompany.com
ALERT_EMAIL_PASSWORD=your-email-password
ALERT_EMAIL_TO=admin@yourcompany.com
```

## 🚀 Deployment Configuration

### Docker Configuration
```bash
# Docker Settings
DOCKER_IMAGE_TAG=latest          # Docker image tag
DOCKER_REGISTRY=docker.io        # Docker registry
DOCKER_NAMESPACE=your-org        # Docker namespace

# Container Resources
CONTAINER_MEMORY_LIMIT=1G        # Memory limit per container
CONTAINER_CPU_LIMIT=1.0          # CPU limit per container
CONTAINER_REPLICAS=3             # Number of container replicas
```

### Load Balancer Configuration
```bash
# Nginx Load Balancer
NGINX_WORKER_PROCESSES=auto      # Nginx worker processes
NGINX_WORKER_CONNECTIONS=1024    # Worker connections
NGINX_KEEPALIVE_TIMEOUT=65       # Keep-alive timeout
NGINX_CLIENT_MAX_BODY_SIZE=10M   # Maximum request body size

# Load Balancing
LB_METHOD=round_robin            # round_robin, least_conn, ip_hash
LB_HEALTH_CHECK_INTERVAL=10      # Health check interval (seconds)
LB_MAX_FAILS=3                   # Maximum failures before marking down
LB_FAIL_TIMEOUT=30               # Fail timeout (seconds)
```

### Cloud Deployment (Railway)
```bash
# Railway Configuration
RAILWAY_PROJECT_ID=your-project-id
RAILWAY_ENVIRONMENT=production    # production, staging, development
RAILWAY_SERVICE_NAME=isa-mcp     # Service name
RAILWAY_DOMAIN=your-app.railway.app

# Auto-Scaling
RAILWAY_MIN_REPLICAS=1           # Minimum replicas
RAILWAY_MAX_REPLICAS=5           # Maximum replicas
RAILWAY_CPU_THRESHOLD=80         # CPU threshold for scaling (%)
RAILWAY_MEMORY_THRESHOLD=80      # Memory threshold for scaling (%)
```

## 🔧 Configuration Access in Code

### Centralized Settings Access
```python
# Access configuration in services
from core.config import get_settings

class MyService(BaseService):
    def __init__(self):
        super().__init__("my_service")
        self.settings = get_settings()
        
        # Access service-specific settings
        self.max_tokens = self.settings.graph_analytics.max_tokens
        self.neo4j_uri = self.settings.graph_analytics.neo4j_uri
        
        # Access global settings
        self.debug_mode = self.settings.debug
        self.database_url = self.settings.database_url
```

### Environment-Specific Loading
```python
# Configuration automatically loads based on ENV variable
import os
from core.config import get_settings

# Set environment
os.environ["ENV"] = "production"

# Get environment-specific settings
settings = get_settings()

# Settings will be loaded from:
# - deployment/production/.env (if ENV=production)
# - deployment/dev/.env (if ENV=development)
# - deployment/test/.env (if ENV=test)
```

### Custom Configuration Sections
```python
# Add new configuration section
@dataclass
class MyServiceSettings:
    api_key: str = ""
    endpoint: str = "https://api.example.com"
    timeout: int = 30

# Extend MCPSettings
@dataclass 
class MCPSettings:
    # ... existing settings ...
    my_service: MyServiceSettings = field(default_factory=MyServiceSettings)
    
    def load_from_env(self):
        # ... existing loading ...
        
        # Load custom settings
        self.my_service.api_key = os.getenv("MY_SERVICE_API_KEY", "")
        self.my_service.endpoint = os.getenv("MY_SERVICE_ENDPOINT", self.my_service.endpoint)
        self.my_service.timeout = int(os.getenv("MY_SERVICE_TIMEOUT", str(self.my_service.timeout)))
        
        return self
```

## 🔄 Configuration Validation

### Environment Validation
```python
# Validate required environment variables
class ConfigValidator:
    required_vars = [
        "DATABASE_URL",
        "ISA_API_URL", 
        "JWT_SECRET_KEY"
    ]
    
    @classmethod
    def validate_environment(cls):
        missing_vars = []
        for var in cls.required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
```

### Configuration Testing
```python
# Test configuration loading
def test_configuration():
    settings = get_settings()
    
    # Validate core settings
    assert settings.server_name
    assert settings.port > 0
    assert settings.database_url
    
    # Validate service settings
    assert settings.graph_analytics.max_tokens > 0
    assert settings.graph_analytics.neo4j_uri
    
    print("✅ Configuration validation passed")
```

## 📚 Configuration Examples

### Development Setup
```bash
# .env for development
ENV=development
DEBUG=true
MCP_PORT=4321
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/isa_mcp_dev
NEO4J_URI=bolt://localhost:7687
REDIS_URL=redis://localhost:6379
ISA_API_URL=http://localhost:8082
GRAPH_DEBUG=true
LOG_LEVEL=DEBUG
```

### Production Setup
```bash
# .env for production
ENV=production
DEBUG=false
MCP_PORT=4321
DATABASE_URL=postgresql://user:pass@prod-db:5432/isa_mcp
NEO4J_URI=bolt://neo4j-cluster:7687
REDIS_URL=redis://redis-cluster:6379
ISA_API_URL=https://isa-api.yourcompany.com
LOG_LEVEL=INFO
METRICS_ENABLED=true
AUDIT_LOG_ENABLED=true
```

### Testing Setup
```bash
# .env for testing
ENV=test
DEBUG=true
MCP_PORT=4322
DATABASE_URL=postgresql://test:test@localhost:5432/isa_mcp_test
NEO4J_URI=bolt://localhost:7688
REDIS_URL=redis://localhost:6380
LOG_LEVEL=DEBUG
CACHE_ENABLED=false
```

---

**Related Documentation:**
- [Environment Variables](environment.md) - Complete environment variable reference
- [Deployment Guide](../deployment/README.md) - Deployment-specific configuration
- [API Reference](README.md) - API configuration options