from typing import List, Dict, Any
from app.config.config_manager import config_manager
from .models import MessageData, AtomicFact, ConversationExtraction
from app.services.ai.chain.chain_builder import ChainBuilder

logger = config_manager.get_logger(__name__)

class ConversationFactExtractor:
    """Extracts atomic facts from conversations"""
    
    def __init__(self):
        self.chain = None
        
    async def initialize(self):
        """Initialize the extraction chain"""
        if not self.chain:
            self.chain = await ChainBuilder.create_structured_chain(
                prompt_name="conv_extractor",
                output_model=ConversationExtraction,
                template_path="app/services/ai/prompt/templates/knowledge"
            )
    
    def _prepare_conversation_text(self, messages: List[MessageData]) -> str:
        """Format messages into conversation text"""
        formatted_messages = []
        for msg in messages:
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            role = msg.sender_type.upper()
            formatted_messages.append(f"[{timestamp}] {role}: {msg.content}")
            
        return "\n".join(formatted_messages)

    async def extract_facts(self, messages: List[MessageData]) -> ConversationExtraction:
        """Extract atomic facts from conversation"""
        try:
            await self.initialize()
            conversation_text = self._prepare_conversation_text(messages)
            
            # Extract facts using chain
            result = await self.chain.ainvoke({
                "messages": conversation_text
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting facts: {str(e)}")
            raise
