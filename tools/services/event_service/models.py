"""
Event Service Data Models
Professional data models with validation using Pydantic
"""

from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class TaskStatus(Enum):
    """Task status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class EventSourceTaskType(Enum):
    """Event source task types"""
    WEB_MONITOR = "web_monitor"
    SCHEDULE = "schedule"
    NEWS_DIGEST = "news_digest"
    THRESHOLD_WATCH = "threshold_watch"

class Event(BaseModel):
    """Event data model"""
    event_id: Optional[UUID4] = None
    task_id: Optional[UUID4] = None
    user_id: Optional[str] = Field(None, max_length=255)
    event_type: str = Field(..., max_length=100, description="Event type")
    event_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    source: str = Field(default="event_sourcing_service", max_length=100)
    priority: int = Field(default=1, ge=1, le=5, description="Priority level (1-5)")
    processed: bool = Field(default=False)
    processed_at: Optional[datetime] = None
    agent_response: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class Task(BaseModel):
    """Background task data model"""
    task_id: Optional[UUID4] = None
    user_id: str = Field(..., max_length=255, description="User ID")
    task_type: str = Field(..., max_length=100, description="Task type")
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    callback_url: Optional[str] = Field(None, max_length=500)
    status: TaskStatus = Field(default=TaskStatus.ACTIVE)
    last_check: Optional[datetime] = None
    next_check: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class EventFeedback(BaseModel):
    """Event feedback data model"""
    task_id: str = Field(..., description="Task ID")
    event_type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: int = Field(default=1, ge=1, le=5)
    requires_processing: bool = Field(default=True)

class WebMonitorConfig(BaseModel):
    """Configuration for web monitoring tasks"""
    urls: List[str] = Field(..., min_items=1, description="URLs to monitor")
    keywords: List[str] = Field(..., min_items=1, description="Keywords to watch for")
    check_interval_minutes: int = Field(default=30, ge=1, le=1440, description="Check interval in minutes")

class ScheduleConfig(BaseModel):
    """Configuration for scheduled tasks"""
    type: str = Field(..., description="Schedule type (daily, interval)")
    hour: Optional[int] = Field(None, ge=0, le=23, description="Hour for daily schedule")
    minute: Optional[int] = Field(None, ge=0, le=59, description="Minute for daily schedule")
    minutes: Optional[int] = Field(None, ge=1, description="Interval in minutes")

class NewsDigestConfig(BaseModel):
    """Configuration for news digest tasks"""
    news_urls: List[str] = Field(default_factory=lambda: ["https://techcrunch.com", "https://news.ycombinator.com"])
    hour: int = Field(default=8, ge=0, le=23, description="Hour for daily digest")

class ServiceResult(BaseModel):
    """Standard service response model"""
    success: bool = Field(..., description="Operation success status")
    error: Optional[str] = Field(None, description="Error message if any")
    data: Optional[Any] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Human readable message")

class EventStatistics(BaseModel):
    """Event statistics model"""
    total_events: int = Field(default=0)
    processed_events: int = Field(default=0)
    unprocessed_events: int = Field(default=0)
    event_types: Dict[str, int] = Field(default_factory=dict)
    processing_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    system_health: str = Field(default="initializing")
    timestamp: datetime = Field(default_factory=datetime.now)

class TaskHealthMetrics(BaseModel):
    """Task health metrics model"""
    total_tasks: int = Field(default=0)
    status_distribution: Dict[str, int] = Field(default_factory=dict)
    task_types: Dict[str, int] = Field(default_factory=dict)
    health_score: float = Field(default=0.0, ge=0.0, le=100.0)
    overall_status: str = Field(default="initializing")
    timestamp: datetime = Field(default_factory=datetime.now)