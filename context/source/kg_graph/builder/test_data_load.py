import asyncio
import logging
from app.graphs.kg_graph.builder.loaders import MessageLoader  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_loader():
    # 创建 loader 实例
    loader = MessageLoader(
        host="localhost",
        port=27017,
        database="chat_db"
    )
    
    # 统计总数
    total_conversations = 0
    total_messages = 0
    sender_types = set()
    
    # 获取并打印所有数据
    print("\nLoading all conversations and messages...")
    async for batch in loader.get_all_conversations_with_messages():
        total_conversations += len(batch.conversations)
        total_messages += len(batch.messages)
        
        # 收集所有发送者类型
        for msg in batch.messages:
            sender_types.add(msg.sender.get('type', 'unknown'))
        
        print(f"\nBatch {batch.batch_id}:")
        print(f"  Conversations in batch: {len(batch.conversations)}")
        print(f"  Messages in batch: {len(batch.messages)}")
        
        # 打印会话示例
        if batch.conversations:
            conv = batch.conversations[0]
            print(f"\n  Sample conversation:")
            print(f"    ID: {conv.conversation_id}")
            print(f"    Title: {conv.title}")
            print(f"    Participants: {len(conv.participants)}")
        
        # 打印消息示例
        if batch.messages:
            msg = batch.messages[0]
            print(f"\n  Sample message:")
            print(f"    Sender type: {msg.sender.get('type')}")
            print(f"    Content: {msg.content[:100]}...")

    # 打印统计信息
    print("\nFinal Statistics:")
    print(f"Total conversations: {total_conversations}")
    print(f"Total messages: {total_messages}")
    print(f"Sender types found: {sorted(sender_types)}")

if __name__ == "__main__":
    asyncio.run(test_loader())