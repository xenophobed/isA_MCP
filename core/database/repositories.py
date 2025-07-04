#!/usr/bin/env python
"""
Database Repositories
Repository pattern implementation for different data domains
"""
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from abc import ABC, abstractmethod

from core.logging import get_logger
from .connection_manager import get_database_manager

logger = get_logger(__name__)

class BaseRepository(ABC):
    """Base repository with common database operations"""
    
    def __init__(self):
        self._db_manager = None
    
    async def _get_db(self):
        """Get database manager instance"""
        if self._db_manager is None:
            self._db_manager = await get_database_manager()
        return self._db_manager

class MemoryRepository(BaseRepository):
    """Repository for memory operations"""
    
    async def get_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a memory by key"""
        try:
            db = await self._get_db()
            result = db.supabase.table('memories').select('*').eq('key', key).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting memory {key}: {e}")
            return None
    
    async def set_memory(self, key: str, value: str, category: str = "general", 
                        importance: int = 1, user_id: str = "default") -> bool:
        """Store or update a memory"""
        try:
            db = await self._get_db()
            now = datetime.now().isoformat()
            
            # Try to update existing memory
            existing = await self.get_memory(key)
            if existing:
                result = db.supabase.table('memories').update({
                    'value': value,
                    'category': category,
                    'importance': importance,
                    'updated_at': now
                }).eq('key', key).execute()
            else:
                # Insert new memory
                result = db.supabase.table('memories').insert({
                    'key': key,
                    'value': value,
                    'category': category,
                    'importance': importance,
                    'created_by': user_id,
                    'created_at': now,
                    'updated_at': now
                }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error setting memory {key}: {e}")
            return False
    
    async def search_memories(self, query: str, category: Optional[str] = None, 
                             limit: int = 10) -> List[Dict[str, Any]]:
        """Search memories by content"""
        try:
            db = await self._get_db()
            query_builder = db.supabase.table('memories').select('*')
            
            if category:
                query_builder = query_builder.eq('category', category)
            
            # Full text search on key and value
            query_builder = query_builder.or_(f'key.ilike.%{query}%,value.ilike.%{query}%')
            query_builder = query_builder.order('importance', desc=True).limit(limit)
            
            result = query_builder.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []
    
    async def delete_memory(self, key: str) -> bool:
        """Delete a memory by key"""
        try:
            db = await self._get_db()
            result = db.supabase.table('memories').delete().eq('key', key).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting memory {key}: {e}")
            return False

class UserRepository(BaseRepository):
    """Repository for user operations"""
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            db = await self._get_db()
            result = db.supabase.table('users').select('*').eq('user_id', user_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def create_user(self, user_id: str, email: str = None, phone: str = None,
                         shipping_addresses: List[Dict] = None, 
                         payment_methods: List[Dict] = None,
                         preferences: Dict = None) -> bool:
        """Create a new user"""
        try:
            db = await self._get_db()
            now = datetime.now().isoformat()
            
            result = db.supabase.table('users').insert({
                'user_id': user_id,
                'email': email,
                'phone': phone,
                'shipping_addresses': shipping_addresses or [],
                'payment_methods': payment_methods or [],
                'preferences': preferences or {},
                'created_at': now,
                'updated_at': now
            }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return False
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            db = await self._get_db()
            updates['updated_at'] = datetime.now().isoformat()
            
            result = db.supabase.table('users').update(updates).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

class SessionRepository(BaseRepository):
    """Repository for session operations"""
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session"""
        try:
            db = await self._get_db()
            result = db.supabase.table('user_sessions').select('*').eq('session_id', session_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    async def create_session(self, session_id: str, user_id: str, 
                           cart_data: Dict = None, checkout_data: Dict = None,
                           expires_at: str = None) -> bool:
        """Create user session"""
        try:
            db = await self._get_db()
            now = datetime.now().isoformat()
            
            result = db.supabase.table('user_sessions').insert({
                'session_id': session_id,
                'user_id': user_id,
                'cart_data': cart_data or {},
                'checkout_data': checkout_data or {},
                'created_at': now,
                'expires_at': expires_at
            }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}")
            return False

class ModelRepository(BaseRepository):
    """Repository for model operations"""
    
    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model by ID"""
        try:
            db = await self._get_db()
            result = db.supabase.table('models').select('*').eq('model_id', model_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting model {model_id}: {e}")
            return None
    
    async def register_model(self, model_id: str, model_type: str, 
                           metadata: Dict = None, capabilities: List[str] = None) -> bool:
        """Register a new model"""
        try:
            db = await self._get_db()
            now = datetime.now().isoformat()
            
            # Insert model
            result = db.supabase.table('models').insert({
                'model_id': model_id,
                'model_type': model_type,
                'metadata': json.dumps(metadata) if metadata else None,
                'created_at': now,
                'updated_at': now
            }).execute()
            
            # Insert capabilities
            if capabilities:
                capability_data = [
                    {'model_id': model_id, 'capability': cap} 
                    for cap in capabilities
                ]
                db.supabase.table('model_capabilities').insert(capability_data).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error registering model {model_id}: {e}")
            return False

class CacheRepository(BaseRepository):
    """Repository for cache operations"""
    
    async def get_weather_cache(self, city: str) -> Optional[Dict[str, Any]]:
        """Get cached weather data"""
        try:
            db = await self._get_db()
            result = db.supabase.table('weather_cache').select('*').eq('city', city).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting weather cache for {city}: {e}")
            return None
    
    async def set_weather_cache(self, city: str, weather_data: Dict) -> bool:
        """Cache weather data"""
        try:
            db = await self._get_db()
            now = datetime.now().isoformat()
            
            # Try to update existing cache
            existing = await self.get_weather_cache(city)
            if existing:
                result = db.supabase.table('weather_cache').update({
                    'weather_data': json.dumps(weather_data),
                    'updated_at': now
                }).eq('city', city).execute()
            else:
                result = db.supabase.table('weather_cache').insert({
                    'city': city,
                    'weather_data': json.dumps(weather_data),
                    'created_at': now,
                    'updated_at': now
                }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error caching weather for {city}: {e}")
            return False

class AuditRepository(BaseRepository):
    """Repository for audit operations"""
    
    async def log_tool_usage(self, tool_name: str, user_id: str, success: bool,
                           execution_time: float, security_level: str, 
                           details: str = None) -> bool:
        """Log tool usage to audit log"""
        try:
            db = await self._get_db()
            result = db.supabase.table('audit_log').insert({
                'timestamp': datetime.now().isoformat(),
                'tool_name': tool_name,
                'user_id': user_id,
                'success': success,
                'execution_time': execution_time,
                'security_level': security_level,
                'details': details
            }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error logging tool usage: {e}")
            return False
    
    async def create_auth_request(self, request_id: str, tool_name: str, 
                                arguments: Dict, user_id: str, security_level: str,
                                reason: str, expires_at: str) -> bool:
        """Create authorization request"""
        try:
            db = await self._get_db()
            result = db.supabase.table('authorization_requests').insert({
                'id': request_id,
                'tool_name': tool_name,
                'arguments': json.dumps(arguments),
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'security_level': security_level,
                'reason': reason,
                'expires_at': expires_at,
                'status': 'pending'
            }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error creating auth request: {e}")
            return False

class EmbeddingRepository(BaseRepository):
    """Repository for embedding operations"""
    
    async def store_embeddings(self, table: str, embeddings_data: List[Dict]) -> bool:
        """Store multiple embeddings"""
        try:
            db = await self._get_db()
            result = db.supabase.table(table).upsert(embeddings_data).execute()
            return True
        except Exception as e:
            logger.error(f"Error storing embeddings to {table}: {e}")
            return False
    
    async def search_embeddings(self, table: str, query_embedding: List[float], 
                              limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict]:
        """Search embeddings by similarity"""
        try:
            db = await self._get_db()
            return await db.execute_vector_search(
                table=table,
                embedding_column='embedding',
                query_embedding=query_embedding,
                limit=limit,
                filters=filters
            )
        except Exception as e:
            logger.error(f"Error searching embeddings in {table}: {e}")
            return []
    
    async def get_embeddings_cache(self, table: str, key_column: str = None) -> Dict[str, List[float]]:
        """Get cached embeddings"""
        try:
            db = await self._get_db()
            select_columns = f'{key_column}, embedding' if key_column else 'id, embedding'
            result = db.supabase.table(table).select(select_columns).execute()
            
            cache = {}
            for row in result.data or []:
                key = row.get(key_column or 'id')
                embedding = row.get('embedding')
                if key and embedding:
                    cache[key] = embedding
            
            return cache
        except Exception as e:
            logger.error(f"Error getting embeddings cache from {table}: {e}")
            return {} 