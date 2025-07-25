"""
Subscription Repository Implementation

订阅数据仓库实现
负责所有订阅相关的数据库操作
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from ..models import Subscription, SubscriptionStatus, StripeSubscriptionStatus
from .base import BaseRepository
from .exceptions import (
    SubscriptionNotFoundException,
    DuplicateEntryException,
    RepositoryException
)

logger = logging.getLogger(__name__)


class SubscriptionRepository(BaseRepository[Subscription]):
    """订阅数据仓库"""
    
    def __init__(self):
        super().__init__('subscriptions')
    
    async def create(self, data: Dict[str, Any]) -> Optional[Subscription]:
        """
        创建新订阅
        
        Args:
            data: 订阅数据
            
        Returns:
            创建的订阅对象
            
        Raises:
            RepositoryException: 创建失败
        """
        try:
            # 准备数据
            subscription_data = self._prepare_subscription_data(data)
            subscription_data = self._prepare_timestamps(subscription_data)
            
            # 执行创建
            result = await self._execute_query(
                lambda: self.table.insert(subscription_data).execute(),
                "Failed to create subscription"
            )
            
            if result.data:
                logger.info(f"Subscription created successfully for user: {subscription_data['user_id']}")
                return Subscription(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise RepositoryException(f"Failed to create subscription: {e}")
    
    async def get_by_id(self, subscription_id: int) -> Optional[Subscription]:
        """
        根据订阅ID获取订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            订阅对象或None
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('id', subscription_id).single().execute(),
                f"Failed to get subscription by id: {subscription_id}"
            )
            
            data = self._handle_single_result(result)
            return Subscription(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting subscription by id {subscription_id}: {e}")
            return None
    
    async def get_by_user_id(self, user_id: str) -> Optional[Subscription]:
        """
        根据用户ID获取活跃订阅
        
        Args:
            user_id: 用户ID
            
        Returns:
            订阅对象或None
        """
        try:
            result = self.table.select('*').eq('user_id', user_id).eq('status', 'active').execute()
            
            if result.data and len(result.data) > 0:
                return Subscription(**result.data[0])
            return None
            
        except Exception as e:
            logger.debug(f"Subscription not found by user_id {user_id}: {e}")
            return None
    
    async def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        """
        根据Stripe订阅ID获取订阅
        
        Args:
            stripe_subscription_id: Stripe订阅ID
            
        Returns:
            订阅对象或None
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('stripe_subscription_id', stripe_subscription_id).single().execute(),
                f"Failed to get subscription by stripe_subscription_id: {stripe_subscription_id}"
            )
            
            data = self._handle_single_result(result)
            return Subscription(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting subscription by stripe_subscription_id {stripe_subscription_id}: {e}")
            return None
    
    async def get_all_by_user_id(self, user_id: str) -> List[Subscription]:
        """
        获取用户的所有订阅（包括历史订阅）
        
        Args:
            user_id: 用户ID
            
        Returns:
            订阅列表
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('user_id', user_id).order('created_at', desc=True).execute(),
                f"Failed to get all subscriptions by user_id: {user_id}"
            )
            
            data_list = self._handle_list_result(result)
            return [Subscription(**data) for data in data_list]
            
        except Exception as e:
            logger.error(f"Error getting all subscriptions by user_id {user_id}: {e}")
            return []
    
    async def update(self, subscription_id: int, data: Dict[str, Any]) -> bool:
        """
        更新订阅信息
        
        Args:
            subscription_id: 订阅ID
            data: 更新数据
            
        Returns:
            是否更新成功
        """
        try:
            update_data = self._prepare_timestamps(data.copy(), is_update=True)
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('id', subscription_id).execute(),
                f"Failed to update subscription: {subscription_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Subscription updated successfully: {subscription_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating subscription {subscription_id}: {e}")
            return False
    
    async def update_by_stripe_id(self, stripe_subscription_id: str, data: Dict[str, Any]) -> bool:
        """
        根据Stripe订阅ID更新订阅
        
        Args:
            stripe_subscription_id: Stripe订阅ID
            data: 更新数据
            
        Returns:
            是否更新成功
        """
        try:
            update_data = self._prepare_timestamps(data.copy(), is_update=True)
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('stripe_subscription_id', stripe_subscription_id).execute(),
                f"Failed to update subscription by stripe_id: {stripe_subscription_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Subscription updated successfully by stripe_id: {stripe_subscription_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating subscription by stripe_id {stripe_subscription_id}: {e}")
            return False
    
    async def delete(self, subscription_id: int) -> bool:
        """
        删除订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            是否删除成功
        """
        try:
            result = await self._execute_query(
                lambda: self.table.delete().eq('id', subscription_id).execute(),
                f"Failed to delete subscription: {subscription_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Subscription deleted successfully: {subscription_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting subscription {subscription_id}: {e}")
            return False
    
    async def cancel_subscription(self, subscription_id: int, immediate: bool = False) -> bool:
        """
        取消订阅
        
        Args:
            subscription_id: 订阅ID
            immediate: 是否立即取消
            
        Returns:
            是否取消成功
        """
        update_data = {
            'canceled_at': datetime.utcnow().isoformat()
        }
        
        if immediate:
            update_data['status'] = 'canceled'
        else:
            update_data['downgrade_at_period_end'] = True
        
        return await self.update(subscription_id, update_data)
    
    async def activate_subscription(self, subscription_id: int) -> bool:
        """
        激活订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            是否激活成功
        """
        return await self.update(subscription_id, {'status': 'active'})
    
    async def get_expiring_subscriptions(self, days_ahead: int = 7) -> List[Subscription]:
        """
        获取即将到期的订阅
        
        Args:
            days_ahead: 提前天数
            
        Returns:
            即将到期的订阅列表
        """
        try:
            expire_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat()
            
            result = await self._execute_query(
                lambda: self.table.select('*').eq('status', 'active').lte('current_period_end', expire_date).execute(),
                "Failed to get expiring subscriptions"
            )
            
            data_list = self._handle_list_result(result)
            return [Subscription(**data) for data in data_list]
            
        except Exception as e:
            logger.error(f"Error getting expiring subscriptions: {e}")
            return []
    
    async def get_active_subscriptions_by_plan(self, plan_type: str) -> List[Subscription]:
        """
        根据计划类型获取活跃订阅
        
        Args:
            plan_type: 计划类型
            
        Returns:
            订阅列表
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('status', 'active').eq('plan_type', plan_type).execute(),
                f"Failed to get active subscriptions by plan: {plan_type}"
            )
            
            data_list = self._handle_list_result(result)
            return [Subscription(**data) for data in data_list]
            
        except Exception as e:
            logger.error(f"Error getting active subscriptions by plan {plan_type}: {e}")
            return []
    
    async def create_default_free_subscription(self, user_id: str) -> Optional[Subscription]:
        """
        为用户创建默认的免费订阅
        
        Args:
            user_id: 用户ID
            
        Returns:
            创建的订阅对象
        """
        now = datetime.utcnow()
        subscription_data = {
            'user_id': user_id,
            'subscription_scope': 'global',
            'plan_type': SubscriptionStatus.FREE.value,
            'status': 'active',
            'credits_included': 1000,
            'current_period_start': now,
            'current_period_end': now + timedelta(days=30),
            'downgrade_at_period_end': False
        }
        
        return await self.create(subscription_data)
    
    def _prepare_subscription_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备订阅数据，设置默认值
        
        Args:
            data: 原始数据
            
        Returns:
            处理后的订阅数据
        """
        subscription_data = data.copy()
        
        # 设置默认值
        subscription_data.setdefault('subscription_scope', 'global')
        subscription_data.setdefault('status', 'active')
        subscription_data.setdefault('plan_type', SubscriptionStatus.FREE.value)
        subscription_data.setdefault('credits_included', 0)
        subscription_data.setdefault('downgrade_at_period_end', False)
        
        # 处理时间戳字段
        now = datetime.utcnow()
        if 'current_period_start' in subscription_data and isinstance(subscription_data['current_period_start'], datetime):
            subscription_data['current_period_start'] = subscription_data['current_period_start'].isoformat()
        if 'current_period_end' in subscription_data and isinstance(subscription_data['current_period_end'], datetime):
            subscription_data['current_period_end'] = subscription_data['current_period_end'].isoformat()
        
        return subscription_data