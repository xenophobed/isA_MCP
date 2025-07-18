#!/usr/bin/env python3
"""
Episodic Memory Engine
Specialized engine for episodic memory management
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import EpisodicMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class EpisodicMemoryEngine(BaseMemoryEngine):
    """Engine for managing episodic memories"""
    
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
        episode_date: Optional[datetime] = None,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Store an episodic memory by intelligently extracting information from dialog
        
        Args:
            user_id: User identifier
            dialog_content: Raw dialog between human and AI
            episode_date: When the episode occurred (defaults to now)
            importance_score: Manual importance override (0.0-1.0)
        """
        try:
            # Extract structured information from dialog
            extraction_result = await self._extract_episode_info(dialog_content)
            
            if not extraction_result['success']:
                logger.error(f"Failed to extract episode info: {extraction_result.get('error')}")
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_episode",
                    message=f"Failed to extract episode information: {extraction_result.get('error')}"
                )
            
            extracted_data = extraction_result['data']
            
            # Create episodic memory with extracted data
            episodic_memory = EpisodicMemory(
                user_id=user_id,
                content=extracted_data.get('clean_content', dialog_content[:500]),
                event_type=extracted_data.get('event_type', 'conversation'),
                location=extracted_data.get('location'),
                participants=extracted_data.get('participants', []),
                emotional_valence=extracted_data.get('emotional_valence', 0.0),
                vividness=extracted_data.get('vividness', 0.5),
                episode_date=episode_date or datetime.now(),
                importance_score=extracted_data.get('importance_score', importance_score)
            )
            
            # Store the memory
            result = await self.store_memory(episodic_memory)
            
            if result.success:
                logger.info(f"Stored intelligent episodic memory: {episodic_memory.id}")
                logger.info(f"Extracted: event_type={extracted_data.get('event_type')}, "
                          f"participants={len(extracted_data.get('participants', []))}, "
                          f"emotional_valence={extracted_data.get('emotional_valence')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to store episode from dialog: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_episode", 
                message=f"Failed to store episode: {str(e)}"
            )

    async def search_episodes_by_event_type(self, user_id: str, event_type: str, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes by event type"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('event_type', event_type)\
                .order('episode_date', desc=True)\
                .limit(limit)\
                .execute()
            
            episodes = []
            for data in result.data or []:
                episode = await self._parse_memory_data(data)
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"Failed to search episodes by event type {event_type}: {e}")
            return []

    async def search_episodes_by_participant(self, user_id: str, participant: str, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes involving a specific participant"""
        try:
            # Get all episodes for user and filter by participant
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .order('episode_date', desc=True)\
                .execute()
            
            episodes = []
            for data in result.data or []:
                episode = await self._parse_memory_data(data)
                if participant.lower() in [p.lower() for p in episode.participants]:
                    episodes.append(episode)
                    if len(episodes) >= limit:
                        break
            
            return episodes
            
        except Exception as e:
            logger.error(f"Failed to search episodes by participant {participant}: {e}")
            return []

    async def search_episodes_by_location(self, user_id: str, location: str, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes by location"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('location', f'%{location}%')\
                .order('episode_date', desc=True)\
                .limit(limit)\
                .execute()
            
            episodes = []
            for data in result.data or []:
                episode = await self._parse_memory_data(data)
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"Failed to search episodes by location {location}: {e}")
            return []

    async def search_episodes_by_timeframe(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime,
        limit: int = 10
    ) -> List[EpisodicMemory]:
        """Search episodes within a timeframe"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('episode_date', start_date.isoformat())\
                .lte('episode_date', end_date.isoformat())\
                .order('episode_date', desc=True)\
                .limit(limit)\
                .execute()
            
            episodes = []
            for data in result.data or []:
                episode = await self._parse_memory_data(data)
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"Failed to search episodes by timeframe: {e}")
            return []

    async def search_episodes_by_emotional_tone(
        self, 
        user_id: str, 
        min_valence: float = -1.0, 
        max_valence: float = 1.0,
        limit: int = 10
    ) -> List[EpisodicMemory]:
        """Search episodes by emotional valence range"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('emotional_valence', min_valence)\
                .lte('emotional_valence', max_valence)\
                .order('vividness', desc=True)\
                .limit(limit)\
                .execute()
            
            episodes = []
            for data in result.data or []:
                episode = await self._parse_memory_data(data)
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"Failed to search episodes by emotional tone: {e}")
            return []

    async def search_episodes_by_importance(
        self, 
        user_id: str, 
        min_importance: float = 0.7,
        limit: int = 10
    ) -> List[EpisodicMemory]:
        """Search high-importance episodes"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('importance_score', min_importance)\
                .order('importance_score', desc=True)\
                .order('episode_date', desc=True)\
                .limit(limit)\
                .execute()
            
            episodes = []
            for data in result.data or []:
                episode = await self._parse_memory_data(data)
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"Failed to search episodes by importance: {e}")
            return []
    
    
    async def _extract_episode_info(self, dialog_content: str) -> Dict[str, Any]:
        """Extract structured episodic information from raw dialog"""
        try:
            # Define extraction schema for episodic memory
            episodic_schema = {
                "event_type": "Type of interaction or event (e.g., 'question_answering', 'planning_session', 'troubleshooting', 'brainstorming', 'learning', 'problem_solving')",
                "clean_content": "Clean, concise summary of what happened in this episode (2-3 sentences max)",
                "location": "Any location mentioned in the conversation (physical or virtual)",
                "participants": "List of people or entities mentioned (exclude AI assistant)",
                "emotional_valence": "Emotional tone as number from -1.0 (very negative) to 1.0 (very positive), 0.0 for neutral",
                "vividness": "How detailed/memorable this episode is from 0.0 (vague) to 1.0 (very detailed)",
                "importance_score": "How important this episode is from 0.0 (trivial) to 1.0 (very important)",
                "key_topics": "Main topics or subjects discussed",
                "outcomes": "Any decisions, conclusions, or results from this episode"
            }
            
            # Extract key information using text extractor
            extraction_result = await self.text_extractor.extract_key_information(
                text=dialog_content,
                schema=episodic_schema
            )
            
            if not extraction_result['success']:
                return extraction_result
            
            extracted_data = extraction_result['data']
            
            # Post-process extracted data
            processed_data = await self._process_extracted_data(extracted_data, dialog_content)
            
            # Also extract entities for additional context
            entities_result = await self.text_extractor.extract_entities(
                text=dialog_content,
                confidence_threshold=0.6
            )
            
            if entities_result['success']:
                entities = entities_result['data'].get('entities', {})
                # Add detected people to participants if not already there
                detected_people = [entity['name'] for entity in entities.get('PERSON', [])]
                current_participants = processed_data.get('participants', [])
                
                for person in detected_people:
                    if person not in current_participants and person.lower() not in ['ai', 'assistant', 'claude']:
                        current_participants.append(person)
                
                processed_data['participants'] = current_participants
                
                # Extract location from entities if not found in schema
                if not processed_data.get('location') and entities.get('LOCATION'):
                    locations = [entity['name'] for entity in entities['LOCATION']]
                    if locations:
                        processed_data['location'] = locations[0]
            
            # Analyze sentiment for emotional valence
            sentiment_result = await self.text_extractor.analyze_sentiment(
                text=dialog_content,
                granularity="overall"
            )
            
            if sentiment_result['success']:
                sentiment_data = sentiment_result['data']
                overall_sentiment = sentiment_data.get('overall_sentiment', {})
                
                # Convert sentiment to valence score
                if overall_sentiment.get('label') == 'positive':
                    processed_data['emotional_valence'] = min(0.8, overall_sentiment.get('score', 0.5))
                elif overall_sentiment.get('label') == 'negative':
                    processed_data['emotional_valence'] = max(-0.8, -overall_sentiment.get('score', 0.5))
                else:
                    processed_data['emotional_valence'] = 0.0
            
            return {
                'success': True,
                'data': processed_data,
                'confidence': extraction_result.get('confidence', 0.7),
                'billing_info': extraction_result.get('billing_info')
            }
            
        except Exception as e:
            logger.error(f"Episode information extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0
            }
    
    async def _process_extracted_data(self, raw_data: Dict[str, Any], original_content: str) -> Dict[str, Any]:
        """Process and validate extracted episodic data"""
        processed = {}
        
        # Event type processing
        event_type = raw_data.get('event_type', 'conversation')
        if isinstance(event_type, str):
            processed['event_type'] = event_type.lower().replace(' ', '_')
        else:
            processed['event_type'] = 'conversation'
        
        # Clean content
        clean_content = raw_data.get('clean_content', '')
        if not clean_content or len(clean_content) < 10:
            # Generate a basic summary if extraction failed
            words = original_content.split()[:30]
            processed['clean_content'] = ' '.join(words) + ('...' if len(words) == 30 else '')
        else:
            processed['clean_content'] = clean_content[:500]  # Limit length
        
        # Location processing
        location = raw_data.get('location')
        if location and isinstance(location, str) and location.lower() not in ['none', 'not mentioned', 'n/a']:
            processed['location'] = location.strip()
        else:
            processed['location'] = None
        
        # Participants processing
        participants = raw_data.get('participants', [])
        if isinstance(participants, str):
            participants = [p.strip() for p in participants.split(',') if p.strip()]
        elif not isinstance(participants, list):
            participants = []
        
        # Filter out AI references and duplicates
        filtered_participants = []
        for p in participants:
            if isinstance(p, str):
                p_lower = p.lower()
                if p_lower not in ['ai', 'assistant', 'claude', 'chatbot', 'bot'] and p not in filtered_participants:
                    filtered_participants.append(p.strip())
        
        processed['participants'] = filtered_participants
        
        # Numerical fields with validation
        try:
            emotional_valence = float(raw_data.get('emotional_valence', 0.0))
            processed['emotional_valence'] = max(-1.0, min(1.0, emotional_valence))
        except (ValueError, TypeError):
            processed['emotional_valence'] = 0.0
        
        try:
            vividness = float(raw_data.get('vividness', 0.5))
            processed['vividness'] = max(0.0, min(1.0, vividness))
        except (ValueError, TypeError):
            processed['vividness'] = 0.5
        
        try:
            importance_score = float(raw_data.get('importance_score', 0.5))
            processed['importance_score'] = max(0.0, min(1.0, importance_score))
        except (ValueError, TypeError):
            processed['importance_score'] = 0.5
        
        # Additional context fields
        processed['key_topics'] = raw_data.get('key_topics', [])
        processed['outcomes'] = raw_data.get('outcomes', [])
        
        return processed
    
    async def _prepare_memory_data(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare episodic memory data for storage"""
        # Add episodic-specific fields
        episodic_fields = [
            'event_type', 'location', 'participants', 'emotional_valence',
            'vividness', 'episode_date'
        ]
        
        for field in episodic_fields:
            if field not in memory_data:
                if field == 'participants':
                    memory_data[field] = json.dumps([])
                elif field == 'emotional_valence':
                    memory_data[field] = 0.0
                elif field == 'vividness':
                    memory_data[field] = 0.5
                elif field == 'episode_date':
                    memory_data[field] = datetime.now().isoformat()
                else:
                    memory_data[field] = None
        
        # Handle JSON fields
        if isinstance(memory_data.get('participants'), list):
            memory_data['participants'] = json.dumps(memory_data['participants'])
        
        # Ensure episode_date is string
        if isinstance(memory_data.get('episode_date'), datetime):
            memory_data['episode_date'] = memory_data['episode_date'].isoformat()
        
        return memory_data
    
    async def _parse_memory_data(self, data: Dict[str, Any]) -> EpisodicMemory:
        """Parse episodic memory data from database"""
        # Parse JSON fields
        if 'embedding' in data and isinstance(data['embedding'], str):
            data['embedding'] = json.loads(data['embedding'])
        if 'context' in data and isinstance(data['context'], str):
            data['context'] = json.loads(data['context'])
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags'])
        if 'participants' in data and isinstance(data['participants'], str):
            data['participants'] = json.loads(data['participants'])
        
        # Parse datetime
        if 'episode_date' in data and isinstance(data['episode_date'], str):
            data['episode_date'] = datetime.fromisoformat(data['episode_date'].replace('Z', '+00:00'))
        
        return EpisodicMemory(**data)