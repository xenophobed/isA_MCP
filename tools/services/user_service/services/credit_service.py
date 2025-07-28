"""
Credit Service Implementation

Handles business logic for credit transactions and balance management
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import uuid

from ..models import CreditTransaction, CreditTransactionCreate
from ..repositories.credit_repository import CreditRepository
from ..repositories.user_repository import UserRepository
from .base import BaseService, ServiceResult

logger = logging.getLogger(__name__)


class CreditService(BaseService):
    """Credit transaction management service"""
    
    def __init__(self):
        super().__init__("CreditService")
        self.credit_repo = CreditRepository()
        self.user_repo = UserRepository()
    
    async def consume_credits(
        self,
        user_id: str,
        amount: float,
        description: Optional[str] = None,
        usage_record_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceResult[CreditTransaction]:
        """
        Consume user credits
        
        Args:
            user_id: User ID
            amount: Credits to consume
            description: Transaction description
            usage_record_id: Associated usage record ID
            metadata: Transaction metadata
            
        Returns:
            ServiceResult with credit transaction
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get current balance
            current_balance = await self.credit_repo.calculate_current_balance(user_id)
            
            # Check if user has enough credits
            if current_balance < amount:
                return ServiceResult.error(
                    f"Insufficient credits. Available: {current_balance}, Required: {amount}"
                )
            
            # Calculate new balance
            new_balance = current_balance - amount
            
            # Create transaction record
            transaction_data = {
                'user_id': user_id,
                'transaction_type': 'consume',
                'credits_amount': amount,
                'credits_before': current_balance,
                'credits_after': new_balance,
                'usage_record_id': usage_record_id,
                'description': description or f"Credits consumed: {amount}",
                'metadata': metadata or {}
            }
            
            transaction = await self.credit_repo.create_transaction(transaction_data)
            
            if not transaction:
                return ServiceResult.error("Failed to create credit transaction")
            
            # Update user's credit balance
            await self.user_repo.update_credits(user_id, new_balance)
            
            logger.info(f"Credits consumed for user {user_id}: {amount} (balance: {new_balance})")
            return ServiceResult.success(transaction, f"Consumed {amount} credits successfully")
            
        except Exception as e:
            logger.error(f"Error consuming credits: {e}")
            return ServiceResult.error(f"Failed to consume credits: {str(e)}")
    
    async def recharge_credits(
        self,
        user_id: str,
        amount: float,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceResult[CreditTransaction]:
        """
        Recharge user credits
        
        Args:
            user_id: User ID
            amount: Credits to add
            description: Transaction description
            reference_id: Reference ID (e.g., payment ID)
            metadata: Transaction metadata
            
        Returns:
            ServiceResult with credit transaction
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get current balance
            current_balance = await self.credit_repo.calculate_current_balance(user_id)
            
            # Calculate new balance
            new_balance = current_balance + amount
            
            # Create transaction record
            transaction_data = {
                'user_id': user_id,
                'transaction_type': 'recharge',
                'credits_amount': amount,
                'credits_before': current_balance,
                'credits_after': new_balance,
                'description': description or f"Credits recharged: {amount}",
                'metadata': metadata or {}
            }
            
            transaction = await self.credit_repo.create_transaction(transaction_data)
            
            if not transaction:
                return ServiceResult.error("Failed to create credit transaction")
            
            # Update user's credit balance
            await self.user_repo.update_credits(user_id, new_balance)
            
            logger.info(f"Credits recharged for user {user_id}: {amount} (balance: {new_balance})")
            return ServiceResult.success(transaction, f"Recharged {amount} credits successfully")
            
        except Exception as e:
            logger.error(f"Error recharging credits: {e}")
            return ServiceResult.error(f"Failed to recharge credits: {str(e)}")
    
    async def refund_credits(
        self,
        user_id: str,
        amount: float,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceResult[CreditTransaction]:
        """
        Refund user credits
        
        Args:
            user_id: User ID
            amount: Credits to refund
            description: Transaction description
            reference_id: Reference ID
            metadata: Transaction metadata
            
        Returns:
            ServiceResult with credit transaction
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get current balance
            current_balance = await self.credit_repo.calculate_current_balance(user_id)
            
            # Calculate new balance
            new_balance = current_balance + amount
            
            # Create transaction record
            transaction_data = {
                'user_id': user_id,
                'transaction_type': 'refund',
                'credits_amount': amount,
                'credits_before': current_balance,
                'credits_after': new_balance,
                'description': description or f"Credits refunded: {amount}",
                'metadata': metadata or {}
            }
            
            transaction = await self.credit_repo.create_transaction(transaction_data)
            
            if not transaction:
                return ServiceResult.error("Failed to create credit transaction")
            
            # Update user's credit balance
            await self.user_repo.update_credits(user_id, new_balance)
            
            logger.info(f"Credits refunded for user {user_id}: {amount} (balance: {new_balance})")
            return ServiceResult.success(transaction, f"Refunded {amount} credits successfully")
            
        except Exception as e:
            logger.error(f"Error refunding credits: {e}")
            return ServiceResult.error(f"Failed to refund credits: {str(e)}")
    
    async def get_credit_balance(self, user_id: str) -> ServiceResult[float]:
        """
        Get user credit balance
        
        Args:
            user_id: User ID
            
        Returns:
            ServiceResult with credit balance
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get current balance
            balance = await self.credit_repo.calculate_current_balance(user_id)
            
            return ServiceResult.success(balance, "Credit balance retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error getting credit balance for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get credit balance: {str(e)}")
    
    async def get_transaction_history(
        self,
        user_id: str,
        transaction_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ServiceResult[List[CreditTransaction]]:
        """
        Get user transaction history
        
        Args:
            user_id: User ID
            transaction_type: Filter by transaction type
            limit: Record limit
            offset: Record offset
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            ServiceResult with transaction list
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get transactions
            transactions = await self.credit_repo.get_user_transactions(
                user_id=user_id,
                transaction_type=transaction_type,
                limit=limit,
                offset=offset,
                start_date=start_date,
                end_date=end_date
            )
            
            return ServiceResult.success(transactions, f"Retrieved {len(transactions)} transactions")
            
        except Exception as e:
            logger.error(f"Error getting transaction history for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get transaction history: {str(e)}")
    
    async def get_transaction_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """
        Get transaction summary for user
        
        Args:
            user_id: User ID
            start_date: Start date for summary
            end_date: End date for summary
            
        Returns:
            ServiceResult with transaction summary
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get summary
            summary = await self.credit_repo.get_transaction_summary(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            return ServiceResult.success(summary, "Transaction summary retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error getting transaction summary for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get transaction summary: {str(e)}")
    
    async def get_recent_transactions(self, user_id: str, hours: int = 24) -> ServiceResult[List[CreditTransaction]]:
        """
        Get recent transactions
        
        Args:
            user_id: User ID
            hours: Hours back to look
            
        Returns:
            ServiceResult with recent transactions
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get recent transactions
            transactions = await self.credit_repo.get_recent_transactions(user_id, hours)
            
            return ServiceResult.success(
                transactions,
                f"Retrieved {len(transactions)} recent transactions"
            )
            
        except Exception as e:
            logger.error(f"Error getting recent transactions for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get recent transactions: {str(e)}")
    
    async def get_transaction_by_id(self, transaction_id: str) -> ServiceResult[CreditTransaction]:
        """
        Get transaction by ID
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            ServiceResult with transaction
        """
        try:
            transaction = await self.credit_repo.get_transaction_by_id(transaction_id)
            
            if not transaction:
                return ServiceResult.not_found(f"Transaction not found: {transaction_id}")
            
            return ServiceResult.success(transaction, "Transaction retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error getting transaction {transaction_id}: {e}")
            return ServiceResult.error(f"Failed to get transaction: {str(e)}")
    
    async def create_transaction(self, transaction_data: CreditTransactionCreate) -> ServiceResult[CreditTransaction]:
        """
        Create custom credit transaction
        
        Args:
            transaction_data: Transaction creation data
            
        Returns:
            ServiceResult with created transaction
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(transaction_data.user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {transaction_data.user_id}")
            
            # Get current balance
            current_balance = await self.credit_repo.calculate_current_balance(transaction_data.user_id)
            
            # Calculate new balance based on transaction type
            if transaction_data.transaction_type == 'consume':
                if current_balance < transaction_data.amount:
                    return ServiceResult.error("Insufficient credits for consumption")
                new_balance = current_balance - transaction_data.amount
            elif transaction_data.transaction_type in ['recharge', 'refund']:
                new_balance = current_balance + transaction_data.amount
            else:
                return ServiceResult.error(f"Invalid transaction type: {transaction_data.transaction_type}")
            
            # Prepare transaction data
            transaction_dict = transaction_data.model_dump()
            transaction_dict['balance_before'] = current_balance
            transaction_dict['balance_after'] = new_balance
            
            # Create transaction
            transaction = await self.credit_repo.create_transaction(transaction_dict)
            
            if not transaction:
                return ServiceResult.error("Failed to create credit transaction")
            
            # Update user's credit balance
            await self.user_repo.update_credits(transaction_data.user_id, new_balance)
            
            return ServiceResult.success(transaction, "Credit transaction created successfully")
            
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return ServiceResult.error(f"Failed to create transaction: {str(e)}")
    
    async def cleanup_old_transactions(self, days_old: int = 365) -> ServiceResult[int]:
        """
        Clean up old credit transactions
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            ServiceResult with number of deleted transactions
        """
        try:
            deleted_count = await self.credit_repo.delete_old_transactions(days_old)
            
            return ServiceResult.success(
                deleted_count,
                f"Cleaned up {deleted_count} old credit transactions"
            )
            
        except Exception as e:
            logger.error(f"Error cleaning up old transactions: {e}")
            return ServiceResult.error(f"Failed to cleanup old transactions: {str(e)}")