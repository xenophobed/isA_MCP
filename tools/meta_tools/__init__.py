"""
Meta-Tools Package

Provides high-level tools for dynamic discovery and execution:
- discover: Search for tools using hierarchical semantic search
- get_tool_schema: Get input schema for a tool
- execute: Execute a discovered tool
- list_skills: List all skill categories
"""

from .discovery_tools import register_discovery_tools

__all__ = ["register_discovery_tools"]
