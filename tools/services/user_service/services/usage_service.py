"""
Usage Service Implementation

Handles business logic for user usage tracking and analytics
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import uuid

from models.schemas.usage_models import UsageRecord, UsageRecordCreate, UsageStatistics
from ..repositories.usage_repository import UsageRepository
from ..repositories.user_repository import UserRepository
from .base import BaseService, ServiceResult

logger = logging.getLogger(__name__)


class UsageService(BaseService):
    """User usage tracking service"""
    
    def __init__(self):
        super().__init__("UsageService")
        self.usage_repo = UsageRepository()
        self.user_repo = UserRepository()
    
    async def record_usage(self, usage_data: UsageRecordCreate) -> ServiceResult[UsageRecord]:
        """
        Record new usage event
        
        Args:
            usage_data: Usage record creation data
            
        Returns:
            ServiceResult with created usage record
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(usage_data.user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {usage_data.user_id}")
            
            # Prepare usage record data
            record_data = usage_data.model_dump()
            record_data['created_at'] = datetime.utcnow()
            
            # Create usage record
            usage_record = await self.usage_repo.create_usage_record(record_data)
            
            if not usage_record:
                return ServiceResult.error("Failed to create usage record")
            
            logger.info(f"Usage recorded for user {usage_data.user_id}: {usage_data.event_type}")
            return ServiceResult.success(usage_record, "Usage recorded successfully")
            
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            return ServiceResult.error(f"Failed to record usage: {str(e)}")
    
    async def get_user_usage_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ServiceResult[List[UsageRecord]]:
        """
        Get user usage history
        
        Args:
            user_id: User ID
            limit: Record limit
            offset: Record offset
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            ServiceResult with usage history list
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get usage history
            usage_records = await self.usage_repo.get_user_usage_history(
                user_id=user_id,
                limit=limit,
                offset=offset,
                start_date=start_date,
                end_date=end_date
            )
            
            return ServiceResult.success(usage_records, f"Retrieved {len(usage_records)} usage records")
            
        except Exception as e:
            logger.error(f"Error getting usage history for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get usage history: {str(e)}")
    
    async def get_usage_statistics(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ServiceResult[UsageStatistics]:
        """
        Get usage statistics for user
        
        Args:
            user_id: User ID
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            ServiceResult with usage statistics
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get usage statistics
            statistics = await self.usage_repo.get_usage_statistics(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            return ServiceResult.success(statistics, "Statistics retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error getting usage statistics for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get usage statistics: {str(e)}")
    
    async def get_usage_by_type(self, user_id: str, event_type: str) -> ServiceResult[Dict[str, Any]]:
        """
        Get usage totals by event type
        
        Args:
            user_id: User ID
            event_type: Event type filter
            
        Returns:
            ServiceResult with usage totals
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get usage by type
            usage_totals = await self.usage_repo.get_total_usage_by_type(user_id, event_type)
            
            return ServiceResult.success(usage_totals, f"Usage totals for {event_type} retrieved")
            
        except Exception as e:
            logger.error(f"Error getting usage by type for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get usage by type: {str(e)}")
    
    async def get_recent_usage(self, user_id: str, hours: int = 24) -> ServiceResult[List[UsageRecord]]:
        """
        Get recent usage records
        
        Args:
            user_id: User ID
            hours: Hours back to look
            
        Returns:
            ServiceResult with recent usage records
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get recent usage
            recent_records = await self.usage_repo.get_recent_usage(user_id, hours)
            
            return ServiceResult.success(
                recent_records, 
                f"Retrieved {len(recent_records)} recent usage records"
            )
            
        except Exception as e:
            logger.error(f"Error getting recent usage for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get recent usage: {str(e)}")
    
    async def record_api_usage(
        self,
        user_id: str,
        endpoint: str,
        tokens_used: int = 0,
        credits_charged: float = 0.0,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        session_id: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None
    ) -> ServiceResult[UsageRecord]:
        """
        Record API usage with simplified parameters
        
        Args:
            user_id: User ID
            endpoint: API endpoint
            tokens_used: Number of tokens used
            credits_charged: Credits charged
            model_name: Model name used
            provider: Service provider
            session_id: Session ID
            request_data: Request data
            response_data: Response data
            
        Returns:
            ServiceResult with created usage record
        """
        usage_data = UsageRecordCreate(
            user_id=user_id,
            session_id=session_id,
            trace_id=str(uuid.uuid4()),
            endpoint=endpoint,
            event_type="api_call",
            credits_charged=credits_charged,
            tokens_used=tokens_used,
            model_name=model_name,
            provider=provider,
            request_data=request_data or {},
            response_data=response_data or {}
        )
        
        return await self.record_usage(usage_data)
    
    async def get_daily_usage_summary(self, user_id: str, days: int = 30) -> ServiceResult[Dict[str, Any]]:
        """
        Get daily usage summary for the last N days
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            ServiceResult with daily usage summary
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get usage records
            usage_records = await self.usage_repo.get_user_usage_history(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=1000  # Get more records for analysis
            )
            
            # Group by day
            daily_summary = {}
            for record in usage_records:
                if record.created_at:
                    day_key = record.created_at.date().isoformat()
                    if day_key not in daily_summary:
                        daily_summary[day_key] = {
                            'total_records': 0,
                            'total_credits': 0.0,
                            'total_tokens': 0,
                            'by_event_type': {}
                        }
                    
                    daily_summary[day_key]['total_records'] += 1
                    daily_summary[day_key]['total_credits'] += record.credits_charged
                    daily_summary[day_key]['total_tokens'] += record.tokens_used or 0
                    
                    event_type = record.event_type
                    if event_type not in daily_summary[day_key]['by_event_type']:
                        daily_summary[day_key]['by_event_type'][event_type] = 0
                    daily_summary[day_key]['by_event_type'][event_type] += 1
            
            return ServiceResult.success(daily_summary, f"Daily summary for {days} days retrieved")
            
        except Exception as e:
            logger.error(f"Error getting daily usage summary for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get daily usage summary: {str(e)}")
    
    async def cleanup_old_records(self, days_old: int = 90) -> ServiceResult[int]:
        """
        Clean up old usage records
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            ServiceResult with number of deleted records
        """
        try:
            deleted_count = await self.usage_repo.delete_old_records(days_old)
            
            return ServiceResult.success(
                deleted_count, 
                f"Cleaned up {deleted_count} old usage records"
            )
            
        except Exception as e:
            logger.error(f"Error cleaning up old records: {e}")
            return ServiceResult.error(f"Failed to cleanup old records: {str(e)}")