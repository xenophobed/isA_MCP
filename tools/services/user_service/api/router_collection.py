"""
Centralized Router Collection

Aggregates all modular API routers for integration into main API server
"""

from fastapi import APIRouter
from .dependencies import *

# Import all modular routers
from .endpoints.health_auth import health_router, auth_router
from .endpoints.users import router as users_router
from .endpoints.subscriptions import router as subscriptions_router
from .endpoints.credits import router as credits_router
from .endpoints.organizations import router as organizations_router
from .endpoints.sessions import router as sessions_router
from .endpoints.payments import router as payments_router
from .endpoints.files import router as files_router
from .endpoints.webhooks import router as webhooks_router
from .endpoints.resources import user_router as resources_user_router, admin_router as resources_admin_router
from .endpoints.invitations import org_router as invitations_org_router, invitation_router as invitations_router
from .endpoints.usage import router as usage_router
from .endpoints.analytics import router as analytics_router
from .endpoints.tasks import router as tasks_router
from .endpoints.events import router as events_router


def create_integrated_router() -> APIRouter:
    """Create a single router with all endpoints integrated"""
    
    # Create main router
    main_router = APIRouter()
    
    # Add all routers with proper tags
    routers_to_add = [
        (health_router, ["Health"]),
        (auth_router, ["Authentication"]),
        (users_router, ["Users"]),
        (subscriptions_router, ["Subscriptions"]),
        (credits_router, ["Credits"]),
        (organizations_router, ["Organizations"]),
        (sessions_router, ["Sessions"]),
        (payments_router, ["Payments"]),
        (files_router, ["Files"]),
        (webhooks_router, ["Webhooks"]),
        (resources_user_router, ["Resource Authorization"]),
        (resources_admin_router, ["Resource Authorization Admin"]),
        (invitations_org_router, ["Invitations"]),
        (invitations_router, ["Invitations"]),
        (usage_router, ["Usage Records"]),
        (analytics_router, ["Analytics"]),
        (tasks_router, ["Tasks"]),
        (events_router, ["Events"])
    ]
    
    for router, tags in routers_to_add:
        main_router.include_router(router, tags=tags)
    
    return main_router


# Export the integrated router
integrated_router = create_integrated_router()

__all__ = ["integrated_router", "create_integrated_router"]