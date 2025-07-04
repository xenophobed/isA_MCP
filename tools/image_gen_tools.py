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
from tools.base_tool import BaseTool

logger = get_logger(__name__)

class ImageGenerationManager(BaseTool):
    """图像生成管理器 - 使用BaseTool统一管理"""
    
    def __init__(self):
        super().__init__()
    
    async def generate_image_with_billing(
        self,
        prompt: str,
        image_type: str = "t2i",
        init_image_path: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        strength: float = 0.8,
        user_id: str = "default"
    ) -> dict:
        """生成图像并自动处理billing"""
        try:
            # 验证参数
            if image_type == "i2i" and not init_image_path:
                raise ValueError("init_image_path is required for image-to-image generation")
            
            # 使用BaseTool的统一ISA调用
            if image_type == "t2i":
                result_data, billing_info = await self.call_isa_with_billing(
                    input_data=prompt,
                    task="generate_image",
                    service_type="image",
                    parameters={
                        "width": width,
                        "height": height
                    }
                )
            elif image_type == "i2i":
                if not init_image_path:
                    raise ValueError("init_image_path is required for i2i generation")
                result_data, billing_info = await self.call_isa_with_billing(
                    input_data=prompt,
                    task="image_to_image",
                    service_type="image",
                    parameters={
                        "init_image": init_image_path,
                        "strength": strength
                    }
                )
            else:
                raise ValueError(f"Unsupported image_type: {image_type}. Use 't2i' or 'i2i'")
            
            # 提取图像URLs
            image_urls = result_data.get('urls', [])
            if isinstance(image_urls, str):
                image_urls = [image_urls]
            
            if not image_urls:
                raise Exception("No image URLs returned from ISA Model")
            
            response_data = {
                "prompt": str(prompt),
                "image_type": str(image_type),
                "image_urls": [str(url) for url in image_urls],
                "user_id": user_id
            }
            
            logger.info(f"Image generated ({image_type}): '{prompt}' -> {len(image_urls)} URLs")
            return response_data
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise

# 全局实例
_image_manager = ImageGenerationManager()

def register_image_gen_tools(mcp):
    """Register image generation tool with the MCP server"""
    
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
        and image-to-image (i2i) generation. Returns image URLs with billing info.
        
        Args:
            prompt: Text description of the desired image
            image_type: "t2i" for text-to-image or "i2i" for image-to-image
            init_image_path: Path to initial image (required for i2i)
            width: Image width in pixels
            height: Image height in pixels  
            strength: Transformation strength for i2i (0.0-1.0)
            user_id: User identifier
            
        Returns:
            JSON string with image URLs and billing information
        
        Keywords: image, generate, ai, picture, art, creation, text-to-image, i2i
        Category: image
        """
        try:
            # 重置billing信息
            _image_manager.reset_billing()
            
            # 使用ImageGenerationManager生成图像
            result_data = await _image_manager.generate_image_with_billing(
                prompt=prompt,
                image_type=image_type,
                init_image_path=init_image_path,
                width=width,
                height=height,
                strength=strength,
                user_id=user_id
            )
            
            # 使用BaseTool的统一响应格式
            return _image_manager.create_response(
                status="success",
                action="generate_image",
                data=result_data
            )
            
        except Exception as e:
            logger.error(f"Error in generate_image: {e}")
            return _image_manager.create_response(
                status="error",
                action="generate_image",
                data={"prompt": prompt, "image_type": image_type, "user_id": user_id},
                error_message=str(e)
            )

logger.info("Image generation tools registered successfully")