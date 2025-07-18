# Neo4j Store - Vector-Enhanced Graph Storage

## Overview

The `Neo4jStore` provides focused graph storage capabilities with integrated vector embeddings. It handles storing entities, relations, and complete graphs with 1536-dimensional embeddings for semantic search. This component is part of a separated architecture where storage and retrieval concerns are handled by different classes.

## Key Features

 **Vector Storage**: Stores 1536-dimensional embeddings with entities and relations  
 **Graph Construction Integration**: Works with GraphConstructor for complete workflows  
 **Batch Operations**: Efficient bulk storage operations  
 **Error Recovery**: Graceful handling of partial storage failures  
 **Text Processing**: Extract and store from raw text using GraphConstructor  
 **Storage Focus**: Dedicated to storage operations only (retrieval handled by KnowledgeRetriever)

## Architecture

```
Text Input � GraphConstructor � KnowledgeGraph with Embeddings
                                  �
                            Neo4jStore � Vector Index + Graph Structure
                                  �
                         Stored Knowledge Graph

Retrieval: Query � KnowledgeRetriever � Neo4j Vector Search + Graph Traversal
```

## Core Components

### Vector Indexes
- **Entity Embeddings**: 1536-dimensional vectors for semantic entity search
- **Relation Embeddings**: 1536-dimensional vectors for relationship similarity
- **Cosine Similarity**: Optimized similarity function for text embeddings

### Graph Structure
- **Entities**: Nodes with properties, types, and embeddings
- **Relations**: Edges with predicates, confidence, and embeddings
- **Metadata**: Comprehensive tracking and provenance

## Usage

### Initialization

```python
from neo4j_store import Neo4jStore
from neo4j_client import Neo4jClient

# Initialize store
neo4j_client = Neo4jClient()
store = Neo4jStore(neo4j_client)
```

### Storing Knowledge Graphs

```python
# Store complete knowledge graph with embeddings
graph_data = {
    "entities": [
        {
            "id": "org_apple_1",
            "name": "Apple Inc",
            "type": "ORGANIZATION", 
            "canonical_form": "Apple Inc",
            "confidence": 0.95,
            "embedding": [0.1] * 1536,  # Vector for similarity search
            "attributes": {
                "founded": {"value": "1976", "type": "TEMPORAL", "confidence": 0.95}
            }
        }
    ],
    "relations": [
        {
            "id": "creates_1",
            "source_id": "org_apple_1",
            "target_id": "prod_iphone_1",
            "type": "CREATES",
            "predicate": "manufactures",
            "confidence": 0.85,
            "embedding": [0.2] * 1536,  # Vector for relation similarity
            "context": "Apple Inc manufactures iPhone"
        }
    ]
}

# Store with comprehensive statistics
storage_result = await store.store_knowledge_graph(graph_data)
print(f"Stored {storage_result['entities_stored']} entities and {storage_result['relations_stored']} relations")
```

### Text Processing and Storage

```python
# Extract knowledge from text and store
result = await store.extract_and_store_from_text(
    text="Apple Inc manufactures iPhone smartphones since 2007",
    source_id="doc_123",
    chunk_id="chunk_1"
)

print(f"Stored {result['entities_stored']} entities")
print(f"Stored {result['relations_stored']} relations")
print(f"Text length: {result['text_length']} characters")
```

### Direct Graph Storage

```python
# Store pre-constructed graph data
from graph_constructor import GraphConstructor

constructor = GraphConstructor()
graph = await constructor.construct_graph(entities, relations, attributes, text)
neo4j_data = constructor.export_for_neo4j_storage(graph)

storage_result = await store.store_knowledge_graph(neo4j_data)
print(f"Stored {storage_result['entities_stored']}/{storage_result['total_entities']} entities")
```

## Storage Architecture

### Storage vs Retrieval Separation
```python
# Storage: Neo4jStore handles all storage operations
from neo4j_store import Neo4jStore
store = Neo4jStore(neo4j_client)

# Retrieval: KnowledgeRetriever handles all search operations
from knowledge_retriever import GraphRAGRetriever
retriever = GraphRAGRetriever(neo4j_client)

# Store knowledge
storage_result = await store.store_knowledge_graph(graph_data)

# Retrieve knowledge
results = await retriever.retrieve(query="Apple products")
```

## Integration with GraphConstructor

### Complete Workflow
```python
# End-to-end workflow: Text -> Knowledge Graph -> Storage
async def process_and_store_text(text: str, source_id: str):
    # Use Neo4jStore's integrated text processing
    result = await store.extract_and_store_from_text(
        text=text,
        source_id=source_id
    )
    
    return {
        "entities_stored": result["entities_stored"],
        "relations_stored": result["relations_stored"],
        "source_id": result["source_id"]
    }

# Alternative: Manual graph construction
async def manual_graph_storage(entities, relations, attributes, text):
    # 1. Construct graph with embeddings
    constructor = GraphConstructor()
    graph = await constructor.construct_graph(entities, relations, attributes, text)
    
    # 2. Export for storage
    storage_data = constructor.export_for_neo4j_storage(graph)
    
    # 3. Store in Neo4j
    result = await store.store_knowledge_graph(storage_data)
    return result
```

## Error Handling

### Graceful Degradation
```python
try:
    results = await store.semantic_search("query")
except Exception as e:
    logger.error(f"Semantic search failed: {e}")
    # Falls back to empty results, continues operation
    results = []
```

### Partial Storage Failures
```python
# Storage continues despite individual failures
storage_result = await store.store_knowledge_graph(graph_data)

if storage_result["entities_stored"] < storage_result["total_entities"]:
    logger.warning(f"Only stored {storage_result['entities_stored']}/{storage_result['total_entities']} entities")
```

## Performance Optimization

### Batch Operations
```python
# Efficient batch storage
entities = [entity1, entity2, entity3, ...]
relations = [relation1, relation2, relation3, ...]

# Single transaction for all entities and relations
graph_data = {"entities": entities, "relations": relations}
result = await store.store_knowledge_graph(graph_data)
```

### Concurrent Search
```python
import asyncio

# Parallel search operations
queries = ["Apple products", "technology companies", "smartphone manufacturers"]
tasks = [store.semantic_search(query) for query in queries]
results = await asyncio.gather(*tasks)
```

## Configuration

### Vector Index Settings
```cypher
-- Entity embedding index (1536 dimensions)
CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
FOR (n:Entity) ON (n.embedding)
OPTIONS {
    indexConfig: {
        `vector.dimensions`: 1536,
        `vector.similarity_function`: 'cosine'
    }
}

-- Relation embedding index
CREATE VECTOR INDEX relation_embeddings IF NOT EXISTS  
FOR ()-[r:RELATES_TO]-() ON (r.embedding)
OPTIONS {
    indexConfig: {
        `vector.dimensions`: 1536,
        `vector.similarity_function`: 'cosine'
    }
}
```

### Store Configuration
```python
# Neo4jStore focuses on storage configuration
config = {
    "batch_size": 100,
    "storage_timeout_seconds": 30,
    "max_retries": 3
}

store = Neo4jStore(neo4j_client)
# Configuration handled by Neo4jClient and GraphConstructor
```

## Storage Statistics

```python
# Comprehensive storage analytics
stats = await neo4j_client.get_graph_statistics()
print(f"Total nodes: {stats['total_nodes']}")
print(f"Total edges: {stats['total_edges']}")
print(f"Entity types: {stats['entity_types']}")
print(f"Relation types: {stats['relation_types']}")
print(f"Avg node confidence: {stats['avg_node_confidence']:.3f}")
print(f"Avg edge confidence: {stats['avg_edge_confidence']:.3f}")
```

## Integration Patterns

### Complete Workflow
```python
# End-to-end knowledge storage and retrieval with separated concerns
async def store_and_retrieve_knowledge(text: str, query: str):
    # 1. Storage: Use Neo4jStore for all storage operations
    store = Neo4jStore(neo4j_client)
    storage_result = await store.extract_and_store_from_text(
        text=text,
        source_id="doc_123"
    )
    
    # 2. Retrieval: Use KnowledgeRetriever for all search operations
    retriever = GraphRAGRetriever(neo4j_client)
    results = await retriever.retrieve(
        query=query,
        include_graph_context=True,
        graph_expansion_depth=2
    )
    
    return {
        "storage": storage_result,
        "retrieval": results
    }
```

## Testing

Test coverage includes:

-  Knowledge graph storage operations
-  Text processing and extraction
-  Batch storage operations
-  Error handling and recovery
-  Concurrent storage operations
-  Large graph data handling
-  GraphConstructor integration
-  Embedding storage verification

Run tests:
```bash
pytest tools/services/data_analytics_service/services/knowledge_service/tests/test_neo4j_store.py -v
```

## Limitations

- **Neo4j Version**: Requires Neo4j 5.x with vector support
- **Memory Usage**: Large embeddings require significant RAM
- **Storage Only**: No retrieval capabilities (use KnowledgeRetriever for search)
- **Dependency**: Requires GraphConstructor for text processing
- **Index Maintenance**: Vector indexes require periodic optimization

## Troubleshooting

### Vector Index Issues
```cypher
-- Check vector index status
SHOW INDEXES YIELD name, state, populationPercent 
WHERE name CONTAINS 'embedding'
```

### Performance Tuning
```cypher
-- Monitor query performance
PROFILE MATCH (n:Entity) 
CALL db.index.vector.queryNodes('entity_embeddings', 10, $embedding) 
YIELD node, score 
RETURN node, score
```

### Memory Optimization
```python
# Optimize for large graphs
config = {
    "connection_pool_size": 20,
    "connection_timeout": 60,
    "batch_size": 50  # Smaller batches for memory-constrained environments
}
```

## Future Enhancements

- [ ] Streaming storage for real-time graphs
- [ ] Distributed storage across clusters
- [ ] Incremental updates and versioning
- [ ] Storage analytics and monitoring
- [ ] Advanced batch optimization strategies