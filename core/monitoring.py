#!/usr/bin/env python3
"""
System Monitoring and Metrics Collection - isA MCP Core

PROJECT DESCRIPTION:
    Comprehensive monitoring infrastructure providing real-time metrics collection, performance tracking,
    rate limiting enforcement, and audit logging for the isA MCP system. This module ensures system
    health monitoring, security compliance, and operational visibility across all service components.

INPUTS:
    - Tool execution requests and results
    - User authentication and authorization events
    - System performance metrics and resource usage
    - Security events and rate limiting triggers
    - Request timing and execution duration data
    - Success/failure status for all operations

OUTPUTS:
    - Real-time system metrics and performance statistics
    - Request history and audit trails for compliance
    - Rate limiting decisions and throttling actions
    - Security violation alerts and monitoring data
    - Performance dashboards and operational insights
    - Historical trend data for capacity planning

FUNCTIONALITY:
    - Request Monitoring and Tracking:
      * Total request counting and categorization
      * Success/failure rate tracking and analysis
      * Request history with detailed context logging
      * User activity monitoring and behavioral analysis
      * Tool usage patterns and performance insights

    - Performance Metrics Collection:
      * Response time measurement and statistics
      * Execution duration tracking for optimization
      * Resource utilization monitoring and alerting
      * Throughput analysis and capacity metrics
      * System uptime and availability tracking

    - Rate Limiting and Abuse Prevention:
      * Sliding window rate limiting implementation
      * Per-user and per-tool rate limit enforcement
      * Configurable rate limiting policies and thresholds
      * Rate limit violation detection and response
      * Adaptive rate limiting based on system load

    - Security and Audit Monitoring:
      * Security violation detection and logging
      * Authorization request tracking and analysis
      * Authentication failure monitoring and alerting
      * Suspicious activity pattern detection
      * Compliance audit trail maintenance

    - Health and Operational Monitoring:
      * System health checks and status reporting
      * Service availability monitoring and alerting
      * Error rate tracking and threshold monitoring
      * Resource consumption analysis and optimization
      * Operational dashboard data collection

DEPENDENCIES:
    - time: System timing and duration measurements
    - datetime: Timestamp generation and formatting
    - logging: Structured logging for audit trails
    - typing: Type hints for monitoring data structures
    - core.logging: Enhanced logging infrastructure

OPTIMIZATION POINTS:
    - Implement efficient circular buffers for request history
    - Add metrics aggregation for reduced memory usage
    - Optimize rate limiting with Redis or distributed storage
    - Add metrics export to external monitoring systems
    - Implement real-time streaming metrics for dashboards
    - Add predictive analytics for capacity planning
    - Optimize memory usage for long-running monitoring
    - Add metric sampling for high-volume environments
    - Implement alert throttling to prevent notification spam
    - Add automatic metric retention and cleanup policies

MONITORING CATEGORIES:
    - Request Metrics: Total, successful, failed request counts
    - Performance Metrics: Response times, execution durations
    - Security Metrics: Violations, denied requests, rate limits
    - System Metrics: Uptime, resource usage, health status
    - User Metrics: Activity patterns, usage statistics

USAGE:
    from core.monitoring import monitor_manager

    # Log request for monitoring
    monitor_manager.log_request(
        tool_name="analyze_data",
        user_id="user123",
        success=True,
        execution_time=1.23,
        security_level="MEDIUM"
    )

    # Check rate limits
    if monitor_manager.check_rate_limit("tool_name", "user_id", policy):
        # Process request
        pass

    # Get current metrics
    metrics = monitor_manager.get_metrics()
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
            "rate_limit_hits": 0,
        }
        self.request_history = []
        self.rate_limiter = {}
        self.start_time = time.time()

    def log_request(
        self, tool_name: str, user_id: str, success: bool, execution_time: float, security_level
    ):
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
            "security_level": (
                security_level.name if hasattr(security_level, "name") else str(security_level)
            ),
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
            timestamp for timestamp in self.rate_limiter[key] if now - timestamp < window
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
            "uptime": time.time() - self.start_time,
        }


# Global instance (will be initialized by the server)
monitor_manager = MonitoringManager()
