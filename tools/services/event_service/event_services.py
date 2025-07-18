#!/usr/bin/env python
"""
Event Sourcing Services
Core business logic for background task management and event monitoring
"""
import asyncio
import json
import hashlib
import uuid
import aiohttp
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class EventSourceTaskType(Enum):
    WEB_MONITOR = "web_monitor"
    SCHEDULE = "schedule"
    NEWS_DIGEST = "news_digest"
    THRESHOLD_WATCH = "threshold_watch"

@dataclass
class EventSourceTask:
    """Background task managed by event sourcing system"""
    task_id: str
    task_type: EventSourceTaskType
    description: str
    config: Dict[str, Any]
    callback_url: str
    created_at: datetime
    status: str = "active"  # active, paused, completed, failed
    last_check: Optional[datetime] = None
    next_check: Optional[datetime] = None
    user_id: str = "default"

@dataclass
class EventFeedback:
    """Event feedback sent back to agent"""
    task_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    priority: int = 1  # 1=low, 5=critical
    requires_processing: bool = True

class EventSourcingService:
    """Independent event sourcing service for background tasks"""
    
    def __init__(self):
        self.tasks: Dict[str, EventSourceTask] = {}
        self.running_monitors: Dict[str, asyncio.Task] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.last_content_hashes: Dict[str, str] = {}
        self._service_task: Optional[asyncio.Task] = None
        
    async def start_service(self):
        """Start the event sourcing service"""
        if not self.running:
            self.running = True
            self._service_task = asyncio.create_task(self._service_loop())
            logger.info("🔄 Event Sourcing Service started")
    
    async def stop_service(self):
        """Stop the event sourcing service"""
        self.running = False
        
        # Cancel service loop
        if self._service_task:
            self._service_task.cancel()
        
        # Cancel all running monitors
        for task in self.running_monitors.values():
            task.cancel()
        self.running_monitors.clear()
        
        self.executor.shutdown(wait=False)
        logger.info("⏹️ Event Sourcing Service stopped")
    
    async def create_task(
        self,
        task_type: EventSourceTaskType,
        description: str,
        config: Dict[str, Any],
        callback_url: str,
        user_id: str = "default"
    ) -> EventSourceTask:
        """Create a new background task"""
        
        task = EventSourceTask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            description=description,
            config=config,
            callback_url=callback_url,
            created_at=datetime.now(),
            user_id=user_id
        )
        
        # Register task
        self.tasks[task.task_id] = task
        
        # Start monitoring for this task
        await self._start_monitor(task)
        
        logger.info(f"📝 Created background task: {task.description}")
        return task
    
    async def list_tasks(self, user_id: str = "default") -> List[EventSourceTask]:
        """List tasks for a user"""
        if user_id == "admin":
            return list(self.tasks.values())
        return [task for task in self.tasks.values() if task.user_id == user_id]
    
    async def pause_task(self, task_id: str, user_id: str = "default") -> bool:
        """Pause a background task"""
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        if task.user_id != user_id and user_id != "admin":
            return False
            
        task.status = "paused"
        if task_id in self.running_monitors:
            self.running_monitors[task_id].cancel()
            del self.running_monitors[task_id]
        
        logger.info(f"⏸️ Paused task: {task.description}")
        return True
    
    async def resume_task(self, task_id: str, user_id: str = "default") -> bool:
        """Resume a paused task"""
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        if task.user_id != user_id and user_id != "admin":
            return False
            
        task.status = "active"
        await self._start_monitor(task)
        
        logger.info(f"▶️ Resumed task: {task.description}")
        return True
    
    async def delete_task(self, task_id: str, user_id: str = "default") -> bool:
        """Delete a background task"""
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        if task.user_id != user_id and user_id != "admin":
            return False
        
        # Cancel monitoring
        if task_id in self.running_monitors:
            self.running_monitors[task_id].cancel()
            del self.running_monitors[task_id]
        
        # Remove task
        del self.tasks[task_id]
        
        logger.info(f"🗑️ Deleted task: {task.description}")
        return True
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status"""
        tasks = list(self.tasks.values())
        active_tasks = [t for t in tasks if t.status == "active"]
        paused_tasks = [t for t in tasks if t.status == "paused"]
        
        return {
            "service_running": self.running,
            "total_tasks": len(tasks),
            "active_tasks": len(active_tasks),
            "paused_tasks": len(paused_tasks),
            "running_monitors": len(self.running_monitors),
            "task_types": {
                "web_monitor": len([t for t in tasks if t.task_type == EventSourceTaskType.WEB_MONITOR]),
                "schedule": len([t for t in tasks if t.task_type == EventSourceTaskType.SCHEDULE]),
                "news_digest": len([t for t in tasks if t.task_type == EventSourceTaskType.NEWS_DIGEST]),
                "threshold_watch": len([t for t in tasks if t.task_type == EventSourceTaskType.THRESHOLD_WATCH])
            }
        }
    
    async def _start_monitor(self, task: EventSourceTask):
        """Start monitoring for a task"""
        if task.status != "active":
            return
            
        if task.task_type == EventSourceTaskType.WEB_MONITOR:
            monitor_task = asyncio.create_task(self._web_monitor(task))
            self.running_monitors[task.task_id] = monitor_task
        elif task.task_type == EventSourceTaskType.SCHEDULE:
            monitor_task = asyncio.create_task(self._schedule_monitor(task))
            self.running_monitors[task.task_id] = monitor_task
        elif task.task_type == EventSourceTaskType.NEWS_DIGEST:
            monitor_task = asyncio.create_task(self._news_digest_monitor(task))
            self.running_monitors[task.task_id] = monitor_task
    
    async def _service_loop(self):
        """Main service loop for health checks"""
        while self.running:
            try:
                # Health check on monitors
                dead_monitors = []
                for task_id, monitor in self.running_monitors.items():
                    if monitor.done():
                        dead_monitors.append(task_id)
                
                # Restart dead monitors
                for task_id in dead_monitors:
                    if task_id in self.tasks and self.tasks[task_id].status == "active":
                        task = self.tasks[task_id]
                        logger.info(f"🔄 Restarting monitor for task: {task.description}")
                        await self._start_monitor(task)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Service loop error: {e}")
                await asyncio.sleep(60)
    
    async def _web_monitor(self, task: EventSourceTask):
        """Monitor web sources for changes"""
        config = task.config
        urls = config.get("urls", [])
        keywords = config.get("keywords", [])
        check_interval = config.get("check_interval_minutes", 30)
        
        while self.running and task.status == "active":
            try:
                for url in urls:
                    content = await self._scrape_web_content(url)
                    
                    if content:
                        # Check if content contains keywords
                        content_lower = content.lower()
                        matching_keywords = [kw for kw in keywords if kw.lower() in content_lower]
                        
                        if matching_keywords:
                            # Check if content changed
                            content_hash = hashlib.md5(content.encode()).hexdigest()
                            last_hash = self.last_content_hashes.get(url, "")
                            
                            if content_hash != last_hash:
                                # Content changed! Send feedback to agent
                                feedback = EventFeedback(
                                    task_id=task.task_id,
                                    event_type="web_content_change",
                                    data={
                                        "url": url,
                                        "content": content[:2000],  # Truncate for feedback
                                        "keywords_found": matching_keywords,
                                        "description": task.description,
                                        "user_id": task.user_id
                                    },
                                    timestamp=datetime.now(),
                                    priority=3
                                )
                                
                                await self._send_feedback(feedback, task.callback_url)
                                self.last_content_hashes[url] = content_hash
                
                task.last_check = datetime.now()
                await asyncio.sleep(check_interval * 60)
                
            except Exception as e:
                logger.error(f"Web monitor error for task {task.task_id}: {e}")
                await asyncio.sleep(60)
    
    async def _schedule_monitor(self, task: EventSourceTask):
        """Monitor for scheduled events"""
        config = task.config
        schedule_type = config.get("type")  # daily, interval, etc.
        
        while self.running and task.status == "active":
            try:
                should_trigger = False
                current_time = datetime.now()
                
                if schedule_type == "daily":
                    target_hour = config.get("hour", 8)
                    target_minute = config.get("minute", 0)
                    
                    if (current_time.hour == target_hour and 
                        current_time.minute == target_minute and
                        (not task.last_check or task.last_check.date() < current_time.date())):
                        should_trigger = True
                
                elif schedule_type == "interval":
                    interval_minutes = config.get("minutes", 60)
                    if (not task.last_check or 
                        (current_time - task.last_check).seconds >= interval_minutes * 60):
                        should_trigger = True
                
                if should_trigger:
                    feedback = EventFeedback(
                        task_id=task.task_id,
                        event_type="scheduled_trigger",
                        data={
                            "trigger_time": current_time.isoformat(),
                            "schedule_config": config,
                            "description": task.description,
                            "user_id": task.user_id
                        },
                        timestamp=current_time,
                        priority=2
                    )
                    
                    await self._send_feedback(feedback, task.callback_url)
                    task.last_check = current_time
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Schedule monitor error for task {task.task_id}: {e}")
                await asyncio.sleep(60)
    
    async def _news_digest_monitor(self, task: EventSourceTask):
        """Monitor for daily news digest"""
        config = task.config
        news_urls = config.get("news_urls", ["https://techcrunch.com", "https://news.ycombinator.com"])
        digest_hour = config.get("hour", 8)
        
        while self.running and task.status == "active":
            try:
                current_time = datetime.now()
                
                # Check if it's time for daily digest
                if (current_time.hour == digest_hour and 
                    current_time.minute < 5 and  # 5-minute window
                    (not task.last_check or task.last_check.date() < current_time.date())):
                    
                    # Scrape news from all URLs
                    news_summaries = []
                    for url in news_urls:
                        content = await self._scrape_web_content(url)
                        if content:
                            # Extract headlines (simplified)
                            headlines = self._extract_headlines(content)
                            news_summaries.append({
                                "source": url,
                                "headlines": headlines[:10]  # Top 10 headlines
                            })
                    
                    if news_summaries:
                        feedback = EventFeedback(
                            task_id=task.task_id,
                            event_type="daily_news_digest",
                            data={
                                "digest_date": current_time.date().isoformat(),
                                "news_summaries": news_summaries,
                                "description": task.description,
                                "user_id": task.user_id
                            },
                            timestamp=current_time,
                            priority=2
                        )
                        
                        await self._send_feedback(feedback, task.callback_url)
                        task.last_check = current_time
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"News digest monitor error for task {task.task_id}: {e}")
                await asyncio.sleep(300)
    
    async def _scrape_web_content(self, url: str) -> Optional[str]:
        """Scrape web content"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content[:5000]  # Limit content size
            return None
        except Exception as e:
            logger.error(f"Web scraping error for {url}: {e}")
            return None
    
    def _extract_headlines(self, content: str) -> List[str]:
        """Extract headlines from web content (simplified)"""
        lines = content.split('\n')
        headlines = []
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200 and not line.startswith('<'):
                headlines.append(line)
                if len(headlines) >= 20:
                    break
        return headlines
    
    async def _send_feedback(self, feedback: EventFeedback, callback_url: str):
        """Send feedback back to the agent via HTTP callback"""
        try:
            feedback_data = {
                "task_id": feedback.task_id,
                "event_type": feedback.event_type,
                "data": feedback.data,
                "timestamp": feedback.timestamp.isoformat(),
                "priority": feedback.priority
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    callback_url,
                    json=feedback_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"📤 Sent feedback to agent: {feedback.event_type}")
                    else:
                        logger.error(f"Failed to send feedback, status: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send feedback: {e}")

# Global service instance
_event_sourcing_service: Optional[EventSourcingService] = None

def get_event_sourcing_service() -> EventSourcingService:
    """Get the global event sourcing service instance"""
    global _event_sourcing_service
    if _event_sourcing_service is None:
        _event_sourcing_service = EventSourcingService()
    return _event_sourcing_service

async def init_event_sourcing_service():
    """Initialize the event sourcing service"""
    service = get_event_sourcing_service()
    await service.start_service()
    return service
