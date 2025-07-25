"""
Session Service Implementation

Handles business logic for session management
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import uuid

from ..models import Session, SessionCreate, SessionMemory, SessionMessage
from ..repositories.session_repository import SessionRepository, SessionMemoryRepository, SessionMessageRepository
from ..repositories.user_repository import UserRepository
from .base import BaseService, ServiceResult

logger = logging.getLogger(__name__)


class SessionService(BaseService):
    """Session management service"""
    
    def __init__(self):
        super().__init__("SessionService")
        self.session_repo = SessionRepository()
        self.memory_repo = SessionMemoryRepository()
        self.message_repo = SessionMessageRepository()
        self.user_repo = UserRepository()
    
    async def create_session(self, session_data: SessionCreate) -> ServiceResult[Session]:
        """
        Create new session
        
        Args:
            session_data: Session creation data
            
        Returns:
            ServiceResult with created session
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(session_data.user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {session_data.user_id}")
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Prepare session data
            session_dict = session_data.model_dump()
            session_dict['session_id'] = session_id
            
            # Create session
            session = await self.session_repo.create_session(session_dict)
            
            if not session:
                return ServiceResult.error("Failed to create session")
            
            logger.info(f"Session created for user {session_data.user_id}: {session_id}")
            return ServiceResult.success(session, "Session created successfully")
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return ServiceResult.error(f"Failed to create session: {str(e)}")
    
    async def get_session(self, session_id: str) -> ServiceResult[Session]:
        """
        Get session by ID
        
        Args:
            session_id: Session ID
            
        Returns:
            ServiceResult with session
        """
        try:
            session = await self.session_repo.get_by_session_id(session_id)
            
            if not session:
                return ServiceResult.not_found(f"Session not found: {session_id}")
            
            return ServiceResult.success(session, "Session retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return ServiceResult.error(f"Failed to get session: {str(e)}")
    
    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> ServiceResult[List[Session]]:
        """
        Get user sessions
        
        Args:
            user_id: User ID
            active_only: Only return active sessions
            limit: Record limit
            offset: Record offset
            
        Returns:
            ServiceResult with session list
        """
        try:
            # Validate user exists
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # Get sessions
            sessions = await self.session_repo.get_user_sessions(
                user_id=user_id,
                active_only=active_only,
                limit=limit,
                offset=offset
            )
            
            return ServiceResult.success(sessions, f"Retrieved {len(sessions)} sessions")
            
        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            return ServiceResult.error(f"Failed to get user sessions: {str(e)}")
    
    async def update_session_status(self, session_id: str, status: str) -> ServiceResult[bool]:
        """
        Update session status
        
        Args:
            session_id: Session ID
            status: New status
            
        Returns:
            ServiceResult with success status
        """
        try:
            # Validate session exists
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                return ServiceResult.not_found(f"Session not found: {session_id}")
            
            # Update status
            success = await self.session_repo.update_session_status(session_id, status)
            
            if not success:
                return ServiceResult.error("Failed to update session status")
            
            return ServiceResult.success(True, f"Session status updated to {status}")
            
        except Exception as e:
            logger.error(f"Error updating session status {session_id}: {e}")
            return ServiceResult.error(f"Failed to update session status: {str(e)}")
    
    async def record_session_activity(self, session_id: str) -> ServiceResult[bool]:
        """
        Record session activity
        
        Args:
            session_id: Session ID
            
        Returns:
            ServiceResult with success status
        """
        try:
            success = await self.session_repo.update_session_activity(session_id)
            
            if not success:
                return ServiceResult.error("Failed to record session activity")
            
            return ServiceResult.success(True, "Session activity recorded")
            
        except Exception as e:
            logger.error(f"Error recording session activity {session_id}: {e}")
            return ServiceResult.error(f"Failed to record session activity: {str(e)}")
    
    async def add_session_message(
        self,
        session_id: str,
        role: str,
        content: str,
        message_type: str = "chat",
        metadata: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0
    ) -> ServiceResult[SessionMessage]:
        """
        Add message to session
        
        Args:
            session_id: Session ID
            role: Message role (user/assistant/system)
            content: Message content
            message_type: Message type
            metadata: Message metadata
            tokens_used: Tokens used
            cost_usd: Cost in USD
            
        Returns:
            ServiceResult with created message
        """
        try:
            # Validate session exists
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                return ServiceResult.not_found(f"Session not found: {session_id}")
            
            # Prepare message data
            message_data = {
                'session_id': session_id,
                'user_id': session.user_id,
                'role': role,
                'content': content,
                'message_type': message_type,
                'message_metadata': metadata or {},
                'tokens_used': tokens_used,
                'cost_usd': cost_usd
            }
            
            # Create message
            message = await self.message_repo.create_message(message_data)
            
            if not message:
                return ServiceResult.error("Failed to create session message")
            
            # Update session metrics
            await self.session_repo.increment_message_count(session_id, tokens_used, cost_usd)
            
            return ServiceResult.success(message, "Message added to session")
            
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            return ServiceResult.error(f"Failed to add session message: {str(e)}")
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> ServiceResult[List[SessionMessage]]:
        """
        Get session messages
        
        Args:
            session_id: Session ID
            limit: Record limit
            offset: Record offset
            
        Returns:
            ServiceResult with message list
        """
        try:
            # Validate session exists
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                return ServiceResult.not_found(f"Session not found: {session_id}")
            
            # Get messages
            messages = await self.message_repo.get_session_messages(
                session_id=session_id,
                limit=limit,
                offset=offset
            )
            
            return ServiceResult.success(messages, f"Retrieved {len(messages)} messages")
            
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return ServiceResult.error(f"Failed to get session messages: {str(e)}")
    
    async def create_session_memory(
        self,
        session_id: str,
        memory_data: Dict[str, Any]
    ) -> ServiceResult[SessionMemory]:
        """
        Create or update session memory
        
        Args:
            session_id: Session ID
            memory_data: Memory data
            
        Returns:
            ServiceResult with session memory
        """
        try:
            # Validate session exists
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                return ServiceResult.not_found(f"Session not found: {session_id}")
            
            # Check if memory already exists
            existing_memory = await self.memory_repo.get_by_session_id(session_id)
            
            if existing_memory:
                # Update existing memory
                success = await self.memory_repo.update_memory(session_id, memory_data)
                if not success:
                    return ServiceResult.error("Failed to update session memory")
                
                # Get updated memory
                updated_memory = await self.memory_repo.get_by_session_id(session_id)
                return ServiceResult.success(updated_memory, "Session memory updated")
            else:
                # Create new memory
                memory_dict = memory_data.copy()
                memory_dict['session_id'] = session_id
                memory_dict['user_id'] = session.user_id
                
                memory = await self.memory_repo.create_memory(memory_dict)
                
                if not memory:
                    return ServiceResult.error("Failed to create session memory")
                
                return ServiceResult.success(memory, "Session memory created")
            
        except Exception as e:
            logger.error(f"Error creating session memory {session_id}: {e}")
            return ServiceResult.error(f"Failed to create session memory: {str(e)}")
    
    async def get_session_memory(self, session_id: str) -> ServiceResult[Optional[SessionMemory]]:
        """
        Get session memory
        
        Args:
            session_id: Session ID
            
        Returns:
            ServiceResult with session memory
        """
        try:
            # Validate session exists
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                return ServiceResult.not_found(f"Session not found: {session_id}")
            
            # Get memory
            memory = await self.memory_repo.get_by_session_id(session_id)
            
            return ServiceResult.success(memory, "Session memory retrieved")
            
        except Exception as e:
            logger.error(f"Error getting session memory {session_id}: {e}")
            return ServiceResult.error(f"Failed to get session memory: {str(e)}")
    
    async def end_session(self, session_id: str) -> ServiceResult[bool]:
        """
        End session (mark as inactive)
        
        Args:
            session_id: Session ID
            
        Returns:
            ServiceResult with success status
        """
        try:
            # Update session status to ended
            result = await self.update_session_status(session_id, "ended")
            
            if not result.is_success:
                return result
            
            # Mark as inactive
            session = await self.session_repo.get_by_session_id(session_id)
            if session:
                await self.session_repo.update_session_status(session_id, "ended")
            
            return ServiceResult.success(True, "Session ended successfully")
            
        except Exception as e:
            logger.error(f"Error ending session {session_id}: {e}")
            return ServiceResult.error(f"Failed to end session: {str(e)}")
    
    async def cleanup_expired_sessions(self, hours_old: int = 24) -> ServiceResult[int]:
        """
        Clean up expired sessions
        
        Args:
            hours_old: Hours threshold for expiration
            
        Returns:
            ServiceResult with number of expired sessions
        """
        try:
            expired_count = await self.session_repo.expire_old_sessions(hours_old)
            
            return ServiceResult.success(
                expired_count,
                f"Expired {expired_count} old sessions"
            )
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return ServiceResult.error(f"Failed to cleanup expired sessions: {str(e)}")
    
    async def get_session_summary(self, session_id: str) -> ServiceResult[Dict[str, Any]]:
        """
        Get session summary with metrics
        
        Args:
            session_id: Session ID
            
        Returns:
            ServiceResult with session summary
        """
        try:
            # Get session
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                return ServiceResult.not_found(f"Session not found: {session_id}")
            
            # Get memory
            memory = await self.memory_repo.get_by_session_id(session_id)
            
            # Get message count
            messages = await self.message_repo.get_session_messages(session_id, limit=1)
            
            summary = {
                'session_id': session_id,
                'user_id': session.user_id,
                'status': session.status,
                'created_at': session.created_at,
                'last_activity': getattr(session, 'last_activity', None),
                'message_count': getattr(session, 'message_count', 0),
                'total_tokens': getattr(session, 'total_tokens', 0),
                'total_cost': float(getattr(session, 'total_cost', 0)),
                'has_memory': memory is not None,
                'is_active': getattr(session, 'is_active', False)
            }
            
            return ServiceResult.success(summary, "Session summary retrieved")
            
        except Exception as e:
            logger.error(f"Error getting session summary {session_id}: {e}")
            return ServiceResult.error(f"Failed to get session summary: {str(e)}")