"""
Context Extraction Utilities

Utilities for extracting context patterns and environment analysis
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter


class ContextExtractionUtils:
    """Utilities for extracting context-based patterns from user data"""
    
    @staticmethod
    def extract_context_signals(
        usage_records: List[Dict[str, Any]], 
        context_type: str
    ) -> Dict[str, Any]:
        """
        Extract context-specific signals from usage data
        
        Args:
            usage_records: List of usage records
            context_type: Type of context to analyze
            
        Returns:
            Dictionary of context signals and patterns
        """
        signals = {
            "usage_frequency": 0.0,
            "tool_diversity": 0.0,
            "session_intensity": 0.0,
            "temporal_consistency": 0.0,
            "context_purity": 0.0
        }
        
        if not usage_records:
            return signals
        
        # Calculate usage frequency (records per day)
        if usage_records:
            date_range = ContextExtractionUtils._get_date_range(usage_records)
            if date_range > 0:
                signals["usage_frequency"] = len(usage_records) / date_range
        
        # Calculate tool diversity
        unique_tools = set(record.get('tool_name') for record in usage_records if record.get('tool_name'))
        total_tool_uses = len([r for r in usage_records if r.get('tool_name')])
        
        if total_tool_uses > 0:
            signals["tool_diversity"] = len(unique_tools) / total_tool_uses
        
        # Calculate session intensity (average tokens per record)
        total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
        if usage_records:
            signals["session_intensity"] = total_tokens / len(usage_records)
        
        # Calculate temporal consistency
        signals["temporal_consistency"] = ContextExtractionUtils._calculate_temporal_consistency(
            usage_records
        )
        
        # Calculate context purity (how well records match the context)
        signals["context_purity"] = ContextExtractionUtils._calculate_context_purity(
            usage_records, context_type
        )
        
        return signals
    
    @staticmethod
    def _get_date_range(usage_records: List[Dict[str, Any]]) -> float:
        """Calculate the date range of usage records in days"""
        if not usage_records:
            return 0.0
        
        dates = []
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    dates.append(dt)
                except:
                    pass
        
        if len(dates) < 2:
            return 1.0  # Default to 1 day if insufficient data
        
        date_range = (max(dates) - min(dates)).days
        return max(1.0, date_range)  # At least 1 day
    
    @staticmethod
    def _calculate_temporal_consistency(usage_records: List[Dict[str, Any]]) -> float:
        """Calculate how consistent the temporal usage patterns are"""
        if len(usage_records) < 3:
            return 0.0
        
        # Group by hour of day
        hour_usage = defaultdict(int)
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    hour_usage[dt.hour] += 1
                except:
                    pass
        
        if not hour_usage:
            return 0.0
        
        # Calculate coefficient of variation (lower = more consistent)
        usage_counts = list(hour_usage.values())
        if len(usage_counts) < 2:
            return 1.0  # Perfect consistency if only one time period
        
        mean_usage = sum(usage_counts) / len(usage_counts)
        if mean_usage == 0:
            return 0.0
        
        variance = sum((count - mean_usage) ** 2 for count in usage_counts) / len(usage_counts)
        coefficient_variation = (variance ** 0.5) / mean_usage
        
        # Convert to consistency score (0-1, higher = more consistent)
        consistency = max(0.0, 1.0 - min(coefficient_variation, 1.0))
        return consistency
    
    @staticmethod
    def _calculate_context_purity(usage_records: List[Dict[str, Any]], context_type: str) -> float:
        """Calculate how purely the records match the given context"""
        if not usage_records:
            return 0.0
        
        # Context keywords for matching
        context_keywords = {
            "development": ["code", "debug", "test", "build", "git", "programming", "function"],
            "analysis": ["analyze", "data", "statistics", "insights", "metrics", "chart"],
            "research": ["search", "research", "investigate", "study", "explore", "find"],
            "document": ["document", "text", "pdf", "write", "edit", "format", "summary"],
            "memory": ["memory", "recall", "remember", "store", "knowledge", "context"]
        }
        
        keywords = context_keywords.get(context_type, [])
        if not keywords:
            return 1.0  # If no keywords defined, assume perfect match
        
        matching_records = 0
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            event_type = record.get('event_type', '').lower()
            
            searchable_text = f"{endpoint} {tool_name} {event_type}"
            
            if any(keyword in searchable_text for keyword in keywords):
                matching_records += 1
        
        return matching_records / len(usage_records)
    
    @staticmethod
    def identify_context_transitions(
        usage_records: List[Dict[str, Any]], 
        time_window_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Identify transitions between different contexts
        
        Args:
            usage_records: List of usage records (should be sorted by time)
            time_window_minutes: Time window for grouping records
            
        Returns:
            List of context transitions with timestamps and descriptions
        """
        if len(usage_records) < 2:
            return []
        
        # Group records into time windows
        time_windows = []
        current_window = []
        current_window_start = None
        
        for record in usage_records:
            created_at = record.get('created_at')
            if not created_at:
                continue
            
            try:
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    dt = created_at
            except:
                continue
            
            # Start new window if needed
            if (not current_window_start or 
                (dt - current_window_start).total_seconds() > time_window_minutes * 60):
                
                if current_window:
                    time_windows.append((current_window_start, current_window))
                
                current_window = [record]
                current_window_start = dt
            else:
                current_window.append(record)
        
        # Add final window
        if current_window:
            time_windows.append((current_window_start, current_window))
        
        # Identify context for each window
        window_contexts = []
        for window_start, window_records in time_windows:
            context = ContextExtractionUtils._identify_window_context(window_records)
            window_contexts.append((window_start, context, window_records))
        
        # Find transitions
        transitions = []
        for i in range(1, len(window_contexts)):
            prev_start, prev_context, prev_records = window_contexts[i-1]
            curr_start, curr_context, curr_records = window_contexts[i]
            
            if prev_context != curr_context:
                transitions.append({
                    "timestamp": curr_start,
                    "from_context": prev_context,
                    "to_context": curr_context,
                    "transition_type": ContextExtractionUtils._classify_transition(
                        prev_context, curr_context
                    ),
                    "duration_minutes": (curr_start - prev_start).total_seconds() / 60,
                    "records_before": len(prev_records),
                    "records_after": len(curr_records)
                })
        
        return transitions
    
    @staticmethod
    def _identify_window_context(window_records: List[Dict[str, Any]]) -> str:
        """Identify the primary context for a group of records"""
        if not window_records:
            return "unknown"
        
        # Count context indicators
        context_scores = defaultdict(int)
        
        context_indicators = {
            "development": ["code", "debug", "test", "build", "git", "programming"],
            "analysis": ["analyze", "data", "statistics", "insights", "metrics"],
            "research": ["search", "research", "investigate", "study", "explore"],
            "document": ["document", "text", "pdf", "write", "edit", "format"],
            "memory": ["memory", "recall", "remember", "store", "knowledge"]
        }
        
        for record in window_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            event_type = record.get('event_type', '').lower()
            
            searchable_text = f"{endpoint} {tool_name} {event_type}"
            
            for context, indicators in context_indicators.items():
                score = sum(1 for indicator in indicators if indicator in searchable_text)
                context_scores[context] += score
        
        if not context_scores:
            return "general"
        
        # Return context with highest score
        return max(context_scores, key=context_scores.get)
    
    @staticmethod
    def _classify_transition(from_context: str, to_context: str) -> str:
        """Classify the type of context transition"""
        # Define transition patterns
        focused_contexts = {"development", "analysis", "research"}
        support_contexts = {"memory", "document", "general"}
        
        if from_context in focused_contexts and to_context in support_contexts:
            return "focus_to_support"
        elif from_context in support_contexts and to_context in focused_contexts:
            return "support_to_focus"
        elif from_context in focused_contexts and to_context in focused_contexts:
            return "focus_switch"
        elif from_context in support_contexts and to_context in support_contexts:
            return "support_switch"
        else:
            return "general_transition"
    
    @staticmethod
    def calculate_context_stability(
        usage_records: List[Dict[str, Any]], 
        time_window_hours: int = 24
    ) -> Dict[str, float]:
        """
        Calculate stability metrics for context usage
        
        Args:
            usage_records: List of usage records
            time_window_hours: Time window for stability calculation
            
        Returns:
            Dictionary with stability metrics
        """
        stability_metrics = {
            "context_persistence": 0.0,  # How long contexts are maintained
            "switch_frequency": 0.0,     # How often contexts switch
            "dominant_context_ratio": 0.0  # Ratio of most common context
        }
        
        if not usage_records:
            return stability_metrics
        
        # Identify context transitions
        transitions = ContextExtractionUtils.identify_context_transitions(
            usage_records, time_window_minutes=time_window_hours * 60
        )
        
        if not transitions:
            # No transitions = very stable (single context)
            stability_metrics["context_persistence"] = 1.0
            stability_metrics["switch_frequency"] = 0.0
            stability_metrics["dominant_context_ratio"] = 1.0
            return stability_metrics
        
        # Calculate context persistence (average time in each context)
        total_transition_time = sum(t["duration_minutes"] for t in transitions)
        if transitions:
            avg_context_duration = total_transition_time / len(transitions)
            # Normalize to 0-1 scale (60 minutes = 0.5, 240 minutes = 1.0)
            stability_metrics["context_persistence"] = min(1.0, avg_context_duration / 240.0)
        
        # Calculate switch frequency (transitions per hour)
        if usage_records:
            date_range_hours = ContextExtractionUtils._get_date_range(usage_records) * 24
            switches_per_hour = len(transitions) / max(1.0, date_range_hours)
            # Normalize: 0 switches/hour = 1.0 stability, 1+ switches/hour = 0.0 stability
            stability_metrics["switch_frequency"] = max(0.0, 1.0 - switches_per_hour)
        
        # Calculate dominant context ratio
        context_counts = defaultdict(int)
        for record in usage_records:
            context = ContextExtractionUtils._identify_window_context([record])
            context_counts[context] += 1
        
        if context_counts:
            most_common_count = max(context_counts.values())
            total_count = sum(context_counts.values())
            stability_metrics["dominant_context_ratio"] = most_common_count / total_count
        
        return stability_metrics
    
    @staticmethod
    def extract_context_performance_metrics(
        usage_records: List[Dict[str, Any]], 
        context_type: str
    ) -> Dict[str, float]:
        """
        Extract performance metrics specific to a context
        
        Args:
            usage_records: List of usage records
            context_type: Context type to analyze
            
        Returns:
            Dictionary with context-specific performance metrics
        """
        metrics = {
            "success_rate": 0.0,
            "avg_response_time": 0.0,
            "efficiency_score": 0.0,
            "error_rate": 0.0,
            "throughput": 0.0
        }
        
        if not usage_records:
            return metrics
        
        # Calculate success rate
        successful_records = sum(
            1 for record in usage_records
            if record.get('response_data', {}).get('success', True)
        )
        metrics["success_rate"] = successful_records / len(usage_records)
        
        # Calculate error rate
        metrics["error_rate"] = 1.0 - metrics["success_rate"]
        
        # Calculate efficiency score (tokens per minute approximation)
        total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
        if usage_records:
            # Estimate time range
            date_range_minutes = ContextExtractionUtils._get_date_range(usage_records) * 24 * 60
            if date_range_minutes > 0:
                metrics["throughput"] = total_tokens / date_range_minutes
            
            # Efficiency = tokens per API call (higher = more efficient)
            avg_tokens_per_call = total_tokens / len(usage_records)
            # Normalize to 0-1 scale (500+ tokens per call = very efficient)
            metrics["efficiency_score"] = min(1.0, avg_tokens_per_call / 500.0)
        
        return metrics