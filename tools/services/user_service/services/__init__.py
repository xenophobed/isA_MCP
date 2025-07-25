"""
Service Layer for User Service

实现业务逻辑层，使用Repository模式进行数据访问
遵循Domain-Driven Design (DDD) 原则
"""

from .base import BaseService, ServiceResult
from .user_service_v2 import UserServiceV2
from .subscription_service_v2 import SubscriptionServiceV2
from .compatibility_adapter import (
    UserServiceCompatibilityAdapter,
    SubscriptionServiceCompatibilityAdapter
)

__all__ = [
    'BaseService',
    'ServiceResult', 
    'UserServiceV2',
    'SubscriptionServiceV2',
    'UserServiceCompatibilityAdapter',
    'SubscriptionServiceCompatibilityAdapter'
]