"""
Event Service
Core business logic for event operations
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..repositories.event_repository import EventRepository
from .user_integration_service import UserIntegrationService
from core.logging import get_logger

class EventService:
    """Core service for event operations with business logic"""
    
    def __init__(self):
        self.event_repo = EventRepository()
        self.user_integration = UserIntegrationService()
        self.logger = get_logger(self.__class__.__name__)
    
    async def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new event with validation and business logic"""
        try:
            # Validate required fields
            if not event_data.get('event_type'):
                return {
                    "success": False,
                    "error": "event_type is required",
                    "event_id": None
                }
            
            # Validate user if user_id provided
            user_id = event_data.get('user_id')
            if user_id:
                user_exists = await self.user_integration.validate_user_exists(user_id)
                if not user_exists:
                    return {
                        "success": False,
                        "error": f"User {user_id} not found",
                        "event_id": None
                    }
            
            # Create event in repository
            event_id = await self.event_repo.append_event(event_data)
            
            if event_id:
                self.logger.info(f"Event created successfully: {event_id}")
                return {
                    "success": True,
                    "error": None,
                    "event_id": event_id,
                    "message": "Event created successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create event in database",
                    "event_id": None
                }
                
        except Exception as e:
            self.logger.error(f"Failed to create event: {e}")
            return {
                "success": False,
                "error": str(e),
                "event_id": None
            }
    
    async def get_event_stream(self, stream_id: str, from_version: Optional[int] = None) -> Dict[str, Any]:
        """Get event stream for replay/projection"""
        try:
            events = await self.event_repo.get_event_stream(stream_id, from_version)
            
            return {
                "success": True,
                "error": None,
                "events": events,
                "stream_id": stream_id,
                "event_count": len(events)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get event stream {stream_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "events": [],
                "stream_id": stream_id,
                "event_count": 0
            }
    
    async def process_event(self, event_id: str, agent_response: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mark event as processed with optional agent response"""
        try:
            success = await self.event_repo.mark_event_processed(event_id, agent_response)
            
            if success:
                return {
                    "success": True,
                    "error": None,
                    "message": f"Event {event_id} marked as processed"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update event status",
                    "message": None
                }
                
        except Exception as e:
            self.logger.error(f"Failed to process event {event_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": None
            }
    
    async def get_recent_events(self, limit: int = 50, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get recent events with business logic"""
        try:
            events = await self.event_repo.get_recent_events(limit, task_id)
            
            return {
                "success": True,
                "error": None,
                "events": events,
                "count": len(events),
                "limit": limit
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get recent events: {e}")
            return {
                "success": False,
                "error": str(e),
                "events": [],
                "count": 0,
                "limit": limit
            }
    
    async def get_events_by_type(self, event_type: str, limit: int = 20) -> Dict[str, Any]:
        """Get events by specific type"""
        try:
            events = await self.event_repo.get_events_by_type(event_type, limit)
            
            return {
                "success": True,
                "error": None,
                "events": events,
                "event_type": event_type,
                "count": len(events)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get events by type {event_type}: {e}")
            return {
                "success": False,
                "error": str(e),
                "events": [],
                "event_type": event_type,
                "count": 0
            }
    
    async def get_unprocessed_events(self, limit: int = 100) -> Dict[str, Any]:
        """Get unprocessed events for agent processing"""
        try:
            events = await self.event_repo.get_unprocessed_events(limit)
            
            return {
                "success": True,
                "error": None,
                "events": events,
                "count": len(events),
                "processing_required": len(events) > 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get unprocessed events: {e}")
            return {
                "success": False,
                "error": str(e),
                "events": [],
                "count": 0,
                "processing_required": False
            }
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get comprehensive event statistics"""
        try:
            stats = await self.event_repo.get_event_statistics()
            
            # Add business intelligence
            if stats.get('total_events', 0) > 0:
                stats['system_health'] = 'healthy' if stats.get('processing_rate', 0) > 80 else 'degraded'
            else:
                stats['system_health'] = 'initializing'
            
            return {
                "success": True,
                "error": None,
                "statistics": stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get event statistics: {e}")
            return {
                "success": False,
                "error": str(e),
                "statistics": {}
            }