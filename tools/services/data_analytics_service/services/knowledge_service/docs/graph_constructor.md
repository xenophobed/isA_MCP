# GraphConstructor - Knowledge Graph Builder with Embeddings

## Overview

The `GraphConstructor` is a core component of the knowledge service that constructs semantic knowledge graphs from extracted entities, relations, and attributes. It integrates with the embedding generation service to create vector-enhanced graphs suitable for hybrid retrieval.

## Key Features

 **Embedding Integration**: Generates 1536-dimensional embeddings for entities, relations, documents, and attributes  
 **Graph Construction**: Creates structured knowledge graphs with nodes, edges, document chunks, and attribute nodes  
 **Document Chunking**: Automatically chunks large documents with embeddings for granular retrieval  
 **Attribute Nodes**: Creates separate nodes for entity attributes with embeddings  
 **Optimization**: Merges duplicate entities and removes redundant relationships  
 **Validation**: Comprehensive graph structure and content validation  
 **Export Formats**: Neo4j-ready format with four node types and general dictionary export  
 **Statistics**: Detailed graph analytics and distribution metrics  

## Architecture

```
Input: Entities + Relations + Attributes
    �
Embedding Generation (1536-dim vectors)
    �
Graph Construction (Nodes + Edges)
    �
Optimization (Merge + Deduplicate)
    �
Output: KnowledgeGraph with Embeddings
```

## Core Classes

### GraphNode
```python
@dataclass
class GraphNode:
    id: str                          # Unique node identifier
    entity: Entity                   # Source entity
    attributes: Dict[str, Attribute] # Entity attributes
    embedding: List[float]           # 1536-dim embedding vector
    node_type: str = "entity"
    metadata: Dict[str, Any] = None
```

### GraphEdge
```python
@dataclass
class GraphEdge:
    id: str                     # Unique edge identifier
    source_id: str             # Source node ID
    target_id: str             # Target node ID
    relation: Relation         # Source relation
    embedding: List[float]     # 1536-dim embedding vector
    edge_type: str = "relation"
    weight: float = 1.0
    metadata: Dict[str, Any] = None
```

### KnowledgeGraph
```python
@dataclass
class KnowledgeGraph:
    nodes: Dict[str, GraphNode]              # All entity nodes
    edges: Dict[str, GraphEdge]              # All relation edges
    document_chunks: Dict[str, DocumentChunk] # Document chunks with embeddings
    attribute_nodes: Dict[str, AttributeNode] # Attribute nodes with embeddings
    metadata: Dict[str, Any]                 # Graph metadata
    created_at: str                         # Creation timestamp
```

### DocumentChunk
```python
@dataclass
class DocumentChunk:
    id: str                      # Unique chunk identifier
    text: str                    # Chunk text content
    chunk_index: int             # Index within source document
    source_document: str         # Source document ID
    embedding: List[float]       # 1536-dim embedding vector
    metadata: Dict[str, Any] = None
```

### AttributeNode
```python
@dataclass
class AttributeNode:
    id: str                      # Unique attribute identifier
    entity_id: str               # Associated entity ID
    name: str                    # Attribute name
    value: str                   # Attribute value
    attribute_type: str          # Attribute type (TEMPORAL, NUMERICAL, etc.)
    confidence: float            # Confidence score
    embedding: List[float]       # 1536-dim embedding vector
    metadata: Dict[str, Any] = None
```

## Usage

### Basic Graph Construction

```python
from graph_constructor import GraphConstructor

constructor = GraphConstructor()

# Construct graph with embeddings
graph = await constructor.construct_graph(
    entities=extracted_entities,
    relations=extracted_relations,
    entity_attributes=entity_attributes,
    source_text="Original text content"
)

print(f"Created graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
```

### Graph Optimization

```python
# Optimize graph structure
optimized_graph = constructor.optimize_graph(graph)

print(f"Optimization results:")
print(f"Nodes: {optimized_graph.metadata['nodes_before_merge']} � {optimized_graph.metadata['nodes_after_merge']}")
print(f"Edges: {optimized_graph.metadata['edges_before_filter']} � {optimized_graph.metadata['edges_after_filter']}")
```

### Graph Validation

```python
# Validate graph structure
validation = constructor.validate_graph(graph)

if validation["valid"]:
    print("Graph is valid!")
    print(f"Statistics: {validation['statistics']}")
else:
    print(f"Validation errors: {validation['errors']}")
```

### Neo4j Export

```python
# Export for Neo4j storage
neo4j_data = constructor.export_for_neo4j_storage(graph)

# Data includes entities and relations with embeddings
print(f"Entities: {len(neo4j_data['entities'])}")
print(f"Relations: {len(neo4j_data['relations'])}")

# Each entity has embedding for vector search
entity = neo4j_data['entities'][0]
print(f"Entity embedding dimensions: {len(entity['embedding'])}")
```

## Embedding Integration

### Entity Text Creation
```python
def _create_entity_text(self, entity: Entity, attributes: Dict[str, Attribute]) -> str:
    text_parts = [entity.canonical_form, entity.entity_type.value]
    
    # Add high-confidence attributes
    for attr_name, attr in attributes.items():
        if attr.confidence > 0.8:
            text_parts.append(f"{attr_name}:{attr.normalized_value}")
    
    return " ".join(text_parts)
```

### Relation Text Creation
```python
def _create_relation_text(self, relation: Relation) -> str:
    text = f"{relation.subject.text} {relation.predicate} {relation.object.text}"
    if relation.context:
        text += f" context: {relation.context}"
    return text
```

## Graph Statistics

The constructor provides comprehensive analytics:

```python
# Entity type distribution
entity_dist = constructor._get_entity_type_distribution(graph)
# {"ORGANIZATION": 5, "PRODUCT": 3, "PERSON": 2}

# Relation type distribution  
relation_dist = constructor._get_relation_type_distribution(graph)
# {"CREATES": 4, "OWNS": 2, "LOCATED_IN": 1}

# Average node degree
avg_degree = constructor._calculate_average_degree(graph)
# 2.3 (average connections per node)
```

## Configuration

```python
config = {
    "merge_similar_entities": True,
    "confidence_threshold": 0.8,
    "max_aliases_per_entity": 10,
    "embedding_model": "text-embedding-3-large"
}

constructor = GraphConstructor(config)
```

## Performance Characteristics

- **Embedding Generation**: Batch processing for efficiency
- **Memory Usage**: Optimized for large graphs (10K+ nodes)
- **Concurrency**: Thread-safe for parallel construction
- **Validation**: O(V + E) complexity for graph validation

## Error Handling

```python
try:
    graph = await constructor.construct_graph(entities, relations, attributes)
except EmbeddingServiceError:
    # Handle embedding generation failures
    pass
except ValidationError:
    # Handle graph validation errors
    pass
```

## Integration with Knowledge Service

```python
# Complete workflow
from knowledge_service import KnowledgeService

service = KnowledgeService()

# 1. Extract entities/relations
entities, relations, attributes = await service.extract_knowledge(text)

# 2. Construct graph with embeddings
constructor = GraphConstructor()
graph = await constructor.construct_graph(entities, relations, attributes, text)

# 3. Store in Neo4j
storage_data = constructor.export_for_neo4j_storage(graph)
await service.store_graph(storage_data)
```

## Testing

Comprehensive test coverage includes:

-  Graph construction with embeddings
-  Entity and relation text creation
-  Node/edge ID generation and uniqueness
-  Graph optimization and merging
-  Validation and error handling
-  Export format compatibility
-  Concurrent operations
-  Performance benchmarks

Run tests with:
```bash
pytest tools/services/data_analytics_service/services/knowledge_service/tests/test_graph_constructor.py -v
```

## Limitations

- Requires embedding service availability
- Memory usage scales with graph size
- Optimization is compute-intensive for large graphs
- Real-time updates not supported (batch processing)

## Future Enhancements

- [ ] Incremental graph updates
- [ ] Multi-language embedding support
- [ ] Custom embedding models
- [ ] Graph streaming for large datasets
- [ ] Real-time optimization