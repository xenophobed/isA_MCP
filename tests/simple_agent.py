import asyncio
import sys
import os
import logging
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple-agent")

# 不再需要自定义 MCPTool 类，langchain_mcp_adapters 会自动处理工具转换

async def main():
    logger.info("启动 MCP 简单代理测试")
    
    try:
        # 使用 MultiServerMCPClient 连接到 MCP 服务器
        logger.info("初始化 MCP 客户端")
        client = MultiServerMCPClient(
            {
                "weather": {
                    "url": "http://localhost:8000/mcp",
                    "transport": "streamable_http",
                }
            }
        )
        
        # 获取可用工具
        logger.info("获取工具")
        langchain_tools = await client.get_tools()
        
        # 创建 LLM
        logger.info("创建 LLM")
        llm = ChatOpenAI(
            model="gpt-4o",
            api_key="your_openai_api_key",
            base_url="https://api.ai-yyds.com/v1",
            temperature=0
        )
        
        # 创建代理 - 使用与 notebook 相同的 create_react_agent
        logger.info("创建代理")
        agent = create_react_agent(
            tools=langchain_tools,
            model=llm
        )
        
        # 由于使用 create_react_agent，不再需要单独的 AgentExecutor
        
        # 运行代理 - 使用与 notebook 相同的输入格式
        logger.info("运行代理")
        result = await agent.ainvoke({
            "messages": [
                {"role": "system", "content": "你是一个有用的AI助手，能够处理用户的天气查询。使用提供的工具回答问题，确保根据用户查询提取正确的参数。"},
                {"role": "user", "content": "伦敦的天气如何？也请告诉我哪些城市比较凉爽。"}
            ]
        })
        
        print("\n=== 代理响应流程 ===\n")
        for i, message in enumerate(result['messages'], 1):
            print(f"\n--- Message {i} ---")
            print(f"Type: {message.__class__.__name__}")
            print(f"Content: {message.content}")
            
            if hasattr(message, 'tool_calls') and message.tool_calls:
                print("\nTool Calls:")
                for tool_call in message.tool_calls:
                    print(f"  - Function: {tool_call['name']}")
                    print(f"    Arguments: {tool_call['args']}")
            
            if hasattr(message, 'name'):
                print(f"Tool Name: {message.name}")
            
            print(f"ID: {message.id}")
            print("-" * 50)
        
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())