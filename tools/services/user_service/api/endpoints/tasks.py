"""
Task Management Endpoints

用户任务管理API端点
提供任务的创建、查询、更新、删除和执行功能
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import sys
import os

# Add dependencies for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.schemas.task_models import (
    UserTask, UserTaskCreate, UserTaskUpdate, 
    TaskAnalytics, TaskTemplate
)
from models.schemas.enums import TaskStatus, TaskType, TaskPriority
from api.dependencies import get_current_user, CurrentUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


# 依赖注入 - 获取任务服务
async def get_task_service():
    """获取任务服务实例"""
    try:
        from services.task_service import TaskService
        return TaskService()
    except ImportError as e:
        logger.error(f"Failed to import TaskService: {e}")
        # 返回模拟服务用于测试
        return MockTaskService()


class MockTaskService:
    """模拟任务服务，用于测试API"""
    
    def __init__(self):
        self._tasks = {}
        self._task_counter = 0
    
    async def create_task(self, user_id: str, task_data: UserTaskCreate):
        """创建任务"""
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        
        task = {
            "task_id": task_id,
            "user_id": user_id,
            "name": task_data.name,
            "description": task_data.description,
            "task_type": task_data.task_type,
            "status": TaskStatus.PENDING,
            "priority": task_data.priority,
            "config": task_data.config,
            "schedule": task_data.schedule,
            "credits_per_run": task_data.credits_per_run,
            "tags": task_data.tags,
            "metadata": task_data.metadata,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "run_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_credits_consumed": 0.0
        }
        
        self._tasks[task_id] = task
        
        return type('ServiceResult', (), {
            'success': True,
            'data': {"task": task, "message": "Task created successfully"}
        })()
    
    async def get_task(self, task_id: str, user_id: str):
        """获取任务"""
        task = self._tasks.get(task_id)
        if not task or task["user_id"] != user_id:
            return type('ServiceResult', (), {
                'success': False,
                'error': 'Task not found'
            })()
        
        return type('ServiceResult', (), {
            'success': True,
            'data': {"task": task, "recent_executions": []}
        })()
    
    async def get_user_tasks(self, user_id: str, **kwargs):
        """获取用户任务列表"""
        user_tasks = [task for task in self._tasks.values() if task["user_id"] == user_id]
        
        return type('ServiceResult', (), {
            'success': True,
            'data': {
                "tasks": user_tasks,
                "count": len(user_tasks),
                "filters": {}
            }
        })()
    
    async def update_task(self, task_id: str, user_id: str, updates: UserTaskUpdate):
        """更新任务"""
        task = self._tasks.get(task_id)
        if not task or task["user_id"] != user_id:
            return type('ServiceResult', (), {
                'success': False,
                'error': 'Task not found'
            })()
        
        # 更新字段
        update_dict = updates.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in update_dict.items():
            task[field] = value
        
        task["updated_at"] = datetime.utcnow()
        
        return type('ServiceResult', (), {
            'success': True,
            'data': {"task": task, "message": "Task updated successfully"}
        })()
    
    async def delete_task(self, task_id: str, user_id: str):
        """删除任务"""
        task = self._tasks.get(task_id)
        if not task or task["user_id"] != user_id:
            return type('ServiceResult', (), {
                'success': False,
                'error': 'Task not found'
            })()
        
        del self._tasks[task_id]
        
        return type('ServiceResult', (), {
            'success': True,
            'data': {"message": "Task deleted successfully"}
        })()
    
    async def execute_task(self, task_id: str, trigger_type: str = "manual"):
        """执行任务"""
        task = self._tasks.get(task_id)
        if not task:
            return type('ServiceResult', (), {
                'success': False,
                'error': 'Task not found'
            })()
        
        execution_id = f"exec_{task_id}_{datetime.utcnow().timestamp()}"
        
        return type('ServiceResult', (), {
            'success': True,
            'data': {
                "execution_id": execution_id,
                "message": "Task execution started"
            }
        })()
    
    async def get_task_templates(self, user_id: str):
        """获取任务模板"""
        templates = {
            "daily_weather": {
                "name": "每日天气",
                "description": "每天定时发送天气预报",
                "task_type": "daily_weather",
                "config_template": {
                    "location": "城市名",
                    "notification_time": "08:00"
                },
                "credits_per_run": 0.5
            },
            "daily_news": {
                "name": "每日新闻",
                "description": "每天定时发送新闻摘要",
                "task_type": "daily_news",
                "config_template": {
                    "categories": ["科技", "财经"],
                    "notification_time": "08:00"
                },
                "credits_per_run": 1.0
            }
        }
        
        return type('ServiceResult', (), {
            'success': True,
            'data': {
                "templates": templates,
                "subscription_level": "free"
            }
        })()
    
    async def get_task_analytics(self, user_id: str, days: int = 30):
        """获取任务分析"""
        user_tasks = [task for task in self._tasks.values() if task["user_id"] == user_id]
        
        analytics = {
            "user_id": user_id,
            "time_period": f"{days}d",
            "total_tasks": len(user_tasks),
            "active_tasks": len([t for t in user_tasks if t["status"] == TaskStatus.PENDING]),
            "completed_tasks": len([t for t in user_tasks if t["status"] == TaskStatus.COMPLETED]),
            "failed_tasks": len([t for t in user_tasks if t["status"] == TaskStatus.FAILED]),
            "success_rate": 0.0,
            "total_credits_consumed": sum(t["total_credits_consumed"] for t in user_tasks)
        }
        
        return type('ServiceResult', (), {
            'success': True,
            'data': {"analytics": analytics}
        })()


def get_task_service_dependency():
    """Get task service dependency"""
    return get_task_service()

TaskServiceDep = Depends(get_task_service_dependency)


@router.post("/", response_model=Dict[str, Any])
async def create_task(
    task_data: UserTaskCreate,
    current_user: CurrentUser,
    task_service = Depends(get_task_service_dependency)
):
    """
    创建新任务
    """
    try:
        result = await task_service.create_task(current_user.user_id, task_data)
        
        if result.success:
            return {
                "success": True,
                "data": result.data,
                "message": "Task created successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to create task"
            )
            
    except Exception as e:
        logger.error(f"Create task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/", response_model=Dict[str, Any])
async def get_user_tasks(
    current_user: CurrentUser,
    task_service = Depends(get_task_service_dependency),
    status: Optional[str] = Query(None, description="Filter by task status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    limit: int = Query(50, ge=1, le=100, description="Number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip")
):
    """
    获取用户任务列表
    """
    try:
        # 转换枚举类型
        status_enum = None
        if status:
            try:
                status_enum = TaskStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid task status: {status}"
                )
        
        task_type_enum = None
        if task_type:
            try:
                task_type_enum = TaskType(task_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid task type: {task_type}"
                )
        
        result = await task_service.get_user_tasks(
            current_user.user_id,
            status=status_enum,
            task_type=task_type_enum,
            limit=limit,
            offset=offset
        )
        
        if result.success:
            return {
                "success": True,
                "data": result.data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Failed to get tasks"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tasks error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task(
    task_id: str,
    current_user: CurrentUser,
    task_service = Depends(get_task_service_dependency)
):
    """
    获取单个任务详情
    """
    try:
        result = await task_service.get_task(task_id, current_user.user_id)
        
        if result.success:
            return {
                "success": True,
                "data": result.data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{task_id}", response_model=Dict[str, Any])
async def update_task(
    task_id: str,
    updates: UserTaskUpdate,
    current_user: CurrentUser,
    task_service = Depends(get_task_service_dependency)
):
    """
    更新任务
    """
    try:
        result = await task_service.update_task(task_id, current_user.user_id, updates)
        
        if result.success:
            return {
                "success": True,
                "data": result.data,
                "message": "Task updated successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{task_id}", response_model=Dict[str, Any])
async def delete_task(
    task_id: str,
    current_user: CurrentUser,
    task_service = Depends(get_task_service_dependency)
):
    """
    删除任务
    """
    try:
        result = await task_service.delete_task(task_id, current_user.user_id)
        
        if result.success:
            return {
                "success": True,
                "message": "Task deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{task_id}/execute", response_model=Dict[str, Any])
async def execute_task(
    task_id: str,
    current_user: CurrentUser,
    task_service = Depends(get_task_service_dependency)
):
    """
    手动执行任务
    """
    try:
        result = await task_service.execute_task(task_id, trigger_type="manual")
        
        if result.success:
            return {
                "success": True,
                "data": result.data,
                "message": "Task execution started"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to execute task"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/templates/list", response_model=Dict[str, Any])
async def get_task_templates(
    current_user: CurrentUser,
    task_service = Depends(get_task_service_dependency)
):
    """
    获取可用的任务模板
    """
    try:
        result = await task_service.get_task_templates(current_user.user_id)
        
        if result.success:
            return {
                "success": True,
                "data": result.data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Failed to get templates"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get templates error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_task_analytics(
    current_user: CurrentUser,
    task_service = Depends(get_task_service_dependency),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """
    获取任务分析数据
    """
    try:
        result = await task_service.get_task_analytics(current_user.user_id, days)
        
        if result.success:
            return {
                "success": True,
                "data": result.data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Failed to get analytics"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get analytics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )