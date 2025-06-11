from typing import Dict, Any
import requests
from .base import DatabaseConnector, DatabaseConfig

class AirbyteConfig(DatabaseConfig):
    """Airbyte specific configuration"""
    airbyte_url: str
    api_key: str
    workspace_id: str

class AirbyteConnector(DatabaseConnector):
    """
    Airbyte implementation of DatabaseConnector.
    Extends the base database connector with Airbyte-specific functionality.
    """
    
    def __init__(self, config: AirbyteConfig):
        super().__init__(config)
        self.headers = {"Authorization": f"Bearer {config.api_key}"}
    
    async def extract(self, connection_id: str, **kwargs) -> Dict[str, Any]:
        """Execute Airbyte sync and extract data"""
        if not self.is_connected:
            raise ConnectionError("Not connected to Airbyte")
        
        # Trigger Airbyte sync
        response = requests.post(
            f"{self.config.airbyte_url}/connections/sync",
            json={"connectionId": connection_id},
            headers=self.headers
        )
        response.raise_for_status()
        
        # Get sync status
        sync_status = response.json()
        return {"sync_status": sync_status}