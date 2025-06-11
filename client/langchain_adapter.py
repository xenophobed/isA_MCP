from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI

from .mcp_client import MCPClient

class MCPTool(BaseTool):
    """MCP工具适配器，用于LangChain集成"""
    
    def __init__(self, client: MCPClient, tool_name: str, description: str, server_name: Optional[str] = None):
        """
        初始化MCP工具适配器
        
        Args:
            client: MCP客户端实例
            tool_name: 工具名称
            description: 工具描述
            server_name: 可选的服务器名称
        """
        self.client = client
        self.tool_name = tool_name
        self.server_name = server_name
        
        # 初始化BaseTool
        super().__init__(
            name=tool_name,
            description=description,
            return_direct=False
        )
    
    async def _arun(self, **kwargs) -> str:
        """异步运行工具"""
        try:
            result = await self.client.call_tool(
                self.tool_name,
                arguments=kwargs,
                server_name=self.server_name
            )
            return str(result)
        except Exception as e:
            return f"工具执行失败: {str(e)}"
    
    def _run(self, **kwargs) -> str:
        """同步运行工具"""
        import asyncio
        return asyncio.run(self._arun(**kwargs))

class LangChainAdapter:
    """LangChain适配器，将MCP工具转换为LangChain代理"""
    
    def __init__(self, client: MCPClient, model_name: str = "gpt-4o", api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化LangChain适配器
        
        Args:
            client: MCP客户端实例
            model_name: 模型名称
            api_key: API密钥
            base_url: 可选的API基础URL
        """
        self.client = client
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
    
    async def create_agent(self) -> AgentExecutor:
        """创建LangChain代理"""
        # 获取MCP工具
        mcp_tools = await self.client.get_tools()
        
        # 转换为LangChain工具
        langchain_tools = [
            MCPTool(
                client=self.client,
                tool_name=tool["name"],
                description=tool.get("description", ""),
                server_name=tool.get("server")
            )
            for tool in mcp_tools
        ]
        
        # 创建LLM
        llm_kwargs = {"model": self.model_name}
        if self.api_key:
            llm_kwargs["api_key"] = self.api_key
        if self.base_url:
            llm_kwargs["base_url"] = self.base_url
        
        llm = ChatOpenAI(**llm_kwargs)
        
        # 创建代理
        agent = create_react_agent(
            llm=llm,
            tools=langchain_tools
        )
        
        # 创建代理执行器
        return AgentExecutor(agent=agent, tools=langchain_tools)
