#!/usr/bin/env python3
"""
Tests for Session Memory Engine with Intelligent Dialog Processing and Summarization
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tools.services.memory_service.engines.session_engine import SessionMemoryEngine
from tools.services.memory_service.models import MemoryOperationResult


class TestSessionMemoryEngine:
    """Test suite for intelligent session memory processing"""

    @pytest.fixture
    def engine(self):
        """Create a mock session engine for testing"""
        with patch('tools.services.memory_service.engines.base_engine.get_supabase_client') as mock_db, \
             patch('tools.services.memory_service.engines.base_engine.EmbeddingGenerator') as mock_embedder, \
             patch('tools.services.intelligence_service.language.text_extractor.TextExtractor') as mock_extractor, \
             patch('tools.services.intelligence_service.language.text_summarizer.TextSummarizer') as mock_summarizer:
            
            # Mock database
            mock_db.return_value = MagicMock()
            
            # Mock embedder
            mock_embedder_instance = AsyncMock()
            mock_embedder.return_value = mock_embedder_instance
            mock_embedder_instance.embed_single.return_value = [0.1, 0.2, 0.3]
            
            # Mock text extractor
            mock_extractor_instance = AsyncMock()
            mock_extractor.return_value = mock_extractor_instance
            
            # Mock text summarizer
            mock_summarizer_instance = AsyncMock()
            mock_summarizer.return_value = mock_summarizer_instance
            
            engine = SessionMemoryEngine()
            engine.db = mock_db.return_value
            engine.embedder = mock_embedder_instance
            engine.text_extractor = mock_extractor_instance
            engine.text_summarizer = mock_summarizer_instance
            
            return engine

    @pytest.mark.asyncio
    async def test_store_session_message_successful(self, engine):
        """Test successful session message storage with intelligent processing"""
        
        # Mock message content
        message_content = "Hello! I'm working on a Python data analysis project and need help with pandas."
        user_id = str(uuid.uuid4())
        session_id = "test_session_123"
        
        # Mock extraction results
        mock_extraction_result = {
            'success': True,
            'data': {
                'main_topics': ['Python', 'data analysis', 'pandas'],
                'questions_asked': ['need help with pandas'],
                'requests_made': ['help with data analysis project'],
                'entities_mentioned': ['Python', 'pandas'],
                'emotional_tone': 'friendly and seeking help',
                'sentiment': {
                    'overall_sentiment': {'label': 'positive', 'score': 0.8},
                    'confidence': 0.9
                }
            },
            'confidence': 0.9
        }
        
        # Configure text extractor mock
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Mock database insertion
        mock_db_result = MagicMock()
        mock_db_result.data = [{'id': 'msg_123'}]
        engine.db.table.return_value.insert.return_value.execute.return_value = mock_db_result
        
        # Mock summarization check (no summarization needed)
        engine._check_and_summarize_session = AsyncMock()
        
        # Test the store_session_message method
        result = await engine.store_session_message(
            user_id=user_id,
            session_id=session_id,
            message_content=message_content,
            message_type="human",
            role="user"
        )
        
        # Assertions
        assert result.success == True
        assert result.memory_id == "msg_123"
        assert result.operation == "store_session_message"
        assert "stored successfully" in result.message
        
        # Verify text extractor was called
        engine.text_extractor.extract_key_information.assert_called_once()
        
        # Verify database insertion was called
        engine.db.table.assert_called_with("session_messages")
        
        # Verify summarization check was called
        engine._check_and_summarize_session.assert_called_once_with(user_id, session_id)

    @pytest.mark.asyncio
    async def test_store_session_message_extraction_failure(self, engine):
        """Test session message storage when extraction fails"""
        
        message_content = "Short"
        user_id = str(uuid.uuid4())
        session_id = "test_session_123"
        
        # Mock failed extraction
        mock_extraction_result = {
            'success': False,
            'error': 'Text too short for meaningful extraction',
            'data': {},
            'confidence': 0.0
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Mock database insertion
        mock_db_result = MagicMock()
        mock_db_result.data = [{'id': 'msg_123'}]
        engine.db.table.return_value.insert.return_value.execute.return_value = mock_db_result
        
        # Mock summarization check
        engine._check_and_summarize_session = AsyncMock()
        
        # Test the store_session_message method
        result = await engine.store_session_message(
            user_id=user_id,
            session_id=session_id,
            message_content=message_content
        )
        
        # Assertions - should still succeed even with extraction failure
        assert result.success == True
        assert result.memory_id == "msg_123"

    @pytest.mark.asyncio
    async def test_get_session_messages(self, engine):
        """Test retrieving session messages"""
        
        user_id = str(uuid.uuid4())
        session_id = "test_session_123"
        
        # Mock database response
        mock_messages_data = [
            {
                'id': 'msg_1',
                'session_id': session_id,
                'user_id': user_id,
                'message_type': 'human',
                'role': 'user',
                'content': 'Hello, I need help with Python.',
                'message_metadata': json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'entities': {'Python': {'confidence': 0.9}},
                    'sentiment': {'label': 'positive', 'score': 0.8}
                }),
                'importance_score': 0.7,
                'created_at': datetime.now().isoformat()
            },
            {
                'id': 'msg_2',
                'session_id': session_id,
                'user_id': user_id,
                'message_type': 'ai',
                'role': 'assistant',
                'content': 'I can help you with Python! What specific area?',
                'message_metadata': json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'entities': {'Python': {'confidence': 0.9}},
                    'sentiment': {'label': 'positive', 'score': 0.9}
                }),
                'importance_score': 0.8,
                'created_at': datetime.now().isoformat()
            }
        ]
        
        # Mock database query
        mock_db_result = MagicMock()
        mock_db_result.data = mock_messages_data
        engine.db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_db_result
        
        # Test get_session_messages
        messages = await engine.get_session_messages(user_id, session_id)
        
        # Assertions
        assert len(messages) == 2
        assert messages[0]['id'] == 'msg_1'
        assert messages[1]['id'] == 'msg_2'
        assert isinstance(messages[0]['message_metadata'], dict)  # Should be parsed from JSON
        assert isinstance(messages[1]['message_metadata'], dict)

    @pytest.mark.asyncio
    async def test_summarize_session_successful(self, engine):
        """Test successful session summarization"""
        
        user_id = str(uuid.uuid4())
        session_id = "test_session_123"
        
        # Mock session messages
        mock_messages = [
            {
                'id': 'msg_1',
                'user_id': user_id,
                'session_id': session_id,
                'role': 'user',
                'content': 'Hello, I need help with Python data analysis.',
                'created_at': datetime.now().isoformat(),
                'is_summary_candidate': True
            },
            {
                'id': 'msg_2',
                'user_id': user_id,
                'session_id': session_id,
                'role': 'assistant',
                'content': 'I can help you with Python data analysis! What specific area?',
                'created_at': datetime.now().isoformat(),
                'is_summary_candidate': True
            }
        ]
        
        # Mock get_session_messages
        engine.get_session_messages = AsyncMock(return_value=mock_messages)
        
        # Mock summarization check
        engine._should_summarize_session_messages = AsyncMock(return_value=True)
        
        # Mock summary generation
        mock_summary_result = {
            'success': True,
            'summary': 'User requested help with Python data analysis and received assistance.',
            'style': 'narrative',
            'length': 'medium',
            'word_count': 12,
            'compression_ratio': 0.3,
            'quality_score': 0.85
        }
        
        engine.text_summarizer.summarize_text.return_value = mock_summary_result
        
        # Mock key points extraction
        mock_key_points_result = {
            'success': True,
            'key_points': [
                'User needs help with Python data analysis',
                'Assistant offered to help with specific areas'
            ],
            'total_points': 2
        }
        
        engine.text_summarizer.extract_key_points.return_value = mock_key_points_result
        
        # Mock database operations
        mock_existing_result = MagicMock()
        mock_existing_result.data = []  # No existing session memory
        
        mock_insert_result = MagicMock()
        mock_insert_result.data = [{'id': 'session_summary_123'}]
        
        engine.db.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing_result
        engine.db.table.return_value.insert.return_value.execute.return_value = mock_insert_result
        
        # Mock message marking
        engine._mark_messages_as_summarized = AsyncMock()
        
        # Test summarize_session
        result = await engine.summarize_session(
            user_id=user_id,
            session_id=session_id,
            force_update=True
        )
        
        # Assertions
        assert result.success == True
        assert result.memory_id == "session_summary_123"
        assert result.operation == "summarize_session"
        assert "summarized successfully" in result.message
        assert result.data['original_message_count'] == 2
        assert result.data['compression_ratio'] == 0.3
        assert result.data['quality_score'] == 0.85

    @pytest.mark.asyncio
    async def test_summarize_session_no_messages(self, engine):
        """Test summarization when no messages exist"""
        
        user_id = str(uuid.uuid4())
        session_id = "test_session_123"
        
        # Mock get_session_messages to return empty list
        engine.get_session_messages = AsyncMock(return_value=[])
        
        # Test summarize_session
        result = await engine.summarize_session(
            user_id=user_id,
            session_id=session_id
        )
        
        # Assertions
        assert result.success == False
        assert "No messages found" in result.message

    @pytest.mark.asyncio
    async def test_get_session_context_with_summary(self, engine):
        """Test getting session context with summary"""
        
        user_id = str(uuid.uuid4())
        session_id = "test_session_123"
        
        # Mock session messages
        mock_messages = [
            {
                'id': 'msg_1',
                'role': 'user',
                'content': 'Hello, I need help with Python.',
                'created_at': datetime.now().isoformat(),
                'message_type': 'human',
                'is_summary_candidate': True,
                'importance_score': 0.7,
                'message_metadata': json.dumps({
                    'entities': {'Python': {'confidence': 0.9}},
                    'sentiment': {'label': 'positive', 'score': 0.8}
                })
            }
        ]
        
        # Mock session memory (summary)
        mock_session_memory = {
            'id': 'session_123',
            'conversation_summary': 'User requested help with Python programming.',
            'last_summary_at': datetime.now().isoformat(),
            'total_messages': 2,
            'key_decisions': json.dumps(['Help with Python programming']),
            'session_metadata': json.dumps({
                'quality_score': 0.85,
                'compression_ratio': 0.3
            })
        }
        
        # Mock methods
        engine.get_session_messages = AsyncMock(return_value=mock_messages)
        engine._get_session_memory = AsyncMock(return_value=mock_session_memory)
        
        # Test get_session_context
        context = await engine.get_session_context(
            user_id=user_id,
            session_id=session_id,
            include_summaries=True
        )
        
        # Assertions
        assert context['success'] == True
        assert context['session_id'] == session_id
        assert context['total_messages'] == 1
        assert context['summary_available'] == True
        assert 'summary' in context
        assert context['summary']['content'] == 'User requested help with Python programming.'
        assert len(context['recent_messages']) == 1

    @pytest.mark.asyncio
    async def test_get_session_context_no_session(self, engine):
        """Test getting context when no session exists"""
        
        user_id = str(uuid.uuid4())
        session_id = "nonexistent_session"
        
        # Mock get_session_messages to return empty list
        engine.get_session_messages = AsyncMock(return_value=[])
        
        # Test get_session_context
        context = await engine.get_session_context(user_id, session_id)
        
        # Assertions
        assert context['success'] == False
        assert "No session found" in context['error']

    @pytest.mark.asyncio
    async def test_should_summarize_session_messages(self, engine):
        """Test summarization trigger logic"""
        
        user_id = str(uuid.uuid4())
        session_id = "test_session_123"
        
        # Create mock messages that should trigger summarization
        mock_messages = []
        for i in range(12):  # More than summary_trigger_count (10)
            mock_messages.append({
                'id': f'msg_{i}',
                'user_id': user_id,
                'session_id': session_id,
                'content': f'Message {i}' * 10,  # Make it longer
                'is_summary_candidate': True
            })
        
        # Mock _get_session_memory to return None (no previous summary)
        engine._get_session_memory = AsyncMock(return_value=None)
        
        # Test should_summarize_session_messages
        should_summarize = await engine._should_summarize_session_messages(mock_messages)
        
        # Assertions
        assert should_summarize == True  # Should trigger due to message count

    @pytest.mark.asyncio
    async def test_should_not_summarize_session_messages(self, engine):
        """Test when summarization should not be triggered"""
        
        user_id = str(uuid.uuid4())
        session_id = "test_session_123"
        
        # Create mock messages that should NOT trigger summarization
        mock_messages = []
        for i in range(3):  # Less than summary_trigger_count (10)
            mock_messages.append({
                'id': f'msg_{i}',
                'user_id': user_id,
                'session_id': session_id,
                'content': f'Short message {i}',
                'is_summary_candidate': True
            })
        
        # Mock _get_session_memory to return None (no previous summary)
        engine._get_session_memory = AsyncMock(return_value=None)
        
        # Test should_summarize_session_messages
        should_summarize = await engine._should_summarize_session_messages(mock_messages)
        
        # Assertions
        assert should_summarize == False  # Should not trigger

    @pytest.mark.asyncio
    async def test_build_conversation_text_from_messages(self, engine):
        """Test building conversation text from messages"""
        
        # Mock messages with different roles
        mock_messages = [
            {
                'role': 'user',
                'content': 'Hello, I need help with Python.',
                'created_at': '2024-01-01T10:00:00Z'
            },
            {
                'role': 'assistant',
                'content': 'I can help you with Python! What do you need?',
                'created_at': '2024-01-01T10:01:00Z'
            },
            {
                'role': 'user',
                'content': 'I want to learn about data analysis.',
                'created_at': '2024-01-01T10:02:00Z'
            }
        ]
        
        # Test _build_conversation_text_from_messages
        conversation_text = engine._build_conversation_text_from_messages(mock_messages)
        
        # Assertions
        assert "User: Hello, I need help with Python." in conversation_text
        assert "Assistant: I can help you with Python! What do you need?" in conversation_text
        assert "User: I want to learn about data analysis." in conversation_text
        assert conversation_text.count("User:") == 2
        assert conversation_text.count("Assistant:") == 1

    @pytest.mark.asyncio
    async def test_extract_message_info_user_message(self, engine):
        """Test extracting information from user message"""
        
        message_content = "I need help with Python data analysis and visualization."
        message_type = "human"
        
        # Mock extraction result
        mock_extraction_result = {
            'success': True,
            'data': {
                'main_topics': ['Python', 'data analysis', 'visualization'],
                'questions_asked': [],
                'requests_made': ['help with Python data analysis and visualization'],
                'entities_mentioned': ['Python'],
                'emotional_tone': 'seeking help'
            },
            'confidence': 0.8
        }
        
        # Mock sentiment analysis result
        mock_sentiment_result = {
            'success': True,
            'data': {
                'overall_sentiment': {'label': 'neutral', 'score': 0.7},
                'confidence': 0.8
            }
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine.text_extractor.analyze_sentiment.return_value = mock_sentiment_result
        
        # Test _extract_message_info
        result = await engine._extract_message_info(message_content, message_type)
        
        # Assertions
        assert result['success'] == True
        assert result['confidence'] == 0.8
        assert 'main_topics' in result['data']
        assert 'sentiment' in result['data']
        assert result['data']['main_topics'] == ['Python', 'data analysis', 'visualization']

    @pytest.mark.asyncio
    async def test_extract_message_info_ai_message(self, engine):
        """Test extracting information from AI message"""
        
        message_content = "I can help you with Python data analysis. Let me show you some examples."
        message_type = "ai"
        
        # Mock extraction result
        mock_extraction_result = {
            'success': True,
            'data': {
                'main_topics': ['Python', 'data analysis', 'examples'],
                'information_provided': ['help with Python data analysis'],
                'suggestions_made': ['show examples'],
                'questions_answered': [],
                'follow_up_needed': False
            },
            'confidence': 0.9
        }
        
        # Mock sentiment analysis result
        mock_sentiment_result = {
            'success': True,
            'data': {
                'overall_sentiment': {'label': 'positive', 'score': 0.9},
                'confidence': 0.9
            }
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine.text_extractor.analyze_sentiment.return_value = mock_sentiment_result
        
        # Test _extract_message_info
        result = await engine._extract_message_info(message_content, message_type)
        
        # Assertions
        assert result['success'] == True
        assert result['confidence'] == 0.9
        assert 'main_topics' in result['data']
        assert 'sentiment' in result['data']
        assert result['data']['suggestions_made'] == ['show examples']

    @pytest.mark.asyncio
    async def test_error_handling_database_failure(self, engine):
        """Test error handling when database operations fail"""
        
        user_id = str(uuid.uuid4())
        session_id = "test_session_123"
        message_content = "Test message"
        
        # Mock extraction success
        mock_extraction_result = {
            'success': True,
            'data': {'main_topics': ['test']},
            'confidence': 0.8
        }
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Mock database failure
        engine.db.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        
        # Test store_session_message
        result = await engine.store_session_message(
            user_id=user_id,
            session_id=session_id,
            message_content=message_content
        )
        
        # Assertions
        assert result.success == False
        assert "Failed to store session message" in result.message

    def test_engine_properties(self, engine):
        """Test engine basic properties"""
        assert engine.table_name == "session_memories"
        assert engine.messages_table_name == "session_messages"
        assert engine.memory_type == "session"
        assert engine.summary_trigger_count == 10
        assert engine.max_session_length == 10000


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])