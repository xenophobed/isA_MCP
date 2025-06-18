#!/usr/bin/env python
"""
Monitoring Resources for MCP Server
Provides access to monitoring and system data as resources
"""
import json
from datetime import datetime

from core.monitoring import monitor_manager
from core.logging import get_logger

logger = get_logger(__name__)

def register_monitoring_resources(mcp):
    """Register all monitoring resources with the MCP server"""
    
    @mcp.resource("monitoring://metrics")
    async def get_metrics_resource() -> str:
        """Get monitoring metrics as resource"""
        metrics = monitor_manager.get_metrics()
        
        result = {
            "status": "success",
            "data": metrics,
            "retrieved_at": datetime.now().isoformat()
        }
        
        logger.info("Monitoring metrics resource accessed")
        return json.dumps(result)

    @mcp.resource("monitoring://health")
    async def get_health_status() -> str:
        """Get system health status"""
        metrics = monitor_manager.get_metrics()
        
        # Calculate health indicators
        total_requests = metrics.get("total_requests", 0)
        successful_requests = metrics.get("successful_requests", 0)
        failed_requests = metrics.get("failed_requests", 0)
        
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 100
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Determine health status
        if error_rate < 1:
            health_status = "HEALTHY"
        elif error_rate < 5:
            health_status = "WARNING"
        else:
            health_status = "CRITICAL"
        
        result = {
            "status": "success",
            "data": {
                "health_status": health_status,
                "success_rate": round(success_rate, 2),
                "error_rate": round(error_rate, 2),
                "total_requests": total_requests,
                "uptime": metrics.get("uptime", 0),
                "security_violations": metrics.get("security_violations", 0),
                "rate_limit_hits": metrics.get("rate_limit_hits", 0)
            },
            "retrieved_at": datetime.now().isoformat()
        }
        
        logger.info(f"Health status resource accessed: {health_status}")
        return json.dumps(result)

    @mcp.resource("monitoring://audit")
    async def get_audit_resource() -> str:
        """Get audit log as resource"""
        recent_logs = monitor_manager.request_history[-50:]  # Last 50 requests
        
        result = {
            "status": "success",
            "data": {
                "audit_logs": recent_logs,
                "count": len(recent_logs),
                "total_history_size": len(monitor_manager.request_history)
            },
            "retrieved_at": datetime.now().isoformat()
        }
        
        logger.info(f"Audit resource accessed: {len(recent_logs)} entries")
        return json.dumps(result)

    logger.info("Monitoring resources registered successfully") 