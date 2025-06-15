import os 
os.environ["ENV"] = "local"

import pytest
import asyncio
from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.basic.weather_tools import get_weather, get_coolest_cities
from app.capability.registry.tool_graph_manager import SearchWeights
import logging

logger = logging.getLogger(__name__)

async def setup_test_tools():
    """Initialize tools manager and register test tools"""
    try:
        # Add debug logging to check template path
        template_path = "app/services/ai/prompt/templates/tool/query_parser.yaml"
        logger.info(f"Checking for template at: {template_path}")
        if os.path.exists(template_path):
            logger.info("Template file found")
        else:
            logger.error(f"Template file not found at {template_path}")
            # Print the current working directory
            logger.info(f"Current working directory: {os.getcwd()}")
            
        await tools_manager.initialize()
        logger.info("Tools manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tools manager: {str(e)}")
        raise

async def test_capability_search():
    """Test searching tools by capability"""
    try:
        # Setup test data
        await setup_test_tools()
        
        # Test text search
        text_results = await tools_manager.graph_manager.search_by_text(
            query="weather",
            limit=5
        )
        assert len(text_results) > 0, "Text search failed"
        assert any(r.name == "get_weather" for r in text_results)
        
        # Test semantic search with different weights
        queries = [
            (
                "Find a tool that can check the current weather conditions",
                SearchWeights(semantic=0.6, functional=0.2, contextual=0.2)
            ),
            (
                "Tool that takes a location and returns weather data",
                SearchWeights(semantic=0.2, functional=0.6, contextual=0.2)
            ),
            (
                "Real-time weather lookup service",
                SearchWeights(semantic=0.4, functional=0.3, contextual=0.3)
            )
        ]
        
        for query, weights in queries:
            results = await tools_manager.graph_manager.search_by_capability(
                query_text=query,
                weights=weights,
                threshold=0.5,  
                limit=5
            )
            
            # Log results for debugging
            logger.info(f"\nQuery: {query}")
            logger.info(f"Weights: {weights}")
            for r in results:
                logger.info(f"Tool: {r.name}, Score: {r.score}")
            
            assert len(results) > 0, f"No results for query: {query}"
            assert any(r.name in ["get_weather", "get_coolest_cities"] for r in results), \
                   f"Weather tools not found for query: {query}"
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise
    finally:
        await tools_manager.cleanup()

def test_search_weights():
    """Test SearchWeights validation"""
    weights = SearchWeights(
        semantic=0.4,
        functional=0.3,
        contextual=0.3
    )
    assert abs(sum(weights.dict().values()) - 1.0) < 0.001

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_capability_search())
