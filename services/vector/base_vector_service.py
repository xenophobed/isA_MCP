from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseVectorService(ABC):
    """向量数据库服务基类"""
    
    @abstractmethod
    async def create_collection(self, name: str) -> Any:
        """创建集合"""
        pass
    
    @abstractmethod
    async def delete_collection(self, name: str) -> bool:
        """删除集合"""
        pass
    
    @abstractmethod
    async def collection_exists(self, name: str) -> bool:
        """检查集合是否存在"""
        pass
    
    @abstractmethod
    async def upsert_points(self, points: List[Dict[str, Any]]) -> bool:
        """插入或更新向量点"""
        pass
    
    @abstractmethod
    async def search(self, query: List[float], limit: int = 10, 
                    filters: Dict = None) -> List[Dict]:
        """搜索向量"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass
