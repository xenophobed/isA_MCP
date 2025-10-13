# Utils Directory

Utility tools and helper modules for the isA MCP project.

## 📁 Contents

### MCP Client & CLI

- **`mcp_client.py`** - Python client library for interacting with MCP server
  - Provides programmatic access to MCP tools
  - Helper functions for testing
  - SSE response parsing
  - Tool discovery and capabilities

- **`mcp_cli.py`** - Comprehensive command-line interface for MCP
  - Interactive REPL mode
  - Direct command execution
  - Support for prompts, tools, and resources
  - Rich formatting and syntax highlighting
  - See `MCP_CLI_GUIDE.md` for usage

- **`MCP_CLI_GUIDE.md`** - Complete user guide for the MCP CLI
  - Installation instructions
  - Usage examples
  - Command reference
  - Advanced usage patterns

## 🚀 Quick Start

### Using MCP Client in Python

```python
from utils.mcp_client import MCPClient
import asyncio

async def main():
    client = MCPClient()

    # Call a tool
    result = await client.call_tool_and_parse(
        "web_search",
        {"query": "AI trends", "count": 5}
    )
    print(result)

asyncio.run(main())
```

### Using MCP CLI

```bash
# Interactive mode
python utils/mcp_cli.py

# Direct commands
python utils/mcp_cli.py search "web"
python utils/mcp_cli.py tool web_search '{"query": "AI", "count": 3}'
python utils/mcp_cli.py capabilities
```

## 📚 Documentation

See individual file docstrings and `MCP_CLI_GUIDE.md` for detailed documentation.

## 🔗 Related

- Main MCP server: `main.py`
- MCP tools: `tools/`
- MCP resources: `resources/`
- MCP prompts: `prompts/`
