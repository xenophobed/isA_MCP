#!/usr/bin/env python
"""
Event Sourcing Tools for MCP Server
Handles background task management and event monitoring
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.monitoring import monitor_manager
from tools.services.event_sourcing_services import get_event_sourcing_service, EventSourceTaskType

logger = get_logger(__name__)

def register_event_sourcing_tools(mcp):
    """Register all event sourcing tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    event_service = get_event_sourcing_service()
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def create_background_task(
        task_type: str,
        description: str,
        config: str,  # JSON string
        callback_url: str = "http://localhost:8000/process_background_feedback",
        user_id: str = "default"
    ) -> str:
        """Create a background monitoring task that runs independently
        
        Args:
            task_type: Type of task (web_monitor, schedule, news_digest, threshold_watch)
            description: Human-readable description of the task
            config: JSON configuration for the task
            callback_url: URL to send feedback to when events occur
            user_id: User who created the task
        
        Returns:
            JSON response with task creation status
        """
        
        try:
            # Parse config
            config_dict = json.loads(config)
            
            # Validate task type
            try:
                task_type_enum = EventSourceTaskType(task_type)
            except ValueError:
                return json.dumps({
                    "status": "error",
                    "error": f"Invalid task type. Must be one of: {[t.value for t in EventSourceTaskType]}",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Create task using service
            task = await event_service.create_task(
                task_type=task_type_enum,
                description=description,
                config=config_dict,
                callback_url=callback_url,
                user_id=user_id
            )
            
            result = {
                "status": "success",
                "action": "create_background_task",
                "data": {
                    "task_id": task.task_id,
                    "description": task.description,
                    "task_type": task.task_type.value,
                    "status": task.status
                },
                "message": f"Background task '{description}' created and will run in background",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Background task created: {task.task_id} by {user_id}")
            return json.dumps(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config: {e}")
            return json.dumps({
                "status": "error",
                "error": f"Invalid JSON in config: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to create background task: {e}")
            return json.dumps({
                "status": "error",
                "error": f"Failed to create background task: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

    @mcp.tool()
    @security_manager.security_check
    async def list_background_tasks(user_id: str = "default") -> str:
        """List all background tasks for the user"""
        
        try:
            tasks = await event_service.list_tasks(user_id)
            
            task_data = []
            for task in tasks:
                task_data.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "description": task.description,
                    "status": task.status,
                    "created_at": task.created_at.isoformat(),
                    "last_check": task.last_check.isoformat() if task.last_check else None,
                    "config": task.config
                })
            
            result = {
                "status": "success",
                "action": "list_background_tasks",
                "data": {
                    "tasks": task_data,
                    "total_tasks": len(task_data)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Listed {len(task_data)} background tasks for {user_id}")
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Failed to list background tasks: {e}")
            return json.dumps({
                "status": "error",
                "error": f"Failed to list background tasks: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def pause_background_task(task_id: str, user_id: str = "default") -> str:
        """Pause a background task"""
        
        try:
            success = await event_service.pause_task(task_id, user_id)
            
            if success:
                logger.info(f"Background task paused: {task_id} by {user_id}")
                return json.dumps({
                    "status": "success",
                    "message": f"Task {task_id} paused",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "error": f"Failed to pause task {task_id} - not found or access denied",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error pausing task {task_id}: {e}")
            return json.dumps({
                "status": "error",
                "error": f"Error pausing task: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def resume_background_task(task_id: str, user_id: str = "default") -> str:
        """Resume a paused background task"""
        
        try:
            success = await event_service.resume_task(task_id, user_id)
            
            if success:
                logger.info(f"Background task resumed: {task_id} by {user_id}")
                return json.dumps({
                    "status": "success",
                    "message": f"Task {task_id} resumed",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "error": f"Failed to resume task {task_id} - not found or access denied",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error resuming task {task_id}: {e}")
            return json.dumps({
                "status": "error",
                "error": f"Error resuming task: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.HIGH)
    async def delete_background_task(task_id: str, user_id: str = "default") -> str:
        """Delete a background task"""
        
        try:
            success = await event_service.delete_task(task_id, user_id)
            
            if success:
                logger.info(f"Background task deleted: {task_id} by {user_id}")
                return json.dumps({
                    "status": "success",
                    "message": f"Task {task_id} deleted",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "error": f"Failed to delete task {task_id} - not found or access denied",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return json.dumps({
                "status": "error",
                "error": f"Error deleting task: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

    @mcp.tool()
    @security_manager.security_check
    async def get_event_sourcing_status() -> str:
        """Get the status of the event sourcing service"""
        
        try:
            status = await event_service.get_service_status()
            
            result = {
                "status": "success",
                "action": "get_event_sourcing_status",
                "data": status,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("Event sourcing status retrieved")
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Failed to get event sourcing status: {e}")
            return json.dumps({
                "status": "error",
                "error": f"Failed to get event sourcing status: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

    logger.info("Event sourcing tools registered successfully")
