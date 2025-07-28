"""
User Repository Implementation

用户数据仓库实现
负责所有用户相关的数据库操作
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from ..models import User
from .base import BaseRepository
from .exceptions import (
    UserNotFoundException, 
    DuplicateEntryException,
    RepositoryException
)

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """用户数据仓库"""
    
    def __init__(self):
        super().__init__('users')
    
    async def create(self, data: Dict[str, Any]) -> Optional[User]:
        """
        创建新用户
        
        Args:
            data: 用户数据
            
        Returns:
            创建的用户对象
            
        Raises:
            DuplicateEntryException: 用户已存在
            RepositoryException: 创建失败
        """
        try:
            # 检查用户是否已存在
            existing_user = await self.get_by_user_id(data.get('user_id'))
            if existing_user:
                raise DuplicateEntryException(f"User with user_id {data.get('user_id')} already exists")
            
            # 准备数据
            user_data = self._prepare_user_data(data)
            user_data = self._prepare_timestamps(user_data)
            
            # 执行创建
            result = await self._execute_query(
                lambda: self.table.insert(user_data).execute(),
                "Failed to create user"
            )
            
            if result.data:
                logger.info(f"User created successfully: {user_data['user_id']}")
                return User(**result.data[0])
            
            return None
            
        except DuplicateEntryException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise RepositoryException(f"Failed to create user: {e}")
    
    async def get_by_id(self, db_id: int) -> Optional[User]:
        """
        根据数据库ID获取用户
        
        Args:
            db_id: 数据库主键ID
            
        Returns:
            用户对象或None
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('id', db_id).single().execute(),
                f"Failed to get user by id: {db_id}"
            )
            
            data = self._handle_single_result(result)
            return User(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting user by id {db_id}: {e}")
            return None
    
    async def get_by_user_id(self, user_id: str) -> Optional[User]:
        """
        根据用户ID获取用户（业务主键）
        
        Args:
            user_id: 用户ID（Auth0 ID等）
            
        Returns:
            用户对象或None
        """
        try:
            result = self.table.select('*').eq('user_id', user_id).execute()
            
            if result.data and len(result.data) > 0:
                return User(**result.data[0])
            return None
            
        except Exception as e:
            logger.debug(f"User not found by user_id {user_id}: {e}")
            return None
    
    async def get_by_auth0_id(self, auth0_id: str) -> Optional[User]:
        """
        根据Auth0 ID获取用户
        
        Args:
            auth0_id: Auth0用户ID
            
        Returns:
            用户对象或None
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('auth0_id', auth0_id).single().execute(),
                f"Failed to get user by auth0_id: {auth0_id}"
            )
            
            data = self._handle_single_result(result)
            return User(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting user by auth0_id {auth0_id}: {e}")
            return None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户
        
        Args:
            email: 用户邮箱
            
        Returns:
            用户对象或None
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('email', email).single().execute(),
                f"Failed to get user by email: {email}"
            )
            
            data = self._handle_single_result(result)
            return User(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    async def update(self, user_id: str, data: Dict[str, Any]) -> bool:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            data: 更新数据
            
        Returns:
            是否更新成功
        """
        try:
            update_data = self._prepare_timestamps(data.copy(), is_update=True)
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('user_id', user_id).execute(),
                f"Failed to update user: {user_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"User updated successfully: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    async def delete(self, user_id: str) -> bool:
        """
        删除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否删除成功
        """
        try:
            result = await self._execute_query(
                lambda: self.table.delete().eq('user_id', user_id).execute(),
                f"Failed to delete user: {user_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"User deleted successfully: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
    
    async def update_credits(self, user_id: str, credits_remaining: int, credits_total: int = None) -> bool:
        """
        更新用户积分
        
        Args:
            user_id: 用户ID
            credits_remaining: 剩余积分
            credits_total: 总积分（可选）
            
        Returns:
            是否更新成功
        """
        update_data = {'credits_remaining': credits_remaining}
        if credits_total is not None:
            update_data['credits_total'] = credits_total
        
        return await self.update(user_id, update_data)
    
    async def update_subscription_status(self, user_id: str, status: str) -> bool:
        """
        更新用户订阅状态
        
        Args:
            user_id: 用户ID
            status: 订阅状态
            
        Returns:
            是否更新成功
        """
        return await self.update(user_id, {'subscription_status': status})
    
    async def activate_user(self, user_id: str) -> bool:
        """
        激活用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否激活成功
        """
        return await self.update(user_id, {'is_active': True})
    
    async def deactivate_user(self, user_id: str) -> bool:
        """
        停用用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否停用成功
        """
        return await self.update(user_id, {'is_active': False})
    
    async def get_active_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        获取活跃用户列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            用户列表
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('is_active', True).range(offset, offset + limit - 1).execute(),
                "Failed to get active users"
            )
            
            data_list = self._handle_list_result(result)
            return [User(**data) for data in data_list]
            
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def _prepare_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备用户数据，设置默认值
        
        Args:
            data: 原始数据
            
        Returns:
            处理后的用户数据
        """
        user_data = data.copy()
        
        # 设置默认值
        user_data.setdefault('credits_remaining', 1000)
        user_data.setdefault('credits_total', 1000)
        user_data.setdefault('subscription_status', 'free')
        user_data.setdefault('is_active', True)
        user_data.setdefault('shipping_addresses', [])
        user_data.setdefault('payment_methods', [])
        user_data.setdefault('preferences', {})
        
        return user_data
    
    async def ensure_user_exists(self, user_id: str, email: str, name: str, **kwargs) -> User:
        """
        确保用户存在，不存在则创建
        
        Args:
            user_id: 用户业务ID
            email: 用户邮箱
            name: 用户姓名
            **kwargs: 其他用户数据
            
        Returns:
            用户对象
            
        Raises:
            RepositoryException: 操作失败
        """
        try:
            # 先检查用户是否存在
            existing_user = await self.get_by_user_id(user_id)
            if existing_user:
                logger.info(f"User {user_id} already exists, returning existing user")
                return existing_user
            
            # 检查邮箱是否被占用
            existing_email_user = await self.get_by_email(email)
            if existing_email_user:
                # 如果邮箱用户没有auth0_id，并且当前请求有auth0_id，则更新现有用户
                auth0_id = kwargs.get('auth0_id')
                if not existing_email_user.auth0_id and auth0_id:
                    logger.info(f"Updating existing user {existing_email_user.user_id} with auth0_id {auth0_id}")
                    # 只更新auth0_id，保持原有的user_id
                    update_data = {
                        'auth0_id': auth0_id,
                        'name': name  # 更新名称
                    }
                    await self.update(existing_email_user.user_id, update_data)
                    # 重新获取更新后的用户
                    updated_user = await self.get_by_user_id(existing_email_user.user_id)
                    return updated_user
                else:
                    logger.warning(f"Email {email} already exists for different user {existing_email_user.user_id}")
                    raise DuplicateEntryException(f"Email {email} is already registered to a different user")
            
            # 创建新用户
            user_data = {
                'user_id': user_id,
                'email': email,
                'name': name,
                'auth0_id': kwargs.get('auth0_id', user_id),  # 默认auth0_id为user_id
                **kwargs
            }
            
            new_user = await self.create(user_data)
            if not new_user:
                raise RepositoryException("Failed to create user")
            
            logger.info(f"Created new user: {user_id}")
            return new_user
            
        except DuplicateEntryException:
            raise
        except Exception as e:
            logger.error(f"Error ensuring user exists: {e}")
            raise RepositoryException(f"Failed to ensure user exists: {e}")