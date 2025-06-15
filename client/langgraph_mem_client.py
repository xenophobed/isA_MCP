#!/usr/bin/env python
"""
修复后的MCP记忆系统客户端
修复AI工具调用后不响应的问题
"""
import asyncio
import os
import json
from dotenv import load_dotenv

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

# 加载环境变量
load_dotenv(".env.local")

# OpenAI API配置
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

# 初始化LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=api_key,
    base_url=api_base
)

class MemoryEnhancedChat:
    def __init__(self, session):
        self.session = session
        self.chat_history = []
    
    async def get_available_tools(self):
        """获取可用的记忆工具"""
        tools_response = await self.session.list_tools()
        tools = []
        for tool in tools_response.tools:
            tool_info = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
            tools.append(tool_info)
        return tools
    
    async def call_mcp_tool(self, tool_name, arguments):
        """调用MCP工具"""
        try:
            result = await self.session.call_tool(tool_name, arguments)
            if hasattr(result, 'content') and result.content:
                return result.content[0].text
            return str(result)
        except Exception as e:
            return f"工具调用失败: {str(e)}"
    
    async def process_user_input(self, user_input):
        """处理用户输入，包括记忆检索和存储"""
        
        # 1. 检索相关记忆
        print("正在检索相关记忆...")
        
        # 检索不同类别的记忆
        user_preferences = await self.call_mcp_tool(
            "recall_by_category", 
            {"category": "user_preferences", "limit": 3}
        )
        
        conversation_history = await self.call_mcp_tool(
            "recall_by_category", 
            {"category": "conversation_history", "limit": 3}
        )
        
        semantic_memories = await self.call_mcp_tool(
            "semantic_search",
            {"query": user_input, "limit": 3}
        )
        
        # 2. 获取可用工具信息
        available_tools = await self.get_available_tools()
        tools_description = "\n".join([
            f"- {tool['name']}: {tool['description']}" 
            for tool in available_tools
        ])
        
        # 3. 构建系统提示
        system_prompt = f"""你是一个具有记忆能力的AI助手。你可以使用以下工具来管理记忆：

{tools_description}

当前记忆信息：

用户偏好记忆：
{user_preferences}

对话历史记忆：
{conversation_history}

语义相关记忆：
{semantic_memories}

使用指南：
1. 如果用户提到个人信息、偏好、重要事实，使用 remember 或 remember_with_embedding 存储
2. 如果用户询问之前的对话或信息，使用 recall 或 semantic_search 检索
3. 对话结束时，使用 remember 存储这次对话的摘要
4. 重要信息的 importance 设置为 3-5，一般信息设置为 1-2

重要：调用工具后，你必须基于工具结果给出有意义的文本回复。不要只调用工具而不回复用户。"""

        # 4. 构建消息序列
        messages = [SystemMessage(content=system_prompt)]
        
        # 添加聊天历史（最近3轮对话）
        messages.extend(self.chat_history[-6:])
        
        # 添加当前用户输入
        messages.append(HumanMessage(content=user_input))
        
        # 5. 绑定工具到LLM
        llm_with_tools = llm.bind_tools([{
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
        } for tool in available_tools])
        
        # 6. 第一次调用LLM - 可能包含工具调用
        response = await llm_with_tools.ainvoke(messages)
        
        # 7. 处理工具调用
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"AI正在调用 {len(response.tool_calls)} 个工具...")
            
            # 将AI的工具调用响应添加到消息历史
            messages.append(response)
            
            # 执行每个工具调用
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_call_id = tool_call['id']
                
                print(f"调用工具: {tool_name}({tool_args})")
                
                tool_result = await self.call_mcp_tool(tool_name, tool_args)
                print(f"工具结果: {tool_result}")
                
                # 将工具结果添加到消息历史
                messages.append(ToolMessage(
                    content=tool_result,
                    tool_call_id=tool_call_id
                ))
            
            # 8. 第二次调用LLM - 基于工具结果生成最终回复
            final_response = await llm_with_tools.ainvoke(messages)
            final_content = final_response.content if final_response.content else "我已经处理了您的请求。"
        else:
            # 没有工具调用，直接使用初始响应
            final_content = response.content if response.content else "我理解了您的问题。"
        
        # 9. 自动存储对话历史
        conversation_summary = f"用户: {user_input}\nAI: {final_content[:200]}..."
        await self.call_mcp_tool(
            "remember",
            {
                "key": f"conversation_{len(self.chat_history)//2}",
                "value": conversation_summary,
                "category": "conversation_history",
                "importance": 2
            }
        )
        
        # 存储到聊天历史
        self.chat_history.extend([
            HumanMessage(content=user_input),
            AIMessage(content=final_content)
        ])
        
        return final_content

async def main():
    print("正在连接到MCP记忆服务器...")
    
    # 连接到MCP服务器
    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()
            
            # 创建记忆增强聊天实例
            chat = MemoryEnhancedChat(session)
            
            # 获取可用工具列表
            tools_response = await session.list_tools()
            tools = tools_response.tools
            print(f"可用工具: {[tool.name for tool in tools]}")
            
            # 交互式聊天循环
            print("\n记忆增强AI助手已启动。输入'exit'退出，输入'summary'查看记忆总结。")
            
            while True:
                user_input = input("\n用户: ")
                
                if user_input.lower() == 'exit':
                    break
                elif user_input.lower() == 'summary':
                    # 显示记忆总结
                    summary = await chat.call_mcp_tool("summarize_memories", {})
                    print(f"\n{summary}")
                    continue
                
                try:
                    # 处理用户输入
                    ai_response = await chat.process_user_input(user_input)
                    print(f"\nAI: {ai_response}")
                    
                except Exception as e:
                    print(f"错误: {e}")
                    import traceback
                    print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())