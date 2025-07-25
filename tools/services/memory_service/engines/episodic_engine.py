#!/usr/bin/env python3
"""
Episodic Memory Engine
Simple, clean implementation for episodic memory management
"""

from typing import Dict, Any, List
from datetime import datetime
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import EpisodicMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class EpisodicMemoryEngine(BaseMemoryEngine):
    """Simple engine for managing episodic memories"""
    
    def __init__(self):
        super().__init__()
        self.text_extractor = TextExtractor()
    
    @property
    def table_name(self) -> str:
        return "episodic_memories"
    
    @property
    def memory_type(self) -> str:
        return "episodic"
    
    async def store_episode(
        self,
        user_id: str,
        dialog_content: str,
        episode_date: datetime = None,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Store episodic memory by extracting episode information from dialog
        
        Simple workflow: TextExtractor → EpisodicMemory → base.store_memory
        """
        try:
            # Extract episode info using TextExtractor
            extraction_result = await self._extract_episode_info(dialog_content)
            
            if not extraction_result['success']:
                logger.error(f"Failed to extract episode info: {extraction_result.get('error')}")
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_episode",
                    message=f"Failed to extract episode information: {extraction_result.get('error')}"
                )
            
            episode_data = extraction_result['data']
            
            # Create EpisodicMemory object - use model fields that exist in both model and DB
            episodic_memory = EpisodicMemory(
                user_id=user_id,
                content=episode_data.get('summary', dialog_content[:200]),  # model需要但DB没有，会在存储时移除
                event_type=episode_data.get('event_type', 'conversation'),
                location=episode_data.get('location'),
                participants=episode_data.get('participants', []),
                emotional_valence=float(episode_data.get('emotional_valence', 0.0)),
                vividness=float(episode_data.get('vividness', 0.5)),  # model需要但DB没有
                importance_score=importance_score,
                episode_date=episode_date or datetime.now(),  # 会映射为occurred_at
                confidence=float(episode_data.get('confidence', 0.8))  # model需要但DB没有
            )
            
            # Let base engine handle embedding and storage
            result = await self.store_memory(episodic_memory)
            
            if result.success:
                logger.info(f"✅ Stored episode: {episodic_memory.event_type} memory")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store episode: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_episode", 
                message=f"Failed to store episode: {str(e)}"
            )

    async def search_episodes_by_event_type(self, user_id: str, event_type: str, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes by episode_title (since event_type column doesn't exist)"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('episode_title', f'%{event_type}%')\
                .order('occurred_at', desc=True)\
                .limit(limit)\
                .execute()
            
            episodes = []
            for data in result.data or []:
                episode = await self._parse_from_storage(data)
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"❌ Failed to search episodes by event type {event_type}: {e}")
            return []

    async def search_episodes_by_participant(self, user_id: str, participant: str, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes involving a specific participant using JSONB contains"""
        try:
            # Use JSONB text search for participant (convert to string search)
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('participants', f'%"{participant}"%')\
                .order('occurred_at', desc=True)\
                .limit(limit)\
                .execute()
            
            episodes = []
            for data in result.data or []:
                episode = await self._parse_from_storage(data)
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"❌ Failed to search episodes by participant {participant}: {e}")
            return []

    async def search_episodes_by_location(self, user_id: str, location: str, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes by location"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('location', f'%{location}%')\
                .order('occurred_at', desc=True)\
                .limit(limit)\
                .execute()
            
            episodes = []
            for data in result.data or []:
                episode = await self._parse_from_storage(data)
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"❌ Failed to search episodes by location {location}: {e}")
            return []
    
    # Private helper methods
    
    async def _extract_episode_info(self, dialog_content: str) -> Dict[str, Any]:
        """Extract episode information using TextExtractor with simple schema"""
        try:
            # Schema for episode extraction - 根据数据库字段设计
            episodic_schema = {
                "episode_title": "Brief title for this episode",
                "summary": "2-3 sentence summary of what happened",
                "event_type": "Type of event (conversation, meeting, planning, problem_solving, etc.)",
                "location": "Any location mentioned (optional)",
                "participants": "List of people mentioned (exclude AI assistant)",
                "temporal_context": "Time context (recent, yesterday, last_week, etc.)",
                "key_events": "List of main events or topics discussed",
                "emotional_context": "Emotional context (positive, negative, neutral, mixed, etc.)",  
                "outcomes": "Any results, decisions, or conclusions",
                "lessons_learned": "What was learned from this episode",
                "emotional_valence": "Emotional tone from -1.0 (negative) to 1.0 (positive), 0.0 neutral",
                "vividness": "How detailed/memorable from 0.0 (vague) to 1.0 (very detailed)",
                "confidence": "Confidence in extraction quality (0.0-1.0)"
            }
            
            # Use TextExtractor to extract structured information
            extraction_result = await self.text_extractor.extract_key_information(
                text=dialog_content,
                schema=episodic_schema
            )
            
            if extraction_result['success']:
                # Simple validation and cleanup
                data = extraction_result['data']
                
                # Ensure required fields with safe defaults
                if not data.get('episode_title'):
                    data['episode_title'] = 'Episode'
                if not data.get('summary'):
                    data['summary'] = dialog_content[:100] + '...' if len(dialog_content) > 100 else dialog_content
                if not data.get('event_type'):
                    data['event_type'] = 'conversation'
                
                # Ensure lists are lists
                for list_field in ['participants', 'key_events', 'outcomes']:
                    if not isinstance(data.get(list_field), list):
                        data[list_field] = []
                
                # Ensure string fields are strings
                for string_field in ['temporal_context', 'emotional_context', 'lessons_learned']:
                    if string_field not in data:
                        if string_field == 'temporal_context':
                            data[string_field] = 'recent'
                        elif string_field == 'emotional_context':
                            data[string_field] = 'neutral'
                        else:
                            data[string_field] = ''
                
                # Ensure numeric fields are numbers
                for numeric_field in ['emotional_valence', 'vividness', 'confidence']:
                    try:
                        data[numeric_field] = float(data.get(numeric_field, 0.0))
                    except (ValueError, TypeError):
                        data[numeric_field] = 0.0
                
                return {
                    'success': True,
                    'data': data,
                    'confidence': extraction_result.get('confidence', 0.7)
                }
            else:
                return extraction_result
            
        except Exception as e:
            logger.error(f"❌ Episode extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {
                    'episode_title': 'Episode',
                    'summary': dialog_content[:100],
                    'event_type': 'conversation',
                    'participants': [],
                    'key_events': [],
                    'outcomes': [],
                    'emotional_valence': 0.0,
                    'vividness': 0.5,
                    'confidence': 0.5
                },
                'confidence': 0.0
            }
    
    # Override base engine methods for episodic-specific handling
    
    def _customize_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data before storage - handle episodic-specific fields"""
        # Remove fields that don't exist in database schema
        # DB有：episode_title, summary, participants, location, temporal_context, key_events, 
        #       emotional_context, outcomes, lessons_learned, emotional_intensity, occurred_at
        # DB没有：content, memory_type, tags, confidence, context, episode_date, vividness, event_type, importance_score
        fields_to_remove = ['content', 'memory_type', 'tags', 'confidence', 'context', 'vividness', 'event_type', 'importance_score']
        
        for field in fields_to_remove:
            data.pop(field, None)
        
        # Map episode_date to occurred_at for database
        if 'episode_date' in data:
            data['occurred_at'] = data.pop('episode_date')
        
        # Map emotional_valence to emotional_intensity (DB使用不同字段名)
        if 'emotional_valence' in data:
            # Convert from -1,1 range to 0,1 range for DB
            valence = data.pop('emotional_valence')
            data['emotional_intensity'] = (valence + 1.0) / 2.0
        
        # Ensure required fields have defaults for database schema
        if 'episode_title' not in data:
            data['episode_title'] = 'Episode'
        if 'summary' not in data:
            data['summary'] = data.get('content', 'No summary')[:200]
        if 'participants' not in data:
            data['participants'] = []
        if 'key_events' not in data:
            data['key_events'] = []
        if 'outcomes' not in data:
            data['outcomes'] = []
        if 'temporal_context' not in data:
            data['temporal_context'] = 'recent'
        if 'emotional_context' not in data:
            data['emotional_context'] = 'neutral'
        if 'lessons_learned' not in data:
            data['lessons_learned'] = ''
        
        return data
    
    def _customize_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data after retrieval - add model-required fields"""
        # Map database fields back to model fields
        if 'occurred_at' in data and 'episode_date' not in data:
            data['episode_date'] = data['occurred_at']
        
        # Map emotional_intensity back to emotional_valence (convert 0-1 to -1,1)
        if 'emotional_intensity' in data and 'emotional_valence' not in data:
            intensity = data.get('emotional_intensity', 0.5)
            data['emotional_valence'] = (intensity * 2.0) - 1.0
        
        # Reconstruct content from summary for model
        if 'content' not in data:
            data['content'] = data.get('summary', 'No content available')
        
        # Add model-required fields with defaults (这些字段不在数据库中但model需要)
        if 'memory_type' not in data:
            data['memory_type'] = 'episodic'
        if 'tags' not in data:
            data['tags'] = []
        if 'confidence' not in data:
            data['confidence'] = 0.8
        if 'vividness' not in data:
            data['vividness'] = 0.5
        if 'event_type' not in data:
            data['event_type'] = 'conversation'
        if 'importance_score' not in data:
            data['importance_score'] = 0.5
            
        return data
    
    async def _create_memory_model(self, data: Dict[str, Any]) -> EpisodicMemory:
        """Create EpisodicMemory model from database data"""
        return EpisodicMemory(**data)