import asyncio
import logging
import pytest
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import uvicorn
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-tools-mgt")

# Create MCP server
mcp = FastMCP("Test Tools Service")

# 1. Tool Creation and Registration
@mcp.tool(name="calculate")
async def calculate(operation: str, a: float, b: float) -> float:
    """Perform basic arithmetic operations.
    
    Args:
        operation: The operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number
        
    Returns:
        Result of the operation
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else "Cannot divide by zero"
    }
    
    if operation not in operations:
        return f"Invalid operation: {operation}"
        
    return operations[operation](a, b)

@mcp.tool(name="get_weather")
async def get_weather(location: str) -> Dict[str, Any]:
    """Get weather information for a location.
    
    Args:
        location: City name or location
        
    Returns:
        Weather information including temperature and condition
    """
    # Simulated weather data
    weather_data = {
        "New York": {"temperature": 72, "condition": "Sunny"},
        "London": {"temperature": 65, "condition": "Cloudy"},
        "Tokyo": {"temperature": 80, "condition": "Rainy"}
    }
    
    return weather_data.get(location, {"temperature": 70, "condition": "Unknown"})

# 2. Tool Discovery Test
async def test_tool_discovery():
    """Test discovering tools from the MCP server."""
    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            
            # Get list of tools
            tools_result = await session.list_tools()
            tools = tools_result.tools if hasattr(tools_result, "tools") else []
            
            # Verify tools are discovered
            assert len(tools) > 0, "No tools discovered"
            
            # Print discovered tools
            logger.info("Discovered tools:")
            for tool in tools:
                logger.info(f"- {tool.name}: {tool.description}")
                
            return tools

# 3. Tool Execution Test
async def test_tool_execution():
    """Test executing tools through the MCP server."""
    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            
            # Test calculate tool
            calc_result = await session.call_tool("calculate", {
                "operation": "add",
                "a": 5,
                "b": 3
            })
            assert calc_result == 8, f"Calculate tool failed: {calc_result}"
            
            # Test weather tool
            weather_result = await session.call_tool("get_weather", {
                "location": "New York"
            })
            assert isinstance(weather_result, dict), f"Weather tool failed: {weather_result}"
            assert "temperature" in weather_result, "Weather result missing temperature"
            
            return {
                "calculate": calc_result,
                "weather": weather_result
            }

# 4. Error Handling Test
async def test_error_handling():
    """Test error handling in tool execution."""
    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            
            # Test invalid operation
            try:
                await session.call_tool("calculate", {
                    "operation": "invalid",
                    "a": 5,
                    "b": 3
                })
            except Exception as e:
                logger.info(f"Expected error for invalid operation: {str(e)}")
            
            # Test division by zero
            try:
                await session.call_tool("calculate", {
                    "operation": "divide",
                    "a": 5,
                    "b": 0
                })
            except Exception as e:
                logger.info(f"Expected error for division by zero: {str(e)}")

@asynccontextmanager
async def run_server():
    """Run the MCP server in a separate process."""
    config = uvicorn.Config(mcp.app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    
    # Start server in background
    server_task = asyncio.create_task(server.serve())
    
    try:
        # Wait for server to start
        await asyncio.sleep(2)
        yield
    finally:
        # Cleanup
        server.should_exit = True
        await server_task

# Main test function
async def run_tests():
    """Run all tests."""
    async with run_server():
        try:
            # Run tests
            logger.info("Testing tool discovery...")
            tools = await test_tool_discovery()
            
            logger.info("Testing tool execution...")
            results = await test_tool_execution()
            
            logger.info("Testing error handling...")
            await test_error_handling()
            
            # Print results
            logger.info("\nTest Results:")
            logger.info(f"Discovered {len(tools)} tools")
            logger.info(f"Tool execution results: {results}")
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(run_tests())
