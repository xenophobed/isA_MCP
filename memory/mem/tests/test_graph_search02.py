import os
os.environ["ENV"] = "local"

import asyncio
from app.services.ai.mem.memory.memory_manager import GraphManager
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_memory_scenarios():
    """Test different memory scenarios"""
    try:
        # Setup
        manager = await GraphManager.create()
        user_filters = {"user_id": "test_user02"}
        
        # 设置用户身份
        await manager.add_user_identity(
            user_id="test_user02",
            primary_name="John",
            aliases=["test_user02"]
        )
        
        # Scenario 1: Recent conversation
        print("\nScenario 1: Adding recent conversation...")
        messages_1 = [
            {"role": "user", "content": "My name is John and I live in New York"},
            {"role": "assistant", "content": "Nice to meet you John! I'll remember that you live in New York."}
        ]
        
        results_1 = await manager.add(
            messages=messages_1,
            filters=user_filters,
            memory_ids=["conversation_1"]
        )
        print(f"Added conversation: {results_1}")
        
        # Scenario 2: Past event
        print("\nScenario 2: Adding past event...")
        messages_2 = [
            {"role": "user", "content": "I graduated from Columbia University in 2020"},
            {"role": "assistant", "content": "I understand that you graduated from Columbia University in 2020."}
        ]
        
        results_2 = await manager.add(
            messages=messages_2,
            filters=user_filters,
            memory_ids=["conversation_2"]
        )
        print(f"Added past event: {results_2}")
        
        # Scenario 3: Search about person
        print("\nScenario 3: Searching person info...")
        search_results = await manager.search(
            query="Tell me about John", 
            filters=user_filters,
            expand_context=True
        )
        print(f"Person information: {search_results}")
        
        # Scenario 4: Search about location
        print("\nScenario 4: Searching location info...")
        location_results = await manager.search(
            query="What do we know about New York?",
            filters=user_filters,
            expand_context=True
        )
        print(f"Location information: {location_results}")
        
        # Scenario 5: Work info
        print("\nScenario 5: Adding related information...")
        messages_3 = [
            {"role": "user", "content": "I work as a software engineer at Tech Corp in New York"},
            {"role": "assistant", "content": "I see that you work as a software engineer at Tech Corp in New York."}
        ]
        
        results_3 = await manager.add(
            messages=messages_3,
            filters=user_filters,
            memory_ids=["conversation_3"]
        )
        print(f"Added work info: {results_3}")
        
        # Scenario 6: Complex search
        print("\nScenario 6: Complex search...")
        complex_results = await manager.search(
            query="What do we know about John's education and work?",
            filters=user_filters,
            expand_context=True
        )
        print(f"Complex search results: {complex_results}")
        
        # Cleanup
        print("\nCleaning up test data...")
        await manager.cleanup(user_filters)
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_memory_scenarios())
