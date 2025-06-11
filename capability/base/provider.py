# capability/base/provider.py

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from .metadata import CapabilityMetadata
from datetime import datetime

class MetadataProvider(ABC):
    def __init__(self):
        self._metadata = None  
        self._last_updated = None
    
    @abstractmethod
    async def get_metadata(self) -> CapabilityMetadata:
        """获取能力元数据"""
        pass
    
    @abstractmethod
    async def update_metadata(self, metadata: CapabilityMetadata):
        """更新能力元数据"""
        pass
        
    async def get_status(self) -> str:
        """获取能力状态"""
        metadata = await self.get_metadata()
        return metadata.status
        
    async def update_status(self, new_status: str):
        """更新能力状态"""
        if self._metadata:
            self._metadata.status = new_status
            self._metadata.last_updated = datetime.now()
            
    async def get_elements(self) -> List[str]:
        """获取关键元素"""
        metadata = await self.get_metadata()
        return metadata.key_elements
