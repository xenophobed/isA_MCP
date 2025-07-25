#!/usr/bin/env python3
"""
Session Memory Engine
Simple, clean implementation for session memory management
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import SessionMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class SessionMemoryEngine(BaseMemoryEngine):
    """Simple engine for managing session memories"""
    
    def __init__(self):
        super().__init__()
        self.text_extractor = TextExtractor()
    
    @property
    def table_name(self) -> str:
        return "session_memories"
    
    @property
    def memory_type(self) -> str:
        return "session"
    
    async def store_session_memory(
        self,
        user_id: str,
        session_id: str,
        content: str,
        message_count: int = 1
    ) -> MemoryOperationResult:
        """
        Store session memory with optional content extraction
        
        Simple workflow: (optional TextExtractor) → SessionMemory → base.store_memory
        """
        try:
            # For session memories, we can optionally extract key topics
            topics_result = await self._extract_session_topics(content)
            topics = topics_result.get('topics', []) if topics_result['success'] else []
            
            # Create SessionMemory object with proper model fields
            session_memory = SessionMemory(
                user_id=user_id,
                content=content,  # model需要但DB没有
                session_id=session_id,
                interaction_sequence=message_count,  # model字段，映射到DB的total_messages
                conversation_state={"topics": topics, "content": content},  # model字段，映射到DB的user_context
                session_type="chat",  # model默认值
                active=True,  # model默认值，映射到DB的is_active
                confidence=0.8,  # model需要但DB没有
                importance_score=0.5  # model需要但DB没有
            )
            
            # Session memories don't need embeddings - store directly
            try:
                # Prepare data for storage without generating embeddings
                memory_data = self._prepare_for_storage_without_embedding(session_memory)
                
                # Insert into database
                db_result = self.db.table(self.table_name).insert(memory_data).execute()
                
                if db_result.data:
                    logger.info(f"✅ Stored {self.memory_type} memory: {session_memory.id}")
                    result = MemoryOperationResult(
                        success=True,
                        memory_id=session_memory.id,
                        operation="store",
                        message=f"Successfully stored {self.memory_type} memory",
                        data={"memory": db_result.data[0]}
                    )
                else:
                    raise Exception("No data returned from insert")
            except Exception as e:
                logger.error(f"❌ Failed to store {self.memory_type} memory: {e}")
                result = MemoryOperationResult(
                    success=False,
                    memory_id=session_memory.id,
                    operation="store",
                    message=f"Failed to store memory: {str(e)}"
                )
            
            if result.success:
                logger.info(f"✅ Stored session memory: {session_id} ({message_count} messages)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store session memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_session_memory",
                message=f"Failed to store session memory: {str(e)}"
            )

    async def get_session_by_id(self, user_id: str, session_id: str) -> SessionMemory:
        """Get session memory by session_id"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('session_id', session_id)\
                .single()\
                .execute()
            
            if result.data:
                return await self._parse_from_storage(result.data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None

    async def search_recent_sessions(self, user_id: str, limit: int = 10) -> List[SessionMemory]:
        """Search recent session memories"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            sessions = []
            for data in result.data or []:
                session = await self._parse_from_storage(data)
                sessions.append(session)
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Failed to search recent sessions: {e}")
            return []

    async def update_session_activity(self, session_id: str, user_id: str, additional_content: str = None) -> MemoryOperationResult:
        """Update session with new activity"""
        try:
            updates = {
                'last_activity': datetime.now().isoformat(),
                'message_count': 'message_count + 1'  # This would need database function support
            }
            
            if additional_content:
                # In a more complex implementation, we'd append content
                # For now, we just update the timestamp
                pass
            
            return await self.update_memory(session_id, updates)
            
        except Exception as e:
            logger.error(f"❌ Failed to update session activity: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=session_id,
                operation="update_session_activity",
                message=f"Failed to update session: {str(e)}"
            )
    
    # Private helper methods
    
    async def _extract_session_topics(self, content: str) -> Dict[str, Any]:
        """Extract topics from session content using TextExtractor"""
        try:
            # Simple schema for topic extraction
            topic_schema = {
                "topics": "List of main topics or subjects discussed in this session",
                "confidence": "Confidence in extraction quality (0.0-1.0)"
            }
            
            # Use TextExtractor to extract topics
            extraction_result = await self.text_extractor.extract_key_information(
                text=content,
                schema=topic_schema
            )
            
            if extraction_result['success']:
                data = extraction_result['data']
                
                # Ensure topics is a list
                if not isinstance(data.get('topics'), list):
                    data['topics'] = []
                
                return {
                    'success': True,
                    'topics': data['topics'],
                    'confidence': extraction_result.get('confidence', 0.7)
                }
            else:
                return {'success': False, 'topics': []}
            
        except Exception as e:
            logger.warning(f"⚠️ Topic extraction failed: {e}")
            return {'success': False, 'topics': []}
    
    def _prepare_for_storage_without_embedding(self, memory) -> Dict[str, Any]:
        """Prepare memory data for database storage without embedding"""
        # Get serialized data
        memory_data = memory.model_dump(mode='json')
        
        # Handle JSON fields
        memory_data = self._serialize_json_fields(memory_data)
        
        # Convert datetime objects  
        memory_data = self._serialize_datetime_fields(memory_data)
        
        # Remove common fields that don't exist in database schemas
        common_fields_to_remove = ['access_count', 'last_accessed_at', 'embedding']
        for field in common_fields_to_remove:
            memory_data.pop(field, None)
        
        # Allow subclasses to customize
        return self._customize_for_storage(memory_data)
    
    def _serialize_json_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize JSON fields for storage"""
        import json
        json_fields = ['user_context', 'key_decisions', 'ongoing_tasks', 'user_preferences', 'important_facts', 'session_metadata']
        for field in json_fields:
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field])
        return data
    
    def _serialize_datetime_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime objects to ISO strings"""
        datetime_fields = ['created_at', 'updated_at', 'last_summary_at']
        for field in datetime_fields:
            if field in data and hasattr(data[field], 'isoformat'):
                data[field] = data[field].isoformat()
        return data
    
    # Override base engine methods for session-specific handling
    
    def _customize_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data before storage - handle session-specific fields"""
        # Remove fields that don't exist in database schema
        # DB有：session_id, conversation_summary, user_context, key_decisions, ongoing_tasks, 
        #       user_preferences, important_facts, total_messages, messages_since_last_summary, 
        #       last_summary_at, is_active, session_metadata
        # DB没有：content, memory_type, tags, confidence, access_count, last_accessed_at, 
        #        importance_score, interaction_sequence, conversation_state, session_type, active, context
        fields_to_remove = ['content', 'memory_type', 'tags', 'confidence', 'importance_score', 'context']
        
        for field in fields_to_remove:
            data.pop(field, None)
        
        # Map model fields to database fields
        if 'interaction_sequence' in data:
            data['total_messages'] = data.pop('interaction_sequence')
        if 'conversation_state' in data:
            data['user_context'] = data.pop('conversation_state')
        if 'active' in data:
            data['is_active'] = data.pop('active')
        if 'session_type' in data:
            # Store session_type in session_metadata as JSON
            session_type = data.pop('session_type')
            if 'session_metadata' not in data:
                data['session_metadata'] = {}
            data['session_metadata']['session_type'] = session_type
        
        # Set default values for database-specific fields
        if 'session_id' not in data:
            data['session_id'] = f"session_{datetime.now().timestamp()}"
        if 'conversation_summary' not in data:
            # Generate summary from available data
            user_context = data.get('user_context', {})
            if isinstance(user_context, dict) and 'content' in user_context:
                data['conversation_summary'] = str(user_context['content'])[:200]
            else:
                data['conversation_summary'] = 'Session summary'
        if 'user_context' not in data:
            data['user_context'] = {}
        if 'key_decisions' not in data:
            data['key_decisions'] = []
        if 'ongoing_tasks' not in data:
            data['ongoing_tasks'] = []
        if 'user_preferences' not in data:
            data['user_preferences'] = {}
        if 'important_facts' not in data:
            data['important_facts'] = []
        if 'total_messages' not in data:
            data['total_messages'] = 1
        if 'messages_since_last_summary' not in data:
            data['messages_since_last_summary'] = 1
        if 'is_active' not in data:
            data['is_active'] = True
        if 'session_metadata' not in data:
            data['session_metadata'] = {}
        
        return data
    
    def _customize_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data after retrieval - add model-required fields"""
        # Map database fields back to model fields
        if 'total_messages' in data and 'interaction_sequence' not in data:
            data['interaction_sequence'] = data['total_messages']
        if 'user_context' in data and 'conversation_state' not in data:
            data['conversation_state'] = data['user_context']
        if 'is_active' in data and 'active' not in data:
            data['active'] = data['is_active']
        
        # Extract session_type from session_metadata
        if 'session_type' not in data and 'session_metadata' in data:
            metadata = data.get('session_metadata', {})
            if isinstance(metadata, dict) and 'session_type' in metadata:
                data['session_type'] = metadata['session_type']
            else:
                data['session_type'] = 'chat'
        
        # Reconstruct content from conversation_summary for model
        if 'content' not in data:
            data['content'] = data.get('conversation_summary', 'Session content')
        
        # Add model-required fields with defaults (这些字段不在数据库中但model需要)
        if 'memory_type' not in data:
            data['memory_type'] = 'session'
        if 'tags' not in data:
            data['tags'] = []
        if 'confidence' not in data:
            data['confidence'] = 0.8
        if 'importance_score' not in data:
            data['importance_score'] = 0.5
        
        return data
    
    async def _create_memory_model(self, data: Dict[str, Any]) -> SessionMemory:
        """Create SessionMemory model from database data"""
        return SessionMemory(**data)
    
    # Missing methods that memory_service.py expects
    
    async def summarize_session(
        self,
        user_id: str,
        session_id: str,
        force_update: bool = False,
        compression_level: str = "medium"
    ) -> MemoryOperationResult:
        """Generate intelligent summary of session conversation"""
        try:
            # Get session data
            session = await self.get_session_by_id(user_id, session_id)
            if not session:
                return MemoryOperationResult(
                    success=False,
                    memory_id=session_id,
                    operation="summarize_session",
                    message=f"Session {session_id} not found"
                )
            
            # Check if summary is needed
            if not force_update and session.conversation_summary:
                return MemoryOperationResult(
                    success=True,
                    memory_id=session_id,
                    operation="summarize_session",
                    message="Summary already exists (use force_update=True to regenerate)",
                    data={"summary": session.conversation_summary}
                )
            
            # Generate intelligent summary using TextExtractor
            summary_result = await self._generate_intelligent_summary(
                session.content or session.conversation_summary,
                compression_level
            )
            
            if summary_result['success']:
                # Update session with new summary
                update_data = {
                    'conversation_summary': summary_result['summary'],
                    'last_summary_at': datetime.now().isoformat(),
                    'messages_since_last_summary': 0
                }
                
                result = self.db.table(self.table_name)\
                    .update(update_data)\
                    .eq('user_id', user_id)\
                    .eq('session_id', session_id)\
                    .execute()
                
                if result.data:
                    return MemoryOperationResult(
                        success=True,
                        memory_id=session_id,
                        operation="summarize_session",
                        message="Session summary generated successfully",
                        data={
                            "summary": summary_result['summary'],
                            "compression_level": compression_level,
                            "confidence": summary_result.get('confidence', 0.8)
                        }
                    )
            
            return MemoryOperationResult(
                success=False,
                memory_id=session_id,
                operation="summarize_session",
                message="Failed to generate summary"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to summarize session: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=session_id,
                operation="summarize_session",
                message=f"Error summarizing session: {str(e)}"
            )
    
    async def get_session_context(
        self,
        user_id: str,
        session_id: str,
        include_summaries: bool = True,
        max_recent_messages: int = 5
    ) -> Dict[str, Any]:
        """Get comprehensive session context including summaries and recent activity"""
        try:
            # Get main session data
            session = await self.get_session_by_id(user_id, session_id)
            if not session:
                return {
                    "session_found": False,
                    "error": f"Session {session_id} not found",
                    "user_id": user_id,
                    "session_id": session_id
                }
            
            # Build context data
            context = {
                "session_found": True,
                "user_id": user_id,
                "session_id": session_id,
                "session_type": getattr(session, 'session_type', 'chat'),
                "is_active": getattr(session, 'active', True),
                "total_messages": getattr(session, 'interaction_sequence', 1),
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "conversation_state": getattr(session, 'conversation_state', {}),
                "key_decisions": getattr(session, 'key_decisions', []),
                "ongoing_tasks": getattr(session, 'ongoing_tasks', []),
                "user_preferences": getattr(session, 'user_preferences', {}),
                "important_facts": getattr(session, 'important_facts', []),
                "session_metadata": getattr(session, 'session_metadata', {})
            }
            
            # Add summaries if requested
            if include_summaries:
                context["conversation_summary"] = getattr(session, 'conversation_summary', '')
                context["last_summary_at"] = getattr(session, 'last_summary_at', None)
                context["messages_since_last_summary"] = getattr(session, 'messages_since_last_summary', 0)
            
            # Add recent activity context
            recent_sessions = await self.search_recent_sessions(user_id, max_recent_messages)
            context["recent_sessions_count"] = len(recent_sessions)
            context["recent_sessions"] = [
                {
                    "session_id": s.session_id,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "summary": getattr(s, 'conversation_summary', '')[:100]  # First 100 chars
                }
                for s in recent_sessions[:max_recent_messages]
            ]
            
            return context
            
        except Exception as e:
            logger.error(f"❌ Failed to get session context: {e}")
            return {
                "session_found": False,
                "error": f"Error getting session context: {str(e)}",
                "user_id": user_id,
                "session_id": session_id
            }
    
    async def get_session_memories(self, user_id: str, session_id: str) -> List[SessionMemory]:
        """Get all session memories for a specific session"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('session_id', session_id)\
                .order('created_at', desc=True)\
                .execute()
            
            memories = []
            for data in result.data or []:
                memory = await self._parse_from_storage(data)
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"❌ Failed to get session memories: {e}")
            return []
    
    async def _generate_intelligent_summary(self, content: str, compression_level: str = "medium") -> Dict[str, Any]:
        """Generate intelligent summary using TextExtractor"""
        try:
            # Define summary schema based on compression level
            summary_schemas = {
                "brief": {
                    "summary": "Very brief summary (1-2 sentences) of the main points discussed",
                    "key_topics": "List of 2-3 main topics"
                },
                "medium": {
                    "summary": "Concise summary (3-4 sentences) covering main discussion points and outcomes",
                    "key_topics": "List of 3-5 main topics discussed",
                    "key_decisions": "Important decisions or conclusions reached",
                    "action_items": "Any action items or next steps mentioned"
                },
                "detailed": {
                    "summary": "Detailed summary (5-7 sentences) with comprehensive coverage of discussion",
                    "key_topics": "Comprehensive list of all topics discussed",
                    "key_decisions": "All decisions and conclusions reached",
                    "action_items": "Complete list of action items and next steps",
                    "important_details": "Important details, facts, or insights shared",
                    "participants_contributions": "Notable contributions from different participants"
                }
            }
            
            schema = summary_schemas.get(compression_level, summary_schemas["medium"])
            
            # Use TextExtractor to generate summary
            extraction_result = await self.text_extractor.extract_key_information(
                text=content,
                schema=schema
            )
            
            if extraction_result['success']:
                data = extraction_result['data']
                
                # Ensure we have a summary
                if not data.get('summary'):
                    data['summary'] = content[:200] + "..." if len(content) > 200 else content
                
                return {
                    'success': True,
                    'summary': data['summary'],
                    'data': data,
                    'confidence': extraction_result.get('confidence', 0.7),
                    'compression_level': compression_level
                }
            else:
                # Fallback to simple truncation
                return {
                    'success': True,
                    'summary': content[:300] + "..." if len(content) > 300 else content,
                    'data': {'summary': content[:300]},
                    'confidence': 0.5,
                    'compression_level': 'fallback'
                }
                
        except Exception as e:
            logger.warning(f"⚠️ Summary generation failed: {e}")
            # Fallback to simple truncation
            return {
                'success': True,
                'summary': content[:200] + "..." if len(content) > 200 else content,
                'data': {'summary': content[:200]},
                'confidence': 0.3,
                'compression_level': 'fallback'
            }