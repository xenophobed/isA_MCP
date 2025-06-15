from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Optional

class CapabilityMetadata(BaseModel):
    capability_id: str
    type: str
    name: str
    description: str
    version: str
    status: str = "active"
    key_elements: List[str]
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Config:
        extra = "allow"

class MetadataProvider(ABC):
    @abstractmethod
    async def get_metadata(self) -> CapabilityMetadata:
        """Get current metadata"""
        pass
    
    @abstractmethod
    async def update_metadata(self, metadata: CapabilityMetadata):
        """Update metadata"""
        pass