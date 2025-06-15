import asyncio
import sys
import os
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("direct-client")

async def main():
    logger.info("启动 MCP 客户端测试")
    
    # 连接到 MCP 服务器
    logger.info("连接到 http://localhost:8000/mcp")
    try:
        async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
            # 创建会话
            logger.info("创建 MCP 会话")
            async with ClientSession(read, write) as session:
                # 初始化会话
                logger.info("初始化会话")
                await session.initialize()
                
                # 获取可用工具
                logger.info("获取可用工具")
                tools = await session.list_tools()
                logger.info(f"可用工具: {tools}")
                
                # 调用天气工具
                logger.info("调用 get_weather 工具")
                result = await session.call_tool("get_weather", {"location": "London"})
                logger.info(f"天气结果: {result}")
    
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 