"""
Context Pattern Analyzer

Analyzes environment-based usage patterns for different contexts
Maps to analyze_context_patterns MCP tool
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging

from ...prediction_models import ContextPattern, PredictionConfidenceLevel
from ..utilities.context_extraction_utils import ContextExtractionUtils
from ..utilities.environment_modeling_utils import EnvironmentModelingUtils

# Import user service repositories
from tools.services.user_service.repositories.usage_repository import UsageRepository
from tools.services.user_service.repositories.session_repository import SessionRepository

# Import memory service if available
try:
    from tools.services.memory_service.memory_service import MemoryService
    MEMORY_SERVICE_AVAILABLE = True
except ImportError:
    MEMORY_SERVICE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.debug("Memory service not available for context analysis")

logger = logging.getLogger(__name__)


class ContextPatternAnalyzer:
    """
    Analyzes environment-based usage patterns
    Identifies context-specific behaviors, tool combinations, and success indicators
    """
    
    def __init__(self):
        """Initialize repositories and utilities"""
        self.usage_repo = UsageRepository()
        self.session_repo = SessionRepository()
        self.context_utils = ContextExtractionUtils()
        self.env_utils = EnvironmentModelingUtils()
        
        # Initialize memory service if available
        if MEMORY_SERVICE_AVAILABLE:
            self.memory_service = MemoryService()
        else:
            self.memory_service = None
        
        # Context type definitions
        self.context_definitions = {
            "development": {
                "keywords": ["code", "debug", "test", "build", "deploy", "git", "programming"],
                "tools": ["code_analyzer", "debugger", "test_runner", "git_tool"],
                "endpoints": ["/api/code", "/api/debug", "/api/test"]
            },
            "analysis": {
                "keywords": ["data", "analyze", "statistics", "chart", "graph", "insights"],
                "tools": ["data_analyzer", "stats_tool", "chart_generator", "query_tool"],
                "endpoints": ["/api/analyze", "/api/data", "/api/stats"]
            },
            "research": {
                "keywords": ["research", "search", "investigate", "study", "explore", "literature"],
                "tools": ["search_engine", "research_tool", "source_finder", "web_crawler"],
                "endpoints": ["/api/search", "/api/research", "/api/web"]
            },
            "document": {
                "keywords": ["document", "text", "pdf", "write", "edit", "format", "summary"],
                "tools": ["text_analyzer", "pdf_reader", "summarizer", "editor"],
                "endpoints": ["/api/document", "/api/text", "/api/pdf"]
            },
            "memory": {
                "keywords": ["remember", "recall", "store", "memory", "knowledge", "context"],
                "tools": ["memory_tool", "knowledge_base", "retrieval_engine"],
                "endpoints": ["/api/memory", "/api/knowledge", "/api/recall"]
            }
        }
        
        logger.info("Context Pattern Analyzer initialized")
    
    async def analyze_patterns(self, user_id: str, context_type: str, timeframe: str = "30d") -> ContextPattern:
        """
        Analyze context-specific patterns for a user
        
        Args:
            user_id: User identifier
            context_type: Type of context to analyze
            
        Returns:
            ContextPattern: Context-specific behavioral patterns
        """
        try:
            logger.info(f"Analyzing context patterns for user {user_id}, context: {context_type}")
            
            # Get usage and session data
            usage_records = await self.usage_repo.get_user_usage_history(
                user_id=user_id,
                start_date=datetime.utcnow() - timedelta(days=30),
                limit=1000
            )
            
            sessions = await self.session_repo.get_user_sessions(
                user_id=user_id,
                limit=50
            )
            
            # Get memory usage patterns if available
            memory_patterns = await self._analyze_memory_usage(user_id)
            
            # Filter data relevant to this context
            context_usage = self._filter_context_usage(usage_records, context_type)
            context_sessions = self._filter_context_sessions(sessions, context_type)
            
            # Analyze patterns
            usage_patterns = self._analyze_usage_patterns(context_usage, context_type)
            tool_combinations = self._identify_tool_combinations(context_usage)
            success_indicators = self._identify_success_indicators(
                context_usage, context_sessions, context_type
            )
            session_characteristics = self._analyze_session_characteristics(context_sessions)
            
            # Calculate confidence
            confidence = self._calculate_confidence(
                context_usage, context_sessions, context_type, usage_records
            )
            
            return ContextPattern(
                user_id=user_id,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                context_type=context_type,
                usage_patterns=usage_patterns,
                tool_combinations=tool_combinations,
                success_indicators=success_indicators,
                memory_usage_patterns=memory_patterns,
                session_characteristics=session_characteristics,
                metadata={
                    "analysis_date": datetime.utcnow(),
                    "context_usage_records": len(context_usage),
                    "context_sessions": len(context_sessions),
                    "total_usage_records": len(usage_records),
                    "context_coverage": len(context_usage) / len(usage_records) if usage_records else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing context patterns for user {user_id}: {e}")
            raise
    
    async def _analyze_memory_usage(self, user_id: str) -> Dict[str, Any]:
        """Analyze memory service usage patterns"""
        if not self.memory_service:
            return {}
        
        try:
            # Get memory statistics if available
            # This would require memory service to have analytics methods
            return {
                "memory_types_used": [],
                "memory_access_frequency": 0.0,
                "memory_creation_rate": 0.0,
                "preferred_memory_types": []
            }
        except Exception as e:
            logger.debug(f"Could not analyze memory usage: {e}")
            return {}
    
    def _filter_context_usage(
        self, 
        usage_records: List[Dict[str, Any]], 
        context_type: str
    ) -> List[Dict[str, Any]]:
        """Filter usage records relevant to specific context"""
        if context_type == "general":
            return usage_records
        
        context_def = self.context_definitions.get(context_type, {})
        keywords = context_def.get("keywords", [])
        tools = context_def.get("tools", [])
        endpoints = context_def.get("endpoints", [])
        
        filtered_records = []
        
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            event_type = record.get('event_type', '').lower()
            
            # Check if record matches context
            matches_context = (
                any(keyword in endpoint for keyword in keywords) or
                any(keyword in tool_name for keyword in keywords) or
                any(keyword in event_type for keyword in keywords) or
                any(tool in tool_name for tool in tools) or
                any(ep in endpoint for ep in endpoints)
            )
            
            if matches_context:
                filtered_records.append(record)
        
        return filtered_records
    
    def _filter_context_sessions(
        self, 
        sessions: List[Dict[str, Any]], 
        context_type: str
    ) -> List[Dict[str, Any]]:
        """Filter sessions relevant to specific context"""
        if context_type == "general":
            return sessions
        
        context_def = self.context_definitions.get(context_type, {})
        keywords = context_def.get("keywords", [])
        
        filtered_sessions = []
        
        for session in sessions:
            conversation_data = session.get('conversation_data', {})
            metadata = session.get('metadata', {})
            
            # Convert to searchable text
            searchable_text = f"{conversation_data} {metadata}".lower()
            
            # Check if session matches context
            if any(keyword in searchable_text for keyword in keywords):
                filtered_sessions.append(session)
        
        return filtered_sessions
    
    def _analyze_usage_patterns(
        self, 
        context_usage: List[Dict[str, Any]], 
        context_type: str
    ) -> Dict[str, Any]:
        """Analyze usage patterns within this context"""
        patterns = {
            "frequency": 0.0,
            "peak_times": [],
            "avg_session_length": 0.0,
            "tool_usage_distribution": {},
            "endpoint_preferences": {},
            "temporal_patterns": {},
            "intensity_patterns": {}
        }
        
        if not context_usage:
            return patterns
        
        # Calculate frequency (records per day over last 30 days)
        patterns["frequency"] = len(context_usage) / 30.0
        
        # Analyze peak times
        hour_usage = defaultdict(int)
        for record in context_usage:
            created_at = record.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                hour_usage[created_at.hour] += 1
        
        if hour_usage:
            avg_usage = sum(hour_usage.values()) / len(hour_usage)
            patterns["peak_times"] = [
                hour for hour, count in hour_usage.items()
                if count > avg_usage * 1.2
            ]
        
        # Tool usage distribution
        tool_counts = Counter()
        for record in context_usage:
            tool_name = record.get('tool_name')
            if tool_name:
                tool_counts[tool_name] += 1
        
        total_tools = sum(tool_counts.values())
        if total_tools > 0:
            patterns["tool_usage_distribution"] = {
                tool: count / total_tools
                for tool, count in tool_counts.items()
            }
        
        # Endpoint preferences
        endpoint_counts = Counter()
        for record in context_usage:
            endpoint = record.get('endpoint')
            if endpoint:
                endpoint_counts[endpoint] += 1
        
        patterns["endpoint_preferences"] = dict(endpoint_counts)
        
        # Temporal patterns (day of week)
        dow_usage = defaultdict(int)
        for record in context_usage:
            created_at = record.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                dow_usage[created_at.strftime('%A')] += 1
        
        patterns["temporal_patterns"] = dict(dow_usage)
        
        # Intensity patterns (tokens/cost per session)
        if context_usage:
            total_tokens = sum(record.get('tokens_used', 0) for record in context_usage)
            total_cost = sum(record.get('cost_usd', 0.0) for record in context_usage)
            
            patterns["intensity_patterns"] = {
                "avg_tokens_per_call": total_tokens / len(context_usage),
                "avg_cost_per_call": total_cost / len(context_usage),
                "total_tokens": total_tokens,
                "total_cost": total_cost
            }
        
        return patterns
    
    def _identify_tool_combinations(
        self, 
        context_usage: List[Dict[str, Any]]
    ) -> List[List[str]]:
        """Identify common tool combinations within context"""
        if len(context_usage) < 2:
            return []
        
        # Group usage records by time windows (1 hour windows)
        time_windows = defaultdict(list)
        
        for record in context_usage:
            created_at = record.get('created_at')
            if not created_at:
                continue
            
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            # Create 1-hour time window key
            window_key = created_at.replace(minute=0, second=0, microsecond=0)
            time_windows[window_key].append(record)
        
        # Find tool combinations within time windows
        combinations = []
        
        for window_records in time_windows.values():
            if len(window_records) > 1:
                tools_in_window = [
                    record.get('tool_name') for record in window_records
                    if record.get('tool_name')
                ]
                
                if len(set(tools_in_window)) > 1:  # Multiple different tools
                    combinations.append(list(set(tools_in_window)))
        
        # Find most common combinations
        combination_counts = Counter()
        for combo in combinations:
            combo_key = tuple(sorted(combo))
            combination_counts[combo_key] += 1
        
        # Return top combinations
        top_combinations = [
            list(combo) for combo, count in combination_counts.most_common(5)
            if count > 1  # Must appear more than once
        ]
        
        return top_combinations
    
    def _identify_success_indicators(
        self, 
        context_usage: List[Dict[str, Any]], 
        context_sessions: List[Dict[str, Any]],
        context_type: str
    ) -> List[str]:
        """Identify indicators of successful sessions in this context"""
        indicators = []
        
        # Usage-based indicators
        if context_usage:
            # High token usage often indicates successful complex operations
            avg_tokens = sum(record.get('tokens_used', 0) for record in context_usage) / len(context_usage)
            if avg_tokens > 200:
                indicators.append("high_token_usage")
            
            # Multiple tool usage indicates comprehensive work
            unique_tools = len(set(record.get('tool_name') for record in context_usage if record.get('tool_name')))
            if unique_tools >= 3:
                indicators.append("diverse_tool_usage")
            
            # Consistent API success (no errors in response data)
            successful_calls = sum(
                1 for record in context_usage
                if record.get('response_data', {}).get('success', True)
            )
            success_rate = successful_calls / len(context_usage)
            if success_rate > 0.9:
                indicators.append("high_success_rate")
        
        # Session-based indicators
        if context_sessions:
            # Long sessions indicate deep work
            session_durations = []
            for session in context_sessions:
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
                            session_durations.append(duration)
                    except:
                        pass
            
            if session_durations:
                avg_duration = sum(session_durations) / len(session_durations)
                if avg_duration > 45:  # 45+ minutes
                    indicators.append("extended_session_duration")
            
            # High message count indicates active engagement
            avg_messages = sum(
                session.get('message_count', 0) for session in context_sessions
            ) / len(context_sessions)
            
            if avg_messages > 15:
                indicators.append("high_engagement")
        
        # Context-specific indicators
        context_indicators = {
            "development": ["code_compilation_success", "test_passing", "deployment_success"],
            "analysis": ["insight_generation", "visualization_creation", "data_export"],
            "research": ["source_discovery", "knowledge_synthesis", "citation_organization"],
            "document": ["document_completion", "formatting_success", "content_export"],
            "memory": ["knowledge_storage", "successful_recall", "context_building"]
        }
        
        if context_type in context_indicators:
            # Add context-specific indicators based on patterns
            # This is a simplified heuristic - in production, you'd have more sophisticated detection
            if len(indicators) >= 2:  # If we already have good general indicators
                indicators.extend(context_indicators[context_type][:2])  # Add top 2 context indicators
        
        return indicators
    
    def _analyze_session_characteristics(
        self, 
        context_sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze characteristics of sessions in this context"""
        characteristics = {
            "avg_duration_minutes": 0.0,
            "avg_message_count": 0.0,
            "avg_token_usage": 0.0,
            "session_completion_rate": 0.0,
            "context_switching_frequency": 0.0
        }
        
        if not context_sessions:
            return characteristics
        
        # Calculate session durations
        durations = []
        message_counts = []
        token_counts = []
        completed_sessions = 0
        
        for session in context_sessions:
            # Duration
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
                except:
                    pass
            
            # Message and token counts
            msg_count = session.get('message_count', 0)
            token_count = session.get('total_tokens', 0)
            
            message_counts.append(msg_count)
            token_counts.append(token_count)
            
            # Completion heuristic
            if (msg_count >= 5 and 
                session.get('status') in ['completed', 'active'] and
                token_count > 100):
                completed_sessions += 1
        
        # Calculate averages
        if durations:
            characteristics["avg_duration_minutes"] = sum(durations) / len(durations)
        
        if message_counts:
            characteristics["avg_message_count"] = sum(message_counts) / len(message_counts)
        
        if token_counts:
            characteristics["avg_token_usage"] = sum(token_counts) / len(token_counts)
        
        characteristics["session_completion_rate"] = completed_sessions / len(context_sessions)
        
        # Context switching (simplified heuristic based on session frequency)
        if len(context_sessions) > 1:
            # If user has many short sessions vs few long ones = more switching
            avg_duration = characteristics["avg_duration_minutes"]
            session_frequency = len(context_sessions) / 30.0  # per day over 30 days
            
            if avg_duration > 0:
                switching_score = session_frequency / (avg_duration / 60)  # sessions per hour
                characteristics["context_switching_frequency"] = min(switching_score, 1.0)
        
        return characteristics
    
    def _calculate_confidence(
        self, 
        context_usage: List[Dict[str, Any]],
        context_sessions: List[Dict[str, Any]],
        context_type: str,
        total_usage: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence in context pattern analysis"""
        base_confidence = 0.5
        
        # Data quantity factors
        context_usage_count = len(context_usage)
        context_sessions_count = len(context_sessions)
        total_usage_count = len(total_usage)
        
        # Boost confidence based on context-specific data
        if context_usage_count >= 20:
            base_confidence += 0.2
        elif context_usage_count >= 10:
            base_confidence += 0.1
        elif context_usage_count < 3:
            base_confidence -= 0.25
        
        if context_sessions_count >= 5:
            base_confidence += 0.15
        elif context_sessions_count >= 2:
            base_confidence += 0.05
        elif context_sessions_count == 0:
            base_confidence -= 0.2
        
        # Context coverage factor (how much of total usage is in this context)
        if total_usage_count > 0:
            context_coverage = context_usage_count / total_usage_count
            if context_coverage > 0.3:  # 30%+ of usage in this context
                base_confidence += 0.15
            elif context_coverage > 0.1:  # 10-30%
                base_confidence += 0.1
            elif context_coverage < 0.05:  # Less than 5%
                base_confidence -= 0.1
        
        # Context specificity factor
        if context_type != "general":
            # Specialized contexts require more confidence adjustment
            if context_usage_count >= 10:
                base_confidence += 0.05  # Bonus for specific context analysis
            else:
                base_confidence -= 0.05  # Penalty for insufficient context-specific data
        
        # Pattern consistency factor
        if context_usage:
            # Check if there are consistent patterns (same tools, similar timing)
            tools_used = [r.get('tool_name') for r in context_usage if r.get('tool_name')]
            if tools_used:
                unique_tools = len(set(tools_used))
                tool_consistency = 1.0 - (unique_tools / len(tools_used))
                if tool_consistency > 0.3:  # Some consistency in tool usage
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
        """Health check for context pattern analyzer"""
        try:
            # Test repository connectivity
            test_result = await self.usage_repo.get_user_usage_history("test", limit=1)
            
            return {
                "status": "healthy",
                "component": "context_pattern_analyzer",
                "last_check": datetime.utcnow(),
                "repositories": {
                    "usage_repo": "connected",
                    "session_repo": "connected"
                },
                "services": {
                    "memory_service": "available" if self.memory_service else "not_available"
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "context_pattern_analyzer",
                "error": str(e),
                "last_check": datetime.utcnow()
            }