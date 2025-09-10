#!/usr/bin/env python3
"""
External Service Registry

Manages registration, discovery, and lifecycle of external services.
"""

import asyncio
import yaml
import json
import logging
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP
from .base_external_service import BaseExternalService, ExternalServiceConfig, ServiceTool

logger = logging.getLogger(__name__)

class ExternalServiceRegistry:
    """Registry for managing external services and their integration with MCP"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("config/external_services")
        self.services: Dict[str, BaseExternalService] = {}
        self.service_configs: Dict[str, ExternalServiceConfig] = {}
        self.mcp_server: Optional[FastMCP] = None
        
        # Service type mappings
        self._service_type_registry: Dict[str, Type[BaseExternalService]] = {}
        
        # Health monitoring
        self._last_health_check: Dict[str, datetime] = {}
        self._health_check_interval = timedelta(minutes=5)
    
    def register_service_type(self, service_type: str, service_class: Type[BaseExternalService]):
        """Register a service type class"""
        self._service_type_registry[service_type] = service_class
        logger.info(f"Registered service type '{service_type}' with class {service_class.__name__}")
    
    async def load_service_configs(self) -> Dict[str, ExternalServiceConfig]:
        """Load service configurations from files"""
        configs = {}
        
        if not self.config_dir.exists():
            logger.warning(f"External services config directory not found: {self.config_dir}")
            return configs
        
        # Load YAML configurations
        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    
                if 'external_services' in config_data:
                    for service_name, service_config in config_data['external_services'].items():
                        configs[service_name] = self._create_service_config(service_name, service_config)
                        
            except Exception as e:
                logger.error(f"Error loading config file {config_file}: {e}")
        
        # Load JSON configurations  
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    
                if 'external_services' in config_data:
                    for service_name, service_config in config_data['external_services'].items():
                        configs[service_name] = self._create_service_config(service_name, service_config)
                        
            except Exception as e:
                logger.error(f"Error loading config file {config_file}: {e}")
        
        self.service_configs = configs
        logger.info(f"Loaded {len(configs)} external service configurations")
        return configs
    
    def _create_service_config(self, name: str, config_data: Dict[str, Any]) -> ExternalServiceConfig:
        """Create ExternalServiceConfig from configuration data"""
        return ExternalServiceConfig(
            name=name,
            service_type=config_data.get('type', 'custom'),
            connection_params=config_data.get('connection', {}),
            auth_config=config_data.get('auth'),
            capabilities=config_data.get('capabilities', []),
            enabled=config_data.get('enabled', True),
            timeout_seconds=config_data.get('timeout_seconds', 30),
            retry_attempts=config_data.get('retry_attempts', 3)
        )
    
    async def initialize_services(self) -> Dict[str, bool]:
        """Initialize all configured services"""
        # Load configurations
        await self.load_service_configs()
        
        initialization_results = {}
        
        for service_name, config in self.service_configs.items():
            if not config.enabled:
                logger.info(f"Skipping disabled service: {service_name}")
                initialization_results[service_name] = False
                continue
            
            try:
                # Create service instance
                service = await self._create_service_instance(config)
                if service:
                    # Register service
                    await self.register_service(service)
                    initialization_results[service_name] = True
                    logger.info(f"Successfully initialized external service: {service_name}")
                else:
                    initialization_results[service_name] = False
                    logger.error(f"Failed to create service instance: {service_name}")
                    
            except Exception as e:
                initialization_results[service_name] = False
                logger.error(f"Error initializing service {service_name}: {e}")
        
        return initialization_results
    
    async def _create_service_instance(self, config: ExternalServiceConfig) -> Optional[BaseExternalService]:
        """Create a service instance based on configuration"""
        service_type = config.service_type
        
        if service_type not in self._service_type_registry:
            logger.error(f"Unknown service type: {service_type}")
            return None
        
        service_class = self._service_type_registry[service_type]
        return service_class(config)
    
    async def register_service(self, service: BaseExternalService) -> bool:
        """Register an external service"""
        try:
            # Attempt to connect
            if not await service.connect():
                logger.error(f"Failed to connect to service: {service.service_name}")
                return False
            
            # Discover capabilities
            capabilities = await service.discover_capabilities()
            logger.info(f"Discovered capabilities for {service.service_name}: {capabilities}")
            
            # Register with MCP if available
            if self.mcp_server:
                await self._register_capabilities_with_mcp(service, capabilities)
            
            # Store service
            self.services[service.service_name] = service
            self._last_health_check[service.service_name] = datetime.utcnow()
            
            logger.info(f"Successfully registered external service: {service.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering service {service.service_name}: {e}")
            return False
    
    async def _register_capabilities_with_mcp(self, service: BaseExternalService, capabilities: Dict[str, List[str]]):
        """Register service capabilities with MCP server"""
        if not self.mcp_server:
            logger.warning("No MCP server available for capability registration")
            return
        
        # Register tools
        for tool_name in capabilities.get('tools', []):
            if tool_name in service.available_tools:
                tool = service.available_tools[tool_name] 
                mcp_tool_name = f"external_{service.service_name}_{tool_name}"
                
                # Create MCP tool wrapper
                async def tool_wrapper(**kwargs):
                    return await service.invoke_tool(tool_name, kwargs)
                
                # Add tool to MCP server
                self.mcp_server.add_tool(mcp_tool_name, tool_wrapper)
                logger.info(f"Registered MCP tool: {mcp_tool_name}")
        
        # Register resources as MCP resources if needed
        for resource_name in capabilities.get('resources', []):
            if resource_name in service.available_resources:
                resource = service.available_resources[resource_name]
                mcp_resource_name = f"external_{service.service_name}_{resource_name}"
                
                # Add resource to MCP server
                # Note: This depends on FastMCP's resource API
                logger.info(f"Registered MCP resource: {mcp_resource_name}")
    
    def set_mcp_server(self, mcp_server: FastMCP):
        """Set the MCP server for capability registration"""
        self.mcp_server = mcp_server
        logger.info("MCP server set for external service registry")
    
    async def get_service(self, service_name: str) -> Optional[BaseExternalService]:
        """Get a registered service by name"""
        return self.services.get(service_name)
    
    async def invoke_service_tool(self, service_name: str, tool_name: str, params: Dict[str, Any]) -> Any:
        """Invoke a tool on a specific service"""
        service = await self.get_service(service_name)
        if not service:
            raise ValueError(f"Service '{service_name}' not found")
        
        if not service.is_healthy:
            # Attempt to reconnect
            await service.connect()
            if not service.is_healthy:
                raise RuntimeError(f"Service '{service_name}' is not healthy")
        
        return await service.invoke_tool(tool_name, params)
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all registered services"""
        health_results = {}
        
        for service_name, service in self.services.items():
            try:
                # Check if we need to perform health check
                last_check = self._last_health_check.get(service_name)
                now = datetime.utcnow()
                
                if last_check and (now - last_check) < self._health_check_interval:
                    health_results[service_name] = service.is_healthy
                    continue
                
                # Perform health check
                is_healthy = await service.health_check()
                health_results[service_name] = is_healthy
                self._last_health_check[service_name] = now
                
                if not is_healthy:
                    logger.warning(f"Service {service_name} failed health check")
                
            except Exception as e:
                health_results[service_name] = False
                logger.error(f"Health check error for service {service_name}: {e}")
        
        return health_results
    
    async def reconnect_service(self, service_name: str) -> bool:
        """Attempt to reconnect a service"""
        service = await self.get_service(service_name)
        if not service:
            return False
        
        try:
            await service.disconnect()
            return await service.connect()
        except Exception as e:
            logger.error(f"Error reconnecting service {service_name}: {e}")
            return False
    
    async def disconnect_all(self):
        """Disconnect all services"""
        for service_name, service in self.services.items():
            try:
                await service.disconnect()
                logger.info(f"Disconnected service: {service_name}")
            except Exception as e:
                logger.error(f"Error disconnecting service {service_name}: {e}")
        
        self.services.clear()
        self._last_health_check.clear()
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered services"""
        status = {}
        for service_name, service in self.services.items():
            status[service_name] = service.get_service_info()
        return status
    
    def list_available_tools(self) -> Dict[str, List[str]]:
        """List all available tools across services"""
        tools_by_service = {}
        for service_name, service in self.services.items():
            tools_by_service[service_name] = list(service.available_tools.keys())
        return tools_by_service