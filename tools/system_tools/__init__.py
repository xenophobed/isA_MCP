"""
System Tools - Built-in tools for file operations, command execution, and code manipulation.

These tools provide Claude Code-like capabilities:
- File operations (Read, Write, Edit, MultiEdit)
- Command execution (Bash, BashOutput, KillShell)
- Code search (Glob, Grep, LS)
- Notebook editing (NotebookRead, NotebookEdit)

All tools follow the MCP protocol and integrate with the isA security framework.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

__all__ = [
    "register_system_tools",
    "register_file_tools",
    "register_bash_tools",
    "register_search_tools",
    "register_notebook_tools",
]


def register_system_tools(mcp: "FastMCP"):
    """
    Register all system tools with the MCP server.

    This is the main entry point for auto-discovery.
    Following the naming convention: register_{module_name}(mcp)
    """
    from .file_tools import register_file_tools
    from .bash_tools import register_bash_tools
    from .search_tools import register_search_tools
    from .notebook_tools import register_notebook_tools

    register_file_tools(mcp)
    register_bash_tools(mcp)
    register_search_tools(mcp)
    register_notebook_tools(mcp)
