# Migration Guide - Vector Database and Guardrail Systems

This guide covers migration paths for deprecated services to their modern, unified replacements.

## 🔄 ChromaDB Service Migration

### What's Changing

The standalone `ChromaService` is being replaced by the unified vector database abstraction layer.

**Deprecated (Old):**
```python
from tools.services.intelligence_service.vector.chroma_service import ChromaService
```

**Recommended (New):**
```python
from tools.services.intelligence_service.vector_db import ChromaVectorDB
```

### Migration Steps

#### 1. Update Imports

**Before:**
```python
from tools.services.intelligence_service.vector.chroma_service import ChromaService, get_chroma_service

# Initialize
service = ChromaService()
# or
service = get_chroma_service()
```

**After:**
```python
from tools.services.intelligence_service.vector_db import ChromaVectorDB
from tools.services.intelligence_service.vector_db.vector_db_factory import create_vector_db

# Initialize
config = {'collection_name': 'my_collection'}
service = ChromaVectorDB(config)
# or use factory
service = create_vector_db('chromadb', config)
```

#### 2. Update Method Calls

**Before:**
```python
# Create collection
collection_name = service.create_collection("my_collection")

# Add documents
result = await service.add_documents(
    collection_name=collection_name,
    documents=["doc1", "doc2"],
    ids=["id1", "id2"]
)

# Query
result = await service.query_collection(
    collection_name=collection_name,
    query_texts=["search query"],
    n_results=5
)
```

**After:**
```python
# Store vectors (replaces add_documents)
success = await service.store_vector(
    id="id1",
    text="doc1", 
    embedding=embedding,
    user_id="user123"
)

# Search vectors (replaces query_collection)
from tools.services.intelligence_service.vector_db.base_vector_db import VectorSearchConfig
config = VectorSearchConfig(top_k=5)
results = await service.search_vectors(
    query_embedding=query_embedding,
    user_id="user123",
    config=config
)
```

#### 3. Handle Response Format Changes

**Before:**
```python
# Old response format
{
    "status": "success",
    "results": {
        "documents": [["doc1", "doc2"]],
        "distances": [[0.1, 0.2]]
    }
}
```

**After:**
```python
# New response format (SearchResult objects)
[
    SearchResult(
        id="id1",
        text="doc1",
        score=0.9,  # 1 - distance
        semantic_score=0.9,
        metadata={"user_id": "user123"}
    )
]
```

### Benefits of Migration

1. **Unified Interface**: Same API works with ChromaDB, Supabase pgvector, and Qdrant
2. **User Isolation**: Built-in user isolation and access control
3. **Hybrid Search**: Integration with hybrid search capabilities
4. **Better Error Handling**: Consistent error handling across all databases
5. **Type Safety**: Proper type hints and SearchResult objects

## 🛡️ Guardrail System Integration

### What's Changing

The separate quality and compliance guardrail systems are now unified.

**Components:**
- **Quality Guardrails**: `guardrail_system.py` (RAG quality validation)
- **Compliance Guardrails**: `guardrail_resources.py` (PII/medical compliance)
- **Unified System**: `unified_guardrail_service.py` (integrated approach)

### Migration to Unified System

#### 1. Replace Separate Systems

**Before:**
```python
# Separate quality and compliance checks
from tools.services.intelligence_service.guardrails import GuardrailSystem
from resources.guardrail_resources import GuardrailChecker

quality_system = GuardrailSystem()
compliance_checker = GuardrailChecker()

# Manual coordination needed
quality_result = await quality_system.validate_result(query, result)
compliance_result = compliance_checker.apply_guardrails(text)
```

**After:**
```python
# Unified approach
from tools.services.intelligence_service.guardrails import get_unified_guardrail_service

service = get_unified_guardrail_service()

# Automatic coordination
result = await service.validate_content(
    content=text,
    query=query,
    context=context
)
```

#### 2. Configure Integration Behavior

```python
from tools.services.intelligence_service.guardrails import UnifiedGuardrailConfig, GuardrailLevel

config = UnifiedGuardrailConfig(
    # Quality settings
    quality_level=GuardrailLevel.MODERATE,
    enable_quality_checks=True,
    
    # Compliance settings  
    compliance_mode="moderate",  # "strict", "moderate", "permissive"
    enable_compliance_checks=True,
    
    # Integration settings
    priority_mode="compliance_first",  # "compliance_first", "quality_first", "balanced"
    fail_on_any_violation=False,
    enable_sanitization=True
)

service = get_unified_guardrail_service(config)
```

#### 3. Handle Unified Results

```python
result = await service.validate_content(content="...", query="...")

# Comprehensive result structure
{
    "overall_status": "APPROVED",  # "APPROVED", "SANITIZED", "WARNING", "BLOCKED", "ERROR"
    "overall_message": "Content approved",
    "sanitized_content": "...",  # Sanitized version if needed
    "quality_validation": {...},
    "compliance_validation": {...},
    "recommendations": [...],
    "risk_assessment": {
        "overall_risk": "LOW",  # "LOW", "MEDIUM", "HIGH"
        "quality_risk": "LOW",
        "compliance_risk": "LOW"
    }
}
```

### Specialized RAG Validation

For RAG-specific use cases:

```python
result = await service.validate_rag_response(
    query="What is machine learning?",
    response="Machine learning is...",
    source_documents=[{"text": "ML definition..."}, ...],
    metadata={"model": "gpt-4"}
)

# Includes RAG-specific analysis
{
    "overall_status": "APPROVED",
    "quality_validation": {...},
    "compliance_validation": {...},
    "rag_specific_validation": {
        "attribution_score": 0.85,
        "factual_consistency": 0.92
    }
}
```

## 📈 Performance Considerations

### ChromaDB Migration

- **Memory Usage**: New abstraction layer has slightly higher memory usage due to unified interface
- **Performance**: Similar performance, but better caching and error handling
- **Scalability**: Better suited for multi-user environments

### Guardrail System

- **Parallel Processing**: Unified system can run quality and compliance checks in parallel
- **Caching**: Built-in validation result caching reduces redundant checks
- **Early Exit**: Smart early exit strategies reduce processing time

## 🔄 Gradual Migration Strategy

### Phase 1: Add New Alongside Old
```python
# Keep existing code working
from tools.services.intelligence_service.vector.chroma_service import get_chroma_service
old_service = get_chroma_service()

# Add new service for new features
from tools.services.intelligence_service.vector_db import ChromaVectorDB
new_service = ChromaVectorDB()
```

### Phase 2: Route New Features to New System
```python
# Route new functionality to new system
if feature_flag_enabled("new_vector_db"):
    service = new_service
else:
    service = old_service
```

### Phase 3: Migrate Existing Features
```python
# Gradually migrate existing features
# Update imports and method calls one by one
```

### Phase 4: Remove Old System
```python
# Remove old imports and deprecated code
# Update all references to new system
```

## ⚠️ Breaking Changes

### ChromaDB Service

1. **Method Signatures**: Changed from collection-based to user-based operations
2. **Response Format**: SearchResult objects instead of raw ChromaDB responses
3. **Configuration**: Different configuration structure for the abstraction layer

### Guardrail System

1. **Import Paths**: Use unified service instead of separate systems
2. **Result Format**: Comprehensive result structure instead of separate responses
3. **Configuration**: New unified configuration object

## 🆘 Troubleshooting

### Common Issues

1. **Import Errors**: Update import paths to use new modules
2. **Method Not Found**: Check method name changes in migration guide
3. **Response Format**: Update code to handle new SearchResult objects
4. **Configuration**: Use new configuration classes

### Getting Help

- Check deprecation warnings in logs
- Review test files for usage examples
- Use the gradual migration strategy
- Test with feature flags before full migration

## ✅ Validation

After migration, validate that:

1. **Functionality**: All features work as expected
2. **Performance**: No significant performance regression
3. **Compatibility**: Integration with other systems works
4. **Testing**: All tests pass with new implementation

---

*Last updated: August 16, 2025*