"""
Capacity Planning Utilities

Utilities for capacity planning and resource scaling decisions
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics
import math


class CapacityPlanningUtils:
    """Utilities for capacity planning and resource scaling"""
    
    @staticmethod
    def calculate_capacity_requirements(
        historical_usage: List[Dict[str, Any]],
        projected_workload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate capacity requirements based on historical data and projections"""
        
        if not historical_usage:
            return {
                'baseline_capacity': 0,
                'projected_capacity': 0,
                'scaling_factor': 1.0,
                'recommendations': []
            }
        
        # Calculate baseline capacity metrics
        total_tokens = sum(record.get('tokens_used', 0) for record in historical_usage)
        total_cost = sum(record.get('cost_usd', 0) for record in historical_usage)
        total_calls = len(historical_usage)
        
        # Time span for rate calculations
        time_span_days = CapacityPlanningUtils._calculate_time_span_days(historical_usage)
        
        baseline_capacity = {
            'tokens_per_day': total_tokens / max(1, time_span_days),
            'cost_per_day': total_cost / max(1, time_span_days),
            'calls_per_day': total_calls / max(1, time_span_days),
            'avg_tokens_per_call': total_tokens / total_calls if total_calls > 0 else 0
        }
        
        # Calculate projected capacity needs
        workload_type = projected_workload.get('workload_type', 'general')
        intensity_multiplier = projected_workload.get('intensity_multiplier', 1.0)
        duration_days = projected_workload.get('duration_days', 30)
        
        # Workload-specific scaling factors
        workload_factors = {
            'machine_learning': 2.5,
            'data_analysis': 1.8,
            'content_generation': 1.5,
            'document_processing': 1.2,
            'research': 1.0,
            'development': 1.6
        }
        
        workload_factor = workload_factors.get(workload_type, 1.0)
        total_scaling_factor = workload_factor * intensity_multiplier
        
        projected_capacity = {
            'tokens_per_day': baseline_capacity['tokens_per_day'] * total_scaling_factor,
            'cost_per_day': baseline_capacity['cost_per_day'] * total_scaling_factor,
            'calls_per_day': baseline_capacity['calls_per_day'] * total_scaling_factor,
            'peak_tokens_per_day': baseline_capacity['tokens_per_day'] * total_scaling_factor * 1.5,
            'total_duration_tokens': baseline_capacity['tokens_per_day'] * total_scaling_factor * duration_days
        }
        
        # Generate scaling recommendations
        recommendations = CapacityPlanningUtils._generate_capacity_recommendations(
            baseline_capacity, projected_capacity, projected_workload
        )
        
        return {
            'baseline_capacity': baseline_capacity,
            'projected_capacity': projected_capacity,
            'scaling_factor': total_scaling_factor,
            'capacity_gap': {
                'tokens': projected_capacity['tokens_per_day'] - baseline_capacity['tokens_per_day'],
                'cost': projected_capacity['cost_per_day'] - baseline_capacity['cost_per_day']
            },
            'recommendations': recommendations
        }
    
    @staticmethod
    def _calculate_time_span_days(usage_records: List[Dict[str, Any]]) -> float:
        """Calculate time span of usage records in days"""
        if not usage_records:
            return 1.0
        
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
            return 1.0
        
        time_span = (max(timestamps) - min(timestamps)).total_seconds() / (24 * 3600)
        return max(1.0, time_span)
    
    @staticmethod
    def _generate_capacity_recommendations(
        baseline: Dict[str, Any],
        projected: Dict[str, Any],
        workload: Dict[str, Any]
    ) -> List[str]:
        """Generate capacity planning recommendations"""
        recommendations = []
        
        # Token capacity recommendations
        token_increase = projected['tokens_per_day'] / baseline['tokens_per_day'] if baseline['tokens_per_day'] > 0 else 1.0
        
        if token_increase > 3.0:
            recommendations.append("Plan for 3x+ token capacity increase")
            recommendations.append("Consider enterprise tier for high-volume usage")
        elif token_increase > 2.0:
            recommendations.append("Scale token capacity by 2x minimum")
        
        # Cost recommendations
        cost_increase = projected['cost_per_day'] / baseline['cost_per_day'] if baseline['cost_per_day'] > 0 else 1.0
        
        if cost_increase > 2.0:
            recommendations.append("Budget for 2x+ cost increase")
            recommendations.append("Implement cost monitoring and alerts")
        
        # Workload-specific recommendations
        workload_type = workload.get('workload_type', 'general')
        
        if workload_type == 'machine_learning':
            recommendations.append("Ensure high-performance compute access")
            recommendations.append("Consider model optimization for efficiency")
        elif workload_type == 'data_analysis':
            recommendations.append("Optimize for batch processing workflows")
        
        # Duration-based recommendations
        duration = workload.get('duration_days', 30)
        
        if duration > 60:
            recommendations.append("Plan for sustained high capacity over extended period")
        elif duration < 7:
            recommendations.append("Prepare for short-term capacity burst")
        
        return recommendations[:6]
    
    @staticmethod
    def assess_scaling_readiness(
        current_usage: Dict[str, Any],
        infrastructure_limits: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess readiness for scaling based on current usage and limits"""
        
        readiness_score = 1.0
        limiting_factors = []
        
        # Check against various limits
        current_tokens_per_day = current_usage.get('tokens_per_day', 0)
        current_cost_per_day = current_usage.get('cost_per_day', 0)
        
        # Token limit assessment
        token_limit = infrastructure_limits.get('daily_token_limit', float('inf'))
        if current_tokens_per_day > token_limit * 0.8:
            limiting_factors.append("Approaching daily token limit")
            readiness_score *= 0.7
        
        # Cost limit assessment
        cost_limit = infrastructure_limits.get('daily_cost_limit', float('inf'))
        if current_cost_per_day > cost_limit * 0.8:
            limiting_factors.append("Approaching daily cost limit")
            readiness_score *= 0.6
        
        # Rate limit assessment
        calls_per_minute = current_usage.get('calls_per_day', 0) / (24 * 60)
        rate_limit = infrastructure_limits.get('calls_per_minute_limit', float('inf'))
        if calls_per_minute > rate_limit * 0.8:
            limiting_factors.append("Approaching API rate limit")
            readiness_score *= 0.8
        
        # Determine readiness level
        if readiness_score > 0.8:
            readiness_level = "ready"
        elif readiness_score > 0.6:
            readiness_level = "caution"
        else:
            readiness_level = "not_ready"
        
        return {
            'readiness_score': readiness_score,
            'readiness_level': readiness_level,
            'limiting_factors': limiting_factors,
            'recommendations': CapacityPlanningUtils._generate_readiness_recommendations(
                readiness_level, limiting_factors
            )
        }
    
    @staticmethod
    def _generate_readiness_recommendations(
        readiness_level: str,
        limiting_factors: List[str]
    ) -> List[str]:
        """Generate recommendations based on scaling readiness"""
        recommendations = []
        
        if readiness_level == "not_ready":
            recommendations.append("Address limiting factors before scaling")
            recommendations.append("Consider infrastructure upgrades")
        elif readiness_level == "caution":
            recommendations.append("Monitor limits closely during scaling")
            recommendations.append("Have contingency plans ready")
        
        # Specific recommendations for limiting factors
        for factor in limiting_factors:
            if "token limit" in factor:
                recommendations.append("Upgrade token allowance or optimize usage")
            elif "cost limit" in factor:
                recommendations.append("Increase budget or implement cost controls")
            elif "rate limit" in factor:
                recommendations.append("Implement request queuing or upgrade tier")
        
        return recommendations