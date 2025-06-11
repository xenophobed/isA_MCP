from typing import Dict, Any, List, Optional, Type, Union
import inspect
import logging
from langchain.tools import BaseTool
from pydantic import BaseModel, create_model

logger = logging.getLogger(__name__)

class CustomToolsAdapter:
    """Adapter for exposing custom tools through the MCP interface."""
    
    def __init__(self, tools: List[BaseTool]):
        """Initialize the custom tools adapter.
        
        Args:
            tools: List of LangChain tools to adapt.
        """
        self.tools = tools
        self.server = self._create_server()
    
    def _create_server(self) -> 'CustomMCPServer':
        """Create a custom MCP server with the adapted tools.
        
        Returns:
            CustomMCPServer: MCP server with the adapted tools.
        """
        return CustomMCPServer(self.tools)
    
    def get_server(self) -> 'CustomMCPServer':
        """Get the custom MCP server.
        
        Returns:
            CustomMCPServer: MCP server with the adapted tools.
        """
        return self.server


class CustomMCPServer:
    """A custom MCP server that exposes tools directly."""
    
    def __init__(self, tools: List[BaseTool]):
        """Initialize the custom MCP server.
        
        Args:
            tools: List of LangChain tools to expose.
        """
        self.tools = tools
    
    def get_tools(self) -> List[BaseTool]:
        """Get the list of tools.
        
        Returns:
            List[BaseTool]: List of tools.
        """
        return self.tools


class ToolsImporter:
    """Utility for importing tools from different modules."""
    
    @staticmethod
    def import_tools_from_module(module_path: str) -> List[BaseTool]:
        """Import all tools from a module.
        
        Args:
            module_path: Dot-separated path to the module.
            
        Returns:
            List[BaseTool]: List of tools from the module.
        """
        try:
            module = __import__(module_path, fromlist=['*'])
            tools = []
            
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if inspect.isclass(attr) and issubclass(attr, BaseTool) and attr != BaseTool:
                    try:
                        tool_instance = attr()
                        tools.append(tool_instance)
                    except Exception as e:
                        logger.warning(f"Failed to instantiate tool {attr_name}: {e}")
            
            return tools
        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {e}")
            return []
    
    @staticmethod
    def import_tools_from_directory(base_package: str, directories: List[str]) -> Dict[str, List[BaseTool]]:
        """Import all tools from multiple directories.
        
        Args:
            base_package: Base package for the imports.
            directories: List of directory names relative to the base package.
            
        Returns:
            Dict[str, List[BaseTool]]: Dictionary mapping directory names to lists of tools.
        """
        result = {}
        
        for directory in directories:
            module_path = f"{base_package}.{directory}"
            tools = ToolsImporter.import_tools_from_module(module_path)
            result[directory] = tools
        
        return result


def convert_tools_to_mcp(tools_list: List[BaseTool]) -> 'CustomMCPServer':
    """Convert a list of LangChain tools to an MCP server.
    
    Args:
        tools_list: List of LangChain tools.
        
    Returns:
        CustomMCPServer: MCP server with the tools.
    """
    adapter = CustomToolsAdapter(tools_list)
    return adapter.get_server()


# Example usage
"""
from app.services.agent.mcp.adapters.tools_adapter import ToolsImporter, convert_tools_to_mcp
from app.services.agent.mcp.registry import get_registry

# Import tools from your existing directories
tools_by_directory = ToolsImporter.import_tools_from_directory(
    "app.services.agent.tools",
    ["basic", "planning", "math", "creative"]
)

# Register each set of tools as a separate MCP server
registry = get_registry()

for directory, tools in tools_by_directory.items():
    if tools:
        mcp_server = convert_tools_to_mcp(tools)
        registry.register_direct_server(f"custom_{directory}", mcp_server)
""" 