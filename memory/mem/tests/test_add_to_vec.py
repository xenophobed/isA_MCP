import asyncio
from app.s_mem.memory.main import Memory
from app.s_mem.configs.base import MemoryConfig

async def test_vector_store():
    # Initialize Memory with async setup
    memory = Memory(MemoryConfig())
    await memory.setup()
    
    # Test Scenario 1: Customer Service
    cs_messages = [
        {"role": "user", "content": "My order #12345 hasn't arrived yet. It's been 5 days."},
        {"role": "assistant", "content": "I understand your concern. Let me check the status for you."},
        {"role": "user", "content": "The tracking shows it's still in transit."},
    ]
    
    cs_metadata = {
        "category": "customer_service",
        "order_id": "12345",
        "priority": "high"
    }
    
    print("\nTesting Customer Service Scenario...")
    try:
        
        # Proceed with vector store test
        cs_result = await memory._add_to_vector_store(cs_messages, cs_metadata, {"user_id": "cs_test_user"})
        print(f"Customer Service Results: {cs_result}")
        
        # Verify the results
        assert cs_result is not None, "Result should not be None"
        if isinstance(cs_result, list):
            for memory_item in cs_result:
                assert "id" in memory_item, "Each memory item should have an ID"
                assert "memory" in memory_item, "Each memory item should have memory content"
                assert "event" in memory_item, "Each memory item should have an event type"
                
    except Exception as e:
        print(f"Error in test: {e}")
        raise
    
if __name__ == "__main__":
    asyncio.run(test_vector_store())