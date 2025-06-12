import asyncio
from app.s_mem.memory.main import Memory
from app.s_mem.configs.base import MemoryConfig

async def main():
    # Initialize Memory instance
    memory = Memory(MemoryConfig())
    
    # Setup the memory system (required before using)
    await memory.setup()
    
    # Example messages
    messages = [
        {"role": "user", "content": "The weather is sunny today in New York"},
        {"role": "assistant", "content": "That's wonderful! Perfect weather for visiting Central Park"}
    ]
    
    try:
        # Add memory with user_id
        result = await memory.add(
            messages=messages,
            user_id="user_123",  # Required identifier
            metadata={
                "timestamp": "2024-12-05",
                "source": "weather_conversation"
            }
        )
        
        # Print results
        print("Vector Store Results:", result["results"])
        print("Graph Relations:", result["relations"])
        
    except Exception as e:
        print(f"Error occurred: {e}")
    
    finally:
        # Cleanup if needed
        pass

if __name__ == "__main__":
    asyncio.run(main())