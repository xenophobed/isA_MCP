"""
Pattern Extraction Utilities

Common utilities for extracting patterns from user data
"""

from typing import Dict, Any, List, Optional, Tuple
from collections import Counter, defaultdict
import statistics
from datetime import datetime


class PatternExtractionUtils:
    """Utilities for extracting behavioral patterns from user data"""
    
    @staticmethod
    def extract_usage_patterns(usage_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract usage patterns from usage records
        
        Args:
            usage_records: List of usage record dictionaries
            
        Returns:
            Dictionary containing extracted patterns
        """
        if not usage_records:
            return {
                "endpoint_frequency": {},
                "event_type_distribution": {},
                "tool_usage": {},
                "cost_patterns": {},
                "token_usage": {}
            }
        
        patterns = {
            "endpoint_frequency": Counter(),
            "event_type_distribution": Counter(),
            "tool_usage": Counter(),
            "cost_patterns": {"total_cost": 0.0, "avg_cost_per_call": 0.0},
            "token_usage": {"total_tokens": 0, "avg_tokens_per_call": 0}
        }
        
        total_cost = 0.0
        total_tokens = 0
        
        for record in usage_records:
            # Extract endpoint patterns
            endpoint = record.get('endpoint', 'unknown')
            patterns["endpoint_frequency"][endpoint] += 1
            
            # Extract event type patterns
            event_type = record.get('event_type', 'unknown')
            patterns["event_type_distribution"][event_type] += 1
            
            # Extract tool usage patterns
            tool_name = record.get('tool_name')
            if tool_name:
                patterns["tool_usage"][tool_name] += 1
            
            # Cost analysis
            cost = record.get('cost_usd', 0.0)
            if isinstance(cost, (int, float)):
                total_cost += cost
            
            # Token analysis
            tokens = record.get('tokens_used', 0)
            if isinstance(tokens, int):
                total_tokens += tokens
        
        # Calculate averages
        record_count = len(usage_records)
        patterns["cost_patterns"]["total_cost"] = total_cost
        patterns["cost_patterns"]["avg_cost_per_call"] = total_cost / record_count
        patterns["token_usage"]["total_tokens"] = total_tokens
        patterns["token_usage"]["avg_tokens_per_call"] = total_tokens / record_count
        
        # Convert Counters to regular dicts for JSON serialization
        patterns["endpoint_frequency"] = dict(patterns["endpoint_frequency"])
        patterns["event_type_distribution"] = dict(patterns["event_type_distribution"])
        patterns["tool_usage"] = dict(patterns["tool_usage"])
        
        return patterns
    
    @staticmethod
    def calculate_success_failure_patterns(
        usage_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate success and failure patterns from usage data
        
        Args:
            usage_records: List of usage records
            
        Returns:
            Dictionary with success/failure analysis
        """
        patterns = {
            "overall_success_rate": 0.0,
            "success_by_endpoint": {},
            "success_by_tool": {},
            "failure_indicators": [],
            "error_patterns": {}
        }
        
        if not usage_records:
            return patterns
        
        endpoint_stats = defaultdict(lambda: {"success": 0, "total": 0})
        tool_stats = defaultdict(lambda: {"success": 0, "total": 0})
        error_patterns = Counter()
        
        total_records = len(usage_records)
        successful_records = 0
        
        for record in usage_records:
            endpoint = record.get('endpoint', 'unknown')
            tool_name = record.get('tool_name')
            
            # Determine success based on response data or error indicators
            is_success = PatternExtractionUtils._is_successful_operation(record)
            
            if is_success:
                successful_records += 1
                endpoint_stats[endpoint]["success"] += 1
                if tool_name:
                    tool_stats[tool_name]["success"] += 1
            else:
                # Extract error patterns
                error_type = PatternExtractionUtils._extract_error_type(record)
                if error_type:
                    error_patterns[error_type] += 1
            
            endpoint_stats[endpoint]["total"] += 1
            if tool_name:
                tool_stats[tool_name]["total"] += 1
        
        # Calculate overall success rate
        patterns["overall_success_rate"] = successful_records / total_records
        
        # Calculate success rates by endpoint
        for endpoint, stats in endpoint_stats.items():
            patterns["success_by_endpoint"][endpoint] = (
                stats["success"] / stats["total"] if stats["total"] > 0 else 0.0
            )
        
        # Calculate success rates by tool
        for tool, stats in tool_stats.items():
            patterns["success_by_tool"][tool] = (
                stats["success"] / stats["total"] if stats["total"] > 0 else 0.0
            )
        
        # Identify failure indicators
        patterns["failure_indicators"] = [
            endpoint for endpoint, rate in patterns["success_by_endpoint"].items()
            if rate < 0.8  # Endpoints with less than 80% success rate
        ]
        
        patterns["error_patterns"] = dict(error_patterns)
        
        return patterns
    
    @staticmethod
    def _is_successful_operation(record: Dict[str, Any]) -> bool:
        """Determine if a usage record represents a successful operation"""
        # Check for explicit success indicators
        response_data = record.get('response_data')
        if isinstance(response_data, dict):
            # Look for error indicators in response
            if 'error' in response_data or 'exception' in response_data:
                return False
            # Look for success indicators
            if 'success' in response_data and response_data['success']:
                return True
        
        # Check cost and token usage (successful operations usually have these)
        cost = record.get('cost_usd', 0.0)
        tokens = record.get('tokens_used', 0)
        
        # If there's cost or token usage, likely successful
        if cost > 0 or tokens > 0:
            return True
        
        # Default to success if no clear failure indicators
        return True
    
    @staticmethod
    def _extract_error_type(record: Dict[str, Any]) -> Optional[str]:
        """Extract error type from a failed operation record"""
        response_data = record.get('response_data')
        if isinstance(response_data, dict):
            if 'error' in response_data:
                error = response_data['error']
                if isinstance(error, str):
                    # Extract common error types
                    if 'timeout' in error.lower():
                        return 'timeout'
                    elif 'permission' in error.lower() or 'unauthorized' in error.lower():
                        return 'permission_denied'
                    elif 'rate' in error.lower() and 'limit' in error.lower():
                        return 'rate_limit'
                    elif 'not found' in error.lower():
                        return 'not_found'
                    else:
                        return 'unknown_error'
        
        return None
    
    @staticmethod
    def detect_preference_patterns(
        usage_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect user preference patterns from usage data
        
        Args:
            usage_records: List of usage records
            
        Returns:
            Dictionary with detected preferences
        """
        if not usage_records:
            return {"preferred_tools": [], "preferred_endpoints": [], "preferences_confidence": 0.0}
        
        # Count usage frequency
        tool_usage = Counter()
        endpoint_usage = Counter()
        provider_usage = Counter()
        
        for record in usage_records:
            tool_name = record.get('tool_name')
            if tool_name:
                tool_usage[tool_name] += 1
            
            endpoint = record.get('endpoint')
            if endpoint:
                endpoint_usage[endpoint] += 1
            
            provider = record.get('provider')
            if provider:
                provider_usage[provider] += 1
        
        # Identify top preferences (tools/endpoints used more than average)
        total_records = len(usage_records)
        
        # Calculate preferences based on frequency
        preferred_tools = []
        if tool_usage:
            avg_tool_usage = sum(tool_usage.values()) / len(tool_usage)
            preferred_tools = [
                tool for tool, count in tool_usage.items()
                if count > avg_tool_usage * 1.2  # 20% above average
            ]
        
        preferred_endpoints = []
        if endpoint_usage:
            avg_endpoint_usage = sum(endpoint_usage.values()) / len(endpoint_usage)
            preferred_endpoints = [
                endpoint for endpoint, count in endpoint_usage.items()
                if count > avg_endpoint_usage * 1.2
            ]
        
        preferred_providers = []
        if provider_usage:
            avg_provider_usage = sum(provider_usage.values()) / len(provider_usage)
            preferred_providers = [
                provider for provider, count in provider_usage.items()
                if count > avg_provider_usage * 1.2
            ]
        
        # Calculate confidence based on data quantity and distribution clarity
        confidence = PatternExtractionUtils._calculate_preference_confidence(
            usage_records, tool_usage, endpoint_usage
        )
        
        return {
            "preferred_tools": preferred_tools,
            "preferred_endpoints": preferred_endpoints,
            "preferred_providers": preferred_providers,
            "tool_usage_distribution": dict(tool_usage),
            "endpoint_usage_distribution": dict(endpoint_usage),
            "provider_usage_distribution": dict(provider_usage),
            "preferences_confidence": confidence
        }
    
    @staticmethod
    def _calculate_preference_confidence(
        usage_records: List[Dict[str, Any]],
        tool_usage: Counter,
        endpoint_usage: Counter
    ) -> float:
        """Calculate confidence in detected preferences"""
        base_confidence = 0.5
        
        # Data quantity factor
        record_count = len(usage_records)
        if record_count >= 100:
            base_confidence += 0.3
        elif record_count >= 50:
            base_confidence += 0.2
        elif record_count >= 20:
            base_confidence += 0.1
        elif record_count < 10:
            base_confidence -= 0.2
        
        # Distribution clarity factor
        if tool_usage:
            # Check if there are clear favorites (high variance in usage)
            usage_counts = list(tool_usage.values())
            if len(usage_counts) > 1:
                mean_usage = statistics.mean(usage_counts)
                variance = statistics.variance(usage_counts)
                cv = (variance ** 0.5) / mean_usage if mean_usage > 0 else 0
                
                # Higher coefficient of variation = clearer preferences
                if cv > 1.0:
                    base_confidence += 0.15
                elif cv > 0.5:
                    base_confidence += 0.1
        
        return max(0.0, min(1.0, base_confidence))