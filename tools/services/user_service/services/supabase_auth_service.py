"""
Supabase Authentication Service

提供Supabase JWT认证服务，用于开发测试环境
支持Supabase生成的JWT token验证和用户信息获取
"""

import jwt
import json
from typing import Dict, Any, Optional
import httpx
import logging
from datetime import datetime

from ..models import Auth0UserInfo

logger = logging.getLogger(__name__)


class SupabaseAuthService:
    """Supabase认证服务类"""
    
    def __init__(self, supabase_url: str, jwt_secret: str, anon_key: str, service_role_key: str):
        """
        初始化Supabase认证服务
        
        Args:
            supabase_url: Supabase项目URL
            jwt_secret: JWT签名密钥
            anon_key: 匿名访问密钥
            service_role_key: 服务角色密钥
        """
        self.supabase_url = supabase_url.rstrip('/')
        self.jwt_secret = jwt_secret
        self.anon_key = anon_key
        self.service_role_key = service_role_key
        
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证Supabase JWT token
        
        Args:
            token: JWT token字符串
            
        Returns:
            解码后的token payload
            
        Raises:
            ValueError: token无效时抛出
        """
        try:
            # 验证JWT token使用HS256算法（Supabase默认）
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False, "verify_iat": False}  # Supabase不总是使用audience，禁用iat验证避免时钟偏差
            )
            
            # 检查token是否过期
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                raise ValueError("Token has expired")
            
            # 检查issuer (可选)
            iss = payload.get('iss')
            if iss and not iss.startswith('supabase'):
                logger.warning(f"Unexpected issuer: {iss}")
            
            logger.info(f"Supabase token verified for user: {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.error("Supabase token has expired")
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid Supabase token: {str(e)}")
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Supabase token verification failed: {str(e)}")
            raise ValueError(f"Token verification failed: {str(e)}")
    
    async def get_user_info(self, user_id: str, access_token: Optional[str] = None) -> Auth0UserInfo:
        """
        从Supabase获取用户信息
        
        Args:
            user_id: Supabase用户ID
            access_token: 访问token (可选)
            
        Returns:
            用户信息对象
            
        Raises:
            ValueError: 获取用户信息失败时抛出
        """
        try:
            # 使用service role key进行管理API调用
            headers = {
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/auth/v1/admin/users/{user_id}",
                    headers=headers
                )
                
                if response.status_code == 404:
                    raise ValueError(f"User {user_id} not found")
                elif response.status_code != 200:
                    logger.error(f"Failed to fetch user info: {response.text}")
                    raise ValueError("Failed to fetch user info from Supabase")
                
                user_data = response.json()
                
                # 转换为标准化的用户信息模型
                user_info = Auth0UserInfo(
                    sub=user_data["id"],
                    email=user_data.get("email", ""),
                    name=user_data.get("user_metadata", {}).get("name", "") or user_data.get("email", ""),
                    picture=user_data.get("user_metadata", {}).get("picture"),
                    email_verified=user_data.get("email_confirmed_at") is not None
                )
                
                logger.info(f"Supabase user info retrieved for: {user_id}")
                return user_info
                
        except httpx.RequestError as e:
            logger.error(f"Request error getting Supabase user info: {str(e)}")
            raise ValueError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting Supabase user info: {str(e)}")
            raise ValueError(f"Error getting user info: {str(e)}")
    
    async def create_user(self, email: str, password: str, name: str, 
                         metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        在Supabase中创建新用户
        
        Args:
            email: 用户邮箱
            password: 用户密码
            name: 用户姓名
            metadata: 用户元数据 (可选)
            
        Returns:
            创建成功返回用户ID，失败返回None
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key,
                "Content-Type": "application/json"
            }
            
            user_data = {
                "email": email,
                "password": password,
                "email_confirm": True,  # 自动确认邮箱
                "user_metadata": {
                    "name": name,
                    **(metadata or {})
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.supabase_url}/auth/v1/admin/users",
                    headers=headers,
                    json=user_data
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    logger.info(f"Supabase user created: {user_info['id']}")
                    return user_info["id"]
                else:
                    logger.error(f"Failed to create Supabase user: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating Supabase user: {str(e)}")
            return None
    
    async def delete_user(self, user_id: str) -> bool:
        """
        删除Supabase用户
        
        Args:
            user_id: Supabase用户ID
            
        Returns:
            是否删除成功
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.supabase_url}/auth/v1/admin/users/{user_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.info(f"Supabase user deleted: {user_id}")
                    return True
                else:
                    logger.error(f"Failed to delete Supabase user: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting Supabase user: {str(e)}")
            return False
    
    def extract_user_id_from_token(self, token: str) -> Optional[str]:
        """
        从JWT token中提取用户ID (不验证token)
        
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
            logger.warning(f"Failed to extract user ID from Supabase token: {str(e)}")
            return None
    
    async def generate_dev_token(self, user_id: str, email: str, role: str = "authenticated") -> str:
        """
        生成开发测试用的JWT token
        
        Args:
            user_id: 用户ID
            email: 用户邮箱
            role: 用户角色 (authenticated/anon)
            
        Returns:
            JWT token字符串
        """
        try:
            payload = {
                "aud": "authenticated",
                "exp": int((datetime.utcnow().timestamp() + 3600)),  # 1小时过期
                "sub": user_id,
                "email": email,
                "role": role,
                "iss": "supabase",
                "iat": int(datetime.utcnow().timestamp()) - 60  # 减去60秒避免时钟偏差
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            logger.info(f"Generated dev token for user: {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"Error generating dev token: {str(e)}")
            raise ValueError(f"Failed to generate token: {str(e)}")