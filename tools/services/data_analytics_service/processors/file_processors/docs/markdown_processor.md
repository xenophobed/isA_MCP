# Markdown Processor Documentation

## Overview

The Markdown Processor is a basic formatting processor that converts structured content data into well-formatted markdown. It focuses purely on formatting and layout - no AI processing involved.

## Purpose

- **Basic formatting only** - No AI text processing or analysis
- **Clean separation of concerns** - AI processing handled by other processors
- **Reusable formatting** - Can be used by any processor that needs markdown output
- **Simple and fast** - Basic string formatting operations only

## Dependencies

- `pathlib` - For file path handling
- `typing` - For type hints
- `dataclasses` - For data structures
- `logging` - For basic logging

**No AI dependencies** - This processor does not use any intelligence services.

## Core Capabilities

| Feature | Support | Description |
|---------|---------|-------------|
| Basic Text Formatting |  | Simple paragraph formatting with headers |
| Image Placeholders |  | Image metadata and placeholder formatting |
| Table Structure |  | Basic table information formatting |
| Document Headers |  | Title, source, and metadata headers |
| Multi-document Support |  | Can format multiple documents |
| Configuration Options |  | Include/exclude sections via config |

## Usage

### Basic Initialization

```python
from markdown_processor import MarkdownProcessor

# Basic initialization
processor = MarkdownProcessor()

# With configuration
processor = MarkdownProcessor({
    'include_images': True,
    'include_tables': True,
    'include_metadata': True
})
```

### Input Data Format

The processor expects structured content data:

```python
content = {
    'title': 'Document Title',
    'source': '/path/to/source.pdf',
    'processing_method': 'unified',  # Optional
    'total_pages': 10,               # Optional
    'text': 'Document text content...',
    'images': [                      # Optional
        {
            'page_number': 1,
            'image_index': 0,
            'width': 800,
            'height': 600,
            'description': 'Chart showing data trends'
        }
    ],
    'tables': [                      # Optional
        {
            'page_number': 2,
            'table_type': 'data_table',
            'confidence': 0.85,
            'content': 'Table content here'
        }
    ]
}
```

### Basic Usage

```python
# Generate markdown from structured content
result = processor.generate_markdown(content)

if result.success:
    print(f"Generated markdown ({len(result.markdown)} chars)")
    print(f"Processing time: {result.processing_time:.3f}s")
    print(f"Structure: {result.structure.total_pages} pages, {result.structure.total_images} images")
    
    # Access the markdown content
    markdown_text = result.markdown
    
    # Access structure metadata
    structure = result.structure
else:
    print(f"Failed to generate markdown: {result.error}")
```

## Output Format

### Generated Markdown Structure

```markdown
# Document Title

**Source:** `/path/to/source.pdf`
**Processing Method:** unified
**Total Pages:** 10

## Content

Document text content formatted into paragraphs.

Each paragraph is separated properly.

## Images

### Image 0 - Page 1

**Description:** Chart showing data trends
**Dimensions:** 800x600 pixels
*[Image data available]*

## Tables

**Total Tables:** 1

### Table 1

**Page:** 2
**Type:** data_table
**Confidence:** 0.85
**Content:**
Table content here
```

### Result Object

```python
@dataclass
class MarkdownResult:
    markdown: str                    # Generated markdown content
    structure: MarkdownStructure     # Document structure metadata
    success: bool                    # Whether generation succeeded
    error: Optional[str] = None      # Error message if failed
    processing_time: float = 0.0     # Processing time in seconds

@dataclass  
class MarkdownStructure:
    documents: List[Dict[str, Any]]  # List of processed documents
    total_pages: int                 # Total pages across all documents
    total_images: int               # Total images across all documents
    total_tables: int               # Total tables across all documents
```

## Architecture Benefits

### Clean Separation

- **Markdown Processor** ’ Basic formatting only
- **PDF Processor** ’ AI analysis + uses markdown processor
- **Service Layer** ’ Orchestrates everything

### Integration Pattern

1. **AI Processor** ’ Handles AI analysis and content enhancement
2. **Markdown Processor** ’ Handles basic formatting
3. **Service Layer** ’ Orchestrates the workflow

## Summary

The Markdown Processor provides clean, basic markdown formatting for structured content data. It's designed to be:

- **Simple** - Basic formatting operations only
- **Fast** - No AI processing or external calls
- **Reusable** - Can be used by any processor
- **Configurable** - Include/exclude sections as needed
- **Reliable** - Predictable output format

Perfect for use as a formatting layer in larger processing pipelines where AI analysis is handled separately.