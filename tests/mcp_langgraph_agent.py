import asyncio
import sys
import os
import logging
from typing import List, Dict, Any, TypedDict, Annotated, Sequence, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# MCP客户端导入
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-langgraph-agent")

# 定义状态类型
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_tools: Optional[List[Dict[str, Any]]]
    tool_calls: Optional[List[Dict[str, Any]]]

# LLM调用函数
async def agent_node(state: AgentState, llm) -> AgentState:
    """使用LLM处理用户输入并生成回应"""
    messages = state["messages"]
    tools = state.get("current_tools", [])
    
    logger.info(f"Calling LLM with {len(messages)} messages and {len(tools)} tools")
    
    # 调用LLM
    try:
        # 按照LangChain的正确调用格式
        response = await llm.ainvoke(
            input=messages,
            tools=tools if tools else None
        )
        logger.info(f"LLM响应类型: {response.__class__.__name__}")
        
        # 添加响应到消息列表
        state["messages"] = list(messages) + [response]
        
        # 检查是否有工具调用
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"发现{len(response.tool_calls)}个工具调用")
            state["tool_calls"] = response.tool_calls
        else:
            state["tool_calls"] = None
    except Exception as e:
        logger.error(f"调用LLM出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        error_message = AIMessage(content=f"处理时出错: {str(e)}")
        state["messages"] = list(messages) + [error_message]
        state["tool_calls"] = None
    
    return state

# MCP工具调用函数
async def tool_node(state: AgentState, mcp_url: str) -> AgentState:
    """使用MCP客户端调用工具"""
    messages = state["messages"]
    tool_calls = state.get("tool_calls", [])
    
    if not tool_calls:
        logger.info("没有工具调用，跳过")
        return state
    
    logger.info(f"执行{len(tool_calls)}个工具调用")
    
    # 处理每个工具调用
    result_messages = []
    
    try:
        # 连接到MCP服务器
        async with streamablehttp_client(mcp_url) as (read, write, _):
            # 创建会话
            async with ClientSession(read, write) as session:
                # 初始化会话
                await session.initialize()
                
                # 处理每个工具调用
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})
                    tool_id = tool_call.get("id", "")
                    
                    logger.info(f"调用工具: {tool_name}，参数: {tool_args}")
                    
                    try:
                        # 调用工具
                        result = await session.call_tool(tool_name, tool_args)
                        logger.info(f"工具结果: {result}")
                        
                        # 创建工具消息
                        result_messages.append(ToolMessage(
                            content=str(result),
                            name=tool_name,
                            tool_call_id=tool_id
                        ))
                    except Exception as e:
                        logger.error(f"调用工具出错: {str(e)}")
                        result_messages.append(ToolMessage(
                            content=f"错误: {str(e)}",
                            name=tool_name,
                            tool_call_id=tool_id
                        ))
    except Exception as e:
        logger.error(f"MCP会话错误: {str(e)}")
    
    # 更新消息
    if result_messages:
        state["messages"] = list(messages) + result_messages
    
    # 清除工具调用
    state["tool_calls"] = None
    
    return state

# 初始化工具列表节点
async def init_tools_node(state: AgentState, mcp_url: str) -> AgentState:
    """获取MCP服务器上的可用工具"""
    logger.info("初始化工具列表")
    
    try:
        # 连接到MCP服务器
        async with streamablehttp_client(mcp_url) as (read, write, _):
            # 创建会话
            async with ClientSession(read, write) as session:
                # 初始化会话
                await session.initialize()
                
                # 获取工具列表
                tools_result = await session.list_tools()
                tools = tools_result.tools if hasattr(tools_result, "tools") else []
                
                # 转换为OpenAI格式的工具描述
                openai_tools = []
                for tool in tools:
                    tool_schema = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema if hasattr(tool, "inputSchema") else {"type": "object", "properties": {}}
                        }
                    }
                    openai_tools.append(tool_schema)
                
                logger.info(f"获取到{len(openai_tools)}个工具")
                state["current_tools"] = openai_tools
    except Exception as e:
        logger.error(f"获取工具列表出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        state["current_tools"] = []
    
    return state

# 路由决策函数
async def should_continue(state: AgentState) -> str:
    """决定是否需要继续执行"""
    tool_calls = state.get("tool_calls", None)
    
    if tool_calls:
        logger.info("有工具调用，继续执行工具")
        return "tool"
    
    # 检查是否是最后一条消息是AI消息
    messages = state["messages"]
    if messages and isinstance(messages[-1], AIMessage):
        logger.info("AI已回应，结束对话")
        return "end"
    
    logger.info("继续LLM处理")
    return "agent"

# 构建Agent图
def build_mcp_agent(llm, mcp_url: str) -> StateGraph:
    """构建MCP集成的Agent图"""
    workflow = StateGraph(AgentState)
    
    # 创建带参数的函数
    def get_init_node():
        async def _init_node(state):
            return await init_tools_node(state, mcp_url)
        return _init_node
        
    def get_agent_node():
        async def _agent_node(state):
            return await agent_node(state, llm)
        return _agent_node
        
    def get_tool_node():
        async def _tool_node(state):
            return await tool_node(state, mcp_url)
        return _tool_node
    
    # 添加节点 - 使用闭包传递参数
    workflow.add_node("init", get_init_node())
    workflow.add_node("agent", get_agent_node())
    workflow.add_node("tool", get_tool_node())
    
    # 添加边
    workflow.add_edge(START, "init")
    workflow.add_edge("init", "agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "agent": "agent",
            "tool": "tool",
            "end": END
        }
    )
    
    workflow.add_edge("tool", "agent")
    
    return workflow.compile()

# 主函数
async def main():
    """主函数"""
    logger.info("启动MCP集成的LangGraph Agent")
    
    try:
        # MCP服务器URL
        mcp_url = "http://localhost:8000/mcp"
        
        # 创建LLM
        logger.info("创建LLM")
        llm = ChatOpenAI(
            model="gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY", "your_openai_api_key"),
            base_url="https://api.ai-yyds.com/v1",
            temperature=0
        )
        
        # 构建代理
        logger.info("构建MCP集成代理")
        agent = build_mcp_agent(llm, mcp_url)
        
        # 系统提示词
        system_prompt = """你是一个有用的AI助手，能够处理用户的天气查询。使用提供的工具回答问题，确保根据用户查询提取正确的参数。"""
        
        # 初始状态
        initial_state = {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content="伦敦的天气如何？也请告诉我哪些城市比较凉爽。")
            ],
            "current_tools": None,
            "tool_calls": None
        }
        
        # 运行代理
        logger.info("运行代理")
        result = await agent.ainvoke(initial_state)
        
        # 打印结果
        print("\n=== 代理执行过程 ===\n")
        for i, message in enumerate(result["messages"], 1):
            print(f"\n--- 消息 {i} ---")
            print(f"类型: {message.__class__.__name__}")
            print(f"内容: {message.content}")
            
            # 打印工具调用信息
            if hasattr(message, "tool_calls") and message.tool_calls:
                print("\n工具调用:")
                for tool_call in message.tool_calls:
                    print(f"  - 函数: {tool_call.get('name', '')}")
                    print(f"    参数: {tool_call.get('args', {})}")
            
            # 打印工具名称
            if hasattr(message, "name") and message.name:
                print(f"工具名称: {message.name}")
            
            # 打印ID
            if hasattr(message, "id") and message.id:
                print(f"ID: {message.id}")
            
            print("-" * 50)
    
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 