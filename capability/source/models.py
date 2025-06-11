from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class MessageData(BaseModel):
    """Essential message data for fact extraction"""
    content: str = Field(description="Message content")
    sender_type: str = Field(description="Type of sender (customer/agent/bot)")
    timestamp: datetime = Field(description="When the message was sent")

    @classmethod
    def from_message(cls, msg: Dict) -> "MessageData":
        """Create MessageData from raw message"""
        raw_content = msg["content"]
        if isinstance(raw_content, dict):
            if raw_content.get("type") == "text":
                content = raw_content.get("text", "")
            else:
                content = str(raw_content)
        else:
            content = str(raw_content)
        
        sender_type = msg["sender"].get("type", "other")
        if sender_type == "ai":
            sender_type = "bot"
            
        return cls(
            content=content,
            sender_type=sender_type,
            timestamp=msg["timestamp"]
        )

class AtomicFact(BaseModel):
    """Simple atomic fact from conversation"""
    entities: List[str] = Field(description="Entities involved in this fact")
    atomic_fact: str = Field(description="Complete fact description")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this fact was extracted"
    )

class ConversationExtraction(BaseModel):
    """Extracted knowledge from conversation"""
    atomic_facts: List[AtomicFact] = Field(
        default_factory=list,
        description="List of atomic facts extracted"
    ) 