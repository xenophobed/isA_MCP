"""
User Management Service

提供完整的用户生命周期管理服务
整合认证、订阅和支付服务，提供统一的用户管理接口
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import json

from .models import (
    User, UserCreate, UserUpdate, UserResponse,
    CreditConsumption, CreditConsumptionResponse,
    ApiUsage, ApiUsageCreate, SubscriptionStatus
)
from .auth_service import Auth0Service
from .subscription_service import SubscriptionService
from .payment_service import PaymentService
from .data_integration import UserDatabaseService


logger = logging.getLogger(__name__)


class UserService:
    """用户管理服务类"""
    
    def __init__(self, auth_service: Auth0Service, 
                 subscription_service: SubscriptionService,
                 payment_service: PaymentService,
                 use_database: bool = True):
        """
        初始化用户服务
        
        Args:
            auth_service: Auth0 认证服务
            subscription_service: 订阅管理服务
            payment_service: 支付服务
            use_database: 是否使用数据库（默认True）
        """
        self.auth_service = auth_service
        self.subscription_service = subscription_service
        self.payment_service = payment_service
        self.use_database = use_database
        
        # 初始化数据库服务
        if use_database:
            try:
                self.db_service = UserDatabaseService()
                logger.info("Database integration enabled")
            except Exception as e:
                logger.warning(f"Database integration failed, falling back to cache: {e}")
                self.use_database = False
                self.db_service = None
        else:
            self.db_service = None
        
        # 临时用户存储（仅在数据库不可用时使用）
        self._users_cache: Dict[str, User] = {}
        self._user_id_counter = 1

    async def get_user_by_auth0_id(self, auth0_id: str) -> Optional[User]:
        """通过 Auth0 ID 获取用户"""
        if self.use_database and self.db_service:
            try:
                user_data = await self.db_service.get_user_by_auth0_id(auth0_id)
                if user_data:
                    user = User(**user_data)
                    logger.info(f"User found in database: {auth0_id}")
                    return user
                logger.info(f"User not found in database: {auth0_id}")
                return None
            except Exception as e:
                logger.error(f"Database error, falling back to cache: {e}")
        
        # Fallback to cache
        user = self._users_cache.get(auth0_id)
        if user:
            logger.info(f"User found in cache: {auth0_id}")
            return user
        logger.info(f"User not found: {auth0_id}")
        return None

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        通过内部 ID 获取用户
        
        Args:
            user_id: 内部用户ID
            
        Returns:
            用户对象，不存在返回None
        """
        try:
            if self.use_database and self.db_service:
                user_data = await self.db_service.get_user_by_id(user_id)
                if user_data:
                    return User(**user_data)
                return None
            
            # Fallback to cache
            for user in self._users_cache.values():
                if user.id == user_id:
                    return user
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None

    async def create_user(self, auth0_id: str, email: str, name: str) -> User:
        """创建新用户"""
        if self.use_database and self.db_service:
            try:
                user_data = await self.db_service.create_user(
                    auth0_id=auth0_id,
                    email=email,
                    name=name,
                    credits_remaining=1000,
                    credits_total=1000,
                    subscription_status="free"
                )
                if user_data:
                    user = User(**user_data)
                    logger.info(f"User created in database: {auth0_id} ({email})")
                    return user
            except Exception as e:
                logger.error(f"Database create user failed, falling back to cache: {e}")
        
        # Fallback to cache
        now = datetime.utcnow()
        user = User(
            id=self._user_id_counter,
            auth0_id=auth0_id,
            email=email,
            name=name,
            credits_remaining=1000,
            credits_total=1000,
            subscription_status=SubscriptionStatus.FREE,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        self._users_cache[auth0_id] = user
        self._user_id_counter += 1
        
        logger.info(f"User created in cache: {auth0_id} ({email})")
        return user

    async def ensure_user_exists(self, auth0_id: str, email: str, name: str) -> User:
        """
        确保用户存在，不存在则创建
        
        Args:
            auth0_id: Auth0 用户ID
            email: 用户邮箱
            name: 用户姓名
            
        Returns:
            用户对象
        """
        try:
            user = await self.get_user_by_auth0_id(auth0_id)
            
            if not user:
                user = await self.create_user(auth0_id, email, name)
            else:
                # 更新用户信息
                if user.email != email or user.name != name:
                    if user.id is not None:
                        await self.update_user(user.id, UserUpdate(
                            email=email, 
                            name=name,
                            credits_remaining=user.credits_remaining,
                            subscription_status=user.subscription_status,
                            is_active=user.is_active
                        ))
                    user.email = email
                    user.name = name
                    user.updated_at = datetime.utcnow()
                    self._users_cache[auth0_id] = user
            
            return user
            
        except Exception as e:
            logger.error(f"Error ensuring user exists: {str(e)}")
            raise ValueError(f"Failed to ensure user exists: {str(e)}")

    async def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """更新用户信息"""
        if self.use_database and self.db_service:
            try:
                update_data = user_update.model_dump(exclude_unset=True)
                success = await self.db_service.update_user(user_id, update_data)
                if success:
                    # Return updated user
                    return await self.get_user_by_id(user_id)
            except Exception as e:
                logger.error(f"Database update user failed: {e}")
        
        # Fallback to cache
        for user in self._users_cache.values():
            if user.id == user_id:
                update_data = user_update.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    if hasattr(user, field):
                        setattr(user, field, value)
                user.updated_at = datetime.utcnow()
                return user
        return None

    async def consume_credits(self, user_id: int, amount: int, 
                            reason: str = "api_call", 
                            endpoint: Optional[str] = None) -> CreditConsumptionResponse:
        """
        消费用户积分
        
        Args:
            user_id: 用户ID
            amount: 消费数量
            reason: 消费原因
            endpoint: API端点（可选）
            
        Returns:
            消费结果
            
        Example:
            >>> response = await user_service.consume_credits(
            ...     user_id=123, amount=10, reason="ai_request"
            ... )
            >>> print(response.success)
            True
        """
        try:
            user = await self.get_user_by_id(user_id)
            
            if not user:
                return CreditConsumptionResponse(
                    success=False,
                    remaining_credits=0,
                    consumed_amount=0,
                    message="用户不存在"
                )
            
            if user.credits_remaining < amount:
                return CreditConsumptionResponse(
                    success=False,
                    remaining_credits=user.credits_remaining,
                    consumed_amount=0,
                    message="积分不足"
                )
            
            # 扣除积分
            user.credits_remaining -= amount
            user.updated_at = datetime.utcnow()
            
            # 更新缓存
            self._users_cache[user.auth0_id] = user
            
            # 记录使用情况
            await self.log_api_usage(
                user_id=user_id,
                endpoint=endpoint or reason,
                tokens_used=amount,
                request_data=json.dumps({"reason": reason, "amount": amount})
            )
            
            logger.info(f"Credits consumed: user={user_id}, amount={amount}, remaining={user.credits_remaining}")
            
            return CreditConsumptionResponse(
                success=True,
                remaining_credits=user.credits_remaining,
                consumed_amount=amount,
                message=f"成功消费 {amount} 积分"
            )
            
        except Exception as e:
            logger.error(f"Error consuming credits: {str(e)}")
            return CreditConsumptionResponse(
                success=False,
                remaining_credits=0,
                consumed_amount=0,
                message=f"积分消费失败: {str(e)}"
            )

    async def allocate_credits_by_plan(self, user_id: int, plan: SubscriptionStatus) -> bool:
        """
        根据订阅计划分配积分
        
        Args:
            user_id: 用户ID
            plan: 订阅计划
            
        Returns:
            是否分配成功
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            # 获取计划配置
            plan_configs = self.subscription_service.plan_configs
            plan_config = plan_configs.get(plan, plan_configs[SubscriptionStatus.FREE])
            
            credits = plan_config["credits"]
            
            # 更新用户积分和订阅状态
            user.credits_total = credits
            user.credits_remaining = credits
            user.subscription_status = plan
            user.updated_at = datetime.utcnow()
            
            # 更新缓存
            self._users_cache[user.auth0_id] = user
            
            logger.info(f"Allocated {credits} credits to user {user_id} for plan {plan.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error allocating credits: {str(e)}")
            return False

    async def log_api_usage(self, user_id: int, endpoint: str, tokens_used: int = 1,
                           request_data: Optional[str] = None,
                           response_data: Optional[str] = None) -> bool:
        """
        记录 API 使用情况
        
        Args:
            user_id: 用户ID
            endpoint: API端点
            tokens_used: 使用的token数量
            request_data: 请求数据JSON字符串（可选）
            response_data: 响应数据JSON字符串（可选）
            
        Returns:
            是否记录成功
        """
        try:
            if self.use_database and self.db_service:
                success = await self.db_service.log_api_usage(
                    user_id=user_id,
                    endpoint=endpoint,
                    tokens_used=tokens_used,
                    request_data=request_data,
                    response_data=response_data
                )
                if success:
                    logger.info(f"API usage logged to database: user={user_id}, endpoint={endpoint}, tokens={tokens_used}")
                    return True
            
            # Log to local log as fallback
            logger.info(f"API usage logged locally: user={user_id}, endpoint={endpoint}, tokens={tokens_used}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging API usage: {str(e)}")
            return False

    async def get_user_info(self, auth0_id: str) -> Optional[UserResponse]:
        """
        获取用户信息响应
        
        Args:
            auth0_id: Auth0 用户ID
            
        Returns:
            用户响应对象，不存在返回None
        """
        try:
            user = await self.get_user_by_auth0_id(auth0_id)
            if not user:
                return None
            
            return UserResponse(
                user_id=user.auth0_id,
                email=user.email,
                name=user.name,
                credits=user.credits_remaining,
                credits_total=user.credits_total,
                plan=user.subscription_status,
                is_active=user.is_active
            )
            
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return None

    async def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户分析数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户分析数据
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return {"error": "用户不存在"}
            
            # 获取订阅分析
            subscription_analytics = await self.subscription_service.get_subscription_analytics(user_id)
            
            # 计算积分使用率
            credits_used = user.credits_total - user.credits_remaining
            credits_usage_percentage = (credits_used / user.credits_total * 100) if user.credits_total > 0 else 0
            
            analytics = {
                "user_info": {
                    "user_id": user.id,
                    "auth0_id": user.auth0_id,
                    "email": user.email,
                    "name": user.name,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                },
                "credits": {
                    "total": user.credits_total,
                    "remaining": user.credits_remaining,
                    "used": credits_used,
                    "usage_percentage": round(credits_usage_percentage, 2)
                },
                "subscription": subscription_analytics.get("analytics", {}) if subscription_analytics.get("success") else {},
                "account_age_days": (datetime.utcnow() - user.created_at).days if user.created_at else 0
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {str(e)}")
            return {"error": str(e)}

    async def deactivate_user(self, user_id: int, reason: str = "user_request") -> bool:
        """
        停用用户账户
        
        Args:
            user_id: 用户ID
            reason: 停用原因
            
        Returns:
            是否停用成功
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            # 更新缓存
            self._users_cache[user.auth0_id] = user
            
            # 记录停用原因
            await self.log_api_usage(
                user_id=user_id,
                endpoint="account_deactivation",
                tokens_used=0,
                request_data=json.dumps({"reason": reason, "deactivated_at": datetime.utcnow().isoformat()})
            )
            
            logger.info(f"User deactivated: {user_id}, reason: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating user: {str(e)}")
            return False

    async def reactivate_user(self, user_id: int) -> bool:
        """
        重新激活用户账户
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否激活成功
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.is_active = True
            user.updated_at = datetime.utcnow()
            
            # 更新缓存
            self._users_cache[user.auth0_id] = user
            
            # 记录重新激活
            await self.log_api_usage(
                user_id=user_id,
                endpoint="account_reactivation",
                tokens_used=0,
                request_data=json.dumps({"reactivated_at": datetime.utcnow().isoformat()})
            )
            
            logger.info(f"User reactivated: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error reactivating user: {str(e)}")
            return False

    async def verify_user_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证用户 token 并返回用户信息
        
        Args:
            token: JWT token
            
        Returns:
            验证结果和用户信息，验证失败返回None
        """
        try:
            # 验证 Auth0 token
            payload = await self.auth_service.verify_token(token)
            auth0_id = payload.get("sub")
            
            if not auth0_id:
                return None
            
            # 获取用户信息
            user = await self.get_user_by_auth0_id(auth0_id)
            
            if not user or not user.is_active:
                return None
            
            return {
                "auth0_payload": payload,
                "user": user.model_dump(),
                "verified": True
            }
            
        except Exception as e:
            logger.error(f"Error verifying user token: {str(e)}")
            return None

    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态
        
        Returns:
            服务状态信息
        """
        return {
            "service": "UserService",
            "status": "operational",
            "cached_users": len(self._users_cache),
            "services": {
                "auth_service": "connected",
                "subscription_service": "connected",
                "payment_service": "connected"
            },
            "timestamp": datetime.utcnow().isoformat()
        } 