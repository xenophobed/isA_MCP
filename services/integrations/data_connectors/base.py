from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class ConnectorConfig(BaseModel):
    """Base configuration model for all connectors"""
    name: str
    description: Optional[str] = None
    enabled: bool = True

class BaseConnector(ABC):
    """
    Base interface for all data connectors.
    
    This abstract base class defines the contract that all concrete connector implementations
    must follow. It uses the Template Method pattern to define the skeleton of the data
    ingestion process.
    
    Attributes:
        config (ConnectorConfig): Configuration for the connector
        is_connected (bool): Connection status flag
    
    Methods:
        connect(): Establish connection to data source
        disconnect(): Close connection to data source
        extract(): Extract data from source
        transform(): Transform extracted data
        validate(): Validate transformed data
        load(): Load validated data to destination
    """
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.is_connected = False
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the data source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the data source"""
        pass
    
    @abstractmethod
    async def extract(self, **kwargs) -> Dict[str, Any]:
        """Extract data from the source"""
        pass
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform the extracted data (optional override)"""
        return data
    
    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate the transformed data (optional override)"""
        return True
    
    async def load(self, data: Dict[str, Any]) -> bool:
        """Load the validated data (optional override)"""
        return True
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Template method that defines the data ingestion process.
        This method orchestrates the entire ETL process.
        """
        try:
            await self.connect()
            raw_data = await self.extract(**kwargs)
            transformed_data = await self.transform(raw_data)
            if await self.validate(transformed_data):
                await self.load(transformed_data)
                return transformed_data
            else:
                raise ValueError("Data validation failed")
        finally:
            await self.disconnect()