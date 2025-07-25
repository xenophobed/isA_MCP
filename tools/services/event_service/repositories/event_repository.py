"""
Event Repository
Professional event data access layer for event sourcing
Based on actual database schema: dev.events table
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_repository import BaseEventRepository

class EventRepository(BaseEventRepository):
    """Repository for event operations following event sourcing patterns"""
    
    async def append_event(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Append event to event stream (core Event Sourcing operation)"""
        try:
            # Use UUID for event_id (matches database schema)
            event_id = uuid.uuid4()
            
            # Map to actual database columns
            event_record = {
                'event_id': event_id,
                'task_id': event_data.get('task_id'),  # UUID foreign key to user_tasks
                'user_id': event_data.get('user_id'),  # VARCHAR foreign key to users  
                'event_type': event_data.get('event_type', 'unknown'),  # VARCHAR(100) NOT NULL
                'event_data': event_data.get('data', event_data),  # JSONB
                'source': event_data.get('source', 'event_sourcing_service'),  # VARCHAR(100)
                'priority': event_data.get('priority', 1),  # INTEGER default 1
                'processed': False,  # BOOLEAN default false
                # created_at and updated_at are set by database defaults
            }
            
            result = self.db.table('events').insert(event_record).execute()
            
            if result.data:
                self.logger.info(f"Event appended to stream: {event_id}")
                return str(event_id)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to append event: {e}")
            return None
    
    async def get_event_stream(self, stream_id: str, from_version: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get event stream for replay/projection"""
        try:
            query = self.db.table('events').select('*').eq('task_id', stream_id)
            
            if from_version:
                # Use created_at as version proxy since we don't have explicit versioning
                query = query.gte('created_at', from_version)
            
            result = query.order('created_at').execute()
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Failed to get event stream {stream_id}: {e}")
            return []
    
    async def get_recent_events(self, limit: int = 50, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent events for monitoring"""
        try:
            query = self.db.table('events').select('*')
            
            if task_id:
                query = query.eq('task_id', task_id)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Failed to get recent events: {e}")
            return []
    
    async def get_events_by_type(self, event_type: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get events by specific type"""
        try:
            result = self.db.table('events')\
                .select('*')\
                .eq('event_type', event_type)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Failed to get events by type {event_type}: {e}")
            return []
    
    async def get_unprocessed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get unprocessed events for agent processing"""
        try:
            result = self.db.table('events')\
                .select('*')\
                .eq('processed', False)\
                .order('created_at')\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Failed to get unprocessed events: {e}")
            return []
    
    async def mark_event_processed(self, event_id: str, 
                                 agent_response: Optional[Dict[str, Any]] = None) -> bool:
        """Mark event as processed with agent response"""
        try:
            update_data = {
                'processed': True,
                'processed_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if agent_response:
                update_data['agent_response'] = agent_response
            
            result = self.db.table('events')\
                .update(update_data)\
                .eq('event_id', event_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to mark event {event_id} as processed: {e}")
            return False
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get comprehensive event statistics"""
        try:
            # Get all events for analysis
            all_events = self.db.table('events').select('event_type, processed').execute()
            events_data = all_events.data if all_events.data else []
            
            total_events = len(events_data)
            processed_events = len([e for e in events_data if e.get('processed', False)])
            unprocessed_events = total_events - processed_events
            
            # Event types distribution
            event_types = {}
            for event in events_data:
                event_type = event.get('event_type', 'unknown')
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            return {
                'total_events': total_events,
                'processed_events': processed_events,
                'unprocessed_events': unprocessed_events,
                'event_types': event_types,
                'processing_rate': round(processed_events / total_events * 100, 2) if total_events > 0 else 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get event statistics: {e}")
            return {
                'total_events': 0,
                'processed_events': 0,
                'unprocessed_events': 0,
                'event_types': {},
                'processing_rate': 0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }