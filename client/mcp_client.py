import logging
from typing import Dict, Any, List, Optional
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientMetadata

class MCPClient:
    """增强型MCP客户端"""
    
    def __init__(self, servers: Dict[str, str], use_auth: bool = False):
        """
        初始化MCP客户端
        
        Args:
            servers: 服务器名称到URL的映射
            use_auth: 是否启用OAuth认证
        """
        self.servers = servers
        self.use_auth = use_auth
        self.sessions = {}
        self.transports = {}  # 存储传输对象
        self.logger = logging.getLogger("mcp.client")
    
    async def connect(self):
        """连接到所有配置的服务器"""
        for server_name, server_url in self.servers.items():
            try:
                # 设置认证（如果需要）
                auth = None
                if self.use_auth:
                    auth = self._create_oauth_provider(server_url)
                
                # 使用streamable HTTP连接
                self.logger.info(f"正在连接到服务器: {server_name} ({server_url})")
                
                # 使用正确的上下文管理器方式
                self.transports = {}
                transport = await streamablehttp_client(server_url, auth=auth).__aenter__()
                read, write, _ = transport
                self.transports[server_name] = transport
                
                # 创建并初始化会话
                session = ClientSession(read, write)
                await session.initialize()
                
                self.sessions[server_name] = session
                self.logger.info(f"已连接到服务器: {server_name}")
            
            except Exception as e:
                self.logger.error(f"连接到服务器 {server_name} 失败: {str(e)}")
    
    async def get_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取可用工具"""
        tools = []
        
        # 如果指定了服务器名称，只查询该服务器
        if server_name:
            if server_name in self.sessions:
                response = await self.sessions[server_name].list_tools()
                # 从 tools 字段提取工具列表
                for tool in response.tools:
                    # 将 Tool 对象转换为字典
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "server": server_name
                    })
            else:
                raise ValueError(f"未知的服务器: {server_name}")
        else:
            # 查询所有服务器
            for name, session in self.sessions.items():
                response = await session.list_tools()
                for tool in response.tools:
                    # 将 Tool 对象转换为字典
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "server": name
                    })
        
        return tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], server_name: Optional[str] = None) -> Any:
        """调用工具"""
        # 如果未指定服务器，尝试找到包含该工具的服务器
        if server_name is None:
            for name, session in self.sessions.items():
                tools = await session.list_tools()
                for tool in tools:
                    if tool.name == tool_name:
                        server_name = name
                        break
                if server_name:
                    break
            
            if server_name is None:
                raise ValueError(f"找不到工具: {tool_name}")
        
        # 调用工具
        if server_name in self.sessions:
            return await self.sessions[server_name].call_tool(tool_name, arguments)
        else:
            raise ValueError(f"未知的服务器: {server_name}")
    
    async def get_resources(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取可用资源"""
        resources = []
        
        if server_name:
            if server_name in self.sessions:
                resources = await self.sessions[server_name].list_resources()
            else:
                raise ValueError(f"未知的服务器: {server_name}")
        else:
            for name, session in self.sessions.items():
                server_resources = await session.list_resources()
                for resource in server_resources:
                    resources.append({**resource, "server": name})
        
        return resources
    
    async def read_resource(self, uri: str, server_name: Optional[str] = None) -> tuple[str, str]:
        """读取资源内容"""
        if server_name:
            if server_name in self.sessions:
                return await self.sessions[server_name].read_resource(uri)
            else:
                raise ValueError(f"未知的服务器: {server_name}")
        else:
            # 尝试在所有服务器上读取资源
            for session in self.sessions.values():
                try:
                    return await session.read_resource(uri)
                except Exception:
                    continue
            
            raise ValueError(f"找不到资源: {uri}")
    
    async def close(self):
        """关闭所有会话"""
        # 不需要显式关闭 session，因为它没有 close 方法
        # ClientSession 是在 with 语句中自动关闭的
        
        # 关闭所有传输
        if hasattr(self, 'transports'):
            for name, transport in self.transports.items():
                try:
                    # 尝试关闭传输
                    if hasattr(transport, '__aexit__'):
                        await transport.__aexit__(None, None, None)
                    self.logger.info(f"已关闭传输: {name}")
                except Exception as e:
                    self.logger.error(f"关闭传输 {name} 失败: {str(e)}")
    
    def _create_oauth_provider(self, server_url: str):
        """创建OAuth认证提供者"""
        # 这里可以实现TokenStorage和回调处理程序
        # 仅作为示例，实际实现需要根据应用程序需求
        return OAuthClientProvider(
            server_url=server_url,
            client_metadata=OAuthClientMetadata(
                client_name="My MCP Client",
                redirect_uris=["http://localhost:3000/callback"],
                grant_types=["authorization_code", "refresh_token"],
                response_types=["code"]
            ),
            storage=None,  # 需要实现TokenStorage
            redirect_handler=lambda url: print(f"请访问: {url}"),
            callback_handler=lambda: input("请输入授权码: ")
        )
