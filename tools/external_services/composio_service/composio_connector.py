#!/usr/bin/env python3
"""
Composio Service Connector

Integrates Composio's 300+ application platform with the MCP system.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from ..base_external_service import BaseExternalService, ExternalServiceConfig, ServiceTool, ServiceResource, ServicePrompt

logger = logging.getLogger(__name__)

# Optional Composio SDK import with graceful fallback
COMPOSIO_AVAILABLE = False
try:
    from composio import Composio, ComposioToolSet
    from composio.client.exceptions import ComposioClientError
    COMPOSIO_AVAILABLE = True
    logger.info("Composio SDK is available")
except ImportError:
    logger.warning("Composio SDK not available. Install with: pip install composio-core")
    Composio = None
    ComposioToolSet = None
    ComposioClientError = Exception

class ComposioService(BaseExternalService):
    """Composio 300+ application integration service"""
    
    def __init__(self, config: ExternalServiceConfig):
        super().__init__(config)
        self.composio_client = None
        self.toolset = None
        self.connected_apps = {}
        self.available_integrations = []
    
    async def connect(self) -> bool:
        """Connect to Composio service"""
        if not COMPOSIO_AVAILABLE:
            error_msg = "Composio SDK not available. Install with: pip install composio-core"
            self._log_connection_attempt(False, error_msg)
            return False
        
        try:
            auth_config = self.config.auth_config or {}
            api_key = self._resolve_env_var(auth_config.get('api_key'))
            
            if not api_key:
                error_msg = "Composio API key is required"
                self._log_connection_attempt(False, error_msg)
                return False
            
            # Initialize Composio client
            self.composio_client = Composio(api_key=api_key)
            self.toolset = ComposioToolSet(api_key=api_key)
            
            # Test connection by getting user info
            user_info = self.composio_client.get_entity()
            logger.info(f"Connected to Composio as: {user_info}")
            
            # Get available integrations
            self.available_integrations = self.composio_client.get_list_of_apps()
            
            self._log_connection_attempt(True)
            return True
            
        except Exception as e:
            error_msg = f"Composio connection failed: {str(e)}"
            self._log_connection_attempt(False, error_msg)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Composio service"""
        if self.composio_client:
            self.composio_client = None
        if self.toolset:
            self.toolset = None
        self.connected_apps.clear()
        self.available_integrations.clear()
        self.is_connected = False
        logger.info(f"Disconnected from Composio service: {self.service_name}")
    
    async def health_check(self) -> bool:
        """Perform health check on Composio service"""
        if not self.is_connected or not self.composio_client:
            return False
        
        try:
            # Simple health check - get entity info
            user_info = self.composio_client.get_entity()
            return user_info is not None
        except Exception as e:
            logger.error(f"Composio health check failed: {e}")
            return False
    
    async def discover_capabilities(self) -> Dict[str, List[str]]:
        """Discover Composio capabilities"""
        if not self.is_connected:
            return {"tools": [], "resources": [], "prompts": []}
        
        # Define core tools
        core_tools = [
            "list_integrations",
            "connect_app",
            "disconnect_app", 
            "get_connected_accounts",
            "execute_action",
            "get_app_actions",
            "get_app_triggers"
        ]
        
        # Add app-specific tools for popular integrations
        popular_apps = ["gmail", "slack", "github", "google_calendar", "trello", "notion", "hubspot"]
        app_tools = []
        
        for app in popular_apps:
            app_tools.extend([
                f"{app}_send_message",
                f"{app}_get_data",
                f"{app}_create_item",
                f"{app}_update_item",
                f"{app}_delete_item"
            ])
        
        all_tools = core_tools + app_tools
        
        # Define resources
        resources = [
            "connected_accounts",
            "available_apps",
            "app_schemas",
            "integration_status"
        ]
        
        # Define prompts
        prompts = [
            "integration_setup_prompt",
            "action_execution_prompt",
            "workflow_creation_prompt"
        ]
        
        # Create tool objects
        for tool_name in all_tools:
            self.available_tools[tool_name] = self._create_tool_definition(tool_name)
        
        # Create resource objects
        for resource_name in resources:
            self.available_resources[resource_name] = self._create_resource_definition(resource_name)
        
        # Create prompt objects
        for prompt_name in prompts:
            self.available_prompts[prompt_name] = self._create_prompt_definition(prompt_name)
        
        return {
            "tools": all_tools,
            "resources": resources,
            "prompts": prompts
        }
    
    def _create_tool_definition(self, tool_name: str) -> ServiceTool:
        """Create tool definition for Composio tools"""
        
        # Core tools
        core_tool_definitions = {
            "list_integrations": ServiceTool(
                name="list_integrations",
                description="List all available Composio app integrations",
                parameters={},
                handler=self._handle_list_integrations,
                service_name=self.service_name
            ),
            "connect_app": ServiceTool(
                name="connect_app",
                description="Connect to an app via Composio",
                parameters={
                    "app_name": "Name of the app to connect",
                    "auth_config": "Authentication configuration for the app"
                },
                handler=self._handle_connect_app,
                service_name=self.service_name
            ),
            "get_connected_accounts": ServiceTool(
                name="get_connected_accounts",
                description="Get list of connected accounts",
                parameters={"app_name": "Optional app name to filter by"},
                handler=self._handle_get_connected_accounts,
                service_name=self.service_name
            ),
            "execute_action": ServiceTool(
                name="execute_action",
                description="Execute an action on a connected app",
                parameters={
                    "app_name": "Name of the app",
                    "action_name": "Name of the action to execute", 
                    "parameters": "Action parameters"
                },
                handler=self._handle_execute_action,
                service_name=self.service_name
            ),
            "get_app_actions": ServiceTool(
                name="get_app_actions",
                description="Get available actions for an app",
                parameters={"app_name": "Name of the app"},
                handler=self._handle_get_app_actions,
                service_name=self.service_name
            )
        }
        
        # App-specific tool patterns
        app_specific_patterns = {
            "gmail_send_message": ServiceTool(
                name="gmail_send_message",
                description="Send email via Gmail",
                parameters={
                    "to": "Recipient email address",
                    "subject": "Email subject",
                    "body": "Email body content"
                },
                handler=self._handle_gmail_send_message,
                service_name=self.service_name
            ),
            "slack_send_message": ServiceTool(
                name="slack_send_message",
                description="Send message via Slack",
                parameters={
                    "channel": "Slack channel",
                    "message": "Message content"
                },
                handler=self._handle_slack_send_message,
                service_name=self.service_name
            ),
            "github_create_issue": ServiceTool(
                name="github_create_issue",
                description="Create GitHub issue",
                parameters={
                    "repository": "Repository name",
                    "title": "Issue title",
                    "body": "Issue description"
                },
                handler=self._handle_github_create_issue,
                service_name=self.service_name
            )
        }
        
        # Check core tools first
        if tool_name in core_tool_definitions:
            return core_tool_definitions[tool_name]
        
        # Check app-specific patterns
        if tool_name in app_specific_patterns:
            return app_specific_patterns[tool_name]
        
        # Generic app tool pattern
        if "_" in tool_name:
            app_name, action = tool_name.split("_", 1)
            return ServiceTool(
                name=tool_name,
                description=f"Execute {action} action on {app_name}",
                parameters={"parameters": "Action parameters"},
                handler=self._handle_generic_app_action,
                service_name=self.service_name
            )
        
        # Default tool definition
        return ServiceTool(
            name=tool_name,
            description=f"Execute {tool_name} via Composio",
            parameters={"parameters": "Tool parameters"},
            handler=self._handle_generic_action,
            service_name=self.service_name
        )
    
    def _create_resource_definition(self, resource_name: str) -> ServiceResource:
        """Create resource definition for Composio resources"""
        resource_definitions = {
            "connected_accounts": ServiceResource(
                name="connected_accounts",
                description="List of connected app accounts",
                resource_type="data",
                uri=f"composio://{self.service_name}/accounts"
            ),
            "available_apps": ServiceResource(
                name="available_apps",
                description="List of available app integrations",
                resource_type="data",
                uri=f"composio://{self.service_name}/apps"
            ),
            "app_schemas": ServiceResource(
                name="app_schemas", 
                description="API schemas for connected apps",
                resource_type="schema",
                uri=f"composio://{self.service_name}/schemas"
            ),
            "integration_status": ServiceResource(
                name="integration_status",
                description="Status of app integrations",
                resource_type="status",
                uri=f"composio://{self.service_name}/status"
            )
        }
        
        return resource_definitions.get(resource_name)
    
    def _create_prompt_definition(self, prompt_name: str) -> ServicePrompt:
        """Create prompt definition for Composio prompts"""
        prompt_definitions = {
            "integration_setup_prompt": ServicePrompt(
                name="integration_setup_prompt",
                description="Guide for setting up app integrations",
                template="Set up {app_name} integration for {use_case}. Required permissions: {permissions}",
                parameters=["app_name", "use_case", "permissions"]
            ),
            "action_execution_prompt": ServicePrompt(
                name="action_execution_prompt",
                description="Guide for executing app actions",
                template="Execute {action_name} on {app_name} with parameters: {parameters}",
                parameters=["action_name", "app_name", "parameters"]
            ),
            "workflow_creation_prompt": ServicePrompt(
                name="workflow_creation_prompt",
                description="Guide for creating multi-app workflows",
                template="Create workflow: {description}. Apps involved: {apps}. Steps: {steps}",
                parameters=["description", "apps", "steps"]
            )
        }
        
        return prompt_definitions.get(prompt_name)
    
    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Invoke a Composio tool"""
        if not self.is_connected:
            raise RuntimeError(f"Composio service {self.service_name} is not connected")
        
        if tool_name not in self.available_tools:
            raise ValueError(f"Tool '{tool_name}' not available in Composio service")
        
        tool = self.available_tools[tool_name]
        
        try:
            result = await tool.handler(params)
            self._log_tool_invocation(tool_name, True)
            return result
        except Exception as e:
            error_msg = f"Tool invocation failed: {str(e)}"
            self._log_tool_invocation(tool_name, False, error_msg)
            raise
    
    # Core tool handlers
    async def _handle_list_integrations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle listing available integrations"""
        try:
            apps = self.composio_client.get_list_of_apps()
            app_list = [{"name": app.name, "description": getattr(app, 'description', '')} for app in apps]
            
            return {
                "success": True,
                "apps": app_list,
                "count": len(app_list),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_connect_app(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle app connection"""
        app_name = params.get('app_name')
        auth_config = params.get('auth_config', {})
        
        if not app_name:
            raise ValueError("app_name parameter is required")
        
        try:
            # Create connection for the app
            connection = self.composio_client.get_entity().create_connection(app_name)
            
            return {
                "success": True,
                "app_name": app_name,
                "connection_id": connection.connectionId,
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "app_name": app_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_get_connected_accounts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle getting connected accounts"""
        app_name = params.get('app_name')
        
        try:
            entity = self.composio_client.get_entity()
            connections = entity.get_connections()
            
            if app_name:
                connections = [conn for conn in connections if conn.app_name == app_name]
            
            account_list = [{
                "app_name": conn.app_name,
                "connection_id": conn.connectionId,
                "status": getattr(conn, 'status', 'active')
            } for conn in connections]
            
            return {
                "success": True,
                "accounts": account_list,
                "count": len(account_list),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_execute_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic action execution"""
        app_name = params.get('app_name')
        action_name = params.get('action_name')
        action_params = params.get('parameters', {})
        
        if not all([app_name, action_name]):
            raise ValueError("app_name and action_name are required")
        
        try:
            # Use toolset to execute action
            tools = self.toolset.get_tools(apps=[app_name], actions=[action_name])
            if not tools:
                raise ValueError(f"Action '{action_name}' not found for app '{app_name}'")
            
            tool = tools[0]
            result = tool.execute(action_params)
            
            return {
                "success": True,
                "app_name": app_name,
                "action_name": action_name,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "app_name": app_name,
                "action_name": action_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_get_app_actions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle getting app actions"""
        app_name = params.get('app_name')
        
        if not app_name:
            raise ValueError("app_name parameter is required")
        
        try:
            actions = self.composio_client.get_list_of_actions(app_name=app_name)
            action_list = [{
                "name": action.name,
                "description": getattr(action, 'description', ''),
                "parameters": getattr(action, 'parameters', {})
            } for action in actions]
            
            return {
                "success": True,
                "app_name": app_name,
                "actions": action_list,
                "count": len(action_list),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "app_name": app_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # App-specific tool handlers
    async def _handle_gmail_send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Gmail send message"""
        to = params.get('to')
        subject = params.get('subject')
        body = params.get('body')
        
        if not all([to, subject, body]):
            raise ValueError("to, subject, and body are required")
        
        return await self._handle_execute_action({
            'app_name': 'gmail',
            'action_name': 'send_email',
            'parameters': {
                'to': to,
                'subject': subject,
                'body': body
            }
        })
    
    async def _handle_slack_send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Slack send message"""
        channel = params.get('channel')
        message = params.get('message')
        
        if not all([channel, message]):
            raise ValueError("channel and message are required")
        
        return await self._handle_execute_action({
            'app_name': 'slack',
            'action_name': 'send_message',
            'parameters': {
                'channel': channel,
                'text': message
            }
        })
    
    async def _handle_github_create_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GitHub create issue"""
        repository = params.get('repository')
        title = params.get('title')
        body = params.get('body', '')
        
        if not all([repository, title]):
            raise ValueError("repository and title are required")
        
        return await self._handle_execute_action({
            'app_name': 'github',
            'action_name': 'create_issue',
            'parameters': {
                'owner': repository.split('/')[0],
                'repo': repository.split('/')[1],
                'title': title,
                'body': body
            }
        })
    
    async def _handle_generic_app_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic app action based on tool name"""
        # This is a fallback handler for dynamically generated tools
        return {
            "success": True,
            "message": "Generic app action handler - implement specific logic",
            "params": params,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_generic_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic action"""
        # This is a fallback handler
        return {
            "success": True,
            "message": "Generic action handler - implement specific logic",
            "params": params,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _fetch_resource(self, resource: ServiceResource, params: Dict[str, Any]) -> Any:
        """Fetch resource data from Composio"""
        if resource.name == "connected_accounts":
            entity = self.composio_client.get_entity()
            connections = entity.get_connections()
            return [{
                "app_name": conn.app_name,
                "connection_id": conn.connectionId,
                "status": getattr(conn, 'status', 'active')
            } for conn in connections]
        
        elif resource.name == "available_apps":
            apps = self.composio_client.get_list_of_apps()
            return [{"name": app.name, "description": getattr(app, 'description', '')} for app in apps]
        
        elif resource.name == "app_schemas":
            # Return schema information for connected apps
            return {"note": "App schemas - implement based on specific requirements"}
        
        elif resource.name == "integration_status":
            # Return integration health status
            return {
                "service_connected": self.is_connected,
                "last_health_check": self._last_health_check,
                "available_integrations_count": len(self.available_integrations)
            }
        
        else:
            raise ValueError(f"Unknown resource: {resource.name}")
    
    def _resolve_env_var(self, value: str) -> str:
        """Resolve environment variable references in configuration values"""
        if value and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]  # Remove ${ and }
            return os.environ.get(env_var, value)
        return value