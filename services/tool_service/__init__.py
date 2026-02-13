"""
Tool Service - MCP Tool Registry and Management
"""

from .tool_service import ToolService


def __getattr__(name):
    if name == "ToolRepository":
        from .tool_repository import ToolRepository

        return ToolRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ToolRepository", "ToolService"]
