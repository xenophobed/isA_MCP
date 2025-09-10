"""
Event Service
Core business logic for event operations
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..repositories.event_repository import EventRepository
from .user_service import UserService
from .base import BaseService, ServiceResult, ServiceStatus
from core.logging import get_logger

class EventService:
    """Core service for event operations with business logic"""
    
    def __init__(self):
        self.event_repo = EventRepository()
        self.user_service = UserService()
        self.logger = get_logger(self.__class__.__name__)
    
    async def create_event(self, event_data: Dict[str, Any]) -> ServiceResult:
        """Create new event with validation and business logic"""
        try:
            # Validate required fields
            if not event_data.get('event_type'):
                return ServiceResult(
                    status=ServiceStatus.VALIDATION_ERROR,
                    message="event_type is required",
                    data=None
                )
            
            # Validate user if user_id provided
            user_id = event_data.get('user_id')
            if user_id:
                user_result = await self.user_service.get_user_by_id(user_id)
                if user_result.status != ServiceStatus.SUCCESS:
                    return ServiceResult(
                        status=ServiceStatus.ERROR,
                        message=f"User {user_id} not found",
                        data=None
                    )
            
            # Create event in repository
            event_id = await self.event_repo.append_event(event_data)
            
            if event_id:
                self.logger.info(f"Event created successfully: {event_id}")
                return ServiceResult(
                    status=ServiceStatus.SUCCESS,
                    data={
                        "event_id": event_id,
                        "message": "Event created successfully"
                    }
                )
            else:
                return ServiceResult(
                    status=ServiceStatus.ERROR,
                    message="Failed to create event in database",
                    data=None
                )
                
        except Exception as e:
            self.logger.error(f"Failed to create event: {e}")
            return ServiceResult(
                status=ServiceStatus.ERROR,
                message=str(e),
                data=None
            )
    
    async def get_event_stream(self, stream_id: str, from_version: Optional[int] = None) -> ServiceResult:
        """Get event stream for replay/projection"""
        try:
            events = await self.event_repo.get_event_stream(stream_id, from_version)
            
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                
                data={
                    "events": events,
                    "stream_id": stream_id,
                    "event_count": len(events)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get event stream {stream_id}: {e}")
            return ServiceResult(
                status=ServiceStatus.ERROR,
                message=str(e),
                data={
                    "events": [],
                    "stream_id": stream_id,
                    "event_count": 0
                }
            )
    
    async def process_event(self, event_id: str, agent_response: Optional[Dict[str, Any]] = None) -> ServiceResult:
        """Mark event as processed with optional agent response"""
        try:
            success = await self.event_repo.mark_event_processed(event_id, agent_response)
            
            if success:
                return ServiceResult(
                    status=ServiceStatus.SUCCESS,
                    
                    data={"message": f"Event {event_id} marked as processed"}
                )
            else:
                return ServiceResult(
                    status=ServiceStatus.ERROR,
                    message="Failed to update event status",
                    data=None
                )
                
        except Exception as e:
            self.logger.error(f"Failed to process event {event_id}: {e}")
            return ServiceResult(
                status=ServiceStatus.ERROR,
                message=str(e),
                data=None
            )
    
    async def get_recent_events(self, limit: int = 50, task_id: Optional[str] = None) -> ServiceResult:
        """Get recent events with business logic"""
        try:
            events = await self.event_repo.get_recent_events(limit, task_id)
            
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                
                data={
                    "events": events,
                    "count": len(events),
                    "limit": limit
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get recent events: {e}")
            return ServiceResult(
                status=ServiceStatus.ERROR,
                message=str(e),
                data={
                    "events": [],
                    "count": 0,
                    "limit": limit
                }
            )
    
    async def get_events_by_type(self, event_type: str, limit: int = 20) -> ServiceResult:
        """Get events by specific type"""
        try:
            events = await self.event_repo.get_events_by_type(event_type, limit)
            
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                
                data={
                    "events": events,
                    "event_type": event_type,
                    "count": len(events)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get events by type {event_type}: {e}")
            return ServiceResult(
                status=ServiceStatus.ERROR,
                message=str(e),
                data={
                    "events": [],
                    "event_type": event_type,
                    "count": 0
                }
            )
    
    async def get_unprocessed_events(self, limit: int = 100) -> ServiceResult:
        """Get unprocessed events for agent processing"""
        try:
            events = await self.event_repo.get_unprocessed_events(limit)
            
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                
                data={
                    "events": events,
                    "count": len(events),
                    "processing_required": len(events) > 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get unprocessed events: {e}")
            return ServiceResult(
                status=ServiceStatus.ERROR,
                message=str(e),
                data={
                    "events": [],
                    "count": 0,
                    "processing_required": False
                }
            )
    
    async def get_event_statistics(self) -> ServiceResult:
        """Get comprehensive event statistics"""
        try:
            stats = await self.event_repo.get_event_statistics()
            
            # Add business intelligence
            if stats.get('total_events', 0) > 0:
                stats['system_health'] = 'healthy' if stats.get('processing_rate', 0) > 80 else 'degraded'
            else:
                stats['system_health'] = 'initializing'
            
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                
                data={"statistics": stats}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get event statistics: {e}")
            return ServiceResult(
                status=ServiceStatus.ERROR,
                message=str(e),
                data={"statistics": {}}
            )
    
    async def process_background_feedback(self, feedback_data: Dict[str, Any]) -> ServiceResult:
        """Process background task feedback and create event"""
        try:
            event_type = feedback_data.get("event_type", "task_feedback")
            task_id = feedback_data.get("task_id")
            
            # Add metadata
            feedback_data["received_at"] = datetime.now().isoformat()
            feedback_data["source"] = "background_task_service"
            
            # Create event
            event_result = await self.create_event(feedback_data)
            
            if event_result.status == ServiceStatus.SUCCESS:
                return ServiceResult(
                    status=ServiceStatus.SUCCESS,
                    
                    data={
                        "status": "processed",
                        "message": "Background feedback processed successfully",
                        "event_id": event_result.data.get("event_id")
                    }
                )
            else:
                return ServiceResult(
                    status=ServiceStatus.ERROR,
                    message=event_result.message,
                    data={
                        "status": "failed",
                        "message": "Failed to process background feedback"
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Failed to process background feedback: {e}")
            return ServiceResult(
                status=ServiceStatus.ERROR,
                message=str(e),
                data={
                    "status": "failed", 
                    "message": "Internal error processing feedback"
                }
            )