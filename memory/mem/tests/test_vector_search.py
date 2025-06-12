import asyncio
from app.s_mem.memory.main import Memory
from app.s_mem.configs.base import MemoryConfig

async def test_vector_search():
    config = MemoryConfig(api_version="v1.1")
    memory = None
    
    try:
        # Initialize and setup memory
        memory = Memory(config)
        await memory.setup()
        
        # First add some test data
        test_messages = [
            {"role": "user", "content": "The weather is sunny today in New York"},
            {"role": "assistant", "content": "That's wonderful! Perfect weather for visiting Central Park"}
        ]
        
        # Add test memory
        await memory.add(
            messages=test_messages,
            user_id="test_user_123",
            metadata={"source": "test_conversation"}
        )
        
        # Test vector search
        filters = {"user_id": "test_user_123"}
        search_query = "weather in New York"
        
        # Perform vector search
        results = await memory._search_vector_store(
            query=search_query,
            filters=filters,
            limit=5
        )
        
        # Print results
        print("\nSearch Results:")
        print(f"Query: '{search_query}'")
        print("-" * 50)
        
        if not results:
            print("No results found")
            return
            
        for result in results:
            print(f"Score: {result.get('score', 'N/A')}")
            print(f"Memory: {result.get('memory', 'N/A')}")
            if 'metadata' in result:
                print(f"Metadata: {result['metadata']}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        if memory:
            await memory.cleanup()

if __name__ == "__main__":
    asyncio.run(test_vector_search())