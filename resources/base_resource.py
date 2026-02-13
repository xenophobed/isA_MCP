#!/usr/bin/env python
"""
Base Resource Class for ISA MCP Resources
统一处理资源依赖、安全检查、数据库连接和响应格式
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger

logger = get_logger(__name__)


class BaseResource:
    """基础资源类，提供统一的依赖管理和响应处理"""

    def __init__(self):
        self._security_manager = None
        self.registered_resources = []

    @property
    def security_manager(self):
        """延迟初始化安全管理器，带错误处理"""
        if self._security_manager is None:
            try:
                self._security_manager = get_security_manager()
            except Exception as e:
                logger.warning(f"Security manager not available: {e}")
                # 返回一个mock安全管理器，避免注册失败
                self._security_manager = MockSecurityManager()
        return self._security_manager

    def register_resource(
        self,
        mcp,
        uri: str,
        func: Callable,
        security_level: SecurityLevel = SecurityLevel.LOW,
        **kwargs,
    ):
        """
        注册资源到MCP服务器，自动应用安全检查和错误处理

        Args:
            mcp: MCP服务器实例
            uri: 资源URI
            func: 资源函数
            security_level: 安全级别
            **kwargs: 传递给@mcp.resource()的额外参数
        """
        # 直接使用原函数，不包装，以保持参数签名
        decorated_func = func

        # 应用安全装饰器（如果安全管理器可用）
        try:
            decorated_func = self.security_manager.security_check(decorated_func)
            decorated_func = self.security_manager.require_authorization(security_level)(
                decorated_func
            )
        except Exception as e:
            logger.warning(f"Security decorators not applied for {uri}: {e}")
            # 保持原函数不变
            pass

        # 注册资源
        resource_func = mcp.resource(uri, **kwargs)(decorated_func)

        # 记录注册的资源
        self.registered_resources.append(
            {"uri": uri, "function": func.__name__, "security_level": security_level.name}
        )

        logger.debug(f"Registered resource: {uri}")
        return resource_func

    def create_success_response(self, data: Any, uri: str = None) -> str:
        """
        创建成功响应

        Args:
            data: 响应数据
            uri: 资源URI（可选）

        Returns:
            str: 格式化的响应字符串
        """
        if isinstance(data, str):
            # 如果数据已经是字符串（如Markdown），直接返回
            return data
        elif isinstance(data, dict):
            # 如果是字典，转换为JSON
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            # 其他类型，转换为字符串
            return str(data)

    def create_error_response(self, uri: str, error_message: str) -> str:
        """
        创建错误响应

        Args:
            uri: 资源URI
            error_message: 错误消息

        Returns:
            str: 格式化的错误响应
        """
        error_response = f"""# Error: {uri}

**Error**: {error_message}

**Timestamp**: {datetime.now().isoformat()}

---
*This error occurred while accessing the resource. Please check the request parameters and try again.*
"""
        return error_response

    def create_not_found_response(self, uri: str, resource_type: str = "resource") -> str:
        """
        创建资源未找到响应

        Args:
            uri: 资源URI
            resource_type: 资源类型描述

        Returns:
            str: 格式化的未找到响应
        """
        return f"""# {resource_type.title()} Not Found: {uri}

No {resource_type} was found for the requested identifier.

**Timestamp**: {datetime.now().isoformat()}

---
*Please verify the identifier and try again.*
"""

    def register_all_resources(self, mcp):
        """
        注册所有资源的模板方法
        子类应该重写这个方法来注册具体的资源
        """
        pass


class MockSecurityManager:
    """Mock安全管理器，用于在安全管理器不可用时提供兼容性"""

    def security_check(self, func):
        """Mock安全检查装饰器"""
        return func

    def require_authorization(self, level):
        """Mock授权装饰器"""

        def decorator(func):
            return func

        return decorator


def create_simple_resource_registration(register_func_name: str = "register_resources"):
    """
    创建简单的资源注册函数装饰器

    Args:
        register_func_name: 注册函数名称

    Returns:
        装饰器函数
    """

    def decorator(resource_class):
        """为资源类添加注册函数"""

        def register_function(mcp):
            """动态创建的注册函数"""
            try:
                instance = resource_class()
                instance.register_all_resources(mcp)
                logger.debug(f"{resource_class.__name__} resources registered")
            except Exception as e:
                logger.error(f"❌ Failed to register {resource_class.__name__}: {e}")
                raise

        # 将注册函数添加到模块级别
        import sys

        caller_frame = sys._getframe(1)
        caller_globals = caller_frame.f_globals
        caller_globals[register_func_name] = register_function

        return resource_class

    return decorator


# 便捷装饰器
def simple_resource(uri_pattern: str, security_level: SecurityLevel = SecurityLevel.LOW):
    """
    简单资源装饰器，用于快速创建资源函数

    Usage:
        @simple_resource("memory://test/{id}")
        async def get_test_resource(id: str) -> str:
            return f"Test resource for {id}"
    """

    def decorator(func):
        func._resource_uri = uri_pattern
        func._security_level = security_level
        return func

    return decorator
