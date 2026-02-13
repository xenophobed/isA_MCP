#!/usr/bin/env python3
"""Modular configuration system for MCP

Configuration hierarchy:
- infra_config: Infrastructure services from isA_Cloud (PostgreSQL, Redis, Qdrant, etc.)
- service_config: External business services from isA_User
- model_config: LLM/embedding models from isA_Model
- mcp_config: MCP-specific settings (server, auth, resources)
- consul_config: Service discovery settings
- logging_config: Logging configuration
"""

import os
from dotenv import load_dotenv
from .logging_config import LoggingConfig
from .infra_config import InfraConfig
from .consul_config import ConsulConfig
from .model_config import ModelConfig
from .service_config import ServiceConfig
from .mcp_config import (
    MCPConfig,
    MCPResourceConfig,
    MCPQdrantConfig,
    MCPMinIOConfig,
    MCPRedisConfig,
    MCPPostgresConfig,
)

# Load environment file based on ENV
env = os.getenv("ENV", "development")
env_file = (
    f"deployment/{env}/config/.env.{env}"
    if env != "development"
    else "deployment/environments/dev.env"
)
load_dotenv(env_file, override=False)

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


__all__ = [
    # Main config
    "MCPConfig",
    "get_settings",
    "reload_settings",
    "settings",
    # Sub-configs
    "LoggingConfig",
    "InfraConfig",
    "ConsulConfig",
    "ModelConfig",
    "ServiceConfig",
    # MCP resource configs
    "MCPResourceConfig",
    "MCPQdrantConfig",
    "MCPMinIOConfig",
    "MCPRedisConfig",
    "MCPPostgresConfig",
]
