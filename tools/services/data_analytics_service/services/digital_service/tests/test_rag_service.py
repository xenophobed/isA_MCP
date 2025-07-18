#!/usr/bin/env python3
"""
Test Suite for RAG Service

Comprehensive tests for the RAG (Retrieval-Augmented Generation) service including:
- Knowledge storage and retrieval
- Semantic search functionality
- Document chunking and processing
- User isolation and permissions
- MCP resource registration
- Error handling and edge cases
"""

import asyncio
import pytest
import uuid
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Import the RAG service
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../../../..')

from tools.services.data_analytics_service.services.digital_service.rag_service import RAGService, rag_service

class TestRAGService:
    """Test suite for RAG Service."""
    
    @pytest.fixture
    def mock_supabase(self):
        """Mock Supabase client."""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        return mock_client, mock_table
    
    @pytest.fixture
    def mock_embedding_generator(self):
        """Mock embedding generator functions."""
        with patch('tools.services.data_analytics_service.services.digital_service.rag_service.embed') as mock_embed, \
             patch('tools.services.data_analytics_service.services.digital_service.rag_service.search') as mock_search, \
             patch('tools.services.data_analytics_service.services.digital_service.rag_service.chunk') as mock_chunk, \
             patch('tools.services.data_analytics_service.services.digital_service.rag_service.rerank') as mock_rerank:
            
            # Configure default return values
            mock_embed.return_value = [0.1] * 1536  # 1536-dimensional embedding
            mock_search.return_value = [("Machine learning is a subset of AI", 0.8), ("Deep learning uses neural networks", 0.6)]
            mock_chunk.return_value = [
                {'text': 'chunk 1', 'index': 0, 'metadata': {}},
                {'text': 'chunk 2', 'index': 1, 'metadata': {}}
            ]
            mock_rerank.return_value = [
                {'document': 'Machine learning is a subset of AI', 'relevance_score': 0.9},
                {'document': 'Deep learning uses neural networks', 'relevance_score': 0.7}
            ]
            
            yield {
                'embed': mock_embed,
                'search': mock_search,
                'chunk': mock_chunk,
                'rerank': mock_rerank
            }
    
    @pytest.fixture
    def mock_graph_resources(self):
        """Mock graph knowledge resources."""
        with patch('tools.services.data_analytics_service.services.digital_service.rag_service.graph_knowledge_resources') as mock_graph:
            mock_graph.register_resource = AsyncMock(return_value={'success': True})
            mock_graph.delete_resource = AsyncMock(return_value={'success': True})
            yield mock_graph
    
    @pytest.fixture
    def rag_service_instance(self, mock_supabase, mock_embedding_generator, mock_graph_resources):
        """Create RAG service instance with mocked dependencies."""
        mock_client, mock_table = mock_supabase
        
        with patch('tools.services.data_analytics_service.services.digital_service.rag_service.get_supabase_client') as mock_get_client:
            mock_get_client.return_value = mock_client
            
            service = RAGService({
                'chunk_size': 400,
                'overlap': 50,
                'top_k': 5,
                'embedding_model': 'text-embedding-3-small'
            })
            
            # Store references for test verification
            service._mock_table = mock_table
            service._mock_embedding = mock_embedding_generator
            service._mock_graph = mock_graph_resources
            
            return service
    
    @pytest.mark.asyncio
    async def test_store_knowledge_success(self, rag_service_instance):
        """Test successful knowledge storage."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        text = "This is a test knowledge item about machine learning."
        metadata = {"source": "test", "category": "ml"}
        
        # Mock successful database insertion
        mock_result = Mock()
        mock_result.data = [{"id": "test_id", "user_id": user_id}]
        service._mock_table.insert.return_value.execute.return_value = mock_result
        
        # Execute
        result = await service.store_knowledge(user_id, text, metadata)
        
        # Verify
        assert result['success'] is True
        assert result['user_id'] == user_id
        assert result['text_length'] == len(text)
        assert result['embedding_dimensions'] == 1536
        assert 'knowledge_id' in result
        assert 'mcp_address' in result
        assert result['mcp_address'].startswith(f"mcp://rag/{user_id}/")
        
        # Verify embedding generation was called
        service._mock_embedding['embed'].assert_called_once_with(text, model='text-embedding-3-small')
        
        # Verify database insertion
        service._mock_table.insert.assert_called_once()
        
        # Verify MCP registration
        service._mock_graph.register_resource.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_knowledge_embedding_failure(self, rag_service_instance):
        """Test knowledge storage when embedding generation fails."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        text = "Test text"
        
        # Mock embedding failure
        service._mock_embedding['embed'].return_value = None
        
        # Execute
        result = await service.store_knowledge(user_id, text)
        
        # Verify
        assert result['success'] is False
        assert result['error'] == 'Failed to generate embedding'
        assert result['user_id'] == user_id
    
    @pytest.mark.asyncio
    async def test_retrieve_context_success(self, rag_service_instance):
        """Test successful context retrieval."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        query = "machine learning"
        
        # Mock database query result
        mock_result = Mock()
        mock_result.data = [
            {
                'id': 'kb1',
                'text': 'Machine learning is a subset of AI',
                'metadata': {'source': 'textbook'},
                'created_at': '2024-01-01T00:00:00'
            },
            {
                'id': 'kb2',
                'text': 'Deep learning uses neural networks',
                'metadata': {'source': 'paper'},
                'created_at': '2024-01-02T00:00:00'
            }
        ]
        # Create proper mock chain for Supabase query
        mock_select = Mock()
        mock_eq = Mock()
        mock_execute = Mock()
        mock_execute.return_value = mock_result
        mock_eq.execute = mock_execute
        mock_select.eq.return_value = mock_eq
        service._mock_table.select.return_value = mock_select
        
        # Execute
        result = await service.retrieve_context(user_id, query, top_k=2)
        
        # Verify
        assert result['success'] is True
        assert result['user_id'] == user_id
        assert result['query'] == query
        assert len(result['context_items']) == 2
        assert result['total_knowledge_items'] == 2
        
        # Check context item structure
        context_item = result['context_items'][0]
        assert 'knowledge_id' in context_item
        assert 'text' in context_item
        assert 'similarity_score' in context_item
        assert 'metadata' in context_item
        assert 'created_at' in context_item
        
        # Verify search was called
        service._mock_embedding['search'].assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retrieve_context_no_knowledge(self, rag_service_instance):
        """Test context retrieval when user has no knowledge."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        query = "test query"
        
        # Mock empty database result
        mock_result = Mock()
        mock_result.data = []
        service._mock_table.select.return_value.eq.return_value.execute.return_value = mock_result
        
        # Execute
        result = await service.retrieve_context(user_id, query)
        
        # Verify
        assert result['success'] is True
        assert result['user_id'] == user_id
        assert result['context_items'] == []
        assert result['total_knowledge_items'] == 0
    
    @pytest.mark.asyncio
    async def test_search_knowledge_with_reranking(self, rag_service_instance):
        """Test knowledge search with reranking."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        query = "artificial intelligence"
        
        # Mock database and search results
        mock_result = Mock()
        mock_result.data = [
            {
                'id': 'kb1',
                'text': 'Machine learning is a subset of AI',
                'metadata': {},
                'created_at': '2024-01-01T00:00:00'
            }
        ]
        # Create proper mock chain for Supabase query
        mock_select = Mock()
        mock_eq = Mock()
        mock_execute = Mock()
        mock_execute.return_value = mock_result
        mock_eq.execute = mock_execute
        mock_select.eq.return_value = mock_eq
        service._mock_table.select.return_value = mock_select
        
        # Execute
        result = await service.search_knowledge(user_id, query, top_k=1)
        
        # Verify
        assert result['success'] is True
        assert result['user_id'] == user_id
        assert result['query'] == query
        assert len(result['search_results']) == 1
        
        # Check search result structure
        search_result = result['search_results'][0]
        assert 'knowledge_id' in search_result
        assert 'text' in search_result
        assert 'relevance_score' in search_result
        assert 'similarity_score' in search_result
        assert 'mcp_address' in search_result
        assert search_result['mcp_address'].startswith(f"mcp://rag/{user_id}/")
        
        # Verify reranking was called
        service._mock_embedding['rerank'].assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, rag_service_instance):
        """Test successful response generation."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        query = "What is machine learning?"
        
        # Mock context retrieval
        with patch.object(service, 'retrieve_context') as mock_retrieve:
            mock_retrieve.return_value = {
                'success': True,
                'context_items': [
                    {
                        'knowledge_id': 'kb1',
                        'text': 'Machine learning is a subset of artificial intelligence',
                        'similarity_score': 0.9,
                        'metadata': {},
                        'created_at': '2024-01-01'
                    }
                ]
            }
            
            # Execute
            result = await service.generate_response(user_id, query, context_limit=1)
            
            # Verify
            assert result['success'] is True
            assert result['user_id'] == user_id
            assert result['query'] == query
            assert 'response' in result
            assert len(result['context_items']) == 1
            assert result['context_used'] == 1
            
            # Check that response contains relevant information
            assert "machine learning" in result['response'].lower()
    
    @pytest.mark.asyncio
    async def test_generate_response_no_context(self, rag_service_instance):
        """Test response generation when no context is available."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        query = "Test query"
        
        # Mock empty context retrieval
        with patch.object(service, 'retrieve_context') as mock_retrieve:
            mock_retrieve.return_value = {
                'success': True,
                'context_items': []
            }
            
            # Execute
            result = await service.generate_response(user_id, query)
            
            # Verify
            assert result['success'] is True
            assert result['context_used'] == 0
            assert "don't have any relevant knowledge" in result['response']
    
    @pytest.mark.asyncio
    async def test_add_document_chunking(self, rag_service_instance):
        """Test document addition with chunking."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        document = "This is a long document that will be chunked. " * 20  # Long text
        metadata = {"source": "test_doc", "type": "article"}
        
        # Mock successful storage for each chunk
        with patch.object(service, 'store_knowledge') as mock_store:
            mock_store.return_value = {
                'success': True,
                'knowledge_id': str(uuid.uuid4()),
                'mcp_address': f"mcp://rag/{user_id}/test_id"
            }
            
            # Execute
            result = await service.add_document(user_id, document, chunk_size=100, metadata=metadata)
            
            # Verify
            assert result['success'] is True
            assert result['user_id'] == user_id
            assert result['total_chunks'] == 2  # Based on mock chunk function
            assert result['stored_chunks'] == 2
            assert 'document_id' in result
            assert result['document_length'] == len(document)
            
            # Verify chunking was called
            service._mock_embedding['chunk'].assert_called_once()
            
            # Verify store_knowledge was called for each chunk
            assert mock_store.call_count == 2
    
    @pytest.mark.asyncio
    async def test_list_user_knowledge(self, rag_service_instance):
        """Test listing user's knowledge items."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        
        # Mock database query result
        mock_result = Mock()
        mock_result.data = [
            {
                'id': 'kb1',
                'text': 'Knowledge item 1' * 10,  # Long text for preview test
                'metadata': {'source': 'test1'},
                'created_at': '2024-01-01T00:00:00',
                'updated_at': '2024-01-01T00:00:00'
            },
            {
                'id': 'kb2',
                'text': 'Short text',
                'metadata': {'source': 'test2'},
                'created_at': '2024-01-02T00:00:00',
                'updated_at': '2024-01-02T00:00:00'
            }
        ]
        service._mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result
        
        # Execute
        result = await service.list_user_knowledge(user_id)
        
        # Verify
        assert result['success'] is True
        assert result['user_id'] == user_id
        assert result['total_count'] == 2
        assert len(result['knowledge_items']) == 2
        
        # Check knowledge item structure
        item = result['knowledge_items'][0]
        assert 'knowledge_id' in item
        assert 'text_preview' in item
        assert 'text_length' in item
        assert 'metadata' in item
        assert 'mcp_address' in item
        
        # Check text preview truncation
        long_item = next(item for item in result['knowledge_items'] if item['knowledge_id'] == 'kb1')
        assert long_item['text_preview'].endswith('...')
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_success(self, rag_service_instance):
        """Test successful knowledge deletion."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        knowledge_id = "kb_to_delete"
        
        # Mock knowledge exists check
        mock_check_result = Mock()
        mock_check_result.data = [{'id': knowledge_id}]
        service._mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_check_result
        
        # Mock successful deletion
        mock_delete_result = Mock()
        service._mock_table.delete.return_value.eq.return_value.eq.return_value.execute.return_value = mock_delete_result
        
        # Execute
        result = await service.delete_knowledge(user_id, knowledge_id)
        
        # Verify
        assert result['success'] is True
        assert result['user_id'] == user_id
        assert result['knowledge_id'] == knowledge_id
        assert result['mcp_deletion'] is True
        
        # Verify MCP resource deletion
        service._mock_graph.delete_resource.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_not_found(self, rag_service_instance):
        """Test knowledge deletion when item doesn't exist."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        knowledge_id = "nonexistent_kb"
        
        # Mock knowledge not found
        mock_result = Mock()
        mock_result.data = []
        service._mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result
        
        # Execute
        result = await service.delete_knowledge(user_id, knowledge_id)
        
        # Verify
        assert result['success'] is False
        assert result['error'] == 'Knowledge item not found or access denied'
        assert result['user_id'] == user_id
        assert result['knowledge_id'] == knowledge_id
    
    @pytest.mark.asyncio
    async def test_get_knowledge_success(self, rag_service_instance):
        """Test successful knowledge item retrieval."""
        # Setup
        service = rag_service_instance
        user_id = "test_user_123"
        knowledge_id = "kb_to_get"
        
        # Mock database query result
        mock_result = Mock()
        mock_result.data = {
            'id': knowledge_id,
            'text': 'Test knowledge content',
            'metadata': {'source': 'test'},
            'chunk_index': 0,
            'source_document': 'test_doc',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00'
        }
        service._mock_table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        # Execute
        result = await service.get_knowledge(user_id, knowledge_id)
        
        # Verify
        assert result['success'] is True
        assert result['user_id'] == user_id
        assert result['knowledge_id'] == knowledge_id
        assert 'knowledge' in result
        
        knowledge = result['knowledge']
        assert knowledge['id'] == knowledge_id
        assert knowledge['text'] == 'Test knowledge content'
        assert knowledge['mcp_address'] == f"mcp://rag/{user_id}/{knowledge_id}"
    
    @pytest.mark.asyncio
    async def test_user_isolation(self, rag_service_instance):
        """Test that users can only access their own knowledge."""
        # This test would verify that user_id filtering works correctly
        # by checking that queries always include user_id filters
        
        service = rag_service_instance
        user1_id = "user1"
        user2_id = "user2"
        
        # Mock database calls to verify user_id filtering
        mock_result = Mock()
        mock_result.data = []
        service._mock_table.select.return_value.eq.return_value.execute.return_value = mock_result
        
        # Execute operation for user1
        await service.list_user_knowledge(user1_id)
        
        # Verify that eq was called with user1_id
        service._mock_table.select.return_value.eq.assert_called_with('user_id', user1_id)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, rag_service_instance):
        """Test error handling in various scenarios."""
        service = rag_service_instance
        user_id = "test_user"
        
        # Test database error during storage
        service._mock_table.insert.side_effect = Exception("Database error")
        
        result = await service.store_knowledge(user_id, "test text")
        
        assert result['success'] is False
        assert 'error' in result
        assert result['user_id'] == user_id

class TestRAGServiceIntegration:
    """Integration tests for RAG Service with real components (when available)."""
    
    @pytest.fixture
    def real_rag_service(self):
        """Create RAG service instance with real dependencies."""
        # Load development environment for testing
        import os
        from dotenv import load_dotenv
        
        # Load dev environment
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '../../../../../..'))
        env_file = os.path.join(project_root, "deployment/dev/.env")
        
        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
        
        # Set environment for dev database schema
        os.environ['ENV'] = 'development'
        os.environ['DB_SCHEMA'] = 'dev'
        
        # Create service with real dependencies
        service = RAGService({
            'chunk_size': 300,
            'overlap': 30,
            'top_k': 3,
            'embedding_model': 'text-embedding-3-small',
            'enable_rerank': False  # Start with reranking disabled for reliability
        })
        
        return service
    
    @pytest.mark.skipif(not os.getenv('INTEGRATION_TESTS'), reason="Integration tests disabled")
    @pytest.mark.asyncio
    async def test_real_embedding_integration(self, real_rag_service):
        """Test with real embedding service (if available)."""
        service = real_rag_service
        
        # Test data
        test_text = "Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models."
        user_id = "integration_test_user_001"
        
        try:
            # Test store knowledge with real embedding generation
            result = await service.store_knowledge(user_id, test_text, {'source': 'integration_test'})
            
            # Verify successful storage
            assert result['success'] is True
            assert 'knowledge_id' in result
            assert result['user_id'] == user_id
            assert result['text_length'] == len(test_text)
            assert result['embedding_dimensions'] > 0  # Real embedding should have dimensions
            
            knowledge_id = result['knowledge_id']
            
            # Test retrieval with real search
            search_result = await service.retrieve_context(user_id, "artificial intelligence", top_k=1)
            
            assert search_result['success'] is True
            assert len(search_result['context_items']) >= 1
            
            # Verify we found our stored text
            found_text = search_result['context_items'][0]['text']
            assert test_text in found_text or found_text in test_text
            
            # Test knowledge search without reranking (default)
            knowledge_search = await service.search_knowledge(user_id, "machine learning algorithms", top_k=1)
            
            assert knowledge_search['success'] is True
            assert len(knowledge_search['search_results']) >= 1
            assert knowledge_search['reranking_used'] is False
            
            # Test knowledge search with reranking enabled
            try:
                knowledge_search_rerank = await service.search_knowledge(
                    user_id, "machine learning algorithms", top_k=1, enable_rerank=True
                )
                assert knowledge_search_rerank['success'] is True
                print(f"Reranking test: {len(knowledge_search_rerank['search_results'])} results")
            except Exception as rerank_error:
                print(f"Reranking failed (expected): {rerank_error}")
            
            # Test response generation
            response_result = await service.generate_response(user_id, "What is machine learning?", context_limit=1)
            
            assert response_result['success'] is True
            assert 'response' in response_result
            assert len(response_result['context_items']) >= 1
            
            # Cleanup: delete the test knowledge
            delete_result = await service.delete_knowledge(user_id, knowledge_id)
            assert delete_result['success'] is True
            
        except Exception as e:
            pytest.fail(f"Real embedding integration test failed: {str(e)}")
    
    @pytest.mark.skipif(not os.getenv('INTEGRATION_TESTS'), reason="Integration tests disabled")
    @pytest.mark.asyncio
    async def test_real_supabase_integration(self, real_rag_service):
        """Test with real Supabase database (if available)."""
        service = real_rag_service
        
        # Test data
        user_id = "integration_test_user_002"
        test_documents = [
            {
                'text': "Python is a high-level programming language known for its simplicity and readability.",
                'metadata': {'topic': 'programming', 'language': 'python'}
            },
            {
                'text': "JavaScript is the programming language of the web, used for both frontend and backend development.",
                'metadata': {'topic': 'programming', 'language': 'javascript'}
            },
            {
                'text': "Data science involves extracting insights from large datasets using statistical methods and machine learning.",
                'metadata': {'topic': 'data_science', 'field': 'analytics'}
            }
        ]
        
        stored_knowledge_ids = []
        
        try:
            # Test storing multiple knowledge items
            for doc in test_documents:
                result = await service.store_knowledge(user_id, doc['text'], doc['metadata'])
                assert result['success'] is True
                stored_knowledge_ids.append(result['knowledge_id'])
            
            # Test listing user knowledge
            list_result = await service.list_user_knowledge(user_id)
            assert list_result['success'] is True
            assert list_result['total_count'] >= len(test_documents)
            assert len(list_result['knowledge_items']) >= len(test_documents)
            
            # Test getting specific knowledge item
            for knowledge_id in stored_knowledge_ids:
                get_result = await service.get_knowledge(user_id, knowledge_id)
                assert get_result['success'] is True
                assert 'knowledge' in get_result
                assert get_result['knowledge']['id'] == knowledge_id
            
            # Test search across stored knowledge
            search_result = await service.search_knowledge(user_id, "programming languages", top_k=5)
            assert search_result['success'] is True
            assert len(search_result['search_results']) >= 2  # Should find Python and JavaScript docs
            
            # Test context retrieval
            context_result = await service.retrieve_context(user_id, "data analysis", top_k=3)
            assert context_result['success'] is True
            # Should find the data science document
            assert any('data science' in item['text'].lower() for item in context_result['context_items'])
            
        except Exception as e:
            pytest.fail(f"Real Supabase integration test failed: {str(e)}")
        
        finally:
            # Cleanup: delete all test knowledge items
            for knowledge_id in stored_knowledge_ids:
                try:
                    await service.delete_knowledge(user_id, knowledge_id)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to cleanup knowledge {knowledge_id}: {cleanup_error}")
    
    @pytest.mark.skipif(not os.getenv('INTEGRATION_TESTS'), reason="Integration tests disabled")
    @pytest.mark.asyncio
    async def test_real_document_chunking_integration(self, real_rag_service):
        """Test document chunking with real services."""
        service = real_rag_service
        
        # Create a longer document that will require chunking
        long_document = """
        Artificial Intelligence (AI) is a broad field of computer science focused on creating systems capable of performing tasks that typically require human intelligence. These tasks include learning, reasoning, problem-solving, perception, and language understanding.

        Machine Learning is a subset of AI that focuses on algorithms and statistical models that enable computer systems to improve their performance on a specific task through experience. Instead of being explicitly programmed for every possible scenario, machine learning systems learn patterns from data.

        Deep Learning is a specialized subset of machine learning that uses artificial neural networks with multiple layers (hence "deep") to model and understand complex patterns in data. Deep learning has been particularly successful in areas like image recognition, natural language processing, and speech recognition.

        Natural Language Processing (NLP) is the branch of AI that deals with the interaction between computers and human language. It involves enabling computers to understand, interpret, and generate human language in a valuable way. NLP combines computational linguistics with machine learning and deep learning models.

        Computer Vision is another important field within AI that focuses on enabling machines to interpret and understand visual information from the world. This includes tasks like image classification, object detection, facial recognition, and autonomous vehicle navigation.

        The applications of AI are vast and growing, spanning industries from healthcare and finance to transportation and entertainment. As AI technology continues to advance, it promises to transform how we work, live, and interact with technology.
        """ * 2  # Make it even longer to ensure chunking
        
        user_id = "integration_test_user_003"
        
        try:
            # Test document addition with chunking
            result = await service.add_document(
                user_id=user_id,
                document=long_document,
                chunk_size=400,
                overlap=50,
                metadata={'source': 'AI_textbook', 'chapter': 'introduction'}
            )
            
            assert result['success'] is True
            assert result['total_chunks'] > 1  # Should be chunked into multiple pieces
            assert result['stored_chunks'] == result['total_chunks']  # All chunks should be stored
            assert 'document_id' in result
            
            document_id = result['document_id']
            stored_chunk_ids = [chunk['knowledge_id'] for chunk in result['chunks']]
            
            # Test that we can search across the chunked document
            search_result = await service.search_knowledge(user_id, "machine learning algorithms", top_k=3)
            assert search_result['success'] is True
            assert len(search_result['search_results']) >= 1
            
            # Test that chunks have proper metadata
            list_result = await service.list_user_knowledge(user_id)
            assert list_result['success'] is True
            
            # Find chunks belonging to our document
            document_chunks = [
                item for item in list_result['knowledge_items']
                if item['metadata'].get('document_id') == document_id
            ]
            
            assert len(document_chunks) == result['total_chunks']
            
            # Verify chunk metadata
            for chunk in document_chunks:
                metadata = chunk['metadata']
                assert metadata.get('document_id') == document_id
                assert 'chunk_index' in metadata
                assert metadata.get('source') == 'AI_textbook'
                assert metadata.get('chapter') == 'introduction'
            
            # Test generation with chunked content
            response_result = await service.generate_response(
                user_id, 
                "Explain the relationship between AI, machine learning, and deep learning",
                context_limit=3
            )
            
            assert response_result['success'] is True
            assert 'response' in response_result
            assert response_result['context_used'] >= 1
            
        except Exception as e:
            pytest.fail(f"Real document chunking integration test failed: {str(e)}")
        
        finally:
            # Cleanup: delete all chunks from this document
            try:
                list_result = await service.list_user_knowledge(user_id)
                if list_result['success']:
                    for item in list_result['knowledge_items']:
                        if item['metadata'].get('document_id') == document_id:
                            await service.delete_knowledge(user_id, item['knowledge_id'])
            except Exception as cleanup_error:
                print(f"Warning: Failed to cleanup document chunks: {cleanup_error}")
    
    @pytest.mark.skipif(not os.getenv('INTEGRATION_TESTS'), reason="Integration tests disabled")
    @pytest.mark.asyncio
    async def test_real_cross_user_isolation(self, real_rag_service):
        """Test that user data isolation works with real database."""
        service = real_rag_service
        
        # Create test data for two different users
        user1_id = "integration_test_user_004"
        user2_id = "integration_test_user_005"
        
        user1_text = "User 1's private knowledge about project management methodologies."
        user2_text = "User 2's private knowledge about software development practices."
        
        user1_knowledge_id = None
        user2_knowledge_id = None
        
        try:
            # Store knowledge for user 1
            result1 = await service.store_knowledge(user1_id, user1_text, {'owner': 'user1'})
            assert result1['success'] is True
            user1_knowledge_id = result1['knowledge_id']
            
            # Store knowledge for user 2
            result2 = await service.store_knowledge(user2_id, user2_text, {'owner': 'user2'})
            assert result2['success'] is True
            user2_knowledge_id = result2['knowledge_id']
            
            # Test that user 1 can only access their own knowledge
            user1_list = await service.list_user_knowledge(user1_id)
            assert user1_list['success'] is True
            user1_texts = [item['text_preview'] for item in user1_list['knowledge_items']]
            assert any('project management' in text for text in user1_texts)
            assert not any('software development' in text for text in user1_texts)
            
            # Test that user 2 can only access their own knowledge
            user2_list = await service.list_user_knowledge(user2_id)
            assert user2_list['success'] is True
            user2_texts = [item['text_preview'] for item in user2_list['knowledge_items']]
            assert any('software development' in text for text in user2_texts)
            assert not any('project management' in text for text in user2_texts)
            
            # Test that user 1 cannot access user 2's specific knowledge
            access_result = await service.get_knowledge(user1_id, user2_knowledge_id)
            assert access_result['success'] is False  # Just check that access was denied
            
            # Test that user 2 cannot access user 1's specific knowledge  
            access_result = await service.get_knowledge(user2_id, user1_knowledge_id)
            assert access_result['success'] is False  # Just check that access was denied
            
            # Test that search results are isolated per user
            search1 = await service.search_knowledge(user1_id, "management", top_k=5)
            assert search1['success'] is True
            search1_texts = [item['text'] for item in search1['search_results']]
            assert not any('software development' in text for text in search1_texts)
            
            search2 = await service.search_knowledge(user2_id, "development", top_k=5)
            assert search2['success'] is True
            search2_texts = [item['text'] for item in search2['search_results']]
            assert not any('project management' in text for text in search2_texts)
            
        except Exception as e:
            pytest.fail(f"Real cross-user isolation test failed: {str(e)}")
        
        finally:
            # Cleanup
            if user1_knowledge_id:
                try:
                    await service.delete_knowledge(user1_id, user1_knowledge_id)
                except Exception:
                    pass
            if user2_knowledge_id:
                try:
                    await service.delete_knowledge(user2_id, user2_knowledge_id)
                except Exception:
                    pass

class TestRAGServicePerformance:
    """Performance tests for RAG Service."""
    
    @pytest.fixture
    def mock_supabase(self):
        """Mock Supabase client for performance tests."""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        return mock_client, mock_table
    
    @pytest.fixture
    def mock_embedding_generator(self):
        """Mock embedding generator functions for performance tests."""
        with patch('tools.services.data_analytics_service.services.digital_service.rag_service.embed') as mock_embed, \
             patch('tools.services.data_analytics_service.services.digital_service.rag_service.search') as mock_search, \
             patch('tools.services.data_analytics_service.services.digital_service.rag_service.chunk') as mock_chunk, \
             patch('tools.services.data_analytics_service.services.digital_service.rag_service.rerank') as mock_rerank:
            
            mock_embed.return_value = [0.1] * 1536
            mock_search.return_value = [("Machine learning is a subset of AI", 0.8), ("Deep learning uses neural networks", 0.6)]
            mock_chunk.return_value = [
                {'text': 'chunk 1', 'index': 0, 'metadata': {}},
                {'text': 'chunk 2', 'index': 1, 'metadata': {}}
            ]
            mock_rerank.return_value = [
                {'document': 'Machine learning is a subset of AI', 'relevance_score': 0.9},
                {'document': 'Deep learning uses neural networks', 'relevance_score': 0.7}
            ]
            
            yield {
                'embed': mock_embed,
                'search': mock_search,
                'chunk': mock_chunk,
                'rerank': mock_rerank
            }
    
    @pytest.fixture
    def mock_graph_resources(self):
        """Mock graph knowledge resources for performance tests."""
        with patch('tools.services.data_analytics_service.services.digital_service.rag_service.graph_knowledge_resources') as mock_graph:
            mock_graph.register_resource = AsyncMock(return_value={'success': True})
            mock_graph.delete_resource = AsyncMock(return_value={'success': True})
            yield mock_graph
    
    @pytest.fixture
    def rag_service_instance(self, mock_supabase, mock_embedding_generator, mock_graph_resources):
        """Create RAG service instance with mocked dependencies for performance tests."""
        mock_client, mock_table = mock_supabase
        
        with patch('tools.services.data_analytics_service.services.digital_service.rag_service.get_supabase_client') as mock_get_client:
            mock_get_client.return_value = mock_client
            
            service = RAGService({
                'chunk_size': 400,
                'overlap': 50,
                'top_k': 5,
                'embedding_model': 'text-embedding-3-small'
            })
            
            # Store references for test verification
            service._mock_table = mock_table
            service._mock_embedding = mock_embedding_generator
            service._mock_graph = mock_graph_resources
            
            return service
    
    @pytest.mark.asyncio
    async def test_batch_operations_performance(self, rag_service_instance):
        """Test performance of batch operations."""
        service = rag_service_instance
        user_id = "perf_test_user"
        
        # Mock successful operations
        with patch.object(service, 'store_knowledge') as mock_store:
            mock_store.return_value = {
                'success': True,
                'knowledge_id': 'test_id',
                'mcp_address': 'test_address'
            }
            
            # Test adding multiple documents
            documents = [f"Document {i} content" for i in range(10)]
            
            import time
            start_time = time.time()
            
            tasks = [service.add_document(user_id, doc) for doc in documents]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify all operations completed
            assert len(results) == 10
            assert all(result.get('success') for result in results if isinstance(result, dict))
            
            # Performance assertion (adjust based on requirements)
            assert duration < 5.0  # Should complete within 5 seconds

def test_rag_service_global_instance():
    """Test that global RAG service instance is properly initialized."""
    from tools.services.data_analytics_service.services.digital_service.rag_service import rag_service
    
    assert rag_service is not None
    assert isinstance(rag_service, RAGService)
    assert rag_service.table_name == "user_knowledge"
    assert rag_service.default_chunk_size == 400
    assert rag_service.default_overlap == 50

# Test configuration and setup
def test_rag_service_configuration():
    """Test RAG service configuration options."""
    config = {
        'chunk_size': 300,
        'overlap': 40,
        'top_k': 10,
        'embedding_model': 'custom-model'
    }
    
    service = RAGService(config)
    
    assert service.default_chunk_size == 300
    assert service.default_overlap == 40
    assert service.default_top_k == 10
    assert service.embedding_model == 'custom-model'

if __name__ == '__main__':
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Run RAG Service Tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests with real services')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only (default)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Set up test arguments
    test_args = [__file__]
    
    if args.verbose:
        test_args.append('-v')
    else:
        test_args.append('-q')
    
    if args.integration:
        # Enable integration tests
        os.environ['INTEGRATION_TESTS'] = '1'
        print("Running integration tests with real services...")
        print("Make sure you have:")
        print("1. ISA model service running (http://localhost:8082)")
        print("2. Supabase local instance running (http://127.0.0.1:54321)")
        print("3. Proper environment variables set in deployment/dev/.env")
        print()
        
        # Run only integration tests
        test_args.extend(['-k', 'TestRAGServiceIntegration'])
    elif args.unit:
        # Run only unit tests (exclude integration)
        test_args.extend(['-k', 'not TestRAGServiceIntegration'])
    else:
        # Default: run unit tests only
        test_args.extend(['-k', 'not TestRAGServiceIntegration'])
        print("Running unit tests only. Use --integration to run integration tests.")
    
    # Run tests
    pytest.main(test_args)