# Image Analyzer - Generic VLM Atomic Function

## Overview

The `image_analyzer` is a pure atomic function that provides generic Vision Language Model (VLM) capabilities. It takes any image and any prompt, then returns the VLM's response through the ISA client.

## Key Features

- ✅ **Truly Atomic** - Pure function with no business logic
- ✅ **Generic VLM Wrapper** - Works with any image analysis task
- ✅ **Multiple Input Types** - Supports file paths and image bytes
- ✅ **ISA Client Integration** - Unified access to OpenAI, Anthropic, ISA models
- ✅ **Comprehensive Error Handling** - Graceful failure with detailed error messages
- ✅ **Performance Tracking** - Built-in processing time measurement

## Basic Usage

### Simple Analysis

```python
from tools.services.intelligence_service.vision.image_analyzer import analyze

# Analyze any image with any prompt
result = await analyze(
    image="screenshot.png",
    prompt="Describe what you see in this image"
)

print(f"Response: {result.response}")
print(f"Success: {result.success}")
print(f"Model: {result.model_used}")
print(f"Time: {result.processing_time:.3f}s")
```

### Advanced Usage

```python
from tools.services.intelligence_service.vision.image_analyzer import ImageAnalyzer

analyzer = ImageAnalyzer()

# Custom model and provider
result = await analyzer.analyze(
    image="screenshot.png",
    prompt="Extract all text visible in this image",
    model="gpt-4.1",
    provider="openai"
)
```

### Image Bytes Input

```python
# Read image as bytes
with open("image.png", "rb") as f:
    image_bytes = f.read()

result = await analyze(
    image=image_bytes,  # Bytes input
    prompt="What colors are in this image?"
)
```

## API Reference

### analyze() Function

Convenience function for quick image analysis.

```python
async def analyze(
    image: Union[str, bytes], 
    prompt: str, 
    **kwargs
) -> ImageAnalysisResult
```

**Parameters:**
- `image` - Image file path (str) or image bytes
- `prompt` - Analysis prompt for the VLM
- `**kwargs` - Additional parameters (model, provider, etc.)

### ImageAnalyzer Class

Main analyzer class with full functionality.

```python
class ImageAnalyzer:
    async def analyze(
        self,
        image: Union[str, bytes],
        prompt: str,
        model: Optional[str] = None,
        provider: str = "openai",
        response_format: str = "text"
    ) -> ImageAnalysisResult
```

**Parameters:**
- `image` - Image to analyze (file path or bytes)
- `prompt` - Analysis prompt requesting any kind of analysis
- `model` - Optional model specification (defaults to provider default)
- `provider` - Provider to use ("openai", "isa", "anthropic")
- `response_format` - Expected response format hint

### ImageAnalysisResult

Result object returned by all analysis functions.

```python
@dataclass
class ImageAnalysisResult:
    response: str              # VLM response text
    model_used: str           # Actual model that processed the request
    processing_time: float    # Time taken in seconds
    success: bool             # Whether analysis succeeded
    error: Optional[str]      # Error message if failed
```

## Use Cases

### 1. Content Description

```python
result = await analyze(
    image="webpage.png",
    prompt="Describe the overall layout and content of this webpage"
)
```

### 2. Text Extraction (OCR)

```python
result = await analyze(
    image="document.png", 
    prompt="Extract all text from this image, maintaining formatting"
)
```

### 3. UI Element Analysis

```python
result = await analyze(
    image="interface.png",
    prompt="List all interactive UI elements visible in this interface"
)
```

### 4. Visual Counting

```python
result = await analyze(
    image="scene.png",
    prompt="Count how many people are visible in this image"
)
```

### 5. Color Analysis

```python
result = await analyze(
    image="design.png",
    prompt="What is the main color scheme used in this design?"
)
```

### 6. Content Verification

```python
result = await analyze(
    image="result.png",
    prompt="Did the search complete successfully? What results are shown?"
)
```

## Error Handling

The analyzer provides comprehensive error handling:

```python
result = await analyze(image="invalid.txt", prompt="test")

if not result.success:
    print(f"Analysis failed: {result.error}")
    # Handle error appropriately
else:
    print(f"Success: {result.response}")
```

**Common Error Types:**
- `Unsupported image type` - Invalid image input type
- `Network error` - ISA client connectivity issues  
- `Model is temporarily unavailable` - VLM service issues
- `File not found` - Invalid image path

## Performance

- **Typical Response Time**: 0.5-2.0 seconds
- **Image Size Limit**: Depends on provider (typically 20MB)
- **Concurrent Requests**: Supports multiple parallel requests
- **Automatic Cleanup**: Temporary files are automatically cleaned up

## Testing

Run comprehensive tests with real VLM calls:

```bash
python tools/services/intelligence_service/vision/test_image_analyzer.py
```

**Test Coverage:**
- ✅ Simple color image analysis
- ✅ Text extraction from images
- ✅ UI elements detection  
- ✅ Bytes input handling
- ✅ Different prompt types
- ✅ Invalid input handling
- ✅ Convenience function testing

## Integration

### With Web Automation

```python
# Step 2: Screen Understanding
page_analysis = await analyze(
    image=screenshot_path,
    prompt=f"Analyze this webpage for the task: {task}"
)

# Step 5: Result Analysis  
result_analysis = await analyze(
    image=final_screenshot,
    prompt=f"Did the task '{task}' complete successfully?"
)
```

### With Other Services

```python
# Document processing
doc_content = await analyze(
    image=document_image,
    prompt="Extract and structure all text content"
)

# Image classification
classification = await analyze(
    image=photo,
    prompt="What category does this image belong to?"
)
```

## Best Practices

1. **Clear Prompts** - Be specific about what you want analyzed
2. **Error Handling** - Always check `result.success` before using response
3. **Resource Management** - Function automatically handles cleanup
4. **Caching** - Consider caching results for repeated analysis of same images
5. **Rate Limiting** - Be mindful of VLM API rate limits

## Atomic Function Design

The image_analyzer follows atomic function principles:

- **No Business Logic** - Only VLM wrapper functionality
- **Pure Function** - Same input always produces same output (modulo VLM variability)
- **No Side Effects** - No global state changes or external dependencies
- **Generic Interface** - Can be used for any image analysis task
- **Isolated Functionality** - Complete independence from other services

This makes it highly reusable and testable across different use cases.