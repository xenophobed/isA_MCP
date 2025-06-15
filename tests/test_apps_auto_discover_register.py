"""
Test script for apps auto-discovery and registration.
"""

import asyncio
import os
import sys
import shutil
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP
from registry.apps_registry import discover_apps, discover_and_register_apps

async def test_app_discovery():
    """Test app discovery from apps directory."""
    print("Starting app discovery test...")
    
    # Create MCP server (but don't start it)
    mcp = FastMCP("Test App Discovery Service")
    print("Created MCP server")
    
    # Discover apps from apps directory
    apps_dir = project_root / "apps"
    print(f"Discovering apps from: {apps_dir}")
    
    # First just discover apps
    apps = discover_apps(str(apps_dir), verbose=True)
    print(f"Total apps discovered: {len(apps)}")
    
    # For each app, print its info
    for app_name, app_info in apps.items():
        print(f"\nApp: {app_name}")
        print(f"  Description: {app_info.description}")
        print(f"  Path: {app_info.path}")
        print(f"  Tools found: {len(app_info.tools)}")
        for tool in app_info.tools:
            print(f"    - {tool.__name__}")
        
        if app_info.metadata:
            print("  Metadata:")
            for key, value in app_info.metadata.items():
                print(f"    - {key}: {value}")
    
    # Now register apps and tools
    app_results = discover_and_register_apps(mcp, str(apps_dir), verbose=True)
    total_tools = sum(count for _, count in app_results.values())
    print(f"\nRegistered {len(app_results)} apps with {total_tools} tools")
    
    # Verify tools were registered by checking mcp's tools
    registered_tools = await mcp.list_tools()
    print("\nRegistered tools:")
    for tool in registered_tools:
        # Tool objects may have name and description as attributes
        try:
            tool_name = tool.name if hasattr(tool, 'name') else str(tool)
            tool_desc = tool.description if hasattr(tool, 'description') else "No description"
            print(f"- {tool_name}: {tool_desc}")
        except Exception as e:
            print(f"Error accessing tool properties: {e}")
    
    print(f"\nNumber of tools registered in MCP: {len(registered_tools)}")
    print(f"Test successful: {len(registered_tools) == total_tools}")
    
    print("Test completed.")

if __name__ == "__main__":
    asyncio.run(test_app_discovery()) 