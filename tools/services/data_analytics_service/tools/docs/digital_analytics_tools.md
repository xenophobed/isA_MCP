# Digital Analytics Tools - MCP Integration Guide

## Overview

The Digital Analytics Tools provide comprehensive knowledge management and RAG (Retrieval-Augmented Generation) capabilities through MCP (Model Context Protocol) integration. These tools enable MCP clients to store, search, and generate intelligent responses using semantic embeddings and vector databases.

## Architecture

```
MCP Client ’ FastMCP Server ’ Digital Analytics Tools ’ RAG Service ’ Supabase Database
                                                   “
                                         Digital Resource Manager
                                         (MCP Resource Registry)
```

## Available MCP Tools

### 1. store_knowledge

**Description**: Store text as knowledge with automatic embedding generation and MCP registration

**MCP Tool Call**:
```json
{
    "tool": "store_knowledge",
    "arguments": {
        "user_id": "user123",
        "text": "Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models.",
        "metadata": "{\"topic\": \"AI\", \"source\": \"textbook\", \"difficulty\": \"beginner\"}"
    }
}
```

**Response**:
```json
{
    "status": "success",
    "action": "store_knowledge",
    "data": {
        "success": true,
        "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
        "mcp_address": "mcp://rag/user123/17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
        "user_id": "user123",
        "text_length": 106,
        "embedding_dimensions": 1536,
        "mcp_registration": true
    },
    "timestamp": "2025-07-18T01:10:41.882493"
}
```

**Features**:
- Generates 1536-dimension embeddings using ISA model service
- Stores in Supabase with vector indexing
- Automatic MCP resource registration
- User isolation and security
- Metadata support for enhanced search

### 2. search_knowledge

**Description**: Search user's knowledge base with semantic similarity and optional reranking

**MCP Tool Call**:
```json
{
    "tool": "search_knowledge",
    "arguments": {
        "user_id": "user123",
        "query": "artificial intelligence",
        "top_k": 5,
        "enable_rerank": false
    }
}
```

**Response**:
```json
{
    "status": "success",
    "action": "search_knowledge",
    "data": {
        "success": true,
        "user_id": "user123",
        "query": "artificial intelligence",
        "search_results": [
            {
                "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
                "text": "Machine learning is a subset of artificial intelligence...",
                "relevance_score": 0.4938972826971005,
                "similarity_score": 0.4938972826971005,
                "metadata": {"topic": "AI", "source": "textbook", "difficulty": "beginner"},
                "created_at": "2025-07-18T01:10:41.215505+00:00",
                "mcp_address": "mcp://rag/user123/17cc3aeb-1aaf-4faa-94ea-a8a65647cc46"
            }
        ],
        "total_knowledge_items": 1,
        "reranking_used": false
    },
    "timestamp": "2025-07-18T01:10:44.092075"
}
```

**Features**:
- Vector similarity search using pgvector
- Optional reranking with Jina reranker v2
- User-isolated search results
- Relevance and similarity scoring
- MCP addresses in results

### 3. generate_rag_response

**Description**: Generate response using RAG (Retrieval-Augmented Generation) pipeline

**MCP Tool Call**:
```json
{
    "tool": "generate_rag_response",
    "arguments": {
        "user_id": "user123",
        "query": "What is machine learning and how does it work?",
        "context_limit": 3
    }
}
```

**Response**:
```json
{
    "status": "success",
    "action": "generate_rag_response",
    "data": {
        "success": true,
        "user_id": "user123",
        "query": "What is machine learning and how does it work?",
        "response": "Based on your knowledge base, machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models. It works by...",
        "context_used": [
            {
                "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
                "text": "Machine learning is a subset of artificial intelligence...",
                "relevance_score": 0.85,
                "mcp_address": "mcp://rag/user123/17cc3aeb-1aaf-4faa-94ea-a8a65647cc46"
            }
        ],
        "context_count": 1,
        "response_length": 250
    },
    "timestamp": "2025-07-18T01:15:22.442891"
}
```

**Features**:
- Retrieves relevant context from user's knowledge base
- Generates informed responses using retrieved context
- Shows context sources with MCP addresses
- Configurable context limit
- Response quality scoring

### 4. add_document

**Description**: Add long document with automatic chunking and storage

**MCP Tool Call**:
```json
{
    "tool": "add_document",
    "arguments": {
        "user_id": "user123",
        "document": "This is a long document about artificial intelligence and machine learning. It covers various topics including neural networks, deep learning, natural language processing, and computer vision. The document explains how AI systems work and their applications in different industries...",
        "chunk_size": 400,
        "overlap": 50,
        "metadata": "{\"title\": \"AI Handbook\", \"author\": \"John Doe\", \"type\": \"manual\"}"
    }
}
```

**Response**:
```json
{
    "status": "success",
    "action": "add_document",
    "data": {
        "success": true,
        "user_id": "user123",
        "document_id": "doc_789abc",
        "chunks_created": 5,
        "knowledge_ids": [
            "chunk_1_uuid",
            "chunk_2_uuid",
            "chunk_3_uuid",
            "chunk_4_uuid",
            "chunk_5_uuid"
        ],
        "total_text_length": 1800,
        "chunk_size": 400,
        "overlap": 50,
        "mcp_registrations": 5
    },
    "timestamp": "2025-07-18T01:20:15.334567"
}
```

**Features**:
- Intelligent text chunking with overlap
- Maintains document structure and context
- Batch embedding generation
- Individual MCP resource registration for each chunk
- Document relationship tracking

### 5. list_user_knowledge

**Description**: List all knowledge items for a user with previews and metadata

**MCP Tool Call**:
```json
{
    "tool": "list_user_knowledge",
    "arguments": {
        "user_id": "user123"
    }
}
```

**Response**:
```json
{
    "status": "success",
    "action": "list_user_knowledge",
    "data": {
        "success": true,
        "user_id": "user123",
        "knowledge_items": [
            {
                "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
                "text_preview": "Machine learning is a subset of artificial intelligence...",
                "text_length": 106,
                "metadata": {"topic": "AI", "source": "textbook"},
                "chunk_index": 0,
                "source_document": "doc_456",
                "created_at": "2025-07-18T01:10:41.215505+00:00",
                "mcp_address": "mcp://rag/user123/17cc3aeb-1aaf-4faa-94ea-a8a65647cc46"
            }
        ],
        "total_count": 1,
        "total_text_length": 106
    },
    "timestamp": "2025-07-18T01:25:33.567890"
}
```

**Features**:
- Complete inventory of user's knowledge base
- Text previews for quick identification
- Metadata and creation timestamps
- MCP addresses for direct access
- Statistics and analytics

### 6. get_knowledge_item

**Description**: Get complete details of a specific knowledge item

**MCP Tool Call**:
```json
{
    "tool": "get_knowledge_item",
    "arguments": {
        "user_id": "user123",
        "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46"
    }
}
```

**Response**:
```json
{
    "status": "success",
    "action": "get_knowledge_item",
    "data": {
        "success": true,
        "user_id": "user123",
        "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
        "knowledge": {
            "id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
            "text": "Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models.",
            "metadata": {"topic": "AI", "source": "textbook", "difficulty": "beginner"},
            "chunk_index": 0,
            "source_document": "test",
            "created_at": "2025-07-18T01:10:41.215505+00:00",
            "updated_at": "2025-07-18T01:10:41.215505+00:00",
            "mcp_address": "mcp://rag/user123/17cc3aeb-1aaf-4faa-94ea-a8a65647cc46"
        }
    },
    "timestamp": "2025-07-18T01:30:44.105103"
}
```

**Features**:
- Complete knowledge item details
- Full text content and metadata
- Creation and modification timestamps
- Document relationship information
- MCP resource address

### 7. delete_knowledge_item

**Description**: Delete a specific knowledge item and its MCP registration

**MCP Tool Call**:
```json
{
    "tool": "delete_knowledge_item",
    "arguments": {
        "user_id": "user123",
        "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46"
    }
}
```

**Response**:
```json
{
    "status": "success",
    "action": "delete_knowledge_item",
    "data": {
        "success": true,
        "user_id": "user123",
        "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
        "deleted_from_database": true,
        "mcp_registration_removed": true
    },
    "timestamp": "2025-07-18T01:35:55.789123"
}
```

**Features**:
- Permanent deletion from database
- Automatic MCP resource cleanup
- User permission validation
- Cascade deletion for document chunks
- Audit trail logging

### 8. retrieve_context

**Description**: Retrieve relevant context items for a query without generating responses

**MCP Tool Call**:
```json
{
    "tool": "retrieve_context",
    "arguments": {
        "user_id": "user123",
        "query": "neural networks and deep learning",
        "top_k": 5
    }
}
```

**Response**:
```json
{
    "status": "success",
    "action": "retrieve_context",
    "data": {
        "success": true,
        "user_id": "user123",
        "query": "neural networks and deep learning",
        "context_items": [
            {
                "knowledge_id": "context_item_1",
                "text": "Neural networks are computational models inspired by biological neural networks...",
                "relevance_score": 0.92,
                "metadata": {"topic": "neural_networks", "difficulty": "intermediate"},
                "mcp_address": "mcp://rag/user123/context_item_1"
            }
        ],
        "context_count": 1
    },
    "timestamp": "2025-07-18T01:40:12.345678"
}
```

**Features**:
- Context retrieval without response generation
- Relevance scoring for context ranking
- Configurable result count
- Metadata and MCP addresses included
- Optimized for context building workflows

### 9. get_rag_service_status

**Description**: Get current status and configuration of the RAG service

**MCP Tool Call**:
```json
{
    "tool": "get_rag_service_status",
    "arguments": {}
}
```

**Response**:
```json
{
    "service_name": "RAG Service",
    "status": "active",
    "table_name": "user_knowledge",
    "default_chunk_size": 400,
    "default_overlap": 50,
    "default_top_k": 5,
    "embedding_model": "text-embedding-3-small",
    "rerank_enabled": false,
    "capabilities": [
        "knowledge_storage",
        "semantic_search",
        "document_chunking",
        "rag_generation",
        "mcp_integration",
        "user_isolation"
    ]
}
```

**Features**:
- Real-time service health monitoring
- Configuration parameter visibility
- Capability enumeration
- Service dependency status
- Performance metrics

## MCP Client Integration Examples

### Python Example

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_digital_analytics():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "your_mcp_server"],
        env={"PYTHONPATH": "/path/to/project"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Store knowledge
            result = await session.call_tool("store_knowledge", {
                "user_id": "user123",
                "text": "Python is a high-level programming language",
                "metadata": '{"topic": "programming", "language": "python"}'
            })
            
            # Search knowledge
            search = await session.call_tool("search_knowledge", {
                "user_id": "user123",
                "query": "programming language",
                "top_k": 3,
                "enable_rerank": true
            })
            
            # Generate RAG response
            response = await session.call_tool("generate_rag_response", {
                "user_id": "user123",
                "query": "What can you tell me about Python?",
                "context_limit": 2
            })

asyncio.run(use_digital_analytics())
```

### JavaScript Example

```javascript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

async function useDigitalAnalytics() {
    const transport = new StdioClientTransport({
        command: "python",
        args: ["-m", "your_mcp_server"]
    });
    
    const client = new Client(
        { name: "digital-client", version: "1.0.0" },
        { capabilities: {} }
    );
    
    await client.connect(transport);
    
    // Add document with chunking
    const addDoc = await client.request(
        { method: "tools/call" },
        {
            name: "add_document",
            arguments: {
                user_id: "user123",
                document: "Large document content here...",
                chunk_size: 300,
                overlap: 30,
                metadata: JSON.stringify({
                    title: "JavaScript Guide",
                    author: "Jane Smith"
                })
            }
        }
    );
    
    // List all knowledge
    const knowledge = await client.request(
        { method: "tools/call" },
        { name: "list_user_knowledge", arguments: { user_id: "user123" } }
    );
    
    await client.close();
}
```

## Tool Categories and Keywords

### Tool Organization

**Category: knowledge_management**
- `store_knowledge` - Keywords: store, knowledge, embedding, save, add, memory
- `search_knowledge` - Keywords: search, find, query, semantic, knowledge, similarity
- `generate_rag_response` - Keywords: generate, RAG, response, answer, context, intelligent
- `add_document` - Keywords: document, add, chunk, process, long_text, split
- `list_user_knowledge` - Keywords: list, knowledge, overview, inventory, user_data
- `get_knowledge_item` - Keywords: get, knowledge, details, item, specific, retrieve
- `delete_knowledge_item` - Keywords: delete, remove, knowledge, item, cleanup
- `retrieve_context` - Keywords: context, retrieve, relevant, similarity, background

**Category: system_info**
- `get_rag_service_status` - Keywords: status, health, configuration, service, RAG

## Error Handling

### Common Error Scenarios

```json
// Service unavailable
{
    "status": "error",
    "action": "store_knowledge",
    "data": {},
    "message": "Knowledge storage failed: ISA embedding service unavailable"
}

// User access denied
{
    "status": "error", 
    "action": "get_knowledge_item",
    "data": {},
    "message": "Knowledge retrieval failed: Access denied for user"
}

// Invalid parameters
{
    "status": "error",
    "action": "search_knowledge", 
    "data": {},
    "message": "Knowledge search failed: Invalid query parameter"
}
```

### Error Recovery Strategies

1. **Service Unavailable**: Implement retry logic with exponential backoff
2. **Permission Errors**: Validate user authentication before tool calls
3. **Invalid Parameters**: Validate inputs on client side before sending
4. **Rate Limiting**: Implement client-side request throttling
5. **Network Issues**: Use connection pooling and timeout handling

## Performance Considerations

### Optimization Tips

1. **Batch Operations**: Use `add_document` for multiple related texts
2. **Appropriate top_k**: Don't retrieve more results than needed
3. **Metadata Indexing**: Use structured metadata for better search performance
4. **Chunk Sizing**: Balance between context and performance (300-500 chars optimal)
5. **Reranking**: Enable only when precision is critical (adds latency)

### Resource Management

- **Memory Usage**: Tools maintain minimal state, most data in database
- **Database Connections**: Connection pooling handles concurrent requests
- **Embedding Cache**: ISA service caches frequent embeddings
- **Vector Indexing**: Automatic pgvector indexing for fast similarity search

## Security Features

### Data Protection

- **User Isolation**: All operations are scoped to specific user_id
- **Access Control**: Read/write permissions enforced at resource level
- **Input Validation**: All parameters validated before processing
- **SQL Injection Prevention**: Parameterized queries throughout
- **Audit Logging**: All operations logged with user context

### Privacy Considerations

- **Data Residency**: All data stored in configured Supabase instance
- **Encryption**: Vector embeddings encrypted at rest and in transit
- **User Deletion**: Complete data removal when user deleted
- **Metadata Scrubbing**: Sensitive information filtered from logs
- **Anonymous Analytics**: Usage metrics collected without PII

## Configuration and Setup

### Required Environment Variables

```bash
# Database Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Embedding Service
ISA_MODEL_SERVICE_URL=http://localhost:8082

# Optional Configuration
RAG_DEFAULT_CHUNK_SIZE=400
RAG_DEFAULT_OVERLAP=50
RAG_DEFAULT_TOP_K=5
ENABLE_RERANKING=false
```

### Service Dependencies

1. **Supabase Database**: Vector storage with pgvector extension
2. **ISA Model Service**: Embedding generation and reranking
3. **Python 3.8+**: Runtime environment
4. **FastMCP Framework**: MCP tool registration
5. **PostgreSQL 14+**: Database engine with vector support

### Deployment Checklist

- [ ] Supabase instance configured with pgvector
- [ ] `user_knowledge` table created with proper schema
- [ ] ISA model service running and accessible
- [ ] Environment variables configured
- [ ] MCP server registered with tools
- [ ] Client authentication configured
- [ ] Monitoring and logging enabled

---

This documentation provides complete guidance for integrating and using the Digital Analytics Tools through MCP clients for comprehensive knowledge management and RAG operations.