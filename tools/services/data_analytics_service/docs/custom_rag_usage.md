# Custom RAG Service - Complete Usage Guide

**Last Updated:** October 21, 2025
**Test PDFs:** bk01.pdf, bk02.pdf, bk03.pdf
**Test User:** testuser

---

## Quick Start

```bash
# Start MCP CLI
python utils/mcp_cli.py

# Store PDFs first
mcp> tool store_knowledge {"user_id": "testuser", "content": "/tmp/test_data/bk01.pdf", "content_type": "pdf", "metadata": {"source": "manual", "title": "CRM Manual Part 1"}, "options": {"enable_vlm_analysis": true, "enable_minio_upload": true, "max_pages": 3}}

# Search stored knowledge
mcp> tool search_knowledge {"user_id": "testuser", "query": "sample collection process", "search_options": {"top_k": 5, "content_type": "pdf"}}

# Generate RAG response
mcp> tool knowledge_response {"user_id": "testuser", "query": "How do I collect samples?", "response_options": {"use_pdf_context": true, "context_limit": 5}}
```

---

## 1. store_knowledge - Store Knowledge

### Parameter Structure

```json
{
  "user_id": "string",           // Required - User ID
  "content": "string",            // Required - Content or file path
  "content_type": "string",       // Required - Type: "text", "document", "image", "pdf"
  "metadata": {                   // Optional - Custom metadata
    "source": "string",           // Source identifier
    "title": "string",            // Title
    "category": "string",         // Category
    "tags": ["string"],           // Tags
    "custom_field": "value"       // Custom fields
  },
  "options": {                    // Optional - Processing options
    // PDF-specific options
    "enable_vlm_analysis": true,  // Use Vision Language Model for image analysis
    "enable_minio_upload": true,  // Upload to MinIO object storage
    "max_pages": 14,              // Maximum pages to process
    "max_concurrent_pages": 2,    // Concurrent page processing limit
    "chunking_strategy": "page",  // Strategy: "page", "recursive", "semantic"

    // Chunking options
    "chunk_size": 800,            // Chunk size in characters
    "chunk_overlap": 100,         // Overlap between chunks

    // Model options
    "model": "gpt-4o-mini",       // VLM model to use
    "description_prompt": "..."   // Custom description prompt
  }
}
```

### Example 1: Store PDF (With Multimodal Analysis)

```bash
tool store_knowledge {
  "user_id": "testuser",
  "content": "/tmp/test_data/bk01.pdf",
  "content_type": "pdf",
  "metadata": {
    "source": "manual",
    "title": "CRM Manual Part 1",
    "category": "documentation"
  },
  "options": {
    "enable_vlm_analysis": true,
    "enable_minio_upload": true,
    "max_pages": 3,
    "max_concurrent_pages": 2
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "success": true,
    "pdf_name": "bk01.pdf",
    "user_id": "testuser",
    "statistics": {
      "pages_stored": 3,
      "images_stored": 20,
      "total_records": 3,
      "processing_time": 15.2
    },
    "storage_result": {
      "success": true,
      "total_records": 3,
      "success_count": 3
    }
  }
}
```

### Example 2: Store PDF (Fast Mode - Without VLM)

```bash
tool store_knowledge {
  "user_id": "testuser",
  "content": "/tmp/test_data/bk02.pdf",
  "content_type": "pdf",
  "metadata": {"source": "manual", "title": "CRM Manual Part 2"},
  "options": {
    "enable_vlm_analysis": false,
    "enable_minio_upload": false
  }
}
```

### Example 3: Store Text Content

```bash
tool store_knowledge {
  "user_id": "testuser",
  "content": "Customer Relationship Management (CRM) is a technology for managing all your company's relationships and interactions with customers and potential customers.",
  "content_type": "text",
  "metadata": {"source": "wiki", "topic": "CRM"}
}
```

### Example 4: Store Document (With Custom Chunking)

```bash
tool store_knowledge {
  "user_id": "testuser",
  "content": "Long document content...",
  "content_type": "document",
  "metadata": {"source": "report"},
  "options": {
    "chunk_size": 400,
    "chunk_overlap": 50
  }
}
```

---

## 2. search_knowledge - Search Knowledge

### Parameter Structure

```json
{
  "user_id": "string",           // Required - User ID
  "query": "string",              // Required - Search query
  "search_options": {             // Optional - Search options
    "top_k": 5,                   // Number of results (default: 5)
    "enable_rerank": false,       // Enable reranking (default: false)
    "search_mode": "hybrid",      // Mode: "semantic", "hybrid", "lexical"
    "content_type": "pdf",        // Filter by type: "text", "image", "pdf"
    "content_types": ["pdf"],     // Filter by multiple types
    "return_format": "results",   // Format: "results", "context", "list"
    "knowledge_id": "uuid"        // Search specific knowledge ID (optional)
  }
}
```

### Example 1: Basic PDF Search

```bash
tool search_knowledge {
  "user_id": "testuser",
  "query": "sample collection process",
  "search_options": {
    "top_k": 5,
    "content_type": "pdf"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "success": true,
    "search_results": [
      {
        "text": "Chapter 3\n\nSample Collection\n1...",
        "page_number": 3,
        "page_summary": "Chapter 3",
        "photo_urls": [
          "http://staging-minio:9000/user-testuser-photos/testuser/pdf_images/bk02_page3_img0.png",
          "http://staging-minio:9000/user-testuser-photos/testuser/pdf_images/bk02_page3_img1.png"
        ],
        "num_photos": 4,
        "relevance_score": 0.0645,
        "metadata": {
          "title": "CRM Manual Part 2",
          "source": "manual",
          "pdf_name": "bk02.pdf",
          "page_number": 3
        }
      }
    ],
    "total_results": 5,
    "total_photos": 20,
    "search_method": "custom_rag_multimodal"
  }
}
```

### Example 2: Hybrid Search (Semantic + Lexical)

```bash
tool search_knowledge {
  "user_id": "testuser",
  "query": "sample collection process",
  "search_options": {
    "top_k": 10,
    "search_mode": "hybrid"
  }
}
```

### Example 3: Semantic-Only Search

```bash
tool search_knowledge {
  "user_id": "testuser",
  "query": "quality control procedures",
  "search_options": {
    "top_k": 3,
    "search_mode": "semantic"
  }
}
```

### Example 4: Return Context Format

```bash
tool search_knowledge {
  "user_id": "testuser",
  "query": "data analysis",
  "search_options": {
    "top_k": 3,
    "return_format": "context"
  }
}
```

**Response (context format):**
```json
{
  "status": "success",
  "data": {
    "success": true,
    "contexts": [
      {"text": "Context 1...", "score": 0.85},
      {"text": "Context 2...", "score": 0.82}
    ],
    "context_count": 3
  }
}
```

### Example 5: Filter by Multiple Content Types

```bash
tool search_knowledge {
  "user_id": "testuser",
  "query": "CRM overview",
  "search_options": {
    "top_k": 5,
    "content_types": ["text", "pdf"]
  }
}
```

---

## 3. knowledge_response - RAG Response Generation

### Parameter Structure

```json
{
  "user_id": "string",           // Required - User ID
  "query": "string",              // Required - User query
  "response_options": {           // Optional - Response options
    // RAG mode configuration
    "rag_mode": "simple",         // RAG mode: "simple", "raptor", "self_rag", "crag", "plan_rag", "hm_rag", "graph"
    "use_pdf_context": true,      // Use PDF context (for PDF-heavy knowledge bases)
    "auto_detect_pdf": true,      // Auto-detect if PDF context is available

    // Context options
    "context_limit": 5,           // Maximum context chunks (default: 3)
    "include_images": true,       // Include images in context (default: true)

    // LLM options
    "model": "gpt-4o-mini",       // Model name
    "provider": "yyds",           // Provider: "yyds", "openai", "anthropic"
    "temperature": 0.3,           // Temperature (0.0-1.0)

    // Citation options
    "enable_citations": true,     // Enable inline citations (default: true)

    // Advanced options
    "modes": ["simple", "crag"],  // Compare multiple RAG modes
    "recommend_mode": false       // Get mode recommendation
  }
}
```

### Example 1: Basic RAG (With PDF Multimodal)

```bash
tool knowledge_response {
  "user_id": "testuser",
  "query": "How do I collect samples? Please provide detailed steps.",
  "response_options": {
    "use_pdf_context": true,
    "context_limit": 5
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "success": true,
    "response": "Sample collection involves the following steps:\n\n1. **Preparation**: Ensure all equipment is sterilized...\n\n2. **Collection**: Follow proper collection protocol...\n\n3. **Storage**: Store samples properly...",
    "answer": "Sample collection involves...",
    "sources": {
      "page_count": 9,
      "photo_count": 57,
      "page_sources": [
        {
          "text": "Chapter 3: Sample Collection...",
          "page_number": 3,
          "similarity_score": 0.0645,
          "photo_urls": ["http://..."],
          "metadata": {"pdf_name": "bk02.pdf"}
        }
      ]
    },
    "response_type": "pdf_multimodal_rag",
    "rag_mode_used": "custom_rag"
  }
}
```

### Example 2: Specify Model and Provider

```bash
tool knowledge_response {
  "user_id": "testuser",
  "query": "What are the key CRM features mentioned?",
  "response_options": {
    "use_pdf_context": true,
    "context_limit": 5,
    "model": "gpt-4o-mini",
    "provider": "yyds",
    "temperature": 0.3
  }
}
```

### Example 3: Specific RAG Mode

```bash
tool knowledge_response {
  "user_id": "testuser",
  "query": "Explain the process",
  "response_options": {
    "rag_mode": "simple",
    "context_limit": 3,
    "model": "gpt-4o-mini"
  }
}
```

### Example 4: Auto-Detect PDF Context

```bash
tool knowledge_response {
  "user_id": "testuser",
  "query": "What are the quality standards?",
  "response_options": {
    "auto_detect_pdf": true,
    "context_limit": 5
  }
}
```

### Example 5: Enable Citations

```bash
tool knowledge_response {
  "user_id": "testuser",
  "query": "What are the quality control procedures?",
  "response_options": {
    "use_pdf_context": true,
    "enable_citations": true,
    "context_limit": 3
  }
}
```

**Response (with citations):**
```json
{
  "data": {
    "response": "Quality control procedures include:\n1. Use CRM system [1]\n2. Follow quality standards [1]\n3. Document all procedures [2]...",
    "inline_citations_enabled": true,
    "sources": {
      "page_sources": [
        {"citation_id": "[1]", "text": "..."},
        {"citation_id": "[2]", "text": "..."}
      ]
    }
  }
}
```

### Example 6: Advanced RAG Mode (CRAG)

```bash
tool knowledge_response {
  "user_id": "testuser",
  "query": "What are the best practices for data collection?",
  "response_options": {
    "rag_mode": "crag",
    "context_limit": 5,
    "model": "gpt-4o-mini"
  }
}
```

### Example 7: Compare Multiple Modes

```bash
tool knowledge_response {
  "user_id": "testuser",
  "query": "Explain the workflow",
  "response_options": {
    "modes": ["simple", "crag", "self_rag"],
    "context_limit": 5
  }
}
```

---

## 4. Progress Tracking (NEW Context Feature)

The data analytics service now includes **universal progress tracking** for all digital asset ingestion operations. This provides real-time feedback during long-running operations like PDF processing.

### 4-Stage Pipeline

All digital asset processing follows a standardized 4-stage pipeline:

1. **Processing (25%)** - Extract raw content from asset
2. **AI Extraction (50%)** - AI models analyze content (VLM for images, NLP for text)
3. **Embedding (75%)** - Generate vector embeddings
4. **Storing (100%)** - Persist to storage systems (MinIO, Vector DB, Neo4j)

### Progress Messages

During `store_knowledge` operations, you'll see progress updates in the following format:

```
[PROC] Stage 1/4 (25%): Processing PDF
[EXTR] Stage 2/4 (50%): AI Extraction - analyzing page 1/10
[EXTR] Stage 2/4 (50%): AI Extraction - analyzing page 2/10
...
[EMBD] Stage 3/4 (75%): Embedding PDF
[STOR] Stage 4/4 (100%): Storing PDF - uploading to MinIO
[STOR] Stage 4/4 (100%): Storing PDF - indexing in Vector DB
[DONE] PDF ingestion complete | {'pages': 10, 'images': 5, 'storage_mb': 2.4}
```

### Supported Asset Types

The progress tracking system supports all digital asset types:
- **PDF** - Documents with multimodal content
- **PowerPoint (PPT/PPTX)** - Presentations with slides
- **Documents (DOC/DOCX)** - Text documents
- **Images (JPG, PNG, GIF)** - Image files
- **Audio (MP3, WAV)** - Audio files
- **Video (MP4, AVI)** - Video files
- **Text** - Plain text content

### Granular Progress

For operations with multiple items (like PDF pages), progress is reported granularly:

```python
# PDF with 10 pages shows:
Processing PDF                           # Stage 1
AI Extraction - analyzing page 1/10      # Stage 2
AI Extraction - analyzing page 2/10      # Stage 2
...
AI Extraction - analyzing page 10/10     # Stage 2
Embedding PDF                            # Stage 3
Storing PDF - uploading to MinIO         # Stage 4
Storing PDF - indexing in Vector DB      # Stage 4
```

### Storage Progress

The storing stage provides detailed feedback about which storage systems are being used:

```
[STOR] Storing PDF - uploading to MinIO
[STOR] Storing PDF - indexing in Vector DB
[STOR] Storing PDF - completed in Neo4j Graph DB
```

### Context API

The progress tracking is implemented via the `DigitalAssetProgressReporter` class:

```python
from tools.services.data_analytics_service.tools.context import (
    DigitalAssetProgressReporter,
    AssetTypeDetector
)

# Initialize reporter
reporter = DigitalAssetProgressReporter(base_tool)

# Report stage progress
await reporter.report_stage(ctx, "processing", "pdf")

# Report granular progress
for i in range(1, total_pages + 1):
    await reporter.report_granular_progress(ctx, "extraction", "pdf", i, total_pages, "page")

# Report storage progress
await reporter.report_storage_progress(ctx, "pdf", "minio", "uploading")
await reporter.report_storage_progress(ctx, "pdf", "vector_db", "indexing")

# Report completion
await reporter.report_complete(ctx, "pdf", {"pages": 10, "images": 5})
```

---

## Complete Workflows

### Workflow 1: Store and Query PDFs

```bash
# 1. Store bk01.pdf
tool store_knowledge {
  "user_id": "testuser",
  "content": "/tmp/test_data/bk01.pdf",
  "content_type": "pdf",
  "metadata": {"source": "manual", "title": "CRM Manual Part 1"},
  "options": {"enable_vlm_analysis": true, "enable_minio_upload": true, "max_pages": 3}
}

# 2. Store bk02.pdf
tool store_knowledge {
  "user_id": "testuser",
  "content": "/tmp/test_data/bk02.pdf",
  "content_type": "pdf",
  "metadata": {"source": "manual", "title": "CRM Manual Part 2"},
  "options": {"enable_vlm_analysis": true, "enable_minio_upload": true, "max_pages": 3}
}

# 3. Search content
tool search_knowledge {
  "user_id": "testuser",
  "query": "sample collection process",
  "search_options": {"top_k": 5, "content_type": "pdf"}
}

# 4. Generate response
tool knowledge_response {
  "user_id": "testuser",
  "query": "How do I collect samples? Please provide detailed steps.",
  "response_options": {"use_pdf_context": true, "context_limit": 5}
}
```

### Workflow 2: Text Knowledge Base

```bash
# 1. Store text content
tool store_knowledge {
  "user_id": "testuser",
  "content": "CRM includes customer data management, sales automation, and marketing automation features.",
  "content_type": "text",
  "metadata": {"source": "internal", "topic": "CRM"}
}

# 2. Query the knowledge
tool knowledge_response {
  "user_id": "testuser",
  "query": "What CRM features are available?",
  "response_options": {"context_limit": 3}
}
```

---

## Parameter Reference

### store_knowledge Required Parameters
| Parameter | Type | Description |
|------|------|------|
| user_id | string | User identifier |
| content | string | Content or file path |
| content_type | string | "text", "document", "image", "pdf" |

### store_knowledge Common Options
| Parameter | Default | Description |
|------|--------|------|
| enable_vlm_analysis | true | Use VLM for image analysis |
| enable_minio_upload | true | Upload images to MinIO |
| max_pages | null | Maximum pages to process |
| chunk_size | 800 | Chunk size in characters |

### search_knowledge Required Parameters
| Parameter | Type | Description |
|------|------|------|
| user_id | string | User identifier |
| query | string | Search query |

### search_knowledge Common Options
| Parameter | Default | Description |
|------|--------|------|
| top_k | 5 | Number of results |
| search_mode | "hybrid" | Search mode |
| content_type | null | Filter by content type |

### knowledge_response Required Parameters
| Parameter | Type | Description |
|------|------|------|
| user_id | string | User identifier |
| query | string | User query |

### knowledge_response Common Options
| Parameter | Default | Description |
|------|--------|------|
| use_pdf_context | false | Use PDF RAG |
| context_limit | 3 | Maximum context chunks |
| model | "gpt-4o-mini" | LLM model |
| provider | "yyds" | Provider |
| temperature | 0.3 | Generation temperature |

---

## Troubleshooting

### Q1: Why am I getting no results?

**A:** Check the following:
1. **User ID mismatch** - Ensure you use the same user_id for storage and search
2. **Missing storage step** - Always call store_knowledge before searching
3. **Parameter format** - Ensure parameters are in correct JSON format

### Q2: How do parameter formats differ?

**A:** Use correct parameter names:
```bash
# Wrong: using max_results (this is an old parameter)
{"user_id": "testuser", "query": "test", "max_results": 5}

# Correct: using response_options.context_limit
{"user_id": "testuser", "query": "test", "response_options": {"context_limit": 5}}
```

### Q3: How do I speed up PDF processing?

**A:** Use fast mode options:
```bash
# Fast mode: disable VLM and MinIO
"options": {
  "enable_vlm_analysis": false,
  "enable_minio_upload": false,
  "max_pages": 10
}
```

### Q4: How do I increase context size?

**A:** Use context_limit:
```bash
"response_options": {
  "context_limit": 10  # Default is 3, max recommended is 10
}
```

### Q5: How do I change providers?

**A:** Set provider parameter:
```bash
# Change from default yyds to openai
"response_options": {
  "provider": "openai",
  "model": "gpt-4o-mini"
}
```

### Q6: Why aren't progress messages showing?

**A:** Progress tracking works differently depending on your client:
- **MCP Client**: Progress appears as structured progress updates
- **HTTP Mode**: Progress appears in log messages with prefixes [PROC], [EXTR], [EMBD], [STOR]
- **CLI Mode**: Both progress updates and log messages are shown

---

## Test Data Status

### Current Test Data

| User ID | PDF | Pages | Images | Status |
|---------|-----|-------|--------|--------|
| testuser | bk01.pdf | 3 | 20 | Stored |
| testuser | bk02.pdf | 3 | 17 | Stored |
| testuser | bk03.pdf | 3 | N/A | Stored |

### Test Queries

```bash
# Test Query 1: Sample collection
tool knowledge_response {"user_id": "testuser", "query": "How do I collect samples? Please provide detailed steps.", "response_options": {"use_pdf_context": true, "context_limit": 5}}

# Test Query 2: CRM features
tool knowledge_response {"user_id": "testuser", "query": "What are the key CRM features mentioned?", "response_options": {"use_pdf_context": true, "context_limit": 5}}

# Test Query 3: Workflow
tool knowledge_response {"user_id": "testuser", "query": "Explain the complete workflow step by step.", "response_options": {"use_pdf_context": true, "context_limit": 5}}
```

---

**Version:** 2.0
**Last Updated:** 2025-10-21
**Testing Status:** Updated with progress tracking documentation
