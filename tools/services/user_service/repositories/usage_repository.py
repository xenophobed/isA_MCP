"""
Usage Repository Implementation

Handles all user usage record related database operations
"""


import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from models.schemas.user_models import UsageRecord, UsageStatistics
from repositories.base import BaseRepository
from repositories.exceptions import RepositoryException

logger = logging.getLogger(__name__)


class UsageRepository(BaseRepository[UsageRecord]):
    """User usage records repository"""
    
    def __init__(self):
        super().__init__('user_usage_records')
    
    async def create(self, data: Dict[str, Any]) -> Optional[UsageRecord]:
        """Implementation of abstract create method"""
        return await self.create_usage_record(data)
    
    async def create_usage_record(self, data: Dict[str, Any]) -> Optional[UsageRecord]:
        """
        Create new usage record
        
        Args:
            data: Usage record data
            
        Returns:
            Created usage record object
            
        Raises:
            RepositoryException: Creation failed
        """
        try:
            # Prepare data with timestamps
            usage_data = self._prepare_timestamps(data.copy())
            
            # Execute creation
            result = await self._execute_query(
                lambda: self.table.insert(usage_data).execute(),
                "Failed to create usage record"
            )
            
            if result.data:
                logger.info(f"Usage record created for user: {usage_data['user_id']}")
                return UsageRecord(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating usage record: {e}")
            raise RepositoryException(f"Failed to create usage record: {e}")
    
    async def get_user_usage_history(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[UsageRecord]:
        """
        Get user usage history
        
        Args:
            user_id: User ID
            limit: Record limit
            offset: Record offset
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of usage records
        """
        try:
            query = self.table.select('*').eq('user_id', user_id)
            
            # Add date filters if provided
            if start_date:
                query = query.gte('created_at', start_date.isoformat())
            if end_date:
                query = query.lte('created_at', end_date.isoformat())
            
            # Add ordering and pagination
            query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
            
            result = await self._execute_query(
                lambda: query.execute(),
                f"Failed to get usage history for user: {user_id}"
            )
            
            data_list = self._handle_list_result(result)
            return [UsageRecord(**data) for data in data_list]
            
        except Exception as e:
            logger.error(f"Error getting usage history for user {user_id}: {e}")
            return []
    
    async def get_usage_statistics(
        self, 
        user_id: str, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> UsageStatistics:
        """
        Get usage statistics for user
        
        Args:
            user_id: User ID
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Usage statistics object
        """
        try:
            # Build base query
            query = self.table.select('*').eq('user_id', user_id)
            
            # Add date filters
            if start_date:
                query = query.gte('created_at', start_date.isoformat())
            if end_date:
                query = query.lte('created_at', end_date.isoformat())
            
            # Execute query
            result = await self._execute_query(
                lambda: query.execute(),
                f"Failed to get usage statistics for user: {user_id}"
            )
            
            records = self._handle_list_result(result)
            
            # Calculate statistics
            return self._calculate_statistics(records, start_date, end_date)
            
        except Exception as e:
            logger.error(f"Error getting usage statistics for user {user_id}: {e}")
            return UsageStatistics(
                total_records=0,
                total_credits_charged=0.0,
                total_cost_usd=0.0,
                total_tokens_used=0,
                by_event_type={},
                by_model={},
                by_provider={},
                date_range={}
            )
    
    async def get_total_usage_by_type(self, user_id: str, event_type: str) -> Dict[str, Any]:
        """
        Get total usage by event type
        
        Args:
            user_id: User ID
            event_type: Event type filter
            
        Returns:
            Usage totals
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('user_id', user_id).eq('event_type', event_type).execute(),
                f"Failed to get usage by type for user: {user_id}"
            )
            
            records = self._handle_list_result(result)
            
            total_credits = sum(float(record.get('credits_charged', 0)) for record in records)
            total_cost = sum(float(record.get('cost_usd', 0)) for record in records)
            total_tokens = sum(int(record.get('tokens_used', 0)) for record in records)
            
            return {
                'total_records': len(records),
                'total_credits_charged': total_credits,
                'total_cost_usd': total_cost,
                'total_tokens_used': total_tokens
            }
            
        except Exception as e:
            logger.error(f"Error getting usage by type for user {user_id}: {e}")
            return {
                'total_records': 0,
                'total_credits_charged': 0.0,
                'total_cost_usd': 0.0,
                'total_tokens_used': 0
            }
    
    async def get_recent_usage(self, user_id: str, hours: int = 24) -> List[UsageRecord]:
        """
        Get recent usage records
        
        Args:
            user_id: User ID
            hours: Hours back to look
            
        Returns:
            List of recent usage records
        """
        start_date = datetime.utcnow() - timedelta(hours=hours)
        return await self.get_user_usage_history(
            user_id=user_id,
            start_date=start_date,
            limit=100
        )
    
    async def delete_old_records(self, days_old: int = 90) -> int:
        """
        Delete old usage records
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of deleted records
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await self._execute_query(
                lambda: self.table.delete().lt('created_at', cutoff_date.isoformat()).execute(),
                f"Failed to delete records older than {days_old} days"
            )
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"Deleted {deleted_count} old usage records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting old records: {e}")
            return 0
    
    async def get_by_id(self, record_id: int) -> Optional[UsageRecord]:
        """Implementation of abstract get_by_id method"""
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('id', record_id).single().execute(),
                f"Failed to get usage record by id: {record_id}"
            )
            
            data = self._handle_single_result(result)
            return UsageRecord(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting usage record by id {record_id}: {e}")
            return None
    
    async def update(self, record_id: int, data: Dict[str, Any]) -> bool:
        """Implementation of abstract update method"""
        try:
            update_data = self._prepare_timestamps(data.copy(), is_update=True)
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('id', record_id).execute(),
                f"Failed to update usage record: {record_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Usage record updated successfully: {record_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating usage record {record_id}: {e}")
            return False
    
    async def delete(self, record_id: int) -> bool:
        """Implementation of abstract delete method"""
        try:
            result = await self._execute_query(
                lambda: self.table.delete().eq('id', record_id).execute(),
                f"Failed to delete usage record: {record_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Usage record deleted successfully: {record_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting usage record {record_id}: {e}")
            return False
    
    def _calculate_statistics(
        self, 
        records: List[Dict[str, Any]], 
        start_date: Optional[datetime], 
        end_date: Optional[datetime]
    ) -> UsageStatistics:
        """
        Calculate usage statistics from records
        
        Args:
            records: List of usage records
            start_date: Start date
            end_date: End date
            
        Returns:
            Calculated statistics
        """
        if not records:
            return UsageStatistics(
                total_records=0,
                total_credits_charged=0.0,
                total_cost_usd=0.0,
                total_tokens_used=0,
                by_event_type={},
                by_model={},
                by_provider={},
                date_range={}
            )
        
        # Calculate totals
        total_credits = sum(float(record.get('credits_charged', 0)) for record in records)
        total_cost = sum(float(record.get('cost_usd', 0)) for record in records)
        total_tokens = sum(int(record.get('tokens_used', 0)) for record in records)
        
        # Group by event type
        by_event_type = {}
        for record in records:
            event_type = record.get('event_type', 'unknown')
            by_event_type[event_type] = by_event_type.get(event_type, 0) + 1
        
        # Group by model
        by_model = {}
        for record in records:
            model = record.get('model_name', 'unknown')
            if model and model != 'unknown':
                by_model[model] = by_model.get(model, 0) + 1
        
        # Group by provider
        by_provider = {}
        for record in records:
            provider = record.get('provider', 'unknown')
            if provider and provider != 'unknown':
                by_provider[provider] = by_provider.get(provider, 0) + 1
        
        # Date range
        date_range = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        return UsageStatistics(
            total_records=len(records),
            total_credits_charged=total_credits,
            total_cost_usd=total_cost,
            total_tokens_used=total_tokens,
            by_event_type=by_event_type,
            by_model=by_model,
            by_provider=by_provider,
            date_range=date_range
        )