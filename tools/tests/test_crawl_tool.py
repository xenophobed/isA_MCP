import os 
os.environ["ENV"] = "local"

from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.basic.crawl_scrape_tool import crawl_webpage
import logging
import asyncio
logger = logging.getLogger(__name__)

async def setup_tools_manager():
    """Initialize tools manager with graph support"""
    try:
        # Clear any existing tools first
        tools_manager.clear_tools()
        
        # Initialize manager
        await tools_manager.initialize(test_mode=True)
        
        # Register the crawl_webpage tool
        crawl_tool = crawl_webpage
        
        # Add tools to manager
        await tools_manager.add_tools([
            crawl_tool
        ])
        
        logger.info("工具管理器初始化完成")
    except Exception as e:
        logger.error(f"工具管理器初始化失败: {e}")
        raise e

async def test_crawl_webpage():
    """测试crawl_webpage工具"""
    try:
        # 测试crawl_webpage工具
        url = "https://www.cursor.com/cn/changelog"
        result = await crawl_webpage.ainvoke({"url": url})
        logger.info(f"crawl_webpage工具测试结果: {result}")
    except Exception as e:
        logger.error(f"crawl_webpage工具测试失败: {e}")
        raise e

async def run_tests():
    """运行所有测试"""
    try:
        await setup_tools_manager()
        await test_crawl_webpage()
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(run_tests())
