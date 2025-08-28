"""
Cost Projection Utilities

Utilities for projecting and analyzing future costs
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics


class CostProjectionUtils:
    """Utilities for cost projections and financial analysis"""
    
    @staticmethod
    def project_workload_costs(
        baseline_costs: Dict[str, Any],
        workload_characteristics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Project costs for a specific workload"""
        
        # Extract baseline metrics
        daily_cost = baseline_costs.get('avg_daily_cost', 0)
        cost_per_token = baseline_costs.get('cost_per_token', 0.001)  # Default estimate
        
        # Extract workload characteristics
        workload_type = workload_characteristics.get('workload_type', 'general')
        duration_days = workload_characteristics.get('duration_days', 30)
        intensity_multiplier = workload_characteristics.get('intensity_multiplier', 1.0)
        expected_volume = workload_characteristics.get('expected_volume', 'normal')
        
        # Cost multipliers by workload type
        cost_multipliers = {
            'machine_learning': 2.2,
            'data_analysis': 1.4,
            'content_generation': 1.6,
            'document_processing': 1.1,
            'research': 1.0,
            'development': 1.3,
            'collaboration': 0.9
        }
        
        # Volume multipliers
        volume_multipliers = {
            'low': 0.6,
            'normal': 1.0,
            'high': 1.8,
            'very_high': 3.2
        }
        
        workload_multiplier = cost_multipliers.get(workload_type, 1.0)
        volume_multiplier = volume_multipliers.get(expected_volume, 1.0)
        
        # Calculate projected costs
        projected_daily_cost = daily_cost * workload_multiplier * intensity_multiplier * volume_multiplier
        total_projected_cost = projected_daily_cost * duration_days
        
        # Calculate confidence intervals
        confidence_range = CostProjectionUtils._calculate_cost_confidence_range(
            total_projected_cost, workload_characteristics
        )
        
        return {
            'daily_cost_projection': projected_daily_cost,
            'total_cost_projection': total_projected_cost,
            'cost_breakdown': {
                'base_cost': daily_cost * duration_days,
                'workload_adjustment': (workload_multiplier - 1) * daily_cost * duration_days,
                'intensity_adjustment': (intensity_multiplier - 1) * daily_cost * duration_days,
                'volume_adjustment': (volume_multiplier - 1) * daily_cost * duration_days
            },
            'confidence_range': confidence_range,
            'cost_factors': {
                'workload_multiplier': workload_multiplier,
                'intensity_multiplier': intensity_multiplier,
                'volume_multiplier': volume_multiplier,
                'total_multiplier': workload_multiplier * intensity_multiplier * volume_multiplier
            }
        }
    
    @staticmethod
    def _calculate_cost_confidence_range(
        base_projection: float,
        workload_characteristics: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate confidence range for cost projections"""
        
        # Base uncertainty factors
        uncertainty_factor = 0.2  # ±20% base uncertainty
        
        # Adjust uncertainty based on workload characteristics
        workload_type = workload_characteristics.get('workload_type', 'general')
        duration_days = workload_characteristics.get('duration_days', 30)
        
        # Higher uncertainty for complex workloads
        if workload_type in ['machine_learning', 'development']:
            uncertainty_factor += 0.1
        
        # Higher uncertainty for longer durations
        if duration_days > 60:
            uncertainty_factor += 0.1
        elif duration_days < 7:
            uncertainty_factor += 0.15  # Short bursts are harder to predict
        
        # Calculate range
        margin = base_projection * uncertainty_factor
        
        return {
            'low_estimate': max(0, base_projection - margin),
            'high_estimate': base_projection + margin,
            'confidence_level': max(0.6, 1.0 - uncertainty_factor),  # Higher uncertainty = lower confidence
            'margin_of_error': margin
        }
    
    @staticmethod
    def analyze_cost_optimization_opportunities(
        projected_costs: Dict[str, Any],
        baseline_efficiency: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify cost optimization opportunities"""
        opportunities = []
        
        total_cost = projected_costs.get('total_cost_projection', 0)
        current_efficiency = baseline_efficiency.get('tokens_per_dollar', 1000)
        
        # High-level cost concerns
        if total_cost > 500:  # $500+ workload
            opportunities.append({
                'type': 'budget_review',
                'priority': 'high',
                'description': 'High-cost workload requires budget review',
                'potential_impact': 'cost_management',
                'recommendations': ['Review budget allocation', 'Consider workload phasing']
            })
        
        # Efficiency opportunities
        if current_efficiency < 5000:  # Low tokens per dollar
            opportunities.append({
                'type': 'efficiency_improvement',
                'priority': 'medium',
                'description': 'Low token efficiency detected',
                'potential_impact': 'cost_reduction',
                'recommendations': ['Optimize prompt engineering', 'Consider batch processing']
            })
        
        # Volume-based opportunities
        cost_breakdown = projected_costs.get('cost_breakdown', {})
        volume_adjustment = cost_breakdown.get('volume_adjustment', 0)
        
        if volume_adjustment > total_cost * 0.3:  # Volume adds 30%+ to cost
            opportunities.append({
                'type': 'volume_optimization',
                'priority': 'medium',
                'description': 'Volume scaling significantly increases cost',
                'potential_impact': 'cost_reduction',
                'recommendations': ['Consider incremental scaling', 'Implement usage optimization']
            })
        
        return opportunities
    
    @staticmethod
    def calculate_roi_projections(
        projected_costs: Dict[str, Any],
        expected_benefits: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate ROI projections for the workload"""
        
        total_cost = projected_costs.get('total_cost_projection', 0)
        
        # Extract expected benefits
        productivity_gain = expected_benefits.get('productivity_multiplier', 1.0)
        time_saved_hours = expected_benefits.get('time_saved_hours', 0)
        quality_improvement = expected_benefits.get('quality_score_improvement', 0)
        
        # Calculate benefit values (simplified model)
        # Assuming $50/hour for time value
        time_value = time_saved_hours * 50
        
        # Productivity value (percentage of cost as benefit)
        productivity_value = total_cost * (productivity_gain - 1) * 2  # 2x multiplier for productivity
        
        # Quality value (subjective, percentage of cost)
        quality_value = total_cost * quality_improvement * 0.5
        
        total_benefits = time_value + productivity_value + quality_value
        
        # Calculate ROI
        if total_cost > 0:
            roi_ratio = total_benefits / total_cost
            roi_percentage = (roi_ratio - 1) * 100
        else:
            roi_ratio = 0
            roi_percentage = 0
        
        return {
            'total_investment': total_cost,
            'projected_benefits': {
                'time_savings_value': time_value,
                'productivity_value': productivity_value,
                'quality_value': quality_value,
                'total_value': total_benefits
            },
            'roi_metrics': {
                'roi_ratio': roi_ratio,
                'roi_percentage': roi_percentage,
                'payback_assessment': CostProjectionUtils._assess_payback(roi_ratio),
                'break_even_point': total_cost / (total_benefits / 365) if total_benefits > 0 else float('inf')  # Days to break even
            }
        }
    
    @staticmethod
    def _assess_payback(roi_ratio: float) -> str:
        """Assess payback quality based on ROI ratio"""
        if roi_ratio >= 3.0:
            return "excellent"
        elif roi_ratio >= 2.0:
            return "very_good"
        elif roi_ratio >= 1.5:
            return "good"
        elif roi_ratio >= 1.1:
            return "acceptable"
        elif roi_ratio >= 1.0:
            return "marginal"
        else:
            return "poor"
    
    @staticmethod
    def create_budget_recommendations(
        cost_projections: Dict[str, Any],
        current_budget_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create budget recommendations based on cost projections"""
        
        total_projected_cost = cost_projections.get('total_cost_projection', 0)
        confidence_range = cost_projections.get('confidence_range', {})
        
        high_estimate = confidence_range.get('high_estimate', total_projected_cost * 1.2)
        low_estimate = confidence_range.get('low_estimate', total_projected_cost * 0.8)
        
        # Recommended budget with buffer
        recommended_budget = high_estimate * 1.15  # 15% buffer on high estimate
        
        recommendations = {
            'recommended_budget': recommended_budget,
            'minimum_budget': total_projected_cost,
            'conservative_budget': high_estimate,
            'budget_buffer': recommended_budget - total_projected_cost,
            'budget_breakdown': {
                'expected_cost': total_projected_cost,
                'uncertainty_buffer': high_estimate - total_projected_cost,
                'contingency_buffer': recommended_budget - high_estimate
            }
        }
        
        # Budget guidance
        if current_budget_info:
            current_budget = current_budget_info.get('available_budget', 0)
            
            if recommended_budget > current_budget:
                recommendations['budget_status'] = 'insufficient'
                recommendations['budget_gap'] = recommended_budget - current_budget
                recommendations['guidance'] = [
                    'Current budget insufficient for projected workload',
                    f'Additional ${recommendations["budget_gap"]:.2f} needed',
                    'Consider reducing scope or increasing budget'
                ]
            elif total_projected_cost > current_budget:
                recommendations['budget_status'] = 'tight'
                recommendations['guidance'] = [
                    'Budget covers expected costs but with no buffer',
                    'Monitor costs closely during execution',
                    'Have contingency plan for overruns'
                ]
            else:
                recommendations['budget_status'] = 'adequate'
                recommendations['guidance'] = [
                    'Current budget adequate for projected workload',
                    'Good buffer for unexpected costs'
                ]
        
        return recommendations