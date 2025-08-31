"""
Service Layer for User Service

实现业务逻辑层，使用Repository模式进行数据访问
遵循Domain-Driven Design (DDD) 原则
"""

from .base import BaseService, ServiceResult
from .user_service_v2 import UserServiceV2
from .subscription_service_v2 import SubscriptionServiceV2
from .organization_service import OrganizationService
from .email_service import EmailService
from .invitation_service import InvitationService
# from .portrait.user_portrait_service import UserPortraitService  # 注释掉避免连锁依赖
from .compatibility_adapter import (
    UserServiceCompatibilityAdapter,
    SubscriptionServiceCompatibilityAdapter
)

__all__ = [
    'BaseService',
    'ServiceResult', 
    'UserServiceV2',
    'SubscriptionServiceV2',
    'OrganizationService',
    'EmailService',
    'InvitationService',
    # 'UserPortraitService',  # 暂时移除
    'UserServiceCompatibilityAdapter',
    'SubscriptionServiceCompatibilityAdapter'
]