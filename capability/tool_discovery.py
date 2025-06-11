"""
Tool discovery module for MCP capability.
"""

from typing import Dict, List, Any, Optional
import logging
from app.services.agent.mcp.registry.registry import get_registry
from app.services.agent.mcp.adapters.tools_adapter import ToolsImporter

logger = logging.getLogger(__name__)

class ToolDiscovery:
    """Discovers tools from various sources and makes them available through MCP."""
    
    @staticmethod
    async def discover_tools_from_servers() -> List[Dict[str, Any]]:
        """Discover tools from all registered MCP servers.
        
        Returns:
            List of tool metadata from all servers.
        """
        registry = get_registry()
        tools = []
        
        for server_name in registry.list_servers():
            config = registry.get_server_config(server_name)
            if not config:
                continue
                
            # For direct servers that have get_tools method
            if config.transport == "direct" and config.server:
                server = config.server
                if hasattr(server, "get_tools"):
                    server_tools = server.get_tools()
                    for tool in server_tools:
                        tool_info = {
                            "name": tool.name if hasattr(tool, "name") else str(tool),
                            "description": tool.description if hasattr(tool, "description") else "",
                            "server": server_name
                        }
                        tools.append(tool_info)
        
        return tools
    
    @staticmethod
    def discover_langchain_tools(base_package: str, directories: List[str]) -> Dict[str, List[Any]]:
        """Discover LangChain tools and convert them to MCP servers.
        
        Args:
            base_package: Base package for the imports
            directories: List of directory names relative to the base package
            
        Returns:
            Dictionary mapping directories to lists of tools.
        """
        registry = get_registry()
        result = ToolsImporter.import_tools_from_directory(base_package, directories)
        
        # Register each set of tools as a separate MCP server
        for directory, tools in result.items():
            if tools:
                from app.services.agent.mcp.adapters.tools_adapter import convert_tools_to_mcp
                mcp_server = convert_tools_to_mcp(tools)
                registry.register_direct_server(f"custom_{directory}", mcp_server)
                
        return result
    
    @staticmethod
    async def get_all_capabilities() -> Dict[str, Dict[str, Any]]:
        """Get all available capabilities from registered servers.
        
        Returns:
            Dictionary mapping tool names to capability information.
        """
        tools = await ToolDiscovery.discover_tools_from_servers()
        capabilities = {}
        
        for tool in tools:
            name = tool.get("name", "")
            if name:
                capabilities[name] = {
                    "description": tool.get("description", ""),
                    "server": tool.get("server", ""),
                    "parameters": tool.get("parameters", {})
                }
                
        return capabilities 