# External Services Configuration

This directory contains configuration files for external MCP service integrations.

## Configuration Files

### external_services.yaml
Main configuration file for all external services including:
- **MindsDB**: AI analytics and predictive modeling service
- **Composio**: 300+ application integration service  
- **Custom Services**: Template for custom external service integrations

## Environment Variables

Set the following environment variables for service authentication:

```bash
# MindsDB Authentication
export MINDSDB_LOGIN="your_email@example.com"
export MINDSDB_PASSWORD="your_password"
# OR
export MINDSDB_API_KEY="your_api_key"

# Composio Authentication  
export COMPOSIO_API_KEY="your_composio_api_key"

# Custom Service Authentication
export CUSTOM_API_TOKEN="your_custom_token"
```

## Service Types

### mindsdb
- Connects to MindsDB cloud or local instance
- Provides AI analytics, natural language queries, predictive modeling
- Supports both login and API key authentication

### composio  
- Connects to Composio's 300+ app integration platform
- Provides pre-built integrations for Gmail, Slack, GitHub, etc.
- Requires API key authentication

### custom
- Template for custom external service integrations
- Supports various authentication methods
- Configurable capabilities and connection parameters

## Enabling Services

To enable a service, set `enabled: true` in the configuration file:

```yaml
external_services:
  mindsdb:
    enabled: true  # Enable MindsDB integration
```

## Adding New Services

1. Create a new service configuration block in `external_services.yaml`
2. Implement the service connector class in `tools/external_services/`
3. Register the service type in the system during initialization

## Security

- Never commit credentials directly to configuration files
- Use environment variables for sensitive information
- Keep API keys and passwords secure
- Consider using encrypted configuration files for production