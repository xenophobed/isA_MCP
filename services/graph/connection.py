from typing import Optional, Dict, Any, AsyncGenerator
from neo4j import AsyncDriver, AsyncSession, AsyncGraphDatabase
from datetime import datetime
import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ConnectionPool:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        max_connections: int = 50,
        max_connection_lifetime: int = 3600,
        connection_timeout: int = 30
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.max_connections = max_connections
        self.max_connection_lifetime = max_connection_lifetime
        self.connection_timeout = connection_timeout
        
        self.driver: Optional[AsyncDriver] = None
        self.last_connection_time: datetime = datetime.now()
        self.health_status: bool = False
        self.active_sessions: int = 0
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the connection pool"""
        try:
            if not self.driver:
                self.driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_lifetime=self.max_connection_lifetime,
                    max_connection_pool_size=self.max_connections,
                    connection_timeout=self.connection_timeout
                )
                # Verify connection
                await self.verify_connectivity()
                logger.info("Neo4j connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j connection pool: {str(e)}")
            self.health_status = False
            raise

    async def verify_connectivity(self) -> bool:
        """Verify database connectivity"""
        try:
            if not self.driver:
                return False
                
            async with self.get_session() as session:
                result = await session.run("RETURN 1 as num")
                record = await result.single()
                self.health_status = record and record.get("num") == 1
                return self.health_status
        except Exception as e:
            logger.error(f"Connection verification failed: {str(e)}")
            self.health_status = False
            return False

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a session from the pool with automatic cleanup"""
        if not self.driver:
            await self.initialize()

        async with self._lock:
            self.active_sessions += 1
            
        try:
            session = self.driver.session()
            yield session
        finally:
            await session.close()
            async with self._lock:
                self.active_sessions -= 1

    async def close(self) -> None:
        """Close the connection pool"""
        if self.driver:
            await self.driver.close()
            self.driver = None            
            logger.info("Neo4j connection pool closed")

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current pool statistics"""
        return {
            "active_sessions": self.active_sessions,
            "max_connections": self.max_connections,
            "health_status": self.health_status,
            "last_connection": self.last_connection_time.isoformat()
        }
