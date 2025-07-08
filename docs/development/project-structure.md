# Project Structure

This document provides a comprehensive overview of the isA_MCP project structure, explaining the purpose and organization of each directory and key file.

## 📁 Root Directory Structure

```
isA_MCP/
├── 🚀 smart_mcp_server.py          # Main server entry point with AI features
├── 📋 requirements.txt             # Python dependencies
├── 📋 pyproject.toml               # Project configuration and metadata
├── 📄 README.md                    # Project overview and quick start
├── 📄 LICENSE                      # MIT license
│
├── 📁 core/                        # Core framework components
├── 📁 tools/                       # MCP tools and services
├── 📁 deployment/                  # Deployment configurations
├── 📁 docs/                        # Documentation (GitBook format)
├── 📁 tests/                       # Comprehensive test suite
├── 📁 examples/                    # Usage examples and demos
├── 📁 logs/                        # Server logs and monitoring
├── 📁 cache/                       # Temporary cache files
├── 📁 config/                      # Configuration files
├── 📁 models/                      # AI model metadata
├── 📁 prompts/                     # AI prompt templates
├── 📁 resources/                   # MCP resources and database files
├── 📁 monitoring/                  # Monitoring and metrics
└── 📁 sessions/                    # User session data
```

## 🧠 Core Framework (`core/`)

The core directory contains the fundamental framework components that power isA_MCP:

```
core/
├── __init__.py                     # Core module initialization
├── config.py                      # Centralized configuration management
├── isa_client.py                  # ISA Model API integration
├── security.py                    # Authentication and authorization
├── auth.py                        # JWT and user authentication
├── monitoring.py                  # Performance monitoring and metrics
├── logging.py                     # Structured logging system
├── exception.py                   # Custom exception handling
├── utils.py                       # Common utility functions
├── auto_discovery.py              # Automatic tool/service discovery
└── database/                      # Database management
    ├── __init__.py
    ├── supabase_client.py         # Supabase integration
    ├── connection_manager.py      # Database connection pooling
    ├── migration_manager.py       # Database schema migrations
    ├── schema_manager.py          # Schema validation and management
    └── repositories.py            # Data access layer
```

### Key Components

#### Configuration System (`config.py`)
- **Centralized Settings**: All service configurations in one place
- **Environment-Based Loading**: Automatic environment detection
- **Type Safety**: Dataclass-based configuration with validation
- **Service-Specific Settings**: Dedicated configuration sections per service

#### ISA Client Integration (`isa_client.py`)
- **AI Service Abstraction**: Unified interface for AI model interactions
- **Billing Tracking**: Automatic cost tracking for AI operations
- **Response Processing**: Standardized response handling
- **Error Handling**: Robust error handling and retry logic

#### Security Framework (`security.py`, `auth.py`)
- **Multi-Level Authorization**: LOW, MEDIUM, HIGH security levels
- **JWT Authentication**: Token-based authentication system
- **Audit Logging**: Comprehensive operation tracking
- **User Management**: User registration and profile management

## 🛠️ Tools and Services (`tools/`)

The tools directory implements the MCP protocol and provides service integrations:

```
tools/
├── __init__.py                     # Tools module initialization
├── base_tool.py                   # Base class for all MCP tools
├── base_service.py                # Base class for complex services
│
├── # Individual Tool Files
├── memory_tools.py                # Memory management tools
├── weather_tools.py               # Weather information tools
├── admin_tools.py                 # Administrative tools
├── data_analytics_tools.py        # Data analysis and SQL generation
├── graph_analytics_tools.py       # Graph analytics and Neo4j
├── web_tools.py                   # Web scraping and automation
├── doc_analytics_tools.py         # Document processing and RAG
├── shopify_tools.py               # E-commerce integration
├── image_gen_tools.py             # AI image generation
├── user_tools.py                  # User management
├── event_sourcing_tools.py        # Event sourcing and background tasks
├── autonomous_tools.py            # AI-powered autonomous operations
│
├── core/                          # Tool framework
│   └── tool_selector.py           # AI-powered tool selection
│
└── services/                      # Service implementations
    ├── __init__.py
    ├── data_analytics_service/     # Complete data analytics pipeline
    ├── graph_analytics_service/    # Graph analytics and Neo4j
    ├── web_services/              # Web scraping platform
    ├── doc_analytics_service/     # Document processing
    ├── user_service/              # User management service
    ├── event_sourcing_service/    # Event sourcing system
    └── shopify_service/           # Shopify integration
```

### Service Architecture Pattern

Each major service follows a consistent structure:

```
service_name/
├── __init__.py                    # Service initialization
├── core/                          # Core service logic
│   ├── __init__.py
│   ├── processor.py               # Main processing logic
│   ├── validator.py               # Input validation
│   └── exceptions.py              # Service-specific exceptions
├── services/                      # Sub-services and external integrations
│   ├── __init__.py
│   ├── api_client.py             # External API integration
│   └── data_manager.py           # Data management
├── utils/                         # Service utilities
│   ├── __init__.py
│   ├── helpers.py                # Helper functions
│   └── constants.py              # Service constants
└── adapters/                     # External system adapters
    ├── __init__.py
    └── database_adapter.py       # Database integration
```

## 🚀 Deployment Configuration (`deployment/`)

Deployment configurations for different environments and platforms:

```
deployment/
├── dev/                          # Development environment
│   ├── .env                      # Development environment variables
│   └── requirements.txt          # Development dependencies
├── production/                   # Production environment
│   ├── Dockerfile               # Production container image
│   ├── docker-compose.yml       # Production cluster setup
│   ├── requirements.txt         # Production dependencies
│   └── railway.json             # Railway deployment config
├── staging/                      # Staging environment
│   └── docker-compose.staging.yml
├── test/                         # Testing environment
│   └── docker-compose.test.yml
├── scripts/                      # Deployment automation
│   ├── start.sh                 # Start scripts
│   ├── stop.sh                  # Stop scripts
│   └── restart.sh               # Restart scripts
├── nginx.conf                    # Load balancer configuration
└── prometheus.yml               # Monitoring configuration
```

## 📚 Documentation (`docs/`)

GitBook-structured documentation with comprehensive coverage:

```
docs/
├── README.md                     # Documentation homepage
├── SUMMARY.md                    # GitBook table of contents
├── book.json                     # GitBook configuration
├── build.sh                      # Documentation build script
│
├── getting-started/              # New user onboarding
├── architecture/                 # System architecture docs
├── services/                     # Service-specific documentation
├── user-guide/                   # User tutorials and guides
├── api/                          # API reference documentation
├── deployment/                   # Deployment guides
├── development/                  # Developer resources
└── resources/                    # Additional resources
```

## 🧪 Testing Framework (`tests/`)

Comprehensive testing with multiple test types:

```
tests/
├── unit/                         # Unit tests for individual components
│   ├── data_analytics/           # Data analytics service tests
│   ├── graph_analytics/          # Graph analytics tests
│   ├── web/                      # Web services tests
│   └── ...                       # Other service tests
├── integration/                  # Integration tests
│   ├── data_analytics/           # End-to-end data workflows
│   ├── graph_analytics/          # Graph analytics integration
│   ├── web/                      # Web scraping integration
│   └── isa_model/               # ISA Model integration
├── mcp/                          # MCP protocol compliance tests
└── performance/                  # Performance and load tests
```

## 📦 Resources and Data (`resources/`)

Database schemas, sample data, and MCP resources:

```
resources/
├── base_resource.py              # Base MCP resource class
├── memory_resources.py           # Memory system resources
├── guardrail_resources.py        # Security guardrails
├── resource_selector.py          # AI-powered resource selection
├── dbs/                          # Database files and schemas
│   ├── supabase/                 # Supabase configurations
│   └── neo4j/                    # Neo4j schemas
└── disabled/                     # Disabled/archived resources
```

## 🔧 Configuration and Metadata

### Configuration Files (`config/`)
```
config/
└── sites/                        # Site-specific configurations
    ├── github_com.json           # GitHub integration config
    ├── google_com.json           # Google services config
    └── ...                       # Other site configs
```

### AI Models and Prompts
```
models/
└── model_metadata.json          # AI model specifications

prompts/
├── system_prompts.py             # System-level prompts
├── autonomous_prompts.py         # Autonomous operation prompts
├── rag_prompts.py               # RAG and document prompts
├── shopify_prompts.py           # E-commerce prompts
└── prompt_selector.py           # AI prompt selection
```

## 🔍 Key Design Patterns

### 1. **Service Layer Pattern**
- Clear separation between tools (MCP interface) and services (business logic)
- Tools provide MCP-compliant interfaces while services handle complex operations
- Shared base classes ensure consistency across all services

### 2. **Configuration Management**
- Centralized configuration in `core/config.py`
- Environment-specific loading with validation
- Type-safe configuration access throughout the application

### 3. **AI Integration Pattern**
- Unified ISA client interface for all AI operations
- Automatic billing tracking and cost management
- Standardized response handling and error management

### 4. **Auto-Discovery System**
- Automatic registration of tools, prompts, and resources
- Metadata extraction from docstrings and type annotations
- AI-powered semantic matching for intelligent routing

### 5. **Security by Design**
- Multi-level authorization built into the base classes
- Comprehensive audit logging for compliance
- JWT-based authentication with user management

## 📈 Scalability Considerations

### Horizontal Scaling
- **Stateless Services**: All services are designed to be stateless
- **Load Balancing**: Nginx-based load balancing across multiple instances
- **Database Connection Pooling**: Efficient database resource management

### Performance Optimization
- **Caching Strategies**: Multi-layer caching with Redis
- **Async Processing**: Async/await patterns throughout the codebase
- **Batch Operations**: Efficient batch processing for bulk operations

### Monitoring and Observability
- **Health Checks**: Built-in health monitoring for all services
- **Performance Metrics**: Comprehensive performance tracking
- **Structured Logging**: JSON-based logging for easy analysis

---

**Related Documentation:**
- [Code Standards](code-standards.md) - Coding conventions and style guide
- [Architecture Overview](../architecture/README.md) - High-level system architecture
- [Service Development](service-development.md) - Guide for building new services