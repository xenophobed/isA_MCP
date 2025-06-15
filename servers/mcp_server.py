#!/usr/bin/env python
"""
MCP Server with automatic tool discovery and registration.
This server automatically discovers and registers tools from the apps directory.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import FastMCP, Context 
from registry.apps_registry import discover_and_register_apps
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

@asynccontextmanager
async def lifespan(app: FastMCP):
    """Lifespan for the MCP server"""
    logger.info("Starting MCP server")
    yield
    logger.info("Stopping MCP server")

# Create MCP server
mcp = FastMCP("MCP Tools Server", lifespan=lifespan)

def setup_server():
    """Set up the MCP server with auto-discovered tools"""
    logger.info("Setting up MCP server with auto-discovered tools")
    
    # Discover and register tools from apps directory
    apps_dir = project_root / "apps"
    logger.info(f"Discovering and registering tools from: {apps_dir}")
    
    app_results = discover_and_register_apps(mcp, str(apps_dir), verbose=True)
    total_tools = sum(count for _, count in app_results.values())
    
    logger.info(f"Registered {len(app_results)} apps with {total_tools} tools")
    
    for app_name, (app_info, tool_count) in app_results.items():
        logger.info(f"App: {app_name}, Tools: {tool_count}")
        
    return total_tools

# Main function
if __name__ == "__main__":
    # Setup the server and register tools
    total_tools = setup_server()
    
    if total_tools > 0:
        logger.info(f"Starting MCP server with {total_tools} tools")
        # 根据MCP SDK文档，正确使用streamable-http传输
        mcp.run(transport="streamable-http")
    else:
        logger.error("No tools were registered. Server will not start.")
        sys.exit(1)
    
        