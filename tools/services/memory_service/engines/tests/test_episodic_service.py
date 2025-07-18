#!/usr/bin/env python3
"""
Tests for Episodic Memory Engine with Intelligent Dialog Processing
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tools.services.memory_service.engines.episodic_engine import EpisodicMemoryEngine
from tools.services.memory_service.models import MemoryOperationResult, EpisodicMemory


class TestEpisodicMemoryEngine:
    """Test suite for intelligent episodic memory processing"""

    @pytest.fixture
    def engine(self):
        """Create a mock episodic engine for testing"""
        with patch('tools.services.memory_service.engines.base_engine.get_supabase_client') as mock_db, \
             patch('tools.services.memory_service.engines.base_engine.EmbeddingGenerator') as mock_embedder, \
             patch('tools.services.memory_service.engines.episodic_engine.TextExtractor') as mock_extractor:
            
            # Mock database
            mock_db.return_value = MagicMock()
            
            # Mock embedder
            mock_embedder_instance = AsyncMock()
            mock_embedder.return_value = mock_embedder_instance
            mock_embedder_instance.embed_single.return_value = [0.1, 0.2, 0.3]
            
            # Mock text extractor
            mock_extractor_instance = AsyncMock()
            mock_extractor.return_value = mock_extractor_instance
            
            engine = EpisodicMemoryEngine()
            engine.db = mock_db.return_value
            engine.embedder = mock_embedder_instance
            engine.text_extractor = mock_extractor_instance
            
            return engine

    @pytest.mark.asyncio
    async def test_store_episode_successful_extraction(self, engine):
        """Test successful episode storage with intelligent extraction"""
        
        # Mock dialog content
        dialog_content = """
        Human: Can you help me plan our team meeting for next Friday? We need to discuss Q4 roadmap and Alice, Bob, and Carol will be joining us in Conference Room A.
        
        AI: I'd be happy to help you plan your team meeting. For your Q4 roadmap discussion with Alice, Bob, and Carol in Conference Room A next Friday, here are some suggestions for your agenda...
        """
        
        # Mock extraction results
        mock_extraction_result = {
            'success': True,
            'data': {
                'event_type': 'planning_session',
                'clean_content': 'Team discussed Q4 roadmap planning with participants Alice, Bob, and Carol in Conference Room A.',
                'location': 'Conference Room A',
                'participants': ['Alice', 'Bob', 'Carol'],
                'emotional_valence': 0.6,
                'vividness': 0.8,
                'importance_score': 0.7,
                'key_topics': ['Q4 roadmap', 'team meeting'],
                'outcomes': ['meeting planned']
            },
            'confidence': 0.85
        }
        
        # Mock entity extraction
        mock_entities_result = {
            'success': True,
            'data': {
                'entities': {
                    'PERSON': [
                        {'name': 'Alice', 'confidence': 0.9},
                        {'name': 'Bob', 'confidence': 0.8},
                        {'name': 'Carol', 'confidence': 0.85}
                    ],
                    'LOCATION': [
                        {'name': 'Conference Room A', 'confidence': 0.9}
                    ]
                }
            }
        }
        
        # Mock sentiment analysis
        mock_sentiment_result = {
            'success': True,
            'data': {
                'overall_sentiment': {
                    'label': 'positive',
                    'score': 0.6
                }
            }
        }
        
        # Configure text extractor mocks
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine.text_extractor.extract_entities.return_value = mock_entities_result
        engine.text_extractor.analyze_sentiment.return_value = mock_sentiment_result
        
        # Mock database insertion
        engine.db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{'id': 'test_memory_id', 'user_id': 'user123'}]
        )
        
        # Test the store_episode method
        result = await engine.store_episode(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == True
        assert result.operation == "store"
        assert "test_memory_id" in str(result.data)
        
        # Verify text extractor was called
        engine.text_extractor.extract_key_information.assert_called_once()
        engine.text_extractor.extract_entities.assert_called_once()
        engine.text_extractor.analyze_sentiment.assert_called_once()
        
        # Verify embedding generation
        engine.embedder.embed_single.assert_called()

    @pytest.mark.asyncio
    async def test_store_episode_extraction_failure(self, engine):
        """Test episode storage when extraction fails"""
        
        dialog_content = "Invalid or too short content"
        
        # Mock failed extraction
        mock_extraction_result = {
            'success': False,
            'error': 'Text too short for meaningful extraction',
            'data': {},
            'confidence': 0.0
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Test the store_episode method
        result = await engine.store_episode(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == False
        assert "Failed to extract episode information" in result.message
        assert result.operation == "store_episode"

    @pytest.mark.asyncio
    async def test_store_episode_with_minimal_dialog(self, engine):
        """Test episode storage with minimal dialog content"""
        
        dialog_content = """
        Human: What's the weather like?
        AI: I don't have access to current weather data.
        """
        
        # Mock extraction with minimal results
        mock_extraction_result = {
            'success': True,
            'data': {
                'event_type': 'question_answering',
                'clean_content': 'User asked about weather, AI explained lack of access to weather data.',
                'location': None,
                'participants': [],
                'emotional_valence': 0.0,
                'vividness': 0.3,
                'importance_score': 0.2,
                'key_topics': ['weather'],
                'outcomes': ['information provided']
            },
            'confidence': 0.6
        }
        
        mock_entities_result = {
            'success': True,
            'data': {'entities': {}}
        }
        
        mock_sentiment_result = {
            'success': True,
            'data': {
                'overall_sentiment': {
                    'label': 'neutral',
                    'score': 0.1
                }
            }
        }
        
        # Configure mocks
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine.text_extractor.extract_entities.return_value = mock_entities_result
        engine.text_extractor.analyze_sentiment.return_value = mock_sentiment_result
        
        # Mock database
        engine.db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{'id': 'minimal_memory_id', 'user_id': 'user123'}]
        )
        
        # Test
        result = await engine.store_episode(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == True
        assert result.operation == "store"

    @pytest.mark.asyncio
    async def test_store_episode_with_complex_dialog(self, engine):
        """Test episode storage with complex multi-turn dialog"""
        
        complex_dialog = """
        Human: I need help organizing our project retrospective meeting. The team includes Sarah from design, Mike from backend, Lisa from frontend, and John from QA. We're meeting in the main conference room tomorrow at 2 PM to discuss what went well and what we can improve for next sprint.
        
        AI: I'd be happy to help you organize your project retrospective! Based on what you've shared, this sounds like an important team gathering. Here's a suggested agenda structure:

        1. What went well (15 minutes)
        2. What could be improved (15 minutes) 
        3. Action items for next sprint (15 minutes)
        4. Team feedback and discussion (15 minutes)

        With Sarah, Mike, Lisa, and John participating, you'll have great cross-functional representation. The main conference room should work well for this size group.

        Human: That's perfect! Can you also suggest some specific questions we should ask during each section?

        AI: Absolutely! Here are some specific questions for each section:

        **What went well:**
        - Which processes or tools helped us be most productive?
        - What collaboration patterns worked best between design, backend, frontend, and QA?
        - Which deliverables are we most proud of this sprint?

        **What could be improved:**
        - Where did we experience bottlenecks or delays?
        - What communication gaps did we notice?
        - Which processes slowed us down or created friction?

        **Action items for next sprint:**
        - What's one process change we want to try?
        - How can we improve handoffs between teams?
        - What tools or resources do we need?

        This should help facilitate a productive discussion with your team!
        """
        
        # Mock comprehensive extraction
        mock_extraction_result = {
            'success': True,
            'data': {
                'event_type': 'meeting_planning',
                'clean_content': 'Team planned project retrospective meeting with cross-functional members including design, backend, frontend, and QA teams. Discussed agenda structure and facilitation questions.',
                'location': 'main conference room',
                'participants': ['Sarah', 'Mike', 'Lisa', 'John'],
                'emotional_valence': 0.7,
                'vividness': 0.9,
                'importance_score': 0.8,
                'key_topics': ['project retrospective', 'team meeting', 'sprint planning', 'cross-functional collaboration'],
                'outcomes': ['agenda created', 'meeting structured', 'questions prepared']
            },
            'confidence': 0.9
        }
        
        mock_entities_result = {
            'success': True,
            'data': {
                'entities': {
                    'PERSON': [
                        {'name': 'Sarah', 'confidence': 0.95},
                        {'name': 'Mike', 'confidence': 0.95},
                        {'name': 'Lisa', 'confidence': 0.95},
                        {'name': 'John', 'confidence': 0.95}
                    ],
                    'LOCATION': [
                        {'name': 'main conference room', 'confidence': 0.9}
                    ],
                    'TIME': [
                        {'name': 'tomorrow at 2 PM', 'confidence': 0.8}
                    ]
                }
            }
        }
        
        mock_sentiment_result = {
            'success': True,
            'data': {
                'overall_sentiment': {
                    'label': 'positive',
                    'score': 0.7
                }
            }
        }
        
        # Configure mocks
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine.text_extractor.extract_entities.return_value = mock_entities_result
        engine.text_extractor.analyze_sentiment.return_value = mock_sentiment_result
        
        # Mock database
        engine.db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{'id': 'complex_memory_id', 'user_id': 'user123'}]
        )
        
        # Test
        result = await engine.store_episode(
            user_id="user123",
            dialog_content=complex_dialog,
            importance_score=0.9
        )
        
        # Assertions
        assert result.success == True
        assert result.operation == "store"
        
        # Verify comprehensive analysis was performed
        engine.text_extractor.extract_key_information.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_extracted_data_validation(self, engine):
        """Test data processing and validation"""
        
        # Test data with various edge cases
        raw_data = {
            'event_type': 'Team Meeting',  # Should be normalized
            'clean_content': '',  # Should fallback to original
            'location': 'None',  # Should be filtered out
            'participants': 'Alice, Bob, AI, assistant',  # Should filter AI references
            'emotional_valence': 1.5,  # Should be clamped
            'vividness': -0.1,  # Should be clamped
            'importance_score': 'invalid',  # Should default
        }
        
        original_content = "This is the original dialog content for fallback."
        
        # Test the processing method directly
        processed = await engine._process_extracted_data(raw_data, original_content)
        
        # Assertions
        assert processed['event_type'] == 'team_meeting'  # Normalized
        assert len(processed['clean_content']) > 10  # Fallback worked
        assert processed['location'] is None  # Filtered out 'None'
        assert 'Alice' in processed['participants']
        assert 'Bob' in processed['participants']
        assert 'AI' not in processed['participants']  # Filtered out
        assert 'assistant' not in processed['participants']  # Filtered out
        assert processed['emotional_valence'] == 1.0  # Clamped
        assert processed['vividness'] == 0.0  # Clamped
        assert processed['importance_score'] == 0.5  # Defaulted

    def test_engine_properties(self, engine):
        """Test engine basic properties"""
        assert engine.table_name == "episodic_memories"
        assert engine.memory_type == "episodic"

    @pytest.mark.asyncio
    async def test_search_episodes_by_event_type(self, engine):
        """Test searching episodes by event type"""
        
        # Mock database response
        mock_episodes_data = [
            {
                'id': 'episode1',
                'user_id': 'user123',
                'event_type': 'planning_session',
                'content': 'Planning meeting content',
                'location': 'Conference Room A',
                'participants': '["Alice", "Bob"]',
                'emotional_valence': 0.6,
                'vividness': 0.8,
                'episode_date': '2024-01-15T10:00:00',
                'importance_score': 0.7,
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            },
            {
                'id': 'episode2',
                'user_id': 'user123',
                'event_type': 'planning_session',
                'content': 'Another planning session',
                'location': 'Office',
                'participants': '["Carol"]',
                'emotional_valence': 0.5,
                'vividness': 0.7,
                'episode_date': '2024-01-14T14:00:00',
                'importance_score': 0.6,
                'embedding': '[0.2, 0.3, 0.4]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_episodes_data
        )
        
        # Test search
        episodes = await engine.search_episodes_by_event_type(
            user_id="user123",
            event_type="planning_session",
            limit=5
        )
        
        # Assertions
        assert len(episodes) == 2
        assert all(episode.event_type == "planning_session" for episode in episodes)
        assert episodes[0].id == "episode1"
        assert episodes[1].id == "episode2"

    @pytest.mark.asyncio
    async def test_search_episodes_by_participant(self, engine):
        """Test searching episodes by participant"""
        
        # Mock database response with multiple episodes
        mock_episodes_data = [
            {
                'id': 'episode1',
                'user_id': 'user123',
                'event_type': 'meeting',
                'content': 'Meeting with Alice',
                'location': 'Office',
                'participants': '["Alice", "Bob"]',
                'emotional_valence': 0.5,
                'vividness': 0.6,
                'episode_date': '2024-01-15T10:00:00',
                'importance_score': 0.5,
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            },
            {
                'id': 'episode2',
                'user_id': 'user123',
                'event_type': 'call',
                'content': 'Call without Alice',
                'location': None,
                'participants': '["Bob", "Carol"]',
                'emotional_valence': 0.3,
                'vividness': 0.4,
                'episode_date': '2024-01-14T14:00:00',
                'importance_score': 0.4,
                'embedding': '[0.2, 0.3, 0.4]',
                'context': '{}',
                'tags': '[]'
            },
            {
                'id': 'episode3',
                'user_id': 'user123',
                'event_type': 'planning',
                'content': 'Planning with Alice',
                'location': 'Conference Room',
                'participants': '["Alice", "Carol"]',
                'emotional_valence': 0.7,
                'vividness': 0.8,
                'episode_date': '2024-01-13T09:00:00',
                'importance_score': 0.8,
                'embedding': '[0.3, 0.4, 0.5]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=mock_episodes_data
        )
        
        # Test search for episodes with Alice
        episodes = await engine.search_episodes_by_participant(
            user_id="user123",
            participant="Alice",
            limit=5
        )
        
        # Assertions
        assert len(episodes) == 2  # Only episodes 1 and 3 have Alice
        assert all("Alice" in episode.participants for episode in episodes)
        assert episodes[0].id == "episode1"
        assert episodes[1].id == "episode3"

    @pytest.mark.asyncio
    async def test_search_episodes_by_location(self, engine):
        """Test searching episodes by location"""
        
        # Mock database response
        mock_episodes_data = [
            {
                'id': 'episode1',
                'user_id': 'user123',
                'event_type': 'meeting',
                'content': 'Conference room meeting',
                'location': 'Conference Room A',
                'participants': '["Alice"]',
                'emotional_valence': 0.5,
                'vividness': 0.6,
                'episode_date': '2024-01-15T10:00:00',
                'importance_score': 0.5,
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_episodes_data
        )
        
        # Test search
        episodes = await engine.search_episodes_by_location(
            user_id="user123",
            location="Conference",
            limit=5
        )
        
        # Assertions
        assert len(episodes) == 1
        assert "Conference Room A" in episodes[0].location

    @pytest.mark.asyncio
    async def test_search_episodes_by_timeframe(self, engine):
        """Test searching episodes by timeframe"""
        
        # Mock database response
        mock_episodes_data = [
            {
                'id': 'episode1',
                'user_id': 'user123',
                'event_type': 'meeting',
                'content': 'Meeting in timeframe',
                'location': 'Office',
                'participants': '["Alice"]',
                'emotional_valence': 0.5,
                'vividness': 0.6,
                'episode_date': '2024-01-15T10:00:00',
                'importance_score': 0.5,
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_episodes_data
        )
        
        # Test search
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        episodes = await engine.search_episodes_by_timeframe(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            limit=5
        )
        
        # Assertions
        assert len(episodes) == 1
        assert episodes[0].id == "episode1"

    @pytest.mark.asyncio
    async def test_search_episodes_by_emotional_tone(self, engine):
        """Test searching episodes by emotional valence"""
        
        # Mock database response with different emotional valences
        mock_episodes_data = [
            {
                'id': 'positive_episode',
                'user_id': 'user123',
                'event_type': 'celebration',
                'content': 'Positive episode',
                'location': 'Office',
                'participants': '["Alice"]',
                'emotional_valence': 0.8,
                'vividness': 0.9,
                'episode_date': '2024-01-15T10:00:00',
                'importance_score': 0.7,
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_episodes_data
        )
        
        # Test search for positive episodes
        episodes = await engine.search_episodes_by_emotional_tone(
            user_id="user123",
            min_valence=0.5,
            max_valence=1.0,
            limit=5
        )
        
        # Assertions
        assert len(episodes) == 1
        assert episodes[0].emotional_valence >= 0.5
        assert episodes[0].id == "positive_episode"

    @pytest.mark.asyncio
    async def test_search_episodes_by_importance(self, engine):
        """Test searching episodes by importance score"""
        
        # Mock database response
        mock_episodes_data = [
            {
                'id': 'important_episode',
                'user_id': 'user123',
                'event_type': 'critical_meeting',
                'content': 'Very important episode',
                'location': 'Boardroom',
                'participants': '["CEO", "CTO"]',
                'emotional_valence': 0.6,
                'vividness': 0.9,
                'episode_date': '2024-01-15T10:00:00',
                'importance_score': 0.9,
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_episodes_data
        )
        
        # Test search for high-importance episodes
        episodes = await engine.search_episodes_by_importance(
            user_id="user123",
            min_importance=0.8,
            limit=5
        )
        
        # Assertions
        assert len(episodes) == 1
        assert episodes[0].importance_score >= 0.8
        assert episodes[0].id == "important_episode"

    @pytest.mark.asyncio
    async def test_search_methods_error_handling(self, engine):
        """Test error handling in search methods"""
        
        # Mock database error
        engine.db.table.return_value.select.side_effect = Exception("Database error")
        
        # Test all search methods handle errors gracefully
        result1 = await engine.search_episodes_by_event_type("user123", "meeting")
        assert result1 == []
        
        result2 = await engine.search_episodes_by_participant("user123", "Alice")
        assert result2 == []
        
        result3 = await engine.search_episodes_by_location("user123", "Office")
        assert result3 == []
        
        result4 = await engine.search_episodes_by_timeframe(
            "user123", 
            datetime(2024, 1, 1), 
            datetime(2024, 1, 31)
        )
        assert result4 == []
        
        result5 = await engine.search_episodes_by_emotional_tone("user123", 0.0, 1.0)
        assert result5 == []
        
        result6 = await engine.search_episodes_by_importance("user123", 0.5)
        assert result6 == []

    @pytest.mark.asyncio
    async def test_search_empty_results(self, engine):
        """Test search methods with empty results"""
        
        # Mock empty database response
        engine.db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        # Test search with no results
        episodes = await engine.search_episodes_by_event_type(
            user_id="user123",
            event_type="nonexistent_type"
        )
        
        # Assertions
        assert len(episodes) == 0
        assert isinstance(episodes, list)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])