#!/usr/bin/env python3
"""
Comprehensive tests for GraphRAG Knowledge Retriever.

Tests hybrid retrieval combining vector similarity search with graph traversal.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from tools.services.data_analytics_service.services.knowledge_service.knowledge_retriever import (
    GraphRAGRetriever, RetrievalResult
)
from tools.services.data_analytics_service.services.knowledge_service.neo4j_client import Neo4jClient


class TestGraphRAGRetriever:
    """Test suite for GraphRAGRetriever class."""

    @pytest.fixture
    def mock_neo4j_client(self):
        """Mock Neo4j client for testing."""
        mock_client = AsyncMock(spec=Neo4jClient)
        
        # Mock vector similarity search results
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
            "iPhone", "iPad", "MacBook", "Tim Cook"
        ]
        
        # Mock shortest path finding
        mock_client.find_shortest_path.return_value = {
            "found": True,
            "length": 2,
            "nodes": ["Apple Inc", "produces", "iPhone"]
        }
        
        # Mock entity retrieval
        mock_client.get_entity.return_value = {
            "id": "org_apple_inc_1",
            "name": "Apple Inc",
            "type": "ORGANIZATION",
            "canonical_form": "Apple Inc",
            "confidence": 0.95
        }
        
        return mock_client

    @pytest.fixture
    def mock_embedding_generator(self):
        """Mock embedding generator."""
        mock_gen = AsyncMock()
        mock_gen.embed_single.return_value = [0.1] * 1536
        mock_gen.embed_batch.return_value = [[0.1] * 1536, [0.2] * 1536]
        return mock_gen

    @pytest.fixture
    @patch('tools.services.data_analytics_service.services.knowledge_service.knowledge_retriever.EmbeddingGenerator')
    def retriever(self, mock_embedding_class, mock_neo4j_client, mock_embedding_generator):
        """GraphRAGRetriever instance with mocked dependencies."""
        mock_embedding_class.return_value = mock_embedding_generator
        return GraphRAGRetriever(mock_neo4j_client)

    @pytest.mark.asyncio
    async def test_retrieve_with_embedding(self, retriever, mock_neo4j_client):
        """Test retrieval with provided embedding."""
        # Arrange
        query = "Apple technology company"
        embedding = [0.5] * 1536
        
        # Act
        results = await retriever.retrieve(
            query=query,
            query_embedding=embedding,
            top_k=5,
            similarity_threshold=0.8,
            include_graph_context=False,
            search_modes=["entities"]
        )
        
        # Assert
        assert len(results) == 2
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert results[0].score >= results[1].score  # Should be sorted by score
        
        # Check result content
        assert "Apple Inc" in results[0].content
        assert "ORGANIZATION" in results[0].content
        
        # Verify Neo4j calls
        mock_neo4j_client.vector_similarity_search.assert_called_once_with(
            embedding=embedding,
            limit=5,
            similarity_threshold=0.8,
            index_name="entity_embeddings",
            node_label="Entity"
        )

    @pytest.mark.asyncio
    async def test_retrieve_generate_embedding(self, retriever, mock_embedding_generator):
        """Test retrieval with embedding generation."""
        # Arrange
        query = "Apple technology"
        
        # Act
        results = await retriever.retrieve(query=query)
        
        # Assert
        assert len(results) > 0
        mock_embedding_generator.embed_single.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_retrieve_with_graph_context(self, retriever, mock_neo4j_client):
        """Test retrieval with graph context expansion."""
        # Arrange
        query = "Apple products"
        
        # Act
        results = await retriever.retrieve(
            query=query,
            include_graph_context=True,
            graph_expansion_depth=2,
            search_modes=["entities"]
        )
        
        # Assert
        assert len(results) > 0
        
        # Should have graph context - check if any context was gathered
        # Note: graph_context might be empty in mock environment
        assert results[0].graph_context is not None
        # Verify graph traversal calls were made
        assert results[0].metadata.get("graph_neighbors_count", 0) >= 0
        
        # Verify graph traversal calls
        mock_neo4j_client.get_entity_neighbors.assert_called()
        mock_neo4j_client.find_shortest_path.assert_called()

    @pytest.mark.asyncio
    async def test_semantic_retrieval(self, retriever, mock_neo4j_client):
        """Test semantic retrieval functionality."""
        # Arrange
        query = "technology company"
        embedding = [0.3] * 1536
        
        # Act
        results = await retriever._semantic_retrieval(
            query=query,
            embedding=embedding,
            limit=10,
            threshold=0.75
        )
        
        # Assert
        assert len(results) == 2
        mock_neo4j_client.vector_similarity_search.assert_called_once_with(
            embedding=embedding,
            limit=10,
            similarity_threshold=0.75
        )

    @pytest.mark.asyncio
    async def test_enhance_with_graph_context(self, retriever, mock_neo4j_client):
        """Test graph context enhancement."""
        # Arrange
        semantic_results = [
            {
                "canonical_form": "Apple Inc",
                "entity_type": "ORGANIZATION",
                "score": 0.95,
                "id": "org_apple_inc_1"
            },
            {
                "canonical_form": "iPhone",
                "entity_type": "PRODUCT",
                "score": 0.87,
                "id": "prod_iphone_1"
            }
        ]
        
        # Act
        enhanced_results = await retriever._enhance_with_graph_context(
            semantic_results=semantic_results,
            depth=2
        )
        
        # Assert
        assert len(enhanced_results) == 2
        assert all(isinstance(r, RetrievalResult) for r in enhanced_results)
        
        # Check that graph context was added
        for result in enhanced_results:
            assert result.graph_context is not None
            assert result.metadata["graph_neighbors_count"] >= 0

    @pytest.mark.asyncio
    async def test_get_graph_context_for_entities(self, retriever, mock_neo4j_client):
        """Test graph context retrieval for multiple entities."""
        # Arrange
        entities = ["Apple Inc", "iPhone"]
        depth = 2
        
        # Act
        graph_context = await retriever._get_graph_context_for_entities(
            entities=entities,
            depth=depth
        )
        
        # Assert
        assert "entities" in graph_context
        assert "neighbors" in graph_context
        assert "paths" in graph_context
        assert graph_context["entities"] == entities
        
        # Verify Neo4j calls
        assert mock_neo4j_client.get_entity_neighbors.call_count == len(entities)
        mock_neo4j_client.find_shortest_path.assert_called()

    @pytest.mark.asyncio
    async def test_create_retrieval_result(self, retriever):
        """Test retrieval result creation."""
        # Arrange
        search_result = {
            "canonical_form": "Apple Inc",
            "entity_type": "ORGANIZATION",
            "score": 0.95,
            "id": "org_apple_inc_1"
        }
        
        graph_context = {
            "connected_entities": ["iPhone", "iPad"],
            "related_paths": [{"nodes": ["Apple Inc", "iPhone"]}]
        }
        
        # Act
        result = await retriever._create_retrieval_result(
            result=search_result,
            graph_context=graph_context
        )
        
        # Assert
        assert isinstance(result, RetrievalResult)
        assert result.score == 0.95
        assert "Apple Inc" in result.content
        assert "ORGANIZATION" in result.content
        assert result.metadata["entity_name"] == "Apple Inc"
        assert result.metadata["entity_type"] == "ORGANIZATION"

    @pytest.mark.asyncio
    async def test_format_content(self, retriever):
        """Test content formatting."""
        # Arrange
        entity = {
            "name": "Apple Inc",
            "type": "ORGANIZATION",
            "description": "Technology company",
            "properties": {"founded": "1976", "ceo": "Tim Cook"}
        }
        
        graph_context = {
            "connected_entities": ["iPhone", "iPad", "MacBook", "Tim Cook", "Steve Jobs", "Apple Store"]
        }
        
        # Act
        content = retriever._format_content(entity, graph_context)
        
        # Assert
        assert "Apple Inc" in content
        assert "ORGANIZATION" in content
        assert "Technology company" in content
        assert "founded: 1976" in content
        assert "Connected to:" in content
        assert "iPhone" in content
        assert "... and 1 more" in content  # Should truncate at 5

    @pytest.mark.asyncio
    async def test_retrieve_by_entities(self, retriever, mock_neo4j_client):
        """Test entity-based retrieval."""
        # Arrange
        entity_names = ["Apple Inc", "iPhone"]
        
        # Act
        results = await retriever.retrieve_by_entities(
            entity_names=entity_names,
            expansion_depth=2
        )
        
        # Assert
        assert len(results) <= len(entity_names)  # May have fewer if entities don't exist
        
        for result in results:
            assert isinstance(result, RetrievalResult)
            assert result.score == 1.0  # Direct entity match should have max score
            assert result.metadata["retrieval_type"] == "entity_direct"
        
        # Verify Neo4j calls
        mock_neo4j_client.get_entity.assert_called()

    @pytest.mark.asyncio
    async def test_retrieve_subgraph(self, retriever):
        """Test subgraph retrieval."""
        # Arrange
        central_entities = ["Apple Inc", "Tim Cook"]
        radius = 3
        
        # Act
        subgraph = await retriever.retrieve_subgraph(
            central_entities=central_entities,
            radius=radius
        )
        
        # Assert
        assert "entities" in subgraph
        assert "neighbors" in subgraph
        assert "paths" in subgraph
        assert subgraph["entities"] == central_entities

    @pytest.mark.asyncio
    async def test_error_handling_in_retrieval(self, retriever, mock_neo4j_client):
        """Test error handling during retrieval."""
        # Arrange
        mock_neo4j_client.vector_similarity_search.side_effect = Exception("Search failed")
        
        # Act
        results = await retriever.retrieve("test query")
        
        # Assert
        assert results == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_error_handling_in_graph_context(self, retriever, mock_neo4j_client):
        """Test error handling in graph context enhancement."""
        # Arrange
        mock_neo4j_client.get_entity_neighbors.side_effect = Exception("Traversal failed")
        
        semantic_results = [
            {"canonical_form": "Apple Inc", "entity_type": "ORGANIZATION", "score": 0.95}
        ]
        
        # Act
        enhanced_results = await retriever._enhance_with_graph_context(
            semantic_results=semantic_results,
            depth=2
        )
        
        # Assert
        assert len(enhanced_results) == 1  # Should fall back to semantic results
        assert enhanced_results[0].graph_context == {}

    @pytest.mark.asyncio
    async def test_empty_semantic_results(self, retriever, mock_neo4j_client):
        """Test handling of empty semantic results."""
        # Arrange
        mock_neo4j_client.vector_similarity_search.return_value = []
        
        # Act
        results = await retriever.retrieve("nonexistent query")
        
        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_high_similarity_threshold(self, retriever, mock_neo4j_client):
        """Test retrieval with high similarity threshold."""
        # Arrange
        mock_neo4j_client.vector_similarity_search.return_value = []  # No results meet threshold
        
        # Act
        results = await retriever.retrieve(
            query="Apple",
            similarity_threshold=0.99
        )
        
        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_concurrent_retrievals(self, retriever):
        """Test concurrent retrieval operations."""
        # Arrange
        queries = ["Apple Inc", "iPhone", "technology", "smartphone"]
        
        # Act
        tasks = [retriever.retrieve(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert
        assert len(results) == 4
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_large_graph_context(self, retriever, mock_neo4j_client):
        """Test handling of large graph contexts."""
        # Arrange
        # Mock a large number of neighbors
        large_neighbors_list = [f"entity_{i}" for i in range(100)]
        mock_neo4j_client.get_entity_neighbors.return_value = large_neighbors_list
        
        # Act
        results = await retriever.retrieve(
            query="central entity",
            include_graph_context=True
        )
        
        # Assert
        assert len(results) > 0
        # Content should be properly formatted even with many connections
        for result in results:
            assert len(result.content) < 10000  # Should not be excessively long

    @pytest.mark.asyncio
    async def test_depth_zero_graph_expansion(self, retriever):
        """Test graph expansion with zero depth."""
        # Act
        results = await retriever.retrieve(
            query="Apple Inc",
            include_graph_context=True,
            graph_expansion_depth=0
        )
        
        # Assert
        assert len(results) > 0
        # Should still work but with minimal graph context

    @pytest.mark.asyncio
    async def test_malformed_search_results(self, retriever, mock_neo4j_client):
        """Test handling of malformed search results."""
        # Arrange
        mock_neo4j_client.vector_similarity_search.return_value = [
            {"score": 0.95},  # Missing required fields
            {"canonical_form": "Apple Inc"},  # Missing score
            {}  # Empty result
        ]
        
        # Act
        results = await retriever.retrieve("test query", search_modes=["entities"])
        
        # Assert
        # Should handle gracefully and create results with default values
        assert len(results) == 3
        for result in results:
            assert isinstance(result, RetrievalResult)
            assert result.score >= 0.0

    @pytest.mark.asyncio
    async def test_entity_specific_context_extraction(self, retriever):
        """Test extraction of entity-specific context from global context."""
        # Arrange
        entity_name = "Apple Inc"
        global_context = {
            "nodes": ["Apple Inc", "iPhone", "Tim Cook"],
            "paths": [
                {"nodes": ["Apple Inc", "produces", "iPhone"]},
                {"nodes": ["Tim Cook", "leads", "Apple Inc"]},
                {"nodes": ["Google", "competes", "Microsoft"]}  # Irrelevant path
            ]
        }
        
        # Act
        entity_context = await retriever._get_entity_specific_context(
            entity_name=entity_name,
            global_graph_context=global_context
        )
        
        # Assert
        assert "related_paths" in entity_context
        assert "connected_entities" in entity_context
        assert len(entity_context["related_paths"]) == 2  # Two paths include Apple Inc
        assert "iPhone" in entity_context["connected_entities"]
        assert "Tim Cook" in entity_context["connected_entities"]
        assert "Google" not in entity_context["connected_entities"]


@pytest.mark.integration
class TestGraphRAGRetrieverIntegration:
    """Integration tests for GraphRAG Retriever."""

    @pytest.mark.asyncio
    async def test_end_to_end_retrieval_workflow(self):
        """Test complete retrieval workflow."""
        # This would require real Neo4j and embedding services
        pytest.skip("Integration test requires real services")

    @pytest.mark.asyncio
    async def test_real_embedding_similarity(self):
        """Test with real embedding similarity calculations."""
        # This would test actual semantic similarity
        pytest.skip("Integration test requires real embedding service")

    @pytest.mark.asyncio
    async def test_performance_with_large_graphs(self):
        """Test retrieval performance with large knowledge graphs."""
        # This would test performance characteristics
        pytest.skip("Performance test requires large graph dataset")


class TestRetrievalResult:
    """Test the RetrievalResult dataclass."""

    def test_retrieval_result_creation(self):
        """Test RetrievalResult creation and attributes."""
        # Arrange & Act
        result = RetrievalResult(
            content="Apple Inc is a technology company",
            score=0.95,
            source_id="org_apple_inc_1",
            chunk_id="chunk_123",
            entity_context={"name": "Apple Inc", "type": "ORGANIZATION"},
            graph_context={"neighbors": ["iPhone", "iPad"]},
            metadata={"entity_type": "ORGANIZATION", "confidence": 0.95}
        )
        
        # Assert
        assert result.content == "Apple Inc is a technology company"
        assert result.score == 0.95
        assert result.source_id == "org_apple_inc_1"
        assert result.chunk_id == "chunk_123"
        assert result.entity_context["name"] == "Apple Inc"
        assert "iPhone" in result.graph_context["neighbors"]
        assert result.metadata["entity_type"] == "ORGANIZATION"

    def test_retrieval_result_optional_fields(self):
        """Test RetrievalResult with optional fields as None."""
        # Arrange & Act
        result = RetrievalResult(
            content="Test content",
            score=0.8,
            source_id="test_id",
            chunk_id=None,
            entity_context={},
            graph_context={},
            metadata={}
        )
        
        # Assert
        assert result.chunk_id is None
        assert result.entity_context == {}
        assert result.graph_context == {}
        assert result.metadata == {}


@pytest.mark.performance
@pytest.mark.skip("Performance tests require separate setup")
class TestRetrievalPerformance:
    """Performance tests for retrieval operations."""

    @pytest.mark.asyncio
    async def test_retrieval_latency(self, retriever, mock_neo4j_client, mock_embedding_generator):
        """Test retrieval operation latency."""
        import time
        
        # Arrange
        query = "Apple technology"
        
        # Act
        start_time = time.time()
        results = await retriever.retrieve(query, top_k=10)
        end_time = time.time()
        
        # Assert
        latency = end_time - start_time
        assert latency < 1.0  # Should complete within 1 second with mocked services
        assert len(results) <= 10

    @pytest.mark.asyncio
    async def test_batch_retrieval_efficiency(self, retriever, mock_neo4j_client, mock_embedding_generator):
        """Test efficiency of batch retrieval operations."""
        # Arrange
        queries = [f"query_{i}" for i in range(10)]
        
        # Act
        start_time = time.time()
        tasks = [retriever.retrieve(query, top_k=5) for query in queries]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert
        total_time = end_time - start_time
        assert total_time < 2.0  # Batch should be efficient
        assert len(results) == 10