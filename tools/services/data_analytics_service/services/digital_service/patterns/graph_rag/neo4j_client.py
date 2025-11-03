#!/usr/bin/env python3
"""
Neo4j Client Adapter for Graph RAG

Wraps isa_common.neo4j_client to provide Graph RAG specific interface.
Maintains compatibility with existing GraphRAGService code while using
the standard gRPC-based Neo4j client.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from isa_common.neo4j_client import Neo4jClient as ISANeo4jClient

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Graph RAG adapter for isa_common.neo4j_client.

    Provides store_entity() and store_relationship() methods that wrap
    the standard create_node() and create_relationship() methods.
    Supports embedding storage and vector similarity search.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Neo4j client adapter

        Args:
            config: Configuration dict (optional, uses defaults from isa_common)
        """
        self.config = config or {}

        # Initialize isa_common Neo4j client
        # It handles gRPC connection, service discovery, etc.
        self.client = ISANeo4jClient(
            user_id=self.config.get('user_id', 'graph-rag-service'),
            host=self.config.get('host'),  # Optional, auto-discovers if not set
            port=self.config.get('port', 50063)
        )

        self.database = self.config.get('database', 'neo4j')

        logger.info("Neo4j Graph RAG adapter initialized with isa_common client")

        # Setup vector indexes on initialization
        self._setup_vector_indexes()

    def _setup_vector_indexes(self):
        """Setup vector indexes for GraphRAG support"""
        try:
            # Create vector index for entity embeddings
            self.client.run_cypher("""
                CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
                FOR (n:Entity) ON (n.embedding)
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: 1536,
                        `vector.similarity_function`: 'cosine'
                    }
                }
            """, database=self.database)

            # Create vector index for relation embeddings
            self.client.run_cypher("""
                CREATE VECTOR INDEX relation_embeddings IF NOT EXISTS
                FOR ()-[r:RELATES_TO]-() ON (r.embedding)
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: 1536,
                        `vector.similarity_function`: 'cosine'
                    }
                }
            """, database=self.database)

            # Create index for document chunks
            self.client.run_cypher("""
                CREATE VECTOR INDEX document_embeddings IF NOT EXISTS
                FOR (n:DocumentChunk) ON (n.embedding)
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: 1536,
                        `vector.similarity_function`: 'cosine'
                    }
                }
            """, database=self.database)

            logger.info("✅ Vector indexes created successfully")

        except Exception as e:
            logger.warning(f"Could not create vector indexes (may not be supported): {e}")

    async def store_entity(self,
                         name: str,
                         entity_type: str,
                         properties: Dict[str, Any] = None,
                         embedding: List[float] = None,
                         user_id: int = None) -> Dict[str, Any]:
        """Store a single entity in Neo4j

        Args:
            name: Entity name/text
            entity_type: Type of entity
            properties: Additional properties
            embedding: Optional embedding vector (1536 dims)
            user_id: Optional user ID for isolation

        Returns:
            Storage result dict with success/error
        """
        properties = properties or {}

        try:
            # Prepare entity properties
            entity_props = {
                'name': name,
                'type': entity_type,
                'created_at': datetime.now().isoformat(),
                **properties
            }

            # Add user_id if provided
            if user_id is not None:
                entity_props['user_id'] = user_id

            # Add embedding if provided
            if embedding:
                entity_props['embedding'] = embedding

            # Use MERGE to avoid duplicates
            cypher = """
            MERGE (e:Entity {name: $name})
            SET e += $props
            RETURN id(e) as node_id, e
            """

            result = self.client.run_cypher(
                cypher,
                params={'name': name, 'props': entity_props},
                database=self.database
            )

            if result and len(result) > 0:
                node_data = result[0]
                return {
                    "success": True,
                    "node_id": node_data.get('node_id'),
                    "entity": node_data.get('e', {})
                }
            else:
                return {"success": False, "error": "Failed to store entity"}

        except Exception as e:
            logger.error(f"Failed to store entity {name}: {e}")
            return {"success": False, "error": str(e)}

    async def store_relationship(self,
                               source_entity: str,
                               target_entity: str,
                               relationship_type: str,
                               properties: Dict[str, Any] = None,
                               embedding: List[float] = None,
                               user_id: int = None) -> Dict[str, Any]:
        """Store a relationship between entities

        Args:
            source_entity: Source entity name
            target_entity: Target entity name
            relationship_type: Type of relationship
            properties: Additional properties
            embedding: Optional vector embedding for the relationship
            user_id: Optional user ID for isolation

        Returns:
            Storage result dict with success/error
        """
        properties = properties or {}

        try:
            # Prepare relationship properties
            rel_props = {
                'type': relationship_type,
                'created_at': datetime.now().isoformat(),
                **properties
            }

            # Add user_id if provided
            if user_id is not None:
                rel_props['user_id'] = user_id

            # Add embedding if provided
            if embedding:
                rel_props['embedding'] = embedding

            # Create or update relationship
            cypher = """
            MATCH (source:Entity {name: $source_name})
            MATCH (target:Entity {name: $target_name})
            MERGE (source)-[r:RELATES_TO]->(target)
            SET r += $props
            RETURN id(r) as rel_id, r
            """

            result = self.client.run_cypher(
                cypher,
                params={
                    'source_name': source_entity,
                    'target_name': target_entity,
                    'props': rel_props
                },
                database=self.database
            )

            if result and len(result) > 0:
                rel_data = result[0]
                return {
                    "success": True,
                    "rel_id": rel_data.get('rel_id'),
                    "relationship": rel_data.get('r', {})
                }
            else:
                return {"success": False, "error": "Failed to store relationship"}

        except Exception as e:
            logger.error(f"Failed to store relationship {source_entity} -> {target_entity}: {e}")
            return {"success": False, "error": str(e)}

    async def vector_search_entities(self,
                                    query_embedding: List[float],
                                    top_k: int = 10,
                                    similarity_threshold: float = 0.7,
                                    user_id: int = None) -> List[Dict[str, Any]]:
        """Vector similarity search for entities

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            user_id: Optional user ID filter

        Returns:
            List of similar entities with scores
        """
        try:
            # Build user filter
            user_filter = "AND e.user_id = $user_id" if user_id is not None else ""

            cypher = f"""
            CALL db.index.vector.queryNodes('entity_embeddings', $top_k, $query_embedding)
            YIELD node as e, score
            WHERE score >= $threshold {user_filter}
            RETURN e, score
            ORDER BY score DESC
            """

            params = {
                'query_embedding': query_embedding,
                'top_k': top_k,
                'threshold': similarity_threshold
            }
            if user_id is not None:
                params['user_id'] = user_id

            result = self.client.run_cypher(cypher, params=params, database=self.database)

            return result or []

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def vector_search_documents(self,
                                     query_embedding: List[float],
                                     top_k: int = 10,
                                     similarity_threshold: float = 0.7,
                                     user_id: int = None) -> List[Dict[str, Any]]:
        """Vector similarity search for document chunks"""
        try:
            user_filter = "AND d.user_id = $user_id" if user_id is not None else ""

            cypher = f"""
            CALL db.index.vector.queryNodes('document_embeddings', $top_k, $query_embedding)
            YIELD node as d, score
            WHERE score >= $threshold {user_filter}
            RETURN d, score
            ORDER BY score DESC
            """

            params = {
                'query_embedding': query_embedding,
                'top_k': top_k,
                'threshold': similarity_threshold
            }
            if user_id is not None:
                params['user_id'] = user_id

            result = self.client.run_cypher(cypher, params=params, database=self.database)

            return result or []

        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return []

    async def get_entity_neighbors(self,
                                  entity_name: str,
                                  max_depth: int = 2,
                                  user_id: int = None) -> Dict[str, Any]:
        """Get neighboring entities via graph traversal"""
        try:
            user_filter = "AND e.user_id = $user_id" if user_id is not None else ""

            cypher = f"""
            MATCH path = (e:Entity {{name: $entity_name}})-[*1..{max_depth}]-(neighbor:Entity)
            WHERE 1=1 {user_filter}
            RETURN DISTINCT neighbor, length(path) as distance
            ORDER BY distance
            LIMIT 50
            """

            params = {'entity_name': entity_name}
            if user_id is not None:
                params['user_id'] = user_id

            result = self.client.run_cypher(cypher, params=params, database=self.database)

            return {'neighbors': result or [], 'entity': entity_name}

        except Exception as e:
            logger.error(f"Failed to get neighbors for {entity_name}: {e}")
            return {'neighbors': [], 'entity': entity_name, 'error': str(e)}

    def close(self):
        """Close the Neo4j client connection"""
        try:
            self.client.close()
            logger.info("Neo4j client closed")
        except Exception as e:
            logger.warning(f"Error closing Neo4j client: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False
