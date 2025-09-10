"""
Credits Management Endpoints

Credit-related functionality extracted from api_server.py
Handles credit consumption, recharge, balance, and transactions
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging
import sys
import os
from datetime import datetime

# Add dependencies for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models.schemas.usage_models import CreditConsumption
from api.dependencies import get_current_user, get_credit_service, CurrentUser, CreditServiceDep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/users/{user_id}/credits", tags=["Credits"])


@router.post("/consume", response_model=Dict[str, Any])
async def consume_credits_v2(
    user_id: str,
    consumption: CreditConsumption,
    current_user: CurrentUser,
    credit_service: CreditServiceDep
):
    """Consume user credits - Original: api_server.py lines 957-998"""
    try:
        if not current_user or not credit_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Verify user authorization
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to consume credits for this user")
        
        # Validate user_id matches URL parameter
        if consumption.user_id != user_id:
            raise HTTPException(status_code=400, detail="user_id in body must match URL parameter")
        
        result = await credit_service.consume_credits(
            user_id=user_id,
            amount=consumption.amount,
            description=consumption.reason or "Credit consumption",
            metadata={"reason": consumption.reason} if consumption.reason else {}
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "remaining_credits": result.data.credits_after,
            "consumed_amount": consumption.amount,
            "message": f"Successfully consumed {consumption.amount} credits"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consuming credits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to consume credits: {str(e)}")


@router.post("/recharge", response_model=Dict[str, Any])
async def recharge_credits(
    user_id: str,
    amount: float,
    description: Optional[str] = None,
    reference_id: Optional[str] = None,
    current_user=None,
    credit_service=None
):
    """Recharge user credits - Original: api_server.py lines 1001-1029"""
    try:
        if not current_user or not credit_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to recharge credits for this user")
            
        result = await credit_service.recharge_credits(
            user_id=user_id,
            amount=amount,
            description=description,
            reference_id=reference_id
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "recharged_amount": amount,
            "new_balance": result.data.credits_after,
            "transaction_id": result.data.transaction_id,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recharging credits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to recharge credits: {str(e)}")


@router.get("/balance", response_model=Dict[str, Any])
async def get_credit_balance(
    user_id: str,
    current_user: CurrentUser,
    credit_service: CreditServiceDep
):
    """Get user credit balance - Original: api_server.py lines 1032-1052"""
    try:
        if not current_user or not credit_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view credits for this user")
            
        result = await credit_service.get_credit_balance(user_id)
        
        if not result.is_success:
            raise HTTPException(status_code=404, detail=result.message)
            
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credit balance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get credit balance: {str(e)}")


@router.get("/transactions", response_model=Dict[str, Any])
async def get_transaction_history(
    user_id: str,
    transaction_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user=None,
    credit_service=None
):
    """Get transaction history - Original: api_server.py lines 1055-1089"""
    try:
        if not current_user or not credit_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view transactions for this user")
            
        result = await credit_service.get_transaction_history(
            user_id=user_id,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "transactions": [t.dict() for t in result.data],
            "total_count": len(result.data),
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transaction history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get transaction history: {str(e)}")