import os 
os.environ["ENV"] = "local"

from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.basic.weather_tools import get_weather, get_coolest_cities
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from app.services.ai.llm.llm_factory import LLMFactory
from app.config.config_manager import config_manager
import logging
import asyncio

logger = logging.getLogger(__name__)

async def setup_tools_manager():
    """Initialize tools manager with graph support"""
    try:
        # Clear any existing tools first
        tools_manager.clear_tools()
        
        # Initialize manager
        await tools_manager.initialize(test_mode=True)
        
        # Register the weather tools
        weather_tool = get_weather
        coolest_cities_tool = get_coolest_cities
        
        # Add tools to manager
        await tools_manager.add_tools([
            weather_tool,
            coolest_cities_tool
        ])
        
        logger.info("Tools manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tools manager: {str(e)}")
        raise

async def test_direct_tool_calls():
    """Test tools by calling them directly"""
    print("\n=== Testing Direct Tool Calls ===")
    
    # Test get_weather
    print("\nTesting get_weather:")
    weather_tool = tools_manager.get_tool("get_weather")
    sf_weather = weather_tool.invoke("sf")
    print(f"SF Weather: {sf_weather}")
    
    nyc_weather = weather_tool.invoke("nyc")
    print(f"NYC Weather: {nyc_weather}")

async def test_tool_node():
    """Test tools through ToolNode"""
    print("\n=== Testing Tool Node ===")
    
    # Create message with tool call
    message_with_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_weather",
                "args": {"location": "sf"},
                "id": "tool_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    # Create tool node
    tool_node = tools_manager.create_tool_node()
    
    # Invoke tool
    print("\nTesting tool node with get_weather:")
    result = tool_node.invoke({"messages": [message_with_tool_call]})
    print(f"Tool node result: {result}")

async def test_error_handling():
    """Test error handling"""
    print("\n=== Testing Error Handling ===")
    
    # Create message with invalid tool call
    message_with_error = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_weather",
                "args": {},  # Missing required argument
                "id": "error_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    # Create tool node
    tool_node = tools_manager.create_tool_node()
    
    # Invoke tool with error
    print("\nTesting error handling:")
    try:
        result = tool_node.invoke({"messages": [message_with_error]})
        print(f"Error handling result: {result}")
    except Exception as e:
        print(f"Caught error: {str(e)}")

async def test_tool_registry_health():
    """Test tool registry health checks"""
    print("\n=== Testing Tool Registry Health ===")
    # Get registry status
    status = await tools_manager.get_registry_status()
    logger.info(f"Registry status: {status}")
    logger.info(f"Registered tools: {status['registered_tools']}")
    
    assert status["health_status"] == "healthy"
    assert len(status["registered_tools"]) == 2  # weather tools
    
    # Verify tool integrity
    issues = await tools_manager.verify_tools_integrity()
    assert len(issues) == 0  # no integrity issues
    
    # Test individual tools
    weather_tool = tools_manager.get_tool("get_weather")
    coolest_cities_tool = tools_manager.get_tool("get_coolest_cities")
    
    assert weather_tool is not None, "Weather tool not found"
    assert coolest_cities_tool is not None, "Coolest cities tool not found"
    
    # Verify both tools are registered in graph
    assert weather_tool.name in status["registered_tools"]
    assert coolest_cities_tool.name in status["registered_tools"]

async def run_tests():
    """Run all tests"""
    try:
        await setup_tools_manager()
        
        # Run tests
        await test_direct_tool_calls()
        await test_tool_node()
        await test_error_handling()
        await test_tool_registry_health()  # Add health check test
        
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        raise
    finally:
        await tools_manager.cleanup()  # Use new cleanup method

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_tests())