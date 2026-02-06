#!/usr/bin/env python3
"""
Vision Tools - MCP tools wrapper for image analysis
AI-powered vision analysis tools for image understanding

Tools provided:
- analyze_image: General image analysis with custom prompts
- describe_image: Automatic image description generation
- extract_text_from_image: OCR text extraction
- identify_objects_in_image: Object detection and classification
- analyze_image_emotion: Emotional content analysis
- compare_two_images: Compare and contrast two images
- get_vision_capabilities: List available vision features
"""

import json
from typing import Any, Dict, List, Optional, Union
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.intelligent_tools.vision.image_analyzer import image_analyzer
from core.logging import get_logger
from core.security import SecurityLevel

logger = get_logger(__name__)


class VisionTools(BaseTool):
    """Vision analysis tools using ImageAnalyzer to provide MCP interface"""

    def __init__(self):
        super().__init__()
        self.analyzer = image_analyzer

    def register_tools(self, mcp: FastMCP):
        """Register all vision tools with the MCP server"""
        # analyze_image
        self.register_tool(
            mcp,
            self.analyze_image_impl,
            name="analyze_image",
            description="""General image analysis tool using VLM models.

Analyzes image content with a custom prompt, supporting any analysis request.

Keywords: vision, image, analyze, vlm, ai, recognition
Category: vision

Args:
    image_path: Path to the image file
    prompt: Analysis prompt describing what information to extract
    model: Optional model name to use
    provider: AI provider (openai, isa, etc.)""",
            security_level=SecurityLevel.LOW
        )

        # describe_image
        self.register_tool(
            mcp,
            self.describe_image_impl,
            name="describe_image",
            description="""Describe image content automatically.

Generates a description of the image including objects, scene, colors, and composition.

Keywords: describe, image, content, scene, objects
Category: vision

Args:
    image_path: Path to the image file
    detail_level: Detail level (basic/medium/detailed)
    language: Output language (zh-cn/en)""",
            security_level=SecurityLevel.LOW
        )

        # extract_text_from_image
        self.register_tool(
            mcp,
            self.extract_text_impl,
            name="extract_text_from_image",
            description="""Extract text from image using OCR.

Uses optical character recognition to extract text content from images.

Keywords: ocr, text, extract, read, recognition
Category: vision

Args:
    image_path: Path to the image file
    language: Text language (auto/zh/en, etc.)""",
            security_level=SecurityLevel.LOW
        )

        # identify_objects_in_image
        self.register_tool(
            mcp,
            self.identify_objects_impl,
            name="identify_objects_in_image",
            description="""Identify objects in an image.

Detects and classifies objects and entities in the image.

Keywords: identify, objects, detection, recognition, classification
Category: vision

Args:
    image_path: Path to the image file
    object_type: Object type to identify (all/people/animals/vehicles/food/text)""",
            security_level=SecurityLevel.LOW
        )

        # analyze_image_emotion
        self.register_tool(
            mcp,
            self.analyze_emotion_impl,
            name="analyze_image_emotion",
            description="""Analyze emotional content in an image.

Analyzes emotional content including facial expressions, atmosphere, and mood.

Keywords: emotion, sentiment, mood, expression, feeling
Category: vision

Args:
    image_path: Path to the image file""",
            security_level=SecurityLevel.LOW
        )

        # compare_two_images
        self.register_tool(
            mcp,
            self.compare_images_impl,
            name="compare_two_images",
            description="""Compare two images.

Analyzes similarities and differences between two images.

Keywords: compare, similarity, difference, analysis, contrast
Category: vision

Args:
    image1_path: Path to the first image
    image2_path: Path to the second image
    comparison_aspects: Comparison aspects, comma-separated""",
            security_level=SecurityLevel.LOW
        )

        # get_vision_capabilities
        self.register_tool(
            mcp,
            self.get_capabilities_impl,
            name="get_vision_capabilities",
            description="""Get available vision analysis capabilities.

Returns list of available vision analysis features and supported operations.

Keywords: capabilities, features, vision, list, available
Category: vision""",
            security_level=SecurityLevel.LOW
        )

    async def analyze_image_impl(
        self,
        image_path: str,
        prompt: str,
        model: Optional[str] = None,
        provider: str = "openai"
    ) -> Dict[str, Any]:
        """Analyze image with custom prompt"""
        logger.info(f"Starting image analysis: {prompt[:50]}...")

        try:
            result = await self.analyzer.analyze(
                image=image_path,
                prompt=prompt,
                model=model,
                provider=provider,
                response_format="text"
            )

            if result.success:
                logger.info(f"Image analysis complete, took {result.processing_time:.2f}s")
                return self.create_response(
                    "success",
                    "analyze_image",
                    {
                        "response": result.response,
                        "model_used": result.model_used,
                        "processing_time": result.processing_time,
                        "prompt": prompt,
                        "provider": provider
                    }
                )
            else:
                logger.error(f"Image analysis failed: {result.error}")
                return self.create_response(
                    "error",
                    "analyze_image",
                    {},
                    f"Analysis failed: {result.error}"
                )

        except Exception as e:
            logger.error(f"Image analysis exception: {e}")
            return self.create_response(
                "error",
                "analyze_image",
                {},
                f"Analysis exception: {str(e)}"
            )

    async def describe_image_impl(
        self,
        image_path: str,
        detail_level: str = "medium",
        language: str = "zh-cn"
    ) -> Dict[str, Any]:
        """Describe image content"""
        prompts = {
            "basic": {
                "zh-cn": "请简要描述这张图片的主要内容。",
                "en": "Please briefly describe the main content of this image."
            },
            "medium": {
                "zh-cn": "请详细描述这张图片的内容，包括主要对象、场景、颜色和构图。",
                "en": "Please describe this image in detail, including main objects, scene, colors and composition."
            },
            "detailed": {
                "zh-cn": "请全面分析这张图片，包括所有可见元素、空间关系、视觉风格、情感表达和可能的背景信息。",
                "en": "Please comprehensively analyze this image, including all visible elements, spatial relationships, visual style, emotional expression and possible background information."
            }
        }

        prompt = prompts.get(detail_level, prompts["medium"]).get(language, prompts["medium"]["zh-cn"])

        return await self.analyze_image_impl(
            image_path=image_path,
            prompt=prompt,
            provider="openai"
        )

    async def extract_text_impl(
        self,
        image_path: str,
        language: str = "auto"
    ) -> Dict[str, Any]:
        """Extract text from image (OCR)"""
        if language == "auto":
            prompt = "请提取图片中的所有文字内容，保持原有格式和布局。如果有多种语言，请全部提取。"
        else:
            prompt = f"请提取图片中所有 {language} 文字内容，保持原有格式和布局。"

        return await self.analyze_image_impl(
            image_path=image_path,
            prompt=prompt,
            provider="openai"
        )

    async def identify_objects_impl(
        self,
        image_path: str,
        object_type: str = "all"
    ) -> Dict[str, Any]:
        """Identify objects in image"""
        prompts = {
            "all": "请识别并列出图片中的所有主要对象和物品。",
            "people": "请识别图片中的人物，包括人数、位置、动作和外观特征。",
            "animals": "请识别图片中的动物，包括种类、数量和行为。",
            "vehicles": "请识别图片中的交通工具，包括类型、颜色和位置。",
            "food": "请识别图片中的食物，包括种类、状态和摆盘方式。",
            "text": "请识别图片中的文字内容和文本元素。"
        }

        prompt = prompts.get(object_type, prompts["all"])

        return await self.analyze_image_impl(
            image_path=image_path,
            prompt=prompt,
            provider="openai"
        )

    async def analyze_emotion_impl(
        self,
        image_path: str
    ) -> Dict[str, Any]:
        """Analyze emotional content in image"""
        prompt = """请分析图片中的情感表达，包括：
        1. 人物的面部表情和情感状态
        2. 整体画面的情感氛围
        3. 色彩和构图传达的情感信息
        4. 场景和环境的情感影响

        请以JSON格式返回分析结果，包含emotions, mood, atmosphere等字段。"""

        return await self.analyze_image_impl(
            image_path=image_path,
            prompt=prompt,
            provider="openai"
        )

    async def compare_images_impl(
        self,
        image1_path: str,
        image2_path: str,
        comparison_aspects: str = "内容,构图,色彩,风格"
    ) -> Dict[str, Any]:
        """Compare two images"""
        aspects_list = [aspect.strip() for aspect in comparison_aspects.split(',')]
        aspects_str = "、".join(aspects_list)

        try:
            result1 = await self.analyze_image_impl(image1_path, f"分析这张图片的{aspects_str}")
            result2 = await self.analyze_image_impl(image2_path, f"分析这张图片的{aspects_str}")

            comparison_prompt = f"""基于以下两张图片的分析结果，请进行详细比较：

第一张图片分析：
{result1}

第二张图片分析：
{result2}

请比较这两张图片在{aspects_str}方面的异同。"""

            from tools.intelligent_tools.language.text_generator import generate
            comparison_result = await generate(comparison_prompt)

            return self.create_response(
                "success",
                "compare_images",
                {
                    "comparison": comparison_result,
                    "aspects": aspects_list,
                    "image1_analysis": result1,
                    "image2_analysis": result2
                }
            )

        except Exception as e:
            return self.create_response(
                "error",
                "compare_images",
                {},
                f"Image comparison failed: {str(e)}"
            )

    async def get_capabilities_impl(self) -> Dict[str, Any]:
        """Get vision capabilities list"""
        capabilities = {
            "supported_formats": ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
            "analysis_types": [
                "General image analysis",
                "Image description generation",
                "OCR text extraction",
                "Object detection",
                "Emotion analysis",
                "Image comparison"
            ],
            "supported_providers": ["openai", "isa"],
            "languages": ["zh-cn", "en"],
            "detail_levels": ["basic", "medium", "detailed"],
            "object_types": ["all", "people", "animals", "vehicles", "food", "text"]
        }

        return self.create_response(
            "success",
            "get_vision_capabilities",
            capabilities
        )


def register_vision_tools(mcp: FastMCP):
    """Register vision analysis tools"""
    tool = VisionTools()
    tool.register_tools(mcp)
    logger.debug("Vision tools registered successfully")
    return tool
