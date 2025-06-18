#!/usr/bin/env python
"""
Security components for MCP Server
Includes authorization, security policies, and decorators
"""
from typing import Dict, Any, Optional
import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from functools import wraps

# Import from our core modules
from .exception import McpError, AuthorizationError, RateLimitError, SecurityViolationError
from .logging import get_logger

logger = get_logger(__name__)

class SecurityLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class AuthorizationResult(Enum):
    APPROVED = "approved"
    DENIED = "denied"  
    PENDING = "pending"
    EXPIRED = "expired"

@dataclass
class AuthorizationRequest:
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    user_id: str
    timestamp: datetime
    security_level: SecurityLevel
    reason: str
    expires_at: datetime
    status: AuthorizationResult = AuthorizationResult.PENDING
    approved_by: Optional[str] = None
    
class SecurityPolicy:
    def __init__(self):
        self.tool_policies = {
            # High security tools require authorization
            "remember": SecurityLevel.MEDIUM,
            "forget": SecurityLevel.HIGH,
            "update_memory": SecurityLevel.MEDIUM,
            "search_memories": SecurityLevel.LOW,
            "get_weather": SecurityLevel.LOW,
            "calculate": SecurityLevel.MEDIUM,
            "get_current_time": SecurityLevel.LOW,
            "analyze_sentiment": SecurityLevel.LOW,
        }
        
        self.forbidden_patterns = [
            r"password",
            r"secret",
            r"api_key",
            r"private_key",
            r"token",
            r"delete.*database",
            r"drop.*table"
        ]
        
        self.rate_limits = {
            "default": {"calls": 100, "window": 3600},  # 100 calls per hour
            "remember": {"calls": 50, "window": 3600},   # 50 calls per hour
            "forget": {"calls": 10, "window": 3600},     # 10 calls per hour
        }

class AuthorizationManager:
    def __init__(self):
        self.pending_requests: Dict[str, AuthorizationRequest] = {}
        self.approved_cache: Dict[str, datetime] = {}
        
    def create_request(self, tool_name: str, arguments: Dict, user_id: str, 
                      security_level: SecurityLevel, reason: str) -> AuthorizationRequest:
        """Create a new authorization request"""
        request_id = hashlib.md5(
            f"{tool_name}:{json.dumps(arguments, sort_keys=True)}:{user_id}:{time.time()}"
            .encode()
        ).hexdigest()
        
        request = AuthorizationRequest(
            id=request_id,
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
            timestamp=datetime.now(),
            security_level=security_level,
            reason=reason,
            expires_at=datetime.now() + timedelta(minutes=30)  # 30 min expiry
        )
        
        self.pending_requests[request_id] = request
        return request
    
    def approve_request(self, request_id: str, approved_by: str) -> bool:
        """Approve an authorization request"""
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            if datetime.now() < request.expires_at:
                request.status = AuthorizationResult.APPROVED
                request.approved_by = approved_by
                
                # Cache approval for similar requests
                cache_key = f"{request.tool_name}:{hashlib.md5(json.dumps(request.arguments, sort_keys=True).encode()).hexdigest()}"
                self.approved_cache[cache_key] = datetime.now() + timedelta(hours=1)
                
                # Debug logging
                print(f"✅ Approved request {request_id}")
                print(f"✅ Tool: {request.tool_name}, Args: {request.arguments}")
                print(f"✅ Cache key: {cache_key}")
                print(f"✅ Cached until: {self.approved_cache[cache_key]}")
                
                return True
            else:
                request.status = AuthorizationResult.EXPIRED
        return False
    
    def deny_request(self, request_id: str) -> bool:
        """Deny an authorization request"""
        if request_id in self.pending_requests:
            self.pending_requests[request_id].status = AuthorizationResult.DENIED
            return True
        return False
    
    def is_pre_approved(self, tool_name: str, arguments: Dict) -> bool:
        """Check if similar request was recently approved"""
        # First check cache
        cache_key = f"{tool_name}:{hashlib.md5(json.dumps(arguments, sort_keys=True).encode()).hexdigest()}"
        if cache_key in self.approved_cache:
            return datetime.now() < self.approved_cache[cache_key]
        
        # Also check if there's a recently approved request for this tool/args combo
        # Use more flexible matching - check if the core arguments match
        for request in self.pending_requests.values():
            if (request.tool_name == tool_name and 
                request.status == AuthorizationResult.APPROVED and
                datetime.now() < request.expires_at):
                
                # Check if the essential arguments match (ignore user_id differences)
                request_args = {k: v for k, v in request.arguments.items() if k != 'user_id'}
                current_args = {k: v for k, v in arguments.items() if k != 'user_id'}
                
                if request_args == current_args:
                    return True
        
        return False

class SecurityManager:
    """Main security manager that combines authorization and monitoring"""
    
    def __init__(self, monitoring_manager=None):
        self.auth_manager = AuthorizationManager()
        self.policy = SecurityPolicy()
        self.monitoring_manager = monitoring_manager
    

        
    def require_authorization(self, security_level: SecurityLevel = SecurityLevel.MEDIUM):
        """Decorator to require authorization for sensitive tools"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Get user context (in real implementation, extract from request context)
                user_id = kwargs.get('user_id', 'default_user')
                
                # Check if pre-approved
                tool_name = func.__name__
                if self.auth_manager.is_pre_approved(tool_name, kwargs):
                    logger.info(f"Tool {tool_name} pre-approved for user {user_id}")
                    return await func(*args, **kwargs)
                
                # Create authorization request
                reason = f"Tool {tool_name} requires {security_level.name} level authorization"
                auth_request = self.auth_manager.create_request(
                    tool_name, kwargs, user_id, security_level, reason
                )
                
                if self.monitoring_manager:
                    self.monitoring_manager.metrics["authorization_requests"] += 1
                
                # In real implementation, this would trigger external authorization flow
                # For demo, we'll simulate immediate approval for non-critical tools
                if security_level in [SecurityLevel.LOW, SecurityLevel.MEDIUM]:
                    self.auth_manager.approve_request(auth_request.id, "auto_approval")
                    logger.info(f"Auto-approved {tool_name} for user {user_id}")
                    return await func(*args, **kwargs)
                else:
                    # For HIGH security tools, check if already approved
                    if self.auth_manager.is_pre_approved(tool_name, kwargs):
                        logger.info(f"Tool {tool_name} pre-approved for user {user_id}")
                        return await func(*args, **kwargs)
                    
                    # Not approved - require client-side authorization
                    raise AuthorizationError(
                        f"Authorization required for {tool_name}. Request ID: {auth_request.id}",
                        {
                            "request_id": auth_request.id, 
                            "reason": reason,
                            "tool_name": tool_name,
                            "tool_args": kwargs,
                            "security_level": security_level.name
                        }
                    )
            
            return wrapper
        return decorator

    def security_check(self, func):
        """Decorator for security checks"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            user_id = kwargs.get('user_id', 'default_user')
            tool_name = func.__name__
            
            try:
                # Rate limiting
                if self.monitoring_manager and not self.monitoring_manager.check_rate_limit(tool_name, user_id, self.policy):
                    if self.monitoring_manager:
                        self.monitoring_manager.log_request(tool_name, user_id, False, 0, SecurityLevel.HIGH)
                    raise RateLimitError(f"Rate limit exceeded for {tool_name}")
                
                # Security pattern check
                content_to_check = json.dumps(kwargs)
                for pattern in self.policy.forbidden_patterns:
                    if re.search(pattern, content_to_check, re.IGNORECASE):
                        if self.monitoring_manager:
                            self.monitoring_manager.metrics["security_violations"] += 1
                            self.monitoring_manager.log_request(tool_name, user_id, False, 0, SecurityLevel.CRITICAL)
                        raise SecurityViolationError(f"Security violation: forbidden pattern detected")
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Log successful execution
                execution_time = time.time() - start_time
                security_level = self.policy.tool_policies.get(tool_name, SecurityLevel.LOW)
                if self.monitoring_manager:
                    self.monitoring_manager.log_request(tool_name, user_id, True, execution_time, security_level)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                security_level = self.policy.tool_policies.get(tool_name, SecurityLevel.LOW)
                if self.monitoring_manager:
                    self.monitoring_manager.log_request(tool_name, user_id, False, execution_time, security_level)
                raise
        
        return wrapper

# Global instances - will be initialized with monitoring manager
security_policy = SecurityPolicy()
authorization_manager = AuthorizationManager()

# This will be initialized by the server with proper monitoring manager
security_manager: Optional[SecurityManager] = None

def initialize_security(monitoring_manager=None) -> SecurityManager:
    """Initialize security manager with monitoring integration"""
    global security_manager
    security_manager = SecurityManager(monitoring_manager)
    return security_manager

def get_security_manager() -> SecurityManager:
    """Get the global security manager instance"""
    if security_manager is None:
        raise RuntimeError("Security manager not initialized. Call initialize_security() first.")
    return security_manager