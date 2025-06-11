#!/usr/bin/env python
"""
Test intent analysis tool with human interaction
"""

import os
os.environ["ENV"] = "local"

from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.plan.intent_analyze_tool import analyze_intention
from app.config.config_manager import config_manager
import logging
import asyncio
import json

logger = config_manager.get_logger(__name__)

# Test scenarios
TEST_SCENARIOS = [
    {
        "message": "I want to plan a trip to Paris next summer",
        "description": "Basic travel request with destination and time",
        "user_input": None
    },
    {
        "message": "Plan a luxury vacation for 4 people with a budget of $5000",
        "description": "Travel request with budget and companions",
        "user_input": {
            "destination": "Maldives",
            "travel_dates": "July 2024",
            "preferences": ["beach", "luxury", "relaxation"]
        }
    },
    {
        "message": "I need a relaxing beach vacation",
        "description": "Travel request with preference only",
        "user_input": None
    }
]

async def setup_tools_manager():
    """Initialize tools manager"""
    try:
        await tools_manager.initialize(test_mode=True)
        await tools_manager.add_tools([analyze_intention])
        logger.info("Tools manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tools manager: {str(e)}")
        raise

async def test_intent_analysis():
    """Test intent analysis with human interaction"""
    logger.info("\n=== Testing Intent Analysis with Human Interaction ===")
    
    for scenario in TEST_SCENARIOS:
        logger.info(f"\nTesting scenario: {scenario['description']}")
        logger.info(f"Message: {scenario['message']}")
        
        try:
            # First analysis without user input
            result = await analyze_intention.ainvoke({
                "message": scenario['message'],
                "context": None,
                "user_input": None
            })
            logger.info(f"Initial analysis result: {result}")
            
            # Check if human interaction is needed
            if result["human_interaction"]["needs_human_input"]:
                logger.info("Human interaction needed:")
                logger.info(f"Missing info: {result['human_interaction']['missing_info']}")
                logger.info(f"Questions: {result['human_interaction']['questions']}")
                
                # If we have user input, simulate human response
                if scenario['user_input']:
                    logger.info("\nSimulating human response...")
                    logger.info(f"User input: {scenario['user_input']}")
                    
                    # Second analysis with user input
                    updated_result = await analyze_intention.ainvoke({
                        "message": scenario['message'],
                        "context": None,
                        "user_input": scenario['user_input']
                    })
                    logger.info(f"Updated analysis result: {updated_result}")
                    
                    # Verify human interaction is resolved
                    assert not updated_result["human_interaction"]["needs_human_input"], \
                        "Human interaction should be resolved after user input"
                    
            # Check tool message if human interaction is needed
            if "tool_message" in result:
                logger.info("\nTool message for human interaction:")
                logger.info(f"Type: {result['tool_message'].name}")
                logger.info(f"Content: {result['tool_message'].content}")
                
        except Exception as e:
            logger.error(f"Error in intent analysis: {str(e)}")
            continue

async def test_error_handling():
    """Test error handling"""
    logger.info("\n=== Testing Error Handling ===")
    
    try:
        # Test with invalid input
        result = await analyze_intention.ainvoke({
            "message": "",
            "context": None,
            "user_input": {"invalid": "data"}
        })
        logger.info(f"Error handling result: {result}")
    except Exception as e:
        logger.error(f"Caught error: {str(e)}")

async def test_tool_registry_health():
    """Test tool registry health"""
    logger.info("\n=== Testing Tool Registry Health ===")
    
    # Get registry status
    status = await tools_manager.get_registry_status()
    logger.info(f"Registry status: {status}")
    
    # Verify tool is registered
    assert "analyze_intention" in status["registered_tools"], \
        "Intent analysis tool should be registered"
    
    # Verify tool integrity
    issues = await tools_manager.verify_tools_integrity()
    assert len(issues) == 0, "No integrity issues should be found"

async def run_tests():
    """Run all tests"""
    try:
        await setup_tools_manager()
        
        # Run tests
        await test_intent_analysis()
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
