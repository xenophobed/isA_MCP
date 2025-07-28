"""
Auth0 Authentication Service

提供 Auth0 集成服务，包括 JWT token 验证和用户信息获取
严格遵循 MCP 协议规范和异步编程模式
"""

import jwt
from jwt import PyJWKClient
from typing import Dict, Any, Optional
import httpx
import logging
from datetime import datetime, timedelta

from ..models import Auth0UserInfo


logger = logging.getLogger(__name__)


class Auth0Service:
    """Auth0 认证服务类"""
    
    def __init__(self, domain: str, audience: str, client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None):
        """
        初始化 Auth0 服务
        
        Args:
            domain: Auth0 域名
            audience: Auth0 audience
            client_id: Auth0 客户端ID (可选)
            client_secret: Auth0 客户端密钥 (可选)
        """
        self.domain = domain
        self.audience = audience
        self.client_id = client_id
        self.client_secret = client_secret
        self.jwks_client = PyJWKClient(f"https://{domain}/.well-known/jwks.json")
        self._management_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证 Auth0 JWT token
        
        Args:
            token: JWT token字符串
            
        Returns:
            解码后的token payload
            
        Raises:
            ValueError: token无效时抛出
            
        Example:
            >>> auth_service = Auth0Service("domain", "audience")
            >>> payload = await auth_service.verify_token("jwt_token")
            >>> print(payload["sub"])
            "auth0|user_id"
        """
        try:
            # 获取signing key
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # 验证token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=f"https://{self.domain}/"
            )

            logger.info(f"Token verified for user: {payload.get('sub')}")
            return payload

        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise ValueError(f"Token verification failed: {str(e)}")

    async def get_management_token(self) -> str:
        """
        获取 Auth0 Management API token
        
        Returns:
            Management API access token
            
        Raises:
            ValueError: 获取token失败时抛出
        """
        # 检查是否有有效的缓存token
        if (self._management_token and self._token_expires_at and 
            datetime.utcnow() < self._token_expires_at - timedelta(minutes=5)):
            return self._management_token

        if not self.client_id or not self.client_secret:
            raise ValueError("Client ID and secret required for management token")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{self.domain}/oauth/token",
                    json={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "audience": f"https://{self.domain}/api/v2/",
                        "grant_type": "client_credentials"
                    },
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    logger.error(f"Failed to get management token: {response.text}")
                    raise ValueError("Failed to get management token")

                data = response.json()
                self._management_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                logger.info("Management token obtained successfully")
                return str(self._management_token)

        except httpx.RequestError as e:
            logger.error(f"Request error getting management token: {str(e)}")
            raise ValueError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting management token: {str(e)}")
            raise ValueError(f"Unexpected error: {str(e)}")

    async def get_user_info(self, user_id: str, access_token: Optional[str] = None) -> Auth0UserInfo:
        """
        从 Auth0 获取用户信息
        
        Args:
            user_id: Auth0 用户ID
            access_token: 访问token (可选，如果不提供则使用管理token)
            
        Returns:
            用户信息对象
            
        Raises:
            ValueError: 获取用户信息失败时抛出
            
        Example:
            >>> user_info = await auth_service.get_user_info("auth0|user_id")
            >>> print(user_info.email)
            "user@example.com"
        """
        try:
            # 如果没有提供access_token，使用管理token
            if not access_token:
                access_token = await self.get_management_token()

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{self.domain}/api/v2/users/{user_id}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                if response.status_code == 404:
                    raise ValueError(f"User {user_id} not found")
                elif response.status_code != 200:
                    logger.error(f"Failed to fetch user info: {response.text}")
                    raise ValueError("Failed to fetch user info from Auth0")

                user_data = response.json()
                
                # 转换为标准化的用户信息模型
                user_info = Auth0UserInfo(
                    sub=user_data["user_id"],
                    email=user_data.get("email", ""),
                    name=user_data.get("name", ""),
                    picture=user_data.get("picture"),
                    email_verified=user_data.get("email_verified", False)
                )

                logger.info(f"User info retrieved for: {user_id}")
                return user_info

        except httpx.RequestError as e:
            logger.error(f"Request error getting user info: {str(e)}")
            raise ValueError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            raise ValueError(f"Error getting user info: {str(e)}")

    async def update_user_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """
        更新用户元数据
        
        Args:
            user_id: Auth0 用户ID
            metadata: 要更新的元数据
            
        Returns:
            是否更新成功
            
        Example:
            >>> success = await auth_service.update_user_metadata(
            ...     "auth0|user_id", 
            ...     {"subscription": "pro"}
            ... )
        """
        try:
            management_token = await self.get_management_token()

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"https://{self.domain}/api/v2/users/{user_id}",
                    headers={
                        "Authorization": f"Bearer {management_token}",
                        "Content-Type": "application/json"
                    },
                    json={"user_metadata": metadata}
                )

                if response.status_code == 200:
                    logger.info(f"User metadata updated for: {user_id}")
                    return True
                else:
                    logger.error(f"Failed to update user metadata: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error updating user metadata: {str(e)}")
            return False

    async def create_user(self, email: str, password: str, name: str, 
                         metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        在 Auth0 中创建新用户
        
        Args:
            email: 用户邮箱
            password: 用户密码
            name: 用户姓名
            metadata: 用户元数据 (可选)
            
        Returns:
            创建成功返回用户ID，失败返回None
        """
        try:
            management_token = await self.get_management_token()

            user_data = {
                "email": email,
                "password": password,
                "name": name,
                "connection": "Username-Password-Authentication",
                "email_verified": False
            }

            if metadata:
                user_data["user_metadata"] = metadata

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{self.domain}/api/v2/users",
                    headers={
                        "Authorization": f"Bearer {management_token}",
                        "Content-Type": "application/json"
                    },
                    json=user_data
                )

                if response.status_code == 201:
                    user_info = response.json()
                    logger.info(f"User created: {user_info['user_id']}")
                    return user_info["user_id"]
                else:
                    logger.error(f"Failed to create user: {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None

    async def delete_user(self, user_id: str) -> bool:
        """
        删除 Auth0 用户
        
        Args:
            user_id: Auth0 用户ID
            
        Returns:
            是否删除成功
        """
        try:
            management_token = await self.get_management_token()

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"https://{self.domain}/api/v2/users/{user_id}",
                    headers={"Authorization": f"Bearer {management_token}"}
                )

                if response.status_code == 204:
                    logger.info(f"User deleted: {user_id}")
                    return True
                else:
                    logger.error(f"Failed to delete user: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False

    def extract_user_id_from_token(self, token: str) -> Optional[str]:
        """
        从 JWT token 中提取用户ID (不验证token)
        
        Args:
            token: JWT token字符串
            
        Returns:
            用户ID，如果提取失败返回None
        """
        try:
            # 解码token但不验证签名 (仅用于快速提取信息)
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("sub")
        except Exception as e:
            logger.warning(f"Failed to extract user ID from token: {str(e)}")
            return None 