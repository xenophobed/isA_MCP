"""
Database Integration for User Service

Integrates the user service with the actual Supabase database
instead of using in-memory cache
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from core.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class UserDatabaseService:
    """Database service for user operations using Supabase"""
    
    def __init__(self):
        """Initialize Supabase connection"""
        self.client = get_supabase_client()
        logger.info("UserDatabaseService initialized with centralized Supabase client")
    
    def table(self, table_name: str):
        """Get a table with the configured schema"""
        return self.client.table(table_name)
    
    async def get_user_by_auth0_id(self, auth0_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Auth0 ID from database"""
        try:
            result = self.table('users').select('*').eq('auth0_id', auth0_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by auth0_id {auth0_id}: {e}")
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by internal ID from database"""
        try:
            result = self.table('users').select('*').eq('id', user_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by id {user_id}: {e}")
            return None
    
    async def create_user(self, auth0_id: str, email: str, name: str, 
                         credits_remaining: int = 1000, credits_total: int = 1000, 
                         subscription_status: str = "free") -> Optional[Dict[str, Any]]:
        """Create new user in database"""
        try:
            now = datetime.utcnow().isoformat()
            
            user_data = {
                'auth0_id': auth0_id,
                'email': email,
                'name': name,
                'credits_remaining': credits_remaining,
                'credits_total': credits_total,
                'subscription_status': subscription_status,
                'created_at': now,
                'updated_at': now
            }
            
            result = self.table('users').insert(user_data).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error creating user {auth0_id}: {e}")
            return None
    
    async def update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user in database"""
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.table('users').update(updates).eq('id', user_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    async def log_api_usage(self, user_id: int, endpoint: str, tokens_used: int = 1,
                           request_data: Optional[str] = None,
                           response_data: Optional[str] = None) -> bool:
        """Log API usage to database"""
        try:
            usage_data = {
                'user_id': user_id,
                'endpoint': endpoint,
                'tokens_used': tokens_used,
                'request_data': request_data,
                'response_data': response_data,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # First try to insert into api_usage table (if it exists)
            try:
                result = self.table('api_usage').insert(usage_data).execute()
                return len(result.data) > 0
            except:
                # Fallback to audit_log table
                audit_data = {
                    'timestamp': usage_data['created_at'],
                    'tool_name': endpoint,
                    'user_id': str(user_id),
                    'success': True,
                    'execution_time': 0.0,
                    'security_level': 'low',
                    'details': f"API usage: {endpoint}, tokens: {tokens_used}"
                }
                result = self.table('audit_log').insert(audit_data).execute()
                return len(result.data) > 0
                
        except Exception as e:
            logger.error(f"Error logging API usage: {e}")
            return False