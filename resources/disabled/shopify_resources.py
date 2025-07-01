#!/usr/bin/env python
"""
Shopify Resources for MCP Server
Provides access to Shopify data and AI-enhanced shopping knowledge as resources
"""
import json
from datetime import datetime
from typing import Dict, List

from core.logging import get_logger
from core.monitoring import monitor_manager
from core.supabase_client import get_supabase_client
from tools.services.shopify_service.shopify_client import ShopifyClient

logger = get_logger(__name__)

def register_shopify_resources(mcp):
    """Register all Shopify resources with the MCP server"""
    
    # Initialize services
    shopify_client = ShopifyClient()
    supabase = get_supabase_client()
    
    @mcp.resource("shopify://catalog/collections")
    async def get_collections_catalog() -> str:
        """获取完整的商品分类目录"""
        monitor_manager.log_request("get_collections_catalog", "system", True, 0.2, "LOW")
        
        try:
            result = await shopify_client.get_collections(50)  # 获取更多分类
            
            if "data" in result and "collections" in result["data"]:
                collections = []
                for edge in result["data"]["collections"]["edges"]:
                    node = edge["node"]
                    collections.append({
                        "id": node["id"],
                        "title": node["title"],
                        "description": node.get("description", ""),
                        "handle": node["handle"],
                        "image_url": node.get("image", {}).get("url", ""),
                        "product_count": node.get("productsCount", 0)  # 如果API支持
                    })
                
                # AI增强分类信息
                enhanced_collections = await ai_assistant.enhance_collection_metadata(collections)
                
                response = {
                    "status": "success",
                    "data": {
                        "collections": enhanced_collections,
                        "count": len(enhanced_collections),
                        "metadata": {
                            "generated_at": datetime.now().isoformat(),
                            "ai_enhanced": True,
                            "total_categories": len(enhanced_collections)
                        }
                    },
                    "retrieved_at": datetime.now().isoformat()
                }
                
                logger.info(f"Collections catalog resource accessed: {len(collections)} collections")
                return json.dumps(response)
            else:
                return json.dumps({"status": "error", "message": "Failed to retrieve collections"})
                
        except Exception as e:
            logger.error(f"Error accessing collections catalog: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.resource("shopify://knowledge/fashion_guide")
    async def get_fashion_knowledge() -> str:
        """获取时尚搭配知识库"""
        try:
            fashion_knowledge = {
                "style_guides": {
                    "casual": {
                        "description": "休闲舒适的日常穿搭",
                        "key_pieces": ["T恤", "牛仔裤", "运动鞋", "卫衣"],
                        "color_palette": ["白色", "黑色", "牛仔蓝", "灰色"],
                        "occasions": ["日常出行", "朋友聚会", "购物"]
                    },
                    "business": {
                        "description": "专业商务装扮",
                        "key_pieces": ["西装", "衬衫", "正装裤", "皮鞋"],
                        "color_palette": ["黑色", "深蓝", "灰色", "白色"],
                        "occasions": ["工作会议", "商务场合", "正式活动"]
                    },
                    "date_night": {
                        "description": "约会浪漫造型",
                        "key_pieces": ["连衣裙", "高跟鞋", "小外套", "精致配饰"],
                        "color_palette": ["粉色", "红色", "黑色", "酒红"],
                        "occasions": ["约会", "晚餐", "看电影"]
                    }
                },
                "color_combinations": {
                    "classic": ["黑白配", "蓝白配", "灰色系"],
                    "spring": ["粉色+白色", "薄荷绿+米色", "浅蓝+白色"],
                    "autumn": ["棕色+橙色", "深绿+卡其", "酒红+灰色"]
                },
                "size_guides": {
                    "tops": {
                        "S": {"胸围": "84-88cm", "肩宽": "38-40cm"},
                        "M": {"胸围": "88-92cm", "肩宽": "40-42cm"},
                        "L": {"胸围": "92-96cm", "肩宽": "42-44cm"}
                    },
                    "bottoms": {
                        "S": {"腰围": "64-68cm", "臀围": "88-92cm"},
                        "M": {"腰围": "68-72cm", "臀围": "92-96cm"},
                        "L": {"腰围": "72-76cm", "臀围": "96-100cm"}
                    }
                },
                "seasonal_trends": await ai_assistant.get_seasonal_trends(),
                "care_instructions": {
                    "cotton": "机洗温水，低温烘干",
                    "wool": "手洗或干洗，平铺晾干",
                    "silk": "手洗冷水，自然晾干",
                    "polyester": "机洗，可烘干"
                }
            }
            
            response = {
                "status": "success",
                "data": fashion_knowledge,
                "metadata": {
                    "knowledge_type": "fashion_guide",
                    "last_updated": datetime.now().isoformat(),
                    "ai_curated": True
                },
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info("Fashion knowledge resource accessed")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error accessing fashion knowledge: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.resource("shopify://preferences/user_profiles")
    async def get_user_shopping_profiles() -> str:
        """获取用户购物偏好档案"""
        conn = sqlite3.connect("shopping_preferences.db")
        try:
            # 初始化表结构（如果不存在）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    style_preference TEXT,
                    size_info TEXT,
                    color_preferences TEXT,
                    budget_range TEXT,
                    shopping_history TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # 获取所有用户偏好
            cursor = conn.execute("""
                SELECT user_id, style_preference, size_info, color_preferences, 
                       budget_range, shopping_history, created_at, updated_at
                FROM user_preferences 
                ORDER BY updated_at DESC
            """)
            preferences = cursor.fetchall()
            
            user_profiles = []
            for user_id, style, size, colors, budget, history, created, updated in preferences:
                try:
                    profile = {
                        "user_id": user_id,
                        "style_preference": json.loads(style) if style else {},
                        "size_info": json.loads(size) if size else {},
                        "color_preferences": json.loads(colors) if colors else [],
                        "budget_range": budget,
                        "shopping_history": json.loads(history) if history else [],
                        "created_at": created,
                        "updated_at": updated
                    }
                    user_profiles.append(profile)
                except json.JSONDecodeError:
                    # 处理无效JSON数据
                    continue
            
            response = {
                "status": "success",
                "data": {
                    "user_profiles": user_profiles,
                    "count": len(user_profiles),
                    "analytics": await ai_assistant.analyze_user_preferences(user_profiles)
                },
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"User shopping profiles resource accessed: {len(user_profiles)} profiles")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error accessing user profiles: {e}")
            return json.dumps({"status": "error", "message": str(e)})
        finally:
            conn.close()

    @mcp.resource("shopify://analytics/shopping_trends")
    async def get_shopping_trends() -> str:
        """获取购物趋势分析"""
        conn = sqlite3.connect("shopping_analytics.db")
        try:
            # 初始化分析表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shopping_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    event_type TEXT,
                    product_id TEXT,
                    product_category TEXT,
                    timestamp TEXT,
                    metadata TEXT
                )
            """)
            
            # 获取最近的购物事件
            cursor = conn.execute("""
                SELECT event_type, product_category, COUNT(*) as count
                FROM shopping_events 
                WHERE timestamp > datetime('now', '-30 days')
                GROUP BY event_type, product_category
                ORDER BY count DESC
                LIMIT 20
            """)
            events = cursor.fetchall()
            
            trend_data = []
            for event_type, category, count in events:
                trend_data.append({
                    "event_type": event_type,
                    "category": category,
                    "frequency": count
                })
            
            # AI生成趋势洞察
            trend_insights = await ai_assistant.generate_trend_insights(trend_data)
            
            response = {
                "status": "success",
                "data": {
                    "trends": trend_data,
                    "insights": trend_insights,
                    "timeframe": "last_30_days",
                    "ai_predictions": await ai_assistant.predict_future_trends(trend_data)
                },
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Shopping trends resource accessed: {len(trend_data)} trends")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error accessing shopping trends: {e}")
            return json.dumps({"status": "error", "message": str(e)})
        finally:
            conn.close()

    @mcp.resource("shopify://cache/product_recommendations")
    async def get_cached_recommendations() -> str:
        """获取缓存的商品推荐"""
        conn = sqlite3.connect("recommendation_cache.db")
        try:
            # 初始化推荐缓存表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_cache (
                    cache_key TEXT PRIMARY KEY,
                    user_id TEXT,
                    recommendations TEXT,
                    generated_at TEXT,
                    expires_at TEXT
                )
            """)
            
            # 获取有效的推荐缓存
            cursor = conn.execute("""
                SELECT cache_key, user_id, recommendations, generated_at
                FROM recommendation_cache 
                WHERE expires_at > datetime('now')
                ORDER BY generated_at DESC
                LIMIT 50
            """)
            cache_entries = cursor.fetchall()
            
            recommendations_cache = []
            for cache_key, user_id, recommendations, generated_at in cache_entries:
                try:
                    rec_data = json.loads(recommendations)
                    recommendations_cache.append({
                        "cache_key": cache_key,
                        "user_id": user_id,
                        "recommendations": rec_data,
                        "generated_at": generated_at
                    })
                except json.JSONDecodeError:
                    continue
            
            response = {
                "status": "success",
                "data": {
                    "cached_recommendations": recommendations_cache,
                    "count": len(recommendations_cache),
                    "cache_stats": {
                        "total_entries": len(recommendations_cache),
                        "cache_hit_rate": await ai_assistant.calculate_cache_hit_rate(),
                        "popular_categories": await ai_assistant.get_popular_recommendation_categories()
                    }
                },
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Recommendation cache resource accessed: {len(recommendations_cache)} entries")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error accessing recommendation cache: {e}")
            return json.dumps({"status": "error", "message": str(e)})
        finally:
            conn.close()

    @mcp.resource("shopify://inventory/stock_alerts")
    async def get_stock_alerts() -> str:
        """获取库存预警信息"""
        try:
            # 模拟库存数据 - 在实际应用中应该从Shopify获取
            stock_data = [
                {"product_id": "gid://shopify/Product/1001", "title": "夏季T恤", "stock": 5, "threshold": 10},
                {"product_id": "gid://shopify/Product/1002", "title": "休闲短裤", "stock": 2, "threshold": 5},
                {"product_id": "gid://shopify/Product/1003", "title": "连衣裙", "stock": 0, "threshold": 3}
            ]
            
            low_stock_alerts = []
            out_of_stock_alerts = []
            
            for item in stock_data:
                if item["stock"] == 0:
                    out_of_stock_alerts.append(item)
                elif item["stock"] <= item["threshold"]:
                    low_stock_alerts.append(item)
            
            # AI生成补货建议
            restock_suggestions = await ai_assistant.generate_restock_suggestions(
                low_stock_alerts + out_of_stock_alerts
            )
            
            response = {
                "status": "success",
                "data": {
                    "low_stock_alerts": low_stock_alerts,
                    "out_of_stock_alerts": out_of_stock_alerts,
                    "total_alerts": len(low_stock_alerts) + len(out_of_stock_alerts),
                    "restock_suggestions": restock_suggestions,
                    "ai_demand_forecast": await ai_assistant.forecast_demand(stock_data)
                },
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Stock alerts resource accessed: {len(low_stock_alerts + out_of_stock_alerts)} alerts")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error accessing stock alerts: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    logger.info("Shopify resources registered successfully")