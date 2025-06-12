#!/usr/bin/env python
import argparse
import asyncio
import sys
import os
import yaml
import logging
from typing import Dict, Any, List

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 修改导入方式，使用绝对导入
from servers.old_mcp_server import create_advanced_server, create_discovery_server

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp-cli")

def load_config(config_path: str) -> Dict[str, Any]:
    """从文件加载配置"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        return {}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP 服务启动工具")
    
    # 基本参数
    parser.add_argument("-c", "--config", help="配置文件路径", default="config.yaml")
    parser.add_argument("-n", "--name", help="服务名称", default=None)
    parser.add_argument("-p", "--port", help="服务端口", type=int, default=None)
    parser.add_argument("--host", help="服务主机", default=None)
    parser.add_argument("-t", "--transport", help="传输协议", choices=["http", "streamable-http", "ws"], default=None)
    
    # 工具发现参数
    parser.add_argument("-d", "--discovery", help="启用工具自动发现", action="store_true")
    parser.add_argument("--tool-dirs", help="工具目录，用逗号分隔", default=None)
    
    # 数据库参数
    parser.add_argument("--neo4j-uri", help="Neo4j 数据库 URI", default=None)
    parser.add_argument("--neo4j-user", help="Neo4j 用户名", default=None)
    parser.add_argument("--neo4j-password", help="Neo4j 密码", default=None)
    
    args = parser.parse_args()
    
    # 加载配置文件
    config = {}
    if os.path.exists(args.config):
        config = load_config(args.config)
    
    # 合并配置，命令行优先
    server_config = config.get("server", {})
    name = args.name or server_config.get("name", "MCP服务")
    port = args.port or server_config.get("port", 8000)
    host = args.host or server_config.get("host", "0.0.0.0")
    transport = args.transport or server_config.get("transport", "streamable-http")
    
    # 工具发现配置
    tools_config = config.get("tools", {})
    discovery_config = config.get("discovery", {})
    enable_discovery = args.discovery or discovery_config.get("enabled", False) or tools_config.get("auto_discovery", False)
    
    # 解析工具目录
    tool_dirs = []
    if args.tool_dirs:
        tool_dirs = args.tool_dirs.split(",")
    elif "directories" in tools_config:
        tool_dirs = tools_config["directories"]
    
    if not tool_dirs:
        tool_dirs = ["tools"]
    
    # 数据库配置
    neo4j_config = config.get("neo4j", {})
    neo4j_uri = args.neo4j_uri or neo4j_config.get("uri")
    neo4j_user = args.neo4j_user or neo4j_config.get("user")
    neo4j_password = args.neo4j_password or neo4j_config.get("password")
    
    # 创建服务器
    logger.info(f"启动 MCP 服务: {name}")
    logger.info(f"服务地址: {host}:{port}")
    logger.info(f"传输协议: {transport}")
    
    if enable_discovery:
        logger.info(f"工具自动发现已启用，扫描目录: {', '.join(tool_dirs)}")
        server = create_discovery_server(
            name=name,
            tool_dirs=tool_dirs,
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password
        )
    else:
        logger.info("工具自动发现已禁用")
        server = create_advanced_server(
            name=name,
            enable_discovery=False
        )
    
    # 运行服务器
    server.run(transport=transport, host=host, port=port)

if __name__ == "__main__":
    main() 