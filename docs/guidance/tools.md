# Tools

Create and register custom tools with the ISA MCP platform.

## Overview

The platform includes 88+ built-in tools organized by category, with automatic discovery for custom tools.

## Tool Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `general_tools` | System utilities | `get_current_time`, `get_current_date` |
| `intelligent_tools` | AI-powered analysis | `analyze_text`, `generate_summary` |
| `data_tools` | Data operations | `query_data`, `transform_data` |
| `memory_tools` | Memory management | `store_memory`, `recall_memory` |
| `web_tools` | Web interactions | `fetch_url`, `search_web` |
| `plan_tools` | Execution planning | `create_execution_plan` |
| `meta_tools` | Platform introspection | `list_tools`, `get_tool_info` |
| `system_tools` | System operations | `execute_command` |
| `isa_vibe_tools` | Vibe skill tools | Domain-specific workflows |

## Creating Custom Tools

### Step 1: Create Tool File

Create a file ending with `_tools.py` in the `tools/` directory:

```python
# tools/my_custom_tools.py
from datetime import datetime
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

def register_my_custom_tools(mcp: FastMCP):
    """Register custom tools with MCP server."""

    @mcp.tool()
    async def my_custom_tool(
        param1: str,
        param2: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        My custom tool description.

        Detailed explanation of what this tool does and when to use it.

        Args:
            param1: Description of param1
            param2: Optional description of param2

        Returns:
            {"result": "...", "status": "success"}

        Keywords: custom, example, demo
        """
        result = f"Processed: {param1}"
        if param2:
            result += f" with value {param2}"

        return {
            "result": result,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }

    print("Custom tools registered")
```

### Step 2: File Naming Convention

The auto-discovery system requires:

1. **Filename**: Must end with `_tools.py`
2. **Register function**: Must be named `register_{filename}(mcp)`

Examples:
- `weather_tools.py` → `register_weather_tools(mcp)`
- `analytics_tools.py` → `register_analytics_tools(mcp)`

### Step 3: Location

Place your tool file in:
- `tools/` (root level)
- `tools/{category}/` (any subdirectory)

## Using BaseTool Class

For advanced tools with ISA integration:

```python
from tools.base_tool import BaseTool
from mcp.server.fastmcp import Context

class WeatherTool(BaseTool):
    def __init__(self):
        super().__init__()

    def register_tools(self, mcp):
        self.register_tool(
            mcp,
            self.get_weather,
            name="get_weather",
            description="Get weather for a location"
        )

    async def get_weather(
        self,
        location: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        # Report progress
        if ctx:
            await ctx.report_progress(0.5, "Fetching weather...")

        # Implementation
        return {"location": location, "temperature": 72}

def register_weather_tools(mcp):
    tool = WeatherTool()
    tool.register_tools(mcp)
```

## BaseTool Features

| Feature | Description |
|---------|-------------|
| Progress Reporting | `ctx.report_progress(progress, message)` |
| Human-in-Loop | `ctx.elicit()` for user input |
| Billing Integration | Automatic usage tracking |
| Security Checks | Built-in authorization |
| Rate Limiting | Configurable limits |

## Tool Annotations

```python
@mcp.tool(
    name="custom_name",           # Override function name
    description="...",            # Override docstring
    annotations=ToolAnnotations(
        readOnlyHint=True,        # Tool doesn't modify state
        destructiveHint=False,    # Tool is safe
        idempotentHint=True       # Safe to retry
    )
)
async def my_tool():
    pass
```

## Best Practices

1. **Descriptive docstrings** - Include keywords for semantic search
2. **Type hints** - Use for all parameters and return values
3. **Error handling** - Return structured error responses
4. **Logging** - Log important operations
5. **Context parameter** - Accept optional `ctx: Context` for MCP features

## Auto-Discovery Process

1. Server scans `tools/` directory recursively
2. Finds all `*_tools.py` files
3. Imports each module
4. Calls `register_{module_name}(mcp)` function
5. Logs success/failure for each module

## Next Steps

- [Prompts](./prompts) - Create custom prompts
- [Resources](./resources) - Create custom resources
- [Skills](./skills) - Skill-based classification
