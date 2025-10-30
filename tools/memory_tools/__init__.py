#!/usr/bin/env python3
"""
Memory Tools Package
Provides MCP tools for interacting with the memory microservice
"""

from .memory_client import MemoryServiceClient, get_memory_client, MemoryServiceConfig
from .memory_tools import register_memory_tools

__all__ = [
    'MemoryServiceClient',
    'get_memory_client',
    'MemoryServiceConfig',
    'register_memory_tools'
]
