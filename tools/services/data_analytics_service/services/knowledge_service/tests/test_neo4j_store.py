#!/usr/bin/env python3
"""
Comprehensive tests for Neo4j GraphRAG Store with vector capabilities.

Tests vector storage, semantic search, graph traversal, and hybrid search operations.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from tools.services.data_analytics_service.services.knowledge_service.neo4j_store import (
    Neo4jStore
)
from tools.services.data_analytics_service.services.knowledge_service.neo4j_client import Neo4jClient


class TestNeo4jStore:
    """Test suite for Neo4jStore class."""

    @pytest.fixture
    def mock_neo4j_client(self):
        """Mock Neo4j client for testing."""
        mock_client = AsyncMock(spec=Neo4jClient)
        
        # Mock vector similarity search
        mock_client.vector_similarity_search.return_value = [
            {
                "id": "org_apple_inc_1",
                "text": "Apple Inc",
                "canonical_form": "Apple Inc",
                "entity_type": "ORGANIZATION",
                "score": 0.95
            },
            {
                "id": "prod_iphone_1", 
                "text": "iPhone",
                "canonical_form": "iPhone",
                "entity_type": "PRODUCT",
                "score": 0.87
            }
        ]
        
        # Mock entity neighbors
        mock_client.get_entity_neighbors.return_value = [
            "iPhone", "iPad", "MacBook"
        ]
        
        # Mock shortest path
        mock_client.find_shortest_path.return_value = {
            "found": True,
            "length": 2,
            "nodes": ["Apple Inc", "intermediate", "iPhone"]
        }
        
        # Mock entity retrieval
        mock_client.get_entity.return_value = {
            "name": "Apple Inc",
            "type": "ORGANIZATION",
            "canonical_form": "Apple Inc",
            "confidence": 0.95,
            "id": "org_apple_inc_1"
        }
        
        # Mock storage operations
        mock_client.store_entity.return_value = {"success": True}
        mock_client.store_relationship.return_value = {"success": True}
        
        return mock_client

    @pytest.fixture
    def mock_embedding_generator(self):
        """Mock embedding generator."""
        mock_gen = AsyncMock()
        mock_gen.embed_single.return_value = [0.1] * 1536
        mock_gen.embed_batch.return_value = [[0.1] * 1536, [0.2] * 1536]
        return mock_gen

    @pytest.fixture
    def mock_graph_constructor(self):
        """Mock graph constructor."""
        mock_constructor = AsyncMock()
        return mock_constructor

    @pytest.fixture
    @patch('tools.services.data_analytics_service.services.knowledge_service.neo4j_store.GraphConstructor')
    @patch('tools.services.data_analytics_service.services.knowledge_service.neo4j_store.EmbeddingGenerator')
    def neo4j_store(self, mock_embedding_class, mock_constructor_class, 
                   mock_neo4j_client, mock_embedding_generator, mock_graph_constructor):
        """Neo4j store with mocked dependencies."""
        mock_embedding_class.return_value = mock_embedding_generator
        mock_constructor_class.return_value = mock_graph_constructor
        return Neo4jStore(mock_neo4j_client)

    @pytest.fixture
    def sample_graph_data(self):
        """Sample graph data for testing storage."""
        return {
            "entities": [
                {
                    "id": "org_apple_inc_1",
                    "name": "Apple Inc",
                    "type": "ORGANIZATION",
                    "canonical_form": "Apple Inc",
                    "confidence": 0.95,
                    "embedding": [0.1] * 1536,
                    "attributes": {
                        "founded": {
                            "value": "1976",
                            "type": "TEMPORAL",
                            "confidence": 0.95
                        }
                    }
                },
                {
                    "id": "prod_iphone_1",
                    "name": "iPhone",
                    "type": "PRODUCT", 
                    "canonical_form": "iPhone",
                    "confidence": 0.90,
                    "embedding": [0.2] * 1536,
                    "attributes": {
                        "category": {
                            "value": "smartphone",
                            "type": "CATEGORICAL",
                            "confidence": 0.85
                        }
                    }
                }
            ],
            "relations": [
                {
                    "id": "creates_1",
                    "source_id": "org_apple_inc_1",
                    "target_id": "prod_iphone_1",
                    "type": "CREATES",
                    "predicate": "manufactures",
                    "confidence": 0.85,
                    "embedding": [0.3] * 1536,
                    "context": "Apple Inc manufactures iPhone"
                }
            ]
        }

    # Removed retrieval tests - these are now handled by KnowledgeRetriever

    @pytest.mark.asyncio
    async def test_store_knowledge_graph(self, neo4j_store, sample_graph_data, mock_neo4j_client):
        """Test storing complete knowledge graph with embeddings."""
        # Act
        storage_result = await neo4j_store.store_knowledge_graph(sample_graph_data)
        
        # Assert
        assert storage_result["entities_stored"] == 2
        assert storage_result["relations_stored"] == 1
        assert storage_result["total_entities"] == 2
        assert storage_result["total_relations"] == 1
        
        # Verify storage calls
        assert mock_neo4j_client.store_entity.call_count == 2
        assert mock_neo4j_client.store_relationship.call_count == 1
        
        # Check entity storage call
        entity_call = mock_neo4j_client.store_entity.call_args_list[0][1]
        assert entity_call["name"] == "Apple Inc"
        assert entity_call["entity_type"] == "ORGANIZATION"
        assert entity_call["embedding"] == [0.1] * 1536
        assert "attr_founded" in entity_call["properties"]

    @pytest.mark.asyncio
    async def test_store_knowledge_graph_with_errors(self, neo4j_store, sample_graph_data, mock_neo4j_client):
        """Test knowledge graph storage with partial failures."""
        # Arrange - Make entity storage fail for second entity
        mock_neo4j_client.store_entity.side_effect = [
            {"success": True},  # First entity succeeds
            Exception("Storage failed")  # Second entity fails
        ]
        
        # Act
        storage_result = await neo4j_store.store_knowledge_graph(sample_graph_data)
        
        # Assert
        assert storage_result["entities_stored"] == 1  # Only one succeeded
        assert storage_result["total_entities"] == 2   # But we tried to store 2

    @pytest.mark.asyncio
    async def test_extract_and_store_from_text(self, neo4j_store, mock_graph_constructor):
        """Test text extraction and storage using GraphConstructor."""
        # Arrange
        text = "Apple Inc manufactures iPhone smartphones"
        source_id = "doc_123"
        chunk_id = "chunk_1"
        
        # Mock the GraphConstructor methods
        mock_graph_constructor.construct_from_text.return_value = {"test": "graph"}
        mock_graph_constructor.export_for_neo4j_storage.return_value = {
            "entities": [],
            "relations": []
        }
        
        # Act
        result = await neo4j_store.extract_and_store_from_text(
            text=text,
            source_id=source_id,
            chunk_id=chunk_id
        )
        
        # Assert
        assert result["source_id"] == source_id
        assert result["chunk_id"] == chunk_id
        assert result["text_length"] == len(text)
        mock_graph_constructor.construct_from_text.assert_called_once()
        mock_graph_constructor.export_for_neo4j_storage.assert_called_once()

    @pytest.mark.asyncio
    async def test_storage_error_handling(self, neo4j_store, mock_neo4j_client):
        """Test error handling in storage operations."""
        # Arrange
        mock_neo4j_client.store_entity.side_effect = Exception("Storage failed")
        graph_data = {
            "entities": [{"id": "test", "name": "Test", "type": "TEST", "embedding": [0.1] * 1536}],
            "relations": []
        }
        
        # Act
        result = await neo4j_store.store_knowledge_graph(graph_data)
        
        # Assert
        assert result["entities_stored"] == 0
        assert result["total_entities"] == 1

    @pytest.mark.asyncio
    async def test_empty_graph_data_storage(self, neo4j_store):
        """Test storing empty graph data."""
        # Arrange
        empty_graph_data = {"entities": [], "relations": []}
        
        # Act
        storage_result = await neo4j_store.store_knowledge_graph(empty_graph_data)
        
        # Assert
        assert storage_result["entities_stored"] == 0
        assert storage_result["relations_stored"] == 0
        assert storage_result["total_entities"] == 0
        assert storage_result["total_relations"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_storage_operations(self, neo4j_store):
        """Test concurrent storage operations."""
        # Arrange
        graph_data_sets = [
            {"entities": [], "relations": []},
            {"entities": [], "relations": []},
            {"entities": [], "relations": []}
        ]
        
        # Act
        tasks = [neo4j_store.store_knowledge_graph(data) for data in graph_data_sets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_large_graph_storage(self, neo4j_store, mock_neo4j_client):
        """Test handling of large graph data."""
        # Arrange
        large_graph_data = {
            "entities": [{"id": f"entity_{i}", "name": f"Entity {i}", "type": "TEST", "embedding": [0.1] * 1536} for i in range(100)],
            "relations": [{"id": f"rel_{i}", "source_id": f"entity_{i}", "target_id": f"entity_{i+1}", "type": "CONNECTS", "embedding": [0.2] * 1536} for i in range(99)]
        }
        
        # Act
        result = await neo4j_store.store_knowledge_graph(large_graph_data)
        
        # Assert
        assert result["total_entities"] == 100
        assert result["total_relations"] == 99
        # Storage calls should be made for all entities and relations
        assert mock_neo4j_client.store_entity.call_count == 100
        assert mock_neo4j_client.store_relationship.call_count == 99

    @pytest.mark.asyncio
    async def test_client_initialization_and_cleanup(self):
        """Test client initialization and cleanup."""
        # Arrange
        mock_client = AsyncMock()
        
        # Act
        store = Neo4jStore(mock_client)
        await store.close()
        
        # Assert
        assert store.neo4j_client == mock_client
        # Note: close() method calls neo4j_client.close() but our mock doesn't have it
        # This tests the interface


@pytest.mark.integration
class TestNeo4jStoreIntegration:
    """Integration tests for Neo4j GraphRAG Store."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete workflow from storage to retrieval."""
        # This would require a real Neo4j instance
        pytest.skip("Integration test requires real Neo4j instance")

    @pytest.mark.asyncio
    async def test_real_vector_search(self):
        """Test with real vector search capabilities."""
        # This would require Neo4j with vector support
        pytest.skip("Integration test requires Neo4j with vector support")

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """Test performance with large graphs."""
        # This would test with large datasets
        pytest.skip("Performance test requires large dataset")


class TestNeo4jStoreEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def neo4j_store_with_failing_client(self):
        """Neo4j store with a client that always fails."""
        mock_client = AsyncMock()
        mock_client.vector_similarity_search.side_effect = Exception("Connection failed")
        mock_client.store_entity.side_effect = Exception("Storage failed")
        mock_client.store_relationship.side_effect = Exception("Storage failed")
        
        with patch('tools.services.data_analytics_service.services.knowledge_service.neo4j_store.GraphConstructor'), \
             patch('tools.services.data_analytics_service.services.knowledge_service.neo4j_store.EmbeddingGenerator'):
            return Neo4jStore(mock_client)

    @pytest.mark.asyncio
    async def test_all_operations_fail_gracefully(self, neo4j_store_with_failing_client):
        """Test that all operations fail gracefully."""
        store = neo4j_store_with_failing_client
        
        # Test storage failure only (retrieval is handled by KnowledgeRetriever)
        storage_result = await store.store_knowledge_graph({"entities": [{"id": "test", "name": "Test", "type": "TEST", "embedding": [0.1]*1536}], "relations": []})
        assert "error" in storage_result or storage_result["entities_stored"] == 0

    @pytest.mark.asyncio
    async def test_malformed_graph_data(self, neo4j_store):
        """Test handling of malformed graph data."""
        # Arrange
        malformed_data = {
            "entities": [
                {"name": "Test"}  # Missing required fields
            ],
            "relations": [
                {"source_id": "invalid"}  # Missing target
            ]
        }
        
        # Act
        storage_result = await neo4j_store.store_knowledge_graph(malformed_data)
        
        # Assert
        # Should handle gracefully with partial success
        assert "entities_stored" in storage_result
        assert "relations_stored" in storage_result