"""
User Pattern Analyzer

Analyzes individual user behavior patterns and preferences
Maps to analyze_user_patterns MCP tool
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from ...prediction_models import UserBehaviorPattern, PredictionConfidenceLevel
from ..utilities.pattern_extraction_utils import PatternExtractionUtils

# Import user service repositories
from tools.services.user_service.repositories.usage_repository import UsageRepository
from tools.services.user_service.repositories.session_repository import SessionRepository
from tools.services.user_service.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserPatternAnalyzer:
    """
    Analyzes individual user behavior patterns and preferences
    Identifies task preferences, tool usage, interaction styles, and success patterns
    """
    
    def __init__(self):
        """Initialize repositories and utilities"""
        self.usage_repo = UsageRepository()
        self.session_repo = SessionRepository()
        self.user_repo = UserRepository()
        self.pattern_utils = PatternExtractionUtils()
        
        logger.info("User Pattern Analyzer initialized")
    
    async def analyze_patterns(self, user_id: str, context: Dict[str, Any]) -> UserBehaviorPattern:
        """
        Analyze individual user behavior patterns
        
        Args:
            user_id: User identifier
            context: Additional context for analysis
            
        Returns:
            UserBehaviorPattern: Individual user preferences and patterns
        """
        try:
            logger.info(f"Analyzing user patterns for user {user_id}")
            
            # Get user data
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
            
            # Get usage data (recent activity for pattern analysis)
            recent_usage = await self.usage_repo.get_recent_usage(user_id, hours=24*30)  # 30 days
            
            # Get session data
            sessions = await self.session_repo.get_user_sessions(user_id, limit=50)
            
            # Extract patterns
            task_preferences = self._extract_task_preferences(recent_usage, sessions)
            tool_preferences = self._extract_tool_preferences(recent_usage)
            interaction_style = self._analyze_interaction_style(sessions, recent_usage, context)
            success_patterns = self._analyze_success_patterns(recent_usage)
            failure_patterns = self._identify_failure_patterns(recent_usage)
            
            # Extract contextual preferences
            context_preferences = self._extract_context_preferences(sessions, context)
            session_patterns = self._extract_session_patterns(sessions)
            
            # Calculate confidence
            confidence = self._calculate_confidence(recent_usage, sessions, user)
            
            return UserBehaviorPattern(
                user_id=user_id,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                task_preferences=task_preferences,
                tool_preferences=tool_preferences,
                interaction_style=interaction_style,
                success_patterns=success_patterns,
                failure_patterns=failure_patterns,
                context_preferences=context_preferences,
                session_patterns=session_patterns,
                metadata={
                    "analysis_date": datetime.utcnow(),
                    "usage_records_analyzed": len(recent_usage),
                    "sessions_analyzed": len(sessions),
                    "user_subscription": user.subscription_status if user else "unknown"
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing user patterns for user {user_id}: {e}")
            raise
    
    def _extract_task_preferences(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract preferred task types from usage and session data"""
        task_indicators = {
            "chat": ["chat", "conversation", "message"],
            "analysis": ["analyze", "analysis", "data", "stats"],
            "search": ["search", "find", "query", "lookup"],
            "memory": ["memory", "remember", "recall", "store"],
            "document": ["document", "file", "text", "pdf"],
            "code": ["code", "programming", "debug", "function"],
            "research": ["research", "investigate", "explore", "study"]
        }
        
        task_scores = {}
        
        # Analyze endpoint patterns
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            event_type = record.get('event_type', '').lower()
            tool_name = record.get('tool_name', '').lower()
            
            combined_text = f"{endpoint} {event_type} {tool_name}"
            
            for task_type, keywords in task_indicators.items():
                score = sum(1 for keyword in keywords if keyword in combined_text)
                task_scores[task_type] = task_scores.get(task_type, 0) + score
        
        # Analyze session conversation data
        for session in sessions:
            conv_data = session.get('conversation_data', {})
            if isinstance(conv_data, dict):
                conv_text = str(conv_data).lower()
                
                for task_type, keywords in task_indicators.items():
                    score = sum(1 for keyword in keywords if keyword in conv_text)
                    task_scores[task_type] = task_scores.get(task_type, 0) + score
        
        # Return top preferences (above average + some threshold)
        if not task_scores:
            return []
        
        avg_score = sum(task_scores.values()) / len(task_scores)
        preferred_tasks = [
            task for task, score in task_scores.items()
            if score > avg_score * 1.2  # 20% above average
        ]
        
        # Sort by score and return top preferences
        preferred_tasks.sort(key=lambda x: task_scores[x], reverse=True)
        return preferred_tasks[:5]  # Top 5 preferences
    
    def _extract_tool_preferences(self, usage_records: List[Dict[str, Any]]) -> List[str]:
        """Extract preferred tools from usage data"""
        pattern_analysis = self.pattern_utils.detect_preference_patterns(usage_records)
        return pattern_analysis.get("preferred_tools", [])
    
    def _analyze_interaction_style(
        self, 
        sessions: List[Dict[str, Any]], 
        usage_records: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze user interaction style"""
        style = {
            "session_length_preference": "medium",  # short, medium, long
            "interaction_frequency": "regular",     # low, regular, high
            "complexity_preference": "medium",      # simple, medium, advanced
            "verbosity": "medium",                  # concise, medium, verbose
            "technical_level": "intermediate"       # beginner, intermediate, advanced
        }
        
        if not sessions:
            return style
        
        # Analyze session characteristics
        session_durations = []
        message_counts = []
        
        for session in sessions:
            # Session duration analysis
            created_at = session.get('created_at')
            last_activity = session.get('last_activity')
            
            if created_at and last_activity:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if isinstance(last_activity, str):
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                
                duration_minutes = (last_activity - created_at).total_seconds() / 60
                if duration_minutes > 0:
                    session_durations.append(duration_minutes)
            
            # Message count analysis
            message_count = session.get('message_count', 0)
            if message_count > 0:
                message_counts.append(message_count)
        
        # Determine session length preference
        if session_durations:
            avg_duration = sum(session_durations) / len(session_durations)
            if avg_duration < 15:  # Less than 15 minutes
                style["session_length_preference"] = "short"
            elif avg_duration > 60:  # More than 1 hour
                style["session_length_preference"] = "long"
        
        # Determine verbosity from message counts
        if message_counts:
            avg_messages = sum(message_counts) / len(message_counts)
            if avg_messages < 10:
                style["verbosity"] = "concise"
            elif avg_messages > 30:
                style["verbosity"] = "verbose"
        
        # Determine technical level from tool usage
        technical_tools = ["code", "debug", "api", "database", "sql", "programming"]
        advanced_endpoints = ["/api/advanced", "/api/admin", "/api/system"]
        
        technical_score = 0
        for record in usage_records:
            tool_name = record.get('tool_name', '').lower()
            endpoint = record.get('endpoint', '').lower()
            
            if any(tech_tool in tool_name for tech_tool in technical_tools):
                technical_score += 2
            
            if any(adv_endpoint in endpoint for adv_endpoint in advanced_endpoints):
                technical_score += 3
        
        # Adjust technical level based on score
        if technical_score > len(usage_records) * 0.3:  # 30% technical usage
            style["technical_level"] = "advanced"
        elif technical_score < len(usage_records) * 0.1:  # Less than 10% technical
            style["technical_level"] = "beginner"
        
        return style
    
    def _analyze_success_patterns(self, usage_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze success patterns by task/tool type"""
        success_analysis = self.pattern_utils.calculate_success_failure_patterns(usage_records)
        
        return {
            "overall_success_rate": success_analysis.get("overall_success_rate", 0.0),
            **success_analysis.get("success_by_tool", {}),
            **success_analysis.get("success_by_endpoint", {})
        }
    
    def _identify_failure_patterns(self, usage_records: List[Dict[str, Any]]) -> List[str]:
        """Identify common failure patterns"""
        success_analysis = self.pattern_utils.calculate_success_failure_patterns(usage_records)
        
        failure_patterns = []
        failure_patterns.extend(success_analysis.get("failure_indicators", []))
        
        # Add error patterns
        error_patterns = success_analysis.get("error_patterns", {})
        for error_type, count in error_patterns.items():
            if count > 2:  # More than 2 occurrences
                failure_patterns.append(f"frequent_{error_type}")
        
        return failure_patterns
    
    def _extract_context_preferences(
        self, 
        sessions: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract context-based preferences"""
        preferences = {
            "preferred_session_types": [],
            "context_switching": "moderate",  # low, moderate, high
            "multi_tasking": False
        }
        
        # Analyze session types from metadata
        session_types = {}
        for session in sessions:
            metadata = session.get('metadata', {})
            if isinstance(metadata, dict):
                session_type = metadata.get('session_type', 'general')
                session_types[session_type] = session_types.get(session_type, 0) + 1
        
        if session_types:
            # Get top session types
            sorted_types = sorted(session_types.items(), key=lambda x: x[1], reverse=True)
            preferences["preferred_session_types"] = [t[0] for t in sorted_types[:3]]
        
        # Check for multi-tasking patterns (multiple concurrent sessions)
        if len(sessions) > 0:
            # Simple heuristic: if average session duration is short but message count is high
            avg_messages = sum(s.get('message_count', 0) for s in sessions) / len(sessions)
            if avg_messages > 20:
                preferences["multi_tasking"] = True
        
        return preferences
    
    def _extract_session_patterns(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract session-specific behavior patterns"""
        patterns = {
            "avg_session_duration": 0.0,
            "avg_messages_per_session": 0.0,
            "session_completion_rate": 0.0,
            "preferred_session_times": []
        }
        
        if not sessions:
            return patterns
        
        durations = []
        message_counts = []
        completion_count = 0
        session_hours = []
        
        for session in sessions:
            # Duration calculation
            created_at = session.get('created_at')
            last_activity = session.get('last_activity')
            
            if created_at and last_activity:
                try:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if isinstance(last_activity, str):
                        last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    
                    duration = (last_activity - created_at).total_seconds() / 60
                    if duration > 0:
                        durations.append(duration)
                    
                    # Track session start times
                    session_hours.append(created_at.hour)
                except:
                    pass
            
            # Message count
            msg_count = session.get('message_count', 0)
            message_counts.append(msg_count)
            
            # Completion heuristic (session with significant activity)
            if msg_count >= 5 and session.get('status') in ['completed', 'active']:
                completion_count += 1
        
        # Calculate averages
        if durations:
            patterns["avg_session_duration"] = sum(durations) / len(durations)
        
        if message_counts:
            patterns["avg_messages_per_session"] = sum(message_counts) / len(message_counts)
        
        patterns["session_completion_rate"] = completion_count / len(sessions)
        
        # Find preferred session times
        if session_hours:
            from collections import Counter
            hour_counts = Counter(session_hours)
            # Get hours with above-average usage
            avg_count = sum(hour_counts.values()) / len(hour_counts) if hour_counts else 0
            preferred_hours = [hour for hour, count in hour_counts.items() 
                             if count > avg_count * 1.2]
            patterns["preferred_session_times"] = sorted(preferred_hours)
        
        return patterns
    
    def _calculate_confidence(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        user: Any
    ) -> float:
        """Calculate confidence in pattern analysis"""
        base_confidence = 0.5
        
        # Data quantity factors
        usage_count = len(usage_records)
        session_count = len(sessions)
        
        if usage_count >= 50:
            base_confidence += 0.25
        elif usage_count >= 20:
            base_confidence += 0.15
        elif usage_count < 5:
            base_confidence -= 0.2
        
        if session_count >= 10:
            base_confidence += 0.15
        elif session_count >= 5:
            base_confidence += 0.1
        elif session_count < 2:
            base_confidence -= 0.15
        
        # User account age factor (older accounts have more stable patterns)
        if user and user.created_at:
            try:
                if isinstance(user.created_at, str):
                    created_date = datetime.fromisoformat(user.created_at.replace('Z', '+00:00'))
                else:
                    created_date = user.created_at
                
                account_age_days = (datetime.utcnow() - created_date).days
                
                if account_age_days > 90:
                    base_confidence += 0.1
                elif account_age_days > 30:
                    base_confidence += 0.05
            except:
                pass
        
        # Pattern consistency factor (if we have consistent patterns, higher confidence)
        if usage_records:
            # Check tool usage consistency
            tool_usage = {}
            for record in usage_records:
                tool = record.get('tool_name')
                if tool:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1
            
            if tool_usage:
                # Higher variation in tools = less consistent patterns
                usage_values = list(tool_usage.values())
                max_usage = max(usage_values)
                if max_usage > len(usage_records) * 0.5:  # One tool dominates 50%+
                    base_confidence += 0.05
        
        return max(0.0, min(1.0, base_confidence))
    
    def _get_confidence_level(self, confidence: float) -> PredictionConfidenceLevel:
        """Convert confidence score to confidence level"""
        if confidence >= 0.8:
            return PredictionConfidenceLevel.VERY_HIGH
        elif confidence >= 0.6:
            return PredictionConfidenceLevel.HIGH
        elif confidence >= 0.3:
            return PredictionConfidenceLevel.MEDIUM
        else:
            return PredictionConfidenceLevel.LOW
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for user pattern analyzer"""
        try:
            # Test repository connectivity
            test_result = await self.usage_repo.get_user_usage_history("test", limit=1)
            
            return {
                "status": "healthy",
                "component": "user_pattern_analyzer",
                "last_check": datetime.utcnow(),
                "repositories": {
                    "usage_repo": "connected",
                    "session_repo": "connected",
                    "user_repo": "connected"
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "user_pattern_analyzer",
                "error": str(e),
                "last_check": datetime.utcnow()
            }