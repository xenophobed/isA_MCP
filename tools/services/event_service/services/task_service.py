"""
Task Service
Core business logic for background task operations
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..repositories.task_repository import TaskRepository
from .user_integration_service import UserIntegrationService
from core.logging import get_logger

class TaskService:
    """Core service for background task operations with business logic"""
    
    def __init__(self):
        self.task_repo = TaskRepository()
        self.user_integration = UserIntegrationService()
        self.logger = get_logger(self.__class__.__name__)
    
    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new background task with validation and business logic"""
        try:
            # Validate required fields
            if not task_data.get('task_type'):
                return {
                    "success": False,
                    "error": "task_type is required",
                    "task_id": None
                }
            
            if not task_data.get('user_id'):
                return {
                    "success": False,
                    "error": "user_id is required",
                    "task_id": None
                }
            
            user_id = task_data['user_id']
            task_type = task_data['task_type']
            
            # Validate user exists
            user_exists = await self.user_integration.validate_user_exists(user_id)
            if not user_exists:
                return {
                    "success": False,
                    "error": f"User {user_id} not found",
                    "task_id": None
                }
            
            # Validate user permissions for task type
            has_permission = await self.user_integration.validate_user_permissions(user_id, task_type)
            if not has_permission:
                return {
                    "success": False,
                    "error": f"User {user_id} does not have permission for {task_type}",
                    "task_id": None
                }
            
            # Check credits if required
            required_credits = self._calculate_task_credits(task_type, task_data.get('config', {}))
            if required_credits > 0:
                has_credits = await self.user_integration.check_user_credits(user_id, required_credits)
                if not has_credits:
                    return {
                        "success": False,
                        "error": f"Insufficient credits for {task_type}",
                        "task_id": None
                    }
            
            # Create task in repository
            task_id = await self.task_repo.create_task(task_data)
            
            if task_id:
                # Record usage for billing
                usage_metadata = {
                    "task_id": task_id,
                    "task_type": task_type,
                    "cost": required_credits
                }
                await self.user_integration.record_usage(user_id, task_type, usage_metadata)
                
                self.logger.info(f"Task created successfully: {task_id}")
                return {
                    "success": True,
                    "error": None,
                    "task_id": task_id,
                    "message": "Task created successfully",
                    "credits_consumed": required_credits
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create task in database",
                    "task_id": None
                }
                
        except Exception as e:
            self.logger.error(f"Failed to create task: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_id": None
            }
    
    def _calculate_task_credits(self, task_type: str, config: Dict[str, Any]) -> float:
        """Calculate credits required for task based on type and configuration"""
        base_costs = {
            'web_monitor': 1.0,
            'schedule': 0.5,
            'news_digest': 2.0,
            'threshold_watch': 1.5
        }
        
        base_cost = base_costs.get(task_type, 1.0)
        
        # Adjust based on configuration complexity
        if task_type == 'web_monitor':
            urls_count = len(config.get('urls', []))
            keywords_count = len(config.get('keywords', []))
            base_cost *= (urls_count * 0.5 + keywords_count * 0.1)
        
        return round(base_cost, 2)
    
    async def get_user_tasks(self, user_id: str, status: Optional[str] = None) -> Dict[str, Any]:
        """Get all tasks for a user"""
        try:
            # Validate user exists
            user_exists = await self.user_integration.validate_user_exists(user_id)
            if not user_exists:
                return {
                    "success": False,
                    "error": f"User {user_id} not found",
                    "tasks": []
                }
            
            tasks = await self.task_repo.get_tasks_by_user(user_id, status)
            
            return {
                "success": True,
                "error": None,
                "tasks": tasks,
                "user_id": user_id,
                "count": len(tasks)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get tasks for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tasks": [],
                "user_id": user_id,
                "count": 0
            }
    
    async def update_task_status(self, task_id: str, status: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Update task status with authorization"""
        try:
            # Get task to verify ownership
            task = await self.task_repo.get_task_by_id(task_id)
            if not task:
                return {
                    "success": False,
                    "error": f"Task {task_id} not found",
                    "message": None
                }
            
            # Verify user ownership if user_id provided
            if user_id and task.get('user_id') != user_id:
                return {
                    "success": False,
                    "error": "Not authorized to modify this task",
                    "message": None
                }
            
            # Update task status
            last_check = datetime.now().isoformat() if status == 'active' else None
            success = await self.task_repo.update_task_status(task_id, status, last_check)
            
            if success:
                return {
                    "success": True,
                    "error": None,
                    "message": f"Task {task_id} status updated to {status}"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update task status",
                    "message": None
                }
                
        except Exception as e:
            self.logger.error(f"Failed to update task {task_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": None
            }
    
    async def delete_task(self, task_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete task with authorization"""
        try:
            # Get task to verify ownership
            task = await self.task_repo.get_task_by_id(task_id)
            if not task:
                return {
                    "success": False,
                    "error": f"Task {task_id} not found",
                    "message": None
                }
            
            # Verify user ownership if user_id provided
            if user_id and task.get('user_id') != user_id:
                return {
                    "success": False,
                    "error": "Not authorized to delete this task",
                    "message": None
                }
            
            # Delete task
            success = await self.task_repo.delete_task(task_id)
            
            if success:
                return {
                    "success": True,
                    "error": None,
                    "message": f"Task {task_id} deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to delete task",
                    "message": None
                }
                
        except Exception as e:
            self.logger.error(f"Failed to delete task {task_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": None
            }
    
    async def get_active_tasks(self, user_id: Optional[str] = None, task_type: Optional[str] = None) -> Dict[str, Any]:
        """Get active tasks with optional filters"""
        try:
            tasks = await self.task_repo.get_active_tasks(user_id, task_type)
            
            return {
                "success": True,
                "error": None,
                "tasks": tasks,
                "count": len(tasks),
                "filters": {
                    "user_id": user_id,
                    "task_type": task_type
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get active tasks: {e}")
            return {
                "success": False,
                "error": str(e),
                "tasks": [],
                "count": 0,
                "filters": {}
            }
    
    async def get_task_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive task health metrics"""
        try:
            metrics = await self.task_repo.get_task_health_metrics()
            
            # Add business intelligence
            health_score = metrics.get('health_score', 0)
            if health_score >= 90:
                metrics['overall_status'] = 'excellent'
            elif health_score >= 70:
                metrics['overall_status'] = 'good'
            elif health_score >= 50:
                metrics['overall_status'] = 'degraded'
            else:
                metrics['overall_status'] = 'poor'
            
            return {
                "success": True,
                "error": None,
                "metrics": metrics
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get task health metrics: {e}")
            return {
                "success": False,
                "error": str(e),
                "metrics": {}
            }