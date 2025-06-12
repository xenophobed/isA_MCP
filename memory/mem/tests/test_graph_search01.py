import asyncio
from app.services.ai.mem.memory.memory_manager import GraphManager
from app.services.ai.mem.configs.base import MemoryConfig

async def test_basic_flow():
    """Test real-world chat scenario"""
    try:
        # Setup
        manager = await GraphManager.create()
        
        user_filters = {"user_id": "test_user"}
        
        # Scenario 3: Adding more context about project
        print("\nScenario 3: Adding project details...")
        messages_2 = [
            {"role": "user", "content": "has my package been delivered?"},
            {"role": "assistant", "content": "Yes, package 1ZC23A570442742030 was delivered by UPS to Port Saint Lucie"}
        ]
        
        results_2 = await manager.add(
            messages=messages_2,
            filters=user_filters,
            memory_ids=["test_user"]
        )
        print(f"Added project details: {results_2}")
        
        # Scenario 4: Searching project context
        print("\nScenario 4: Getting project context...")
        project_results = await manager.search(
            query="has my package been delivered?",
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