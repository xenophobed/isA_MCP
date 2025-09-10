"""
User Management Endpoints

Core user management functionality extracted from api_server.py
Handles user creation, authentication, and basic user info retrieval
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
import logging
from datetime import datetime
import sys
import os

# Add dependencies for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models.schemas.user_models import UserEnsureRequest, UserResponse
from api.dependencies import get_current_user, get_user_service, CurrentUser, UserServiceDep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.post("/ensure", response_model=Dict[str, Any])
async def ensure_user_exists(
    user_data: UserEnsureRequest,
    current_user: CurrentUser,
    user_service: UserServiceDep
):
    """
    确保用户存在，不存在则创建
    替换传统的 app/api/user/ensure/route.ts
    
    Original: api_server.py lines 301-354
    """
    try:
        if not current_user or not user_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # 验证 JWT token 中的用户ID与请求数据中的auth0_id是否匹配
        token_auth0_id = current_user["sub"]
        request_auth0_id = user_data.auth0_id
        
        if token_auth0_id != request_auth0_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token mismatch: token auth0_id ({token_auth0_id}) does not match request auth0_id ({request_auth0_id})"
            )
        
        # 使用 Auth0 ID 作为 user_id
        result = await user_service.ensure_user_exists(
            user_id=user_data.auth0_id,
            email=user_data.email,
            name=user_data.name,
            auth0_id=user_data.auth0_id
        )
        
        if not result.is_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to ensure user exists: {result.message}"
            )
        
        user = result.data
        return {
            "success": True,
            "user_id": user.id,
            "auth0_id": user.auth0_id,
            "email": user.email,
            "name": user.name,
            "credits": user.credits_remaining,
            "credits_total": user.credits_total,
            "plan": user.subscription_status.value,
            "is_active": user.is_active,
            "created": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring user exists: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ensure user exists: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
    user_service: UserServiceDep
):
    """
    获取当前用户信息
    替换传统的 hooks/useAuth0Supabase.ts
    
    Original: api_server.py lines 357-382
    """
    try:
        if not current_user or not user_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        auth0_id = current_user["sub"]
        user_result = await user_service.get_user_info(auth0_id)
        
        if not user_result.is_success:
            raise HTTPException(
                status_code=404,
                detail=f"User not found: {auth0_id}"
            )
        
        return user_result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user info: {str(e)}"
        )