"""
Task Repository
Professional background task data access layer
Based on actual database schema: dev.user_tasks table
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_repository import BaseTaskRepository

class TaskRepository(BaseTaskRepository):
    """Repository for background task operations"""
    
    async def create_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Create background task in user_tasks table"""
        try:
            # Use UUID for task_id (matches database schema)
            task_id = uuid.uuid4()
            
            # Map to actual database columns
            task_record = {
                'task_id': task_id,
                'user_id': task_data.get('user_id'),  # VARCHAR foreign key to users
                'task_type': task_data.get('task_type'),  # VARCHAR(100) NOT NULL
                'description': task_data.get('description'),  # TEXT
                'config': task_data.get('config', {}),  # JSONB
                'callback_url': task_data.get('callback_url'),  # VARCHAR(500)
                'status': task_data.get('status', 'active'),  # VARCHAR(50) default 'active'
                'last_check': task_data.get('last_check'),  # TIMESTAMP WITH TIME ZONE
                'next_check': task_data.get('next_check'),  # TIMESTAMP WITH TIME ZONE
                # created_at and updated_at are set by database defaults
            }
            
            result = self.db.table('user_tasks').insert(task_record).execute()
            
            if result.data:
                self.logger.info(f"Task created: {task_id}")
                return str(task_id)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create task: {e}")
            return None
    
    async def get_active_tasks(self, user_id: Optional[str] = None, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active background tasks"""
        try:
            query = self.db.table('user_tasks').select('*').eq('status', 'active')
            
            if user_id:
                query = query.eq('user_id', user_id)
            if task_type:
                query = query.eq('task_type', task_type)
            
            result = query.order('created_at', desc=True).execute()
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Failed to get active tasks: {e}")
            return []
    
    async def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        try:
            result = self.db.table('user_tasks')\
                .select('*')\
                .eq('task_id', task_id)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    async def update_task_status(self, task_id: str, status: str, 
                               last_check: Optional[str] = None,
                               next_check: Optional[str] = None) -> bool:
        """Update task execution status"""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if last_check:
                update_data['last_check'] = last_check
            if next_check:
                update_data['next_check'] = next_check
            
            result = self.db.table('user_tasks')\
                .update(update_data)\
                .eq('task_id', task_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to update task {task_id}: {e}")
            return False
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete background task"""
        try:
            result = self.db.table('user_tasks')\
                .delete()\
                .eq('task_id', task_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to delete task {task_id}: {e}")
            return False
    
    async def get_tasks_by_user(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tasks for a specific user"""
        try:
            query = self.db.table('user_tasks').select('*').eq('user_id', user_id)
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('created_at', desc=True).execute()
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Failed to get tasks for user {user_id}: {e}")
            return []
    
    async def get_task_health_metrics(self) -> Dict[str, Any]:
        """Get task execution health metrics"""
        try:
            # Get all tasks for analysis
            all_tasks = self.db.table('user_tasks').select('task_type, status, created_at, last_check').execute()
            tasks_data = all_tasks.data if all_tasks.data else []
            
            total_tasks = len(tasks_data)
            active_tasks = len([t for t in tasks_data if t.get('status') == 'active'])
            paused_tasks = len([t for t in tasks_data if t.get('status') == 'paused'])
            completed_tasks = len([t for t in tasks_data if t.get('status') == 'completed'])
            failed_tasks = len([t for t in tasks_data if t.get('status') == 'failed'])
            
            # Task types distribution
            task_types = {}
            for task in tasks_data:
                task_type = task.get('task_type', 'unknown')
                task_types[task_type] = task_types.get(task_type, 0) + 1
            
            # Status distribution
            status_distribution = {
                'active': active_tasks,
                'paused': paused_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks
            }
            
            return {
                'total_tasks': total_tasks,
                'status_distribution': status_distribution,
                'task_types': task_types,
                'health_score': round((active_tasks + completed_tasks) / total_tasks * 100, 2) if total_tasks > 0 else 100,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get task health metrics: {e}")
            return {
                'total_tasks': 0,
                'status_distribution': {},
                'task_types': {},
                'health_score': 0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_stale_tasks(self, hours_threshold: int = 24) -> List[Dict[str, Any]]:
        """Get tasks that haven't been checked in specified hours"""
        try:
            from datetime import timedelta
            cutoff_time = (datetime.now() - timedelta(hours=hours_threshold)).isoformat()
            
            result = self.db.table('user_tasks')\
                .select('*')\
                .eq('status', 'active')\
                .lt('last_check', cutoff_time)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Failed to get stale tasks: {e}")
            return []