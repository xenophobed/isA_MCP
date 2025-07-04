"""
Subscription Management Service

提供订阅管理服务，包括订阅创建、更新、取消和计划管理
与数据库交互管理订阅生命周期
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

from .models import (
    Subscription, SubscriptionCreate, SubscriptionStatus, 
    StripeSubscriptionStatus, User
)


logger = logging.getLogger(__name__)


class SubscriptionService:
    """订阅管理服务类"""
    
    def __init__(self, database_connection=None):
        """
        初始化订阅服务
        
        Args:
            database_connection: 数据库连接（可选，将来集成数据库时使用）
        """
        self.db = database_connection
        
        # 计划配置
        self.plan_configs = {
            SubscriptionStatus.FREE: {
                "credits": 1000,
                "features": ["basic_ai", "limited_requests"],
                "price": 0,
                "duration_days": 30
            },
            SubscriptionStatus.PRO: {
                "credits": 10000,
                "features": ["advanced_ai", "priority_support", "analytics"],
                "price": 2000,  # 20美元，以分为单位
                "duration_days": 30
            },
            SubscriptionStatus.ENTERPRISE: {
                "credits": 50000,
                "features": ["premium_ai", "dedicated_support", "custom_models", "api_access"],
                "price": 10000,  # 100美元，以分为单位
                "duration_days": 30
            }
        }

    async def create_subscription(self, user_id: int, plan_type: SubscriptionStatus,
                                stripe_subscription_id: Optional[str] = None,
                                stripe_customer_id: Optional[str] = None) -> Dict[str, Any]:
        """
        创建新订阅
        
        Args:
            user_id: 用户ID
            plan_type: 订阅计划类型
            stripe_subscription_id: Stripe 订阅ID（可选）
            stripe_customer_id: Stripe 客户ID（可选）
            
        Returns:
            创建的订阅信息
            
        Example:
            >>> sub_service = SubscriptionService()
            >>> subscription = await sub_service.create_subscription(
            ...     user_id=123,
            ...     plan_type=SubscriptionStatus.PRO
            ... )
        """
        try:
            now = datetime.utcnow()
            plan_config = self.plan_configs[plan_type]
            
            subscription_data = {
                "user_id": user_id,
                "plan_type": plan_type,
                "status": StripeSubscriptionStatus.ACTIVE,
                "current_period_start": now,
                "current_period_end": now + timedelta(days=plan_config["duration_days"]),
                "stripe_subscription_id": stripe_subscription_id,
                "stripe_customer_id": stripe_customer_id,
                "created_at": now,
                "updated_at": now
            }
            
            # 这里将来会与数据库集成
            # subscription = await self.db.create_subscription(subscription_data)
            
            # 临时返回模拟数据
            subscription = Subscription(
                id=1,  # 临时ID
                user_id=subscription_data["user_id"],
                stripe_subscription_id=subscription_data["stripe_subscription_id"],
                stripe_customer_id=subscription_data["stripe_customer_id"],
                status=subscription_data["status"],
                plan_type=subscription_data["plan_type"],
                current_period_start=subscription_data["current_period_start"],
                current_period_end=subscription_data["current_period_end"],
                created_at=subscription_data["created_at"],
                updated_at=subscription_data["updated_at"]
            )
            
            logger.info(f"Subscription created for user {user_id}: {plan_type.value}")
            
            return {
                "subscription": subscription.dict(),
                "plan_config": plan_config,
                "success": True,
                "message": f"订阅 {plan_type.value} 创建成功"
            }
            
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "订阅创建失败"
            }

    async def get_subscription_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        根据用户ID获取订阅信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            订阅信息，不存在返回None
        """
        try:
            # 这里将来会与数据库集成
            # subscription = await self.db.get_subscription_by_user_id(user_id)
            
            # 临时返回模拟数据
            if user_id:
                subscription = Subscription(
                    id=1,
                    user_id=user_id,
                    stripe_subscription_id=None,
                    stripe_customer_id=None,
                    plan_type=SubscriptionStatus.FREE,
                    status=StripeSubscriptionStatus.ACTIVE,
                    current_period_start=datetime.utcnow(),
                    current_period_end=datetime.utcnow() + timedelta(days=30)
                )
                
                plan_config = self.plan_configs[subscription.plan_type]
                
                return {
                    "subscription": subscription.dict(),
                    "plan_config": plan_config,
                    "is_active": subscription.status == StripeSubscriptionStatus.ACTIVE
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting subscription for user {user_id}: {str(e)}")
            return None

    async def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 Stripe 订阅ID获取订阅信息
        
        Args:
            stripe_subscription_id: Stripe 订阅ID
            
        Returns:
            订阅信息，不存在返回None
        """
        try:
            # 这里将来会与数据库集成
            # subscription = await self.db.get_subscription_by_stripe_id(stripe_subscription_id)
            
            logger.info(f"Getting subscription by Stripe ID: {stripe_subscription_id}")
            return None  # 临时返回
            
        except Exception as e:
            logger.error(f"Error getting subscription by Stripe ID: {str(e)}")
            return None

    async def update_subscription_status(self, subscription_id: int, 
                                       status: StripeSubscriptionStatus,
                                       stripe_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        更新订阅状态
        
        Args:
            subscription_id: 订阅ID
            status: 新的订阅状态
            stripe_data: Stripe 数据（可选）
            
        Returns:
            是否更新成功
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if stripe_data:
                if "current_period_start" in stripe_data:
                    update_data["current_period_start"] = datetime.fromtimestamp(
                        stripe_data["current_period_start"]
                    )
                if "current_period_end" in stripe_data:
                    update_data["current_period_end"] = datetime.fromtimestamp(
                        stripe_data["current_period_end"]
                    )
            
            # 这里将来会与数据库集成
            # success = await self.db.update_subscription(subscription_id, update_data)
            
            logger.info(f"Subscription {subscription_id} status updated to {status.value}")
            return True  # 临时返回
            
        except Exception as e:
            logger.error(f"Error updating subscription status: {str(e)}")
            return False

    async def cancel_subscription(self, subscription_id: int, 
                                immediate: bool = False) -> Dict[str, Any]:
        """
        取消订阅
        
        Args:
            subscription_id: 订阅ID
            immediate: 是否立即取消（否则在周期结束时取消）
            
        Returns:
            取消结果
        """
        try:
            if immediate:
                status = StripeSubscriptionStatus.CANCELED
                canceled_at = datetime.utcnow()
            else:
                status = StripeSubscriptionStatus.ACTIVE  # 保持激活到周期结束
                canceled_at = None
            
            update_data = {
                "status": status,
                "canceled_at": canceled_at,
                "updated_at": datetime.utcnow()
            }
            
            # 这里将来会与数据库集成
            # success = await self.db.update_subscription(subscription_id, update_data)
            
            logger.info(f"Subscription {subscription_id} canceled (immediate: {immediate})")
            
            return {
                "success": True,
                "canceled_immediately": immediate,
                "message": "订阅取消成功" if immediate else "订阅将在当前周期结束时取消"
            }
            
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "订阅取消失败"
            }

    async def upgrade_subscription(self, user_id: int, 
                                 new_plan: SubscriptionStatus) -> Dict[str, Any]:
        """
        升级订阅计划
        
        Args:
            user_id: 用户ID
            new_plan: 新的订阅计划
            
        Returns:
            升级结果
        """
        try:
            current_subscription = await self.get_subscription_by_user_id(user_id)
            
            if not current_subscription:
                return {
                    "success": False,
                    "error": "未找到当前订阅",
                    "message": "用户没有有效订阅"
                }
            
            current_plan = SubscriptionStatus(current_subscription["subscription"]["plan_type"])
            
            # 检查是否为升级
            plan_hierarchy = [SubscriptionStatus.FREE, SubscriptionStatus.PRO, SubscriptionStatus.ENTERPRISE]
            current_index = plan_hierarchy.index(current_plan)
            new_index = plan_hierarchy.index(new_plan)
            
            if new_index <= current_index:
                return {
                    "success": False,
                    "error": "无效的升级",
                    "message": "只能升级到更高级的计划"
                }
            
            # 更新订阅计划
            update_data = {
                "plan_type": new_plan,
                "updated_at": datetime.utcnow()
            }
            
            # 这里将来会与数据库集成
            # success = await self.db.update_subscription(subscription_id, update_data)
            
            new_config = self.plan_configs[new_plan]
            
            logger.info(f"Subscription upgraded for user {user_id}: {current_plan.value} -> {new_plan.value}")
            
            return {
                "success": True,
                "old_plan": current_plan.value,
                "new_plan": new_plan.value,
                "new_config": new_config,
                "message": f"订阅已升级至 {new_plan.value}"
            }
            
        except Exception as e:
            logger.error(f"Error upgrading subscription: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "订阅升级失败"
            }

    async def downgrade_subscription(self, user_id: int, 
                                   new_plan: SubscriptionStatus) -> Dict[str, Any]:
        """
        降级订阅计划
        
        Args:
            user_id: 用户ID
            new_plan: 新的订阅计划
            
        Returns:
            降级结果
        """
        try:
            current_subscription = await self.get_subscription_by_user_id(user_id)
            
            if not current_subscription:
                return {
                    "success": False,
                    "error": "未找到当前订阅",
                    "message": "用户没有有效订阅"
                }
            
            current_plan = SubscriptionStatus(current_subscription["subscription"]["plan_type"])
            
            # 降级通常在下个周期生效
            update_data = {
                "plan_type": new_plan,
                "downgrade_at_period_end": True,
                "updated_at": datetime.utcnow()
            }
            
            # 这里将来会与数据库集成
            # success = await self.db.update_subscription(subscription_id, update_data)
            
            new_config = self.plan_configs[new_plan]
            
            logger.info(f"Subscription downgraded for user {user_id}: {current_plan.value} -> {new_plan.value}")
            
            return {
                "success": True,
                "old_plan": current_plan.value,
                "new_plan": new_plan.value,
                "new_config": new_config,
                "effective_date": "下个计费周期",
                "message": f"订阅将在下个周期降级至 {new_plan.value}"
            }
            
        except Exception as e:
            logger.error(f"Error downgrading subscription: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "订阅降级失败"
            }

    async def get_subscription_analytics(self, user_id: int) -> Dict[str, Any]:
        """
        获取订阅分析数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            分析数据
        """
        try:
            subscription_info = await self.get_subscription_by_user_id(user_id)
            
            if not subscription_info:
                return {
                    "success": False,
                    "message": "未找到订阅信息"
                }
            
            subscription = subscription_info["subscription"]
            plan_config = subscription_info["plan_config"]
            
            # 计算订阅相关指标
            current_period_start = datetime.fromisoformat(subscription["current_period_start"].replace('Z', '+00:00'))
            current_period_end = datetime.fromisoformat(subscription["current_period_end"].replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=current_period_start.tzinfo)
            
            days_remaining = (current_period_end - now).days
            days_total = (current_period_end - current_period_start).days
            usage_percentage = ((days_total - days_remaining) / days_total) * 100
            
            analytics = {
                "subscription_id": subscription["id"],
                "plan_type": subscription["plan_type"],
                "status": subscription["status"],
                "days_remaining": max(0, days_remaining),
                "days_total": days_total,
                "usage_percentage": round(usage_percentage, 2),
                "credits_allocated": plan_config["credits"],
                "features": plan_config["features"],
                "monthly_value": plan_config["price"] / 100,  # 转换为美元
                "renewal_date": subscription["current_period_end"],
                "is_active": subscription_info["is_active"]
            }
            
            return {
                "success": True,
                "analytics": analytics
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription analytics: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "获取订阅分析失败"
            }

    def get_plan_comparison(self) -> Dict[str, Any]:
        """
        获取所有计划的对比信息
        
        Returns:
            计划对比数据
        """
        comparison = {}
        
        for plan, config in self.plan_configs.items():
            comparison[plan.value] = {
                "name": plan.value.title(),
                "price_monthly": config["price"] / 100,  # 转换为美元
                "credits": config["credits"],
                "features": config["features"],
                "duration_days": config["duration_days"],
                "recommended": plan == SubscriptionStatus.PRO  # 推荐 Pro 计划
            }
        
        return {
            "plans": comparison,
            "currency": "USD",
            "billing_cycle": "monthly"
        }

    async def check_subscription_expiry(self, user_id: int) -> Dict[str, Any]:
        """
        检查订阅是否即将过期
        
        Args:
            user_id: 用户ID
            
        Returns:
            过期检查结果
        """
        try:
            subscription_info = await self.get_subscription_by_user_id(user_id)
            
            if not subscription_info:
                return {
                    "has_subscription": False,
                    "message": "用户没有有效订阅"
                }
            
            subscription = subscription_info["subscription"]
            current_period_end = datetime.fromisoformat(subscription["current_period_end"].replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=current_period_end.tzinfo)
            
            days_remaining = (current_period_end - now).days
            
            # 定义警告阈值
            warning_threshold = 7  # 7天内过期发出警告
            critical_threshold = 3  # 3天内过期为紧急
            
            status = "active"
            if days_remaining <= 0:
                status = "expired"
            elif days_remaining <= critical_threshold:
                status = "critical"
            elif days_remaining <= warning_threshold:
                status = "warning"
            
            return {
                "has_subscription": True,
                "status": status,
                "days_remaining": max(0, days_remaining),
                "expiry_date": subscription["current_period_end"],
                "plan_type": subscription["plan_type"],
                "needs_renewal": days_remaining <= warning_threshold,
                "is_expired": days_remaining <= 0
            }
            
        except Exception as e:
            logger.error(f"Error checking subscription expiry: {str(e)}")
            return {
                "error": str(e),
                "message": "检查订阅过期状态失败"
            } 