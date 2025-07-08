#!/usr/bin/env python3
"""
Query Aggregator Service

Provides intelligent query routing and aggregation across multiple search and analysis methods.
Optimized for AI agent interactions with comprehensive result synthesis.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from tools.base_service import BaseService
from .neo4j_graphrag_client import get_neo4j_graphrag_client
from .graphrag_retriever import GraphRAGRetriever
from .knowledge_graph import KnowledgeGraph
from ..utils.embedding_utils import get_embedding_service
from ..utils.graph_utils import calculate_centrality, find_communities, validate_graph_structure

logger = get_logger(__name__)

class QueryType(Enum):
    """Types of queries supported."""
    SEMANTIC = "semantic"           # Semantic similarity search
    ENTITY = "entity"              # Entity-based search
    RELATIONSHIP = "relationship"   # Relationship-based search
    PATH = "path"                  # Path finding
    NEIGHBORHOOD = "neighborhood"   # Local neighborhood exploration
    ANALYTICAL = "analytical"      # Graph analysis queries
    HYBRID = "hybrid"              # Multi-method combined search
    CYPHER = "cypher"              # Direct Cypher queries

@dataclass
class QueryResult:
    """Standardized query result structure."""
    query_id: str
    query_type: QueryType
    query_text: str
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    execution_time: float
    timestamp: datetime
    confidence_scores: Optional[List[float]] = None
    result_count: int = 0
    
    def __post_init__(self):
        self.result_count = len(self.results)

class QueryAggregator(BaseService):
    """
    Advanced query service that intelligently routes queries and aggregates results
    from multiple search and analysis methods for optimal AI agent interaction.
    """
    
    def __init__(self):
        """Initialize query aggregator."""
        super().__init__("QueryAggregator")
        self.embedding_service = None
        self.graphrag_client = None
        self.knowledge_graph = None
        self.retriever = None
        
    async def _initialize_services(self):
        """Initialize services lazily."""
        if self.graphrag_client is None:
            self.embedding_service = get_embedding_service()
            self.graphrag_client = await get_neo4j_graphrag_client()
            
            if self.graphrag_client:
                self.knowledge_graph = KnowledgeGraph(self.graphrag_client)
                self.retriever = GraphRAGRetriever(self.graphrag_client)
    
    async def intelligent_query(self,
                              query: str,
                              context: Optional[Dict[str, Any]] = None,
                              max_results: int = 20,
                              include_analysis: bool = True) -> Dict[str, Any]:
        """
        Intelligent query that automatically determines the best search strategy
        and aggregates results from multiple methods.
        
        Args:
            query: Natural language query
            context: Optional context to guide search
            max_results: Maximum number of results to return
            include_analysis: Whether to include graph analysis
            
        Returns:
            Comprehensive query results with aggregated insights
        """
        start_time = datetime.now()
        query_id = f"iq_{int(start_time.timestamp() * 1000)}"
        
        try:
            await self._initialize_services()
            
            if not self.graphrag_client:
                return {
                    "status": "error",
                    "message": "Graph services not available",
                    "query": query
                }
            
            logger.info(f"Starting intelligent query: {query[:100]}...")
            
            # Analyze query to determine strategy
            query_strategy = await self._analyze_query_intent(query, context)
            
            # Execute multiple search strategies in parallel
            search_tasks = []
            
            # Always include semantic search
            search_tasks.append(self._semantic_search(query, max_results // 2))
            
            # Add strategy-specific searches
            if query_strategy.get("has_entities"):
                search_tasks.append(self._entity_focused_search(query, query_strategy["entities"], max_results // 4))
            
            if query_strategy.get("has_relationships"):
                search_tasks.append(self._relationship_search(query, max_results // 4))
            
            if query_strategy.get("is_analytical"):
                search_tasks.append(self._analytical_search(query, context))
            
            # Execute searches concurrently
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Aggregate and synthesize results
            aggregated_results = await self._aggregate_search_results(
                query, search_results, query_strategy, max_results
            )
            
            # Add analysis if requested
            if include_analysis and aggregated_results["results"]:
                analysis = await self._generate_result_analysis(
                    query, aggregated_results["results"], query_strategy
                )
                aggregated_results["analysis"] = analysis
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "success",
                "query_id": query_id,
                "query": query,
                "strategy": query_strategy,
                "results": aggregated_results["results"],
                "result_summary": aggregated_results["summary"],
                "analysis": aggregated_results.get("analysis", {}),
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Intelligent query failed: {e}")
            return {
                "status": "error",
                "query_id": query_id,
                "query": query,
                "message": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def semantic_search(self,
                            query: str,
                            similarity_threshold: float = 0.7,
                            max_results: int = 10) -> QueryResult:
        """Pure semantic similarity search."""
        start_time = datetime.now()
        
        try:
            await self._initialize_services()
            
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_single_embedding(query)
            
            # Perform semantic search
            results = await self.graphrag_client.semantic_search(
                query=query,
                embedding=query_embedding,
                limit=max_results,
                similarity_threshold=similarity_threshold
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                query_id=f"sem_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.SEMANTIC,
                query_text=query,
                results=results,
                metadata={
                    "similarity_threshold": similarity_threshold,
                    "embedding_dimension": len(query_embedding) if query_embedding else 0
                },
                execution_time=execution_time,
                timestamp=start_time,
                confidence_scores=[r.get("similarity", 0.0) for r in results]
            )
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return QueryResult(
                query_id=f"sem_error_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.SEMANTIC,
                query_text=query,
                results=[],
                metadata={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    async def entity_search(self,
                          entity_name: Optional[str] = None,
                          entity_type: Optional[str] = None,
                          properties: Optional[Dict[str, Any]] = None,
                          max_results: int = 50) -> QueryResult:
        """Search for specific entities."""
        start_time = datetime.now()
        
        try:
            await self._initialize_services()
            
            results = await self.knowledge_graph.query_entities(
                entity_type=entity_type,
                properties=properties,
                limit=max_results
            )
            
            # Filter by entity name if provided
            if entity_name:
                results = [r for r in results if entity_name.lower() in r.get("name", "").lower()]
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                query_id=f"ent_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.ENTITY,
                query_text=f"Entity search: {entity_name or 'any'} ({entity_type or 'any type'})",
                results=results,
                metadata={
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "properties": properties
                },
                execution_time=execution_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"Entity search failed: {e}")
            return QueryResult(
                query_id=f"ent_error_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.ENTITY,
                query_text=f"Entity search error: {entity_name}",
                results=[],
                metadata={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    async def relationship_search(self,
                                source_entity: Optional[str] = None,
                                target_entity: Optional[str] = None,
                                relationship_type: Optional[str] = None,
                                max_results: int = 50) -> QueryResult:
        """Search for relationships."""
        start_time = datetime.now()
        
        try:
            await self._initialize_services()
            
            results = await self.knowledge_graph.query_relationships(
                source_entity=source_entity,
                target_entity=target_entity,
                relationship_type=relationship_type,
                limit=max_results
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                query_id=f"rel_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.RELATIONSHIP,
                query_text=f"Relationship: {source_entity or 'any'} -> {target_entity or 'any'}",
                results=results,
                metadata={
                    "source_entity": source_entity,
                    "target_entity": target_entity,
                    "relationship_type": relationship_type
                },
                execution_time=execution_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"Relationship search failed: {e}")
            return QueryResult(
                query_id=f"rel_error_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.RELATIONSHIP,
                query_text=f"Relationship search error",
                results=[],
                metadata={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    async def path_analysis(self,
                          source_entity: str,
                          target_entity: str,
                          max_depth: int = 5) -> QueryResult:
        """Find and analyze paths between entities."""
        start_time = datetime.now()
        
        try:
            await self._initialize_services()
            
            paths = await self.knowledge_graph.find_paths(
                source_entity=source_entity,
                target_entity=target_entity,
                max_depth=max_depth,
                path_type="all"
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                query_id=f"path_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.PATH,
                query_text=f"Paths: {source_entity} -> {target_entity}",
                results=paths,
                metadata={
                    "source_entity": source_entity,
                    "target_entity": target_entity,
                    "max_depth": max_depth,
                    "shortest_path_length": min((p.get("length", float('inf')) for p in paths), default=0)
                },
                execution_time=execution_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"Path analysis failed: {e}")
            return QueryResult(
                query_id=f"path_error_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.PATH,
                query_text=f"Path analysis error: {source_entity} -> {target_entity}",
                results=[],
                metadata={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    async def neighborhood_analysis(self,
                                  entity_name: str,
                                  radius: int = 2,
                                  include_analysis: bool = True) -> QueryResult:
        """Analyze the neighborhood around an entity."""
        start_time = datetime.now()
        
        try:
            await self._initialize_services()
            
            neighborhood = await self.knowledge_graph.get_entity_neighborhood(
                entity_name=entity_name,
                radius=radius,
                include_properties=True
            )
            
            # Add analysis if requested
            analysis = {}
            if include_analysis and neighborhood.get("neighbors"):
                # Calculate local centrality
                local_graph = {
                    "nodes": {entity_name: neighborhood.get("central_entity", {})},
                    "edges": {}
                }
                
                # Add neighbors as nodes
                for i, neighbor in enumerate(neighborhood.get("neighbors", [])):
                    local_graph["nodes"][f"neighbor_{i}"] = neighbor
                    # Create edges (simplified)
                    local_graph["edges"][f"edge_{i}"] = {
                        "source": entity_name,
                        "target": f"neighbor_{i}",
                        "weight": 1.0
                    }
                
                try:
                    centrality = calculate_centrality(local_graph, "degree")
                    analysis["centrality"] = centrality
                    analysis["degree"] = len(neighborhood.get("neighbors", []))
                except Exception as e:
                    logger.warning(f"Local centrality calculation failed: {e}")
            
            result_data = {
                "neighborhood": neighborhood,
                "analysis": analysis
            }
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                query_id=f"neigh_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.NEIGHBORHOOD,
                query_text=f"Neighborhood of {entity_name}",
                results=[result_data],
                metadata={
                    "entity_name": entity_name,
                    "radius": radius,
                    "neighbor_count": len(neighborhood.get("neighbors", []))
                },
                execution_time=execution_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"Neighborhood analysis failed: {e}")
            return QueryResult(
                query_id=f"neigh_error_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.NEIGHBORHOOD,
                query_text=f"Neighborhood analysis error: {entity_name}",
                results=[],
                metadata={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    async def graph_analysis(self,
                           analysis_types: List[str] = None,
                           entity_filter: Optional[str] = None) -> QueryResult:
        """Perform comprehensive graph analysis."""
        start_time = datetime.now()
        analysis_types = analysis_types or ["statistics", "centrality", "communities"]
        
        try:
            await self._initialize_services()
            
            results = {}
            
            # Graph statistics
            if "statistics" in analysis_types:
                stats = await self.knowledge_graph.get_graph_statistics()
                results["statistics"] = {
                    "total_entities": stats.total_entities,
                    "total_relationships": stats.total_relationships,
                    "entity_types": stats.entity_types,
                    "relationship_types": stats.relationship_types,
                    "average_degree": stats.average_degree,
                    "connected_components": stats.connected_components
                }
            
            # Centrality analysis
            if "centrality" in analysis_types:
                try:
                    # Get a subgraph for analysis (limit size for performance)
                    entities = await self.knowledge_graph.query_entities(limit=100)
                    relationships = await self.knowledge_graph.query_relationships(limit=200)
                    
                    if entities and relationships:
                        # Build graph structure
                        graph = {
                            "nodes": {e["name"]: e for e in entities},
                            "edges": {f"edge_{i}": r for i, r in enumerate(relationships)}
                        }
                        
                        centrality_results = {}
                        for metric in ["degree", "betweenness", "closeness"]:
                            try:
                                centrality = calculate_centrality(graph, metric)
                                # Get top 10 most central entities
                                top_central = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
                                centrality_results[metric] = top_central
                            except Exception as e:
                                logger.warning(f"Centrality calculation failed for {metric}: {e}")
                        
                        results["centrality"] = centrality_results
                except Exception as e:
                    logger.warning(f"Centrality analysis failed: {e}")
                    results["centrality"] = {"error": str(e)}
            
            # Community detection
            if "communities" in analysis_types:
                try:
                    # Use same subgraph as centrality
                    entities = await self.knowledge_graph.query_entities(limit=100)
                    relationships = await self.knowledge_graph.query_relationships(limit=200)
                    
                    if entities and relationships:
                        graph = {
                            "nodes": {e["name"]: e for e in entities},
                            "edges": {f"edge_{i}": r for i, r in enumerate(relationships)}
                        }
                        
                        communities = find_communities(graph)
                        results["communities"] = communities
                except Exception as e:
                    logger.warning(f"Community detection failed: {e}")
                    results["communities"] = {"error": str(e)}
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                query_id=f"analysis_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.ANALYTICAL,
                query_text=f"Graph analysis: {', '.join(analysis_types)}",
                results=[results],
                metadata={
                    "analysis_types": analysis_types,
                    "entity_filter": entity_filter
                },
                execution_time=execution_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"Graph analysis failed: {e}")
            return QueryResult(
                query_id=f"analysis_error_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.ANALYTICAL,
                query_text=f"Graph analysis error",
                results=[],
                metadata={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    async def cypher_query(self,
                          cypher: str,
                          parameters: Optional[Dict[str, Any]] = None) -> QueryResult:
        """Execute a direct Cypher query."""
        start_time = datetime.now()
        
        try:
            await self._initialize_services()
            
            results = await self.graphrag_client.neo4j_client.execute_query(cypher, parameters)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                query_id=f"cypher_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.CYPHER,
                query_text=cypher,
                results=results,
                metadata={
                    "parameters": parameters,
                    "query_length": len(cypher)
                },
                execution_time=execution_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"Cypher query failed: {e}")
            return QueryResult(
                query_id=f"cypher_error_{int(start_time.timestamp() * 1000)}",
                query_type=QueryType.CYPHER,
                query_text=cypher,
                results=[],
                metadata={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=start_time
            )
    
    # === Helper methods ===
    
    async def _analyze_query_intent(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze query to determine optimal search strategy."""
        strategy = {
            "has_entities": False,
            "has_relationships": False,
            "is_analytical": False,
            "is_factual": False,
            "entities": [],
            "confidence": 0.8
        }
        
        # Simple keyword-based analysis (could be enhanced with NLP)
        query_lower = query.lower()
        
        # Check for analytical queries
        analytical_keywords = ["analyze", "analysis", "compare", "statistics", "central", "important", "communities", "clusters"]
        if any(keyword in query_lower for keyword in analytical_keywords):
            strategy["is_analytical"] = True
        
        # Check for relationship queries
        relationship_keywords = ["relationship", "connection", "link", "between", "related", "connect"]
        if any(keyword in query_lower for keyword in relationship_keywords):
            strategy["has_relationships"] = True
        
        # Check for factual queries
        factual_keywords = ["what", "who", "when", "where", "how", "why"]
        if any(query_lower.startswith(keyword) for keyword in factual_keywords):
            strategy["is_factual"] = True
        
        # TODO: Use NER to extract entities from query
        # For now, assume entities are present if not purely analytical
        if not strategy["is_analytical"]:
            strategy["has_entities"] = True
        
        return strategy
    
    async def _semantic_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Perform semantic search."""
        try:
            query_embedding = await self.embedding_service.generate_single_embedding(query)
            results = await self.graphrag_client.semantic_search(
                query=query,
                embedding=query_embedding,
                limit=max_results,
                similarity_threshold=0.6
            )
            return results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    async def _entity_focused_search(self, query: str, entities: List[str], max_results: int) -> List[Dict[str, Any]]:
        """Search focusing on specific entities."""
        try:
            results = []
            for entity in entities[:5]:  # Limit to prevent too many queries
                entity_results = await self.knowledge_graph.query_entities(
                    properties={"name": entity},
                    limit=max_results // len(entities)
                )
                results.extend(entity_results)
            return results
        except Exception as e:
            logger.error(f"Entity focused search failed: {e}")
            return []
    
    async def _relationship_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search for relationships."""
        try:
            results = await self.knowledge_graph.query_relationships(limit=max_results)
            return results
        except Exception as e:
            logger.error(f"Relationship search failed: {e}")
            return []
    
    async def _analytical_search(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform analytical search."""
        try:
            stats = await self.knowledge_graph.get_graph_statistics()
            return {
                "type": "analytics",
                "statistics": {
                    "total_entities": stats.total_entities,
                    "total_relationships": stats.total_relationships,
                    "entity_types": stats.entity_types,
                    "relationship_types": stats.relationship_types
                }
            }
        except Exception as e:
            logger.error(f"Analytical search failed: {e}")
            return {"type": "analytics", "error": str(e)}
    
    async def _aggregate_search_results(self,
                                      query: str,
                                      search_results: List[Any],
                                      strategy: Dict[str, Any],
                                      max_results: int) -> Dict[str, Any]:
        """Aggregate results from multiple search methods."""
        all_results = []
        result_sources = []
        
        for i, result in enumerate(search_results):
            if isinstance(result, Exception):
                logger.warning(f"Search method {i} failed: {result}")
                continue
            
            if isinstance(result, list):
                all_results.extend(result)
                result_sources.extend([f"method_{i}"] * len(result))
            elif isinstance(result, dict):
                all_results.append(result)
                result_sources.append(f"method_{i}")
        
        # Remove duplicates and rank results
        unique_results = []
        seen_ids = set()
        
        for i, result in enumerate(all_results):
            # Create a unique identifier for the result
            result_id = self._get_result_id(result)
            
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                result["_source"] = result_sources[i]
                result["_rank"] = len(unique_results)
                unique_results.append(result)
                
                if len(unique_results) >= max_results:
                    break
        
        return {
            "results": unique_results,
            "summary": {
                "total_results": len(unique_results),
                "search_methods_used": len([r for r in search_results if not isinstance(r, Exception)]),
                "deduplicated_from": len(all_results)
            }
        }
    
    async def _generate_result_analysis(self,
                                      query: str,
                                      results: List[Dict[str, Any]],
                                      strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis of search results."""
        analysis = {
            "result_distribution": {},
            "key_entities": [],
            "key_relationships": [],
            "insights": []
        }
        
        # Analyze result sources
        sources = {}
        for result in results:
            source = result.get("_source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        analysis["result_distribution"] = sources
        
        # Extract key entities (simplified)
        entities = set()
        for result in results:
            if "entity" in result:
                entities.add(result["entity"].get("name", ""))
            elif "name" in result:
                entities.add(result["name"])
        analysis["key_entities"] = list(entities)[:10]
        
        # Generate insights based on strategy
        if strategy.get("is_analytical"):
            analysis["insights"].append("This appears to be an analytical query - consider using graph analysis tools")
        
        if len(results) == 0:
            analysis["insights"].append("No results found - try broader search terms or check if data exists")
        elif len(results) > 50:
            analysis["insights"].append("Many results found - consider adding filters or more specific terms")
        
        return analysis
    
    def _get_result_id(self, result: Dict[str, Any]) -> str:
        """Generate a unique ID for a result to enable deduplication."""
        if "entity" in result and "name" in result["entity"]:
            return f"entity_{result['entity']['name']}"
        elif "name" in result:
            return f"entity_{result['name']}"
        elif "source" in result and "target" in result:
            return f"rel_{result['source']}_{result['target']}"
        else:
            return f"result_{hash(str(result))}"

# Global instance
_query_aggregator = None

def get_query_aggregator() -> QueryAggregator:
    """Get or create the global query aggregator instance."""
    global _query_aggregator
    if _query_aggregator is None:
        _query_aggregator = QueryAggregator()
    return _query_aggregator