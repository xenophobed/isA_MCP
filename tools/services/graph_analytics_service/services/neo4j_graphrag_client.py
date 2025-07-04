#!/usr/bin/env python3
"""
Neo4j GraphRAG Client

Enhanced Neo4j client specifically designed for GraphRAG operations with 
vector similarity search and graph traversal capabilities.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import json

from .neo4j_client import Neo4jClient
from ..core.entity_extractor import EntityExtractor
from ..core.relation_extractor import RelationExtractor
from ..utils.embedding_utils import get_embedding_service

logger = logging.getLogger(__name__)

class Neo4jGraphRAGClient:
    """
    Enhanced Neo4j client for GraphRAG operations.
    
    Provides sophisticated graph-based retrieval augmented generation
    with vector similarity search and graph traversal.
    """
    
    def __init__(self, neo4j_client: Neo4jClient):
        """Initialize GraphRAG client with Neo4j connection."""
        self.neo4j_client = neo4j_client
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.embedding_service = get_embedding_service()
        
    async def semantic_search(
        self,
        query: str,
        embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector similarity.
        
        Args:
            query: The search query
            embedding: Query embedding vector
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of matching entities with similarity scores
        """
        try:
            return await self.neo4j_client.vector_similarity_search(
                embedding=embedding,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
            
    async def graph_traversal_search(
        self,
        starting_entities: List[str],
        max_depth: int = 2,
        relation_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform graph traversal from starting entities.
        
        Args:
            starting_entities: List of entity names to start from
            max_depth: Maximum traversal depth
            relation_types: Specific relation types to follow
            
        Returns:
            Subgraph containing connected entities and relationships
        """
        try:
            subgraph = {
                "nodes": [],
                "edges": [],
                "paths": []
            }
            
            for entity in starting_entities:
                # Get neighbors for each starting entity
                neighbors = await self.neo4j_client.get_entity_neighbors(
                    entity_name=entity,
                    depth=max_depth
                )
                
                # Add to subgraph
                for neighbor in neighbors:
                    if neighbor not in subgraph["nodes"]:
                        subgraph["nodes"].append(neighbor)
                        
                # Get relationships
                for i, source in enumerate(starting_entities):
                    for j, target in enumerate(neighbors):
                        if i != j:  # Don't connect entity to itself
                            path = await self.neo4j_client.find_shortest_path(
                                source_entity=source,
                                target_entity=target
                            )
                            if path:
                                subgraph["paths"].append(path)
                                
            return subgraph
            
        except Exception as e:
            logger.error(f"Graph traversal search failed: {e}")
            return {"nodes": [], "edges": [], "paths": []}
            
    async def hybrid_search(
        self,
        query: str,
        embedding: List[float],
        limit: int = 10,
        expand_depth: int = 1
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining semantic and graph traversal.
        
        Args:
            query: The search query
            embedding: Query embedding vector
            limit: Maximum number of initial semantic results
            expand_depth: Depth for graph expansion
            
        Returns:
            Combined results with semantic matches and graph context
        """
        try:
            # First, perform semantic search
            semantic_results = await self.semantic_search(
                query=query,
                embedding=embedding,
                limit=limit
            )
            
            # Extract entity names from semantic results
            entity_names = [
                result.get("entity", {}).get("name", "")
                for result in semantic_results
                if result.get("entity")
            ]
            
            # Perform graph traversal to expand context
            graph_context = await self.graph_traversal_search(
                starting_entities=entity_names,
                max_depth=expand_depth
            )
            
            return {
                "semantic_results": semantic_results,
                "graph_context": graph_context,
                "combined_entities": list(set(entity_names + graph_context["nodes"]))
            }
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return {
                "semantic_results": [],
                "graph_context": {"nodes": [], "edges": [], "paths": []},
                "combined_entities": []
            }
            
    async def extract_and_store_from_text(
        self,
        text: str,
        source_id: str,
        chunk_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract entities and relationships from text and store in graph.
        
        Args:
            text: Input text to process
            source_id: Identifier for the source document
            chunk_id: Optional chunk identifier
            
        Returns:
            Summary of extracted and stored data
        """
        try:
            # Extract entities
            entities = await self.entity_extractor.extract_entities(text)
            
            # Extract relationships
            relationships = await self.relation_extractor.extract_relations(
                text=text,
                entities=entities
            )
            
            # Store entities in Neo4j
            stored_entities = []
            for entity in entities:
                try:
                    # Generate embedding for entity
                    entity_text = f"{entity.text} {entity.entity_type.value}"
                    if hasattr(entity, 'properties') and entity.properties:
                        entity_text += f" {str(entity.properties)}"
                    
                    embedding = await self.embedding_service.generate_single_embedding(entity_text)
                    
                    result = await self.neo4j_client.store_entity(
                        name=entity.text,
                        entity_type=entity.entity_type.value,
                        properties={
                            "canonical_form": entity.canonical_form,
                            "confidence": entity.confidence,
                            "properties": entity.properties,
                            "source_id": source_id,
                            "chunk_id": chunk_id
                        },
                        embedding=embedding
                    )
                    stored_entities.append(result)
                except Exception as e:
                    logger.warning(f"Failed to store entity {entity.text}: {e}")
                    
            # Store relationships
            stored_relationships = []
            for rel in relationships:
                try:
                    result = await self.neo4j_client.store_relationship(
                        source_entity=rel.subject.text,
                        target_entity=rel.object.text,
                        relationship_type=rel.relation_type.value,
                        properties={
                            "predicate": rel.predicate,
                            "confidence": rel.confidence,
                            "context": rel.context,
                            **rel.properties,
                            "source_id": source_id,
                            "chunk_id": chunk_id
                        }
                    )
                    stored_relationships.append(result)
                except Exception as e:
                    logger.warning(f"Failed to store relationship {rel}: {e}")
                    
            return {
                "entities_extracted": len(entities),
                "relationships_extracted": len(relationships),
                "entities_stored": len(stored_entities),
                "relationships_stored": len(stored_relationships),
                "source_id": source_id,
                "chunk_id": chunk_id
            }
            
        except Exception as e:
            logger.error(f"Text processing and storage failed: {e}")
            return {
                "entities_extracted": 0,
                "relationships_extracted": 0,
                "entities_stored": 0,
                "relationships_stored": 0,
                "error": str(e)
            }
            
    async def get_entity_context(
        self,
        entity_name: str,
        context_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get comprehensive context for an entity.
        
        Args:
            entity_name: Name of the entity
            context_depth: Depth of context to retrieve
            
        Returns:
            Entity context including neighbors and relationships
        """
        try:
            # Get entity details
            entity = await self.neo4j_client.get_entity(entity_name)
            
            # Get neighbors
            neighbors = await self.neo4j_client.get_entity_neighbors(
                entity_name=entity_name,
                depth=context_depth
            )
            
            return {
                "entity": entity,
                "neighbors": neighbors,
                "context_depth": context_depth
            }
            
        except Exception as e:
            logger.error(f"Failed to get entity context: {e}")
            return {"entity": None, "neighbors": [], "error": str(e)}
            
    async def close(self):
        """Close the Neo4j connection."""
        await self.neo4j_client.close()


# Global client instance
_neo4j_graphrag_client: Optional[Neo4jGraphRAGClient] = None

async def get_neo4j_graphrag_client() -> Optional[Neo4jGraphRAGClient]:
    """Get or create the global Neo4j GraphRAG client instance."""
    global _neo4j_graphrag_client
    
    if _neo4j_graphrag_client is None:
        try:
            from .neo4j_client import get_neo4j_client
            neo4j_client = await get_neo4j_client()
            
            if neo4j_client:
                _neo4j_graphrag_client = Neo4jGraphRAGClient(neo4j_client)
                logger.info("Neo4j GraphRAG client initialized successfully")
            else:
                logger.warning("Neo4j client not available, GraphRAG client not created")
                
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j GraphRAG client: {e}")
            
    return _neo4j_graphrag_client