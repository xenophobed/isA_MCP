"""
User Service Implementation

User service implementation using Repository pattern
Focused on business logic with data access through Repository layer
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas.user_models import User, UserCreate, UserUpdate, UserResponse
from models.schemas.enums import SubscriptionStatus
from repositories.user_repository import UserRepository
from repositories.base import RepositoryException
from repositories.exceptions import UserNotFoundException, DuplicateEntryException
from tools.services.user_service.services.base import BaseService, ServiceResult

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """User service using Repository pattern"""
    
    def __init__(self, user_repository: UserRepository = None):
        """
        Initialize user service
        
        Args:
            user_repository: User data repository (injectable for testing)
        """
        super().__init__("UserService")
        self.user_repo = user_repository or UserRepository()
    
    async def ensure_user_exists(self, user_id: str, email: str, name: str, auth0_id: str = None) -> ServiceResult[User]:
        """
        确保用户存在，不存在则创建
        
        Args:
            user_id: 用户业务ID
            email: 用户邮箱
            name: 用户姓名
            auth0_id: Auth0用户ID (可选，默认为user_id)
            
        Returns:
            ServiceResult[User]: 用户信息结果
        """
        try:
            # 如果没有提供auth0_id，使用user_id作为auth0_id
            if auth0_id is None:
                auth0_id = user_id
                
            self._log_operation("ensure_user_exists", f"user_id={user_id}, email={email}")
            
            # 验证输入参数
            validation_error = self._validate_required_fields(
                {"user_id": user_id, "email": email, "name": name},
                ["user_id", "email", "name"]
            )
            if validation_error:
                return validation_error
            
            if not self._validate_email(email):
                return ServiceResult.validation_error(
                    message="Invalid email format",
                    error_details={"email": email}
                )
            
            # 使用Repository的ensure_user_exists方法
            try:
                user = await self.user_repo.ensure_user_exists(
                    user_id=user_id,
                    email=email,
                    name=name,
                    auth0_id=auth0_id
                )
                
                self._log_operation("user_ensured", f"user_id={user_id}")
                return ServiceResult.success(
                    data=user,
                    message="User exists or created successfully"
                )
                
            except Exception as repo_error:
                logger.error(f"Repository error: {repo_error}")
                return ServiceResult.error(f"Failed to ensure user exists: {str(repo_error)}")
                
        except DuplicateEntryException as e:
            return ServiceResult.validation_error(
                message="User already exists",
                error_details={"auth0_id": auth0_id}
            )
        except Exception as e:
            return self._handle_exception(e, "ensure user exists")
    
    async def get_user_by_auth0_id(self, auth0_id: str) -> ServiceResult[User]:
        """
        通过Auth0 ID获取用户
        
        Args:
            auth0_id: Auth0用户ID
            
        Returns:
            ServiceResult[User]: 用户信息结果
        """
        try:
            self._log_operation("get_user_by_auth0_id", f"auth0_id={auth0_id}")
            
            if not auth0_id:
                return ServiceResult.validation_error("Auth0 ID is required")
            
            # 首先尝试通过user_id查找（通常user_id就是auth0_id）
            user = await self.user_repo.get_by_user_id(auth0_id)
            
            # 如果没找到，尝试通过auth0_id字段查找
            if not user:
                user = await self.user_repo.get_by_auth0_id(auth0_id)
            
            if user:
                return ServiceResult.success(
                    data=user,
                    message="User found successfully"
                )
            else:
                return ServiceResult.not_found("User not found")
                
        except Exception as e:
            return self._handle_exception(e, "get user by auth0_id")
    
    async def get_user_by_id(self, user_id: str) -> ServiceResult[User]:
        """
        通过用户ID获取用户
        
        Args:
            user_id: 用户业务ID
            
        Returns:
            ServiceResult[User]: 用户信息结果
        """
        try:
            self._log_operation("get_user_by_id", f"user_id={user_id}")
            
            if not user_id:
                return ServiceResult.validation_error("User ID is required")
            
            user = await self.user_repo.get_by_user_id(user_id)
            
            if user:
                return ServiceResult.success(
                    data=user,
                    message="User found successfully"
                )
            else:
                return ServiceResult.not_found("User not found")
                
        except Exception as e:
            return self._handle_exception(e, "get user by id")
    
    async def get_user_by_email(self, email: str) -> ServiceResult[User]:
        """
        通过邮箱获取用户
        
        Args:
            email: 用户邮箱
            
        Returns:
            ServiceResult[User]: 用户信息结果
        """
        try:
            self._log_operation("get_user_by_email", f"email={email}")
            
            if not email or not self._validate_email(email):
                return ServiceResult.validation_error("Valid email is required")
            
            user = await self.user_repo.get_by_email(email)
            
            if user:
                return ServiceResult.success(
                    data=user,
                    message="User found successfully"
                )
            else:
                return ServiceResult.not_found("User not found")
                
        except Exception as e:
            return self._handle_exception(e, "get user by email")
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> ServiceResult[User]:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            update_data: 更新数据
            
        Returns:
            ServiceResult[User]: 更新后的用户信息
        """
        try:
            self._log_operation("update_user", f"user_id={user_id}")
            
            if not user_id:
                return ServiceResult.validation_error("User ID is required")
            
            # 验证邮箱格式（如果包含邮箱更新）
            if 'email' in update_data and not self._validate_email(update_data['email']):
                return ServiceResult.validation_error("Invalid email format")
            
            # 检查用户是否存在
            existing_user = await self.user_repo.get_by_user_id(user_id)
            if not existing_user:
                return ServiceResult.not_found("User not found")
            
            # 执行更新
            success = await self.user_repo.update(user_id, update_data)
            
            if success:
                # 获取更新后的用户信息
                updated_user = await self.user_repo.get_by_user_id(user_id)
                return ServiceResult.success(
                    data=updated_user,
                    message="User updated successfully"
                )
            else:
                return ServiceResult.error("Failed to update user")
                
        except Exception as e:
            return self._handle_exception(e, "update user")
    
    async def consume_credits(self, user_id: str, amount: int, reason: str = "api_call") -> ServiceResult[Dict[str, Any]]:
        """
        消费用户积分
        
        Args:
            user_id: 用户ID
            amount: 消费数量
            reason: 消费原因
            
        Returns:
            ServiceResult[Dict]: 消费结果
        """
        try:
            self._log_operation("consume_credits", f"user_id={user_id}, amount={amount}, reason={reason}")
            
            if not user_id:
                return ServiceResult.validation_error("User ID is required")
            
            if amount <= 0:
                return ServiceResult.validation_error("Amount must be positive")
            
            # 获取用户信息
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 检查积分是否足够
            if user.credits_remaining < amount:
                return ServiceResult.validation_error(
                    message="Insufficient credits",
                    error_details={
                        "requested": amount,
                        "available": user.credits_remaining
                    }
                )
            
            # 更新积分
            new_credits = user.credits_remaining - amount
            success = await self.user_repo.update_credits(user_id, new_credits)
            
            if success:
                result_data = {
                    "consumed_amount": amount,
                    "remaining_credits": new_credits,
                    "reason": reason
                }
                
                return ServiceResult.success(
                    data=result_data,
                    message=f"Successfully consumed {amount} credits"
                )
            else:
                return ServiceResult.error("Failed to update credits")
                
        except Exception as e:
            return self._handle_exception(e, "consume credits")
    
    async def add_credits(self, user_id: str, amount: int, reason: str = "credit_purchase") -> ServiceResult[Dict[str, Any]]:
        """
        为用户添加积分
        
        Args:
            user_id: 用户ID
            amount: 添加数量
            reason: 添加原因
            
        Returns:
            ServiceResult[Dict]: 添加结果
        """
        try:
            self._log_operation("add_credits", f"user_id={user_id}, amount={amount}, reason={reason}")
            
            if not user_id:
                return ServiceResult.validation_error("User ID is required")
            
            if amount <= 0:
                return ServiceResult.validation_error("Amount must be positive")
            
            # 获取用户信息
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 更新积分
            new_credits_remaining = user.credits_remaining + amount
            new_credits_total = user.credits_total + amount
            
            success = await self.user_repo.update_credits(
                user_id, 
                new_credits_remaining, 
                new_credits_total
            )
            
            if success:
                result_data = {
                    "added_amount": amount,
                    "remaining_credits": new_credits_remaining,
                    "total_credits": new_credits_total,
                    "reason": reason
                }
                
                return ServiceResult.success(
                    data=result_data,
                    message=f"Successfully added {amount} credits"
                )
            else:
                return ServiceResult.error("Failed to add credits")
                
        except Exception as e:
            return self._handle_exception(e, "add credits")
    
    async def activate_user(self, user_id: str) -> ServiceResult[User]:
        """
        激活用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            ServiceResult[User]: 激活后的用户信息
        """
        try:
            self._log_operation("activate_user", f"user_id={user_id}")
            
            success = await self.user_repo.activate_user(user_id)
            
            if success:
                user = await self.user_repo.get_by_user_id(user_id)
                return ServiceResult.success(
                    data=user,
                    message="User activated successfully"
                )
            else:
                return ServiceResult.error("Failed to activate user")
                
        except Exception as e:
            return self._handle_exception(e, "activate user")
    
    async def deactivate_user(self, user_id: str) -> ServiceResult[User]:
        """
        停用用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            ServiceResult[User]: 停用后的用户信息
        """
        try:
            self._log_operation("deactivate_user", f"user_id={user_id}")
            
            success = await self.user_repo.deactivate_user(user_id)
            
            if success:
                user = await self.user_repo.get_by_user_id(user_id)
                return ServiceResult.success(
                    data=user,
                    message="User deactivated successfully"
                )
            else:
                return ServiceResult.error("Failed to deactivate user")
                
        except Exception as e:
            return self._handle_exception(e, "deactivate user")
    
    async def get_user_info_response(self, auth0_id: str) -> ServiceResult[UserResponse]:
        """
        获取用户信息响应格式（用于API返回）
        
        Args:
            auth0_id: Auth0用户ID
            
        Returns:
            ServiceResult[UserResponse]: 用户响应信息
        """
        try:
            user_result = await self.get_user_by_auth0_id(auth0_id)
            
            if not user_result.is_success:
                return user_result  # 返回原始错误结果
            
            user = user_result.data
            user_response = UserResponse(
                user_id=user.user_id,
                email=user.email,
                name=user.name,
                credits=user.credits_remaining,
                credits_total=user.credits_total,
                plan=user.subscription_status,
                is_active=user.is_active
            )
            
            return ServiceResult.success(
                data=user_response,
                message="User information retrieved successfully"
            )
            
        except Exception as e:
            return self._handle_exception(e, "get user info response")
    
    async def get_user_info(self, auth0_id: str) -> ServiceResult[UserResponse]:
        """
        获取用户信息（API兼容性方法）
        
        Args:
            auth0_id: Auth0用户ID
            
        Returns:
            ServiceResult[UserResponse]: 用户响应信息
        """
        return await self.get_user_info_response(auth0_id)
    
    async def get_user_by_id_int(self, user_id: int) -> ServiceResult[User]:
        """
        通过数字ID获取用户（向后兼容）
        
        Args:
            user_id: 数据库主键ID
            
        Returns:
            ServiceResult[User]: 用户信息结果
        """
        try:
            self._log_operation("get_user_by_id_int", f"user_id={user_id}")
            
            if not user_id:
                return ServiceResult.validation_error("User ID is required")
            
            # 使用Repository的get_by_id方法（接受int类型）
            user = await self.user_repo.get_by_id(user_id)
            
            if user:
                return ServiceResult.success(
                    data=user,
                    message="User found successfully"
                )
            else:
                return ServiceResult.not_found("User not found")
                
        except Exception as e:
            return self._handle_exception(e, "get user by id int")
    
    async def update_user_legacy(self, user_id: int, user_update: 'UserUpdate') -> ServiceResult[User]:
        """
        更新用户信息（向后兼容版本）
        
        Args:
            user_id: 数字用户ID
            user_update: UserUpdate对象
            
        Returns:
            ServiceResult[User]: 更新后的用户信息
        """
        try:
            self._log_operation("update_user_legacy", f"user_id={user_id}")
            
            # 先获取用户的字符串ID
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 转换UserUpdate为Dict
            update_data = user_update.model_dump(exclude_unset=True)
            
            # 使用字符串ID更新
            return await self.update_user(user.user_id, update_data)
                
        except Exception as e:
            return self._handle_exception(e, "update user legacy")
    
    async def log_api_usage(self, user_id: int, endpoint: str, tokens_used: int = 1,
                           request_data: Optional[str] = None,
                           response_data: Optional[str] = None) -> ServiceResult[bool]:
        """
        记录API使用情况
        
        Args:
            user_id: 数字用户ID
            endpoint: API端点
            tokens_used: 使用的token数量
            request_data: 请求数据JSON字符串
            response_data: 响应数据JSON字符串
            
        Returns:
            ServiceResult[bool]: 是否记录成功
        """
        try:
            self._log_operation("log_api_usage", f"user_id={user_id}, endpoint={endpoint}")
            
            # 由于我们的Repository不直接支持，这里先做简单日志记录
            # 实际应该通过Repository记录到数据库
            self.logger.info(f"API Usage: user_id={user_id}, endpoint={endpoint}, tokens={tokens_used}")
            
            return ServiceResult.success(
                data=True,
                message="API usage logged successfully"
            )
                
        except Exception as e:
            return self._handle_exception(e, "log api usage")
    
    async def allocate_credits_by_plan(self, user_id: int, plan: SubscriptionStatus) -> ServiceResult[bool]:
        """
        根据订阅计划分配积分
        
        Args:
            user_id: 数字用户ID
            plan: 订阅计划
            
        Returns:
            ServiceResult[bool]: 是否分配成功
        """
        try:
            self._log_operation("allocate_credits_by_plan", f"user_id={user_id}, plan={plan.value}")
            
            # 获取用户
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 获取计划配置
            plan_configs = {
                SubscriptionStatus.FREE: {"credits": 1000},
                SubscriptionStatus.PRO: {"credits": 10000},
                SubscriptionStatus.ENTERPRISE: {"credits": 50000}
            }
            
            plan_config = plan_configs.get(plan)
            if not plan_config:
                return ServiceResult.validation_error(f"Invalid plan: {plan}")
            
            credits = plan_config["credits"]
            
            # 更新用户积分和订阅状态
            success = await self.user_repo.update_credits(user.user_id, credits, credits)
            if success:
                await self.user_repo.update_subscription_status(user.user_id, plan.value)
                
                return ServiceResult.success(
                    data=True,
                    message=f"Allocated {credits} credits for plan {plan.value}"
                )
            else:
                return ServiceResult.error("Failed to allocate credits")
                
        except Exception as e:
            return self._handle_exception(e, "allocate credits by plan")
    
    async def get_user_analytics(self, user_id: int) -> ServiceResult[Dict[str, Any]]:
        """
        获取用户分析数据
        
        Args:
            user_id: 数字用户ID
            
        Returns:
            ServiceResult[Dict]: 用户分析数据
        """
        try:
            self._log_operation("get_user_analytics", f"user_id={user_id}")
            
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
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
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None
                },
                "credits": {
                    "total": user.credits_total,
                    "remaining": user.credits_remaining,
                    "used": credits_used,
                    "usage_percentage": round(credits_usage_percentage, 2)
                },
                "subscription": {
                    "status": user.subscription_status.value,
                    "plan_type": user.subscription_status.value
                },
                "account_age_days": self._calculate_account_age(user.created_at)
            }
            
            return ServiceResult.success(
                data=analytics,
                message="User analytics retrieved successfully"
            )
            
        except Exception as e:
            return self._handle_exception(e, "get user analytics")
    
    async def verify_user_token(self, token: str) -> ServiceResult[Dict[str, Any]]:
        """
        验证用户token并返回用户信息
        
        Args:
            token: JWT token
            
        Returns:
            ServiceResult[Dict]: 验证结果和用户信息
        """
        try:
            self._log_operation("verify_user_token", "verifying token")
            
            # 这里需要集成Auth0Service来验证token
            # 目前先返回基本结构
            return ServiceResult.error(
                message="Token verification not implemented in ServiceV2",
                error_code="NOT_IMPLEMENTED"
            )
                
        except Exception as e:
            return self._handle_exception(e, "verify user token")
    
    def get_service_status(self) -> ServiceResult[Dict[str, Any]]:
        """
        获取服务状态
        
        Returns:
            ServiceResult[Dict]: 服务状态信息
        """
        try:
            status_data = {
                "service": "UserServiceV2",
                "status": "operational",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "2.0.0",
                "repository": "active",
                "features": [
                    "user_management",
                    "credit_management", 
                    "subscription_integration",
                    "analytics"
                ]
            }
            
            return ServiceResult.success(
                data=status_data,
                message="Service status retrieved successfully"
            )
            
        except Exception as e:
            return self._handle_exception(e, "get service status")
    
    def _calculate_account_age(self, created_at) -> int:
        """
        计算账户年龄（天数）
        
        Args:
            created_at: 创建时间
            
        Returns:
            账户年龄天数
        """
        if not created_at:
            return 0
        
        try:
            # 处理时区问题
            if isinstance(created_at, str):
                created_datetime = datetime.fromisoformat(created_at.replace('Z', ''))
            else:
                created_datetime = created_at
            
            # 确保时区一致
            if created_datetime.tzinfo is not None:
                created_datetime = created_datetime.replace(tzinfo=None)
            
            now = datetime.utcnow()
            return (now - created_datetime).days
        except Exception:
            return 0