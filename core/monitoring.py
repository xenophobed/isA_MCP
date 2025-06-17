#!/usr/bin/env python
"""
Monitoring components for MCP Server
Includes metrics tracking, rate limiting, and audit logging
"""
import time
import logging
from datetime import datetime
from typing import Dict

# Import here to avoid circular imports when needed
logger = logging.getLogger(__name__)

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
                   execution_time: float, security_level):
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
            "security_level": security_level.name if hasattr(security_level, 'name') else str(security_level)
        }
        
        self.request_history.append(request_log)
        
        # Keep only last 1000 requests
        if len(self.request_history) > 1000:
            self.request_history.pop(0)
    
    def check_rate_limit(self, tool_name: str, user_id: str, policy) -> bool:
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
            "uptime": time.time() - self.start_time
        }

# Global instance (will be initialized by the server)
monitor_manager = MonitoringManager()