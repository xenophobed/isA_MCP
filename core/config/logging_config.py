#!/usr/bin/env python3
"""Logging configuration for MCP"""

import os
from dataclasses import dataclass


def _bool(val: str) -> bool:
    return val.lower() == "true"


def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default


@dataclass
class LoggingConfig:
    """Centralized logging configuration with Loki gRPC support"""

    log_level: str = "INFO"
    log_file: str = "logs/mcp_server.log"
    enable_console: bool = True
    enable_structured: bool = False

    # Loki gRPC settings
    loki_enabled: bool = False
    loki_grpc_host: str = "localhost"
    loki_grpc_port: int = 50054

    # Service identity
    service_name: str = "mcp"
    environment: str = "development"

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Load logging config from environment variables"""
        env = os.getenv("ENV", "development")
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/mcp_server.log"),
            enable_console=True,
            enable_structured=_bool(os.getenv("ENABLE_STRUCTURED_LOGGING", "false")),
            loki_enabled=_bool(os.getenv("LOKI_ENABLED", "false")),
            loki_grpc_host=os.getenv("LOKI_GRPC_HOST", "localhost"),
            loki_grpc_port=_int(os.getenv("LOKI_GRPC_PORT", "50054"), 50054),
            service_name=os.getenv("SERVICE_NAME", "mcp"),
            environment=os.getenv("ENVIRONMENT", env),
        )
