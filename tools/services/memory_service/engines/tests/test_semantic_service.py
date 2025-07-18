#!/usr/bin/env python3
"""
Tests for Semantic Memory Engine with Intelligent Dialog Processing
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tools.services.memory_service.engines.semantic_engine import SemanticMemoryEngine
from tools.services.memory_service.models import MemoryOperationResult, SemanticMemory


class TestSemanticMemoryEngine:
    """Test suite for intelligent semantic memory processing"""

    @pytest.fixture
    def engine(self):
        """Create a mock semantic engine for testing"""
        with patch('tools.services.memory_service.engines.base_engine.get_supabase_client') as mock_db, \
             patch('tools.services.memory_service.engines.base_engine.EmbeddingGenerator') as mock_embedder, \
             patch('tools.services.memory_service.engines.semantic_engine.TextExtractor') as mock_extractor:
            
            # Mock database
            mock_db.return_value = MagicMock()
            
            # Mock embedder
            mock_embedder_instance = AsyncMock()
            mock_embedder.return_value = mock_embedder_instance
            mock_embedder_instance.embed_single.return_value = [0.1, 0.2, 0.3]
            
            # Mock text extractor
            mock_extractor_instance = AsyncMock()
            mock_extractor.return_value = mock_extractor_instance
            
            engine = SemanticMemoryEngine()
            engine.db = mock_db.return_value
            engine.embedder = mock_embedder_instance
            engine.text_extractor = mock_extractor_instance
            
            return engine

    @pytest.mark.asyncio
    async def test_store_semantic_memory_successful_extraction(self, engine):
        """Test successful semantic memory storage with intelligent extraction"""
        
        # Mock dialog content with semantic concepts
        dialog_content = """
        Human: Can you explain what machine learning is and how it relates to artificial intelligence?
        
        AI: Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It involves algorithms that can identify patterns in data and make predictions or decisions based on those patterns.

        Artificial intelligence is the broader field that encompasses any technique enabling machines to mimic human intelligence. Machine learning is one approach to achieving AI, along with other methods like rule-based systems and expert systems.

        The key principle behind machine learning is that systems can automatically learn and improve from experience. This makes it particularly powerful for tasks like image recognition, natural language processing, and predictive analytics.
        """
        
        # Mock extraction results
        mock_extraction_result = {
            'success': True,
            'data': {
                'concepts': [
                    {
                        'concept_type': 'definition',
                        'definition': 'Machine learning is a subset of artificial intelligence that enables computers to learn from experience without explicit programming',
                        'properties': {
                            'learning_method': 'pattern_recognition',
                            'data_dependency': 'high',
                            'automation_level': 'automatic'
                        },
                        'abstraction_level': 'medium',
                        'category': 'technology',
                        'related_concepts': ['artificial_intelligence', 'algorithms', 'pattern_recognition'],
                        'importance_score': 0.9
                    },
                    {
                        'concept_type': 'definition',
                        'definition': 'Artificial intelligence is a field that encompasses techniques enabling machines to mimic human intelligence',
                        'properties': {
                            'scope': 'broad_field',
                            'goal': 'human_intelligence_mimicry',
                            'approach': 'multiple_techniques'
                        },
                        'abstraction_level': 'abstract',
                        'category': 'technology',
                        'related_concepts': ['machine_learning', 'expert_systems', 'rule_based_systems'],
                        'importance_score': 0.9
                    },
                    {
                        'concept_type': 'principle',
                        'definition': 'Systems can automatically learn and improve from experience',
                        'properties': {
                            'learning_source': 'experience',
                            'improvement_mechanism': 'automatic',
                            'adaptability': 'high'
                        },
                        'abstraction_level': 'medium',
                        'category': 'technology',
                        'related_concepts': ['machine_learning', 'adaptation'],
                        'importance_score': 0.8
                    }
                ],
                'knowledge_domain': 'technology',
                'abstraction_level': 'medium',
                'key_relationships': [
                    'machine_learning is subset of artificial_intelligence',
                    'pattern_recognition enables machine_learning'
                ],
                'extraction_confidence': 0.9
            },
            'confidence': 0.9
        }
        
        # Configure text extractor mock
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Mock store_memory to return the expected result
        engine.store_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="semantic_memory_id",
            operation="store_semantic_memory",
            message="Semantic concept stored successfully"
        ))
        
        # Mock _find_existing_concept to return None (no existing concepts)
        engine._find_existing_concept = AsyncMock(return_value=None)
        
        # Test the store_semantic_memory method
        result = await engine.store_semantic_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == True
        assert result.operation == "store_semantic_memory"
        assert "3 semantic concepts" in result.message
        assert result.data['total_concepts'] == 3
        
        # Verify text extractor was called
        engine.text_extractor.extract_key_information.assert_called_once()
        
        # Verify store_memory was called multiple times (once per concept)
        assert engine.store_memory.call_count == 3

    @pytest.mark.asyncio
    async def test_store_semantic_memory_extraction_failure(self, engine):
        """Test semantic memory storage when extraction fails"""
        
        dialog_content = "Too short"
        
        # Mock failed extraction
        mock_extraction_result = {
            'success': False,
            'error': 'Text too short for meaningful semantic extraction',
            'data': {},
            'confidence': 0.0
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Test the store_semantic_memory method
        result = await engine.store_semantic_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == False
        assert "Failed to extract semantic information" in result.message
        assert result.operation == "store_semantic_memory"

    @pytest.mark.asyncio
    async def test_store_semantic_memory_with_existing_concept(self, engine):
        """Test semantic memory storage with existing concept merging"""
        
        dialog_content = """
        Human: Tell me more about machine learning and its applications.
        AI: Machine learning has many applications including image recognition and natural language processing.
        """
        
        # Mock extraction result
        mock_extraction_result = {
            'success': True,
            'data': {
                'concepts': [
                    {
                        'concept_type': 'definition',
                        'definition': 'Machine learning has applications in image recognition and NLP',
                        'properties': {
                            'applications': ['image_recognition', 'nlp']
                        },
                        'abstraction_level': 'medium',
                        'category': 'technology',
                        'related_concepts': ['computer_vision', 'nlp'],
                        'importance_score': 0.8
                    }
                ],
                'knowledge_domain': 'technology',
                'abstraction_level': 'medium',
                'key_relationships': [],
                'extraction_confidence': 0.8
            },
            'confidence': 0.8
        }
        
        # Mock existing concept
        existing_concept = SemanticMemory(
            id="existing_concept_id",
            user_id="user123",
            content="Machine learning: subset of AI",
            memory_type="semantic",
            concept_type="definition",
            definition="Machine learning is a subset of artificial intelligence",
            properties={"learning_method": "pattern_recognition"},
            abstraction_level="medium",
            related_concepts=["artificial_intelligence"],
            category="technology",
            importance_score=0.7,
            access_count=1,
            source="user_dialog",
            verification_status="unverified",
            embedding=[0.1, 0.2, 0.3]
        )
        
        # Configure mocks
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine._find_existing_concept = AsyncMock(return_value=existing_concept)
        engine._merge_semantic_concept = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="existing_concept_id",
            operation="merge",
            message="Semantic concept merged and updated"
        ))
        
        # Test
        result = await engine.store_semantic_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == True
        assert result.operation == "store_semantic_memory"
        assert "1 semantic concepts" in result.message
        
        # Verify merge was called
        engine._merge_semantic_concept.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_concepts_by_category(self, engine):
        """Test searching concepts by category"""
        
        # Mock database response
        mock_concepts_data = [
            {
                'id': 'concept1',
                'user_id': 'user123',
                'content': 'Machine learning: AI subset',
                'memory_type': 'semantic',
                'concept_type': 'definition',
                'definition': 'Machine learning is a subset of AI',
                'properties': '{"learning_method": "pattern_recognition"}',
                'abstraction_level': 'medium',
                'related_concepts': '["artificial_intelligence"]',
                'category': 'technology',
                'importance_score': 0.9,
                'access_count': 5,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            },
            {
                'id': 'concept2',
                'user_id': 'user123',
                'content': 'Neural networks: computational model',
                'memory_type': 'semantic',
                'concept_type': 'definition',
                'definition': 'Neural networks are computational models inspired by biological neural networks',
                'properties': '{"inspiration": "biological_neurons"}',
                'abstraction_level': 'medium',
                'related_concepts': '["machine_learning", "deep_learning"]',
                'category': 'technology',
                'importance_score': 0.8,
                'access_count': 3,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.2, 0.3, 0.4]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_concepts_data
        )
        
        # Test search
        concepts = await engine.search_concepts_by_category(
            user_id="user123",
            category="technology",
            limit=5
        )
        
        # Assertions
        assert len(concepts) == 2
        assert all(concept.category == "technology" for concept in concepts)

    @pytest.mark.asyncio
    async def test_search_concepts_by_abstraction_level(self, engine):
        """Test searching concepts by abstraction level"""
        
        # Mock database response
        mock_concepts_data = [
            {
                'id': 'concept1',
                'user_id': 'user123',
                'content': 'Abstract concept: intelligence',
                'memory_type': 'semantic',
                'concept_type': 'definition',
                'definition': 'Intelligence is the ability to acquire and apply knowledge',
                'properties': '{}',
                'abstraction_level': 'abstract',
                'related_concepts': '[]',
                'category': 'philosophy',
                'importance_score': 0.9,
                'access_count': 2,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_concepts_data
        )
        
        # Test search
        concepts = await engine.search_concepts_by_abstraction_level(
            user_id="user123",
            abstraction_level="abstract",
            limit=5
        )
        
        # Assertions
        assert len(concepts) == 1
        assert concepts[0].abstraction_level == "abstract"

    @pytest.mark.asyncio
    async def test_search_concepts_by_type(self, engine):
        """Test searching concepts by concept type"""
        
        # Mock database response
        mock_concepts_data = [
            {
                'id': 'concept1',
                'user_id': 'user123',
                'content': 'Principle: learning from experience',
                'memory_type': 'semantic',
                'concept_type': 'principle',
                'definition': 'Systems can learn automatically from experience',
                'properties': '{"automation": "high"}',
                'abstraction_level': 'medium',
                'related_concepts': '["machine_learning"]',
                'category': 'technology',
                'importance_score': 0.8,
                'access_count': 4,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_concepts_data
        )
        
        # Test search
        concepts = await engine.search_concepts_by_type(
            user_id="user123",
            concept_type="principle",
            limit=5
        )
        
        # Assertions
        assert len(concepts) == 1
        assert concepts[0].concept_type == "principle"

    @pytest.mark.asyncio
    async def test_search_concepts_by_definition(self, engine):
        """Test searching concepts by definition content"""
        
        # Mock database response
        mock_concepts_data = [
            {
                'id': 'concept1',
                'user_id': 'user123',
                'content': 'AI: intelligence in machines',
                'memory_type': 'semantic',
                'concept_type': 'definition',
                'definition': 'Artificial intelligence enables machines to exhibit intelligent behavior',
                'properties': '{}',
                'abstraction_level': 'medium',
                'related_concepts': '["machine_learning"]',
                'category': 'technology',
                'importance_score': 0.9,
                'access_count': 6,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_concepts_data
        )
        
        # Test search
        concepts = await engine.search_concepts_by_definition(
            user_id="user123",
            definition_keyword="intelligence",
            limit=5
        )
        
        # Assertions
        assert len(concepts) == 1
        assert "intelligence" in concepts[0].definition.lower()

    @pytest.mark.asyncio
    async def test_search_concepts_by_related_concept(self, engine):
        """Test searching concepts by related concept"""
        
        # Mock database response
        mock_concepts_data = [
            {
                'id': 'concept1',
                'user_id': 'user123',
                'content': 'Deep learning: ML subset',
                'memory_type': 'semantic',
                'concept_type': 'definition',
                'definition': 'Deep learning is a subset of machine learning using neural networks',
                'properties': '{"architecture": "neural_networks"}',
                'abstraction_level': 'medium',
                'related_concepts': '["machine_learning", "neural_networks"]',
                'category': 'technology',
                'importance_score': 0.8,
                'access_count': 3,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            },
            {
                'id': 'concept2',
                'user_id': 'user123',
                'content': 'Computer vision: image processing',
                'memory_type': 'semantic',
                'concept_type': 'definition',
                'definition': 'Computer vision enables machines to interpret visual information',
                'properties': '{"data_type": "images"}',
                'abstraction_level': 'medium',
                'related_concepts': '["machine_learning", "image_processing"]',
                'category': 'technology',
                'importance_score': 0.7,
                'access_count': 2,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.2, 0.3, 0.4]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=mock_concepts_data
        )
        
        # Test search
        concepts = await engine.search_concepts_by_related_concept(
            user_id="user123",
            related_concept_id="machine_learning",
            limit=5
        )
        
        # Assertions
        assert len(concepts) == 2
        assert all("machine_learning" in concept.related_concepts for concept in concepts)

    @pytest.mark.asyncio
    async def test_add_concept_relation(self, engine):
        """Test adding relationship between concepts"""
        
        # Mock source concept
        source_concept = SemanticMemory(
            id="source_concept_id",
            user_id="user123",
            content="Machine learning: AI subset",
            memory_type="semantic",
            concept_type="definition",
            definition="Machine learning is a subset of AI",
            properties={},
            abstraction_level="medium",
            related_concepts=["artificial_intelligence"],
            category="technology",
            importance_score=0.8,
            access_count=3,
            source="user_dialog",
            verification_status="unverified",
            embedding=[0.1, 0.2, 0.3]
        )
        
        # Mock get_memory to return source concept
        engine.get_memory = AsyncMock(return_value=source_concept)
        
        # Mock update_memory
        engine.update_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="source_concept_id",
            operation="add_relation",
            message="Relation added successfully"
        ))
        
        # Test adding new relation
        result = await engine.add_concept_relation("source_concept_id", "target_concept_id")
        
        # Assertions
        assert result.success == True
        assert result.operation == "add_relation"
        
        # Verify update_memory was called
        engine.update_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_concept_properties(self, engine):
        """Test updating concept properties"""
        
        # Mock existing concept
        existing_concept = SemanticMemory(
            id="concept_id",
            user_id="user123",
            content="Machine learning: AI subset",
            memory_type="semantic",
            concept_type="definition",
            definition="Machine learning is a subset of AI",
            properties={"learning_method": "pattern_recognition"},
            abstraction_level="medium",
            related_concepts=["artificial_intelligence"],
            category="technology",
            importance_score=0.8,
            access_count=3,
            source="user_dialog",
            verification_status="unverified",
            embedding=[0.1, 0.2, 0.3]
        )
        
        # Mock get_memory to return existing concept
        engine.get_memory = AsyncMock(return_value=existing_concept)
        
        # Mock update_memory
        engine.update_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="concept_id",
            operation="update_properties",
            message="Properties updated successfully"
        ))
        
        # Test updating properties
        new_properties = {"application": "computer_vision", "complexity": "high"}
        result = await engine.update_concept_properties("concept_id", new_properties)
        
        # Assertions
        assert result.success == True
        assert result.operation == "update_properties"
        
        # Verify update_memory was called
        engine.update_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_semantic_data_validation(self, engine):
        """Test semantic data processing and validation"""
        
        # Test data with various edge cases
        raw_data = {
            'concepts': [
                {
                    'concept_type': 'Machine Learning',  # Should be normalized
                    'definition': 'A subset of AI that enables learning from data',
                    'properties': {'learning': 'automatic'},
                    'abstraction_level': 'MEDIUM',  # Wrong case
                    'category': 'Technology',  # Wrong case
                    'related_concepts': ['AI', 'Data Science'],
                    'importance_score': 1.5  # Should be clamped
                },
                {
                    # Missing definition - should be filtered out
                    'concept_type': 'incomplete',
                    'properties': {'test': 'value'}
                }
            ],
            'knowledge_domain': 'Technology',
            'abstraction_level': 'Medium',
            'key_relationships': ['ML is subset of AI'],
            'extraction_confidence': 'invalid'  # Should default
        }
        
        original_content = "This is the original dialog content for fallback."
        
        # Test the processing method directly
        processed = await engine._process_semantic_data(raw_data, original_content)
        
        # Assertions
        assert len(processed['concepts']) == 1  # Only valid concept processed
        assert processed['concepts'][0]['concept_type'] == 'machine_learning'  # Normalized
        assert processed['concepts'][0]['abstraction_level'] == 'medium'  # Normalized
        assert processed['concepts'][0]['category'] == 'technology'  # Normalized
        assert processed['concepts'][0]['importance_score'] == 1.0  # Clamped
        assert processed['knowledge_domain'] == 'technology'  # Normalized
        assert processed['extraction_confidence'] == 0.7  # Defaulted

    @pytest.mark.asyncio
    async def test_extract_basic_concepts_fallback(self, engine):
        """Test basic concept extraction when structured extraction fails"""
        
        content = "Machine learning is a powerful technology. Artificial intelligence refers to smart systems. Deep learning means neural networks with many layers."
        
        # Test basic concept extraction
        basic_concepts = engine._extract_basic_concepts(content)
        
        # Assertions
        assert len(basic_concepts) <= 2  # Limited to 2 concepts
        assert any('machine learning' in concept['definition'].lower() for concept in basic_concepts)
        assert all(concept['importance_score'] == 0.6 for concept in basic_concepts)  # Basic confidence

    @pytest.mark.asyncio
    async def test_search_methods_error_handling(self, engine):
        """Test error handling in search methods"""
        
        # Mock database error
        engine.db.table.return_value.select.side_effect = Exception("Database error")
        
        # Test all search methods handle errors gracefully
        result1 = await engine.search_concepts_by_category("user123", "technology")
        assert result1 == []
        
        result2 = await engine.search_concepts_by_abstraction_level("user123", "medium")
        assert result2 == []
        
        result3 = await engine.search_concepts_by_type("user123", "definition")
        assert result3 == []
        
        result4 = await engine.search_concepts_by_definition("user123", "intelligence")
        assert result4 == []
        
        result5 = await engine.search_concepts_by_related_concept("user123", "ai")
        assert result5 == []

    def test_engine_properties(self, engine):
        """Test engine basic properties"""
        assert engine.table_name == "semantic_memories"
        assert engine.memory_type == "semantic"

    @pytest.mark.asyncio
    async def test_extraction_with_complex_concepts(self, engine):
        """Test extraction of complex multi-concept discussions"""
        
        dialog_content = """
        Human: What's the difference between supervised and unsupervised learning?
        
        AI: Great question! These are two fundamental paradigms in machine learning.
        
        Supervised learning uses labeled training data to learn mappings from inputs to outputs. The algorithm learns from examples where the correct answer is provided. Common types include classification (predicting categories) and regression (predicting continuous values).
        
        Unsupervised learning, on the other hand, works with unlabeled data to discover hidden patterns or structures. It includes clustering (grouping similar data points), dimensionality reduction (simplifying data while preserving important features), and association rule learning.
        
        The key difference is that supervised learning has a "teacher" providing correct answers, while unsupervised learning must find patterns without guidance.
        """
        
        # Mock complex extraction result
        mock_extraction_result = {
            'success': True,
            'data': {
                'concepts': [
                    {
                        'concept_type': 'paradigm',
                        'definition': 'Supervised learning uses labeled training data to learn input-output mappings',
                        'properties': {
                            'data_type': 'labeled',
                            'learning_style': 'guided',
                            'examples': ['classification', 'regression']
                        },
                        'abstraction_level': 'medium',
                        'category': 'technology',
                        'related_concepts': ['machine_learning', 'classification', 'regression'],
                        'importance_score': 0.9
                    },
                    {
                        'concept_type': 'paradigm',
                        'definition': 'Unsupervised learning discovers patterns in unlabeled data without guidance',
                        'properties': {
                            'data_type': 'unlabeled',
                            'learning_style': 'discovery',
                            'examples': ['clustering', 'dimensionality_reduction']
                        },
                        'abstraction_level': 'medium',
                        'category': 'technology',
                        'related_concepts': ['machine_learning', 'clustering', 'pattern_recognition'],
                        'importance_score': 0.9
                    }
                ],
                'knowledge_domain': 'technology',
                'abstraction_level': 'medium',
                'key_relationships': [
                    'supervised_learning uses labeled_data',
                    'unsupervised_learning discovers hidden_patterns'
                ],
                'extraction_confidence': 0.85
            },
            'confidence': 0.85
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine.store_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="complex_concept_id",
            operation="store_semantic_memory",
            message="Complex semantic concept stored successfully"
        ))
        engine._find_existing_concept = AsyncMock(return_value=None)
        
        # Test
        result = await engine.store_semantic_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == True
        assert result.data['total_concepts'] == 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])