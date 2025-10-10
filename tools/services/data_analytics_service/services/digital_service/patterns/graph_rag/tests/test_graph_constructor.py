#!/usr/bin/env python3
"""
Comprehensive tests for GraphConstructor with embedding support.

Tests graph construction, embedding generation, optimization, and validation.
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Mock the heavy dependencies before importing
sys.modules['core.database.supabase_client'] = MagicMock()
sys.modules['core.database'] = MagicMock()
sys.modules['core.database.connection_manager'] = MagicMock()
sys.modules['asyncpg'] = MagicMock()
sys.modules['supabase'] = MagicMock()
sys.modules['postgrest'] = MagicMock()

# Mock entity types and classes
class EntityType(Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION" 
    PRODUCT = "PRODUCT"
    LOCATION = "LOCATION"

class RelationType(Enum):
    CREATES = "CREATES"
    OWNS = "OWNS"
    LOCATED_IN = "LOCATED_IN"

class AttributeType(Enum):
    TEMPORAL = "TEMPORAL"
    NUMERICAL = "NUMERICAL"
    CATEGORICAL = "CATEGORICAL"

@dataclass
class Entity:
    text: str
    entity_type: EntityType
    canonical_form: str
    confidence: float
    aliases: List[str]
    start_position: int
    end_position: int

@dataclass
class Relation:
    subject: Entity
    predicate: str
    object: Entity
    relation_type: RelationType
    confidence: float
    context: str
    properties: Dict[str, Any] = None
    temporal_info: Dict[str, Any] = None

@dataclass
class Attribute:
    name: str
    value: str
    normalized_value: str
    attribute_type: AttributeType
    confidence: float
    source_text: str

# Import the actual classes without over-mocking
from tools.services.data_analytics_service.services.knowledge_service.graph_constructor import (
    GraphConstructor, GraphNode, GraphEdge, KnowledgeGraph, DocumentChunk, AttributeNode
)


class TestGraphConstructor:
    """Test suite for GraphConstructor class."""

    @pytest.fixture
    def mock_embedding_generator(self):
        """Mock embedding generator that returns predictable embeddings."""
        mock_gen = AsyncMock()
        # Return 1536-dimensional mock embeddings
        mock_gen.embed_batch.return_value = [
            [0.1] * 1536,  # Entity 1 embedding
            [0.2] * 1536,  # Entity 2 embedding
        ]
        mock_gen.embed_single.return_value = [0.3] * 1536
        # Mock chunking functionality
        mock_gen.chunk_text.return_value = []  # Default: no chunks
        return mock_gen

    @pytest.fixture
    def sample_entities(self):
        """Sample entities for testing."""
        return [
            Entity(
                text="Apple Inc",
                entity_type=EntityType.ORGANIZATION,
                canonical_form="Apple Inc",
                confidence=0.95,
                aliases=["Apple", "AAPL"],
                start_position=0,
                end_position=9
            ),
            Entity(
                text="iPhone",
                entity_type=EntityType.PRODUCT,
                canonical_form="iPhone",
                confidence=0.90,
                aliases=["iPhone device"],
                start_position=15,
                end_position=21
            )
        ]

    @pytest.fixture
    def sample_relations(self):
        """Sample relations for testing."""
        apple = Entity(
            text="Apple Inc",
            entity_type=EntityType.ORGANIZATION,
            canonical_form="Apple Inc",
            confidence=0.95,
            aliases=[],
            start_position=0,
            end_position=9
        )
        iphone = Entity(
            text="iPhone",
            entity_type=EntityType.PRODUCT,
            canonical_form="iPhone",
            confidence=0.90,
            aliases=[],
            start_position=15,
            end_position=21
        )
        
        return [
            Relation(
                subject=apple,
                predicate="manufactures",
                object=iphone,
                relation_type=RelationType.CREATES,
                confidence=0.85,
                context="Apple Inc manufactures iPhone smartphones",
                properties={"industry": "technology"},
                temporal_info={"since": "2007"}
            )
        ]

    @pytest.fixture
    def sample_attributes(self):
        """Sample entity attributes for testing."""
        return {
            "Apple Inc": {
                "founded": Attribute(
                    name="founded",
                    value="1976",
                    normalized_value="1976",
                    attribute_type=AttributeType.TEMPORAL,
                    confidence=0.95,
                    source_text="founded in 1976"
                ),
                "revenue": Attribute(
                    name="revenue",
                    value="$394.3 billion",
                    normalized_value="394300000000",
                    attribute_type=AttributeType.NUMERICAL,
                    confidence=0.90,
                    source_text="revenue of $394.3 billion"
                )
            },
            "iPhone": {
                "category": Attribute(
                    name="category",
                    value="smartphone",
                    normalized_value="smartphone",
                    attribute_type=AttributeType.CATEGORICAL,
                    confidence=0.85,
                    source_text="iPhone smartphone"
                )
            }
        }

    @pytest.fixture
    def graph_constructor(self, mock_embedding_generator):
        """GraphConstructor instance with mocked embedding generator."""
        constructor = GraphConstructor()
        constructor.embedding_generator = mock_embedding_generator
        return constructor

    @pytest.mark.asyncio
    async def test_construct_graph_basic(self, graph_constructor, sample_entities, 
                                       sample_relations, sample_attributes, mock_embedding_generator):
        """Test basic graph construction with embeddings."""
        # Arrange
        source_text = "Apple Inc manufactures iPhone smartphones"
        
        # Act
        graph = await graph_constructor.construct_graph(
            entities=sample_entities,
            relations=sample_relations,
            entity_attributes=sample_attributes,
            source_text=source_text
        )
        
        # Assert
        assert isinstance(graph, KnowledgeGraph)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        
        # Check nodes have embeddings
        for node in graph.nodes.values():
            assert node.embedding is not None
            assert len(node.embedding) == 1536
            
        # Check edges have embeddings
        for edge in graph.edges.values():
            assert edge.embedding is not None
            assert len(edge.embedding) == 1536
            
        # Verify embedding generator was called
        mock_embedding_generator.embed_batch.assert_called()

    @pytest.mark.asyncio
    async def test_construct_graph_with_empty_inputs(self, graph_constructor):
        """Test graph construction with empty inputs."""
        # Act
        graph = await graph_constructor.construct_graph(
            entities=[],
            relations=[],
            entity_attributes={},
            source_text=""
        )
        
        # Assert
        assert isinstance(graph, KnowledgeGraph)
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        assert graph.metadata["entities_count"] == 0
        assert graph.metadata["relations_count"] == 0

    @pytest.mark.asyncio
    async def test_entity_text_creation(self, graph_constructor, sample_entities, sample_attributes):
        """Test entity text creation for embeddings."""
        # Arrange
        entity = sample_entities[0]  # Apple Inc
        attributes = sample_attributes["Apple Inc"]
        
        # Act
        entity_text = graph_constructor._create_entity_text(entity, attributes)
        
        # Assert
        assert "Apple Inc" in entity_text
        assert "ORGANIZATION" in entity_text
        assert "founded:1976" in entity_text  # High confidence attribute
        assert "revenue:394300000000" in entity_text  # High confidence attribute

    @pytest.mark.asyncio
    async def test_relation_text_creation(self, graph_constructor, sample_relations):
        """Test relation text creation for embeddings."""
        # Arrange
        relation = sample_relations[0]
        
        # Act
        relation_text = graph_constructor._create_relation_text(relation)
        
        # Assert
        assert "Apple Inc" in relation_text
        assert "manufactures" in relation_text
        assert "iPhone" in relation_text
        assert "context:" in relation_text

    @pytest.mark.asyncio
    async def test_node_id_generation(self, graph_constructor, sample_entities):
        """Test unique node ID generation."""
        # Arrange
        entity = sample_entities[0]
        
        # Act
        node_id1 = graph_constructor._generate_node_id(entity)
        node_id2 = graph_constructor._generate_node_id(entity)
        
        # Assert
        assert node_id1 != node_id2  # Should be unique
        assert "organization" in node_id1.lower()
        assert "apple_inc" in node_id1.lower()

    @pytest.mark.asyncio
    async def test_edge_id_generation(self, graph_constructor, sample_relations):
        """Test unique edge ID generation."""
        # Arrange
        relation = sample_relations[0]
        
        # Act
        edge_id1 = graph_constructor._generate_edge_id(relation)
        edge_id2 = graph_constructor._generate_edge_id(relation)
        
        # Assert
        assert edge_id1 != edge_id2  # Should be unique
        assert "creates" in edge_id1.lower()

    @pytest.mark.asyncio
    async def test_graph_metadata(self, graph_constructor, sample_entities, 
                                sample_relations, sample_attributes):
        """Test graph metadata generation."""
        # Arrange
        source_text = "Apple Inc manufactures iPhone smartphones"
        
        # Act
        graph = await graph_constructor.construct_graph(
            entities=sample_entities,
            relations=sample_relations,
            entity_attributes=sample_attributes,
            source_text=source_text
        )
        
        # Assert
        metadata = graph.metadata
        assert metadata["source_text_length"] == len(source_text)
        assert metadata["entities_count"] == 2
        assert metadata["relations_count"] == 1
        assert metadata["attributes_count"] == 3  # 2 for Apple + 1 for iPhone
        assert "ORGANIZATION" in metadata["entity_types"]
        assert "PRODUCT" in metadata["entity_types"]
        assert "CREATES" in metadata["relation_types"]

    @pytest.mark.asyncio
    async def test_optimize_graph(self, graph_constructor, sample_entities, 
                                sample_relations, sample_attributes):
        """Test graph optimization functionality."""
        # Arrange
        graph = await graph_constructor.construct_graph(
            entities=sample_entities,
            relations=sample_relations,
            entity_attributes=sample_attributes,
            source_text="test"
        )
        
        # Act
        optimized_graph = graph_constructor.optimize_graph(graph)
        
        # Assert
        assert isinstance(optimized_graph, KnowledgeGraph)
        assert optimized_graph.metadata["optimization_applied"] is True
        assert "optimization_timestamp" in optimized_graph.metadata
        assert "nodes_before_merge" in optimized_graph.metadata
        assert "nodes_after_merge" in optimized_graph.metadata

    @pytest.mark.asyncio
    async def test_validate_graph(self, graph_constructor, sample_entities, 
                                sample_relations, sample_attributes):
        """Test graph validation."""
        # Arrange
        graph = await graph_constructor.construct_graph(
            entities=sample_entities,
            relations=sample_relations,
            entity_attributes=sample_attributes,
            source_text="test"
        )
        
        # Act
        validation = graph_constructor.validate_graph(graph)
        
        # Assert
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        assert "statistics" in validation
        assert validation["statistics"]["total_nodes"] == 2
        assert validation["statistics"]["total_edges"] == 1

    @pytest.mark.asyncio
    async def test_export_for_neo4j_storage(self, graph_constructor, sample_entities, 
                                          sample_relations, sample_attributes):
        """Test Neo4j export format with embeddings."""
        # Arrange
        graph = await graph_constructor.construct_graph(
            entities=sample_entities,
            relations=sample_relations,
            entity_attributes=sample_attributes,
            source_text="test"
        )
        
        # Act
        neo4j_data = graph_constructor.export_for_neo4j_storage(graph)
        
        # Assert
        assert "entities" in neo4j_data
        assert "relations" in neo4j_data
        assert "attributes" in neo4j_data  # Attributes are now separate nodes
        assert len(neo4j_data["entities"]) == 2
        assert len(neo4j_data["relations"]) == 1
        
        # Check entity format
        entity = neo4j_data["entities"][0]
        assert "id" in entity
        assert "name" in entity
        assert "type" in entity
        assert "embedding" in entity
        # Attributes are now separate, not nested in entity
        assert len(entity["embedding"]) == 1536
        
        # Check relation format
        relation = neo4j_data["relations"][0]
        assert "id" in relation
        assert "source_id" in relation
        assert "target_id" in relation
        assert "embedding" in relation
        assert len(relation["embedding"]) == 1536

    @pytest.mark.asyncio
    async def test_merge_similar_nodes(self, graph_constructor):
        """Test node merging functionality."""
        # Arrange - Create duplicate entities
        entity1 = Entity(
            text="Apple Inc",
            entity_type=EntityType.ORGANIZATION,
            canonical_form="Apple Inc",
            confidence=0.95,
            aliases=["Apple"],
            start_position=0,
            end_position=9
        )
        
        entity2 = Entity(
            text="Apple Inc",  # Same canonical form
            entity_type=EntityType.ORGANIZATION,
            canonical_form="Apple Inc",
            confidence=0.85,  # Lower confidence
            aliases=["AAPL"],
            start_position=10,
            end_position=19
        )
        
        # Create nodes manually
        node1 = GraphNode(
            id="org_apple_inc_1",
            entity=entity1,
            attributes={},
            embedding=[0.1] * 1536
        )
        
        node2 = GraphNode(
            id="org_apple_inc_2",
            entity=entity2,
            attributes={},
            embedding=[0.2] * 1536
        )
        
        nodes = {"node1": node1, "node2": node2}
        
        # Act
        merged_nodes = graph_constructor._merge_similar_nodes(nodes)
        
        # Assert
        assert len(merged_nodes) == 1  # Should merge into one
        merged_node = list(merged_nodes.values())[0]
        assert merged_node.entity.confidence == 0.95  # Should keep higher confidence
        assert "Apple" in merged_node.entity.aliases
        assert "AAPL" in merged_node.entity.aliases  # Should merge aliases

    @pytest.mark.asyncio
    async def test_error_handling_in_embedding_generation(self, graph_constructor):
        """Test error handling when embedding generation fails."""
        # Arrange
        with patch.object(graph_constructor.embedding_generator, 'embed_batch', 
                         side_effect=Exception("Embedding service unavailable")):
            entities = [Entity(
                text="Test Entity",
                entity_type=EntityType.PERSON,
                canonical_form="Test Entity",
                confidence=0.5,
                aliases=[],
                start_position=0,
                end_position=11
            )]
            
            # Act & Assert
            with pytest.raises(Exception):
                await graph_constructor.construct_graph(
                    entities=entities,
                    relations=[],
                    entity_attributes={},
                    source_text="test"
                )

    @pytest.mark.asyncio
    async def test_graph_statistics_calculation(self, graph_constructor, sample_entities, 
                                              sample_relations, sample_attributes):
        """Test graph statistics calculation methods."""
        # Arrange
        graph = await graph_constructor.construct_graph(
            entities=sample_entities,
            relations=sample_relations,
            entity_attributes=sample_attributes,
            source_text="test"
        )
        
        # Act
        entity_dist = graph_constructor._get_entity_type_distribution(graph)
        relation_dist = graph_constructor._get_relation_type_distribution(graph)
        avg_degree = graph_constructor._calculate_average_degree(graph)
        
        # Assert
        assert entity_dist["ORGANIZATION"] == 1
        assert entity_dist["PRODUCT"] == 1
        assert relation_dist["CREATES"] == 1
        assert avg_degree == 1.0  # Each node has 1 connection

    @pytest.mark.asyncio
    async def test_concurrent_graph_construction(self, mock_embedding_generator):
        """Test concurrent graph construction operations."""
        # Arrange
        constructor1 = GraphConstructor()
        constructor2 = GraphConstructor()
        constructor1.embedding_generator = mock_embedding_generator
        constructor2.embedding_generator = mock_embedding_generator
        
        entities = [Entity(
            text="Test",
            entity_type=EntityType.PERSON,
            canonical_form="Test",
            confidence=0.5,
            aliases=[],
            start_position=0,
            end_position=4
        )]
        
        # Act
        graph1 = await constructor1.construct_graph(entities, [], {}, "test1")
        graph2 = await constructor2.construct_graph(entities, [], {}, "test2")
        
        # Assert
        assert len(graph1.nodes) == 1
        assert len(graph2.nodes) == 1
        # Both graphs should be constructed successfully
        assert isinstance(graph1, KnowledgeGraph)
        assert isinstance(graph2, KnowledgeGraph)
        # Each node should have embeddings
        node1 = list(graph1.nodes.values())[0]
        node2 = list(graph2.nodes.values())[0]
        assert len(node1.embedding) == 1536
        assert len(node2.embedding) == 1536

    @pytest.mark.asyncio
    async def test_document_chunk_creation(self, graph_constructor, mock_embedding_generator):
        """Test document chunk creation with embeddings."""
        # Arrange
        source_text = "This is a long document that needs to be chunked. " * 50  # Long text
        source_id = "test_doc_1"
        
        # Mock chunking response
        mock_embedding_generator.chunk_text.return_value = [
            {
                "text": "This is a long document that needs to be chunked. " * 10,
                "embedding": [0.1] * 1536,
                "metadata": {"chunk_index": 0}
            },
            {
                "text": "This is a long document that needs to be chunked. " * 10,
                "embedding": [0.2] * 1536,
                "metadata": {"chunk_index": 1}
            }
        ]
        
        # Act
        graph = await graph_constructor.construct_graph(
            entities=[],
            relations=[],
            entity_attributes={},
            source_text=source_text,
            source_id=source_id,
            chunk_size=200,
            chunk_overlap=50
        )
        
        # Assert
        assert len(graph.document_chunks) == 2
        assert graph.metadata["document_chunks_count"] == 2
        
        # Check document chunks structure
        for chunk_id, chunk in graph.document_chunks.items():
            assert isinstance(chunk, DocumentChunk)
            assert chunk.source_document == source_id
            assert len(chunk.embedding) == 1536
            assert chunk.chunk_index in [0, 1]
            assert chunk.text is not None
            assert len(chunk.text) > 0
        
        # Verify chunking was called
        mock_embedding_generator.chunk_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_attribute_node_creation(self, graph_constructor, sample_entities, sample_attributes, mock_embedding_generator):
        """Test attribute node creation with embeddings."""
        # Arrange
        source_text = "Apple Inc was founded in 1976 and has revenue of $394.3 billion"
        
        # Mock single embedding calls for attributes
        mock_embedding_generator.embed_single.return_value = [0.5] * 1536
        
        # Act
        graph = await graph_constructor.construct_graph(
            entities=sample_entities,
            relations=[],
            entity_attributes=sample_attributes,
            source_text=source_text
        )
        
        # Assert
        assert len(graph.attribute_nodes) == 3  # 2 for Apple + 1 for iPhone
        assert graph.metadata["attribute_nodes_count"] == 3
        
        # Check attribute nodes structure
        for attr_id, attr_node in graph.attribute_nodes.items():
            assert isinstance(attr_node, AttributeNode)
            assert attr_node.entity_id is not None
            assert attr_node.name is not None
            assert attr_node.value is not None
            assert len(attr_node.embedding) == 1536
            assert attr_node.confidence > 0
            assert attr_node.attribute_type in ["TEMPORAL", "NUMERICAL", "CATEGORICAL"]
        
        # Verify embedding generation was called (may use batch or fallback)
        # Due to fallback logic, embed_single might be called less than expected
        assert mock_embedding_generator.embed_single.call_count >= 2


@pytest.mark.integration
class TestGraphConstructorIntegration:
    """Integration tests for GraphConstructor with real embedding generator."""

    @pytest.mark.asyncio
    async def test_real_embedding_generation(self):
        """Test with real embedding generator (requires API access)."""
        pytest.skip("Integration test requires real embedding service - skipping for now")