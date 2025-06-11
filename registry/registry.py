"""
MCP Registry - Manages server registration and configuration.
"""

import os
import json
import importlib
import pkgutil
from typing import Dict, Any, List, Optional, Union, Callable, Type
from pathlib import Path
import logging
from dataclasses import dataclass
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    transport: str
    url: Optional[str] = None
    server: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None

class MCPRegistry:
    """Registry for MCP servers."""
    
    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._configs_dir: Optional[Path] = None
        self._server_modules: Dict[str, Dict[str, Callable]] = {}
        
        # Discover available server modules 
        # 注意：现在推迟服务器模块的导入，以避免循环导入
        self._server_modules = {}

    def discover_server_modules(self):
        """Discover available server modules from the servers directory."""
        if self._server_modules:
            return  # 如果已经发现，就不再重复
            
        logger.info("Discovering server modules...")
        
        # 按需导入 servers 包
        from app.services.agent.mcp import servers
        
        # Iterate through server categories (data, finance, etc.)
        for category_finder, category_name, is_pkg in pkgutil.iter_modules(servers.__path__):
            if is_pkg:
                try:
                    # Import category package
                    category_module = importlib.import_module(f"app.services.agent.mcp.servers.{category_name}")
                    
                    # Initialize category in server modules dict
                    self._server_modules[category_name] = {}
                    
                    # Get the path to the category directory
                    category_path = Path(category_module.__file__).parent
                    
                    # Discover server modules in this category
                    for _, server_name, _ in pkgutil.iter_modules([str(category_path)]):
                        if server_name != "__init__":
                            try:
                                # Import server module
                                server_module = importlib.import_module(f"app.services.agent.mcp.servers.{category_name}.{server_name}")
                                
                                # Check if module has get_config function
                                if hasattr(server_module, "get_config"):
                                    # Add to server modules dict
                                    self._server_modules[category_name][server_name] = server_module.get_config
                                    logger.info(f"Discovered server module: {category_name}.{server_name}")
                            except Exception as e:
                                logger.error(f"Failed to import server module {category_name}.{server_name}: {e}")
                except Exception as e:
                    logger.error(f"Failed to import category module {category_name}: {e}")
    
    def set_config_dir(self, directory: Union[str, Path]) -> None:
        """Set the directory to load/save configurations from/to."""
        self._configs_dir = Path(directory)
        os.makedirs(self._configs_dir, exist_ok=True)
    
    def register_server(self, name: str, config: MCPServerConfig) -> None:
        """Register a server with the registry.
        
        Args:
            name: Unique name for the server
            config: Server configuration
        """
        self._servers[name] = config
        logger.info(f"Registered MCP server: {name}")
    
    def register_direct_server(self, name: str, server: Any) -> None:
        """Register a direct server instance.
        
        Args:
            name: Unique name for the server
            server: Server instance
        """
        self._servers[name] = MCPServerConfig(
            transport="direct",
            server=server
        )
        logger.info(f"Registered direct MCP server: {name}")
    
    def unregister_server(self, name: str) -> None:
        """Unregister a server from the registry.
        
        Args:
            name: Name of the server to unregister
        """
        if name in self._servers:
            del self._servers[name]
            logger.info(f"Unregistered MCP server: {name}")
    
    def get_server_config(self, name: str) -> Optional[MCPServerConfig]:
        """Get server configuration by name.
        
        Args:
            name: Name of the server
            
        Returns:
            Server configuration or None if not found
        """
        return self._servers.get(name)
    
    def list_servers(self) -> List[str]:
        """List all registered server names.
        
        Returns:
            List of registered server names
        """
        return list(self._servers.keys())
    
    def get_all_configs(self) -> Dict[str, MCPServerConfig]:
        """Get all server configurations.
        
        Returns:
            Dictionary mapping server names to configurations
        """
        return self._servers.copy()
    
    def get_all_servers(self) -> Dict[str, MCPServerConfig]:
        """Get all registered MCP server configurations."""
        return self._servers.copy()
    
    def get_enabled_servers(self) -> Dict[str, MCPServerConfig]:
        """Get all enabled MCP server configurations."""
        return {name: server for name, server in self._servers.items() if server.enabled}
    
    def get_servers_by_category(self, category: str) -> Dict[str, MCPServerConfig]:
        """Get all server configurations in a specific category."""
        return {name: server for name, server in self._servers.items() 
                if server.category == category and server.enabled}
    
    def get_available_servers(self) -> Dict[str, List[str]]:
        """Get a dictionary of available server modules by category."""
        # 确保服务器模块已被发现
        self.discover_server_modules()
        
        result = {}
        for category, servers in self._server_modules.items():
            result[category] = list(servers.keys())
        return result
    
    def register_server_by_category(self, category: str, server_name: str, **kwargs) -> None:
        """Register a server by category and name.
        
        Args:
            category: The category of the server (e.g., 'data', 'finance')
            server_name: The name of the server module (e.g., 'dbt', 'stripe')
            **kwargs: Additional arguments to pass to the server's get_config function
        
        Raises:
            ValueError: If the server module is not found
        """
        # 确保服务器模块已被发现
        self.discover_server_modules()
        
        if category not in self._server_modules:
            raise ValueError(f"Category '{category}' not found")
            
        if server_name not in self._server_modules[category]:
            raise ValueError(f"Server '{server_name}' not found in category '{category}'")
            
        # Get the get_config function
        get_config_func = self._server_modules[category][server_name]
        
        # Get the server configuration
        config = get_config_func(**kwargs)
        
        # Register the server
        self.register_server(server_name, config)
    
    def register_category(self, category: str, **kwargs) -> None:
        """Register all servers in a category.
        
        Args:
            category: The category of servers to register (e.g., 'data', 'finance')
            **kwargs: Server-specific arguments as a nested dictionary:
                      {server_name: {arg_name: arg_value, ...}, ...}
        """
        # 确保服务器模块已被发现
        self.discover_server_modules()
        
        if category not in self._server_modules:
            logger.warning(f"Category '{category}' not found")
            return
            
        for server_name, get_config_func in self._server_modules[category].items():
            try:
                # Get server-specific arguments
                server_kwargs = kwargs.get(server_name, {})
                
                # Get the server configuration
                config = get_config_func(**server_kwargs)
                
                # Register the server
                self.register_server(server_name, config)
            except Exception as e:
                logger.error(f"Failed to register server {category}.{server_name}: {e}")
    
    def save_config(self, name: str) -> None:
        """Save a server configuration to disk."""
        if not self._configs_dir:
            raise ValueError("Config directory not set. Call set_config_dir first.")
        
        server = self.get_server_config(name)
        if not server:
            raise ValueError(f"Server {name} not found in registry")
        
        config_file = self._configs_dir / f"{name}.json"
        with open(config_file, 'w') as f:
            # Use a simplified representation that can be serialized to JSON
            serializable_config = {
                "name": name,
                "transport": server.transport,
                "config": server.config,
                "enabled": server.enabled,
                "category": server.category
            }
            json.dump(serializable_config, f, indent=2)
    
    def load_config(self, name: str) -> None:
        """Load a server configuration from disk."""
        if not self._configs_dir:
            raise ValueError("Config directory not set. Call set_config_dir first.")
        
        config_file = self._configs_dir / f"{name}.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Config file {config_file} not found")
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            server_config = MCPServerConfig(
                name=name,
                transport=config_data["transport"],
                config=config_data["config"],
                enabled=config_data["enabled"],
                category=config_data["category"]
            )
            self.register_server(name, server_config)
    
    def load_all_configs(self) -> None:
        """Load all server configurations from disk."""
        if not self._configs_dir:
            raise ValueError("Config directory not set. Call set_config_dir first.")
        
        for config_file in self._configs_dir.glob("*.json"):
            try:
                self.load_config(config_file.stem)
            except Exception as e:
                logger.error(f"Failed to load config {config_file}: {e}")
    
    def save_all_configs(self) -> None:
        """Save all server configurations to disk."""
        if not self._configs_dir:
            raise ValueError("Config directory not set. Call set_config_dir first.")
        
        for name in self._servers:
            try:
                self.save_config(name)
            except Exception as e:
                logger.error(f"Failed to save config {name}: {e}")
    
    def get_client_config(self) -> Dict[str, Dict[str, Any]]:
        """Get the configuration for MultiServerMCPClient."""
        client_config = {}
        for name, server in self.get_enabled_servers().items():
            client_config[name] = {
                **server.config,
                "transport": server.transport
            }
        return client_config
    
    def create_mcp_client(self) -> MultiServerMCPClient:
        """Create an MCP client with all registered servers."""
        client_config = self.get_client_config()
        return MultiServerMCPClient(client_config)
    
    def register_dbt(self, project_dir: Optional[str] = None) -> None:
        """Register a DBT server."""
        self.register_server_by_category("data", "dbt", project_dir=project_dir)
    
    def register_stripe(self, api_key: Optional[str] = None) -> None:
        """Register a Stripe server."""
        self.register_server_by_category("finance", "stripe", api_key=api_key)
        
    def register_github(self, token: Optional[str] = None) -> None:
        """Register a GitHub server."""
        self.register_server_by_category("devops", "github", token=token)
    
    def register_custom_server(self, name: str, command: str, args: List[str], 
                              env: Optional[Dict[str, str]] = None,
                              category: str = "general") -> None:
        """Register a custom stdio-based server."""
        server_config = MCPServerConfig(
            transport="stdio",
            config={
                "command": command,
                "args": args
            },
            enabled=True,
            category=category
        )
        self.register_server(name, server_config)
    
    def register_websocket_server(self, name: str, url: str, category: str = "general") -> None:
        """Register a WebSocket-based server."""
        server_config = MCPServerConfig(
            transport="websocket",
            url=url,
            enabled=True,
            category=category
        )
        self.register_server(name, server_config)
    
    def register_sse_server(self, name: str, url: str, category: str = "general") -> None:
        """Register an SSE-based server."""
        server_config = MCPServerConfig(
            transport="sse",
            url=url,
            enabled=True,
            category=category
        )
        self.register_server(name, server_config)


# Global registry instance
_registry = MCPRegistry()

def get_registry() -> MCPRegistry:
    """Get the global registry instance.
    
    Returns:
        Global MCPRegistry instance
    """
    return _registry
