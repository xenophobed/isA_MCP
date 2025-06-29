#!/usr/bin/env python
"""
Event Sourcing Resources for MCP Server
Provides read-only resources for event sourcing system data
"""
import json
from datetime import datetime
from typing import Dict, Any

from core.logging import get_logger
from tools.services.event_sourcing_services import get_event_sourcing_service

logger = get_logger(__name__)

def register_event_sourcing_resources(mcp):
    """Register all event sourcing resources with the MCP server"""
    
    event_service = get_event_sourcing_service()
    
    @mcp.resource("event://tasks")
    async def get_all_tasks() -> str:
        """Get all background tasks as a resource
        
        This resource provides a comprehensive view of all background tasks
        in the event sourcing system. Clients can read this to understand
        current system state and task status.
        """
        try:
            tasks = await event_service.list_tasks("admin")  # Get all tasks
            task_data = []
            
            for task in tasks:
                task_data.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "description": task.description,
                    "status": task.status,
                    "created_at": task.created_at.isoformat(),
                    "last_check": task.last_check.isoformat() if task.last_check else None,
                    "config": task.config,
                    "user_id": task.user_id,
                    "callback_url": task.callback_url
                })
            
            resource_data = {
                "resource_type": "event_tasks",
                "tasks": task_data,
                "total": len(task_data),
                "generated_at": datetime.now().isoformat(),
                "description": "All background tasks in the event sourcing system"
            }
            
            logger.info(f"Event tasks resource accessed: {len(task_data)} tasks")
            return json.dumps(resource_data, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to get event tasks resource: {e}")
            return json.dumps({
                "error": f"Failed to get tasks: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    @mcp.resource("event://status")
    async def get_service_status() -> str:
        """Get event sourcing service status as a resource
        
        This resource provides the current operational status of the
        event sourcing service, including running monitors and task statistics.
        """
        try:
            status = await event_service.get_service_status()
            
            resource_data = {
                "resource_type": "event_service_status",
                "status": status,
                "generated_at": datetime.now().isoformat(),
                "description": "Current status of the event sourcing service"
            }
            
            logger.info("Event service status resource accessed")
            return json.dumps(resource_data, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to get event service status resource: {e}")
            return json.dumps({
                "error": f"Failed to get service status: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    @mcp.resource("event://tasks/active")
    async def get_active_tasks() -> str:
        """Get only active background tasks as a resource
        
        This resource provides a filtered view of only the currently
        active background tasks that are being monitored.
        """
        try:
            all_tasks = await event_service.list_tasks("admin")
            active_tasks = [task for task in all_tasks if task.status == "active"]
            
            task_data = []
            for task in active_tasks:
                task_data.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "description": task.description,
                    "created_at": task.created_at.isoformat(),
                    "last_check": task.last_check.isoformat() if task.last_check else None,
                    "config": task.config,
                    "user_id": task.user_id
                })
            
            resource_data = {
                "resource_type": "active_event_tasks",
                "active_tasks": task_data,
                "total_active": len(task_data),
                "generated_at": datetime.now().isoformat(),
                "description": "Currently active background tasks being monitored"
            }
            
            logger.info(f"Active event tasks resource accessed: {len(task_data)} active tasks")
            return json.dumps(resource_data, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to get active event tasks resource: {e}")
            return json.dumps({
                "error": f"Failed to get active tasks: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    @mcp.resource("event://tasks/by-type/{task_type}")
    async def get_tasks_by_type(task_type: str) -> str:
        """Get background tasks filtered by type as a resource
        
        This resource provides tasks filtered by their type (web_monitor,
        schedule, news_digest, threshold_watch).
        """
        try:
            all_tasks = await event_service.list_tasks("admin")
            filtered_tasks = [task for task in all_tasks if task.task_type.value == task_type]
            
            task_data = []
            for task in filtered_tasks:
                task_data.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "description": task.description,
                    "status": task.status,
                    "created_at": task.created_at.isoformat(),
                    "last_check": task.last_check.isoformat() if task.last_check else None,
                    "config": task.config,
                    "user_id": task.user_id
                })
            
            resource_data = {
                "resource_type": f"event_tasks_by_type_{task_type}",
                "task_type": task_type,
                "tasks": task_data,
                "count": len(task_data),
                "generated_at": datetime.now().isoformat(),
                "description": f"Background tasks of type '{task_type}'"
            }
            
            logger.info(f"Event tasks by type resource accessed: {task_type} ({len(task_data)} tasks)")
            return json.dumps(resource_data, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to get event tasks by type resource: {e}")
            return json.dumps({
                "error": f"Failed to get tasks by type: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    @mcp.resource("event://config/examples")
    async def get_config_examples() -> str:
        """Get configuration examples for different task types
        
        This resource provides example configurations for creating
        different types of background tasks.
        """
        try:
            examples = {
                "web_monitor": {
                    "description": "Monitor websites for content changes",
                    "example_config": {
                        "urls": ["https://techcrunch.com", "https://news.ycombinator.com"],
                        "keywords": ["AI", "machine learning", "OpenAI"],
                        "check_interval_minutes": 30
                    },
                    "usage": "Monitors specified URLs for content containing keywords"
                },
                "schedule": {
                    "description": "Create scheduled reminders or tasks",
                    "example_configs": [
                        {
                            "type": "daily",
                            "hour": 9,
                            "minute": 0,
                            "message": "Daily standup reminder"
                        },
                        {
                            "type": "interval",
                            "minutes": 120,
                            "message": "Check project status every 2 hours"
                        }
                    ],
                    "usage": "Creates scheduled triggers at specified times"
                },
                "news_digest": {
                    "description": "Generate daily news digests",
                    "example_config": {
                        "news_urls": ["https://techcrunch.com", "https://news.ycombinator.com"],
                        "hour": 8,
                        "categories": ["technology", "startups"]
                    },
                    "usage": "Scrapes news sources and creates daily digest"
                },
                "threshold_watch": {
                    "description": "Monitor metrics and alert on thresholds",
                    "example_config": {
                        "metric_url": "https://api.example.com/metrics",
                        "threshold_value": 100,
                        "check_interval_minutes": 15
                    },
                    "usage": "Monitors API endpoints for threshold breaches"
                }
            }
            
            resource_data = {
                "resource_type": "event_config_examples",
                "examples": examples,
                "generated_at": datetime.now().isoformat(),
                "description": "Configuration examples for different event sourcing task types"
            }
            
            logger.info("Event config examples resource accessed")
            return json.dumps(resource_data, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to get config examples resource: {e}")
            return json.dumps({
                "error": f"Failed to get config examples: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    logger.info("Event sourcing resources registered successfully") 