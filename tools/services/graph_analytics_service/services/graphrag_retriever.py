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

logger = logging.getLogger(__name__)

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
    
    def __init__(self, neo4j_graphrag_client):
        """Initialize retriever with GraphRAG client."""
        self.graphrag_client = neo4j_graphrag_client
        
    async def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        graph_expansion_depth: int = 2,
        include_graph_context: bool = True
    ) -> List[RetrievalResult]:
        """
        Perform comprehensive retrieval using multiple strategies.
        
        Args:
            query: The search query
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            graph_expansion_depth: Depth for graph context expansion
            include_graph_context: Whether to include graph traversal
            
        Returns:
            List of retrieval results with context
        """
        try:
            results = []
            
            # Strategy 1: Semantic similarity search
            semantic_results = await self._semantic_retrieval(
                query=query,
                embedding=query_embedding,
                limit=top_k,
                threshold=similarity_threshold
            )
            
            # Strategy 2: Graph-based retrieval if enabled
            if include_graph_context and semantic_results:
                enhanced_results = await self._enhance_with_graph_context(
                    semantic_results=semantic_results,
                    depth=graph_expansion_depth
                )
                results.extend(enhanced_results)
            else:
                # Convert semantic results to RetrievalResult objects
                for result in semantic_results:
                    retrieval_result = await self._create_retrieval_result(
                        result=result,
                        graph_context={}
                    )
                    results.append(retrieval_result)
                    
            # Sort by score and return top_k
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
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
            return await self.graphrag_client.semantic_search(
                query=query,
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
            # Extract entities from semantic results
            entities = []
            for result in semantic_results:
                if "entity" in result and "name" in result["entity"]:
                    entities.append(result["entity"]["name"])
                    
            # Get graph context for these entities
            graph_context = await self.graphrag_client.graph_traversal_search(
                starting_entities=entities,
                max_depth=depth
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
            
    async def _create_retrieval_result(
        self,
        result: Dict[str, Any],
        graph_context: Dict[str, Any]
    ) -> RetrievalResult:
        """Create a RetrievalResult object from search result."""
        try:
            entity = result.get("entity", {})
            
            return RetrievalResult(
                content=self._format_content(entity, graph_context),
                score=result.get("similarity", 0.0),
                source_id=entity.get("source_id", "unknown"),
                chunk_id=entity.get("chunk_id"),
                entity_context=entity,
                graph_context=graph_context,
                metadata={
                    "entity_name": entity.get("name", ""),
                    "entity_type": entity.get("type", ""),
                    "properties": entity.get("properties", {}),
                    "graph_neighbors_count": len(graph_context.get("connected_entities", [])),
                    "graph_paths_count": len(graph_context.get("related_paths", []))
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
            
            # Get context for each entity
            for entity_name in entity_names:
                entity_context = await self.graphrag_client.get_entity_context(
                    entity_name=entity_name,
                    context_depth=expansion_depth
                )
                
                if entity_context.get("entity"):
                    retrieval_result = RetrievalResult(
                        content=self._format_content(
                            entity_context["entity"],
                            {"connected_entities": [n.get("name", "") for n in entity_context.get("neighbors", [])]}
                        ),
                        score=1.0,  # Full score for exact entity match
                        source_id=entity_context["entity"].get("source_id", "unknown"),
                        chunk_id=entity_context["entity"].get("chunk_id"),
                        entity_context=entity_context["entity"],
                        graph_context=entity_context,
                        metadata={
                            "entity_name": entity_name,
                            "retrieval_type": "entity_direct",
                            "neighbors_count": len(entity_context.get("neighbors", []))
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
            return await self.graphrag_client.graph_traversal_search(
                starting_entities=central_entities,
                max_depth=radius
            )
        except Exception as e:
            logger.error(f"Subgraph retrieval failed: {e}")
            return {"nodes": [], "edges": [], "paths": []}