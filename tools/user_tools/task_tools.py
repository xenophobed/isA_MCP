#!/usr/bin/env python3
"""
Task Management Tools
User task management with TODO, reminders, and task tracking

Scenarios:
1. Create tasks (TODO, reminders, custom tasks)
2. Query tasks (list, filter by type, status, due date)
3. Update and delete tasks
4. Mark tasks as completed
5. Get due tasks and reminders

Integrates with:
- Task Service: User task management (port 8201)
- Calendar Service: Calendar event linking
- Notification Service: Task reminders

Architecture:
- Uses ServiceConfig for service URL configuration
- Supports task types: TODO, REMINDER, CALENDAR_EVENT, CUSTOM
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Annotated
from pydantic import BaseModel, Field
from enum import Enum

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
# Enums (matching task_service models)
# ============================================================================

class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskType(str, Enum):
    """Task type"""
    DAILY_WEATHER = "daily_weather"
    DAILY_NEWS = "daily_news"
    NEWS_MONITOR = "news_monitor"
    WEATHER_ALERT = "weather_alert"
    PRICE_TRACKER = "price_tracker"
    DATA_BACKUP = "data_backup"
    TODO = "todo"
    REMINDER = "reminder"
    CALENDAR_EVENT = "calendar_event"
    CUSTOM = "custom"


class TaskPriority(str, Enum):
    """Task priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================================
# Pydantic Models
# ============================================================================

class TaskCreateRequest(BaseModel):
    """Task creation request"""
    name: str = Field(..., description="Task name/title")
    description: Optional[str] = Field(None, description="Task description")
    task_type: TaskType = Field(default=TaskType.TODO, description="Task type")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    config: Dict[str, Any] = Field(default_factory=dict, description="Task-specific configuration")
    schedule: Optional[Dict[str, Any]] = Field(None, description="Schedule configuration for recurring tasks")
    tags: List[str] = Field(default_factory=list, description="Task tags for organization")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")
    reminder_time: Optional[str] = Field(None, description="Reminder time in ISO format")


# ============================================================================
# Task Tools Class
# ============================================================================

class TaskTools(BaseTool):
    """Task management tools for TODO, reminders, and task tracking"""

    def __init__(self):
        super().__init__()
        self.task_service_url = "http://localhost:8211"  # task_service port from ports.yaml
        # Default headers for internal service-to-service calls
        # In production, this should use proper service account auth
        self._default_headers = {
            "Content-Type": "application/json",
            "X-Service-Name": "mcp_server",
            "X-Internal-Call": "true"
        }
        self.http_client = httpx.AsyncClient(timeout=30.0, headers=self._default_headers)

    def _get_headers(self, user_id: str) -> dict:
        """Get request headers with user_id for task_service authentication"""
        return {
            "Content-Type": "application/json",
            "X-Internal-Call": "true",
            "X-User-Id": user_id
        }

    def register_tools(self, mcp):
        """Register task management tools"""

        # 1. Create task
        self.register_tool(
            mcp,
            self.create_task_impl,
            name="create_task",
            description="Create task todo reminder item add new schedule track",
            security_level=SecurityLevel.MEDIUM,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=False)
        )

        # 2. Get task
        self.register_tool(
            mcp,
            self.get_task_impl,
            name="get_task",
            description="Get retrieve fetch task todo reminder details information by id",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # 3. List tasks
        self.register_tool(
            mcp,
            self.list_tasks_impl,
            name="list_tasks",
            description="List query search filter tasks todos reminders by type status priority due date",
            security_level=SecurityLevel.LOW,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # 4. Update task
        self.register_tool(
            mcp,
            self.update_task_impl,
            name="update_task",
            description="Update modify edit change task todo reminder details priority status",
            security_level=SecurityLevel.MEDIUM,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=False)
        )

        # 5. Delete task
        self.register_tool(
            mcp,
            self.delete_task_impl,
            name="delete_task",
            description="Delete remove cancel task todo reminder",
            security_level=SecurityLevel.MEDIUM,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=False)
        )

        # 6. Complete task
        self.register_tool(
            mcp,
            self.complete_task_impl,
            name="complete_task",
            description="Complete finish mark done task todo check off",
            security_level=SecurityLevel.MEDIUM,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=False)
        )

        # 7. Get due tasks
        self.register_tool(
            mcp,
            self.get_due_tasks_impl,
            name="get_due_tasks",
            description="Get retrieve due tasks todos deadlines today this week overdue",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # 8. Get reminders
        self.register_tool(
            mcp,
            self.get_reminders_impl,
            name="get_reminders",
            description="Get retrieve upcoming reminders notifications alerts",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # 9. Get task analytics
        self.register_tool(
            mcp,
            self.get_task_analytics_impl,
            name="get_task_analytics",
            description="Get task analytics statistics productivity metrics completion rate",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        logger.debug(f"Registered {len(self.registered_tools)} task management tools")

    # ========================================================================
    # Task CRUD Implementation
    # ========================================================================

    async def create_task_impl(
        self,
        name: Annotated[str, Field(description="Task name/title (e.g., 'Buy groceries', 'Call mom')")],
        task_type: Annotated[str, Field(description="Task type: todo, reminder, calendar_event, custom")] = "todo",
        description: Annotated[Optional[str], Field(description="Task description")] = None,
        priority: Annotated[str, Field(description="Priority: low, medium, high, urgent")] = "medium",
        due_date: Annotated[Optional[str], Field(description="Due date in ISO format (e.g., '2025-01-30')")] = None,
        reminder_time: Annotated[Optional[str], Field(description="Reminder time in ISO format (e.g., '2025-01-30T14:00:00')")] = None,
        tags: Annotated[Optional[List[str]], Field(description="Tags for organization (e.g., ['work', 'urgent'])")] = None,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Create a task, TODO item, or reminder

        Example usage:
        - "Add a todo: buy groceries"
        - "Remind me to call mom at 5pm"
        - "Create a task to finish report by Friday"
        """
        await self.log_info(ctx, f"Creating task: {name}")
        await self.report_progress(ctx, 1, 3, "Validating inputs")

        # Validate task type
        valid_types = ["todo", "reminder", "calendar_event", "custom",
                       "daily_weather", "daily_news", "news_monitor",
                       "weather_alert", "price_tracker", "data_backup"]
        if task_type not in valid_types:
            return self.create_response(
                "error", "create_task",
                {"error": f"Task type must be one of: {', '.join(valid_types[:4])}"}
            )

        # Validate priority
        valid_priorities = ["low", "medium", "high", "urgent"]
        if priority not in valid_priorities:
            return self.create_response(
                "error", "create_task",
                {"error": f"Priority must be one of: {', '.join(valid_priorities)}"}
            )

        # Validate dates if provided
        if due_date:
            try:
                datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            except ValueError as e:
                return self.create_response(
                    "error", "create_task",
                    {"error": f"Invalid due_date format: {str(e)}"}
                )

        if reminder_time:
            try:
                datetime.fromisoformat(reminder_time.replace('Z', '+00:00'))
            except ValueError as e:
                return self.create_response(
                    "error", "create_task",
                    {"error": f"Invalid reminder_time format: {str(e)}"}
                )

        await self.report_progress(ctx, 2, 3, "Creating task in task service")

        # Prepare request data
        task_data = {
            "name": name,
            "task_type": task_type,
            "priority": priority,
            "config": {},
            "tags": tags or [],
            "metadata": {}
        }

        if description:
            task_data["description"] = description
        if due_date:
            task_data["due_date"] = due_date
        if reminder_time:
            task_data["reminder_time"] = reminder_time

        # Call task service
        try:
            response = await self.http_client.post(
                f"{self.task_service_url}/api/v1/tasks",
                json=task_data,
                headers=self._get_headers(user_id)
            )

            if response.status_code in [200, 201]:
                result = response.json()
                task_id = result.get("task_id")

                await self.report_progress(ctx, 3, 3, "Complete")
                await self.log_info(ctx, f"Task created: {task_id}")

                return self.create_response(
                    "success", "create_task",
                    {
                        "task_id": task_id,
                        "name": name,
                        "task_type": task_type,
                        "priority": priority,
                        "due_date": due_date,
                        "reminder_time": reminder_time,
                        "status": "pending"
                    }
                )
            else:
                error_msg = response.text
                await self.log_error(ctx, f"Failed to create task: {error_msg}")
                return self.create_response(
                    "error", "create_task",
                    {"error": f"Creation failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error creating task: {e}")
            return self.create_response(
                "error", "create_task",
                {"error": str(e)}
            )

    async def get_task_impl(
        self,
        task_id: Annotated[str, Field(description="Task ID to retrieve")],
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Get task details"""
        await self.log_info(ctx, f"Getting task: {task_id}")

        try:
            response = await self.http_client.get(
                f"{self.task_service_url}/api/v1/tasks/{task_id}",
                headers=self._get_headers(user_id)
            )

            if response.status_code == 200:
                task = response.json()
                await self.log_info(ctx, f"Retrieved task: {task.get('name')}")

                return self.create_response(
                    "success", "get_task",
                    {
                        "task": task,
                        "task_id": task_id
                    }
                )
            elif response.status_code == 404:
                return self.create_response(
                    "error", "get_task",
                    {"error": "Task not found"}
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "get_task",
                    {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error getting task: {e}")
            return self.create_response(
                "error", "get_task",
                {"error": str(e)}
            )

    async def list_tasks_impl(
        self,
        user_id: str = "default",
        task_type: Annotated[Optional[str], Field(description="Filter by type: todo, reminder, etc.")] = None,
        status: Annotated[Optional[str], Field(description="Filter by status: pending, completed, etc.")] = None,
        priority: Annotated[Optional[str], Field(description="Filter by priority: low, medium, high, urgent")] = None,
        tags: Annotated[Optional[str], Field(description="Filter by tags (comma-separated)")] = None,
        due_before: Annotated[Optional[str], Field(description="Filter tasks due before date (ISO format)")] = None,
        due_after: Annotated[Optional[str], Field(description="Filter tasks due after date (ISO format)")] = None,
        limit: Annotated[int, Field(description="Max tasks to return", ge=1, le=1000)] = 100,
        offset: Annotated[int, Field(description="Offset for pagination", ge=0)] = 0,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """List tasks with optional filters"""
        await self.log_info(ctx, f"Listing tasks for user {user_id}")

        try:
            params = {
                "limit": limit,
                "offset": offset
            }
            if task_type:
                params["task_type"] = task_type
            if status:
                params["status"] = status
            if priority:
                params["priority"] = priority
            if tags:
                params["tags"] = tags
            if due_before:
                params["due_before"] = due_before
            if due_after:
                params["due_after"] = due_after

            response = await self.http_client.get(
                f"{self.task_service_url}/api/v1/tasks",
                params=params,
                headers=self._get_headers(user_id)
            )

            if response.status_code == 200:
                result = response.json()
                tasks = result.get("tasks", [])
                total = result.get("count", len(tasks))

                await self.log_info(ctx, f"Found {total} tasks")

                return self.create_response(
                    "success", "list_tasks",
                    {
                        "total": total,
                        "count": len(tasks),
                        "tasks": tasks,
                        "filters": {
                            "task_type": task_type,
                            "status": status,
                            "priority": priority,
                            "tags": tags
                        }
                    }
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "list_tasks",
                    {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error listing tasks: {e}")
            return self.create_response(
                "error", "list_tasks",
                {"error": str(e)}
            )

    async def update_task_impl(
        self,
        task_id: Annotated[str, Field(description="Task ID to update")],
        user_id: str = "default",
        name: Annotated[Optional[str], Field(description="New task name")] = None,
        description: Annotated[Optional[str], Field(description="New task description")] = None,
        priority: Annotated[Optional[str], Field(description="New priority: low, medium, high, urgent")] = None,
        status: Annotated[Optional[str], Field(description="New status: pending, completed, cancelled, paused")] = None,
        due_date: Annotated[Optional[str], Field(description="New due date in ISO format")] = None,
        reminder_time: Annotated[Optional[str], Field(description="New reminder time in ISO format")] = None,
        tags: Annotated[Optional[List[str]], Field(description="New tags list")] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Update task details"""
        await self.log_info(ctx, f"Updating task: {task_id}")

        # Build update data
        update_data = {}
        if name:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if priority:
            update_data["priority"] = priority
        if status:
            update_data["status"] = status
        if due_date:
            update_data["due_date"] = due_date
        if reminder_time:
            update_data["reminder_time"] = reminder_time
        if tags is not None:
            update_data["tags"] = tags

        if not update_data:
            return self.create_response(
                "error", "update_task",
                {"error": "No fields to update"}
            )

        try:
            response = await self.http_client.put(
                f"{self.task_service_url}/api/v1/tasks/{task_id}",
                json=update_data,
                headers=self._get_headers(user_id)
            )

            if response.status_code == 200:
                task = response.json()
                await self.log_info(ctx, f"Task updated: {task_id}")

                return self.create_response(
                    "success", "update_task",
                    {
                        "task_id": task_id,
                        "task": task,
                        "status": "updated"
                    }
                )
            elif response.status_code == 404:
                return self.create_response(
                    "error", "update_task",
                    {"error": "Task not found"}
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "update_task",
                    {"error": f"Update failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error updating task: {e}")
            return self.create_response(
                "error", "update_task",
                {"error": str(e)}
            )

    async def delete_task_impl(
        self,
        task_id: Annotated[str, Field(description="Task ID to delete")],
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Delete a task"""
        await self.log_info(ctx, f"Deleting task: {task_id}")

        try:
            response = await self.http_client.delete(
                f"{self.task_service_url}/api/v1/tasks/{task_id}",
                headers=self._get_headers(user_id)
            )

            if response.status_code in [200, 204]:
                await self.log_info(ctx, f"Task {task_id} deleted")

                return self.create_response(
                    "success", "delete_task",
                    {
                        "task_id": task_id,
                        "status": "deleted"
                    }
                )
            elif response.status_code == 404:
                return self.create_response(
                    "error", "delete_task",
                    {"error": "Task not found"}
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "delete_task",
                    {"error": f"Delete failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error deleting task: {e}")
            return self.create_response(
                "error", "delete_task",
                {"error": str(e)}
            )

    async def complete_task_impl(
        self,
        task_id: Annotated[str, Field(description="Task ID to mark as completed")],
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Mark a task as completed

        Example usage:
        - "Mark the groceries task as done"
        - "Complete my 'call mom' reminder"
        """
        await self.log_info(ctx, f"Completing task: {task_id}")

        try:
            # Update task status to completed
            response = await self.http_client.put(
                f"{self.task_service_url}/api/v1/tasks/{task_id}",
                json={"status": "completed"},
                headers=self._get_headers(user_id)
            )

            if response.status_code == 200:
                task = response.json()
                await self.log_info(ctx, f"Task {task_id} completed")

                return self.create_response(
                    "success", "complete_task",
                    {
                        "task_id": task_id,
                        "name": task.get("name"),
                        "status": "completed",
                        "completed_at": datetime.utcnow().isoformat()
                    }
                )
            elif response.status_code == 404:
                return self.create_response(
                    "error", "complete_task",
                    {"error": "Task not found"}
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "complete_task",
                    {"error": f"Completion failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error completing task: {e}")
            return self.create_response(
                "error", "complete_task",
                {"error": str(e)}
            )

    # ========================================================================
    # Query Methods Implementation
    # ========================================================================

    async def get_due_tasks_impl(
        self,
        user_id: str = "default",
        time_range: Annotated[str, Field(description="Time range: today, tomorrow, this_week, overdue")] = "today",
        include_completed: Annotated[bool, Field(description="Include completed tasks")] = False,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Get tasks due within a time range

        Example usage:
        - "What's due today?"
        - "Show me overdue tasks"
        - "What do I have due this week?"
        """
        await self.log_info(ctx, f"Getting due tasks for user {user_id} ({time_range})")

        # Calculate date range
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        if time_range == "today":
            due_after = today_start.isoformat()
            due_before = today_end.isoformat()
        elif time_range == "tomorrow":
            due_after = today_end.isoformat()
            due_before = (today_end + timedelta(days=1)).isoformat()
        elif time_range == "this_week":
            due_after = today_start.isoformat()
            due_before = (today_start + timedelta(days=7)).isoformat()
        elif time_range == "overdue":
            due_after = None
            due_before = now.isoformat()
        else:
            return self.create_response(
                "error", "get_due_tasks",
                {"error": "time_range must be: today, tomorrow, this_week, or overdue"}
            )

        try:
            params = {
                "limit": 100
            }
            if due_after:
                params["due_after"] = due_after
            if due_before:
                params["due_before"] = due_before
            if not include_completed:
                params["status"] = "pending"

            response = await self.http_client.get(
                f"{self.task_service_url}/api/v1/tasks",
                params=params,
                headers=self._get_headers(user_id)
            )

            if response.status_code == 200:
                result = response.json()
                tasks = result.get("tasks", [])

                # For overdue, filter to only tasks past due
                if time_range == "overdue":
                    tasks = [t for t in tasks if t.get("due_date") and
                             datetime.fromisoformat(t["due_date"].replace('Z', '+00:00')) < now]

                await self.log_info(ctx, f"Found {len(tasks)} due tasks ({time_range})")

                return self.create_response(
                    "success", "get_due_tasks",
                    {
                        "time_range": time_range,
                        "count": len(tasks),
                        "tasks": tasks
                    }
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "get_due_tasks",
                    {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error getting due tasks: {e}")
            return self.create_response(
                "error", "get_due_tasks",
                {"error": str(e)}
            )

    async def get_reminders_impl(
        self,
        user_id: str = "default",
        hours_ahead: Annotated[int, Field(description="Hours ahead to look for reminders", ge=1, le=168)] = 24,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Get upcoming reminders

        Example usage:
        - "What reminders do I have?"
        - "Show me reminders for the next 24 hours"
        """
        await self.log_info(ctx, f"Getting reminders for user {user_id} (next {hours_ahead} hours)")

        try:
            now = datetime.utcnow()
            reminder_before = (now + timedelta(hours=hours_ahead)).isoformat()

            params = {
                "task_type": "reminder",
                "status": "pending",
                "limit": 100
            }

            response = await self.http_client.get(
                f"{self.task_service_url}/api/v1/tasks",
                params=params,
                headers=self._get_headers(user_id)
            )

            if response.status_code == 200:
                result = response.json()
                all_reminders = result.get("tasks", [])

                # Filter to reminders within the time window
                upcoming_reminders = []
                for reminder in all_reminders:
                    reminder_time = reminder.get("reminder_time")
                    if reminder_time:
                        try:
                            rt = datetime.fromisoformat(reminder_time.replace('Z', '+00:00'))
                            if now <= rt <= datetime.fromisoformat(reminder_before.replace('Z', '+00:00')):
                                upcoming_reminders.append(reminder)
                        except ValueError:
                            pass

                # Sort by reminder time
                upcoming_reminders.sort(key=lambda x: x.get("reminder_time", ""))

                await self.log_info(ctx, f"Found {len(upcoming_reminders)} upcoming reminders")

                return self.create_response(
                    "success", "get_reminders",
                    {
                        "hours_ahead": hours_ahead,
                        "count": len(upcoming_reminders),
                        "reminders": upcoming_reminders
                    }
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "get_reminders",
                    {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error getting reminders: {e}")
            return self.create_response(
                "error", "get_reminders",
                {"error": str(e)}
            )

    async def get_task_analytics_impl(
        self,
        user_id: str = "default",
        time_period: Annotated[str, Field(description="Time period: day, week, month, all")] = "week",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Get task analytics and productivity metrics

        Example usage:
        - "How productive was I this week?"
        - "Show me my task completion stats"
        """
        await self.log_info(ctx, f"Getting task analytics for user {user_id} ({time_period})")

        try:
            response = await self.http_client.get(
                f"{self.task_service_url}/api/v1/tasks/analytics",
                params={"time_period": time_period},
                headers=self._get_headers(user_id)
            )

            if response.status_code == 200:
                analytics = response.json()
                await self.log_info(ctx, f"Retrieved task analytics")

                return self.create_response(
                    "success", "get_task_analytics",
                    {
                        "time_period": time_period,
                        "analytics": analytics
                    }
                )
            else:
                # Fallback: calculate basic analytics from task list
                await self.log_info(ctx, "Analytics endpoint not available, calculating from tasks")

                tasks_response = await self.http_client.get(
                    f"{self.task_service_url}/api/v1/tasks",
                    params={"limit": 1000},
                    headers=self._get_headers(user_id)
                )

                if tasks_response.status_code == 200:
                    result = tasks_response.json()
                    tasks = result.get("tasks", [])

                    # Calculate basic stats
                    total = len(tasks)
                    completed = sum(1 for t in tasks if t.get("status") == "completed")
                    pending = sum(1 for t in tasks if t.get("status") == "pending")
                    failed = sum(1 for t in tasks if t.get("status") == "failed")

                    # Task type distribution
                    type_dist = {}
                    for t in tasks:
                        tt = t.get("task_type", "unknown")
                        type_dist[tt] = type_dist.get(tt, 0) + 1

                    analytics = {
                        "total_tasks": total,
                        "completed_tasks": completed,
                        "pending_tasks": pending,
                        "failed_tasks": failed,
                        "completion_rate": round(completed / total * 100, 2) if total > 0 else 0,
                        "task_types_distribution": type_dist
                    }

                    return self.create_response(
                        "success", "get_task_analytics",
                        {
                            "time_period": time_period,
                            "analytics": analytics
                        }
                    )
                else:
                    error_msg = tasks_response.text
                    return self.create_response(
                        "error", "get_task_analytics",
                        {"error": f"Query failed: {error_msg}"}
                    )

        except Exception as e:
            await self.log_error(ctx, f"Error getting task analytics: {e}")
            return self.create_response(
                "error", "get_task_analytics",
                {"error": str(e)}
            )

    async def cleanup(self):
        """Cleanup resources"""
        await self.http_client.aclose()


# ============================================================================
# Registration - Auto-discovery
# ============================================================================

def register_task_tools(mcp):
    """
    Register task management tools

    IMPORTANT: Function name must match pattern: register_{filename}(mcp)
    For task_tools.py, function must be: register_task_tools(mcp)
    """
    tool = TaskTools()
    tool.register_tools(mcp)
    logger.debug(f"Task management tools registered successfully")
    return tool
