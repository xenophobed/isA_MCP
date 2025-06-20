#!/usr/bin/env python
"""
Event Feedback HTTP Server
Simple callback server that forwards events to LangGraph Agent for processing
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/event_feedback.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Event Feedback Server", version="1.0.0")

# Configuration for LangGraph Agent endpoint
LANGGRAPH_AGENT_URL = "http://localhost:8001/process_event"  # Agent endpoint

# Store recent events for monitoring
recent_events = []

@app.post("/process_background_feedback")
async def process_background_feedback(request: Request):
    """Receive event feedback and forward to LangGraph Agent"""
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
        
        # Forward to LangGraph Agent
        agent_response = await forward_to_agent(feedback_data)
        
        if agent_response:
            logger.info(f"✅ Event forwarded to agent successfully")
            return JSONResponse(content={
                "status": "forwarded",
                "message": "Event forwarded to LangGraph Agent",
                "agent_response": agent_response
            })
        else:
            logger.warning(f"⚠️ Failed to forward event to agent")
            return JSONResponse(content={
                "status": "failed",
                "message": "Failed to forward event to agent"
            })
        
    except Exception as e:
        logger.error(f"❌ Error processing feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def forward_to_agent(event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Forward event data to LangGraph Agent for processing"""
    try:
        # Prepare event for agent
        agent_payload = {
            "event_type": "background_task_event",
            "timestamp": datetime.now().isoformat(),
            "data": event_data,
            "source": "event_sourcing_system"
        }
        
        # Send to agent
        async with aiohttp.ClientSession() as session:
            async with session.post(
                LANGGRAPH_AGENT_URL,
                json=agent_payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"📤 Agent processed event: {result.get('status', 'unknown')}")
                    return result
                else:
                    logger.error(f"Agent returned status {response.status}")
                    return None
                    
    except aiohttp.ClientError as e:
        logger.error(f"Network error forwarding to agent: {e}")
        return None
    except Exception as e:
        logger.error(f"Error forwarding to agent: {e}")
        return None

@app.get("/events/recent")
async def get_recent_events():
    """Get recent events for monitoring"""
    return {
        "total_events": len(recent_events),
        "recent_events": recent_events[-10:],  # Last 10 events
        "event_types": list(set(event.get("event_type", "unknown") for event in recent_events))
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "events_processed": len(recent_events),
        "agent_endpoint": LANGGRAPH_AGENT_URL
    }

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Event Feedback Server",
        "version": "1.0.0",
        "status": "running",
        "purpose": "Forwards background task events to LangGraph Agent",
        "endpoints": [
            "/process_background_feedback",
            "/events/recent",
            "/health"
        ],
        "agent_endpoint": LANGGRAPH_AGENT_URL,
        "events_processed": len(recent_events)
    }

def main():
    """Run the event feedback server"""
    print("🚀 Starting Event Feedback Server...")
    print("📡 Server will listen on http://localhost:8000")
    print("📥 Event callback endpoint: http://localhost:8000/process_background_feedback")
    print(f"📤 Will forward events to: {LANGGRAPH_AGENT_URL}")
    print("📊 Monitor at: http://localhost:8000/events/recent")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main() 