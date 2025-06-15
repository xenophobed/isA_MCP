import asyncio
import logging
from app.capability.source.conv_extractor import ConversationFactExtractor
from app.capability.source.conv_fact_extractor import FactConfidenceScorer
from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.basic.weather_tools import get_weather, get_coolest_cities
import json

logger = logging.getLogger(__name__)

async def test_vector_workflow():
    """Test vector extraction and embedding for weather tools"""
    try:
        # Get tool instances from tools_manager
        weather_tool = tools_manager.get_tool_by_name("get_weather")
        coolest_cities_tool = tools_manager.get_tool_by_name("get_coolest_cities")
        
        # Initialize embedder
        embedder = ToolVectorEmbedder()
        
        logger.info("\n=== Testing Vector Workflow ===\n")
        
        # Test metadata extraction for weather tool
        logger.info("1. Extracting metadata for get_weather tool...")
        weather_metadata = ToolMetadataExtractor.extract_from_tool(weather_tool)
        logger.info("\nExtracted Metadata:")
        logger.info(json.dumps(weather_metadata.dict(), indent=2))
        
        # Verify weather tool functionality
        logger.info("\nVerifying weather tool functionality:")
        sf_weather = weather_tool.invoke("sf")
        logger.info(f"SF Weather: {sf_weather}")
        
        # Test vector embedding for weather tool
        logger.info("\n2. Generating vectors for get_weather tool...")
        weather_vectors = await embedder.generate_vectors(weather_metadata)
        
        logger.info("\nVector Results:")
        for key, vector in weather_vectors.items():
            if key == 'metadata':
                logger.info(f"\nEmbedding Input Texts:")
                for text_key, text in vector.items():
                    logger.info(f"{text_key}: {text}")
            else:
                # Handle vector data - assuming it's a list of floats
                logger.info(f"\n{key}:")
                logger.info(f"Dimension: {len(vector)}")
                logger.info(f"Sample values: {vector[:3]}...")  
        
        # Test metadata extraction for coolest cities tool
        logger.info("\n3. Extracting metadata for get_coolest_cities tool...")
        cities_metadata = ToolMetadataExtractor.extract_from_tool(coolest_cities_tool)
        logger.info("\nExtracted Metadata:")
        logger.info(json.dumps(cities_metadata.dict(), indent=2))
        
        # Verify coolest cities tool functionality
        logger.info("\nVerifying coolest cities tool functionality:")
        coolest = coolest_cities_tool.run({})
        logger.info(f"Coolest cities: {coolest}")
        
        # Test vector embedding for coolest cities tool
        logger.info("\n4. Generating vectors for get_coolest_cities tool...")
        cities_vectors = await embedder.generate_vectors(cities_metadata)
        
        logger.info("\nVector Results:")
        for key, vector in cities_vectors.items():
            if key == 'metadata':
                logger.info(f"\nEmbedding Input Texts:")
                for text_key, text in vector.items():
                    logger.info(f"{text_key}: {text}")
            else:
                # Handle vector data
                logger.info(f"\n{key}:")
                logger.info(f"Dimension: {len(vector)}")
                logger.info(f"Sample values: {vector[:3]}...")
        
        # Compare vector dimensions
        logger.info("\nVector Dimension Comparison:")
        for key in weather_vectors:
            if key != 'metadata':
                weather_dim = len(weather_vectors[key])
                cities_dim = len(cities_vectors[key])
                logger.info(f"{key}: Weather({weather_dim}) vs Cities({cities_dim})")
        
        logger.info("\n=== Test Completed Successfully ===")
        return True
        
    except Exception as e:
        logger.error(f"\nError during testing: {str(e)}")
        raise

def test_error_handling():
    """Test error handling in vector workflow"""
    logger.info("\n=== Testing Error Handling ===")
    
    # Test case 1: None tool
    try:
        logger.info("\nTesting with None tool...")
        ToolMetadataExtractor.extract_from_tool(None)
    except Exception as e:
        logger.info(f"✓ Expected error for None tool: {str(e)}")
    
    # Test case 2: Invalid tool
    try:
        logger.info("\nTesting with invalid tool...")
        class InvalidTool:
            name = "invalid_tool"
        invalid_tool = InvalidTool()
        ToolMetadataExtractor.extract_from_tool(invalid_tool)
    except Exception as e:
        logger.info(f"✓ Expected error for invalid tool: {str(e)}")
    
    # Test case 3: Invalid tool input
    try:
        logger.info("\nTesting with invalid tool input...")
        weather_tool = tools_manager.get_tool_by_name("get_weather")
        weather_tool.invoke(None)
    except Exception as e:
        logger.info(f"✓ Expected error for invalid input: {str(e)}")
    
    # Test case 4: Non-existent tool
    try:
        logger.info("\nTesting with non-existent tool...")
        invalid_tool = tools_manager.get_tool_by_name("non_existent_tool")
        if invalid_tool:
            ToolMetadataExtractor.extract_from_tool(invalid_tool)
    except Exception as e:
        logger.info(f"✓ Expected error for non-existent tool: {str(e)}")
    
    logger.info("\n✓ All error handling tests completed")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run all tests
    asyncio.run(test_vector_workflow())
    test_error_handling()