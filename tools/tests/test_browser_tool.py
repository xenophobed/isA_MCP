import os
import asyncio
import logging
from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.basic.browser_tool import browser_tool

# Set test environment
os.environ["ENV"] = "local"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_tools_manager():
    """Initialize tools manager"""
    await tools_manager.initialize(test_mode=True)
    return tools_manager

async def test_photoprism_docs():
    """Test browser tool with PhotoPrism documentation"""
    try:
        # Setup
        logger.info("Initializing tools manager...")
        await setup_tools_manager()
        
        # Test tasks
        tasks = [
            "Go to https://docs.photoprism.dev/ and get the main page title",
            "Find and extract the latest version number from the documentation",
            "Get the list of main features from the homepage",
            "Find the installation instructions section"
        ]
        
        for i, task in enumerate(tasks, 1):
            logger.info(f"\n=== Task {i}: {task} ===")
            try:
                result = await browser_tool.ainvoke(task)
                
                # Print results
                print(f"\nResult type: {type(result)}")
                print(f"Content:\n{result.get('content', 'No content')}")
                
                if result.get('gif_path'):
                    print(f"GIF path: {result['gif_path']}")
                    
            except Exception as e:
                logger.error(f"Error in task {i}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
    finally:
        logger.info("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(test_photoprism_docs())
