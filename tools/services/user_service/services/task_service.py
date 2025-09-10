"""
User Task Service

独立的用户任务管理服务 - 不再依赖外部Event Service
提供完整的任务生命周期管理功能
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import uuid

from core.logging import get_logger
from .base import BaseService, ServiceResult
from ..repositories.task_repository import TaskRepository
from ..repositories.user_repository import UserRepository
from models.schemas.task_models import (
    UserTask, UserTaskCreate, UserTaskUpdate,
    TaskExecution, TaskExecutionCreate, TaskTemplate,
    TaskAnalytics, TaskScheduleConfig, TaskNotificationConfig
)
from models.schemas.enums import TaskStatus, TaskType, TaskPriority

logger = get_logger(__name__)


class TaskService(BaseService):
    """用户任务管理服务"""
    
    def __init__(self):
        super().__init__()
        self.task_repo = TaskRepository()
        self.user_repo = UserRepository()
        self._task_executors = {}  # 任务执行器缓存
        
    # 任务基础管理
    async def create_task(self, user_id: str, task_data: UserTaskCreate) -> ServiceResult:
        """创建用户任务"""
        try:
            # 1. 验证用户存在
            user = await self.user_repo.get_user_by_id(user_id)
            if not user:
                return self._error("User not found")
            
            # 2. 检查权限和限制
            permission_result = await self._check_task_permissions(user_id, task_data.task_type)
            if not permission_result.success:
                return permission_result
            
            # 3. 验证任务配置
            config_result = await self._validate_task_config(task_data.task_type, task_data.config)
            if not config_result.success:
                return config_result
            
            # 4. 创建任务
            task = await self.task_repo.create_task(user_id, task_data)
            if not task:
                return self._error("Failed to create task")
            
            # 5. 如果有调度配置，设置下次执行时间
            if task_data.schedule:
                next_run_time = await self._calculate_next_run_time(task_data.schedule)
                if next_run_time:
                    await self.task_repo.update_task(
                        task.task_id, 
                        user_id, 
                        UserTaskUpdate(
                            status=TaskStatus.SCHEDULED,
                            next_run_time=next_run_time
                        )
                    )
            
            logger.info(f"Task created: {task.task_id} for user {user_id}")
            
            return self._success({
                "task": task.model_dump(),
                "message": "Task created successfully"
            })
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return self._error(f"Task creation failed: {str(e)}")
    
    async def get_task(self, task_id: str, user_id: str) -> ServiceResult:
        """获取任务详情"""
        try:
            task = await self.task_repo.get_task_by_id(task_id, user_id)
            if not task:
                return self._error("Task not found")
            
            # 获取执行历史
            executions = await self.task_repo.get_task_executions(task_id, limit=10)
            
            return self._success({
                "task": task.model_dump(),
                "recent_executions": [exec.model_dump() for exec in executions]
            })
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return self._error(f"Failed to get task: {str(e)}")
    
    async def update_task(
        self, 
        task_id: str, 
        user_id: str, 
        updates: UserTaskUpdate
    ) -> ServiceResult:
        """更新任务"""
        try:
            # 检查任务是否存在
            existing_task = await self.task_repo.get_task_by_id(task_id, user_id)
            if not existing_task:
                return self._error("Task not found")
            
            # 如果更新了配置，需要验证
            if updates.config is not None:
                config_result = await self._validate_task_config(
                    existing_task.task_type, 
                    updates.config
                )
                if not config_result.success:
                    return config_result
            
            # 如果更新了调度配置，计算下次执行时间
            if updates.schedule is not None:
                next_run_time = await self._calculate_next_run_time(updates.schedule)
                if next_run_time and not hasattr(updates, 'next_run_time'):
                    updates.next_run_time = next_run_time
            
            # 执行更新
            updated_task = await self.task_repo.update_task(task_id, user_id, updates)
            if not updated_task:
                return self._error("Failed to update task")
            
            logger.info(f"Task updated: {task_id}")
            
            return self._success({
                "task": updated_task.model_dump(),
                "message": "Task updated successfully"
            })
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return self._error(f"Task update failed: {str(e)}")
    
    async def delete_task(self, task_id: str, user_id: str) -> ServiceResult:
        """删除任务"""
        try:
            success = await self.task_repo.delete_task(task_id, user_id)
            if not success:
                return self._error("Task not found or already deleted")
            
            logger.info(f"Task deleted: {task_id}")
            
            return self._success({"message": "Task deleted successfully"})
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return self._error(f"Task deletion failed: {str(e)}")
    
    async def get_user_tasks(
        self,
        user_id: str,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> ServiceResult:
        """获取用户任务列表"""
        try:
            tasks = await self.task_repo.get_user_tasks(
                user_id, status, task_type, limit, offset
            )
            
            # 增强任务信息
            enhanced_tasks = []
            for task in tasks:
                enhanced_task = await self._enhance_task_info(task)
                enhanced_tasks.append(enhanced_task)
            
            return self._success({
                "tasks": enhanced_tasks,
                "count": len(enhanced_tasks),
                "filters": {
                    "status": status.value if status else None,
                    "task_type": task_type.value if task_type else None
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to get user tasks: {e}")
            return self._error(f"Failed to get tasks: {str(e)}")
    
    # 任务执行相关
    async def execute_task(self, task_id: str, trigger_type: str = "manual") -> ServiceResult:
        """手动执行任务"""
        try:
            task = await self.task_repo.get_task_by_id(task_id)
            if not task:
                return self._error("Task not found")
            
            # 检查任务状态
            if task.status == TaskStatus.RUNNING:
                return self._error("Task is already running")
            
            if task.status in [TaskStatus.CANCELLED, TaskStatus.FAILED]:
                return self._error(f"Cannot execute task with status: {task.status}")
            
            # 创建执行记录
            execution_data = TaskExecutionCreate(
                task_id=task_id,
                trigger_type=trigger_type,
                trigger_data={"manual_trigger": True}
            )
            
            execution = await self.task_repo.create_execution_record(
                task_id, task.user_id, execution_data
            )
            
            if not execution:
                return self._error("Failed to create execution record")
            
            # 异步执行任务
            asyncio.create_task(self._execute_task_async(task, execution))
            
            return self._success({
                "execution_id": execution.execution_id,
                "message": "Task execution started"
            })
            
        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {e}")
            return self._error(f"Task execution failed: {str(e)}")
    
    async def _execute_task_async(self, task: UserTask, execution: TaskExecution):
        """异步执行任务"""
        try:
            # 更新任务状态为运行中
            await self.task_repo.update_task(
                task.task_id, 
                task.user_id, 
                UserTaskUpdate(status=TaskStatus.RUNNING)
            )
            
            # 获取任务执行器
            executor = await self._get_task_executor(task.task_type)
            if not executor:
                raise Exception(f"No executor found for task type: {task.task_type}")
            
            # 执行任务
            result = await executor.execute(task)
            
            # 更新执行记录
            await self.task_repo.update_execution_record(execution.execution_id, {
                "success": True,
                "result": result,
                "credits_consumed": task.credits_per_run or 0,
                "started_at": execution.started_at.isoformat() if execution.started_at else None
            })
            
            # 更新任务执行信息
            execution_result = {
                "success": True,
                "result": result,
                "credits_consumed": task.credits_per_run or 0
            }
            
            # 如果是定期任务，计算下次执行时间
            if task.schedule:
                next_run_time = await self._calculate_next_run_time(task.schedule)
                if next_run_time:
                    execution_result["next_run_time"] = next_run_time.isoformat()
                    await self.task_repo.update_task(
                        task.task_id,
                        task.user_id,
                        UserTaskUpdate(status=TaskStatus.SCHEDULED)
                    )
                else:
                    await self.task_repo.update_task(
                        task.task_id,
                        task.user_id,
                        UserTaskUpdate(status=TaskStatus.COMPLETED)
                    )
            else:
                await self.task_repo.update_task(
                    task.task_id,
                    task.user_id,
                    UserTaskUpdate(status=TaskStatus.COMPLETED)
                )
            
            await self.task_repo.update_task_execution_info(task.task_id, execution_result)
            
            logger.info(f"Task executed successfully: {task.task_id}")
            
        except Exception as e:
            logger.error(f"Task execution failed: {task.task_id}, error: {e}")
            
            # 更新失败状态
            await self.task_repo.update_execution_record(execution.execution_id, {
                "success": False,
                "error": str(e),
                "started_at": execution.started_at.isoformat() if execution.started_at else None
            })
            
            await self.task_repo.update_task_execution_info(task.task_id, {
                "success": False,
                "error": str(e),
                "credits_consumed": 0
            })
            
            await self.task_repo.update_task(
                task.task_id,
                task.user_id,
                UserTaskUpdate(status=TaskStatus.FAILED)
            )
    
    # 任务模板和分析
    async def get_task_templates(self, user_id: str) -> ServiceResult:
        """获取任务模板"""
        try:
            user = await self.user_repo.get_user_by_id(user_id)
            subscription_level = user.get('subscription_status', 'free') if user else 'free'
            
            templates = await self.task_repo.get_task_templates(subscription_level)
            
            return self._success({
                "templates": [template.model_dump() for template in templates],
                "subscription_level": subscription_level
            })
            
        except Exception as e:
            logger.error(f"Failed to get task templates: {e}")
            return self._error(f"Failed to get templates: {str(e)}")
    
    async def get_task_analytics(self, user_id: str, days: int = 30) -> ServiceResult:
        """获取任务分析数据"""
        try:
            analytics = await self.task_repo.get_task_analytics(user_id, days)
            if not analytics:
                return self._error("Failed to generate analytics")
            
            return self._success({"analytics": analytics.model_dump()})
            
        except Exception as e:
            logger.error(f"Failed to get task analytics: {e}")
            return self._error(f"Analytics generation failed: {str(e)}")
    
    # 任务调度相关
    async def get_pending_tasks(self) -> List[UserTask]:
        """获取待执行的任务（供调度器使用）"""
        try:
            return await self.task_repo.get_pending_tasks()
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            return []
    
    # 私有方法
    async def _check_task_permissions(self, user_id: str, task_type: TaskType) -> ServiceResult:
        """检查用户任务权限"""
        try:
            user = await self.user_repo.get_user_by_id(user_id)
            if not user:
                return self._error("User not found")
            
            subscription_status = user.get('subscription_status', 'free')
            
            # 免费用户限制
            if subscription_status == 'free':
                free_allowed = [TaskType.DAILY_WEATHER, TaskType.DAILY_NEWS]
                if task_type not in free_allowed:
                    return self._error("Premium feature requires subscription upgrade")
                
                # 检查任务数量限制
                active_tasks = await self.task_repo.get_user_tasks(
                    user_id, status=TaskStatus.SCHEDULED
                )
                if len(active_tasks) >= 3:  # 免费用户最多3个活跃任务
                    return self._error("Free tier limited to 3 active tasks")
            
            return self._success({"allowed": True})
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return self._error(f"Permission check failed: {str(e)}")
    
    async def _validate_task_config(self, task_type: TaskType, config: Dict[str, Any]) -> ServiceResult:
        """验证任务配置"""
        try:
            # 根据任务类型验证必需的配置项
            required_configs = {
                TaskType.NEWS_MONITOR: ['keywords', 'sources'],
                TaskType.WEATHER_ALERT: ['location', 'alert_types'],
                TaskType.PRICE_TRACKER: ['product_urls', 'target_price'],
                TaskType.DAILY_WEATHER: ['location'],
                TaskType.DAILY_NEWS: ['categories']
            }
            
            if task_type in required_configs:
                for required_field in required_configs[task_type]:
                    if required_field not in config:
                        return self._error(f"Missing required config: {required_field}")
            
            return self._success({"valid": True})
            
        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            return self._error(f"Invalid configuration: {str(e)}")
    
    async def _calculate_next_run_time(self, schedule: Dict[str, Any]) -> Optional[datetime]:
        """计算下次执行时间"""
        try:
            schedule_type = schedule.get('schedule_type')
            
            if schedule_type == 'interval':
                interval_seconds = schedule.get('interval_seconds', 3600)
                return datetime.utcnow() + timedelta(seconds=interval_seconds)
            
            elif schedule_type == 'once':
                run_at_str = schedule.get('run_at')
                if run_at_str:
                    return datetime.fromisoformat(run_at_str.replace('Z', '+00:00')).replace(tzinfo=None)
            
            elif schedule_type == 'cron':
                # 简化的cron实现，这里只实现每日执行
                # 实际项目中应该使用croniter或类似库
                if schedule.get('cron_expression') == '@daily':
                    tomorrow = datetime.utcnow().replace(hour=8, minute=0, second=0, microsecond=0)
                    if tomorrow <= datetime.utcnow():
                        tomorrow += timedelta(days=1)
                    return tomorrow
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to calculate next run time: {e}")
            return None
    
    async def _enhance_task_info(self, task: UserTask) -> Dict[str, Any]:
        """增强任务信息"""
        enhanced = task.model_dump()
        
        # 添加运行时信息
        if task.last_run_time:
            time_since_last_run = datetime.utcnow() - task.last_run_time
            enhanced['time_since_last_run'] = str(time_since_last_run)
        
        # 添加成功率
        if task.run_count > 0:
            enhanced['success_rate'] = round((task.success_count / task.run_count) * 100, 2)
        else:
            enhanced['success_rate'] = 0.0
        
        # 添加下次执行时间的友好显示
        if task.next_run_time:
            time_until_next_run = task.next_run_time - datetime.utcnow()
            enhanced['time_until_next_run'] = str(time_until_next_run) if time_until_next_run.total_seconds() > 0 else "Overdue"
        
        # 添加任务类型友好名称
        type_names = {
            TaskType.NEWS_MONITOR: "新闻监控",
            TaskType.WEATHER_ALERT: "天气预警",
            TaskType.PRICE_TRACKER: "价格跟踪",
            TaskType.DAILY_WEATHER: "每日天气",
            TaskType.DAILY_NEWS: "每日新闻"
        }
        enhanced['type_display_name'] = type_names.get(task.task_type, task.task_type.value)
        
        return enhanced
    
    async def _get_task_executor(self, task_type: TaskType):
        """获取任务执行器"""
        # 这里应该返回对应的任务执行器
        # 暂时返回一个模拟执行器
        if task_type not in self._task_executors:
            self._task_executors[task_type] = MockTaskExecutor(task_type)
        
        return self._task_executors[task_type]


class MockTaskExecutor:
    """模拟任务执行器"""
    
    def __init__(self, task_type: TaskType):
        self.task_type = task_type
    
    async def execute(self, task: UserTask) -> Dict[str, Any]:
        """执行任务"""
        # 模拟执行时间
        await asyncio.sleep(1)
        
        # 根据任务类型返回不同的结果
        if self.task_type == TaskType.DAILY_WEATHER:
            return {
                "weather_data": {
                    "location": task.config.get("location", "Unknown"),
                    "temperature": "22°C",
                    "condition": "Sunny",
                    "humidity": "65%"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif self.task_type == TaskType.DAILY_NEWS:
            return {
                "news_items": [
                    {"title": "Sample News 1", "summary": "News summary 1"},
                    {"title": "Sample News 2", "summary": "News summary 2"}
                ],
                "count": 2,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        else:
            return {
                "task_type": self.task_type.value,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }