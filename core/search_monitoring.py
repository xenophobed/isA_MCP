#!/usr/bin/env python3
"""
Search Service Monitoring and Metrics
Provides monitoring, metrics, and health checks for the unified search service
"""

import asyncio
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class SearchMetrics:
    """Search performance metrics"""
    total_searches: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    fallback_searches: int = 0
    cached_searches: int = 0
    avg_response_time_ms: float = 0.0
    avg_results_per_search: float = 0.0
    total_response_time_ms: float = 0.0
    last_reset: datetime = None
    
    def __post_init__(self):
        if self.last_reset is None:
            self.last_reset = datetime.now()

class SearchMonitor:
    """Monitors search service performance and health"""
    
    def __init__(self):
        self.metrics = SearchMetrics()
        self.recent_searches = []  # Rolling window of recent searches
        self.max_recent_searches = 100
        self.health_check_interval = 60  # seconds
        self.last_health_check = time.time()

        # Performance thresholds - read from environment
        # Convert GRAPH_SLOW_THRESHOLD from seconds to milliseconds
        slow_threshold_seconds = float(os.getenv("GRAPH_SLOW_THRESHOLD", "5.0"))
        self.slow_search_threshold_ms = slow_threshold_seconds * 1000  # Convert to ms
        self.error_rate_threshold = 0.1  # 10%
        
    def record_search(self, response_time_ms: float, results_count: int, 
                     success: bool = True, used_cache: bool = False, 
                     used_fallback: bool = False):
        """Record a search operation"""
        try:
            self.metrics.total_searches += 1
            self.metrics.total_response_time_ms += response_time_ms
            
            if success:
                self.metrics.successful_searches += 1
            else:
                self.metrics.failed_searches += 1
                
            if used_cache:
                self.metrics.cached_searches += 1
                
            if used_fallback:
                self.metrics.fallback_searches += 1
            
            # Update averages
            if self.metrics.total_searches > 0:
                self.metrics.avg_response_time_ms = (
                    self.metrics.total_response_time_ms / self.metrics.total_searches
                )
                
                total_results = sum(s.get('results_count', 0) for s in self.recent_searches)
                total_results += results_count
                self.metrics.avg_results_per_search = total_results / self.metrics.total_searches
            
            # Add to recent searches
            search_record = {
                'timestamp': time.time(),
                'response_time_ms': response_time_ms,
                'results_count': results_count,
                'success': success,
                'used_cache': used_cache,
                'used_fallback': used_fallback
            }
            
            self.recent_searches.append(search_record)
            
            # Trim recent searches to max size
            if len(self.recent_searches) > self.max_recent_searches:
                self.recent_searches = self.recent_searches[-self.max_recent_searches:]
                
            # Log slow searches
            if response_time_ms > self.slow_search_threshold_ms:
                logger.warning(f"Slow search detected: {response_time_ms:.1f}ms")
                
        except Exception as e:
            logger.error(f"Error recording search metrics: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        try:
            metrics_dict = asdict(self.metrics)
            
            # Add calculated metrics
            metrics_dict.update({
                'success_rate': (
                    self.metrics.successful_searches / max(self.metrics.total_searches, 1)
                ),
                'error_rate': (
                    self.metrics.failed_searches / max(self.metrics.total_searches, 1)
                ),
                'cache_hit_rate': (
                    self.metrics.cached_searches / max(self.metrics.total_searches, 1)
                ),
                'fallback_rate': (
                    self.metrics.fallback_searches / max(self.metrics.total_searches, 1)
                ),
                'uptime_hours': (
                    (datetime.now() - self.metrics.last_reset).total_seconds() / 3600
                )
            })
            
            return metrics_dict
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {}
    
    def get_recent_performance(self, minutes: int = 5) -> Dict[str, Any]:
        """Get performance metrics for recent time window"""
        try:
            cutoff_time = time.time() - (minutes * 60)
            recent = [s for s in self.recent_searches if s['timestamp'] > cutoff_time]
            
            if not recent:
                return {
                    'window_minutes': minutes,
                    'total_searches': 0,
                    'avg_response_time_ms': 0,
                    'success_rate': 0,
                    'cache_hit_rate': 0
                }
            
            total_searches = len(recent)
            successful = sum(1 for s in recent if s['success'])
            cached = sum(1 for s in recent if s['used_cache'])
            avg_response_time = sum(s['response_time_ms'] for s in recent) / total_searches
            
            return {
                'window_minutes': minutes,
                'total_searches': total_searches,
                'avg_response_time_ms': avg_response_time,
                'success_rate': successful / total_searches,
                'cache_hit_rate': cached / total_searches,
                'searches_per_minute': total_searches / minutes
            }
            
        except Exception as e:
            logger.error(f"Error getting recent performance: {e}")
            return {}
    
    def check_health(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            current_time = time.time()
            
            # Only check periodically
            if current_time - self.last_health_check < self.health_check_interval:
                return {'status': 'ok', 'last_check': self.last_health_check}
            
            self.last_health_check = current_time
            
            health_status = {
                'status': 'ok',
                'timestamp': current_time,
                'checks': {}
            }
            
            # Check error rate
            metrics = self.get_metrics()
            error_rate = metrics.get('error_rate', 0)
            
            if error_rate > self.error_rate_threshold:
                health_status['status'] = 'warning'
                health_status['checks']['error_rate'] = {
                    'status': 'warning',
                    'value': error_rate,
                    'threshold': self.error_rate_threshold,
                    'message': f'Error rate {error_rate:.1%} exceeds threshold {self.error_rate_threshold:.1%}'
                }
            else:
                health_status['checks']['error_rate'] = {
                    'status': 'ok',
                    'value': error_rate,
                    'threshold': self.error_rate_threshold
                }
            
            # Check recent performance
            recent_perf = self.get_recent_performance(5)
            avg_response_time = recent_perf.get('avg_response_time_ms', 0)
            
            if avg_response_time > self.slow_search_threshold_ms:
                health_status['status'] = 'warning'
                health_status['checks']['response_time'] = {
                    'status': 'warning',
                    'value': avg_response_time,
                    'threshold': self.slow_search_threshold_ms,
                    'message': f'Average response time {avg_response_time:.1f}ms exceeds threshold {self.slow_search_threshold_ms}ms'
                }
            else:
                health_status['checks']['response_time'] = {
                    'status': 'ok',
                    'value': avg_response_time,
                    'threshold': self.slow_search_threshold_ms
                }
            
            # Check search activity
            recent_searches = recent_perf.get('total_searches', 0)
            health_status['checks']['activity'] = {
                'status': 'ok',
                'recent_searches_5min': recent_searches,
                'message': f'{recent_searches} searches in last 5 minutes'
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {
                'status': 'error',
                'timestamp': time.time(),
                'error': str(e)
            }
    
    def reset_metrics(self):
        """Reset all metrics"""
        try:
            self.metrics = SearchMetrics()
            self.recent_searches.clear()
            logger.info("Search metrics reset")
            
        except Exception as e:
            logger.error(f"Error resetting metrics: {e}")
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get comprehensive diagnostic information"""
        try:
            return {
                'metrics': self.get_metrics(),
                'recent_5min': self.get_recent_performance(5),
                'recent_15min': self.get_recent_performance(15),
                'recent_60min': self.get_recent_performance(60),
                'health': self.check_health(),
                'configuration': {
                    'slow_search_threshold_ms': self.slow_search_threshold_ms,
                    'error_rate_threshold': self.error_rate_threshold,
                    'max_recent_searches': self.max_recent_searches,
                    'health_check_interval': self.health_check_interval
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting diagnostic info: {e}")
            return {'error': str(e)}

# Global monitor instance
_search_monitor = None

def get_search_monitor() -> SearchMonitor:
    """Get global search monitor instance"""
    global _search_monitor
    if _search_monitor is None:
        _search_monitor = SearchMonitor()
    return _search_monitor

def log_search_operation(response_time_ms: float, results_count: int, 
                        success: bool = True, used_cache: bool = False, 
                        used_fallback: bool = False):
    """Convenience function to log search operations"""
    monitor = get_search_monitor()
    monitor.record_search(response_time_ms, results_count, success, used_cache, used_fallback)