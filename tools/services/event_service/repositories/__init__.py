"""
Event Service Repositories Package
Professional data access layer following Repository pattern
"""

from .base_repository import BaseEventRepository as BaseRepository
from .event_repository import EventRepository  
from .task_repository import TaskRepository

__all__ = [
    "BaseRepository",
    "EventRepository", 
    "TaskRepository"
]