# External Services Integration

This module provides a comprehensive framework for integrating external MCP services like MindsDB, Composio, and custom services into your Smart MCP Server.

## 🌟 Features

- **Unified Integration Framework**: Abstract base classes for consistent external service integration
- **MindsDB Integration**: AI analytics, natural language queries, and predictive modeling
- **Composio Integration**: 300+ application integrations (Gmail, Slack, GitHub, etc.)
- **Custom Service Template**: Easily add your own external service integrations
- **Automatic Discovery**: External services are automatically discovered and registered
- **Health Monitoring**: Built-in health checks and reconnection mechanisms
- **Configuration-Driven**: Enable/disable services via configuration files

## 📁 Directory Structure

```
external_services/
├── __init__.py                     # Package initialization
├── README.md                      # This file
├── base_external_service.py       # Abstract base classes
├── service_registry.py            # Service registration and management
├── mindsdb_service/               # MindsDB integration
│   ├── __init__.py
│   └── mindsdb_connector.py
├── composio_service/              # Composio integration
│   ├── __init__.py
│   └── composio_connector.py
├── custom_services/               # Custom service templates
│   └── template_service.py
└── tests/                        # Test suites
    └── test_external_services.py
```

## 🚀 Quick Start

### 1. Enable External Services

Edit `config/external_services/external_services.yaml`:

```yaml
external_services:
  mindsdb:
    enabled: true
    # ... configuration
```

### 2. Set Environment Variables

```bash
# MindsDB
export MINDSDB_LOGIN="your_email@example.com"
export MINDSDB_PASSWORD="your_password"

# Composio
export COMPOSIO_API_KEY="your_composio_api_key"
```

### 3. Install Dependencies

```bash
# For MindsDB integration
pip install mindsdb-sdk

# For Composio integration
pip install composio-core
```

### 4. Start Your MCP Server

The external services will be automatically discovered and integrated when you start your Smart MCP Server.

## 🛠️ Available Services

### MindsDB Service

**Capabilities:**
- Natural language to SQL queries
- Predictive model creation and querying
- Knowledge base creation and search
- Federated data access across 200+ data sources

**Tools:**
- `external_mindsdb_natural_language_query`
- `external_mindsdb_create_predictive_model`
- `external_mindsdb_query_model`
- `external_mindsdb_list_databases`
- `external_mindsdb_execute_sql`

**Example Usage:**
```python
# Natural language query
result = await mcp_client.call_tool(
    "external_mindsdb_natural_language_query",
    {"query": "Show me sales trends for the last quarter"}
)

# Create predictive model
model_result = await mcp_client.call_tool(
    "external_mindsdb_create_predictive_model",
    {
        "model_name": "sales_predictor",
        "target_column": "sales_amount",
        "data_source": "sales_data"
    }
)
```

### Composio Service

**Capabilities:**
- 300+ application integrations
- Gmail, Slack, GitHub, Calendar, CRM integrations
- OAuth authentication handling
- Action execution across multiple apps

**Tools:**
- `external_composio_list_integrations`
- `external_composio_gmail_send_message`
- `external_composio_slack_send_message`
- `external_composio_github_create_issue`
- `external_composio_execute_action`

**Example Usage:**
```python
# Send Gmail
result = await mcp_client.call_tool(
    "external_composio_gmail_send_message",
    {
        "to": "recipient@example.com",
        "subject": "Hello from MCP",
        "body": "This email was sent via Composio integration!"
    }
)

# Create GitHub issue
issue_result = await mcp_client.call_tool(
    "external_composio_github_create_issue",
    {
        "repository": "owner/repo",
        "title": "Bug Report",
        "body": "Description of the issue"
    }
)
```

## 🔧 Creating Custom Services

### 1. Copy the Template

```bash
cp tools/external_services/custom_services/template_service.py \
   tools/external_services/custom_services/my_service.py
```

### 2. Implement Your Service

```python
from ..base_external_service import BaseExternalService, ExternalServiceConfig

class MyCustomService(BaseExternalService):
    async def connect(self) -> bool:
        # Implement connection logic
        pass
    
    async def discover_capabilities(self) -> Dict[str, List[str]]:
        # Define your tools, resources, and prompts
        pass
    
    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        # Implement tool execution
        pass
```

### 3. Register Your Service Type

In `core/external_discovery.py`:

```python
def _register_service_types(self):
    # Add your service type
    self.external_registry.register_service_type("my_service", MyCustomService)
```

### 4. Add Configuration

In `config/external_services/external_services.yaml`:

```yaml
external_services:
  my_custom_service:
    type: "my_service"
    enabled: true
    connection:
      base_url: "https://api.myservice.com"
    auth:
      method: "api_key"
      api_key: "${MY_SERVICE_API_KEY}"
```

## 🔍 Management Tools

The framework provides built-in management tools:

- `external_service_status` - Get status of all external services
- `external_service_health_check` - Perform health checks
- `external_service_reconnect` - Reconnect a service
- `list_external_service_tools` - List all available external tools

## 🧪 Testing

Run the test suite:

```bash
cd tools/external_services
python -m pytest tests/ -v
```

## 🔒 Security Considerations

- **Environment Variables**: Always use environment variables for sensitive information
- **API Keys**: Never commit API keys to version control
- **Authentication**: All services support secure authentication methods
- **Network Security**: Services use HTTPS and proper certificate validation

## 📚 Configuration Reference

### Global Settings

```yaml
global_settings:
  enabled: true                    # Enable/disable all external services
  default_timeout: 30              # Default connection timeout (seconds)
  default_retry_attempts: 3        # Default retry attempts
  health_check_interval: 5         # Health check interval (minutes)
  auto_reconnect: true             # Enable automatic reconnection
  log_level: "INFO"               # Logging level
```

### Service Configuration

```yaml
service_name:
  type: "service_type"             # Service type (mindsdb, composio, custom)
  enabled: true                    # Enable this service
  connection:                      # Connection parameters
    url: "service_url"
    api_version: "v1"
  auth:                           # Authentication configuration
    method: "api_key"              # Auth method (api_key, bearer_token, login)
    api_key: "${ENV_VAR}"         # Environment variable reference
  capabilities:                   # Optional capability filtering
    - "capability_1"
    - "capability_2"
  timeout_seconds: 30             # Connection timeout
  retry_attempts: 3               # Retry attempts
```

## 🤝 Contributing

1. **Add New Service Types**: Implement new external service connectors
2. **Improve Existing Services**: Add more tools and capabilities
3. **Write Tests**: Add comprehensive test coverage
4. **Documentation**: Update documentation for new features

## 📝 License

This external services integration framework is part of the Smart MCP Server project and follows the same licensing terms.