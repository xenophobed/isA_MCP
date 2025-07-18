#!/usr/bin/env python3
"""
Session Memory Engine
Specialized engine for session memory management with intelligent dialog processing and summarization
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timedelta
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import SessionMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor
from tools.services.intelligence_service.language.text_summarizer import TextSummarizer, SummaryStyle, SummaryLength

logger = get_logger(__name__)


class SessionMemoryEngine(BaseMemoryEngine):
    """Engine for managing session memories with intelligent dialog processing"""
    
    def __init__(self):
        super().__init__()
        self.text_extractor = TextExtractor()
        self.text_summarizer = TextSummarizer()
        # Configuration for session management
        self.max_session_length = 10000  # Characters before triggering summarization
        self.summary_trigger_count = 10  # Messages before considering summarization
    
    @property
    def table_name(self) -> str:
        return "session_memories"  # For session-level summaries
    
    @property
    def messages_table_name(self) -> str:
        return "session_messages"  # For individual messages
    
    @property
    def memory_type(self) -> str:
        return "session"
    
    async def store_session_message(
        self,
        user_id: str,
        session_id: str,
        message_content: str,
        message_type: str = "human",
        role: str = "user",
        importance_score: float = 0.7
    ) -> MemoryOperationResult:
        """Store a single message with intelligent processing"""
        try:
            # Extract information from message
            extraction_result = await self._extract_message_info(message_content, message_type)
            
            # Build message metadata
            message_metadata = {
                "timestamp": datetime.now().isoformat(),
                "extraction_confidence": extraction_result.get('confidence', 0.0)
            }
            
            # Add extracted information if successful
            if extraction_result.get('success'):
                message_metadata.update({
                    "extracted_info": extraction_result.get('data', {}),
                    "entities": extraction_result.get('data', {}).get('entities', {}),
                    "sentiment": extraction_result.get('data', {}).get('sentiment')
                })
            
            # Store message in session_messages table
            message_data = {
                "session_id": session_id,
                "user_id": user_id,
                "message_type": message_type,
                "role": role,
                "content": message_content,
                "message_metadata": json.dumps(message_metadata, default=str),
                "importance_score": importance_score,
                "is_summary_candidate": True
            }
            
            # Insert into session_messages table
            result = self.db.table(self.messages_table_name).insert(message_data).execute()
            
            if result.data:
                message_id = result.data[0]['id']
                logger.info(f"Stored session message {message_id} for session {session_id}")
                
                # Check if summarization is needed
                await self._check_and_summarize_session(user_id, session_id)
                
                return MemoryOperationResult(
                    success=True,
                    memory_id=message_id,
                    operation="store_session_message",
                    message="Session message stored successfully"
                )
            else:
                raise Exception("Failed to insert message into database")
            
        except Exception as e:
            logger.error(f"Failed to store session message: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_session_message",
                message=f"Failed to store session message: {str(e)}"
            )
    
    async def store_session_memory(
        self,
        user_id: str,
        session_id: str,
        content: str,
        interaction_sequence: int,
        conversation_state: Dict[str, Any],
        session_type: str = "chat",
        active: bool = True,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Store a session memory (legacy method for compatibility)"""
        
        session_memory = SessionMemory(
            user_id=user_id,
            content=content,
            session_id=session_id,
            interaction_sequence=interaction_sequence,
            conversation_state=conversation_state,
            session_type=session_type,
            active=active,
            importance_score=importance_score
        )
        
        return await self.store_memory(session_memory)
    
    async def get_session_messages(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a specific session"""
        try:
            result = self.db.table(self.messages_table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('session_id', session_id)\
                .order('created_at', desc=False)\
                .execute()
            
            messages = []
            for data in result.data or []:
                # Parse JSON metadata
                if 'message_metadata' in data and isinstance(data['message_metadata'], str):
                    try:
                        data['message_metadata'] = json.loads(data['message_metadata'])
                    except:
                        data['message_metadata'] = {}
                messages.append(data)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get session messages for {session_id}: {e}")
            return []
    
    async def get_session_memories(self, user_id: str, session_id: str) -> List[SessionMemory]:
        """Get all memories for a specific session (legacy compatibility)"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('session_id', session_id)\
                .order('created_at', desc=False)\
                .execute()
            
            memories = []
            for data in result.data or []:
                memory = await self._parse_memory_data(data)
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get session memories for {session_id}: {e}")
            return []
    
    async def get_active_sessions(self, user_id: str) -> List[str]:
        """Get all active session IDs for a user"""
        try:
            result = self.db.table(self.table_name)\
                .select('session_id')\
                .eq('user_id', user_id)\
                .eq('active', True)\
                .execute()
            
            session_ids = list(set([data['session_id'] for data in result.data or []]))
            return session_ids
            
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    async def get_latest_session_state(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get the latest conversation state for a session"""
        try:
            result = self.db.table(self.table_name)\
                .select('conversation_state')\
                .eq('user_id', user_id)\
                .eq('session_id', session_id)\
                .order('interaction_sequence', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                state_data = result.data[0]['conversation_state']
                if isinstance(state_data, str):
                    return json.loads(state_data)
                return state_data
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get latest session state: {e}")
            return {}
    
    async def end_session(self, user_id: str, session_id: str) -> MemoryOperationResult:
        """Mark all memories in a session as inactive"""
        try:
            result = self.db.table(self.table_name)\
                .update({'active': False})\
                .eq('user_id', user_id)\
                .eq('session_id', session_id)\
                .execute()
            
            count = len(result.data) if result.data else 0
            
            return MemoryOperationResult(
                success=True,
                operation="end_session",
                message=f"Ended session {session_id}, deactivated {count} memories",
                affected_count=count
            )
            
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return MemoryOperationResult(
                success=False,
                operation="end_session",
                message=f"Failed to end session: {str(e)}"
            )
    
    async def update_conversation_state(
        self, 
        memory_id: str, 
        state_updates: Dict[str, Any]
    ) -> MemoryOperationResult:
        """Update conversation state for a session memory"""
        try:
            memory = await self.get_memory(memory_id)
            if not memory:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="update_state",
                    message="Memory not found"
                )
            
            # Merge state
            merged_state = memory.conversation_state.copy()
            merged_state.update(state_updates)
            
            updates = {'conversation_state': merged_state}
            
            return await self.update_memory(memory_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to update conversation state: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="update_state",
                message=f"Failed to update state: {str(e)}"
            )
    
    async def get_session_summary(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get summary statistics for a session"""
        try:
            memories = await self.get_session_memories(user_id, session_id)
            
            if not memories:
                return {}
            
            return {
                'session_id': session_id,
                'user_id': user_id,
                'total_interactions': len(memories),
                'session_type': memories[0].session_type if memories else 'unknown',
                'active': any(m.active for m in memories),
                'start_time': min(m.created_at for m in memories),
                'last_interaction': max(m.created_at for m in memories),
                'avg_importance': sum(m.importance_score for m in memories) / len(memories)
            }
            
        except Exception as e:
            logger.error(f"Failed to get session summary: {e}")
            return {}
    
    async def _prepare_memory_data(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare session memory data for storage"""
        # Add session-specific fields
        session_fields = [
            'session_id', 'interaction_sequence', 'conversation_state',
            'session_type', 'active'
        ]
        
        for field in session_fields:
            if field not in memory_data:
                if field == 'conversation_state':
                    memory_data[field] = json.dumps({})
                elif field == 'session_type':
                    memory_data[field] = 'chat'
                elif field == 'active':
                    memory_data[field] = True
                elif field == 'interaction_sequence':
                    memory_data[field] = 1
                else:
                    memory_data[field] = None
        
        # Handle JSON fields
        if isinstance(memory_data.get('conversation_state'), dict):
            memory_data['conversation_state'] = json.dumps(memory_data['conversation_state'])
        
        return memory_data
    
    async def _parse_memory_data(self, data: Dict[str, Any]) -> SessionMemory:
        """Parse session memory data from database"""
        # Parse JSON fields
        if 'embedding' in data and isinstance(data['embedding'], str):
            data['embedding'] = json.loads(data['embedding'])
        if 'context' in data and isinstance(data['context'], str):
            data['context'] = json.loads(data['context'])
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags'])
        if 'conversation_state' in data and isinstance(data['conversation_state'], str):
            data['conversation_state'] = json.loads(data['conversation_state'])
        
        return SessionMemory(**data)
    
    # New intelligent processing methods
    
    async def summarize_session(
        self,
        user_id: str,
        session_id: str,
        force_update: bool = False,
        compression_level: str = "medium"
    ) -> MemoryOperationResult:
        """Summarize a session conversation intelligently"""
        try:
            # Get all session messages
            messages = await self.get_session_messages(user_id, session_id)
            
            if not messages:
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="summarize_session",
                    message="No messages found for session"
                )
            
            # Check if summarization is needed
            if not force_update and not await self._should_summarize_session_messages(messages):
                return MemoryOperationResult(
                    success=True,
                    memory_id="",
                    operation="summarize_session",
                    message="Session does not need summarization yet"
                )
            
            # Build conversation text for summarization
            conversation_text = self._build_conversation_text_from_messages(messages)
            
            # Determine summary style and length based on session characteristics
            summary_style = SummaryStyle.NARRATIVE  # Good for conversations
            summary_length = {
                "brief": SummaryLength.BRIEF,
                "medium": SummaryLength.MEDIUM,
                "detailed": SummaryLength.DETAILED
            }.get(compression_level, SummaryLength.MEDIUM)
            
            # Generate summary using TextSummarizer
            summary_result = await self.text_summarizer.summarize_text(
                text=conversation_text,
                style=summary_style,
                length=summary_length,
                custom_focus=["main topics", "key decisions", "action items", "important information"]
            )
            
            if not summary_result.get('success'):
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="summarize_session",
                    message=f"Failed to generate summary: {summary_result.get('error')}"
                )
            
            # Extract key points from conversation
            key_points_result = await self.text_summarizer.extract_key_points(
                text=conversation_text,
                max_points=8
            )
            
            # Create summary content
            summary_content = summary_result['summary']
            
            # Build session metadata for summary
            session_metadata = {
                "summary_generated_at": datetime.now().isoformat(),
                "compression_ratio": summary_result.get('compression_ratio', 0.0),
                "quality_score": summary_result.get('quality_score', 0.0),
                "summary_length": summary_length.value,
                "summary_style": summary_style.value,
                "original_length": len(conversation_text),
                "compression_level": compression_level
            }
            
            # Prepare data for session_memories table
            session_memory_data = {
                "session_id": session_id,
                "user_id": user_id,
                "conversation_summary": summary_content,
                "key_decisions": json.dumps(key_points_result.get('key_points', []) if key_points_result.get('success') else []),
                "total_messages": len(messages),
                "messages_since_last_summary": 0,  # Reset after summary
                "last_summary_at": datetime.now().isoformat(),
                "is_active": True,
                "session_metadata": json.dumps(session_metadata)
            }
            
            # Insert or update session memory
            # Check if session memory already exists
            existing_result = self.db.table(self.table_name)\
                .select('*')\
                .eq('session_id', session_id)\
                .execute()
            
            if existing_result.data:
                # Update existing session memory
                result = self.db.table(self.table_name)\
                    .update(session_memory_data)\
                    .eq('session_id', session_id)\
                    .execute()
                memory_id = existing_result.data[0]['id']
            else:
                # Insert new session memory
                result = self.db.table(self.table_name)\
                    .insert(session_memory_data)\
                    .execute()
                memory_id = result.data[0]['id'] if result.data else ""
            
            if result.data:
                # Mark old messages as summarized (keep them but mark as processed)
                await self._mark_messages_as_summarized(user_id, session_id, messages)
                
                logger.info(f"Session {session_id} summarized: {len(messages)} messages → summary")
                
                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    operation="summarize_session",
                    message=f"Session summarized successfully: {len(messages)} messages compressed to summary",
                    data={
                        "summary_id": memory_id,
                        "original_message_count": len(messages),
                        "compression_ratio": summary_result.get('compression_ratio', 0.0),
                        "quality_score": summary_result.get('quality_score', 0.0),
                        "key_points_count": len(key_points_result.get('key_points', []))
                    }
                )
            else:
                raise Exception("Failed to store session summary")
            
        except Exception as e:
            logger.error(f"Failed to summarize session {session_id}: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="summarize_session",
                message=f"Failed to summarize session: {str(e)}"
            )
    
    async def get_session_context(
        self,
        user_id: str,
        session_id: str,
        include_summaries: bool = True,
        max_recent_messages: int = 5
    ) -> Dict[str, Any]:
        """Get comprehensive session context including summaries and recent messages"""
        try:
            # Get session messages
            messages = await self.get_session_messages(user_id, session_id)
            
            if not messages:
                return {"success": False, "error": "No session found"}
            
            # Get session summary if available
            session_memory = await self._get_session_memory(user_id, session_id)
            
            # Get recent messages
            recent_messages = messages[-max_recent_messages:] if messages else []
            
            context = {
                "success": True,
                "session_id": session_id,
                "total_messages": len(messages),
                "active_messages": len([m for m in messages if m.get('is_summary_candidate', True)]),
                "summary_available": session_memory is not None,
                "recent_messages": []
            }
            
            # Add summary if requested and available
            if include_summaries and session_memory:
                # Parse JSON fields
                key_decisions = session_memory.get('key_decisions', '[]')
                if isinstance(key_decisions, str):
                    try:
                        key_decisions = json.loads(key_decisions)
                    except:
                        key_decisions = []
                
                session_metadata = session_memory.get('session_metadata', '{}')
                if isinstance(session_metadata, str):
                    try:
                        session_metadata = json.loads(session_metadata)
                    except:
                        session_metadata = {}
                
                context["summary"] = {
                    "content": session_memory.get('conversation_summary', ''),
                    "created_at": session_memory.get('last_summary_at', ''),
                    "covers_messages": session_memory.get('total_messages', 0),
                    "key_points": key_decisions,
                    "quality_score": session_metadata.get('quality_score', 0.0),
                    "compression_ratio": session_metadata.get('compression_ratio', 0.0)
                }
            
            # Add recent messages
            for message in recent_messages:
                message_metadata = message.get('message_metadata', {})
                if isinstance(message_metadata, str):
                    try:
                        message_metadata = json.loads(message_metadata)
                    except:
                        message_metadata = {}
                
                message_info = {
                    "content": message.get('content', ''),
                    "role": message.get('role', 'unknown'),
                    "timestamp": message.get('created_at', ''),
                    "message_type": message.get('message_type', 'unknown'),
                    "entities": message_metadata.get('entities', {}),
                    "sentiment": message_metadata.get('sentiment', {}),
                    "importance_score": message.get('importance_score', 0.0)
                }
                context["recent_messages"].append(message_info)
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get session context: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_message_info(self, message_content: str, message_type: str) -> Dict[str, Any]:
        """Extract information from a single message using TextExtractor"""
        try:
            # Define extraction schema based on message type
            if message_type in ["human", "user"]:
                schema = {
                    "main_topics": "Main topics or subjects discussed",
                    "questions_asked": "Questions asked by the user",
                    "requests_made": "Requests or tasks mentioned",
                    "entities_mentioned": "Important people, places, things mentioned",
                    "emotional_tone": "Emotional tone of the message"
                }
            else:  # AI/assistant messages
                schema = {
                    "main_topics": "Main topics covered in response",
                    "information_provided": "Key information or facts provided",
                    "suggestions_made": "Suggestions or recommendations given",
                    "questions_answered": "Questions that were answered",
                    "follow_up_needed": "Whether follow-up is needed"
                }
            
            # Extract key information
            extraction_result = await self.text_extractor.extract_key_information(
                text=message_content,
                schema=schema
            )
            
            # Also analyze sentiment
            sentiment_result = await self.text_extractor.analyze_sentiment(
                text=message_content,
                granularity="overall"
            )
            
            # Combine results
            if extraction_result.get('success'):
                extracted_data = extraction_result['data'].copy()
                if sentiment_result.get('success'):
                    extracted_data['sentiment'] = sentiment_result['data']
                
                return {
                    'success': True,
                    'data': extracted_data,
                    'confidence': extraction_result.get('confidence', 0.7)
                }
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"Failed to extract message info: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0
            }
    
    async def _get_message_count(self, user_id: str, session_id: str) -> int:
        """Get the total message count for a session"""
        try:
            result = self.db.table(self.messages_table_name)\
                .select('id', count='exact')\
                .eq('user_id', user_id)\
                .eq('session_id', session_id)\
                .execute()
            
            return result.count if result.count else 0
                
        except Exception as e:
            logger.error(f"Failed to get message count: {e}")
            return 0
    
    async def _check_and_summarize_session(self, user_id: str, session_id: str):
        """Check if session needs summarization and trigger if necessary"""
        try:
            messages = await self.get_session_messages(user_id, session_id)
            
            if await self._should_summarize_session_messages(messages):
                logger.info(f"Auto-triggering summarization for session {session_id}")
                await self.summarize_session(user_id, session_id, force_update=False)
                
        except Exception as e:
            logger.error(f"Failed to check summarization for session {session_id}: {e}")
    
    async def _should_summarize_session_messages(self, messages: List[Dict[str, Any]]) -> bool:
        """Determine if a session should be summarized based on messages"""
        if not messages:
            return False
        
        # Filter active messages that are candidates for summarization
        active_messages = [m for m in messages if m.get('is_summary_candidate', True)]
        
        # Check various criteria
        message_count_trigger = len(active_messages) >= self.summary_trigger_count
        
        # Calculate total character length
        total_length = sum(len(m.get('content', '')) for m in active_messages)
        length_trigger = total_length >= self.max_session_length
        
        # Check if we have a recent summary (only if messages contain required fields)
        if messages and 'user_id' in messages[0] and 'session_id' in messages[0]:
            session_memory = await self._get_session_memory(messages[0]['user_id'], messages[0]['session_id'])
            if session_memory:
                last_summary_at = session_memory.get('last_summary_at')
                if last_summary_at:
                    # Check how many messages since last summary
                    messages_since_summary = session_memory.get('messages_since_last_summary', 0)
                    summary_age_trigger = messages_since_summary >= 5
                else:
                    summary_age_trigger = message_count_trigger  # No previous summary
            else:
                summary_age_trigger = message_count_trigger  # No session memory yet
        else:
            summary_age_trigger = message_count_trigger  # Fallback to message count trigger
        
        return message_count_trigger or length_trigger or summary_age_trigger
    
    async def _get_session_memory(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session memory record"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('session_id', session_id)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            return None
                
        except Exception as e:
            logger.error(f"Failed to get session memory: {e}")
            return None
    
    async def _mark_messages_as_summarized(self, user_id: str, session_id: str, messages: List[Dict[str, Any]]):
        """Mark messages as processed by summary"""
        try:
            # Update messages to mark them as processed
            for message in messages:
                if message.get('is_summary_candidate', True):
                    self.db.table(self.messages_table_name)\
                        .update({'is_summary_candidate': False})\
                        .eq('id', message['id'])\
                        .execute()
                        
        except Exception as e:
            logger.error(f"Failed to mark messages as summarized: {e}")
    
    def _build_conversation_text_from_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Build readable conversation text from messages"""
        # Sort by creation time
        sorted_messages = sorted(messages, key=lambda x: x.get('created_at', ''))
        
        conversation_parts = []
        
        for message in sorted_messages:
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            
            # Format message with role and content
            if role in ["user", "human"]:
                conversation_parts.append(f"User: {content}")
            elif role in ["assistant", "ai"]:
                conversation_parts.append(f"Assistant: {content}")
            else:
                conversation_parts.append(f"{role.title()}: {content}")
        
        return "\n\n".join(conversation_parts)
    
    def _build_conversation_text(self, memories: List[SessionMemory]) -> str:
        """Build a readable conversation text from session memories"""
        # Sort by sequence and filter active messages
        active_messages = [m for m in memories if m.active and m.conversation_state.get("type") != "session_summary"]
        active_messages.sort(key=lambda x: x.interaction_sequence)
        
        conversation_parts = []
        
        for memory in active_messages:
            role = memory.conversation_state.get("role", "unknown")
            
            # Format message with role and content
            if role in ["user", "human"]:
                conversation_parts.append(f"User: {memory.content}")
            elif role in ["assistant", "ai"]:
                conversation_parts.append(f"Assistant: {memory.content}")
            else:
                conversation_parts.append(f"{role.title()}: {memory.content}")
        
        return "\n\n".join(conversation_parts)
    
    async def _compress_old_messages(self, user_id: str, session_id: str, messages_to_compress: List[SessionMemory]) -> int:
        """Mark old messages as inactive to compress storage"""
        if not messages_to_compress:
            return 0
        
        try:
            compressed_count = 0
            for memory in messages_to_compress:
                # Mark as inactive but keep the data
                if memory.id:  # Ensure memory has an ID
                    update_result = await self.update_memory(memory.id, {"active": False})
                    if update_result.success:
                        compressed_count += 1
            
            return compressed_count
            
        except Exception as e:
            logger.error(f"Failed to compress old messages: {e}")
            return 0