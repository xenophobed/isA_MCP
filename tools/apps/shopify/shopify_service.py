#!/usr/bin/env python
"""
AI Shopping Assistant Service
提供AI增强的购物体验和个性化推荐
"""

import json
import openai
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class StyleProfile:
    """用户风格档案"""
    style_preference: str
    color_palette: List[str]
    size_info: Dict[str, str]
    budget_range: str
    lifestyle: str
    body_type: str

@dataclass
class ShoppingContext:
    """购物上下文"""
    occasion: str
    season: str
    weather: str
    time_of_day: str
    location: str

class AIShoppingAssistant:
    """AI购物助手"""
    
    def __init__(self):
        # OpenAI配置
        self.openai_client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        )
        
        # 模型配置
        self.model = "gpt-4o-mini"
        self.max_tokens = 2000
        
        # 风格知识库
        self.style_knowledge = {
            "casual": {
                "keywords": ["舒适", "休闲", "日常", "轻松"],
                "colors": ["白色", "黑色", "牛仔蓝", "灰色", "米色"],
                "materials": ["棉质", "牛仔", "针织"],
                "pieces": ["T恤", "牛仔裤", "运动鞋", "卫衣", "休闲裤"]
            },
            "business": {
                "keywords": ["专业", "正式", "商务", "优雅"],
                "colors": ["黑色", "深蓝", "灰色", "白色", "酒红"],
                "materials": ["羊毛", "丝绸", "棉质", "聚酯纤维"],
                "pieces": ["西装", "衬衫", "西裤", "皮鞋", "风衣"]
            },
            "romantic": {
                "keywords": ["浪漫", "优雅", "约会", "女性化"],
                "colors": ["粉色", "薰衣草色", "米色", "白色", "浅蓝"],
                "materials": ["蕾丝", "雪纺", "丝绸", "缎面"],
                "pieces": ["连衣裙", "半身裙", "丝巾", "高跟鞋", "小外套"]
            },
            "street": {
                "keywords": ["街头", "时尚", "个性", "潮流"],
                "colors": ["黑色", "白色", "荧光色", "迷彩", "撞色"],
                "materials": ["牛仔", "皮革", "棉质", "尼龙"],
                "pieces": ["帽衫", "工装裤", "运动鞋", "背包", "棒球帽"]
            }
        }
        
        # 季节性推荐
        self.seasonal_trends = {
            "spring": {
                "colors": ["粉色", "薄荷绿", "浅蓝", "米色"],
                "materials": ["棉质", "亚麻", "轻薄针织"],
                "trends": ["花卉印花", "浅色系", "轻薄材质"]
            },
            "summer": {
                "colors": ["白色", "天蓝", "柠檬黄", "薄荷绿"],
                "materials": ["亚麻", "棉质", "雪纺"],
                "trends": ["透气材质", "短袖", "防晒"]
            },
            "autumn": {
                "colors": ["棕色", "橙色", "深绿", "酒红"],
                "materials": ["羊毛", "绒面", "厚棉"],
                "trends": ["层次搭配", "大地色系", "保暖"]
            },
            "winter": {
                "colors": ["黑色", "深蓝", "灰色", "深红"],
                "materials": ["羊毛", "羽绒", "厚针织"],
                "trends": ["保暖", "深色系", "厚重材质"]
            }
        }
    
    async def _call_openai(self, prompt: str, system_prompt: str = None) -> str:
        """调用OpenAI API"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"AI服务暂时不可用: {str(e)}"
    
    async def enhance_search_results(self, query: str, products: List[Dict]) -> List[Dict]:
        """增强搜索结果"""
        if not products:
            return products
        
        system_prompt = """你是一个专业的购物助手，能够理解用户搜索意图并为商品添加相关性评分和推荐理由。"""
        
        prompt = f"""
        用户搜索: "{query}"
        
        商品列表:
        {json.dumps(products, ensure_ascii=False, indent=2)}
        
        请为每个商品添加:
        1. 相关性评分 (1-10分)
        2. 推荐理由 (为什么这个商品匹配用户搜索)
        3. 突出卖点
        
        返回JSON格式的增强商品列表。
        """
        
        try:
            enhanced_result = await self._call_openai(prompt, system_prompt)
            # 尝试解析JSON，如果失败则返回原始商品列表
            try:
                enhanced_products = json.loads(enhanced_result)
                return enhanced_products if isinstance(enhanced_products, list) else products
            except json.JSONDecodeError:
                return products
        except Exception as e:
            logger.error(f"Error enhancing search results: {e}")
            return products
    
    async def generate_search_insights(self, query: str, products: List[Dict]) -> Dict:
        """生成搜索洞察"""
        system_prompt = """你是一个时尚和购物专家，能够分析搜索结果并提供有用的购物洞察。"""
        
        prompt = f"""
        用户搜索: "{query}"
        找到 {len(products)} 个商品
        
        请提供:
        1. 搜索意图分析
        2. 价格范围建议
        3. 风格趋势洞察
        4. 购买建议
        5. 搭配建议
        
        返回JSON格式的洞察报告。
        """
        
        try:
            insights_result = await self._call_openai(prompt, system_prompt)
            try:
                insights = json.loads(insights_result)
                return insights
            except json.JSONDecodeError:
                return {"insights": insights_result}
        except Exception as e:
            logger.error(f"Error generating search insights: {e}")
            return {"error": "无法生成搜索洞察"}
    
    async def generate_product_recommendations(self, product: Dict, user_id: str) -> List[Dict]:
        """生成商品个性化推荐"""
        system_prompt = """你是一个个性化推荐专家，基于用户查看的商品提供相关推荐。"""
        
        prompt = f"""
        用户正在查看的商品:
        {json.dumps(product, ensure_ascii=False, indent=2)}
        
        请推荐3-5个相关商品类型或搭配建议:
        1. 同类商品的其他选择
        2. 搭配商品推荐
        3. 配饰建议
        4. 升级版本推荐
        5. 预算友好替代
        
        返回JSON格式的推荐列表。
        """
        
        try:
            recommendations_result = await self._call_openai(prompt, system_prompt)
            try:
                recommendations = json.loads(recommendations_result)
                return recommendations if isinstance(recommendations, list) else []
            except json.JSONDecodeError:
                return [{"type": "general", "description": recommendations_result}]
        except Exception as e:
            logger.error(f"Error generating product recommendations: {e}")
            return []
    
    async def enhance_product_description(self, product: Dict) -> str:
        """增强商品描述"""
        system_prompt = """你是一个专业的商品文案专家，能够创作吸引人的商品描述。"""
        
        prompt = f"""
        商品信息:
        {json.dumps(product, ensure_ascii=False, indent=2)}
        
        请创作一个吸引人的商品描述，包括:
        1. 商品特色亮点
        2. 适用场景
        3. 材质和工艺优势
        4. 搭配建议
        5. 适合人群
        
        语调要专业又亲切，长度控制在200字以内。
        """
        
        try:
            enhanced_description = await self._call_openai(prompt, system_prompt)
            return enhanced_description
        except Exception as e:
            logger.error(f"Error enhancing product description: {e}")
            return product.get('description', '暂无描述')
    
    async def generate_style_suggestions(self, product: Dict) -> List[Dict]:
        """生成风格搭配建议"""
        system_prompt = """你是一个专业的造型师，擅长为商品提供风格搭配建议。"""
        
        prompt = f"""
        商品信息:
        {json.dumps(product, ensure_ascii=False, indent=2)}
        
        请为这个商品提供3-4种不同风格的搭配建议:
        1. 商务正式风格
        2. 休闲日常风格
        3. 约会浪漫风格
        4. 时尚潮流风格
        
        每种风格包括:
        - 搭配的其他单品
        - 颜色组合建议
        - 适合场合
        - 造型要点
        
        返回JSON格式的搭配建议。
        """
        
        try:
            style_result = await self._call_openai(prompt, system_prompt)
            try:
                style_suggestions = json.loads(style_result)
                return style_suggestions if isinstance(style_suggestions, list) else []
            except json.JSONDecodeError:
                return [{"style": "general", "description": style_result}]
        except Exception as e:
            logger.error(f"Error generating style suggestions: {e}")
            return []
    
    async def generate_size_guide(self, product: Dict) -> Dict:
        """生成尺码指南"""
        system_prompt = """你是一个专业的尺码顾问，帮助用户选择合适的尺码。"""
        
        prompt = f"""
        商品信息:
        {json.dumps(product, ensure_ascii=False, indent=2)}
        
        请提供详细的尺码选择指南:
        1. 测量指导 (如何正确测量身体尺寸)
        2. 尺码建议 (基于不同体型的建议)
        3. 合身效果说明
        4. 注意事项 (材质特性、版型特点等)
        
        返回JSON格式的尺码指南。
        """
        
        try:
            size_guide_result = await self._call_openai(prompt, system_prompt)
            try:
                size_guide = json.loads(size_guide_result)
                return size_guide
            except json.JSONDecodeError:
                return {"guide": size_guide_result}
        except Exception as e:
            logger.error(f"Error generating size guide: {e}")
            return {"error": "无法生成尺码指南"}
    
    async def analyze_cart_and_suggest(self, cart_items: List[Dict], user_id: str) -> Dict:
        """分析购物车并提供建议"""
        system_prompt = """你是一个智能购物助手，能够分析用户的购物车并提供优化建议。"""
        
        prompt = f"""
        用户购物车内容:
        {json.dumps(cart_items, ensure_ascii=False, indent=2)}
        
        请分析购物车并提供:
        1. 搭配完整性分析 (是否缺少某些搭配单品)
        2. 颜色协调性建议
        3. 预算优化建议
        4. 推荐添加的商品
        5. 可以移除的重复或不必要商品
        6. 季节适应性分析
        
        返回JSON格式的分析报告和建议。
        """
        
        try:
            cart_analysis_result = await self._call_openai(prompt, system_prompt)
            try:
                cart_analysis = json.loads(cart_analysis_result)
                return cart_analysis
            except json.JSONDecodeError:
                return {"analysis": cart_analysis_result}
        except Exception as e:
            logger.error(f"Error analyzing cart: {e}")
            return {"error": "无法分析购物车"}
    
    async def generate_complete_outfits(self, products: List[Dict], style_preference: str, 
                                      occasion: str, budget_range: str, user_id: str) -> List[Dict]:
        """生成完整搭配方案"""
        system_prompt = """你是一个专业的造型师，能够从商品库中组合出完整的搭配方案。"""
        
        prompt = f"""
        可用商品:
        {json.dumps(products, ensure_ascii=False, indent=2)}
        
        搭配要求:
        - 风格偏好: {style_preference}
        - 场合: {occasion}
        - 预算范围: {budget_range}
        
        请创建3-4套完整的搭配方案，每套包括:
        1. 搭配的具体商品组合
        2. 总价格
        3. 搭配理念
        4. 适合场合
        5. 造型要点
        6. 可选配饰建议
        
        返回JSON格式的搭配方案列表。
        """
        
        try:
            outfits_result = await self._call_openai(prompt, system_prompt)
            try:
                outfits = json.loads(outfits_result)
                return outfits if isinstance(outfits, list) else []
            except json.JSONDecodeError:
                return [{"outfit": "default", "description": outfits_result}]
        except Exception as e:
            logger.error(f"Error generating outfits: {e}")
            return []
    
    async def generate_styling_tips(self, style_preference: str, occasion: str) -> List[str]:
        """生成造型技巧"""
        system_prompt = """你是一个资深的时尚造型师，提供实用的造型技巧。"""
        
        prompt = f"""
        风格偏好: {style_preference}
        场合: {occasion}
        
        请提供5-7个实用的造型技巧，包括:
        1. 颜色搭配技巧
        2. 比例调节方法
        3. 层次搭配要点
        4. 配饰使用建议
        5. 体型修饰技巧
        
        每个技巧要具体实用，适合普通消费者操作。
        """
        
        try:
            tips_result = await self._call_openai(prompt, system_prompt)
            # 将结果分割成列表
            tips = [tip.strip() for tip in tips_result.split('\n') if tip.strip()]
            return tips[:7]  # 最多返回7个技巧
        except Exception as e:
            logger.error(f"Error generating styling tips: {e}")
            return ["基础造型建议暂时不可用"]
    
    async def suggest_color_combinations(self, style_preference: str) -> Dict:
        """建议颜色组合"""
        style_colors = self.style_knowledge.get(style_preference, {}).get('colors', [])
        
        system_prompt = """你是一个色彩搭配专家，精通时尚色彩理论。"""
        
        prompt = f"""
        风格类型: {style_preference}
        基础色彩: {style_colors}
        
        请提供该风格的颜色搭配建议:
        1. 主色调选择
        2. 经典颜色组合
        3. 季节性颜色建议
        4. 适合肤色的颜色选择
        5. 避免的颜色组合
        
        返回JSON格式的颜色搭配指南。
        """
        
        try:
            color_result = await self._call_openai(prompt, system_prompt)
            try:
                color_suggestions = json.loads(color_result)
                return color_suggestions
            except json.JSONDecodeError:
                return {"suggestions": color_result}
        except Exception as e:
            logger.error(f"Error suggesting colors: {e}")
            return {"error": "颜色建议暂时不可用"}
    
    async def generate_checkout_tips(self, user_id: str) -> List[str]:
        """生成结账提示"""
        tips = [
            "确认商品尺码和颜色是否正确",
            "检查收货地址信息",
            "了解退换货政策",
            "选择合适的支付方式",
            "关注物流配送时间",
            "保存订单确认信息"
        ]
        return tips
    
    async def generate_personalized_recommendations(self, user_preference: str, 
                                                  shopping_history: str, user_id: str) -> List[Dict]:
        """生成个性化推荐"""
        system_prompt = """你是一个个性化推荐专家，基于用户偏好和历史提供精准推荐。"""
        
        prompt = f"""
        用户偏好: {user_preference}
        购物历史: {shopping_history}
        
        请生成5-8个个性化推荐，每个推荐包括:
        1. 推荐商品类型
        2. 推荐理由
        3. 适合场合
        4. 预期价格范围
        5. 搜索关键词
        
        返回JSON格式的推荐列表。
        """
        
        try:
            recommendations_result = await self._call_openai(prompt, system_prompt)
            try:
                recommendations = json.loads(recommendations_result)
                return recommendations if isinstance(recommendations, list) else []
            except json.JSONDecodeError:
                return [{"type": "general", "description": recommendations_result}]
        except Exception as e:
            logger.error(f"Error generating personalized recommendations: {e}")
            return []
    
    async def get_trending_recommendations(self) -> List[Dict]:
        """获取趋势推荐"""
        current_season = self._get_current_season()
        seasonal_data = self.seasonal_trends.get(current_season, {})
        
        return [
            {
                "type": "seasonal_colors",
                "title": f"{current_season}季流行色",
                "items": seasonal_data.get('colors', []),
                "description": f"本季最受欢迎的颜色趋势"
            },
            {
                "type": "trending_materials",
                "title": "热门材质",
                "items": seasonal_data.get('materials', []),
                "description": "当前最受关注的面料材质"
            },
            {
                "type": "style_trends",
                "title": "风格趋势",
                "items": seasonal_data.get('trends', []),
                "description": "本季主要的时尚风格趋势"
            }
        ]
    
    async def get_seasonal_recommendations(self) -> List[Dict]:
        """获取季节性推荐"""
        current_season = self._get_current_season()
        next_season = self._get_next_season()
        
        return [
            {
                "season": current_season,
                "type": "current_season",
                "recommendations": self.seasonal_trends.get(current_season, {}),
                "priority": "high"
            },
            {
                "season": next_season,
                "type": "prepare_for_next",
                "recommendations": self.seasonal_trends.get(next_season, {}),
                "priority": "medium"
            }
        ]
    
    async def enhance_collection_metadata(self, collections: List[Dict]) -> List[Dict]:
        """增强分类元数据"""
        enhanced_collections = []
        
        for collection in collections:
            enhanced = collection.copy()
            
            # 添加AI生成的标签和描述增强
            enhanced['ai_tags'] = await self._generate_collection_tags(collection)
            enhanced['style_matching'] = await self._match_collection_to_styles(collection)
            enhanced['seasonal_relevance'] = self._calculate_seasonal_relevance(collection)
            
            enhanced_collections.append(enhanced)
        
        return enhanced_collections
    
    async def _generate_collection_tags(self, collection: Dict) -> List[str]:
        """为分类生成AI标签"""
        title = collection.get('title', '')
        description = collection.get('description', '')
        
        # 基于标题和描述生成相关标签
        tags = []
        for style, data in self.style_knowledge.items():
            if any(keyword in title.lower() or keyword in description.lower() 
                   for keyword in data['keywords']):
                tags.extend(data['keywords'][:2])
        
        return list(set(tags))[:5]  # 返回最多5个不重复标签
    
    async def _match_collection_to_styles(self, collection: Dict) -> List[str]:
        """匹配分类到风格类型"""
        title = collection.get('title', '').lower()
        description = collection.get('description', '').lower()
        
        matched_styles = []
        for style, data in self.style_knowledge.items():
            if any(keyword in title or keyword in description 
                   for keyword in data['keywords']):
                matched_styles.append(style)
        
        return matched_styles
    
    def _calculate_seasonal_relevance(self, collection: Dict) -> Dict:
        """计算季节相关性"""
        current_season = self._get_current_season()
        title = collection.get('title', '').lower()
        
        # 季节关键词匹配
        season_keywords = {
            'spring': ['春', '春季', 'spring'],
            'summer': ['夏', '夏季', 'summer'],
            'autumn': ['秋', '秋季', 'autumn', 'fall'],
            'winter': ['冬', '冬季', 'winter']
        }
        
        relevance = {}
        for season, keywords in season_keywords.items():
            score = sum(1 for keyword in keywords if keyword in title)
            relevance[season] = score
        
        # 当前季节加权
        if current_season in relevance:
            relevance[current_season] += 2
        
        return relevance
    
    def _get_current_season(self) -> str:
        """获取当前季节"""
        month = datetime.now().month
        if month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        elif month in [9, 10, 11]:
            return 'autumn'
        else:
            return 'winter'
    
    def _get_next_season(self) -> str:
        """获取下一个季节"""
        current = self._get_current_season()
        seasons = ['spring', 'summer', 'autumn', 'winter']
        current_index = seasons.index(current)
        return seasons[(current_index + 1) % 4]
    
    async def get_seasonal_trends(self) -> Dict:
        """获取季节趋势"""
        current_season = self._get_current_season()
        return self.seasonal_trends.get(current_season, {})
    
    async def analyze_user_preferences(self, user_profiles: List[Dict]) -> Dict:
        """分析用户偏好数据"""
        if not user_profiles:
            return {"analysis": "暂无用户数据"}
        
        # 统计分析
        style_counts = {}
        color_counts = {}
        budget_counts = {}
        
        for profile in user_profiles:
            # 统计风格偏好
            style = profile.get('style_preference', {})
            if isinstance(style, dict):
                for s in style.values():
                    style_counts[s] = style_counts.get(s, 0) + 1
            
            # 统计颜色偏好
            colors = profile.get('color_preferences', [])
            for color in colors:
                color_counts[color] = color_counts.get(color, 0) + 1
            
            # 统计预算分布
            budget = profile.get('budget_range', '')
            budget_counts[budget] = budget_counts.get(budget, 0) + 1
        
        return {
            "total_users": len(user_profiles),
            "popular_styles": sorted(style_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "popular_colors": sorted(color_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "budget_distribution": budget_counts,
            "analysis_date": datetime.now().isoformat()
        }
    
    async def generate_trend_insights(self, trend_data: List[Dict]) -> Dict:
        """生成趋势洞察"""
        system_prompt = """你是一个数据分析师和时尚趋势专家，能够从购物数据中发现有价值的趋势洞察。"""
        
        prompt = f"""
        购物趋势数据:
        {json.dumps(trend_data, ensure_ascii=False, indent=2)}
        
        请分析这些数据并提供:
        1. 主要趋势发现
        2. 用户行为模式
        3. 热门品类分析
        4. 季节性趋势
        5. 商业建议
        
        返回JSON格式的洞察报告。
        """
        
        try:
            insights_result = await self._call_openai(prompt, system_prompt)
            try:
                insights = json.loads(insights_result)
                return insights
            except json.JSONDecodeError:
                return {"insights": insights_result}
        except Exception as e:
            logger.error(f"Error generating trend insights: {e}")
            return {"error": "趋势分析暂时不可用"}
    
    async def predict_future_trends(self, trend_data: List[Dict]) -> Dict:
        """预测未来趋势"""
        system_prompt = """你是一个时尚趋势预测专家，能够基于历史数据预测未来的购物和时尚趋势。"""
        
        prompt = f"""
        历史趋势数据:
        {json.dumps(trend_data, ensure_ascii=False, indent=2)}
        
        基于这些数据，请预测未来3-6个月的趋势:
        1. 可能上升的品类
        2. 预期的风格变化
        3. 色彩趋势预测
        4. 消费行为变化
        5. 建议关注的新兴趋势
        
        返回JSON格式的预测报告。
        """
        
        try:
            prediction_result = await self._call_openai(prompt, system_prompt)
            try:
                predictions = json.loads(prediction_result)
                return predictions
            except json.JSONDecodeError:
                return {"predictions": prediction_result}
        except Exception as e:
            logger.error(f"Error predicting trends: {e}")
            return {"error": "趋势预测暂时不可用"}
    
    async def calculate_cache_hit_rate(self) -> float:
        """计算缓存命中率（模拟）"""
        # 这里应该是实际的缓存统计逻辑
        return 0.85  # 85%命中率
    
    async def get_popular_recommendation_categories(self) -> List[Dict]:
        """获取热门推荐分类"""
        return [
            {"category": "搭配推荐", "count": 245, "percentage": 35.2},
            {"category": "同类商品", "count": 186, "percentage": 26.7},
            {"category": "季节推荐", "count": 134, "percentage": 19.2},
            {"category": "风格匹配", "count": 132, "percentage": 18.9}
        ]
    
    async def generate_restock_suggestions(self, low_stock_items: List[Dict]) -> List[Dict]:
        """生成补货建议"""
        suggestions = []
        
        for item in low_stock_items:
            suggestion = {
                "product_id": item["product_id"],
                "current_stock": item["stock"],
                "suggested_restock": max(item["threshold"] * 2, 10),
                "priority": "high" if item["stock"] == 0 else "medium",
                "reason": "库存不足" if item["stock"] > 0 else "已缺货"
            }
            suggestions.append(suggestion)
        
        return suggestions
    
    async def forecast_demand(self, stock_data: List[Dict]) -> Dict:
        """需求预测"""
        # 简化的需求预测逻辑
        total_products = len(stock_data)
        low_stock_count = sum(1 for item in stock_data if item["stock"] <= item["threshold"])
        
        return {
            "demand_level": "high" if low_stock_count / total_products > 0.5 else "moderate",
            "restocking_urgency": "immediate" if low_stock_count > 5 else "planned",
            "forecast_period": "next_7_days",
            "confidence": 0.78
        }