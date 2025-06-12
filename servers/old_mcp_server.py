from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging
import asyncio
import os
import inspect
import glob
from typing import List, Dict, Any, Optional

from mcp.server import Server
from mcp.server.fastmcp import FastMCP
import mcp.types as types

from ..core.config import get_settings
from ..tools.tools_manager import tools_manager
from ..capability.registry.tool_graph_manager import ToolGraphManager

# 配置日志
logger = logging.getLogger(__name__)

# 服务器生命周期管理
@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[dict]:
    """管理服务器启动和关闭生命周期"""
    # 初始化资源
    settings = get_settings() if get_settings else None
    logging.info("服务器启动，资源已初始化")
    

async def discover_tools(directories: List[str] = None, graph_manager: Optional[ToolGraphManager] = None):
    """
    自动发现并注册工具
    
    Args:
        directories: 要扫描的目录列表
        graph_manager: 图数据库管理器实例
    """
    if not directories:
        directories = ["tools"]
    
    for directory in directories:
        if not os.path.exists(directory):
            logger.warning(f"工具目录不存在: {directory}")
            continue
            
        logger.info(f"扫描工具目录: {directory}")
        
        # 查找所有Python文件
        py_files = glob.glob(os.path.join(directory, "**/*.py"), recursive=True)
        
        for py_file in py_files:
            try:
                # 转换文件路径为模块路径
                rel_path = os.path.relpath(py_file)
                module_path = rel_path.replace(os.path.sep, ".").replace(".py", "")
                
                # 动态导入模块
                module = __import__(module_path, fromlist=['*'])
                
                # 检查模块中的所有函数
                for name, obj in inspect.getmembers(module, inspect.isfunction):
                    # 检查是否有docstring
                    doc = inspect.getdoc(obj)
                    if not doc:
                        continue
                        
                    # 检查是否包含 @semantic 标记 (向量化需要)
                    if "@semantic" in doc:
                        logger.info(f"发现语义标记工具: {name} in {module_path}")
            except Exception as e:
                logger.error(f"处理模块时出错 {py_file}: {str(e)}")

# 创建高级 MCP 服务器
def create_advanced_server(
    name: str, 
    tool_dirs: List[str] = None,
    enable_discovery: bool = False,
    neo4j_uri: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None
):
    """
    创建高级 MCP 服务器，支持工具自动发现和图数据库集成
    
    Args:
        name: 服务器名称
        tool_dirs: 工具目录列表
        enable_discovery: 是否启用工具自动发现
        neo4j_uri: Neo4j 数据库 URI
        neo4j_user: Neo4j 用户名
        neo4j_password: Neo4j 密码
        
    Returns:
        FastMCP: 配置好的 MCP 服务器实例
    """
    # 使用官方的 FastMCP 创建服务器
    mcp_server = FastMCP(name)
    
    # 添加生命周期管理
    mcp_server.lifespan = server_lifespan
    
    # 如果启用工具发现，初始化工具管理器
    if enable_discovery:
        # 创建初始化函数
        async def initialize_tools():
            logger.info(f"初始化工具发现: {name}")
            
            # 初始化工具管理器
            test_mode = not all([neo4j_uri, neo4j_user, neo4j_password])
            await tools_manager.initialize(test_mode=test_mode)
            
            # 如果提供了图数据库连接信息，则替换工具管理器中的连接
            if not test_mode and tools_manager.graph_manager:
                tools_manager.graph_manager.graph_db.uri = neo4j_uri
                tools_manager.graph_manager.graph_db.user = neo4j_user
                tools_manager.graph_manager.graph_db.password = neo4j_password
            
            # 发现工具
            await discover_tools(tool_dirs, tools_manager.graph_manager)
            
            # 将发现的工具注册到图数据库
            if not test_mode and tools_manager.graph_manager:
                await tools_manager.update_tool_registry(force=True)
                
            logger.info(f"工具发现完成，已注册 {len(tools_manager.tools)} 个工具")
        
        # 运行初始化
        asyncio.create_task(initialize_tools())
    
    return mcp_server

# 创建集成了工具发现的 MCP 服务器
def create_discovery_server(
    name: str, 
    tool_dirs: List[str] = None,
    neo4j_uri: Optional[str] = None,
    neo4j_user: Optional[str] = None, 
    neo4j_password: Optional[str] = None
):
    """
    创建具有工具自动发现功能的 MCP 服务器
    
    Args:
        name: 服务器名称
        tool_dirs: 工具目录列表
        neo4j_uri: Neo4j 数据库 URI
        neo4j_user: Neo4j 用户名 
        neo4j_password: Neo4j 密码
        
    Returns:
        FastMCP: 配置好的 MCP 服务器实例
    """
    return create_advanced_server(
        name=name,
        tool_dirs=tool_dirs,
        enable_discovery=True,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password
    )
