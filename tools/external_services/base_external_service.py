wo#!/usr/bin/env python3
"""
Base External Service Classes

Provides abstract base classes and configuration for external service integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExternalServiceConfig:
    """Configuration for external service connections"""
    name: str
    service_type: str  # "mcp_server", "rest_api", "custom"
    connection_params: Dict[str, Any]
    auth_config: Optional[Dict[str, Any]] = None
    capabilities: List[str] = field(default_factory=list)
    enabled: bool = True
    timeout_seconds: int = 30
    retry_attempts: int = 3

@dataclass 
class ServiceTool:
    """Represents an external service tool"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    service_name: str
    
@dataclass
class ServiceResource:
    """Represents an external service resource"""
    name: str
    description: str
    resource_type: str  # "data", "config", "auth", etc.
    uri: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServicePrompt:
    """Represents an external service prompt template"""
    name: str
    description: str
    template: str
    parameters: List[str] = field(default_factory=list)

class BaseExternalService(ABC):
    """Abstract base class for external service integrations"""
    
    def __init__(self, config: ExternalServiceConfig):
        self.config = config
        self.is_connected = False
        self.connection_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        
        # Service capabilities
        self.available_tools: Dict[str, ServiceTool] = {}
        self.available_resources: Dict[str, ServiceResource] = {}
        self.available_prompts: Dict[str, ServicePrompt] = {}
        
        # Connection state
        self._client = None
        self._connection_metadata: Dict[str, Any] = {}
    
    @property
    def service_name(self) -> str:
        """Get the service name"""
        return self.config.name
    
    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy and connected"""
        return self.is_connected and self.last_error is None
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to external service
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from external service"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Perform health check on service
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def discover_capabilities(self) -> Dict[str, List[str]]:
        """
        Discover available tools, prompts, resources from service
        
        Returns:
            Dict with keys: 'tools', 'resources', 'prompts'
            Values are lists of capability names
        """
        pass
    
    @abstractmethod
    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Invoke a tool from the external service
        
        Args:
            tool_name: Name of the tool to invoke
            params: Parameters for the tool
            
        Returns:
            Tool execution result
        """
        pass
    
    async def get_resource(self, resource_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Get a resource from the external service
        
        Args:
            resource_name: Name of the resource
            params: Optional parameters for resource access
            
        Returns:
            Resource data
        """
        if resource_name not in self.available_resources:
            raise ValueError(f"Resource '{resource_name}' not available in service '{self.service_name}'")
        
        resource = self.available_resources[resource_name]
        return await self._fetch_resource(resource, params or {})
    
    async def render_prompt(self, prompt_name: str, params: Dict[str, Any]) -> str:
        """
        Render a prompt template from the external service
        
        Args:
            prompt_name: Name of the prompt template
            params: Parameters to fill in the template
            
        Returns:
            Rendered prompt text
        """
        if prompt_name not in self.available_prompts:
            raise ValueError(f"Prompt '{prompt_name}' not available in service '{self.service_name}'")
        
        prompt = self.available_prompts[prompt_name]
        return self._render_prompt_template(prompt.template, params)
    
    @abstractmethod
    async def _fetch_resource(self, resource: ServiceResource, params: Dict[str, Any]) -> Any:
        """Internal method to fetch resource data"""
        pass
    
    def _render_prompt_template(self, template: str, params: Dict[str, Any]) -> str:
        """Internal method to render prompt template"""
        try:
            return template.format(**params)
        except KeyError as e:
            raise ValueError(f"Missing parameter for prompt template: {e}")
    
    def _log_connection_attempt(self, success: bool, error: Optional[str] = None):
        """Log connection attempt"""
        if success:
            self.is_connected = True
            self.connection_time = datetime.utcnow()
            self.last_error = None
            logger.info(f"Successfully connected to external service: {self.service_name}")
        else:
            self.is_connected = False
            self.last_error = error
            logger.error(f"Failed to connect to external service {self.service_name}: {error}")
    
    def _log_tool_invocation(self, tool_name: str, success: bool, error: Optional[str] = None):
        """Log tool invocation"""
        if success:
            logger.info(f"Successfully invoked tool '{tool_name}' on service '{self.service_name}'")
        else:
            logger.error(f"Failed to invoke tool '{tool_name}' on service '{self.service_name}': {error}")
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and status"""
        return {
            "name": self.service_name,
            "type": self.config.service_type,
            "connected": self.is_connected,
            "healthy": self.is_healthy,
            "connection_time": self.connection_time.isoformat() if self.connection_time else None,
            "last_error": self.last_error,
            "capabilities": {
                "tools_count": len(self.available_tools),
                "resources_count": len(self.available_resources), 
                "prompts_count": len(self.available_prompts)
            },
            "tools": list(self.available_tools.keys()),
            "resources": list(self.available_resources.keys()),
            "prompts": list(self.available_prompts.keys())
        }