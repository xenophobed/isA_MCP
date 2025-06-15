from typing import Dict, Any
import asyncpg
from .base import BaseConnector, ConnectorConfig

class DatabaseConfig(ConnectorConfig):
    """Database specific configuration"""
    connection_string: str
    schema: str = "public"

class DatabaseConnector(BaseConnector):
    """
    Concrete implementation of BaseConnector for database connections.
    Implements the Template Method pattern defined in BaseConnector.
    """
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.connection = None
    
    async def connect(self) -> None:
        """Establish database connection"""
        self.connection = await asyncpg.connect(self.config.connection_string)
        self.is_connected = True
    
    async def disconnect(self) -> None:
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            self.is_connected = False
    
    async def extract(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute query and extract data"""
        if not self.is_connected:
            raise ConnectionError("Not connected to database")
        
        rows = await self.connection.fetch(query)
        return {"data": [dict(row) for row in rows]}