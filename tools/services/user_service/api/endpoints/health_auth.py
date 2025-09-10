"""
Health and Authentication Endpoints

Extracted from api_server.py lines 221-298
Contains all health check and authentication endpoints with full functionality preserved
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
from datetime import datetime
import sys
import os

# Add dependencies for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from api.dependencies import get_unified_auth_service, UnifiedAuthServiceDep

logger = logging.getLogger(__name__)

# Create routers
health_router = APIRouter(tags=["Health"])
auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@health_router.get("/")
async def root():
    """Root path health check"""
    return {
        "service": "User Management API",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@health_router.get("/health")
async def health_check(user_service=None):
    """Detailed health check"""
    try:
        if user_service:
            service_status = user_service.get_service_status()
        else:
            service_status = {"status": "service_not_initialized"}
            
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": service_status,
            "uptime": "operational"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@auth_router.get("/info")
async def get_auth_info(unified_auth_service: UnifiedAuthServiceDep):
    """Get authentication service information"""
    if unified_auth_service:
        return {
            "status": "multi-provider",
            "info": unified_auth_service.get_service_info(),
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        return {
            "status": "single-provider", 
            "auth0_available": auth0_service is not None,
            "supabase_available": supabase_service is not None,
            "timestamp": datetime.utcnow().isoformat()
        }


@auth_router.post("/dev-token")
async def generate_dev_token(user_id: str, email: str, unified_auth_service: UnifiedAuthServiceDep):
    """生成开发测试用的JWT token (仅Supabase)"""
    if not unified_auth_service or not unified_auth_service.supabase_service:
        raise HTTPException(
            status_code=404,
            detail="Development token generation not available (requires Supabase auth)"
        )
    
    try:
        token = await unified_auth_service.generate_dev_token(user_id, email)
        if token:
            return {
                "token": token,
                "user_id": user_id,
                "email": email,
                "expires_in": 3600,  # 1小时
                "provider": "supabase",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate token")
    except Exception as e:
        logger.error(f"Error generating dev token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")