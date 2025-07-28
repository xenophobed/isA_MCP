"""
Unified Authentication Service

统一认证服务，支持多种认证提供者 (Auth0 和 Supabase)
提供统一的接口用于token验证和用户信息获取
"""

from typing import Dict, Any, Optional
import logging
from enum import Enum

from .auth_service import Auth0Service
from .supabase_auth_service import SupabaseAuthService
from ..models import Auth0UserInfo

logger = logging.getLogger(__name__)


class AuthProvider(Enum):
    """认证提供者枚举"""
    AUTH0 = "auth0"
    SUPABASE = "supabase"


class UnifiedAuthService:
    """统一认证服务类"""
    
    def __init__(self, 
                 auth0_service: Optional[Auth0Service] = None,
                 supabase_service: Optional[SupabaseAuthService] = None,
                 default_provider: str = "both"):
        """
        初始化统一认证服务
        
        Args:
            auth0_service: Auth0认证服务实例
            supabase_service: Supabase认证服务实例
            default_provider: 默认认证提供者 ("auth0", "supabase", "both")
        """
        self.auth0_service = auth0_service
        self.supabase_service = supabase_service
        self.default_provider = default_provider
        
        if not auth0_service and not supabase_service:
            raise ValueError("At least one authentication service must be provided")
    
    async def verify_token(self, token: str, provider: Optional[str] = None) -> tuple[Dict[str, Any], AuthProvider]:
        """
        验证JWT token，自动检测或指定认证提供者
        
        Args:
            token: JWT token字符串
            provider: 指定认证提供者 ("auth0", "supabase", None=自动检测)
            
        Returns:
            tuple: (解码后的payload, 使用的认证提供者)
            
        Raises:
            ValueError: token无效时抛出
        """
        if provider:
            # 使用指定的提供者
            if provider == "auth0" and self.auth0_service:
                payload = await self.auth0_service.verify_token(token)
                return payload, AuthProvider.AUTH0
            elif provider == "supabase" and self.supabase_service:
                payload = await self.supabase_service.verify_token(token)
                return payload, AuthProvider.SUPABASE
            else:
                raise ValueError(f"Provider {provider} not available")
        
        # 自动检测认证提供者
        errors = []
        
        # 根据default_provider决定尝试顺序
        if self.default_provider == "auth0" or self.default_provider == "both":
            if self.auth0_service:
                try:
                    payload = await self.auth0_service.verify_token(token)
                    logger.debug("Token verified using Auth0")
                    return payload, AuthProvider.AUTH0
                except Exception as e:
                    errors.append(f"Auth0: {str(e)}")
        
        if self.default_provider == "supabase" or self.default_provider == "both":
            if self.supabase_service:
                try:
                    payload = await self.supabase_service.verify_token(token)
                    logger.debug("Token verified using Supabase")
                    return payload, AuthProvider.SUPABASE
                except Exception as e:
                    errors.append(f"Supabase: {str(e)}")
        
        # 如果所有提供者都失败
        error_msg = "; ".join(errors)
        logger.error(f"Token verification failed for all providers: {error_msg}")
        raise ValueError(f"Token verification failed: {error_msg}")
    
    async def get_user_info(self, user_id: str, provider: AuthProvider, 
                           access_token: Optional[str] = None) -> Auth0UserInfo:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            provider: 认证提供者
            access_token: 访问token (可选)
            
        Returns:
            用户信息对象
            
        Raises:
            ValueError: 获取用户信息失败时抛出
        """
        try:
            if provider == AuthProvider.AUTH0 and self.auth0_service:
                return await self.auth0_service.get_user_info(user_id, access_token)
            elif provider == AuthProvider.SUPABASE and self.supabase_service:
                return await self.supabase_service.get_user_info(user_id, access_token)
            else:
                raise ValueError(f"Provider {provider.value} not available")
                
        except Exception as e:
            logger.error(f"Error getting user info from {provider.value}: {str(e)}")
            raise
    
    async def create_user(self, email: str, password: str, name: str,
                         provider: AuthProvider,
                         metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        创建新用户
        
        Args:
            email: 用户邮箱
            password: 用户密码
            name: 用户姓名
            provider: 认证提供者
            metadata: 用户元数据 (可选)
            
        Returns:
            创建成功返回用户ID，失败返回None
        """
        try:
            if provider == AuthProvider.AUTH0 and self.auth0_service:
                return await self.auth0_service.create_user(email, password, name, metadata)
            elif provider == AuthProvider.SUPABASE and self.supabase_service:
                return await self.supabase_service.create_user(email, password, name, metadata)
            else:
                raise ValueError(f"Provider {provider.value} not available")
                
        except Exception as e:
            logger.error(f"Error creating user with {provider.value}: {str(e)}")
            return None
    
    async def delete_user(self, user_id: str, provider: AuthProvider) -> bool:
        """
        删除用户
        
        Args:
            user_id: 用户ID
            provider: 认证提供者
            
        Returns:
            是否删除成功
        """
        try:
            if provider == AuthProvider.AUTH0 and self.auth0_service:
                return await self.auth0_service.delete_user(user_id)
            elif provider == AuthProvider.SUPABASE and self.supabase_service:
                return await self.supabase_service.delete_user(user_id)
            else:
                raise ValueError(f"Provider {provider.value} not available")
                
        except Exception as e:
            logger.error(f"Error deleting user with {provider.value}: {str(e)}")
            return False
    
    def extract_user_id_from_token(self, token: str) -> Optional[str]:
        """
        从JWT token中提取用户ID (不验证token)
        
        Args:
            token: JWT token字符串
            
        Returns:
            用户ID，如果提取失败返回None
        """
        # 尝试所有可用的服务
        if self.auth0_service:
            user_id = self.auth0_service.extract_user_id_from_token(token)
            if user_id:
                return user_id
        
        if self.supabase_service:
            user_id = self.supabase_service.extract_user_id_from_token(token)
            if user_id:
                return user_id
        
        return None
    
    async def generate_dev_token(self, user_id: str, email: str) -> Optional[str]:
        """
        生成开发测试用的JWT token (仅Supabase支持)
        
        Args:
            user_id: 用户ID
            email: 用户邮箱
            
        Returns:
            JWT token字符串或None
        """
        if self.supabase_service:
            try:
                return await self.supabase_service.generate_dev_token(user_id, email)
            except Exception as e:
                logger.error(f"Error generating dev token: {str(e)}")
                return None
        
        logger.warning("Dev token generation only available with Supabase service")
        return None
    
    def get_available_providers(self) -> list[str]:
        """
        获取可用的认证提供者列表
        
        Returns:
            可用认证提供者列表
        """
        providers = []
        if self.auth0_service:
            providers.append("auth0")
        if self.supabase_service:
            providers.append("supabase")
        return providers
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        获取服务信息
        
        Returns:
            服务信息字典
        """
        return {
            "available_providers": self.get_available_providers(),
            "default_provider": self.default_provider,
            "auth0_enabled": self.auth0_service is not None,
            "supabase_enabled": self.supabase_service is not None
        }