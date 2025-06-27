#!/usr/bin/env python
"""
Supabase Database Client
Centralized Supabase connection and utilities for the MCP server
"""
import os
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

from core.logging import get_logger

logger = get_logger(__name__)

class SupabaseClient:
    """Singleton Supabase client for database operations"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Supabase client"""
        load_dotenv()
        
        self.supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials. Check NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        
        try:
            self._client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    @property
    def client(self) -> Client:
        """Get the Supabase client instance"""
        if self._client is None:
            self._initialize()
        return self._client
    
    # Memory operations
    async def get_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a memory by key"""
        try:
            result = self.client.table('memories').select('*').eq('key', key).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting memory {key}: {e}")
            return None
    
    async def set_memory(self, key: str, value: str, category: str = "general", 
                        importance: int = 1, user_id: str = "default") -> bool:
        """Store or update a memory"""
        try:
            now = datetime.now().isoformat()
            
            # Try to update existing memory
            existing = await self.get_memory(key)
            if existing:
                result = self.client.table('memories').update({
                    'value': value,
                    'category': category,
                    'importance': importance,
                    'updated_at': now
                }).eq('key', key).execute()
            else:
                # Insert new memory
                result = self.client.table('memories').insert({
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
            query_builder = self.client.table('memories').select('*')
            
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
            result = self.client.table('memories').delete().eq('key', key).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting memory {key}: {e}")
            return False
    
    # User operations
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            result = self.client.table('users').select('*').eq('user_id', user_id).single().execute()
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
            now = datetime.now().isoformat()
            
            result = self.client.table('users').insert({
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
            updates['updated_at'] = datetime.now().isoformat()
            
            result = self.client.table('users').update(updates).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    # Session operations  
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session"""
        try:
            result = self.client.table('user_sessions').select('*').eq('session_id', session_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    async def create_session(self, session_id: str, user_id: str, 
                           cart_data: Dict = None, checkout_data: Dict = None,
                           expires_at: str = None) -> bool:
        """Create user session"""
        try:
            now = datetime.now().isoformat()
            
            result = self.client.table('user_sessions').insert({
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
    
    # Model operations
    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model by ID"""
        try:
            result = self.client.table('models').select('*').eq('model_id', model_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting model {model_id}: {e}")
            return None
    
    async def register_model(self, model_id: str, model_type: str, 
                           metadata: Dict = None, capabilities: List[str] = None) -> bool:
        """Register a new model"""
        try:
            now = datetime.now().isoformat()
            
            # Insert model
            result = self.client.table('models').insert({
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
                self.client.table('model_capabilities').insert(capability_data).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error registering model {model_id}: {e}")
            return False
    
    # Weather operations
    async def get_weather_cache(self, city: str) -> Optional[Dict[str, Any]]:
        """Get cached weather data"""
        try:
            result = self.client.table('weather_cache').select('*').eq('city', city).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting weather cache for {city}: {e}")
            return None
    
    async def set_weather_cache(self, city: str, weather_data: Dict) -> bool:
        """Cache weather data"""
        try:
            now = datetime.now().isoformat()
            
            # Try to update existing cache
            existing = await self.get_weather_cache(city)
            if existing:
                result = self.client.table('weather_cache').update({
                    'weather_data': json.dumps(weather_data),
                    'updated_at': now
                }).eq('city', city).execute()
            else:
                result = self.client.table('weather_cache').insert({
                    'city': city,
                    'weather_data': json.dumps(weather_data),
                    'created_at': now,
                    'updated_at': now
                }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error caching weather for {city}: {e}")
            return False
    
    # Audit operations
    async def log_tool_usage(self, tool_name: str, user_id: str, success: bool,
                           execution_time: float, security_level: str, 
                           details: str = None) -> bool:
        """Log tool usage to audit log"""
        try:
            result = self.client.table('audit_log').insert({
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
    
    # Authorization operations
    async def create_auth_request(self, request_id: str, tool_name: str, 
                                arguments: Dict, user_id: str, security_level: str,
                                reason: str, expires_at: str) -> bool:
        """Create authorization request"""
        try:
            result = self.client.table('authorization_requests').insert({
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
    
    # Generic operations
    async def execute_query(self, table: str, operation: str, data: Dict = None, 
                           filters: Dict = None) -> Optional[Any]:
        """Execute generic database operation"""
        try:
            query_builder = self.client.table(table)
            
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

# Global instance
_supabase_client = None

def get_supabase_client() -> SupabaseClient:
    """Get the global Supabase client instance"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client