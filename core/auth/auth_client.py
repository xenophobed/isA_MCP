#!/usr/bin/env python3
"""
认证服务客户端
与User Service (8000)和Auth Service (8202)通信
"""

import aiohttp
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """认证服务客户端"""

    def __init__(self, base_url: str = None):
        if base_url is None:
            from core.config import get_settings

            settings = get_settings()
            base_url = settings.auth_service_url or "http://localhost:8000"
        self.base_url = base_url.rstrip("/")
        self.session = None

    async def _ensure_session(self):
        """确保会话存在"""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证JWT token或API key

        Args:
            token: JWT token或API key (isa_ prefix)

        Returns:
            验证结果包含用户信息
        """
        await self._ensure_session()

        # Detect API keys (isa_ prefix) and route to verify-api-key endpoint
        if token.startswith("isa_"):
            return await self._verify_api_key(token)

        try:
            # 尝试调用User Service的统一认证端点
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/verify-token",
                json={"token": token},
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "user": data.get("user", {}),
                        "token_type": data.get("token_type", "jwt"),
                    }
                else:
                    error_data = await response.text()
                    logger.warning(f"Token verification failed: {error_data}")
                    return {"success": False, "error": f"Verification failed: {response.status}"}

        except aiohttp.ClientError as e:
            logger.error(f"Auth service connection error: {str(e)}")
            return {"success": False, "error": f"Service unavailable: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error in token verification: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """Verify an isa_ API key via auth service."""
        await self._ensure_session()
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/verify-api-key",
                json={"api_key": api_key},
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("valid"):
                        return {
                            "success": True,
                            "user": {
                                "user_id": data.get("organization_id"),
                                "organization_id": data.get("organization_id"),
                                "key_id": data.get("key_id"),
                                "permissions": data.get("permissions", []),
                            },
                            "token_type": "api_key",
                        }
                    return {"success": False, "error": data.get("error", "Invalid API key")}
                else:
                    return {
                        "success": False,
                        "error": f"API key verification failed: {response.status}",
                    }
        except aiohttp.ClientError as e:
            logger.error(f"Auth service connection error during API key verification: {str(e)}")
            return {"success": False, "error": f"Service unavailable: {str(e)}"}

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            用户信息
        """
        await self._ensure_session()

        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/users/{user_id}", headers={"Accept": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}

        except Exception as e:
            logger.error(f"Error fetching user info: {str(e)}")
            return {}

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
