#!/usr/bin/env python
"""
Administration and monitoring tools for MCP Server
"""
import json
from datetime import datetime
from core.security import security_check, McpError

@security_check
async def get_authorization_requests(user_id: str = "admin") -> str:
    """Get pending authorization requests (admin only)"""
    if user_id != "admin":
        raise McpError("Unauthorized: Admin access required")
    
    from core.security import auth_manager, AuthorizationResult
    
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

@security_check
async def approve_authorization(request_id: str, approved_by: str = "admin") -> str:
    """Approve an authorization request"""
    from core.security import auth_manager
    
    success = auth_manager.approve_request(request_id, approved_by)
    
    return json.dumps({
        "status": "success" if success else "failed",
        "action": "approve_authorization",
        "data": {"request_id": request_id, "approved": success, "approved_by": approved_by},
        "timestamp": datetime.now().isoformat()
    })

@security_check
async def get_monitoring_metrics(user_id: str = "admin") -> str:
    """Get system monitoring metrics"""
    if user_id != "admin":
        raise McpError("Unauthorized: Admin access required")
    
    from core.monitoring import monitor_manager
    
    metrics = monitor_manager.get_metrics()
    
    return json.dumps({
        "status": "success",
        "action": "get_monitoring_metrics",
        "data": metrics,
        "timestamp": datetime.now().isoformat()
    })

@security_check  
async def get_audit_log(limit: int = 50, user_id: str = "admin") -> str:
    """Get audit log entries"""
    if user_id != "admin":
        raise McpError("Unauthorized: Admin access required")
    
    from core.monitoring import monitor_manager
    
    # Get from monitoring manager's request history
    recent_logs = monitor_manager.request_history[-limit:] if limit > 0 else monitor_manager.request_history
    
    return json.dumps({
        "status": "success",
        "action": "get_audit_log", 
        "data": {"logs": recent_logs, "count": len(recent_logs)},
        "timestamp": datetime.now().isoformat()
    })

async def get_metrics_resource() -> str:
    """Get monitoring metrics as resource"""
    from core.monitoring import monitor_manager
    
    return json.dumps({
        "status": "success",
        "data": monitor_manager.get_metrics(),
        "retrieved_at": datetime.now().isoformat()
    })