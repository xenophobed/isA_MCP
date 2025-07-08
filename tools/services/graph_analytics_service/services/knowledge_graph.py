#!/usr/bin/env python3
"""
Knowledge Graph Service

High-level interface for knowledge graph operations including
construction, querying, and management.
"""

import logging
from typing import List, Dict, Any, Optional, Set
import asyncio
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GraphStatistics:
    """Statistics about the knowledge graph."""
    total_entities: int
    total_relationships: int
    entity_types: Dict[str, int]
    relationship_types: Dict[str, int]
    average_degree: float
    connected_components: int
    last_updated: datetime

class KnowledgeGraph:
    """
    High-level knowledge graph service providing comprehensive
    graph management and querying capabilities.
    """
    
    def __init__(self, neo4j_graphrag_client):
        """Initialize knowledge graph with GraphRAG client."""
        self.graphrag_client = neo4j_graphrag_client
        self.neo4j_client = neo4j_graphrag_client.neo4j_client
        
    async def build_from_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Build knowledge graph from a collection of documents.
        
        Args:
            documents: List of documents with 'content', 'id', and optional metadata
            batch_size: Number of documents to process in parallel
            
        Returns:
            Build statistics and summary
        """
        try:
            total_docs = len(documents)
            processed_docs = 0
            total_entities = 0
            total_relationships = 0
            errors = []
            
            logger.info(f"Building knowledge graph from {total_docs} documents")
            
            # Process documents in batches
            for i in range(0, total_docs, batch_size):
                batch = documents[i:i + batch_size]
                batch_tasks = []
                
                for doc in batch:
                    task = self._process_document(doc)
                    batch_tasks.append(task)
                    
                # Process batch
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Collect results
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        error_msg = f"Document {batch[j].get('id', 'unknown')}: {str(result)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                    else:
                        total_entities += result.get("entities_stored", 0)
                        total_relationships += result.get("relationships_stored", 0)
                        processed_docs += 1
                        
                # Log progress
                logger.info(f"Processed {processed_docs}/{total_docs} documents")
                
            return {
                "total_documents": total_docs,
                "processed_documents": processed_docs,
                "failed_documents": len(errors),
                "total_entities_created": total_entities,
                "total_relationships_created": total_relationships,
                "errors": errors[:10],  # Limit error list
                "success_rate": processed_docs / total_docs if total_docs > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Knowledge graph building failed: {e}")
            return {
                "total_documents": len(documents),
                "processed_documents": 0,
                "error": str(e)
            }
            
    async def _process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document for knowledge extraction."""
        try:
            content = document.get("content", "")
            doc_id = document.get("id", "unknown")
            metadata = document.get("metadata", {})
            
            if not content.strip():
                return {"entities_stored": 0, "relationships_stored": 0}
                
            # Extract and store entities and relationships
            result = await self.graphrag_client.extract_and_store_from_text(
                text=content,
                source_id=doc_id,
                chunk_id=metadata.get("chunk_id")
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise e
            
    async def query_entities(
        self,
        entity_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query entities by type and properties.
        
        Args:
            entity_type: Filter by entity type
            properties: Filter by properties
            limit: Maximum number of results
            
        Returns:
            List of matching entities
        """
        try:
            # Build Cypher query
            where_clauses = []
            
            if entity_type:
                where_clauses.append(f"n.type = '{entity_type}'")
                
            if properties:
                for key, value in properties.items():
                    if isinstance(value, str):
                        where_clauses.append(f"n.{key} = '{value}'")
                    else:
                        where_clauses.append(f"n.{key} = {value}")
                        
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
            MATCH (n:Entity)
            WHERE {where_clause}
            RETURN n
            LIMIT {limit}
            """
            
            results = await self.neo4j_client.execute_query(query)
            
            # Format results
            entities = []
            for record in results:
                node = record["n"]
                entities.append(dict(node))
                
            return entities
            
        except Exception as e:
            logger.error(f"Entity query failed: {e}")
            return []
            
    async def query_relationships(
        self,
        source_entity: Optional[str] = None,
        target_entity: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query relationships by entities and type.
        
        Args:
            source_entity: Source entity name
            target_entity: Target entity name
            relationship_type: Relationship type
            limit: Maximum number of results
            
        Returns:
            List of matching relationships
        """
        try:
            # Build Cypher query
            where_clauses = []
            
            if source_entity:
                where_clauses.append(f"source.name = '{source_entity}'")
            if target_entity:
                where_clauses.append(f"target.name = '{target_entity}'")
            if relationship_type:
                where_clauses.append(f"type(r) = '{relationship_type}'")
                
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
            MATCH (source:Entity)-[r]->(target:Entity)
            WHERE {where_clause}
            RETURN source.name as source, type(r) as relationship, target.name as target, r
            LIMIT {limit}
            """
            
            results = await self.neo4j_client.execute_query(query)
            
            # Format results
            relationships = []
            for record in results:
                relationships.append({
                    "source": record["source"],
                    "relationship": record["relationship"],
                    "target": record["target"],
                    "properties": dict(record["r"])
                })
                
            return relationships
            
        except Exception as e:
            logger.error(f"Relationship query failed: {e}")
            return []
            
    async def get_graph_statistics(self) -> GraphStatistics:
        """Get comprehensive statistics about the knowledge graph."""
        try:
            stats = await self.neo4j_client.get_graph_statistics()
            
            # Get entity type distribution
            entity_type_query = """
            MATCH (n:Entity)
            RETURN n.type as type, count(*) as count
            ORDER BY count DESC
            """
            
            entity_type_results = await self.neo4j_client.execute_query(entity_type_query)
            entity_types = {record["type"]: record["count"] for record in entity_type_results}
            
            # Get relationship type distribution
            relationship_type_query = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(*) as count
            ORDER BY count DESC
            """
            
            rel_type_results = await self.neo4j_client.execute_query(relationship_type_query)
            relationship_types = {record["type"]: record["count"] for record in rel_type_results}
            
            # Calculate average degree
            degree_query = """
            MATCH (n:Entity)
            RETURN avg(COUNT { (n)--() }) as avg_degree
            """
            
            degree_results = await self.neo4j_client.execute_query(degree_query)
            avg_degree = degree_results[0]["avg_degree"] if degree_results else 0.0
            
            return GraphStatistics(
                total_entities=stats.get("entities", 0),
                total_relationships=stats.get("relationships", 0),
                entity_types=entity_types,
                relationship_types=relationship_types,
                average_degree=float(avg_degree) if avg_degree else 0.0,
                connected_components=1,  # Simplified - would need complex query
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            return GraphStatistics(
                total_entities=0,
                total_relationships=0,
                entity_types={},
                relationship_types={},
                average_degree=0.0,
                connected_components=0,
                last_updated=datetime.now()
            )
            
    async def find_paths(
        self,
        source_entity: str,
        target_entity: str,
        max_depth: int = 5,
        path_type: str = "shortest"
    ) -> List[Dict[str, Any]]:
        """
        Find paths between two entities.
        
        Args:
            source_entity: Source entity name
            target_entity: Target entity name
            max_depth: Maximum path length
            path_type: Type of path ('shortest', 'all')
            
        Returns:
            List of paths
        """
        try:
            if path_type == "shortest":
                path = await self.neo4j_client.find_shortest_path(
                    source_entity=source_entity,
                    target_entity=target_entity
                )
                return [path] if path else []
            else:
                # Find all paths (limited implementation)
                query = f"""
                MATCH path = (source:Entity {{name: '{source_entity}'}})-[*1..{max_depth}]-(target:Entity {{name: '{target_entity}'}})
                RETURN path
                LIMIT 10
                """
                
                results = await self.neo4j_client.execute_query(query)
                paths = []
                
                for record in results:
                    path_data = record["path"]
                    # Extract path information
                    nodes = [node["name"] for node in path_data.nodes]
                    relationships = [rel.type for rel in path_data.relationships]
                    
                    paths.append({
                        "nodes": nodes,
                        "relationships": relationships,
                        "length": len(relationships)
                    })
                    
                return paths
                
        except Exception as e:
            logger.error(f"Path finding failed: {e}")
            return []
            
    async def get_entity_neighborhood(
        self,
        entity_name: str,
        radius: int = 2,
        include_properties: bool = True
    ) -> Dict[str, Any]:
        """
        Get the neighborhood of an entity.
        
        Args:
            entity_name: Name of the central entity
            radius: Neighborhood radius
            include_properties: Whether to include node properties
            
        Returns:
            Neighborhood structure
        """
        try:
            context = await self.graphrag_client.get_entity_context(
                entity_name=entity_name,
                context_depth=radius
            )
            
            if not context.get("entity"):
                return {"nodes": [], "edges": []}
                
            # Format neighborhood
            neighborhood = {
                "central_entity": context["entity"],
                "neighbors": context.get("neighbors", []),
                "radius": radius
            }
            
            if not include_properties:
                # Remove properties from entities
                for neighbor in neighborhood["neighbors"]:
                    neighbor.pop("properties", None)
                    
            return neighborhood
            
        except Exception as e:
            logger.error(f"Neighborhood retrieval failed: {e}")
            return {"nodes": [], "edges": []}
            
    async def merge_duplicate_entities(
        self,
        similarity_threshold: float = 0.9
    ) -> Dict[str, Any]:
        """
        Identify and merge duplicate entities based on similarity.
        
        Args:
            similarity_threshold: Threshold for considering entities duplicates
            
        Returns:
            Merge operation summary
        """
        try:
            # This is a simplified implementation
            # In practice, you'd use vector similarity or string matching
            
            query = """
            MATCH (e1:Entity), (e2:Entity)
            WHERE e1.name <> e2.name 
            AND e1.type = e2.type
            AND apoc.text.jaroWinkler(e1.name, e2.name) > $threshold
            RETURN e1.name as entity1, e2.name as entity2, 
                   apoc.text.jaroWinkler(e1.name, e2.name) as similarity
            """
            
            # Note: This requires APOC plugin in Neo4j
            # For now, return empty result
            logger.info("Duplicate entity merging requires APOC plugin")
            return {
                "candidates_found": 0,
                "entities_merged": 0,
                "note": "Requires APOC plugin for string similarity functions"
            }
            
        except Exception as e:
            logger.error(f"Entity merging failed: {e}")
            return {"error": str(e)}
            
    async def export_subgraph(
        self,
        entity_names: List[str],
        radius: int = 2,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export a subgraph around specific entities.
        
        Args:
            entity_names: Central entities for the subgraph
            radius: Expansion radius
            format: Export format ('json', 'gexf', 'graphml')
            
        Returns:
            Exported subgraph data
        """
        try:
            subgraph = await self.graphrag_client.graph_traversal_search(
                starting_entities=entity_names,
                max_depth=radius
            )
            
            if format == "json":
                return subgraph
            else:
                # Other formats would require additional libraries
                logger.warning(f"Export format '{format}' not implemented, returning JSON")
                return subgraph
                
        except Exception as e:
            logger.error(f"Subgraph export failed: {e}")
            return {"nodes": [], "edges": [], "error": str(e)}