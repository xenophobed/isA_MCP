"""
Payment Processing Endpoints

Payment-related functionality extracted from api_server.py
Handles Stripe payment intents and checkout sessions
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post("/create-intent", response_model=Dict[str, Any])
async def create_payment_intent(
    amount: int,
    currency: str = "usd",
    plan_type: Optional[str] = None,
    current_user=None,
    payment_service=None,
    user_service=None
):
    """Create payment intent - Original: api_server.py lines 449-491"""
    try:
        if not current_user or not payment_service or not user_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Get user info
        user_result = await user_service.get_user_by_auth0_id(current_user["sub"])
        if not user_result.is_success or not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        user = user_result.data
        
        # Create payment intent
        intent_result = await payment_service.create_payment_intent(
            amount=amount,
            currency=currency,
            customer_email=user.email,
            metadata={
                "user_id": user.user_id,
                "plan_type": plan_type or "unknown"
            }
        )
        
        if not intent_result.is_success:
            raise HTTPException(status_code=400, detail=intent_result.message)
            
        return {
            "success": True,
            "client_secret": intent_result.data["client_secret"],
            "payment_intent_id": intent_result.data["id"],
            "amount": amount,
            "currency": currency,
            "message": "Payment intent created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create payment intent: {str(e)}")


@router.post("/create-checkout", response_model=Dict[str, Any])
async def create_checkout_session(
    price_id: str,
    success_url: str,
    cancel_url: str,
    current_user=None,
    payment_service=None,
    user_service=None
):
    """Create checkout session - Original: api_server.py lines 492-550"""
    try:
        if not current_user or not payment_service or not user_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Get user info
        user_result = await user_service.get_user_by_auth0_id(current_user["sub"])
        if not user_result.is_success or not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        user = user_result.data
        
        # Create checkout session
        session_result = await payment_service.create_checkout_session(
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=user.email,
            metadata={
                "user_id": user.user_id,
                "auth0_id": current_user["sub"]
            }
        )
        
        if not session_result.is_success:
            raise HTTPException(status_code=400, detail=session_result.message)
            
        return {
            "success": True,
            "checkout_url": session_result.data["url"],
            "session_id": session_result.data["id"],
            "message": "Checkout session created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")