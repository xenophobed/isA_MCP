"""
Environment Modeling Utilities

Utilities for modeling user environments and contextual factors
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
from dataclasses import dataclass


@dataclass
class EnvironmentProfile:
    """Represents a user's environment profile"""
    primary_tools: List[str]
    preferred_contexts: List[str] 
    working_hours: Tuple[int, int]  # (start_hour, end_hour)
    collaboration_level: float  # 0.0 = individual, 1.0 = highly collaborative
    multitasking_tendency: float  # 0.0 = focused, 1.0 = high multitasking
    technical_proficiency: float  # 0.0 = basic, 1.0 = expert
    context_switch_tolerance: float  # 0.0 = low tolerance, 1.0 = high tolerance


class EnvironmentModelingUtils:
    """Utilities for modeling user environments and contextual factors"""
    
    @staticmethod
    def build_environment_profile(
        usage_records: List[Dict[str, Any]],
        session_records: List[Dict[str, Any]] = None,
        memory_records: List[Dict[str, Any]] = None
    ) -> EnvironmentProfile:
        """
        Build a comprehensive environment profile for a user
        
        Args:
            usage_records: List of usage records
            session_records: List of session records (optional)
            memory_records: List of memory records (optional)
            
        Returns:
            EnvironmentProfile object with user's environmental characteristics
        """
        if not usage_records:
            return EnvironmentProfile(
                primary_tools=[],
                preferred_contexts=[],
                working_hours=(9, 17),
                collaboration_level=0.5,
                multitasking_tendency=0.5,
                technical_proficiency=0.5,
                context_switch_tolerance=0.5
            )
        
        # Extract primary tools
        primary_tools = EnvironmentModelingUtils._extract_primary_tools(usage_records)
        
        # Identify preferred contexts
        preferred_contexts = EnvironmentModelingUtils._identify_preferred_contexts(usage_records)
        
        # Determine working hours
        working_hours = EnvironmentModelingUtils._determine_working_hours(usage_records)
        
        # Calculate collaboration level
        collaboration_level = EnvironmentModelingUtils._calculate_collaboration_level(
            usage_records, session_records or []
        )
        
        # Assess multitasking tendency
        multitasking_tendency = EnvironmentModelingUtils._assess_multitasking_tendency(
            usage_records, session_records or []
        )
        
        # Evaluate technical proficiency
        technical_proficiency = EnvironmentModelingUtils._evaluate_technical_proficiency(
            usage_records
        )
        
        # Measure context switch tolerance
        context_switch_tolerance = EnvironmentModelingUtils._measure_context_switch_tolerance(
            usage_records
        )
        
        return EnvironmentProfile(
            primary_tools=primary_tools,
            preferred_contexts=preferred_contexts,
            working_hours=working_hours,
            collaboration_level=collaboration_level,
            multitasking_tendency=multitasking_tendency,
            technical_proficiency=technical_proficiency,
            context_switch_tolerance=context_switch_tolerance
        )
    
    @staticmethod
    def _extract_primary_tools(usage_records: List[Dict[str, Any]]) -> List[str]:
        """Extract the most frequently used tools"""
        tool_counts = Counter()
        
        for record in usage_records:
            tool_name = record.get('tool_name')
            if tool_name:
                tool_counts[tool_name] += 1
        
        # Return top 5 most used tools
        return [tool for tool, count in tool_counts.most_common(5)]
    
    @staticmethod
    def _identify_preferred_contexts(usage_records: List[Dict[str, Any]]) -> List[str]:
        """Identify the user's preferred working contexts"""
        context_scores = defaultdict(int)
        
        # Context keywords for identification
        context_patterns = {
            "development": ["code", "debug", "test", "build", "git", "programming", "function", "class"],
            "analysis": ["analyze", "data", "statistics", "insights", "metrics", "chart", "report"],
            "research": ["search", "research", "investigate", "study", "explore", "find", "query"],
            "documentation": ["document", "text", "pdf", "write", "edit", "format", "summary", "note"],
            "collaboration": ["share", "team", "review", "discuss", "meeting", "chat", "communicate"],
            "learning": ["learn", "tutorial", "example", "help", "guide", "instruction", "understand"]
        }
        
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            event_type = record.get('event_type', '').lower()
            
            searchable_text = f"{endpoint} {tool_name} {event_type}"
            
            for context, patterns in context_patterns.items():
                score = sum(1 for pattern in patterns if pattern in searchable_text)
                context_scores[context] += score
        
        # Return contexts sorted by preference
        return [context for context, score in sorted(context_scores.items(), 
                                                   key=lambda x: x[1], reverse=True) if score > 0]
    
    @staticmethod
    def _determine_working_hours(usage_records: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Determine the user's typical working hours"""
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
                    continue
        
        if not hour_usage:
            return (9, 17)  # Default business hours
        
        # Find the range with 70% of activity
        sorted_hours = sorted(hour_usage.items(), key=lambda x: x[1], reverse=True)
        total_usage = sum(hour_usage.values())
        target_usage = total_usage * 0.7
        
        selected_hours = []
        cumulative_usage = 0
        
        for hour, usage in sorted_hours:
            selected_hours.append(hour)
            cumulative_usage += usage
            if cumulative_usage >= target_usage:
                break
        
        if selected_hours:
            start_hour = min(selected_hours)
            end_hour = max(selected_hours)
            return (start_hour, end_hour)
        
        return (9, 17)
    
    @staticmethod
    def _calculate_collaboration_level(
        usage_records: List[Dict[str, Any]], 
        session_records: List[Dict[str, Any]]
    ) -> float:
        """Calculate how collaborative the user's work style is"""
        collaboration_indicators = 0
        total_indicators = len(usage_records)
        
        if total_indicators == 0:
            return 0.5
        
        collaboration_keywords = [
            "share", "team", "review", "discuss", "meeting", "chat", 
            "communicate", "collaborate", "merge", "pull", "request"
        ]
        
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            event_type = record.get('event_type', '').lower()
            
            searchable_text = f"{endpoint} {tool_name} {event_type}"
            
            if any(keyword in searchable_text for keyword in collaboration_keywords):
                collaboration_indicators += 1
        
        # Check for concurrent sessions (indicates collaboration)
        concurrent_sessions = 0
        for i, session in enumerate(session_records):
            overlapping = 0
            session_start = session.get('created_at')
            session_end = session.get('ended_at')
            
            if not session_start or not session_end:
                continue
            
            for other_session in session_records[i+1:]:
                other_start = other_session.get('created_at')
                other_end = other_session.get('ended_at')
                
                if not other_start or not other_end:
                    continue
                
                # Check for overlap
                if (session_start <= other_end and session_end >= other_start):
                    overlapping += 1
            
            concurrent_sessions += min(overlapping, 1)  # Binary indicator per session
        
        base_collaboration = collaboration_indicators / total_indicators
        
        # Boost collaboration score if concurrent sessions detected
        if session_records:
            session_boost = min(0.3, concurrent_sessions / len(session_records))
            base_collaboration = min(1.0, base_collaboration + session_boost)
        
        return base_collaboration
    
    @staticmethod
    def _assess_multitasking_tendency(
        usage_records: List[Dict[str, Any]], 
        session_records: List[Dict[str, Any]]
    ) -> float:
        """Assess the user's tendency to multitask"""
        if not usage_records:
            return 0.5
        
        # Calculate tool switching frequency
        tool_switches = 0
        prev_tool = None
        
        for record in sorted(usage_records, key=lambda x: x.get('created_at', '')):
            current_tool = record.get('tool_name')
            if prev_tool and current_tool and prev_tool != current_tool:
                tool_switches += 1
            prev_tool = current_tool
        
        if len(usage_records) > 1:
            switch_rate = tool_switches / (len(usage_records) - 1)
        else:
            switch_rate = 0
        
        # Calculate context switches within short time windows
        quick_switches = 0
        for i in range(1, len(usage_records)):
            current = usage_records[i]
            previous = usage_records[i-1]
            
            try:
                current_time = datetime.fromisoformat(
                    current.get('created_at', '').replace('Z', '+00:00')
                )
                previous_time = datetime.fromisoformat(
                    previous.get('created_at', '').replace('Z', '+00:00')
                )
                
                # If tool switch within 5 minutes, consider it rapid multitasking
                if (current_time - previous_time).total_seconds() < 300:  # 5 minutes
                    if current.get('tool_name') != previous.get('tool_name'):
                        quick_switches += 1
            except:
                continue
        
        quick_switch_rate = quick_switches / max(1, len(usage_records))
        
        # Combine metrics
        multitasking_score = (switch_rate * 0.6 + quick_switch_rate * 0.4)
        return min(1.0, multitasking_score * 2)  # Scale up for sensitivity
    
    @staticmethod
    def _evaluate_technical_proficiency(usage_records: List[Dict[str, Any]]) -> float:
        """Evaluate the user's technical proficiency level"""
        if not usage_records:
            return 0.5
        
        # Technical indicators
        technical_keywords = [
            "debug", "test", "build", "deploy", "git", "api", "database", "query",
            "function", "class", "method", "variable", "algorithm", "optimization"
        ]
        
        advanced_keywords = [
            "architecture", "design", "pattern", "refactor", "performance", 
            "scalability", "security", "integration", "automation", "pipeline"
        ]
        
        basic_score = 0
        advanced_score = 0
        total_records = len(usage_records)
        
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            event_type = record.get('event_type', '').lower()
            
            searchable_text = f"{endpoint} {tool_name} {event_type}"
            
            # Count technical indicators
            basic_matches = sum(1 for keyword in technical_keywords if keyword in searchable_text)
            advanced_matches = sum(1 for keyword in advanced_keywords if keyword in searchable_text)
            
            if basic_matches > 0:
                basic_score += 1
            if advanced_matches > 0:
                advanced_score += 1
        
        # Calculate proficiency
        basic_ratio = basic_score / total_records
        advanced_ratio = advanced_score / total_records
        
        # Weight advanced usage more heavily
        proficiency = (basic_ratio * 0.4 + advanced_ratio * 0.6)
        return min(1.0, proficiency * 1.5)  # Scale for better distribution
    
    @staticmethod
    def _measure_context_switch_tolerance(usage_records: List[Dict[str, Any]]) -> float:
        """Measure how well the user tolerates context switches"""
        if len(usage_records) < 3:
            return 0.5
        
        # Identify context switches and measure performance after switches
        context_switches = []
        contexts = []
        
        # First, identify context for each record
        for record in usage_records:
            context = EnvironmentModelingUtils._identify_record_context(record)
            contexts.append(context)
        
        # Find context switches and measure subsequent performance
        switch_performance = []
        
        for i in range(1, len(contexts)):
            if contexts[i] != contexts[i-1]:
                # This is a context switch
                switch_time = usage_records[i].get('created_at')
                
                # Measure performance in next few records
                performance_window = usage_records[i:i+3]  # Next 3 records
                performance_score = EnvironmentModelingUtils._calculate_performance_score(
                    performance_window
                )
                
                switch_performance.append(performance_score)
        
        if not switch_performance:
            return 0.7  # Default moderate tolerance
        
        # High tolerance = consistent performance after switches
        avg_performance = sum(switch_performance) / len(switch_performance)
        performance_variance = sum(
            (score - avg_performance) ** 2 for score in switch_performance
        ) / len(switch_performance)
        
        # Low variance = high tolerance
        tolerance = max(0.0, 1.0 - performance_variance)
        return tolerance
    
    @staticmethod
    def _identify_record_context(record: Dict[str, Any]) -> str:
        """Identify the context of a single record"""
        endpoint = record.get('endpoint', '').lower()
        tool_name = record.get('tool_name', '').lower()
        event_type = record.get('event_type', '').lower()
        
        searchable_text = f"{endpoint} {tool_name} {event_type}"
        
        context_patterns = {
            "development": ["code", "debug", "test", "build", "git"],
            "analysis": ["analyze", "data", "statistics", "metrics"],
            "research": ["search", "research", "investigate", "explore"],
            "documentation": ["document", "text", "write", "edit"]
        }
        
        for context, patterns in context_patterns.items():
            if any(pattern in searchable_text for pattern in patterns):
                return context
        
        return "general"
    
    @staticmethod
    def _calculate_performance_score(records: List[Dict[str, Any]]) -> float:
        """Calculate a performance score for a set of records"""
        if not records:
            return 0.5
        
        # Use tokens used and success rate as performance indicators
        total_tokens = sum(record.get('tokens_used', 0) for record in records)
        successful_records = sum(
            1 for record in records 
            if record.get('response_data', {}).get('success', True)
        )
        
        success_rate = successful_records / len(records)
        avg_tokens = total_tokens / len(records) if records else 0
        
        # Normalize tokens (higher tokens often indicate more complex/successful tasks)
        token_score = min(1.0, avg_tokens / 500)  # 500 tokens as baseline
        
        # Combine success rate and token usage
        performance_score = (success_rate * 0.7 + token_score * 0.3)
        return performance_score
    
    @staticmethod
    def analyze_environment_trends(
        usage_records: List[Dict[str, Any]], 
        time_window_days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze trends in the user's environment over time
        
        Args:
            usage_records: List of usage records
            time_window_days: Size of time window for trend analysis
            
        Returns:
            Dictionary with trend analysis results
        """
        trends = {
            "tool_usage_trends": {},
            "context_preference_trends": {},
            "productivity_trends": {},
            "collaboration_trends": {},
            "skill_development_trends": {}
        }
        
        if not usage_records:
            return trends
        
        # Sort records by time
        sorted_records = sorted(
            usage_records, 
            key=lambda x: x.get('created_at', '')
        )
        
        # Create time windows
        windows = EnvironmentModelingUtils._create_time_windows(
            sorted_records, time_window_days
        )
        
        # Analyze trends for each metric
        trends["tool_usage_trends"] = EnvironmentModelingUtils._analyze_tool_trends(windows)
        trends["context_preference_trends"] = EnvironmentModelingUtils._analyze_context_trends(windows)
        trends["productivity_trends"] = EnvironmentModelingUtils._analyze_productivity_trends(windows)
        trends["collaboration_trends"] = EnvironmentModelingUtils._analyze_collaboration_trends(windows)
        trends["skill_development_trends"] = EnvironmentModelingUtils._analyze_skill_trends(windows)
        
        return trends
    
    @staticmethod
    def _create_time_windows(
        records: List[Dict[str, Any]], 
        window_days: int
    ) -> List[List[Dict[str, Any]]]:
        """Create time-based windows of records"""
        if not records:
            return []
        
        windows = []
        current_window = []
        window_start = None
        
        for record in records:
            created_at = record.get('created_at')
            if not created_at:
                continue
            
            try:
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    dt = created_at
                
                if window_start is None:
                    window_start = dt
                    current_window = [record]
                elif (dt - window_start).days < window_days:
                    current_window.append(record)
                else:
                    # Start new window
                    if current_window:
                        windows.append(current_window)
                    current_window = [record]
                    window_start = dt
            except:
                continue
        
        # Add final window
        if current_window:
            windows.append(current_window)
        
        return windows
    
    @staticmethod
    def _analyze_tool_trends(windows: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze trends in tool usage"""
        tool_usage_by_window = []
        
        for window in windows:
            tool_counts = Counter()
            for record in window:
                tool_name = record.get('tool_name')
                if tool_name:
                    tool_counts[tool_name] += 1
            tool_usage_by_window.append(dict(tool_counts))
        
        return {
            "windows": tool_usage_by_window,
            "trending_up": EnvironmentModelingUtils._identify_increasing_tools(tool_usage_by_window),
            "trending_down": EnvironmentModelingUtils._identify_decreasing_tools(tool_usage_by_window)
        }
    
    @staticmethod
    def _analyze_context_trends(windows: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze trends in context preferences"""
        context_by_window = []
        
        for window in windows:
            context_counts = defaultdict(int)
            for record in window:
                context = EnvironmentModelingUtils._identify_record_context(record)
                context_counts[context] += 1
            context_by_window.append(dict(context_counts))
        
        return {
            "windows": context_by_window,
            "shifting_preferences": EnvironmentModelingUtils._identify_preference_shifts(context_by_window)
        }
    
    @staticmethod
    def _analyze_productivity_trends(windows: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze productivity trends over time"""
        productivity_by_window = []
        
        for window in windows:
            if not window:
                productivity_by_window.append(0.0)
                continue
            
            total_tokens = sum(record.get('tokens_used', 0) for record in window)
            avg_tokens_per_record = total_tokens / len(window)
            productivity_by_window.append(avg_tokens_per_record)
        
        return {
            "productivity_scores": productivity_by_window,
            "trend_direction": EnvironmentModelingUtils._calculate_trend_direction(productivity_by_window)
        }
    
    @staticmethod
    def _analyze_collaboration_trends(windows: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze collaboration trends"""
        collaboration_by_window = []
        
        collaboration_keywords = ["share", "team", "review", "discuss", "collaborate"]
        
        for window in windows:
            if not window:
                collaboration_by_window.append(0.0)
                continue
            
            collaborative_records = 0
            for record in window:
                searchable_text = f"{record.get('endpoint', '')} {record.get('tool_name', '')}"
                if any(keyword in searchable_text.lower() for keyword in collaboration_keywords):
                    collaborative_records += 1
            
            collaboration_ratio = collaborative_records / len(window)
            collaboration_by_window.append(collaboration_ratio)
        
        return {
            "collaboration_ratios": collaboration_by_window,
            "trend_direction": EnvironmentModelingUtils._calculate_trend_direction(collaboration_by_window)
        }
    
    @staticmethod
    def _analyze_skill_trends(windows: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze skill development trends"""
        skill_by_window = []
        
        for window in windows:
            skill_score = EnvironmentModelingUtils._evaluate_technical_proficiency(window)
            skill_by_window.append(skill_score)
        
        return {
            "skill_scores": skill_by_window,
            "trend_direction": EnvironmentModelingUtils._calculate_trend_direction(skill_by_window),
            "skill_velocity": EnvironmentModelingUtils._calculate_skill_velocity(skill_by_window)
        }
    
    @staticmethod
    def _identify_increasing_tools(tool_usage_windows: List[Dict[str, int]]) -> List[str]:
        """Identify tools with increasing usage"""
        if len(tool_usage_windows) < 2:
            return []
        
        increasing_tools = []
        all_tools = set()
        for window in tool_usage_windows:
            all_tools.update(window.keys())
        
        for tool in all_tools:
            recent_usage = tool_usage_windows[-1].get(tool, 0)
            earlier_usage = tool_usage_windows[-2].get(tool, 0)
            
            if recent_usage > earlier_usage:
                increasing_tools.append(tool)
        
        return increasing_tools
    
    @staticmethod
    def _identify_decreasing_tools(tool_usage_windows: List[Dict[str, int]]) -> List[str]:
        """Identify tools with decreasing usage"""
        if len(tool_usage_windows) < 2:
            return []
        
        decreasing_tools = []
        all_tools = set()
        for window in tool_usage_windows:
            all_tools.update(window.keys())
        
        for tool in all_tools:
            recent_usage = tool_usage_windows[-1].get(tool, 0)
            earlier_usage = tool_usage_windows[-2].get(tool, 0)
            
            if recent_usage < earlier_usage and earlier_usage > 0:
                decreasing_tools.append(tool)
        
        return decreasing_tools
    
    @staticmethod
    def _identify_preference_shifts(context_windows: List[Dict[str, int]]) -> Dict[str, str]:
        """Identify shifts in context preferences"""
        if len(context_windows) < 2:
            return {}
        
        recent_prefs = context_windows[-1]
        earlier_prefs = context_windows[-2]
        
        shifts = {}
        all_contexts = set(recent_prefs.keys()) | set(earlier_prefs.keys())
        
        for context in all_contexts:
            recent = recent_prefs.get(context, 0)
            earlier = earlier_prefs.get(context, 0)
            
            if recent > earlier * 1.5:  # 50% increase
                shifts[context] = "increasing"
            elif recent < earlier * 0.5:  # 50% decrease
                shifts[context] = "decreasing"
        
        return shifts
    
    @staticmethod
    def _calculate_trend_direction(values: List[float]) -> str:
        """Calculate overall trend direction"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend
        increases = 0
        decreases = 0
        
        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                increases += 1
            elif values[i] < values[i-1]:
                decreases += 1
        
        if increases > decreases:
            return "increasing"
        elif decreases > increases:
            return "decreasing"
        else:
            return "stable"
    
    @staticmethod
    def _calculate_skill_velocity(skill_scores: List[float]) -> float:
        """Calculate the rate of skill development"""
        if len(skill_scores) < 2:
            return 0.0
        
        # Calculate average change between windows
        changes = []
        for i in range(1, len(skill_scores)):
            change = skill_scores[i] - skill_scores[i-1]
            changes.append(change)
        
        if not changes:
            return 0.0
        
        avg_change = sum(changes) / len(changes)
        return avg_change