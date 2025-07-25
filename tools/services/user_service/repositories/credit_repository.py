"""
Credit Transaction Repository Implementation

Handles all credit transaction related database operations
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import uuid

from ..models import CreditTransaction
from .base import BaseRepository
from .exceptions import RepositoryException

logger = logging.getLogger(__name__)


class CreditRepository(BaseRepository[CreditTransaction]):
    """Credit transaction repository"""
    
    def __init__(self):
        super().__init__('user_credit_transactions')
    
    async def create(self, data: Dict[str, Any]) -> Optional[CreditTransaction]:
        """Implementation of abstract create method"""
        return await self.create_transaction(data)
    
    async def create_transaction(self, data: Dict[str, Any]) -> Optional[CreditTransaction]:
        """
        Create new credit transaction
        
        Args:
            data: Transaction data
            
        Returns:
            Created transaction object
            
        Raises:
            RepositoryException: Creation failed
        """
        try:
            # Prepare transaction data
            transaction_data = self._prepare_transaction_data(data)
            transaction_data = self._prepare_timestamps(transaction_data)
            
            # Execute creation
            result = await self._execute_query(
                lambda: self.table.insert(transaction_data).execute(),
                "Failed to create credit transaction"
            )
            
            if result.data:
                logger.info(f"Credit transaction created for user: {transaction_data['user_id']}")
                return CreditTransaction(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating credit transaction: {e}")
            raise RepositoryException(f"Failed to create credit transaction: {e}")
    
    async def get_user_transactions(
        self,
        user_id: str,
        transaction_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CreditTransaction]:
        """
        Get user credit transactions
        
        Args:
            user_id: User ID
            transaction_type: Filter by transaction type
            limit: Record limit
            offset: Record offset
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of credit transactions
        """
        try:
            query = self.table.select('*').eq('user_id', user_id)
            
            # Add type filter
            if transaction_type:
                query = query.eq('transaction_type', transaction_type)
            
            # Add date filters
            if start_date:
                query = query.gte('created_at', start_date.isoformat())
            if end_date:
                query = query.lte('created_at', end_date.isoformat())
            
            # Add ordering and pagination
            query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
            
            result = await self._execute_query(
                lambda: query.execute(),
                f"Failed to get transactions for user: {user_id}"
            )
            
            data_list = self._handle_list_result(result)
            return [CreditTransaction(**data) for data in data_list]
            
        except Exception as e:
            logger.error(f"Error getting transactions for user {user_id}: {e}")
            return []
    
    async def get_transaction_by_id(self, transaction_id: str) -> Optional[CreditTransaction]:
        """
        Get transaction by transaction ID
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Transaction object or None
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('transaction_id', transaction_id).single().execute(),
                f"Failed to get transaction: {transaction_id}"
            )
            
            data = self._handle_single_result(result)
            return CreditTransaction(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting transaction {transaction_id}: {e}")
            return None
    
    async def calculate_current_balance(self, user_id: str) -> float:
        """
        Calculate current credit balance for user
        
        Args:
            user_id: User ID
            
        Returns:
            Current credit balance
        """
        try:
            # Get the most recent transaction
            result = await self._execute_query(
                lambda: self.table.select('credits_after').eq('user_id', user_id).order('created_at', desc=True).limit(1).execute(),
                f"Failed to get current balance for user: {user_id}"
            )
            
            if result.data and len(result.data) > 0:
                return float(result.data[0]['credits_after'])
            
            # If no transactions, return 0
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating balance for user {user_id}: {e}")
            return 0.0
    
    async def get_transaction_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get transaction summary for user
        
        Args:
            user_id: User ID
            start_date: Start date for summary
            end_date: End date for summary
            
        Returns:
            Transaction summary
        """
        try:
            query = self.table.select('*').eq('user_id', user_id)
            
            # Add date filters
            if start_date:
                query = query.gte('created_at', start_date.isoformat())
            if end_date:
                query = query.lte('created_at', end_date.isoformat())
            
            result = await self._execute_query(
                lambda: query.execute(),
                f"Failed to get transaction summary for user: {user_id}"
            )
            
            transactions = self._handle_list_result(result)
            
            # Calculate summary
            return self._calculate_transaction_summary(transactions)
            
        except Exception as e:
            logger.error(f"Error getting transaction summary for user {user_id}: {e}")
            return {
                'total_transactions': 0,
                'total_consumed': 0.0,
                'total_recharged': 0.0,
                'total_refunded': 0.0,
                'by_type': {},
                'current_balance': 0.0
            }
    
    async def get_recent_transactions(self, user_id: str, hours: int = 24) -> List[CreditTransaction]:
        """
        Get recent transactions
        
        Args:
            user_id: User ID
            hours: Hours back to look
            
        Returns:
            List of recent transactions
        """
        start_date = datetime.utcnow() - timedelta(hours=hours)
        return await self.get_user_transactions(
            user_id=user_id,
            start_date=start_date,
            limit=100
        )
    
    async def get_transactions_by_usage_record(self, usage_record_id: int) -> List[CreditTransaction]:
        """
        Get transactions associated with usage record
        
        Args:
            usage_record_id: Usage record ID
            
        Returns:
            List of associated transactions
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('usage_record_id', usage_record_id).execute(),
                f"Failed to get transactions for usage record: {usage_record_id}"
            )
            
            data_list = self._handle_list_result(result)
            return [CreditTransaction(**data) for data in data_list]
            
        except Exception as e:
            logger.error(f"Error getting transactions for usage record {usage_record_id}: {e}")
            return []
    
    async def delete_old_transactions(self, days_old: int = 365) -> int:
        """
        Delete old credit transactions
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of deleted transactions
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await self._execute_query(
                lambda: self.table.delete().lt('created_at', cutoff_date.isoformat()).execute(),
                f"Failed to delete transactions older than {days_old} days"
            )
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"Deleted {deleted_count} old credit transactions")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting old transactions: {e}")
            return 0
    
    def _prepare_transaction_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare transaction data with defaults
        
        Args:
            data: Raw transaction data
            
        Returns:
            Prepared transaction data
        """
        transaction_data = data.copy()
        
        # Generate transaction ID if not provided
        if 'transaction_id' not in transaction_data:
            transaction_data['transaction_id'] = str(uuid.uuid4())
        
        # Set defaults
        transaction_data.setdefault('metadata', {})
        transaction_data.setdefault('description', '')
        
        # Map field names to match database schema
        if 'amount' in transaction_data:
            transaction_data['credits_amount'] = transaction_data.pop('amount')
        if 'balance_before' in transaction_data:
            transaction_data['credits_before'] = transaction_data.pop('balance_before')
        if 'balance_after' in transaction_data:
            transaction_data['credits_after'] = transaction_data.pop('balance_after')
        
        return transaction_data
    
    def _calculate_transaction_summary(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate transaction summary from raw data
        
        Args:
            transactions: List of transaction records
            
        Returns:
            Calculated summary
        """
        if not transactions:
            return {
                'total_transactions': 0,
                'total_consumed': 0.0,
                'total_recharged': 0.0,
                'total_refunded': 0.0,
                'by_type': {},
                'current_balance': 0.0
            }
        
        total_consumed = 0.0
        total_recharged = 0.0
        total_refunded = 0.0
        by_type = {}
        
        # Calculate totals by transaction type
        for transaction in transactions:
            t_type = transaction.get('transaction_type', 'unknown')
            amount = float(transaction.get('credits_amount', 0))
            
            # Count by type
            by_type[t_type] = by_type.get(t_type, 0) + 1
            
            # Sum by type
            if t_type == 'consume':
                total_consumed += amount
            elif t_type == 'recharge':
                total_recharged += amount
            elif t_type == 'refund':
                total_refunded += amount
        
        # Get current balance from most recent transaction
        current_balance = 0.0
        if transactions:
            # Transactions are ordered by created_at desc
            current_balance = float(transactions[0].get('credits_after', 0))
        
        return {
            'total_transactions': len(transactions),
            'total_consumed': total_consumed,
            'total_recharged': total_recharged,
            'total_refunded': total_refunded,
            'by_type': by_type,
            'current_balance': current_balance
        }
    
    async def get_by_id(self, transaction_id: str) -> Optional[CreditTransaction]:
        """Implementation of abstract get_by_id method"""
        return await self.get_transaction_by_id(transaction_id)
    
    async def update(self, transaction_id: str, data: Dict[str, Any]) -> bool:
        """Implementation of abstract update method"""
        try:
            update_data = self._prepare_timestamps(data.copy(), is_update=True)
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('transaction_id', transaction_id).execute(),
                f"Failed to update credit transaction: {transaction_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Credit transaction updated successfully: {transaction_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating credit transaction {transaction_id}: {e}")
            return False
    
    async def delete(self, transaction_id: str) -> bool:
        """Implementation of abstract delete method"""
        try:
            result = await self._execute_query(
                lambda: self.table.delete().eq('transaction_id', transaction_id).execute(),
                f"Failed to delete credit transaction: {transaction_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Credit transaction deleted successfully: {transaction_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting credit transaction {transaction_id}: {e}")
            return False