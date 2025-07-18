#!/usr/bin/env python3
"""
GraphRAG Retriever

Sophisticated retrieval system that combines vector similarity search
with graph traversal for enhanced context retrieval.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass

from core.logging import get_logger
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator
from .neo4j_client import Neo4jClient

logger = get_logger(__name__)

@dataclass
class RetrievalResult:
    """Container for retrieval results."""
    content: str
    score: float
    source_id: str
    chunk_id: Optional[str]
    entity_context: Dict[str, Any]
    graph_context: Dict[str, Any]
    metadata: Dict[str, Any]

class GraphRAGRetriever:
    """
    Advanced retriever that combines multiple retrieval strategies
    for comprehensive context gathering.
    """
    
    def __init__(self, neo4j_client: Neo4jClient):
        """Initialize retriever with Neo4j client."""
        self.neo4j_client = neo4j_client
        self.embedding_generator = EmbeddingGenerator()
        
    async def retrieve(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        graph_expansion_depth: int = 2,
        include_graph_context: bool = True,
        search_modes: List[str] = ["entities", "documents", "attributes", "relations"]
    ) -> List[RetrievalResult]:
        """
        Perform comprehensive multi-modal retrieval using vector similarity + graph traversal.
        
        Args:
            query: The search query
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            graph_expansion_depth: Depth for graph context expansion
            include_graph_context: Whether to include graph traversal
            search_modes: Types of nodes to search ["entities", "documents", "attributes", "relations"]
            
        Returns:
            List of retrieval results with context from all search modes
        """
        try:
            all_results = []
            
            # Generate embedding if not provided
            if query_embedding is None:
                query_embedding = await self.embedding_generator.embed_single(query)
            
            # Multi-modal vector similarity search across all node types
            search_tasks = []
            
            if "entities" in search_modes:
                search_tasks.append(self._search_entities(query_embedding, top_k, similarity_threshold))
            if "documents" in search_modes:
                search_tasks.append(self._search_documents(query_embedding, top_k, similarity_threshold))
            if "attributes" in search_modes:
                search_tasks.append(self._search_attributes(query_embedding, top_k, similarity_threshold))
            if "relations" in search_modes:
                search_tasks.append(self._search_relations(query_embedding, top_k, similarity_threshold))
            
            # Execute all searches in parallel
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Combine results from all search modes
            for i, result_set in enumerate(search_results):
                if isinstance(result_set, Exception):
                    logger.warning(f"Search mode {search_modes[i] if i < len(search_modes) else 'unknown'} failed: {result_set}")
                    continue
                if result_set:
                    all_results.extend(result_set)
            
            # Enhance with graph context if enabled
            if include_graph_context and all_results:
                enhanced_results = await self._enhance_with_graph_context(
                    semantic_results=all_results,
                    depth=graph_expansion_depth
                )
                final_results = enhanced_results
            else:
                # Convert to RetrievalResult objects
                final_results = []
                for result in all_results:
                    retrieval_result = await self._create_retrieval_result(
                        result=result,
                        graph_context={}
                    )
                    final_results.append(retrieval_result)
                    
            # Sort by score and return top_k
            final_results.sort(key=lambda x: x.score, reverse=True)
            return final_results[:top_k]
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []
    
    async def _search_entities(
        self,
        embedding: List[float],
        limit: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Search entity nodes using vector similarity."""
        try:
            return await self.neo4j_client.vector_similarity_search(
                embedding=embedding,
                limit=limit,
                similarity_threshold=threshold,
                index_name="entity_embeddings",
                node_label="Entity"
            )
        except Exception as e:
            logger.error(f"Entity search failed: {e}")
            return []
    
    async def _search_documents(
        self,
        embedding: List[float],
        limit: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Search document chunk nodes using vector similarity."""
        try:
            return await self.neo4j_client.vector_similarity_search(
                embedding=embedding,
                limit=limit,
                similarity_threshold=threshold,
                index_name="document_embeddings",
                node_label="Document"
            )
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return []
    
    async def _search_attributes(
        self,
        embedding: List[float],
        limit: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Search attribute nodes using vector similarity."""
        try:
            return await self.neo4j_client.vector_similarity_search(
                embedding=embedding,
                limit=limit,
                similarity_threshold=threshold,
                index_name="attribute_embeddings", 
                node_label="Attribute"
            )
        except Exception as e:
            logger.error(f"Attribute search failed: {e}")
            return []
    
    async def _search_relations(
        self,
        embedding: List[float],
        limit: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Search relation edges using vector similarity."""
        try:
            return await self.neo4j_client.vector_similarity_search_relations(
                embedding=embedding,
                limit=limit,
                similarity_threshold=threshold,
                index_name="relation_embeddings"
            )
        except Exception as e:
            logger.error(f"Relation search failed: {e}")
            return []
            
    async def _semantic_retrieval(
        self,
        query: str,
        embedding: List[float],
        limit: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        try:
            return await self.neo4j_client.vector_similarity_search(
                embedding=embedding,
                limit=limit,
                similarity_threshold=threshold
            )
        except Exception as e:
            logger.error(f"Semantic retrieval failed: {e}")
            return []
            
    async def _enhance_with_graph_context(
        self,
        semantic_results: List[Dict[str, Any]],
        depth: int
    ) -> List[RetrievalResult]:
        """Enhance semantic results with graph context."""
        enhanced_results = []
        
        try:
            # Extract entity names from semantic results
            entities = []
            for result in semantic_results:
                # Results come from vector similarity search
                if "canonical_form" in result:
                    entities.append(result["canonical_form"])
                elif "text" in result:
                    entities.append(result["text"])
                    
            # Get graph context for these entities
            graph_context = await self._get_graph_context_for_entities(
                entities=entities,
                depth=depth
            )
            
            # Create enhanced retrieval results
            for result in semantic_results:
                # Get specific entity context
                entity_name = result.get("entity", {}).get("name", "")
                entity_context = await self._get_entity_specific_context(
                    entity_name, graph_context
                )
                
                retrieval_result = await self._create_retrieval_result(
                    result=result,
                    graph_context=entity_context
                )
                enhanced_results.append(retrieval_result)
                
        except Exception as e:
            logger.error(f"Graph context enhancement failed: {e}")
            # Fall back to semantic results only
            for result in semantic_results:
                retrieval_result = await self._create_retrieval_result(
                    result=result,
                    graph_context={}
                )
                enhanced_results.append(retrieval_result)
                
        return enhanced_results
        
    async def _get_entity_specific_context(
        self,
        entity_name: str,
        global_graph_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get context specific to an entity from global graph context."""
        try:
            if not entity_name:
                return {}
                
            # Filter global context for this specific entity
            entity_context = {
                "direct_neighbors": [],
                "related_paths": [],
                "connected_entities": []
            }
            
            # Find neighbors
            if entity_name in global_graph_context.get("nodes", []):
                # Find paths that include this entity
                for path in global_graph_context.get("paths", []):
                    if isinstance(path, dict) and "nodes" in path:
                        if entity_name in path["nodes"]:
                            entity_context["related_paths"].append(path)
                            
            # Find directly connected entities
            for path in entity_context["related_paths"]:
                for node in path.get("nodes", []):
                    if node != entity_name and node not in entity_context["connected_entities"]:
                        entity_context["connected_entities"].append(node)
                        
            return entity_context
            
        except Exception as e:
            logger.error(f"Failed to get entity-specific context: {e}")
            return {}

    async def _get_graph_context_for_entities(
        self, 
        entities: List[str], 
        depth: int
    ) -> Dict[str, Any]:
        """Get graph context for a list of entities."""
        try:
            all_neighbors = {}
            all_paths = []
            
            # Get neighbors for each entity
            for entity in entities:
                neighbors = await self.neo4j_client.get_entity_neighbors(
                    entity_name=entity,
                    depth=depth
                )
                all_neighbors[entity] = neighbors
                
                # Get paths between entities
                for other_entity in entities:
                    if entity != other_entity:
                        path = await self.neo4j_client.find_shortest_path(
                            source_entity=entity,
                            target_entity=other_entity
                        )
                        if path.get("found"):
                            all_paths.append(path)
            
            return {
                "entities": entities,
                "neighbors": all_neighbors,
                "paths": all_paths
            }
            
        except Exception as e:
            logger.error(f"Failed to get graph context: {e}")
            return {"entities": entities, "neighbors": {}, "paths": []}
            
    async def _create_retrieval_result(
        self,
        result: Dict[str, Any],
        graph_context: Dict[str, Any]
    ) -> RetrievalResult:
        """Create a RetrievalResult object from search result."""
        try:
            # Extract entity info from vector search result
            entity_name = result.get("canonical_form", result.get("text", ""))
            entity_type = result.get("entity_type", "Unknown")
            
            entity_context = {
                "name": entity_name,
                "type": entity_type,
                "id": result.get("id", ""),
                "canonical_form": result.get("canonical_form", ""),
                "score": result.get("score", 0.0)
            }
            
            return RetrievalResult(
                content=self._format_content(entity_context, graph_context),
                score=result.get("score", 0.0),
                source_id=result.get("id", "unknown"),
                chunk_id=None,  # Vector search doesn't have chunks
                entity_context=entity_context,
                graph_context=graph_context,
                metadata={
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "similarity_score": result.get("score", 0.0),
                    "graph_neighbors_count": len(graph_context.get("neighbors", {}).get(entity_name, [])),
                    "graph_paths_count": len(graph_context.get("paths", []))
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create retrieval result: {e}")
            return RetrievalResult(
                content="",
                score=0.0,
                source_id="unknown",
                chunk_id=None,
                entity_context={},
                graph_context={},
                metadata={"error": str(e)}
            )
            
    def _format_content(
        self,
        entity: Dict[str, Any],
        graph_context: Dict[str, Any]
    ) -> str:
        """Format entity and graph context into readable content."""
        try:
            content_parts = []
            
            # Entity information
            entity_name = entity.get("name", "Unknown")
            entity_type = entity.get("type", "Unknown")
            entity_desc = entity.get("description", "")
            
            content_parts.append(f"Entity: {entity_name} (Type: {entity_type})")
            
            if entity_desc:
                content_parts.append(f"Description: {entity_desc}")
                
            # Properties
            properties = entity.get("properties", {})
            if properties:
                prop_strs = [f"{k}: {v}" for k, v in properties.items() 
                           if k not in ["name", "type", "description"]]
                if prop_strs:
                    content_parts.append(f"Properties: {', '.join(prop_strs)}")
                    
            # Graph context
            connected_entities = graph_context.get("connected_entities", [])
            if connected_entities:
                content_parts.append(f"Connected to: {', '.join(connected_entities[:5])}")
                if len(connected_entities) > 5:
                    content_parts.append(f"... and {len(connected_entities) - 5} more")
                    
            return "\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Content formatting failed: {e}")
            return f"Entity: {entity.get('name', 'Unknown')}"
            
    async def retrieve_by_entities(
        self,
        entity_names: List[str],
        expansion_depth: int = 2
    ) -> List[RetrievalResult]:
        """
        Retrieve information by starting from specific entities.
        
        Args:
            entity_names: List of entity names to start from
            expansion_depth: Depth for graph expansion
            
        Returns:
            List of retrieval results
        """
        try:
            results = []
            
            # Get graph context for all entities
            graph_context = await self._get_graph_context_for_entities(
                entities=entity_names,
                depth=expansion_depth
            )
            
            # Get detailed entity information
            for entity_name in entity_names:
                entity_info = await self.neo4j_client.get_entity(entity_name)
                
                if entity_info:
                    entity_context = {
                        "name": entity_name,
                        "type": entity_info.get("type", "Unknown"),
                        "canonical_form": entity_info.get("canonical_form", entity_name),
                        "confidence": entity_info.get("confidence", 1.0)
                    }
                    
                    # Get specific context for this entity
                    entity_graph_context = {
                        "connected_entities": graph_context.get("neighbors", {}).get(entity_name, []),
                        "related_paths": [p for p in graph_context.get("paths", []) 
                                        if entity_name in p.get("nodes", [])]
                    }
                    
                    retrieval_result = RetrievalResult(
                        content=self._format_content(entity_context, entity_graph_context),
                        score=1.0,  # Full score for exact entity match
                        source_id=entity_info.get("id", entity_name),
                        chunk_id=None,
                        entity_context=entity_context,
                        graph_context=entity_graph_context,
                        metadata={
                            "entity_name": entity_name,
                            "retrieval_type": "entity_direct",
                            "neighbors_count": len(entity_graph_context["connected_entities"])
                        }
                    )
                    results.append(retrieval_result)
                    
            return results
            
        except Exception as e:
            logger.error(f"Entity-based retrieval failed: {e}")
            return []
            
    async def retrieve_subgraph(
        self,
        central_entities: List[str],
        radius: int = 2
    ) -> Dict[str, Any]:
        """
        Retrieve a subgraph centered on specific entities.
        
        Args:
            central_entities: Central entities for the subgraph
            radius: Radius of the subgraph
            
        Returns:
            Subgraph structure with nodes and edges
        """
        try:
            return await self._get_graph_context_for_entities(
                entities=central_entities,
                depth=radius
            )
        except Exception as e:
            logger.error(f"Subgraph retrieval failed: {e}")
            return {"entities": [], "neighbors": {}, "paths": []}
    
    async def search_documents(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """
        Search document chunks only using vector similarity.
        
        Args:
            query: Search query
            top_k: Number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of document chunk results
        """
        return await self.retrieve(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            include_graph_context=False,
            search_modes=["documents"]
        )
    
    async def search_attributes(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """
        Search attribute nodes only using vector similarity.
        
        Args:
            query: Search query
            top_k: Number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of attribute results
        """
        return await self.retrieve(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            include_graph_context=False,
            search_modes=["attributes"]
        )
    
    async def search_relations(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """
        Search relation edges only using vector similarity.
        
        Args:
            query: Search query
            top_k: Number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of relation results
        """
        return await self.retrieve(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            include_graph_context=False,
            search_modes=["relations"]
        )
    
    async def search_entities_only(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """
        Search entity nodes only using vector similarity.
        
        Args:
            query: Search query
            top_k: Number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of entity results
        """
        return await self.retrieve(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            include_graph_context=False,
            search_modes=["entities"]
        )