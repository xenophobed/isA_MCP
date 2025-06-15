from typing import Optional, Dict, Any, List
from .connection import ConnectionPool
from .transaction import TransactionManager
import logging
from contextlib import asynccontextmanager
from neo4j import AsyncGraphDatabase
from app.services.db.graph.neo4j.queries.conv_queries import ConversationQueries
from app.services.db.graph.neo4j.queries.tools_capabilities import ToolCapabilitiesQueries

logger = logging.getLogger(__name__)

class Neo4jService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ):
        # Only initialize if not already initialized
        if not hasattr(self, 'initialized'):
            self.pool = ConnectionPool(
                uri=uri,
                user=user,
                password=password,
                **kwargs
            )
            self.transaction_manager = TransactionManager()
            self.initialized = True
            self.driver = None
            self.gds_available = False

    async def initialize(self) -> None:
        """Initialize Neo4j connection and check GDS availability"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.pool.uri,
                auth=(self.pool.user, self.pool.password)
            )
            
            # Verify connectivity
            await self.driver.verify_connectivity()
            
            # Check GDS availability
            try:
                async with self.driver.session() as session:
                    result = await session.run(
                        "CALL gds.list() YIELD name RETURN count(name) as count"
                    )
                    records = await result.data()
                    self.gds_available = records and records[0]['count'] >= 0
                    logger.info("Graph Data Science library is available" if self.gds_available else "Using fallback vector similarity")
            except Exception as e:
                logger.info("Graph Data Science library not available, using fallback vector similarity")
                self.gds_available = False
                
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j connection: {e}")
            raise

    async def query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        read_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute Neo4j query with GDS fallback support"""
        if not self.driver:
            raise RuntimeError("Neo4j driver not initialized. Call initialize() first.")
            
        try:
            # If query contains GDS functions and GDS is not available, use fallback
            if not self.gds_available and "gds.similarity.cosine" in query:
                # Get the fallback version of the query
                query = self._get_fallback_query(query)
            
            # Determine if this is a write operation based on the query
            is_write = any(keyword in query.upper() for keyword in ["CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DROP"])
            read_only = not is_write and read_only
                
            async with self.driver.session(
                database="neo4j",
                default_access_mode="READ" if read_only else "WRITE"
            ) as session:
                result = await session.run(query, params or {})
                records = await result.data()
                return records
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def _get_fallback_query(self, query: str) -> str:
        """Get fallback version of GDS queries"""
        # Map of original queries to their fallback versions
        fallback_queries = {
            ConversationQueries.SEARCH_SIMILAR_FACTS: ConversationQueries.SEARCH_SIMILAR_FACTS_FALLBACK,
            ToolCapabilitiesQueries.SEARCH_BY_VECTOR.query: ToolCapabilitiesQueries.SEARCH_BY_VECTOR_FALLBACK.query
        }
        
        # Return fallback version if exists, otherwise return original
        for original, fallback in fallback_queries.items():
            if original in query:
                return fallback
                
        # If no exact match, but query uses GDS, construct manual cosine similarity
        if "gds.similarity.cosine" in query:
            # Extract vector fields from GDS function call
            import re
            gds_pattern = r"gds\.similarity\.cosine\(([^,]+),\s*([^)]+)\)"
            matches = re.findall(gds_pattern, query)
            
            if matches:
                for vec1, vec2 in matches:
                    manual_cosine = f"""
                    reduce(dot = 0.0, i IN range(0, size({vec1})-1) | 
                        dot + {vec1}[i] * {vec2}[i]
                    ) / (
                        sqrt(reduce(norm1 = 0.0, i IN range(0, size({vec1})-1) | 
                            norm1 + {vec1}[i] * {vec1}[i]
                        )) * 
                        sqrt(reduce(norm2 = 0.0, i IN range(0, size({vec2})-1) | 
                            norm2 + {vec2}[i] * {vec2}[i]
                        ))
                    )
                    """
                    query = query.replace(f"gds.similarity.cosine({vec1}, {vec2})", manual_cosine.strip())
                    
        return query

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            if self.driver:
                await self.driver.verify_connectivity()
                return {
                    "healthy": True,
                    "gds_available": self.gds_available
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e)
            }

    async def close(self) -> None:
        """Close the service"""
        if self.driver:
            await self.driver.close()
            self.driver = None

    # Compatibility methods for existing code
    async def run_query(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Compatibility method for existing code"""
        return await self.query(query, params)

    # Additional utility methods can be added here