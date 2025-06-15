import asyncio
from datetime import datetime, timedelta, UTC
from app.services.graphs.kg_graph.builder.loaders import MessageLoader
from app.config.config_manager import config_manager

async def test_message_loader():
    try:
        print("\nInitializing MessageLoader...")
        loader = MessageLoader(
            host="localhost",
            port=27017,
            database="chat_db",
            batch_size=10
        )

        # Test MongoDB connection
        print("\nTesting MongoDB connection...")
        try:
            await loader.client.admin.command('ping')
            print("MongoDB connection successful!")
        except Exception as e:
            print(f"MongoDB connection failed: {str(e)}")
            return

        # Print raw document structure
        print("\nExamining raw MongoDB documents:")
        
        print("\nLooking for conversations...")
        conversation_count = 0
        async for doc in loader.db.conversations.find().limit(3):
            conversation_count += 1
            print(f"\nConversation document {conversation_count}:")
            print(doc)
        
        if conversation_count == 0:
            print("No conversations found in the database!")

        print("\nLooking for messages...")
        message_count = 0
        async for doc in loader.db.messages.find().limit(3):
            message_count += 1
            print(f"\nMessage document {message_count}:")
            print(doc)
            
        if message_count == 0:
            print("No messages found in the database!")

        # Test conversations since yesterday
        print("\nTesting get_conversations_since:")
        yesterday = datetime.now(UTC) - timedelta(days=1)
        print(f"Querying conversations since: {yesterday}")
        
        batch_count = 0
        async for batch in loader.get_conversations_since(yesterday):
            batch_count += 1
            print(f"\nBatch {batch_count}:")
            print(f"Recent Conversations: {len(batch.conversations)}")
            print(f"Recent Messages: {len(batch.messages)}")
            
            if batch.conversations:
                conv = batch.conversations[0]
                print(f"\nSample Conversation:")
                print(f"ID: {conv.conversation_id}")
                print(f"Created at: {conv.created_at}")
                if hasattr(conv, 'participants'):
                    print(f"Participants: {len(conv.participants)}")

        if batch_count == 0:
            print("No conversation batches found!")

    except Exception as e:
        print(f"\nError in test: {str(e)}")
        raise

if __name__ == "__main__":
    print("\nStarting test...")
    asyncio.run(test_message_loader())
    print("\nTest completed!")