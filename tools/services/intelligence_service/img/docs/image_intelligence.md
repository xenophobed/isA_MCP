# Atomic Image Intelligence Documentation

## Overview

The Atomic Image Intelligence Service provides specialized image processing capabilities through the ISA Model platform. It offers nine distinct image processing modes, each optimized for specific use cases with transparent cost management and batch processing support.

## Available Services

### Core Capabilities

1. **Text-to-Image** - Generate images from text descriptions ($3/1000 images)
2. **Image-to-Image** - Transform existing images with new prompts ($0.04/image)
3. **Style Transfer** - Apply artistic styles to existing images ($0.04/image)
4. **Sticker Generation** - Create cute sticker designs ($0.0024/image)
5. **Face Swap** - Advanced face swapping between images ($0.04/image)
6. **Professional Headshot** - Convert casual photos to professional portraits ($0.04/image)
7. **Photo Inpainting** - Fill or modify specific areas within images ($0.04/image)
8. **Photo Outpainting** - Expand images beyond original boundaries ($0.04/image)
9. **Emoji Generation** - Create custom emoji designs ($0.0024/image)

## Service Architecture

```
AtomicImageIntelligence (Direct ISA Client Usage)
    ↓
ISAModelClient (Direct Connection)
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│  FLUX Schnell   │ FLUX Kontext Pro│   Sticker Maker │
│ (Text-to-Image) │(Image-to-Image) │   (Stickers)    │
│   $3/1000       │    $0.04/img    │  $0.0024/img    │
└─────────────────┴─────────────────┴─────────────────┘
```

**Key Architectural Features:**
- Direct ISA client usage (no BaseTool inheritance)
- Lazy-loaded ISA client for optimal performance
- Proper model and provider parameter passing
- Standardized response format across all services

## Quick Start

```python
from tools.services.intelligence_service.img.image_intelligence_service import AtomicImageIntelligence

# Initialize service
service = AtomicImageIntelligence()

# Text to Image - Fast and affordable
result = await service.generate_text_to_image(
    prompt="a cute cat sitting in a garden",
    width=1024,
    height=1024
)
print(f"Generated: {result['urls'][0]}")
```

## Service Methods

### 1. Text-to-Image Generation

**Method**: `generate_text_to_image()`  
**Model**: FLUX Schnell  
**Cost**: $3 per 1000 images  
**Best For**: High-volume, rapid prototyping

```python
result = await service.generate_text_to_image(
    prompt="beautiful sunset over mountains",
    width=1024,
    height=1024,
    num_images=1,
    steps=4
)

# Response
{
    "success": True,
    "urls": ["https://replicate.delivery/.../out-0.jpg"],
    "cost": 0.003,
    "metadata": {
        "task_type": "text_to_image",
        "model": "flux-schnell",
        "billing": {...}
    }
}
```

### 2. Image Transformation

**Method**: `transform_image()`  
**Model**: FLUX Kontext Pro  
**Cost**: $0.04 per image  
**Best For**: Image editing, style application

```python
result = await service.transform_image(
    prompt="transform into a futuristic cityscape",
    init_image_url="https://example.com/input.jpg",
    strength=0.8
)
```

### 3. Style Transfer

**Method**: `transfer_style()`  
**Model**: FLUX Kontext Pro  
**Cost**: $0.04 per image  
**Best For**: Artistic style application

```python
result = await service.transfer_style(
    content_image_url="https://example.com/photo.jpg",
    style_prompt="impressionist painting style",
    strength=0.7
)
```

### 4. Sticker Generation

**Method**: `generate_sticker()`  
**Model**: Sticker Maker  
**Cost**: $0.0024 per image  
**Best For**: Cute designs, social media content

```python
result = await service.generate_sticker(
    prompt="robot",
    width=1152,
    height=1152,
    output_format="webp"
)
```

### 5. Face Swap

**Method**: `swap_faces()`  
**Model**: Face Swap  
**Cost**: $0.04 per image  
**Best For**: Identity transfer, creative portraits

```python
result = await service.swap_faces(
    source_face_url="https://example.com/face.jpg",
    target_image_url="https://example.com/body.jpg",
    hair_source="target"
)
```

### 6. Professional Headshot

**Method**: `create_professional_headshot()`  
**Model**: FLUX Kontext Pro  
**Cost**: $0.04 per image  
**Best For**: LinkedIn photos, business portraits

```python
result = await service.create_professional_headshot(
    input_image_url="https://example.com/casual.jpg",
    style="professional business headshot",
    strength=0.6
)
```

### 7. Photo Inpainting

**Method**: `inpaint_photo()`  
**Model**: FLUX Kontext Pro  
**Cost**: $0.04 per image  
**Best For**: Object removal, area modification

```python
result = await service.inpaint_photo(
    image_url="https://example.com/photo.jpg",
    inpaint_prompt="remove the background object",
    strength=0.8
)
```

### 8. Photo Outpainting

**Method**: `outpaint_photo()`  
**Model**: FLUX Kontext Pro  
**Cost**: $0.04 per image  
**Best For**: Image extension, scene expansion

```python
result = await service.outpaint_photo(
    image_url="https://example.com/photo.jpg",
    expand_prompt="extend the landscape to show more mountains",
    strength=0.7
)
```

### 9. Emoji Generation

**Method**: `generate_emoji()`  
**Model**: Sticker Maker  
**Cost**: $0.0024 per image  
**Best For**: Custom emojis, chat applications

```python
result = await service.generate_emoji(
    description="thumbs up",
    style="cute emoji"
)
```

## Cost Comparison

| Service | Method | Cost | Speed | Best Use Case |
|---------|--------|------|-------|---------------|
| Text-to-Image | `generate_text_to_image()` | $3/1000 | ⚡ Very Fast | High-volume generation |
| Image Transform | `transform_image()` | $0.04/img | 🔄 Medium | Image editing |
| Style Transfer | `transfer_style()` | $0.04/img | 🎨 Medium | Artistic effects |
| Sticker | `generate_sticker()` | $0.0024/img | ⚡ Fast | Cute graphics |
| Face Swap | `swap_faces()` | $0.04/img | 🔄 Medium | Identity transfer |
| Headshot | `create_professional_headshot()` | $0.04/img | 🔄 Medium | Business photos |
| Inpainting | `inpaint_photo()` | $0.04/img | 🔄 Medium | Object removal |
| Outpainting | `outpaint_photo()` | $0.04/img | 🔄 Medium | Image extension |
| Emoji | `generate_emoji()` | $0.0024/img | ⚡ Fast | Custom emojis |

## Batch Processing

Process multiple images concurrently:

```python
from tools.services.intelligence_service.img.image_intelligence_service import ImageTask

# Create batch tasks
tasks = [
    ImageTask(
        task_type="text_to_image",
        model="flux-schnell",
        parameters={"width": 1024, "height": 1024},
        input_data="a red apple"
    ),
    ImageTask(
        task_type="sticker_generation",
        model="sticker-maker", 
        parameters={"width": 512, "height": 512},
        input_data="happy cat"
    )
]

# Process with concurrency limit
results = await service.batch_process(tasks, max_concurrent=3)

# Analyze results
for i, result in enumerate(results):
    if result["success"]:
        print(f"Task {i+1}: {result['urls'][0]} (${result['cost']:.6f})")
    else:
        print(f"Task {i+1} failed: {result['error']}")
```

## Cost Management

### Cost Estimation

```python
# Get cost estimates before processing
text_to_image_cost = service.get_cost_estimate("text_to_image", 100)
sticker_cost = service.get_cost_estimate("sticker_generation", 10)

print(f"100 text-to-image: ${text_to_image_cost:.6f}")
print(f"10 stickers: ${sticker_cost:.6f}")
```

### Task Information

```python
# Get detailed task information
info = service.get_task_info("professional_headshot")
print(f"Model: {info['model']}")
print(f"Cost: ${info['estimated_cost']:.6f}")
print(f"Description: {info['description']}")
```

### Capability Discovery

```python
# List all available capabilities
capabilities = service.list_capabilities()
print(f"Available services: {capabilities}")

# Validate task types
is_valid = service._validate_task_type("face_swap")
print(f"Face swap available: {is_valid}")
```

## Standard Response Format

All methods return a standardized response:

```python
{
    "success": True,
    "urls": ["https://replicate.delivery/.../image.jpg"],
    "cost": 0.003,
    "metadata": {
        "task_type": "text_to_image",
        "model": "flux-schnell",
        "billing": {
            "total_cost": 0.003,
            "currency": "USD",
            "timestamp": "2025-07-13T...",
            "operation": "image_generation"
        }
    }
}
```

### Error Response

```python
{
    "success": False,
    "error": "Error description",
    "task_type": "text_to_image"
}
```

## Testing

Run the comprehensive test suite:

```bash
python tools/services/intelligence_service/img/tests/test_image_intelligence.py
```

**Expected Results**:
```
==================================================
TEST SUMMARY
==================================================
Tests Passed: 4/4
Basic Image Intelligence Functionality:  PASS
Specialized Image Tasks:  PASS  
Cost Estimation:  PASS
Service Capabilities:  PASS

Success Rate: 100.0%
```

## Advanced Usage

### Complete Workflow

```python
async def image_processing_workflow():
    service = AtomicImageIntelligence()
    
    # 1. Generate base image (cheapest option)
    base_result = await service.generate_text_to_image(
        prompt="professional office environment"
    )
    
    # 2. Create professional headshot
    if base_result["success"]:
        headshot_result = await service.create_professional_headshot(
            input_image_url=base_result["urls"][0],
            style="corporate executive headshot"
        )
    
    # 3. Generate matching sticker
    sticker_result = await service.generate_sticker(
        prompt="professional business person"
    )
    
    return {
        "base_image": base_result["urls"][0],
        "headshot": headshot_result["urls"][0],
        "sticker": sticker_result["urls"][0]
    }
```

### Cost-Optimized Processing

```python
async def cost_optimized_generation(prompts, budget_usd=1.0):
    service = AtomicImageIntelligence()
    
    # Estimate costs
    total_estimated = 0.0
    for prompt in prompts:
        cost = service.get_cost_estimate("text_to_image", 1)
        total_estimated += cost
    
    if total_estimated > budget_usd:
        print(f"Estimated cost ${total_estimated:.6f} exceeds budget ${budget_usd}")
        return []
    
    # Process within budget
    results = []
    actual_cost = 0.0
    
    for prompt in prompts:
        if actual_cost < budget_usd:
            result = await service.generate_text_to_image(prompt=prompt)
            if result["success"]:
                results.append(result["urls"][0])
                actual_cost += result["cost"]
    
    print(f"Generated {len(results)} images for ${actual_cost:.6f}")
    return results
```

## Best Practices

### 1. Choose the Right Service

- **Text-to-Image**: General purpose, high volume needs
- **Sticker/Emoji Generation**: Cheapest option for simple graphics
- **Professional Headshot**: Business and LinkedIn photos
- **Style Transfer**: Artistic effects and creative projects
- **Face Swap**: Entertainment and creative content
- **Inpainting/Outpainting**: Photo editing and enhancement

### 2. Optimize Costs

```python
# Use the most cost-effective service for your needs
if use_case == "high_volume":
    # Text-to-image is most cost-effective for bulk
    method = service.generate_text_to_image
elif use_case == "simple_graphics":
    # Stickers are cheapest per image
    method = service.generate_sticker
elif use_case == "photo_editing":
    # Image-to-image for transformations
    method = service.transform_image
```

### 3. Handle Responses

```python
async def safe_image_generation(service, prompt):
    try:
        result = await service.generate_text_to_image(prompt=prompt)
        
        if result["success"]:
            print(f"✅ Generated: {result['urls'][0]}")
            print(f"💰 Cost: ${result['cost']:.6f}")
            return result["urls"][0]
        else:
            print(f"❌ Generation failed: {result['error']}")
            return None
            
    except Exception as e:
        print(f"🚨 Exception occurred: {e}")
        return None
```

### 4. Monitor Performance

```python
import time

async def benchmark_service():
    service = AtomicImageIntelligence()
    
    start_time = time.time()
    result = await service.generate_text_to_image("test image")
    end_time = time.time()
    
    duration = end_time - start_time
    
    if result["success"]:
        cost = result["cost"]
        print(f"⏱️  Generation time: {duration:.2f}s")
        print(f"💰 Cost: ${cost:.6f}")
        print(f"📊 Cost per second: ${cost/duration:.6f}")
```

## Configuration

The service is configured through task_configs in the AtomicImageIntelligence class and uses direct ISA client initialization:

```python
class AtomicImageIntelligence:
    def __init__(self):
        self.service_name = "atomic_image_intelligence"
        self._client = None  # Lazy-loaded ISA client
        
        # Task type configurations with proper model routing
        self.task_configs = {
            "text_to_image": {
                "model": "flux-schnell",
                "provider": "replicate", 
                "task": "generate",
                "cost_per_1000": 3.0
            },
            "image_to_image": {
                "model": "flux-kontext-pro",  # Correct model for i2i
                "provider": "replicate",
                "task": "img2img", 
                "cost_per_image": 0.04
            },
            "sticker_generation": {
                "model": "sticker-maker",
                "provider": "replicate",
                "task": "generate",
                "cost_per_image": 0.0024
            }
            # ... other configurations
        }
    
    @property
    def isa_client(self):
        """Lazy load ISA client for optimal performance"""
        if self._client is None:
            from isa_model.client import ISAModelClient
            self._client = ISAModelClient()
        return self._client
```

**Key Configuration Updates:**
- Removed BaseTool inheritance for direct ISA client usage
- Added lazy-loaded ISA client property
- Fixed model routing (flux-kontext-pro for image-to-image tasks)
- Proper parameter passing to ISA client with model and provider

## Recent Updates & Fixes

### Version 2.0 - Architecture Improvements

**Fixed Issues:**
- ✅ **Resolved `num_inference_steps` parameter conflict** - Removed BaseTool inheritance causing parameter overrides
- ✅ **Fixed URL extraction** - URLs now properly extracted from `result.urls` instead of `data.urls`
- ✅ **Fixed model routing** - Proper model selection (flux-kontext-pro for i2i, flux-schnell for t2i)
- ✅ **Improved performance** - Direct ISA client usage eliminates middleware overhead

**Architecture Changes:**
- Removed BaseTool inheritance to eliminate parameter conflicts
- Added direct ISA client usage pattern (like text_generator.py)
- Implemented lazy-loaded ISA client for optimal resource usage
- Fixed model and provider parameter passing to ISA client

**Test Results:**
```
Tests Passed: 4/4 (100% success rate)
✅ Text-to-Image Generation: Working ($0.003/image)
✅ Sticker Generation: Working ($0.0024/image) 
✅ Emoji Generation: Working ($0.0024/image)
✅ Cost Estimation: Accurate
✅ Parameter Validation: Proper error handling
```

## Troubleshooting

### Common Issues

1. **ISA Client**: Ensure `REPLICATE_API_TOKEN` is set and ISA service is running
2. **Image URLs**: All methods return publicly accessible URLs from Replicate delivery network
3. **Cost Tracking**: Costs are automatically tracked in billing metadata
4. **Batch Processing**: Use concurrency limits to avoid rate limiting
5. **Model Selection**: Service automatically routes to correct model based on task type

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.INFO)

# This will show detailed request/response logs
service = AtomicImageIntelligence()
result = await service.generate_text_to_image("debug test")
```

## Integration with MCP Tools

The service integrates seamlessly with the existing MCP image generation tools:

```python
# The service can be used directly or through MCP tools
# See tools/services/intelligence_service/image_gen_tools.py for MCP integration
```

## Summary

The Atomic Image Intelligence Service provides:

- **9 specialized image processing capabilities**
- **Transparent cost management with estimates**
- **Batch processing with concurrency control**
- **Standardized response formats**
- **Comprehensive error handling**
- **Production-ready architecture**

Choose the right service based on your use case and budget requirements. Use cost estimation before processing large batches, and leverage batch processing for efficiency.