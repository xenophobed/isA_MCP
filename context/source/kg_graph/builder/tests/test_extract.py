import asyncio
from datetime import datetime
from typing import List
from pydantic import BaseModel

# Import your extractor
from app.services.graphs.kg_graph.builder.extractor import KnowledgeExtractor

# Create a simple Message class to mimic your actual message structure
class TestMessage(BaseModel):
    conversation_id: str
    content: str
    timestamp: datetime
    sender: dict

async def test_extractor():
    # Create test messages
    messages = [
        TestMessage(
            conversation_id="test_conv_123",
            content="我想买一台新的笔记本电脑",
            timestamp=datetime(2024, 1, 1, 10, 0),
            sender={"user_id": "user1"}
        ),
        TestMessage(
            conversation_id="test_conv_123",
            content="我们有最新的MacBook Pro，性能很好",
            timestamp=datetime(2024, 1, 1, 10, 1),
            sender={"user_id": "agent1"}
        ),
        TestMessage(
            conversation_id="test_conv_123",
            content="价格是多少？",
            timestamp=datetime(2024, 1, 1, 10, 2),
            sender={"user_id": "user1"}
        ),
    ]

    # Initialize extractor
    extractor = KnowledgeExtractor()
    
    # Process conversation
    try:
        result = await extractor.process_conversation(messages)
        print("\nExtracted Knowledge:")
        print("-------------------")
        for fact in result["atomic_facts"]:
            print(f"\nKey Elements: {fact['key_elements']}")
            print(f"Atomic Fact: {fact['atomic_fact']}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_extractor())