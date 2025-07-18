# PDF Processor Documentation

## Overview

The PDF Processor is a comprehensive tool for extracting text, images, metadata, and structural information from PDF documents. It supports both native PDF text extraction and image-based content analysis.

## Dependencies

- `pypdf` - For native PDF text extraction and metadata
- `PyMuPDF (fitz)` - For advanced image extraction and unified processing
- `base64` - For image data encoding

## Core Capabilities

| Feature | Support | Description |
|---------|---------|-------------|
| Text Extraction |  | Extract all text content from PDF pages |
| Image Extraction |  | Extract images as base64-encoded data URLs |
| Metadata Extraction |  | PDF metadata (pages, size, author, etc.) |
| Structure Analysis |  | Page dimensions, content types, layout |
| Table Detection |  | Basic text-based table detection |
| Unified Processing |  | Combined text + image + vision analysis |

## Usage

### Basic Initialization

```python
from pdf_processor import PDFProcessor

# Initialize processor
processor = PDFProcessor(config={
    'default_language': 'auto'  # Optional configuration
})

# Check if processor is available
if processor.is_available():
    print("PDF processor ready")
```

### Method Overview

#### 1. Text Extraction

Extract all text content from PDF pages.

**Input:**
- `pdf_path`: Path to PDF file
- `options`: Optional processing parameters

**Output:**
```python
{
    'pdf_path': str,
    'full_text': str,           # Combined text from all pages
    'pages': List[str],         # Text per page
    'text_blocks': List[Dict],  # Structured text blocks with positions
    'confidence': float,        # Extraction confidence (1.0)
    'language': str,            # Document language
    'processing_time': float,   # Processing duration in seconds
    'extraction_method': str,   # 'pypdf' or 'pymupdf'
    'success': bool
}
```

**Usage:**
```python
result = await processor.extract_native_pdf_text('/path/to/document.pdf')
if result['success']:
    print(f"Extracted {len(result['full_text'])} characters")
    print(f"Pages: {len(result['pages'])}")
```

#### 2. Image Extraction

Extract images as base64-encoded data URLs.

**Input:**
- `pdf_path`: Path to PDF file
- `options`: Optional processing parameters

**Output:**
```python
{
    'pdf_path': str,
    'total_images': int,
    'images': [
        {
            'page_number': int,
            'image_index': int,
            'width': int,
            'height': int,
            'image_data': str,      # base64 data URL
            'format': str,          # 'PNG'
            'size_bytes': int
        }
    ],
    'success': bool
}
```

**Usage:**
```python
result = await processor.extract_pdf_images('/path/to/document.pdf')
if result['success']:
    for img in result['images']:
        print(f"Page {img['page_number']}: {img['width']}x{img['height']}")
        # img['image_data'] contains: 'data:image/png;base64,iVBORw0KG...'
```

#### 3. Metadata Extraction

Extract PDF document metadata.

**Input:**
- `pdf_path`: Path to PDF file
- `options`: Optional processing parameters

**Output:**
```python
{
    'pdf_path': str,
    'page_count': int,
    'file_size': int,           # Bytes
    'pdf_version': str,
    'title': str,
    'author': str,
    'subject': str,
    'creator': str,
    'producer': str,
    'creation_date': str,
    'modification_date': str,
    'is_encrypted': bool,
    'success': bool
}
```

#### 4. Structure Analysis

Analyze PDF structure and layout.

**Input:**
- `pdf_path`: Path to PDF file
- `options`: Optional analysis parameters

**Output:**
```python
{
    'pdf_path': str,
    'total_pages': int,
    'page_info': [
        {
            'page_number': int,
            'width': float,
            'height': float,
            'rotation': int,
            'has_text': bool,
            'has_images': bool,
            'text_length': int
        }
    ],
    'is_encrypted': bool,
    'success': bool
}
```

#### 5. Unified Processing (Recommended)

Comprehensive processing combining all extraction methods.

**Input:**
- `pdf_path`: Path to PDF file
- `options`: Processing configuration
  ```python
  {
      'extract_text': bool,    # Default: True
      'extract_images': bool,  # Default: True  
      'extract_tables': bool   # Default: True
  }
  ```

**Output:**
```python
{
    'pdf_path': str,
    'total_pages': int,
    'success': bool,
    
    # Text extraction results
    'text_extraction': {
        'full_text': str,
        'pages': List[str],
        'text_blocks': List[Dict],
        'confidence': float,
        'language': str,
        'extraction_method': str
    },
    
    # Image analysis results
    'image_analysis': {
        'total_images': int,
        'extracted_images': List[Dict],
        'vision_analyses': [
            {
                'page_number': int,
                'page_image_data': str,  # base64 data URL of full page
                'analysis_reason': str,  # 'no_text' or 'has_images'
                'width': int,
                'height': int
            }
        ],
        'pages_needing_vision': int
    },
    
    # Table detection results
    'table_extraction': {
        'total_tables': int,
        'tables': List[Dict],
        'extraction_method': str
    }
}
```

**Usage:**
```python
result = await processor.process_pdf_unified('/path/to/document.pdf', {
    'extract_text': True,
    'extract_images': True,
    'extract_tables': True
})

if result['success']:
    # Access text
    text_data = result['text_extraction']
    print(f"Text: {len(text_data['full_text'])} characters")
    
    # Access images
    image_data = result['image_analysis']
    print(f"Images: {image_data['total_images']} extracted")
    
    # Pages needing vision analysis
    for vision in image_data['vision_analyses']:
        print(f"Page {vision['page_number']} ready for vision analysis")
        # vision['page_image_data'] contains full page as base64 image
```

## Test Results Example

Based on a 14-page Chinese medical report (3.17MB):

- **Text Extraction**: 8,437 characters successfully extracted
- **Image Extraction**: 18 images extracted (sizes from 200x100 to 2570x3402)
- **Processing Time**: ~0.21 seconds for text extraction
- **Table Detection**: 9 tables detected
- **Vision Analysis**: 8 pages flagged for additional vision processing

## Error Handling

All methods return a `success` boolean field. On failure:

```python
{
    'pdf_path': str,
    'error': str,
    'success': False,
    'processing_time': float  # When available
}
```

## Best Practices

1. **Use Unified Processing** for comprehensive analysis
2. **Check Dependencies** with `processor.is_available()`
3. **Handle Large Files** - images are base64 encoded and can be memory intensive
4. **Vision Analysis** - Use `vision_analyses` data for AI-powered content analysis
5. **Error Handling** - Always check `success` field before processing results

## Integration Example

```python
async def process_document(pdf_path: str):
    processor = PDFProcessor()
    
    if not processor.is_available():
        raise Exception("PDF processor not available")
    
    # Unified processing
    result = await processor.process_pdf_unified(pdf_path)
    
    if not result['success']:
        raise Exception(f"Processing failed: {result['error']}")
    
    # Extract text content
    full_text = result['text_extraction']['full_text']
    
    # Extract images for vision analysis
    images_for_vision = []
    for vision in result['image_analysis']['vision_analyses']:
        images_for_vision.append({
            'page': vision['page_number'],
            'image': vision['page_image_data']  # Ready for vision AI
        })
    
    # Extract individual images
    extracted_images = result['image_analysis']['extracted_images']
    
    return {
        'text': full_text,
        'vision_pages': images_for_vision,
        'individual_images': extracted_images,
        'tables_detected': result['table_extraction']['total_tables']
    }
```

## Supported Formats

- PDF (.pdf)

## Output Formats

- **Text**: UTF-8 strings
- **Images**: Base64-encoded PNG data URLs (`data:image/png;base64,...`)
- **Metadata**: Structured dictionaries
- **Coordinates**: Bounding boxes when available