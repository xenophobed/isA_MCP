#!/usr/bin/env python
"""
Rate Limiter for Web Services
Manages rate limiting across different domains and services with intelligent throttling
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests: int
    window_seconds: int
    burst_limit: Optional[int] = None
    
    def __post_init__(self):
        if self.burst_limit is None:
            self.burst_limit = self.requests * 2

class RateLimiter:
    """Advanced rate limiter with domain-specific and service-specific limits"""
    
    def __init__(self):
        # Track requests per domain/service
        self.request_history: Dict[str, List[float]] = {}
        
        # Rate limit configurations
        self.rate_limits = {
            # Search engines
            "search_google": RateLimit(requests=10, window_seconds=60, burst_limit=15),
            "search_bing": RateLimit(requests=15, window_seconds=60, burst_limit=20),
            "search_duckduckgo": RateLimit(requests=20, window_seconds=60, burst_limit=30),
            
            # Social media platforms
            "social_twitter": RateLimit(requests=5, window_seconds=300, burst_limit=8),
            "social_facebook": RateLimit(requests=5, window_seconds=300, burst_limit=8),
            "social_linkedin": RateLimit(requests=8, window_seconds=300, burst_limit=12),
            
            # E-commerce
            "ecommerce_amazon": RateLimit(requests=10, window_seconds=60, burst_limit=15),
            "ecommerce_ebay": RateLimit(requests=15, window_seconds=60, burst_limit=20),
            "ecommerce_shopify": RateLimit(requests=20, window_seconds=60, burst_limit=30),
            
            # General web crawling
            "crawl": RateLimit(requests=30, window_seconds=60, burst_limit=50),
            
            # Monitoring
            "monitor": RateLimit(requests=100, window_seconds=60, burst_limit=150),
            
            # Default limits
            "default": RateLimit(requests=20, window_seconds=60, burst_limit=30)
        }
        
        # Domain-specific overrides
        self.domain_limits = {
            "google.com": "search_google",
            "bing.com": "search_bing", 
            "duckduckgo.com": "search_duckduckgo",
            "twitter.com": "social_twitter",
            "x.com": "social_twitter",
            "facebook.com": "social_facebook",
            "linkedin.com": "social_linkedin",
            "amazon.com": "ecommerce_amazon",
            "ebay.com": "ecommerce_ebay"
        }
        
        # Adaptive delays based on response patterns
        self.adaptive_delays: Dict[str, float] = {}
        self.error_counts: Dict[str, int] = {}
        self.last_error_time: Dict[str, float] = {}
    
    def _get_rate_limit_config(self, identifier: str) -> RateLimit:
        """Get rate limit configuration for identifier"""
        # Check if it's a domain
        for domain, limit_type in self.domain_limits.items():
            if domain in identifier:
                return self.rate_limits[limit_type]
        
        # Check if it's a direct service identifier
        if identifier in self.rate_limits:
            return self.rate_limits[identifier]
        
        # Return default
        return self.rate_limits["default"]
    
    def _clean_old_requests(self, identifier: str, window_seconds: int):
        """Remove old requests outside the time window"""
        if identifier not in self.request_history:
            self.request_history[identifier] = []
        
        now = time.time()
        cutoff_time = now - window_seconds
        
        self.request_history[identifier] = [
            req_time for req_time in self.request_history[identifier]
            if req_time > cutoff_time
        ]
    
    def _calculate_adaptive_delay(self, identifier: str) -> float:
        """Calculate adaptive delay based on error patterns"""
        base_delay = self.adaptive_delays.get(identifier, 1.0)
        error_count = self.error_counts.get(identifier, 0)
        last_error = self.last_error_time.get(identifier, 0)
        
        # Increase delay if recent errors
        if error_count > 0 and time.time() - last_error < 300:  # 5 minutes
            base_delay *= (1 + error_count * 0.5)
        
        # Gradually reduce delay if no recent errors
        if time.time() - last_error > 600:  # 10 minutes
            base_delay *= 0.9
            self.error_counts[identifier] = max(0, error_count - 1)
        
        # Keep delay within reasonable bounds
        base_delay = max(0.5, min(30.0, base_delay))
        self.adaptive_delays[identifier] = base_delay
        
        return base_delay
    
    async def wait_for_rate_limit(self, identifier: str) -> bool:
        """Wait if necessary to respect rate limits"""
        config = self._get_rate_limit_config(identifier)
        self._clean_old_requests(identifier, config.window_seconds)
        
        current_requests = len(self.request_history[identifier])
        
        # Check if we're at the limit
        if current_requests >= config.requests:
            # Calculate wait time
            oldest_request = min(self.request_history[identifier])
            wait_time = config.window_seconds - (time.time() - oldest_request)
            
            if wait_time > 0:
                logger.info(f"Rate limit reached for {identifier}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                
                # Clean up again after waiting
                self._clean_old_requests(identifier, config.window_seconds)
        
        # Add adaptive delay
        adaptive_delay = self._calculate_adaptive_delay(identifier)
        if adaptive_delay > 1.0:
            logger.debug(f"Applying adaptive delay of {adaptive_delay:.2f}s for {identifier}")
            await asyncio.sleep(adaptive_delay)
        
        # Record this request
        self.request_history[identifier].append(time.time())
        
        return True
    
    def can_make_request(self, identifier: str) -> bool:
        """Check if a request can be made without waiting"""
        config = self._get_rate_limit_config(identifier)
        self._clean_old_requests(identifier, config.window_seconds)
        
        current_requests = len(self.request_history[identifier])
        return current_requests < config.requests
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get number of remaining requests in current window"""
        config = self._get_rate_limit_config(identifier)
        self._clean_old_requests(identifier, config.window_seconds)
        
        current_requests = len(self.request_history[identifier])
        return max(0, config.requests - current_requests)
    
    def get_reset_time(self, identifier: str) -> float:
        """Get time until rate limit resets"""
        config = self._get_rate_limit_config(identifier)
        self._clean_old_requests(identifier, config.window_seconds)
        
        if identifier not in self.request_history or not self.request_history[identifier]:
            return 0.0
        
        oldest_request = min(self.request_history[identifier])
        reset_time = config.window_seconds - (time.time() - oldest_request)
        
        return max(0.0, reset_time)
    
    def record_error(self, identifier: str, error_type: str = "generic"):
        """Record an error for adaptive rate limiting"""
        self.error_counts[identifier] = self.error_counts.get(identifier, 0) + 1
        self.last_error_time[identifier] = time.time()
        
        # Increase adaptive delay based on error type
        current_delay = self.adaptive_delays.get(identifier, 1.0)
        
        if error_type in ["timeout", "connection_error"]:
            self.adaptive_delays[identifier] = current_delay * 1.5
        elif error_type in ["rate_limited", "too_many_requests"]:
            self.adaptive_delays[identifier] = current_delay * 2.0
        elif error_type in ["server_error", "503", "502"]:
            self.adaptive_delays[identifier] = current_delay * 1.2
        else:
            self.adaptive_delays[identifier] = current_delay * 1.1
        
        logger.warning(f"Recorded error for {identifier}: {error_type}, new delay: {self.adaptive_delays[identifier]:.2f}s")
    
    def record_success(self, identifier: str):
        """Record a successful request for adaptive optimization"""
        # Gradually reduce adaptive delay on success
        current_delay = self.adaptive_delays.get(identifier, 1.0)
        if current_delay > 1.0:
            self.adaptive_delays[identifier] = current_delay * 0.95
    
    def add_custom_limit(self, identifier: str, requests: int, window_seconds: int, burst_limit: Optional[int] = None):
        """Add custom rate limit configuration"""
        self.rate_limits[identifier] = RateLimit(
            requests=requests,
            window_seconds=window_seconds,
            burst_limit=burst_limit or requests * 2
        )
        logger.info(f"Added custom rate limit for {identifier}: {requests} req/{window_seconds}s")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status"""
        status = {
            "active_identifiers": list(self.request_history.keys()),
            "rate_limits": {},
            "adaptive_delays": self.adaptive_delays.copy(),
            "error_counts": self.error_counts.copy()
        }
        
        # Get current status for each active identifier
        for identifier in self.request_history.keys():
            config = self._get_rate_limit_config(identifier)
            status["rate_limits"][identifier] = {
                "requests_made": len(self.request_history[identifier]),
                "requests_limit": config.requests,
                "remaining_requests": self.get_remaining_requests(identifier),
                "reset_time_seconds": self.get_reset_time(identifier),
                "window_seconds": config.window_seconds,
                "can_make_request": self.can_make_request(identifier)
            }
        
        return status
    
    def reset_identifier(self, identifier: str):
        """Reset rate limiting for specific identifier"""
        if identifier in self.request_history:
            del self.request_history[identifier]
        if identifier in self.adaptive_delays:
            del self.adaptive_delays[identifier]
        if identifier in self.error_counts:
            del self.error_counts[identifier]
        if identifier in self.last_error_time:
            del self.last_error_time[identifier]
        
        logger.info(f"Reset rate limiting for {identifier}")
    
    def cleanup_old_data(self):
        """Clean up old tracking data"""
        current_time = time.time()
        cleanup_cutoff = current_time - 3600  # 1 hour
        
        # Clean up old request histories
        for identifier in list(self.request_history.keys()):
            self.request_history[identifier] = [
                req_time for req_time in self.request_history[identifier]
                if req_time > cleanup_cutoff
            ]
            if not self.request_history[identifier]:
                del self.request_history[identifier]
        
        # Clean up old error times
        for identifier in list(self.last_error_time.keys()):
            if current_time - self.last_error_time[identifier] > 3600:
                del self.last_error_time[identifier]
                if identifier in self.error_counts:
                    del self.error_counts[identifier]
        
        logger.debug("Cleaned up old rate limiting data")