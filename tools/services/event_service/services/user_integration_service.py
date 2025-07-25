"""
User Integration Service
Handles integration between event_service and user_service
Ensures foreign key constraints and user validation
"""

import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from core.logging import get_logger

class UserIntegrationService:
    """Service for handling user-related operations and validation"""
    
    def __init__(self, user_service_url: str = "http://localhost:8100"):
        self.user_service_url = user_service_url
        self.logger = get_logger(self.__class__.__name__)
    
    async def validate_user_exists(self, user_id: str) -> bool:
        """Validate that user exists in user_service before creating tasks/events"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.user_service_url}/api/v1/users/{user_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        self.logger.debug(f"User {user_id} validated successfully")
                        return True
                    elif response.status == 404:
                        self.logger.warning(f"User {user_id} not found")
                        return False
                    else:
                        self.logger.error(f"User validation failed with status {response.status}")
                        return False
                        
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error validating user {user_id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error validating user {user_id}: {e}")
            return False
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from user_service"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.user_service_url}/api/v1/users/{user_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        return user_data.get('data')
                    else:
                        return None
                        
        except Exception as e:
            self.logger.error(f"Failed to get user info for {user_id}: {e}")
            return None
    
    async def validate_user_permissions(self, user_id: str, operation: str) -> bool:
        """Validate user permissions for specific operations"""
        try:
            user_info = await self.get_user_info(user_id)
            if not user_info:
                return False
            
            # Check if user is active
            if not user_info.get('is_active', False):
                self.logger.warning(f"User {user_id} is not active")
                return False
            
            # Check subscription status for premium features
            subscription_status = user_info.get('subscription_status', 'free')
            
            if operation in ['web_monitor', 'news_digest'] and subscription_status == 'free':
                # Free users might have limitations
                self.logger.info(f"User {user_id} has free subscription for operation {operation}")
                # Could add specific free tier limitations here
            
            return True
            
        except Exception as e:
            self.logger.error(f"Permission validation failed for user {user_id}: {e}")
            return False
    
    async def check_user_credits(self, user_id: str, required_credits: float = 0.0) -> bool:
        """Check if user has sufficient credits for operation"""
        try:
            user_info = await self.get_user_info(user_id)
            if not user_info:
                return False
            
            credits_remaining = float(user_info.get('credits_remaining', 0))
            
            if credits_remaining >= required_credits:
                return True
            else:
                self.logger.warning(f"User {user_id} has insufficient credits: {credits_remaining} < {required_credits}")
                return False
                
        except Exception as e:
            self.logger.error(f"Credit check failed for user {user_id}: {e}")
            return False
    
    async def record_usage(self, user_id: str, task_type: str, metadata: Dict[str, Any]) -> bool:
        """Record usage in user_service for billing/analytics"""
        try:
            usage_data = {
                "model_name": f"event_service_{task_type}",
                "input_tokens": metadata.get('input_size', 0),
                "output_tokens": metadata.get('output_size', 0),
                "cost": metadata.get('cost', 0.0),
                "request_metadata": {
                    "task_type": task_type,
                    "event_service": True,
                    **metadata
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.user_service_url}/api/v1/users/{user_id}/usage",
                    json=usage_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 201:
                        self.logger.info(f"Usage recorded for user {user_id}")
                        return True
                    else:
                        self.logger.error(f"Failed to record usage: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to record usage for user {user_id}: {e}")
            return False
    
    def get_integration_health(self) -> Dict[str, Any]:
        """Get health status of user service integration"""
        return {
            "user_service_url": self.user_service_url,
            "last_check": datetime.now().isoformat(),
            "status": "configured"
        }