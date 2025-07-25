#!/usr/bin/env python3
"""
Event Service Tools
MCP tools for event sourcing and background task management
"""

import json
import os
import logging
from mcp.server.fastmcp import FastMCP
from datetime import datetime

from tools.services.event_service.event_services import (
    EventSourceTaskType, 
    init_event_sourcing_service
)
from tools.services.event_service.services.event_service import EventService
from tools.services.event_service.services.task_service import TaskService

logger = logging.getLogger(__name__)

class EventServiceTools:
    """Event service tools for MCP integration"""
    
    def __init__(self):
        self.event_service_instance = None
        self.task_service = TaskService()
        self.event_service_logic = EventService()
        
    async def get_event_service(self):
        """Get or initialize event service"""
        if self.event_service_instance is None:
            self.event_service_instance = await init_event_sourcing_service()
        return self.event_service_instance

def register_event_service_tools(mcp: FastMCP):
    """Register event service tools with MCP"""
    tools = EventServiceTools()
    
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
                chat_api_url = os.getenv('CHAT_API_URL', 'http://localhost:8080')
                callback_url = f"{chat_api_url}/api/chat/event_callback"
            
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
            
            # Validate task type
            try:
                task_type_enum = EventSourceTaskType(task_type)
            except ValueError:
                return json.dumps({
                    "status": "error",
                    "message": f"Invalid task type: {task_type}. Valid types: {[t.value for t in EventSourceTaskType]}",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Get event service
            event_service = await tools.get_event_service()
            
            # Create task using new TaskService
            task_data = {
                "task_type": task_type,
                "description": description,
                "config": config_dict,
                "callback_url": callback_url,
                "user_id": user_id
            }
            
            result = await tools.task_service.create_task(task_data)
            
            if not result['success']:
                return json.dumps({
                    "status": "error",
                    "message": result['error'],
                    "timestamp": datetime.now().isoformat()
                })
            
            task_id = result['task_id']
            
            # Also create in old event service for compatibility
            event_service = await tools.get_event_service()
            task = await event_service.create_task(
                task_type=task_type_enum,
                description=description,
                config=config_dict,
                callback_url=callback_url,
                user_id=user_id
            )
            
            return json.dumps({
                "status": "success",
                "task_id": task.task_id,
                "description": task.description,
                "task_type": task.task_type.value,
                "db_stored": db_task_id is not None,
                "message": f"Background task '{description}' created successfully",
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
            user_id: User ID to filter tasks (use "admin" to see all)
            status_filter: Optional status filter (active, paused, completed, failed)
        """
        try:
            # Get from event service
            event_service = await tools.get_event_service()
            tasks = await event_service.list_tasks(user_id)
            
            # Also get from database
            db_user_id = None if user_id == "admin" else user_id
            db_status = status_filter if status_filter else None
            db_tasks = await tools.db_service.get_background_tasks(
                user_id=db_user_id,
                status=db_status
            )
            
            # Convert service tasks to dict format
            service_tasks = []
            for task in tasks:
                if not status_filter or task.status == status_filter:
                    service_tasks.append({
                        "task_id": task.task_id,
                        "task_type": task.task_type.value,
                        "description": task.description,
                        "status": task.status,
                        "user_id": task.user_id,
                        "created_at": task.created_at.isoformat(),
                        "last_check": task.last_check.isoformat() if task.last_check else None,
                        "config": task.config
                    })
            
            return json.dumps({
                "status": "success",
                "service_tasks": service_tasks,
                "database_tasks": db_tasks,
                "total_service_tasks": len(service_tasks),
                "total_database_tasks": len(db_tasks),
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
            event_service = await tools.get_event_service()
            
            if action == "pause":
                success = await event_service.pause_task(task_id, user_id)
                if success:
                    await tools.db_service.update_background_task_status(task_id, "paused")
                    
            elif action == "resume":
                success = await event_service.resume_task(task_id, user_id)
                if success:
                    await tools.db_service.update_background_task_status(task_id, "active")
                    
            elif action == "delete":
                success = await event_service.delete_task(task_id, user_id)
                if success:
                    await tools.db_service.delete_background_task(task_id)
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Invalid action: {action}. Valid actions: pause, resume, delete",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "status": "success" if success else "error",
                "message": f"Task {action} {'succeeded' if success else 'failed'}",
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
            event_service = await tools.get_event_service()
            service_status = await event_service.get_service_status()
            
            # Get database statistics
            db_stats = await tools.db_service.get_event_statistics()
            
            return json.dumps({
                "status": "success",
                "service_status": service_status,
                "database_statistics": db_stats,
                "environment": {
                    "event_service_port": os.getenv("EVENT_SERVICE_PORT", "8101"),
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
                events = await tools.db_service.get_events_by_type(event_type, limit)
            elif task_id:
                events = await tools.db_service.get_recent_events(limit, task_id)
            else:
                events = await tools.db_service.get_recent_events(limit)
            
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
    
    logger.info("Event service tools registered successfully")

def register_event_tools(mcp: FastMCP):
    """Register event service tools - auto-discovery entry point"""
    return register_event_service_tools(mcp)