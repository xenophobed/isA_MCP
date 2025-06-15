from typing import Dict, Optional, List, Any
from .base import BaseQuery, QueryType, QueryMetrics
import logging
from datetime import datetime
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)

class QueryRegistry:
    """Central registry for all Neo4j queries"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.queries: Dict[str, BaseQuery] = {}
            self.query_cache: Dict[tuple, Any] = {}
            self._lock = asyncio.Lock()
            self.initialized = True

    def register_query(self, query: BaseQuery) -> None:
        """Register a new query"""
        if query.name in self.queries:
            logger.warning(f"Query {query.name} already registered. Updating...")
        self.queries[query.name] = query
        logger.info(f"Registered query: {query.name} (v{query.version})")

    def get_query(self, name: str) -> Optional[BaseQuery]:
        """Get a query by name"""
        return self.queries.get(name)

    async def get_cached_result(
        self,
        query_name: str,
        params: tuple
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached query result"""
        cache_key = (query_name, params)
        async with self._lock:
            return self.query_cache.get(cache_key)

    async def execute_query(
        self,
        neo4j_service: Any,
        query_name: str,
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute a query with metrics recording"""
        query = self.get_query(query_name)
        if not query:
            raise ValueError(f"Query {query_name} not found")

        start_time = datetime.now()
        error = None
        result = None
        cache_hit = False

        try:
            # Skip caching if query contains non-hashable types
            if query.cacheable and query.query_type == QueryType.READ:
                # Convert params to hashable format
                cache_key = self._make_cache_key(query_name, params)
                cached_result = await self.get_cached_result(query_name, cache_key)
                if cached_result:
                    cache_hit = True
                    result = cached_result
                    return result

                # Execute and cache the result
                result = await self._execute_query_without_cache(
                    neo4j_service, query_name, params
                )
                async with self._lock:
                    self.query_cache[(query_name, cache_key)] = result
                return result

        except TypeError:
            # If params contain unhashable types, skip caching
            result = await self._execute_query_without_cache(
                neo4j_service, query_name, params
            )
            return result

        finally:
            # Record metrics
            if result is not None:  # Only record metrics if query was executed
                execution_time = (datetime.now() - start_time).total_seconds()
                metrics = QueryMetrics(
                    execution_time=execution_time,
                    timestamp=datetime.now(),
                    cache_hit=cache_hit,
                    error=error,
                    affected_nodes=len(result) if result else 0
                )
                query.record_metrics(metrics)

        return await self._execute_query_without_cache(
            neo4j_service, query_name, params
        )

    def _make_cache_key(self, query_name: str, params: Dict[str, Any]) -> tuple:
        """Create a hashable cache key from params"""
        hashable_items = []
        for k, v in sorted(params.items()):
            if isinstance(v, (list, dict)):
                continue  # Skip non-hashable types
            hashable_items.append((k, v))
        return (query_name, tuple(hashable_items))

    async def execute_vector_query(
        self,
        neo4j_service: Any,
        query_name: str,
        vector: List[float],
        params: Dict[str, Any],
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Execute vector-based query"""
        query = self.get_query(query_name)
        query_params = {
            **params,
            "query_vector": vector,
            "threshold": similarity_threshold,
            "dimension": len(vector)
        }
        
        # Skip caching for vector queries since vectors aren't hashable
        return await self._execute_query_without_cache(
            neo4j_service, 
            query_name, 
            query_params
        )

    async def _execute_query_without_cache(
        self,
        neo4j_service: Any,
        query_name: str,
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute a query without caching"""
        query = self.get_query(query_name)
        if not query:
            raise ValueError(f"Query {query_name} not found")

        # Parameter validation
        if not query.validate_parameters(params):
            raise ValueError("Invalid parameters provided")

        # Execute query
        result = await neo4j_service.query(
            query=query.query,
            params=params,
            read_only=query.query_type == QueryType.READ
        )
        return result