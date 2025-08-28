#!/usr/bin/env python
"""
Event Feedback HTTP Server
Enhanced callback server that processes events with the chat API and stores in database
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import aiohttp

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
handlers = [logging.StreamHandler()]

# Only add file handler if logs directory exists  
log_dir = 'logs'
if os.path.exists(log_dir):
    handlers.append(logging.FileHandler(os.path.join(log_dir, 'event_feedback.log')))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Event Feedback Server", version="2.0.0")

# CORS Configuration
try:
    from .cors_config import get_cors_config
    app.add_middleware(CORSMiddleware, **get_cors_config())
    logger.info("✅ CORS middleware configured successfully")
except ImportError:
    # Fallback to default CORS config if config file not available
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Frontend development server
            "http://localhost:3000",  # Alternative frontend port
            "http://127.0.0.1:5173", # Alternative localhost format
            "http://127.0.0.1:3000", # Alternative localhost format
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    logger.info("✅ CORS middleware configured with fallback config")

# Configuration from environment variables
CHAT_API_URL = os.getenv('CHAT_API_URL', 'http://localhost:8080')
EVENT_SERVICE_PORT = int(os.getenv('EVENT_SERVICE_PORT', '8101'))

# Initialize database service
try:
    from tools.services.event_service.event_database_service import EventDatabaseService
    db_service = EventDatabaseService()
    logger.info("✅ Database service initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize database service: {e}")
    db_service = None

# Store recent events for monitoring
recent_events = []

@app.post("/process_background_feedback")
async def process_background_feedback(request: Request):
    """Receive event feedback and forward to Chat API for intelligent processing"""
    try:
        # Get the feedback data
        feedback_data = await request.json()
        
        event_type = feedback_data.get("event_type", "unknown")
        task_id = feedback_data.get("task_id", "unknown")
        
        logger.info(f"📥 Received event: {event_type} from task {task_id}")
        
        # Add metadata
        feedback_data["received_at"] = datetime.now().isoformat()
        feedback_data["server"] = "event_feedback_server"
        
        # Store for monitoring
        recent_events.append(feedback_data)
        if len(recent_events) > 50:  # Keep only last 50
            recent_events.pop(0)
        
        # Store event in database
        event_id = None
        if db_service:
            try:
                event_id = await db_service.store_event(feedback_data)
                if event_id:
                    logger.info(f"💾 Stored event in database: {event_id}")
            except Exception as e:
                logger.error(f"❌ Failed to store event in database: {e}")
        
        # Process with Chat API
        processing_result = await process_with_chat_api(feedback_data, event_id)
        
        if processing_result:
            # Update event as processed in database
            if db_service and event_id:
                try:
                    await db_service.update_event_processed(event_id, processing_result)
                    logger.info(f"✅ Updated event processing status: {event_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to update event status: {e}")
            
            logger.info(f"✅ Event processed successfully")
            return JSONResponse(content={
                "status": "processed",
                "message": "Event processed with Chat API",
                "event_id": event_id,
                "processing_result": processing_result
            })
        else:
            logger.warning(f"⚠️ Failed to process event")
            return JSONResponse(content={
                "status": "failed",
                "message": "Failed to process event with Chat API",
                "event_id": event_id
            })
        
    except Exception as e:
        logger.error(f"❌ Error processing feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/event_callback")
async def event_callback(request: Request):
    """Alternative endpoint for event callbacks"""
    # Just forward to the main processing endpoint
    return await process_background_feedback(request)

async def process_with_chat_api(event_data: Dict[str, Any], event_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Process event using the chat API for intelligent analysis"""
    try:
        # Create intelligent prompt based on event type
        prompt = create_event_processing_prompt(event_data)
        
        # Prepare payload for chat API (correct format)
        chat_payload = {
            "message": prompt,
            "user_id": event_data.get("data", {}).get("user_id", "event_system"),
            "session_id": f"event_session_{event_data.get('task_id', 'unknown')}",
            "prompt_name": None,
            "prompt_args": {}
        }
        
        # Send to chat API (correct endpoint)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CHAT_API_URL}/api/chat",
                json=chat_payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer dev_key_test"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    # Process SSE stream from Chat API
                    complete_response = ""
                    chat_events = []
                    
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        
                        if line_text.startswith('data: ') and line_text != 'data: [DONE]':
                            try:
                                event_data = json.loads(line_text[6:])  # Remove 'data: ' prefix
                                chat_events.append(event_data)
                                
                                # Accumulate LLM chunks for complete response
                                if (event_data.get("type") == "custom_stream" and 
                                    event_data.get("content", {}).get("custom_llm_chunk")):
                                    complete_response += event_data["content"]["custom_llm_chunk"]
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse SSE event: {e}")
                                continue
                    
                    logger.info(f"📤 Chat API processed event successfully: {len(chat_events)} events")
                    return {
                        "chat_response": complete_response,
                        "chat_events": chat_events,
                        "events_count": len(chat_events),
                        "processed_at": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Chat API returned status {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error response: {error_text}")
                    return None
                    
    except aiohttp.ClientError as e:
        logger.error(f"Network error connecting to chat API: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing with chat API: {e}")
        return None

def create_event_processing_prompt(event_data: Dict[str, Any]) -> str:
    """Create an intelligent prompt for event processing"""
    event_type = event_data.get("event_type", "unknown")
    data = event_data.get("data", {})
    
    if event_type == "web_content_change":
        url = data.get("url", "unknown")
        keywords = data.get("keywords_found", [])
        content_preview = data.get("content", "")[:200]
        
        return f"""
🔔 **Web Content Change Alert**

A monitored website has changed and contains relevant keywords:

**URL:** {url}
**Keywords Found:** {', '.join(keywords)}
**Content Preview:** {content_preview}...

Please analyze this change and provide:
1. A summary of what might have changed
2. The significance of this change
3. Any recommended actions
4. Whether this requires immediate attention

Task Description: {data.get('description', 'Web monitoring task')}
"""
    
    elif event_type == "scheduled_trigger":
        schedule_config = data.get("schedule_config", {})
        trigger_time = data.get("trigger_time", "")
        
        return f"""
⏰ **Scheduled Event Triggered**

A scheduled task has been triggered:

**Trigger Time:** {trigger_time}
**Schedule Type:** {schedule_config.get('type', 'unknown')}
**Task Description:** {data.get('description', 'Scheduled task')}

Please execute the scheduled task and provide:
1. Confirmation that the task was completed
2. Any results or findings
3. Next scheduled execution time
4. Any issues encountered
"""
    
    elif event_type == "daily_news_digest":
        news_summaries = data.get("news_summaries", [])
        digest_date = data.get("digest_date", "")
        
        headlines = []
        for summary in news_summaries:
            source = summary.get("source", "Unknown Source")
            source_headlines = summary.get("headlines", [])
            headlines.extend([f"[{source}] {h}" for h in source_headlines[:3]])
        
        return f"""
📰 **Daily News Digest - {digest_date}**

Here are today's top headlines from monitored sources:

{chr(10).join(f"• {h}" for h in headlines[:10])}

Please provide:
1. A summary of key trends and themes
2. Any urgent or breaking news items
3. Technology/business implications
4. Recommendations for follow-up
"""
    
    else:
        # Generic event processing
        return f"""
🔔 **Event Alert: {event_type}**

An event has occurred that requires attention:

**Event Data:**
{json.dumps(data, indent=2)}

Please analyze this event and provide:
1. What this event means
2. Any required actions
3. Priority level
4. Recommendations for handling
"""

@app.get("/events/recent")
async def get_recent_events(limit: int = 10):
    """Get recent events for monitoring"""
    try:
        # Get from database if available
        db_events = []
        if db_service:
            try:
                db_events = await db_service.get_recent_events(limit=limit)
            except Exception as e:
                logger.error(f"Failed to get events from database: {e}")
        
        return {
            "total_memory_events": len(recent_events),
            "total_database_events": len(db_events),
            "memory_events": recent_events[-limit:],  # Last N events from memory
            "database_events": db_events,  # Events from database
            "event_types": list(set(event.get("event_type", "unknown") for event in recent_events)),
            "database_available": db_service is not None
        }
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_healthy = False
        if db_service:
            try:
                stats = await db_service.get_event_statistics()
                db_healthy = stats is not None
            except Exception:
                db_healthy = False
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "events_processed": len(recent_events),
            "chat_api_url": CHAT_API_URL,
            "database_healthy": db_healthy,
            "database_available": db_service is not None,
            "port": EVENT_SERVICE_PORT
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Event Feedback Server",
        "version": "2.0.0",
        "status": "running",
        "purpose": "Processes background task events with Chat API and stores in database",
        "endpoints": [
            "/process_background_feedback",
            "/event_callback",
            "/events/recent",
            "/health"
        ],
        "chat_api_url": CHAT_API_URL,
        "database_available": db_service is not None,
        "events_processed": len(recent_events),
        "port": EVENT_SERVICE_PORT
    }

def main():
    """Run the event feedback server"""
    print("🚀 Starting Enhanced Event Feedback Server...")
    print(f"📡 Server will listen on http://localhost:{EVENT_SERVICE_PORT}")
    print(f"📥 Event callback endpoint: http://localhost:{EVENT_SERVICE_PORT}/process_background_feedback")
    print(f"📤 Will process events with Chat API: {CHAT_API_URL}")
    print(f"📊 Monitor at: http://localhost:{EVENT_SERVICE_PORT}/events/recent")
    print(f"💾 Database service: {'Available' if db_service else 'Not available'}")
    print("🌐 CORS enabled for frontend origins: localhost:5173, localhost:3000")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=EVENT_SERVICE_PORT,
        log_level="info"
    )

if __name__ == "__main__":
    main() 