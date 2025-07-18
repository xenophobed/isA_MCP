# Embedding Generator Documentation

## Overview

The `embedding_generator.py` provides a simple wrapper around the ISA client for text embedding operations. It handles all embedding complexities including single/batch processing, similarity computation, text chunking, and document reranking.

## Usage

### Simple Embeddings

```python
from tools.services.intelligence_service.language.embedding_generator import embed

# Basic usage
embedding = await embed("Hello world")
print(f"Embedding dimensions: {len(embedding)}")  # 1536 dimensions

# Batch embeddings
embeddings = await embed(["Text 1", "Text 2", "Text 3"])
print(f"Generated {len(embeddings)} embeddings")
```

### Similarity Computation

```python
from tools.services.intelligence_service.language.embedding_generator import similarity

# Compute similarity between texts
score = await similarity("machine learning", "artificial intelligence")
print(f"Similarity: {score:.3f}")  # Real result: 0.588
```

### Semantic Search

```python
from tools.services.intelligence_service.language.embedding_generator import search

# Find most similar texts
results = await search(
    "artificial intelligence",
    [
        "Machine learning algorithms",
        "Cooking recipes", 
        "Deep learning networks",
        "Sports news"
    ],
    top_k=2
)

for text, score in results:
    print(f"{score:.3f}: {text}")
```

### Text Chunking

```python
from tools.services.intelligence_service.language.embedding_generator import chunk

# Chunk long text with embeddings
long_text = """
This is a very long document that needs to be split into smaller chunks
for processing. Each chunk will have its own embedding vector.
"""

chunks = await chunk(long_text, chunk_size=100, overlap=20)
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: {chunk['text'][:50]}...")
    print(f"Embedding dims: {len(chunk['embedding'])}")
```

### Document Reranking

```python
from tools.services.intelligence_service.language.embedding_generator import rerank

# Rerank documents by relevance
documents = [
    "Machine learning is a subset of artificial intelligence",
    "Cooking recipes for beginners", 
    "Deep learning uses neural networks"
]

results = await rerank("artificial intelligence", documents, top_k=3)
for result in results:
    score = result["relevance_score"]  # Real results: 0.690, 0.147, 0.090
    doc = result["document"]
    print(f"{score:.3f}: {doc}")
```

### Using the Class

```python
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator

generator = EmbeddingGenerator()

# Single embedding
embedding = await generator.embed_single("Hello world")

# Batch embeddings
embeddings = await generator.embed_batch(["Text 1", "Text 2"])

# Similarity search
results = await generator.find_most_similar("query", ["doc1", "doc2"], top_k=5)
```

## API Reference

### `embed(text, **kwargs)`

Convenience function for text embeddings.

**Parameters:**
- `text` (str | List[str]): Text or list of texts to embed
- `model` (str, optional): Specific model (default: text-embedding-3-small)
- `normalize` (bool, optional): Whether to normalize embeddings (default: True)
- `**kwargs`: Additional parameters passed to ISA client

**Returns:**
- `List[float]` for single text (1536 dimensions)
- `List[List[float]]` for batch of texts

### `similarity(text1, text2, **kwargs)`

Compute cosine similarity between two texts.

**Parameters:**
- `text1` (str): First text
- `text2` (str): Second text
- `model` (str, optional): Model to use for embeddings
- `**kwargs`: Additional parameters

**Returns:**
- `float`: Similarity score (0.0-1.0)

### `search(query, candidates, top_k=5, **kwargs)`

Find most similar texts to a query.

**Parameters:**
- `query` (str): Query text
- `candidates` (List[str]): List of candidate texts
- `top_k` (int, optional): Number of results (default: 5)
- `**kwargs`: Additional parameters

**Returns:**
- `List[Tuple[str, float]]`: List of (text, similarity_score) tuples

### `chunk(text, chunk_size=400, overlap=50, **kwargs)`

Chunk text into smaller pieces with embeddings.

**Parameters:**
- `text` (str): Text to chunk
- `chunk_size` (int, optional): Size of each chunk (default: 400)
- `overlap` (int, optional): Overlap between chunks (default: 50)
- `metadata` (dict, optional): Additional metadata
- `**kwargs`: Additional parameters

**Returns:**
- `List[dict]`: List of chunks with text, embeddings, and metadata

### `rerank(query, documents, top_k=5, **kwargs)`

Rerank documents by relevance using ISA Jina Reranker v2.

**Parameters:**
- `query` (str): Query text
- `documents` (List[str]): Documents to rerank
- `top_k` (int, optional): Number of results (default: 5)
- `model` (str, optional): Reranker model (default: isa-jina-reranker-v2-service)
- `**kwargs`: Additional parameters

**Returns:**
- `List[dict]`: Reranked documents with relevance scores

## Parameters

### Models
- **text-embedding-3-small**: 1536 dimensions, fast, cost-effective (default)
- **text-embedding-3-large**: 3072 dimensions, highest quality
- **bge-m3**: 1024 dimensions, free (local), good for development

### Chunking
- **chunk_size**: 400 characters optimal for most embedding models
- **overlap**: 50 characters good balance for context preservation

### Reranking
- **ISA Jina Reranker v2**: State-of-the-art 2024 model, 100+ languages

## Examples

### RAG Pipeline
```python
async def rag_pipeline(documents, query):
    # Step 1: Chunk documents
    all_chunks = []
    for doc in documents:
        chunks = await chunk(doc, chunk_size=400, overlap=50)
        all_chunks.extend(chunks)
    
    # Step 2: Similarity search
    chunk_texts = [c["text"] for c in all_chunks]
    similar = await search(query, chunk_texts, top_k=10)
    
    # Step 3: Rerank for precision
    candidates = [text for text, _ in similar]
    final = await rerank(query, candidates, top_k=5)
    
    return final
```

### Semantic Search System
```python
class SemanticSearchSystem:
    def __init__(self):
        self.generator = EmbeddingGenerator()
        self.documents = {}
    
    async def index_documents(self, docs):
        texts = list(docs.values())
        embeddings = await self.generator.embed_batch(texts)
        
        for doc_id, text, embedding in zip(docs.keys(), texts, embeddings):
            self.documents[doc_id] = {"text": text, "embedding": embedding}
    
    async def search(self, query, top_k=5):
        candidate_texts = [doc["text"] for doc in self.documents.values()]
        return await self.generator.find_most_similar(query, candidate_texts, top_k=top_k)
```

## Error Handling

The generator handles ISA client complexities automatically and provides meaningful error messages.

```python
try:
    embedding = await embed("Hello world")
    print(f"Success: {len(embedding)} dimensions")
except Exception as e:
    if "ISA embedding failed" in str(e):
        print(f"Service error: {e}")
    elif "No embedding in response" in str(e):
        print(f"Data error: {e}")
    else:
        print(f"Unexpected error: {e}")
```

## Performance Notes

- **Cost**: text-embedding-3-small: $0.02/1M tokens, text-embedding-3-large: $0.13/1M tokens
- **Speed**: Embedding generation typically takes 1-3 seconds per batch
- **Dimensions**: 1536 (small) or 3072 (large) per embedding vector
- **Reranking**: ~2-5 docs/second, $0.0002/request
- **Batching**: ISA handles batch optimization automatically

## Integration

### In MCP Tools
```python
from tools.services.intelligence_service.language.embedding_generator import embed, similarity

class SemanticTool(BaseTool):
    async def process_request(self, user_input, knowledge_base):
        # Find relevant knowledge
        results = await search(user_input, knowledge_base, top_k=3)
        
        # Use most relevant content
        context = results[0][0] if results else ""
        return f"Based on: {context}"
```

### In Services
```python
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator

class MemoryService:
    def __init__(self):
        self.embedder = EmbeddingGenerator()
    
    async def store_memory(self, content):
        embedding = await self.embedder.embed_single(content)
        await self.db.store_memory(content, embedding)
    
    async def search_memories(self, query):
        return await self.embedder.find_most_similar(
            query, 
            self.get_memory_texts(),
            top_k=10
        )
```

## Testing

Run the test suite:
```bash
python -m tools.services.intelligence_service.language.tests.test_embedding_generator
```

### Verified Test Results

All core features tested with actual ISA client (14/15 tests passed, 1 skipped):

- ✅ **Single Embeddings**: 1536 dimensions (text-embedding-3-small)
- ✅ **Batch Embeddings**: Multiple texts processed efficiently 
- ✅ **Similarity Computation**: Real cosine similarity (0.588 between "machine learning" and "artificial intelligence")
- ✅ **Similarity Search**: Ranked results with relevance scores (0.433, 0.332 for ML topics)
- ✅ **Text Chunking**: Returns chunks with text, embeddings, indices, and metadata
- ✅ **Document Reranking**: ISA Jina Reranker v2 with relevance scores (0.690, 0.147, 0.090)
- ✅ **Model Parameters**: Custom models and normalization work correctly
- ✅ **Convenience Functions**: All wrapper functions operational

The tests cover:
- Single and batch embedding generation
- Similarity computation and search
- Text chunking with embeddings
- Document reranking with ISA Jina Reranker v2
- Model parameter variations
- All convenience functions

## Summary

The embedding generator provides a simple, clean interface to ISA's embedding capabilities:
- **Simple**: Just call `embed(text)` and get vectors back
- **Flexible**: Single/batch, similarity, chunking, reranking all in one service
- **Robust**: Handles ISA client complexities automatically
- **Efficient**: Leverages ISA's built-in caching and optimization
- **Easy Integration**: Works seamlessly with existing tools and services

Perfect for any application that needs AI embeddings, similarity search, or document reranking without the complexity of handling multiple embedding APIs.