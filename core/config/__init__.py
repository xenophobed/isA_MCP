#!/usr/bin/env python3
"""Modular configuration system for MCP"""
import os
from dotenv import load_dotenv
from .logging_config import LoggingConfig
from .infra_config import InfraConfig
from .mcp_config import MCPConfig

# Load environment file based on ENV
env = os.getenv("ENV", "development")
env_file = f"deployment/{env}/config/.env.{env}" if env != "development" else "deployment/dev/.env"
load_dotenv(env_file, override=True)

# Create global settings instance
settings = MCPConfig.from_env()

def get_settings() -> MCPConfig:
    """Get global settings instance"""
    return settings

def reload_settings() -> MCPConfig:
    """Reload settings from environment"""
    global settings
    settings = MCPConfig.from_env()
    return settings

__all__ = ['LoggingConfig', 'InfraConfig', 'MCPConfig', 'get_settings', 'reload_settings', 'settings']
