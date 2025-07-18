#!/usr/bin/env python3
"""
Vision Tools - MCP tools wrapper for image analysis
基于 ImageAnalyzer 的视觉分析工具
"""

import json
from typing import List, Optional, Union
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.intelligence_service.vision.image_analyzer import image_analyzer
from core.logging import get_logger

logger = get_logger(__name__)

class VisionTools(BaseTool):
    """视觉分析工具，基于 ImageAnalyzer 提供 MCP 接口"""
    
    def __init__(self):
        super().__init__()
        self.analyzer = image_analyzer
    
    async def analyze_image(
        self,
        image: Union[str, bytes],
        prompt: str,
        model: Optional[str] = None,
        provider: str = "openai",
        response_format: str = "text"
    ) -> str:
        """
        分析图像内容
        
        Args:
            image: 图像文件路径或字节数据
            prompt: 分析提示词
            model: 可选的模型规格
            provider: 提供商 (openai, isa等)
            response_format: 响应格式提示
        """
        logger.info(f"🔍 开始图像分析: {prompt[:50]}...")
        
        try:
            result = await self.analyzer.analyze(
                image=image,
                prompt=prompt,
                model=model,
                provider=provider,
                response_format=response_format
            )
            
            if result.success:
                logger.info(f"✅ 图像分析完成，用时 {result.processing_time:.2f}s")
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
                logger.error(f"❌ 图像分析失败: {result.error}")
                return self.create_response(
                    "error",
                    "analyze_image",
                    {},
                    f"分析失败: {result.error}"
                )
                
        except Exception as e:
            logger.error(f"❌ 图像分析异常: {e}")
            return self.create_response(
                "error",
                "analyze_image",
                {},
                f"分析异常: {str(e)}"
            )
    
    async def describe_image(
        self,
        image: Union[str, bytes],
        detail_level: str = "medium",
        language: str = "zh-cn"
    ) -> str:
        """
        描述图像内容
        
        Args:
            image: 图像文件路径或字节数据
            detail_level: 详细级别 (basic, medium, detailed)
            language: 语言 (zh-cn, en)
        """
        
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
        
        return await self.analyze_image(
            image=image,
            prompt=prompt,
            response_format="description"
        )
    
    async def extract_text(
        self,
        image: Union[str, bytes],
        language: str = "auto"
    ) -> str:
        """
        从图像中提取文字 (OCR)
        
        Args:
            image: 图像文件路径或字节数据
            language: 语言代码 (auto, zh, en等)
        """
        
        if language == "auto":
            prompt = "请提取图片中的所有文字内容，保持原有格式和布局。如果有多种语言，请全部提取。"
        else:
            prompt = f"请提取图片中所有 {language} 文字内容，保持原有格式和布局。"
        
        return await self.analyze_image(
            image=image,
            prompt=prompt,
            response_format="text"
        )
    
    async def identify_objects(
        self,
        image: Union[str, bytes],
        object_type: str = "all"
    ) -> str:
        """
        识别图像中的对象
        
        Args:
            image: 图像文件路径或字节数据
            object_type: 对象类型 (all, people, animals, vehicles, food等)
        """
        
        prompts = {
            "all": "请识别并列出图片中的所有主要对象和物品。",
            "people": "请识别图片中的人物，包括人数、位置、动作和外观特征。",
            "animals": "请识别图片中的动物，包括种类、数量和行为。",
            "vehicles": "请识别图片中的交通工具，包括类型、颜色和位置。",
            "food": "请识别图片中的食物，包括种类、状态和摆盘方式。",
            "text": "请识别图片中的文字内容和文本元素。"
        }
        
        prompt = prompts.get(object_type, prompts["all"])
        
        return await self.analyze_image(
            image=image,
            prompt=prompt,
            response_format="json"
        )
    
    async def analyze_emotion(
        self,
        image: Union[str, bytes]
    ) -> str:
        """
        分析图像中的情感表达
        
        Args:
            image: 图像文件路径或字节数据
        """
        
        prompt = """请分析图片中的情感表达，包括：
        1. 人物的面部表情和情感状态
        2. 整体画面的情感氛围
        3. 色彩和构图传达的情感信息
        4. 场景和环境的情感影响
        
        请以JSON格式返回分析结果，包含emotions, mood, atmosphere等字段。"""
        
        return await self.analyze_image(
            image=image,
            prompt=prompt,
            response_format="json"
        )
    
    async def compare_images(
        self,
        image1: Union[str, bytes],
        image2: Union[str, bytes],
        comparison_aspects: Optional[List[str]] = None
    ) -> str:
        """
        比较两张图片
        
        Args:
            image1: 第一张图片
            image2: 第二张图片  
            comparison_aspects: 比较方面列表
        """
        
        if comparison_aspects is None:
            comparison_aspects = ["内容", "构图", "色彩", "风格"]
        
        aspects_str = "、".join(comparison_aspects)
        
        # 注意：这里需要处理多图片输入，当前 image_analyzer 可能需要扩展
        # 暂时使用单图片分析方式
        try:
            result1 = await self.analyze_image(image1, f"分析第一张图片的{aspects_str}")
            result2 = await self.analyze_image(image2, f"分析第二张图片的{aspects_str}")
            
            comparison_prompt = f"""基于以下两张图片的分析结果，请进行详细比较：

第一张图片分析：
{result1}

第二张图片分析：
{result2}

请比较这两张图片在{aspects_str}方面的异同。"""
            
            # 这里可以调用文本生成器进行比较分析
            from tools.services.intelligence_service.language.text_generator import generate
            comparison_result = await generate(comparison_prompt)
            
            return self.create_response(
                "success",
                "compare_images",
                {
                    "comparison": comparison_result,
                    "aspects": comparison_aspects,
                    "image1_analysis": result1,
                    "image2_analysis": result2
                }
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "compare_images",
                {},
                f"图片比较失败: {str(e)}"
            )


def register_vision_tools(mcp: FastMCP):
    """注册视觉分析工具"""
    vision_tools = VisionTools()
    
    @mcp.tool()
    async def analyze_image(
        image_path: str,
        prompt: str,
        model: str = None,
        provider: str = "openai"
    ) -> str:
        """
        通用图像分析工具
        
        使用VLM模型分析图像内容，支持任意分析提示词。
        
        Keywords: vision, image, analyze, vlm, ai, recognition
        Category: vision
        
        Args:
            image_path: 图像文件路径
            prompt: 分析提示词，描述你想要从图像中获取什么信息
            model: 可选的模型名称
            provider: AI提供商 (openai, isa等)
        """
        return await vision_tools.analyze_image(
            image=image_path,
            prompt=prompt,
            model=model,
            provider=provider
        )
    
    @mcp.tool()
    async def describe_image(
        image_path: str,
        detail_level: str = "medium",
        language: str = "zh-cn"
    ) -> str:
        """
        描述图像内容
        
        自动描述图像的主要内容，包括对象、场景、构图等。
        
        Keywords: describe, image, content, scene, objects
        Category: vision
        
        Args:
            image_path: 图像文件路径
            detail_level: 详细程度 (basic/medium/detailed)
            language: 语言 (zh-cn/en)
        """
        return await vision_tools.describe_image(
            image=image_path,
            detail_level=detail_level,
            language=language
        )
    
    @mcp.tool()
    async def extract_text_from_image(
        image_path: str,
        language: str = "auto"
    ) -> str:
        """
        从图像中提取文字 (OCR)
        
        使用光学字符识别技术提取图像中的文字内容。
        
        Keywords: ocr, text, extract, read, recognition
        Category: vision
        
        Args:
            image_path: 图像文件路径
            language: 文字语言 (auto/zh/en等)
        """
        return await vision_tools.extract_text(
            image=image_path,
            language=language
        )
    
    @mcp.tool()
    async def identify_objects_in_image(
        image_path: str,
        object_type: str = "all"
    ) -> str:
        """
        识别图像中的对象
        
        识别并分类图像中的各种对象和实体。
        
        Keywords: identify, objects, detection, recognition, classification
        Category: vision
        
        Args:
            image_path: 图像文件路径
            object_type: 对象类型 (all/people/animals/vehicles/food/text)
        """
        return await vision_tools.identify_objects(
            image=image_path,
            object_type=object_type
        )
    
    @mcp.tool()
    async def analyze_image_emotion(
        image_path: str
    ) -> str:
        """
        分析图像情感表达
        
        分析图像中的情感内容，包括人物表情、氛围、情绪等。
        
        Keywords: emotion, sentiment, mood, expression, feeling
        Category: vision
        
        Args:
            image_path: 图像文件路径
        """
        return await vision_tools.analyze_emotion(
            image=image_path
        )
    
    @mcp.tool()
    async def compare_two_images(
        image1_path: str,
        image2_path: str,
        comparison_aspects: str = "内容,构图,色彩,风格"
    ) -> str:
        """
        比较两张图片
        
        对比分析两张图片的相似性和差异。
        
        Keywords: compare, similarity, difference, analysis, contrast
        Category: vision
        
        Args:
            image1_path: 第一张图片路径
            image2_path: 第二张图片路径
            comparison_aspects: 比较方面，逗号分隔
        """
        aspects_list = [aspect.strip() for aspect in comparison_aspects.split(',')]
        return await vision_tools.compare_images(
            image1=image1_path,
            image2=image2_path,
            comparison_aspects=aspects_list
        )
    
    @mcp.tool()
    def get_vision_capabilities() -> str:
        """
        获取视觉分析能力列表
        
        返回当前可用的视觉分析功能和支持的操作类型。
        
        Keywords: capabilities, features, vision, list, available
        Category: vision
        """
        capabilities = {
            "supported_formats": ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
            "analysis_types": [
                "通用图像分析",
                "图像描述生成", 
                "OCR文字提取",
                "对象识别检测",
                "情感表达分析",
                "图像对比分析"
            ],
            "supported_providers": ["openai", "isa"],
            "languages": ["zh-cn", "en"],
            "detail_levels": ["basic", "medium", "detailed"],
            "object_types": ["all", "people", "animals", "vehicles", "food", "text"]
        }
        
        return json.dumps(capabilities, indent=2, ensure_ascii=False)
    
    logger.info("🔍 视觉分析工具注册成功")