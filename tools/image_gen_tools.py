#!/usr/bin/env python
"""
Image Generation Tools for MCP Server
Simple image generation with URL return only
"""
import json
from datetime import datetime
from typing import Optional

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger

# Import isa_model
from isa_model.inference import AIFactory

logger = get_logger(__name__)

def register_image_gen_tools(mcp):
    """Register image generation tool with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def generate_image(
        prompt: str,
        image_type: str = "t2i",  # "t2i" or "i2i"
        init_image_path: Optional[str] = None,  # Required for i2i
        width: int = 1024,
        height: int = 1024,
        strength: float = 0.8,  # For i2i only
        user_id: str = "default"
    ) -> str:
        """Generate image from text prompt or transform existing image
        
        This tool creates images using AI models. Supports both text-to-image (t2i)
        and image-to-image (i2i) generation. Returns image URLs only.
        
        Args:
            prompt: Text description of the desired image
            image_type: "t2i" for text-to-image or "i2i" for image-to-image
            init_image_path: Path to initial image (required for i2i)
            width: Image width in pixels
            height: Image height in pixels  
            strength: Transformation strength for i2i (0.0-1.0)
            user_id: User identifier
            
        Returns:
            JSON string with image URLs
        
        Keywords: image, generate, ai, picture, art, creation, text-to-image, i2i
        Category: image
        """
        
        try:
            # Validate parameters
            if image_type == "i2i" and not init_image_path:
                raise ValueError("init_image_path is required for image-to-image generation")
            
            # Create image generation service
            img = AIFactory().get_img(type=image_type)
            
            # Generate image based on type
            if image_type == "t2i":
                result = await img.generate_image(
                    prompt=prompt,
                    width=width,
                    height=height
                )
            elif image_type == "i2i":
                if not init_image_path:
                    raise ValueError("init_image_path is required for i2i generation")
                result = await img.image_to_image(
                    prompt=prompt,
                    init_image=init_image_path,
                    strength=strength
                )
            else:
                raise ValueError(f"Unsupported image_type: {image_type}. Use 't2i' or 'i2i'")
            
            # Close the service
            await img.close()
            
            # Extract URLs from result and convert FileOutput objects to strings
            raw_urls = result.get('urls', [])
            image_urls = [str(url) for url in raw_urls]  # Convert FileOutput objects to strings
            
            if not image_urls:
                raise Exception("No image URLs returned from generation service")
            
            # Simple response with URLs only (ensure all values are JSON serializable)
            response = {
                "status": "success",
                "action": "generate_image",
                "data": {
                    "prompt": str(prompt),
                    "image_type": str(image_type),
                    "image_urls": [str(url) for url in image_urls],  # Ensure URLs are strings
                    "cost_usd": float(result.get('cost_usd', 0.0)) if isinstance(result, dict) else 0.0
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Image generated ({image_type}): '{prompt}' -> {len(image_urls)} URLs")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "generate_image",
                "data": {
                    "prompt": prompt,
                    "image_type": image_type,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Image generation failed: {e}")
            return json.dumps(error_response)

logger.info("Image generation tools registered successfully")