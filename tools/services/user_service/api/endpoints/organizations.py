"""
Organization Management Endpoints

Organization-related functionality extracted from api_server.py
Handles organization CRUD, membership, invitations, and stats
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

from models import OrganizationCreate, OrganizationUpdate, OrganizationMemberCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


@router.post("", response_model=Dict[str, Any])
async def create_organization(
    org_data: OrganizationCreate,
    current_user=None,
    organization_service=None
):
    """Create organization - Original: api_server.py lines 1092-1119"""
    try:
        if not current_user or not organization_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        result = await organization_service.create_organization(
            owner_id=current_user["sub"],
            name=org_data.name,
            description=org_data.description
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "organization": result.data.dict(),
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create organization: {str(e)}")


@router.get("/{organization_id}", response_model=Dict[str, Any])
async def get_organization(
    organization_id: str,
    current_user=None,
    organization_service=None
):
    """Get organization - Original: api_server.py lines 1122-1145"""
    try:
        if not current_user or not organization_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Check if user has access to this organization
        access_result = await organization_service.check_user_access(current_user["sub"], organization_id)
        if not access_result.is_success:
            raise HTTPException(status_code=403, detail="Not authorized to access this organization")
            
        result = await organization_service.get_organization(organization_id)
        
        if not result.is_success:
            raise HTTPException(status_code=404, detail=result.message)
            
        return result.data.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get organization: {str(e)}")


@router.put("/{organization_id}", response_model=Dict[str, Any])
async def update_organization(
    organization_id: str,
    update_data: OrganizationUpdate,
    current_user=None,
    organization_service=None
):
    """Update organization - Original: api_server.py lines 1148-1175"""
    try:
        if not current_user or not organization_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Verify user is admin of this organization
        access_result = await organization_service.check_admin_access(current_user["sub"], organization_id)
        if not access_result.is_success:
            raise HTTPException(status_code=403, detail="Admin access required")
            
        result = await organization_service.update_organization(organization_id, update_data)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "organization": result.data.dict(),
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update organization: {str(e)}")


@router.delete("/{organization_id}", response_model=Dict[str, Any])
async def delete_organization(
    organization_id: str,
    current_user=None,
    organization_service=None
):
    """Delete organization - Original: api_server.py lines 1178-1200"""
    try:
        if not current_user or not organization_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Verify user is owner of this organization
        access_result = await organization_service.check_owner_access(current_user["sub"], organization_id)
        if not access_result.is_success:
            raise HTTPException(status_code=403, detail="Owner access required")
            
        result = await organization_service.delete_organization(organization_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "message": "Organization deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete organization: {str(e)}")


@router.get("/{organization_id}/members", response_model=Dict[str, Any])
async def get_organization_members(
    organization_id: str,
    current_user=None,
    organization_service=None
):
    """Get organization members - Original: api_server.py lines 1203-1225"""
    try:
        if not current_user or not organization_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Check if user has access to this organization
        access_result = await organization_service.check_user_access(current_user["sub"], organization_id)
        if not access_result.is_success:
            raise HTTPException(status_code=403, detail="Not authorized to view organization members")
            
        result = await organization_service.get_organization_members(organization_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "members": [member.dict() for member in result.data],
            "count": len(result.data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization members: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get organization members: {str(e)}")