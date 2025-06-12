import os
os.environ["ENV"] = "local"

import asyncio
from app.services.ai.mem.memory.memory_manager import GraphManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_tracking_flow():
    """Test real-world tracking scenario"""
    try:
        # Setup
        manager = await GraphManager.create()
        user_filters = {"user_id": "test_user"}
        
        # Scenario 1: Store tracking info
        print("\nScenario 1: Adding tracking information...")
        messages_1 = [
            {"role": "user", "content": "Track my package 1ZC23A570442742030"},
            {"role": "assistant", "content": "Your package 1ZC23A570442742030 was delivered to Port Saint Lucie, Florida on 2024-08-23"}
        ]
        
        results_1 = await manager.add(
            messages=messages_1,
            filters=user_filters,
            memory_ids=["test_user"]  
        )
        print(f"Added tracking info: {results_1}")
        
        # Wait a bit to ensure storage is complete
        await asyncio.sleep(2)
        
        # Scenario 2: Search for tracking info
        print("\nScenario 2: Searching tracking info...")
        search_results = await manager.search(
            query="1ZC23A570442742030", 
            filters=user_filters,
            expand_context=True
        )
        print(f"Tracking information: {search_results}")
        
        # Scenario 3: Add delivery update
        print("\nScenario 3: Adding delivery update...")
        messages_2 = [
            {"role": "user", "content": "Any updates on 1ZC23A570442742030?"},
            {"role": "assistant", "content": "Yes, package 1ZC23A570442742030 was delivered by UPS to Port Saint Lucie"}
        ]
        
        results_2 = await manager.add(
            messages=messages_2,
            filters=user_filters,
            memory_ids=["test_user"],
        )
        print(f"Added update: {results_2}")
        
        # Scenario 4: Final status check
        print("\nScenario 4: Final status check...")
        final_results = await manager.search(
            query="1ZC23A570442742030?",
            filters=user_filters,
            expand_context=True
        )
        print(f"Final status: {final_results}")
        
        # Cleanup
        print("\nCleaning up test data...")
        await manager.cleanup(user_filters)
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_tracking_flow())