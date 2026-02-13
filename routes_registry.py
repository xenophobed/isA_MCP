#!/usr/bin/env python3
"""
MCP Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# 定义所有路由
SERVICE_ROUTES = [
    {"path": "/", "methods": ["GET"], "auth_required": False, "description": "Root health check"},
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check",
    },
    {
        "path": "/mcp",
        "methods": ["GET", "POST", "OPTIONS"],
        "auth_required": True,
        "description": "MCP Protocol endpoint - main MCP interface",
    },
    {
        "path": "/search",
        "methods": ["POST", "OPTIONS"],
        "auth_required": True,
        "description": "Semantic search for tools/prompts/resources using Qdrant",
    },
    {
        "path": "/sync",
        "methods": ["POST", "OPTIONS"],
        "auth_required": True,
        "description": "Manual sync trigger for PostgreSQL + Qdrant",
    },
    {
        "path": "/progress/{operation_id}/stream",
        "methods": ["GET"],
        "auth_required": True,
        "description": "SSE streaming endpoint for real-time progress updates",
    },
    # Skill API endpoints
    {
        "path": "/api/v1/skills",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List or create skill categories",
    },
    {
        "path": "/api/v1/skills/{skill_id}",
        "methods": ["GET", "DELETE"],
        "auth_required": True,
        "description": "Get or delete skill by ID",
    },
    {
        "path": "/api/v1/skills/{skill_id}/tools",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get tools in a skill category",
    },
    {
        "path": "/api/v1/skills/classify",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Classify a tool into skill categories",
    },
    {
        "path": "/api/v1/skills/suggestions",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List pending skill suggestions",
    },
    # Search API endpoints
    {
        "path": "/api/v1/search",
        "methods": ["POST", "OPTIONS"],
        "auth_required": True,
        "description": "Hierarchical search with skill-based routing",
    },
    {
        "path": "/api/v1/search/skills",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Search skills only",
    },
    {
        "path": "/api/v1/search/tools",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Search tools only with optional skill filter",
    },
]


def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    api_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        if path in ["/", "/health"]:
            health_routes.append(path)
        else:
            # 使用紧凑表示
            api_routes.append(path)

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/mcp",  # Unified API path convention
        "health": ",".join(health_routes),
        "api": ",".join(api_routes),
        "methods": "GET,POST,OPTIONS",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


# 服务元数据
SERVICE_METADATA = {
    "service_name": "mcp_service",
    "version": "1.0.0",
    "tags": ["v1", "platform", "ai", "mcp"],
    "capabilities": [
        "semantic_search",
        "tool_discovery",
        "prompt_management",
        "resource_management",
        "progress_tracking",
    ],
}
