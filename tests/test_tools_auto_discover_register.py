"""
Test script for tools auto-discovery and registration.
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
from registry.tools_registry import discover_and_register_tools

async def test_tool_registration():
    """Test tool registration from tools directory."""
    print("Starting tool registration test...")
    
    # Create a temporary tools directory for testing
    test_tools_dir = project_root / "test_tools"
    os.makedirs(test_tools_dir, exist_ok=True)
    
    try:
        # Copy our test tools to the test directory
        for tool_file in ["calculator.py", "weather_tools.py"]:
            src = project_root / "tools" / tool_file
            if src.exists():
                shutil.copy(src, test_tools_dir / tool_file)
                print(f"Copied {tool_file} to test directory")
        
        # Create MCP server (but don't start it)
        mcp = FastMCP("Test Tool Service")
        print("Created MCP server")
        
        # Discover and register tools from test directory
        print(f"Discovering tools from: {test_tools_dir}")
        tools_count = discover_and_register_tools(mcp, str(test_tools_dir), verbose=True)
        print(f"Total tools registered: {tools_count}")
        
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
                print(f"Tool object: {tool}")
                print(f"Tool dir: {dir(tool)}")
        
        print(f"\nNumber of tools found: {len(registered_tools)}")
        print(f"Test successful: {len(registered_tools) == tools_count}")
        
    finally:
        # Clean up
        print("\nCleaning up...")
        if test_tools_dir.exists():
            shutil.rmtree(test_tools_dir)
        
        print("Test completed.")

if __name__ == "__main__":
    asyncio.run(test_tool_registration())
