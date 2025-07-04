#!/usr/bin/env python
"""
Database Compatibility Layer
Provides backward compatibility with existing supabase_client usage
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from core.logging import get_logger
from .connection_manager import get_database_manager
from .repositories import (
    MemoryRepository, UserRepository, SessionRepository, 
    ModelRepository, CacheRepository, AuditRepository
)

logger = get_logger(__name__)

class CompatibilitySupabaseClient:
    """Compatibility wrapper that mimics the old SupabaseClient interface"""
    
    def __init__(self):
        self._db_manager = None
        self._memory_repo = MemoryRepository()
        self._user_repo = UserRepository()
        self._session_repo = SessionRepository()
        self._model_repo = ModelRepository()
        self._cache_repo = CacheRepository()
        self._audit_repo = AuditRepository()
    
    async def _get_db(self):
        """Get database manager instance"""
        if self._db_manager is None:
            self._db_manager = await get_database_manager()
        return self._db_manager
    
    @property
    async def client(self):
        """Get Supabase client for backward compatibility"""
        db = await self._get_db()
        return db.supabase
    
    # Memory operations - delegate to MemoryRepository
    async def get_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a memory by key"""
        return await self._memory_repo.get_memory(key)
    
    async def set_memory(self, key: str, value: str, category: str = "general", 
                        importance: int = 1, user_id: str = "default") -> bool:
        """Store or update a memory"""
        return await self._memory_repo.set_memory(key, value, category, importance, user_id)
    
    async def search_memories(self, query: str, category: Optional[str] = None, 
                             limit: int = 10) -> List[Dict[str, Any]]:
        """Search memories by content"""
        return await self._memory_repo.search_memories(query, category, limit)
    
    async def delete_memory(self, key: str) -> bool:
        """Delete a memory by key"""
        return await self._memory_repo.delete_memory(key)
    
    # User operations - delegate to UserRepository
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return await self._user_repo.get_user(user_id)
    
    async def create_user(self, user_id: str, email: str = None, phone: str = None,
                         shipping_addresses: List[Dict] = None, 
                         payment_methods: List[Dict] = None,
                         preferences: Dict = None) -> bool:
        """Create a new user"""
        return await self._user_repo.create_user(
            user_id, email, phone, shipping_addresses, payment_methods, preferences
        )
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user data"""
        return await self._user_repo.update_user(user_id, updates)
    
    # Session operations - delegate to SessionRepository
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session"""
        return await self._session_repo.get_session(session_id)
    
    async def create_session(self, session_id: str, user_id: str, 
                           cart_data: Dict = None, checkout_data: Dict = None,
                           expires_at: str = None) -> bool:
        """Create user session"""
        return await self._session_repo.create_session(
            session_id, user_id, cart_data, checkout_data, expires_at
        )
    
    # Model operations - delegate to ModelRepository
    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model by ID"""
        return await self._model_repo.get_model(model_id)
    
    async def register_model(self, model_id: str, model_type: str, 
                           metadata: Dict = None, capabilities: List[str] = None) -> bool:
        """Register a new model"""
        return await self._model_repo.register_model(model_id, model_type, metadata, capabilities)
    
    # Weather operations - delegate to CacheRepository
    async def get_weather_cache(self, city: str) -> Optional[Dict[str, Any]]:
        """Get cached weather data"""
        return await self._cache_repo.get_weather_cache(city)
    
    async def set_weather_cache(self, city: str, weather_data: Dict) -> bool:
        """Cache weather data"""
        return await self._cache_repo.set_weather_cache(city, weather_data)
    
    # Audit operations - delegate to AuditRepository
    async def log_tool_usage(self, tool_name: str, user_id: str, success: bool,
                           execution_time: float, security_level: str, 
                           details: str = None) -> bool:
        """Log tool usage to audit log"""
        return await self._audit_repo.log_tool_usage(
            tool_name, user_id, success, execution_time, security_level, details
        )
    
    async def create_auth_request(self, request_id: str, tool_name: str, 
                                arguments: Dict, user_id: str, security_level: str,
                                reason: str, expires_at: str) -> bool:
        """Create authorization request"""
        return await self._audit_repo.create_auth_request(
            request_id, tool_name, arguments, user_id, security_level, reason, expires_at
        )
    
    # Generic operations - provide direct database access
    async def execute_query(self, table: str, operation: str, data: Dict = None, 
                           filters: Dict = None) -> Optional[Any]:
        """Execute generic database operation"""
        try:
            db = await self._get_db()
            query_builder = db.supabase.table(table)
            
            if operation == 'select':
                query_builder = query_builder.select('*')
            elif operation == 'insert':
                return query_builder.insert(data).execute()
            elif operation == 'update':
                query_builder = query_builder.update(data)
            elif operation == 'delete':
                query_builder = query_builder.delete()
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    query_builder = query_builder.eq(key, value)
            
            return query_builder.execute()
            
        except Exception as e:
            logger.error(f"Error executing query on {table}: {e}")
            return None

# Global instance for backward compatibility
_compatibility_client = None

async def get_supabase_client() -> CompatibilitySupabaseClient:
    """Get the compatibility Supabase client instance"""
    global _compatibility_client
    if _compatibility_client is None:
        _compatibility_client = CompatibilitySupabaseClient()
    return _compatibility_client

def get_supabase_client_sync() -> CompatibilitySupabaseClient:
    """Get compatibility client synchronously (for non-async contexts)"""
    global _compatibility_client
    if _compatibility_client is None:
        _compatibility_client = CompatibilitySupabaseClient()
    return _compatibility_client 