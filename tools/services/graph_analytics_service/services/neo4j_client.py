#!/usr/bin/env python3
"""
Neo4j Client for Graph Analytics

Provides connectivity and operations for Neo4j Aura database with vector support.
Handles graph storage, querying, and GraphRAG operations.
"""

import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json

from core.logging import get_logger
from core.supabase_client import get_supabase_client

try:
    from neo4j import GraphDatabase, Driver, Result
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    GraphDatabase = None
    Driver = None
    Result = None

logger = get_logger(__name__)

class Neo4jClient:
    """Neo4j client for graph operations with vector support"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Neo4j client
        
        Args:
            config: Configuration dict with Neo4j settings
        """
        self.config = config or {}
        self.driver: Optional[Driver] = None
        self.supabase = get_supabase_client()
        
        if not NEO4J_AVAILABLE:
            logger.warning("Neo4j driver not available. Install with: pip install neo4j")
            return
        
        # Get Neo4j connection details from environment or config
        self.uri = self.config.get('uri') or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.username = self.config.get('username') or os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = self.config.get('password') or os.getenv('NEO4J_PASSWORD', 'password')
        self.database = self.config.get('database') or os.getenv('NEO4J_DATABASE', 'neo4j')
        
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password),
                max_connection_lifetime=30 * 60,  # 30 minutes
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,  # 60 seconds
            )
            
            # Test connection
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                result.single()
            
            logger.info(f"Neo4j client connected to {self.uri}")
            
            # Initialize vector index if supported
            self._setup_vector_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def __del__(self):
        """Clean up driver connection"""
        if self.driver:
            self.driver.close()
    
    def _setup_vector_indexes(self):
        """Setup vector indexes for GraphRAG support"""
        if not self.driver:
            return
        
        try:
            with self.driver.session(database=self.database) as session:
                # Create vector index for entity embeddings
                session.run("""
                    CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
                    FOR (n:Entity) ON (n.embedding)
                    OPTIONS {
                        indexConfig: {
                            `vector.dimensions`: 1536,
                            `vector.similarity_function`: 'cosine'
                        }
                    }
                """)
                
                # Create vector index for relation embeddings
                session.run("""
                    CREATE VECTOR INDEX relation_embeddings IF NOT EXISTS
                    FOR ()-[r:RELATES_TO]-() ON (r.embedding)
                    OPTIONS {
                        indexConfig: {
                            `vector.dimensions`: 1536,
                            `vector.similarity_function`: 'cosine'
                        }
                    }
                """)
                
                logger.info("Vector indexes created successfully")
                
        except Exception as e:
            logger.warning(f"Could not create vector indexes (may not be supported): {e}")
    
    async def store_knowledge_graph(self, graph_data: Dict[str, Any], 
                                   graph_id: str = None) -> str:
        """Store knowledge graph in Neo4j
        
        Args:
            graph_data: Graph data from GraphConstructor
            graph_id: Optional graph identifier
            
        Returns:
            Graph ID for the stored graph
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        graph_id = graph_id or f"graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            with self.driver.session(database=self.database) as session:
                # Clear existing graph data for this ID
                session.run("MATCH (n {graph_id: $graph_id}) DETACH DELETE n", graph_id=graph_id)
                
                # Store nodes
                for node_data in graph_data['nodes']:
                    await self._store_node(session, node_data, graph_id)
                
                # Store edges
                for edge_data in graph_data['edges']:
                    await self._store_edge(session, edge_data, graph_id)
                
                # Store graph metadata
                await self._store_graph_metadata(session, graph_data['metadata'], graph_id)
                
                logger.info(f"Stored knowledge graph {graph_id} with {len(graph_data['nodes'])} nodes and {len(graph_data['edges'])} edges")
                
        except Exception as e:
            logger.error(f"Failed to store knowledge graph: {e}")
            raise
        
        return graph_id
    
    async def _store_node(self, session, node_data: Dict[str, Any], graph_id: str):
        """Store a single node in Neo4j"""
        entity = node_data['entity']
        attributes = node_data['attributes']
        
        # Prepare node properties
        node_props = {
            'id': node_data['id'],
            'graph_id': graph_id,
            'text': entity['text'],
            'entity_type': entity['type'],
            'canonical_form': entity['canonical_form'],
            'aliases': entity.get('aliases', []),
            'confidence': entity['confidence'],
            'created_at': datetime.now().isoformat()
        }
        
        # Add attributes as properties
        for attr_name, attr_data in attributes.items():
            # Prefix attribute names to avoid conflicts
            prop_name = f"attr_{attr_name}"
            node_props[prop_name] = attr_data['value']
            node_props[f"{prop_name}_type"] = attr_data['type']
            node_props[f"{prop_name}_confidence"] = attr_data['confidence']
        
        # Create node with Entity label and entity type label
        cypher = f"""
        CREATE (n:Entity:{entity['type']} $props)
        """
        
        session.run(cypher, props=node_props)
    
    async def _store_edge(self, session, edge_data: Dict[str, Any], graph_id: str):
        """Store a single edge in Neo4j"""
        relation = edge_data['relation']
        
        # Create relationship between nodes
        cypher = """
        MATCH (source:Entity {id: $source_id, graph_id: $graph_id})
        MATCH (target:Entity {id: $target_id, graph_id: $graph_id})
        CREATE (source)-[r:RELATES_TO {
            id: $edge_id,
            graph_id: $graph_id,
            relation_type: $relation_type,
            predicate: $predicate,
            confidence: $confidence,
            context: $context,
            weight: $weight,
            created_at: $created_at
        }]->(target)
        """
        
        session.run(cypher,
            source_id=edge_data['source'],
            target_id=edge_data['target'],
            graph_id=graph_id,
            edge_id=edge_data['id'],
            relation_type=relation['type'],
            predicate=relation['predicate'],
            confidence=relation['confidence'],
            context=relation['context'],
            weight=edge_data['weight'],
            created_at=datetime.now().isoformat()
        )
    
    async def _store_graph_metadata(self, session, metadata: Dict[str, Any], graph_id: str):
        """Store graph metadata"""
        # Store metadata as a separate node
        cypher = """
        CREATE (m:GraphMetadata {
            graph_id: $graph_id,
            metadata: $metadata,
            created_at: $created_at
        })
        """
        
        session.run(cypher,
            graph_id=graph_id,
            metadata=json.dumps(metadata),
            created_at=datetime.now().isoformat()
        )
    
    async def query_graph(self, cypher_query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute Cypher query on the graph
        
        Args:
            cypher_query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Query results as list of dictionaries
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        parameters = parameters or {}
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher_query, parameters)
                records = []
                for record in result:
                    records.append(dict(record))
                return records
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def vector_similarity_search(self, query_embedding: List[float], 
                                     limit: int = 10, 
                                     threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Perform vector similarity search on entity embeddings
        
        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            threshold: Similarity threshold
            
        Returns:
            List of similar entities with scores
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        try:
            cypher = """
            CALL db.index.vector.queryNodes('entity_embeddings', $k, $query_vector)
            YIELD node, score
            WHERE score >= $threshold
            RETURN node.id as id, 
                   node.text as text,
                   node.entity_type as entity_type,
                   node.canonical_form as canonical_form,
                   score
            ORDER BY score DESC
            LIMIT $limit
            """
            
            parameters = {
                'query_vector': query_embedding,
                'k': limit * 2,  # Query more to filter by threshold
                'threshold': threshold,
                'limit': limit
            }
            
            return await self.query_graph(cypher, parameters)
            
        except Exception as e:
            logger.warning(f"Vector search not available or failed: {e}")
            # Fallback to text-based search
            return await self._fallback_text_search(query_embedding, limit)
    
    async def _fallback_text_search(self, query_embedding: List[float], 
                                   limit: int) -> List[Dict[str, Any]]:
        """Fallback text-based search when vector search is not available"""
        # This is a placeholder - in practice, you'd need a way to convert
        # embeddings back to text or use a different search method
        cypher = """
        MATCH (n:Entity)
        RETURN n.id as id,
               n.text as text,
               n.entity_type as entity_type,
               n.canonical_form as canonical_form,
               0.5 as score
        LIMIT $limit
        """
        
        return await self.query_graph(cypher, {'limit': limit})
    
    async def get_entity_neighbors(self, entity_id: str, 
                                 max_depth: int = 2, 
                                 relation_types: List[str] = None) -> Dict[str, Any]:
        """Get neighboring entities and relationships
        
        Args:
            entity_id: Entity ID to start from
            max_depth: Maximum traversal depth
            relation_types: Filter by specific relation types
            
        Returns:
            Subgraph around the entity
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        relation_filter = ""
        if relation_types:
            relation_filter = f"AND r.relation_type IN {relation_types}"
        
        cypher = f"""
        MATCH path = (start:Entity {{id: $entity_id}})-[r:RELATES_TO*1..{max_depth}]-(neighbor:Entity)
        WHERE true {relation_filter}
        RETURN path, 
               relationships(path) as rels,
               nodes(path) as nodes
        LIMIT 100
        """
        
        try:
            results = await self.query_graph(cypher, {'entity_id': entity_id})
            
            # Process results into subgraph format
            nodes = {}
            edges = {}
            
            for result in results:
                for node in result.get('nodes', []):
                    node_id = node.get('id')
                    if node_id:
                        nodes[node_id] = dict(node)
                
                for rel in result.get('rels', []):
                    rel_id = rel.get('id')
                    if rel_id:
                        edges[rel_id] = dict(rel)
            
            return {
                'nodes': nodes,
                'edges': edges,
                'center_entity': entity_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get entity neighbors: {e}")
            return {'nodes': {}, 'edges': {}, 'center_entity': entity_id}
    
    async def get_shortest_path(self, source_id: str, target_id: str, 
                              max_length: int = 6) -> List[Dict[str, Any]]:
        """Find shortest path between two entities
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_length: Maximum path length
            
        Returns:
            Shortest path as list of nodes and relationships
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        cypher = f"""
        MATCH path = shortestPath((source:Entity {{id: $source_id}})-[r:RELATES_TO*1..{max_length}]-(target:Entity {{id: $target_id}}))
        RETURN path,
               length(path) as path_length,
               nodes(path) as nodes,
               relationships(path) as relationships
        """
        
        try:
            results = await self.query_graph(cypher, {
                'source_id': source_id,
                'target_id': target_id
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to find shortest path: {e}")
            return []
    
    async def get_graph_statistics(self, graph_id: str = None) -> Dict[str, Any]:
        """Get statistics about the stored graph
        
        Args:
            graph_id: Optional graph ID to filter by
            
        Returns:
            Graph statistics
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        graph_filter = f"WHERE n.graph_id = '{graph_id}'" if graph_id else ""
        
        cypher = f"""
        MATCH (n:Entity) {graph_filter}
        OPTIONAL MATCH (n)-[r:RELATES_TO]-()
        RETURN 
            count(DISTINCT n) as total_nodes,
            count(DISTINCT r) as total_edges,
            collect(DISTINCT n.entity_type) as entity_types,
            collect(DISTINCT r.relation_type) as relation_types,
            avg(n.confidence) as avg_node_confidence,
            avg(r.confidence) as avg_edge_confidence
        """
        
        try:
            results = await self.query_graph(cypher)
            if results:
                return results[0]
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            return {}

# Global instance
_neo4j_client = None

def get_neo4j_client(config: Optional[Dict[str, Any]] = None) -> Neo4jClient:
    """Get the global Neo4j client instance"""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient(config)
    return _neo4j_client