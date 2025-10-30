# Simple RAG Service - User Guide

## Overview

The Simple RAG (Retrieval-Augmented Generation) service provides semantic search and context-aware AI responses using vector similarity. It's the foundational RAG pattern that stores text as embeddings, retrieves relevant content, and generates responses with inline citations.

**Architecture:**
- **Vector Store**: Qdrant (via isa_common gRPC client)
- **Embeddings**: ISA Model embedding service
- **LLM**: ISA Model generation service
- **Chunking**: 400 characters per chunk, 50 character overlap
- **Multi-tenancy**: User-based isolation via `user_id` filtering

## Three Core Operations

The Simple RAG service exposes three MCP tools in `tools/services/data_analytics_service/tools/digital_tools.py`:

1. **store_knowledge** - Store text for later retrieval
2. **search_knowledge** - Search stored knowledge by semantic similarity
3. **knowledge_response** - Full RAG: retrieve context + generate AI response with citations

---

## 1. Store Knowledge (`store_knowledge`)

Store text content that can be retrieved later via semantic search.

### API Definition

```python
@mcp.tool()
async def store_knowledge(
    user_id: str,
    content: str,
    content_type: str = "text",
    metadata: dict = None,
    options: dict = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | User identifier for multi-tenant isolation |
| `content` | string | Yes | Text content to store (any length) |
| `content_type` | string | No | Content type, default: "text" |
| `metadata` | dict | No | Additional metadata to attach |
| `options` | dict | No | Storage options (e.g., chunk_size, overlap) |

### Example Usage

```bash
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "store_knowledge",
      "arguments": {
        "user_id": "alice",
        "content": "The Great Wall of China was built over many centuries, with major construction occurring during the Ming Dynasty (1368-1644). It stretches over 13,000 miles and was built to protect Chinese states from invasions.",
        "content_type": "text"
      }
    }
  }'
```

### Real Test Result

```json
{
  "status": "success",
  "action": "store_knowledge",
  "data": {
    "success": true,
    "error": null,
    "content_type": "text"
  }
}
```

### Processing Pipeline

When you store content, it goes through 4 stages:

1. **[PROC] Stage 1/4 (25%)**: Processing - Text preprocessing
2. **[EXTR] Stage 2/4 (50%)**: AI Extraction - Content analysis
3. **[EMBD] Stage 3/4 (75%)**: Embedding - Generate vector embeddings
4. **[STOR] Stage 4/4 (100%)**: Storing - Save to Qdrant

### Chunking Behavior

- **Short text** (d400 chars): Stored as single chunk
- **Long text** (>400 chars): Split into 400-char chunks with 50-char overlap
- **Example**: 212 chars ’ 1 chunk, 5000 chars ’ ~13 chunks

---

## 2. Search Knowledge (`search_knowledge`)

Search stored knowledge using semantic similarity.

### API Definition

```python
@mcp.tool()
async def search_knowledge(
    user_id: str,
    query: str,
    search_options: dict = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | User identifier for filtering results |
| `query` | string | Yes | Search query text |
| `search_options` | dict | No | Search configuration (see below) |

### Search Options

```python
{
    "top_k": 5,                    # Number of results (default: 5)
    "enable_rerank": False,        # Enable result reranking (default: False)
    "search_mode": "hybrid",       # "semantic", "hybrid", "lexical" (default: "hybrid")
    "content_types": ["text"],     # Filter by content type (default: ["text", "image"])
    "return_format": "results",    # "results", "context", "list" (default: "results")
    "rag_mode": "simple"           # RAG service mode (default: "simple")
}
```

### Example Usage

```bash
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "search_knowledge",
      "arguments": {
        "user_id": "alice",
        "query": "When was the Eiffel Tower built?",
        "search_options": {
          "top_k": 3,
          "content_types": ["text"]
        }
      }
    }
  }'
```

### Real Test Result

```json
{
  "status": "success",
  "action": "search_knowledge",
  "data": {
    "success": true,
    "search_results": [
      {
        "text": "The Eiffel Tower was built between 1887 and 1889 for the Paris World Fair. It was designed by Gustave Eiffel.",
        "relevance_score": 0.7655214667320251,
        "metadata": {
          "start_pos": 0.0,
          "text": "The Eiffel Tower was built between 1887 and 1889...",
          "stored_at": "2025-10-28T05:32:46.071246",
          "chunk_id": 0.0,
          "user_id": "FIXED_RAGSOURCE_TEST",
          "end_pos": 109.0
        },
        "content_type": "text"
      }
    ],
    "total_results": 1,
    "search_method": "simple_rag_unified",
    "query": "When was the Eiffel Tower built?"
  }
}
```

### Relevance Scores

- **0.8 - 1.0**: Highly relevant (exact or near-exact match)
- **0.6 - 0.8**: Relevant (good semantic match)
- **0.4 - 0.6**: Somewhat relevant (partial match)
- **< 0.4**: Low relevance (weak semantic connection)

---

## 3. Knowledge Response (`knowledge_response`)

Full RAG pipeline: retrieve relevant context + generate AI response with inline citations.

### API Definition

```python
@mcp.tool()
async def knowledge_response(
    user_id: str,
    query: str,
    response_options: dict = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | User identifier |
| `query` | string | Yes | User question/query |
| `response_options` | dict | No | Generation configuration (see below) |

### Response Options

```python
{
    "rag_mode": "simple",           # RAG mode: "simple", "crag", "custom", etc.
    "context_limit": 3,             # Max context items to retrieve (default: 3)
    "model": "gpt-4o-mini",         # LLM model (default: "gpt-4o-mini")
    "temperature": 0.3,             # Generation temperature (default: 0.3)
    "provider": "yyds",             # Model provider (default: "yyds")
    "enable_citations": True,       # Include inline citations (default: True)
    "include_images": True,         # Include image context (default: True)
    "use_pdf_context": False,       # Use PDF-aware pipeline (default: False)
    "auto_detect_pdf": True         # Auto-detect PDF content (default: True)
}
```

### Example Usage

```bash
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "knowledge_response",
      "arguments": {
        "user_id": "alice",
        "query": "When was the Great Wall of China built and why?",
        "response_options": {
          "context_limit": 3,
          "model": "gpt-4o-mini",
          "temperature": 0.3,
          "enable_citations": true
        }
      }
    }
  }'
```

### Real Test Result

```json
{
  "status": "success",
  "action": "knowledge_response",
  "data": {
    "success": true,
    "response": "The Great Wall of China was built over many centuries, with significant construction taking place during the Ming Dynasty, which lasted from 1368 to 1644. The wall stretches over 13,000 miles and was primarily constructed to protect Chinese states from invasions and raids by nomadic groups from the north [1]. The wall's construction involved various materials and techniques, reflecting the different periods in which it was built, and it served not only as a defensive structure but also as a means of border control and trade regulation.",
    "context_items": 1,
    "text_sources": [
      {
        "text": "The Great Wall of China was built over many centuries, with major construction occurring during the Ming Dynasty (1368-1644). It stretches over 13,000 miles and was built to protect Chinese states from invasions.",
        "score": 0.7318657040596008,
        "metadata": {
          "start_pos": 0.0,
          "user_id": "RAG_CONTEXT_TEST",
          "stored_at": "2025-10-28T06:30:10.723101",
          "chunk_id": 0.0,
          "end_pos": 212.0
        }
      }
    ],
    "image_sources": [],
    "metadata": {
      "context_length": 216,
      "sources_count": 1,
      "use_citations": true
    },
    "inline_citations_enabled": true,
    "response_type": "text_rag",
    "rag_mode_used": "simple"
  }
}
```

### Generation Pipeline

The knowledge_response goes through 4 stages:

1. **[PROC] Stage 1/4 (25%)**: Query Analysis - Analyze the query
2. **[RETR] Stage 2/4 (50%)**: Context Retrieval - Search and retrieve context
3. **[PREP] Stage 3/4 (75%)**: Context Preparation - Prepare context for generation
4. **[GEN] Stage 4/4 (100%)**: AI Generation - Generate response with LLM

### Inline Citations

Citations are automatically embedded in the response:

```
"...protect Chinese states from invasions and raids by nomadic groups from the north [1]."
```

The `[1]` references the first source in `text_sources` array.

---

## Complete Workflow Example

### Step 1: Store Knowledge

```bash
# Store information about Python
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "store_knowledge",
      "arguments": {
        "user_id": "developer_alice",
        "content": "Python is a high-level programming language created by Guido van Rossum in 1991. Python emphasizes code readability with significant whitespace and supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
        "content_type": "text"
      }
    }
  }'
```

### Step 2: Search Knowledge

```bash
# Search for Python information
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "search_knowledge",
      "arguments": {
        "user_id": "developer_alice",
        "query": "Who created Python?",
        "search_options": {
          "top_k": 3
        }
      }
    }
  }'
```

### Step 3: Generate Answer with Citations

```bash
# Get AI-generated answer with citations
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "knowledge_response",
      "arguments": {
        "user_id": "developer_alice",
        "query": "Who created Python and what are its key features?",
        "response_options": {
          "context_limit": 3,
          "enable_citations": true
        }
      }
    }
  }'
```

**Expected Response:**
```
"Python was created by Guido van Rossum in 1991 [1]. It is a high-level programming language that emphasizes code readability through the use of significant whitespace [1]. Python supports multiple programming paradigms, including procedural, object-oriented, and functional programming [1], making it versatile for various development tasks."
```

---

## Multi-Tenancy & Data Isolation

Simple RAG provides **user-based multi-tenancy**:

- Each `user_id` has isolated data
- User A cannot search User B's knowledge
- Qdrant filters ensure strict isolation

### Example: Two Users, Separate Data

```bash
# User A stores data
curl ... -d '{"user_id": "alice", "content": "Alice's private notes..."}'

# User B stores data
curl ... -d '{"user_id": "bob", "content": "Bob's private notes..."}'

# User A searches (only sees Alice's data)
curl ... -d '{"user_id": "alice", "query": "private notes"}'
# Returns: Alice's notes only

# User B searches (only sees Bob's data)
curl ... -d '{"user_id": "bob", "query": "private notes"}'
# Returns: Bob's notes only
```

---

## Configuration & Environment

### Required Environment Variables

```bash
# Qdrant Configuration
QDRANT_HOST=isa-qdrant-grpc          # Qdrant gRPC host
QDRANT_PORT=50062                    # Qdrant gRPC port
QDRANT_COLLECTION=user_knowledge     # Collection name
VECTOR_DIMENSION=1536                # Embedding dimension

# ISA Model Service
ISA_API_URL=http://isa-model:8080    # ISA model service URL

# RAG Configuration (optional)
RAG_CHUNK_SIZE=400                   # Default: 400 chars
RAG_CHUNK_OVERLAP=50                 # Default: 50 chars
```

### Chunking Configuration

Override default chunking via `options` parameter:

```python
store_knowledge(
    user_id="alice",
    content="Very long text...",
    options={
        "chunk_size": 500,      # Larger chunks
        "overlap": 100          # More overlap
    }
)
```

---

## Performance Characteristics

### Storage (store_knowledge)

- **Small text** (<500 chars): ~2-3 seconds
- **Medium text** (500-5000 chars): ~3-5 seconds
- **Large text** (>5000 chars): ~5-10 seconds

**Bottleneck**: Embedding generation (vectorization)

### Search (search_knowledge)

- **Typical query**: ~500ms - 1s
- **With reranking**: +500ms - 1s
- **Scales**: O(log n) with Qdrant HNSW index

### Generation (knowledge_response)

- **End-to-end**: ~3-5 seconds
  - Retrieval: ~500ms - 1s
  - LLM generation: ~2-4s (depends on response length)

---

## Best Practices

### 1. Chunk Size Selection

```python
# Short documents (articles, FAQs)
chunk_size=300, overlap=50

# Medium documents (documentation pages)
chunk_size=400, overlap=50  #  Default, recommended

# Long documents (books, research papers)
chunk_size=600, overlap=100
```

### 2. Context Limit Tuning

```python
# Quick answers (high precision)
context_limit=1

# Balanced retrieval (recommended)
context_limit=3  #  Default

# Comprehensive answers (high recall)
context_limit=5
```

### 3. Citation Best Practices

- **Always enable citations** for factual queries
- Citations allow verification of AI responses
- Users can trace answers back to source documents

### 4. Search vs Generate

**Use `search_knowledge` when:**
- You want raw search results
- Building custom UI to display results
- Need relevance scores for ranking

**Use `knowledge_response` when:**
- You want natural language answers
- Need AI synthesis of multiple sources
- Citations are important

---

## Troubleshooting

### Issue: No search results found

**Symptoms:**
```json
{
  "search_results": [],
  "total_results": 0
}
```

**Solutions:**
1. Check if content was stored for that `user_id`
2. Try broader search queries
3. Verify Qdrant collection exists: `docker logs mcp-staging | grep "Collection"`
4. Check user_id matches between store and search

### Issue: Low relevance scores

**Symptoms:**
```json
{
  "relevance_score": 0.3  // Too low
}
```

**Solutions:**
1. Use more specific queries
2. Improve stored content quality (add context)
3. Increase `top_k` to see more results
4. Consider hybrid search mode

### Issue: Citations missing

**Symptoms:**
```
"response": "The answer..."  // No [1], [2], etc.
```

**Solutions:**
1. Verify `enable_citations: true` in response_options
2. Check that retrieval found sources (`context_items > 0`)
3. Model may not include citations if context is weak

### Issue: context_items = 0

**Symptoms:**
```json
{
  "context_items": 0,
  "text_sources": []
}
```

**Solutions:**
1. Verify search works: Use `search_knowledge` first
2. Check if RAG factory is being used (see logs)
3. Verify user_id has stored content
4. This was a bug we fixed - ensure you're on latest code

---

## Testing Commands

### Quick Test Suite

```bash
# 1. Test Store
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"store_knowledge","arguments":{"user_id":"test_user","content":"Test content for Simple RAG","content_type":"text"}}}'

# 2. Test Search
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_knowledge","arguments":{"user_id":"test_user","query":"Test content","search_options":{"top_k":3}}}}'

# 3. Test Generate
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"knowledge_response","arguments":{"user_id":"test_user","query":"What is the test content?","response_options":{"enable_citations":true}}}}'
```

---

## Architecture Diagram

```
                                                         
                    MCP Tools Layer                      
              (digital_tools.py)                         
                                                         
                                                 
     store_         search_        knowledge_    
    knowledge      knowledge        response     
                                                 
                                                         
                         
                         ¼
                                                         
                   RAG Factory                           
              (rag_factory.py)                           
                                                         
       get_rag_service(mode="simple")                  
                                                        
                                              
                                              ¼
                                                         
              SimpleRAGService                           
         (simple_rag_service.py)                         
                                                         
                                                
   store()    retrieve()    generate()          
                                                
                                                         
                                        
       ¼                ¼                 ¼
                                        
  Qdrant          ISA            ISA    
 (Vector        Embedding        LLM    
  Store)         Service       Service  
                                        
```

---

## Next Steps

Now that Simple RAG is working, you can:

1. **Add Hybrid Search** - Combine vector + keyword search for better recall
2. **Implement Reranking** - Use cross-encoder to improve result quality
3. **Migrate Advanced RAG** - Port CRAG, Custom RAG, Graph RAG patterns
4. **Add Evaluation** - Measure retrieval and generation quality
5. **Optimize Performance** - Cache embeddings, batch operations

---

## References

- **Code**: `tools/services/data_analytics_service/`
  - Tools: `tools/digital_tools.py`
  - Service: `services/digital_service/patterns/simple_rag_service.py`
  - Base: `services/digital_service/base/base_rag_service.py`
  - Factory: `services/digital_service/base/rag_factory.py`

- **Dependencies**:
  - Qdrant Client: `isa_common.qdrant_client`
  - ISA Model: HTTP client to ISA model service
  - Pydantic Models: `base/rag_models.py`

---

**Last Updated**: 2025-10-28
**Version**: 1.0 (Post-rebuild, fully operational)
