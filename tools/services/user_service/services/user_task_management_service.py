#!/usr/bin/env python3
"""
User Task Management Service
用户任务管理服务 - 集成 Event Service 的任务管理功能
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import uuid

from core.logging import get_logger
from .base import BaseService
from ..repositories.user_repository import UserRepository

logger = get_logger(__name__)

class UserTaskManagementService(BaseService):
    """用户任务管理服务"""
    
    def __init__(self):
        super().__init__()
        self.user_repo = UserRepository()
        self.event_service_url = "http://localhost:8101"
        
    async def create_user_task(self, user_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """为用户创建任务"""
        try:
            # 1. 验证用户存在
            user = await self.user_repo.get_user_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "User not found",
                    "task_id": None
                }
            
            # 2. 检查用户权限和积分
            task_type = task_data.get('task_type')
            permission_check = await self._check_task_permissions(user_id, task_type)
            if not permission_check['allowed']:
                return {
                    "success": False,
                    "error": permission_check['reason'],
                    "task_id": None
                }
            
            # 3. 调用 Event Service 创建任务
            import aiohttp
            async with aiohttp.ClientSession() as session:
                event_payload = {
                    **task_data,
                    "user_id": user_id,
                    "callback_url": f"{self.event_service_url}/process_background_feedback"
                }
                
                async with session.post(
                    f"{self.event_service_url}/api/tasks",
                    json=event_payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # 4. 记录用户任务
                        await self._record_user_task_activity(user_id, {
                            "action": "task_created",
                            "task_id": result.get("task_id"),
                            "task_type": task_type,
                            "credits_consumed": result.get("credits_consumed", 0)
                        })
                        
                        return {
                            "success": True,
                            "task_id": result.get("task_id"),
                            "message": "Task created successfully",
                            "credits_consumed": result.get("credits_consumed", 0)
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Event service error: {error_text}",
                            "task_id": None
                        }
                        
        except Exception as e:
            logger.error(f"Failed to create user task: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_id": None
            }
    
    async def get_user_tasks(self, user_id: str, status: Optional[str] = None, 
                           task_type: Optional[str] = None) -> Dict[str, Any]:
        """获取用户任务列表"""
        try:
            # 验证用户
            user = await self.user_repo.get_user_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "User not found",
                    "tasks": []
                }
            
            # 从数据库获取用户任务
            query = self.db.table('user_tasks').select('*').eq('user_id', user_id)
            
            if status:
                query = query.eq('status', status)
            if task_type:
                query = query.eq('task_type', task_type)
                
            result = query.order('created_at', desc=True).execute()
            tasks = result.data if result.data else []
            
            # 增强任务信息
            enhanced_tasks = []
            for task in tasks:
                enhanced_task = await self._enhance_task_info(task)
                enhanced_tasks.append(enhanced_task)
            
            return {
                "success": True,
                "tasks": enhanced_tasks,
                "count": len(enhanced_tasks),
                "filters": {
                    "status": status,
                    "task_type": task_type
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get user tasks: {e}")
            return {
                "success": False,
                "error": str(e),
                "tasks": []
            }
    
    async def update_task_status(self, user_id: str, task_id: str, 
                               new_status: str) -> Dict[str, Any]:
        """更新任务状态"""
        try:
            # 验证任务所有权
            task = await self._get_user_task(user_id, task_id)
            if not task:
                return {
                    "success": False,
                    "error": "Task not found or access denied"
                }
            
            # 调用 Event Service 更新状态
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    f"{self.event_service_url}/api/tasks/{task_id}",
                    json={"status": new_status, "user_id": user_id}
                ) as response:
                    if response.status == 200:
                        # 记录活动
                        await self._record_user_task_activity(user_id, {
                            "action": "status_updated",
                            "task_id": task_id,
                            "old_status": task.get("status"),
                            "new_status": new_status
                        })
                        
                        return {
                            "success": True,
                            "message": f"Task status updated to {new_status}"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Event service error: {error_text}"
                        }
                        
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_user_task(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """删除用户任务"""
        try:
            # 验证任务所有权
            task = await self._get_user_task(user_id, task_id)
            if not task:
                return {
                    "success": False,
                    "error": "Task not found or access denied"
                }
            
            # 调用 Event Service 删除任务
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.event_service_url}/api/tasks/{task_id}",
                    params={"user_id": user_id}
                ) as response:
                    if response.status == 200:
                        # 记录活动
                        await self._record_user_task_activity(user_id, {
                            "action": "task_deleted",
                            "task_id": task_id,
                            "task_type": task.get("task_type")
                        })
                        
                        return {
                            "success": True,
                            "message": "Task deleted successfully"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Event service error: {error_text}"
                        }
                        
        except Exception as e:
            logger.error(f"Failed to delete task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_task_analytics(self, user_id: str, time_period: str = "30d") -> Dict[str, Any]:
        """获取用户任务分析数据"""
        try:
            # 计算时间范围
            if time_period == "7d":
                since = datetime.now() - timedelta(days=7)
            elif time_period == "30d":
                since = datetime.now() - timedelta(days=30)
            elif time_period == "90d":
                since = datetime.now() - timedelta(days=90)
            else:
                since = datetime.now() - timedelta(days=30)
            
            # 获取任务数据
            tasks_result = self.db.table('user_tasks')\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('created_at', since.isoformat())\
                .execute()
            
            tasks = tasks_result.data if tasks_result.data else []
            
            # 分析数据
            analytics = {
                "total_tasks": len(tasks),
                "active_tasks": len([t for t in tasks if t.get('status') == 'active']),
                "completed_tasks": len([t for t in tasks if t.get('status') == 'completed']),
                "failed_tasks": len([t for t in tasks if t.get('status') == 'failed']),
                "task_types": {},
                "creation_trend": {},
                "success_rate": 0.0,
                "time_period": time_period
            }
            
            # 任务类型分布
            for task in tasks:
                task_type = task.get('task_type', 'unknown')
                analytics["task_types"][task_type] = analytics["task_types"].get(task_type, 0) + 1
            
            # 成功率计算
            completed = analytics["completed_tasks"]
            total_finished = completed + analytics["failed_tasks"]
            if total_finished > 0:
                analytics["success_rate"] = round(completed / total_finished * 100, 2)
            
            return {
                "success": True,
                "analytics": analytics
            }
            
        except Exception as e:
            logger.error(f"Failed to get task analytics: {e}")
            return {
                "success": False,
                "error": str(e),
                "analytics": {}
            }
    
    async def get_task_templates(self, user_id: str) -> Dict[str, Any]:
        """获取任务模板"""
        try:
            # 基础模板
            templates = {
                "news_monitor": {
                    "name": "新闻监控",
                    "description": "监控指定关键词的新闻变化",
                    "config_template": {
                        "keywords": ["关键词1", "关键词2"],
                        "sources": ["新闻源1", "新闻源2"],
                        "check_interval_minutes": 30,
                        "urgency_threshold": 0.7
                    },
                    "credits_cost": 2.0
                },
                "weather_alert": {
                    "name": "天气预警",
                    "description": "监控天气变化并发送预警",
                    "config_template": {
                        "location": "城市名",
                        "alert_types": ["rain", "temperature"],
                        "temperature_threshold": {"min": 0, "max": 35},
                        "check_interval_minutes": 60
                    },
                    "credits_cost": 1.0
                },
                "price_tracker": {
                    "name": "价格跟踪",
                    "description": "跟踪商品价格变化",
                    "config_template": {
                        "product_urls": ["商品链接"],
                        "target_price": 299.0,
                        "price_drop_threshold": 0.1,
                        "check_interval_minutes": 120
                    },
                    "credits_cost": 1.5
                },
                "daily_weather": {
                    "name": "每日天气",
                    "description": "每天定时发送天气预报",
                    "config_template": {
                        "location": "城市名",
                        "notification_time": "08:00",
                        "include_forecast": True,
                        "include_aqi": True
                    },
                    "credits_cost": 0.5
                },
                "daily_news": {
                    "name": "每日新闻",
                    "description": "每天定时发送新闻摘要",
                    "config_template": {
                        "categories": ["科技", "财经"],
                        "sources": ["新闻源"],
                        "notification_time": "08:00",
                        "max_articles": 10
                    },
                    "credits_cost": 1.0
                }
            }
            
            # 根据用户订阅等级过滤模板
            user = await self.user_repo.get_user_by_id(user_id)
            subscription_level = user.get('subscription_status', 'free') if user else 'free'
            
            if subscription_level == 'free':
                # 免费用户只能使用基础模板
                allowed_templates = ["daily_weather", "daily_news"]
                templates = {k: v for k, v in templates.items() if k in allowed_templates}
            
            return {
                "success": True,
                "templates": templates,
                "subscription_level": subscription_level
            }
            
        except Exception as e:
            logger.error(f"Failed to get task templates: {e}")
            return {
                "success": False,
                "error": str(e),
                "templates": {}
            }
    
    async def _check_task_permissions(self, user_id: str, task_type: str) -> Dict[str, Any]:
        """检查用户任务权限"""
        try:
            user = await self.user_repo.get_user_by_id(user_id)
            if not user:
                return {"allowed": False, "reason": "User not found"}
            
            subscription_status = user.get('subscription_status', 'free')
            
            # 免费用户限制
            if subscription_status == 'free':
                free_allowed = ["daily_weather", "daily_news"]
                if task_type not in free_allowed:
                    return {"allowed": False, "reason": "Premium feature requires subscription"}
                
                # 检查免费用户任务数量限制
                active_tasks = self.db.table('user_tasks')\
                    .select('id')\
                    .eq('user_id', user_id)\
                    .eq('status', 'active')\
                    .execute()
                
                if len(active_tasks.data) >= 3:  # 免费用户最多3个活跃任务
                    return {"allowed": False, "reason": "Free tier limited to 3 active tasks"}
            
            return {"allowed": True, "reason": None}
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return {"allowed": False, "reason": str(e)}
    
    async def _get_user_task(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """获取用户特定任务"""
        try:
            result = self.db.table('user_tasks')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('task_id', task_id)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Failed to get user task: {e}")
            return None
    
    async def _enhance_task_info(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """增强任务信息"""
        enhanced = task.copy()
        
        # 添加运行时信息
        if task.get('last_check'):
            last_check = datetime.fromisoformat(task['last_check'].replace('Z', '+00:00'))
            enhanced['time_since_last_check'] = str(datetime.now() - last_check.replace(tzinfo=None))
        
        # 添加任务类型友好名称
        type_names = {
            "news_monitor": "新闻监控",
            "weather_alert": "天气预警", 
            "price_tracker": "价格跟踪",
            "daily_weather": "每日天气",
            "daily_news": "每日新闻"
        }
        enhanced['type_display_name'] = type_names.get(task.get('task_type'), task.get('task_type'))
        
        return enhanced
    
    async def _record_user_task_activity(self, user_id: str, activity: Dict[str, Any]):
        """记录用户任务活动"""
        try:
            activity_record = {
                "user_id": user_id,
                "activity_type": "task_management",
                "activity_data": activity,
                "timestamp": datetime.now().isoformat()
            }
            
            # 这里可以记录到用户活动日志表
            logger.info(f"User {user_id} task activity: {activity}")
            
        except Exception as e:
            logger.error(f"Failed to record task activity: {e}")