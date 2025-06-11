from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

from mcp.server import Server
from mcp.server.fastmcp import FastMCP
import mcp.types as types

from ..core.config import get_settings
from ..resources.database import Database

# 服务器生命周期管理
@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[dict]:
    """管理服务器启动和关闭生命周期"""
    # 初始化资源
    settings = get_settings()
    db = await Database.connect(settings.database_url)
    logging.info("服务器启动，资源已初始化")
    
    try:
        # 将资源放入上下文供处理程序使用
        yield {"db": db}
    finally:
        # 关闭时清理资源
        await db.disconnect()
        logging.info("服务器关闭，资源已清理")

# 创建高级 MCP 服务器
def create_advanced_server(name: str):
    # 使用官方的 FastMCP 创建服务器
    mcp_server = FastMCP(name)
    
    # 添加生命周期管理
    mcp_server.lifespan = server_lifespan
    
    return mcp_server
