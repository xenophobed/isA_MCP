from typing import Any, Callable, TypeVar, Optional, List, Dict
from neo4j import AsyncSession
import logging
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

class TransactionManager:
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    async def execute_with_retry(
        self,
        session: AsyncSession,
        operation: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute operation with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                tx = await session.begin_transaction()
                try:
                    result = await operation(tx, *args, **kwargs)
                    await tx.commit()
                    return result
                finally:
                    await tx.close()
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Transaction attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
                logger.error(f"Transaction failed after {self.max_retries} attempts")
                raise last_error

    async def execute_read(
        self,
        session: AsyncSession,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute read operation"""
        async def _read_operation(tx, query, params):
            result = await tx.run(query, parameters=params or {})
            return await result.data()
            
        return await self.execute_with_retry(session, _read_operation, query, params)

    async def execute_write(
        self,
        session: AsyncSession,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute write operation"""
        async def _write_operation(tx, query, params):
            result = await tx.run(query, parameters=params or {})
            return await result.data()
            
        return await self.execute_with_retry(session, _write_operation, query, params)

def transactional(read_only: bool = False):
    """Decorator for transactional operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            transaction_manager = TransactionManager()
            async with self.pool.get_session() as session:
                if read_only:
                    return await transaction_manager.execute_read(session, *args, **kwargs)
                return await transaction_manager.execute_write(session, *args, **kwargs)
        return wrapper
    return decorator