import asyncio
import logging
from app.services.graphs.kg_graph.builder.data_manager import DataManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_data_manager():
    # 1. 创建并初始化 DataManager
    data_manager = DataManager()
    await data_manager.initialize(
        host="localhost",
        port=27017,
        database="chat_db"
    )
    
    # 2. 加载所有数据
    print("\nLoading all data into DataManager...")
    await data_manager.load_all_data()
    
    # 3. 验证数据加载
    print("\nVerifying loaded data:")
    print(f"Total conversations in cache: {len(data_manager.conversations)}")
    print(f"Total messages in cache: {len(data_manager.messages)}")
    
    # 4. 验证会话-消息关系
    conversation_counts = {}
    for conv_id, msg_list in data_manager._conversation_messages.items():
        conversation_counts[conv_id] = len(msg_list)
    
    print("\nMessage distribution across conversations:")
    print(f"Number of conversations with messages: {len(conversation_counts)}")
    if conversation_counts:
        print(f"Average messages per conversation: {sum(conversation_counts.values()) / len(conversation_counts):.2f}")
        print(f"Max messages in a conversation: {max(conversation_counts.values())}")
        print(f"Min messages in a conversation: {min(conversation_counts.values())}")
    
    # 5. 验证用户参与情况
    user_counts = {}
    for user_id, conv_set in data_manager._user_conversations.items():
        user_counts[user_id] = len(conv_set)
    
    print("\nUser participation statistics:")
    print(f"Total unique users: {len(user_counts)}")
    if user_counts:
        print(f"Average conversations per user: {sum(user_counts.values()) / len(user_counts):.2f}")
        print(f"Most active user: {max(user_counts.items(), key=lambda x: x[1])}")

if __name__ == "__main__":
    asyncio.run(test_data_manager())