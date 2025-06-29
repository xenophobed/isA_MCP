#!/usr/bin/env python3
"""
Unit tests for EmbeddingStorage - Step 3 of the analytics workflow
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from tools.services.data_analytics_service.core.embedding_storage import (
    EmbeddingStorage, EmbeddingRecord, SearchResult
)
from tools.services.data_analytics_service.core.semantic_enricher import SemanticMetadata


@pytest.fixture
def sample_semantic_metadata():
    """Sample semantic metadata for testing"""
    return SemanticMetadata(
        original_metadata={
            'tables': [
                {
                    'table_name': 'customers',
                    'table_type': 'table',
                    'record_count': 1000,
                    'table_comment': 'Customer data'
                }
            ],
            'columns': [
                {
                    'table_name': 'customers',
                    'column_name': 'email',
                    'data_type': 'varchar',
                    'is_nullable': False,
                    'column_comment': 'Customer email'
                }
            ],
            'relationships': []
        },
        business_entities=[
            {
                'entity_name': 'customers',
                'entity_type': 'entity',
                'confidence': 0.9,
                'key_attributes': ['email'],
                'relationships': [],
                'business_importance': 'high'
            }
        ],
        semantic_tags={
            'table:customers': ['domain:customer', 'pattern:entity'],
            'column:customers.email': ['semantic:identifier']
        },
        data_patterns=[],
        business_rules=[],
        domain_classification={'primary_domain': 'ecommerce'},
        confidence_scores={'overall': 0.8}
    )


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model"""
    mock_model = AsyncMock()
    mock_model.embed = AsyncMock(return_value=[0.1] * 1536)  # Mock 1536-dim embedding
    return mock_model


@pytest.fixture
def embedding_storage():
    """Create EmbeddingStorage instance without database connection"""
    return EmbeddingStorage()


@pytest.fixture
def embedding_storage_with_db():
    """Create EmbeddingStorage instance with mock database config"""
    config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'user': 'test_user',
        'password': 'test_pass'
    }
    return EmbeddingStorage(config)


class TestEmbeddingStorage:
    """Test cases for EmbeddingStorage"""
    
    def test_initialization(self, embedding_storage):
        """Test EmbeddingStorage initialization"""
        assert embedding_storage is not None
        assert embedding_storage.connection_config == {}
        assert embedding_storage.connection is None
        assert embedding_storage.embedding_model is None
        assert isinstance(embedding_storage.embedding_cache, dict)
    
    def test_initialization_with_config(self, embedding_storage_with_db):
        """Test EmbeddingStorage initialization with config"""
        assert embedding_storage_with_db.connection_config['host'] == 'localhost'
        assert embedding_storage_with_db.connection_config['port'] == 5432
    
    @pytest.mark.asyncio
    async def test_initialize_with_model(self, embedding_storage, mock_embedding_model):
        """Test initialization with embedding model"""
        await embedding_storage.initialize(mock_embedding_model)
        assert embedding_storage.embedding_model == mock_embedding_model
    
    @pytest.mark.asyncio
    async def test_generate_embedding_with_model(self, embedding_storage, mock_embedding_model):
        """Test embedding generation with model"""
        await embedding_storage.initialize(mock_embedding_model)
        
        content = "test content"
        embedding = await embedding_storage._generate_embedding(content)
        
        assert embedding is not None
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
        mock_embedding_model.embed.assert_called_once_with(content)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_fallback(self, embedding_storage):
        """Test embedding generation fallback without model"""
        content = "test content"
        embedding = await embedding_storage._generate_embedding(content)
        
        assert embedding is not None
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_caching(self, embedding_storage, mock_embedding_model):
        """Test embedding caching"""
        await embedding_storage.initialize(mock_embedding_model)
        
        content = "test content"
        
        # First call
        embedding1 = await embedding_storage._generate_embedding(content)
        
        # Second call with same content
        embedding2 = await embedding_storage._generate_embedding(content)
        
        # Should be cached (same result)
        assert embedding1 == embedding2
        # Model should only be called once
        mock_embedding_model.embed.assert_called_once()
    
    def test_create_table_content(self, embedding_storage, sample_semantic_metadata):
        """Test table content creation for embedding"""
        table = sample_semantic_metadata.original_metadata['tables'][0]
        content = embedding_storage._create_table_content(table, sample_semantic_metadata)
        
        assert 'Table: customers' in content
        assert 'Records: 1000' in content
        assert 'Entity Type:' in content
        assert 'Tags:' in content
    
    def test_create_column_content(self, embedding_storage, sample_semantic_metadata):
        """Test column content creation for embedding"""
        column = sample_semantic_metadata.original_metadata['columns'][0]
        content = embedding_storage._create_column_content(column, sample_semantic_metadata)
        
        assert 'Column: customers.email' in content
        assert 'Data Type: varchar' in content
        assert 'Nullable: No' in content
        assert 'Tags:' in content
    
    def test_create_relationship_content(self, embedding_storage):
        """Test relationship content creation"""
        relationship = {
            'from_table': 'orders',
            'from_column': 'customer_id',
            'to_table': 'customers',
            'to_column': 'customer_id',
            'constraint_type': 'foreign_key'
        }
        
        content = embedding_storage._create_relationship_content(relationship)
        
        assert 'orders.customer_id' in content
        assert 'customers.customer_id' in content
        assert 'foreign_key' in content
    
    def test_create_entity_content(self, embedding_storage):
        """Test entity content creation"""
        entity = {
            'entity_name': 'customers',
            'entity_type': 'entity',
            'business_importance': 'high',
            'key_attributes': ['email', 'name'],
            'relationships': [
                {'type': 'foreign_key', 'target_table': 'orders'}
            ]
        }
        
        content = embedding_storage._create_entity_content(entity)
        
        assert 'Business Entity: customers' in content
        assert 'Type: entity' in content
        assert 'Importance: high' in content
        assert 'Key Attributes: email, name' in content
        assert 'Relationships:' in content
    
    def test_generate_id(self, embedding_storage):
        """Test ID generation"""
        entity_id = embedding_storage._generate_id('table', 'customers')
        
        assert entity_id.startswith('table:')
        assert len(entity_id) > 10  # Should have hash component
        
        # Same input should generate same ID
        entity_id2 = embedding_storage._generate_id('table', 'customers')
        assert entity_id == entity_id2
    
    @pytest.mark.asyncio
    async def test_store_table_embeddings(self, embedding_storage, sample_semantic_metadata, mock_embedding_model):
        """Test storing table embeddings"""
        await embedding_storage.initialize(mock_embedding_model)
        
        # Mock the store_embedding_record method
        embedding_storage._store_embedding_record = AsyncMock(return_value=True)
        
        result = await embedding_storage._store_table_embeddings(sample_semantic_metadata)
        
        assert result['stored'] == 1
        assert result['failed'] == 0
        assert len(result['errors']) == 0
        
        # Verify embedding generation was called
        mock_embedding_model.embed.assert_called()
    
    @pytest.mark.asyncio
    async def test_store_column_embeddings(self, embedding_storage, sample_semantic_metadata, mock_embedding_model):
        """Test storing column embeddings"""
        await embedding_storage.initialize(mock_embedding_model)
        
        # Mock the store_embedding_record method
        embedding_storage._store_embedding_record = AsyncMock(return_value=True)
        
        result = await embedding_storage._store_column_embeddings(sample_semantic_metadata)
        
        assert result['stored'] == 1
        assert result['failed'] == 0
        assert len(result['errors']) == 0
    
    @pytest.mark.asyncio
    async def test_store_semantic_metadata_complete(self, embedding_storage, sample_semantic_metadata, mock_embedding_model):
        """Test complete semantic metadata storage"""
        await embedding_storage.initialize(mock_embedding_model)
        
        # Mock the store_embedding_record method
        embedding_storage._store_embedding_record = AsyncMock(return_value=True)
        
        result = await embedding_storage.store_semantic_metadata(sample_semantic_metadata)
        
        assert result['stored_embeddings'] > 0
        assert result['failed_embeddings'] == 0
        assert 'storage_time' in result
        assert len(result['errors']) == 0
    
    @pytest.mark.asyncio
    async def test_search_similar_entities_memory(self, embedding_storage, mock_embedding_model):
        """Test searching similar entities in memory cache"""
        await embedding_storage.initialize(mock_embedding_model)
        
        # Store some test records in cache
        embedding_storage.embedding_cache['test_record'] = {
            'entity_name': 'customers',
            'entity_type': 'table',
            'content': 'test content',
            'metadata': {},
            'semantic_tags': [],
            'embedding': [0.1] * 1536
        }
        
        results = await embedding_storage.search_similar_entities("test query")
        
        # Should find results in memory cache
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_find_related_metadata(self, embedding_storage, mock_embedding_model):
        """Test finding related metadata"""
        await embedding_storage.initialize(mock_embedding_model)
        
        # Mock search method
        embedding_storage.search_similar_entities = AsyncMock(return_value=[
            SearchResult(
                entity_name='customers',
                entity_type='table',
                similarity_score=0.8,
                content='customer table',
                metadata={},
                semantic_tags=[]
            )
        ])
        
        related = await embedding_storage.find_related_metadata('users', ['email'])
        
        assert 'similar_tables' in related
        assert 'related_columns' in related
        assert 'business_entities' in related
        assert 'patterns' in related
    
    def test_get_table_confidence(self, embedding_storage, sample_semantic_metadata):
        """Test getting table confidence score"""
        table = sample_semantic_metadata.original_metadata['tables'][0]
        confidence = embedding_storage._get_table_confidence(table, sample_semantic_metadata)
        
        assert 0 <= confidence <= 1
        assert confidence == 0.9  # From the business entity
    
    def test_get_column_confidence(self, embedding_storage, sample_semantic_metadata):
        """Test getting column confidence score"""
        column = sample_semantic_metadata.original_metadata['columns'][0]
        confidence = embedding_storage._get_column_confidence(column, sample_semantic_metadata)
        
        assert 0 <= confidence <= 1
        assert confidence > 0.5  # Should have boost for 'email' column


class TestEmbeddingRecord:
    """Test cases for EmbeddingRecord dataclass"""
    
    def test_embedding_record_creation(self):
        """Test EmbeddingRecord creation"""
        record = EmbeddingRecord(
            id='test_id',
            entity_type='table',
            entity_name='customers',
            content='test content',
            embedding=[0.1] * 1536,
            metadata={},
            semantic_tags=[],
            confidence_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert record.id == 'test_id'
        assert record.entity_type == 'table'
        assert record.entity_name == 'customers'
        assert len(record.embedding) == 1536


class TestSearchResult:
    """Test cases for SearchResult dataclass"""
    
    def test_search_result_creation(self):
        """Test SearchResult creation"""
        result = SearchResult(
            entity_name='customers',
            entity_type='table',
            similarity_score=0.9,
            content='customer table',
            metadata={},
            semantic_tags=['customer', 'entity']
        )
        
        assert result.entity_name == 'customers'
        assert result.entity_type == 'table'
        assert result.similarity_score == 0.9
        assert 'customer' in result.semantic_tags


@pytest.mark.asyncio
class TestEmbeddingStorageIntegration:
    """Integration tests for EmbeddingStorage"""
    
    async def test_full_storage_workflow(self, embedding_storage, sample_semantic_metadata, mock_embedding_model):
        """Test complete storage workflow"""
        await embedding_storage.initialize(mock_embedding_model)
        
        # Mock database operations
        embedding_storage._store_embedding_record = AsyncMock(return_value=True)
        
        # Execute full workflow
        result = await embedding_storage.store_semantic_metadata(sample_semantic_metadata)
        
        # Verify results
        assert result['stored_embeddings'] > 0
        assert result['failed_embeddings'] == 0
        assert 'storage_time' in result
        
        # Verify embeddings were generated
        mock_embedding_model.embed.assert_called()


if __name__ == '__main__':
    pytest.main([__file__])