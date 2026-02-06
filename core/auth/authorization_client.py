#!/usr/bin/env python3
"""
授权服务客户端
与Authorization Service (8203)通信
"""

import aiohttp
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuthorizationServiceClient:
    """授权服务客户端"""
    
    def __init__(self, base_url: str = None):
        if base_url is None:
            from core.config import get_settings
            settings = get_settings()
            base_url = settings.authorization_service_url or "http://localhost:8203"
        self.base_url = base_url.rstrip("/")
        self.session = None
    
    async def _ensure_session(self):
        """确保会话存在"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def check_access(
        self,
        user_id: str,
        resource_type: str,
        resource_name: str,
        required_access_level: str = "read_only",
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        检查用户对资源的访问权限
        
        Args:
            user_id: 用户ID
            resource_type: 资源类型
            resource_name: 资源名称
            required_access_level: 所需访问级别
            organization_id: 组织ID（可选）
            
        Returns:
            权限检查结果
        """
        await self._ensure_session()
        
        try:
            payload = {
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "required_access_level": required_access_level
            }
            
            if organization_id:
                payload["organization_id"] = organization_id
            
            async with self.session.post(
                f"{self.base_url}/api/v1/authorization/check-access",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    return {
                        "has_access": data.get("has_access", False),
                        "user_access_level": data.get("user_access_level", "none"),
                        "permission_source": data.get("permission_source"),
                        "subscription_tier": data.get("subscription_tier"),
                        "reason": data.get("reason", ""),
                        "expires_at": data.get("expires_at")
                    }
                else:
                    return {
                        "has_access": False,
                        "reason": data.get("error", "Authorization check failed"),
                        "error": data.get("error")
                    }
                    
        except aiohttp.ClientError as e:
            logger.error(f"Authorization service connection error: {str(e)}")
            return {
                "has_access": False,
                "reason": f"Service unavailable: {str(e)}",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in access check: {str(e)}")
            return {
                "has_access": False,
                "reason": str(e),
                "error": str(e)
            }
    
    async def check_bulk_access(
        self,
        user_id: str,
        resources: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        批量检查资源访问权限
        
        Args:
            user_id: 用户ID
            resources: 资源列表
            
        Returns:
            批量权限检查结果
        """
        await self._ensure_session()
        
        try:
            payload = {
                "user_id": user_id,
                "resources": resources
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/check-access/bulk",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"results": [], "error": f"Bulk check failed: {response.status}"}
                    
        except Exception as e:
            logger.error(f"Error in bulk access check: {str(e)}")
            return {"results": [], "error": str(e)}
    
    async def get_user_permissions(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        获取用户的所有权限
        
        Args:
            user_id: 用户ID
            organization_id: 组织ID（可选）
            
        Returns:
            Dict[资源名称, 访问级别]
        """
        await self._ensure_session()
        
        try:
            params = {"user_id": user_id}
            if organization_id:
                params["organization_id"] = organization_id
            
            async with self.session.get(
                f"{self.base_url}/api/v1/auth/user-permissions",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # 转换权限格式
                    permissions = {}
                    for perm in data.get("permissions", []):
                        resource_key = f"{perm['resource_type']}/{perm['resource_name']}"
                        permissions[resource_key] = perm.get("access_level", "none")
                    return permissions
                else:
                    return {}
                    
        except Exception as e:
            logger.error(f"Error fetching user permissions: {str(e)}")
            return {}
    
    async def grant_permission(
        self,
        user_id: str,
        resource_type: str,
        resource_name: str,
        access_level: str,
        granted_by: str,
        expires_in_days: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        授予用户权限
        
        Args:
            user_id: 用户ID
            resource_type: 资源类型
            resource_name: 资源名称
            access_level: 访问级别
            granted_by: 授予者ID
            expires_in_days: 过期天数
            reason: 授予原因
            
        Returns:
            授予结果
        """
        await self._ensure_session()
        
        try:
            payload = {
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "access_level": access_level,
                "permission_source": "admin_grant",
                "granted_by": granted_by
            }
            
            if expires_in_days:
                payload["expires_in_days"] = expires_in_days
            if reason:
                payload["reason"] = reason
            
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/grant",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    return {
                        "success": True,
                        "permission_id": data.get("permission_id"),
                        "message": data.get("message", "Permission granted")
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error", "Grant failed")
                    }
                    
        except Exception as e:
            logger.error(f"Error granting permission: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def revoke_permission(
        self,
        user_id: str,
        resource_type: str,
        resource_name: str,
        revoked_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        撤销用户权限
        
        Args:
            user_id: 用户ID
            resource_type: 资源类型
            resource_name: 资源名称
            revoked_by: 撤销者ID
            reason: 撤销原因
            
        Returns:
            撤销结果
        """
        await self._ensure_session()
        
        try:
            payload = {
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "revoked_by": revoked_by
            }
            
            if reason:
                payload["reason"] = reason
            
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/revoke",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    return {
                        "success": True,
                        "message": data.get("message", "Permission revoked")
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error", "Revoke failed")
                    }
                    
        except Exception as e:
            logger.error(f"Error revoking permission: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()