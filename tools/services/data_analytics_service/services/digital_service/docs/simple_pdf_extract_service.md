# Simple PDF Extract Service Documentation

## Overview

The Simple PDF Extract Service is a streamlined, high-performance PDF text extraction service optimized with Dask parallel processing. It focuses solely on converting PDFs to text chunks without complex preprocessing or graph analytics workflows.

## Key Features

- ✅ **Fast Text Extraction** - Lightning-fast text-only mode (0.079s for 14 pages)
- ✅ **Parallel Image Processing** - Dask-optimized image text extraction 
- ✅ **Production Components** - Uses existing PDFProcessor and ImageAnalyzer
- ✅ **Simple Interface** - Clean input/output with minimal complexity
- ✅ **Two Processing Modes** - Text-only and full extraction

## Service Input

### Method: `extract_pdf_to_chunks()`

```python
await service.extract_pdf_to_chunks(
    pdf_path: str,                           # Required: Path to PDF file
    user_id: int,                           # Required: User identifier
    options: Optional[Dict[str, Any]],      # Optional: Processing options
    metadata: Optional[Dict[str, Any]]      # Optional: Additional metadata
)
```

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pdf_path` | `str` | ✅ Yes | Absolute path to PDF file |
| `user_id` | `int` | ✅ Yes | User ID for tracking |
| `options` | `Dict` | ❌ No | Processing configuration |
| `metadata` | `Dict` | ❌ No | Additional metadata |

### Options Configuration

```python
options = {
    "mode": "text",              # "text" or "full" 
    "max_workers": 4             # Dask worker count (optional)
}
```

**Processing Modes:**
- `"text"` - Text extraction only (fast, ~0.079s)
- `"full"` - Text + image text extraction (slower, includes VLM processing)

### Example Input

```python
# Text-only extraction
result = await service.extract_pdf_to_chunks(
    pdf_path="/path/to/document.pdf",
    user_id=12345,
    options={"mode": "text"},
    metadata={"source": "user_upload"}
)

# Full extraction with images
result = await service.extract_pdf_to_chunks(
    pdf_path="/path/to/document.pdf", 
    user_id=12345,
    options={"mode": "full"},
    metadata={"priority": "high"}
)
```

## Service Output

### Success Response Structure

```python
{
    "success": True,                         # Processing success indicator
    "chunks": [                             # List of text chunks
        "Text chunk 1 content...",
        "Text chunk 2 content...",
        "Text chunk 3 content..."
    ],
    "chunk_count": 5,                       # Number of chunks created
    "total_characters": 8485,               # Total characters extracted
    "pages_processed": 14,                  # Number of PDF pages processed
    "images_processed": 26,                 # Number of images analyzed (full mode only)
    "mode": "full",                         # Processing mode used
    "user_id": 12345,                       # User ID
    "processing_time": 31.934,              # Total processing time in seconds
    "metadata": {                           # Enhanced metadata
        "pdf_path": "/path/to/document.pdf",
        "extracted_at": "2025-07-17T16:34:56.123456",
        "source": "user_upload"             # Original metadata preserved
    }
}
```

### Error Response Structure

```python
{
    "success": False,                       # Processing failed
    "error": "PDF file not found: /path/to/document.pdf",
    "processing_time": 0.001                # Time before failure
}
```

## Real Test Results

Based on actual test with 14-page Chinese medical report (3.17MB PDF, ~8,473 characters of extractable text):

### Text-Only Mode (`"text"`)
```python
{
    "success": True,
    "chunks": [
        # Chunk 1: 2000 characters (full size with default config)
        "深圳平安粤海门诊部\n第一部分　 报告首页\n尊敬的\n先生：\n您好！\n感谢您对 深圳平安粤海门诊部 的信赖...",  # (truncated for display)
        
        # Chunk 2: 2000 characters  
        "异常结果，我们在体检项目后加以★标识。请您结合临床症状及时就医...",  # (truncated for display)
        
        # Chunk 3: 1961 characters
        # Chunk 4: 1883 characters  
        # Chunk 5: 1441 characters (last chunk, remainder)
    ],
    "chunk_count": 5,
    "total_characters": 8485,               # ✅ Accurate: PDF contains ~8,473 extractable chars
    "pages_processed": 14,
    "images_processed": 0,
    "mode": "text",
    "user_id": 12345,
    "processing_time": 0.076,               # 🚀 Lightning fast!
    "metadata": {
        "pdf_path": "/Users/xenodennis/Documents/Fun/isA_MCP/test.pdf",
        "extracted_at": "2025-07-17T16:42:22.741000",
        "test": "text_only"
    }
}
```

**Actual Chunk Sizes:** 2000, 2000, 1961, 1883, 1441 characters (chunks shown truncated above for readability)

### Full Mode (`"full"`) - Integrated Image Text by Page
```python
{
    "success": True,
    "chunks": [
        # Page content with integrated image text
        "深圳平安粤海门诊部\n第一部分　 报告首页\n尊敬的\n先生：\n您好！\n\n[Page Image Text]: 深圳平安粤海门诊部\n体检报告\n受检者信息\n姓名: [姓名]\n性别: 男\n年龄: [年龄]",
        
        "第二部分 体检结果\n血常规检查\nWBC: 正常范围\nRBC: 正常范围\n\n[Embedded Image Text]: 血常规检查结果\nWBC: 5.2 × 10⁹/L (参考值: 4.0-10.0)\nRBC: 4.8 × 10¹²/L (参考值: 4.5-5.5)",
        
        # ... more chunks with page text + integrated image content
    ],
    "chunk_count": 11,                      # More chunks due to image content integration
    "total_characters": 18372,              # ✅ 9,887 additional chars from images (8,485 + 9,887)
    "pages_processed": 14,
    "images_processed": 26,                 # 🖼️ 26 images analyzed in parallel with Dask
    "mode": "full", 
    "user_id": 12345,
    "processing_time": 38.798,              # Includes parallel VLM processing time
    "metadata": {
        "pdf_path": "/Users/xenodennis/Documents/Fun/isA_MCP/test.pdf",
        "extracted_at": "2025-07-17T16:42:23.685000",
        "test": "full_extraction"
    }
}
```

## Performance Characteristics

| Mode | Processing Time | Use Case |
|------|----------------|----------|
| `"text"` | ~0.079s | Fast text extraction, searchable PDFs |
| `"full"` | ~31s | Complete extraction including image text |

**Performance Factors:**
- **Text extraction**: Extremely fast (~0.079s for 14 pages)
- **Image processing**: Dependent on number of images and VLM response time
- **Dask parallelization**: Significantly speeds up image processing vs sequential

## Output Text Structure

### Text-Only Mode
- Raw PDF text extracted by PDFProcessor (8,485 characters)
- Simple chunking with configurable size (default: 2000 chars)
- Chunk overlap for context preservation (default: 200 chars)

### Full Mode - Integrated by Page
- **Page Text + Image Content** integrated together per page
- Format: `[Page Image Text]: ...` and `[Embedded Image Text]: ...`
- Total: 18,372 characters (8,485 original + 9,887 from images)

**Example Integration:**
```
Page 1 original text:
深圳平安粤海门诊部
第一部分　 报告首页
尊敬的先生：
您好！

[Page Image Text]: 深圳平安粤海门诊部
体检报告
受检者信息
姓名: [姓名]
性别: 男
年龄: [年龄]

[Embedded Image Text]: 血常规检查结果
WBC: 5.2 × 10⁹/L (参考值: 4.0-10.0)
RBC: 4.8 × 10¹²/L (参考值: 4.5-5.5)
```

This ensures image content is **contextually linked** to the correct page, not just appended at the end.

## Chunking Configuration

Default chunking settings:
```python
{
    "chunk_size": 2000,        # Maximum characters per chunk
    "chunk_overlap": 200       # Character overlap between chunks
}
```

Chunks are created at word boundaries to maintain readability.

## Error Handling

Common error scenarios:

```python
# File not found
{
    "success": False,
    "error": "PDF file not found: /path/to/missing.pdf",
    "processing_time": 0.001
}

# PDF processing failed  
{
    "success": False,
    "error": "Text extraction failed: PDF is encrypted",
    "processing_time": 0.050
}

# Image analysis failed (partial failure - text still extracted)
{
    "success": True,           # Text succeeded
    "chunks": ["text chunks..."],
    "images_processed": 5,     # Some images failed
    # ... other fields
}
```

## Chunk Size Configuration

### Available Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chunk_size` | `2000` | Maximum characters per chunk |
| `chunk_overlap` | `200` | Character overlap between adjacent chunks |

### Configuration Examples

```python
# Small chunks for detailed processing
service = SimplePDFExtractService({
    'chunk_size': 1000,
    'chunk_overlap': 100
})

# Large chunks for broader context  
service = SimplePDFExtractService({
    'chunk_size': 4000,
    'chunk_overlap': 400
})

# No overlap for distinct chunks
service = SimplePDFExtractService({
    'chunk_size': 2000,
    'chunk_overlap': 0
})
```

## Integration Example

```python
from tools.services.data_analytics_service.services.digital_service.simple_pdf_extract_service import SimplePDFExtractService

# Initialize service with custom chunk size
service = SimplePDFExtractService({
    'chunk_size': 1500,        # Custom size
    'chunk_overlap': 150       # Custom overlap
})

# Optional: Initialize Dask for parallel processing
await service.initialize_dask(workers=4, threads_per_worker=2)

# Extract PDF
result = await service.extract_pdf_to_chunks(
    pdf_path="/path/to/document.pdf",
    user_id=12345,
    options={"mode": "full"},
    metadata={"source": "api_upload"}
)

# Process results
if result["success"]:
    print(f"Extracted {result['chunk_count']} chunks")
    print(f"Total text: {result['total_characters']} characters")
    
    # Use the chunks
    for i, chunk in enumerate(result["chunks"]):
        print(f"Chunk {i+1}: {chunk[:100]}...")
else:
    print(f"Extraction failed: {result['error']}")

# Cleanup
service.close_dask()
```

## Dependencies

- **PDFProcessor**: For PDF text and image extraction
- **ImageAnalyzer**: For VLM-based image text extraction  
- **Dask**: For parallel image processing
- **PyPDF2/PyMuPDF**: PDF processing libraries
- **ISA Client**: Vision model access

## Best Practices

1. **Use text mode for speed** when images don't contain important text
2. **Initialize Dask** for better image processing performance
3. **Check success field** before processing results
4. **Handle partial failures** - text may succeed even if some images fail
5. **Consider file size** - larger PDFs with many images take longer in full mode
6. **Clean up Dask** when done to release resources