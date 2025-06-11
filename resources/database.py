import logging
from typing import Dict, Any, Optional

class Database:
    """简单的数据库类用于演示"""
    
    def __init__(self, url: str):
        self.url = url
        self.connected = False
        self.data = {}
        self.logger = logging.getLogger("database")
    
    @classmethod
    async def connect(cls, url: str) -> 'Database':
        """连接到数据库"""
        db = cls(url)
        db.connected = True
        db.logger.info(f"已连接到数据库: {url}")
        return db
    
    async def disconnect(self):
        """断开数据库连接"""
        self.connected = False
        self.logger.info("已断开数据库连接")
    
    async def get(self, key: str) -> Optional[Any]:
        """从数据库获取值"""
        if not self.connected:
            raise ValueError("数据库未连接")
        return self.data.get(key)
    
    async def set(self, key: str, value: Any):
        """在数据库中设置值"""
        if not self.connected:
            raise ValueError("数据库未连接")
        self.data[key] = value 