#!/usr/bin/env python3
"""
Tests for Factual Memory Engine with Intelligent Dialog Processing
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tools.services.memory_service.engines.factual_engine import FactualMemoryEngine
from tools.services.memory_service.models import MemoryOperationResult, FactualMemory


class TestFactualMemoryEngine:
    """Test suite for intelligent factual memory processing"""

    @pytest.fixture
    def engine(self):
        """Create a mock factual engine for testing"""
        with patch('tools.services.memory_service.engines.base_engine.get_supabase_client') as mock_db, \
             patch('tools.services.memory_service.engines.base_engine.EmbeddingGenerator') as mock_embedder, \
             patch('tools.services.memory_service.engines.factual_engine.TextExtractor') as mock_extractor:
            
            # Mock database
            mock_db.return_value = MagicMock()
            
            # Mock embedder
            mock_embedder_instance = AsyncMock()
            mock_embedder.return_value = mock_embedder_instance
            mock_embedder_instance.embed_single.return_value = [0.1, 0.2, 0.3]
            
            # Mock text extractor
            mock_extractor_instance = AsyncMock()
            mock_extractor.return_value = mock_extractor_instance
            
            engine = FactualMemoryEngine()
            engine.db = mock_db.return_value
            engine.embedder = mock_embedder_instance
            engine.text_extractor = mock_extractor_instance
            
            return engine

    @pytest.mark.asyncio
    async def test_store_factual_memory_successful_extraction(self, engine):
        """Test successful factual memory storage with intelligent extraction"""
        
        # Mock dialog content with factual information
        dialog_content = """
        Human: I'm a software engineer at Google, and I specialize in machine learning. My favorite programming language is Python, and I've been working there for 3 years.
        
        AI: That's great! Machine learning is a fascinating field. Python is indeed an excellent choice for ML work, especially with libraries like TensorFlow and PyTorch. How do you like working at Google?
        """
        
        # Mock extraction results
        mock_extraction_result = {
            'success': True,
            'data': {
                'facts': [
                    {
                        'fact_type': 'personal_info',
                        'subject': 'user',
                        'predicate': 'works_at',
                        'object_value': 'Google',
                        'context': 'employment',
                        'confidence': 0.9
                    },
                    {
                        'fact_type': 'skill',
                        'subject': 'user',
                        'predicate': 'specializes_in',
                        'object_value': 'machine learning',
                        'context': 'professional expertise',
                        'confidence': 0.9
                    },
                    {
                        'fact_type': 'preference',
                        'subject': 'user',
                        'predicate': 'prefers_language',
                        'object_value': 'Python',
                        'context': 'programming',
                        'confidence': 0.8
                    },
                    {
                        'fact_type': 'personal_info',
                        'subject': 'user',
                        'predicate': 'work_duration',
                        'object_value': '3 years',
                        'context': 'at Google',
                        'confidence': 0.9
                    }
                ],
                'source': 'user_statement',
                'domain': 'technology',
                'extraction_confidence': 0.85
            },
            'confidence': 0.85
        }
        
        # Configure text extractor mock
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Mock database insertion
        engine.db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{'id': 'fact_memory_id', 'user_id': 'user123'}]
        )
        
        # Mock _find_existing_fact to return None (no existing facts)
        engine._find_existing_fact = AsyncMock(return_value=None)
        
        # Test the store_factual_memory method
        result = await engine.store_factual_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == True
        assert result.operation == "store_factual_memory"
        assert "4 factual memories" in result.message
        assert result.data['total_facts'] == 4
        
        # Verify text extractor was called
        engine.text_extractor.extract_key_information.assert_called_once()
        
        # Verify embedding generation
        engine.embedder.embed_single.assert_called()

    @pytest.mark.asyncio
    async def test_store_factual_memory_extraction_failure(self, engine):
        """Test factual memory storage when extraction fails"""
        
        dialog_content = "Invalid or too short content"
        
        # Mock failed extraction
        mock_extraction_result = {
            'success': False,
            'error': 'Text too short for meaningful extraction',
            'data': {},
            'confidence': 0.0
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Test the store_factual_memory method
        result = await engine.store_factual_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == False
        assert "Failed to extract factual information" in result.message
        assert result.operation == "store_factual_memory"

    @pytest.mark.asyncio
    async def test_store_factual_memory_with_existing_fact(self, engine):
        """Test factual memory storage with existing fact merging"""
        
        dialog_content = """
        Human: Actually, I've been working at Google for 4 years now, not 3.
        AI: Thanks for the correction! I'll update that information.
        """
        
        # Mock extraction result
        mock_extraction_result = {
            'success': True,
            'data': {
                'facts': [
                    {
                        'fact_type': 'personal_info',
                        'subject': 'user',
                        'predicate': 'work_duration',
                        'object_value': '4 years',
                        'context': 'at Google',
                        'confidence': 0.9
                    }
                ],
                'source': 'user_correction',
                'domain': 'personal',
                'extraction_confidence': 0.9
            },
            'confidence': 0.9
        }
        
        # Mock existing fact
        existing_fact = FactualMemory(
            id="existing_fact_id",
            user_id="user123",
            content="user work_duration 3 years (at Google)",
            memory_type="factual",
            fact_type="personal_info",
            subject="user",
            predicate="work_duration",
            object_value="3 years",
            confidence=0.8,
            importance_score=0.5,
            access_count=1,
            source="user_statement",
            verification_status="unverified",
            embedding=[0.1, 0.2, 0.3]
        )
        
        # Configure mocks
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine._find_existing_fact = AsyncMock(return_value=existing_fact)
        engine._merge_factual_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="existing_fact_id",
            operation="merge",
            message="Factual memory merged and updated"
        ))
        
        # Test
        result = await engine.store_factual_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == True
        assert result.operation == "store_factual_memory"
        assert "1 factual memories" in result.message
        
        # Verify merge was called
        engine._merge_factual_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_facts_by_subject(self, engine):
        """Test searching facts by subject"""
        
        # Mock database response
        mock_facts_data = [
            {
                'id': 'fact1',
                'user_id': 'user123',
                'content': 'user works_at Google',
                'memory_type': 'factual',
                'fact_type': 'personal_info',
                'subject': 'user',
                'predicate': 'works_at',
                'object_value': 'Google',
                'confidence': 0.9,
                'importance_score': 0.8,
                'access_count': 1,
                'source': 'user_statement',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]',
                'related_facts': '[]'
            },
            {
                'id': 'fact2',
                'user_id': 'user123',
                'content': 'user specializes_in machine learning',
                'memory_type': 'factual',
                'fact_type': 'skill',
                'subject': 'user',
                'predicate': 'specializes_in',
                'object_value': 'machine learning',
                'confidence': 0.8,
                'importance_score': 0.7,
                'access_count': 1,
                'source': 'user_statement',
                'verification_status': 'unverified',
                'embedding': '[0.2, 0.3, 0.4]',
                'context': '{}',
                'tags': '[]',
                'related_facts': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_facts_data
        )
        
        # Test search
        facts = await engine.search_facts_by_subject(
            user_id="user123",
            subject="user",
            limit=5
        )
        
        # Assertions
        assert len(facts) == 2
        assert facts[0].subject == "user"
        assert facts[1].subject == "user"

    @pytest.mark.asyncio
    async def test_search_facts_by_fact_type(self, engine):
        """Test searching facts by fact type"""
        
        # Mock database response
        mock_facts_data = [
            {
                'id': 'fact1',
                'user_id': 'user123',
                'content': 'user knows Python',
                'memory_type': 'factual',
                'fact_type': 'skill',
                'subject': 'user',
                'predicate': 'knows',
                'object_value': 'Python',
                'confidence': 0.9,
                'importance_score': 0.7,
                'access_count': 1,
                'source': 'user_statement',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]',
                'related_facts': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_facts_data
        )
        
        # Test search
        facts = await engine.search_facts_by_fact_type(
            user_id="user123",
            fact_type="skill",
            limit=5
        )
        
        # Assertions
        assert len(facts) == 1
        assert facts[0].fact_type == "skill"

    @pytest.mark.asyncio
    async def test_search_facts_by_confidence(self, engine):
        """Test searching facts by confidence level"""
        
        # Mock database response
        mock_facts_data = [
            {
                'id': 'high_confidence_fact',
                'user_id': 'user123',
                'content': 'user certified_in AWS',
                'memory_type': 'factual',
                'fact_type': 'verified_info',
                'subject': 'user',
                'predicate': 'certified_in',
                'object_value': 'AWS',
                'confidence': 0.95,
                'importance_score': 0.9,
                'access_count': 1,
                'source': 'certification_body',
                'verification_status': 'verified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]',
                'related_facts': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_facts_data
        )
        
        # Test search for high-confidence facts
        facts = await engine.search_facts_by_confidence(
            user_id="user123",
            min_confidence=0.9,
            limit=5
        )
        
        # Assertions
        assert len(facts) == 1
        assert facts[0].confidence >= 0.9

    @pytest.mark.asyncio
    async def test_search_facts_by_source(self, engine):
        """Test searching facts by source"""
        
        # Mock database response
        mock_facts_data = [
            {
                'id': 'fact1',
                'user_id': 'user123',
                'content': 'company founded_in 1998',
                'memory_type': 'factual',
                'fact_type': 'external_info',
                'subject': 'company',
                'predicate': 'founded_in',
                'object_value': '1998',
                'confidence': 0.8,
                'importance_score': 0.6,
                'access_count': 1,
                'source': 'Wikipedia',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]',
                'related_facts': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_facts_data
        )
        
        # Test search
        facts = await engine.search_facts_by_source(
            user_id="user123",
            source="Wikipedia",
            limit=5
        )
        
        # Assertions
        assert len(facts) == 1
        assert "Wikipedia" in facts[0].source

    @pytest.mark.asyncio
    async def test_search_facts_by_verification(self, engine):
        """Test searching facts by verification status"""
        
        # Mock database response
        mock_facts_data = [
            {
                'id': 'verified_fact',
                'user_id': 'user123',
                'content': 'user has_degree Computer Science',
                'memory_type': 'factual',
                'fact_type': 'credential',
                'subject': 'user',
                'predicate': 'has_degree',
                'object_value': 'Computer Science',
                'confidence': 0.95,
                'importance_score': 0.9,
                'access_count': 1,
                'source': 'university_record',
                'verification_status': 'verified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]',
                'related_facts': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_facts_data
        )
        
        # Test search
        facts = await engine.search_facts_by_verification(
            user_id="user123",
            verification_status="verified",
            limit=5
        )
        
        # Assertions
        assert len(facts) == 1
        assert facts[0].verification_status == "verified"

    @pytest.mark.asyncio
    async def test_process_factual_data_validation(self, engine):
        """Test factual data processing and validation"""
        
        # Test data with various edge cases
        raw_data = {
            'facts': [
                {
                    'fact_type': 'Personal Info',  # Should be normalized
                    'subject': 'user',
                    'predicate': 'works at',
                    'object_value': 'Google Inc.',
                    'context': 'employment info',
                    'confidence': 1.5  # Should be clamped
                },
                {
                    # Missing required fields - should be filtered out
                    'fact_type': 'incomplete',
                    'subject': 'user'
                    # Missing predicate and object_value
                }
            ],
            'source': 'User Statement',
            'domain': 'Technology',
            'extraction_confidence': 'invalid'  # Should default
        }
        
        original_content = "This is the original dialog content for fallback."
        
        # Test the processing method directly
        processed = await engine._process_factual_data(raw_data, original_content)
        
        # Assertions
        assert len(processed['facts']) == 1  # Only valid fact processed
        assert processed['facts'][0]['fact_type'] == 'personal_info'  # Normalized
        assert processed['facts'][0]['confidence'] == 1.0  # Clamped
        assert processed['source'] == 'user_statement'  # Normalized
        assert processed['domain'] == 'technology'  # Normalized
        assert processed['extraction_confidence'] == 0.7  # Defaulted

    @pytest.mark.asyncio
    async def test_extract_basic_facts_fallback(self, engine):
        """Test basic fact extraction when structured extraction fails"""
        
        content = "Python is a programming language. Machine learning is complex. Google has many employees."
        
        # Test basic fact extraction
        basic_facts = engine._extract_basic_facts(content)
        
        # Assertions
        assert len(basic_facts) <= 2  # Limited to 2 facts
        assert any('python' in fact['subject'].lower() for fact in basic_facts)
        assert all(fact['confidence'] == 0.6 for fact in basic_facts)  # Basic confidence

    @pytest.mark.asyncio
    async def test_search_methods_error_handling(self, engine):
        """Test error handling in search methods"""
        
        # Mock database error
        engine.db.table.return_value.select.side_effect = Exception("Database error")
        
        # Test all search methods handle errors gracefully
        result1 = await engine.search_facts_by_subject("user123", "user")
        assert result1 == []
        
        result2 = await engine.search_facts_by_fact_type("user123", "skill")
        assert result2 == []
        
        result3 = await engine.search_facts_by_confidence("user123", 0.8)
        assert result3 == []
        
        result4 = await engine.search_facts_by_source("user123", "source")
        assert result4 == []
        
        result5 = await engine.search_facts_by_verification("user123", "verified")
        assert result5 == []

    def test_engine_properties(self, engine):
        """Test engine basic properties"""
        assert engine.table_name == "factual_memories"
        assert engine.memory_type == "factual"

    def test_process_single_fact_validation(self, engine):
        """Test single fact processing validation"""
        
        # Valid fact
        valid_fact = {
            'subject': 'user',
            'predicate': 'works_at',
            'object_value': 'Google',
            'fact_type': 'employment',
            'confidence': 0.9
        }
        
        processed = engine._process_single_fact(valid_fact)
        assert processed is not None
        assert processed['subject'] == 'user'
        assert processed['confidence'] == 0.9
        
        # Invalid fact (missing required fields)
        invalid_fact = {
            'subject': 'user',
            # Missing predicate and object_value
        }
        
        processed_invalid = engine._process_single_fact(invalid_fact)
        assert processed_invalid is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])