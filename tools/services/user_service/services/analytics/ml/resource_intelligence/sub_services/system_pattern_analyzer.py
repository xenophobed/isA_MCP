"""
System Pattern Analyzer

Analyzes system resource usage patterns and identifies optimization opportunities
Maps to analyze_system_patterns MCP tool
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
import statistics

from ...prediction_models import SystemPattern, PredictionConfidenceLevel
from ..utilities.resource_monitoring_utils import ResourceMonitoringUtils
from ..utilities.cost_analysis_utils import CostAnalysisUtils

# Import user service repositories
from tools.services.user_service.repositories.usage_repository import UsageRepository
from tools.services.user_service.repositories.session_repository import SessionRepository
from tools.services.user_service.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class SystemPatternAnalyzer:
    """
    Analyzes system resource usage patterns for users
    Identifies bottlenecks, optimization opportunities, and cost implications
    """
    
    def __init__(self):
        """Initialize repositories and utilities"""
        self.usage_repository = UsageRepository()
        self.session_repository = SessionRepository()
        self.user_repository = UserRepository()
        self.resource_utils = ResourceMonitoringUtils()
        self.cost_utils = CostAnalysisUtils()
        
        # System resource categories
        self.resource_categories = {
            "compute": ["cpu", "processing", "computation", "calculate", "analyze"],
            "memory": ["memory", "storage", "cache", "data", "large"],
            "network": ["network", "api", "request", "download", "upload"],
            "database": ["database", "query", "sql", "search", "index"],
            "ai_models": ["model", "llm", "gpt", "claude", "embedding", "completion"]
        }
        
        logger.info("System Pattern Analyzer initialized")
    
    async def analyze_patterns(
        self, 
        user_id: str, 
        system_context: Dict[str, Any],
        timeframe: str
    ) -> SystemPattern:
        """
        Analyze system resource usage patterns for a user
        
        Args:
            user_id: User identifier
            system_context: Current system context information
            timeframe: Analysis timeframe
            
        Returns:
            SystemPattern: System resource usage insights
        """
        try:
            logger.info(f"Analyzing system patterns for user {user_id}, timeframe: {timeframe}")
            
            # Get usage and session data from real database
            start_date, end_date = self._parse_timeframe(timeframe)
            
            usage_records = await self.usage_repository.get_user_usage_history(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=2000  # Extended limit for comprehensive analysis
            )
            
            sessions = await self.session_repository.get_user_sessions(
                user_id=user_id,
                limit=100
            )
            
            user_profile = await self.user_repository.get_by_user_id(user_id)
            
            logger.info(f"Retrieved {len(usage_records)} usage records and {len(sessions)} sessions")
            
            # Analyze resource utilization patterns
            resource_utilization = await self._analyze_resource_utilization(
                usage_records, sessions, system_context
            )
            
            # Identify system bottlenecks
            bottlenecks = await self._identify_bottlenecks(
                usage_records, sessions, resource_utilization
            )
            
            # Find optimization opportunities
            optimization_opportunities = await self._find_optimization_opportunities(
                usage_records, sessions, resource_utilization, bottlenecks
            )
            
            # Perform cost analysis
            cost_analysis = await self._perform_cost_analysis(
                usage_records, resource_utilization, user_profile
            )
            
            # Calculate system load patterns
            load_patterns = await self._analyze_load_patterns(usage_records, sessions)
            
            # Assess resource efficiency
            efficiency_metrics = await self._assess_resource_efficiency(
                usage_records, sessions, resource_utilization
            )
            
            # Calculate confidence based on data quality and completeness
            confidence = self._calculate_confidence(
                usage_records, sessions, timeframe, system_context
            )
            
            # Convert peak times to proper format
            peak_times = self._extract_peak_times(usage_records)
            peak_usage_dict = {f"hour_{hour}": 1.0 for hour in peak_times} if peak_times else {"hour_9": 0.5}
            
            return SystemPattern(
                user_id=user_id,
                confidence=confidence,
                confidence_level=self._determine_confidence_level(confidence),
                resource_usage=resource_utilization.get('compute', {}) if resource_utilization else {"cpu": 0.3, "memory": 0.4},
                performance_metrics=efficiency_metrics if efficiency_metrics else {"overall_efficiency": 0.5},
                bottlenecks=bottlenecks,
                peak_usage_times=peak_usage_dict,
                optimization_opportunities=optimization_opportunities,
                metadata={
                    "analysis_date": datetime.utcnow(),
                    "system_usage_records": len(usage_records),
                    "system_sessions": len(sessions),
                    "timeframe_analyzed": timeframe,
                    "system_context_provided": bool(system_context),
                    "cost_analysis": cost_analysis,
                    "load_patterns": load_patterns,
                    "resource_utilization": resource_utilization,
                    "resource_trends": self._calculate_resource_trends(usage_records)
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing system patterns for user {user_id}: {e}")
            raise
    
    def _parse_timeframe(self, timeframe: str) -> tuple:
        """Parse timeframe string to start and end dates"""
        now = datetime.utcnow()
        
        if timeframe.endswith('d'):
            days = int(timeframe[:-1])
            start_date = now - timedelta(days=days)
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            start_date = now - timedelta(hours=hours)
        elif timeframe.endswith('w'):
            weeks = int(timeframe[:-1])
            start_date = now - timedelta(weeks=weeks)
        else:
            # Default to 30 days
            start_date = now - timedelta(days=30)
        
        return start_date, now
    
    async def _analyze_resource_utilization(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        system_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze resource utilization patterns"""
        utilization = {}
        
        if not usage_records:
            return utilization
        
        # Calculate compute utilization (based on tokens and processing)
        total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
        total_processing_calls = len([r for r in usage_records if self._is_compute_intensive(r)])
        
        utilization['compute'] = {
            'total_tokens_processed': total_tokens,
            'compute_intensive_calls': total_processing_calls,
            'avg_tokens_per_call': total_tokens / len(usage_records) if usage_records else 0,
            'utilization_score': min(1.0, total_tokens / 1000000)  # Normalize to 1M tokens
        }
        
        # Calculate cost utilization
        total_cost = sum(record.get('cost_usd', 0) for record in usage_records)
        utilization['cost'] = {
            'total_cost_usd': total_cost,
            'avg_cost_per_call': total_cost / len(usage_records) if usage_records else 0,
            'cost_efficiency': self._calculate_cost_efficiency(usage_records)
        }
        
        # Calculate API utilization patterns
        api_calls_by_endpoint = Counter(record.get('endpoint', 'unknown') for record in usage_records)
        utilization['api'] = {
            'total_api_calls': len(usage_records),
            'unique_endpoints': len(api_calls_by_endpoint),
            'most_used_endpoints': dict(api_calls_by_endpoint.most_common(5)),
            'api_diversity_score': len(api_calls_by_endpoint) / len(usage_records) if usage_records else 0
        }
        
        # Calculate session utilization
        if sessions:
            total_session_time = sum(
                session.get('total_tokens', 0) for session in sessions
            )
            avg_session_length = statistics.mean([
                session.get('message_count', 0) for session in sessions
            ]) if sessions else 0
            
            utilization['sessions'] = {
                'total_sessions': len(sessions),
                'total_session_tokens': total_session_time,
                'avg_session_length': avg_session_length,
                'session_efficiency': self._calculate_session_efficiency(sessions)
            }
        
        # Analyze tool utilization
        tool_usage = Counter(record.get('tool_name', 'unknown') for record in usage_records)
        utilization['tools'] = {
            'tools_used': dict(tool_usage),
            'most_used_tool': tool_usage.most_common(1)[0] if tool_usage else None,
            'tool_diversity': len(tool_usage)
        }
        
        return utilization
    
    def _is_compute_intensive(self, record: Dict[str, Any]) -> bool:
        """Check if a record represents compute-intensive operations"""
        compute_keywords = self.resource_categories["compute"]
        endpoint = record.get('endpoint', '').lower()
        tool_name = record.get('tool_name', '').lower()
        
        return any(keyword in f"{endpoint} {tool_name}" for keyword in compute_keywords)
    
    def _calculate_cost_efficiency(self, usage_records: List[Dict[str, Any]]) -> float:
        """Calculate cost efficiency score"""
        if not usage_records:
            return 0.0
        
        # Efficiency = tokens per dollar spent
        total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
        total_cost = sum(record.get('cost_usd', 0) for record in usage_records)
        
        if total_cost == 0:
            return 1.0  # Free usage is maximally efficient
        
        tokens_per_dollar = total_tokens / total_cost
        # Normalize to 0-1 scale (10000 tokens per dollar = high efficiency)
        return min(1.0, tokens_per_dollar / 10000)
    
    def _calculate_session_efficiency(self, sessions: List[Dict[str, Any]]) -> float:
        """Calculate session efficiency score"""
        if not sessions:
            return 0.0
        
        # Efficiency = tokens per message (higher = more efficient)
        total_tokens = sum(session.get('total_tokens', 0) for session in sessions)
        total_messages = sum(session.get('message_count', 0) for session in sessions)
        
        if total_messages == 0:
            return 0.0
        
        tokens_per_message = total_tokens / total_messages
        # Normalize to 0-1 scale (500 tokens per message = high efficiency)
        return min(1.0, tokens_per_message / 500)
    
    async def _identify_bottlenecks(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        resource_utilization: Dict[str, Any]
    ) -> List[str]:
        """Identify system bottlenecks"""
        bottlenecks = []
        
        # Cost bottlenecks
        cost_data = resource_utilization.get('cost', {})
        if cost_data.get('avg_cost_per_call', 0) > 0.1:  # $0.10 per call threshold
            bottlenecks.append("High per-call costs detected")
        
        # API bottlenecks
        api_data = resource_utilization.get('api', {})
        if api_data.get('api_diversity_score', 1) < 0.1:  # Low diversity
            bottlenecks.append("Over-dependence on single API endpoint")
        
        # Session bottlenecks
        session_data = resource_utilization.get('sessions', {})
        if session_data and session_data.get('session_efficiency', 0) < 0.3:
            bottlenecks.append("Low session efficiency - short sessions with high overhead")
        
        # Compute bottlenecks
        compute_data = resource_utilization.get('compute', {})
        if compute_data.get('utilization_score', 0) > 0.8:
            bottlenecks.append("High compute utilization - approaching limits")
        
        # Time-based bottlenecks
        peak_times = self._extract_peak_times(usage_records)
        if peak_times and len(peak_times) < 3:  # Concentrated usage
            bottlenecks.append("Usage concentrated in narrow time windows")
        
        return bottlenecks
    
    async def _find_optimization_opportunities(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        resource_utilization: Dict[str, Any],
        bottlenecks: List[str]
    ) -> List[str]:
        """Find optimization opportunities"""
        opportunities = []
        
        # Cost optimization opportunities
        cost_data = resource_utilization.get('cost', {})
        if cost_data.get('cost_efficiency', 1) < 0.5:
            opportunities.append("Optimize token usage to reduce costs")
        
        # API optimization
        api_data = resource_utilization.get('api', {})
        if api_data.get('api_diversity_score', 0) > 0.8:
            opportunities.append("Consider API consolidation to reduce complexity")
        
        # Session optimization
        session_data = resource_utilization.get('sessions', {})
        if session_data and session_data.get('avg_session_length', 0) < 5:
            opportunities.append("Increase session lengths for better efficiency")
        
        # Tool usage optimization
        tool_data = resource_utilization.get('tools', {})
        if tool_data.get('tool_diversity', 0) > 10:
            opportunities.append("Standardize on fewer tools for consistency")
        
        # Load balancing opportunities
        peak_times = self._extract_peak_times(usage_records)
        if len(peak_times) > 5:
            opportunities.append("Distribute usage more evenly across time periods")
        
        # Batch processing opportunities
        if len(usage_records) > 100:
            single_call_ratio = len([r for r in usage_records if r.get('tokens_used', 0) < 50]) / len(usage_records)
            if single_call_ratio > 0.7:
                opportunities.append("Consider batching small requests for efficiency")
        
        return opportunities
    
    async def _perform_cost_analysis(
        self, 
        usage_records: List[Dict[str, Any]], 
        resource_utilization: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform comprehensive cost analysis"""
        cost_analysis = {}
        
        if not usage_records:
            return cost_analysis
        
        # Basic cost metrics
        total_cost = sum(record.get('cost_usd', 0) for record in usage_records)
        total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
        
        cost_analysis.update({
            'total_cost_usd': total_cost,
            'total_tokens': total_tokens,
            'cost_per_token': total_cost / total_tokens if total_tokens > 0 else 0,
            'avg_daily_cost': total_cost / 30,  # Assuming 30-day analysis
            'projected_monthly_cost': total_cost  # Current 30-day period
        })
        
        # Cost by resource type
        cost_by_endpoint = defaultdict(float)
        tokens_by_endpoint = defaultdict(int)
        
        for record in usage_records:
            endpoint = record.get('endpoint', 'unknown')
            cost_by_endpoint[endpoint] += record.get('cost_usd', 0)
            tokens_by_endpoint[endpoint] += record.get('tokens_used', 0)
        
        cost_analysis['cost_by_endpoint'] = dict(cost_by_endpoint)
        cost_analysis['tokens_by_endpoint'] = dict(tokens_by_endpoint)
        
        # Identify cost drivers
        sorted_costs = sorted(cost_by_endpoint.items(), key=lambda x: x[1], reverse=True)
        cost_analysis['top_cost_drivers'] = sorted_costs[:5]
        
        # Calculate potential savings
        efficiency_score = resource_utilization.get('cost', {}).get('cost_efficiency', 0.5)
        if efficiency_score < 0.7:
            potential_savings = total_cost * (0.7 - efficiency_score)
            cost_analysis['potential_savings'] = potential_savings
            cost_analysis['savings_percentage'] = (potential_savings / total_cost * 100) if total_cost > 0 else 0
        else:
            cost_analysis['potential_savings'] = 0
            cost_analysis['savings_percentage'] = 0
        
        # User tier analysis
        if user_profile:
            subscription_status = user_profile.get('subscription_status', 'free')
            cost_analysis['subscription_status'] = subscription_status
            cost_analysis['cost_tier_analysis'] = self._analyze_cost_tier_efficiency(
                total_cost, subscription_status
            )
        
        return cost_analysis
    
    def _analyze_cost_tier_efficiency(self, total_cost: float, subscription_status: str) -> Dict[str, Any]:
        """Analyze efficiency relative to subscription tier"""
        tier_limits = {
            'free': {'monthly_limit': 20, 'efficient_range': (0, 15)},
            'pro': {'monthly_limit': 200, 'efficient_range': (20, 150)},
            'enterprise': {'monthly_limit': float('inf'), 'efficient_range': (200, float('inf'))}
        }
        
        tier_info = tier_limits.get(subscription_status, tier_limits['free'])
        efficient_min, efficient_max = tier_info['efficient_range']
        
        analysis = {
            'current_usage': total_cost,
            'tier_limit': tier_info['monthly_limit'],
            'efficient_range': tier_info['efficient_range'],
            'utilization_ratio': total_cost / tier_info['monthly_limit'] if tier_info['monthly_limit'] != float('inf') else 0
        }
        
        if total_cost < efficient_min:
            analysis['recommendation'] = "Under-utilizing subscription tier"
        elif total_cost > efficient_max:
            analysis['recommendation'] = "Consider upgrading subscription tier"
        else:
            analysis['recommendation'] = "Optimal usage for current tier"
        
        return analysis
    
    async def _analyze_load_patterns(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze system load patterns"""
        load_patterns = {}
        
        if not usage_records:
            return load_patterns
        
        # Time-based load analysis
        hourly_usage = defaultdict(int)
        daily_usage = defaultdict(int)
        
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    
                    hourly_usage[dt.hour] += record.get('tokens_used', 0)
                    daily_usage[dt.date()] += record.get('tokens_used', 0)
                except:
                    continue
        
        load_patterns['hourly_distribution'] = dict(hourly_usage)
        load_patterns['daily_distribution'] = {str(k): v for k, v in daily_usage.items()}
        
        # Peak load identification
        if hourly_usage:
            peak_hour = max(hourly_usage, key=hourly_usage.get)
            peak_load = hourly_usage[peak_hour]
            avg_load = sum(hourly_usage.values()) / len(hourly_usage)
            
            load_patterns['peak_hour'] = peak_hour
            load_patterns['peak_load_tokens'] = peak_load
            load_patterns['avg_hourly_load'] = avg_load
            load_patterns['peak_to_avg_ratio'] = peak_load / avg_load if avg_load > 0 else 0
        
        # Session load patterns
        if sessions:
            session_loads = [session.get('total_tokens', 0) for session in sessions]
            if session_loads:
                load_patterns['session_load_stats'] = {
                    'max_session_tokens': max(session_loads),
                    'min_session_tokens': min(session_loads),
                    'avg_session_tokens': statistics.mean(session_loads),
                    'median_session_tokens': statistics.median(session_loads)
                }
        
        return load_patterns
    
    async def _assess_resource_efficiency(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        resource_utilization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess overall resource efficiency"""
        efficiency_metrics = {}
        
        # Token efficiency
        if usage_records:
            successful_calls = len([r for r in usage_records if r.get('response_data', {}).get('success', True)])
            efficiency_metrics['success_rate'] = successful_calls / len(usage_records)
            
            # Response quality efficiency (proxy: tokens per successful operation)
            successful_records = [r for r in usage_records if r.get('response_data', {}).get('success', True)]
            if successful_records:
                total_successful_tokens = sum(r.get('tokens_used', 0) for r in successful_records)
                efficiency_metrics['tokens_per_success'] = total_successful_tokens / len(successful_records)
            
            # Time efficiency (operations per time unit)
            time_span_hours = self._calculate_time_span_hours(usage_records)
            if time_span_hours > 0:
                efficiency_metrics['operations_per_hour'] = len(usage_records) / time_span_hours
        
        # Resource allocation efficiency
        compute_data = resource_utilization.get('compute', {})
        if compute_data:
            efficiency_metrics['compute_efficiency'] = compute_data.get('utilization_score', 0)
        
        cost_data = resource_utilization.get('cost', {})
        if cost_data:
            efficiency_metrics['cost_efficiency'] = cost_data.get('cost_efficiency', 0)
        
        # Overall efficiency score
        efficiency_scores = [
            efficiency_metrics.get('success_rate', 0.5),
            efficiency_metrics.get('compute_efficiency', 0.5),
            efficiency_metrics.get('cost_efficiency', 0.5)
        ]
        efficiency_metrics['overall_efficiency'] = sum(efficiency_scores) / len(efficiency_scores)
        
        return efficiency_metrics
    
    def _calculate_time_span_hours(self, usage_records: List[Dict[str, Any]]) -> float:
        """Calculate time span of usage records in hours"""
        if not usage_records:
            return 0.0
        
        timestamps = []
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    timestamps.append(dt)
                except:
                    continue
        
        if len(timestamps) < 2:
            return 1.0  # Default to 1 hour
        
        time_span = (max(timestamps) - min(timestamps)).total_seconds() / 3600
        return max(1.0, time_span)  # At least 1 hour
    
    def _extract_peak_times(self, usage_records: List[Dict[str, Any]]) -> List[int]:
        """Extract peak usage hours"""
        hourly_counts = defaultdict(int)
        
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    hourly_counts[dt.hour] += 1
                except:
                    continue
        
        if not hourly_counts:
            return []
        
        # Find hours with above-average usage
        avg_usage = sum(hourly_counts.values()) / len(hourly_counts)
        peak_hours = [hour for hour, count in hourly_counts.items() if count > avg_usage * 1.5]
        
        return sorted(peak_hours)
    
    def _calculate_resource_trends(self, usage_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate resource usage trends over time"""
        trends = {}
        
        if not usage_records:
            return trends
        
        # Group records by day
        daily_metrics = defaultdict(lambda: {'count': 0, 'tokens': 0, 'cost': 0})
        
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    
                    day_key = dt.date()
                    daily_metrics[day_key]['count'] += 1
                    daily_metrics[day_key]['tokens'] += record.get('tokens_used', 0)
                    daily_metrics[day_key]['cost'] += record.get('cost_usd', 0)
                except:
                    continue
        
        if len(daily_metrics) < 2:
            return trends
        
        # Calculate trends
        days = sorted(daily_metrics.keys())
        first_week = days[:7] if len(days) >= 7 else days[:len(days)//2]
        last_week = days[-7:] if len(days) >= 7 else days[len(days)//2:]
        
        first_week_avg = sum(daily_metrics[day]['tokens'] for day in first_week) / len(first_week)
        last_week_avg = sum(daily_metrics[day]['tokens'] for day in last_week) / len(last_week)
        
        trends['token_usage_trend'] = 'increasing' if last_week_avg > first_week_avg else 'decreasing'
        trends['trend_magnitude'] = abs(last_week_avg - first_week_avg) / first_week_avg if first_week_avg > 0 else 0
        
        return trends
    
    def _calculate_confidence(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        timeframe: str,
        system_context: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for system pattern analysis"""
        confidence_factors = []
        
        # Data volume factor
        record_count = len(usage_records)
        if record_count >= 100:
            confidence_factors.append(1.0)
        elif record_count >= 50:
            confidence_factors.append(0.8)
        elif record_count >= 20:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.3)
        
        # Time coverage factor
        time_span = self._calculate_time_span_hours(usage_records)
        expected_hours = 24 * 30 if timeframe == "30d" else 24 * 7  # Default expectations
        coverage = min(1.0, time_span / expected_hours)
        confidence_factors.append(coverage)
        
        # Data quality factor
        complete_records = len([r for r in usage_records if r.get('tokens_used') and r.get('endpoint')])
        data_quality = complete_records / len(usage_records) if usage_records else 0
        confidence_factors.append(data_quality)
        
        # Session data factor
        if sessions:
            session_factor = min(1.0, len(sessions) / 10)  # 10+ sessions for good confidence
            confidence_factors.append(session_factor)
        else:
            confidence_factors.append(0.3)
        
        # System context factor
        context_completeness = len(system_context) / 5.0  # Expect ~5 context fields
        confidence_factors.append(min(1.0, context_completeness))
        
        # Calculate weighted average
        weights = [0.3, 0.2, 0.2, 0.15, 0.15]  # Data volume gets highest weight
        weighted_confidence = sum(f * w for f, w in zip(confidence_factors, weights))
        
        return max(0.05, min(0.95, weighted_confidence))  # Keep in reasonable range
    
    def _determine_confidence_level(self, confidence: float) -> PredictionConfidenceLevel:
        """Determine confidence level category"""
        if confidence >= 0.8:
            return PredictionConfidenceLevel.VERY_HIGH
        elif confidence >= 0.6:
            return PredictionConfidenceLevel.HIGH
        elif confidence >= 0.4:
            return PredictionConfidenceLevel.MEDIUM
        else:
            return PredictionConfidenceLevel.LOW
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for system pattern analyzer"""
        try:
            # Test repository connections
            health_status = "healthy"
            details = {}
            
            # Test usage repository
            try:
                # Simple query to test connection
                await self.usage_repository.get_user_usage_history("health_check", limit=1)
                details["usage_repository"] = "healthy"
            except Exception as e:
                details["usage_repository"] = f"unhealthy: {str(e)}"
                health_status = "degraded"
            
            # Test session repository
            try:
                await self.session_repository.get_user_sessions("health_check", limit=1)
                details["session_repository"] = "healthy"
            except Exception as e:
                details["session_repository"] = f"unhealthy: {str(e)}"
                health_status = "degraded"
            
            return {
                "status": health_status,
                "component": "system_pattern_analyzer",
                "details": details,
                "last_check": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "system_pattern_analyzer",
                "error": str(e),
                "last_check": datetime.utcnow()
            }