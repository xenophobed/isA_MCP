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
from core.database.supabase_client import get_supabase_client

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
    
    async def store_entity(self, 
                         name: str,
                         entity_type: str,
                         properties: Dict[str, Any] = None,
                         embedding: List[float] = None) -> Dict[str, Any]:
        """Store a single entity in Neo4j
        
        Args:
            name: Entity name/text
            entity_type: Type of entity
            properties: Additional properties
            embedding: Optional embedding vector
            
        Returns:
            Storage result
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        properties = properties or {}
        
        try:
            with self.driver.session(database=self.database) as session:
                # Prepare entity properties
                entity_props = {
                    'name': name,
                    'type': entity_type,
                    'created_at': datetime.now().isoformat(),
                    **properties
                }
                
                # Add embedding if provided
                if embedding:
                    entity_props['embedding'] = embedding
                
                # Create or update entity
                cypher = f"""
                MERGE (e:Entity {{name: $name}})
                SET e += $props
                RETURN e
                """
                
                result = session.run(cypher, name=name, props=entity_props)
                record = result.single()
                
                if record:
                    return {"success": True, "entity": dict(record["e"])}
                else:
                    return {"success": False, "error": "Failed to store entity"}
                    
        except Exception as e:
            logger.error(f"Failed to store entity {name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def store_relationship(self,
                               source_entity: str,
                               target_entity: str,
                               relationship_type: str,
                               properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Store a relationship between entities
        
        Args:
            source_entity: Source entity name
            target_entity: Target entity name
            relationship_type: Type of relationship
            properties: Additional properties
            
        Returns:
            Storage result
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        properties = properties or {}
        
        try:
            with self.driver.session(database=self.database) as session:
                # Prepare relationship properties
                rel_props = {
                    'type': relationship_type,
                    'created_at': datetime.now().isoformat(),
                    **properties
                }
                
                # Create relationship
                cypher = f"""
                MATCH (source:Entity {{name: $source_name}})
                MATCH (target:Entity {{name: $target_name}})
                MERGE (source)-[r:{relationship_type}]->(target)
                SET r += $props
                RETURN r
                """
                
                result = session.run(cypher, 
                                   source_name=source_entity,
                                   target_name=target_entity,
                                   props=rel_props)
                record = result.single()
                
                if record:
                    return {"success": True, "relationship": dict(record["r"])}
                else:
                    return {"success": False, "error": "Failed to store relationship"}
                    
        except Exception as e:
            logger.error(f"Failed to store relationship {source_entity}->{target_entity}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_entity(self, entity_name: str) -> Dict[str, Any]:
        """Get entity by name"""
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("MATCH (e:Entity {name: $name}) RETURN e", name=entity_name)
                record = result.single()
                
                if record:
                    return dict(record["e"])
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get entity {entity_name}: {e}")
            return None
    
    async def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query"""
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        parameters = parameters or {}
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                records = []
                for record in result:
                    records.append(dict(record))
                return records
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
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
    
    async def vector_similarity_search(self, 
                                     embedding: List[float], 
                                     limit: int = 10, 
                                     similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Perform vector similarity search on entity embeddings
        
        Args:
            embedding: Query vector embedding
            limit: Maximum number of results
            similarity_threshold: Similarity threshold
            
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
                'query_vector': embedding,
                'k': limit * 2,  # Query more to filter by threshold
                'threshold': similarity_threshold,
                'limit': limit
            }
            
            return await self.execute_query(cypher, parameters)
            
        except Exception as e:
            logger.warning(f"Vector search not available or failed: {e}")
            # Fallback to text-based search
            return await self._fallback_text_search(embedding, limit)
    
    async def _fallback_text_search(self, embedding: List[float], 
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
        
        return await self.execute_query(cypher, {'limit': limit})
    
    async def get_entity_neighbors(self, 
                                 entity_name: str, 
                                 depth: int = 2) -> List[str]:
        """Get neighboring entity names
        
        Args:
            entity_name: Entity name to start from
            depth: Maximum traversal depth
            
        Returns:
            List of neighbor entity names
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        cypher = f"""
        MATCH (start:Entity {{name: $entity_name}})-[*1..{depth}]-(neighbor:Entity)
        WHERE neighbor.name <> $entity_name
        RETURN DISTINCT neighbor.name as name
        LIMIT 100
        """
        
        try:
            results = await self.execute_query(cypher, {'entity_name': entity_name})
            return [record['name'] for record in results]
            
        except Exception as e:
            logger.error(f"Failed to get entity neighbors: {e}")
            return []
    
    async def find_shortest_path(self, 
                               source_entity: str, 
                               target_entity: str) -> Dict[str, Any]:
        """Find shortest path between two entities
        
        Args:
            source_entity: Source entity name
            target_entity: Target entity name
            
        Returns:
            Shortest path information
        """
        if not self.driver:
            raise RuntimeError("Neo4j client not available")
        
        cypher = """
        MATCH path = shortestPath((source:Entity {name: $source_name})-[*1..6]-(target:Entity {name: $target_name}))
        RETURN path,
               length(path) as path_length,
               [node in nodes(path) | node.name] as node_names
        """
        
        try:
            results = await self.execute_query(cypher, {
                'source_name': source_entity,
                'target_name': target_entity
            })
            
            if results:
                result = results[0]
                return {
                    "found": True,
                    "length": result["path_length"],
                    "nodes": result["node_names"]
                }
            else:
                return {"found": False, "length": 0, "nodes": []}
            
        except Exception as e:
            logger.error(f"Failed to find shortest path: {e}")
            return {"found": False, "length": 0, "nodes": [], "error": str(e)}
    
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
            results = await self.execute_query(cypher)
            if results:
                return results[0]
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            return {}

# Global instance
_neo4j_client = None

async def get_neo4j_client(config: Optional[Dict[str, Any]] = None) -> Optional[Neo4jClient]:
    """Get the global Neo4j client instance"""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient(config)
    return _neo4j_client