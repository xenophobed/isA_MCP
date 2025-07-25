"""
Subscription Service V2 Implementation

新版订阅服务实现，使用Repository模式
专注于订阅业务逻辑，数据访问通过Repository层处理
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from ..models import Subscription, SubscriptionStatus, StripeSubscriptionStatus
from ..repositories import SubscriptionRepository, UserRepository
from ..repositories.exceptions import SubscriptionNotFoundException
from .base import BaseService, ServiceResult

logger = logging.getLogger(__name__)


class SubscriptionServiceV2(BaseService):
    """订阅服务V2 - 使用Repository模式"""
    
    def __init__(self, subscription_repository: SubscriptionRepository = None, 
                 user_repository: UserRepository = None):
        """
        初始化订阅服务
        
        Args:
            subscription_repository: 订阅数据仓库
            user_repository: 用户数据仓库
        """
        super().__init__("SubscriptionServiceV2")
        self.subscription_repo = subscription_repository or SubscriptionRepository()
        self.user_repo = user_repository or UserRepository()
        
        # 订阅计划配置
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
    
    async def create_subscription(self, user_id: str, plan_type: SubscriptionStatus,
                                stripe_subscription_id: Optional[str] = None,
                                stripe_customer_id: Optional[str] = None) -> ServiceResult[Subscription]:
        """
        创建新订阅
        
        Args:
            user_id: 用户ID
            plan_type: 订阅计划类型
            stripe_subscription_id: Stripe订阅ID（可选）
            stripe_customer_id: Stripe客户ID（可选）
            
        Returns:
            ServiceResult[Subscription]: 创建的订阅信息
        """
        try:
            self._log_operation("create_subscription", f"user_id={user_id}, plan={plan_type.value}")
            
            # 验证用户是否存在
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 检查是否已有活跃订阅
            existing_subscription = await self.subscription_repo.get_by_user_id(user_id)
            if existing_subscription:
                return ServiceResult.validation_error(
                    message="User already has an active subscription",
                    error_details={"existing_plan": existing_subscription.plan_type}
                )
            
            # 获取计划配置
            plan_config = self.plan_configs.get(plan_type)
            if not plan_config:
                return ServiceResult.validation_error(f"Invalid plan type: {plan_type}")
            
            # 准备订阅数据
            now = datetime.utcnow()
            subscription_data = {
                'user_id': user_id,
                'plan_type': plan_type.value,
                'status': 'active',
                'credits_included': plan_config['credits'],
                'current_period_start': now,
                'current_period_end': now + timedelta(days=plan_config['duration_days']),
                'stripe_subscription_id': stripe_subscription_id,
                'stripe_customer_id': stripe_customer_id
            }
            
            # 创建订阅
            subscription = await self.subscription_repo.create(subscription_data)
            
            if subscription:
                # 更新用户的订阅状态和积分
                await self.user_repo.update_subscription_status(user_id, plan_type.value)
                await self.user_repo.update_credits(
                    user_id, 
                    plan_config['credits'], 
                    plan_config['credits']
                )
                
                self._log_operation("subscription_created", f"subscription_id={subscription.id}")
                return ServiceResult.success(
                    data=subscription,
                    message=f"Subscription {plan_type.value} created successfully"
                )
            else:
                return ServiceResult.error("Failed to create subscription")
                
        except Exception as e:
            return self._handle_exception(e, "create subscription")
    
    async def get_subscription_by_user_id(self, user_id: str) -> ServiceResult[Subscription]:
        """
        获取用户的活跃订阅
        
        Args:
            user_id: 用户ID
            
        Returns:
            ServiceResult[Subscription]: 订阅信息
        """
        try:
            self._log_operation("get_subscription_by_user_id", f"user_id={user_id}")
            
            if not user_id:
                return ServiceResult.validation_error("User ID is required")
            
            subscription = await self.subscription_repo.get_by_user_id(user_id)
            
            if subscription:
                return ServiceResult.success(
                    data=subscription,
                    message="Subscription found successfully"
                )
            else:
                return ServiceResult.not_found("No active subscription found")
                
        except Exception as e:
            return self._handle_exception(e, "get subscription by user id")
    
    async def get_or_create_free_subscription(self, user_id: str) -> ServiceResult[Subscription]:
        """
        获取用户订阅，如果不存在则创建免费订阅
        
        Args:
            user_id: 用户ID
            
        Returns:
            ServiceResult[Subscription]: 订阅信息
        """
        try:
            self._log_operation("get_or_create_free_subscription", f"user_id={user_id}")
            
            # 先尝试获取现有订阅
            subscription_result = await self.get_subscription_by_user_id(user_id)
            
            if subscription_result.is_success:
                return subscription_result
            
            # 如果没有订阅，创建免费订阅
            if subscription_result.status.value == "not_found":
                self._log_operation("creating_free_subscription", f"user_id={user_id}")
                return await self.create_free_subscription(user_id)
            
            # 其他错误情况直接返回
            return subscription_result
            
        except Exception as e:
            return self._handle_exception(e, "get or create free subscription")
    
    async def create_free_subscription(self, user_id: str) -> ServiceResult[Subscription]:
        """
        为用户创建免费订阅
        
        Args:
            user_id: 用户ID
            
        Returns:
            ServiceResult[Subscription]: 创建的免费订阅
        """
        try:
            self._log_operation("create_free_subscription", f"user_id={user_id}")
            
            subscription = await self.subscription_repo.create_default_free_subscription(user_id)
            
            if subscription:
                # 更新用户的订阅状态
                await self.user_repo.update_subscription_status(user_id, SubscriptionStatus.FREE.value)
                
                return ServiceResult.success(
                    data=subscription,
                    message="Free subscription created successfully"
                )
            else:
                return ServiceResult.error("Failed to create free subscription")
                
        except Exception as e:
            return self._handle_exception(e, "create free subscription")
    
    async def upgrade_subscription(self, user_id: str, new_plan: SubscriptionStatus,
                                 stripe_subscription_id: Optional[str] = None) -> ServiceResult[Subscription]:
        """
        升级订阅计划
        
        Args:
            user_id: 用户ID
            new_plan: 新的订阅计划
            stripe_subscription_id: Stripe订阅ID
            
        Returns:
            ServiceResult[Subscription]: 升级后的订阅信息
        """
        try:
            self._log_operation("upgrade_subscription", f"user_id={user_id}, new_plan={new_plan.value}")
            
            # 获取当前订阅
            current_subscription_result = await self.get_subscription_by_user_id(user_id)
            if not current_subscription_result.is_success:
                return current_subscription_result
            
            current_subscription = current_subscription_result.data
            current_plan = SubscriptionStatus(current_subscription.plan_type)
            
            # 检查是否为升级
            plan_hierarchy = [SubscriptionStatus.FREE, SubscriptionStatus.PRO, SubscriptionStatus.ENTERPRISE]
            current_index = plan_hierarchy.index(current_plan)
            new_index = plan_hierarchy.index(new_plan)
            
            if new_index <= current_index:
                return ServiceResult.validation_error(
                    message="Can only upgrade to higher tier plans",
                    error_details={
                        "current_plan": current_plan.value,
                        "requested_plan": new_plan.value
                    }
                )
            
            # 获取新计划配置
            plan_config = self.plan_configs.get(new_plan)
            if not plan_config:
                return ServiceResult.validation_error(f"Invalid plan type: {new_plan}")
            
            # 更新订阅
            update_data = {
                'plan_type': new_plan.value,
                'credits_included': plan_config['credits'],
                'stripe_subscription_id': stripe_subscription_id
            }
            
            success = await self.subscription_repo.update(current_subscription.id, update_data)
            
            if success:
                # 更新用户状态和积分
                await self.user_repo.update_subscription_status(user_id, new_plan.value)
                await self.user_repo.update_credits(
                    user_id,
                    plan_config['credits'],
                    plan_config['credits']
                )
                
                # 获取更新后的订阅
                updated_subscription = await self.subscription_repo.get_by_user_id(user_id)
                
                return ServiceResult.success(
                    data=updated_subscription,
                    message=f"Subscription upgraded to {new_plan.value} successfully"
                )
            else:
                return ServiceResult.error("Failed to upgrade subscription")
                
        except Exception as e:
            return self._handle_exception(e, "upgrade subscription")
    
    async def cancel_subscription(self, user_id: str, immediate: bool = False) -> ServiceResult[Dict[str, Any]]:
        """
        取消订阅
        
        Args:
            user_id: 用户ID
            immediate: 是否立即取消
            
        Returns:
            ServiceResult[Dict]: 取消结果
        """
        try:
            self._log_operation("cancel_subscription", f"user_id={user_id}, immediate={immediate}")
            
            # 获取当前订阅
            subscription_result = await self.get_subscription_by_user_id(user_id)
            if not subscription_result.is_success:
                return subscription_result
            
            subscription = subscription_result.data
            
            # 取消订阅
            success = await self.subscription_repo.cancel_subscription(subscription.id, immediate)
            
            if success:
                if immediate:
                    # 立即取消，降级到免费计划
                    await self.user_repo.update_subscription_status(user_id, SubscriptionStatus.FREE.value)
                    await self._create_free_subscription_after_cancel(user_id)
                
                result_data = {
                    "subscription_id": subscription.id,
                    "canceled_immediately": immediate,
                    "effective_date": datetime.utcnow().isoformat() if immediate else subscription.current_period_end.isoformat()
                }
                
                return ServiceResult.success(
                    data=result_data,
                    message="Subscription canceled successfully"
                )
            else:
                return ServiceResult.error("Failed to cancel subscription")
                
        except Exception as e:
            return self._handle_exception(e, "cancel subscription")
    
    async def get_subscription_analytics(self, user_id: str) -> ServiceResult[Dict[str, Any]]:
        """
        获取订阅分析数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            ServiceResult[Dict]: 分析数据
        """
        try:
            self._log_operation("get_subscription_analytics", f"user_id={user_id}")
            
            subscription_result = await self.get_subscription_by_user_id(user_id)
            if not subscription_result.is_success:
                return subscription_result
            
            subscription = subscription_result.data
            plan_config = self.plan_configs.get(SubscriptionStatus(subscription.plan_type))
            
            if not plan_config:
                return ServiceResult.error("Invalid subscription plan")
            
            # 计算分析数据
            now = datetime.utcnow()
            
            # 处理时间字段，确保时区一致
            if isinstance(subscription.current_period_end, str):
                period_end = datetime.fromisoformat(subscription.current_period_end.replace('Z', ''))
                if period_end.tzinfo is not None:
                    period_end = period_end.replace(tzinfo=None)
            else:
                period_end = subscription.current_period_end
                if period_end.tzinfo is not None:
                    period_end = period_end.replace(tzinfo=None)
            
            if isinstance(subscription.current_period_start, str):
                period_start = datetime.fromisoformat(subscription.current_period_start.replace('Z', ''))
                if period_start.tzinfo is not None:
                    period_start = period_start.replace(tzinfo=None)
            else:
                period_start = subscription.current_period_start
                if period_start.tzinfo is not None:
                    period_start = period_start.replace(tzinfo=None)
            
            days_remaining = max(0, (period_end - now).days)
            days_total = (period_end - period_start).days
            usage_percentage = ((days_total - days_remaining) / days_total * 100) if days_total > 0 else 0
            
            analytics_data = {
                "subscription_id": subscription.id,
                "plan_type": subscription.plan_type,
                "status": subscription.status,
                "days_remaining": days_remaining,
                "days_total": days_total,
                "usage_percentage": round(usage_percentage, 2),
                "credits_included": subscription.credits_included,
                "features": plan_config["features"],
                "monthly_value": plan_config["price"] / 100,  # 转换为美元
                "renewal_date": period_end.isoformat(),
                "is_active": subscription.status == 'active'
            }
            
            return ServiceResult.success(
                data=analytics_data,
                message="Subscription analytics retrieved successfully"
            )
            
        except Exception as e:
            return self._handle_exception(e, "get subscription analytics")
    
    def get_plan_comparison(self) -> ServiceResult[Dict[str, Any]]:
        """
        获取所有计划的对比信息
        
        Returns:
            ServiceResult[Dict]: 计划对比数据
        """
        try:
            self._log_operation("get_plan_comparison")
            
            comparison = {}
            
            for plan, config in self.plan_configs.items():
                comparison[plan.value] = {
                    "name": plan.value.title(),
                    "price_monthly": config["price"] / 100,  # 转换为美元
                    "credits": config["credits"],
                    "features": config["features"],
                    "duration_days": config["duration_days"],
                    "recommended": plan == SubscriptionStatus.PRO  # 推荐Pro计划
                }
            
            result_data = {
                "plans": comparison,
                "currency": "USD",
                "billing_cycle": "monthly"
            }
            
            return ServiceResult.success(
                data=result_data,
                message="Plan comparison data retrieved successfully"
            )
            
        except Exception as e:
            return self._handle_exception(e, "get plan comparison")
    
    async def _create_free_subscription_after_cancel(self, user_id: str):
        """
        取消付费订阅后创建免费订阅
        
        Args:
            user_id: 用户ID
        """
        try:
            await self.subscription_repo.create_default_free_subscription(user_id)
            self._log_operation("free_subscription_created_after_cancel", f"user_id={user_id}")
        except Exception as e:
            self.logger.error(f"Failed to create free subscription after cancel: {e}")
    
    async def update_subscription_from_stripe(self, stripe_subscription_id: str, 
                                            stripe_data: Dict[str, Any]) -> ServiceResult[Subscription]:
        """
        根据Stripe webhook数据更新订阅
        
        Args:
            stripe_subscription_id: Stripe订阅ID
            stripe_data: Stripe数据
            
        Returns:
            ServiceResult[Subscription]: 更新后的订阅信息
        """
        try:
            self._log_operation("update_subscription_from_stripe", f"stripe_id={stripe_subscription_id}")
            
            # 获取订阅
            subscription = await self.subscription_repo.get_by_stripe_subscription_id(stripe_subscription_id)
            if not subscription:
                return ServiceResult.not_found("Subscription not found")
            
            # 准备更新数据
            update_data = {}
            
            if 'status' in stripe_data:
                update_data['status'] = stripe_data['status']
            
            if 'current_period_start' in stripe_data:
                update_data['current_period_start'] = datetime.fromtimestamp(
                    stripe_data['current_period_start']
                ).isoformat()
            
            if 'current_period_end' in stripe_data:
                update_data['current_period_end'] = datetime.fromtimestamp(
                    stripe_data['current_period_end']
                ).isoformat()
            
            # 更新订阅
            success = await self.subscription_repo.update_by_stripe_id(stripe_subscription_id, update_data)
            
            if success:
                updated_subscription = await self.subscription_repo.get_by_stripe_subscription_id(stripe_subscription_id)
                return ServiceResult.success(
                    data=updated_subscription,
                    message="Subscription updated from Stripe successfully"
                )
            else:
                return ServiceResult.error("Failed to update subscription from Stripe")
                
        except Exception as e:
            return self._handle_exception(e, "update subscription from stripe")
    
    async def get_subscription_by_user_id_int(self, user_id: int) -> ServiceResult[Dict[str, Any]]:
        """
        获取用户订阅（向后兼容，接收int类型user_id）
        
        Args:
            user_id: 数字用户ID
            
        Returns:
            ServiceResult[Dict]: 订阅信息（原版格式）
        """
        try:
            self._log_operation("get_subscription_by_user_id_int", f"user_id={user_id}")
            
            # 先通过数字ID获取用户，得到字符串user_id
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 使用字符串user_id获取订阅
            subscription_result = await self.get_subscription_by_user_id(user.user_id)
            
            if not subscription_result.is_success:
                return subscription_result
            
            subscription = subscription_result.data
            plan_config = self.plan_configs.get(SubscriptionStatus(subscription.plan_type))
            
            # 转换为原版格式
            legacy_format = {
                "subscription": {
                    "id": subscription.id,
                    "user_id": user_id,  # 返回数字ID以保持兼容性
                    "stripe_subscription_id": subscription.stripe_subscription_id,
                    "stripe_customer_id": subscription.stripe_customer_id,
                    "plan_type": subscription.plan_type,
                    "status": subscription.status,
                    "current_period_start": subscription.current_period_start,
                    "current_period_end": subscription.current_period_end,
                    "created_at": subscription.created_at,
                    "updated_at": subscription.updated_at
                },
                "plan_config": plan_config,
                "is_active": subscription.status == 'active'
            }
            
            return ServiceResult.success(
                data=legacy_format,
                message="Subscription found successfully"
            )
            
        except Exception as e:
            return self._handle_exception(e, "get subscription by user id int")
    
    async def update_subscription_status(self, subscription_id: int, 
                                       status: 'StripeSubscriptionStatus',
                                       stripe_data: Optional[Dict[str, Any]] = None) -> ServiceResult[bool]:
        """
        更新订阅状态
        
        Args:
            subscription_id: 订阅ID
            status: 新的订阅状态
            stripe_data: Stripe数据（可选）
            
        Returns:
            ServiceResult[bool]: 是否更新成功
        """
        try:
            self._log_operation("update_subscription_status", f"subscription_id={subscription_id}, status={status.value}")
            
            update_data = {"status": status.value}
            
            if stripe_data:
                if "current_period_start" in stripe_data:
                    update_data["current_period_start"] = datetime.fromtimestamp(
                        stripe_data["current_period_start"]
                    ).isoformat()
                if "current_period_end" in stripe_data:
                    update_data["current_period_end"] = datetime.fromtimestamp(
                        stripe_data["current_period_end"]
                    ).isoformat()
            
            success = await self.subscription_repo.update(subscription_id, update_data)
            
            if success:
                return ServiceResult.success(
                    data=True,
                    message=f"Subscription status updated to {status.value}"
                )
            else:
                return ServiceResult.error("Failed to update subscription status")
                
        except Exception as e:
            return self._handle_exception(e, "update subscription status")
    
    async def downgrade_subscription(self, user_id: int, 
                                   new_plan: SubscriptionStatus) -> ServiceResult[Dict[str, Any]]:
        """
        降级订阅计划
        
        Args:
            user_id: 数字用户ID
            new_plan: 新的订阅计划
            
        Returns:
            ServiceResult[Dict]: 降级结果
        """
        try:
            self._log_operation("downgrade_subscription", f"user_id={user_id}, new_plan={new_plan.value}")
            
            # 获取用户
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 获取当前订阅
            current_subscription_result = await self.get_subscription_by_user_id(user.user_id)
            if not current_subscription_result.is_success:
                return current_subscription_result
            
            current_subscription = current_subscription_result.data
            current_plan = SubscriptionStatus(current_subscription.plan_type)
            
            # 检查是否为降级
            plan_hierarchy = [SubscriptionStatus.FREE, SubscriptionStatus.PRO, SubscriptionStatus.ENTERPRISE]
            current_index = plan_hierarchy.index(current_plan)
            new_index = plan_hierarchy.index(new_plan)
            
            if new_index >= current_index:
                return ServiceResult.validation_error(
                    message="Can only downgrade to lower tier plans",
                    error_details={
                        "current_plan": current_plan.value,
                        "requested_plan": new_plan.value
                    }
                )
            
            # 获取新计划配置
            plan_config = self.plan_configs.get(new_plan)
            if not plan_config:
                return ServiceResult.validation_error(f"Invalid plan type: {new_plan}")
            
            # 降级通常在下个周期生效
            update_data = {
                'plan_type': new_plan.value,
                'credits_included': plan_config['credits'],
                'downgrade_at_period_end': True
            }
            
            success = await self.subscription_repo.update(current_subscription.id, update_data)
            
            if success:
                result_data = {
                    "success": True,
                    "old_plan": current_plan.value,
                    "new_plan": new_plan.value,
                    "new_config": plan_config,
                    "effective_date": "下个计费周期",
                    "message": f"订阅将在下个周期降级至 {new_plan.value}"
                }
                
                return ServiceResult.success(
                    data=result_data,
                    message=f"Subscription will be downgraded to {new_plan.value} at period end"
                )
            else:
                return ServiceResult.error("Failed to downgrade subscription")
                
        except Exception as e:
            return self._handle_exception(e, "downgrade subscription")
    
    async def check_subscription_expiry(self, user_id: int) -> ServiceResult[Dict[str, Any]]:
        """
        检查订阅是否即将过期
        
        Args:
            user_id: 数字用户ID
            
        Returns:
            ServiceResult[Dict]: 过期检查结果
        """
        try:
            self._log_operation("check_subscription_expiry", f"user_id={user_id}")
            
            # 获取用户
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 获取订阅
            subscription_result = await self.get_subscription_by_user_id(user.user_id)
            
            if not subscription_result.is_success:
                return ServiceResult.success(
                    data={
                        "has_subscription": False,
                        "message": "用户没有有效订阅"
                    },
                    message="No subscription found"
                )
            
            subscription = subscription_result.data
            
            # 处理时间字段
            if isinstance(subscription.current_period_end, str):
                current_period_end = datetime.fromisoformat(subscription.current_period_end.replace('Z', ''))
            else:
                current_period_end = subscription.current_period_end
            
            if current_period_end.tzinfo is not None:
                current_period_end = current_period_end.replace(tzinfo=None)
            
            now = datetime.utcnow()
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
            
            expiry_data = {
                "has_subscription": True,
                "status": status,
                "days_remaining": max(0, days_remaining),
                "expiry_date": current_period_end.isoformat(),
                "plan_type": subscription.plan_type,
                "needs_renewal": days_remaining <= warning_threshold,
                "is_expired": days_remaining <= 0
            }
            
            return ServiceResult.success(
                data=expiry_data,
                message="Subscription expiry check completed"
            )
            
        except Exception as e:
            return self._handle_exception(e, "check subscription expiry")
    
    async def create_subscription_legacy(self, user_id: int, plan_type: SubscriptionStatus,
                                       stripe_subscription_id: Optional[str] = None,
                                       stripe_customer_id: Optional[str] = None) -> ServiceResult[Dict[str, Any]]:
        """
        创建订阅（向后兼容版本）
        
        Args:
            user_id: 数字用户ID
            plan_type: 订阅计划类型
            stripe_subscription_id: Stripe订阅ID
            stripe_customer_id: Stripe客户ID
            
        Returns:
            ServiceResult[Dict]: 创建结果（原版格式）
        """
        try:
            self._log_operation("create_subscription_legacy", f"user_id={user_id}, plan={plan_type.value}")
            
            # 获取用户字符串ID
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 使用新版方法创建订阅
            result = await self.create_subscription(
                user.user_id, 
                plan_type, 
                stripe_subscription_id, 
                stripe_customer_id
            )
            
            if result.is_success:
                subscription = result.data
                plan_config = self.plan_configs.get(plan_type)
                
                # 转换为原版格式
                legacy_result = {
                    "subscription": subscription.model_dump() if hasattr(subscription, 'model_dump') else subscription.dict(),
                    "plan_config": plan_config,
                    "success": True,
                    "message": f"订阅 {plan_type.value} 创建成功"
                }
                
                return ServiceResult.success(
                    data=legacy_result,
                    message=result.message
                )
            else:
                return result
                
        except Exception as e:
            return self._handle_exception(e, "create subscription legacy")
    
    async def get_subscription_analytics_legacy(self, user_id: int) -> ServiceResult[Dict[str, Any]]:
        """
        获取订阅分析数据（向后兼容版本）
        
        Args:
            user_id: 数字用户ID
            
        Returns:
            ServiceResult[Dict]: 分析数据（原版格式）
        """
        try:
            self._log_operation("get_subscription_analytics_legacy", f"user_id={user_id}")
            
            # 获取用户
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 使用新版方法
            result = await self.get_subscription_analytics(user.user_id)
            
            if result.is_success:
                # 包装为原版格式
                legacy_result = {
                    "success": True,
                    "analytics": result.data
                }
                
                return ServiceResult.success(
                    data=legacy_result,
                    message=result.message
                )
            else:
                return ServiceResult.success(
                    data={
                        "success": False,
                        "message": result.message
                    },
                    message="Failed to get subscription analytics"
                )
                
        except Exception as e:
            return self._handle_exception(e, "get subscription analytics legacy")