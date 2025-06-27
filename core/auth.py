#!/usr/bin/env python3
"""
生产级认证和授权系统
JWT Token + API Key + Rate Limiting
"""
import jwt
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """认证错误"""
    pass

class AuthorizationError(Exception):
    """授权错误"""
    pass

class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', self._generate_secret())
        self.api_keys = {}  # 存储API密钥
        self.rate_limits = {}  # 存储速率限制
        self.blocked_ips = set()  # 被封禁的IP
        
    def _generate_secret(self) -> str:
        """生成安全密钥"""
        return secrets.token_urlsafe(32)
    
    def generate_jwt_token(self, user_id: str, permissions: list = None) -> str:
        """生成JWT令牌"""
        try:
            payload = {
                'user_id': user_id,
                'permissions': permissions or [],
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=24)
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            logger.info(f"JWT token generated for user: {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate JWT token: {e}")
            raise AuthenticationError("Token generation failed")
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
    
    def generate_api_key(self, user_id: str, description: str = None) -> str:
        """生成API密钥"""
        api_key = f"mcp_{secrets.token_urlsafe(32)}"
        
        self.api_keys[api_key] = {
            'user_id': user_id,
            'description': description,
            'created_at': datetime.utcnow(),
            'last_used': None,
            'usage_count': 0,
            'is_active': True
        }
        
        logger.info(f"API key generated for user: {user_id}")
        return api_key
    
    def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """验证API密钥"""
        if api_key not in self.api_keys:
            raise AuthenticationError("Invalid API key")
        
        key_info = self.api_keys[api_key]
        
        if not key_info['is_active']:
            raise AuthenticationError("API key is disabled")
        
        # 更新使用记录
        key_info['last_used'] = datetime.utcnow()
        key_info['usage_count'] += 1
        
        return key_info
    
    def check_rate_limit(self, identifier: str, limit: int = 100, window: int = 3600) -> bool:
        """检查速率限制"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window)
        
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []
        
        # 清理过期记录
        self.rate_limits[identifier] = [
            timestamp for timestamp in self.rate_limits[identifier]
            if timestamp > window_start
        ]
        
        # 检查是否超过限制
        if len(self.rate_limits[identifier]) >= limit:
            logger.warning(f"Rate limit exceeded for: {identifier}")
            return False
        
        # 记录当前请求
        self.rate_limits[identifier].append(now)
        return True
    
    async def authenticate_request(self, headers: Dict[str, str], remote_addr: str) -> Dict[str, Any]:
        """认证请求"""
        # 检查IP是否被封禁
        if remote_addr in self.blocked_ips:
            raise AuthenticationError("IP address is blocked")
        
        # 检查认证头
        auth_header = headers.get('authorization', '') or headers.get('Authorization', '')
        
        if auth_header.startswith('Bearer '):
            # JWT Token认证
            token = auth_header[7:]
            payload = self.verify_jwt_token(token)
            
            # 速率限制检查
            if not self.check_rate_limit(f"user_{payload['user_id']}", limit=1000):
                raise AuthorizationError("Rate limit exceeded")
            
            return {
                'auth_type': 'jwt',
                'user_id': payload['user_id'],
                'permissions': payload.get('permissions', [])
            }
            
        elif auth_header.startswith('ApiKey '):
            # API Key认证
            api_key = auth_header[7:]
            key_info = self.verify_api_key(api_key)
            
            # 速率限制检查
            if not self.check_rate_limit(f"apikey_{api_key}", limit=500):
                raise AuthorizationError("Rate limit exceeded")
            
            return {
                'auth_type': 'api_key',
                'user_id': key_info['user_id'],
                'permissions': ['api_access']
            }
        
        # 检查X-API-Key头
        api_key = headers.get('x-api-key') or headers.get('X-API-Key')
        if api_key:
            key_info = self.verify_api_key(api_key)
            
            if not self.check_rate_limit(f"apikey_{api_key}", limit=500):
                raise AuthorizationError("Rate limit exceeded")
            
            return {
                'auth_type': 'api_key',
                'user_id': key_info['user_id'],
                'permissions': ['api_access']
            }
        
        # 开发环境允许无认证访问
        if os.getenv('NODE_ENV') != 'production':
            return {
                'auth_type': 'development',
                'user_id': 'dev_user',
                'permissions': ['admin', 'api_access']
            }
        
        raise AuthenticationError("No valid authentication provided")

# 全局安全管理器实例
security_manager = SecurityManager()

async def require_auth(headers: Dict[str, str], remote_addr: str, permissions: list = None) -> Dict[str, Any]:
    """认证函数"""
    try:
        auth_info = await security_manager.authenticate_request(headers, remote_addr)
        
        # 权限检查
        if permissions:
            user_permissions = auth_info.get('permissions', [])
            if not any(perm in user_permissions for perm in permissions):
                raise AuthorizationError(f"Insufficient permissions. Required: {permissions}")
        
        return auth_info
        
    except (AuthenticationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise AuthenticationError("Authentication failed")

def create_auth_middleware():
    """创建认证中间件"""
    async def auth_middleware(request, call_next):
        # 跳过健康检查等公开端点
        if request.url.path in ['/health', '/']:
            response = await call_next(request)
            return response
        
        try:
            auth_info = await require_auth(
                dict(request.headers), 
                request.client.host if request.client else "unknown"
            )
            request.state.auth_info = auth_info
            response = await call_next(request)
            return response
            
        except AuthenticationError as e:
            from starlette.responses import JSONResponse
            return JSONResponse(
                {'error': str(e)}, 
                status_code=401
            )
        except AuthorizationError as e:
            from starlette.responses import JSONResponse
            return JSONResponse(
                {'error': str(e)}, 
                status_code=429
            )
    
    return auth_middleware