#!/usr/bin/env python
"""
Test context ensure tool
"""

import os
os.environ["ENV"] = "local"

from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.basic.context_ensure_tool import ensure_travel_context
from app.services.ai.tools.plan.intent_analyze_tool import analyze_intention
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from app.services.ai.llm.llm_factory import LLMFactory
from app.config.config_manager import config_manager
import logging
import asyncio

logger = config_manager.get_logger(__name__)

# Test scenarios
TEST_SCENARIOS = [
    {
        "message": "I want to plan a trip to Paris next summer",
        "description": "Basic travel request with destination and time"
    },
    {
        "message": "Plan a luxury vacation for 4 people with a budget of $5000",
        "description": "Travel request with budget and companions"
    },
    {
        "message": "I need a relaxing beach vacation",
        "description": "Travel request with preference only"
    }
]

async def setup_tools_manager():
    """Initialize tools manager with graph support"""
    try:
        # Clear any existing tools first
        tools_manager.clear_tools()
        
        # Initialize manager
        await tools_manager.initialize(test_mode=True)
        
        # Register the tools
        await tools_manager.add_tools([
            ensure_travel_context,
            analyze_intention
        ])
        
        logger.info("Tools manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tools manager: {str(e)}")
        raise

async def test_intent_and_context():
    """Test intent analysis and context collection workflow"""
    logger.info("\n=== Testing Intent and Context Collection ===")
    
    for scenario in TEST_SCENARIOS:
        logger.info(f"\nTesting scenario: {scenario['description']}")
        logger.info(f"Message: {scenario['message']}")
        
        # First analyze intent
        intent_tool = tools_manager.get_tool("analyze_intention")
        intent_result = await intent_tool.ainvoke(scenario['message'])
        logger.info(f"Intent analysis result: {intent_result}")
        
        # Then ensure context
        context_tool = tools_manager.get_tool("ensure_travel_context")
        context_result = context_tool(intent_result)
        logger.info(f"Context collection result: {context_result}")
        
        # Log missing information
        if context_result["needs_human_input"]:
            logger.info("Missing information:")
            for question in context_result["questions"]:
                logger.info(f"- {question}")

async def test_tool_node():
    """Test tools through ToolNode"""
    logger.info("\n=== Testing Tool Node ===")
    
    # Create message with tool calls
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "analyze_intention",
                "args": {"message": TEST_SCENARIOS[0]["message"]},
                "id": "intent_tool_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    # Create tool node
    tool_node = tools_manager.create_tool_node()
    
    # Test intent analysis
    logger.info("\nTesting intent analysis through tool node:")
    intent_result = await tool_node.ainvoke({"messages": [message]})
    logger.info(f"Tool node intent result: {intent_result}")
    
    # Test context collection
    context_message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "ensure_travel_context",
                "args": {
                    "intent_data": intent_result["messages"][0].content,
                    "current_context": {}
                },
                "id": "context_tool_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    logger.info("\nTesting context collection through tool node:")
    context_result = await tool_node.ainvoke({"messages": [context_message]})
    logger.info(f"Tool node context result: {context_result}")

async def test_error_handling():
    """Test error handling"""
    logger.info("\n=== Testing Error Handling ===")
    
    # Test with invalid intent data
    try:
        context_tool = tools_manager.get_tool("ensure_travel_context")
        result = context_tool({"invalid": "data"})
        logger.info(f"Error handling result: {result}")
    except Exception as e:
        logger.error(f"Caught error: {str(e)}")

async def test_tool_registry_health():
    """Test tool registry health checks"""
    logger.info("\n=== Testing Tool Registry Health ===")
    
    # Get registry status
    status = await tools_manager.get_registry_status()
    logger.info(f"Registry status: {status}")
    logger.info(f"Registered tools: {status['registered_tools']}")
    
    assert status["health_status"] == "healthy"
    assert len(status["registered_tools"]) == 2  # context and intent tools
    
    # Verify tool integrity
    issues = await tools_manager.verify_tools_integrity()
    assert len(issues) == 0  # no integrity issues
    
    # Test individual tools
    context_tool = tools_manager.get_tool("ensure_travel_context")
    intent_tool = tools_manager.get_tool("analyze_intention")
    
    assert context_tool is not None, "Context tool not found"
    assert intent_tool is not None, "Intent tool not found"
    
    # Verify both tools are registered in graph
    assert context_tool.name in status["registered_tools"]
    assert intent_tool.name in status["registered_tools"]

async def run_tests():
    """Run all tests"""
    try:
        await setup_tools_manager()
        
        # Run tests
        await test_intent_and_context()
        await test_tool_node()
        await test_error_handling()
        await test_tool_registry_health()
        
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        raise
    finally:
        await tools_manager.cleanup()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_tests()) 