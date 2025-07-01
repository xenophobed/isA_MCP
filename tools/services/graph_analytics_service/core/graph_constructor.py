#!/usr/bin/env python3
"""
Graph Constructor for Graph Analytics

Constructs knowledge graphs from extracted entities, relations, and attributes.
Handles graph structure creation, optimization, and validation.
"""

import json
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict

from core.logging import get_logger
from .entity_extractor import Entity, EntityType
from .relation_extractor import Relation, RelationType
from .attribute_extractor import Attribute, AttributeType

logger = get_logger(__name__)

@dataclass
class GraphNode:
    """Graph node representing an entity"""
    id: str
    entity: Entity
    attributes: Dict[str, Attribute]
    node_type: str = "entity"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class GraphEdge:
    """Graph edge representing a relationship"""
    id: str
    source_id: str
    target_id: str
    relation: Relation
    edge_type: str = "relation"
    weight: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class KnowledgeGraph:
    """Knowledge graph data structure"""
    nodes: Dict[str, GraphNode]
    edges: Dict[str, GraphEdge]
    metadata: Dict[str, Any]
    created_at: str
    
    def __post_init__(self):
        if not hasattr(self, 'created_at'):
            self.created_at = datetime.now().isoformat()

class GraphConstructor:
    """Construct knowledge graphs from extracted information"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize graph constructor
        
        Args:
            config: Configuration dict with constructor settings
        """
        self.config = config or {}
        self.node_id_counter = 0
        self.edge_id_counter = 0
        
        logger.info("GraphConstructor initialized")
    
    def construct_graph(self, 
                       entities: List[Entity],
                       relations: List[Relation],
                       entity_attributes: Dict[str, Dict[str, Attribute]],
                       source_text: str = "") -> KnowledgeGraph:
        """Construct knowledge graph from extracted components
        
        Args:
            entities: List of extracted entities
            relations: List of extracted relations
            entity_attributes: Dictionary mapping entity text to attributes
            source_text: Original source text
            
        Returns:
            Constructed knowledge graph
        """
        nodes = {}
        edges = {}
        
        # Create nodes from entities
        entity_to_node_id = {}
        for entity in entities:
            node_id = self._generate_node_id(entity)
            entity_to_node_id[entity.text] = node_id
            
            # Get attributes for this entity
            attributes = entity_attributes.get(entity.text, {})
            
            node = GraphNode(
                id=node_id,
                entity=entity,
                attributes=attributes,
                metadata={
                    "entity_type": entity.entity_type.value,
                    "confidence": entity.confidence,
                    "canonical_form": entity.canonical_form,
                    "aliases": entity.aliases
                }
            )
            nodes[node_id] = node
        
        # Create edges from relations
        for relation in relations:
            # Find corresponding node IDs
            source_id = entity_to_node_id.get(relation.subject.text)
            target_id = entity_to_node_id.get(relation.object.text)
            
            if source_id and target_id:
                edge_id = self._generate_edge_id(relation)
                
                edge = GraphEdge(
                    id=edge_id,
                    source_id=source_id,
                    target_id=target_id,
                    relation=relation,
                    weight=relation.confidence,
                    metadata={
                        "relation_type": relation.relation_type.value,
                        "predicate": relation.predicate,
                        "confidence": relation.confidence,
                        "context": relation.context,
                        "properties": relation.properties,
                        "temporal_info": relation.temporal_info
                    }
                )
                edges[edge_id] = edge
        
        # Create graph metadata
        metadata = {
            "source_text_length": len(source_text),
            "entities_count": len(entities),
            "relations_count": len(relations),
            "attributes_count": sum(len(attrs) for attrs in entity_attributes.values()),
            "entity_types": list(set(e.entity_type.value for e in entities)),
            "relation_types": list(set(r.relation_type.value for r in relations)),
            "construction_config": self.config
        }
        
        graph = KnowledgeGraph(
            nodes=nodes,
            edges=edges,
            metadata=metadata,
            created_at=datetime.now().isoformat()
        )
        
        logger.info(f"Constructed knowledge graph: {len(nodes)} nodes, {len(edges)} edges")
        return graph
    
    def _generate_node_id(self, entity: Entity) -> str:
        """Generate unique node ID for entity"""
        self.node_id_counter += 1
        # Use entity type and canonical form for meaningful IDs
        safe_text = entity.canonical_form.replace(" ", "_").replace("/", "_")
        return f"{entity.entity_type.value.lower()}_{safe_text}_{self.node_id_counter}"
    
    def _generate_edge_id(self, relation: Relation) -> str:
        """Generate unique edge ID for relation"""
        self.edge_id_counter += 1
        return f"{relation.relation_type.value.lower()}_{self.edge_id_counter}"
    
    def optimize_graph(self, graph: KnowledgeGraph) -> KnowledgeGraph:
        """Optimize graph structure by merging similar nodes and removing redundant edges"""
        
        # Find and merge similar entities
        merged_nodes = self._merge_similar_nodes(graph.nodes)
        
        # Remove redundant edges
        filtered_edges = self._remove_redundant_edges(graph.edges, merged_nodes)
        
        # Update metadata
        graph.metadata.update({
            "optimization_applied": True,
            "optimization_timestamp": datetime.now().isoformat(),
            "nodes_before_merge": len(graph.nodes),
            "nodes_after_merge": len(merged_nodes),
            "edges_before_filter": len(graph.edges),
            "edges_after_filter": len(filtered_edges)
        })
        
        optimized_graph = KnowledgeGraph(
            nodes=merged_nodes,
            edges=filtered_edges,
            metadata=graph.metadata,
            created_at=graph.created_at
        )
        
        logger.info(f"Optimized graph: {len(merged_nodes)} nodes, {len(filtered_edges)} edges")
        return optimized_graph
    
    def _merge_similar_nodes(self, nodes: Dict[str, GraphNode]) -> Dict[str, GraphNode]:
        """Merge nodes representing the same entity"""
        merged_nodes = {}
        processed_entities = set()
        
        for node_id, node in nodes.items():
            entity_key = node.entity.canonical_form.lower()
            
            if entity_key in processed_entities:
                continue
            
            # Find all nodes with the same canonical form
            similar_nodes = [
                (nid, n) for nid, n in nodes.items()
                if n.entity.canonical_form.lower() == entity_key
            ]
            
            if len(similar_nodes) == 1:
                # No merging needed
                merged_nodes[node_id] = node
            else:
                # Merge similar nodes
                merged_node = self._merge_nodes(similar_nodes)
                merged_nodes[merged_node.id] = merged_node
            
            processed_entities.add(entity_key)
        
        return merged_nodes
    
    def _merge_nodes(self, similar_nodes: List[Tuple[str, GraphNode]]) -> GraphNode:
        """Merge multiple nodes representing the same entity"""
        # Use the node with highest confidence as base
        base_node_id, base_node = max(similar_nodes, key=lambda x: x[1].entity.confidence)
        
        # Merge attributes from all nodes
        merged_attributes = {}
        all_aliases = set(base_node.entity.aliases)
        
        for node_id, node in similar_nodes:
            # Merge attributes (keep highest confidence for each attribute)
            for attr_name, attribute in node.attributes.items():
                if (attr_name not in merged_attributes or 
                    attribute.confidence > merged_attributes[attr_name].confidence):
                    merged_attributes[attr_name] = attribute
            
            # Collect all aliases
            all_aliases.update(node.entity.aliases)
        
        # Update base entity with merged information
        base_node.entity.aliases = list(all_aliases)
        base_node.attributes = merged_attributes
        base_node.metadata.update({
            "merged_from": [node_id for node_id, _ in similar_nodes if node_id != base_node_id],
            "merge_count": len(similar_nodes)
        })
        
        return base_node
    
    def _remove_redundant_edges(self, edges: Dict[str, GraphEdge], 
                               nodes: Dict[str, GraphNode]) -> Dict[str, GraphEdge]:
        """Remove redundant or low-quality edges"""
        # Group edges by source-target pair
        edge_groups = defaultdict(list)
        for edge_id, edge in edges.items():
            key = (edge.source_id, edge.target_id)
            edge_groups[key].append((edge_id, edge))
        
        filtered_edges = {}
        
        for (source_id, target_id), edge_list in edge_groups.items():
            if len(edge_list) == 1:
                # Single edge, keep it
                edge_id, edge = edge_list[0]
                filtered_edges[edge_id] = edge
            else:
                # Multiple edges between same nodes, keep the best one
                best_edge_id, best_edge = max(edge_list, key=lambda x: x[1].weight)
                
                # Update metadata to show merged edges
                merged_relations = [edge.relation.relation_type.value for _, edge in edge_list]
                best_edge.metadata.update({
                    "merged_relations": merged_relations,
                    "original_edge_count": len(edge_list)
                })
                
                filtered_edges[best_edge_id] = best_edge
        
        return filtered_edges
    
    def validate_graph(self, graph: KnowledgeGraph) -> Dict[str, Any]:
        """Validate graph structure and content"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        # Check node validity
        for node_id, node in graph.nodes.items():
            if not node.entity.text.strip():
                validation_results["errors"].append(f"Node {node_id} has empty entity text")
                validation_results["valid"] = False
        
        # Check edge validity
        for edge_id, edge in graph.edges.items():
            if edge.source_id not in graph.nodes:
                validation_results["errors"].append(f"Edge {edge_id} references missing source node {edge.source_id}")
                validation_results["valid"] = False
            
            if edge.target_id not in graph.nodes:
                validation_results["errors"].append(f"Edge {edge_id} references missing target node {edge.target_id}")
                validation_results["valid"] = False
            
            if edge.weight < 0 or edge.weight > 1:
                validation_results["warnings"].append(f"Edge {edge_id} has unusual weight: {edge.weight}")
        
        # Calculate statistics
        validation_results["statistics"] = {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "isolated_nodes": len([n for n in graph.nodes.keys() if not self._node_has_edges(n, graph.edges)]),
            "average_node_degree": self._calculate_average_degree(graph),
            "entity_type_distribution": self._get_entity_type_distribution(graph),
            "relation_type_distribution": self._get_relation_type_distribution(graph)
        }
        
        return validation_results
    
    def _node_has_edges(self, node_id: str, edges: Dict[str, GraphEdge]) -> bool:
        """Check if node has any edges"""
        for edge in edges.values():
            if edge.source_id == node_id or edge.target_id == node_id:
                return True
        return False
    
    def _calculate_average_degree(self, graph: KnowledgeGraph) -> float:
        """Calculate average node degree"""
        if not graph.nodes:
            return 0.0
        
        degree_sum = 0
        for node_id in graph.nodes.keys():
            degree = sum(1 for edge in graph.edges.values() 
                        if edge.source_id == node_id or edge.target_id == node_id)
            degree_sum += degree
        
        return degree_sum / len(graph.nodes)
    
    def _get_entity_type_distribution(self, graph: KnowledgeGraph) -> Dict[str, int]:
        """Get distribution of entity types"""
        distribution = defaultdict(int)
        for node in graph.nodes.values():
            distribution[node.entity.entity_type.value] += 1
        return dict(distribution)
    
    def _get_relation_type_distribution(self, graph: KnowledgeGraph) -> Dict[str, int]:
        """Get distribution of relation types"""
        distribution = defaultdict(int)
        for edge in graph.edges.values():
            distribution[edge.relation.relation_type.value] += 1
        return dict(distribution)
    
    def export_graph_to_dict(self, graph: KnowledgeGraph) -> Dict[str, Any]:
        """Export graph to dictionary format"""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "entity": {
                        "text": node.entity.text,
                        "type": node.entity.entity_type.value,
                        "canonical_form": node.entity.canonical_form,
                        "aliases": node.entity.aliases,
                        "confidence": node.entity.confidence
                    },
                    "attributes": {
                        name: {
                            "value": attr.value,
                            "type": attr.attribute_type.value,
                            "confidence": attr.confidence
                        }
                        for name, attr in node.attributes.items()
                    },
                    "metadata": node.metadata
                }
                for node in graph.nodes.values()
            ],
            "edges": [
                {
                    "id": edge.id,
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relation": {
                        "type": edge.relation.relation_type.value,
                        "predicate": edge.relation.predicate,
                        "confidence": edge.relation.confidence,
                        "context": edge.relation.context
                    },
                    "weight": edge.weight,
                    "metadata": edge.metadata
                }
                for edge in graph.edges.values()
            ],
            "metadata": graph.metadata,
            "created_at": graph.created_at
        }