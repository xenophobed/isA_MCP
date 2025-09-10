#!/usr/bin/env python3
"""
External Services Integration Package

Provides integration capabilities for external MCP services like MindsDB, Composio, etc.
"""

from .base_external_service import BaseExternalService, ExternalServiceConfig
from .service_registry import ExternalServiceRegistry

__version__ = "1.0.0"
__all__ = [
    "BaseExternalService",
    "ExternalServiceConfig", 
    "ExternalServiceRegistry"
]