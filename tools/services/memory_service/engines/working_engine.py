#!/usr/bin/env python3
"""
Working Memory Engine
Specialized engine for working memory management
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import WorkingMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class WorkingMemoryEngine(BaseMemoryEngine):
    """Engine for managing working memories"""
    
    def __init__(self):
        super().__init__()
        self.text_extractor = TextExtractor()
    
    @property
    def table_name(self) -> str:
        return "working_memories"
    
    @property
    def memory_type(self) -> str:
        return "working"
    
    async def store_working_memory(
        self,
        user_id: str,
        dialog_content: str,
        current_task_context: Optional[Dict[str, Any]] = None,
        ttl_seconds: int = 3600,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Store working memories by intelligently extracting task information from dialog
        
        Args:
            user_id: User identifier
            dialog_content: Raw dialog between human and AI containing task information
            current_task_context: Optional existing task context to merge with
            ttl_seconds: Time to live in seconds (default 1 hour)
            importance_score: Manual importance override (0.0-1.0)
        """
        try:
            # Extract working memory information from dialog
            extraction_result = await self._extract_working_memory_info(dialog_content)
            
            if not extraction_result['success']:
                logger.error(f"Failed to extract working memory info: {extraction_result.get('error')}")
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_working_memory",
                    message=f"Failed to extract working memory information: {extraction_result.get('error')}"
                )
            
            extracted_data = extraction_result['data']
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            
            # Merge task context with existing context if provided
            task_context = extracted_data.get('task_context', {})
            if current_task_context:
                task_context.update(current_task_context)
            
            # Create working memory with extracted data
            working_memory = WorkingMemory(
                user_id=user_id,
                content=extracted_data.get('clean_content', dialog_content[:500]),
                task_id=extracted_data.get('task_id', f"task_{datetime.now().timestamp()}"),
                task_context=task_context,
                ttl_seconds=ttl_seconds,
                priority=extracted_data.get('priority', 1),
                expires_at=expires_at,
                importance_score=extracted_data.get('importance_score', importance_score)
            )
            
            # Store the memory
            result = await self.store_memory(working_memory)
            
            if result.success:
                logger.info(f"Stored intelligent working memory: {working_memory.id}")
                logger.info(f"Extracted: task_id={extracted_data.get('task_id')}, "
                          f"priority={extracted_data.get('priority')}, "
                          f"expires_in={ttl_seconds}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to store working memory from dialog: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_working_memory",
                message=f"Failed to store working memory: {str(e)}"
            )
    
    async def search_active_working_memories(self, user_id: str, limit: int = 20) -> List[WorkingMemory]:
        """Search all non-expired working memories"""
        try:
            now = datetime.now().isoformat()
            
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gt('expires_at', now)\
                .order('priority', desc=True)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            memories = []
            for data in result.data or []:
                memory = await self._parse_memory_data(data)
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search active working memories: {e}")
            return []
    
    async def search_working_memories_by_task(self, user_id: str, task_id: str, limit: int = 10) -> List[WorkingMemory]:
        """Search working memories for a specific task"""
        try:
            now = datetime.now().isoformat()
            
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('task_id', f'%{task_id}%')\
                .gt('expires_at', now)\
                .order('priority', desc=True)\
                .limit(limit)\
                .execute()
            
            memories = []
            for data in result.data or []:
                memory = await self._parse_memory_data(data)
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search working memories by task {task_id}: {e}")
            return []
    
    async def extend_memory_ttl(self, memory_id: str, additional_seconds: int) -> MemoryOperationResult:
        """Extend the TTL of a working memory"""
        try:
            memory = await self.get_memory(memory_id)
            if not memory:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="extend_ttl",
                    message="Memory not found"
                )
            
            new_expires_at = memory.expires_at + timedelta(seconds=additional_seconds)
            new_ttl = memory.ttl_seconds + additional_seconds
            
            updates = {
                'expires_at': new_expires_at.isoformat(),
                'ttl_seconds': new_ttl
            }
            
            return await self.update_memory(memory_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to extend memory TTL: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="extend_ttl",
                message=f"Failed to extend TTL: {str(e)}"
            )
    
    async def search_working_memories_by_priority(
        self, 
        user_id: str, 
        min_priority: int = 1,
        limit: int = 10
    ) -> List[WorkingMemory]:
        """Search working memories by priority level"""
        try:
            now = datetime.now().isoformat()
            
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('priority', min_priority)\
                .gt('expires_at', now)\
                .order('priority', desc=True)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            memories = []
            for data in result.data or []:
                memory = await self._parse_memory_data(data)
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search working memories by priority: {e}")
            return []

    async def search_working_memories_by_time_remaining(
        self, 
        user_id: str, 
        max_hours_remaining: float = 1.0,
        limit: int = 10
    ) -> List[WorkingMemory]:
        """Search working memories that expire soon"""
        try:
            now = datetime.now()
            max_expires_at = (now + timedelta(hours=max_hours_remaining)).isoformat()
            
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gt('expires_at', now.isoformat())\
                .lt('expires_at', max_expires_at)\
                .order('expires_at')\
                .limit(limit)\
                .execute()
            
            memories = []
            for data in result.data or []:
                memory = await self._parse_memory_data(data)
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search working memories by time remaining: {e}")
            return []

    async def search_working_memories_by_context_key(
        self, 
        user_id: str, 
        context_key: str,
        limit: int = 10
    ) -> List[WorkingMemory]:
        """Search working memories that contain a specific context key"""
        try:
            now = datetime.now().isoformat()
            
            # Get all active working memories for user and filter by context key
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gt('expires_at', now)\
                .order('priority', desc=True)\
                .execute()
            
            memories = []
            for data in result.data or []:
                memory = await self._parse_memory_data(data)
                if context_key in memory.task_context:
                    memories.append(memory)
                    if len(memories) >= limit:
                        break
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search working memories by context key {context_key}: {e}")
            return []
    
    async def cleanup_expired_memories(self, user_id: Optional[str] = None) -> MemoryOperationResult:
        """Clean up expired working memories"""
        try:
            now = datetime.now().isoformat()
            
            delete_query = self.db.table(self.table_name)\
                .delete()\
                .lt('expires_at', now)
            
            if user_id:
                delete_query = delete_query.eq('user_id', user_id)
            
            result = delete_query.execute()
            
            count = len(result.data) if result.data else 0
            
            return MemoryOperationResult(
                success=True,
                operation="cleanup_expired",
                message=f"Cleaned up {count} expired working memories",
                affected_count=count
            )
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            return MemoryOperationResult(
                success=False,
                operation="cleanup_expired",
                message=f"Failed to cleanup: {str(e)}"
            )
    
    async def update_task_context(
        self, 
        memory_id: str, 
        context_updates: Dict[str, Any]
    ) -> MemoryOperationResult:
        """Update task context for a working memory"""
        try:
            memory = await self.get_memory(memory_id)
            if not memory:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="update_context",
                    message="Memory not found"
                )
            
            # Merge context
            merged_context = memory.task_context.copy()
            merged_context.update(context_updates)
            merged_context['last_updated'] = datetime.now().isoformat()
            
            updates = {'task_context': merged_context}
            
            return await self.update_memory(memory_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to update task context: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="update_context",
                message=f"Failed to update context: {str(e)}"
            )
    
    async def update_task_progress(
        self, 
        memory_id: str, 
        current_step: str,
        progress_percentage: Optional[float] = None,
        next_actions: Optional[List[str]] = None
    ) -> MemoryOperationResult:
        """Update task progress for a working memory"""
        try:
            context_updates = {
                'current_step': current_step,
                'progress_updated_at': datetime.now().isoformat()
            }
            
            if progress_percentage is not None:
                context_updates['progress_percentage'] = max(0.0, min(100.0, progress_percentage))
            
            if next_actions:
                context_updates['next_actions'] = next_actions
            
            return await self.update_task_context(memory_id, context_updates)
            
        except Exception as e:
            logger.error(f"Failed to update task progress: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="update_progress",
                message=f"Failed to update progress: {str(e)}"
            )
    
    async def get_task_summary(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """Get a summary of all working memories for a task"""
        try:
            memories = await self.search_working_memories_by_task(user_id, task_id)
            
            if not memories:
                return {
                    'task_id': task_id,
                    'total_memories': 0,
                    'status': 'no_active_memories',
                    'summary': 'No active working memories found for this task'
                }
            
            # Aggregate information
            total_memories = len(memories)
            highest_priority = max(memory.priority for memory in memories)
            latest_memory = max(memories, key=lambda m: m.created_at)
            
            # Extract common context information
            current_steps = []
            next_actions = []
            blocking_issues = []
            
            for memory in memories:
                if 'current_step' in memory.task_context:
                    current_steps.append(memory.task_context['current_step'])
                if 'next_actions' in memory.task_context:
                    actions = memory.task_context['next_actions']
                    if isinstance(actions, list):
                        next_actions.extend(actions)
                    else:
                        next_actions.append(str(actions))
                if 'blocking_issues' in memory.task_context:
                    issues = memory.task_context['blocking_issues']
                    if isinstance(issues, list):
                        blocking_issues.extend(issues)
                    else:
                        blocking_issues.append(str(issues))
            
            return {
                'task_id': task_id,
                'total_memories': total_memories,
                'highest_priority': highest_priority,
                'latest_update': latest_memory.created_at.isoformat(),
                'current_steps': list(set(current_steps)),
                'next_actions': list(set(next_actions)),
                'blocking_issues': list(set(blocking_issues)),
                'status': 'active',
                'summary': f'Task has {total_memories} active working memories with priority {highest_priority}'
            }
            
        except Exception as e:
            logger.error(f"Failed to get task summary for {task_id}: {e}")
            return {
                'task_id': task_id,
                'error': str(e),
                'status': 'error',
                'summary': f'Failed to retrieve task summary: {str(e)}'
            }
    
    async def _prepare_memory_data(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare working memory data for storage"""
        # Add working-specific fields
        working_fields = [
            'task_id', 'task_context', 'ttl_seconds', 'priority', 'expires_at'
        ]
        
        for field in working_fields:
            if field not in memory_data:
                if field == 'task_context':
                    memory_data[field] = json.dumps({})
                elif field == 'ttl_seconds':
                    memory_data[field] = 3600
                elif field == 'priority':
                    memory_data[field] = 1
                elif field == 'expires_at':
                    memory_data[field] = (datetime.now() + timedelta(hours=1)).isoformat()
                else:
                    memory_data[field] = None
        
        # Handle JSON fields
        if isinstance(memory_data.get('task_context'), dict):
            memory_data['task_context'] = json.dumps(memory_data['task_context'])
        
        # Ensure expires_at is string
        if isinstance(memory_data.get('expires_at'), datetime):
            memory_data['expires_at'] = memory_data['expires_at'].isoformat()
        
        return memory_data
    
    async def _parse_memory_data(self, data: Dict[str, Any]) -> WorkingMemory:
        """Parse working memory data from database"""
        # Parse JSON fields
        if 'embedding' in data and isinstance(data['embedding'], str):
            data['embedding'] = json.loads(data['embedding'])
        if 'context' in data and isinstance(data['context'], str):
            data['context'] = json.loads(data['context'])
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags'])
        if 'task_context' in data and isinstance(data['task_context'], str):
            data['task_context'] = json.loads(data['task_context'])
        
        # Parse datetime
        if 'expires_at' in data and isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        
        return WorkingMemory(**data)
    
    async def _extract_working_memory_info(self, dialog_content: str) -> Dict[str, Any]:
        """Extract structured working memory information from raw dialog"""
        try:
            # Define extraction schema for working memory
            working_schema = {
                "task_id": "Identifier for the current task or objective (e.g., 'data_analysis_project', 'bug_fix_auth', 'meeting_prep')",
                "clean_content": "Clean, concise summary of the current task or working context (2-3 sentences max)",
                "task_context": "Important context information as key-value pairs (current_step, progress, variables, interim_results, next_actions)",
                "priority": "Task priority as integer from 1 (low) to 5 (urgent)",
                "importance_score": "How important this working memory is from 0.0 (trivial) to 1.0 (critical)",
                "current_step": "What step in the process we're currently on",
                "next_actions": "List of immediate next actions or tasks",
                "interim_results": "Any intermediate results or findings so far",
                "blocking_issues": "Any issues or blockers that need to be resolved",
                "time_sensitivity": "How time-sensitive this task is (low/medium/high/urgent)"
            }
            
            # Extract key information using text extractor
            extraction_result = await self.text_extractor.extract_key_information(
                text=dialog_content,
                schema=working_schema
            )
            
            if not extraction_result['success']:
                return extraction_result
            
            extracted_data = extraction_result['data']
            
            # Post-process extracted data
            processed_data = await self._process_working_memory_data(extracted_data, dialog_content)
            
            return {
                'success': True,
                'data': processed_data,
                'confidence': extraction_result.get('confidence', 0.7),
                'billing_info': extraction_result.get('billing_info')
            }
            
        except Exception as e:
            logger.error(f"Working memory information extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0
            }
    
    async def _process_working_memory_data(self, raw_data: Dict[str, Any], original_content: str) -> Dict[str, Any]:
        """Process and validate extracted working memory data"""
        processed = {}
        
        # Task ID processing
        task_id = raw_data.get('task_id', '')
        if not task_id or len(str(task_id).strip()) < 3:
            # Generate a basic task ID if extraction failed
            words = original_content.split()[:3]
            task_id = '_'.join(word.lower().strip('.,!?') for word in words if word.isalnum())
            if not task_id:
                task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        processed['task_id'] = str(task_id).lower().replace(' ', '_')[:50]
        
        # Clean content
        clean_content = raw_data.get('clean_content', '')
        if not clean_content or len(clean_content) < 10:
            # Generate a basic summary if extraction failed
            words = original_content.split()[:30]
            processed['clean_content'] = ' '.join(words) + ('...' if len(words) == 30 else '')
        else:
            processed['clean_content'] = clean_content[:500]  # Limit length
        
        # Priority processing
        try:
            priority_raw = raw_data.get('priority', 1)
            if isinstance(priority_raw, str):
                priority = int(float(priority_raw))  # Handle string floats like "3.5"
            else:
                priority = int(priority_raw)
            processed['priority'] = max(1, min(5, priority))  # Clamp between 1-5
        except (ValueError, TypeError):
            processed['priority'] = 1
        
        # Importance score processing
        try:
            importance_score = float(raw_data.get('importance_score', 0.5))
            processed['importance_score'] = max(0.0, min(1.0, importance_score))
        except (ValueError, TypeError):
            processed['importance_score'] = 0.5
        
        # Task context processing
        task_context = {}
        
        # Add specific context fields
        context_fields = ['current_step', 'next_actions', 'interim_results', 'blocking_issues', 'time_sensitivity']
        for field in context_fields:
            value = raw_data.get(field)
            if value:
                task_context[field] = value
        
        # Add general task context if provided
        general_context = raw_data.get('task_context', {})
        if isinstance(general_context, dict):
            task_context.update(general_context)
        
        # Add extraction metadata
        task_context['extraction_timestamp'] = datetime.now().isoformat()
        task_context['source'] = 'intelligent_extraction'
        
        processed['task_context'] = task_context
        
        return processed