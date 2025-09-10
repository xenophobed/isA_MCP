#!/usr/bin/env python3
"""
Template for Custom External Service Integration

This is a template/example for creating custom external service integrations.
Copy this file and modify it to integrate with your own external services.
"""

import os
import logging
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..base_external_service import BaseExternalService, ExternalServiceConfig, ServiceTool, ServiceResource, ServicePrompt

logger = logging.getLogger(__name__)

class CustomTemplateService(BaseExternalService):
    """
    Template for custom external service integration
    
    This class demonstrates how to create a custom external service connector.
    Replace the implementation with your specific service logic.
    """
    
    def __init__(self, config: ExternalServiceConfig):
        super().__init__(config)
        self.session = None
        self.base_url = None
        self.api_version = None
        self.auth_headers = {}
    
    async def connect(self) -> bool:
        """Connect to custom external service"""
        try:
            # Get connection parameters
            self.base_url = self.config.connection_params.get('base_url')
            self.api_version = self.config.connection_params.get('api_version', 'v1')
            
            if not self.base_url:
                error_msg = "base_url is required in connection parameters"
                self._log_connection_attempt(False, error_msg)
                return False
            
            # Setup authentication
            auth_config = self.config.auth_config or {}
            auth_method = auth_config.get('method')
            
            if auth_method == 'api_key':
                api_key = self._resolve_env_var(auth_config.get('api_key'))
                self.auth_headers['X-API-Key'] = api_key
            elif auth_method == 'bearer_token':
                token = self._resolve_env_var(auth_config.get('token'))
                self.auth_headers['Authorization'] = f'Bearer {token}'
            elif auth_method == 'basic_auth':
                username = self._resolve_env_var(auth_config.get('username'))
                password = self._resolve_env_var(auth_config.get('password'))
                # For basic auth, you'd typically use aiohttp's BasicAuth
                # self.auth = aiohttp.BasicAuth(username, password)
                
            # Create HTTP session
            self.session = aiohttp.ClientSession(headers=self.auth_headers)
            
            # Test connection
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    self._log_connection_attempt(True)
                    return True
                else:
                    error_msg = f"Health check failed with status {response.status}"
                    self._log_connection_attempt(False, error_msg)
                    return False
                    
        except Exception as e:
            error_msg = f"Custom service connection failed: {str(e)}"
            self._log_connection_attempt(False, error_msg)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from custom external service"""
        if self.session:
            await self.session.close()
            self.session = None
        self.auth_headers.clear()
        self.is_connected = False
        logger.info(f"Disconnected from custom service: {self.service_name}")
    
    async def health_check(self) -> bool:
        """Perform health check on custom service"""
        if not self.is_connected or not self.session:
            return False
        
        try:
            async with self.session.get(f"{self.base_url}/health", timeout=5) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Custom service health check failed: {e}")
            return False
    
    async def discover_capabilities(self) -> Dict[str, List[str]]:
        """Discover custom service capabilities"""
        if not self.is_connected:
            return {"tools": [], "resources": [], "prompts": []}
        
        # Example capabilities - replace with your service's actual capabilities
        tools = [
            "custom_action_1",
            "custom_action_2", 
            "send_notification",
            "get_data",
            "process_request"
        ]
        
        resources = [
            "service_status",
            "available_endpoints",
            "configuration"
        ]
        
        prompts = [
            "request_formatting_prompt",
            "error_handling_prompt"
        ]
        
        # Create tool objects
        for tool_name in tools:
            self.available_tools[tool_name] = self._create_tool_definition(tool_name)
        
        # Create resource objects
        for resource_name in resources:
            self.available_resources[resource_name] = self._create_resource_definition(resource_name)
        
        # Create prompt objects
        for prompt_name in prompts:
            self.available_prompts[prompt_name] = self._create_prompt_definition(prompt_name)
        
        return {
            "tools": tools,
            "resources": resources,
            "prompts": prompts
        }
    
    def _create_tool_definition(self, tool_name: str) -> ServiceTool:
        """Create tool definition for custom tools"""
        tool_definitions = {
            "custom_action_1": ServiceTool(
                name="custom_action_1",
                description="Perform custom action 1",
                parameters={"input": "Input data for the action"},
                handler=self._handle_custom_action_1,
                service_name=self.service_name
            ),
            "custom_action_2": ServiceTool(
                name="custom_action_2",
                description="Perform custom action 2",
                parameters={"config": "Configuration for the action"},
                handler=self._handle_custom_action_2,
                service_name=self.service_name
            ),
            "send_notification": ServiceTool(
                name="send_notification",
                description="Send a notification through the service",
                parameters={
                    "recipient": "Notification recipient",
                    "message": "Notification message",
                    "priority": "Notification priority (low/medium/high)"
                },
                handler=self._handle_send_notification,
                service_name=self.service_name
            ),
            "get_data": ServiceTool(
                name="get_data",
                description="Get data from the service",
                parameters={
                    "endpoint": "API endpoint to query",
                    "filters": "Optional filters for the query"
                },
                handler=self._handle_get_data,
                service_name=self.service_name
            ),
            "process_request": ServiceTool(
                name="process_request",
                description="Process a generic request",
                parameters={"request_data": "Request data to process"},
                handler=self._handle_process_request,
                service_name=self.service_name
            )
        }
        
        return tool_definitions.get(tool_name, ServiceTool(
            name=tool_name,
            description=f"Execute {tool_name}",
            parameters={"params": "Tool parameters"},
            handler=self._handle_generic_tool,
            service_name=self.service_name
        ))
    
    def _create_resource_definition(self, resource_name: str) -> ServiceResource:
        """Create resource definition for custom resources"""
        resource_definitions = {
            "service_status": ServiceResource(
                name="service_status",
                description="Current status of the custom service",
                resource_type="status",
                uri=f"custom://{self.service_name}/status"
            ),
            "available_endpoints": ServiceResource(
                name="available_endpoints",
                description="List of available API endpoints",
                resource_type="data",
                uri=f"custom://{self.service_name}/endpoints"
            ),
            "configuration": ServiceResource(
                name="configuration",
                description="Service configuration information",
                resource_type="config",
                uri=f"custom://{self.service_name}/config"
            )
        }
        
        return resource_definitions.get(resource_name)
    
    def _create_prompt_definition(self, prompt_name: str) -> ServicePrompt:
        """Create prompt definition for custom prompts"""
        prompt_definitions = {
            "request_formatting_prompt": ServicePrompt(
                name="request_formatting_prompt",
                description="Format requests for the custom service",
                template="Format this request for {service_name}: {request}. Required format: {format_spec}",
                parameters=["service_name", "request", "format_spec"]
            ),
            "error_handling_prompt": ServicePrompt(
                name="error_handling_prompt",
                description="Handle errors from the custom service",
                template="Handle this error from {service_name}: {error}. Suggest resolution: {context}",
                parameters=["service_name", "error", "context"]
            )
        }
        
        return prompt_definitions.get(prompt_name)
    
    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Invoke a custom tool"""
        if not self.is_connected:
            raise RuntimeError(f"Custom service {self.service_name} is not connected")
        
        if tool_name not in self.available_tools:
            raise ValueError(f"Tool '{tool_name}' not available in custom service")
        
        tool = self.available_tools[tool_name]
        
        try:
            result = await tool.handler(params)
            self._log_tool_invocation(tool_name, True)
            return result
        except Exception as e:
            error_msg = f"Tool invocation failed: {str(e)}"
            self._log_tool_invocation(tool_name, False, error_msg)
            raise
    
    # Tool handler methods - implement your custom logic here
    async def _handle_custom_action_1(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom action 1"""
        input_data = params.get('input')
        
        try:
            # Example: Make API call to your service
            async with self.session.post(
                f"{self.base_url}/api/{self.api_version}/action1",
                json={"input": input_data}
            ) as response:
                result_data = await response.json()
                
                return {
                    "success": response.status == 200,
                    "result": result_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_custom_action_2(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom action 2"""
        config = params.get('config', {})
        
        # Implement your custom logic here
        return {
            "success": True,
            "message": "Custom action 2 executed",
            "config": config,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_send_notification(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sending notification"""
        recipient = params.get('recipient')
        message = params.get('message')
        priority = params.get('priority', 'medium')
        
        if not all([recipient, message]):
            raise ValueError("recipient and message are required")
        
        try:
            # Example: Send notification via your service API
            async with self.session.post(
                f"{self.base_url}/api/{self.api_version}/notifications",
                json={
                    "recipient": recipient,
                    "message": message,
                    "priority": priority
                }
            ) as response:
                return {
                    "success": response.status == 200,
                    "notification_id": (await response.json()).get('id'),
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_get_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle getting data"""
        endpoint = params.get('endpoint', 'data')
        filters = params.get('filters', {})
        
        try:
            # Build query parameters
            query_params = {k: v for k, v in filters.items() if v is not None}
            
            async with self.session.get(
                f"{self.base_url}/api/{self.api_version}/{endpoint}",
                params=query_params
            ) as response:
                data = await response.json()
                
                return {
                    "success": response.status == 200,
                    "data": data,
                    "count": len(data) if isinstance(data, list) else 1,
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_process_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle processing a request"""
        request_data = params.get('request_data')
        
        if not request_data:
            raise ValueError("request_data is required")
        
        # Implement your custom request processing logic
        return {
            "success": True,
            "message": "Request processed successfully",
            "processed_data": request_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_generic_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generic tool handler"""
        return {
            "success": True,
            "message": "Generic tool executed",
            "params": params,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _fetch_resource(self, resource: ServiceResource, params: Dict[str, Any]) -> Any:
        """Fetch resource data from custom service"""
        if resource.name == "service_status":
            return {
                "connected": self.is_connected,
                "base_url": self.base_url,
                "api_version": self.api_version,
                "last_health_check": datetime.utcnow().isoformat()
            }
        elif resource.name == "available_endpoints":
            # Return available endpoints (mock data - implement your logic)
            return [
                {"path": "/api/v1/action1", "method": "POST"},
                {"path": "/api/v1/action2", "method": "POST"},
                {"path": "/api/v1/data", "method": "GET"},
                {"path": "/api/v1/notifications", "method": "POST"}
            ]
        elif resource.name == "configuration":
            return {
                "service_name": self.service_name,
                "service_type": self.config.service_type,
                "connection_params": self.config.connection_params,
                "capabilities": self.config.capabilities
            }
        else:
            raise ValueError(f"Unknown resource: {resource.name}")
    
    def _resolve_env_var(self, value: str) -> str:
        """Resolve environment variable references in configuration values"""
        if value and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]  # Remove ${ and }
            return os.environ.get(env_var, value)
        return value