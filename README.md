# Modern MCP (Machine Conversation Protocol)

This package provides a modern architecture for using the MCP protocol directly, without relying on LangChain tools as intermediaries.

## Architecture

The MCP architecture consists of the following components:

### 1. Adapters

The adapters module (`app/services/agent/mcp/adapters/`) handles service adapters and protocol translations. It includes:

- `tools_adapter.py`: Converts LangChain tools to MCP servers
- Custom adapters for different tool formats

Example from `tools_adapter.py`:
```python
# Convert a list of LangChain tools to an MCP server
tools_list = [my_tool1, my_tool2]
mcp_server = convert_tools_to_mcp(tools_list)
```

### 2. Capability

The capability module (`app/services/agent/mcp/capability/`) handles tool discovery and capability management. It includes:

- `tool_discovery.py`: Discovers tools from various sources
- Tool matching and capability management

Example from `tool_discovery.py`:
```python
# Discover LangChain tools and register them as MCP servers
tool_sets = ToolDiscovery.discover_langchain_tools(
    "app.services.agent.tools",
    ["basic", "planning", "math"]
)

# Get all capabilities from registered servers
capabilities = await ToolDiscovery.get_all_capabilities()
```

### 3. Execution

The execution module (`app/services/agent/mcp/execution/`) handles tool execution and workflow management. It includes:

- `executor.py`: Executes tools with proper parameter handling
- Workflow orchestration and chaining

Example from `executor.py`:
```python
# Create an executor for a set of tools
executor = ToolExecutor(tools)

# Execute a tool
result = await executor.execute("tool_name", {"param1": "value1"})
```

### 4. Integration

The integration module handles data integration and external service connections. It includes:

- Data format conversion
- External service connections

### 5. Knowledge

The knowledge module handles data retrieval and knowledge management. It includes:

- Data retrieval tools
- Knowledge storage and management

### 6. Registry

The registry module (`app/services/agent/mcp/registry/`) manages MCP server registrations. It includes:

- `registry.py`: Manages server registrations and configurations

Example from `registry.py`:
```python
# Get the global registry instance
registry = get_registry()

# Register a direct server
registry.register_direct_server("server_name", server_instance)

# List all registered servers
servers = registry.list_servers()
```

### 7. Servers

The servers module (`app/services/agent/mcp/servers/`) defines and hosts MCP servers. It includes:

- `fastapi/fastmcp.py`: FastAPI implementation of MCP server
- `weather_server.py`: Example weather server

Example from `weather_server.py`:
```python
# Create server instance
mcp = FastMCP("Weather")

# Register a tool
@mcp.tool()
async def weather(location: str):
    # Implementation
    return {"temperature": 72, "condition": "Sunny"}

# Run the server
mcp.run()
```

### 8. Tools

The tools module (`app/services/agent/mcp/tools/`) contains actual tool implementations. It includes:

- `basic/weather_tools.py`: Example weather tools
- Other tool categories

Example from `weather_tools.py`:
```python
@tool
async def get_weather(location: str):
    # Implementation
    return {"temperature": 72, "condition": "Sunny"}
```

### 9. Client

The client module (`app/services/agent/mcp/client/`) provides clients for connecting to MCP servers. It includes:

- `modern_client.py`: Modern MCP client that directly uses the MCP protocol
- `langchain_mcp_client.py`: LangChain-based MCP client

Example from `modern_client.py`:
```python
# Create client
client = MCPDirectClient()

# Execute a tool
result = await client.aexecute("tool_name", {"param1": "value1"})
```

## Usage Example

See the `modern_example.py` file for a complete usage example:

```python
import asyncio
from app.services.agent.mcp.registry.registry import get_registry
from app.services.agent.mcp.client.modern_client import MCPDirectClient
from app.services.agent.mcp.servers.weather_server import mcp as weather_server

async def main():
    # Set up registry
    registry = get_registry()
    
    # Register server
    registry.register_direct_server("weather", weather_server)
    
    # Create client
    client = MCPDirectClient()
    
    # Execute tool
    result = await client.aexecute("weather", {"location": "New York"})
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Running Tests

To run tests, use the following command:

```bash
pytest app/services/agent/mcp/tests/
``` # isA_MCP
# isA_MCP
