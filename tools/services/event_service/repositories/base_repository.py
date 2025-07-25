"""
Base Repository for Event Service
Optimized for Event Sourcing patterns with Supabase
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.database.supabase_client import get_supabase_client
from core.logging import get_logger

class BaseEventRepository(ABC):
    """Base repository for event operations"""
    
    def __init__(self):
        self.db = get_supabase_client()
        self.logger = get_logger(self.__class__.__name__)
    
    async def _execute_query(self, operation: str, table: str, **kwargs) -> Dict[str, Any]:
        """Execute database query with error handling"""
        try:
            self.logger.debug(f"Executing {operation} on {table}")
            return {"success": True, "data": None, "error": None}
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
            return {"success": False, "data": None, "error": str(e)}

class BaseTaskRepository(ABC):
    """Base repository for background task operations"""
    
    def __init__(self):
        self.db = get_supabase_client()
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def create_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Create background task"""
        pass
    
    @abstractmethod
    async def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get active tasks"""
        pass
    
    @abstractmethod
    async def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status"""
        pass