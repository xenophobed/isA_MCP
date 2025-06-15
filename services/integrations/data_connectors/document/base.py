from typing import Dict, Any
import aiofiles
from .base import BaseConnector, ConnectorConfig

class FileConfig(ConnectorConfig):
    """File specific configuration"""
    file_path: str
    file_type: str

class FileConnector(BaseConnector):
    """
    Concrete implementation of BaseConnector for file operations.
    Implements the Template Method pattern defined in BaseConnector.
    """
    
    def __init__(self, config: FileConfig):
        super().__init__(config)
        self.file = None
    
    async def connect(self) -> None:
        """Open file connection"""
        self.file = await aiofiles.open(self.config.file_path, mode='r')
        self.is_connected = True
    
    async def disconnect(self) -> None:
        """Close file connection"""
        if self.file:
            await self.file.close()
            self.is_connected = False
    
    async def extract(self, **kwargs) -> Dict[str, Any]:
        """Read file content"""
        if not self.is_connected:
            raise ConnectionError("File not opened")
        
        content = await self.file.read()
        return {"content": content}