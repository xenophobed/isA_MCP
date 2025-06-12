import os
os.environ["ENV"] = "local"

import asyncio
from app.services.ai.mem.memory.memory_manager import GraphManager
from app.services.ai.mem.configs.base import MemoryConfig

async def test_basic_flow():
    """Test real-world chat scenario"""
    try:
        # Setup
        manager = await GraphManager.create()
        
        user_filters = {"user_id": "test_user_123"}
        
        # Scenario 1: User starts conversation about work
        print("\nScenario 1: Adding work information...")
        messages_1 = [
            {"role": "user", "content": "I work with Sarah on the mobile app project"},
            {"role": "assistant", "content": "That's great! How long have you been working on the mobile app?"}
        ]
        
        results_1 = await manager.add(
            messages=messages_1,
            filters=user_filters,
            memory_ids=["chat_1"]
        )
        print(f"Added work relationships: {results_1}")
        
        # Scenario 2: Later conversation about Sarah
        print("\nScenario 2: Searching for Sarah info...")
        search_results = await manager.search(
            query="What do we know about Sarah?",
            filters=user_filters,
            search_type="entity",
            expand_context=True,
            limit=10
        )
        print(f"Sarah-related information: {search_results}")
        
        # Scenario 3: Adding more context about project
        print("\nScenario 3: Adding project details...")
        messages_2 = [
            {"role": "user", "content": "The mobile app deadline is next month"},
            {"role": "assistant", "content": "I see. And you're working with Sarah to meet this deadline."}
        ]
        
        results_2 = await manager.add(
            messages=messages_2,
            filters=user_filters,
            memory_ids=["chat_1", "chat_2"]
        )
        print(f"Added project details: {results_2}")
        
        # Scenario 4: Searching project context
        print("\nScenario 4: Getting project context...")
        project_results = await manager.search(
            query="Tell me about the mobile app project",
            filters=user_filters,
            expand_context=True
        )
        print(f"Project information: {project_results}")
        
        # Cleanup
        print("\nCleaning up test data...")
        await manager.cleanup(user_filters)
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_basic_flow())