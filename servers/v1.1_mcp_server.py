#!/usr/bin/env python
"""
Enhanced MCP Server with Authorization, Security, and Monitoring
Fixed imports for the actual MCP Python SDK
"""
import asyncio
import json
import sqlite3
import os
import hashlib
import time
import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Dict, List, Optional, Any, Union
import random
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps
import aiohttp
import uuid
from concurrent.futures import ThreadPoolExecutor

# Correct MCP imports
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ImageContent, EmbeddedResource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Custom Exception class since we can't import McpError
class McpError(Exception):
    """Custom MCP Error class"""
    def __init__(self, message: str, data: Optional[Dict] = None):
        super().__init__(message)
        self.data = data or {}

class SecurityLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class AuthorizationResult(Enum):
    APPROVED = "approved"
    DENIED = "denied"  
    PENDING = "pending"
    EXPIRED = "expired"

@dataclass
class AuthorizationRequest:
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    user_id: str
    timestamp: datetime
    security_level: SecurityLevel
    reason: str
    expires_at: datetime
    status: AuthorizationResult = AuthorizationResult.PENDING
    approved_by: Optional[str] = None
    
class SecurityPolicy:
    def __init__(self):
        self.tool_policies = {
            # High security tools require authorization
            "remember": SecurityLevel.MEDIUM,
            "forget": SecurityLevel.HIGH,
            "search_memories": SecurityLevel.LOW,
            "get_weather": SecurityLevel.LOW,
            "calculate": SecurityLevel.MEDIUM,
            "get_current_time": SecurityLevel.LOW,
            "analyze_sentiment": SecurityLevel.LOW,
        }
        
        self.forbidden_patterns = [
            r"password",
            r"secret",
            r"api_key",
            r"private_key",
            r"token",
            r"delete.*database",
            r"drop.*table"
        ]
        
        self.rate_limits = {
            "default": {"calls": 100, "window": 3600},  # 100 calls per hour
            "remember": {"calls": 50, "window": 3600},   # 50 calls per hour
            "forget": {"calls": 10, "window": 3600},     # 10 calls per hour
        }

class AuthorizationManager:
    def __init__(self):
        self.pending_requests: Dict[str, AuthorizationRequest] = {}
        self.approved_cache: Dict[str, datetime] = {}
        
    def create_request(self, tool_name: str, arguments: Dict, user_id: str, 
                      security_level: SecurityLevel, reason: str) -> AuthorizationRequest:
        """Create a new authorization request"""
        request_id = hashlib.md5(
            f"{tool_name}:{json.dumps(arguments, sort_keys=True)}:{user_id}:{time.time()}"
            .encode()
        ).hexdigest()
        
        request = AuthorizationRequest(
            id=request_id,
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
            timestamp=datetime.now(),
            security_level=security_level,
            reason=reason,
            expires_at=datetime.now() + timedelta(minutes=30)  # 30 min expiry
        )
        
        self.pending_requests[request_id] = request
        return request
    
    def approve_request(self, request_id: str, approved_by: str) -> bool:
        """Approve an authorization request"""
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            if datetime.now() < request.expires_at:
                request.status = AuthorizationResult.APPROVED
                request.approved_by = approved_by
                
                # Cache approval for similar requests
                cache_key = f"{request.tool_name}:{hashlib.md5(json.dumps(request.arguments, sort_keys=True).encode()).hexdigest()}"
                self.approved_cache[cache_key] = datetime.now() + timedelta(hours=1)
                
                return True
            else:
                request.status = AuthorizationResult.EXPIRED
        return False
    
    def deny_request(self, request_id: str) -> bool:
        """Deny an authorization request"""
        if request_id in self.pending_requests:
            self.pending_requests[request_id].status = AuthorizationResult.DENIED
            return True
        return False
    
    def is_pre_approved(self, tool_name: str, arguments: Dict) -> bool:
        """Check if similar request was recently approved"""
        cache_key = f"{tool_name}:{hashlib.md5(json.dumps(arguments, sort_keys=True).encode()).hexdigest()}"
        if cache_key in self.approved_cache:
            return datetime.now() < self.approved_cache[cache_key]
        return False

class MonitoringManager:
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "authorization_requests": 0,
            "denied_requests": 0,
            "security_violations": 0,
            "rate_limit_hits": 0
        }
        self.request_history = []
        self.rate_limiter = {}
        self.start_time = time.time()
    
    def log_request(self, tool_name: str, user_id: str, success: bool, 
                   execution_time: float, security_level: SecurityLevel):
        """Log a request for monitoring"""
        self.metrics["total_requests"] += 1
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
            
        request_log = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "user_id": user_id,
            "success": success,
            "execution_time": execution_time,
            "security_level": security_level.name
        }
        
        self.request_history.append(request_log)
        
        # Keep only last 1000 requests
        if len(self.request_history) > 1000:
            self.request_history.pop(0)
    
    def check_rate_limit(self, tool_name: str, user_id: str, policy: SecurityPolicy) -> bool:
        """Check if request is within rate limits"""
        key = f"{user_id}:{tool_name}"
        now = time.time()
        
        limit_config = policy.rate_limits.get(tool_name, policy.rate_limits["default"])
        window = limit_config["window"]
        max_calls = limit_config["calls"]
        
        if key not in self.rate_limiter:
            self.rate_limiter[key] = []
        
        # Clean old entries
        self.rate_limiter[key] = [
            timestamp for timestamp in self.rate_limiter[key] 
            if now - timestamp < window
        ]
        
        if len(self.rate_limiter[key]) >= max_calls:
            self.metrics["rate_limit_hits"] += 1
            return False
            
        self.rate_limiter[key].append(now)
        return True
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        return {
            **self.metrics,
            "recent_requests": self.request_history[-10:],  # Last 10 requests
            "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }

# Initialize components
security_policy = SecurityPolicy()
auth_manager = AuthorizationManager()
monitor_manager = MonitoringManager()
monitor_manager.start_time = time.time()

def require_authorization(security_level: SecurityLevel = SecurityLevel.MEDIUM):
    """Decorator to require authorization for sensitive tools"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user context (in real implementation, extract from request context)
            user_id = kwargs.get('user_id', 'default_user')
            
            # Check if pre-approved
            tool_name = func.__name__
            if auth_manager.is_pre_approved(tool_name, kwargs):
                logger.info(f"Tool {tool_name} pre-approved for user {user_id}")
                return await func(*args, **kwargs)
            
            # Create authorization request
            reason = f"Tool {tool_name} requires {security_level.name} level authorization"
            auth_request = auth_manager.create_request(
                tool_name, kwargs, user_id, security_level, reason
            )
            
            monitor_manager.metrics["authorization_requests"] += 1
            
            # In real implementation, this would trigger external authorization flow
            # For demo, we'll simulate immediate approval for non-critical tools
            if security_level in [SecurityLevel.LOW, SecurityLevel.MEDIUM]:
                auth_manager.approve_request(auth_request.id, "auto_approval")
                logger.info(f"Auto-approved {tool_name} for user {user_id}")
                return await func(*args, **kwargs)
            else:
                # Would wait for external approval in real system
                raise McpError(
                    f"Authorization required for {tool_name}. Request ID: {auth_request.id}",
                    {"request_id": auth_request.id, "reason": reason}
                )
        
        return wrapper
    return decorator

def security_check(func):
    """Decorator for security checks"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        user_id = kwargs.get('user_id', 'default_user')
        tool_name = func.__name__
        
        try:
            # Rate limiting
            if not monitor_manager.check_rate_limit(tool_name, user_id, security_policy):
                monitor_manager.log_request(tool_name, user_id, False, 0, SecurityLevel.HIGH)
                raise McpError(f"Rate limit exceeded for {tool_name}")
            
            # Security pattern check
            import re
            content_to_check = json.dumps(kwargs)
            for pattern in security_policy.forbidden_patterns:
                if re.search(pattern, content_to_check, re.IGNORECASE):
                    monitor_manager.metrics["security_violations"] += 1
                    monitor_manager.log_request(tool_name, user_id, False, 0, SecurityLevel.CRITICAL)
                    raise McpError(f"Security violation: forbidden pattern detected")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Log successful execution
            execution_time = time.time() - start_time
            security_level = security_policy.tool_policies.get(tool_name, SecurityLevel.LOW)
            monitor_manager.log_request(tool_name, user_id, True, execution_time, security_level)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            security_level = security_policy.tool_policies.get(tool_name, SecurityLevel.LOW)
            monitor_manager.log_request(tool_name, user_id, False, execution_time, security_level)
            raise
    
    return wrapper

# Initialize database
def init_database():
    """Initialize database with monitoring and authorization tables"""
    conn = sqlite3.connect("memory.db")
    
    # Drop existing tables
    tables_to_drop = ["memories", "weather_cache", "prompt_usage", "authorization_requests", "audit_log"]
    for table in tables_to_drop:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    
    # Create core tables
    conn.execute("""
    CREATE TABLE memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        value TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'general',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        importance INTEGER DEFAULT 1,
        created_by TEXT DEFAULT 'system'
    )
    """)
    
    conn.execute("""
    CREATE TABLE weather_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        weather_data TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    conn.execute("""
    CREATE TABLE prompt_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt_name TEXT NOT NULL,
        arguments TEXT NOT NULL,
        used_at TEXT NOT NULL,
        context TEXT,
        user_id TEXT DEFAULT 'default'
    )
    """)
    
    # Authorization table
    conn.execute("""
    CREATE TABLE authorization_requests (
        id TEXT PRIMARY KEY,
        tool_name TEXT NOT NULL,
        arguments TEXT NOT NULL,
        user_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        security_level TEXT NOT NULL,
        reason TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        status TEXT NOT NULL,
        approved_by TEXT
    )
    """)
    
    # Audit log table
    conn.execute("""
    CREATE TABLE audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        user_id TEXT NOT NULL,
        success BOOLEAN NOT NULL,
        execution_time REAL NOT NULL,
        security_level TEXT NOT NULL,
        details TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized with security and monitoring tables")

# Create MCP server
mcp = FastMCP("Enhanced Secure MCP Server")

# Mock weather data
MOCK_WEATHER_DATA = {
    "beijing": {"temperature": 15, "condition": "Sunny", "humidity": 45, "wind": "5 km/h NE"},
    "default": {"temperature": random.randint(10, 30), "condition": random.choice(["Sunny", "Cloudy", "Rainy"]), "humidity": random.randint(30, 80), "wind": f"{random.randint(2, 15)} km/h N"}
}

# Event Sourcing System - 在现有导入后添加
import aiohttp
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Coroutine

class EventSourceTaskType(Enum):
    WEB_MONITOR = "web_monitor"
    SCHEDULE = "schedule" 
    THRESHOLD_WATCH = "threshold_watch"
    NEWS_DIGEST = "news_digest"

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
        
    async def start_service(self):
        """Start the event sourcing service"""
        self.running = True
        asyncio.create_task(self._service_loop())
        logger.info("🔄 Event Sourcing Service started")
    
    async def stop_service(self):
        """Stop the event sourcing service"""
        self.running = False
        
        # Cancel all running monitors
        for task in self.running_monitors.values():
            task.cancel()
        self.running_monitors.clear()
        
        self.executor.shutdown(wait=False)
        logger.info("⏹️ Event Sourcing Service stopped")
    
    async def register_task(self, task: EventSourceTask):
        """Register a new background task"""
        self.tasks[task.task_id] = task
        
        # Start monitoring for this task
        if task.task_type == EventSourceTaskType.WEB_MONITOR:
            monitor_task = asyncio.create_task(self._web_monitor(task))
            self.running_monitors[task.task_id] = monitor_task
        elif task.task_type == EventSourceTaskType.SCHEDULE:
            monitor_task = asyncio.create_task(self._schedule_monitor(task))
            self.running_monitors[task.task_id] = monitor_task
        elif task.task_type == EventSourceTaskType.NEWS_DIGEST:
            monitor_task = asyncio.create_task(self._news_digest_monitor(task))
            self.running_monitors[task.task_id] = monitor_task
        
        logger.info(f"📝 Registered background task: {task.description}")
    
    async def pause_task(self, task_id: str) -> bool:
        """Pause a background task"""
        if task_id in self.tasks:
            self.tasks[task_id].status = "paused"
            if task_id in self.running_monitors:
                self.running_monitors[task_id].cancel()
                del self.running_monitors[task_id]
            return True
        return False
    
    async def resume_task(self, task_id: str) -> bool:
        """Resume a paused task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "active"
            
            # Restart monitoring
            if task.task_type == EventSourceTaskType.WEB_MONITOR:
                monitor_task = asyncio.create_task(self._web_monitor(task))
                self.running_monitors[task.task_id] = monitor_task
            elif task.task_type == EventSourceTaskType.SCHEDULE:
                monitor_task = asyncio.create_task(self._schedule_monitor(task))
                self.running_monitors[task.task_id] = monitor_task
            elif task.task_type == EventSourceTaskType.NEWS_DIGEST:
                monitor_task = asyncio.create_task(self._news_digest_monitor(task))
                self.running_monitors[task.task_id] = monitor_task
            
            return True
        return False
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a background task"""
        if task_id in self.tasks:
            # Cancel monitoring
            if task_id in self.running_monitors:
                self.running_monitors[task_id].cancel()
                del self.running_monitors[task_id]
            
            # Remove task
            del self.tasks[task_id]
            return True
        return False
    
    async def list_tasks(self) -> List[EventSourceTask]:
        """List all tasks"""
        return list(self.tasks.values())
    
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
                        
                        if task.task_type == EventSourceTaskType.WEB_MONITOR:
                            monitor_task = asyncio.create_task(self._web_monitor(task))
                            self.running_monitors[task.task_id] = monitor_task
                        elif task.task_type == EventSourceTaskType.NEWS_DIGEST:
                            monitor_task = asyncio.create_task(self._news_digest_monitor(task))
                            self.running_monitors[task.task_id] = monitor_task
                
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
                    # Use existing web scraper tool
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
        """Scrape web content using existing tools"""
        try:
            # Simulate web scraping (in real implementation, would use existing scraper)
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
        # This is a simplified implementation
        # In real implementation, would use BeautifulSoup or similar
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

# Global event sourcing service instance
event_sourcing_service = EventSourcingService()

# =====================
# ENHANCED TOOLS WITH SECURITY
# =====================

@mcp.tool()
@security_check
@require_authorization(SecurityLevel.MEDIUM)
async def remember(key: str, value: str, category: str = "general", importance: int = 1, user_id: str = "default") -> str:
    """Store information in long-term memory with authorization"""
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        
        cursor = conn.execute("""
            UPDATE memories 
            SET value = ?, category = ?, importance = ?, updated_at = ?
            WHERE key = ?
        """, (value, category, importance, now, key))
        
        if cursor.rowcount == 0:
            conn.execute("""
                INSERT INTO memories (key, value, category, importance, created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key, value, category, importance, now, now, user_id))
        
        conn.commit()
        
        # Return structured JSON
        return json.dumps({
            "status": "success",
            "action": "remember",
            "data": {
                "key": key,
                "value": value,
                "category": category,
                "importance": importance,
                "created_by": user_id
            },
            "timestamp": now
        })
    finally:
        conn.close()

@mcp.tool()
@security_check
@require_authorization(SecurityLevel.HIGH)
async def forget(key: str, user_id: str = "default") -> str:
    """Remove information from memory with high security authorization"""
    conn = sqlite3.connect("memory.db")
    try:
        cursor = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        conn.commit()
        
        success = cursor.rowcount > 0
        return json.dumps({
            "status": "success" if success else "not_found",
            "action": "forget",
            "data": {"key": key, "deleted": success},
            "timestamp": datetime.now().isoformat()
        })
    finally:
        conn.close()

@mcp.tool()
@security_check
async def search_memories(query: str, category: str = None, min_importance: int = 1, user_id: str = "default") -> str:
    """Search through memories with security checks"""
    conn = sqlite3.connect("memory.db")
    try:
        sql = """
            SELECT key, value, category, importance, created_at, updated_at, created_by
            FROM memories 
            WHERE (key LIKE ? OR value LIKE ?) AND importance >= ?
        """
        params = [f"%{query}%", f"%{query}%", min_importance]
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        
        sql += " ORDER BY importance DESC, updated_at DESC LIMIT 10"
        
        cursor = conn.execute(sql, params)
        results = cursor.fetchall()
        
        memories = []
        for key, value, cat, importance, created_at, updated_at, created_by in results:
            memories.append({
                "key": key,
                "value": value,
                "category": cat,
                "importance": importance,
                "created_at": created_at,
                "updated_at": updated_at,
                "created_by": created_by
            })
        
        return json.dumps({
            "status": "success",
            "action": "search_memories",
            "data": {
                "query": query,
                "results": memories,
                "count": len(memories)
            },
            "timestamp": datetime.now().isoformat()
        })
    finally:
        conn.close()

@mcp.tool()
@security_check
async def get_weather(city: str, user_id: str = "default") -> str:
    """Get weather information with caching and monitoring"""
    city_lower = city.lower()
    
    conn = sqlite3.connect("memory.db")
    try:
        # Check cache
        cursor = conn.execute("""
            SELECT weather_data, updated_at 
            FROM weather_cache 
            WHERE city = ? AND datetime(updated_at) > datetime('now', '-1 hour')
        """, (city_lower,))
        cached = cursor.fetchone()
        
        if cached:
            weather_data, updated_at = cached
            result = json.loads(weather_data)
            result["cached"] = True
            result["cached_at"] = updated_at
        else:
            # Get fresh data
            if city_lower in MOCK_WEATHER_DATA:
                weather_data = MOCK_WEATHER_DATA[city_lower].copy()
            else:
                weather_data = MOCK_WEATHER_DATA["default"].copy()
            
            weather_data.update({
                "city": city,
                "cached": False,
                "retrieved_at": datetime.now().isoformat()
            })
            
            # Cache result
            now = datetime.now().isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO weather_cache (city, weather_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (city_lower, json.dumps(weather_data), now, now))
            conn.commit()
            
            result = weather_data
        
        return json.dumps({
            "status": "success",
            "action": "get_weather",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
    finally:
        conn.close()

# =====================
# MONITORING AND AUTHORIZATION TOOLS
# =====================

@mcp.tool()
@security_check
async def get_authorization_requests(user_id: str = "admin") -> str:
    """Get pending authorization requests (admin only)"""
    if user_id != "admin":
        raise McpError("Unauthorized: Admin access required")
    
    requests = []
    for req_id, request in auth_manager.pending_requests.items():
        if request.status == AuthorizationResult.PENDING:
            requests.append({
                "id": req_id,
                "tool_name": request.tool_name,
                "user_id": request.user_id,
                "security_level": request.security_level.name,
                "reason": request.reason,
                "timestamp": request.timestamp.isoformat(),
                "expires_at": request.expires_at.isoformat()
            })
    
    return json.dumps({
        "status": "success",
        "action": "get_authorization_requests",
        "data": {"requests": requests, "count": len(requests)},
        "timestamp": datetime.now().isoformat()
    })

@mcp.tool()
@security_check
async def approve_authorization(request_id: str, approved_by: str = "admin") -> str:
    """Approve an authorization request"""
    success = auth_manager.approve_request(request_id, approved_by)
    
    return json.dumps({
        "status": "success" if success else "failed",
        "action": "approve_authorization",
        "data": {"request_id": request_id, "approved": success, "approved_by": approved_by},
        "timestamp": datetime.now().isoformat()
    })

@mcp.tool()
@security_check
async def get_monitoring_metrics(user_id: str = "admin") -> str:
    """Get system monitoring metrics"""
    if user_id != "admin":
        raise McpError("Unauthorized: Admin access required")
    
    metrics = monitor_manager.get_metrics()
    
    return json.dumps({
        "status": "success",
        "action": "get_monitoring_metrics",
        "data": metrics,
        "timestamp": datetime.now().isoformat()
    })

@mcp.tool()
@security_check  
async def get_audit_log(limit: int = 50, user_id: str = "admin") -> str:
    """Get audit log entries"""
    if user_id != "admin":
        raise McpError("Unauthorized: Admin access required")
    
    # Get from monitoring manager's request history
    recent_logs = monitor_manager.request_history[-limit:] if limit > 0 else monitor_manager.request_history
    
    return json.dumps({
        "status": "success",
        "action": "get_audit_log", 
        "data": {"logs": recent_logs, "count": len(recent_logs)},
        "timestamp": datetime.now().isoformat()
    })

# =====================
# RESOURCES WITH MONITORING
# =====================

@mcp.resource("memory://all")
async def get_all_memories() -> str:
    """Get all memories with monitoring"""
    monitor_manager.log_request("get_all_memories", "system", True, 0.1, SecurityLevel.LOW)
    
    conn = sqlite3.connect("memory.db")
    try:
        cursor = conn.execute("""
            SELECT key, value, category, importance, created_at, updated_at, created_by
            FROM memories ORDER BY importance DESC, created_at DESC
        """)
        memories = cursor.fetchall()
        
        memory_list = []
        for key, value, category, importance, created_at, updated_at, created_by in memories:
            memory_list.append({
                "key": key,
                "value": value,
                "category": category,
                "importance": importance,
                "created_at": created_at,
                "updated_at": updated_at,
                "created_by": created_by
            })
        
        return json.dumps({
            "status": "success",
            "data": {"memories": memory_list, "count": len(memory_list)},
            "retrieved_at": datetime.now().isoformat()
        })
    finally:
        conn.close()

@mcp.resource("monitoring://metrics")
async def get_metrics_resource() -> str:
    """Get monitoring metrics as resource"""
    return json.dumps({
        "status": "success",
        "data": monitor_manager.get_metrics(),
        "retrieved_at": datetime.now().isoformat()
    })

def main():
    """Main server function with enhanced security"""
    print("🚀 Starting Enhanced Secure MCP Server...")
    
    # Initialize database
    init_database()
    
    # Add sample data
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        sample_memories = [
            ("user_name", "Assistant User", "personal", 5, "system"),
            ("api_guidelines", "Always use structured JSON responses", "technical", 5, "system"),
            ("security_policy", "All high-security operations require authorization", "security", 5, "system")
        ]
        
        for key, value, category, importance, created_by in sample_memories:
            conn.execute("""
                INSERT OR IGNORE INTO memories (key, value, category, importance, created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key, value, category, importance, now, now, created_by))
        
        conn.commit()
        logger.info("Sample data initialized")
    finally:
        conn.close()
    
    print("✅ Enhanced Secure MCP Server ready!")
    print("🔐 Security Features:")
    print("  - Authorization system for sensitive operations")
    print("  - Rate limiting and security pattern detection") 
    print("  - Comprehensive audit logging")
    print("  - Structured JSON responses")
    print("🎯 Tools: remember*, forget*, search_memories, get_weather, monitoring tools")
    print("📊 Resources: memory://all, monitoring://metrics")
    print("* = Requires authorization")
    
    # Run the server
    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()