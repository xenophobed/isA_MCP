#!/usr/bin/env python3
"""
Event Service MCP Tools
完全迁移自event_service/event_tools.py的MCP工具
现在集成在user_service中
"""

import json
import os
import logging
from mcp.server.fastmcp import FastMCP
from datetime import datetime
from typing import Dict, Any, Optional

# Import user service components - direct absolute imports
from tools.services.user_service.services.event_service import EventService
from tools.services.user_service.services.task_service import TaskService

logger = logging.getLogger(__name__)

class EventServiceTools:
    """Event service tools for MCP integration - 迁移到user_service"""
    
    def __init__(self):
        self.event_service = EventService()
        self.task_service = TaskService()
        
    def register_tools(self, mcp: FastMCP):
        """Register all event service tools"""
        
        @mcp.tool()
        async def create_background_task(
            task_type: str,
            description: str,
            config,  # JSON string or dict
            callback_url: str = "",
            user_id: str = "default"
        ) -> str:
            """
            Create a background monitoring task
            
            Creates background tasks for web monitoring, scheduled events, or news digests.
            Tasks run independently and send callbacks when events occur.
            
            Keywords: background, monitor, schedule, watch, track, notify
            Category: event_sourcing
            
            Args:
                task_type: Type of task (web_monitor, schedule, news_digest, threshold_watch)
                description: Human-readable description of the task
                config: Task configuration as JSON string or Python dict
                callback_url: URL to send event callbacks to
                user_id: User ID for task ownership
            """
            try:
                # Set default callback URL if not provided
                if not callback_url:
                    user_service_url = os.getenv('USER_SERVICE_URL', 'http://localhost:8100')
                    callback_url = f"{user_service_url}/api/v1/events/process_background_feedback"
                
                # Parse configuration - handle both string and dict inputs
                if isinstance(config, str):
                    try:
                        config_dict = json.loads(config)
                    except json.JSONDecodeError:
                        return json.dumps({
                            "status": "error",
                            "message": "Invalid JSON in config parameter",
                            "timestamp": datetime.now().isoformat()
                        })
                elif isinstance(config, dict):
                    config_dict = config
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"config must be a string or dict, got {type(config)}",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Create task data
                task_data = {
                    "task_type": task_type,
                    "description": description,
                    "config": config_dict,
                    "callback_url": callback_url,
                    "user_id": user_id
                }
                
                # Create task using task service
                result = await self.task_service.create_task(user_id, task_data)
                
                if result.success:
                    return json.dumps({
                        "status": "success",
                        "task_id": result.data.get("task", {}).get("task_id"),
                        "description": description,
                        "task_type": task_type,
                        "callback_url": callback_url,
                        "message": f"Background task '{description}' created successfully",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": result.error,
                        "timestamp": datetime.now().isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error creating background task: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to create background task: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        @mcp.tool()
        async def list_background_tasks(
            user_id: str = "default",
            status_filter: str = ""
        ) -> str:
            """
            List background tasks
            
            Shows all background monitoring tasks for a user with their current status.
            
            Keywords: list, tasks, background, status, monitor
            Category: event_sourcing
            
            Args:
                user_id: User ID to filter tasks
                status_filter: Optional status filter (active, paused, completed, failed)
            """
            try:
                # Get tasks from task service
                result = await self.task_service.get_user_tasks(
                    user_id=user_id,
                    status=status_filter if status_filter else None
                )
                
                if result.success:
                    tasks = result.data.get("tasks", [])
                    
                    # Format for compatibility
                    formatted_tasks = []
                    for task in tasks:
                        formatted_tasks.append({
                            "task_id": task.get("task_id"),
                            "task_type": task.get("task_type"),
                            "description": task.get("description"),
                            "status": task.get("status"),
                            "user_id": task.get("user_id"),
                            "created_at": task.get("created_at"),
                            "last_run_time": task.get("last_run_time"),
                            "config": task.get("config", {})
                        })
                    
                    return json.dumps({
                        "status": "success",
                        "tasks": formatted_tasks,
                        "total_tasks": len(formatted_tasks),
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": result.error,
                        "timestamp": datetime.now().isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error listing background tasks: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to list background tasks: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        @mcp.tool()
        async def control_background_task(
            task_id: str,
            action: str,  # pause, resume, delete
            user_id: str = "default"
        ) -> str:
            """
            Control background task (pause/resume/delete)
            
            Manages the lifecycle of background monitoring tasks.
            
            Keywords: pause, resume, delete, stop, control, manage
            Category: event_sourcing
            
            Args:
                task_id: ID of the task to control
                action: Action to perform (pause, resume, delete)
                user_id: User ID for authorization
            """
            try:
                if action == "delete":
                    result = await self.task_service.delete_task(task_id, user_id)
                elif action in ["pause", "resume"]:
                    from tools.services.user_service.models.schemas.task_models import UserTaskUpdate
                    from tools.services.user_service.models.schemas.enums import TaskStatus
                    
                    status = TaskStatus.PAUSED if action == "pause" else TaskStatus.SCHEDULED
                    updates = UserTaskUpdate(status=status)
                    result = await self.task_service.update_task(task_id, user_id, updates)
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"Invalid action: {action}. Valid actions: pause, resume, delete",
                        "timestamp": datetime.now().isoformat()
                    })
                
                if result.success:
                    return json.dumps({
                        "status": "success",
                        "message": f"Task {action} succeeded",
                        "task_id": task_id,
                        "action": action,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"Task {action} failed: {result.error}",
                        "task_id": task_id,
                        "action": action,
                        "timestamp": datetime.now().isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error controlling background task: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to {action} task: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        @mcp.tool()
        async def get_event_service_status() -> str:
            """
            Get event service status and statistics
            
            Shows the current state of the event sourcing service including task counts and health.
            
            Keywords: status, health, stats, service, monitor
            Category: event_sourcing
            """
            try:
                # Get event statistics
                event_stats_result = await self.event_service.get_event_statistics()
                event_stats = event_stats_result.data.get("statistics", {}) if event_stats_result.success else {}
                
                return json.dumps({
                    "status": "success",
                    "service_status": {
                        "service_name": "user_service_with_events",
                        "status": "healthy",
                        "port": os.getenv("PORT", "8100"),
                        "integrated": True
                    },
                    "event_statistics": event_stats,
                    "environment": {
                        "user_service_port": os.getenv("PORT", "8100"),
                        "db_schema": os.getenv("DB_SCHEMA", "dev"),
                        "env": os.getenv("ENV", "development")
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error getting event service status: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to get service status: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        @mcp.tool()
        async def get_recent_events(
            limit: int = 20,
            task_id: str = "",
            event_type: str = ""
        ) -> str:
            """
            Get recent events from the database
            
            Retrieves recent events generated by background tasks for monitoring and debugging.
            
            Keywords: events, recent, history, log, debug
            Category: event_sourcing
            
            Args:
                limit: Maximum number of events to return
                task_id: Optional filter by task ID
                event_type: Optional filter by event type
            """
            try:
                if event_type:
                    result = await self.event_service.get_events_by_type(event_type, limit)
                elif task_id:
                    result = await self.event_service.get_recent_events(limit, task_id)
                else:
                    result = await self.event_service.get_recent_events(limit)
                
                if result.success:
                    events = result.data.get("events", [])
                    
                    return json.dumps({
                        "status": "success",
                        "events": events,
                        "count": len(events),
                        "filters": {
                            "limit": limit,
                            "task_id": task_id if task_id else None,
                            "event_type": event_type if event_type else None
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    return json.dumps({
                        "status": "error",
                        "message": result.error,
                        "timestamp": datetime.now().isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error getting recent events: {e}")
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to get recent events: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        @mcp.tool()
        def create_web_monitor_config(
            urls,  # JSON array of URLs or list
            keywords,  # JSON array of keywords or list
            check_interval_minutes: int = 30
        ) -> str:
            """
            Create configuration for web monitoring task
            
            Helper tool to generate properly formatted configuration for web monitoring tasks.
            
            Keywords: config, web, monitor, setup, helper
            Category: event_sourcing
            
            Args:
                urls: JSON array of URLs to monitor or Python list
                keywords: JSON array of keywords to watch for or Python list
                check_interval_minutes: How often to check (in minutes)
            """
            try:
                # Handle both string and list inputs
                if isinstance(urls, str):
                    urls_list = json.loads(urls)
                elif isinstance(urls, list):
                    urls_list = urls
                else:
                    raise ValueError(f"urls must be a string or list, got {type(urls)}")
                    
                if isinstance(keywords, str):
                    keywords_list = json.loads(keywords)
                elif isinstance(keywords, list):
                    keywords_list = keywords
                else:
                    raise ValueError(f"keywords must be a string or list, got {type(keywords)}")
                
                config = {
                    "urls": urls_list,
                    "keywords": keywords_list,
                    "check_interval_minutes": check_interval_minutes
                }
                
                return json.dumps({
                    "status": "success",
                    "config": config,
                    "config_json": json.dumps(config),
                    "example_usage": f"Use this config_json value in create_background_task",
                    "timestamp": datetime.now().isoformat()
                })
                
            except json.JSONDecodeError as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Invalid JSON in urls or keywords: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to create config: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        logger.info("Event service MCP tools registered successfully in user_service")


def register_event_service_tools(mcp: FastMCP):
    """Register event service tools with MCP"""
    tools = EventServiceTools()
    tools.register_tools(mcp)


def register_event_tools(mcp: FastMCP):
    """Register event service tools - auto-discovery entry point"""
    return register_event_service_tools(mcp)