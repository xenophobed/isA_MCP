"""
Session Repository Implementation

Handles all session related database operations
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from ..models import Session, SessionMemory, SessionMessage
from .base import BaseRepository
from .exceptions import RepositoryException

logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository[Session]):
    """Session management repository"""
    
    def __init__(self):
        super().__init__('sessions')
    
    async def create(self, data: Dict[str, Any]) -> Optional[Session]:
        """Implementation of abstract create method"""
        return await self.create_session(data)
    
    async def create_session(self, data: Dict[str, Any]) -> Optional[Session]:
        """
        Create new session
        
        Args:
            data: Session data
            
        Returns:
            Created session object
            
        Raises:
            RepositoryException: Creation failed
        """
        try:
            # Prepare data with timestamps
            session_data = self._prepare_session_data(data)
            session_data = self._prepare_timestamps(session_data)
            
            # Execute creation
            result = await self._execute_query(
                lambda: self.table.insert(session_data).execute(),
                "Failed to create session"
            )
            
            if result.data:
                logger.info(f"Session created: {session_data['session_id']}")
                return Session(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise RepositoryException(f"Failed to create session: {e}")
    
    async def get_by_session_id(self, session_id: str) -> Optional[Session]:
        """
        Get session by session ID
        
        Args:
            session_id: Session ID
            
        Returns:
            Session object or None
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('session_id', session_id).single().execute(),
                f"Failed to get session: {session_id}"
            )
            
            data = self._handle_single_result(result)
            return Session(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    async def get_user_sessions(
        self, 
        user_id: str, 
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """
        Get user sessions
        
        Args:
            user_id: User ID
            active_only: Only return active sessions
            limit: Record limit
            offset: Record offset
            
        Returns:
            List of sessions
        """
        try:
            query = self.table.select('*').eq('user_id', user_id)
            
            if active_only:
                query = query.eq('is_active', True)
            
            query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
            
            result = await self._execute_query(
                lambda: query.execute(),
                f"Failed to get sessions for user: {user_id}"
            )
            
            data_list = self._handle_list_result(result)
            return [Session(**data) for data in data_list]
            
        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            return []
    
    async def update_session_status(self, session_id: str, status: str) -> bool:
        """
        Update session status
        
        Args:
            session_id: Session ID
            status: New status
            
        Returns:
            Success status
        """
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow(),
                'last_activity': datetime.utcnow()
            }
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('session_id', session_id).execute(),
                f"Failed to update session status: {session_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Session status updated: {session_id} -> {status}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating session status {session_id}: {e}")
            return False
    
    async def update_session_activity(self, session_id: str) -> bool:
        """
        Update session last activity timestamp
        
        Args:
            session_id: Session ID
            
        Returns:
            Success status
        """
        try:
            update_data = {
                'last_activity': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('session_id', session_id).execute(),
                f"Failed to update session activity: {session_id}"
            )
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating session activity {session_id}: {e}")
            return False
    
    async def increment_message_count(self, session_id: str, tokens_used: int = 0, cost: float = 0.0) -> bool:
        """
        Increment session message count and update metrics
        
        Args:
            session_id: Session ID
            tokens_used: Tokens used in message
            cost: Cost of message
            
        Returns:
            Success status
        """
        try:
            # Get current values
            session = await self.get_by_session_id(session_id)
            if not session:
                return False
            
            update_data = {
                'message_count': (getattr(session, 'message_count', 0) or 0) + 1,
                'total_tokens': (getattr(session, 'total_tokens', 0) or 0) + tokens_used,
                'total_cost': float((getattr(session, 'total_cost', 0) or 0)) + cost,
                'last_activity': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('session_id', session_id).execute(),
                f"Failed to increment message count: {session_id}"
            )
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error incrementing message count {session_id}: {e}")
            return False
    
    async def expire_old_sessions(self, hours_old: int = 24) -> int:
        """
        Mark old inactive sessions as expired
        
        Args:
            hours_old: Hours threshold for expiration
            
        Returns:
            Number of expired sessions
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)
            
            update_data = {
                'status': 'expired',
                'is_active': False,
                'expires_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('is_active', True).lt('last_activity', cutoff_time.isoformat()).execute(),
                f"Failed to expire old sessions"
            )
            
            expired_count = len(result.data) if result.data else 0
            logger.info(f"Expired {expired_count} old sessions")
            return expired_count
            
        except Exception as e:
            logger.error(f"Error expiring old sessions: {e}")
            return 0
    
    def _prepare_session_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare session data with defaults
        
        Args:
            data: Raw session data
            
        Returns:
            Prepared session data
        """
        session_data = data.copy()
        
        # Set defaults
        session_data.setdefault('status', 'active')
        session_data.setdefault('is_active', True)
        session_data.setdefault('message_count', 0)
        session_data.setdefault('total_tokens', 0)
        session_data.setdefault('total_cost', 0.0)
        session_data.setdefault('conversation_data', {})
        session_data.setdefault('metadata', {})
        session_data.setdefault('session_summary', '')
        
        # Set activity timestamps
        now = datetime.utcnow()
        session_data.setdefault('last_activity', now)
        
        return session_data
    
    async def get_by_id(self, session_id: str) -> Optional[Session]:
        """Implementation of abstract get_by_id method"""
        return await self.get_by_session_id(session_id)
    
    async def update(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Implementation of abstract update method"""
        try:
            update_data = self._prepare_timestamps(data.copy(), is_update=True)
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('session_id', session_id).execute(),
                f"Failed to update session: {session_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Session updated successfully: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    async def delete(self, session_id: str) -> bool:
        """Implementation of abstract delete method"""
        try:
            result = await self._execute_query(
                lambda: self.table.delete().eq('session_id', session_id).execute(),
                f"Failed to delete session: {session_id}"
            )
            
            success = bool(result.data)
            if success:
                logger.info(f"Session deleted successfully: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False


class SessionMemoryRepository(BaseRepository[SessionMemory]):
    """Session memory repository"""
    
    def __init__(self):
        super().__init__('session_memories')
    
    async def create(self, data: Dict[str, Any]) -> Optional[SessionMemory]:
        """Implementation of abstract create method"""
        return await self.create_memory(data)
    
    async def create_memory(self, data: Dict[str, Any]) -> Optional[SessionMemory]:
        """
        Create session memory
        
        Args:
            data: Memory data
            
        Returns:
            Created memory object
        """
        try:
            memory_data = self._prepare_timestamps(data.copy())
            
            result = await self._execute_query(
                lambda: self.table.insert(memory_data).execute(),
                "Failed to create session memory"
            )
            
            if result.data:
                return SessionMemory(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating session memory: {e}")
            raise RepositoryException(f"Failed to create session memory: {e}")
    
    async def get_by_session_id(self, session_id: str) -> Optional[SessionMemory]:
        """
        Get session memory by session ID
        
        Args:
            session_id: Session ID
            
        Returns:
            Session memory or None
        """
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('session_id', session_id).single().execute(),
                f"Failed to get session memory: {session_id}"
            )
            
            data = self._handle_single_result(result)
            return SessionMemory(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting session memory {session_id}: {e}")
            return None
    
    async def update_memory(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session memory
        
        Args:
            session_id: Session ID
            data: Update data
            
        Returns:
            Success status
        """
        try:
            update_data = self._prepare_timestamps(data.copy(), is_update=True)
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('session_id', session_id).execute(),
                f"Failed to update session memory: {session_id}"
            )
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating session memory {session_id}: {e}")
            return False
    
    async def get_by_id(self, memory_id: str) -> Optional[SessionMemory]:
        """Implementation of abstract get_by_id method"""
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('id', memory_id).single().execute(),
                f"Failed to get session memory: {memory_id}"
            )
            
            data = self._handle_single_result(result)
            return SessionMemory(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting session memory {memory_id}: {e}")
            return None
    
    async def update(self, memory_id: str, data: Dict[str, Any]) -> bool:
        """Implementation of abstract update method"""
        try:
            update_data = self._prepare_timestamps(data.copy(), is_update=True)
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('id', memory_id).execute(),
                f"Failed to update session memory: {memory_id}"
            )
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating session memory {memory_id}: {e}")
            return False
    
    async def delete(self, memory_id: str) -> bool:
        """Implementation of abstract delete method"""
        try:
            result = await self._execute_query(
                lambda: self.table.delete().eq('id', memory_id).execute(),
                f"Failed to delete session memory: {memory_id}"
            )
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error deleting session memory {memory_id}: {e}")
            return False


class SessionMessageRepository(BaseRepository[SessionMessage]):
    """Session message repository"""
    
    def __init__(self):
        super().__init__('session_messages')
    
    async def create(self, data: Dict[str, Any]) -> Optional[SessionMessage]:
        """Implementation of abstract create method"""
        return await self.create_message(data)
    
    async def create_message(self, data: Dict[str, Any]) -> Optional[SessionMessage]:
        """
        Create session message
        
        Args:
            data: Message data
            
        Returns:
            Created message object
        """
        try:
            message_data = self._prepare_message_data(data)
            message_data = self._prepare_timestamps(message_data)
            
            result = await self._execute_query(
                lambda: self.table.insert(message_data).execute(),
                "Failed to create session message"
            )
            
            if result.data:
                return SessionMessage(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating session message: {e}")
            raise RepositoryException(f"Failed to create session message: {e}")
    
    async def get_session_messages(
        self, 
        session_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[SessionMessage]:
        """
        Get messages for session
        
        Args:
            session_id: Session ID
            limit: Record limit
            offset: Record offset
            
        Returns:
            List of messages
        """
        try:
            query = self.table.select('*').eq('session_id', session_id)
            query = query.order('created_at', desc=False).range(offset, offset + limit - 1)
            
            result = await self._execute_query(
                lambda: query.execute(),
                f"Failed to get messages for session: {session_id}"
            )
            
            data_list = self._handle_list_result(result)
            return [SessionMessage(**data) for data in data_list]
            
        except Exception as e:
            logger.error(f"Error getting session messages {session_id}: {e}")
            return []
    
    def _prepare_message_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare message data with defaults
        
        Args:
            data: Raw message data
            
        Returns:
            Prepared message data
        """
        message_data = data.copy()
        
        # Set defaults
        message_data.setdefault('message_type', 'chat')
        message_data.setdefault('message_metadata', {})
        message_data.setdefault('tokens_used', 0)
        message_data.setdefault('cost_usd', 0.0)
        message_data.setdefault('is_summary_candidate', True)
        message_data.setdefault('importance_score', 0.5)
        
        return message_data
    
    async def get_by_id(self, message_id: str) -> Optional[SessionMessage]:
        """Implementation of abstract get_by_id method"""
        try:
            result = await self._execute_query(
                lambda: self.table.select('*').eq('id', message_id).single().execute(),
                f"Failed to get session message: {message_id}"
            )
            
            data = self._handle_single_result(result)
            return SessionMessage(**data) if data else None
            
        except Exception as e:
            logger.error(f"Error getting session message {message_id}: {e}")
            return None
    
    async def update(self, message_id: str, data: Dict[str, Any]) -> bool:
        """Implementation of abstract update method"""
        try:
            update_data = self._prepare_timestamps(data.copy(), is_update=True)
            
            result = await self._execute_query(
                lambda: self.table.update(update_data).eq('id', message_id).execute(),
                f"Failed to update session message: {message_id}"
            )
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating session message {message_id}: {e}")
            return False
    
    async def delete(self, message_id: str) -> bool:
        """Implementation of abstract delete method"""
        try:
            result = await self._execute_query(
                lambda: self.table.delete().eq('id', message_id).execute(),
                f"Failed to delete session message: {message_id}"
            )
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error deleting session message {message_id}: {e}")
            return False