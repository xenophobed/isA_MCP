#!/usr/bin/env python
"""
Web Search Service - 基础网页搜索服务
提供简单的搜索功能，返回链接和基本信息
"""

from typing import Dict, Any, List, Optional

from core.logging import get_logger
from core.config import get_settings
from ..engines.search_engine import SearchEngine, SearchProvider, BraveSearchStrategy

logger = get_logger(__name__)


class WebSearchService:
    """基础网页搜索服务"""

    def __init__(self):
        self.search_engine = SearchEngine()
        self._initialized = False
        logger.info("✅ WebSearchService initialized")

    async def initialize(self):
        """初始化搜索引擎"""
        if self._initialized:
            return

        # Get settings from centralized config
        settings = get_settings()

        # 注册Brave搜索
        brave_api_key = settings.brave_api_key
        if brave_api_key:
            brave_strategy = BraveSearchStrategy(brave_api_key)
            self.search_engine.register_strategy(SearchProvider.BRAVE, brave_strategy)
            logger.info("✅ Brave search registered")
        else:
            logger.warning("⚠️ No Brave API key found in config")

        self._initialized = True
    
    async def search(self, query: str, count: int = 10) -> Dict[str, Any]:
        """
        搜索并返回结果
        
        Args:
            query: 搜索查询
            count: 结果数量
            
        Returns:
            搜索结果字典
        """
        try:
            await self.initialize()
            
            logger.info(f"🔍 Searching: {query}")
            
            # 执行搜索
            results = await self.search_engine.search(query, count=count)
            
            # 返回简单格式
            return {
                "success": True,
                "query": query,
                "total": len(results),
                "results": [
                    {
                        "title": r.title,
                        "url": r.url,
                        "snippet": r.snippet,
                        "score": r.score
                    }
                    for r in results
                ],
                "urls": [r.url for r in results]
            }
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": [],
                "urls": []
            }
    
    async def get_urls(self, query: str, count: int = 5) -> List[str]:
        """获取搜索结果的URL列表（用于爬虫）"""
        result = await self.search(query, count)
        return result.get("urls", [])
    
    async def close(self):
        """清理资源"""
        await self.search_engine.close()
        logger.info("✅ WebSearchService closed")


# 测试函数
async def test_search():
    """简单测试"""
    import asyncio
    
    service = WebSearchService()
    
    try:
        result = await service.search("python tutorial", count=3)
        print(f"Success: {result['success']}")
        print(f"Found: {result['total']} results")
        
        for i, res in enumerate(result['results']):
            print(f"{i+1}. {res['title']}")
            print(f"   {res['url']}")
    
    finally:
        await service.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_search())