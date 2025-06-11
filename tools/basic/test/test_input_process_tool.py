#!/usr/bin/env python
"""
Test input processing tools
"""

import os
os.environ["ENV"] = "local"

from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.basic.input_process_tool import process_image, process_audio
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from app.services.ai.llm.llm_factory import LLMFactory
from app.config.config_manager import config_manager
import logging
import asyncio

logger = config_manager.get_logger(__name__)

# Test resources
TEST_RESOURCES = {
    'image_url': 'https://images.pexels.com/photos/356844/pexels-photo-356844.jpeg',
    'audio_url': 'https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0011_8k.wav'
}

async def setup_tools_manager():
    """Initialize tools manager with graph support"""
    try:
        # Clear any existing tools first
        tools_manager.clear_tools()
        
        # Initialize manager
        await tools_manager.initialize(test_mode=True)
        
        # Register the input processing tools
        image_tool = process_image
        audio_tool = process_audio
        
        # Add tools to manager
        await tools_manager.add_tools([
            image_tool,
            audio_tool
        ])
        
        logger.info("Tools manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tools manager: {str(e)}")
        raise

async def test_direct_tool_calls():
    """Test tools by calling them directly"""
    logger.info("\n=== Testing Direct Tool Calls ===")
    
    # Test process_image
    logger.info("\nTesting process_image:")
    image_tool = tools_manager.get_tool("process_image")
    image_result = await image_tool.ainvoke(TEST_RESOURCES['image_url'])
    logger.info(f"Image Analysis Result: {image_result}")
    
    # Test process_audio
    logger.info("\nTesting process_audio:")
    audio_tool = tools_manager.get_tool("process_audio")
    audio_result = await audio_tool.ainvoke(TEST_RESOURCES['audio_url'])
    logger.info(f"Audio Transcription Result: {audio_result}")

async def test_tool_node():
    """Test tools through ToolNode"""
    logger.info("\n=== Testing Tool Node ===")
    
    # Create message with tool call for image
    message_with_image_tool = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "process_image",
                "args": {"image_url": TEST_RESOURCES['image_url']},
                "id": "image_tool_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    # Create message with tool call for audio
    message_with_audio_tool = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "process_audio",
                "args": {"audio_url": TEST_RESOURCES['audio_url']},
                "id": "audio_tool_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    # Create tool node
    tool_node = tools_manager.create_tool_node()
    
    # Test image processing
    logger.info("\nTesting tool node with process_image:")
    image_result = await tool_node.ainvoke({"messages": [message_with_image_tool]})
    logger.info(f"Tool node image result: {image_result}")
    
    # Test audio processing
    logger.info("\nTesting tool node with process_audio:")
    audio_result = await tool_node.ainvoke({"messages": [message_with_audio_tool]})
    logger.info(f"Tool node audio result: {audio_result}")

async def test_error_handling():
    """Test error handling"""
    logger.info("\n=== Testing Error Handling ===")
    
    # Create message with invalid image tool call
    message_with_error = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "process_image",
                "args": {},  # Missing required argument
                "id": "error_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    # Create tool node
    tool_node = tools_manager.create_tool_node()
    
    # Invoke tool with error
    logger.info("\nTesting error handling:")
    try:
        result = await tool_node.ainvoke({"messages": [message_with_error]})
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
    assert len(status["registered_tools"]) == 2  # input processing tools
    
    # Verify tool integrity
    issues = await tools_manager.verify_tools_integrity()
    assert len(issues) == 0  # no integrity issues
    
    # Test individual tools
    image_tool = tools_manager.get_tool("process_image")
    audio_tool = tools_manager.get_tool("process_audio")
    
    assert image_tool is not None, "Image tool not found"
    assert audio_tool is not None, "Audio tool not found"
    
    # Verify both tools are registered in graph
    assert image_tool.name in status["registered_tools"]
    assert audio_tool.name in status["registered_tools"]

async def run_tests():
    """Run all tests"""
    try:
        await setup_tools_manager()
        
        # Run tests
        await test_direct_tool_calls()
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
