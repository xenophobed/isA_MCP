from typing import List, Dict, Any, Callable, Optional
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
from app.services.agent.capabilities.contextual.capability.registry.tool_graph_manager import ToolGraphManager
from app.config.config_manager import config_manager
from app.repositories.tool.tool_repo import ToolRepository
from app.models.tool.tool_model import Tool

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

__all__ = ['tools_manager', 'initialize']
