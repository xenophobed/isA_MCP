#!/usr/bin/env python3
"""
Working Memory Engine
Simple, clean implementation for working memory management
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import WorkingMemory, MemoryOperationResult

logger = get_logger(__name__)


class WorkingMemoryEngine(BaseMemoryEngine):
    """Simple engine for managing working memories"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def table_name(self) -> str:
        return "working_memories"
    
    @property
    def memory_type(self) -> str:
        return "working"
    
    async def store_working_memory(
        self,
        user_id: str,
        content: str,
        priority: str = "medium",
        expires_at: datetime = None
    ) -> MemoryOperationResult:
        """
        Store working memory directly (no extraction needed)
        
        Simple workflow: WorkingMemory → base.store_memory
        """
        try:
            # Working memories are typically short-term, so set expiry
            if expires_at is None:
                expires_at = datetime.now() + timedelta(hours=24)  # Default 24 hours
            
            # Convert priority string to int for model (DB constraint: 1-5)
            priority_map = {"low": 1, "medium": 3, "high": 5}
            priority_int = priority_map.get(priority, 3)
            
            # Create WorkingMemory object with proper model fields
            working_memory = WorkingMemory(
                user_id=user_id,
                content=content,  # model需要但DB没有
                task_id=f"task_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",  # 生成task_id
                task_context={"content": content, "created": datetime.now().isoformat()},  # 将content包装到context中
                priority=priority_int,  # model要求int
                ttl_seconds=int((expires_at - datetime.now()).total_seconds()),
                expires_at=expires_at,
                confidence=0.8,  # model需要但DB没有
                importance_score=0.5  # model需要但DB没有
            )
            
            # Let base engine handle embedding and storage
            result = await self.store_memory(working_memory)
            
            if result.success:
                logger.info(f"✅ Stored working memory: {content[:50]}... (expires: {expires_at})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store working memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_working_memory",
                message=f"Failed to store working memory: {str(e)}"
            )

    async def search_active_working_memories(self, user_id: str, limit: int = 10) -> List[WorkingMemory]:
        """Search active working memories that haven't expired using database field is_active"""
        try:
            current_time = datetime.now().isoformat()
            
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('is_active', True)\
                .gt('expires_at', current_time)\
                .order('priority', desc=True)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            memories = []
            for data in result.data or []:
                memory = await self._parse_from_storage(data)
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"❌ Failed to search active working memories: {e}")
            return []

    async def get_active_working_memories(self, user_id: str) -> List[WorkingMemory]:
        """Get active working memories (alias for search_active_working_memories)"""
        return await self.search_active_working_memories(user_id)

    async def complete_working_memory(self, memory_id: str) -> MemoryOperationResult:
        """Mark a working memory as completed using database field is_active"""
        return await self.update_memory(memory_id, {'is_active': False})

    async def cleanup_expired_memories(self, user_id: str) -> int:
        """Clean up expired working memories"""
        try:
            current_time = datetime.now().isoformat()
            
            result = self.db.table(self.table_name)\
                .delete()\
                .eq('user_id', user_id)\
                .lt('expires_at', current_time)\
                .execute()
            
            count = len(result.data) if result.data else 0
            if count > 0:
                logger.info(f"🧹 Cleaned up {count} expired working memories for user {user_id}")
            
            return count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired memories: {e}")
            return 0
    
    # Override base engine methods for working-specific handling
    
    def _customize_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data before storage - handle working-specific fields"""
        # Remove fields that don't exist in database schema
        # DB有：context_type, context_id, state_data, current_step, progress_percentage, 
        #       next_actions, dependencies, blocking_issues, priority, expires_at, is_active
        # DB没有：content, memory_type, tags, confidence, access_count, last_accessed_at, 
        #        importance_score, task_id, task_context, ttl_seconds, context
        fields_to_remove = ['content', 'memory_type', 'tags', 'confidence', 'importance_score', 'ttl_seconds', 'context']
        
        for field in fields_to_remove:
            data.pop(field, None)
        
        # Map model fields to database fields
        if 'task_id' in data:
            data['context_id'] = data.pop('task_id')
        if 'task_context' in data:
            data['state_data'] = data.pop('task_context')
        
        # Set default values for database-specific fields
        if 'context_type' not in data:
            data['context_type'] = 'task'
        if 'context_id' not in data:
            data['context_id'] = 'unknown'
        if 'state_data' not in data:
            data['state_data'] = {}
        if 'current_step' not in data:
            data['current_step'] = 'active'
        if 'progress_percentage' not in data:
            data['progress_percentage'] = 0.0
        if 'next_actions' not in data:
            data['next_actions'] = []
        if 'dependencies' not in data:
            data['dependencies'] = []
        if 'blocking_issues' not in data:
            data['blocking_issues'] = []
        if 'priority' not in data:
            data['priority'] = 3
        if 'is_active' not in data:
            data['is_active'] = True
        
        return data
    
    def _customize_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data after retrieval - add model-required fields"""
        # Map database fields back to model fields
        if 'context_id' in data and 'task_id' not in data:
            data['task_id'] = data['context_id']
        if 'state_data' in data and 'task_context' not in data:
            data['task_context'] = data['state_data']
        
        # Reconstruct content from state_data for model
        if 'content' not in data:
            state_data = data.get('state_data', {})
            if isinstance(state_data, dict) and 'content' in state_data:
                data['content'] = state_data['content']
            else:
                data['content'] = 'Working memory task'
        
        # Calculate ttl_seconds from expires_at for model
        if 'ttl_seconds' not in data and 'expires_at' in data:
            try:
                from datetime import datetime
                expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
                ttl = int((expires_at - datetime.now()).total_seconds())
                data['ttl_seconds'] = max(ttl, 1)  # Ensure at least 1 second
            except:
                data['ttl_seconds'] = 3600  # Default 1 hour
        
        # Add model-required fields with defaults (这些字段不在数据库中但model需要)
        if 'memory_type' not in data:
            data['memory_type'] = 'working'
        if 'tags' not in data:
            data['tags'] = []
        if 'confidence' not in data:
            data['confidence'] = 0.8
        if 'importance_score' not in data:
            data['importance_score'] = 0.5
        
        return data
    
    async def _create_memory_model(self, data: Dict[str, Any]) -> WorkingMemory:
        """Create WorkingMemory model from database data"""
        return WorkingMemory(**data)