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

import logging
from tools.base_service import BaseService
from .entity_extractor import Entity, EntityType
from .relation_extractor import Relation, RelationType
from .attribute_extractor import Attribute, AttributeType
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator

logger = logging.getLogger(__name__)

@dataclass
class GraphNode:
    """Graph node representing an entity"""
    id: str
    entity: Entity
    attributes: Dict[str, Attribute]
    embedding: List[float]  # NEW: 1536-dim embedding
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
    embedding: List[float]  # NEW: 1536-dim embedding
    edge_type: str = "relation"
    weight: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class DocumentChunk:
    """Document chunk with embedding"""
    id: str
    text: str
    chunk_index: int
    source_document: str
    embedding: List[float]  # 1536-dim embedding
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class AttributeNode:
    """Attribute as separate node with embedding"""
    id: str
    entity_id: str
    name: str
    value: str
    attribute_type: str
    confidence: float
    embedding: List[float]  # 1536-dim embedding
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class KnowledgeGraph:
    """Knowledge graph data structure with document chunks and attribute nodes"""
    nodes: Dict[str, GraphNode]
    edges: Dict[str, GraphEdge]
    document_chunks: Dict[str, DocumentChunk]  # NEW
    attribute_nodes: Dict[str, AttributeNode]  # NEW
    metadata: Dict[str, Any]
    created_at: str
    
    def __post_init__(self):
        if not hasattr(self, 'created_at'):
            self.created_at = datetime.now().isoformat()

class GraphConstructor(BaseService):
    """Construct knowledge graphs from extracted information"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize graph constructor
        
        Args:
            config: Configuration dict with constructor settings
        """
        super().__init__("GraphConstructor")
        self.config = config or {}
        self.node_id_counter = 0
        self.edge_id_counter = 0
        self.embedding_generator = EmbeddingGenerator()  # NEW
        
        logger.info("GraphConstructor initialized")
    
    async def construct_graph(self, 
                       entities: List[Entity],
                       relations: List[Relation],
                       entity_attributes: Dict[str, Dict[str, Attribute]],
                       source_text: str = "",
                       source_id: str = "",
                       chunk_size: int = 1000,
                       chunk_overlap: int = 200) -> KnowledgeGraph:
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
        
        # Generate embeddings for entities
        entity_texts = []
        for entity in entities:
            attributes = entity_attributes.get(entity.text, {})
            entity_text = self._create_entity_text(entity, attributes)
            entity_texts.append(entity_text)

        # Batch generate embeddings with explicit model
        entity_embeddings = await self.embedding_generator.embed_batch(entity_texts, model="text-embedding-3-small")

        # Create nodes from entities with embeddings
        entity_to_node_id = {}
        for i, entity in enumerate(entities):
            node_id = self._generate_node_id(entity)
            entity_to_node_id[entity.text] = node_id
            
            # Get attributes for this entity
            attributes = entity_attributes.get(entity.text, {})
            
            node = GraphNode(
                id=node_id,
                entity=entity,
                attributes=attributes,
                embedding=entity_embeddings[i],  # NEW
                metadata={
                    "entity_type": entity.entity_type.value,
                    "confidence": entity.confidence,
                    "canonical_form": entity.canonical_form,
                    "aliases": entity.aliases
                }
            )
            nodes[node_id] = node
        
        # Generate embeddings for relations
        relation_texts = []
        for relation in relations:
            relation_text = self._create_relation_text(relation)
            relation_texts.append(relation_text)

        relation_embeddings = await self.embedding_generator.embed_batch(relation_texts, model="text-embedding-3-small")

        # Create edges from relations with embeddings
        for i, relation in enumerate(relations):
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
                    embedding=relation_embeddings[i],  # NEW
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
        
        # Create document chunks with embeddings if source text provided
        document_chunks = {}
        if source_text and len(source_text) > chunk_size:
            chunks_data = await self.embedding_generator.chunk_text(
                text=source_text,
                chunk_size=chunk_size,
                overlap=chunk_overlap,
                metadata={"source_id": source_id},
                model="text-embedding-3-small"
            )
            
            for i, chunk_data in enumerate(chunks_data):
                chunk_id = f"{source_id}_chunk_{i}" if source_id else f"chunk_{i}"
                document_chunk = DocumentChunk(
                    id=chunk_id,
                    text=chunk_data["text"],
                    chunk_index=i,
                    source_document=source_id or "unknown",
                    embedding=chunk_data["embedding"],
                    metadata=chunk_data.get("metadata", {})
                )
                document_chunks[chunk_id] = document_chunk
        
        # Create attribute nodes with embeddings (CONCURRENT BATCH PROCESSING)
        attribute_nodes = {}
        
        # Collect all attribute texts for batch embedding generation
        attr_texts = []
        attr_metadata = []
        
        for entity_text, attributes in entity_attributes.items():
            entity_id = entity_to_node_id.get(entity_text)
            if entity_id:
                for attr_name, attribute in attributes.items():
                    # Prepare attribute text for embedding
                    attr_text = f"{attr_name}: {attribute.normalized_value} (type: {attribute.attribute_type.value})"
                    attr_texts.append(attr_text)
                    
                    # Store metadata for later node creation
                    attr_id = f"attr_{entity_id}_{attr_name}"
                    attr_metadata.append({
                        'attr_id': attr_id,
                        'entity_id': entity_id,
                        'attr_name': attr_name,
                        'attribute': attribute
                    })
        
        # Batch generate embeddings for all attributes at once (CONCURRENT)
        if attr_texts:
            logger.info(f"Generating embeddings for {len(attr_texts)} attributes concurrently...")
            attr_embeddings = await self.embedding_generator.embed_batch(attr_texts, model="text-embedding-3-small")
            
            # Create attribute nodes with embeddings
            for i, metadata in enumerate(attr_metadata):
                attribute_node = AttributeNode(
                    id=metadata['attr_id'],
                    entity_id=metadata['entity_id'],
                    name=metadata['attr_name'],
                    value=metadata['attribute'].normalized_value,
                    attribute_type=metadata['attribute'].attribute_type.value,
                    confidence=metadata['attribute'].confidence,
                    embedding=attr_embeddings[i],
                    metadata={
                        "source_text": metadata['attribute'].source_text,
                        "original_value": metadata['attribute'].value
                    }
                )
                attribute_nodes[metadata['attr_id']] = attribute_node
            
            logger.info(f"Created {len(attribute_nodes)} attribute nodes with concurrent embeddings")
        
        # Create graph metadata
        metadata = {
            "source_text_length": len(source_text),
            "entities_count": len(entities),
            "relations_count": len(relations),
            "attributes_count": sum(len(attrs) for attrs in entity_attributes.values()),
            "document_chunks_count": len(document_chunks),  # NEW
            "attribute_nodes_count": len(attribute_nodes),  # NEW
            "entity_types": list(set(e.entity_type.value for e in entities)),
            "relation_types": list(set(r.relation_type.value for r in relations)),
            "source_id": source_id,  # NEW
            "construction_config": self.config
        }
        
        graph = KnowledgeGraph(
            nodes=nodes,
            edges=edges,
            document_chunks=document_chunks,  # NEW
            attribute_nodes=attribute_nodes,  # NEW
            metadata=metadata,
            created_at=datetime.now().isoformat()
        )
        
        logger.info(f"Constructed knowledge graph: {len(nodes)} nodes, {len(edges)} edges, {len(document_chunks)} chunks, {len(attribute_nodes)} attributes")
        return graph
    
    async def construct_from_text(self, 
                                text: str, 
                                source_metadata: Dict[str, Any] = None) -> KnowledgeGraph:
        """Construct knowledge graph directly from text using optimized unified extraction
        
        Args:
            text: Source text to process
            source_metadata: Metadata including source_id, chunk_id, etc.
            
        Returns:
            Complete knowledge graph with entities, relations, attributes, and document chunks
        """
        metadata = source_metadata or {}
        source_id = metadata.get("source_id", "unknown")
        
        # Check if we should use fast unified extraction
        use_unified = len(text) > 1500  # Use unified for most texts (lowered threshold)
        
        if use_unified:
            logger.info(f"Using Dask-optimized unified extraction for large text ({len(text)} chars)")
            
            # Use Dask-optimized unified extractor
            from .dask_unified_extractor import dask_unified_extractor
            
            # Initialize Dask if not already done
            if not dask_unified_extractor.dask_client:
                await dask_unified_extractor.initialize_dask(workers=4, threads_per_worker=2)
            
            # Extract everything in parallel chunks
            unified_result = await dask_unified_extractor.extract_knowledge_parallel(
                text=text,
                domain=metadata.get('domain', 'general'),
                confidence_threshold=0.7,
                max_workers=4
            )
            
            if not unified_result.success:
                logger.warning(f"Unified extraction failed: {unified_result.error}, falling back to sequential")
                # Fall back to sequential processing
                return await self._construct_from_text_sequential(text, source_metadata)
            
            logger.info(f"✅ Unified extraction completed: {len(unified_result.entities)} entities, "
                       f"{len(unified_result.relationships)} relationships, "
                       f"{len(unified_result.attributes)} attributed entities in {unified_result.processing_time:.3f}s")
            
            # Convert unified results to our format
            entities = []
            relations = []
            entity_attributes = {}
            
            # Convert entities
            from .entity_extractor import Entity, EntityType
            for entity_data in unified_result.entities:
                try:
                    entity_type = EntityType(entity_data.get('type', 'CONCEPT'))
                except ValueError:
                    entity_type = EntityType.CONCEPT
                
                entity = Entity(
                    text=entity_data.get('name', ''),
                    entity_type=entity_type,
                    start=0,  # Unified extraction doesn't track positions
                    end=len(entity_data.get('name', '')),
                    confidence=entity_data.get('confidence', 0.8)
                )
                entities.append(entity)
            
            # Convert relationships
            from .relation_extractor import Relation, RelationType
            for rel_data in unified_result.relationships:
                try:
                    # Find subject and object entities
                    subject_entity = None
                    object_entity = None
                    
                    for entity in entities:
                        if entity.text.lower() == rel_data.get('subject', '').lower():
                            subject_entity = entity
                        if entity.text.lower() == rel_data.get('object', '').lower():
                            object_entity = entity
                    
                    if subject_entity and object_entity:
                        relation = Relation(
                            subject=subject_entity,
                            predicate=rel_data.get('predicate', ''),
                            object=object_entity,
                            relation_type=RelationType.SEMANTIC,  # Default type
                            confidence=rel_data.get('confidence', 0.8)
                        )
                        relations.append(relation)
                except Exception as e:
                    logger.warning(f"Failed to convert relationship: {e}")
            
            # Convert attributes
            from .attribute_extractor import Attribute, AttributeType
            for entity_name, attrs in unified_result.attributes.items():
                entity_attrs = {}
                for attr_name, attr_data in attrs.items():
                    if isinstance(attr_data, dict):
                        attribute = Attribute(
                            name=attr_name,
                            value=attr_data.get('value', ''),
                            attribute_type=AttributeType.TEXT,  # Default type
                            confidence=attr_data.get('confidence', 0.8),
                            source_text=attr_data.get('source', ''),
                            normalized_value=attr_data.get('value', '')
                        )
                        entity_attrs[attr_name] = attribute
                
                if entity_attrs:
                    entity_attributes[entity_name] = entity_attrs
            
            logger.info(f"Converted unified results: {len(entities)} entities, {len(relations)} relations, {len(entity_attributes)} attributed entities")
            
        else:
            logger.info(f"Using sequential extraction for small text ({len(text)} chars)")
            return await self._construct_from_text_sequential(text, source_metadata)
        
        # Construct complete graph
        return await self.construct_graph(
            entities=entities,
            relations=relations,
            entity_attributes=entity_attributes,
            source_text=text,
            source_id=source_id
        )
    
    async def _construct_from_text_sequential(self, 
                                            text: str, 
                                            source_metadata: Dict[str, Any] = None) -> KnowledgeGraph:
        """Sequential extraction for smaller texts (fallback method)"""
        metadata = source_metadata or {}
        source_id = metadata.get("source_id", "unknown")
        
        # Import extraction services
        from .entity_extractor import EntityExtractor
        from .relation_extractor import RelationExtractor  
        from .attribute_extractor import AttributeExtractor
        
        # Initialize extractors
        entity_extractor = EntityExtractor()
        relation_extractor = RelationExtractor()
        attribute_extractor = AttributeExtractor()
        
        # Extract entities first (required for relations)
        entities = await entity_extractor.extract_entities(text)
        logger.info(f"Extracted {len(entities)} entities from text")
        
        # Extract relations (depends on entities, so cannot be fully concurrent)
        relations = await relation_extractor.extract_relations(text, entities)
        logger.info(f"Extracted {len(relations)} relations from text")
        
        # Extract attributes (CONCURRENT PROCESSING)
        entity_attributes = {}
        
        # Create concurrent tasks for attribute extraction
        if entities:
            logger.info(f"Starting concurrent attribute extraction for {len(entities)} entities...")
            
            # Create tasks for all entities concurrently
            async def extract_attributes_for_entity(entity):
                try:
                    attributes = await attribute_extractor.extract_attributes(text, entity)
                    return entity.text, attributes
                except Exception as e:
                    logger.warning(f"Attribute extraction failed for {entity.text}: {e}")
                    return entity.text, {}
            
            # Run all attribute extractions concurrently
            import asyncio
            tasks = [extract_attributes_for_entity(entity) for entity in entities]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            for result in results:
                if isinstance(result, tuple):
                    entity_text, attributes = result
                    if attributes:
                        entity_attributes[entity_text] = attributes
                else:
                    logger.warning(f"Attribute extraction task failed: {result}")
            
            logger.info(f"Concurrent attribute extraction completed for {len(entity_attributes)} entities")
        
        total_attrs = sum(len(attrs) for attrs in entity_attributes.values())
        logger.info(f"Extracted {total_attrs} attributes for {len(entity_attributes)} entities")
        
        # Construct complete graph
        return await self.construct_graph(
            entities=entities,
            relations=relations,
            entity_attributes=entity_attributes,
            source_text=text,
            source_id=source_id
        )
    
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
    
    def _create_entity_text(self, entity: Entity, attributes: Dict[str, Attribute]) -> str:
        """Create text representation for entity embedding"""
        text_parts = [entity.canonical_form, entity.entity_type.value]

        # Add key attributes
        for attr_name, attr in attributes.items():
            if attr.confidence > 0.8:  # Only high-confidence attributes
                text_parts.append(f"{attr_name}:{attr.normalized_value}")

        return " ".join(text_parts)

    def _create_relation_text(self, relation: Relation) -> str:
        """Create text representation for relation embedding"""
        text = f"{relation.subject.text} {relation.predicate} {relation.object.text}"
        if relation.context:
            text += f" context: {relation.context}"
        return text
    
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
            document_chunks=graph.document_chunks,  # Preserve document chunks
            attribute_nodes=graph.attribute_nodes,  # Preserve attribute nodes
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
    
    def export_for_neo4j_storage(self, graph: KnowledgeGraph) -> Dict[str, Any]:
        """Export graph in Neo4j-ready format with embeddings (entities, relations, documents, attributes)"""
        return {
            "entities": [
                {
                    "id": node.id,
                    "name": node.entity.text,
                    "type": node.entity.entity_type.value,
                    "canonical_form": node.entity.canonical_form,
                    "confidence": node.entity.confidence,
                    "embedding": node.embedding,  # For vector index
                    "source_document": graph.metadata.get("source_id", ""),
                    # Flatten attributes to avoid nested objects
                    "start_pos": node.entity.start,
                    "end_pos": node.entity.end,
                    "aliases": node.entity.aliases,
                    # Don't include complex attributes object - handle separately
                } for node in graph.nodes.values()
            ],
            "relations": [
                {
                    "id": edge.id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "type": edge.relation.relation_type.value,
                    "predicate": edge.relation.predicate,
                    "confidence": edge.relation.confidence,
                    "embedding": edge.embedding,  # For vector index
                    "context": edge.relation.context
                } for edge in graph.edges.values()
            ],
            "documents": [  # NEW: Document chunks as separate nodes
                {
                    "id": chunk.id,
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                    "source_document": chunk.source_document,
                    "embedding": chunk.embedding  # For vector index
                } for chunk in graph.document_chunks.values()
            ],
            "attributes": [  # NEW: Attributes as separate nodes
                {
                    "id": attr.id,
                    "entity_id": attr.entity_id,
                    "name": attr.name,
                    "value": attr.value,
                    "type": attr.attribute_type,
                    "confidence": attr.confidence,
                    "embedding": attr.embedding  # For vector index
                } for attr in graph.attribute_nodes.values()
            ]
        }

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
                    "embedding": node.embedding,
                    "metadata": node.metadata
                }
                for node in graph.nodes.values()
            ],
            "document_chunks": [  # NEW
                {
                    "id": chunk.id,
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                    "source_document": chunk.source_document,
                    "embedding": chunk.embedding,
                    "metadata": chunk.metadata
                }
                for chunk in graph.document_chunks.values()
            ],
            "attribute_nodes": [  # NEW
                {
                    "id": attr.id,
                    "entity_id": attr.entity_id,
                    "name": attr.name,
                    "value": attr.value,
                    "type": attr.attribute_type,
                    "confidence": attr.confidence,
                    "embedding": attr.embedding,
                    "metadata": attr.metadata
                }
                for attr in graph.attribute_nodes.values()
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
                    "embedding": edge.embedding,
                    "metadata": edge.metadata
                }
                for edge in graph.edges.values()
            ],
            "metadata": graph.metadata,
            "created_at": graph.created_at
        }