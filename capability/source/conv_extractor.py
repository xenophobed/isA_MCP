from typing import List, Dict, Any
from datetime import datetime
from app.config.config_manager import config_manager
from .conv_fact_extractor import ConversationFactExtractor
from .models import MessageData

logger = config_manager.get_logger(__name__)

class ConversationExtractor:
    """Extracts essential conversation data for fact analysis"""
    
    def __init__(self):
        self.fact_extractor = ConversationFactExtractor()
        self.db = None
        self.llm_service = None
        
    async def initialize(self):
        """Initialize extractor and connections"""
        try:
            self.db = await config_manager.get_db("mongodb")
            await self.fact_extractor.initialize()
        except Exception as e:
            logger.error(f"Error initializing ConversationExtractor: {str(e)}")
            raise
            
    async def extract_conversation(self, conversation_id: str) -> Dict:
        """Extract essential conversation data"""
        try:
            # Load messages
            raw_messages = await self._load_conversation_messages(conversation_id)
            if not raw_messages:
                logger.warning(f"No messages found for conversation {conversation_id}")
                return None
                
            # Clean and extract essential data
            cleaned_messages = []
            for msg in raw_messages:
                try:
                    cleaned_msg = MessageData.from_message(msg)
                    cleaned_messages.append(cleaned_msg)
                except Exception as e:
                    logger.warning(f"Skipping invalid message: {str(e)}")
                    continue
            
            if not cleaned_messages:
                return None
            
            # Sort messages by timestamp
            cleaned_messages.sort(key=lambda x: x.timestamp)
            
            # Extract facts
            extraction_result = await self.fact_extractor.extract_facts(cleaned_messages)
            
            return {
                "messages": [
                    {
                        "content": msg.content,
                        "sender_type": msg.sender_type,
                        "timestamp": msg.timestamp
                    }
                    for msg in cleaned_messages
                ],
                "atomic_facts": extraction_result.atomic_facts if extraction_result else []
            }
            
        except Exception as e:
            logger.error(f"Error extracting conversation {conversation_id}: {str(e)}")
            raise
            
    async def _load_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Load messages from MongoDB"""
        try:
            cursor = self.db.messages.find(
                {"conversation_id": conversation_id},
                {
                    "message_id": 1,
                    "conversation_id": 1,
                    "content": 1,
                    "type": 1,
                    "sender": 1,
                    "timestamp": 1,
                    "_id": 0
                }
            ).sort("timestamp", 1)
            
            return [msg async for msg in cursor]
            
        except Exception as e:
            logger.error(f"Error loading messages: {str(e)}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        if self.llm_service and hasattr(self.llm_service, 'close'):
            try:
                await self.llm_service.close()
            except Exception as e:
                logger.error(f"Error cleaning up LLM service: {e}")
                raise
