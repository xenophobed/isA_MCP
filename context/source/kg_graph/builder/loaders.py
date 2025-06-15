# app/kg/builder/loaders.py
from typing import List, Dict, Any, AsyncIterator, Optional
from datetime import datetime
from app.config.config_manager import config_manager
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

config_manager.set_log_level("INFO")
logger = config_manager.get_logger(__name__)

class Participant(BaseModel):
    user_id: str
    type: str
    joined_at: Optional[datetime] = None
    
class Message(BaseModel):
    message_id: str
    conversation_id: str
    content: Any
    type: str
    sender: Dict[str, str]
    timestamp: datetime
    metadata: Dict = Field(default_factory=dict)

class Conversation(BaseModel):
    conversation_id: str
    inbox_id: str
    title: str
    participants: List[Participant]
    created_at: datetime
    last_active_at: datetime
    status: str
    metadata: Dict = Field(default_factory=dict)

class DataBatch:
    def __init__(self, 
                 batch_id: str,
                 conversations: List[Conversation],
                 messages: List[Message],
                 metadata: Dict[str, Any] = None):
        self.batch_id = batch_id
        self.conversations = conversations
        self.messages = messages
        self.metadata = metadata or {}

class MessageLoader:
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 27017,
                 database: str = "chat_db",
                 batch_size: int = 100):
        self.client = AsyncIOMotorClient(f"mongodb://{host}:{port}")
        self.db = self.client[database]
        self.batch_size = batch_size

    async def get_user_conversations_with_messages(self, user_id: str) -> AsyncIterator[DataBatch]:
        """获取用户的所有会话及其消息"""
        try:
            conversations = []
            cursor = self.db.conversations.find({
                "participants.user_id": user_id
            })
            
            async for doc in cursor:
                try:
                    doc['_id'] = str(doc['_id'])
                    conversation = Conversation(**doc)
                    conversations.append(conversation)
                except Exception as e:
                    logger.error(f"Error processing conversation: {str(e)}")
                    continue

            for i in range(0, len(conversations), self.batch_size):
                batch_conversations = conversations[i:i + self.batch_size]
                conversation_ids = [c.conversation_id for c in batch_conversations]
                
                messages = []
                cursor = self.db.messages.find({
                    "conversation_id": {"$in": conversation_ids}
                }).sort("timestamp", 1)
                
                async for msg_doc in cursor:
                    try:
                        msg_doc['_id'] = str(msg_doc['_id'])
                        message = Message(**msg_doc)
                        messages.append(message)
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        continue

                yield DataBatch(
                    batch_id=f"batch_{i//self.batch_size}",
                    conversations=batch_conversations,
                    messages=messages,
                    metadata={
                        "user_id": user_id,
                        "timestamp": datetime.utcnow(),
                        "total_conversations": len(batch_conversations),
                        "total_messages": len(messages)
                    }
                )

        except Exception as e:
            logger.error(f"Error loading data for user {user_id}: {str(e)}")
            raise

    async def get_all_conversations_with_messages(self) -> AsyncIterator[DataBatch]:
        """获取所有会话及其消息"""
        try:
            conversations = []
            # 获取所有会话，不再过滤特定用户
            cursor = self.db.conversations.find({})
            
            async for doc in cursor:
                try:
                    doc['_id'] = str(doc['_id'])
                    conversation = Conversation(**doc)
                    conversations.append(conversation)
                except Exception as e:
                    logger.error(f"Error processing conversation: {str(e)}")
                    continue

            # 按批次处理会话
            for i in range(0, len(conversations), self.batch_size):
                batch_conversations = conversations[i:i + self.batch_size]
                conversation_ids = [c.conversation_id for c in batch_conversations]
                
                messages = []
                cursor = self.db.messages.find({
                    "conversation_id": {"$in": conversation_ids}
                }).sort("timestamp", 1)
                
                async for msg_doc in cursor:
                    try:
                        msg_doc['_id'] = str(msg_doc['_id'])
                        message = Message(**msg_doc)
                        messages.append(message)
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        continue

                yield DataBatch(
                    batch_id=f"batch_{i//self.batch_size}",
                    conversations=batch_conversations,
                    messages=messages,
                    metadata={
                        "timestamp": datetime.utcnow(),
                        "total_conversations": len(batch_conversations),
                        "total_messages": len(messages)
                    }
                )

        except Exception as e:
            logger.error(f"Error loading all conversations: {str(e)}")
            raise

    async def get_conversations_since(self, timestamp: datetime) -> AsyncIterator[DataBatch]:
        """获取指定时间之后的会话及其消息"""
        try:
            logger.info(f"Querying conversations since {timestamp}")
            conversations = []
            
            # 获取指定时间之后的会话
            query = {
                "last_active_at": {"$gte": timestamp}
            }
            logger.info(f"MongoDB query: {query}")
            
            cursor = self.db.conversations.find(query)
            conversation_count = 0
            
            async for doc in cursor:
                conversation_count += 1
                try:
                    doc['_id'] = str(doc['_id'])
                    conversation = Conversation(**doc)
                    conversations.append(conversation)
                    if conversation_count % 100 == 0:
                        logger.info(f"Processed {conversation_count} conversations")
                except Exception as e:
                    logger.error(f"Error processing conversation document: {str(e)}")
                    continue

            logger.info(f"Found {len(conversations)} conversations since {timestamp}")
            
            # 按批次处理会话
            batch_number = 0
            for i in range(0, len(conversations), self.batch_size):
                batch_number += 1
                logger.info(f"Processing batch {batch_number}")
                
                batch_conversations = conversations[i:i + self.batch_size]
                conversation_ids = [c.conversation_id for c in batch_conversations]
                
                messages = []
                message_query = {
                    "conversation_id": {"$in": conversation_ids},
                    "timestamp": {"$gte": timestamp}
                }
                logger.info(f"Querying messages for batch {batch_number}")
                
                cursor = self.db.messages.find(message_query).sort("timestamp", 1)
                async for msg_doc in cursor:
                    try:
                        msg_doc['_id'] = str(msg_doc['_id'])
                        message = Message(**msg_doc)
                        messages.append(message)
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        continue

                logger.info(f"Batch {batch_number}: Found {len(messages)} messages for {len(batch_conversations)} conversations")
                
                yield DataBatch(
                    batch_id=f"batch_{batch_number}",
                    conversations=batch_conversations,
                    messages=messages,
                    metadata={
                        "timestamp": timestamp,
                        "total_conversations": len(batch_conversations),
                        "total_messages": len(messages)
                    }
                )

        except Exception as e:
            logger.error(f"Error loading conversations since {timestamp}: {str(e)}", exc_info=True)
            raise