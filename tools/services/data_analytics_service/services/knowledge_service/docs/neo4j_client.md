# Neo4j Client Documentation

## Overview

The Neo4j Client provides connectivity and operations for Neo4j Aura database with vector support. It handles graph storage, querying, and GraphRAG operations with user isolation and permission management.

## Key Features

- **Vector-enabled Neo4j connectivity** with automatic index creation
- **Knowledge graph storage** with user isolation
- **GraphRAG operations** including vector similarity search
- **Entity and relationship management** with embeddings
- **Document chunk storage** for large text processing
- **User permission-based access control**
- **Fallback mechanisms** when vector features are unavailable

## Class: Neo4jClient

### Initialization

```python
from tools.services.data_analytics_service.services.knowledge_service.neo4j_client import Neo4jClient

# Initialize with default config
client = Neo4jClient()

# Initialize with custom config
config = {
    'uri': 'bolt://localhost:7687',
    'username': 'neo4j',
    'password': 'password',
    'database': 'neo4j'
}
client = Neo4jClient(config)
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `uri` | str | `bolt://localhost:7687` | Neo4j connection URI |
| `username` | str | `neo4j` | Neo4j username |
| `password` | str | `password` | Neo4j password |
| `database` | str | `neo4j` | Neo4j database name |

## Core Methods

### Entity Operations

#### store_entity()
Store a single entity in Neo4j with optional embedding.

```python
result = await client.store_entity(
    name="John Doe",
    entity_type="PERSON",
    properties={"age": 30, "confidence": 0.95},
    embedding=[0.1, 0.2, 0.3, ...]
)
```

**Parameters:**
- `name` (str): Entity name/text
- `entity_type` (str): Type of entity (PERSON, ORGANIZATION, etc.)
- `properties` (Dict): Additional properties
- `embedding` (List[float], optional): Vector embedding

**Returns:** Dict with success status and entity data

#### get_entity()
Retrieve entity by name.

```python
entity = await client.get_entity("John Doe")
```

### Relationship Operations

#### store_relationship()
Store a relationship between entities with optional embedding.

```python
result = await client.store_relationship(
    source_entity="John Doe",
    target_entity="ACME Corp",
    relationship_type="WORKS_FOR",
    properties={"since": "2023", "role": "Engineer"},
    embedding=[0.4, 0.5, 0.6, ...]
)
```

**Parameters:**
- `source_entity` (str): Source entity name
- `target_entity` (str): Target entity name
- `relationship_type` (str): Type of relationship
- `properties` (Dict): Additional properties
- `embedding` (List[float], optional): Vector embedding

### Document Operations

#### store_document_chunk()
Store document chunk node with embedding for large text processing.

```python
result = await client.store_document_chunk(
    chunk_id="chunk_123",
    text="This is a document chunk...",
    properties={"page": 1, "source": "document.pdf"},
    embedding=[0.1, 0.2, 0.3, ...]
)
```

**Parameters:**
- `chunk_id` (str): Unique chunk identifier
- `text` (str): Document text content
- `properties` (Dict): Additional properties
- `embedding` (List[float]): Vector embedding

#### store_attribute_node()
Store attribute node linked to an entity.

```python
result = await client.store_attribute_node(
    attr_id="attr_123",
    entity_id="entity_456",
    name="age",
    value="30",
    properties={"type": "numeric"},
    embedding=[0.4, 0.5, 0.6, ...]
)
```

### Vector Search Operations

#### vector_similarity_search()
Perform vector similarity search on entity embeddings.

```python
results = await client.vector_similarity_search(
    embedding=[0.1, 0.2, 0.3, ...],
    limit=10,
    similarity_threshold=0.8
)
```

**Parameters:**
- `embedding` (List[float]): Query vector
- `limit` (int): Maximum results (default: 10)
- `similarity_threshold` (float): Minimum similarity score (default: 0.8)

**Returns:** List of entities with similarity scores

#### vector_similarity_search_relations()
Search for similar relationships using vector embeddings.

```python
results = await client.vector_similarity_search_relations(
    embedding=[0.1, 0.2, 0.3, ...],
    limit=10,
    similarity_threshold=0.7,
    index_name="relation_embeddings"
)
```

### Graph Operations

#### get_entity_neighbors()
Get neighboring entity names with configurable depth.

```python
neighbors = await client.get_entity_neighbors("John Doe", depth=2)
```

#### find_shortest_path()
Find shortest path between two entities.

```python
path = await client.find_shortest_path("John Doe", "ACME Corp")
# Returns: {"found": True, "length": 2, "nodes": ["John Doe", "Engineering", "ACME Corp"]}
```

#### get_graph_statistics()
Get comprehensive graph statistics.

```python
stats = await client.get_graph_statistics(graph_id="optional_graph_id")
```

**Returns:**
- `total_nodes`: Number of entities
- `total_edges`: Number of relationships  
- `entity_types`: List of entity types
- `relation_types`: List of relationship types
- `avg_node_confidence`: Average entity confidence
- `avg_edge_confidence`: Average relationship confidence

### User and Resource Management

#### get_user_resources()
Get all resources for a specific user.

```python
resources = await client.get_user_resources(user_id=123)
```

**Returns:**
- `entities`: Count of user's entities
- `documents`: Count of user's documents
- `total`: Total resource count

#### query_knowledge_graph()
Query knowledge graph with user permissions.

```python
results = await client.query_knowledge_graph(
    resource_id="resource_123",
    query="search_term",
    user_id=123
)
```

### Knowledge Graph Storage

#### store_knowledge_graph()
Store complete knowledge graph from GraphConstructor.

```python
graph_id = await client.store_knowledge_graph(
    graph_data={
        'nodes': [...],
        'edges': [...],
        'metadata': {...}
    },
    graph_id="optional_id"
)
```

### Query Operations

#### execute_query()
Execute custom Cypher queries.

```python
results = await client.execute_query(
    "MATCH (n:Person) RETURN n.name as name LIMIT $limit",
    parameters={"limit": 10}
)
```

## Vector Index Configuration

The client automatically creates vector indexes for GraphRAG support:

### Entity Embeddings Index
- **Name:** `entity_embeddings`
- **Dimensions:** 1536 (OpenAI embedding size)
- **Similarity Function:** Cosine
- **Target:** Entity nodes

### Relation Embeddings Index
- **Name:** `relation_embeddings`
- **Dimensions:** 1536
- **Similarity Function:** Cosine
- **Target:** RELATES_TO relationships

## Error Handling

### Connection Errors
- Graceful fallback when Neo4j is unavailable
- Runtime errors for operations without valid connection
- Automatic retry logic for transient failures

### Vector Search Fallback
When vector indexes are unavailable:
- Falls back to text-based search
- Returns results with default relevance scores
- Logs warnings for debugging

### User Isolation
- All operations respect user permissions
- Entities and documents tagged with user_id
- Query filtering by user ownership

## Usage Examples

### Basic Entity Creation and Search

```python
# Initialize client
client = Neo4jClient()

# Store entities
await client.store_entity(
    name="Ò3sâ§wË Ë",
    entity_type="MEDICAL_FACILITY",
    properties={"location": "Ò3", "type": "Ë Ë"}
)

# Search with vector similarity
results = await client.vector_similarity_search(
    embedding=query_embedding,
    limit=5,
    similarity_threshold=0.8
)
```

### Knowledge Graph Storage

```python
# Store complete knowledge graph
graph_data = {
    'nodes': [...],  # From GraphConstructor
    'edges': [...],  # From GraphConstructor  
    'metadata': {...}
}

graph_id = await client.store_knowledge_graph(graph_data)
```

### User Resource Management

```python
# Get user's resources
user_resources = await client.get_user_resources(user_id=123)

# Query with user permissions
results = await client.query_knowledge_graph(
    resource_id="resource_123",
    query=";ó¿Â",
    user_id=123
)
```

## Global Client Instance

Use the global client instance for application-wide access:

```python
from tools.services.data_analytics_service.services.knowledge_service.neo4j_client import get_neo4j_client

# Get global instance
client = await get_neo4j_client(config)
```

## Dependencies

- **neo4j**: Neo4j Python driver
- **core.logging**: Centralized logging
- **core.database.supabase_client**: User authentication
- **core.config**: Configuration management

## Integration with Graph Analytics Service

The Neo4j Client is the foundation for:

1. **PDF to Knowledge Graph**: Stores extracted entities and relationships
2. **GraphRAG Queries**: Enables vector-based retrieval
3. **User Isolation**: Ensures data security and permissions
4. **MCP Resources**: Provides persistent storage for registered resources

## Testing

Comprehensive test suite available at:
`tools/services/data_analytics_service/services/knowledge_service/tests/test_neo4j_client.py`

Run tests with:
```bash
python -m pytest test_neo4j_client.py -v
```

For integration tests with real Neo4j:
```bash
python -m pytest test_neo4j_client.py -v --integration
```

## Configuration Best Practices

### Production Setup
- Use Neo4j Aura for managed hosting
- Configure connection pooling appropriately
- Set up proper authentication and SSL
- Monitor vector index performance

### Development Setup
- Use local Neo4j instance
- Enable debug logging
- Test with sample data
- Verify vector index creation

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify Neo4j is running
   - Check connection parameters
   - Confirm network access

2. **Vector Index Not Available**
   - Check Neo4j version (requires 5.0+)
   - Verify vector plugin installation
   - Review index creation logs

3. **Token Limit Errors**
   - Use document chunking for large texts
   - Adjust embedding chunk sizes
   - Monitor token usage

### Logging

Enable debug logging for detailed troubleshooting:
```python
import logging
logging.getLogger('tools.services.data_analytics_service.services.knowledge_service.neo4j_client').setLevel(logging.DEBUG)
```