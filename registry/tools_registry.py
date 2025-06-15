"""
Tools registry module for automatic discovery and registration of MCP tools.
"""

import os
import importlib
import inspect
import sys
import logging
from typing import Any, Optional
from pathlib import Path

def discover_and_register_tools(mcp: Any, tools_dir: str, verbose: bool = False) -> int:
    """
    Discover and register all tools in the specified directory.
    
    Args:
        mcp: The MCP server instance.
        tools_dir: Path to the directory containing tool modules.
        verbose: Whether to print verbose output.
        
    Returns:
        int: Number of tools registered.
    """
    if not os.path.exists(tools_dir):
        if verbose:
            print(f"Tools directory not found: {tools_dir}")
        return 0
        
    tool_count = 0
    
    # Ensure the parent directory is in the Python path
    tools_dir_path = Path(tools_dir)
    parent_dir = str(tools_dir_path.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    tools_dir_name = tools_dir_path.name
    
    # Get all Python files in the tools directory
    for fname in os.listdir(tools_dir):
        if fname.endswith(".py") and not fname.startswith("_"):
            module_name = f"{tools_dir_name}.{fname[:-3]}"
            
            if verbose:
                print(f"Discovering tools in module: {module_name}")
                
            try:
                # Import the module
                mod = importlib.import_module(module_name)
                
                # Find and register functions
                for name, func in inspect.getmembers(mod, inspect.isfunction):
                    # Only register functions not starting with underscore
                    if not name.startswith("_"):
                        if verbose:
                            print(f"Registering tool: {name}")
                        try:
                            mcp.tool()(func)
                            tool_count += 1
                        except Exception as e:
                            if verbose:
                                print(f"Error registering tool {name}: {e}")
                        
            except ImportError as e:
                # Handle common import errors gracefully
                if verbose:
                    print(f"Import error in module {module_name}: {e}")
                    print("This could be due to missing dependencies or incorrect imports.")
                    print("Skipping this module and continuing with discovery.")
            except Exception as e:
                if verbose:
                    print(f"Error loading module {module_name}: {e}")
    
    if verbose:
        print(f"Total tools registered: {tool_count}")
        
    return tool_count

def register_tools_directory(mcp: Any, tools_dir: str, verbose: bool = False) -> int:
    """
    Convenience wrapper for discover_and_register_tools.
    
    Args:
        mcp: The MCP server instance.
        tools_dir: Path to the directory containing tool modules.
        verbose: Whether to print verbose output.
        
    Returns:
        int: Number of tools registered.
    """
    return discover_and_register_tools(mcp, tools_dir, verbose)

# Command line interface
if __name__ == "__main__":
    import argparse
    from mcp.server.fastmcp import FastMCP
    
    parser = argparse.ArgumentParser(description="Discover and register MCP tools from a directory")
    parser.add_argument("--dir", "-d", default="./tools", help="Directory containing tool modules")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--app-name", "-n", default="Tool Discovery App", help="Name of the MCP application")
    parser.add_argument("--list", "-l", action="store_true", help="List discovered tools without starting server")
    args = parser.parse_args()
    
    # Create MCP server
    mcp = FastMCP(args.app_name)
    
    # Discover and register tools
    count = discover_and_register_tools(mcp, args.dir, args.verbose)
    print(f"Discovered and registered {count} tools")
    
    if args.list:
        # Import asyncio only when needed
        import asyncio
        
        async def list_tools():
            tools = await mcp.list_tools()
            print("\nRegistered tools:")
            for tool in tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                tool_desc = tool.description if hasattr(tool, 'description') else "No description"
                print(f"- {tool_name}: {tool_desc}")
        
        asyncio.run(list_tools())
    else:
        # Start the server
        print(f"Starting MCP server with {count} tools...")
        mcp.run()
