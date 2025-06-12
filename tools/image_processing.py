from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from typing import List, Dict, Any, Tuple
import colorsys
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """图像处理工具类"""
    
    def __init__(self):
        self.font_cache = {}
        self.target_width = 1200  # 目标宽度
        self.target_height = 800  # 目标高度
        
    def get_image_size(self, image_url: str) -> Tuple[int, int]:
        """获取图片尺寸"""
        try:
            response = requests.get(image_url, stream=True)
            img = Image.open(BytesIO(response.content))
            return img.size
        except Exception as e:
            logger.error(f"Error getting image size: {e}")
            raise
            
    def get_color_brightness(self, color: str) -> float:
        """计算颜色亮度 (0-255)"""
        try:
            # 处理 rgba 格式
            if color.startswith('rgba'):
                color = color.strip('rgba()').split(',')
                r, g, b = map(int, color[:3])
            # 处理 rgb 格式
            elif color.startswith('rgb'):
                color = color.strip('rgb()').split(',')
                r, g, b = map(int, color)
            # 处理十六进制格式
            else:
                color = color.lstrip('#')
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
                
            # 使用感知亮度公式
            return (0.299 * r + 0.587 * g + 0.114 * b)
            
        except Exception as e:
            logger.error(f"Error calculating color brightness: {e}")
            return 128  # 返回中等亮度作为默认值
            
    def _parse_color(self, color_str: str) -> tuple:
        """解析颜色字符串为RGBA元组"""
        try:
            if color_str.startswith('rgba'):
                # 处理 rgba 格式
                values = color_str.strip('rgba()').split(',')
                return tuple(map(int, values))
            elif color_str.startswith('rgb'):
                # 处理 rgb 格式
                values = color_str.strip('rgb()').split(',')
                return tuple(map(int, values)) + (255,)
            else:
                # 处理十六进制格式
                color = color_str.lstrip('#')
                if len(color) == 6:
                    r = int(color[0:2], 16)
                    g = int(color[2:4], 16)
                    b = int(color[4:6], 16)
                    return (r, g, b, 255)
                return (0, 0, 0, 255)  # 默认黑色
        except Exception as e:
            logger.error(f"Error parsing color {color_str}: {e}")
            return (0, 0, 0, 255)  # 默认黑色

    async def overlay_text(self, 
                          image_url: str,
                          text_placements: List[Dict[str, Any]]) -> Image.Image:
        """在图片上叠加文字"""
        try:
            # 获取图片
            response = requests.get(image_url, stream=True)
            image = Image.open(BytesIO(response.content))
            
            # 调整图片大小
            image = self._resize_image(image)
            
            # 如果是 RGBA 模式，转换为 RGB
            if image.mode == 'RGBA':
                image = image.convert('RGB')
            
            # 创建绘图对象
            draw = ImageDraw.Draw(image, 'RGBA')  # 使用RGBA模式以支持透明度
            
            # 首先计算所有文本的总边界框
            total_bbox = None
            text_boxes = []
            
            for placement in text_placements:
                try:
                    # 获取字体
                    font = self._get_font(placement.font_family, placement.font_size)
                    
                    # 计算文本位置和大小
                    pos = placement.position
                    x = pos['x1'] * image.width
                    y = pos['y1'] * image.height
                    
                    # 使用 textbbox 获取文本边界框
                    bbox = draw.textbbox((x, y), placement.text, font=font)
                    text_boxes.append({
                        'bbox': bbox,
                        'placement': placement,
                        'font': font,
                        'x': x,
                        'y': y
                    })
                    
                    # 更新总边界框
                    if total_bbox is None:
                        total_bbox = list(bbox)
                    else:
                        total_bbox[0] = min(total_bbox[0], bbox[0])  # x1
                        total_bbox[1] = min(total_bbox[1], bbox[1])  # y1
                        total_bbox[2] = max(total_bbox[2], bbox[2])  # x2
                        total_bbox[3] = max(total_bbox[3], bbox[3])  # y2
                        
                except Exception as e:
                    logger.error(f"Error calculating text box: {e}")
                    continue
            
            if total_bbox and text_boxes:
                # 为整个文本块添加背景
                padding = (total_bbox[3] - total_bbox[1]) * 0.2  # 使用文本高度的20%作为内边距
                background_box = [
                    total_bbox[0] - padding,
                    total_bbox[1] - padding,
                    total_bbox[2] + padding,
                    total_bbox[3] + padding
                ]
                
                # 绘制半透明背景
                draw.rectangle(background_box, fill=(0, 0, 0, 80))
                
                # 绘制所有文本
                for text_box in text_boxes:
                    # 解析颜色
                    color = self._parse_color(text_box['placement'].color)
                    
                    # 绘制文本
                    draw.text(
                        (text_box['x'], text_box['y']),
                        text_box['placement'].text,
                        font=text_box['font'],
                        fill=color
                    )
            
            return image
            
        except Exception as e:
            logger.error(f"Error overlaying text: {e}")
            raise
            
    def _resize_image(self, image: Image.Image) -> Image.Image:
        """调整图片大小到目标尺寸"""
        # 计算宽高比
        aspect_ratio = image.width / image.height
        target_ratio = self.target_width / self.target_height
        
        if aspect_ratio > target_ratio:
            # 图片更宽，以高度为准
            new_height = self.target_height
            new_width = int(new_height * aspect_ratio)
        else:
            # 图片更高，以宽度为准
            new_width = self.target_width
            new_height = int(new_width / aspect_ratio)
        
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
    def _get_font(self, font_family: str, size: int) -> ImageFont.FreeTypeFont:
        """获取字体对象（带缓存）"""
        cache_key = f"{font_family}_{size}"
        if cache_key not in self.font_cache:
            try:
                self.font_cache[cache_key] = ImageFont.truetype(font_family, size)
            except Exception:
                # 如果找不到指定字体，使用默认字体
                logger.warning(f"Font {font_family} not found, using default font")
                self.font_cache[cache_key] = ImageFont.load_default()
                
        return self.font_cache[cache_key] 