#!/usr/bin/env python3
"""
MCP统一认证授权中间件
集成微服务架构的认证和授权
"""

import os
import logging
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .mcp_auth_service import MCPAuthService, ResourceType, AccessLevel

logger = logging.getLogger(__name__)


class MCPUnifiedAuthMiddleware(BaseHTTPMiddleware):
    """
    MCP统一认证授权中间件

    Features:
    - 集成User Service (8000)进行身份认证
    - 集成Authorization Service (8203)进行权限检查
    - 支持JWT Token和API Key
    - 自动解析MCP资源类型和权限需求
    """

    def __init__(self, app, config: Optional[Dict[str, Any]] = None):
        super().__init__(app)
        self.config = config or {}

        # 初始化认证服务
        self.auth_service = MCPAuthService(config)

        # 是否要求认证
        self.require_auth = self._get_auth_setting()

        # 路径配置
        self.bypass_paths = {
            "/health",
            "/static",
            "/portal",
            "/",
            "/admin",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

        # MCP路径映射
        self.mcp_routes = {
            "/mcp/tools": ResourceType.MCP_TOOL,
            "/mcp/prompts": ResourceType.PROMPT,
            "/mcp/resources": ResourceType.RESOURCE,
            "/api/mcp/tools": ResourceType.MCP_TOOL,
            "/api/mcp/prompts": ResourceType.PROMPT,
            "/api/mcp/resources": ResourceType.RESOURCE,
        }

        if self.require_auth:
            logger.info(
                f"  Auth: enabled ({self.auth_service.auth_service_url}, {self.auth_service.authorization_service_url})"
            )
        else:
            logger.info("  Auth: open access (disabled)")

    def _get_auth_setting(self) -> bool:
        """获取认证设置"""
        env_auth = os.getenv("REQUIRE_MCP_AUTH", "false").lower()
        if env_auth in ["true", "1", "yes", "on"]:
            return True

        if self.config.get("require_auth", False):
            return True

        return False

    def _should_bypass_auth(self, path: str) -> bool:
        """检查是否应该绕过认证"""
        for bypass_path in self.bypass_paths:
            if path.startswith(bypass_path):
                return True

        if "/static/" in path:
            return True

        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """从请求中提取token"""
        # Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()

        # API Key headers
        for header in ["X-API-Key", "X-MCP-API-Key"]:
            key = request.headers.get(header, "").strip()
            if key:
                return key

        # Query parameter (仅用于测试)
        api_key = request.query_params.get("api_key", "").strip()
        if api_key:
            return api_key

        return None

    def _parse_mcp_request(self, request: Request) -> tuple[Optional[ResourceType], Optional[str]]:
        """
        解析MCP请求，提取资源类型和名称

        Returns:
            (resource_type, resource_name)
        """
        path = request.url.path

        # 检查是否是MCP路径
        for route_prefix, resource_type in self.mcp_routes.items():
            if path.startswith(route_prefix):
                # 提取资源名称（路径的最后部分）
                parts = path.split("/")
                if len(parts) > 0:
                    resource_name = parts[-1] if parts[-1] else "default"
                else:
                    resource_name = "default"

                return resource_type, resource_name

        # 检查特定端点
        if "/knowledge" in path:
            return ResourceType.KNOWLEDGE_ITEM, "knowledge_base"
        elif "/rag" in path:
            return ResourceType.RAG_SESSION, "rag_service"

        return None, None

    def _determine_access_level(self, method: str) -> AccessLevel:
        """根据HTTP方法确定访问级别"""
        if method in ["GET", "HEAD", "OPTIONS"]:
            return AccessLevel.READ_ONLY
        elif method in ["POST", "PUT", "PATCH"]:
            return AccessLevel.READ_WRITE
        elif method == "DELETE":
            return AccessLevel.ADMIN
        else:
            return AccessLevel.READ_ONLY

    async def dispatch(self, request: Request, call_next):
        """中间件主处理方法"""
        path = request.url.path

        # Always extract X-Organization-Id header (even when auth is bypassed)
        org_header = request.headers.get("X-Organization-Id", "").strip()
        if org_header:
            request.state.organization_id = org_header

        # 检查是否需要认证
        if not self.require_auth or self._should_bypass_auth(path):
            logger.debug(f"🔓 Bypassing auth for: {path}")
            return await call_next(request)

        # 提取token
        token = self._extract_token(request)
        if not token:
            logger.warning(f"❌ No token provided for: {path}")
            return JSONResponse(
                {
                    "error": "Authentication required",
                    "message": "Please provide a valid JWT token or API key",
                    "path": path,
                },
                status_code=401,
                headers={
                    "WWW-Authenticate": 'Bearer realm="MCP API"',
                    "X-Auth-Methods": "Bearer token, X-API-Key, X-MCP-API-Key",
                },
            )

        # 验证token并获取用户上下文
        user_context = await self.auth_service.authenticate_token(token)

        if not user_context.is_authenticated:
            logger.warning(f"❌ Invalid token for: {path}")
            return JSONResponse(
                {
                    "error": "Invalid authentication",
                    "message": "The provided token is invalid or expired",
                    "path": path,
                },
                status_code=401,
            )

        # 解析MCP资源信息
        resource_type, resource_name = self._parse_mcp_request(request)

        # 如果是MCP资源，检查权限
        if resource_type:
            required_level = self._determine_access_level(request.method)

            # 检查资源访问权限
            access_result = await self.auth_service.check_resource_access(
                user_context, resource_type, resource_name, required_level
            )

            if not access_result.get("has_access"):
                logger.warning(
                    f"❌ Access denied for {user_context.user_id} to {resource_type.value}/{resource_name}"
                )
                return JSONResponse(
                    {
                        "error": "Access denied",
                        "message": access_result.get("reason", "Insufficient permissions"),
                        "required_subscription": access_result.get("required_subscription"),
                        "current_subscription": user_context.subscription_tier.value,
                        "resource": f"{resource_type.value}/{resource_name}",
                        "required_level": required_level.value,
                    },
                    status_code=403,
                )

            logger.debug(
                f"✅ Access granted for {user_context.user_id} to {resource_type.value}/{resource_name}"
            )

        # 设置请求状态供下游使用
        request.state.authenticated = True
        request.state.user_context = user_context
        request.state.user_id = user_context.user_id
        request.state.organization_id = user_context.organization_id
        request.state.subscription_tier = user_context.subscription_tier.value
        request.state.permissions = await self.auth_service.get_user_permissions(user_context)

        # Allow X-Organization-Id header to override JWT org for multi-org users
        org_header = request.headers.get("X-Organization-Id", "").strip()
        if org_header:
            request.state.organization_id = org_header

        # 继续处理请求
        response = await call_next(request)

        # 可选：添加用户信息到响应头
        if user_context.is_authenticated:
            response.headers["X-User-ID"] = user_context.user_id
            if user_context.organization_id:
                response.headers["X-Organization-ID"] = user_context.organization_id

        return response


def add_mcp_unified_auth_middleware(app, config: Optional[Dict[str, Any]] = None):
    """
    添加MCP统一认证授权中间件到应用

    Args:
        app: Starlette/FastAPI应用
        config: 配置字典
    """
    if config is None:
        config = {}

    # 添加中间件
    app.add_middleware(MCPUnifiedAuthMiddleware, config=config)

    logger.debug("MCP Unified Auth Middleware added to application")
    return True
