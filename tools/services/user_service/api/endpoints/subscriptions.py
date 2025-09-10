"""
Subscription Management Endpoints

Subscription-related functionality extracted from api_server.py
Handles subscription creation and plan management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from models import SubscriptionStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


@router.post("")
async def create_subscription(
    plan_type: str,
    current_user=None,       # Will be injected via dependency
    user_service=None,       # Will be injected via dependency
    subscription_service=None # Will be injected via dependency
):
    """
    Create subscription
    
    Original: api_server.py lines 389-428
    """
    try:
        if not current_user or not user_service or not subscription_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        user_result = await user_service.get_user_by_auth0_id(current_user["sub"])
        if not user_result.is_success or not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data
        
        # 验证计划类型
        try:
            subscription_plan = SubscriptionStatus(plan_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan type: {plan_type}"
            )
        
        if user.id is None:
            raise HTTPException(status_code=500, detail="User ID is missing")
            
        result = await subscription_service.create_subscription(
            user_id=current_user["sub"],
            plan_type=subscription_plan
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.get("/plans")
async def get_subscription_plans(subscription_service=None):
    """
    Get all subscription plans
    
    Original: api_server.py lines 431-445
    """
    try:
        if not subscription_service:
            raise HTTPException(status_code=500, detail="Subscription service not properly injected")
            
        plans_result = subscription_service.get_plan_comparison()
        if not plans_result.is_success:
            raise HTTPException(status_code=500, detail=plans_result.error_message)
        plans = plans_result.data
        return plans
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription plans: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get subscription plans: {str(e)}"
        )