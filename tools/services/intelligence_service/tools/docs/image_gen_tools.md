# Image Generation Tools Documentation

## Overview

The `image_gen_tools.py` provides intelligent image generation capabilities for MCP clients. It generates high-quality images using AI-powered models with multiple specialized modes, automatic cost tracking, and transparent billing information.

## Available Tools

### `generate_image`

Creates images using advanced AI models with specialized capabilities. The AI automatically selects the best model and parameters based on the image type requested.

**Function Signature:**
```python
async def generate_image(
    prompt: str,
    image_type: str = "text_to_image",
    init_image_url: Optional[str] = None,
    width: int = 1024,
    height: int = 1024,
    strength: float = 0.8,
    target_image_url: Optional[str] = None
) -> str
```

**Parameters:**
- `prompt` (required): Text description or transformation instruction
- `image_type` (optional): Type of image generation (default: "text_to_image")
- `init_image_url` (optional): Initial image URL for transformation tasks
- `width` (optional): Image width in pixels (default: 1024)
- `height` (optional): Image height in pixels (default: 1024)
- `strength` (optional): Transformation strength 0.0-1.0 (default: 0.8)
- `target_image_url` (optional): Target image URL for face swap operations

**Returns:**
JSON response with generated image URLs, cost information, and metadata

## Image Generation Types

The AI automatically selects the most appropriate model and processing approach based on the image type:

### Text-to-Image
Generate images from text descriptions using FLUX Schnell.
```
Input: "text_to_image"
Cost: $3 per 1000 images
Speed: � Very Fast
```

### Image-to-Image
Transform existing images with new prompts using FLUX Kontext Pro.
```
Input: "image_to_image"
Cost: $0.04 per image
Speed: = Medium
Required: init_image_url
```

### Sticker Generation
Create cute sticker designs using specialized Sticker Maker.
```
Input: "sticker"
Cost: $0.0024 per image
Speed: � Fast
```

### Emoji Generation
Generate custom emoji designs using Sticker Maker.
```
Input: "emoji"
Cost: $0.0024 per image
Speed: � Fast
```

### Professional Headshot
Convert casual photos to professional portraits using FLUX Kontext Pro.
```
Input: "professional_headshot"
Cost: $0.04 per image
Speed: = Medium
Required: init_image_url
```

### Face Swap
Swap faces between images using advanced Face Swap model.
```
Input: "face_swap"
Cost: $0.04 per image
Speed: = Medium
Required: init_image_url, target_image_url
```

## Usage Examples

### Basic Text-to-Image
```python
# AI selects FLUX Schnell for optimal cost/speed
result = await mcp_client.call_tool("generate_image", {
    "prompt": "a beautiful sunset over mountains",
    "image_type": "text_to_image",
    "width": 1024,
    "height": 1024
})
```

### Image Transformation
```python
# AI uses FLUX Kontext Pro for high-quality transformations
result = await mcp_client.call_tool("generate_image", {
    "prompt": "transform into cyberpunk style",
    "image_type": "image_to_image",
    "init_image_url": "https://example.com/photo.jpg",
    "strength": 0.8
})
```

### Sticker Creation
```python
# AI uses Sticker Maker for cost-effective cute designs
result = await mcp_client.call_tool("generate_image", {
    "prompt": "cute robot character",
    "image_type": "sticker",
    "width": 1152,
    "height": 1152
})
```

### Professional Headshot
```python
# AI transforms casual photos to professional portraits
result = await mcp_client.call_tool("generate_image", {
    "prompt": "professional business headshot",
    "image_type": "professional_headshot",
    "init_image_url": "https://example.com/casual-photo.jpg",
    "strength": 0.6
})
```

### Face Swap
```python
# AI performs advanced face swapping
result = await mcp_client.call_tool("generate_image", {
    "prompt": "face swap",
    "image_type": "face_swap",
    "init_image_url": "https://example.com/source-face.jpg",
    "target_image_url": "https://example.com/target-body.jpg"
})
```

### Custom Emoji
```python
# AI creates custom emoji designs
result = await mcp_client.call_tool("generate_image", {
    "prompt": "thumbs up gesture",
    "image_type": "emoji"
})
```

## Response Format

### Success Response
```json
{
  "status": "success",
  "action": "generate_image",
  "data": {
    "prompt": "a beautiful sunset over mountains",
    "image_type": "text_to_image",
    "image_urls": [
      "https://replicate.delivery/.../out-0.jpg"
    ],
    "cost": 0.003,
    "model": "flux-schnell"
  },
  "timestamp": "2025-07-13T16:52:22.071592"
}
```

### Error Response
```json
{
  "status": "error",
  "action": "generate_image",
  "data": {
    "prompt": "test prompt",
    "image_type": "image_to_image"
  },
  "timestamp": "2025-07-13T16:52:22.071592",
  "error": "init_image_url is required for image-to-image generation"
}
```

## Cost Comparison

| Image Type | Model | Cost | Best Use Case |
|------------|-------|------|---------------|
| text_to_image | FLUX Schnell | $3/1000 | High-volume generation |
| image_to_image | FLUX Kontext Pro | $0.04/img | Photo transformation |
| sticker | Sticker Maker | $0.0024/img | Cute graphics |
| emoji | Sticker Maker | $0.0024/img | Custom emojis |
| professional_headshot | FLUX Kontext Pro | $0.04/img | Business photos |
| face_swap | Face Swap | $0.04/img | Creative content |

## Available Information Tool

### `get_image_generation_types`

Get detailed information about all available image generation types and their capabilities.

**Function Signature:**
```python
def get_image_generation_types() -> str
```

**Returns:**
Comprehensive information about all available image types, including descriptions, requirements, and cost estimates.

**Usage:**
```python
result = await mcp_client.call_tool("get_image_generation_types", {})
```

**Response:**
```json
{
  "status": "success",
  "action": "get_available_types",
  "data": {
    "available_types": [
      "text_to_image",
      "image_to_image",
      "style_transfer",
      "sticker_generation",
      "face_swap",
      "professional_headshot",
      "photo_inpainting",
      "photo_outpainting",
      "emoji_generation",
      "t2i",
      "i2i"
    ],
    "total_types": 11,
    "descriptions": {
      "text_to_image": {
        "description": "Generate images from text descriptions",
        "requires_init_image": false,
        "cost_estimate": 0.003,
        "model": "flux-schnell"
      },
      "sticker": {
        "description": "Generate cute sticker designs",
        "requires_init_image": false,
        "cost_estimate": 0.0024,
        "model": "sticker-maker"
      }
    }
  }
}
```

## AI Decision Making

The AI automatically determines:

### Model Selection
- **FLUX Schnell**: For text-to-image when speed and cost efficiency are priorities
- **FLUX Kontext Pro**: For image transformations requiring high quality and control
- **Sticker Maker**: For cute designs, stickers, and emojis (most cost-effective)
- **Face Swap**: For advanced face manipulation tasks

### Parameter Optimization
- **Text-to-image**: Optimizes for speed with 3 inference steps
- **Image transformations**: Balances quality and transformation strength
- **Stickers/Emojis**: Maximizes output quality with specialized parameters
- **Professional headshots**: Uses moderate strength to preserve identity

## Best Practices

### Choosing Image Types
- **text_to_image**: General purpose, high volume needs
- **sticker**: Cheapest option for simple, cute graphics  
- **emoji**: Custom emoji creation for apps/chat
- **professional_headshot**: LinkedIn photos, business portraits
- **image_to_image**: Photo editing and style transfer
- **face_swap**: Entertainment and creative content

### Cost Optimization
```python
# High-volume generation - use text_to_image
for prompt in many_prompts:
    result = await generate_image(prompt, "text_to_image")

# Simple graphics - use sticker (most cost-effective)
result = await generate_image("cute design", "sticker")

# Photo editing - use image_to_image
result = await generate_image("artistic style", "image_to_image", init_image_url)
```

### Error Handling
```python
result = await mcp_client.call_tool("generate_image", params)
result_data = json.loads(result)

if result_data["status"] == "success":
    images = result_data["data"]["image_urls"]
    cost = result_data["data"]["cost"]
    print(f"Generated {len(images)} images for ${cost:.6f}")
else:
    error = result_data["error"]
    print(f"Generation failed: {error}")
```

### Parameter Guidelines
- **Width/Height**: Use 1024x1024 for general images, 1152x1152 for stickers
- **Strength**: 0.6-0.7 for subtle changes, 0.8-0.9 for dramatic transformations
- **Image URLs**: All input images must be publicly accessible URLs

## Integration Examples

### React Agent Integration
```python
# In your React agent loop
image_result = await mcp_client.call_tool("generate_image", {
    "prompt": user_description,
    "image_type": "text_to_image",
    "width": 1024,
    "height": 1024
})

image_data = json.loads(image_result)
if image_data["status"] == "success":
    image_url = image_data["data"]["image_urls"][0]
    cost = image_data["data"]["cost"]
    # Use image_url in your application
```

### Batch Processing Workflow
```python
async def process_image_batch(prompts, image_type="text_to_image"):
    results = []
    total_cost = 0.0
    
    for prompt in prompts:
        result = await mcp_client.call_tool("generate_image", {
            "prompt": prompt,
            "image_type": image_type
        })
        
        result_data = json.loads(result)
        if result_data["status"] == "success":
            data = result_data["data"]
            results.append(data["image_urls"][0])
            total_cost += data["cost"]
    
    print(f"Generated {len(results)} images for ${total_cost:.6f}")
    return results
```

### Professional Headshot Pipeline
```python
async def create_professional_headshots(casual_photos):
    headshots = []
    
    for photo_url in casual_photos:
        result = await mcp_client.call_tool("generate_image", {
            "prompt": "professional business headshot, high quality",
            "image_type": "professional_headshot",
            "init_image_url": photo_url,
            "strength": 0.6
        })
        
        result_data = json.loads(result)
        if result_data["status"] == "success":
            headshots.append(result_data["data"]["image_urls"][0])
    
    return headshots
```

## Testing

Run the comprehensive test suite:

```bash
python tools/services/intelligence_service/tools/tests/test_image_gen.py
```

**Expected Results:**
```
==================================================
TEST SUMMARY
==================================================
Tests Passed: 4/4
Basic Image Generation Functionality:  PASS
Image Generation Types:  PASS  
Image Type Information:  PASS
Parameter Validation:  PASS

Success Rate: 100.0%
```

## Error Handling

Common error scenarios and handling:

1. **Missing Required Parameters**: Clear validation messages for required fields
2. **Invalid Image Types**: Automatic fallback to text-to-image
3. **ISA Service Issues**: Graceful error handling with detailed messages
4. **Invalid URLs**: Validation of image URL accessibility

## Performance Notes

- **Speed**: Text-to-image is fastest (2-5 seconds), image transformations take 5-15 seconds
- **Cost**: Stickers/emojis are most cost-effective, text-to-image best for volume
- **Quality**: FLUX Kontext Pro provides highest quality for transformations
- **Billing**: All costs are automatically tracked and reported in responses

## Security

- **Input Validation**: All prompts and parameters are validated before processing
- **URL Safety**: Image URLs are validated for accessibility and safety
- **Cost Controls**: Transparent cost reporting prevents unexpected charges
- **Error Isolation**: Failures don't affect other operations

## Summary

The image_gen_tools.py provides intelligent AI-driven image generation that:
- **Automatically selects optimal models** based on image type
- **Provides transparent cost tracking** for all operations
- **Supports 9 specialized generation modes** for different use cases
- **Handles errors gracefully** with detailed feedback
- **Integrates seamlessly with MCP workflows**
- **Optimizes for both cost and quality** based on requirements

Use this tool as the primary image generation interface for your MCP applications. Simply specify the desired image type and prompt - the AI handles all model selection and optimization automatically.