"""
Analytics Endpoints

Analytics-related functionality extracted from api_server.py
Handles user analytics, behavior insights, and predictions
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/users/{user_id}/analytics", tags=["Analytics"])


@router.get("")
async def get_user_analytics(
    user_id: str,
    current_user=None,
    user_service=None,
    analytics_service=None
):
    """Get user analytics - Original: api_server.py lines 2327-2376"""
    try:
        if not current_user or not user_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view analytics for this user")
            
        # Get basic user analytics from user service
        result = await user_service.get_user_analytics(user_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        analytics_data = result.data
        
        # If analytics service is available, get enhanced analytics
        if analytics_service:
            try:
                enhanced_result = await analytics_service.get_user_insights(user_id)
                if enhanced_result.is_success:
                    analytics_data.update({
                        "enhanced_insights": enhanced_result.data,
                        "analytics_version": "enhanced"
                    })
            except Exception as e:
                logger.warning(f"Failed to get enhanced analytics for user {user_id}: {e}")
                analytics_data["analytics_version"] = "basic"
        else:
            analytics_data["analytics_version"] = "basic"
            
        return {
            "user_id": user_id,
            "analytics": analytics_data,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user analytics: {str(e)}")


@router.get("/switch-context")
async def switch_user_context(
    user_id: str,
    organization_id: Optional[str] = None,
    current_user=None,
    user_service=None,
    organization_service=None
):
    """Switch user context - Original: api_server.py lines 1306-1333"""
    try:
        if not current_user or not user_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to switch context for this user")
            
        # If organization_id provided, verify user has access
        if organization_id and organization_service:
            access_result = await organization_service.check_user_access(user_id, organization_id)
            if not access_result.is_success:
                raise HTTPException(status_code=403, detail="Not authorized to switch to this organization context")
                
        result = await user_service.switch_user_context(
            user_id=user_id,
            organization_id=organization_id
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "new_context": result.data,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching user context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to switch user context: {str(e)}")


@router.get("/organizations")
async def get_user_organizations(
    user_id: str,
    current_user=None,
    organization_service=None
):
    """Get user organizations - Original: api_server.py lines 1272-1305"""
    try:
        if not current_user or not organization_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view organizations for this user")
            
        result = await organization_service.get_user_organizations(user_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "organizations": [org.dict() for org in result.data],
            "count": len(result.data),
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user organizations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user organizations: {str(e)}")