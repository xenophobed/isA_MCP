# RAG Service Documentation

## Overview

The RAG (Retrieval-Augmented Generation) Service provides a complete knowledge management and retrieval system with embedding generation, storage, semantic search, and response generation capabilities.

## Features

- **User-Isolated Knowledge Bases**: Each user has their own secure knowledge repository
- **Real Embedding Generation**: Uses ISA service for text embeddings
- **Semantic Search**: Find relevant content using vector similarity
- **Document Chunking**: Automatically splits long documents into manageable pieces
- **Optional Reranking**: Enhanced relevance scoring using Jina reranker
- **MCP Resource Registration**: Integrates with graph knowledge resources
- **Full RAG Pipeline**: Store ’ Search ’ Retrieve ’ Generate responses

## Configuration

```python
config = {
    'chunk_size': 400,           # Default chunk size for documents
    'overlap': 50,               # Overlap between chunks
    'top_k': 5,                  # Default number of results to return
    'embedding_model': 'text-embedding-3-small',  # ISA embedding model
    'enable_rerank': False       # Enable/disable reranking (default: False)
}
```

## Core Methods

### store_knowledge(user_id, text, metadata=None)
Store text as knowledge with automatic embedding generation and MCP registration.

**Args:**
- `user_id` (str): User identifier
- `text` (str): Text content to store
- `metadata` (dict, optional): Additional metadata

**Returns:**
- Dictionary with success status, knowledge_id, MCP address, and embedding info

### retrieve_context(user_id, query, top_k=None)
Retrieve relevant context from user's knowledge base using semantic search.

**Args:**
- `user_id` (str): User identifier
- `query` (str): Search query
- `top_k` (int, optional): Number of results to return

**Returns:**
- Dictionary with context items and similarity scores

### search_knowledge(user_id, query, top_k=None, enable_rerank=None)
Advanced search with optional reranking and relevance scoring.

**Args:**
- `user_id` (str): User identifier
- `query` (str): Search query
- `top_k` (int, optional): Number of results to return
- `enable_rerank` (bool, optional): Enable reranking (overrides default)

**Returns:**
- Dictionary with search results and relevance scores

### generate_response(user_id, query, context_limit=3, model=None)
Complete RAG pipeline: retrieve context and generate response.

**Args:**
- `user_id` (str): User identifier
- `query` (str): User query
- `context_limit` (int): Maximum context items to use
- `model` (str, optional): LLM model for generation

**Returns:**
- Dictionary with generated response and context used

### add_document(user_id, document, chunk_size=None, overlap=None, metadata=None)
Add long document with automatic chunking and storage.

**Args:**
- `user_id` (str): User identifier
- `document` (str): Document text
- `chunk_size` (int, optional): Chunk size override
- `overlap` (int, optional): Overlap override
- `metadata` (dict, optional): Metadata for all chunks

**Returns:**
- Dictionary with chunking results and stored chunk info

### list_user_knowledge(user_id)
List all knowledge items for a user.

**Args:**
- `user_id` (str): User identifier

**Returns:**
- Dictionary with user's knowledge items and previews

### get_knowledge(user_id, knowledge_id)
Get specific knowledge item with full details.

**Args:**
- `user_id` (str): User identifier
- `knowledge_id` (str): Knowledge item identifier

**Returns:**
- Dictionary with complete knowledge item data

### delete_knowledge(user_id, knowledge_id)
Delete a knowledge item and its MCP registration.

**Args:**
- `user_id` (str): User identifier
- `knowledge_id` (str): Knowledge item identifier

**Returns:**
- Dictionary with deletion status

## Usage Examples

### Basic Knowledge Storage
```python
# Store knowledge
result = await rag_service.store_knowledge(
    user_id="user123",
    text="Machine learning is a subset of AI",
    metadata={"topic": "AI", "source": "textbook"}
)

# Search knowledge
search_result = await rag_service.search_knowledge(
    user_id="user123",
    query="artificial intelligence",
    top_k=3
)
```

### Document Processing
```python
# Add long document with chunking
result = await rag_service.add_document(
    user_id="user123",
    document=long_text,
    chunk_size=500,
    overlap=50,
    metadata={"document": "AI_handbook", "chapter": "intro"}
)
```

### RAG Generation
```python
# Generate response using RAG
response = await rag_service.generate_response(
    user_id="user123",
    query="What is machine learning?",
    context_limit=2
)
```

### Advanced Search with Reranking
```python
# Search with reranking enabled
search_result = await rag_service.search_knowledge(
    user_id="user123",
    query="deep learning algorithms",
    top_k=5,
    enable_rerank=True
)
```

## Database Schema

The service uses a `user_knowledge` table with the following structure:

```sql
CREATE TABLE user_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding_vector VECTOR(1536),
    metadata JSONB DEFAULT '{}',
    chunk_index INTEGER DEFAULT 0,
    source_document TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## MCP Integration

Each knowledge item is registered as an MCP resource with:
- Resource ID: knowledge UUID
- MCP Address: `mcp://rag/{user_id}/{knowledge_id}`
- Resource Type: `knowledge_base_item`
- Metadata includes text preview, source info, and embedding model

## Testing

### Unit Tests
```bash
python -m pytest tools/services/data_analytics_service/services/digital_service/tests/test_rag_service.py -k "not TestRAGServiceIntegration"
```

### Integration Tests (requires services)
```bash
INTEGRATION_TESTS=1 python -m pytest tools/services/data_analytics_service/services/digital_service/tests/test_rag_service.py -k "TestRAGServiceIntegration"
```

## Requirements

- **ISA Model Service**: Running on port 8082 for embeddings
- **Supabase Database**: With `user_knowledge` table in dev schema
- **pgvector Extension**: For vector similarity search
- **Python Dependencies**: supabase, asyncio, uuid, json

## Error Handling

The service includes comprehensive error handling:
- Embedding generation failures with fallbacks
- Database connection issues
- Invalid user access attempts
- Reranking service failures (falls back to similarity search)
- MCP registration failures (logs warnings but continues)

## Security

- **User Isolation**: All operations are scoped to specific users
- **Access Control**: Users can only access their own knowledge
- **Data Validation**: Input sanitization and type checking
- **Error Masking**: Internal errors don't expose sensitive information

## Performance Considerations

- **Batch Operations**: Optimized for multiple document processing
- **Caching**: Database connection pooling
- **Async Operations**: Non-blocking I/O for all operations
- **Index Usage**: Optimized database queries with proper indexing
- **Memory Management**: Efficient handling of large documents