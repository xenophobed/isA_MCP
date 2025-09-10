"""
Session Management Endpoints

Session-related functionality extracted from api_server.py
Handles session creation, management, messages, and memory
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

from models import SessionCreate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Sessions"])


@router.post("/api/v1/users/{user_id}/sessions", response_model=Dict[str, Any])
async def create_session(
    user_id: str,
    session_data: SessionCreate,
    current_user=None,
    session_service=None
):
    """Create session - Original: api_server.py lines 755-794"""
    try:
        if not current_user or not session_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to create session for this user")
            
        result = await session_service.create_session(session_data)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "session": result.data.dict(),
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/api/v1/users/{user_id}/sessions", response_model=Dict[str, Any])
async def get_user_sessions(
    user_id: str,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user=None,
    session_service=None
):
    """Get user sessions - Original: api_server.py lines 795-825"""
    try:
        if not current_user or not session_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view sessions for this user")
            
        result = await session_service.get_user_sessions(
            user_id=user_id,
            active_only=active_only,
            limit=limit,
            offset=offset
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "sessions": [session.dict() for session in result.data],
            "count": len(result.data),
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user sessions: {str(e)}")


@router.put("/api/v1/sessions/{session_id}/status", response_model=Dict[str, Any])
async def update_session_status(
    session_id: str,
    status: str,
    current_user=None,
    session_service=None
):
    """Update session status - Original: api_server.py lines 826-849"""
    try:
        if not current_user or not session_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Verify user owns this session
        session_result = await session_service.get_session(session_id)
        if not session_result.is_success:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session_result.data.user_id != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this session")
            
        result = await session_service.update_session_status(session_id, status)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "session_id": session_id,
            "new_status": status,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update session status: {str(e)}")


@router.post("/api/v1/sessions/{session_id}/messages", response_model=Dict[str, Any])
async def add_session_message(
    session_id: str,
    role: str,
    content: str,
    message_type: str = "chat",
    tokens_used: int = 0,
    cost_usd: float = 0.0,
    current_user=None,
    session_service=None
):
    """Add session message - Original: api_server.py lines 850-884"""
    try:
        if not current_user or not session_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Verify user owns this session
        session_result = await session_service.get_session(session_id)
        if not session_result.is_success:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session_result.data.user_id != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Not authorized to add messages to this session")
            
        result = await session_service.add_session_message(
            session_id=session_id,
            role=role,
            content=content,
            message_type=message_type,
            tokens_used=tokens_used,
            cost_usd=cost_usd
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "message": result.data.dict(),
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding session message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add session message: {str(e)}")


@router.get("/api/v1/sessions/{session_id}/messages", response_model=Dict[str, Any])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user=None,
    session_service=None
):
    """Get session messages - Original: api_server.py lines 885-915"""
    try:
        if not current_user or not session_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Verify user owns this session
        session_result = await session_service.get_session(session_id)
        if not session_result.is_success:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session_result.data.user_id != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Not authorized to view messages for this session")
            
        result = await session_service.get_session_messages(
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "messages": [message.dict() for message in result.data],
            "count": len(result.data),
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session messages: {str(e)}")


@router.get("/api/v1/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(
    session_id: str,
    current_user=None,
    session_service=None
):
    """Get session details - Original: api_server.py lines 918-946"""
    try:
        if not current_user or not session_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        result = await session_service.get_session(session_id)
        
        if not result.is_success:
            raise HTTPException(status_code=404, detail=result.message)
            
        # Verify user owns this session
        if result.data.user_id != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Not authorized to view this session")
            
        return {
            "session": result.data.dict(),
            "message": "Session retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")