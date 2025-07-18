# OCR Extractor Documentation

## Overview

The OCR Extractor service provides text extraction capabilities from images using the ISA SuryaOCR model through the ISA Model Client. It supports multi-language text recognition and confidence-based filtering.

## Features

- **Multi-language OCR**: Support for multiple languages including English and Chinese
- **Confidence filtering**: Filter results based on confidence thresholds
- **Structured output**: Returns detailed information about extracted text regions
- **Error handling**: Comprehensive error handling and reporting
- **Async support**: Full asynchronous operation support

## Installation

Ensure you have the ISA Model Client installed:

```bash
pip install isa-model-client
```

## Quick Start

```python
import asyncio
from ocr_extractor import OCRExtractor

async def main():
    extractor = OCRExtractor()
    
    # Basic text extraction
    result = await extractor.extract_text("document.png", languages=["en"])
    
    if result["success"]:
        print(f"Extracted text: {result['total_text']}")
    else:
        print(f"Error: {result['error']}")

asyncio.run(main())
```

## API Reference

### OCRExtractor Class

#### `__init__()`

Initialize the OCR extractor with ISA Model Client.

#### `extract_text(image_path, languages=None)`

Extract text from an image using OCR.

**Parameters:**
- `image_path` (str): Path to the image file
- `languages` (List[str], optional): List of language codes (default: ["en"])

**Returns:**
- Dictionary with extraction results:
  ```python
  {
      "success": bool,
      "text_results": List[Dict],  # Individual text regions
      "total_text": str,           # Combined text
      "total_characters": int,     # Character count
      "region_count": int          # Number of regions
  }
  ```

**Example:**
```python
result = await extractor.extract_text(
    "contract.png", 
    languages=["en", "zh"]
)
```

#### `extract_with_confidence_filter(image_path, min_confidence=0.5, languages=None)`

Extract text with confidence filtering.

**Parameters:**
- `image_path` (str): Path to the image file
- `min_confidence` (float): Minimum confidence threshold (0.0 to 1.0)
- `languages` (List[str], optional): List of language codes

**Returns:**
- Same as `extract_text()` but with additional `confidence_threshold` field

**Example:**
```python
result = await extractor.extract_with_confidence_filter(
    "document.png",
    min_confidence=0.8,
    languages=["en"]
)
```

#### `print_results(result)`

Print OCR extraction results in a formatted way.

**Parameters:**
- `result` (Dict): Result dictionary from extraction methods

## Usage Examples

### Basic Text Extraction

```python
import asyncio
from ocr_extractor import OCRExtractor

async def basic_extraction():
    extractor = OCRExtractor()
    
    result = await extractor.extract_text("invoice.png")
    extractor.print_results(result)

asyncio.run(basic_extraction())
```

### Multi-language Support

```python
async def multilingual_extraction():
    extractor = OCRExtractor()
    
    # Extract from image with English and Chinese text
    result = await extractor.extract_text(
        "mixed_language_document.png",
        languages=["en", "zh"]
    )
    
    if result["success"]:
        for i, region in enumerate(result["text_results"]):
            print(f"Region {i+1}: {region['text']} (confidence: {region['confidence']:.3f})")

asyncio.run(multilingual_extraction())
```

### Confidence Filtering

```python
async def high_confidence_extraction():
    extractor = OCRExtractor()
    
    # Only extract text with high confidence
    result = await extractor.extract_with_confidence_filter(
        "noisy_image.png",
        min_confidence=0.9
    )
    
    print(f"High-confidence text: {result['total_text']}")

asyncio.run(high_confidence_extraction())
```

### Error Handling

```python
async def robust_extraction():
    extractor = OCRExtractor()
    
    try:
        result = await extractor.extract_text("document.png")
        
        if result["success"]:
            print(f"Success: Extracted {result['region_count']} regions")
            print(f"Total text: {result['total_text']}")
        else:
            print(f"OCR failed: {result['error']}")
            
    except Exception as e:
        print(f"Unexpected error: {e}")

asyncio.run(robust_extraction())
```

## Supported Languages

The OCR extractor supports multiple languages through the ISA SuryaOCR model. Common language codes include:

- `en`: English
- `zh`: Chinese (Simplified)
- `es`: Spanish
- `fr`: French
- `de`: German
- `ja`: Japanese
- `ko`: Korean

## Output Format

### Text Results Structure

Each text region in `text_results` contains:

```python
{
    "text": "Extracted text content",
    "confidence": 0.95,  # Confidence score (0.0 to 1.0)
    # Additional fields may be available depending on the model
}
```

### Complete Result Structure

```python
{
    "success": True,
    "text_results": [
        {"text": "Hello World", "confidence": 0.95},
        {"text": "Sample Text", "confidence": 0.88}
    ],
    "total_text": "Hello World Sample Text",
    "total_characters": 23,
    "region_count": 2
}
```

## Performance Tips

1. **Image Quality**: Higher quality images produce better OCR results
2. **Language Specification**: Specify only the languages you expect to improve accuracy
3. **Confidence Filtering**: Use appropriate confidence thresholds to balance accuracy and completeness
4. **Batch Processing**: Process multiple images concurrently for better performance

## Troubleshooting

### Common Issues

1. **Empty Results**: 
   - Check image quality and format
   - Verify the image contains readable text
   - Try lowering confidence threshold

2. **Low Accuracy**:
   - Improve image resolution
   - Ensure proper lighting in the image
   - Specify correct languages

3. **Performance Issues**:
   - Consider image size and complexity
   - Use confidence filtering to reduce processing time

### Error Messages

- `"OCR extraction failed: Network error"`: Check internet connection
- `"Failed to process image"`: Verify image file exists and is readable
- `"Unknown error occurred"`: Check ISA Model Client configuration

## Testing

Run the test suite:

```bash
pytest tools/services/intelligence_service/vision/tests/test_ocr_extract.py -v
```

## Dependencies

- `isa-model-client`: For accessing ISA SuryaOCR model
- `asyncio`: For asynchronous operations
- `typing`: For type hints

## License

This service is part of the ISA MCP project and follows the same licensing terms.