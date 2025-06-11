import os 
os.environ["ENV"] = "local"

from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.basic.rag_tools import vector_search
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
import logging
import asyncio

logger = logging.getLogger(__name__)

async def setup_tools_manager():
    """Initialize tools manager with graph support"""
    try:
        await tools_manager.initialize()
        logger.info("Tools manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tools manager: {str(e)}")
        raise

async def test_direct_tool_calls():
    """Test tools by calling them directly"""
    print("\n=== Testing Direct Tool Calls ===")
    
    # Test vector_search
    print("\nTesting vector_search:")
    vector_tool = tools_manager.get_tool_by_name("vector_search")
    results = vector_tool.invoke({"query": "What are the shipping requirements?"})
    print(f"Search Results: {results}")

async def test_tool_node():
    """Test tools through ToolNode"""
    print("\n=== Testing Tool Node ===")
    
    # Create message with tool call
    message_with_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "vector_search",
                "args": {
                    "query": "What are the shipping requirements?",
                    "collection_name": "tp_product"
                },
                "id": "tool_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    # Create tool node
    tool_node = tools_manager.create_tool_node(["vector_search"])
    
    # Invoke tool
    print("\nTesting tool node with vector_search:")
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
                "name": "vector_search",
                "args": {},  # Missing required argument
                "id": "error_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    # Create tool node
    tool_node = tools_manager.create_tool_node(["vector_search"])
    
    # Invoke tool with error
    print("\nTesting error handling:")
    try:
        result = tool_node.invoke({"messages": [message_with_error]})
        print(f"Error handling result: {result}")
    except Exception as e:
        print(f"Caught error: {str(e)}")

async def test_tool_registry_health():
    """Test tool registry health checks"""
    # Get registry status
    status = await tools_manager.get_registry_status()
    assert status["health_status"] == "healthy"
    assert len(status["registered_tools"]) >= 1  # at least vector_search tool
    
    # Verify tool integrity
    issues = await tools_manager.verify_tools_integrity()
    assert len(issues) == 0  # no integrity issues
    
    # Test vector search tool
    vector_tool = tools_manager.get_tool_by_name("vector_search")
    assert vector_tool is not None, "Vector search tool not found"
    
    # Verify tool is registered in graph
    assert vector_tool.name in status["registered_tools"]

async def run_tests():
    """Run all tests"""
    try:
        await setup_tools_manager()
        
        # Run tests
        await test_direct_tool_calls()
        await test_tool_node()
        await test_error_handling()
        await test_tool_registry_health()
        
        print("\n✅ RAG tools test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {str(e)}")
        raise
    finally:
        await tools_manager.cleanup()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(run_tests())
