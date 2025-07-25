"""
Database Integration for User Service

Integrates the user service with the actual Supabase database
instead of using in-memory cache
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
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
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email from database"""
        try:
            result = self.table('users').select('*').eq('email', email).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    async def create_user(self, auth0_id: str, email: str, name: str, 
                         credits_remaining: int = 1000, credits_total: int = 1000, 
                         subscription_status: str = "free") -> Optional[Dict[str, Any]]:
        """Create new user in database"""
        try:
            now = datetime.utcnow().isoformat()
            
            user_data = {
                'user_id': auth0_id,  # user_id是业务主键，存储Auth0 ID字符串
                'auth0_id': auth0_id,  # auth0_id字段用于显式标识Auth0来源
                'email': email,
                'name': name,
                'credits_remaining': credits_remaining,
                'credits_total': credits_total,
                'subscription_status': subscription_status,
                'is_active': True,  # 添加默认的 is_active 状态
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

    # 订阅相关数据库操作
    async def create_subscription(self, user_id: int, stripe_subscription_id: str,
                                stripe_customer_id: str, plan_type: str, status: str,
                                current_period_start: datetime, current_period_end: datetime) -> Optional[Dict[str, Any]]:
        """Create subscription in database"""
        try:
            now = datetime.utcnow().isoformat()
            
            # Get the user's auth0_id which is what the subscription table expects
            user_data = await self.get_user_by_id(user_id)
            if not user_data:
                logger.error(f"User not found for ID: {user_id}")
                return None
                
            user_auth0_id = user_data.get('user_id')  # user_id字段存储的就是auth0_id字符串
            
            subscription_data = {
                'user_id': user_auth0_id,  # 使用auth0_id作为外键，符合数据库设计
                'subscription_scope': 'global',  # Add required field
                'stripe_subscription_id': stripe_subscription_id,
                'stripe_customer_id': stripe_customer_id,
                'plan_type': plan_type,
                'status': status,
                'current_period_start': current_period_start.isoformat() if current_period_start.year > 1970 else datetime.utcnow().isoformat(),
                'current_period_end': current_period_end.isoformat() if current_period_end.year > 1970 else (datetime.utcnow() + timedelta(days=30)).isoformat(),
                'created_at': now,
                'updated_at': now
            }
            
            result = self.table('subscriptions').insert(subscription_data).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None

    async def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by Stripe subscription ID"""
        try:
            result = self.table('subscriptions').select('*').eq('stripe_subscription_id', stripe_subscription_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting subscription by stripe_id {stripe_subscription_id}: {e}")
            return None

    async def get_subscription_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get active subscription by user ID"""
        try:
            result = self.table('subscriptions').select('*').eq('user_id', user_id).eq('status', 'active').single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting subscription by user_id {user_id}: {e}")
            return None

    async def update_subscription(self, subscription_id: int, updates: Dict[str, Any]) -> bool:
        """Update subscription in database"""
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.table('subscriptions').update(updates).eq('id', subscription_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating subscription {subscription_id}: {e}")
            return False

    async def update_subscription_by_stripe_id(self, stripe_subscription_id: str, updates: Dict[str, Any]) -> bool:
        """Update subscription by Stripe subscription ID"""
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.table('subscriptions').update(updates).eq('stripe_subscription_id', stripe_subscription_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating subscription by stripe_id {stripe_subscription_id}: {e}")
            return False

    async def update_user_subscription_status(self, user_id: int, subscription_status: str, 
                                            credits_total: int = None, credits_remaining: int = None) -> bool:
        """Update user's subscription status and credits"""
        try:
            updates = {
                'subscription_status': subscription_status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if credits_total is not None:
                updates['credits_total'] = credits_total
            if credits_remaining is not None:
                updates['credits_remaining'] = credits_remaining
            
            result = self.table('users').update(updates).eq('id', user_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating user subscription status {user_id}: {e}")
            return False

    async def log_webhook_event(self, event_id: str, event_type: str, 
                              processed: bool, user_id: int = None, 
                              stripe_subscription_id: str = None, 
                              error_message: str = None) -> bool:
        """Log webhook processing event"""
        try:
            webhook_data = {
                'event_id': event_id,
                'event_type': event_type,
                'processed': processed,
                'user_id': user_id,
                'stripe_subscription_id': stripe_subscription_id,
                'error_message': error_message,
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.table('webhook_events').insert(webhook_data).execute()
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error logging webhook event: {e}")
            return False