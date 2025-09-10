"""
Cost Analysis Utilities

Utilities for analyzing and optimizing resource costs
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class CostAnalysisUtils:
    """Utilities for cost analysis and optimization"""
    
    @staticmethod
    def analyze_cost_structure(usage_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cost structure across different dimensions"""
        if not usage_records:
            return {}
        
        total_cost = sum(record.get('cost_usd', 0) for record in usage_records)
        
        # Cost by endpoint
        cost_by_endpoint = defaultdict(float)
        # Cost by tool
        cost_by_tool = defaultdict(float)
        # Cost by time period
        cost_by_day = defaultdict(float)
        
        for record in usage_records:
            cost = record.get('cost_usd', 0)
            endpoint = record.get('endpoint', 'unknown')
            tool = record.get('tool_name', 'unknown')
            
            cost_by_endpoint[endpoint] += cost
            cost_by_tool[tool] += cost
            
            # Daily cost
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    cost_by_day[dt.date()] += cost
                except:
                    pass
        
        return {
            'total_cost': total_cost,
            'cost_by_endpoint': dict(cost_by_endpoint),
            'cost_by_tool': dict(cost_by_tool),
            'daily_costs': {str(k): v for k, v in cost_by_day.items()},
            'avg_daily_cost': sum(cost_by_day.values()) / len(cost_by_day) if cost_by_day else 0,
            'cost_drivers': sorted(cost_by_endpoint.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    @staticmethod
    def calculate_cost_efficiency_metrics(usage_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate cost efficiency metrics"""
        if not usage_records:
            return {'cost_per_token': 0, 'cost_per_operation': 0, 'efficiency_score': 0}
        
        total_cost = sum(record.get('cost_usd', 0) for record in usage_records)
        total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
        
        cost_per_token = total_cost / total_tokens if total_tokens > 0 else 0
        cost_per_operation = total_cost / len(usage_records)
        
        # Efficiency score (higher tokens per dollar = better efficiency)
        tokens_per_dollar = total_tokens / total_cost if total_cost > 0 else float('inf')
        efficiency_score = min(1.0, tokens_per_dollar / 10000)  # Normalize to 0-1
        
        return {
            'cost_per_token': cost_per_token,
            'cost_per_operation': cost_per_operation,
            'tokens_per_dollar': tokens_per_dollar,
            'efficiency_score': efficiency_score
        }


class CapacityPlanningUtils:
    """Utilities for capacity planning and resource scaling"""
    
    @staticmethod
    def calculate_capacity_requirements(
        current_usage: Dict[str, Any],
        growth_factor: float,
        duration_days: int
    ) -> Dict[str, Any]:
        """Calculate capacity requirements based on growth projections"""
        
        base_daily_tokens = current_usage.get('avg_daily_tokens', 0)
        base_daily_cost = current_usage.get('avg_daily_cost', 0)
        base_daily_calls = current_usage.get('avg_daily_calls', 0)
        
        # Apply growth factor
        projected_daily_tokens = base_daily_tokens * growth_factor
        projected_daily_cost = base_daily_cost * growth_factor
        projected_daily_calls = base_daily_calls * growth_factor
        
        return {
            'projected_daily_tokens': projected_daily_tokens,
            'projected_daily_cost': projected_daily_cost,
            'projected_daily_calls': projected_daily_calls,
            'total_projected_tokens': projected_daily_tokens * duration_days,
            'total_projected_cost': projected_daily_cost * duration_days,
            'capacity_buffer_needed': max(1.2, growth_factor * 1.1)  # 20% minimum buffer
        }
    
    @staticmethod
    def recommend_scaling_strategy(
        current_capacity: Dict[str, Any],
        projected_needs: Dict[str, Any]
    ) -> List[str]:
        """Recommend scaling strategy based on capacity analysis"""
        recommendations = []
        
        current_tokens = current_capacity.get('avg_daily_tokens', 0)
        projected_tokens = projected_needs.get('projected_daily_tokens', 0)
        
        if projected_tokens > current_tokens * 2:
            recommendations.append("Implement gradual scaling over time")
            recommendations.append("Consider premium tier for better rate limits")
        elif projected_tokens > current_tokens * 1.5:
            recommendations.append("Monitor usage closely and scale incrementally")
        
        return recommendations


class CostProjectionUtils:
    """Utilities for cost projections and budgeting"""
    
    @staticmethod
    def project_costs(
        baseline_costs: Dict[str, Any],
        workload_multiplier: float,
        duration_days: int
    ) -> Dict[str, Any]:
        """Project costs for upcoming workload"""
        
        daily_cost = baseline_costs.get('avg_daily_cost', 0)
        projected_daily_cost = daily_cost * workload_multiplier
        
        return {
            'daily_cost_projection': projected_daily_cost,
            'total_cost_projection': projected_daily_cost * duration_days,
            'cost_range': {
                'low': projected_daily_cost * duration_days * 0.8,
                'high': projected_daily_cost * duration_days * 1.3
            },
            'budget_recommendation': projected_daily_cost * duration_days * 1.2  # 20% buffer
        }
    
    @staticmethod
    def analyze_cost_trends(usage_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cost trends over time"""
        if not usage_records:
            return {}
        
        # Group by week for trend analysis
        weekly_costs = defaultdict(float)
        
        for record in usage_records:
            created_at = record.get('created_at')
            cost = record.get('cost_usd', 0)
            
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    
                    # Get week start (Monday)
                    week_start = dt - timedelta(days=dt.weekday())
                    week_key = week_start.date()
                    weekly_costs[week_key] += cost
                except:
                    pass
        
        if len(weekly_costs) < 2:
            return {'trend': 'insufficient_data'}
        
        costs = list(weekly_costs.values())
        recent_avg = sum(costs[-2:]) / 2 if len(costs) >= 2 else costs[-1]
        earlier_avg = sum(costs[:2]) / 2 if len(costs) >= 2 else costs[0]
        
        if recent_avg > earlier_avg * 1.1:
            trend = 'increasing'
        elif recent_avg < earlier_avg * 0.9:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'recent_weekly_avg': recent_avg,
            'earlier_weekly_avg': earlier_avg,
            'trend_magnitude': (recent_avg - earlier_avg) / earlier_avg if earlier_avg > 0 else 0
        }