"""
Event Database Service

Integrates event sourcing service with Supabase database
Creates and manages event tables for task and feedback storage
"""

import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import logging
import json

logger = logging.getLogger(__name__)

class EventDatabaseService:
    """Database service for event operations using Supabase"""
    
    def __init__(self):
        """Initialize Supabase connection and ensure tables exist"""
        load_dotenv()
        
        self.supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        # Get schema from environment (defaults to 'public')
        self.schema = os.getenv('DB_SCHEMA', 'public')
        logger.info(f"EventDatabaseService initialized with Supabase using schema: {self.schema}")
        
        # Check if event tables exist
        self._check_event_tables()
    
    def table(self, table_name: str):
        """Get a table with the configured schema"""
        return self.client.schema(self.schema).table(table_name)
    
    def _check_event_tables(self):
        """Check if event tables exist in database"""
        required_tables = ['events', 'background_tasks']
        
        for table_name in required_tables:
            try:
                self.table(table_name).select('*').limit(1).execute()
                logger.info(f"Event table '{table_name}' exists in schema '{self.schema}'")
            except Exception as e:
                if 'does not exist' in str(e):
                    logger.warning(f"Event table '{table_name}' does not exist")
                    self._log_required_schema(table_name)
                else:
                    logger.error(f"Error checking table '{table_name}': {e}")
    
    def _log_required_schema(self, table_name: str):
        """Log the required schema for missing tables"""
        if table_name == 'events':
            logger.info("Required schema for 'events' table:")
            logger.info("""
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_id UUID DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    source VARCHAR(100) DEFAULT 'event_sourcing_service',
    priority INTEGER DEFAULT 1,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    agent_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_events_task_id ON events(task_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_processed ON events(processed);
CREATE INDEX idx_events_created_at ON events(created_at);
            """)
        
        elif table_name == 'background_tasks':
            logger.info("Required schema for 'background_tasks' table:")
            logger.info("""
CREATE TABLE background_tasks (
    id SERIAL PRIMARY KEY,
    task_id UUID DEFAULT uuid_generate_v4(),
    task_type VARCHAR(100) NOT NULL,
    description TEXT,
    config JSONB,
    callback_url VARCHAR(500),
    user_id VARCHAR(255) DEFAULT 'default',
    status VARCHAR(50) DEFAULT 'active',
    last_check TIMESTAMP WITH TIME ZONE,
    next_check TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_background_tasks_user_id ON background_tasks(user_id);
CREATE INDEX idx_background_tasks_status ON background_tasks(status);
CREATE INDEX idx_background_tasks_type ON background_tasks(task_type);
CREATE INDEX idx_background_tasks_created_at ON background_tasks(created_at);
            """)
    
    # Background Tasks Operations
    async def store_background_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Store background task in database"""
        try:
            task_record = {
                'task_id': task_data.get('task_id', str(uuid.uuid4())),
                'task_type': task_data.get('task_type'),
                'description': task_data.get('description'),
                'config': task_data.get('config', {}),
                'callback_url': task_data.get('callback_url'),
                'user_id': task_data.get('user_id', 'default'),
                'status': task_data.get('status', 'active'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            result = self.table('background_tasks').insert(task_record).execute()
            
            if result.data:
                task_id = result.data[0]['task_id']
                logger.info(f"Background task stored with ID: {task_id}")
                return task_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error storing background task: {e}")
            if 'does not exist' in str(e):
                logger.error("Please create the background_tasks table first")
            return None
    
    async def get_background_tasks(self, user_id: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Get background tasks from database"""
        try:
            query = self.table('background_tasks').select('*')
            
            if user_id:
                query = query.eq('user_id', user_id)
            if status:
                query = query.eq('status', status)
            
            result = query.order('created_at', desc=True).execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting background tasks: {e}")
            return []
    
    async def update_background_task_status(self, task_id: str, status: str, 
                                          last_check: Optional[str] = None) -> bool:
        """Update background task status"""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if last_check:
                update_data['last_check'] = last_check
            
            result = self.table('background_tasks')\
                .update(update_data)\
                .eq('task_id', task_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating background task status: {e}")
            return False
    
    async def delete_background_task(self, task_id: str) -> bool:
        """Delete background task from database"""
        try:
            result = self.table('background_tasks')\
                .delete()\
                .eq('task_id', task_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error deleting background task: {e}")
            return False
    
    # Event Operations
    async def store_event(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Store event in database"""
        try:
            event_id = str(uuid.uuid4())
            
            event_record = {
                'event_id': event_id,
                'task_id': event_data.get('task_id'),
                'event_type': event_data.get('event_type', 'unknown'),
                'event_data': event_data.get('data', event_data),
                'source': event_data.get('source', 'event_sourcing_service'),
                'priority': event_data.get('priority', 1),
                'processed': False,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            result = self.table('events').insert(event_record).execute()
            
            if result.data:
                logger.info(f"Event stored with ID: {event_id}")
                return event_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error storing event: {e}")
            if 'does not exist' in str(e):
                logger.error("Please create the events table first")
            return None
    
    async def update_event_processed(self, event_id: str, 
                                   agent_response: Optional[Dict[str, Any]] = None) -> bool:
        """Mark event as processed and store agent response"""
        try:
            update_data = {
                'processed': True,
                'processed_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if agent_response:
                update_data['agent_response'] = agent_response
            
            result = self.table('events')\
                .update(update_data)\
                .eq('event_id', event_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating event processed status: {e}")
            return False
    
    async def get_recent_events(self, limit: int = 50, task_id: str = None) -> List[Dict[str, Any]]:
        """Get recent events from database"""
        try:
            query = self.table('events').select('*')
            
            if task_id:
                query = query.eq('task_id', task_id)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []
    
    async def get_events_by_type(self, event_type: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get events by specific type"""
        try:
            result = self.table('events')\
                .select('*')\
                .eq('event_type', event_type)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting events by type: {e}")
            return []
    
    async def get_unprocessed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get unprocessed events for agent processing"""
        try:
            result = self.table('events')\
                .select('*')\
                .eq('processed', False)\
                .order('created_at', desc=False)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting unprocessed events: {e}")
            return []
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get event processing statistics"""
        try:
            # Get total events count
            all_events = self.table('events').select('id, event_type, processed').execute()
            events_data = all_events.data if all_events.data else []
            
            total_events = len(events_data)
            processed_events = len([e for e in events_data if e.get('processed', False)])
            unprocessed_events = total_events - processed_events
            
            # Get event types distribution
            event_types = {}
            for event in events_data:
                event_type = event.get('event_type', 'unknown')
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # Get background tasks stats
            tasks_result = self.table('background_tasks').select('status, task_type').execute()
            tasks_data = tasks_result.data if tasks_result.data else []
            
            task_statuses = {}
            task_types = {}
            for task in tasks_data:
                status = task.get('status', 'unknown')
                task_type = task.get('task_type', 'unknown')
                task_statuses[status] = task_statuses.get(status, 0) + 1
                task_types[task_type] = task_types.get(task_type, 0) + 1
            
            return {
                'events': {
                    'total': total_events,
                    'processed': processed_events,
                    'unprocessed': unprocessed_events,
                    'types': event_types
                },
                'background_tasks': {
                    'total': len(tasks_data),
                    'statuses': task_statuses,
                    'types': task_types
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting event statistics: {e}")
            return {
                'events': {'total': 0, 'processed': 0, 'unprocessed': 0, 'types': {}},
                'background_tasks': {'total': 0, 'statuses': {}, 'types': {}},
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def cleanup_old_events(self, days_to_keep: int = 30) -> int:
        """Clean up events older than specified days"""
        try:
            from datetime import timedelta
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            result = self.table('events')\
                .delete()\
                .lt('created_at', cutoff_date)\
                .execute()
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"Cleaned up {deleted_count} old events")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")
            return 0