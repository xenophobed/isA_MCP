# Digital Service RAG Architecture

## 📁 File Relationships & Architecture Overview

This document explains the relationships between all RAG-related files and how they work together.

## 🏗️ Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Tool Layer (digital_tools.py)            │
│  - Exposes: store_knowledge, search_knowledge, knowledge_response│
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ calls get_rag_service(mode='simple')
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│               Factory Layer (base/rag_factory.py) **MISSING**    │
│  - Creates appropriate RAG service based on mode                 │
│  - get_rag_service(mode) → returns BaseRAGService instance      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ creates
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│          Pattern Layer (patterns/simple_rag_service.py)          │
│  - Implements specific RAG pattern (Simple, Custom, CRAG, etc.)  │
│  - Uses: Qdrant (vectors), ISA Model (embeddings/LLM)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ extends
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│          Base Layer (base/base_rag_service.py)                   │
│  - Abstract base class with 3 core methods:                      │
│    • store(RAGStoreRequest) → RAGResult                         │
│    • retrieve(RAGRetrieveRequest) → RAGResult                   │
│    • generate(RAGGenerateRequest) → RAGResult                   │
│  - Provides utility methods: _chunk_text, _generate_embedding    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ uses
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│          Data Models (base/rag_models.py)                        │
│  - Pydantic models for type safety and validation:               │
│    • RAGConfig, RAGMode (enum)                                  │
│    • RAGStoreRequest, RAGRetrieveRequest, RAGGenerateRequest    │
│    • RAGResult, RAGSource                                       │
└─────────────────────────────────────────────────────────────────┘
```

## 📂 File Breakdown

### Core Files (New Architecture - ✅ Migrated)

#### 1. `base/rag_models.py`
**Purpose**: Define all data contracts using Pydantic
**Key Classes**:
- `RAGMode` - Enum for RAG modes (SIMPLE, GRAPH, CUSTOM, etc.)
- `RAGConfig` - Configuration with validation (chunk_size, top_k, etc.)
- `RAGStoreRequest` - Request model for storing content
- `RAGRetrieveRequest` - Request model for retrieval
- `RAGGenerateRequest` - Request model for generation
- `RAGResult` - Unified response format
- `RAGSource` - Individual retrieval source with score

**Usage Example**:
```python
from base.rag_models import RAGStoreRequest, RAGConfig, RAGMode

config = RAGConfig(mode=RAGMode.SIMPLE, chunk_size=400, top_k=5)
request = RAGStoreRequest(
    content="Python is a programming language",
    user_id="user123",
    content_type="text"
)
```

#### 2. `base/base_rag_service.py`
**Purpose**: Abstract base class for all RAG implementations
**Key Methods**:
- `__init__(config: RAGConfig)` - Initialize with config
- **Abstract**:
  - `store(request: RAGStoreRequest) → RAGResult`
  - `retrieve(request: RAGRetrieveRequest) → RAGResult`
  - `generate(request: RAGGenerateRequest) → RAGResult`
- **Utilities**:
  - `_chunk_text()` - Split text into chunks
  - `_generate_embedding()` - Generate embeddings via ISA Model
  - `_generate_response()` - Generate LLM response via ISA Model
  - `_build_context()` - Build context from sources

**Key Design Principles**:
- ❌ NO concrete storage initialization (no Supabase, no Qdrant here)
- ✅ Each pattern decides its own storage needs
- ✅ Direct ISA Model integration (no middle layers)

#### 3. `base/rag_factory.py` ⚠️  **ISSUE: SHOULD EXIST BUT MISSING**
**Purpose**: Factory pattern to create RAG service instances
**Expected Location**: `tools/services/data_analytics_service/services/digital_service/base/rag_factory.py`
**Current Problem**: File doesn't exist, but `digital_tools.py` imports from this path!

**Should Provide**:
```python
def get_rag_service(mode: str = "simple", config: Optional[Dict] = None) -> BaseRAGService:
    """Create RAG service based on mode"""
    if mode == "simple":
        return SimpleRAGService(RAGConfig(**config))
    # ... other modes
```

#### 4. `patterns/simple_rag_service.py`
**Purpose**: Simple vector RAG implementation
**Storage**: Qdrant only
**Key Implementation**:
```python
class SimpleRAGService(BaseRAGService):
    def __init__(self, config: RAGConfig):
        super().__init__(config)
        # Initialize Qdrant client directly
        self.qdrant_client = QdrantClient(host='isa-qdrant-grpc', port=50062)

    async def store(self, request: RAGStoreRequest) -> RAGResult:
        # 1. Chunk text
        chunks = self._chunk_text(request.content)
        # 2. Generate embeddings (via ISA Model)
        # 3. Store to Qdrant
        # 4. Return RAGResult

    async def retrieve(self, request: RAGRetrieveRequest) -> RAGResult:
        # 1. Generate query embedding
        # 2. Search Qdrant
        # 3. Return RAGResult with sources

    async def generate(self, request: RAGGenerateRequest) -> RAGResult:
        # 1. Build context from sources
        # 2. Generate response (via ISA Model)
        # 3. Return RAGResult with content
```

### Legacy Files (Old Architecture - ⏳ To Be Deprecated)

#### 5. `rag_service.py` (root directory)
**Status**: OLD - Being replaced by new pattern-based approach
**Issues**:
- Uses Supabase directly
- Uses `intelligence_service/embedding_generator` middle layers
- Monolithic design (not pattern-based)

**Migration Path**: Functionality moved to `patterns/*_rag_service.py`

#### 6. `rag_factory.py` (root directory)
**Status**: OLD - Complex registry pattern
**Issues**:
- Different design from new base/rag_factory.py
- Uses old class-based factory with registration

**Migration Path**: Should be replaced by simpler `base/rag_factory.py`

#### 7. `enhanced_digital_service.py`
**Status**: HIGH-LEVEL ORCHESTRATOR - May need updates
**Purpose**: Coordinates multiple services with policy-based config
**Key Features**:
- VectorDBPolicy (AUTO, PERFORMANCE, STORAGE, etc.)
- ProcessingMode (SEQUENTIAL, PARALLEL, BATCH, STREAMING)
- Integrates PDF processing, guardrails, caching

**Relationship**:
- **USES** RAG services via factory
- **PROVIDES** high-level analytics capabilities
- **COORDINATES** multiple backend services

## 🔄 Data Flow

### Store Knowledge Flow
```
User → digital_tools.store_knowledge()
     → get_rag_service(mode='simple')
     → SimpleRAGService.store(RAGStoreRequest)
     → _chunk_text() → _generate_embedding() → qdrant_client.upsert_points()
     → Return RAGResult
```

### Search Knowledge Flow
```
User → digital_tools.search_knowledge()
     → get_rag_service(mode='simple')
     → SimpleRAGService.retrieve(RAGRetrieveRequest)
     → _generate_embedding() → qdrant_client.search_points()
     → Convert to RAGSource objects
     → Return RAGResult with sources
```

### Generate Response Flow
```
User → digital_tools.knowledge_response()
     → get_rag_service(mode='simple')
     → SimpleRAGService.generate(RAGGenerateRequest)
     → _build_context() → _generate_response()
     → Return RAGResult with generated content
```

## 🎯 Key Architectural Decisions

### 1. **No Middle Layers**
- ❌ OLD: `rag_service.py` → `embedding_generator` → `isa_model`
- ✅ NEW: `simple_rag_service.py` → `isa_model.AsyncISAModel` (direct)

### 2. **Storage Responsibility**
- ❌ OLD: Base class initializes Supabase for everyone
- ✅ NEW: Each pattern decides its own storage:
  - `SimpleRAG` → Qdrant only
  - `CustomRAG` → MinIO + Qdrant
  - `GraphRAG` → Neo4j + Qdrant

### 3. **Type Safety with Pydantic**
- All requests/responses use Pydantic models
- Automatic validation (e.g., `user_id` cannot be empty)
- Clear data contracts between layers

### 4. **Factory Pattern**
- Single entry point: `get_rag_service(mode='simple')`
- Easy to add new patterns
- Centralized configuration

## ⚠️ Current Issues

### Issue 1: Missing `base/rag_factory.py`
**Problem**: `digital_tools.py` imports from `base.rag_factory` but file doesn't exist
**Impact**: MCP server fails to load tools
**Solution**: Move or create factory in `base/` directory

### Issue 2: Import Paths
**Problem**: Multiple rag_factory.py files (root and expected in base/)
**Solution**: Consolidate to one location (prefer `base/`)

### Issue 3: Unmigrated Patterns
**Problem**: Only `SimpleRAG` migrated to new architecture
**Impact**: Other modes (CRAG, Custom, Graph, etc.) not available
**Solution**: Migrate patterns one by one following SimpleRAG template

## 🚀 Next Steps

1. **Fix Factory Location** ✅ HIGH PRIORITY
   - Create `base/rag_factory.py` with simple implementation
   - Ensure `digital_tools.py` can import it

2. **Test Simple RAG** ✅ HIGH PRIORITY
   - Run `test_simple_rag.sh`
   - Verify ISA Model and Qdrant integration

3. **Migrate Custom RAG** (for PDF multimodal)
   - Pattern: MinIO + Qdrant
   - VLM for image descriptions

4. **Migrate Advanced Patterns**
   - CRAG (quality assessment)
   - Plan-RAG (structured reasoning)
   - Graph-RAG (Neo4j knowledge graphs)

5. **Deprecate Old Files**
   - Remove `rag_service.py` (root)
   - Remove old `rag_factory.py` (root)
   - Update any references

## 📖 Usage Examples

### Example 1: Simple Text Storage
```python
from base.rag_factory import get_rag_service
from base.rag_models import RAGStoreRequest

service = get_rag_service(mode='simple')
result = await service.store(RAGStoreRequest(
    content="Python is a programming language",
    user_id="user123",
    content_type="text"
))
print(result.success, result.content)
```

### Example 2: Retrieve and Generate
```python
# Retrieve
retrieval = await service.retrieve(RAGRetrieveRequest(
    query="What is Python?",
    user_id="user123",
    top_k=3
))

# Generate
response = await service.generate(RAGGenerateRequest(
    query="What is Python?",
    user_id="user123",
    retrieval_sources=[s.dict() for s in retrieval.sources]
))
print(response.content)
```

### Example 3: Via Factory with Config
```python
service = get_rag_service(
    mode='simple',
    config={
        'chunk_size': 500,
        'overlap': 100,
        'top_k': 10
    }
)
```

## 🔍 Testing

### Unit Tests
- `test_simple_rag.sh` - Validates structure and imports

### Integration Tests
- `digital_tools_test.sh` - End-to-end via MCP server

### Manual Testing
```bash
# Test structure
cd /Users/xenodennis/Documents/Fun/isA_MCP
bash tools/services/data_analytics_service/services/digital_service/tests/test_simple_rag.sh

# Test via MCP (requires server running)
bash tools/services/data_analytics_service/tests/digital_tools_test.sh
```
