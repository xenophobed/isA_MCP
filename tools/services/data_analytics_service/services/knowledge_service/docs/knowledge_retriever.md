# Knowledge Retriever - Hybrid Graph-Enhanced Retrieval System

## Overview

The `GraphRAGRetriever` (KnowledgeRetriever) provides sophisticated retrieval capabilities that combine vector similarity search with graph traversal for enhanced context gathering. This component is part of a separated architecture where retrieval and storage concerns are handled by different classes.

## Key Features

✅ **Multi-Modal Retrieval**: Search across entities, relations, documents, and attributes  
✅ **Vector Similarity**: Uses 1536-dimensional embeddings for semantic search  
✅ **Document Chunk Search**: Granular retrieval from document chunks with embeddings  
✅ **Attribute Search**: Search across entity attributes as separate nodes  
✅ **Graph Context**: Expands results with graph neighborhood information  
✅ **Multiple Strategies**: Entity-only, document-only, attribute-only, or combined retrieval  
✅ **Entity-Based Search**: Direct retrieval by known entity names  
✅ **Subgraph Extraction**: Extract connected subgraphs around entities  
✅ **Configurable Depth**: Control graph expansion and context depth  

## Architecture

```
Query Input → Embedding Generation → Multi-Modal Vector Search
                                            ↓
                                    [Entities] [Documents] [Attributes] [Relations]
                                            ↓
                                    Combined Semantic Results
                                            ↓
                                    Graph Context Expansion
                                            ↓
                                Enhanced Results with Context
```

## Core Components

### RetrievalResult
```python
@dataclass
class RetrievalResult:
    content: str                    # Formatted content for display
    score: float                    # Similarity/relevance score
    source_id: str                  # Original source identifier
    chunk_id: Optional[str]         # Optional chunk identifier
    entity_context: Dict[str, Any]  # Entity-specific context
    graph_context: Dict[str, Any]   # Graph neighborhood context
    metadata: Dict[str, Any]        # Additional metadata
```

### GraphRAGRetriever
Main retrieval class with multiple search strategies and context enhancement capabilities.

## Usage

### Multi-Modal Retrieval

```python
from knowledge_retriever import GraphRAGRetriever

retriever = GraphRAGRetriever(neo4j_client)

# Multi-modal retrieval across all node types
results = await retriever.retrieve(
    query="Apple products",
    top_k=10,
    similarity_threshold=0.7,
    include_graph_context=True,
    graph_expansion_depth=2,
    search_modes=["entities", "documents", "attributes", "relations"]  # All modes
)

for result in results:
    print(f"Content: {result.content}")
    print(f"Score: {result.score:.3f}")
    print(f"Connected entities: {len(result.graph_context.get('connected_entities', []))}")
```

### Document-Only Search

```python
# Search only in document chunks
results = await retriever.search_documents(
    query="Apple founding story",
    top_k=5,
    similarity_threshold=0.8
)

print(f"Found {len(results)} relevant document chunks")
```

### Attribute-Only Search

```python
# Search only in attribute nodes
results = await retriever.search_attributes(
    query="revenue financial",
    top_k=5,
    similarity_threshold=0.7
)

print(f"Found {len(results)} relevant attributes")
```

### Entity-Only Search

```python
# Search only entities (no graph expansion)
results = await retriever.search_entities_only(
    query="technology companies",
    top_k=10,
    similarity_threshold=0.8
)

print(f"Found {len(results)} matching entities")
```

### Semantic-Only Retrieval

```python
# Pure semantic similarity search
results = await retriever.retrieve(
    query="technology companies",
    include_graph_context=False,  # Disable graph expansion
    top_k=5,
    similarity_threshold=0.8
)

print(f"Found {len(results)} semantically similar entities")
```

### Entity-Based Retrieval

```python
# Start from known entities
results = await retriever.retrieve_by_entities(
    entity_names=["Apple Inc", "iPhone"],
    expansion_depth=3
)

for result in results:
    print(f"Entity: {result.entity_context['name']}")
    print(f"Type: {result.entity_context['type']}")
    print(f"Neighbors: {len(result.graph_context['connected_entities'])}")
```

### Subgraph Extraction

```python
# Extract connected subgraph
subgraph = await retriever.retrieve_subgraph(
    central_entities=["Apple Inc", "Google"],
    radius=2
)

print(f"Subgraph contains:")
print(f"  - Entities: {len(subgraph['entities'])}")
print(f"  - Neighbor relationships: {len(subgraph['neighbors'])}")
print(f"  - Connection paths: {len(subgraph['paths'])}")
```

## Retrieval Strategies

### 1. Semantic Similarity Search
```python
# Internal method used by retrieve()
semantic_results = await retriever._semantic_retrieval(
    query="technology company",
    embedding=query_embedding,
    limit=10,
    threshold=0.75
)
```

### 2. Graph Context Enhancement
```python
# Enhance semantic results with graph context
enhanced_results = await retriever._enhance_with_graph_context(
    semantic_results=semantic_results,
    depth=2
)
```

### 3. Entity Context Extraction
```python
# Get specific context for an entity
entity_context = await retriever._get_entity_specific_context(
    entity_name="Apple Inc",
    global_graph_context=graph_context
)
```

## Configuration Options

### Retrieval Parameters
```python
# Comprehensive retrieval configuration
results = await retriever.retrieve(
    query="Apple smartphone technology",
    query_embedding=None,              # Auto-generate if None
    top_k=15,                         # Number of results
    similarity_threshold=0.7,         # Minimum similarity score
    graph_expansion_depth=3,          # Graph traversal depth
    include_graph_context=True        # Enable/disable graph expansion
)
```

### Advanced Configuration
```python
config = {
    "max_results": 50,
    "similarity_threshold": 0.75,
    "graph_expansion_depth": 3,
    "context_window_size": 5,
    "embedding_model": "text-embedding-3-large"
}

retriever = GraphRAGRetriever(neo4j_client, config)
```

## Content Formatting

### Entity Content Format
The retriever formats entity information into readable content:

```
Entity: Apple Inc (Type: ORGANIZATION)
Properties: founded: 1976, revenue: 394300000000
Connected to: iPhone, iPad, MacBook, Tim Cook, Cupertino
```

### Graph Context Integration
```python
# Example of formatted content with graph context
def _format_content(self, entity: Dict, graph_context: Dict) -> str:
    content_parts = [
        f"Entity: {entity['name']} (Type: {entity['type']})",
        f"Connected to: {', '.join(graph_context['connected_entities'][:5])}"
    ]
    return "\n".join(content_parts)
```

## Performance Characteristics

- **Embedding Generation**: Batch processing for multiple queries
- **Vector Search**: O(log n) with proper Neo4j vector indices
- **Graph Traversal**: O(b^d) where b=branching factor, d=depth
- **Memory Usage**: Scales with result size and graph context depth
- **Concurrency**: Thread-safe for parallel retrieval operations

## Error Handling

```python
try:
    results = await retriever.retrieve("complex query")
except EmbeddingServiceError:
    # Handle embedding generation failures
    results = await retriever.retrieve_by_entities(["fallback_entity"])
except Neo4jConnectionError:
    # Handle database connection issues
    logger.error("Neo4j connection failed")
    results = []
```

### Graceful Degradation
```python
# Retriever handles failures gracefully
results = await retriever.retrieve("test query")

# If semantic search fails, returns empty list
# If graph expansion fails, returns semantic results only
# Individual entity failures don't stop the entire operation
```

## Integration with Storage

### Complete Workflow
```python
from neo4j_store import Neo4jStore
from knowledge_retriever import GraphRAGRetriever

# Separate storage and retrieval
async def store_and_retrieve_workflow(text: str, query: str):
    # 1. Storage phase
    store = Neo4jStore(neo4j_client)
    storage_result = await store.extract_and_store_from_text(
        text=text,
        source_id="doc_123"
    )
    
    # 2. Retrieval phase
    retriever = GraphRAGRetriever(neo4j_client)
    results = await retriever.retrieve(
        query=query,
        include_graph_context=True
    )
    
    return {
        "stored": storage_result,
        "retrieved": results
    }
```

## Testing

Comprehensive test coverage includes:

- ✅ Hybrid retrieval with semantic + graph context
- ✅ Pure semantic similarity search
- ✅ Entity-based retrieval strategies
- ✅ Graph context enhancement and expansion
- ✅ Subgraph extraction functionality
- ✅ Error handling and graceful degradation
- ✅ Content formatting and result creation
- ✅ Concurrent retrieval operations
- ✅ Large result set handling

Run tests:
```bash
pytest tools/services/data_analytics_service/services/knowledge_service/tests/test_knowledge_retriever.py -v
```

## Configuration Examples

### High-Precision Retrieval
```python
# For precise, high-quality results
results = await retriever.retrieve(
    query="specific technical query",
    top_k=5,
    similarity_threshold=0.9,        # High threshold
    graph_expansion_depth=1,         # Limited expansion
    include_graph_context=True
)
```

### Broad Context Retrieval
```python
# For comprehensive context gathering
results = await retriever.retrieve(
    query="general topic exploration",
    top_k=20,
    similarity_threshold=0.6,        # Lower threshold
    graph_expansion_depth=3,         # Deep expansion
    include_graph_context=True
)
```

### Fast Semantic Search
```python
# For quick semantic lookups
results = await retriever.retrieve(
    query="quick lookup",
    top_k=10,
    include_graph_context=False,     # Skip graph expansion
    similarity_threshold=0.75
)
```

## Limitations

- **Graph Complexity**: Deep graph traversals can be computationally expensive
- **Memory Usage**: Large graph contexts require significant memory
- **Neo4j Dependency**: Requires Neo4j 5.x with vector index support
- **Embedding Service**: Depends on external embedding generation service
- **Context Quality**: Graph context quality depends on stored relationship quality

## Future Enhancements

- [ ] Intelligent context pruning for large graphs
- [ ] Multi-hop reasoning with weighted paths
- [ ] Personalized retrieval based on user preferences
- [ ] Real-time result ranking optimization
- [ ] Caching strategies for frequent queries
- [ ] Advanced relevance scoring algorithms
- [ ] Support for temporal and versioned graphs