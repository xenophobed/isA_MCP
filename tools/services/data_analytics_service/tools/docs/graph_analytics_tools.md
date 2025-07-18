# Graph Analytics Tools Documentation

## Overview

The Graph Analytics Tools provide a complete pipeline for converting PDF documents into knowledge graphs stored in Neo4j database. This tool combines verified PDF extraction with advanced knowledge graph construction and GraphRAG querying capabilities.

## Key Features

- **Fast PDF Processing**: Optimized PDF text extraction (~1 second for typical documents)
- **Knowledge Graph Creation**: Entity, relationship, and attribute extraction using AI
- **Neo4j Storage**: Real database storage with user isolation
- **GraphRAG Queries**: Semantic search across your knowledge graphs
- **MCP Integration**: Full MCP resource management for tool discoverability

## Architecture

```
PDF Document → Text Extraction → Knowledge Processing → Neo4j Storage → GraphRAG Queries
     ↓              ↓                    ↓                  ↓             ↓
   PDF File    5 Text Chunks    Entities/Relations    Vector Storage   Search Results
```

## Performance Metrics

- **PDF Extraction**: ~1 second for 14-page documents
- **Knowledge Graph Creation**: ~17 seconds for typical medical reports
- **Parallel Processing**: 5 chunks processed simultaneously
- **Total Pipeline**: ~18 seconds end-to-end

## Available Tools

### 1. process_pdf_to_knowledge_graph

**Purpose**: Convert PDF documents into searchable knowledge graphs

**Parameters**:
```python
pdf_path: str              # Path to PDF file (required)
user_id: int = 88888      # User ID for data isolation
source_metadata: str = "{}" # JSON metadata about the document
options: str = "{}"        # JSON processing options
```

**Processing Options**:
```json
{
  "mode": "text"           # "text" (fast) or "full" (includes images)
}
```

**Source Metadata Example**:
```json
{
  "domain": "medical",           # Document domain for better extraction
  "document_type": "report",     # Type of document
  "patient_id": "12345"         # Custom metadata fields
}
```

**Response Format**:
```json
{
  "status": "success",
  "action": "process_pdf_to_knowledge_graph",
  "data": {
    "pdf_processing": {
      "file_path": "/path/to/document.pdf",
      "pages_processed": 14,
      "total_characters": 8485,
      "chunks_created": 5,
      "extraction_time": 0.08
    },
    "knowledge_graph": {
      "resource_id": "uuid-4f8a2b1c-3d5e-6789",
      "mcp_resource_address": "mcp://graph_knowledge/uuid-4f8a2b1c",
      "entities_count": 25,
      "relationships_count": 18,
      "processing_time": 17.2
    },
    "neo4j_storage": {
      "nodes_created": 25,
      "relationships_created": 18,
      "storage_time": 1.4
    }
  }
}
```

### 2. query_knowledge_graph

**Purpose**: Search knowledge graphs using natural language queries

**Parameters**:
```python
query: str                     # Natural language query (required)
user_id: int = 88888          # User ID for permission checking
resource_id: str = ""         # Specific resource ID (empty = search all)
options: str = "{}"           # JSON query options
```

**Query Options**:
```json
{
  "search_mode": "semantic",        # "semantic" or "multi_modal"
  "limit": 10,                      # Maximum results to return
  "similarity_threshold": 0.7       # Minimum similarity score (0.0-1.0)
}
```

**Example Queries**:
- "What medical conditions are mentioned?"
- "Who are the healthcare providers?"
- "What test results are abnormal?"
- "Find all relationships between patients and doctors"

**Response Format**:
```json
{
  "status": "success",
  "action": "query_knowledge_graph",
  "data": {
    "query": "What medical conditions are mentioned?",
    "results_found": 8,
    "results": [
      {
        "type": "entity",
        "content": "High blood pressure detected in patient",
        "score": 0.92,
        "metadata": {
          "entity_type": "MEDICAL_CONDITION",
          "source_file": "medical_report.pdf"
        }
      }
    ],
    "resources_searched": 2,
    "query_metadata": {
      "processing_time": 1.8,
      "search_mode": "semantic"
    }
  }
}
```

### 3. get_user_knowledge_graphs

**Purpose**: List all knowledge graph resources for a user

**Parameters**:
```python
user_id: int = 88888          # User ID
```

**Response Format**:
```json
{
  "status": "success",
  "action": "get_user_knowledge_graphs",
  "data": {
    "user_id": 88888,
    "resource_count": 3,
    "mcp_resources": {
      "uuid-1": {
        "address": "mcp://graph_knowledge/uuid-1",
        "source_file": "report1.pdf",
        "created_at": "2025-07-17T20:03:11"
      }
    },
    "user_isolation": true
  }
}
```

### 4. get_graph_analytics_status

**Purpose**: Get service status and capabilities

**Response Format**:
```json
{
  "tool_name": "graph_analytics_tools",
  "version": "2.0.0",
  "status": "✅ VERIFIED WORKING",
  "supported_formats": ["PDF"],
  "verified_features": [
    "✅ PDF → Text extraction (SimplePDFExtractService)",
    "✅ Text → Knowledge Graph (GraphAnalyticsService)",
    "✅ Real Neo4j storage with user isolation",
    "✅ GraphRAG queries with actual results"
  ],
  "performance": {
    "pdf_extraction": "~1s for 14 pages",
    "knowledge_graph_creation": "~17s typical",
    "parallel_chunks": 5
  }
}
```

## Usage Examples

### Basic PDF Processing

```python
import asyncio
from tools.mcp_client import call_tool

async def process_document():
    result = await call_tool(
        "process_pdf_to_knowledge_graph",
        pdf_path="/path/to/document.pdf",
        user_id=12345,
        source_metadata='{"domain": "medical", "type": "lab_report"}',
        options='{"mode": "text"}'
    )
    print(f"Created knowledge graph with {result['data']['knowledge_graph']['entities_count']} entities")

asyncio.run(process_document())
```

### Searching Knowledge Graphs

```python
async def search_knowledge():
    # Search all user's knowledge graphs
    result = await call_tool(
        "query_knowledge_graph", 
        query="What are the patient's test results?",
        user_id=12345,
        options='{"limit": 5, "similarity_threshold": 0.8}'
    )
    
    for result in result['data']['results']:
        print(f"Found: {result['content']} (score: {result['score']})")

asyncio.run(search_knowledge())
```

### Managing Resources

```python
async def list_resources():
    result = await call_tool("get_user_knowledge_graphs", user_id=12345)
    resources = result['data']['mcp_resources']
    
    print(f"Found {len(resources)} knowledge graphs:")
    for resource_id, details in resources.items():
        print(f"- {details['source_file']} ({resource_id})")

asyncio.run(list_resources())
```

## Technical Details

### Dependencies

- **PDF Extract Service**: Fast PDF text extraction
- **Graph Analytics Service**: Knowledge graph construction
- **Neo4j Database**: Vector storage and graph queries
- **ISA Model Service**: AI-powered entity/relationship extraction
- **User Service**: Authentication and isolation

### Data Flow

1. **PDF Input**: User provides PDF file path
2. **Text Extraction**: PDF converted to 5 optimized text chunks (~2000 chars each)
3. **Parallel Processing**: Each chunk processed simultaneously for entities/relationships
4. **Knowledge Graph**: Results combined into unified graph structure
5. **Neo4j Storage**: Graph stored with user isolation and vector embeddings
6. **MCP Registration**: Resource registered for discoverability
7. **GraphRAG Ready**: Available for semantic search queries

### Performance Optimizations

- **No Double Chunking**: PDF chunks used directly without re-chunking
- **Parallel Processing**: 5 chunks processed simultaneously
- **Optimized Models**: Uses fast `gpt-4o-mini` for extraction
- **Vector Embeddings**: `text-embedding-3-small` for semantic search
- **User Isolation**: Data separated by user ID in Neo4j

### Error Handling

The tools provide comprehensive error handling:

- **File Not Found**: Clear error if PDF doesn't exist
- **Processing Failures**: Detailed error messages for extraction issues
- **Permission Errors**: User isolation prevents cross-user access
- **Network Issues**: Graceful handling of service connectivity

### Security Features

- **User Isolation**: All data separated by user ID
- **Permission Checking**: Users can only access their own resources
- **Resource Validation**: MCP addresses validated before access
- **Input Sanitization**: All inputs validated and sanitized

## Best Practices

### Optimal Document Types

- **Medical Reports**: Excellent entity extraction for patients, conditions, tests
- **Business Documents**: Good for organizations, people, locations
- **Technical Papers**: Effective for concepts, relationships, definitions
- **Legal Documents**: Suitable for entities, parties, terms

### Performance Tips

1. **Use Text Mode**: For fastest processing, use `"mode": "text"`
2. **Batch Processing**: Process multiple documents for same user
3. **Specific Queries**: More specific queries return better results
4. **Domain Metadata**: Include domain info for better extraction

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Slow processing | Check Neo4j connection, ensure text mode |
| No entities found | Verify document has meaningful text content |
| Permission denied | Check user_id matches resource owner |
| Empty results | Lower similarity_threshold in queries |

## Integration with MCP

The Graph Analytics Tools are fully integrated with the MCP (Model Context Protocol) system:

- **Tool Discovery**: Tools automatically discoverable via MCP
- **Resource Management**: Knowledge graphs registered as MCP resources
- **Standard Interface**: Consistent JSON request/response format
- **Error Handling**: Standard MCP error response format

This makes the tools easy to integrate with any MCP-compatible client or framework.