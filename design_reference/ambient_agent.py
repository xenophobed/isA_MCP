"""
Event-Sourcing Ambient Agent System
The agent delegates tasks to an event sourcing system via MCP tools,
and the system proactively sends feedback back to the agent for processing.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from abc import ABC, abstractmethod

# Event Sourcing System (separate service that the agent calls via MCP)
class EventSourceTaskType(Enum):
    WEB_MONITOR = "web_monitor"
    SCHEDULE = "schedule"
    THRESHOLD_WATCH = "threshold_watch"
    FILE_WATCH = "file_watch"
    API_POLL = "api_poll"

@dataclass
class EventSourceTask:
    """Task that gets created in the event sourcing system"""
    task_id: str
    task_type: EventSourceTaskType
    description: str
    config: Dict[str, Any]
    callback_url: str  # Where to send results back to agent
    created_at: datetime
    status: str = "active"  # active, paused, completed, failed
    last_check: Optional[datetime] = None
    next_check: Optional[datetime] = None

@dataclass 
class EventFeedback:
    """Feedback sent from event sourcing system back to agent"""
    task_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    priority: int = 1  # 1=low, 5=critical
    requires_processing: bool = True

# MCP Tool Interface for Event Sourcing System
class EventSourcingMCPTools:
    """MCP tools that the agent calls to interact with event sourcing system"""
    
    @staticmethod
    async def create_background_task(task_config: Dict[str, Any]) -> str:
        """
        MCP Tool: create_background_task
        Agent calls this to create a background monitoring task
        """
        try:
            task = EventSourceTask(
                task_id=str(uuid.uuid4()),
                task_type=EventSourceTaskType(task_config["task_type"]),
                description=task_config["description"],
                config=task_config["config"],
                callback_url=task_config["callback_url"],
                created_at=datetime.now()
            )
            
            # Register task with event sourcing system
            await EventSourcingService.register_task(task)
            
            return json.dumps({
                "status": "success",
                "task_id": task.task_id,
                "message": f"Background task '{task.description}' created and will run in background"
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error", 
                "message": f"Failed to create background task: {str(e)}"
            })
    
    @staticmethod
    async def pause_background_task(task_id: str) -> str:
        """MCP Tool: pause_background_task"""
        try:
            success = await EventSourcingService.pause_task(task_id)
            if success:
                return json.dumps({"status": "success", "message": f"Task {task_id} paused"})
            else:
                return json.dumps({"status": "error", "message": f"Task {task_id} not found"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    @staticmethod
    async def resume_background_task(task_id: str) -> str:
        """MCP Tool: resume_background_task"""
        try:
            success = await EventSourcingService.resume_task(task_id)
            if success:
                return json.dumps({"status": "success", "message": f"Task {task_id} resumed"})
            else:
                return json.dumps({"status": "error", "message": f"Task {task_id} not found"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    @staticmethod
    async def list_background_tasks() -> str:
        """MCP Tool: list_background_tasks"""
        try:
            tasks = await EventSourcingService.list_tasks()
            return json.dumps({
                "status": "success",
                "tasks": [asdict(task) for task in tasks]
            }, default=str)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    @staticmethod
    async def delete_background_task(task_id: str) -> str:
        """MCP Tool: delete_background_task"""
        try:
            success = await EventSourcingService.delete_task(task_id)
            if success:
                return json.dumps({"status": "success", "message": f"Task {task_id} deleted"})
            else:
                return json.dumps({"status": "error", "message": f"Task {task_id} not found"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

# Event Sourcing Service (runs independently)
class EventSourcingService:
    """
    Independent service that executes background tasks and sends feedback to agent
    This runs separately from the agent and proactively sends results back
    """
    
    _tasks: Dict[str, EventSourceTask] = {}
    _running_monitors: Dict[str, asyncio.Task] = {}
    _feedback_callback: Optional[Callable] = None
    _running = False
    
    @classmethod
    async def start_service(cls, feedback_callback: Callable[[EventFeedback], None]):
        """Start the event sourcing service"""
        cls._feedback_callback = feedback_callback
        cls._running = True
        
        # Start the main service loop
        asyncio.create_task(cls._service_loop())
        print("🔄 Event Sourcing Service started")
    
    @classmethod
    async def stop_service(cls):
        """Stop the event sourcing service"""
        cls._running = False
        
        # Cancel all running monitors
        for task in cls._running_monitors.values():
            task.cancel()
        cls._running_monitors.clear()
        
        print("⏹️ Event Sourcing Service stopped")
    
    @classmethod
    async def register_task(cls, task: EventSourceTask):
        """Register a new background task"""
        cls._tasks[task.task_id] = task
        
        # Start monitoring for this task
        if task.task_type == EventSourceTaskType.WEB_MONITOR:
            monitor_task = asyncio.create_task(cls._web_monitor(task))
            cls._running_monitors[task.task_id] = monitor_task
        elif task.task_type == EventSourceTaskType.SCHEDULE:
            monitor_task = asyncio.create_task(cls._schedule_monitor(task))
            cls._running_monitors[task.task_id] = monitor_task
        elif task.task_type == EventSourceTaskType.THRESHOLD_WATCH:
            monitor_task = asyncio.create_task(cls._threshold_monitor(task))
            cls._running_monitors[task.task_id] = monitor_task
        
        print(f"📝 Registered background task: {task.description}")
    
    @classmethod
    async def pause_task(cls, task_id: str) -> bool:
        """Pause a background task"""
        if task_id in cls._tasks:
            cls._tasks[task_id].status = "paused"
            if task_id in cls._running_monitors:
                cls._running_monitors[task_id].cancel()
                del cls._running_monitors[task_id]
            return True
        return False
    
    @classmethod
    async def resume_task(cls, task_id: str) -> bool:
        """Resume a paused task"""
        if task_id in cls._tasks:
            task = cls._tasks[task_id]
            task.status = "active"
            
            # Restart monitoring
            if task.task_type == EventSourceTaskType.WEB_MONITOR:
                monitor_task = asyncio.create_task(cls._web_monitor(task))
                cls._running_monitors[task.task_id] = monitor_task
            elif task.task_type == EventSourceTaskType.SCHEDULE:
                monitor_task = asyncio.create_task(cls._schedule_monitor(task))
                cls._running_monitors[task.task_id] = monitor_task
            
            return True
        return False
    
    @classmethod
    async def delete_task(cls, task_id: str) -> bool:
        """Delete a background task"""
        if task_id in cls._tasks:
            # Cancel monitoring
            if task_id in cls._running_monitors:
                cls._running_monitors[task_id].cancel()
                del cls._running_monitors[task_id]
            
            # Remove task
            del cls._tasks[task_id]
            return True
        return False
    
    @classmethod
    async def list_tasks(cls) -> List[EventSourceTask]:
        """List all tasks"""
        return list(cls._tasks.values())
    
    @classmethod
    async def _service_loop(cls):
        """Main service loop for health checks and maintenance"""
        while cls._running:
            try:
                # Health check on monitors
                dead_monitors = []
                for task_id, monitor in cls._running_monitors.items():
                    if monitor.done():
                        dead_monitors.append(task_id)
                
                # Restart dead monitors
                for task_id in dead_monitors:
                    if task_id in cls._tasks and cls._tasks[task_id].status == "active":
                        task = cls._tasks[task_id]
                        print(f"🔄 Restarting monitor for task: {task.description}")
                        
                        if task.task_type == EventSourceTaskType.WEB_MONITOR:
                            monitor_task = asyncio.create_task(cls._web_monitor(task))
                            cls._running_monitors[task.task_id] = monitor_task
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logging.error(f"Service loop error: {e}")
                await asyncio.sleep(60)
    
    @classmethod
    async def _web_monitor(cls, task: EventSourceTask):
        """Monitor web sources for changes"""
        config = task.config
        urls = config.get("urls", [])
        keywords = config.get("keywords", [])
        check_interval = config.get("check_interval_minutes", 30)
        
        # Store last known content state
        last_content_hashes = {}
        
        while cls._running and task.status == "active":
            try:
                for url in urls:
                    # Simulate web scraping (in real implementation, would call actual web scraper)
                    content = await cls._simulate_web_scrape(url)
                    
                    if content:
                        # Check if content contains keywords
                        content_lower = content.lower()
                        matching_keywords = [kw for kw in keywords if kw.lower() in content_lower]
                        
                        if matching_keywords:
                            # Check if content changed
                            content_hash = hash(content)
                            last_hash = last_content_hashes.get(url, None)
                            
                            if content_hash != last_hash:
                                # Content changed! Send feedback to agent
                                feedback = EventFeedback(
                                    task_id=task.task_id,
                                    event_type="web_content_change",
                                    data={
                                        "url": url,
                                        "content": content[:1000],  # Truncate for feedback
                                        "keywords_found": matching_keywords,
                                        "description": task.description
                                    },
                                    timestamp=datetime.now(),
                                    priority=3
                                )
                                
                                await cls._send_feedback(feedback)
                                last_content_hashes[url] = content_hash
                
                task.last_check = datetime.now()
                await asyncio.sleep(check_interval * 60)
                
            except Exception as e:
                logging.error(f"Web monitor error for task {task.task_id}: {e}")
                await asyncio.sleep(60)
    
    @classmethod
    async def _schedule_monitor(cls, task: EventSourceTask):
        """Monitor for scheduled events"""
        config = task.config
        schedule_type = config.get("type")  # daily, interval, etc.
        
        while cls._running and task.status == "active":
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
                            "description": task.description
                        },
                        timestamp=current_time,
                        priority=2
                    )
                    
                    await cls._send_feedback(feedback)
                    task.last_check = current_time
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logging.error(f"Schedule monitor error for task {task.task_id}: {e}")
                await asyncio.sleep(60)
    
    @classmethod
    async def _threshold_monitor(cls, task: EventSourceTask):
        """Monitor for threshold breaches"""
        config = task.config
        metric = config.get("metric")
        threshold = config.get("threshold")
        check_interval = config.get("check_interval_minutes", 15)
        
        while cls._running and task.status == "active":
            try:
                # Simulate metric checking (would call actual APIs/services)
                current_value = await cls._simulate_metric_check(metric)
                
                if current_value is not None and current_value > threshold:
                    feedback = EventFeedback(
                        task_id=task.task_id,
                        event_type="threshold_breach",
                        data={
                            "metric": metric,
                            "current_value": current_value,
                            "threshold": threshold,
                            "description": task.description
                        },
                        timestamp=datetime.now(),
                        priority=4
                    )
                    
                    await cls._send_feedback(feedback)
                
                task.last_check = datetime.now()
                await asyncio.sleep(check_interval * 60)
                
            except Exception as e:
                logging.error(f"Threshold monitor error for task {task.task_id}: {e}")
                await asyncio.sleep(60)
    
    @classmethod
    async def _send_feedback(cls, feedback: EventFeedback):
        """Send feedback back to the agent"""
        if cls._feedback_callback:
            try:
                await cls._feedback_callback(feedback)
                print(f"📤 Sent feedback to agent: {feedback.event_type}")
            except Exception as e:
                logging.error(f"Failed to send feedback: {e}")
    
    @classmethod
    async def _simulate_web_scrape(cls, url: str) -> Optional[str]:
        """Simulate web scraping (replace with actual implementation)"""
        # In real implementation, this would call actual web scraping service
        import random
        if random.random() > 0.7:  # 30% chance of "new content"
            return f"New AI breakthrough announced at {url} - timestamp: {datetime.now()}"
        return None
    
    @classmethod
    async def _simulate_metric_check(cls, metric: str) -> Optional[float]:
        """Simulate metric checking (replace with actual implementation)"""
        # In real implementation, would call APIs, check databases, etc.
        import random
        if metric == "bitcoin_price":
            return random.uniform(45000, 55000)
        elif metric == "cpu_usage":
            return random.uniform(20, 95)
        return None

# Enhanced LangGraph Agent with Event Sourcing Integration
class EventDrivenLangGraphAgent:
    """
    Enhanced agent that can create background tasks and process feedback
    """
    
    def __init__(self, base_agent):
        self.base_agent = base_agent
        self.pending_feedbacks: asyncio.Queue = asyncio.Queue()
        self.processing_feedback = False
        
    async def initialize(self):
        """Initialize the event-driven agent"""
        print("🤖 Initializing Event-Driven LangGraph Agent...")
        
        # Start the event sourcing service with feedback callback
        await EventSourcingService.start_service(self._handle_feedback)
        
        # Start feedback processing loop
        asyncio.create_task(self._feedback_processing_loop())
        
        print("✅ Event-Driven Agent initialized")
    
    async def run_conversation(self, user_input: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Enhanced conversation that can handle background task requests"""
        
        # First, run the normal agent conversation
        result = await self.base_agent.run_conversation(user_input, thread_id)
        
        # Check if the agent called any background task MCP tools
        # (This would be detected by checking the conversation messages for tool calls)
        
        return result
    
    async def _handle_feedback(self, feedback: EventFeedback):
        """Handle feedback from event sourcing system"""
        print(f"📥 Received feedback: {feedback.event_type} for task {feedback.task_id}")
        
        # Queue the feedback for processing
        await self.pending_feedbacks.put(feedback)
    
    async def _feedback_processing_loop(self):
        """Process feedback from event sourcing system"""
        while True:
            try:
                # Get feedback from queue
                feedback = await self.pending_feedbacks.get()
                
                # Create a prompt for the agent to process the feedback
                processing_prompt = f"""
You have received background task feedback from the event sourcing system:

Task ID: {feedback.task_id}
Event Type: {feedback.event_type}
Priority: {feedback.priority}
Timestamp: {feedback.timestamp}

Data:
{json.dumps(feedback.data, indent=2)}

Please analyze this feedback and determine:
1. Is this information relevant and actionable for the user?
2. Should the user be notified immediately?
3. What summary or action should be taken?

If the user should be notified, format a clear, concise message explaining what happened and any recommended actions.
If this is not worth notifying the user about, respond with "NO_NOTIFICATION_NEEDED".
"""
                
                # Process the feedback with the agent
                result = await self.base_agent.run_conversation(processing_prompt)
                
                # If agent says to notify user, send notification
                if result["response"] and "NO_NOTIFICATION_NEEDED" not in result["response"]:
                    await self._send_notification_to_user(feedback, result["response"])
                
                # Mark feedback as processed
                self.pending_feedbacks.task_done()
                
            except Exception as e:
                logging.error(f"Feedback processing error: {e}")
                await asyncio.sleep(1)
    
    async def _send_notification_to_user(self, feedback: EventFeedback, agent_message: str):
        """Send notification to user based on agent's analysis"""
        try:
            # Get the original task to find notification preferences
            tasks = await EventSourcingService.list_tasks()
            original_task = None
            for task in tasks:
                if task.task_id == feedback.task_id:
                    original_task = task
                    break
            
            if original_task:
                # Use the configured notification method from the original task
                notification_config = original_task.config.get("notification", {})
                method = notification_config.get("method", "twilio")
                
                if method == "twilio":
                    phone = notification_config.get("phone_number")
                    # Call Twilio MCP tool
                    await self._send_via_mcp("twilio_send_sms", {
                        "to": phone,
                        "message": f"🤖 Background Task Update:\n\n{agent_message}"
                    })
                    
                elif method == "email":
                    email = notification_config.get("email")
                    # Call Email MCP tool
                    await self._send_via_mcp("send_email", {
                        "to": email,
                        "subject": f"Background Task: {original_task.description}",
                        "body": agent_message
                    })
                
                print(f"📱 Sent notification to user via {method}")
            
        except Exception as e:
            logging.error(f"Failed to send user notification: {e}")
    
    async def _send_via_mcp(self, tool_name: str, params: Dict[str, Any]):
        """Send notification via MCP tool"""
        # This would call the actual MCP manager
        # await mcp_manager.call_tool(tool_name, params)
        print(f"📤 Would send via {tool_name}: {params}")

# Usage Example
async def example_usage():
    """Example of how the new system works"""
    
    # Initialize the event-driven agent
    from .langgraph_agent import LangGraphAgent
    base_agent = LangGraphAgent()
    event_agent = EventDrivenLangGraphAgent(base_agent)
    await event_agent.initialize()
    
    # User makes a request that creates a background task
    user_request = """
    I want you to monitor TechCrunch for new articles about artificial intelligence 
    and let me know when something important comes up. Send alerts to my phone +1234567890.
    """
    
    # The agent processes this and calls the MCP tool to create a background task
    # (This would happen automatically in the agent's conversation)
    task_config = {
        "task_type": "web_monitor",
        "description": "Monitor TechCrunch for AI articles",
        "config": {
            "urls": ["https://techcrunch.com"],
            "keywords": ["artificial intelligence", "AI", "machine learning"],
            "check_interval_minutes": 30,
            "notification": {
                "method": "twilio",
                "phone_number": "+1234567890"
            }
        },
        "callback_url": "http://agent-service/feedback"
    }
    
    # Create the background task via MCP tool
    task_result = await EventSourcingMCPTools.create_background_task(task_config)
    print("Task creation result:", task_result)
    
    # The event sourcing system is now monitoring in the background
    # When it finds new AI articles, it will send feedback to the agent
    # The agent will analyze the feedback and decide whether to notify the user
    
    # Simulate some time passing...
    await asyncio.sleep(5)
    
    # List active tasks
    tasks_result = await EventSourcingMCPTools.list_background_tasks()
    print("Active tasks:", tasks_result)

if __name__ == "__main__":
    asyncio.run(example_usage())