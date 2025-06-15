"""
Apps registry module for automatic discovery and registration of MCP apps.
"""

import os
import importlib
import inspect
import sys
import logging
import importlib.util
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class AppInfo:
    """应用信息类，包含应用的元数据和工具"""
    def __init__(self, name: str, path: str, description: str = None):
        self.name = name
        self.path = path
        self.description = description or f"Application: {name}"
        self.tools = []
        self.modules = []
        self.metadata = {}
    
    def add_tool(self, tool: Any):
        """添加工具到应用"""
        self.tools.append(tool)
    
    def add_module(self, module_name: str, module: Any):
        """添加模块到应用"""
        self.modules.append((module_name, module))
    
    def set_metadata(self, key: str, value: Any):
        """设置应用元数据"""
        self.metadata[key] = value
    
    def __repr__(self):
        return f"AppInfo(name='{self.name}', tools={len(self.tools)}, path='{self.path}')"


def discover_apps(apps_dir: str, verbose: bool = False) -> Dict[str, AppInfo]:
    """
    发现指定目录下的应用
    
    Args:
        apps_dir: 应用目录路径
        verbose: 是否打印详细信息
        
    Returns:
        Dict[str, AppInfo]: 应用名称到应用信息的映射
    """
    apps = {}
    apps_dir_path = Path(apps_dir)
    
    if not apps_dir_path.exists() or not apps_dir_path.is_dir():
        if verbose:
            print(f"Apps directory not found: {apps_dir}")
        return apps
    
    # 确保父目录在Python路径中
    parent_dir = str(apps_dir_path.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # 遍历应用目录下的所有子目录
    for item in apps_dir_path.iterdir():
        if item.is_dir() and not item.name.startswith('_'):
            app_name = item.name
            app_path = str(item)
            
            if verbose:
                print(f"Discovering app: {app_name} at {app_path}")
            
            # 创建应用信息对象
            app_info = AppInfo(app_name, app_path)
            
            # 尝试导入应用的__init__.py以获取应用描述
            try:
                init_file = item / "__init__.py"
                if init_file.exists():
                    # 导入应用模块
                    module_name = f"apps.{app_name}"
                    app_module = importlib.import_module(module_name)
                    
                    # 获取应用描述
                    app_info.description = app_module.__doc__ or app_info.description
                    
                    # 探索应用模块导出的内容
                    if hasattr(app_module, "__all__"):
                        app_info.set_metadata("exports", app_module.__all__)
                    
                    app_info.add_module("__init__", app_module)
                    
                    if verbose:
                        print(f"  Imported app module: {module_name}")
                        if app_module.__doc__:
                            print(f"  Description: {app_module.__doc__.strip()}")
            except Exception as e:
                if verbose:
                    print(f"  Error importing app __init__.py: {e}")
            
            # 探索应用目录中的其他Python文件
            for py_file in item.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                    
                try:
                    module_name = f"apps.{app_name}.{py_file.stem}"
                    
                    if verbose:
                        print(f"  Importing module: {module_name}")
                        
                    # 导入模块
                    module = importlib.import_module(module_name)
                    app_info.add_module(py_file.stem, module)
                    
                    # 查找模块中的工具函数
                    for name, func in inspect.getmembers(module, inspect.isfunction):
                        if name.startswith('_'):
                            continue
                            
                        # 检查是否有工具标记
                        is_tool = False
                        if hasattr(func, "_tool") or (
                            func.__doc__ and any(marker in func.__doc__ for marker in ["@tool", "@semantic", "@function"])):
                            is_tool = True
                        
                        # 如果是工具或名称包含关键词，则认为是工具函数
                        if is_tool or any(keyword in name for keyword in ["tool", "query", "get", "list", "create", "update", "delete"]):
                            app_info.add_tool(func)
                            if verbose:
                                print(f"    Found tool: {name}")
                except Exception as e:
                    if verbose:
                        print(f"  Error importing module {py_file.name}: {e}")
            
            # 添加到应用字典
            apps[app_name] = app_info
    
    if verbose:
        print(f"Discovered {len(apps)} apps")
        
    return apps


def register_app_tools(mcp: Any, app_info: AppInfo, prefix: str = None, verbose: bool = False) -> int:
    """
    将应用中的工具注册到MCP服务器
    
    Args:
        mcp: MCP服务器实例
        app_info: 应用信息
        prefix: 工具名称前缀（通常是应用名称）
        verbose: 是否打印详细信息
        
    Returns:
        int: 注册的工具数量
    """
    tool_count = 0
    prefix = prefix or app_info.name
    
    for tool in app_info.tools:
        try:
            # 获取原始工具名称
            tool_name = tool.__name__
            
            # 创建带有应用前缀的工具名称
            prefixed_name = f"{prefix}_{tool_name}"
            
            if verbose:
                print(f"  Registering tool: {prefixed_name}")
            
            # 注册工具到MCP，使用前缀名称
            mcp.tool(name=prefixed_name)(tool)
            tool_count += 1
        except Exception as e:
            if verbose:
                print(f"  Error registering tool {tool.__name__}: {e}")
    
    return tool_count


def discover_and_register_apps(mcp: Any, apps_dir: str, verbose: bool = False) -> Dict[str, Tuple[AppInfo, int]]:
    """
    发现并注册应用目录下的所有应用
    
    Args:
        mcp: MCP服务器实例
        apps_dir: 应用目录路径
        verbose: 是否打印详细信息
        
    Returns:
        Dict[str, Tuple[AppInfo, int]]: 应用名称到(应用信息,注册工具数)的映射
    """
    result = {}
    
    # 发现应用
    apps = discover_apps(apps_dir, verbose)
    
    # 为每个应用注册工具
    for app_name, app_info in apps.items():
        if verbose:
            print(f"Registering tools for app: {app_name}")
            
        tool_count = register_app_tools(mcp, app_info, app_name, verbose)
        result[app_name] = (app_info, tool_count)
        
        if verbose:
            print(f"  Registered {tool_count} tools for {app_name}")
    
    total_tools = sum(count for _, count in result.values())
    if verbose:
        print(f"Total apps registered: {len(result)}")
        print(f"Total tools registered: {total_tools}")
    
    return result


# Command line interface
if __name__ == "__main__":
    import argparse
    from mcp.server.fastmcp import FastMCP
    
    parser = argparse.ArgumentParser(description="Discover and register MCP apps from a directory")
    parser.add_argument("--dir", "-d", default="./apps", help="Directory containing app modules")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--app-name", "-n", default="App Discovery Service", help="Name of the MCP application")
    parser.add_argument("--list", "-l", action="store_true", help="List discovered apps without starting server")
    args = parser.parse_args()
    
    # Create MCP server
    mcp = FastMCP(args.app_name)
    
    # Discover apps
    apps = discover_apps(args.dir, args.verbose)
    
    if args.list:
        print("\nDiscovered apps:")
        for app_name, app_info in apps.items():
            print(f"- {app_name}: {app_info.description}")
            print(f"  Tools: {len(app_info.tools)}")
            for tool in app_info.tools:
                print(f"    - {tool.__name__}")
            print()
        sys.exit(0)
    
    # Register apps
    result = discover_and_register_apps(mcp, args.dir, args.verbose)
    total_tools = sum(count for _, count in result.values())
    
    print(f"\nRegistered {len(result)} apps with {total_tools} tools")
    
    # Start the server
    print(f"Starting MCP server...")
    mcp.run()
