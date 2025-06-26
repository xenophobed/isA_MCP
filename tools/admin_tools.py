#!/usr/bin/env python
"""
Admin Tools for MCP Server
Handles authorization, monitoring, and security operations
"""
import json
from datetime import datetime

from core.security import get_security_manager
from core.monitoring import monitor_manager
from core.logging import get_logger
from core.exception import McpError

logger = get_logger(__name__)

def register_admin_tools(mcp):
    """Register all admin tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    async def get_authorization_requests(user_id: str = "admin") -> str:
        """Get pending authorization requests (admin only)"""
        if user_id != "admin":
            raise McpError("Unauthorized: Admin access required")
        
        security_manager = get_security_manager()
        auth_manager = security_manager.auth_manager
        
        requests = []
        for req_id, request in auth_manager.pending_requests.items():
            if request.status.value == "pending":
                requests.append({
                    "id": req_id,
                    "tool_name": request.tool_name,
                    "user_id": request.user_id,
                    "security_level": request.security_level.name,
                    "reason": request.reason,
                    "timestamp": request.timestamp.isoformat(),
                    "expires_at": request.expires_at.isoformat()
                })
        
        result = {
            "status": "success",
            "action": "get_authorization_requests",
            "data": {"requests": requests, "count": len(requests)},
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Authorization requests retrieved by {user_id}")
        return json.dumps(result)

    @mcp.tool()
    @security_manager.security_check
    async def approve_authorization(request_id: str, approved_by: str = "admin") -> str:
        """Approve an authorization request"""
        auth_manager = security_manager.auth_manager
        
        success = auth_manager.approve_request(request_id, approved_by)
        
        result = {
            "status": "success" if success else "failed",
            "action": "approve_authorization",
            "data": {"request_id": request_id, "approved": success, "approved_by": approved_by},
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Authorization request {request_id} {'approved' if success else 'failed'} by {approved_by}")
        return json.dumps(result)

    @mcp.tool()
    @security_manager.security_check
    async def get_monitoring_metrics(user_id: str = "admin") -> str:
        """Get system monitoring metrics"""
        if user_id != "admin":
            raise McpError("Unauthorized: Admin access required")
        
        metrics = monitor_manager.get_metrics()
        
        result = {
            "status": "success",
            "action": "get_monitoring_metrics",
            "data": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Monitoring metrics retrieved by {user_id}")
        return json.dumps(result)

    @mcp.tool()
    @security_manager.security_check
    async def get_audit_log(limit: int = 50, user_id: str = "admin") -> str:
        """Get audit log entries"""
        if user_id != "admin":
            raise McpError("Unauthorized: Admin access required")
        
        # Get from monitoring manager's request history
        recent_logs = monitor_manager.request_history[-limit:] if limit > 0 else monitor_manager.request_history
        
        result = {
            "status": "success",
            "action": "get_audit_log", 
            "data": {"logs": recent_logs, "count": len(recent_logs)},
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Audit log retrieved by {user_id} (limit: {limit})")
        return json.dumps(result) 