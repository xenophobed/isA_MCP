"""
MCP (Model Context Protocol) integration package for agent services.

This package provides utilities for registering and using MCP servers.
"""

from app.services.agent.mcp.registry.registry import get_registry, MCPRegistry, MCPServerConfig
from app.services.agent.mcp.client.modern_client import MCPDirectClient

__all__ = [
    'get_registry',
    'MCPRegistry',
    'MCPServerConfig',
    'MCPDirectClient'
] 