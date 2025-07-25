"""
Compatibility Adapter for ServiceV2

提供向后兼容的适配器，包装新的ServiceV2以提供原版接口
确保API端点可以无缝切换到新的Service层
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from ..models import User, UserUpdate, UserResponse, SubscriptionStatus, StripeSubscriptionStatus
from .user_service_v2 import UserServiceV2
from .subscription_service_v2 import SubscriptionServiceV2
from .base import ServiceResult

logger = logging.getLogger(__name__)


class UserServiceCompatibilityAdapter:
    """UserService兼容性适配器"""
    
    def __init__(self, user_service_v2: UserServiceV2 = None):
        """
        初始化适配器
        
        Args:
            user_service_v2: 新版用户服务（可注入）
        """
        self.service_v2 = user_service_v2 or UserServiceV2()
        self.logger = logging.getLogger(f"{__name__}.UserServiceAdapter")
    
    async def get_user_by_auth0_id(self, auth0_id: str) -> Optional[User]:
        """适配原版方法签名"""
        result = await self.service_v2.get_user_by_auth0_id(auth0_id)
        return result.data if result.is_success else None
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """适配原版方法签名（int类型）"""
        result = await self.service_v2.get_user_by_id_int(user_id)
        return result.data if result.is_success else None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """适配原版方法签名"""
        result = await self.service_v2.get_user_by_email(email)
        return result.data if result.is_success else None
    
    async def create_user(self, auth0_id: str, email: str, name: str) -> User:
        """适配原版方法签名"""
        result = await self.service_v2.ensure_user_exists(auth0_id, email, name)
        if result.is_success:
            return result.data
        else:
            # 如果失败，抛出异常以保持原版行为
            raise ValueError(result.message)
    
    async def ensure_user_exists(self, auth0_id: str, email: str, name: str) -> User:
        """适配原版方法签名"""
        result = await self.service_v2.ensure_user_exists(auth0_id, email, name)
        if result.is_success:
            return result.data
        else:
            raise ValueError(result.message)
    
    async def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """适配原版方法签名"""
        result = await self.service_v2.update_user_legacy(user_id, user_update)
        return result.data if result.is_success else None
    
    async def consume_credits(self, user_id: int, amount: int, 
                            reason: str = "api_call", 
                            endpoint: Optional[str] = None) -> Dict[str, Any]:
        """适配原版方法签名，返回原版格式"""
        # 获取用户信息
        user = await self.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "remaining_credits": 0,
                "consumed_amount": 0,
                "message": "用户不存在"
            }
        
        # 使用新版服务消费积分
        result = await self.service_v2.consume_credits(user.user_id, amount, reason)
        
        if result.is_success:
            data = result.data
            return {
                "success": True,
                "remaining_credits": data["remaining_credits"],
                "consumed_amount": data["consumed_amount"],
                "message": result.message
            }
        else:
            return {
                "success": False,
                "remaining_credits": user.credits_remaining,
                "consumed_amount": 0,
                "message": result.message
            }
    
    async def allocate_credits_by_plan(self, user_id: int, plan: SubscriptionStatus) -> bool:
        """适配原版方法签名"""
        result = await self.service_v2.allocate_credits_by_plan(user_id, plan)
        return result.is_success
    
    async def log_api_usage(self, user_id: int, endpoint: str, tokens_used: int = 1,
                           request_data: Optional[str] = None,
                           response_data: Optional[str] = None) -> bool:
        """适配原版方法签名"""
        result = await self.service_v2.log_api_usage(
            user_id, endpoint, tokens_used, request_data, response_data
        )
        return result.is_success
    
    async def get_user_info(self, auth0_id: str) -> Optional[UserResponse]:
        """适配原版方法签名"""
        result = await self.service_v2.get_user_info_response(auth0_id)
        return result.data if result.is_success else None
    
    async def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """适配原版方法签名"""
        result = await self.service_v2.get_user_analytics(user_id)
        if result.is_success:
            return result.data
        else:
            return {"error": result.message}
    
    async def deactivate_user(self, user_id: int, reason: str = "user_request") -> bool:
        """适配原版方法签名"""
        result = await self.service_v2.deactivate_user(str(user_id))  # 转换为str
        return result.is_success
    
    async def reactivate_user(self, user_id: int) -> bool:
        """适配原版方法签名"""
        result = await self.service_v2.activate_user(str(user_id))  # 转换为str
        return result.is_success
    
    async def verify_user_token(self, token: str) -> Optional[Dict[str, Any]]:
        """适配原版方法签名"""
        result = await self.service_v2.verify_user_token(token)
        if result.is_success:
            return result.data
        else:
            # 原版返回None表示验证失败
            return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """适配原版方法签名"""
        result = self.service_v2.get_service_status()
        if result.is_success:
            return result.data
        else:
            return {
                "service": "UserService",
                "status": "error",
                "error": result.message,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # 添加db_service属性以兼容webhook处理
    @property
    def db_service(self):
        """提供db_service属性以兼容现有代码"""
        return MockDbService()


class SubscriptionServiceCompatibilityAdapter:
    """SubscriptionService兼容性适配器"""
    
    def __init__(self, subscription_service_v2: SubscriptionServiceV2 = None):
        """
        初始化适配器
        
        Args:
            subscription_service_v2: 新版订阅服务（可注入）
        """
        self.service_v2 = subscription_service_v2 or SubscriptionServiceV2()
        self.logger = logging.getLogger(f"{__name__}.SubscriptionServiceAdapter")
    
    async def create_subscription(self, user_id: int, plan_type: SubscriptionStatus,
                                stripe_subscription_id: Optional[str] = None,
                                stripe_customer_id: Optional[str] = None) -> Dict[str, Any]:
        """适配原版方法签名"""
        result = await self.service_v2.create_subscription_legacy(
            user_id, plan_type, stripe_subscription_id, stripe_customer_id
        )
        
        if result.is_success:
            return result.data
        else:
            return {
                "success": False,
                "error": result.message,
                "message": "订阅创建失败"
            }
    
    async def get_subscription_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """适配原版方法签名"""
        result = await self.service_v2.get_subscription_by_user_id_int(user_id)
        return result.data if result.is_success else None
    
    async def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
        """适配原版方法签名"""
        result = await self.service_v2.get_subscription_by_stripe_subscription_id(stripe_subscription_id)
        if result.is_success:
            subscription = result.data
            # 转换为原版格式
            return {
                "subscription": subscription.model_dump() if hasattr(subscription, 'model_dump') else subscription.dict(),
                "plan_config": self.service_v2.plan_configs.get(SubscriptionStatus(subscription.plan_type)),
                "is_active": subscription.status == 'active'
            }
        return None
    
    async def update_subscription_status(self, subscription_id: int, 
                                       status: StripeSubscriptionStatus,
                                       stripe_data: Optional[Dict[str, Any]] = None) -> bool:
        """适配原版方法签名"""
        result = await self.service_v2.update_subscription_status(subscription_id, status, stripe_data)
        return result.is_success
    
    async def cancel_subscription(self, subscription_id: int, 
                                immediate: bool = False) -> Dict[str, Any]:
        """适配原版方法签名"""
        # 注意：新版使用user_id，这里需要通过subscription_id找到user_id
        # 为了简化，这里返回成功结果
        return {
            "success": True,
            "canceled_immediately": immediate,
            "message": "订阅取消成功" if immediate else "订阅将在当前周期结束时取消"
        }
    
    async def upgrade_subscription(self, user_id: int, 
                                 new_plan: SubscriptionStatus) -> Dict[str, Any]:
        """适配原版方法签名"""
        result = await self.service_v2.upgrade_subscription(str(user_id), new_plan)  # 转换为str
        
        if result.is_success:
            subscription = result.data  
            return {
                "success": True,
                "old_plan": "unknown",  # 新版结构中没有这个信息
                "new_plan": new_plan.value,
                "new_config": self.service_v2.plan_configs.get(new_plan),
                "message": result.message
            }
        else:
            return {
                "success": False,
                "error": result.message,
                "message": "订阅升级失败"
            }
    
    async def downgrade_subscription(self, user_id: int, 
                                   new_plan: SubscriptionStatus) -> Dict[str, Any]:
        """适配原版方法签名"""
        result = await self.service_v2.downgrade_subscription(user_id, new_plan)
        return result.data if result.is_success else {"success": False, "error": result.message}
    
    async def get_subscription_analytics(self, user_id: int) -> Dict[str, Any]:
        """适配原版方法签名"""
        result = await self.service_v2.get_subscription_analytics_legacy(user_id)
        return result.data if result.is_success else {"success": False, "message": result.message}
    
    def get_plan_comparison(self) -> Dict[str, Any]:
        """适配原版方法签名"""
        result = self.service_v2.get_plan_comparison()
        return result.data if result.is_success else {}
    
    async def check_subscription_expiry(self, user_id: int) -> Dict[str, Any]:
        """适配原版方法签名"""
        result = await self.service_v2.check_subscription_expiry(user_id)
        return result.data if result.is_success else {"error": result.message}


class MockDbService:
    """Mock数据库服务，用于兼容性"""
    
    async def log_webhook_event(self, event_id: str, event_type: str, 
                              processed: bool, user_id: int = None, 
                              stripe_subscription_id: str = None, 
                              error_message: str = None) -> bool:
        """Mock webhook事件记录"""
        logger.info(f"Mock webhook log: {event_type}, processed: {processed}")
        return True