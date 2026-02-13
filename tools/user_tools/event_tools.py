#!/usr/bin/env python3
"""
Event & Task Management Tools
Proactive agent trigger management for event-driven and time-based tasks

Scenarios:
1. Register event triggers (price alerts, news monitoring, threshold detection)
2. Register scheduled tasks (daily summaries, periodic reports)
3. Manage user triggers (list, query, delete)
4. Query event history

Integrates with:
- Event Service: Real-time event monitoring
- Task Service: Scheduled recurring tasks
- Agent Service: Proactive workflow triggering

Architecture:
- Uses ServiceConfig for service URL configuration
- Supports service orchestration for complex workflows
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Annotated
from pydantic import BaseModel, Field

# MCP SDK imports
from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

# ISA imports
from tools.base_tool import BaseTool
from core.security import SecurityLevel
from core.logging import get_logger
from core.config.service_config import ServiceConfig

logger = get_logger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class TriggerCondition(BaseModel):
    """Condition configuration for event triggers"""

    event_type: Optional[str] = Field(
        None, description="Event type to monitor (e.g., price_change, news_published)"
    )
    event_source: Optional[str] = Field(
        None, description="Event source (frontend, backend, system, iot_device)"
    )
    event_category: Optional[str] = Field(
        None, description="Event category (user_action, system, alert)"
    )
    threshold_type: Optional[str] = Field(
        None, description="Threshold type: percentage or absolute"
    )
    threshold_value: Optional[float] = Field(None, description="Threshold value for triggering")
    direction: Optional[str] = Field(None, description="Direction: up, down, or any")
    product: Optional[str] = Field(
        None, description="Product/asset to monitor (e.g., Bitcoin, AAPL stock)"
    )
    keywords: Optional[List[str]] = Field(None, description="Keywords to monitor in events")
    schedule: Optional[Dict[str, Any]] = Field(
        None, description="Schedule configuration for time-based triggers"
    )


class ActionConfig(BaseModel):
    """Action configuration when trigger fires"""

    action: str = Field(
        ...,
        description="Action to perform: generate_summary, price_alert, event_notification, custom",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Action-specific parameters"
    )
    notification_channels: Optional[List[str]] = Field(
        None, description="Notification channels: email, sms, push"
    )


class TriggerResponse(BaseModel):
    """Trigger registration response"""

    trigger_id: str
    trigger_type: str
    description: str
    user_id: str
    enabled: bool
    created_at: str


# ============================================================================
# Event Tools Class
# ============================================================================


class EventTools(BaseTool):
    """Event and task management tools for proactive agent triggers"""

    def __init__(self):
        super().__init__()
        self.event_service_url = "http://localhost:8002"  # TODO: from config
        self.task_service_url = "http://localhost:8003"  # TODO: from config
        self.agent_service_url = "http://localhost:8000"  # TODO: from config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    def register_tools(self, mcp):
        """Register event and task management tools"""

        # 1. Register price alert trigger
        self.register_tool(
            mcp,
            self.register_price_alert_impl,
            name="register_price_alert",
            description="Register price alert trigger monitor product asset stock crypto currency threshold percentage change notification",
            security_level=SecurityLevel.MEDIUM,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=False),
        )

        # 2. Register time-based trigger (daily summary, periodic reports)
        self.register_tool(
            mcp,
            self.register_scheduled_task_impl,
            name="register_scheduled_task",
            description="Register schedule daily weekly monthly recurring task summary report periodic notification time-based",
            security_level=SecurityLevel.MEDIUM,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=False),
        )

        # 3. Register event pattern trigger
        self.register_tool(
            mcp,
            self.register_event_trigger_impl,
            name="register_event_trigger",
            description="Register event pattern trigger monitor detect security alert system notification custom event",
            security_level=SecurityLevel.MEDIUM,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=False),
        )

        # 4. List user triggers
        self.register_tool(
            mcp,
            self.list_triggers_impl,
            name="list_triggers",
            description="List show query display user triggers alerts tasks scheduled active enabled",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True),
        )

        # 5. Delete trigger
        self.register_tool(
            mcp,
            self.delete_trigger_impl,
            name="delete_trigger",
            description="Delete remove unregister cancel trigger alert task scheduled",
            security_level=SecurityLevel.MEDIUM,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=False),
        )

        # 6. Query event history
        self.register_tool(
            mcp,
            self.query_events_impl,
            name="query_events",
            description="Query search filter events history log past recent activity user",
            security_level=SecurityLevel.LOW,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=True),
        )

        logger.debug(f"Registered {len(self.registered_tools)} event management tools")

    # ========================================================================
    # Price Alert Implementation
    # ========================================================================

    async def register_price_alert_impl(
        self,
        product: Annotated[
            str, Field(description="Product name to monitor (e.g., Bitcoin, AAPL, Tesla)")
        ],
        threshold_value: Annotated[
            float, Field(description="Price change threshold (e.g., 50 for 50%)", gt=0)
        ],
        threshold_type: Annotated[
            str, Field(description="Threshold type: 'percentage' or 'absolute'")
        ] = "percentage",
        direction: Annotated[str, Field(description="Direction: 'up', 'down', or 'any'")] = "any",
        notification_channels: Annotated[
            Optional[List[str]], Field(description="Channels: email, sms, push")
        ] = None,
        user_id: str = "default",
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """
        Register a price alert trigger

        Example usage:
        - "Alert me when Bitcoin price rises 50%"
        - "Notify me if Tesla stock drops by 10%"
        - "Tell me when gold price changes by $50"
        """
        await self.log_info(
            ctx,
            f"Registering price alert: {product} {threshold_type} {direction} {threshold_value}",
        )
        await self.report_progress(ctx, 1, 4, "Validating inputs")

        # Validate inputs
        if threshold_type not in ["percentage", "absolute"]:
            return self.create_response(
                "error",
                "register_price_alert",
                {"error": "threshold_type must be 'percentage' or 'absolute'"},
            )

        if direction not in ["up", "down", "any"]:
            return self.create_response(
                "error",
                "register_price_alert",
                {"error": "direction must be 'up', 'down', or 'any'"},
            )

        # Build trigger description
        description = f"Alert when {product} price "
        if direction == "up":
            description += "rises"
        elif direction == "down":
            description += "drops"
        else:
            description += "changes"

        if threshold_type == "percentage":
            description += f" by {threshold_value}%"
        else:
            description += f" by ${threshold_value}"

        await self.report_progress(ctx, 2, 4, "Creating trigger configuration")

        # Build trigger conditions
        conditions = {
            "event_type": "price_change",
            "product": product,
            "threshold_type": threshold_type,
            "threshold_value": threshold_value,
            "direction": direction,
        }

        # Build action config
        action_config = {
            "action": "price_alert",
            "parameters": {
                "product": product,
                "threshold": f"{threshold_value}{'%' if threshold_type == 'percentage' else '$'}",
                "notification_channels": notification_channels or ["email"],
            },
        }

        await self.report_progress(ctx, 3, 4, "Registering with agent service")

        # Call agent service to register trigger
        try:
            response = await self.http_client.post(
                f"{self.agent_service_url}/api/v1/triggers/register",
                json={
                    "user_id": user_id,
                    "trigger_type": "threshold",
                    "description": description,
                    "conditions": conditions,
                    "action_config": action_config,
                },
                headers={"x-api-key": "internal_mcp_key"},  # TODO: proper auth
            )

            if response.status_code == 200:
                result = response.json()
                trigger_id = result.get("trigger_id")

                await self.report_progress(ctx, 4, 4, "Complete")
                await self.log_info(ctx, f"Price alert registered: {trigger_id}")

                return self.create_response(
                    "success",
                    "register_price_alert",
                    {
                        "trigger_id": trigger_id,
                        "description": description,
                        "product": product,
                        "threshold": f"{threshold_value}{'%' if threshold_type == 'percentage' else '$'}",
                        "direction": direction,
                        "status": "active",
                        "notification_channels": notification_channels or ["email"],
                    },
                )
            else:
                error_msg = response.text
                await self.log_error(ctx, f"Failed to register trigger: {error_msg}")
                return self.create_response(
                    "error", "register_price_alert", {"error": f"Registration failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error registering price alert: {e}")
            return self.create_response("error", "register_price_alert", {"error": str(e)})

    # ========================================================================
    # Scheduled Task Implementation
    # ========================================================================

    async def register_scheduled_task_impl(
        self,
        task_name: Annotated[
            str, Field(description="Task name (e.g., 'Daily News Summary', 'Weekly Report')")
        ],
        task_type: Annotated[
            str, Field(description="Task type: daily_news, daily_weather, custom")
        ] = "custom",
        schedule_type: Annotated[
            str, Field(description="Schedule type: daily, weekly, monthly, cron")
        ] = "daily",
        schedule_time: Annotated[
            str, Field(description="Time in HH:MM format (e.g., '09:00')")
        ] = "09:00",
        schedule_day: Annotated[
            Optional[int], Field(description="Day for weekly (1-7) or monthly (1-31)")
        ] = None,
        action_parameters: Annotated[
            Optional[Dict[str, Any]], Field(description="Action-specific parameters")
        ] = None,
        user_id: str = "default",
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """
        Register a scheduled recurring task

        Example usage:
        - "Send me news summary every day at 9am"
        - "Remind me weather forecast every morning"
        - "Generate weekly report every Monday at 10am"
        """
        await self.log_info(
            ctx, f"Registering scheduled task: {task_name} ({schedule_type} at {schedule_time})"
        )
        await self.report_progress(ctx, 1, 4, "Validating schedule")

        # Validate schedule type
        if schedule_type not in ["daily", "weekly", "monthly", "cron"]:
            return self.create_response(
                "error",
                "register_scheduled_task",
                {"error": "schedule_type must be daily, weekly, monthly, or cron"},
            )

        # Build schedule configuration
        schedule = {"type": schedule_type, "time": schedule_time}

        if schedule_type == "weekly" and schedule_day:
            schedule["weekday"] = schedule_day
        elif schedule_type == "monthly" and schedule_day:
            schedule["day"] = schedule_day

        description = f"{task_name} - {schedule_type} at {schedule_time}"

        await self.report_progress(ctx, 2, 4, "Creating task configuration")

        # Build conditions
        conditions = {"schedule": schedule, "task_type": task_type}

        # Build action config
        action_config = {
            "action": (
                "generate_summary"
                if "summary" in task_name.lower() or "news" in task_type.lower()
                else "custom"
            ),
            "parameters": action_parameters or {},
        }

        await self.report_progress(ctx, 3, 4, "Registering with agent service")

        # Call agent service to register trigger
        try:
            response = await self.http_client.post(
                f"{self.agent_service_url}/api/v1/triggers/register",
                json={
                    "user_id": user_id,
                    "trigger_type": "scheduled_task",
                    "description": description,
                    "conditions": conditions,
                    "action_config": action_config,
                },
                headers={"x-api-key": "internal_mcp_key"},
            )

            if response.status_code == 200:
                result = response.json()
                trigger_id = result.get("trigger_id")

                await self.report_progress(ctx, 4, 4, "Complete")
                await self.log_info(ctx, f"Scheduled task registered: {trigger_id}")

                return self.create_response(
                    "success",
                    "register_scheduled_task",
                    {
                        "trigger_id": trigger_id,
                        "task_name": task_name,
                        "description": description,
                        "schedule": schedule,
                        "task_type": task_type,
                        "status": "active",
                        "next_run": "calculated_by_scheduler",
                    },
                )
            else:
                error_msg = response.text
                await self.log_error(ctx, f"Failed to register task: {error_msg}")
                return self.create_response(
                    "error",
                    "register_scheduled_task",
                    {"error": f"Registration failed: {error_msg}"},
                )

        except Exception as e:
            await self.log_error(ctx, f"Error registering scheduled task: {e}")
            return self.create_response("error", "register_scheduled_task", {"error": str(e)})

    # ========================================================================
    # Event Pattern Trigger Implementation
    # ========================================================================

    async def register_event_trigger_impl(
        self,
        trigger_name: Annotated[
            str, Field(description="Trigger name (e.g., 'Security Alert', 'Failed Login Monitor')")
        ],
        event_type: Annotated[str, Field(description="Event type to monitor")],
        event_source: Annotated[
            Optional[str], Field(description="Event source: frontend, backend, system")
        ] = None,
        event_category: Annotated[Optional[str], Field(description="Event category")] = None,
        keywords: Annotated[
            Optional[List[str]], Field(description="Keywords to match in event data")
        ] = None,
        action_type: Annotated[
            str, Field(description="Action type: event_notification, custom")
        ] = "event_notification",
        user_id: str = "default",
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """
        Register an event pattern trigger

        Example usage:
        - "Alert me when there are failed login attempts"
        - "Notify me of security events"
        - "Monitor system errors"
        """
        await self.log_info(ctx, f"Registering event trigger: {trigger_name} for {event_type}")
        await self.report_progress(ctx, 1, 3, "Building trigger configuration")

        # Build conditions
        conditions = {"event_type": event_type}

        if event_source:
            conditions["event_source"] = event_source
        if event_category:
            conditions["event_category"] = event_category
        if keywords:
            conditions["keywords"] = keywords

        # Build action config
        action_config = {
            "action": action_type,
            "parameters": {"event_type": event_type, "notification_channels": ["email"]},
        }

        await self.report_progress(ctx, 2, 3, "Registering with agent service")

        try:
            response = await self.http_client.post(
                f"{self.agent_service_url}/api/v1/triggers/register",
                json={
                    "user_id": user_id,
                    "trigger_type": "event_pattern",
                    "description": trigger_name,
                    "conditions": conditions,
                    "action_config": action_config,
                },
                headers={"x-api-key": "internal_mcp_key"},
            )

            if response.status_code == 200:
                result = response.json()
                trigger_id = result.get("trigger_id")

                await self.report_progress(ctx, 3, 3, "Complete")
                await self.log_info(ctx, f"Event trigger registered: {trigger_id}")

                return self.create_response(
                    "success",
                    "register_event_trigger",
                    {
                        "trigger_id": trigger_id,
                        "trigger_name": trigger_name,
                        "event_type": event_type,
                        "event_source": event_source,
                        "event_category": event_category,
                        "keywords": keywords,
                        "status": "active",
                    },
                )
            else:
                error_msg = response.text
                await self.log_error(ctx, f"Failed to register trigger: {error_msg}")
                return self.create_response(
                    "error",
                    "register_event_trigger",
                    {"error": f"Registration failed: {error_msg}"},
                )

        except Exception as e:
            await self.log_error(ctx, f"Error registering event trigger: {e}")
            return self.create_response("error", "register_event_trigger", {"error": str(e)})

    # ========================================================================
    # Query and Management
    # ========================================================================

    async def list_triggers_impl(
        self, user_id: str = "default", ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """List all active triggers for a user"""
        await self.log_info(ctx, f"Listing triggers for user {user_id}")

        try:
            response = await self.http_client.get(
                f"{self.agent_service_url}/api/v1/triggers/list",
                params={"user_id": user_id},
                headers={"x-api-key": "internal_mcp_key"},
            )

            if response.status_code == 200:
                triggers = response.json()
                await self.log_info(ctx, f"Found {len(triggers)} triggers")

                return self.create_response(
                    "success",
                    "list_triggers",
                    {"user_id": user_id, "count": len(triggers), "triggers": triggers},
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "list_triggers", {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error listing triggers: {e}")
            return self.create_response("error", "list_triggers", {"error": str(e)})

    async def delete_trigger_impl(
        self,
        trigger_id: Annotated[str, Field(description="Trigger ID to delete")],
        user_id: str = "default",
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Delete a trigger"""
        await self.log_info(ctx, f"Deleting trigger {trigger_id}")

        try:
            response = await self.http_client.delete(
                f"{self.agent_service_url}/api/v1/triggers/{trigger_id}",
                headers={"x-api-key": "internal_mcp_key"},
            )

            if response.status_code == 200:
                await self.log_info(ctx, f"Trigger {trigger_id} deleted")

                return self.create_response(
                    "success", "delete_trigger", {"trigger_id": trigger_id, "status": "deleted"}
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "delete_trigger", {"error": f"Delete failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error deleting trigger: {e}")
            return self.create_response("error", "delete_trigger", {"error": str(e)})

    async def query_events_impl(
        self,
        event_type: Annotated[Optional[str], Field(description="Filter by event type")] = None,
        start_time: Annotated[Optional[str], Field(description="Start time ISO format")] = None,
        end_time: Annotated[Optional[str], Field(description="End time ISO format")] = None,
        limit: Annotated[int, Field(description="Max events to return", ge=1, le=1000)] = 100,
        user_id: str = "default",
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Query event history"""
        await self.log_info(ctx, f"Querying events for user {user_id}")

        try:
            params = {"user_id": user_id, "limit": limit}
            if event_type:
                params["event_type"] = event_type
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time

            response = await self.http_client.post(
                f"{self.event_service_url}/api/events/query", json=params
            )

            if response.status_code == 200:
                result = response.json()
                events = result.get("events", [])
                total = result.get("total", 0)

                await self.log_info(ctx, f"Found {total} events")

                return self.create_response(
                    "success",
                    "query_events",
                    {
                        "total": total,
                        "count": len(events),
                        "events": events,
                        "filters": {
                            "event_type": event_type,
                            "start_time": start_time,
                            "end_time": end_time,
                        },
                    },
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "query_events", {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error querying events: {e}")
            return self.create_response("error", "query_events", {"error": str(e)})

    async def cleanup(self):
        """Cleanup resources"""
        await self.http_client.aclose()


# ============================================================================
# Registration - Auto-discovery
# ============================================================================


def register_event_tools(mcp):
    """
    Register event and task management tools

    IMPORTANT: Function name must match pattern: register_{filename}(mcp)
    For event_tools.py, function must be: register_event_tools(mcp)
    """
    tool = EventTools()
    tool.register_tools(mcp)
    logger.debug(f" Event management tools registered successfully")
    return tool
