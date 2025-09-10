"""
Invitation Management Endpoints

Invitation-related functionality extracted from api_server.py
Handles organization invitations, acceptance, and management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

from models import OrganizationInvitationCreate, AcceptInvitationRequest

logger = logging.getLogger(__name__)

# Create routers for different invitation endpoints
org_router = APIRouter(prefix="/api/v1/organizations/{organization_id}/invitations", tags=["Invitations"])
invitation_router = APIRouter(prefix="/api/v1/invitations", tags=["Invitations"])


# Organization invitation endpoints
@org_router.post("", response_model=Dict[str, Any])
async def create_organization_invitation(
    organization_id: str,
    invitation_data: OrganizationInvitationCreate,
    current_user=None,
    invitation_service=None,
    organization_service=None
):
    """Create organization invitation - Original: api_server.py lines 1334-1377"""
    try:
        if not current_user or not invitation_service or not organization_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Check if user has admin access to this organization
        access_result = await organization_service.check_admin_access(current_user["sub"], organization_id)
        if not access_result.is_success:
            raise HTTPException(status_code=403, detail="Admin access required to create invitations")
            
        result = await invitation_service.create_invitation(
            organization_id=organization_id,
            inviter_id=current_user["sub"],
            invitee_email=invitation_data.email,
            role=invitation_data.role,
            message=invitation_data.message
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "invitation": result.data.dict(),
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating invitation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create invitation: {str(e)}")


@org_router.get("", response_model=Dict[str, Any])
async def get_organization_invitations(
    organization_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user=None,
    invitation_service=None,
    organization_service=None
):
    """Get organization invitations - Original: api_server.py lines 1380-1415"""
    try:
        if not current_user or not invitation_service or not organization_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Check if user has access to this organization
        access_result = await organization_service.check_user_access(current_user["sub"], organization_id)
        if not access_result.is_success:
            raise HTTPException(status_code=403, detail="Not authorized to view invitations for this organization")
            
        result = await invitation_service.get_organization_invitations(
            organization_id=organization_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "invitations": [invitation.dict() for invitation in result.data],
            "count": len(result.data),
            "organization_id": organization_id,
            "status_filter": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization invitations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get organization invitations: {str(e)}")


# General invitation endpoints
@invitation_router.get("/{invitation_token}", response_model=Dict[str, Any])
async def get_invitation_by_token(
    invitation_token: str,
    invitation_service=None
):
    """Get invitation by token - Original: api_server.py lines 1418-1443"""
    try:
        if not invitation_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        result = await invitation_service.get_invitation_by_token(invitation_token)
        
        if not result.is_success:
            if "not found" in result.message.lower() or "expired" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "invitation": result.data.dict(),
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invitation by token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get invitation: {str(e)}")


@invitation_router.post("/accept", response_model=Dict[str, Any])
async def accept_invitation(
    accept_request: AcceptInvitationRequest,
    current_user=None,
    invitation_service=None
):
    """Accept invitation - Original: api_server.py lines 1446-1483"""
    try:
        if not current_user or not invitation_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        result = await invitation_service.accept_invitation(
            invitation_token=accept_request.invitation_token,
            accepter_id=current_user["sub"]
        )
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "expired" in result.message.lower():
                raise HTTPException(status_code=410, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "organization_id": result.data["organization_id"],
            "role": result.data["role"],
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to accept invitation: {str(e)}")


@invitation_router.delete("/{invitation_id}", response_model=Dict[str, Any])
async def cancel_invitation(
    invitation_id: str,
    current_user=None,
    invitation_service=None
):
    """Cancel invitation - Original: api_server.py lines 1486-1519"""
    try:
        if not current_user or not invitation_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Get invitation to verify permissions
        invitation_result = await invitation_service.get_invitation(invitation_id)
        if not invitation_result.is_success:
            raise HTTPException(status_code=404, detail="Invitation not found")
            
        invitation = invitation_result.data
        
        # Check if user can cancel this invitation (must be inviter or org admin)
        if invitation.inviter_id != current_user["sub"]:
            # TODO: Check if user is org admin
            raise HTTPException(status_code=403, detail="Not authorized to cancel this invitation")
            
        result = await invitation_service.cancel_invitation(
            invitation_id=invitation_id,
            cancelled_by=current_user["sub"]
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
        logger.error(f"Error cancelling invitation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel invitation: {str(e)}")


@invitation_router.post("/{invitation_id}/resend", response_model=Dict[str, Any])
async def resend_invitation(
    invitation_id: str,
    current_user=None,
    invitation_service=None
):
    """Resend invitation - Original: api_server.py lines 1522-1555"""
    try:
        if not current_user or not invitation_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Get invitation to verify permissions
        invitation_result = await invitation_service.get_invitation(invitation_id)
        if not invitation_result.is_success:
            raise HTTPException(status_code=404, detail="Invitation not found")
            
        invitation = invitation_result.data
        
        # Check if user can resend this invitation (must be inviter or org admin)
        if invitation.inviter_id != current_user["sub"]:
            # TODO: Check if user is org admin
            raise HTTPException(status_code=403, detail="Not authorized to resend this invitation")
            
        result = await invitation_service.resend_invitation(invitation_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "invitation": result.data.dict(),
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending invitation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to resend invitation: {str(e)}")