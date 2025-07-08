# Graph Analytics Tools Usage Guide

## Overview

The Graph Analytics Tools provide a simplified, AI agent-friendly interface for building and querying knowledge graphs using Neo4j GraphRAG. The tools are designed with just **two core functions** to handle all graph analytics needs.

## Tools Available

### 🏗️ `build_knowledge_graph_from_files`
Build knowledge graphs from any file source with automatic processing.

### 🔍 `intelligent_query` 
Smart querying with automatic strategy selection and result aggregation.

---

## 🏗️ Build Knowledge Graph from Files

### Purpose
Automatically builds knowledge graphs from various file sources including documents, directories, or file lists. Supports multiple formats and handles the complete extraction pipeline.

### Usage

```python
await build_knowledge_graph_from_files(
    source="path/to/source",
    graph_name="optional_graph_name",
    file_patterns=["*.txt", "*.pdf"],  # Optional, for directories
    recursive=True  # Optional, for directories
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | `str` | ✅ | File path, directory path, or JSON list of files |
| `graph_name` | `str` | ❌ | Optional name for the knowledge graph |
| `file_patterns` | `List[str]` | ❌ | File patterns like `["*.txt", "*.md"]` (for directories) |
| `recursive` | `bool` | ❌ | Whether to process subdirectories (default: `True`) |

### Source Types

#### 1. Single File
```python
source = "/path/to/document.pdf"
```

#### 2. Directory
```python
source = "/path/to/documents/"
# Optionally specify patterns
file_patterns = ["*.pdf", "*.txt", "*.md"]
```

#### 3. File List (JSON)
```python
source = '["file1.txt", "file2.pdf", "folder/file3.docx"]'
```

### Supported File Formats

- **Text**: `.txt`, `.md`
- **Documents**: `.pdf`, `.docx`
- **Data**: `.json`, `.csv`
- **Web**: `.html`, `.xml`
- **Auto-detection**: Unknown formats processed as text

### Example Usage

```python
# Build from single PDF
result = await build_knowledge_graph_from_files(
    source="/path/to/research_paper.pdf",
    graph_name="research_knowledge"
)

# Build from directory with filtering
result = await build_knowledge_graph_from_files(
    source="/path/to/documents/",
    file_patterns=["*.pdf", "*.txt"],
    recursive=True,
    graph_name="document_collection"
)

# Build from file list
file_list = [
    "/docs/paper1.pdf",
    "/docs/paper2.txt", 
    "/reports/analysis.docx"
]
result = await build_knowledge_graph_from_files(
    source=json.dumps(file_list),
    graph_name="multi_source_graph"
)
```

### Response Format

```json
{
  "status": "success",
  "operation": "build_knowledge_graph_from_files",
  "data": {
    "build_summary": {
      "successful_documents": 5,
      "failed_documents": 0,
      "total_entities_created": 1247,
      "total_relationships_created": 342,
      "processing_time": 45.2
    },
    "graph_info": {
      "graph_name": "research_knowledge",
      "node_count": 1247,
      "relationship_count": 342
    },
    "message": "Knowledge graph built successfully! Processed 5 documents, created 1247 entities and 342 relationships."
  }
}
```

---

## 🔍 Intelligent Query

### Purpose
Performs intelligent querying with automatic strategy selection. Routes queries to optimal search methods and aggregates results with analysis insights.

### Usage

```python
await intelligent_query(
    query="your natural language query",
    max_results=20,
    include_analysis=True,
    context='{"analysis_type": "comparison"}'
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | `str` | ✅ | Natural language query or search terms |
| `max_results` | `int` | ❌ | Maximum results to return (default: 20) |
| `include_analysis` | `bool` | ❌ | Include graph analysis insights (default: `True`) |
| `context` | `str` | ❌ | Optional JSON context to guide search strategy |

### Query Types Supported

#### 1. Semantic Search
```python
query = "machine learning algorithms"
```

#### 2. Entity Search
```python
query = "researchers working on AI"
```

#### 3. Relationship Queries
```python
query = "connections between universities and tech companies"
```

#### 4. Analytical Queries
```python
query = "compare different approaches mentioned in the documents"
context = '{"analysis_type": "comparison", "focus": "methods"}'
```

#### 5. Factual Questions
```python
query = "when was the research conducted?"
```

### Context Options

Use the `context` parameter to guide search strategy:

```json
{
  "analysis_type": "comparison|summary|network|analytical",
  "focus": "methods|authors|institutions|results",
  "domain": "technical|business|academic",
  "time_range": "recent|historical|specific"
}
```

### Example Usage

```python
# Basic semantic search
result = await intelligent_query(
    query="neural networks and deep learning",
    max_results=10
)

# Entity-focused search
result = await intelligent_query(
    query="authors and their affiliations",
    context='{"analysis_type": "network", "focus": "authors"}'
)

# Comparative analysis
result = await intelligent_query(
    query="compare machine learning approaches in the papers",
    context='{"analysis_type": "comparison", "focus": "methods"}',
    include_analysis=True
)

# Specific factual query
result = await intelligent_query(
    query="what datasets were used in the experiments?",
    max_results=5
)
```

### Response Format

```json
{
  "status": "success",
  "operation": "intelligent_query",
  "data": {
    "query_id": "iq_1751879033747",
    "query": "machine learning algorithms",
    "strategy": {
      "has_entities": true,
      "has_relationships": false,
      "is_analytical": false,
      "confidence": 0.85
    },
    "results": [
      {
        "text": "Machine Learning",
        "entity_type": "CONCEPT",
        "canonical_form": "Machine Learning",
        "score": 0.857,
        "_source": "semantic_search",
        "_rank": 0
      }
    ],
    "result_summary": {
      "total_results": 10,
      "search_methods_used": 2,
      "deduplicated_from": 15
    },
    "analysis": {
      "insights": [
        "Machine Learning is the most relevant concept",
        "Multiple algorithmic approaches were identified"
      ],
      "key_entities": ["Machine Learning", "Neural Networks"],
      "relationships_found": 5
    },
    "execution_time": 0.52,
    "message": "Found 10 results using entity-focused search strategy. Query execution took 0.52 seconds."
  }
}
```

---

## 🚀 Getting Started

### 1. Basic Workflow

```python
# Step 1: Build your knowledge graph
build_result = await build_knowledge_graph_from_files(
    source="/path/to/your/documents/",
    graph_name="my_knowledge_base"
)

# Step 2: Query the graph
query_result = await intelligent_query(
    query="what are the main concepts discussed?",
    max_results=20,
    include_analysis=True
)
```

### 2. Advanced Usage

```python
# Build from multiple sources
sources = [
    "/research/papers/",
    "/reports/analysis.pdf",
    "/data/structured_data.json"
]

for source in sources:
    await build_knowledge_graph_from_files(
        source=source,
        graph_name="comprehensive_kb"
    )

# Perform different types of queries
queries = [
    {
        "query": "key researchers and their contributions",
        "context": '{"analysis_type": "network", "focus": "authors"}'
    },
    {
        "query": "compare different methodologies",
        "context": '{"analysis_type": "comparison", "focus": "methods"}'
    },
    {
        "query": "timeline of developments",
        "context": '{"analysis_type": "temporal", "focus": "events"}'
    }
]

for q in queries:
    result = await intelligent_query(**q)
    # Process results...
```

---

## 📊 Performance and Best Practices

### File Processing

- **Optimal chunk size**: 100K characters (leverages LLM long context)
- **Batch processing**: Concurrent processing with configurable limits
- **Supported formats**: Auto-detection with fallbacks
- **Large files**: Automatically chunked with overlap for context

### Query Performance

- **Response time**: 0.2-1.0 seconds typical
- **Caching**: Vector embeddings cached for repeated queries  
- **Strategy selection**: Automatic routing to optimal search methods
- **Result aggregation**: Intelligent deduplication and ranking

### Best Practices

1. **Graph Building**:
   - Use descriptive `graph_name` for organization
   - Process related documents together
   - Use appropriate `file_patterns` for selective processing

2. **Querying**:
   - Start with broad queries, then narrow down
   - Use `context` to guide complex analytical queries
   - Set appropriate `max_results` for your use case
   - Enable `include_analysis` for insights

3. **Performance**:
   - Build graphs incrementally for large document sets
   - Use specific queries rather than very broad ones
   - Monitor execution times and adjust `max_results`

---

## 🔧 Configuration

### Environment Variables

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# Optional: Custom settings
GRAPH_CHUNK_SIZE=100000
GRAPH_MAX_CONCURRENT=5
GRAPH_SIMILARITY_THRESHOLD=0.7
```

### Service Configuration

The tools automatically initialize required services:
- **File Processor**: Handles multiple file formats
- **Batch Builder**: Manages graph construction pipeline  
- **Query Aggregator**: Routes and aggregates search results
- **Neo4j GraphRAG Client**: Vector similarity and graph operations

---

## 🎯 Use Cases

### 1. Research Analysis
```python
# Build knowledge base from research papers
await build_knowledge_graph_from_files(
    source="/research/papers/",
    file_patterns=["*.pdf"],
    graph_name="research_corpus"
)

# Analyze research trends
await intelligent_query(
    query="evolution of machine learning techniques over time",
    context='{"analysis_type": "temporal", "focus": "methods"}'
)
```

### 2. Document Intelligence
```python
# Process business documents
await build_knowledge_graph_from_files(
    source="/business/reports/",
    graph_name="business_intelligence"
)

# Extract insights
await intelligent_query(
    query="key performance indicators and their relationships",
    context='{"analysis_type": "network", "focus": "metrics"}'
)
```

### 3. Competitive Analysis
```python
# Compare competitor information
await intelligent_query(
    query="compare product features across different companies",
    context='{"analysis_type": "comparison", "focus": "products"}'
)
```

---

## 🛠️ Troubleshooting

### Common Issues

1. **No results returned**:
   - Check if knowledge graph was built successfully
   - Verify query terms exist in the documents
   - Try broader search terms

2. **Slow performance**:
   - Reduce `max_results` 
   - Check Neo4j connection
   - Monitor system resources

3. **Build failures**:
   - Verify file paths and permissions
   - Check supported file formats
   - Review error messages in logs

### Error Handling

Both tools return detailed error information:

```json
{
  "status": "error",
  "operation": "build_knowledge_graph_from_files",
  "data": {
    "source": "/invalid/path",
    "error": "FileNotFoundError: Source not found"
  },
  "error_message": "Source not found: /invalid/path"
}
```

---

## 📈 Version Information

- **Version**: 2.0.0
- **Service**: GraphAnalyticsService
- **Neo4j Integration**: GraphRAG with vector similarity
- **Architecture**: Service-based with lazy initialization

For technical details, see the [API Documentation](API_DOCUMENTATION.md) and [Project Structure](PROJECT_STRUCTURE.md).