#!/usr/bin/env python3
"""
MCP认证授权服务
统一处理MCP系统的认证和授权需求
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """MCP资源类型"""

    MCP_TOOL = "mcp_tool"
    PROMPT = "prompt"
    RESOURCE = "resource"
    KNOWLEDGE_ITEM = "knowledge_item"
    RAG_SESSION = "rag_session"
    API_ENDPOINT = "api_endpoint"
    DATABASE = "database"
    FILE_STORAGE = "file_storage"
    COMPUTE = "compute"
    AI_MODEL = "ai_model"


class AccessLevel(Enum):
    """访问级别"""

    NONE = "none"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    OWNER = "owner"


class SubscriptionTier(Enum):
    """订阅级别"""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


@dataclass
class UserContext:
    """用户上下文信息"""

    user_id: str
    email: Optional[str] = None
    organization_id: Optional[str] = None
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    is_authenticated: bool = False
    permissions: Dict[str, AccessLevel] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = {}
        if self.metadata is None:
            self.metadata = {}


class MCPAuthService:
    """
    MCP认证授权服务
    集成多个微服务提供统一的认证授权功能
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Get settings for fallback URLs
        from core.config import get_settings

        settings = get_settings()

        # 服务端点配置 - use config first, then settings, then hardcoded fallback
        self.auth_service_url = (
            self.config.get("auth_service_url")
            or settings.auth_service_url
            or "http://localhost:8000"
        )
        self.authorization_service_url = (
            self.config.get("authorization_service_url")
            or settings.authorization_service_url
            or "http://localhost:8203"
        )

        # 懒加载客户端
        self._auth_client = None
        self._authz_client = None

        logger.debug(
            f"MCP Auth Service initialized (auth={self.auth_service_url}, authz={self.authorization_service_url})"
        )

    @property
    def auth_client(self):
        """懒加载认证客户端"""
        if self._auth_client is None:
            from .auth_client import AuthServiceClient

            self._auth_client = AuthServiceClient(self.auth_service_url)
        return self._auth_client

    @property
    def authz_client(self):
        """懒加载授权客户端"""
        if self._authz_client is None:
            from .authorization_client import AuthorizationServiceClient

            self._authz_client = AuthorizationServiceClient(self.authorization_service_url)
        return self._authz_client

    async def authenticate_token(self, token: str) -> UserContext:
        """
        验证token并返回用户上下文

        Args:
            token: JWT token或API key

        Returns:
            UserContext: 用户上下文信息
        """
        try:
            # 调用认证服务验证token
            auth_result = await self.auth_client.verify_token(token)

            if not auth_result.get("success"):
                logger.warning(f"Token verification failed: {auth_result.get('error')}")
                return UserContext(user_id="anonymous", is_authenticated=False)

            # 构建用户上下文
            user_data = auth_result.get("user", {})
            context = UserContext(
                user_id=user_data.get("user_id", "unknown"),
                email=user_data.get("email"),
                organization_id=user_data.get("organization_id"),
                subscription_tier=SubscriptionTier(user_data.get("subscription_tier", "free")),
                is_authenticated=True,
                metadata=user_data,
            )

            return context

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return UserContext(user_id="anonymous", is_authenticated=False)

    async def check_resource_access(
        self,
        user_context: UserContext,
        resource_type: ResourceType,
        resource_name: str,
        required_level: AccessLevel = AccessLevel.READ_ONLY,
    ) -> Dict[str, Any]:
        """
        检查用户对资源的访问权限

        Args:
            user_context: 用户上下文
            resource_type: 资源类型
            resource_name: 资源名称
            required_level: 所需访问级别

        Returns:
            Dict包含访问权限信息
        """
        try:
            # 如果用户未认证，直接拒绝
            if not user_context.is_authenticated:
                return {
                    "has_access": False,
                    "reason": "User not authenticated",
                    "required_subscription": None,
                }

            # 调用授权服务检查权限
            authz_result = await self.authz_client.check_access(
                user_id=user_context.user_id,
                resource_type=resource_type.value,
                resource_name=resource_name,
                required_access_level=required_level.value,
                organization_id=user_context.organization_id,
            )

            return authz_result

        except Exception as e:
            logger.error(f"Authorization check error: {str(e)}")
            return {
                "has_access": False,
                "reason": f"Authorization service error: {str(e)}",
                "error": str(e),
            }

    async def get_user_permissions(self, user_context: UserContext) -> Dict[str, AccessLevel]:
        """
        获取用户的所有权限

        Args:
            user_context: 用户上下文

        Returns:
            Dict[资源名称, 访问级别]
        """
        try:
            if not user_context.is_authenticated:
                return {}

            # 调用授权服务获取用户权限
            permissions = await self.authz_client.get_user_permissions(
                user_id=user_context.user_id, organization_id=user_context.organization_id
            )

            # 转换为AccessLevel枚举
            result = {}
            for resource, level in permissions.items():
                try:
                    result[resource] = AccessLevel(level)
                except ValueError:
                    result[resource] = AccessLevel.NONE

            return result

        except Exception as e:
            logger.error(f"Error fetching user permissions: {str(e)}")
            return {}

    async def grant_permission(
        self,
        admin_context: UserContext,
        target_user_id: str,
        resource_type: ResourceType,
        resource_name: str,
        access_level: AccessLevel,
        expires_in_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        授予用户权限（需要管理员权限）

        Args:
            admin_context: 管理员上下文
            target_user_id: 目标用户ID
            resource_type: 资源类型
            resource_name: 资源名称
            access_level: 访问级别
            expires_in_days: 过期天数

        Returns:
            授予结果
        """
        try:
            # 检查管理员权限
            admin_check = await self.check_resource_access(
                admin_context, ResourceType.API_ENDPOINT, "permission_management", AccessLevel.ADMIN
            )

            if not admin_check.get("has_access"):
                return {"success": False, "error": "Admin permission required"}

            # 调用授权服务授予权限
            result = await self.authz_client.grant_permission(
                user_id=target_user_id,
                resource_type=resource_type.value,
                resource_name=resource_name,
                access_level=access_level.value,
                granted_by=admin_context.user_id,
                expires_in_days=expires_in_days,
            )

            return result

        except Exception as e:
            logger.error(f"Error granting permission: {str(e)}")
            return {"success": False, "error": str(e)}

    async def revoke_permission(
        self,
        admin_context: UserContext,
        target_user_id: str,
        resource_type: ResourceType,
        resource_name: str,
    ) -> Dict[str, Any]:
        """
        撤销用户权限（需要管理员权限）

        Args:
            admin_context: 管理员上下文
            target_user_id: 目标用户ID
            resource_type: 资源类型
            resource_name: 资源名称

        Returns:
            撤销结果
        """
        try:
            # 检查管理员权限
            admin_check = await self.check_resource_access(
                admin_context, ResourceType.API_ENDPOINT, "permission_management", AccessLevel.ADMIN
            )

            if not admin_check.get("has_access"):
                return {"success": False, "error": "Admin permission required"}

            # 调用授权服务撤销权限
            result = await self.authz_client.revoke_permission(
                user_id=target_user_id,
                resource_type=resource_type.value,
                resource_name=resource_name,
                revoked_by=admin_context.user_id,
            )

            return result

        except Exception as e:
            logger.error(f"Error revoking permission: {str(e)}")
            return {"success": False, "error": str(e)}


# 默认的MCP资源权限配置
DEFAULT_MCP_PERMISSIONS = {
    # Free tier MCP tools
    "mcp_tool/store_knowledge": {"tier": SubscriptionTier.FREE, "level": AccessLevel.READ_WRITE},
    "mcp_tool/search_knowledge": {"tier": SubscriptionTier.FREE, "level": AccessLevel.READ_ONLY},
    "mcp_tool/weather_api": {"tier": SubscriptionTier.FREE, "level": AccessLevel.READ_ONLY},
    # Pro tier MCP tools
    "mcp_tool/generate_rag_response": {
        "tier": SubscriptionTier.PRO,
        "level": AccessLevel.READ_WRITE,
    },
    "mcp_tool/advanced_analytics": {"tier": SubscriptionTier.PRO, "level": AccessLevel.READ_WRITE},
    # Enterprise tier resources
    "mcp_resource/knowledge_base_admin": {
        "tier": SubscriptionTier.ENTERPRISE,
        "level": AccessLevel.ADMIN,
    },
    # Prompts
    "mcp_prompt/basic_assistant": {"tier": SubscriptionTier.FREE, "level": AccessLevel.READ_ONLY},
    "mcp_prompt/advanced_coder": {"tier": SubscriptionTier.PRO, "level": AccessLevel.READ_ONLY},
}
