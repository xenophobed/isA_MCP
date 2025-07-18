# Digital Resource Manager - MCP Client Integration Guide

## Overview

The Digital Resource Manager provides MCP (Model Context Protocol) resource registration and management for digital analytics and RAG (Retrieval-Augmented Generation) services. This document explains how MCP clients can discover, access, and manage digital knowledge resources.

## Architecture

```
MCP Client ’ MCP Server ’ Digital Resource Manager ’ RAG Service ’ Supabase Database
                      “
                 Resource Registry
                 (Memory-based)
```

## Resource Types

The Digital Resource Manager supports these resource types:

- **`knowledge_item`**: Individual text chunks with embeddings
- **`rag_session`**: RAG conversation sessions with context tracking
- **`document_chunk`**: Document fragments from chunked files
- **`analytics_report`**: Generated analytics and insights
- **`embedding_collection`**: Collections of related embeddings

## MCP Resource Addressing

All digital resources use the following MCP addressing scheme:

### Knowledge Items
```
mcp://rag/{user_id}/{knowledge_id}
```

### RAG Sessions
```
mcp://rag_session/{user_id}/{session_id}
```

### Examples
```
mcp://rag/user123/17cc3aeb-1aaf-4faa-94ea-a8a65647cc46
mcp://rag_session/user123/session_abc-def-789
```

## Integration with Digital Analytics Tools

### Using Digital Analytics Tools

The digital analytics tools are registered as MCP tools and can be accessed by MCP clients:

#### 1. Store Knowledge
```python
# MCP Tool Call
{
    "tool": "store_knowledge",
    "arguments": {
        "user_id": "user123",
        "text": "Machine learning is a subset of artificial intelligence...",
        "metadata": "{\"topic\": \"AI\", \"source\": \"textbook\"}"
    }
}

# Response
{
    "status": "success",
    "data": {
        "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
        "mcp_address": "mcp://rag/user123/17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
        "text_length": 106,
        "embedding_dimensions": 1536,
        "mcp_registration": true
    }
}
```

#### 2. Search Knowledge
```python
# MCP Tool Call
{
    "tool": "search_knowledge",
    "arguments": {
        "user_id": "user123",
        "query": "artificial intelligence",
        "top_k": 5,
        "enable_rerank": false
    }
}

# Response
{
    "status": "success",
    "data": {
        "search_results": [
            {
                "knowledge_id": "17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
                "text": "Machine learning is a subset of artificial intelligence...",
                "relevance_score": 0.4938,
                "mcp_address": "mcp://rag/user123/17cc3aeb-1aaf-4faa-94ea-a8a65647cc46",
                "metadata": {"topic": "AI", "source": "textbook"}
            }
        ],
        "total_knowledge_items": 1,
        "reranking_used": false
    }
}
```

#### 3. Generate RAG Response
```python
# MCP Tool Call
{
    "tool": "generate_rag_response",
    "arguments": {
        "user_id": "user123",
        "query": "What is machine learning?",
        "context_limit": 3
    }
}

# Response includes generated response with context sources
```

#### 4. Add Document with Chunking
```python
# MCP Tool Call
{
    "tool": "add_document",
    "arguments": {
        "user_id": "user123",
        "document": "Long document text here...",
        "chunk_size": 400,
        "overlap": 50,
        "metadata": "{\"title\": \"AI Manual\", \"author\": \"John Doe\"}"
    }
}

# Creates multiple knowledge items with sequential chunk indices
```

## Direct Resource Manager Usage

### Initialization

```python
from resources.digital_resource import digital_knowledge_resources

# Global instance is automatically available
resource_manager = digital_knowledge_resources
```

### Register Knowledge Items

```python
# Register a knowledge item as an MCP resource
registration_result = await resource_manager.register_knowledge_item(
    knowledge_id="knowledge_123",
    user_id="user123",
    knowledge_data={
        "text_preview": "Machine learning is a subset...",
        "text_length": 106,
        "embedding_model": "text-embedding-3-small",
        "metadata": {"topic": "AI"},
        "source_file": "textbook.pdf",
        "chunk_index": 0,
        "document_id": "doc_456"
    }
)

# Result includes MCP address: mcp://rag/user123/knowledge_123
```

### Register RAG Sessions

```python
# Register a RAG session for tracking
session_result = await resource_manager.register_rag_session(
    session_id="session_789",
    user_id="user123",
    session_data={
        "query": "What is machine learning?",
        "context_used": 3,
        "response_length": 250,
        "knowledge_items_used": ["knowledge_123", "knowledge_456"],
        "metadata": {"conversation_type": "educational"}
    }
)

# Creates: mcp://rag_session/user123/session_789
```

### Query User Resources

```python
# Get all resources for a user
user_resources = await resource_manager.get_user_resources(
    user_id="user123",
    resource_type="knowledge_item"  # Optional filter
)

# Search resources by content
search_results = await resource_manager.search_resources(
    user_id="user123",
    query="artificial intelligence",
    resource_type="knowledge_item",
    limit=10
)

# Get document chunks
chunks = await resource_manager.get_document_chunks(
    document_id="doc_456",
    user_id="user123"
)
```

### Resource Analytics

```python
# Get comprehensive analytics
analytics = await resource_manager.get_resource_analytics("user123")

# Returns:
{
    "total_resources": 15,
    "resource_types": {"knowledge_item": 12, "rag_session": 3},
    "knowledge_stats": {
        "total_items": 12,
        "total_text_length": 5000,
        "avg_text_length": 416.67,
        "embedding_models": {"text-embedding-3-small": 12},
        "documents": 3
    },
    "document_stats": {
        "total_documents": 3,
        "total_chunks": 12,
        "avg_chunks_per_document": 4.0
    },
    "rag_session_stats": {
        "total_sessions": 3,
        "avg_context_used": 2.33
    }
}
```

## MCP Client Implementation Example

### Python MCP Client

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_digital_analytics():
    # Connect to MCP server with digital analytics tools
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "your_mcp_server"],
        env={"PYTHONPATH": "/path/to/your/project"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:", [tool.name for tool in tools.tools])
            
            # Store knowledge
            store_result = await session.call_tool(
                "store_knowledge",
                arguments={
                    "user_id": "user123",
                    "text": "Python is a programming language",
                    "metadata": '{"topic": "programming"}'
                }
            )
            print("Stored:", store_result.content)
            
            # Search knowledge
            search_result = await session.call_tool(
                "search_knowledge",
                arguments={
                    "user_id": "user123",
                    "query": "programming language",
                    "top_k": 3
                }
            )
            print("Search results:", search_result.content)
            
            # Generate RAG response
            rag_result = await session.call_tool(
                "generate_rag_response",
                arguments={
                    "user_id": "user123",
                    "query": "Tell me about Python",
                    "context_limit": 2
                }
            )
            print("RAG response:", rag_result.content)

# Run the example
asyncio.run(use_digital_analytics())
```

### JavaScript/TypeScript MCP Client

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

async function useDigitalAnalytics() {
    // Create transport and client
    const transport = new StdioClientTransport({
        command: "python",
        args: ["-m", "your_mcp_server"],
        env: { PYTHONPATH: "/path/to/your/project" }
    });
    
    const client = new Client(
        { name: "digital-analytics-client", version: "1.0.0" },
        { capabilities: {} }
    );
    
    await client.connect(transport);
    
    // Store knowledge
    const storeResult = await client.request(
        { method: "tools/call" },
        {
            name: "store_knowledge",
            arguments: {
                user_id: "user123",
                text: "JavaScript is a versatile programming language",
                metadata: JSON.stringify({ topic: "programming", language: "JS" })
            }
        }
    );
    
    console.log("Stored:", storeResult);
    
    // Search knowledge
    const searchResult = await client.request(
        { method: "tools/call" },
        {
            name: "search_knowledge",
            arguments: {
                user_id: "user123",
                query: "JavaScript programming",
                top_k: 5,
                enable_rerank: true
            }
        }
    );
    
    console.log("Search results:", searchResult);
    
    await client.close();
}

useDigitalAnalytics().catch(console.error);
```

## Resource Lifecycle

### 1. Knowledge Storage Flow
```
MCP Client ’ store_knowledge ’ RAG Service ’ Supabase ’ Digital Resource Manager
                                                    “
                                              MCP Resource Registered
                                              mcp://rag/{user_id}/{knowledge_id}
```

### 2. Knowledge Retrieval Flow
```
MCP Client ’ search_knowledge ’ RAG Service ’ Supabase Vector Search
                                        “
                            Results with MCP addresses returned
```

### 3. Resource Discovery Flow
```
MCP Client ’ Resource Manager ’ Filter by user/type ’ Return resource list with MCP addresses
```

## Security and Permissions

### User Isolation
- All resources are isolated by `user_id`
- Cross-user access is prevented at the resource manager level
- Each resource has explicit read/write permissions

### Access Control
```python
{
    "access_permissions": {
        "owner": "user123",
        "read_access": ["user123"],
        "write_access": ["user123"]
    }
}
```

### Resource Validation
- All resource IDs are validated before operations
- User permissions are checked for every access
- Resources are automatically cleaned up when deleted

## Error Handling

### Common Error Responses

```python
# Resource not found
{
    "success": false,
    "error": "Resource not found",
    "resource_id": "invalid_id"
}

# Access denied
{
    "success": false,
    "error": "Access denied",
    "resource_id": "knowledge_123",
    "user_id": "unauthorized_user"
}

# Service unavailable
{
    "success": false,
    "error": "Embedding service unavailable",
    "details": "ISA service connection failed"
}
```

## Performance Considerations

### Resource Caching
- Resources are stored in memory for fast access
- User resource mappings are maintained for efficient queries
- Document chunk relationships are pre-computed

### Scalability
- Resource manager supports thousands of resources per user
- Pagination is available for large result sets
- Analytics calculations are optimized for performance

### Memory Management
- Resources are lightweight metadata structures
- Actual content is stored in Supabase database
- Cleanup methods prevent memory leaks

## Best Practices

### For MCP Client Developers

1. **Always specify user_id** for resource isolation
2. **Handle async operations** properly with await/promises
3. **Parse JSON responses** to access structured data
4. **Implement error handling** for service unavailability
5. **Use appropriate top_k values** to limit response size

### For Resource Management

1. **Register resources immediately** after storage
2. **Clean up resources** when no longer needed
3. **Use meaningful metadata** for better searchability
4. **Monitor resource analytics** for usage patterns
5. **Implement proper user authentication** before operations

## Monitoring and Debugging

### Resource Statistics
```python
# Get global statistics
stats = digital_knowledge_resources.get_global_stats()
# Returns total resources, users, types, etc.

# Get user analytics
analytics = await digital_knowledge_resources.get_resource_analytics("user123")
# Returns detailed user-specific metrics
```

### Logging
- All operations are logged with appropriate levels
- Error details include context for debugging
- Performance metrics are available for monitoring

## Configuration

### Environment Variables
```bash
# Required for RAG service integration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Optional for enhanced performance
ISA_MODEL_SERVICE_URL=http://localhost:8082
ENABLE_RERANKING=false
```

### Service Dependencies
- **Supabase**: Vector database for embeddings
- **ISA Model Service**: Embedding generation and reranking
- **Python 3.8+**: Runtime environment
- **FastMCP**: MCP tool registration framework

---

This documentation provides comprehensive guidance for MCP clients to effectively use the Digital Resource Manager and Digital Analytics Tools for knowledge management and RAG operations.