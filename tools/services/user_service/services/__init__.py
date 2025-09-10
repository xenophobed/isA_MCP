"""
Service Layer for User Service

Implements business logic layer using Repository pattern for data access
Follows Domain-Driven Design (DDD) principles
"""

from .base import BaseService, ServiceResult
from .user_service import UserService
from .subscription_service import SubscriptionService
from .organization_service import OrganizationService
from .email_service import EmailService
from .invitation_service import InvitationService
# from .portrait.user_portrait_service import UserPortraitService  # Commented out to avoid chain dependencies

__all__ = [
    'BaseService',
    'ServiceResult', 
    'UserService',
    'SubscriptionService',
    'OrganizationService',
    'EmailService',
    'InvitationService',
    # 'UserPortraitService',  # Temporarily removed
]