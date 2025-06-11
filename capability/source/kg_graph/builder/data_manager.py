from typing import Dict, List, Set, Optional
from collections import defaultdict
from datetime import datetime
from app.config.config_manager import config_manager
from .loaders import Message, Conversation, MessageLoader, DataBatch

config_manager.set_log_level("INFO")
logger = config_manager.get_logger(__name__)

class DataManager:
    """数据管理器: 负责数据的加载、缓存和提供访问接口"""
    
    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
        self._messages: Dict[str, Message] = {}
        self._conversation_messages: Dict[str, List[str]] = defaultdict(list)
        self._user_conversations: Dict[str, Set[str]] = defaultdict(set)
        self._loaded_batches: Set[str] = set()
        self.loader: Optional[MessageLoader] = None
        
    @property
    def conversations(self) -> Dict[str, Conversation]:
        return self._conversations
    
    @property
    def messages(self) -> Dict[str, Message]:
        return self._messages

    async def initialize(self, 
                        host: str = "localhost",
                        port: int = 27017,
                        database: str = "chat_db",
                        batch_size: int = 100):
        """初始化数据管理器"""
        self.loader = MessageLoader(
            host=host,
            port=port,
            database=database,
            batch_size=batch_size
        )

    async def load_user_data(self, user_id: str) -> None:
        """加载用户数据"""
        if not self.loader:
            raise RuntimeError("DataManager not initialized. Call initialize() first.")
            
        try:
            async for batch in self.loader.get_user_conversations_with_messages(user_id):
                if batch.batch_id not in self._loaded_batches:
                    # 处理会话
                    for conv in batch.conversations:
                        self._conversations[conv.conversation_id] = conv
                        # 更新用户-会话映射
                        for participant in conv.participants:
                            self._user_conversations[participant.user_id].add(conv.conversation_id)
                    
                    # 处理消息
                    for msg in batch.messages:
                        self._messages[msg.message_id] = msg
                        self._conversation_messages[msg.conversation_id].append(msg.message_id)
                    
                    self._loaded_batches.add(batch.batch_id)
            
            logger.info(f"Loaded {len(self._conversations)} conversations and {len(self._messages)} messages for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error loading data for user {user_id}: {str(e)}")
            raise

    async def load_all_data(self) -> None:
        """加载所有数据"""
        if not self.loader:
            raise RuntimeError("DataManager not initialized. Call initialize() first.")
            
        try:
            async for batch in self.loader.get_all_conversations_with_messages():
                if batch.batch_id not in self._loaded_batches:
                    # 处理会话
                    for conv in batch.conversations:
                        self._conversations[conv.conversation_id] = conv
                        # 更新用户-会话映射
                        for participant in conv.participants:
                            self._user_conversations[participant.user_id].add(conv.conversation_id)
                    
                    # 处理消息
                    for msg in batch.messages:
                        self._messages[msg.message_id] = msg
                        self._conversation_messages[msg.conversation_id].append(msg.message_id)
                    
                    self._loaded_batches.add(batch.batch_id)
            
            logger.info(f"Loaded {len(self._conversations)} conversations and {len(self._messages)} messages in total")
            
        except Exception as e:
            logger.error(f"Error loading all data: {str(e)}")
            raise

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversations.get(conversation_id)
    
    def get_message(self, message_id: str) -> Optional[Message]:
        return self._messages.get(message_id)
    
    def get_conversation_messages(self, conversation_id: str) -> List[Message]:
        """获取指定会话的所有消息"""
        message_ids = self._conversation_messages.get(conversation_id, [])
        return [self._messages[mid] for mid in message_ids if mid in self._messages]
    
    def get_user_conversations(self, user_id: str) -> List[Conversation]:
        """获取用户参与的所有会话"""
        conv_ids = self._user_conversations.get(user_id, set())
        return [self._conversations[cid] for cid in conv_ids if cid in self._conversations]

    def clear_cache(self) -> None:
        """清除所有缓存的数据"""
        self._conversations.clear()
        self._messages.clear()
        self._conversation_messages.clear()
        self._user_conversations.clear()
        self._loaded_batches.clear()

    async def load_data_since(self, timestamp: datetime) -> None:
        """加载指定时间之后的数据"""
        if not self.loader:
            raise RuntimeError("DataManager not initialized. Call initialize() first.")
        
        try:
            logger.info(f"Starting to load data since {timestamp}")
            batch_count = 0
            total_conversations = 0
            total_messages = 0
            
            async for batch in self.loader.get_conversations_since(timestamp):
                batch_count += 1
                logger.info(f"Processing batch {batch.batch_id}")
                
                if batch.batch_id not in self._loaded_batches:
                    # 处理会话
                    conv_count = len(batch.conversations)
                    msg_count = len(batch.messages)
                    logger.info(f"Batch contains {conv_count} conversations and {msg_count} messages")
                    
                    for conv in batch.conversations:
                        self._conversations[conv.conversation_id] = conv
                        total_conversations += 1
                        # 更新用户-会话映射
                        for participant in conv.participants:
                            self._user_conversations[participant.user_id].add(conv.conversation_id)
                    
                    # 处理消息
                    for msg in batch.messages:
                        self._messages[msg.message_id] = msg
                        self._conversation_messages[msg.conversation_id].append(msg.message_id)
                        total_messages += 1
                    
                    self._loaded_batches.add(batch.batch_id)
                    logger.info(f"Completed processing batch {batch.batch_id}")
            
            logger.info(f"Data loading completed:")
            logger.info(f"Total batches processed: {batch_count}")
            logger.info(f"Total conversations loaded: {total_conversations}")
            logger.info(f"Total messages loaded: {total_messages}")
            
        except Exception as e:
            logger.error(f"Error loading data since {timestamp}: {str(e)}", exc_info=True)
            raise