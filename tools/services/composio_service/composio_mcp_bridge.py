#!/usr/bin/env python3
"""
Composio MCP Bridge
Dynamically converts Composio apps into MCP tools
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger

logger = get_logger(__name__)


class ComposioMCPBridge:
    """Bridge between Composio apps and MCP tool system"""

    def __init__(self, composio_service):
        self.composio_service = composio_service
        self.registered_tools = {}
        self.user_connections = {}  # Store per-user connections

    async def register_composio_tools_with_mcp(self, mcp):
        """Dynamically register Composio apps as MCP tools

        Returns:
            Dict[str, Dict]: 已注册工具的元数据，用于搜索索引
            格式: {tool_name: {description, category, keywords, ...}}
        """
        logger.info("🌉 Registering Composio apps as MCP tools...")

        if not self.composio_service or not self.composio_service.is_connected:
            logger.warning("Composio service not connected")
            return {}

        # Try to get security manager, fall back to no security if not initialized
        try:
            security_manager = get_security_manager()
        except RuntimeError:
            logger.warning(
                "Security manager not initialized, registering tools without security decorators"
            )
            security_manager = None

        # 存储所有注册工具的元数据
        tools_metadata = {}

        # Register core management tools first
        management_tools = await self._register_management_tools(mcp, security_manager)
        tools_metadata.update(management_tools)

        # Get available apps from Composio
        try:
            result = await self.composio_service.invoke_tool("list_integrations", {})
            if result.get("success"):
                apps = result.get("apps", [])
                logger.info(f"Found {len(apps)} Composio apps to register")

                # Register top 20 apps for testing
                priority_apps = [
                    "gmail",
                    "slack",
                    "github",
                    "notion",
                    "googlecalendar",
                    "discord",
                    "telegram",
                    "asana",
                    "trello",
                    "dropbox",
                    "googledrive",
                    "hubspot",
                    "salesforce",
                    "jira",
                    "linear",
                    "mailchimp",
                    "airtable",
                    "zoom",
                    "stripe",
                    "shopify",
                ]

                logger.info(f"🧪 Testing with {len(priority_apps)} priority apps...")

                registered_count = 0
                for app in apps:
                    app_name = app.get("name", "").lower()
                    if app_name in priority_apps:
                        app_tools_metadata = await self._register_app_as_tools(
                            mcp, app, security_manager
                        )
                        tools_metadata.update(app_tools_metadata)
                        registered_count += 1
                        logger.info(
                            f"  ✅ Registered {app_name} ({registered_count}/{len(priority_apps)})"
                        )

                logger.info(
                    f"  🎉 Successfully registered {registered_count} priority Composio apps!"
                )
                logger.info(f"  📊 Total tools registered: {len(tools_metadata)}")

        except Exception as e:
            logger.error(f"Failed to register Composio tools: {e}")

        return tools_metadata

    async def _register_management_tools(self, mcp, security_manager):
        """Register Composio management tools

        Returns:
            Dict[str, Dict]: 管理工具的元数据
        """
        tools_metadata = {}

        # Tool 1: Connect app
        async def composio_connect_app(app_name: str, user_id: str = "default") -> str:
            """Connect a user's account to a Composio app (Gmail, Slack, etc.)

            This initiates the OAuth flow to connect a user's account to an app.
            Each user can have their own connections to different apps.

            Args:
                app_name: Name of the app to connect (e.g., "gmail", "slack")
                user_id: Unique user identifier for account isolation

            Returns:
                JSON with connection URL or status

            Keywords: composio, connect, oauth, integration, app, gmail, slack, github
            Category: integration
            """
            try:
                # Create user-specific connection
                result = await self.composio_service.invoke_tool(
                    "connect_app", {"app_name": app_name, "auth_config": {"entity_id": user_id}}
                )

                if result.get("success"):
                    # Check if this is an OAuth flow response
                    if result.get("status") == "oauth_required":
                        # Return OAuth response directly
                        return json.dumps(
                            {
                                "status": "oauth_required",
                                "oauth_url": result.get("oauth_url"),
                                "connection_request_id": result.get("connection_request_id"),
                                "message": result.get("message"),
                                "instructions": result.get("instructions"),
                                "app_name": app_name,
                                "user_id": user_id,
                            },
                            indent=2,
                        )
                    else:
                        # Legacy connection response
                        connection_id = result.get("connection_id")

                        # Store user connection mapping
                        if user_id not in self.user_connections:
                            self.user_connections[user_id] = {}
                        self.user_connections[user_id][app_name] = connection_id

                        return json.dumps(
                            {
                                "status": "success",
                                "message": f"Connected {app_name} for user {user_id}",
                                "connection_id": connection_id,
                                "app_name": app_name,
                                "user_id": user_id,
                            },
                            indent=2,
                        )
                else:
                    return json.dumps(
                        {
                            "status": "error",
                            "message": result.get("error", "Connection failed"),
                            "app_name": app_name,
                        },
                        indent=2,
                    )

            except Exception as e:
                logger.error(f"Error connecting {app_name} for {user_id}: {e}")
                return json.dumps(
                    {"status": "error", "message": str(e), "app_name": app_name}, indent=2
                )

        # Register composio_connect_app
        if security_manager:
            composio_connect_app = security_manager.require_authorization(SecurityLevel.LOW)(
                composio_connect_app
            )
        mcp.tool()(composio_connect_app)

        tools_metadata["composio_connect_app"] = {
            "description": "Connect a user's account to a Composio app (Gmail, Slack, etc.)",
            "category": "integration",
            "keywords": [
                "composio",
                "connect",
                "oauth",
                "integration",
                "app",
                "gmail",
                "slack",
                "github",
            ],
        }

        # Tool 2: List user connections
        async def composio_list_user_connections(user_id: str = "default") -> str:
            """List all connected apps for a specific user

            Shows which apps the user has connected via Composio.

            Args:
                user_id: User identifier

            Returns:
                JSON with list of connected apps and their status

            Keywords: composio, connections, apps, list, user, status
            Category: integration
            """
            try:
                result = await self.composio_service.invoke_tool(
                    "get_connected_accounts", {"user_id": user_id}
                )

                if result.get("success"):
                    accounts = result.get("accounts", [])

                    # Filter for this user
                    user_accounts = []
                    for account in accounts:
                        # Check if this account belongs to the user
                        if user_id in self.user_connections:
                            if account.get("app_name") in self.user_connections[user_id]:
                                user_accounts.append(account)

                    return json.dumps(
                        {
                            "status": "success",
                            "user_id": user_id,
                            "connected_apps": user_accounts,
                            "count": len(user_accounts),
                        },
                        indent=2,
                    )
                else:
                    return json.dumps(
                        {
                            "status": "error",
                            "message": result.get("error", "Failed to get connections"),
                        },
                        indent=2,
                    )

            except Exception as e:
                logger.error(f"Error listing connections for {user_id}: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)

        # Register composio_list_user_connections
        if security_manager:
            composio_list_user_connections = security_manager.require_authorization(
                SecurityLevel.LOW
            )(composio_list_user_connections)
        mcp.tool()(composio_list_user_connections)

        tools_metadata["composio_list_user_connections"] = {
            "description": "List all connected apps for a specific user",
            "category": "integration",
            "keywords": ["composio", "connections", "apps", "list", "user", "status"],
        }

        # Tool 3: List available apps
        async def composio_list_available_apps() -> str:
            """List all available Composio apps that can be connected

            Shows the 745+ apps available through Composio integration.

            Returns:
                JSON with list of available apps

            Keywords: composio, apps, available, integrations, list
            Category: integration
            """
            try:
                result = await self.composio_service.invoke_tool("list_integrations", {})

                if result.get("success"):
                    apps = result.get("apps", [])

                    # Group apps by category for better organization
                    categorized = {
                        "communication": [],
                        "productivity": [],
                        "development": [],
                        "crm": [],
                        "other": [],
                    }

                    for app in apps[:50]:  # Limit to first 50 for readability
                        app_name = app.get("name", "").lower()
                        if any(x in app_name for x in ["gmail", "slack", "discord", "telegram"]):
                            categorized["communication"].append(app_name)
                        elif any(x in app_name for x in ["notion", "trello", "asana", "calendar"]):
                            categorized["productivity"].append(app_name)
                        elif any(x in app_name for x in ["github", "gitlab", "jira"]):
                            categorized["development"].append(app_name)
                        elif any(x in app_name for x in ["hubspot", "salesforce", "pipedrive"]):
                            categorized["crm"].append(app_name)
                        else:
                            categorized["other"].append(app_name)

                    return json.dumps(
                        {
                            "status": "success",
                            "total_apps": len(apps),
                            "categories": categorized,
                            "message": f"Showing first 50 of {len(apps)} available apps",
                        },
                        indent=2,
                    )
                else:
                    return json.dumps(
                        {"status": "error", "message": result.get("error", "Failed to list apps")},
                        indent=2,
                    )

            except Exception as e:
                logger.error(f"Error listing available apps: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)

        # Register composio_list_available_apps
        if security_manager:
            composio_list_available_apps = security_manager.require_authorization(
                SecurityLevel.LOW
            )(composio_list_available_apps)
        mcp.tool()(composio_list_available_apps)

        tools_metadata["composio_list_available_apps"] = {
            "description": "List all available Composio apps that can be connected",
            "category": "integration",
            "keywords": ["composio", "apps", "available", "integrations", "list"],
        }

        logger.info("✅ Registered Composio management tools")
        return tools_metadata

    async def _register_app_as_tools(self, mcp, app_info: Dict, security_manager):
        """Register a specific Composio app as MCP tools

        Returns:
            Dict[str, Dict]: 注册工具的元数据
        """
        app_name = app_info.get("name", "").lower()
        tools_metadata = {}

        # Create dynamic tool functions for common actions
        tool1_meta = await self._create_dynamic_tool(
            mcp,
            app_name,
            "send_message",
            f"Send a message via {app_name.title()}",
            security_manager,
        )
        if tool1_meta:
            tools_metadata.update(tool1_meta)

        tool2_meta = await self._create_dynamic_tool(
            mcp, app_name, "get_data", f"Get data from {app_name.title()}", security_manager
        )
        if tool2_meta:
            tools_metadata.update(tool2_meta)

        return tools_metadata

    async def _create_dynamic_tool(
        self, mcp, app_name: str, action: str, description: str, security_manager
    ):
        """Create a dynamic MCP tool for a Composio app action

        Returns:
            Dict[str, Dict]: 工具元数据
        """

        tool_name = f"composio_{app_name}_{action}"

        # Skip if already registered
        if tool_name in self.registered_tools:
            return {}

        # Define the dynamic tool function
        async def dynamic_composio_tool(
            parameters: Dict[str, Any] = None, user_id: str = "default"
        ) -> str:
            """Dynamic Composio tool wrapper"""
            try:
                # Check if user has connected this app
                if (
                    user_id not in self.user_connections
                    or app_name not in self.user_connections[user_id]
                ):
                    # Return HIL format to trigger authorization flow
                    return json.dumps(
                        {
                            "status": "authorization_requested",
                            "action": "ask_human",
                            "question": f"Authorization required for {app_name.title()}",
                            "message": f"To use {app_name.title()} for {action}, you need to authorize access. Would you like to connect your {app_name.title()} account?",
                            "context": f"This action requires access to your {app_name.title()} account to {action}.",
                            "app_name": app_name,
                            "tool_name": tool_name,
                            "original_action": action,
                            "user_id": user_id,
                            "data": {
                                "request_type": "oauth_authorization",
                                "app": app_name,
                                "scope": action,
                            },
                        },
                        indent=2,
                    )

                # Execute the action via Composio
                result = await self.composio_service.invoke_tool(
                    "execute_action",
                    {
                        "app_name": app_name,
                        "action_name": action,
                        "parameters": parameters or {},
                        "entity_id": user_id,
                    },
                )

                if result.get("success"):
                    return json.dumps(
                        {
                            "status": "success",
                            "app": app_name,
                            "action": action,
                            "result": result.get("result"),
                            "user_id": user_id,
                            "timestamp": datetime.now().isoformat(),
                        },
                        indent=2,
                    )
                else:
                    return json.dumps(
                        {
                            "status": "error",
                            "message": result.get("error", "Action failed"),
                            "app": app_name,
                            "action": action,
                        },
                        indent=2,
                    )

            except Exception as e:
                logger.error(f"Error executing {app_name}.{action}: {e}")
                return json.dumps(
                    {"status": "error", "message": str(e), "app": app_name, "action": action},
                    indent=2,
                )

        # Set function metadata
        dynamic_composio_tool.__name__ = tool_name
        dynamic_composio_tool.__doc__ = f"""{description}
        
        This tool executes the {action} action on {app_name.title()} via Composio.
        User must first connect their {app_name.title()} account using composio_connect_app.
        
        Args:
            parameters: Action-specific parameters
            user_id: User identifier for account isolation
            
        Returns:
            JSON with action result
            
        Keywords: composio, {app_name}, {action}, integration
        Category: integration/{app_name}
        """

        # Register with MCP
        if security_manager:
            security_level = (
                SecurityLevel.MEDIUM
                if "send" in action or "create" in action
                else SecurityLevel.LOW
            )
            dynamic_composio_tool = security_manager.require_authorization(security_level)(
                dynamic_composio_tool
            )
        mcp.tool()(dynamic_composio_tool)

        self.registered_tools[tool_name] = True
        logger.info(f"  ✅ Registered tool: {tool_name}")

        # 返回工具元数据用于搜索索引
        return {
            tool_name: {
                "description": description,
                "category": f"integration/{app_name}",
                "keywords": ["composio", app_name, action, "integration"],
            }
        }


def register_composio_bridge(mcp):
    """Register Composio bridge with MCP server

    Returns:
        Dict[str, Dict]: 已注册工具的元数据，用于搜索索引
    """
    try:
        import os

        # Check if Composio is enabled FIRST (before any imports)
        api_key = os.environ.get("COMPOSIO_API_KEY")
        if not api_key:
            logger.debug("Composio API key not set, skipping bridge registration")
            return {}

        # Only import Composio service if API key is configured
        # This avoids slow SDK import when Composio is not being used
        from .composio_connector import ComposioService

        # Create service configuration
        config = {
            "name": "composio",
            "service_type": "composio",
            "connection_params": {"base_url": "https://api.composio.dev"},
            "auth_config": {"api_key": api_key},
            "capabilities": ["gmail", "slack", "github"],
            "enabled": True,
            "timeout_seconds": 30,
        }

        # Initialize Composio service
        composio_service = ComposioService(config)

        # Create and run async initialization
        async def init_and_register():
            # Connect to Composio
            connected = await composio_service.connect()
            if connected:
                # Create bridge and register tools
                bridge = ComposioMCPBridge(composio_service)
                tools_metadata = await bridge.register_composio_tools_with_mcp(mcp)
                logger.info("✅ Composio MCP Bridge registered successfully")
                return tools_metadata
            else:
                logger.warning("Failed to connect to Composio service")
                return {}

        # Run the async initialization and return metadata
        import asyncio
        import concurrent.futures

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an async context - use thread pool to avoid blocking
                logger.info(
                    "Running Composio registration in thread pool to avoid blocking event loop..."
                )

                def run_in_new_loop():
                    """Run init_and_register in a new event loop in a separate thread"""
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(init_and_register())
                    finally:
                        new_loop.close()

                # Run in thread pool with timeout
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_in_new_loop)
                    try:
                        return future.result(timeout=30)
                    except concurrent.futures.TimeoutError:
                        logger.warning("⚠️ Composio registration timed out after 30s")
                        return {}
            else:
                # Run in existing event loop
                return loop.run_until_complete(init_and_register())
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(init_and_register())

    except Exception as e:
        logger.error(f"Failed to register Composio bridge: {e}")
        return {}
