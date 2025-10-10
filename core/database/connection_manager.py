#!/usr/bin/env python
"""
Database Connection Manager
Centralized connection pooling and management for Supabase
"""
import os
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from contextlib import asynccontextmanager

# Make asyncpg optional - only needed for direct PostgreSQL connections
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

from supabase import create_client, Client
from dotenv import load_dotenv

from core.logging import get_logger
from core.config import get_settings

logger = get_logger(__name__)

class DatabaseManager:
    """Centralized database manager with connection pooling"""
    
    _instance = None
    _supabase_client = None
    _pg_pool = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    async def initialize(self):
        """Initialize database connections and pools"""
        if self._initialized:
            return
            
        load_dotenv()
        settings = get_settings()
        
        # Initialize Supabase client
        await self._init_supabase_client(settings)
        
        # Initialize PostgreSQL connection pool for direct access
        await self._init_pg_pool(settings)
        
        self._initialized = True
        logger.info("Database manager initialized successfully")
    
    async def _init_supabase_client(self, settings):
        """Initialize Supabase client"""
        self.supabase_url = settings.supabase_url
        self.supabase_key = settings.supabase_service_role_key
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials")
        
        try:
            self._supabase_client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    async def _init_pg_pool(self, settings):
        """Initialize PostgreSQL connection pool for vector operations"""
        # Only try to create PostgreSQL pool if asyncpg is available
        if ASYNCPG_AVAILABLE:
            try:
                # Extract connection details from Supabase URL
                db_url = self._build_postgres_url(settings)

                self._pg_pool = await asyncpg.create_pool(
                    db_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60,
                    server_settings={
                        'application_name': 'mcp_server',
                        'search_path': 'dev,test,public'
                    }
                )
                logger.info("PostgreSQL connection pool initialized")
            except Exception as e:
                logger.warning(f"PostgreSQL pool initialization failed: {e}")
                # Continue without pool - fallback to Supabase client only
        else:
            logger.info("asyncpg not available - using Supabase client only (no direct PostgreSQL pool)")
    
    def _build_postgres_url(self, settings) -> str:
        """Build PostgreSQL connection URL from Supabase settings"""
        # Extract from Supabase URL: https://xxx.supabase.co -> xxx.supabase.co
        host = self.supabase_url.replace('https://', '').replace('http://', '')
        
        return f"postgresql://postgres:{settings.supabase_pwd}@{host}:5432/postgres"
    
    @property
    def supabase(self) -> Client:
        """Get Supabase client"""
        if not self._initialized:
            raise RuntimeError("Database manager not initialized")
        return self._supabase_client
    
    @asynccontextmanager
    async def get_pg_connection(self):
        """Get PostgreSQL connection from pool"""
        if not self._pg_pool:
            raise RuntimeError("PostgreSQL pool not available")
        
        async with self._pg_pool.acquire() as connection:
            yield connection
    
    async def execute_query(self, query: str, *args) -> List[Dict]:
        """Execute raw PostgreSQL query"""
        if not self._pg_pool:
            raise RuntimeError("PostgreSQL pool not available")
        
        async with self.get_pg_connection() as conn:
            result = await conn.fetch(query, *args)
            return [dict(row) for row in result]
    
    async def execute_vector_search(self, table: str, embedding_column: str, 
                                   query_embedding: List[float], 
                                   limit: int = 10, 
                                   filters: Dict[str, Any] = None) -> List[Dict]:
        """Execute vector similarity search"""
        if not self._pg_pool:
            # Fallback to Supabase RPC function
            return await self._supabase_vector_search(table, query_embedding, limit, filters)
        
        # Build query with filters
        where_clause = ""
        params = [query_embedding, limit]
        param_idx = 3
        
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(f"{key} = ${param_idx}")
                params.append(value)
                param_idx += 1
            if conditions:
                where_clause = f"WHERE {' AND '.join(conditions)}"
        
        query = f"""
        SELECT *, 1 - ({embedding_column} <=> $1) AS similarity
        FROM {table}
        {where_clause}
        ORDER BY {embedding_column} <=> $1
        LIMIT $2
        """
        
        return await self.execute_query(query, *params)
    
    async def _supabase_vector_search(self, table: str, query_embedding: List[float], 
                                     limit: int, filters: Dict[str, Any]) -> List[Dict]:
        """Fallback vector search using Supabase RPC"""
        # This would use table-specific RPC functions like match_documents, match_metadata_embeddings
        function_map = {
            'rag_documents': 'match_documents',
            'db_metadata_embedding': 'match_metadata_embeddings'
        }
        
        function_name = function_map.get(table)
        if not function_name:
            raise ValueError(f"No RPC function mapped for table: {table}")
        
        params = {
            'query_embedding': query_embedding,
            'match_count': limit,
            'match_threshold': 0.0
        }
        
        # Add table-specific filters
        if filters:
            if table == 'rag_documents' and 'collection_name' in filters:
                params['collection_filter'] = filters['collection_name']
            elif table == 'db_metadata_embedding':
                if 'entity_type' in filters:
                    params['entity_type_filter'] = filters['entity_type']
                if 'database_source' in filters:
                    params['database_filter'] = filters['database_source']
        
        result = self.supabase.rpc(function_name, params).execute()
        return result.data or []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database connection health"""
        try:
            # Test Supabase connection using proper schema
            schema = os.getenv('DB_SCHEMA', 'public')
            result = self.supabase.schema(schema).table('memories').select('count').limit(1).execute()
            supabase_healthy = True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            supabase_healthy = False
        
        # Test PostgreSQL pool
        pg_healthy = False
        if self._pg_pool:
            try:
                async with self.get_pg_connection() as conn:
                    await conn.fetchval('SELECT 1')
                pg_healthy = True
            except Exception as e:
                logger.error(f"PostgreSQL health check failed: {e}")
        
        return {
            'supabase_healthy': supabase_healthy,
            'postgresql_healthy': pg_healthy,
            'pool_size': self._pg_pool.get_size() if self._pg_pool else 0,
            'pool_free': self._pg_pool.get_idle_size() if self._pg_pool else 0,
            'timestamp': datetime.now().isoformat()
        }
    
    async def close(self):
        """Close all database connections"""
        if self._pg_pool:
            await self._pg_pool.close()
        self._initialized = False
        logger.info("Database connections closed")

# Global instance
_database_manager = None

async def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
        await _database_manager.initialize()
    return _database_manager

def get_database_manager_sync() -> DatabaseManager:
    """Get database manager synchronously (for non-async contexts)"""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
        # Note: Still need to call initialize() in async context
    return _database_manager 