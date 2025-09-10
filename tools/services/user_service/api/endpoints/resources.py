"""
Resource Authorization Endpoints

Resource authorization functionality extracted from api_server.py
Handles resource access checks, permissions, and admin operations
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging
import sys
import os

# Add dependencies for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models.schemas.resource_models import ResourceAccessCheck, GrantResourceAccessRequest, RevokeResourceAccessRequest
from api.dependencies import get_current_user, get_resource_service, CurrentUser

logger = logging.getLogger(__name__)

# Create separate routers for user and admin endpoints
user_router = APIRouter(prefix="/api/v1", tags=["Resource Authorization"])
admin_router = APIRouter(prefix="/api/v1/admin/resources", tags=["Resource Authorization Admin"])


# User endpoints
@user_router.post("/resources/check-access", response_model=Dict[str, Any])
async def check_resource_access(
    access_check: ResourceAccessCheck,
    current_user: CurrentUser
):
    """Check resource access - Original: api_server.py lines 2029-2058"""
    try:
        if not current_user or not resource_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        result = await resource_service.check_access(
            user_id=current_user["sub"],
            resource_id=access_check.resource_id,
            resource_type=access_check.resource_type,
            requested_access_level=access_check.access_level
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "has_access": result.data.has_access,
            "access_level": result.data.access_level.value if result.data.access_level else "none",
            "resource_id": access_check.resource_id,
            "resource_type": access_check.resource_type.value,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking resource access: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check resource access: {str(e)}")


@user_router.get("/users/{user_id}/resources/summary", response_model=Dict[str, Any])
async def get_user_resource_summary(
    user_id: str,
    current_user: CurrentUser,
    resource_service=None
):
    """Get user resource summary - Original: api_server.py lines 2059-2098"""
    try:
        if not current_user or not resource_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view resource summary for this user")
            
        result = await resource_service.get_user_resource_summary(user_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return result.data.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user resource summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user resource summary: {str(e)}")


@user_router.get("/users/{user_id}/resources/accessible", response_model=Dict[str, Any])
async def get_user_accessible_resources(
    user_id: str,
    current_user: CurrentUser,
    resource_type: Optional[str] = None,
    resource_service=None
):
    """Get user accessible resources - Original: api_server.py lines 2099-2138"""
    try:
        if not current_user or not resource_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view accessible resources for this user")
            
        result = await resource_service.get_user_accessible_resources(
            user_id=user_id,
            resource_type=resource_type
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "accessible_resources": [resource.dict() for resource in result.data],
            "count": len(result.data),
            "user_id": user_id,
            "resource_type_filter": resource_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting accessible resources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get accessible resources: {str(e)}")


# Admin endpoints
@admin_router.post("/grant-access", response_model=Dict[str, Any])
async def grant_resource_access(
    grant_request: GrantResourceAccessRequest,
    current_user: CurrentUser,
    resource_service=None
):
    """Grant resource access - Original: api_server.py lines 2141-2178"""
    try:
        if not current_user or not resource_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Check if current user has admin access
        admin_result = await resource_service.check_admin_access(current_user["sub"])
        if not admin_result.is_success:
            raise HTTPException(status_code=403, detail="Admin access required")
            
        result = await resource_service.grant_access(
            user_id=grant_request.user_id,
            resource_id=grant_request.resource_id,
            resource_type=grant_request.resource_type,
            access_level=grant_request.access_level,
            granted_by=current_user["sub"],
            expires_at=grant_request.expires_at
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "permission": result.data.dict(),
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting resource access: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to grant resource access: {str(e)}")


@admin_router.post("/revoke-access", response_model=Dict[str, Any])
async def revoke_resource_access(
    revoke_request: RevokeResourceAccessRequest,
    current_user: CurrentUser,
    resource_service=None
):
    """Revoke resource access - Original: api_server.py lines 2179-2214"""
    try:
        if not current_user or not resource_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Check if current user has admin access
        admin_result = await resource_service.check_admin_access(current_user["sub"])
        if not admin_result.is_success:
            raise HTTPException(status_code=403, detail="Admin access required")
            
        result = await resource_service.revoke_access(
            user_id=revoke_request.user_id,
            resource_id=revoke_request.resource_id,
            resource_type=revoke_request.resource_type,
            revoked_by=current_user["sub"],
            reason=revoke_request.reason
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking resource access: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to revoke resource access: {str(e)}")


@admin_router.get("/permissions", response_model=Dict[str, Any])
async def get_all_permissions(
    current_user: CurrentUser,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    resource_service=None
):
    """Get all permissions - Original: api_server.py lines 2217-2254"""
    try:
        if not current_user or not resource_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Check if current user has admin access
        admin_result = await resource_service.check_admin_access(current_user["sub"])
        if not admin_result.is_success:
            raise HTTPException(status_code=403, detail="Admin access required")
            
        result = await resource_service.get_permissions(
            resource_id=resource_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "permissions": [permission.dict() for permission in result.data],
            "count": len(result.data),
            "limit": limit,
            "offset": offset,
            "filters": {
                "resource_id": resource_id,
                "user_id": user_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting permissions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get permissions: {str(e)}")


@admin_router.post("/initialize-defaults", response_model=Dict[str, Any])
async def initialize_default_permissions(
    current_user: CurrentUser,
    resource_service=None
):
    """Initialize default permissions - Original: api_server.py lines 2257-2282"""
    try:
        if not current_user or not resource_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Check if current user has admin access
        admin_result = await resource_service.check_admin_access(current_user["sub"])
        if not admin_result.is_success:
            raise HTTPException(status_code=403, detail="Admin access required")
            
        result = await resource_service.initialize_default_permissions()
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "initialized_permissions": result.data,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing default permissions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize default permissions: {str(e)}")


@admin_router.post("/cleanup-expired", response_model=Dict[str, Any])
async def cleanup_expired_permissions(
    current_user: CurrentUser,
    resource_service=None
):
    """Cleanup expired permissions - Original: api_server.py lines 2285-2308"""
    try:
        if not current_user or not resource_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Check if current user has admin access
        admin_result = await resource_service.check_admin_access(current_user["sub"])
        if not admin_result.is_success:
            raise HTTPException(status_code=403, detail="Admin access required")
            
        result = await resource_service.cleanup_expired_permissions()
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "cleaned_up_count": result.data,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up expired permissions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup expired permissions: {str(e)}")