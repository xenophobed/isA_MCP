from typing import List, Dict, Any, Callable, Optional, Union
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
import logging
import asyncio
import os
import uuid
import inspect
import importlib.util
import sys
from pathlib import Path

# 有条件导入，避免缺少依赖时出错
try:
    from app.services.agent.capabilities.contextual.capability.registry.tool_graph_manager import ToolGraphManager
    from app.config.config_manager import config_manager
    from app.repositories.tool.tool_repo import ToolRepository
    from app.models.tool.tool_model import Tool
    EXTERNAL_DEPS = True
except ImportError:
    # 尝试导入本地依赖
    try:
        from ..capability.registry.tool_graph_manager import ToolGraphManager
        EXTERNAL_DEPS = False
    except ImportError:
        ToolGraphManager = None
        EXTERNAL_DEPS = False

logger = logging.getLogger(__name__)

class ToolsManager:
    """Manages tool registration, error handling, and node creation"""
    
    def __init__(self):
        self.tools: List[BaseTool] = []
        self.error_handlers: Dict[str, Callable] = {}
        self.graph_manager = None
        self._initialization_lock = asyncio.Lock()
        self._initialized = False
        self._sync_interval = 300  # 5 minutes
        self._sync_task = None
        self._test_mode = False
        self._tool_repo = None
        self._persist_to_db = False
        self._mcp_tools = {}  # 存储原生MCP工具
        
    async def initialize(self, test_mode: bool = False, persist_to_db: bool = False):
        """Initialize the tools manager with graph support
        
        Args:
            test_mode: 是否以测试模式运行
            persist_to_db: 是否持久化工具到数据库
        """
        self._test_mode = test_mode
        self._persist_to_db = persist_to_db
        
        async with self._initialization_lock:
            if not self._initialized:
                try:
                    if self._persist_to_db:
                        self._tool_repo = ToolRepository()
                        await self._load_tools_from_db()
                
                    if not self._test_mode:
                        # Regular initialization with Neo4j
                        conn_params = {
                            'uri': os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
                            'user': os.getenv('NEO4J_USER', 'neo4j'),
                            'password': os.getenv('NEO4J_PASSWORD', 'admin@123')
                        }
                        
                        logger.info(f"Initializing Neo4j connection with URI: {conn_params['uri']}")
                        
                        # Create and initialize graph manager
                        self.graph_manager = await ToolGraphManager.create(
                            uri=conn_params['uri'],
                            user=conn_params['user'],
                            password=conn_params['password']
                        )
                        
                        # Initial sync
                        await self.graph_manager.sync_tools(self.tools)
                        
                        # Start background sync
                        self._start_background_sync()
                    else:
                        logger.info("Initializing tools manager in test mode - skipping Neo4j connection")
                        
                        if not test_mode:
                            # 这里可以添加代码导入所有工具模块，但不在这里实现，避免破坏现有功能
                            pass
                    
                    self._initialized = True
                    
                except Exception as e:
                    if not self._test_mode:
                        logger.error(f"Failed to initialize tools manager: {str(e)}")
                        raise
                    else:
                        logger.warning(f"Neo4j initialization skipped in test mode: {str(e)}")
    
    async def _load_tools_from_db(self):
        """从数据库加载工具(不影响现有内存中工具)"""
        if not self._tool_repo:
            return
            
        try:
            # 获取所有活跃状态的工具
            db_tools = await self._tool_repo.find_by_status("active")
            if not db_tools:
                logger.info("没有从数据库加载到工具")
                return
                
            logger.info(f"从数据库加载了 {len(db_tools)} 个工具")
            # 这里只记录工具信息，不实际加载，避免影响现有功能
        except Exception as e:
            logger.error(f"从数据库加载工具时出错: {e}")
    
    def _start_background_sync(self):
        """Start background sync task"""
        async def sync_loop():
            while True:
                try:
                    await asyncio.sleep(self._sync_interval)
                    await self.update_tool_registry()
                except Exception as e:
                    logger.error(f"Background sync failed: {str(e)}")

        self._sync_task = asyncio.create_task(sync_loop())
    
    async def cleanup(self):
        """Cleanup resources"""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        if self.graph_manager:
            await self.graph_manager.graph_db.close()
    
    async def update_tool_registry(self, force: bool = False):
        """Force update all tools in registry"""
        if not self._test_mode and self.graph_manager:
            await self.graph_manager.sync_tools(self.tools)
    
    def register_tool(self, error_handler: Optional[Callable] = None):
        """Decorator to register a tool with optional error handler"""
        def decorator(func: Callable) -> Callable:
            # Register the default tool using langchain's decorator
            tool_func = tool(func)
            
            # Add to our tools list
            self.tools.append(tool_func)
            
            # Register error handler if provided
            if error_handler:
                self.error_handlers[func.__name__] = error_handler
                
            # Register tool in graph if not in test mode and manager exists
            if not self._test_mode and self._initialized and self.graph_manager:
                asyncio.create_task(self.graph_manager.register_tool(tool_func))
            
            # 如果启用数据库持久化，存储到数据库(异步执行，不阻塞)
            if self._persist_to_db and self._tool_repo:
                # 使用异步任务存储，不影响现有流程
                asyncio.create_task(self._persist_tool_to_db(tool_func))
            
            return tool_func
        return decorator
    
    def register_mcp_tool(self, name: str, func: Callable, description: str = None):
        """注册原生MCP工具到工具管理器
        
        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述（如果未提供，将从函数文档获取）
        """
        if not description and func.__doc__:
            description = func.__doc__.strip()
        elif not description:
            description = f"{name} tool"
            
        # 存储原生MCP工具
        self._mcp_tools[name] = {
            "func": func,
            "description": description
        }
        
        # 创建Langchain工具包装
        @tool(name=name)
        async def wrapped_tool(*args, **kwargs):
            """自动包装的MCP工具"""
            result = await func(*args, **kwargs)
            return result
            
        # 设置描述
        wrapped_tool.description = description
        
        # 添加到工具列表
        self.tools.append(wrapped_tool)
        
        # 注册到图数据库
        if not self._test_mode and self._initialized and self.graph_manager:
            asyncio.create_task(self.graph_manager.register_tool(wrapped_tool))
            
        return wrapped_tool
    
    async def discover_tools_from_file(self, file_path: str) -> List[str]:
        """从文件中发现并注册工具
        
        Args:
            file_path: Python文件路径
            
        Returns:
            List[str]: 已注册工具名称列表
        """
        discovered_tools = []
        
        try:
            # 获取绝对路径
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                logger.warning(f"文件不存在: {abs_path}")
                return discovered_tools
                
            # 构建模块名
            module_name = Path(file_path).stem
            
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(module_name, abs_path)
            if not spec or not spec.loader:
                logger.warning(f"无法加载模块规范: {abs_path}")
                return discovered_tools
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找所有函数
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                # 检查是否有docstring
                doc = inspect.getdoc(obj)
                if not doc:
                    continue
                    
                # 检查是否有语义标记
                if "@semantic" in doc:
                    logger.info(f"发现语义标记工具: {name} in {file_path}")
                    
                    # 注册为Langchain工具
                    tool_func = tool(obj)
                    self.tools.append(tool_func)
                    discovered_tools.append(name)
                    
                    # 注册到图数据库
                    if not self._test_mode and self.graph_manager:
                        await self.graph_manager.register_tool(tool_func)
        
        except Exception as e:
            logger.error(f"从文件加载工具时出错 {file_path}: {str(e)}")
            
        return discovered_tools
    
    async def discover_tools_from_directory(self, directory: str) -> Dict[str, List[str]]:
        """从目录中发现并注册工具
        
        Args:
            directory: 目录路径
            
        Returns:
            Dict[str, List[str]]: 按文件分组的已注册工具名称
        """
        result = {}
        
        if not os.path.exists(directory):
            logger.warning(f"目录不存在: {directory}")
            return result
            
        # 获取所有Python文件
        py_files = [
            os.path.join(root, file)
            for root, _, files in os.walk(directory)
            for file in files if file.endswith('.py')
        ]
        
        for py_file in py_files:
            try:
                tools = await self.discover_tools_from_file(py_file)
                if tools:
                    result[py_file] = tools
            except Exception as e:
                logger.error(f"处理文件时出错 {py_file}: {str(e)}")
                
        return result
    
    def default_error_handler(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Default error handler for tools"""
        error = state.get("error")
        tool_calls = state["messages"][-1].tool_calls
        return {
            "messages": [
                ToolMessage(
                    content=f"Error: {repr(error)}\nPlease fix your mistakes.",
                    tool_call_id=tc["id"],
                )
                for tc in tool_calls
            ]
        }
    
    def create_tool_node(self, tools: Optional[List[str]] = None) -> ToolNode:
        """Create a tool node with error handling"""
        if tools:
            # Convert tool names to actual tool objects
            tools_to_use = [
                tool for tool in self.tools 
                if tool.name in tools
            ]
        else:
            tools_to_use = self.tools
            
        return ToolNode(tools_to_use).with_fallbacks(
            [RunnableLambda(self.default_error_handler)],
            exception_key="error"
        )
    
    def get_tools(self, tool_names: Optional[List[str]] = None) -> List[BaseTool]:
        """Get tools by names or all tools if no names provided
        
        Args:
            tool_names: Optional list of tool names to filter by
            
        Returns:
            List of tools matching the provided names or all tools
        """
        if not tool_names:
            return self.tools
            
        return [
            tool for tool in self.tools 
            if tool.name in tool_names or getattr(tool, "__name__", "") in tool_names
        ]
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a specific tool by name"""
        for tool in self.tools:
            if tool.name == name or getattr(tool, "__name__", "") == name:
                return tool
        return None
    
    async def add_tools(self, tools: List[BaseTool]):
        """Add external tools and register them in graph"""
        # 确保工具格式正确
        for tool in tools:
            if not hasattr(tool, 'name') or not hasattr(tool, 'description'):
                logger.warning(f"Tool {tool} missing required attributes")
                continue
            
            # 添加标准化的参数schema
            if not hasattr(tool, 'args_schema'):
                tool.args_schema = {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The input query for the tool"
                        }
                    },
                    "required": ["query"]
                }
            
        self.tools.extend(tools)
        
        # Only register in graph if not in test mode and graph manager exists
        if not self._test_mode and self.graph_manager is not None:
            # Register each tool in graph
            for tool in tools:
                await self.graph_manager.register_tool(tool)
                
        # 如果启用数据库持久化，存储到数据库
        if self._persist_to_db and self._tool_repo:
            for tool in tools:
                await self._persist_tool_to_db(tool)
    
    def clear_tools(self):
        """Clear all registered tools"""
        self.tools = []
        self._mcp_tools = {}
    
    async def verify_tools_integrity(self) -> List[Dict[str, Any]]:
        """Verify integrity of all registered tools"""
        if not self._test_mode and self.graph_manager:
            return await self.graph_manager.verify_tool_integrity(self.tools)
        return []
    
    async def get_registry_status(self) -> Dict[str, Any]:
        """Get status of tool registry"""
        if not self._test_mode and self.graph_manager:
            return await self.graph_manager.get_registry_status()
        return {
            "health_status": "healthy",
            "registered_tools": [tool.name for tool in self.tools],
            "message": "Running in test mode" if self._test_mode else "Graph manager not initialized"
        }
    
    async def _persist_tool_to_db(self, tool_obj: BaseTool):
        """将工具持久化到数据库(不影响现有功能)"""
        if not self._tool_repo:
            return
            
        try:
            # 检查工具是否已经存在
            existing_tool = await self._tool_repo.find_by_name(tool_obj.name)
            if existing_tool:
                # 工具已存在，无需重复添加
                return
                
            # 获取工具元数据
            source = inspect.getsource(tool_obj.__call__) if hasattr(tool_obj, '__call__') else ""
            
            # 处理schema - 确保它是一个字典
            schema_dict = {}
            if hasattr(tool_obj, "args_schema"):
                schema = getattr(tool_obj, "args_schema")
                if schema:
                    if isinstance(schema, dict):
                        schema_dict = schema
                    elif hasattr(schema, "schema"):
                        # Pydantic模型类，获取其schema
                        schema_dict = schema.schema()
                    elif hasattr(schema, "model_json_schema"):
                        # Pydantic v2模型类
                        schema_dict = schema.model_json_schema()
                    elif hasattr(schema, "__annotations__"):
                        # 尝试从类型注解构建简单schema
                        schema_dict = {"properties": {}}
                        for field, type_hint in schema.__annotations__.items():
                            schema_dict["properties"][field] = {"type": str(type_hint)}
            
            # 处理元数据 - 确保它是一个字典
            metadata_dict = {
                "source": source[:1000] if source else "",  # 限制长度
                "is_async": asyncio.iscoroutinefunction(tool_obj.func) if hasattr(tool_obj, "func") else False
            }
            
            # 创建工具模型
            tool_model = Tool(
                id=str(uuid.uuid4()),
                name=tool_obj.name,
                description=tool_obj.description,
                category=getattr(tool_obj, "category", "general"),
                schema=schema_dict,
                metadata=metadata_dict
            )
            
            # 保存到数据库
            await self._tool_repo.create_tool(tool_model)
            logger.info(f"工具 {tool_obj.name} 已保存到数据库")
        except Exception as e:
            logger.error(f"保存工具到数据库时出错: {e}")
    
    async def import_tools_to_db(self):
        """将所有已注册工具导入到数据库(不影响现有功能)"""
        if not self._persist_to_db or not self._tool_repo:
            logger.warning("数据库持久化未启用，无法导入工具")
            return
            
        for tool in self.tools:
            await self._persist_tool_to_db(tool)
            
        logger.info(f"已将 {len(self.tools)} 个工具导入到数据库")

    def has_tool(self, name: str) -> bool:
        """Check if a tool with the given name exists
        
        Args:
            name: Name of the tool to check
            
        Returns:
            True if the tool exists, False otherwise
        """
        return self.get_tool(name) is not None

# Initialize global tools manager
tools_manager = ToolsManager()

# Make initialize available at module level
async def initialize(persist_to_db: bool = False):
    """Initialize the global tools manager"""
    await tools_manager.initialize(persist_to_db=persist_to_db)

# 新增快捷方法
async def discover_directory(directory: str) -> Dict[str, List[str]]:
    """从目录发现工具的快捷方法"""
    return await tools_manager.discover_tools_from_directory(directory)

__all__ = ['tools_manager', 'initialize', 'discover_directory']
