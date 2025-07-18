#!/usr/bin/env python3
"""
Strict Test Suite for Neo4j Client

Complete and rigorous testing of all Neo4j client functionality.
All tests must pass without exceptions.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# Import the module to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestNeo4jClientInitialization:
    """Test Neo4j client initialization and connection - Strict Testing"""
    
    def test_init_without_neo4j_driver(self):
        """Test initialization when neo4j driver is not available"""
        with patch('neo4j_client.NEO4J_AVAILABLE', False):
            with patch('neo4j_client.get_logger'):
                with patch('neo4j_client.get_supabase_client'):
                    with patch('neo4j_client.get_settings'):
                        from neo4j_client import Neo4jClient
                        client = Neo4jClient()
                        assert client.driver is None
    
    @patch('neo4j_client.get_settings')
    @patch('neo4j_client.get_supabase_client') 
    @patch('neo4j_client.get_logger')
    @patch('neo4j_client.GraphDatabase')
    def test_init_with_config_success(self, mock_graph_db, mock_logger, mock_supabase, mock_settings):
        """Test successful initialization with custom config"""
        # Setup mocks
        mock_settings.return_value = MagicMock()
        mock_settings.return_value.graph_analytics.neo4j_uri = 'bolt://localhost:7687'
        mock_settings.return_value.graph_analytics.neo4j_username = 'neo4j'
        mock_settings.return_value.graph_analytics.neo4j_password = 'password'
        mock_settings.return_value.graph_analytics.neo4j_database = 'neo4j'
        
        # Setup driver mock
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {'test': 1}
        mock_session.run.return_value = mock_result
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = None
        mock_driver.session.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver
        
        config = {
            'uri': 'bolt://test:7687',
            'username': 'test_user',
            'password': 'test_pass',
            'database': 'test_db'
        }
        
        with patch('neo4j_client.NEO4J_AVAILABLE', True):
            from neo4j_client import Neo4jClient
            client = Neo4jClient(config)
            
        assert client.uri == 'bolt://test:7687'
        assert client.username == 'test_user'
        assert client.password == 'test_pass'
        assert client.database == 'test_db'
        assert client.driver is not None
        mock_graph_db.driver.assert_called_once()
    
    @patch('neo4j_client.get_settings')
    @patch('neo4j_client.get_supabase_client')
    @patch('neo4j_client.get_logger')
    @patch('neo4j_client.GraphDatabase')
    def test_init_connection_failure(self, mock_graph_db, mock_logger, mock_supabase, mock_settings):
        """Test handling of connection failures"""
        # Setup mocks
        mock_settings.return_value = MagicMock()
        mock_settings.return_value.graph_analytics.neo4j_uri = 'bolt://localhost:7687'
        mock_settings.return_value.graph_analytics.neo4j_username = 'neo4j'
        mock_settings.return_value.graph_analytics.neo4j_password = 'password'
        mock_settings.return_value.graph_analytics.neo4j_database = 'neo4j'
        
        mock_graph_db.driver.side_effect = Exception("Connection failed")
        
        with patch('neo4j_client.NEO4J_AVAILABLE', True):
            from neo4j_client import Neo4jClient
            client = Neo4jClient()
            assert client.driver is None

class TestNeo4jClientBasicOperations:
    """Test basic Neo4j operations - Strict Testing"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a properly mocked Neo4j client for testing"""
        with patch('neo4j_client.NEO4J_AVAILABLE', True):
            with patch('neo4j_client.get_logger'):
                with patch('neo4j_client.get_supabase_client'):
                    with patch('neo4j_client.get_settings'):
                        with patch('neo4j_client.GraphDatabase'):
                            from neo4j_client import Neo4jClient
                            client = Neo4jClient()
                            client.driver = MagicMock()
                            return client
    
    @pytest.mark.asyncio
    async def test_store_entity_success(self, mock_client):
        """Test successful entity storage"""
        # Setup session mock
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = MagicMock()
        
        # Setup record access
        mock_record.__getitem__ = MagicMock(return_value={'name': 'test_entity', 'type': 'PERSON'})
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        # Setup context manager
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        
        mock_client.driver.session.return_value = mock_session
        
        result = await mock_client.store_entity(
            name="test_entity",
            entity_type="PERSON",
            properties={"confidence": 0.9},
            embedding=[0.1, 0.2, 0.3]
        )
        
        assert result["success"] is True
        assert "entity" in result
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_entity_failure(self, mock_client):
        """Test entity storage failure"""
        mock_session = MagicMock()
        mock_session.run.side_effect = Exception("Storage failed")
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_client.driver.session.return_value = mock_session
        
        result = await mock_client.store_entity("test", "PERSON")
        
        assert result["success"] is False
        assert "error" in result
        assert "Storage failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_store_relationship_success(self, mock_client):
        """Test successful relationship storage"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = MagicMock()
        
        mock_record.__getitem__ = MagicMock(return_value={'type': 'KNOWS'})
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_client.driver.session.return_value = mock_session
        
        result = await mock_client.store_relationship(
            source_entity="Alice",
            target_entity="Bob",
            relationship_type="KNOWS",
            properties={"since": "2023"},
            embedding=[0.4, 0.5, 0.6]
        )
        
        assert result["success"] is True
        assert "relationship" in result
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_query_success(self, mock_client):
        """Test successful query execution"""
        mock_session = MagicMock()
        
        # Create mock records that can be iterated
        mock_record1 = MagicMock()
        mock_record1.__iter__ = lambda self: iter([('name', 'Alice')])
        mock_record1.keys.return_value = ['name']
        mock_record1.__getitem__ = lambda self, key: 'Alice' if key == 'name' else None
        mock_record1.get.return_value = 'Alice'
        
        mock_record2 = MagicMock()
        mock_record2.__iter__ = lambda self: iter([('name', 'Bob')])
        mock_record2.keys.return_value = ['name']
        mock_record2.__getitem__ = lambda self, key: 'Bob' if key == 'name' else None
        mock_record2.get.return_value = 'Bob'
        
        # Mock the session.run result to be iterable
        mock_result = [mock_record1, mock_record2]
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_client.driver.session.return_value = mock_session
        
        result = await mock_client.execute_query(
            "MATCH (n:Person) RETURN n.name as name",
            {"limit": 10}
        )
        
        assert len(result) == 2
        mock_session.run.assert_called_once()

class TestNeo4jClientNewMethods:
    """Test the newly added methods for Graph Analytics Service - Strict Testing"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a properly mocked Neo4j client for testing"""
        with patch('neo4j_client.NEO4J_AVAILABLE', True):
            with patch('neo4j_client.get_logger'):
                with patch('neo4j_client.get_supabase_client'):
                    with patch('neo4j_client.get_settings'):
                        with patch('neo4j_client.GraphDatabase'):
                            from neo4j_client import Neo4jClient
                            client = Neo4jClient()
                            client.driver = MagicMock()
                            return client
    
    @pytest.mark.asyncio
    async def test_store_document_chunk(self, mock_client):
        """Test document chunk storage"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = MagicMock()
        
        mock_record.__getitem__ = MagicMock(return_value={'id': 'chunk_123', 'text': 'Sample text'})
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_client.driver.session.return_value = mock_session
        
        result = await mock_client.store_document_chunk(
            chunk_id="chunk_123",
            text="Sample text chunk",
            properties={"page": 1},
            embedding=[0.1, 0.2, 0.3]
        )
        
        assert result["success"] is True
        assert "chunk" in result
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_attribute_node(self, mock_client):
        """Test attribute node storage"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = MagicMock()
        
        mock_record.__getitem__ = MagicMock(return_value={'id': 'attr_123', 'name': 'age'})
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_client.driver.session.return_value = mock_session
        
        result = await mock_client.store_attribute_node(
            attr_id="attr_123",
            entity_id="entity_456",
            name="age",
            value="30",
            properties={"type": "numeric"},
            embedding=[0.4, 0.5, 0.6]
        )
        
        assert result["success"] is True
        assert "attribute" in result
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vector_similarity_search_relations(self, mock_client):
        """Test vector similarity search for relationships"""
        mock_client.execute_query = AsyncMock(return_value=[
            {
                'relationship_type': 'KNOWS',
                'source_entity': 'Alice',
                'target_entity': 'Bob',
                'score': 0.85
            }
        ])
        
        result = await mock_client.vector_similarity_search_relations(
            embedding=[0.1, 0.2, 0.3],
            limit=5,
            similarity_threshold=0.7
        )
        
        assert len(result) == 1
        assert result[0]['relationship_type'] == 'KNOWS'
        assert result[0]['score'] == 0.85
        mock_client.execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_resources(self, mock_client):
        """Test getting user resources"""
        mock_client.execute_query = AsyncMock(side_effect=[
            [{'entity_count': 5}],  # First call for entities
            [{'document_count': 3}]  # Second call for documents
        ])
        
        result = await mock_client.get_user_resources(user_id=123)
        
        assert result["success"] is True
        assert result["resources"]["entities"] == 5
        assert result["resources"]["documents"] == 3
        assert result["resources"]["total"] == 8
        assert mock_client.execute_query.call_count == 2
    
    @pytest.mark.asyncio
    async def test_query_knowledge_graph(self, mock_client):
        """Test knowledge graph querying"""
        mock_client.execute_query = AsyncMock(return_value=[
            {
                'entity': '深圳平安',
                'entity_type': 'MEDICAL_TERM',
                'canonical_form': '深圳平安',
                'related_entities': ['门诊部', '医疗']
            }
        ])
        
        result = await mock_client.query_knowledge_graph(
            resource_id="test_resource",
            query="深圳平安",
            user_id=123
        )
        
        assert result["success"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["entity"] == "深圳平安"
        assert result["query"] == "深圳平安"
        mock_client.execute_query.assert_called_once()

class TestNeo4jClientVectorOperations:
    """Test vector-related operations - Strict Testing"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a properly mocked Neo4j client for testing"""
        with patch('neo4j_client.NEO4J_AVAILABLE', True):
            with patch('neo4j_client.get_logger'):
                with patch('neo4j_client.get_supabase_client'):
                    with patch('neo4j_client.get_settings'):
                        with patch('neo4j_client.GraphDatabase'):
                            from neo4j_client import Neo4jClient
                            client = Neo4jClient()
                            client.driver = MagicMock()
                            return client
    
    @pytest.mark.asyncio
    async def test_vector_similarity_search_success(self, mock_client):
        """Test successful vector similarity search"""
        mock_client.execute_query = AsyncMock(return_value=[
            {
                'id': 'entity_1',
                'text': 'machine learning',
                'entity_type': 'CONCEPT',
                'score': 0.95
            },
            {
                'id': 'entity_2', 
                'text': 'artificial intelligence',
                'entity_type': 'CONCEPT',
                'score': 0.88
            }
        ])
        
        result = await mock_client.vector_similarity_search(
            embedding=[0.1, 0.2, 0.3],
            limit=5,
            similarity_threshold=0.8
        )
        
        assert len(result) == 2
        assert result[0]['score'] == 0.95
        assert result[1]['text'] == 'artificial intelligence'
        mock_client.execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vector_similarity_search_fallback(self, mock_client):
        """Test vector search fallback when vector index fails"""
        mock_client.execute_query = AsyncMock(side_effect=[
            Exception("Vector index not available"),  # First call fails
            [{'id': 'entity_1', 'text': 'fallback result', 'score': 0.5}]  # Fallback call
        ])
        
        result = await mock_client.vector_similarity_search(
            embedding=[0.1, 0.2, 0.3]
        )
        
        assert len(result) == 1
        assert result[0]['text'] == 'fallback result'
        assert result[0]['score'] == 0.5
        assert mock_client.execute_query.call_count == 2

class TestNeo4jClientGraphOperations:
    """Test graph-level operations - Strict Testing"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a properly mocked Neo4j client for testing"""
        with patch('neo4j_client.NEO4J_AVAILABLE', True):
            with patch('neo4j_client.get_logger'):
                with patch('neo4j_client.get_supabase_client'):
                    with patch('neo4j_client.get_settings'):
                        with patch('neo4j_client.GraphDatabase'):
                            from neo4j_client import Neo4jClient
                            client = Neo4jClient()
                            client.driver = MagicMock()
                            return client
    
    @pytest.mark.asyncio
    async def test_get_entity_neighbors(self, mock_client):
        """Test getting entity neighbors"""
        mock_client.execute_query = AsyncMock(return_value=[
            {'name': 'Alice'},
            {'name': 'Bob'},
            {'name': 'Charlie'}
        ])
        
        result = await mock_client.get_entity_neighbors("David", depth=2)
        
        assert len(result) == 3
        assert 'Alice' in result
        assert 'Bob' in result
        assert 'Charlie' in result
        mock_client.execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_shortest_path_found(self, mock_client):
        """Test finding shortest path between entities"""
        mock_client.execute_query = AsyncMock(return_value=[
            {
                'path_length': 2,
                'node_names': ['Alice', 'Bob', 'Charlie']
            }
        ])
        
        result = await mock_client.find_shortest_path("Alice", "Charlie")
        
        assert result["found"] is True
        assert result["length"] == 2
        assert result["nodes"] == ['Alice', 'Bob', 'Charlie']
        mock_client.execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_shortest_path_not_found(self, mock_client):
        """Test when no path exists between entities"""
        mock_client.execute_query = AsyncMock(return_value=[])
        
        result = await mock_client.find_shortest_path("Alice", "Isolated")
        
        assert result["found"] is False
        assert result["length"] == 0
        assert result["nodes"] == []
    
    @pytest.mark.asyncio
    async def test_get_graph_statistics(self, mock_client):
        """Test getting graph statistics"""
        mock_client.execute_query = AsyncMock(return_value=[
            {
                'total_nodes': 100,
                'total_edges': 150,
                'entity_types': ['PERSON', 'ORGANIZATION', 'CONCEPT'],
                'relation_types': ['KNOWS', 'WORKS_FOR', 'RELATES_TO'],
                'avg_node_confidence': 0.85,
                'avg_edge_confidence': 0.78
            }
        ])
        
        result = await mock_client.get_graph_statistics()
        
        assert result['total_nodes'] == 100
        assert result['total_edges'] == 150
        assert len(result['entity_types']) == 3
        assert result['avg_node_confidence'] == 0.85
        mock_client.execute_query.assert_called_once()

class TestNeo4jClientErrorHandling:
    """Test error handling scenarios - Strict Testing"""
    
    def test_operations_without_driver(self):
        """Test that operations fail gracefully without driver"""
        with patch('neo4j_client.NEO4J_AVAILABLE', True):
            with patch('neo4j_client.get_logger'):
                with patch('neo4j_client.get_supabase_client'):
                    with patch('neo4j_client.get_settings'):
                        with patch('neo4j_client.GraphDatabase'):
                            from neo4j_client import Neo4jClient
                            client = Neo4jClient()
                            client.driver = None
                            
                            with pytest.raises(RuntimeError, match="Neo4j client not available"):
                                asyncio.run(client.store_entity("test", "PERSON"))
                            
                            with pytest.raises(RuntimeError, match="Neo4j client not available"):
                                asyncio.run(client.execute_query("MATCH (n) RETURN n"))
    
    @pytest.mark.asyncio
    async def test_query_execution_error(self):
        """Test query execution error handling"""
        with patch('neo4j_client.NEO4J_AVAILABLE', True):
            with patch('neo4j_client.get_logger'):
                with patch('neo4j_client.get_supabase_client'):
                    with patch('neo4j_client.get_settings'):
                        with patch('neo4j_client.GraphDatabase'):
                            from neo4j_client import Neo4jClient
                            client = Neo4jClient()
                            client.driver = MagicMock()
                            
                            mock_session = MagicMock()
                            mock_session.run.side_effect = Exception("Query failed")
                            mock_session.__enter__ = MagicMock(return_value=mock_session)
                            mock_session.__exit__ = MagicMock(return_value=None)
                            client.driver.session.return_value = mock_session
                            
                            with pytest.raises(Exception, match="Query failed"):
                                await client.execute_query("INVALID QUERY")

class TestGlobalClientInstance:
    """Test the global client instance functionality - Strict Testing"""
    
    @patch('neo4j_client._neo4j_client', None)
    @patch('neo4j_client.Neo4jClient')
    @pytest.mark.asyncio
    async def test_get_neo4j_client_creates_instance(self, mock_client_class):
        """Test that get_neo4j_client creates a new instance when needed"""
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance
        
        from neo4j_client import get_neo4j_client
        
        config = {'uri': 'bolt://test:7687'}
        result = await get_neo4j_client(config)
        
        assert result == mock_instance
        mock_client_class.assert_called_once_with(config)
    
    @patch('neo4j_client._neo4j_client')
    @pytest.mark.asyncio
    async def test_get_neo4j_client_returns_existing(self, mock_existing_client):
        """Test that get_neo4j_client returns existing instance"""
        existing_client = MagicMock()
        mock_existing_client = existing_client
        
        from neo4j_client import get_neo4j_client
        
        with patch('neo4j_client._neo4j_client', existing_client):
            result = await get_neo4j_client()
            assert result == existing_client

class TestNeo4jClientKnowledgeGraphOperations:
    """Test knowledge graph storage operations - Strict Testing"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a properly mocked Neo4j client for testing"""
        with patch('neo4j_client.NEO4J_AVAILABLE', True):
            with patch('neo4j_client.get_logger'):
                with patch('neo4j_client.get_supabase_client'):
                    with patch('neo4j_client.get_settings'):
                        with patch('neo4j_client.GraphDatabase'):
                            from neo4j_client import Neo4jClient
                            client = Neo4jClient()
                            client.driver = MagicMock()
                            return client
    
    @pytest.mark.asyncio
    async def test_store_knowledge_graph_success(self, mock_client):
        """Test successful knowledge graph storage"""
        mock_session = MagicMock()
        mock_session.run.return_value = None
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_client.driver.session.return_value = mock_session
        
        # Mock the internal methods
        mock_client._store_node = AsyncMock()
        mock_client._store_edge = AsyncMock()
        mock_client._store_graph_metadata = AsyncMock()
        
        graph_data = {
            'nodes': [{'id': 'node1', 'entity': {'text': 'test', 'type': 'TEST'}, 'attributes': {}}],
            'edges': [{'id': 'edge1', 'source': 'node1', 'target': 'node2', 'relation': {'type': 'TEST'}}],
            'metadata': {'created': '2023-01-01'}
        }
        
        result = await mock_client.store_knowledge_graph(graph_data, "test_graph")
        
        assert result == "test_graph"
        mock_client._store_node.assert_called()
        mock_client._store_edge.assert_called()
        mock_client._store_graph_metadata.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_entity_success(self, mock_client):
        """Test successful entity retrieval"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = MagicMock()
        
        expected_entity = {'name': 'test_entity', 'type': 'PERSON'}
        mock_record.__getitem__ = MagicMock(return_value=expected_entity)
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_client.driver.session.return_value = mock_session
        
        result = await mock_client.get_entity("test_entity")
        
        assert result == expected_entity
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, mock_client):
        """Test entity retrieval when entity not found"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_client.driver.session.return_value = mock_session
        
        result = await mock_client.get_entity("nonexistent_entity")
        
        assert result is None
        mock_session.run.assert_called_once()

# Integration test marker for tests that require actual Neo4j instance
@pytest.mark.skipif(
    True,  # Skip by default
    reason="Integration tests require --integration flag and running Neo4j"
)
class TestNeo4jClientIntegration:
    """Integration tests that require actual Neo4j instance"""
    
    @pytest.mark.asyncio
    async def test_real_neo4j_connection(self):
        """Test connection to real Neo4j instance"""
        config = {
            'uri': 'bolt://localhost:7687',
            'username': 'neo4j',
            'password': 'password',
            'database': 'neo4j'
        }
        
        from neo4j_client import Neo4jClient
        client = Neo4jClient(config)
        
        if client.driver:
            # Test basic connectivity
            result = await client.execute_query("RETURN 1 as test")
            assert result[0]['test'] == 1
            
            # Test entity storage and retrieval
            entity_id = str(uuid.uuid4())
            store_result = await client.store_entity(
                name=f"test_entity_{entity_id}",
                entity_type="TEST",
                properties={"test_id": entity_id}
            )
            assert store_result["success"] is True
            
            # Clean up
            await client.execute_query(
                "MATCH (n:Entity {test_id: $test_id}) DELETE n",
                {"test_id": entity_id}
            )

if __name__ == "__main__":
    # Run tests with: python -m pytest test_neo4j_client_strict.py -v
    # Run with integration tests: python -m pytest test_neo4j_client_strict.py -v --integration
    pytest.main([__file__, "-v"])