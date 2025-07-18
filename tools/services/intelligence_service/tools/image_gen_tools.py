#!/usr/bin/env python3
"""
Image Generation Tools for MCP Server
Simple image generation with specialized capabilities
"""

import json
from typing import Optional
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.intelligence_service.img.image_intelligence_service import AtomicImageIntelligence
from core.logging import get_logger

logger = get_logger(__name__)

class ImageGenerator(BaseTool):
    """Simple image generation tool using Atomic Image Intelligence"""
    
    def __init__(self):
        super().__init__()
        self.intelligence = AtomicImageIntelligence()
    
    async def generate_image(
        self,
        prompt: str,
        image_type: str = "text_to_image",
        init_image_url: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        strength: float = 0.8,
        target_image_url: Optional[str] = None
    ) -> str:
        """
        Generate image using atomic intelligence
        
        Args:
            prompt: Text description or transformation instruction
            image_type: Type of image generation
            init_image_url: Initial image URL (for image-to-image tasks)
            width: Image width
            height: Image height
            strength: Transformation strength (for image-to-image)
            target_image_url: Target image URL (for face swap)
        """
        print(f"🎨 Starting image generation: {image_type}")
        
        try:
            # Call appropriate service method based on image type
            if image_type == "text_to_image" or image_type == "t2i":
                result = await self.intelligence.generate_text_to_image(
                    prompt=prompt,
                    width=width,
                    height=height,
                    steps=3
                )
            elif image_type == "image_to_image" or image_type == "i2i":
                if not init_image_url:
                    raise ValueError("init_image_url required for image-to-image")
                result = await self.intelligence.transform_image(
                    prompt=prompt,
                    init_image_url=init_image_url,
                    strength=strength,
                    width=width,
                    height=height
                )
            elif image_type == "sticker":
                result = await self.intelligence.generate_sticker(
                    prompt=prompt,
                    width=width,
                    height=height
                )
            elif image_type == "emoji":
                result = await self.intelligence.generate_emoji(
                    description=prompt
                )
            elif image_type == "professional_headshot":
                if not init_image_url:
                    raise ValueError("init_image_url required for professional headshot")
                result = await self.intelligence.create_professional_headshot(
                    input_image_url=init_image_url,
                    style=prompt,
                    strength=strength
                )
            elif image_type == "face_swap":
                if not init_image_url or not target_image_url:
                    raise ValueError("Both source and target images required for face swap")
                result = await self.intelligence.swap_faces(
                    source_face_url=init_image_url,
                    target_image_url=target_image_url
                )
            else:
                # Default to text-to-image
                result = await self.intelligence.generate_text_to_image(
                    prompt=prompt,
                    width=width,
                    height=height,
                    steps=3
                )
            
            if result.get("success"):
                response_data = {
                    "prompt": prompt,
                    "image_type": image_type,
                    "image_urls": result.get("urls", []),
                    "cost": result.get("cost", 0.0),
                    "model": result.get("metadata", {}).get("model", "unknown")
                }
                
                print(f"✅ Image generated successfully (${result.get('cost', 0.0):.6f})")
                
                return self.create_response(
                    "success",
                    "generate_image",
                    response_data
                )
            else:
                print(f"❌ Image generation failed: {result.get('error')}")
                return self.create_response(
                    "error",
                    "generate_image",
                    {"prompt": prompt, "image_type": image_type},
                    result.get("error", "Unknown error")
                )
                
        except Exception as e:
            return self.create_response(
                "error",
                "generate_image",
                {"prompt": prompt, "image_type": image_type},
                f"Image generation failed: {str(e)}"
            )
    

def register_image_gen_tools(mcp: FastMCP):
    """Register image generation tools"""
    generator = ImageGenerator()
    
    @mcp.tool()
    async def generate_image(
        prompt: str,
        image_type: str = "text_to_image",
        init_image_url: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        strength: float = 0.8,
        target_image_url: Optional[str] = None
    ) -> str:
        """
        Generate create make produce images pictures photos artwork using AI
        
        This tool creates new images from text descriptions. Generate images of people, animals, objects, scenes.
        Make pictures of anything: cute kids, children, babies, pets, characters, landscapes, portraits.
        Create images of people, animals, objects. Generate photos of cute kids, beautiful people, professional portraits.
        Make artwork of scenes, characters, objects. Produce pictures of anything you describe.
        
        Keywords: image, picture, photo, generate, create, make, produce, ai, artwork, drawing, painting, illustration, portrait, person, people, child, kid, baby, animal, pet, dog, cat, cute, beautiful, professional, artistic, cartoon, scene, landscape, object, character, of, with, showing, featuring, containing
        Category: image
        
        Args:
            prompt: Text description or transformation instruction (e.g., "cartoon style", "cyberpunk style", "professional headshot")
            image_type: Generation type (text_to_image, image_to_image, sticker, emoji, professional_headshot, face_swap)
            init_image_url: Initial image URL (required for image_to_image, professional_headshot, face_swap)
            width: Image width in pixels (default: 1024)
            height: Image height in pixels (default: 1024)
            strength: Transformation strength 0.0-1.0 (for image_to_image, default: 0.8)
            target_image_url: Target image URL (required for face_swap)
        """
        return await generator.generate_image(
            prompt, image_type, init_image_url, width, height, strength, target_image_url
        )
    
    
    print("🎨 Image generation tools registered successfully")

logger.info("Image generation tools module loaded successfully")