import os
from typing import Dict, Any, Optional
from pydantic import BaseSettings

class MCPSettings(BaseSettings):
    """Configuration settings for MCP services"""
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Authentication (disabled by default for initial setup)
    require_auth: bool = False
    api_keys: Dict[str, str] = {}
    
    # Weather service configuration
    openweather_api_key: Optional[str] = None
    
    class Config:
        env_prefix = "MCP_"
        env_file = ".env"

# Global settings instance
settings = MCPSettings()

def get_settings() -> MCPSettings:
    """Get global settings instance"""
    return settings
