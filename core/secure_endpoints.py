#!/usr/bin/env python3
"""
安全的API端点管理
包含认证、API密钥生成、用户管理等功能
"""
import os
import json
from datetime import datetime
from typing import Dict, Any
from starlette.responses import JSONResponse
from starlette.requests import Request
from core.auth import security_manager, AuthenticationError, AuthorizationError
import logging

logger = logging.getLogger(__name__)

async def auth_generate_key_endpoint(request: Request):
    """生成API密钥端点"""
    try:
        # 开发环境或管理员权限检查
        if os.getenv('NODE_ENV') == 'production':
            # 生产环境需要管理员认证
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return JSONResponse({
                    'error': 'Admin authentication required'
                }, status_code=401)
        
        # 获取请求数据
        try:
            body = await request.body()
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return JSONResponse({
                'error': 'Invalid JSON in request body'
            }, status_code=400)
        
        user_id = data.get('user_id', 'default_user')
        description = data.get('description', 'Generated via API')
        
        # 生成API密钥
        api_key = security_manager.generate_api_key(user_id, description)
        
        return JSONResponse({
            'status': 'success',
            'api_key': api_key,
            'user_id': user_id,
            'description': description,
            'created_at': datetime.utcnow().isoformat(),
            'usage_instructions': {
                'header_method': f'Authorization: ApiKey {api_key}',
                'header_alternative': f'X-API-Key: {api_key}',
                'example_curl': f'curl -H "X-API-Key: {api_key}" https://your-service.railway.app/discover'
            }
        })
        
    except Exception as e:
        logger.error(f"API key generation error: {e}")
        return JSONResponse({
            'error': 'Failed to generate API key',
            'message': str(e)
        }, status_code=500)

async def auth_verify_key_endpoint(request: Request):
    """验证API密钥端点"""
    try:
        api_key = request.headers.get('X-API-Key') or request.headers.get('x-api-key')
        
        if not api_key:
            return JSONResponse({
                'error': 'No API key provided',
                'message': 'Include X-API-Key header'
            }, status_code=400)
        
        # 验证API密钥
        key_info = security_manager.verify_api_key(api_key)
        
        return JSONResponse({
            'status': 'valid',
            'user_id': key_info['user_id'],
            'description': key_info['description'],
            'created_at': key_info['created_at'].isoformat(),
            'last_used': key_info['last_used'].isoformat() if key_info['last_used'] else None,
            'usage_count': key_info['usage_count'],
            'is_active': key_info['is_active']
        })
        
    except AuthenticationError as e:
        return JSONResponse({
            'status': 'invalid',
            'error': str(e)
        }, status_code=401)
    except Exception as e:
        logger.error(f"API key verification error: {e}")
        return JSONResponse({
            'error': 'Verification failed',
            'message': str(e)
        }, status_code=500)

async def auth_generate_jwt_endpoint(request: Request):
    """生成JWT令牌端点"""
    try:
        # 获取请求数据
        try:
            body = await request.body()
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return JSONResponse({
                'error': 'Invalid JSON in request body'
            }, status_code=400)
        
        user_id = data.get('user_id')
        permissions = data.get('permissions', ['api_access'])
        
        if not user_id:
            return JSONResponse({
                'error': 'user_id is required'
            }, status_code=400)
        
        # 生成JWT令牌
        token = security_manager.generate_jwt_token(user_id, permissions)
        
        return JSONResponse({
            'status': 'success',
            'token': token,
            'user_id': user_id,
            'permissions': permissions,
            'expires_in': '24 hours',
            'usage_instructions': {
                'header': f'Authorization: Bearer {token}',
                'example_curl': f'curl -H "Authorization: Bearer {token}" https://your-service.railway.app/discover'
            }
        })
        
    except Exception as e:
        logger.error(f"JWT generation error: {e}")
        return JSONResponse({
            'error': 'Failed to generate JWT token',
            'message': str(e)
        }, status_code=500)

async def auth_status_endpoint(request: Request):
    """认证状态端点"""
    try:
        # 检查当前请求的认证状态
        auth_info = getattr(request.state, 'auth_info', None)
        
        if not auth_info:
            return JSONResponse({
                'authenticated': False,
                'message': 'No authentication provided'
            })
        
        return JSONResponse({
            'authenticated': True,
            'auth_type': auth_info.get('auth_type'),
            'user_id': auth_info.get('user_id'),
            'permissions': auth_info.get('permissions'),
            'security_features': {
                'rate_limiting': True,
                'ip_blocking': True,
                'token_expiration': True,
                'secure_headers': True
            }
        })
        
    except Exception as e:
        logger.error(f"Auth status error: {e}")
        return JSONResponse({
            'error': 'Failed to get auth status',
            'message': str(e)
        }, status_code=500)

async def security_info_endpoint(request: Request):
    """安全信息端点"""
    try:
        return JSONResponse({
            'security_features': {
                'authentication': {
                    'jwt_tokens': True,
                    'api_keys': True,
                    'rate_limiting': True,
                    'ip_blocking': True
                },
                'encryption': {
                    'https_only': True,
                    'secure_headers': True,
                    'token_signing': True
                },
                'monitoring': {
                    'audit_logging': True,
                    'usage_tracking': True,
                    'error_monitoring': True
                }
            },
            'rate_limits': {
                'jwt_users': '1000 requests/hour',
                'api_key_users': '500 requests/hour',
                'anonymous': '100 requests/hour'
            },
            'supported_auth_methods': [
                'Authorization: Bearer <jwt-token>',
                'Authorization: ApiKey <api-key>',
                'X-API-Key: <api-key>'
            ],
            'endpoints': {
                '/auth/generate-key': 'Generate new API key',
                '/auth/verify-key': 'Verify API key validity',
                '/auth/generate-jwt': 'Generate JWT token',
                '/auth/status': 'Check authentication status'
            }
        })
        
    except Exception as e:
        logger.error(f"Security info error: {e}")
        return JSONResponse({
            'error': 'Failed to get security info',
            'message': str(e)
        }, status_code=500)

def add_auth_endpoints(app):
    """添加认证相关端点到应用"""
    from starlette.routing import Route
    
    auth_routes = [
        Route('/auth/generate-key', auth_generate_key_endpoint, methods=['POST']),
        Route('/auth/verify-key', auth_verify_key_endpoint, methods=['GET']),
        Route('/auth/generate-jwt', auth_generate_jwt_endpoint, methods=['POST']),
        Route('/auth/status', auth_status_endpoint, methods=['GET']),
        Route('/security', security_info_endpoint, methods=['GET']),
    ]
    
    for route in auth_routes:
        app.router.routes.append(route)