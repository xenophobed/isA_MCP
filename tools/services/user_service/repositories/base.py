"""
Base Repository Classes and Interfaces

定义Repository模式的抽象基类和接口
遵循SOLID原则，提供统一的数据访问规范
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TypeVar, Generic
from datetime import datetime
import logging

from core.database.supabase_client import get_supabase_client
from .exceptions import RepositoryException, DatabaseConnectionException

# 泛型类型变量
T = TypeVar('T')

logger = logging.getLogger(__name__)


class BaseRepository(ABC, Generic[T]):
    """Repository抽象基类"""
    
    def __init__(self, table_name: str):
        """
        初始化Repository
        
        Args:
            table_name: 数据库表名
        """
        self.table_name = table_name
        self._client = None
        
    @property
    def client(self):
        """获取数据库客户端（懒加载）"""
        if self._client is None:
            try:
                self._client = get_supabase_client()
                logger.debug(f"Database client initialized for table: {self.table_name}")
            except Exception as e:
                logger.error(f"Failed to initialize database client: {e}")
                raise DatabaseConnectionException(f"Database connection failed: {e}")
        return self._client
    
    @property
    def table(self):
        """获取数据库表对象"""
        return self.client.table(self.table_name)
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Optional[T]:
        """
        创建新记录
        
        Args:
            data: 创建数据
            
        Returns:
            创建的对象
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: Any) -> Optional[T]:
        """
        根据ID获取记录
        
        Args:
            entity_id: 实体ID
            
        Returns:
            实体对象或None
        """
        pass
    
    @abstractmethod
    async def update(self, entity_id: Any, data: Dict[str, Any]) -> bool:
        """
        更新记录
        
        Args:
            entity_id: 实体ID
            data: 更新数据
            
        Returns:
            是否更新成功
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_id: Any) -> bool:
        """
        删除记录
        
        Args:
            entity_id: 实体ID
            
        Returns:
            是否删除成功
        """
        pass
    
    async def _execute_query(self, query_func, error_message: str = "Database query failed"):
        """
        执行数据库查询的通用方法
        
        Args:
            query_func: 查询函数
            error_message: 错误消息
            
        Returns:
            查询结果
            
        Raises:
            RepositoryException: 查询失败时抛出
        """
        try:
            result = query_func()
            return result
        except Exception as e:
            logger.error(f"{error_message}: {e}")
            raise RepositoryException(f"{error_message}: {e}")
    
    def _prepare_timestamps(self, data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """
        准备时间戳字段
        
        Args:
            data: 数据字典
            is_update: 是否为更新操作
            
        Returns:
            包含时间戳的数据字典
        """
        now = datetime.utcnow().isoformat()
        
        if not is_update:
            data['created_at'] = now
        data['updated_at'] = now
        
        return data
    
    def _handle_single_result(self, result, error_message: str = "Record not found"):
        """
        处理单条记录查询结果
        
        Args:
            result: 查询结果
            error_message: 错误消息
            
        Returns:
            记录数据或None
        """
        if hasattr(result, 'data') and result.data:
            return result.data
        return None
    
    def _handle_list_result(self, result):
        """
        处理列表查询结果
        
        Args:
            result: 查询结果
            
        Returns:
            记录列表
        """
        if hasattr(result, 'data') and result.data:
            return result.data
        return []


class ReadOnlyRepository(BaseRepository[T]):
    """只读Repository基类"""
    
    async def create(self, data: Dict[str, Any]) -> Optional[T]:
        raise NotImplementedError("Create operation not supported in read-only repository")
    
    async def update(self, entity_id: Any, data: Dict[str, Any]) -> bool:
        raise NotImplementedError("Update operation not supported in read-only repository")
    
    async def delete(self, entity_id: Any) -> bool:
        raise NotImplementedError("Delete operation not supported in read-only repository")