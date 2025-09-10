"""
Task Repository

用户任务数据访问层，提供任务相关的数据库操作
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas.task_models import (
    UserTask, UserTaskCreate, UserTaskUpdate,
    TaskExecution, TaskExecutionCreate,
    TaskTemplate, TaskAnalytics
)
from models.schemas.enums import TaskStatus, TaskType, TaskPriority
from repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TaskRepository(BaseRepository):
    """任务数据访问层"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'user_tasks'
        self.execution_table = 'task_executions'
        self.template_table = 'task_templates'
    
    async def create_task(self, user_id: str, task_data: UserTaskCreate) -> Optional[UserTask]:
        """创建用户任务"""
        try:
            task_id = f"task_{uuid.uuid4().hex[:12]}"
            
            task_record = {
                "task_id": task_id,
                "user_id": user_id,
                "name": task_data.name,
                "description": task_data.description,
                "task_type": task_data.task_type.value,
                "status": TaskStatus.PENDING.value,
                "priority": task_data.priority.value,
                "config": task_data.config,
                "schedule": task_data.schedule,
                "credits_per_run": task_data.credits_per_run,
                "tags": task_data.tags,
                "metadata": task_data.metadata,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "run_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_credits_consumed": 0.0
            }
            
            result = self.db.table(self.table_name).insert(task_record).execute()
            
            if result.data:
                return UserTask.model_validate(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None
    
    async def get_task_by_id(self, task_id: str, user_id: str = None) -> Optional[UserTask]:
        """根据ID获取任务"""
        try:
            query = self.db.table(self.table_name).select("*").eq("task_id", task_id)
            
            if user_id:
                query = query.eq("user_id", user_id)
                
            result = query.execute()
            
            if result.data:
                return UserTask.model_validate(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    async def update_task(self, task_id: str, user_id: str, updates: UserTaskUpdate) -> Optional[UserTask]:
        """更新任务"""
        try:
            update_data = {}
            
            # 只更新非None的字段
            for field, value in updates.model_dump(exclude_unset=True).items():
                if value is not None:
                    if hasattr(value, 'value'):  # 枚举类型
                        update_data[field] = value.value
                    else:
                        update_data[field] = value
            
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.db.table(self.table_name)\
                .update(update_data)\
                .eq("task_id", task_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if result.data:
                return UserTask.model_validate(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return None
    
    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """删除任务（软删除）"""
        try:
            result = self.db.table(self.table_name)\
                .update({
                    "deleted_at": datetime.utcnow().isoformat(),
                    "status": TaskStatus.CANCELLED.value,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("task_id", task_id)\
                .eq("user_id", user_id)\
                .is_("deleted_at", None)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False
    
    async def get_user_tasks(
        self, 
        user_id: str, 
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserTask]:
        """获取用户任务列表"""
        try:
            query = self.db.table(self.table_name)\
                .select("*")\
                .eq("user_id", user_id)\
                .is_("deleted_at", None)
            
            if status:
                query = query.eq("status", status.value)
            
            if task_type:
                query = query.eq("task_type", task_type.value)
            
            result = query.order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            if result.data:
                return [UserTask.model_validate(task) for task in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Failed to get user tasks: {e}")
            return []
    
    async def get_pending_tasks(self, limit: int = 50) -> List[UserTask]:
        """获取待执行的任务"""
        try:
            now = datetime.utcnow().isoformat()
            
            result = self.db.table(self.table_name)\
                .select("*")\
                .eq("status", TaskStatus.SCHEDULED.value)\
                .lte("next_run_time", now)\
                .is_("deleted_at", None)\
                .order("priority", desc=True)\
                .order("next_run_time")\
                .limit(limit)\
                .execute()
            
            if result.data:
                return [UserTask.model_validate(task) for task in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            return []
    
    async def update_task_execution_info(
        self, 
        task_id: str, 
        execution_result: Dict[str, Any]
    ) -> bool:
        """更新任务执行信息"""
        try:
            success = execution_result.get('success', False)
            credits_consumed = execution_result.get('credits_consumed', 0.0)
            
            # 构建更新数据
            update_data = {
                "last_run_time": datetime.utcnow().isoformat(),
                "run_count": "run_count + 1",  # PostgreSQL函数
                "total_credits_consumed": f"total_credits_consumed + {credits_consumed}",
                "last_result": execution_result.get('result'),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if success:
                update_data["success_count"] = "success_count + 1"
                update_data["last_success_time"] = datetime.utcnow().isoformat()
                update_data["last_error"] = None
            else:
                update_data["failure_count"] = "failure_count + 1"
                update_data["last_error"] = execution_result.get('error', 'Unknown error')
            
            # 如果有下次执行时间，更新它
            if execution_result.get('next_run_time'):
                update_data["next_run_time"] = execution_result['next_run_time']
            
            result = self.db.table(self.table_name)\
                .update(update_data)\
                .eq("task_id", task_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update task execution info: {e}")
            return False
    
    # 任务执行记录相关方法
    async def create_execution_record(
        self, 
        task_id: str, 
        user_id: str,
        execution_data: TaskExecutionCreate
    ) -> Optional[TaskExecution]:
        """创建任务执行记录"""
        try:
            execution_id = f"exec_{uuid.uuid4().hex[:12]}"
            
            record = {
                "execution_id": execution_id,
                "task_id": task_id,
                "user_id": user_id,
                "status": TaskStatus.RUNNING.value,
                "started_at": datetime.utcnow().isoformat(),
                "trigger_type": execution_data.trigger_type,
                "trigger_data": execution_data.trigger_data,
                "created_at": datetime.utcnow().isoformat(),
                "api_calls_made": 0,
                "credits_consumed": 0.0
            }
            
            result = self.db.table(self.execution_table).insert(record).execute()
            
            if result.data:
                return TaskExecution.model_validate(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to create execution record: {e}")
            return None
    
    async def update_execution_record(
        self, 
        execution_id: str, 
        execution_result: Dict[str, Any]
    ) -> bool:
        """更新执行记录"""
        try:
            update_data = {
                "status": TaskStatus.COMPLETED.value if execution_result.get('success') else TaskStatus.FAILED.value,
                "completed_at": datetime.utcnow().isoformat(),
                "result": execution_result.get('result'),
                "credits_consumed": execution_result.get('credits_consumed', 0.0),
                "tokens_used": execution_result.get('tokens_used'),
                "api_calls_made": execution_result.get('api_calls_made', 0)
            }
            
            if not execution_result.get('success'):
                update_data.update({
                    "error_message": execution_result.get('error', 'Unknown error'),
                    "error_details": execution_result.get('error_details')
                })
            
            # 计算执行时长
            if execution_result.get('started_at'):
                started = datetime.fromisoformat(execution_result['started_at'])
                duration = (datetime.utcnow() - started).total_seconds() * 1000
                update_data["duration_ms"] = int(duration)
            
            result = self.db.table(self.execution_table)\
                .update(update_data)\
                .eq("execution_id", execution_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update execution record: {e}")
            return False
    
    async def get_task_executions(
        self, 
        task_id: str, 
        limit: int = 50
    ) -> List[TaskExecution]:
        """获取任务执行历史"""
        try:
            result = self.db.table(self.execution_table)\
                .select("*")\
                .eq("task_id", task_id)\
                .order("started_at", desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                return [TaskExecution.model_validate(record) for record in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Failed to get task executions: {e}")
            return []
    
    # 任务分析相关方法
    async def get_task_analytics(
        self, 
        user_id: str, 
        days: int = 30
    ) -> Optional[TaskAnalytics]:
        """获取任务分析数据"""
        try:
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # 获取任务统计
            tasks_result = self.db.table(self.table_name)\
                .select("status, task_type, run_count, success_count, failure_count, total_credits_consumed")\
                .eq("user_id", user_id)\
                .gte("created_at", since)\
                .is_("deleted_at", None)\
                .execute()
            
            # 获取执行统计
            executions_result = self.db.table(self.execution_table)\
                .select("status, credits_consumed, tokens_used, api_calls_made, duration_ms")\
                .eq("user_id", user_id)\
                .gte("started_at", since)\
                .execute()
            
            tasks = tasks_result.data or []
            executions = executions_result.data or []
            
            # 计算统计数据
            analytics = TaskAnalytics(
                user_id=user_id,
                time_period=f"{days}d"
            )
            
            # 任务状态统计
            for task in tasks:
                status = task.get('status', '')
                if status == TaskStatus.PENDING.value:
                    analytics.active_tasks += 1
                elif status == TaskStatus.COMPLETED.value:
                    analytics.completed_tasks += 1
                elif status == TaskStatus.FAILED.value:
                    analytics.failed_tasks += 1
                elif status == TaskStatus.PAUSED.value:
                    analytics.paused_tasks += 1
                
                # 任务类型分布
                task_type = task.get('task_type', 'unknown')
                analytics.task_types_distribution[task_type] = \
                    analytics.task_types_distribution.get(task_type, 0) + 1
                
                # 资源消耗
                analytics.total_credits_consumed += task.get('total_credits_consumed', 0)
            
            analytics.total_tasks = len(tasks)
            
            # 执行统计
            successful_executions = 0
            total_duration = 0
            duration_count = 0
            
            for execution in executions:
                analytics.total_executions += 1
                
                if execution.get('status') == TaskStatus.COMPLETED.value:
                    successful_executions += 1
                elif execution.get('status') == TaskStatus.FAILED.value:
                    analytics.failed_executions += 1
                
                analytics.total_credits_consumed += execution.get('credits_consumed', 0)
                analytics.total_tokens_used += execution.get('tokens_used', 0) or 0
                analytics.total_api_calls += execution.get('api_calls_made', 0) or 0
                
                if execution.get('duration_ms'):
                    total_duration += execution['duration_ms']
                    duration_count += 1
            
            analytics.successful_executions = successful_executions
            
            # 计算成功率
            if analytics.total_executions > 0:
                analytics.success_rate = round(
                    (successful_executions / analytics.total_executions) * 100, 2
                )
            
            # 计算平均执行时长（转换为秒）
            if duration_count > 0:
                analytics.average_execution_time = round(total_duration / duration_count / 1000, 2)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get task analytics: {e}")
            return None
    
    # 任务模板相关方法
    async def get_task_templates(
        self, 
        subscription_level: str = "free"
    ) -> List[TaskTemplate]:
        """获取可用的任务模板"""
        try:
            result = self.db.table(self.template_table)\
                .select("*")\
                .eq("is_active", True)\
                .lte("required_subscription_level", subscription_level)\
                .order("category")\
                .order("name")\
                .execute()
            
            if result.data:
                return [TaskTemplate.model_validate(template) for template in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Failed to get task templates: {e}")
            return []