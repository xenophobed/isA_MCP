from typing import Dict, Any
import requests
from .base import BaseConnector, ConnectorConfig

class NifiConfig(ConnectorConfig):
    """Apache NiFi specific configuration"""
    nifi_url: str
    username: str
    password: str
    processor_id: str

class NifiConnector(BaseConnector):
    """
    Apache NiFi implementation of BaseConnector.
    Handles IoT data streams through NiFi processors.
    """
    
    def __init__(self, config: NifiConfig):
        super().__init__(config)
        self.auth = (config.username, config.password)
    
    async def connect(self) -> None:
        """Connect to NiFi instance"""
        response = requests.get(
            f"{self.config.nifi_url}/flow/process-groups/root",
            auth=self.auth
        )
        response.raise_for_status()
        self.is_connected = True
    
    async def extract(self, **kwargs) -> Dict[str, Any]:
        """Get data from NiFi processor"""
        if not self.is_connected:
            raise ConnectionError("Not connected to NiFi")
        
        response = requests.get(
            f"{self.config.nifi_url}/processors/{self.config.processor_id}/input-ports",
            auth=self.auth
        )
        response.raise_for_status()
        return response.json()
