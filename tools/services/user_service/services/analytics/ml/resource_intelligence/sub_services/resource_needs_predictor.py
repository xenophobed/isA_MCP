"""
Resource Needs Predictor

Predicts future resource requirements based on planned workloads
Maps to predict_resource_needs MCP tool
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
import statistics
import math

from ...prediction_models import ResourceNeedsPrediction, PredictionConfidenceLevel
from ..utilities.capacity_planning_utils import CapacityPlanningUtils
from ..utilities.cost_projection_utils import CostProjectionUtils

# Import user service repositories
from tools.services.user_service.repositories.usage_repository import UsageRepository
from tools.services.user_service.repositories.session_repository import SessionRepository
from tools.services.user_service.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class ResourceNeedsPredictor:
    """
    Predicts future resource requirements based on planned workloads
    Analyzes historical patterns to forecast resource needs and costs
    """
    
    def __init__(self):
        """Initialize repositories and utilities"""
        self.usage_repository = UsageRepository()
        self.session_repository = SessionRepository()
        self.user_repository = UserRepository()
        self.capacity_utils = CapacityPlanningUtils()
        self.cost_utils = CostProjectionUtils()
        
        # Workload type resource multipliers
        self.workload_multipliers = {
            "data_analysis": {"compute": 1.5, "memory": 2.0, "cost": 1.3},
            "machine_learning": {"compute": 3.0, "memory": 2.5, "cost": 2.5},
            "content_generation": {"compute": 2.0, "memory": 1.2, "cost": 1.8},
            "document_processing": {"compute": 1.2, "memory": 1.5, "cost": 1.1},
            "research": {"compute": 1.0, "memory": 1.0, "cost": 1.0},
            "development": {"compute": 1.8, "memory": 1.3, "cost": 1.4},
            "collaboration": {"compute": 0.8, "memory": 1.0, "cost": 0.9}
        }
        
        logger.info("Resource Needs Predictor initialized")
    
    async def predict_needs(
        self, 
        user_id: str, 
        upcoming_workload: Dict[str, Any]
    ) -> ResourceNeedsPrediction:
        """
        Predict resource needs for upcoming workload
        
        Args:
            user_id: User identifier
            upcoming_workload: Planned workload information
            
        Returns:
            ResourcePrediction: Predicted resource requirements and recommendations
        """
        try:
            logger.info(f"Predicting resource needs for user {user_id}")
            
            # Get historical data for baseline patterns
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=60)  # 60-day history for better patterns
            
            usage_records = await self.usage_repository.get_user_usage_history(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=3000  # Extended limit for pattern analysis
            )
            
            sessions = await self.session_repository.get_user_sessions(
                user_id=user_id,
                limit=150
            )
            
            user_profile = await self.user_repository.get_user_profile(user_id)
            
            logger.info(f"Retrieved {len(usage_records)} usage records and {len(sessions)} sessions for baseline")
            
            # Analyze current baseline resource patterns
            baseline_patterns = await self._analyze_baseline_patterns(
                usage_records, sessions, user_profile
            )
            
            # Predict resource requirements based on workload
            predicted_requirements = await self._predict_requirements(
                upcoming_workload, baseline_patterns, usage_records
            )
            
            # Generate scaling recommendations
            scaling_recommendations = await self._generate_scaling_recommendations(
                predicted_requirements, baseline_patterns, upcoming_workload
            )
            
            # Project costs
            cost_projections = await self._project_costs(
                predicted_requirements, baseline_patterns, upcoming_workload
            )
            
            # Generate resource alerts
            resource_alerts = await self._generate_resource_alerts(
                predicted_requirements, baseline_patterns, user_profile
            )
            
            # Calculate prediction confidence
            confidence = self._calculate_prediction_confidence(
                usage_records, sessions, upcoming_workload, baseline_patterns
            )
            
            # Extract key metrics for the model
            cpu_estimate = min(1.0, predicted_requirements.get('compute_requirements', {}).get('processing_intensity', 0.5))
            memory_estimate = predicted_requirements.get('compute_requirements', {}).get('memory_needed_gb', 2.0)
            duration_estimate = upcoming_workload.get('duration_days', 30) * 24 * 3600  # Convert to seconds
            cost_estimate = predicted_requirements.get('total_predicted_cost', 10.0)
            
            return ResourceNeedsPrediction(
                user_id=user_id,
                confidence=confidence,
                confidence_level=self._determine_confidence_level(confidence),
                estimated_cpu=cpu_estimate,
                estimated_memory=memory_estimate,
                estimated_duration=duration_estimate,
                cost_estimate=cost_estimate,
                high_cpu_usage_predicted=cpu_estimate > 0.7,
                memory_intensive_predicted=memory_estimate > 8.0,
                metadata={
                    "prediction_date": datetime.utcnow(),
                    "baseline_records": len(usage_records),
                    "baseline_sessions": len(sessions),
                    "workload_type": upcoming_workload.get("workload_type", "unknown"),
                    "prediction_horizon": upcoming_workload.get("duration_days", 30),
                    "predicted_requirements": predicted_requirements,
                    "scaling_recommendations": scaling_recommendations,
                    "cost_projections": cost_projections,
                    "resource_alerts": resource_alerts
                }
            )
            
        except Exception as e:
            logger.error(f"Error predicting resource needs for user {user_id}: {e}")
            raise
    
    async def _analyze_baseline_patterns(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze baseline resource usage patterns"""
        baseline = {}
        
        if not usage_records:
            return {
                "avg_daily_tokens": 0,
                "avg_daily_cost": 0,
                "avg_daily_calls": 0,
                "peak_usage_multiplier": 1.0,
                "resource_efficiency": 0.5
            }
        
        # Calculate daily averages
        daily_metrics = defaultdict(lambda: {'tokens': 0, 'cost': 0, 'calls': 0})
        
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    
                    day_key = dt.date()
                    daily_metrics[day_key]['tokens'] += record.get('tokens_used', 0)
                    daily_metrics[day_key]['cost'] += record.get('cost_usd', 0)
                    daily_metrics[day_key]['calls'] += 1
                except:
                    continue
        
        if daily_metrics:
            daily_tokens = [metrics['tokens'] for metrics in daily_metrics.values()]
            daily_costs = [metrics['cost'] for metrics in daily_metrics.values()]
            daily_calls = [metrics['calls'] for metrics in daily_metrics.values()]
            
            baseline.update({
                'avg_daily_tokens': statistics.mean(daily_tokens),
                'avg_daily_cost': statistics.mean(daily_costs),
                'avg_daily_calls': statistics.mean(daily_calls),
                'max_daily_tokens': max(daily_tokens),
                'max_daily_cost': max(daily_costs),
                'peak_usage_multiplier': max(daily_tokens) / statistics.mean(daily_tokens) if statistics.mean(daily_tokens) > 0 else 1.0
            })
        
        # Analyze tool usage patterns
        tool_usage = Counter(record.get('tool_name', 'unknown') for record in usage_records)
        baseline['primary_tools'] = dict(tool_usage.most_common(5))
        
        # Analyze endpoint patterns
        endpoint_usage = Counter(record.get('endpoint', 'unknown') for record in usage_records)
        baseline['primary_endpoints'] = dict(endpoint_usage.most_common(5))
        
        # Calculate resource efficiency
        total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
        total_cost = sum(record.get('cost_usd', 0) for record in usage_records)
        
        if total_cost > 0:
            baseline['tokens_per_dollar'] = total_tokens / total_cost
            baseline['resource_efficiency'] = min(1.0, (total_tokens / total_cost) / 10000)  # Normalize
        else:
            baseline['tokens_per_dollar'] = float('inf')
            baseline['resource_efficiency'] = 1.0
        
        # Analyze session patterns
        if sessions:
            session_tokens = [session.get('total_tokens', 0) for session in sessions]
            session_messages = [session.get('message_count', 0) for session in sessions]
            
            baseline.update({
                'avg_session_tokens': statistics.mean(session_tokens) if session_tokens else 0,
                'avg_session_messages': statistics.mean(session_messages) if session_messages else 0,
                'session_efficiency': (sum(session_tokens) / sum(session_messages)) if sum(session_messages) > 0 else 0
            })
        
        # User profile factors
        if user_profile:
            subscription_status = user_profile.get('subscription_status', 'free')
            baseline['subscription_tier'] = subscription_status
            baseline['user_experience_level'] = self._infer_experience_level(usage_records, user_profile)
        
        return baseline
    
    def _infer_experience_level(
        self, 
        usage_records: List[Dict[str, Any]], 
        user_profile: Dict[str, Any]
    ) -> str:
        """Infer user experience level from usage patterns"""
        if not usage_records:
            return "beginner"
        
        # Advanced usage indicators
        advanced_indicators = 0
        total_records = len(usage_records)
        
        # Tool diversity
        unique_tools = len(set(record.get('tool_name', '') for record in usage_records))
        if unique_tools > 5:
            advanced_indicators += 1
        
        # High token usage per call (complex queries)
        avg_tokens = sum(record.get('tokens_used', 0) for record in usage_records) / total_records
        if avg_tokens > 200:
            advanced_indicators += 1
        
        # API diversity
        unique_endpoints = len(set(record.get('endpoint', '') for record in usage_records))
        if unique_endpoints > 3:
            advanced_indicators += 1
        
        # Cost per operation (willingness to use expensive operations)
        avg_cost = sum(record.get('cost_usd', 0) for record in usage_records) / total_records
        if avg_cost > 0.05:
            advanced_indicators += 1
        
        # Account age from profile
        if user_profile.get('created_at'):
            try:
                created_at = user_profile['created_at']
                if isinstance(created_at, str):
                    account_age = (datetime.utcnow() - datetime.fromisoformat(created_at.replace('Z', '+00:00'))).days
                else:
                    account_age = (datetime.utcnow() - created_at).days
                
                if account_age > 90:  # 3+ months
                    advanced_indicators += 1
            except:
                pass
        
        if advanced_indicators >= 4:
            return "expert"
        elif advanced_indicators >= 2:
            return "intermediate"
        else:
            return "beginner"
    
    async def _predict_requirements(
        self, 
        upcoming_workload: Dict[str, Any], 
        baseline_patterns: Dict[str, Any],
        usage_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Predict resource requirements for upcoming workload"""
        requirements = {}
        
        # Extract workload characteristics
        workload_type = upcoming_workload.get("workload_type", "general")
        duration_days = upcoming_workload.get("duration_days", 30)
        intensity_multiplier = upcoming_workload.get("intensity_multiplier", 1.0)
        expected_volume = upcoming_workload.get("expected_volume", "normal")
        
        # Get baseline daily averages
        baseline_daily_tokens = baseline_patterns.get('avg_daily_tokens', 100)
        baseline_daily_cost = baseline_patterns.get('avg_daily_cost', 1.0)
        baseline_daily_calls = baseline_patterns.get('avg_daily_calls', 10)
        
        # Apply workload-specific multipliers
        workload_multiplier = self.workload_multipliers.get(workload_type, {
            "compute": 1.0, "memory": 1.0, "cost": 1.0
        })
        
        # Volume scaling
        volume_multipliers = {
            "low": 0.5,
            "normal": 1.0,
            "high": 2.0,
            "very_high": 4.0
        }
        volume_multiplier = volume_multipliers.get(expected_volume, 1.0)
        
        # Calculate predicted daily requirements
        predicted_daily_tokens = (
            baseline_daily_tokens * 
            workload_multiplier["compute"] * 
            intensity_multiplier * 
            volume_multiplier
        )
        
        predicted_daily_cost = (
            baseline_daily_cost * 
            workload_multiplier["cost"] * 
            intensity_multiplier * 
            volume_multiplier
        )
        
        predicted_daily_calls = (
            baseline_daily_calls * 
            volume_multiplier * 
            intensity_multiplier
        )
        
        # Total predictions for the workload duration
        requirements.update({
            # Daily predictions
            'predicted_daily_tokens': predicted_daily_tokens,
            'predicted_daily_cost': predicted_daily_cost,
            'predicted_daily_calls': predicted_daily_calls,
            
            # Total predictions
            'total_predicted_tokens': predicted_daily_tokens * duration_days,
            'total_predicted_cost': predicted_daily_cost * duration_days,
            'total_predicted_calls': predicted_daily_calls * duration_days,
            
            # Peak predictions (using baseline peak multiplier)
            'peak_daily_tokens': predicted_daily_tokens * baseline_patterns.get('peak_usage_multiplier', 1.5),
            'peak_daily_cost': predicted_daily_cost * baseline_patterns.get('peak_usage_multiplier', 1.5),
            
            # Resource categories
            'compute_requirements': {
                'tokens_per_day': predicted_daily_tokens,
                'processing_intensity': workload_multiplier["compute"],
                'parallel_capacity_needed': self._estimate_parallel_capacity(upcoming_workload)
            },
            
            'cost_requirements': {
                'daily_budget_needed': predicted_daily_cost,
                'total_budget_needed': predicted_daily_cost * duration_days,
                'cost_efficiency_target': baseline_patterns.get('resource_efficiency', 0.5)
            },
            
            'api_requirements': {
                'calls_per_day': predicted_daily_calls,
                'rate_limit_buffer': max(1.2, predicted_daily_calls / (24 * 60)),  # per minute
                'concurrent_connections_needed': math.ceil(predicted_daily_calls / (24 * 60 * 60) * 10)  # peak estimate
            }
        })
        
        # Add workload-specific requirements
        if workload_type == "machine_learning":
            requirements['specialized_requirements'] = {
                'gpu_compute': True,
                'large_context_windows': True,
                'batch_processing_capability': True,
                'model_fine_tuning_resources': upcoming_workload.get('requires_fine_tuning', False)
            }
        elif workload_type == "data_analysis":
            requirements['specialized_requirements'] = {
                'data_processing_tools': True,
                'visualization_capabilities': True,
                'statistical_computing': True,
                'large_dataset_handling': upcoming_workload.get('dataset_size', 'medium') == 'large'
            }
        
        return requirements
    
    def _estimate_parallel_capacity(self, upcoming_workload: Dict[str, Any]) -> int:
        """Estimate parallel processing capacity needed"""
        concurrent_users = upcoming_workload.get("concurrent_users", 1)
        batch_size = upcoming_workload.get("batch_operations", 1)
        urgency_factor = {"low": 1, "normal": 2, "high": 4, "critical": 8}.get(
            upcoming_workload.get("urgency", "normal"), 2
        )
        
        return max(1, concurrent_users * batch_size * urgency_factor)
    
    async def _generate_scaling_recommendations(
        self, 
        predicted_requirements: Dict[str, Any], 
        baseline_patterns: Dict[str, Any],
        upcoming_workload: Dict[str, Any]
    ) -> List[str]:
        """Generate scaling recommendations based on predictions"""
        recommendations = []
        
        # Token scaling recommendations
        predicted_daily_tokens = predicted_requirements.get('predicted_daily_tokens', 0)
        baseline_daily_tokens = baseline_patterns.get('avg_daily_tokens', 100)
        
        if predicted_daily_tokens > baseline_daily_tokens * 3:
            recommendations.append("Consider upgrading to higher token limits")
            recommendations.append("Implement token usage monitoring and alerts")
        elif predicted_daily_tokens > baseline_daily_tokens * 1.5:
            recommendations.append("Monitor token usage closely during workload")
        
        # Cost scaling recommendations
        predicted_daily_cost = predicted_requirements.get('predicted_daily_cost', 0)
        baseline_daily_cost = baseline_patterns.get('avg_daily_cost', 1.0)
        
        if predicted_daily_cost > baseline_daily_cost * 2:
            recommendations.append("Budget for increased operational costs")
            recommendations.append("Consider cost optimization strategies")
        
        # Subscription tier recommendations
        current_tier = baseline_patterns.get('subscription_tier', 'free')
        total_predicted_cost = predicted_requirements.get('total_predicted_cost', 0)
        
        tier_thresholds = {'free': 20, 'pro': 200, 'enterprise': float('inf')}
        current_limit = tier_thresholds.get(current_tier, 20)
        
        if total_predicted_cost > current_limit * 0.8:
            if current_tier == 'free':
                recommendations.append("Consider upgrading to Pro tier for this workload")
            elif current_tier == 'pro' and total_predicted_cost > 200:
                recommendations.append("Consider Enterprise tier for large-scale workload")
        
        # Parallel processing recommendations
        parallel_capacity = predicted_requirements.get('compute_requirements', {}).get('parallel_capacity_needed', 1)
        if parallel_capacity > 5:
            recommendations.append("Implement batch processing for efficiency")
            recommendations.append("Consider workload distribution across time")
        
        # API rate limiting recommendations
        api_reqs = predicted_requirements.get('api_requirements', {})
        calls_per_day = api_reqs.get('calls_per_day', 0)
        
        if calls_per_day > 10000:
            recommendations.append("Implement request queuing and rate limiting")
            recommendations.append("Consider API optimization to reduce call frequency")
        
        # Workload-specific recommendations
        workload_type = upcoming_workload.get("workload_type", "general")
        
        if workload_type == "machine_learning":
            recommendations.append("Pre-warm ML models for faster response times")
            recommendations.append("Consider model caching for repeated operations")
        elif workload_type == "data_analysis":
            recommendations.append("Optimize data preprocessing to reduce compute load")
            recommendations.append("Consider incremental processing for large datasets")
        
        # Timeline-based recommendations
        duration_days = upcoming_workload.get("duration_days", 30)
        if duration_days < 7:
            recommendations.append("Short-term workload: Focus on immediate capacity scaling")
        elif duration_days > 90:
            recommendations.append("Long-term workload: Implement gradual scaling strategy")
        
        return recommendations[:8]  # Limit to top 8 recommendations
    
    async def _project_costs(
        self, 
        predicted_requirements: Dict[str, Any], 
        baseline_patterns: Dict[str, Any],
        upcoming_workload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Project costs for the upcoming workload"""
        projections = {}
        
        # Basic cost projections
        total_predicted_cost = predicted_requirements.get('total_predicted_cost', 0)
        daily_predicted_cost = predicted_requirements.get('predicted_daily_cost', 0)
        duration_days = upcoming_workload.get("duration_days", 30)
        
        projections.update({
            'total_cost_estimate': total_predicted_cost,
            'daily_cost_estimate': daily_predicted_cost,
            'peak_daily_cost_estimate': predicted_requirements.get('peak_daily_cost', 0),
            'cost_confidence_range': {
                'low_estimate': total_predicted_cost * 0.7,
                'high_estimate': total_predicted_cost * 1.4,
                'most_likely': total_predicted_cost
            }
        })
        
        # Cost breakdown by category
        compute_ratio = 0.6  # Typical ratio for compute costs
        api_ratio = 0.3     # API call costs
        overhead_ratio = 0.1 # Infrastructure overhead
        
        projections['cost_breakdown'] = {
            'compute_costs': total_predicted_cost * compute_ratio,
            'api_costs': total_predicted_cost * api_ratio,
            'infrastructure_overhead': total_predicted_cost * overhead_ratio
        }
        
        # Compare to baseline
        baseline_monthly_cost = baseline_patterns.get('avg_daily_cost', 1.0) * 30
        cost_increase_factor = total_predicted_cost / baseline_monthly_cost if baseline_monthly_cost > 0 else 1.0
        
        projections['cost_comparison'] = {
            'baseline_monthly_cost': baseline_monthly_cost,
            'projected_increase_factor': cost_increase_factor,
            'additional_cost': total_predicted_cost - (baseline_monthly_cost * (duration_days / 30))
        }
        
        # ROI and efficiency projections
        current_efficiency = baseline_patterns.get('tokens_per_dollar', 1000)
        workload_type = upcoming_workload.get("workload_type", "general")
        
        # Estimate efficiency changes based on workload type
        efficiency_factors = {
            "machine_learning": 0.8,  # More expensive per token
            "data_analysis": 1.1,     # Good efficiency
            "content_generation": 0.9,
            "document_processing": 1.2,
            "research": 1.0,
            "development": 1.0
        }
        
        expected_efficiency = current_efficiency * efficiency_factors.get(workload_type, 1.0)
        
        projections['efficiency_projections'] = {
            'current_tokens_per_dollar': current_efficiency,
            'projected_tokens_per_dollar': expected_efficiency,
            'efficiency_change': expected_efficiency / current_efficiency if current_efficiency > 0 else 1.0
        }
        
        # Budget recommendations
        projections['budget_recommendations'] = {
            'recommended_budget': total_predicted_cost * 1.2,  # 20% buffer
            'critical_budget_threshold': total_predicted_cost * 1.5,
            'daily_budget_alert_threshold': daily_predicted_cost * 1.3
        }
        
        return projections
    
    async def _generate_resource_alerts(
        self, 
        predicted_requirements: Dict[str, Any], 
        baseline_patterns: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate resource alerts based on predictions"""
        alerts = []
        
        # Cost alerts
        total_cost = predicted_requirements.get('total_predicted_cost', 0)
        current_tier = baseline_patterns.get('subscription_tier', 'free')
        
        tier_limits = {'free': 20, 'pro': 200, 'enterprise': 1000}
        current_limit = tier_limits.get(current_tier, 20)
        
        if total_cost > current_limit:
            alerts.append(f"CRITICAL: Predicted cost (${total_cost:.2f}) exceeds {current_tier} tier limit (${current_limit})")
        elif total_cost > current_limit * 0.8:
            alerts.append(f"WARNING: Predicted cost approaching {current_tier} tier limit")
        
        # Token usage alerts
        predicted_tokens = predicted_requirements.get('total_predicted_tokens', 0)
        if predicted_tokens > 1000000:  # 1M tokens
            alerts.append("HIGH: Very high token usage predicted - consider optimization")
        elif predicted_tokens > 500000:  # 500K tokens
            alerts.append("MEDIUM: High token usage predicted - monitor closely")
        
        # API rate alerts
        api_reqs = predicted_requirements.get('api_requirements', {})
        calls_per_day = api_reqs.get('calls_per_day', 0)
        
        if calls_per_day > 50000:
            alerts.append("CRITICAL: Very high API usage - check rate limits")
        elif calls_per_day > 10000:
            alerts.append("WARNING: High API usage predicted")
        
        # Parallel capacity alerts
        parallel_needed = predicted_requirements.get('compute_requirements', {}).get('parallel_capacity_needed', 1)
        if parallel_needed > 10:
            alerts.append("MEDIUM: High parallel processing needs - ensure adequate capacity")
        
        # Efficiency alerts
        baseline_efficiency = baseline_patterns.get('resource_efficiency', 0.5)
        if baseline_efficiency < 0.3:
            alerts.append("OPTIMIZATION: Low baseline efficiency detected - consider optimization")
        
        # Experience level alerts
        user_experience = baseline_patterns.get('user_experience_level', 'beginner')
        if user_experience == 'beginner' and total_cost > 50:
            alerts.append("GUIDANCE: High cost predicted for new user - consider guidance resources")
        
        # Specialized requirement alerts
        specialized = predicted_requirements.get('specialized_requirements', {})
        if specialized.get('gpu_compute'):
            alerts.append("RESOURCE: GPU compute resources required")
        if specialized.get('large_dataset_handling'):
            alerts.append("RESOURCE: Large dataset processing capabilities needed")
        
        return alerts[:6]  # Limit to top 6 most important alerts
    
    def _analyze_workload_characteristics(self, upcoming_workload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze characteristics of the upcoming workload"""
        analysis = {}
        
        workload_type = upcoming_workload.get("workload_type", "general")
        duration_days = upcoming_workload.get("duration_days", 30)
        intensity = upcoming_workload.get("intensity_multiplier", 1.0)
        volume = upcoming_workload.get("expected_volume", "normal")
        
        analysis.update({
            'workload_classification': workload_type,
            'duration_category': self._classify_duration(duration_days),
            'intensity_level': self._classify_intensity(intensity),
            'volume_level': volume,
            'complexity_score': self._calculate_workload_complexity(upcoming_workload),
            'risk_level': self._assess_workload_risk(upcoming_workload)
        })
        
        # Add workload-specific characteristics
        if workload_type in self.workload_multipliers:
            multipliers = self.workload_multipliers[workload_type]
            analysis['resource_intensity'] = {
                'compute_intensive': multipliers["compute"] > 1.5,
                'memory_intensive': multipliers["memory"] > 1.5,
                'cost_intensive': multipliers["cost"] > 1.5
            }
        
        return analysis
    
    def _classify_duration(self, duration_days: int) -> str:
        """Classify workload duration"""
        if duration_days <= 7:
            return "short_term"
        elif duration_days <= 30:
            return "medium_term"
        elif duration_days <= 90:
            return "long_term"
        else:
            return "extended"
    
    def _classify_intensity(self, intensity_multiplier: float) -> str:
        """Classify workload intensity"""
        if intensity_multiplier >= 3.0:
            return "very_high"
        elif intensity_multiplier >= 2.0:
            return "high"
        elif intensity_multiplier >= 1.5:
            return "medium"
        else:
            return "low"
    
    def _calculate_workload_complexity(self, upcoming_workload: Dict[str, Any]) -> float:
        """Calculate workload complexity score"""
        complexity_factors = []
        
        # Type complexity
        type_complexity = {
            "machine_learning": 0.9,
            "data_analysis": 0.7,
            "content_generation": 0.6,
            "document_processing": 0.4,
            "research": 0.3,
            "development": 0.8,
            "collaboration": 0.2
        }
        complexity_factors.append(
            type_complexity.get(upcoming_workload.get("workload_type", "general"), 0.5)
        )
        
        # Volume complexity
        volume_complexity = {"low": 0.2, "normal": 0.5, "high": 0.8, "very_high": 1.0}
        complexity_factors.append(
            volume_complexity.get(upcoming_workload.get("expected_volume", "normal"), 0.5)
        )
        
        # Duration complexity (longer = more complex coordination)
        duration_days = upcoming_workload.get("duration_days", 30)
        duration_complexity = min(1.0, duration_days / 90)
        complexity_factors.append(duration_complexity)
        
        # Intensity complexity
        intensity = upcoming_workload.get("intensity_multiplier", 1.0)
        intensity_complexity = min(1.0, intensity / 3.0)
        complexity_factors.append(intensity_complexity)
        
        # Additional factors
        if upcoming_workload.get("concurrent_users", 1) > 5:
            complexity_factors.append(0.8)
        if upcoming_workload.get("requires_fine_tuning", False):
            complexity_factors.append(0.9)
        if upcoming_workload.get("dataset_size") == "large":
            complexity_factors.append(0.7)
        
        return sum(complexity_factors) / len(complexity_factors)
    
    def _assess_workload_risk(self, upcoming_workload: Dict[str, Any]) -> str:
        """Assess overall workload risk level"""
        risk_factors = 0
        
        # High resource requirements
        if upcoming_workload.get("intensity_multiplier", 1.0) > 2.0:
            risk_factors += 1
        if upcoming_workload.get("expected_volume") in ["high", "very_high"]:
            risk_factors += 1
        
        # Complex workload types
        if upcoming_workload.get("workload_type") in ["machine_learning", "development"]:
            risk_factors += 1
        
        # Timeline pressure
        if upcoming_workload.get("urgency") in ["high", "critical"]:
            risk_factors += 1
        if upcoming_workload.get("duration_days", 30) < 7:
            risk_factors += 1
        
        # Resource constraints
        if upcoming_workload.get("concurrent_users", 1) > 10:
            risk_factors += 1
        
        if risk_factors >= 4:
            return "high"
        elif risk_factors >= 2:
            return "medium"
        else:
            return "low"
    
    def _create_timeline_projections(
        self, 
        predicted_requirements: Dict[str, Any], 
        upcoming_workload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create timeline-based resource projections"""
        duration_days = upcoming_workload.get("duration_days", 30)
        daily_tokens = predicted_requirements.get('predicted_daily_tokens', 0)
        daily_cost = predicted_requirements.get('predicted_daily_cost', 0)
        
        # Create weekly projections
        weeks = max(1, math.ceil(duration_days / 7))
        weekly_projections = []
        
        for week in range(weeks):
            week_start = week * 7
            week_end = min((week + 1) * 7, duration_days)
            week_days = week_end - week_start
            
            # Apply ramping factor (workloads often start slower)
            if week == 0:
                ramp_factor = 0.7  # First week slower
            elif week == weeks - 1 and weeks > 1:
                ramp_factor = 0.8  # Last week may be slower
            else:
                ramp_factor = 1.0
            
            weekly_projections.append({
                'week': week + 1,
                'days': week_days,
                'tokens': daily_tokens * week_days * ramp_factor,
                'cost': daily_cost * week_days * ramp_factor,
                'ramp_factor': ramp_factor
            })
        
        return {
            'total_duration_days': duration_days,
            'weekly_projections': weekly_projections,
            'peak_week': max(weekly_projections, key=lambda x: x['tokens'])['week'] if weekly_projections else 1,
            'total_timeline_cost': sum(wp['cost'] for wp in weekly_projections),
            'cost_distribution': 'front_loaded' if duration_days > 14 else 'uniform'
        }
    
    def _calculate_prediction_confidence(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        upcoming_workload: Dict[str, Any],
        baseline_patterns: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for resource prediction"""
        confidence_factors = []
        
        # Historical data quality
        if len(usage_records) >= 200:
            confidence_factors.append(0.9)
        elif len(usage_records) >= 100:
            confidence_factors.append(0.8)
        elif len(usage_records) >= 50:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.3)
        
        # Data recency and consistency
        if usage_records:
            recent_records = [r for r in usage_records[-30:]]  # Last 30 records
            if len(recent_records) >= 20:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.5)
        
        # Workload specification completeness
        workload_completeness = 0
        required_fields = ['workload_type', 'duration_days', 'expected_volume']
        for field in required_fields:
            if upcoming_workload.get(field):
                workload_completeness += 1
        
        confidence_factors.append(workload_completeness / len(required_fields))
        
        # Baseline pattern stability
        peak_multiplier = baseline_patterns.get('peak_usage_multiplier', 1.0)
        if 1.2 <= peak_multiplier <= 3.0:  # Reasonable variation
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)
        
        # Experience level factor
        experience = baseline_patterns.get('user_experience_level', 'beginner')
        experience_confidence = {'expert': 0.9, 'intermediate': 0.7, 'beginner': 0.5}
        confidence_factors.append(experience_confidence[experience])
        
        # Calculate weighted confidence
        weights = [0.3, 0.2, 0.2, 0.15, 0.15]
        weighted_confidence = sum(f * w for f, w in zip(confidence_factors, weights))
        
        return max(0.1, min(0.95, weighted_confidence))
    
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
        """Health check for resource needs predictor"""
        try:
            health_status = "healthy"
            details = {}
            
            # Test repository connections
            try:
                await self.usage_repository.get_user_usage_history("health_check", limit=1)
                details["usage_repository"] = "healthy"
            except Exception as e:
                details["usage_repository"] = f"unhealthy: {str(e)}"
                health_status = "degraded"
            
            try:
                await self.session_repository.get_user_sessions("health_check", limit=1)
                details["session_repository"] = "healthy"
            except Exception as e:
                details["session_repository"] = f"unhealthy: {str(e)}"
                health_status = "degraded"
            
            return {
                "status": health_status,
                "component": "resource_needs_predictor",
                "details": details,
                "last_check": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "resource_needs_predictor",
                "error": str(e),
                "last_check": datetime.utcnow()
            }