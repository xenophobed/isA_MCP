#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import sys
from typing import Any, Dict


# 添加父级目录到路径以便导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))

os.environ["ENV"] = "local"

from app.services.ai.tools.tools_manager import tools_manager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("ToolLoaderTest")

async def test_tool_registration():
    """测试工具注册和数据库持久化"""
    logger.info("\n" + "="*50)
    logger.info("🚀 启动工具注册测试")
    logger.info("="*50)
    
    # 初始化 - 启用数据库持久化但使用测试模式跳过Neo4j
    await tools_manager.initialize(test_mode=True, persist_to_db=True)
    
    # 记录已注册工具
    registered_tools = len(tools_manager.tools)
    logger.info(f"已注册工具数量: {registered_tools}")
    logger.info(f"已注册工具列表: {[t.name for t in tools_manager.tools]}")
    
    # 创建和添加一个测试工具
    from langchain_core.tools import BaseTool
    
    class TestCalculatorTool(BaseTool):
        name: str = "test_calculator"
        description: str = "测试计算器工具"
        
        def _run(self, expression: str) -> str:
            try:
                return f"计算结果: {eval(expression)}"
            except Exception as e:
                return f"计算错误: {str(e)}"
    
    # 手动添加工具
    new_tool = TestCalculatorTool()
    await tools_manager.add_tools([new_tool])
    
    # 验证新工具已添加
    logger.info(f"添加新工具后的工具数量: {len(tools_manager.tools)}")
    logger.info(f"添加后的工具列表: {[t.name for t in tools_manager.tools]}")
    
    # 导入工具到数据库
    logger.info("\n尝试将工具导入到数据库...")
    await tools_manager.import_tools_to_db()
    
    # 验证从数据库加载
    logger.info("\n从数据库加载工具...")
    await tools_manager._load_tools_from_db()
    
    # 测试获取工具
    weather_tool = tools_manager.get_tool("get_weather")
    if weather_tool:
        logger.info(f"\n获取到工具: {weather_tool.name}")
        logger.info(f"工具描述: {weather_tool.description}")
        try:
            result = weather_tool.invoke("beijing")
            logger.info(f"调用工具结果: {result}")
        except Exception as e:
            logger.error(f"调用工具出错: {e}")
    
    logger.info("\n" + "="*50)
    logger.info("🏁 工具注册测试完成")
    logger.info("="*50)

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(test_tool_registration()) 