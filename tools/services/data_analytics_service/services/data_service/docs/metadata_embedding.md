# AI-Powered Metadata Embedding Service Documentation

## Overview

The **AI-Powered Metadata Embedding Service** is Step 3 of the data analytics pipeline that generates vector embeddings from semantic metadata and stores them in pgvector for efficient similarity search. It has been upgraded to use the `intelligence_service.embedding_generator` for state-of-the-art embedding generation with advanced features like batch processing and AI-powered reranking.

## Features

### 🤖 AI-Powered Embedding Generation
- **Text Embedding 3 Small** - 1536 dimensions, cost-effective, high quality
- **Batch Processing** - Efficient processing of multiple texts simultaneously
- **Embedding Caching** - Intelligent caching to reduce costs and improve performance
- **Fallback Support** - Graceful fallback to direct ISA client when AI service unavailable

### 🔍 Advanced Search Capabilities
- **Similarity Search** - Vector similarity search using pgvector
- **AI-Powered Reranking** - Enhanced relevance using ISA Jina Reranker v2
- **Entity Type Filtering** - Filter search results by metadata type
- **Confidence Thresholds** - Adjustable similarity thresholds

### 📊 Comprehensive Storage
- **Business Entities** - Table and entity metadata with embeddings
- **Semantic Tags** - Semantic annotations with vector representations
- **Business Rules** - Inferred rules stored as searchable embeddings
- **Data Patterns** - Detected patterns with semantic similarity

## Quick Start

```python
from tools.services.data_analytics_service.services.data_service.metadata_embedding import get_embedding_service
from tools.services.data_analytics_service.services.data_service.semantic_enricher import enrich_metadata

# Get embedding service instance
embedding_service = get_embedding_service("my_database")

# Process metadata from Steps 1-2
semantic_metadata = await enrich_metadata(raw_metadata)

# Store embeddings in pgvector
results = await embedding_service.store_semantic_metadata(semantic_metadata)
print(f"Stored {results['stored_embeddings']} embeddings")

# Search for similar entities
search_results = await embedding_service.search_with_reranking(
    "ecommerce customer data",
    limit=5
)
```

## API Reference

### AIMetadataEmbeddingService Class

```python
class AIMetadataEmbeddingService(BaseService):
    """AI-powered metadata embedding generation and storage"""
    
    def __init__(self, database_source: str = "customs_trade_db"):
        """Initialize service with database source identifier"""
        
    async def store_semantic_metadata(self, semantic_metadata: SemanticMetadata) -> Dict[str, Any]:
        """Store semantic metadata with AI-generated embeddings"""
        
    async def search_similar_entities(self, query: str, entity_type: Optional[str] = None, 
                                    limit: int = 10, similarity_threshold: float = 0.7) -> List[SearchResult]:
        """Search for similar entities using embedding similarity"""
        
    async def search_with_reranking(self, query: str, entity_type: Optional[str] = None,
                                  limit: int = 10, similarity_threshold: float = 0.7,
                                  use_reranking: bool = True) -> List[SearchResult]:
        """Enhanced search with AI-powered reranking for better relevance"""
```

### Data Classes

```python
@dataclass
class EmbeddingRecord:
    """Record structure for stored embeddings"""
    id: str
    entity_type: str  # 'table', 'column', 'business_rule', 'semantic_tags', 'data_pattern'
    entity_name: str
    entity_full_name: str
    content: str
    embedding: List[float]  # 1536 dimensions
    metadata: Dict[str, Any]
    semantic_tags: List[str]
    confidence_score: float
    created_at: datetime
    updated_at: datetime

@dataclass
class SearchResult:
    """Search result from embedding similarity search"""
    entity_name: str
    entity_type: str
    similarity_score: float  # 0.0-1.0 (cosine similarity or reranking score)
    content: str
    metadata: Dict[str, Any]
    semantic_tags: List[str]
```

## Input Format

The service expects `SemanticMetadata` from Step 2 (semantic enricher):

```python
semantic_metadata = SemanticMetadata(
    original_metadata={...},  # From Step 1
    business_entities=[
        {
            "entity_name": "customer_orders",
            "entity_type": "transactional",
            "confidence": 0.85,
            "business_importance": "high",
            "record_count": 15000,
            "key_attributes": ["order_id", "customer_id", "total_amount"]
        }
    ],
    semantic_tags={
        "table:customer_orders": ["pattern:transactional", "domain:ecommerce"],
        "column:customer_orders.order_id": ["semantic:identifier"]
    },
    business_rules=[
        {
            "rule_type": "data_constraint",
            "description": "Order ID must be unique and non-null",
            "confidence": 0.9
        }
    ],
    data_patterns=[
        {
            "pattern_type": "temporal_pattern", 
            "description": "Orders follow seasonal patterns",
            "confidence": 0.7
        }
    ]
)
```

## Output Examples

### Storage Results

```json
{
  "stored_embeddings": 8,
  "failed_embeddings": 0,
  "storage_time": "2025-07-18T15:30:45.123456",
  "errors": [],
  "billing_info": {
    "cost_usd": 0.00456,
    "operations": [
      {"operation": "embed_batch", "cost": 0.00456, "tokens": 1280}
    ]
  }
}
```

### Search Results

```json
[
  {
    "entity_name": "customer_orders",
    "entity_type": "table",
    "similarity_score": 0.892,
    "content": "Table: customer_orders, Type: transactional, Importance: high, Records: 15000",
    "metadata": {
      "business_importance": "high",
      "record_count": 15000,
      "key_attributes": ["order_id", "customer_id", "total_amount"]
    },
    "semantic_tags": ["pattern:transactional", "domain:ecommerce"]
  },
  {
    "entity_name": "data_constraint", 
    "entity_type": "business_rule",
    "similarity_score": 0.745,
    "content": "Business rule (data_constraint): Order ID must be unique and non-null",
    "metadata": {},
    "semantic_tags": ["rule:data_constraint"]
  }
]
```

## AI Integration Details

### Embedding Generation

The service uses `intelligence_service.embedding_generator` for:

1. **Single Embeddings** - `embed(text)` for individual content
2. **Batch Embeddings** - `embed([text1, text2, ...])` for efficient batch processing
3. **Caching** - Automatic caching based on text hash to reduce costs
4. **1536 Dimensions** - Using text-embedding-3-small for optimal cost/performance

### AI-Powered Reranking

Enhanced search uses ISA Jina Reranker v2:

```python
# First: Get similarity search results
initial_results = await search_similar_entities(query, limit=20)

# Then: Rerank using AI for better relevance
reranked_results = await rerank(query, documents, top_k=10)

# Result: Better relevance ordering with reranking scores
```

### Content Processing

Different metadata types are processed into searchable text:

```python
# Business Entity Content
"Table: customer_orders, Type: transactional, Importance: high, Records: 15000, Key attributes: order_id, customer_id, total_amount"

# Semantic Tags Content  
"Table: customer_orders has semantic tags: pattern:transactional, domain:ecommerce, importance:high"

# Business Rule Content
"Business rule (data_constraint): Order ID must be unique and non-null for transaction integrity"

# Data Pattern Content
"Data pattern (temporal_pattern): Orders follow seasonal patterns with peak during holidays"
```

## Usage Examples

### Complete Pipeline Integration

```python
from tools.services.data_analytics_service.processors.data_processors.metadata_extractor import extract_metadata
from tools.services.data_analytics_service.services.data_service.semantic_enricher import enrich_metadata
from tools.services.data_analytics_service.services.data_service.metadata_embedding import get_embedding_service

async def complete_metadata_pipeline(data_source_path, database_name):
    """Complete Steps 1-3 pipeline"""
    
    # Step 1: Extract metadata
    raw_metadata = extract_metadata(data_source_path)
    if 'error' in raw_metadata:
        return {'error': f"Metadata extraction failed: {raw_metadata['error']}"}
    
    # Step 2: Enrich with AI semantic analysis  
    semantic_metadata = await enrich_metadata(raw_metadata)
    
    # Step 3: Generate embeddings and store
    embedding_service = get_embedding_service(database_name)
    storage_results = await embedding_service.store_semantic_metadata(semantic_metadata)
    
    return {
        'success': True,
        'stored_embeddings': storage_results['stored_embeddings'],
        'ai_analysis_source': semantic_metadata.ai_analysis['source'],
        'pipeline_cost': storage_results.get('billing_info', {}).get('cost_usd', 0)
    }
```

### Search and Discovery

```python
async def search_metadata_knowledge(query, database_name):
    """Search across all stored metadata"""
    
    embedding_service = get_embedding_service(database_name)
    
    # Enhanced search with AI reranking
    results = await embedding_service.search_with_reranking(
        query=query,
        limit=10,
        similarity_threshold=0.6,
        use_reranking=True
    )
    
    # Process results by type
    entities = [r for r in results if r.entity_type == 'table']
    rules = [r for r in results if r.entity_type == 'business_rule']
    patterns = [r for r in results if r.entity_type == 'data_pattern']
    
    return {
        'entities': len(entities),
        'rules': len(rules), 
        'patterns': len(patterns),
        'top_result': results[0] if results else None
    }
```

### Batch Processing

```python
async def process_multiple_datasets(datasets, database_name):
    """Process multiple datasets efficiently"""
    
    embedding_service = get_embedding_service(database_name)
    
    for dataset_info in datasets:
        # Process each dataset through pipeline
        raw_metadata = extract_metadata(dataset_info['path'])
        semantic_metadata = await enrich_metadata(raw_metadata)
        
        # Store with batch optimization
        results = await embedding_service.store_semantic_metadata(semantic_metadata)
        
        print(f"Dataset {dataset_info['name']}: {results['stored_embeddings']} embeddings stored")
```

### Cross-Database Search

```python
async def search_across_databases(query, database_names):
    """Search across multiple databases"""
    
    all_results = []
    
    for db_name in database_names:
        service = get_embedding_service(db_name)
        results = await service.search_with_reranking(query, limit=5)
        
        # Add database context
        for result in results:
            result.metadata['database_source'] = db_name
            all_results.append(result)
    
    # Sort by similarity score
    all_results.sort(key=lambda x: x.similarity_score, reverse=True)
    
    return all_results[:10]  # Top 10 across all databases
```

## Performance & Costs

### Embedding Generation
- **Cost**: ~$0.02 per 1M tokens (text-embedding-3-small)
- **Speed**: 2-5 seconds for batch embedding generation
- **Dimensions**: 1536 per embedding vector
- **Caching**: Reduces duplicate embedding costs by ~60-80%

### Storage Performance
- **Typical Dataset**: 100-500 embeddings per database
- **Storage Time**: 10-30 seconds for full semantic metadata
- **pgvector Search**: Sub-second similarity search
- **Reranking**: 2-5 documents/second, $0.0002/request

### Cost Optimization Tips
- Use embedding caching for repeated content
- Batch process multiple texts together
- Set appropriate similarity thresholds
- Monitor billing through service billing info

## Database Schema

The service stores embeddings in the `db_meta_embedding` table:

```sql
CREATE TABLE db_meta_embedding (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    entity_full_name TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- pgvector extension
    metadata JSONB,
    semantic_tags TEXT[],
    confidence_score FLOAT,
    source_step INTEGER,
    database_source TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient search
CREATE INDEX ON db_meta_embedding USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON db_meta_embedding (entity_type);
CREATE INDEX ON db_meta_embedding (database_source);
```

## Error Handling

### Graceful Fallback

```python
# AI service unavailable - automatic fallback
if not service.embedding_generator:
    logger.warning("Using fallback ISA client for embedding generation")
    # Falls back to direct ISA client calls
```

### Storage Error Recovery

```python
# Individual embedding failures don't stop batch processing
results = await service.store_semantic_metadata(semantic_metadata)

if results['failed_embeddings'] > 0:
    print(f"Some embeddings failed: {results['errors']}")
    # Process successful embeddings, retry failed ones
```

### Search Error Handling

```python
try:
    results = await service.search_with_reranking(query)
except Exception as e:
    # Fallback to basic similarity search
    results = await service.search_similar_entities(query)
```

## Configuration

### Embedding Models

```python
# Default: text-embedding-3-small (1536 dimensions, cost-effective)
embedding = await embed(text)

# Alternative: Use different model via embedding generator
embedding = await embed(text, model="text-embedding-3-large")  # 3072 dimensions, higher quality
```

### Search Parameters

```python
# Configure search behavior
results = await service.search_with_reranking(
    query="customer data",
    entity_type="table",           # Filter by type
    limit=10,                      # Max results
    similarity_threshold=0.7,      # Min similarity
    use_reranking=True            # Enable AI reranking
)
```

### Database Configuration

```python
# Multiple database sources
service_db1 = get_embedding_service("ecommerce_db")
service_db2 = get_embedding_service("analytics_db") 
service_db3 = get_embedding_service("crm_db")
```

## Testing

### Test Suite

Run the comprehensive test suite:

```bash
cd tools/services/data_analytics_service/services/data_service/tests
python test_metadata_embedding.py
```

### Expected Results

```
🤖 AI-Powered Metadata Embedding Service Test Suite
============================================================
🤖 Testing AI Metadata Embedding Service Initialization
✅ AI embedding generator available
   Database source: test_db
   Service name: AIMetadataEmbeddingService

🧠 Testing AI Embedding Generation  
✅ Generated embedding with 1536 dimensions
✅ Generated 3 batch embeddings

📊 Testing Semantic Metadata Processing
   📋 Processing 1 business entities
   🏷️  Processing 3 semantic tag groups
   📝 Processing 1 business rules
   🔍 Processing 1 data patterns
   ✅ Generated 6/6 embeddings successfully
✅ Semantic metadata processing test passed!

🔍 Testing Search and Reranking Functionality
   🔎 Testing search query embedding generation
   ✅ Generated embedding for: ecommerce customer data...
   ✅ Generated embedding for: transactional patterns...
   ✅ Generated embedding for: business rules for orders...
   🎯 AI reranking successful - 3 results
      1. Score: 0.854 - Customer orders table with ecommerce transaction...
      2. Score: 0.245 - Business rule: Order ID must be unique for data...
      3. Score: 0.123 - Inventory management system for product track...
✅ Search and reranking test passed!

🔧 Testing Convenience Functions
   ✅ Global instance management working
   ✅ Backward compatibility working
✅ Convenience functions test passed!

============================================================
🤖 AI Metadata Embedding Service Test Summary
============================================================
Total tests: 5
Passed: 5
Failed: 0
✅ All tests passed!

📋 Test Details:
   1. Service Initialization: ✅ PASS
   2. Embedding Generation: ✅ PASS
   3. Semantic Metadata Processing: ✅ PASS
   4. Search and Reranking: ✅ PASS
   5. Convenience Functions: ✅ PASS

🤖 AI embedding generator is available and working!
```

**Latest Integration Test Results (with metadata_store_service.py):**
- ✅ Step 1 (Extraction): 0.01s - Found 1 table, 5 columns
- ✅ Step 2 (Enrichment): 29.80s - Generated 1 business entity, 6 semantic tags  
- ✅ Step 3 (Storage): 11.44s - **17 embeddings stored successfully**
- ✅ Search Ready: True
- ✅ Total Duration: 41.25s
- ✅ **Schema Issue Resolved**: Using correct `dev` schema and `db_meta_embedding` table

## Integration with Data Analytics Pipeline

### Pipeline Flow: Steps 1 → 2 → 3

```python
# Complete pipeline automation
async def automated_data_analysis_pipeline(data_source, database_name):
    """Automated pipeline from raw data to searchable embeddings"""
    
    print("📊 Step 1: Extracting metadata...")
    raw_metadata = extract_metadata(data_source)
    
    print("🧠 Step 2: AI semantic enrichment...")
    semantic_metadata = await enrich_metadata(raw_metadata)
    
    print("🤖 Step 3: AI embedding generation and storage...")
    embedding_service = get_embedding_service(database_name)
    results = await embedding_service.store_semantic_metadata(semantic_metadata)
    
    return {
        'pipeline_status': 'completed',
        'tables_analyzed': len(raw_metadata.get('tables', [])),
        'ai_analysis_source': semantic_metadata.ai_analysis['source'],
        'embeddings_stored': results['stored_embeddings'],
        'search_ready': True
    }
```

### Next Steps Integration

Ready for Steps 4-6:
- **Step 4**: Query matching using embedding similarity search
- **Step 5**: SQL generation from matched semantic context
- **Step 6**: Query execution with semantic understanding

## Limitations

- Requires active intelligence_service for full AI functionality
- pgvector database extension required for vector similarity search
- Embedding costs accumulate with large-scale processing
- 1536-dimensional vectors require ~6KB storage per embedding
- Reranking limited to smaller result sets for performance

## Dependencies

- `tools.services.intelligence_service.language.embedding_generator`
- `core.database.supabase_client` - pgvector database connection
- `tools.base_service` - Base service functionality with billing
- `pgvector` - PostgreSQL vector similarity search
- `asyncio` - Async/await support
- `typing` - Type hints
- `dataclasses` - Structured data classes

## Summary

The AI-Powered Metadata Embedding Service successfully transforms semantic metadata into searchable vector embeddings using state-of-the-art AI embedding models. It provides:

- **Advanced AI Integration** - text-embedding-3-small with 1536 dimensions
- **Efficient Batch Processing** - Cost-effective bulk embedding generation
- **Enhanced Search** - Similarity search with AI-powered reranking
- **Robust Storage** - pgvector integration with comprehensive metadata
- **Production Performance** - Caching, error handling, and billing tracking

Use this service as Step 3 in your data analytics pipeline to enable semantic search and similarity-based data discovery across your metadata catalog.