"""
Event Management Endpoints
完全迁移自event_server.py的所有功能
包含事件反馈处理、Chat API集成、智能提示生成等
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import sys
import os
import aiohttp
import json

# Add dependencies for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.schemas.event_models import Event, EventFeedback, EventStatistics
from services.base import ServiceResult, ServiceStatus
from api.dependencies import get_current_user, CurrentUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/events", tags=["Events"])

# Configuration from environment variables
CHAT_API_URL = os.getenv('CHAT_API_URL', 'http://localhost:8080')

# Store recent events for monitoring (from event_server.py)
recent_events = []

# 依赖注入 - 获取事件服务
def get_event_service():
    """获取事件服务实例"""
    try:
        # Use absolute import path
        from tools.services.user_service.services.event_service import EventService
        return EventService()
    except ImportError as e:
        logger.error(f"Failed to import EventService: {e}")
        raise ImportError(f"EventService not available: {e}")

# MockEventService removed - using real EventService only


def get_event_service_dependency():
    """Get event service dependency"""
    return get_event_service()

EventServiceDep = Depends(get_event_service_dependency)


# ========== 核心事件反馈处理端点 (原event_server.py的主要功能) ==========

@router.post("/process_background_feedback", response_model=Dict[str, Any])
async def process_background_feedback(
    request: Request,
    event_service = Depends(get_event_service_dependency)
):
    """
    接收后台任务反馈并处理 - 核心Event Sourcing功能
    完全迁移自event_server.py的主要端点
    """
    try:
        # Get the feedback data
        feedback_data = await request.json()
        
        event_type = feedback_data.get("event_type", "unknown")
        task_id = feedback_data.get("task_id", "unknown")
        
        logger.info(f"📥 Received event: {event_type} from task {task_id}")
        
        # Add metadata (from event_server.py)
        feedback_data["received_at"] = datetime.now().isoformat()
        feedback_data["server"] = "user_service_event_processor"
        
        # Store for monitoring (from event_server.py)
        recent_events.append(feedback_data)
        if len(recent_events) > 50:  # Keep only last 50
            recent_events.pop(0)
        
        # Store event using event service
        result = await event_service.create_event(feedback_data)
        event_id = None
        if result.status == ServiceStatus.SUCCESS:
            event_id = result.data.get("event_id") if result.data else None
            logger.info(f"💾 Stored event: {event_id}")
        
        # Process with Chat API (from event_server.py)
        processing_result = await process_with_chat_api(feedback_data, event_id)
        
        if processing_result:
            # Update event as processed 
            if event_id:
                await event_service.process_event(event_id, processing_result)
                logger.info(f"✅ Updated event processing status: {event_id}")
            
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


@router.post("/event_callback", response_model=Dict[str, Any])
async def event_callback(request: Request):
    """备用事件回调端点 - 兼容原event_server.py"""
    return await process_background_feedback(request)


async def process_with_chat_api(event_data: Dict[str, Any], event_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    使用Chat API处理事件 - 完全迁移自event_server.py
    """
    try:
        # Create intelligent prompt based on event type
        prompt = create_event_processing_prompt(event_data)
        
        # Prepare payload for chat API (correct format from event_server.py)
        chat_payload = {
            "message": prompt,
            "user_id": event_data.get("data", {}).get("user_id", "event_system"),
            "session_id": f"event_session_{event_data.get('task_id', 'unknown')}",
            "prompt_name": None,
            "prompt_args": {}
        }
        
        # Send to chat API (correct endpoint from event_server.py)
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
                    # Process SSE stream from Chat API (from event_server.py)
                    complete_response = ""
                    chat_events = []
                    
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        
                        if line_text.startswith('data: ') and line_text != 'data: [DONE]':
                            try:
                                event_data_parsed = json.loads(line_text[6:])  # Remove 'data: ' prefix
                                chat_events.append(event_data_parsed)
                                
                                # Accumulate LLM chunks for complete response
                                if (event_data_parsed.get("type") == "custom_stream" and 
                                    event_data_parsed.get("content", {}).get("custom_llm_chunk")):
                                    complete_response += event_data_parsed["content"]["custom_llm_chunk"]
                                    
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
    """
    创建事件处理的智能提示 - 完全迁移自event_server.py
    """
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


# ========== 事件查询和管理端点 ==========

@router.get("/recent", response_model=Dict[str, Any])
async def get_recent_events_endpoint(
    event_service = Depends(get_event_service_dependency),
    limit: int = Query(10, ge=1, le=200, description="Number of events to return")
):
    """
    获取最近事件 - 兼容原event_server.py的/events/recent端点
    """
    try:
        # Get from event service
        result = await event_service.get_recent_events(limit)
        
        db_events = []
        if result.success:
            db_events = result.data.get("events", [])
        
        return {
            "total_memory_events": len(recent_events),
            "total_database_events": len(db_events),
            "memory_events": recent_events[-limit:],  # Last N events from memory
            "database_events": db_events,  # Events from database
            "event_types": list(set(event.get("event_type", "unknown") for event in recent_events)),
            "database_available": True
        }
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-type/{event_type}", response_model=Dict[str, Any])
async def get_events_by_type(
    event_type: str,
    event_service = Depends(get_event_service_dependency),
    limit: int = Query(20, ge=1, le=100, description="Number of events to return")
):
    """按类型获取事件"""
    try:
        result = await event_service.get_events_by_type(event_type, limit)
        
        if result.success:
            return {
                "success": True,
                "data": result.data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or f"Failed to get events by type {event_type}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get events by type error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/unprocessed", response_model=Dict[str, Any])
async def get_unprocessed_events(
    event_service = Depends(get_event_service_dependency),
    limit: int = Query(100, ge=1, le=500, description="Number of events to return")
):
    """获取未处理事件"""
    try:
        result = await event_service.get_unprocessed_events(limit)
        
        if result.success:
            return {
                "success": True,
                "data": result.data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Failed to get unprocessed events"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get unprocessed events error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{event_id}/process", response_model=Dict[str, Any])
async def process_event(
    event_id: str,
    event_service = Depends(get_event_service_dependency),
    agent_response: Optional[Dict[str, Any]] = None
):
    """处理事件"""
    try:
        result = await event_service.process_event(event_id, agent_response)
        
        if result.success:
            return {
                "success": True,
                "data": result.data,
                "message": "Event processed successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.error or "Event not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/statistics", response_model=Dict[str, Any])
async def get_event_statistics(
    event_service = Depends(get_event_service_dependency)
):
    """获取事件统计"""
    try:
        result = await event_service.get_event_statistics()
        
        if result.success:
            return {
                "success": True,
                "data": result.data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Failed to get event statistics"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get event statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ========== 创建事件端点 (需要认证) ==========

@router.post("/", response_model=Dict[str, Any])
async def create_event(
    event_data: Dict[str, Any],
    current_user: CurrentUser,
    event_service = Depends(get_event_service_dependency)
):
    """创建新事件 (需要用户认证)"""
    try:
        # Add user context
        event_data["user_id"] = current_user.user_id
        
        result = await event_service.create_event(event_data)
        
        if result.success:
            return {
                "success": True,
                "data": result.data,
                "message": "Event created successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to create event"
            )
            
    except Exception as e:
        logger.error(f"Create event error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )