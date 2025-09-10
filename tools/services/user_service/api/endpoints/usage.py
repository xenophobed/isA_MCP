"""
Usage Tracking Endpoints

Usage-related functionality extracted from api_server.py
Handles usage records, statistics, and analytics
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from models import UsageRecordCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/users/{user_id}/usage", tags=["Usage Records"])


@router.post("", response_model=Dict[str, Any])
async def create_usage_record(
    user_id: str,
    usage_data: UsageRecordCreate,
    current_user=None,
    usage_service=None
):
    """Create usage record - Original: api_server.py lines 655-683"""
    try:
        if not current_user or not usage_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to create usage records for this user")
            
        result = await usage_service.create_usage_record(
            user_id=user_id,
            endpoint=usage_data.endpoint,
            tokens_used=usage_data.tokens_used,
            request_data=usage_data.request_data,
            response_data=usage_data.response_data,
            session_id=usage_data.session_id,
            cost_usd=usage_data.cost_usd
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "usage_record": result.data.dict(),
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating usage record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create usage record: {str(e)}")


@router.get("", response_model=Dict[str, Any])
async def get_usage_records(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    endpoint: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user=None,
    usage_service=None
):
    """Get usage records - Original: api_server.py lines 684-720"""
    try:
        if not current_user or not usage_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view usage records for this user")
            
        # Parse dates if provided
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
                
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
                
        result = await usage_service.get_usage_records(
            user_id=user_id,
            start_date=start_datetime,
            end_date=end_datetime,
            endpoint=endpoint,
            limit=limit,
            offset=offset
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "usage_records": [record.dict() for record in result.data],
            "count": len(result.data),
            "limit": limit,
            "offset": offset,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "endpoint": endpoint
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage records: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage records: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_usage_statistics(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user=None,
    usage_service=None
):
    """Get usage statistics - Original: api_server.py lines 721-754"""
    try:
        if not current_user or not usage_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view usage statistics for this user")
            
        # Parse dates if provided
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
                
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
                
        result = await usage_service.get_usage_statistics(
            user_id=user_id,
            start_date=start_datetime,
            end_date=end_datetime
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "statistics": result.data,
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage statistics: {str(e)}")