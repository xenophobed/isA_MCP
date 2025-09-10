"""
Dependency Injection System

Centralized dependency management for all API endpoints
"""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, Header
import jwt
from jwt.exceptions import InvalidTokenError
import os
import logging
from functools import lru_cache

from services.user_service import UserService
from services.subscription_service import SubscriptionService
from services.credit_service import CreditService
from services.session_service import SessionService
from services.email_service import EmailService
from services.file_storage_service import FileStorageService
from services.auth_service import Auth0Service
from services.supabase_auth_service import SupabaseAuthService
from services.unified_auth_service import UnifiedAuthService
from repositories.user_repository import UserRepository
from repositories.base import BaseRepository
from config import UserServiceConfig

logger = logging.getLogger(__name__)


class DependencyContainer:
    """Centralized dependency container for service management"""
    
    def __init__(self):
        self._config = None
        self._user_repository = None
        self._user_service = None
        self._subscription_service = None
        self._credit_service = None
        self._session_service = None
        self._email_service = None
        self._file_storage_service = None
        self._auth_service = None
        self._supabase_auth_service = None
        self._unified_auth_service = None
        self._organization_service = None
        self._invitation_service = None
        self._analytics_service = None
        self._usage_service = None
        self._payment_service = None
        self._resource_service = None
    
    @property
    def config(self) -> UserServiceConfig:
        if self._config is None:
            self._config = UserServiceConfig()
        return self._config
    
    @property
    def user_repository(self) -> UserRepository:
        if self._user_repository is None:
            self._user_repository = UserRepository()
        return self._user_repository
    
    @property
    def user_service(self) -> UserService:
        if self._user_service is None:
            self._user_service = UserService(
                user_repository=self.user_repository
            )
        return self._user_service
    
    @property
    def subscription_service(self) -> SubscriptionService:
        if self._subscription_service is None:
            self._subscription_service = SubscriptionService(
                subscription_repository=None,
                user_repository=self.user_repository
            )
        return self._subscription_service
    
    @property
    def credit_service(self) -> CreditService:
        if self._credit_service is None:
            self._credit_service = CreditService()
        return self._credit_service
    
    @property
    def session_service(self) -> SessionService:
        if self._session_service is None:
            self._session_service = SessionService()
        return self._session_service
    
    @property
    def email_service(self) -> EmailService:
        if self._email_service is None:
            self._email_service = EmailService()
        return self._email_service
    
    @property
    def file_storage_service(self) -> FileStorageService:
        if self._file_storage_service is None:
            self._file_storage_service = FileStorageService()
        return self._file_storage_service
    
    @property
    def auth_service(self) -> Auth0Service:
        if self._auth_service is None:
            self._auth_service = Auth0Service(
                domain=self.config.auth0_domain,
                audience=self.config.auth0_audience,
                client_id=getattr(self.config, 'auth0_client_id', None),
                client_secret=getattr(self.config, 'auth0_client_secret', None)
            )
        return self._auth_service
    
    @property
    def supabase_auth_service(self) -> Optional[SupabaseAuthService]:
        if self._supabase_auth_service is None:
            config = self.config
            if config.auth_provider in ["supabase", "both"]:
                try:
                    self._supabase_auth_service = SupabaseAuthService(
                        supabase_url=config.supabase_url,
                        jwt_secret=config.supabase_jwt_secret,
                        anon_key=config.supabase_anon_key,
                        service_role_key=config.supabase_service_role_key
                    )
                except Exception as e:
                    logger.warning(f"Failed to initialize Supabase auth service: {e}")
                    self._supabase_auth_service = None
        return self._supabase_auth_service
    
    @property
    def unified_auth_service(self) -> UnifiedAuthService:
        if self._unified_auth_service is None:
            self._unified_auth_service = UnifiedAuthService(
                auth0_service=self.auth_service,
                supabase_service=self.supabase_auth_service,
                default_provider=self.config.auth_provider
            )
        return self._unified_auth_service


# Global dependency container instance
container = DependencyContainer()


@lru_cache()
def get_config() -> UserServiceConfig:
    """Get application configuration"""
    return container.config


def get_user_service() -> UserService:
    """Get user service instance"""
    return container.user_service


def get_subscription_service() -> SubscriptionService:
    """Get subscription service instance"""
    return container.subscription_service


def get_credit_service() -> CreditService:
    """Get credit service instance"""
    return container.credit_service


def get_session_service() -> SessionService:
    """Get session service instance"""
    return container.session_service


def get_email_service() -> EmailService:
    """Get email service instance"""
    return container.email_service


def get_file_storage_service() -> FileStorageService:
    """Get file storage service instance"""
    return container.file_storage_service


def get_auth_service() -> Auth0Service:
    """Get auth service instance"""
    return container.auth_service


def get_supabase_auth_service() -> Optional[SupabaseAuthService]:
    """Get Supabase auth service instance"""
    return container.supabase_auth_service


def get_unified_auth_service() -> UnifiedAuthService:
    """Get unified auth service instance"""
    return container.unified_auth_service


def get_organization_service():
    """Get organization service instance (placeholder)"""
    return container._organization_service


def get_invitation_service():
    """Get invitation service instance (placeholder)"""
    return container._invitation_service


def get_analytics_service():
    """Get analytics service instance (placeholder)"""
    return container._analytics_service


def get_usage_service():
    """Get usage service instance (placeholder)"""
    return container._usage_service


def get_payment_service():
    """Get payment service instance (placeholder)"""
    return container._payment_service


def get_resource_service():
    """Get resource service instance (placeholder)"""
    return container._resource_service


async def get_current_user(authorization: Annotated[str, Header()] = None) -> dict:
    """Extract and validate current user from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization
        
        # Get unified auth service
        unified_auth = get_unified_auth_service()
        
        if unified_auth:
            # Use unified auth service to verify token
            try:
                # Try to verify token with available providers
                payload, provider = await unified_auth.verify_token(token)
                if payload:
                    logger.debug(f"Token verified using {provider.value}")
                    return payload
            except Exception as e:
                logger.warning(f"Unified auth verification failed: {e}")
        
        # Fallback to Auth0 validation if unified auth fails
        config = get_config()
        
        # Decode JWT token using Auth0 configuration
        payload = jwt.decode(
            token,
            key=getattr(config, 'auth0_public_key', None),
            algorithms=["RS256"],
            audience=config.auth0_audience,
            issuer=getattr(config, 'auth0_issuer', f"https://{config.auth0_domain}/")
        )
        
        return payload
        
    except (IndexError, InvalidTokenError) as e:
        logger.warning(f"Invalid token provided: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        raise HTTPException(status_code=401, detail="Token validation failed")


# Dependency type aliases for cleaner endpoint signatures
CurrentUser = Annotated[dict, Depends(get_current_user)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
SubscriptionServiceDep = Annotated[SubscriptionService, Depends(get_subscription_service)]
CreditServiceDep = Annotated[CreditService, Depends(get_credit_service)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]
FileStorageServiceDep = Annotated[FileStorageService, Depends(get_file_storage_service)]
Auth0ServiceDep = Annotated[Auth0Service, Depends(get_auth_service)]
SupabaseAuthServiceDep = Annotated[Optional[SupabaseAuthService], Depends(get_supabase_auth_service)]
UnifiedAuthServiceDep = Annotated[UnifiedAuthService, Depends(get_unified_auth_service)]