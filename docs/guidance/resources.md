# Resources

Create and register custom resources with the ISA MCP platform.

## Overview

Resources are read-only data sources accessible via URI patterns. The platform includes 9 built-in resource types.

## Resource Types

| Resource | URI Pattern | Description |
|----------|-------------|-------------|
| Data Analytics | `analytics://...` | Analytics data access |
| Digital | `digital://...` | Digital content |
| Graph Knowledge | `graph://...` | Knowledge graph data |
| Guardrail | `guardrail://...` | Safety/policy resources |
| Process | `process://...` | Process definitions |
| Skill | `skill://...` | Skill definitions |
| Vibe Skill | `vibe://...` | Vibe skill workflows |
| Symbolic Model | `model://...` | Model definitions |

## Creating Custom Resources

### Simple Pattern

```python
# resources/my_resources.py
from mcp.server.fastmcp import FastMCP
from datetime import datetime

def register_my_resources(mcp: FastMCP):
    """Register custom resources."""

    @mcp.resource("config://settings/{key}")
    async def get_config(key: str) -> str:
        """
        Get configuration value by key.

        Returns configuration data for the specified key.
        """
        configs = {
            "app_name": "ISA Platform",
            "version": "1.0.0",
            "environment": "production"
        }

        if key in configs:
            return f"""# Configuration: {key}

**Value**: {configs[key]}
**Retrieved**: {datetime.now().isoformat()}
"""
        return f"# Configuration Not Found: {key}"

    @mcp.resource("status://health")
    async def get_health_status() -> str:
        """Get system health status."""
        return """# System Health

**Status**: Healthy
**Uptime**: 99.9%
**Last Check**: Now
"""

    print("Custom resources registered")
```

### Using BaseResource Class

For advanced resources with security and formatting:

```python
from resources.base_resource import BaseResource
from core.security import SecurityLevel

class DataResources(BaseResource):
    def __init__(self):
        super().__init__()

    def register_all_resources(self, mcp):
        # Low security - public data
        self.register_resource(
            mcp,
            "data://public/{dataset}",
            self.get_public_data,
            security_level=SecurityLevel.LOW
        )

        # High security - sensitive data
        self.register_resource(
            mcp,
            "data://private/{dataset}",
            self.get_private_data,
            security_level=SecurityLevel.HIGH
        )

    async def get_public_data(self, dataset: str) -> str:
        data = await self.fetch_dataset(dataset)
        return self.create_success_response(data, f"data://public/{dataset}")

    async def get_private_data(self, dataset: str) -> str:
        # Security check applied automatically
        data = await self.fetch_secure_dataset(dataset)
        return self.create_success_response(data)

    async def fetch_dataset(self, name: str) -> dict:
        return {"dataset": name, "records": 100}

    async def fetch_secure_dataset(self, name: str) -> dict:
        return {"dataset": name, "records": 50, "secure": True}

def register_data_resources(mcp):
    resources = DataResources()
    resources.register_all_resources(mcp)
```

## URI Patterns

Resources use URI templates with path parameters:

| Pattern | Example | Parameters |
|---------|---------|------------|
| `type://fixed` | `status://health` | None |
| `type://{param}` | `user://{id}` | `id` |
| `type://{a}/{b}` | `data://{category}/{id}` | `a`, `b` |

## BaseResource Features

### Response Helpers

```python
# Success response
return self.create_success_response(
    data={"key": "value"},
    uri="resource://uri"
)

# Error response
return self.create_error_response(
    uri="resource://uri",
    error_message="Something went wrong"
)

# Not found response
return self.create_not_found_response(
    uri="resource://uri",
    resource_type="dataset"
)
```

### Security Levels

```python
from core.security import SecurityLevel

# Available levels
SecurityLevel.LOW      # Public access
SecurityLevel.MEDIUM   # Authenticated users
SecurityLevel.HIGH     # Authorized users only
SecurityLevel.CRITICAL # Admin only
```

## Decorator Pattern

Quick resource definition:

```python
from resources.base_resource import simple_resource
from core.security import SecurityLevel

@simple_resource("cache://data/{key}", SecurityLevel.LOW)
async def get_cached_data(key: str) -> str:
    return f"Cached value for {key}"
```

## File Structure

```
resources/
├── base_resource.py          # Base class
├── data_analytics_resource.py
├── digital_resource.py
├── graph_knowledge_resources.py
├── guardrail_resources.py
├── process_resource.py
├── skill_resources.py
├── vibe_skill_resources.py
└── symbolic_model_resources.py
```

## Resource Response Formats

### Markdown (Recommended)

```python
async def get_report(id: str) -> str:
    return f"""# Report: {id}

## Summary
This is the report summary.

## Details
- Item 1
- Item 2

## Metadata
**Generated**: {datetime.now().isoformat()}
"""
```

### JSON

```python
async def get_data(id: str) -> str:
    import json
    return json.dumps({
        "id": id,
        "data": {"key": "value"}
    }, indent=2)
```

## Best Practices

1. **URI design** - Use clear, hierarchical patterns
2. **Security levels** - Apply appropriate access controls
3. **Response format** - Use markdown for human-readable, JSON for structured
4. **Error handling** - Use helper methods for consistent errors
5. **Documentation** - Include docstrings for discovery

## Accessing Resources

```python
# Client code
result = await client.read_resource("config://settings/app_name")
print(result)
```

## Next Steps

- [Tools](./tools) - Create custom tools
- [Prompts](./prompts) - Create custom prompts
- [Skills](./skills) - Skill-based workflows
