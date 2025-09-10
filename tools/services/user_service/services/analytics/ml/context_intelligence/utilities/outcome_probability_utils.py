"""
Outcome Probability Utilities

Utilities for calculating probabilities and confidence scores for task outcomes
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import math
from dataclasses import dataclass
from enum import Enum


class TaskDifficulty(Enum):
    TRIVIAL = "trivial"
    EASY = "easy" 
    MODERATE = "moderate"
    HARD = "hard"
    EXPERT = "expert"


class RiskLevel(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProbabilityFactors:
    """Factors that influence task outcome probability"""
    user_skill_match: float  # How well user skills match task requirements
    historical_success: float  # Historical success rate for similar tasks
    task_complexity: float  # Relative complexity of the task
    context_favorability: float  # How favorable the current context is
    resource_availability: float  # Availability of required resources
    time_pressure: float  # Time constraints (0 = no pressure, 1 = high pressure)
    collaboration_factor: float  # Impact of team collaboration
    risk_factors: float  # Identified risk factors


class OutcomeProbabilityUtils:
    """Utilities for calculating task outcome probabilities and confidence scores"""
    
    @staticmethod
    def calculate_success_probability(
        user_capability: Dict[str, float],
        task_requirements: Dict[str, float],
        historical_data: List[Dict[str, Any]],
        context_factors: Dict[str, Any]
    ) -> Tuple[float, ProbabilityFactors]:
        """
        Calculate the probability of task success
        
        Args:
            user_capability: Dictionary of user capabilities and skill levels
            task_requirements: Dictionary of task requirements and difficulty levels
            historical_data: Historical performance data for similar tasks
            context_factors: Current contextual factors
            
        Returns:
            Tuple of (success_probability, contributing_factors)
        """
        # Calculate individual probability factors
        skill_match = OutcomeProbabilityUtils._calculate_skill_match(
            user_capability, task_requirements
        )
        
        historical_success = OutcomeProbabilityUtils._calculate_historical_success(
            historical_data, task_requirements
        )
        
        task_complexity = OutcomeProbabilityUtils._assess_task_complexity(
            task_requirements
        )
        
        context_favorability = OutcomeProbabilityUtils._assess_context_favorability(
            context_factors
        )
        
        resource_availability = OutcomeProbabilityUtils._assess_resource_availability(
            context_factors
        )
        
        time_pressure = OutcomeProbabilityUtils._assess_time_pressure(
            context_factors
        )
        
        collaboration_factor = OutcomeProbabilityUtils._assess_collaboration_factor(
            context_factors, historical_data
        )
        
        risk_factors = OutcomeProbabilityUtils._calculate_risk_impact(
            context_factors, task_requirements
        )
        
        # Create probability factors object
        factors = ProbabilityFactors(
            user_skill_match=skill_match,
            historical_success=historical_success,
            task_complexity=task_complexity,
            context_favorability=context_favorability,
            resource_availability=resource_availability,
            time_pressure=time_pressure,
            collaboration_factor=collaboration_factor,
            risk_factors=risk_factors
        )
        
        # Calculate weighted probability
        base_probability = OutcomeProbabilityUtils._calculate_base_probability(factors)
        
        # Apply contextual modifiers
        adjusted_probability = OutcomeProbabilityUtils._apply_contextual_modifiers(
            base_probability, factors, context_factors
        )
        
        # Ensure probability is within valid range
        final_probability = max(0.0, min(1.0, adjusted_probability))
        
        return final_probability, factors
    
    @staticmethod
    def _calculate_skill_match(
        user_capability: Dict[str, float], 
        task_requirements: Dict[str, float]
    ) -> float:
        """Calculate how well user skills match task requirements"""
        if not task_requirements:
            return 1.0
        
        if not user_capability:
            return 0.3  # Default low capability
        
        matches = []
        for skill, required_level in task_requirements.items():
            user_level = user_capability.get(skill, 0.0)
            
            if required_level == 0:
                matches.append(1.0)  # No requirement
            else:
                # Calculate match ratio with diminishing returns for overqualification
                ratio = user_level / required_level
                if ratio >= 1.0:
                    # Overqualified (good but with diminishing returns)
                    match_score = 1.0 - (1.0 / (1.0 + ratio - 1.0))
                else:
                    # Underqualified (linear penalty)
                    match_score = ratio
                matches.append(match_score)
        
        # Return average match score
        return sum(matches) / len(matches)
    
    @staticmethod
    def _calculate_historical_success(
        historical_data: List[Dict[str, Any]], 
        task_requirements: Dict[str, float]
    ) -> float:
        """Calculate historical success rate for similar tasks"""
        if not historical_data:
            return 0.5  # Default neutral probability
        
        # Find similar tasks based on requirements
        similar_tasks = []
        for record in historical_data:
            similarity = OutcomeProbabilityUtils._calculate_task_similarity(
                record, task_requirements
            )
            if similarity > 0.3:  # Minimum similarity threshold
                similar_tasks.append((record, similarity))
        
        if not similar_tasks:
            # No similar tasks, use overall success rate
            successful = sum(
                1 for record in historical_data
                if record.get('success', False)
            )
            return successful / len(historical_data)
        
        # Weight by similarity and recency
        weighted_success = 0.0
        total_weight = 0.0
        
        for record, similarity in similar_tasks:
            success = 1.0 if record.get('success', False) else 0.0
            recency_weight = OutcomeProbabilityUtils._calculate_recency_weight(record)
            
            weight = similarity * recency_weight
            weighted_success += success * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_success / total_weight
        else:
            return 0.5
    
    @staticmethod
    def _calculate_task_similarity(
        historical_record: Dict[str, Any], 
        task_requirements: Dict[str, float]
    ) -> float:
        """Calculate similarity between historical task and current requirements"""
        historical_reqs = historical_record.get('requirements', {})
        
        if not historical_reqs or not task_requirements:
            return 0.0
        
        # Calculate similarity based on overlapping requirements
        common_skills = set(historical_reqs.keys()) & set(task_requirements.keys())
        
        if not common_skills:
            return 0.0
        
        similarity_scores = []
        for skill in common_skills:
            hist_level = historical_reqs[skill]
            curr_level = task_requirements[skill]
            
            # Calculate level similarity (1.0 = identical, 0.0 = completely different)
            if hist_level == 0 and curr_level == 0:
                similarity_scores.append(1.0)
            elif hist_level == 0 or curr_level == 0:
                similarity_scores.append(0.0)
            else:
                ratio = min(hist_level, curr_level) / max(hist_level, curr_level)
                similarity_scores.append(ratio)
        
        # Weight by coverage (how many requirements are covered)
        coverage = len(common_skills) / max(len(historical_reqs), len(task_requirements))
        avg_similarity = sum(similarity_scores) / len(similarity_scores)
        
        return avg_similarity * coverage
    
    @staticmethod
    def _calculate_recency_weight(record: Dict[str, Any]) -> float:
        """Calculate recency weight for historical records"""
        created_at = record.get('created_at')
        if not created_at:
            return 0.5  # Default weight
        
        try:
            if isinstance(created_at, str):
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                dt = created_at
            
            days_ago = (datetime.utcnow() - dt).days
            
            # Exponential decay: recent records have higher weight
            # Half-life of 30 days
            weight = math.exp(-days_ago / 43.3)  # ln(2)/0.016 ≈ 43.3
            return max(0.1, weight)  # Minimum weight of 0.1
            
        except:
            return 0.5
    
    @staticmethod
    def _assess_task_complexity(task_requirements: Dict[str, float]) -> float:
        """Assess the overall complexity of the task"""
        if not task_requirements:
            return 0.1  # Minimal complexity
        
        # Calculate complexity based on requirements
        requirement_levels = list(task_requirements.values())
        avg_requirement = sum(requirement_levels) / len(requirement_levels)
        max_requirement = max(requirement_levels)
        num_requirements = len(requirement_levels)
        
        # Complexity increases with:
        # 1. Higher average requirement levels
        # 2. Higher maximum requirement
        # 3. More requirements (more complex coordination)
        
        base_complexity = avg_requirement
        peak_complexity = max_requirement * 0.3
        breadth_complexity = min(1.0, num_requirements / 10.0) * 0.2
        
        total_complexity = base_complexity + peak_complexity + breadth_complexity
        return min(1.0, total_complexity)
    
    @staticmethod
    def _assess_context_favorability(context_factors: Dict[str, Any]) -> float:
        """Assess how favorable the current context is for task success"""
        favorability_score = 0.5  # Neutral baseline
        
        # Working hours favorability
        working_hours = context_factors.get('working_hours', (9, 17))
        current_hour = datetime.utcnow().hour
        
        if working_hours[0] <= current_hour <= working_hours[1]:
            favorability_score += 0.2
        else:
            favorability_score -= 0.1
        
        # Context purity (how focused the current context is)
        context_purity = context_factors.get('context_purity', 0.5)
        favorability_score += (context_purity - 0.5) * 0.3
        
        # Temporal consistency (predictable work patterns)
        temporal_consistency = context_factors.get('temporal_consistency', 0.5)
        favorability_score += (temporal_consistency - 0.5) * 0.2
        
        # Multitasking load (lower is better for complex tasks)
        multitasking_tendency = context_factors.get('multitasking_tendency', 0.5)
        task_complexity = context_factors.get('task_complexity', 0.5)
        
        if task_complexity > 0.7 and multitasking_tendency > 0.7:
            favorability_score -= 0.2  # High complexity + high multitasking = bad
        
        return max(0.0, min(1.0, favorability_score))
    
    @staticmethod
    def _assess_resource_availability(context_factors: Dict[str, Any]) -> float:
        """Assess availability of required resources"""
        # This is a simplified assessment - in practice, you'd check actual resource availability
        base_availability = 0.7  # Assume good resource availability
        
        # Factor in collaboration level (more collaboration = more resources)
        collaboration_level = context_factors.get('collaboration_level', 0.5)
        collaboration_boost = collaboration_level * 0.2
        
        # Factor in technical proficiency (higher proficiency = better resource utilization)
        tech_proficiency = context_factors.get('technical_proficiency', 0.5)
        proficiency_boost = (tech_proficiency - 0.5) * 0.2
        
        # Factor in past resource usage patterns
        historical_resource_success = context_factors.get('historical_resource_success', 0.7)
        
        total_availability = base_availability + collaboration_boost + proficiency_boost
        # Weight with historical success
        weighted_availability = (total_availability * 0.7 + historical_resource_success * 0.3)
        
        return max(0.1, min(1.0, weighted_availability))
    
    @staticmethod
    def _assess_time_pressure(context_factors: Dict[str, Any]) -> float:
        """Assess time pressure (0 = no pressure, 1 = extreme pressure)"""
        # Check for explicit deadline information
        deadline = context_factors.get('deadline')
        estimated_duration = context_factors.get('estimated_duration_minutes', 60)
        
        if deadline:
            try:
                if isinstance(deadline, str):
                    deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                else:
                    deadline_dt = deadline
                
                time_until_deadline = (deadline_dt - datetime.utcnow()).total_seconds() / 60
                
                if time_until_deadline <= 0:
                    return 1.0  # Past deadline
                
                pressure_ratio = estimated_duration / time_until_deadline
                return min(1.0, max(0.0, pressure_ratio))
            except:
                pass
        
        # Infer time pressure from context
        session_intensity = context_factors.get('session_intensity', 0.5)
        recent_activity_spike = context_factors.get('recent_activity_spike', False)
        
        base_pressure = session_intensity * 0.3
        if recent_activity_spike:
            base_pressure += 0.2
        
        return min(1.0, base_pressure)
    
    @staticmethod
    def _assess_collaboration_factor(
        context_factors: Dict[str, Any], 
        historical_data: List[Dict[str, Any]]
    ) -> float:
        """Assess the impact of collaboration on task success"""
        collaboration_level = context_factors.get('collaboration_level', 0.5)
        
        # Check historical performance with/without collaboration
        solo_success_rate = 0.5
        collab_success_rate = 0.5
        
        solo_tasks = [r for r in historical_data if not r.get('collaborative', False)]
        collab_tasks = [r for r in historical_data if r.get('collaborative', False)]
        
        if solo_tasks:
            solo_successes = sum(1 for r in solo_tasks if r.get('success', False))
            solo_success_rate = solo_successes / len(solo_tasks)
        
        if collab_tasks:
            collab_successes = sum(1 for r in collab_tasks if r.get('success', False))
            collab_success_rate = collab_successes / len(collab_tasks)
        
        # Weight collaboration impact based on current collaboration level
        collaboration_impact = (
            collaboration_level * collab_success_rate + 
            (1 - collaboration_level) * solo_success_rate
        )
        
        return collaboration_impact
    
    @staticmethod
    def _calculate_risk_impact(
        context_factors: Dict[str, Any], 
        task_requirements: Dict[str, float]
    ) -> float:
        """Calculate the impact of risk factors on success probability"""
        risk_impact = 0.0  # Start with no risk
        
        # Technical risk factors
        tech_proficiency = context_factors.get('technical_proficiency', 0.5)
        max_requirement = max(task_requirements.values()) if task_requirements else 0.5
        
        if max_requirement > tech_proficiency + 0.3:
            risk_impact += 0.3  # Significant skill gap
        
        # Context switching risk
        context_switch_tolerance = context_factors.get('context_switch_tolerance', 0.5)
        multitasking_tendency = context_factors.get('multitasking_tendency', 0.5)
        
        if multitasking_tendency > 0.7 and context_switch_tolerance < 0.4:
            risk_impact += 0.2  # High multitasking with low tolerance
        
        # Time pressure risk
        time_pressure = OutcomeProbabilityUtils._assess_time_pressure(context_factors)
        if time_pressure > 0.7:
            risk_impact += 0.2  # High time pressure
        
        # Resource availability risk
        resource_availability = OutcomeProbabilityUtils._assess_resource_availability(context_factors)
        if resource_availability < 0.4:
            risk_impact += 0.25  # Low resource availability
        
        # Historical failure pattern risk
        recent_failures = context_factors.get('recent_failure_rate', 0.0)
        if recent_failures > 0.3:
            risk_impact += recent_failures * 0.3
        
        return min(1.0, risk_impact)
    
    @staticmethod
    def _calculate_base_probability(factors: ProbabilityFactors) -> float:
        """Calculate base success probability from all factors"""
        # Positive factors (higher = better)
        positive_factors = [
            factors.user_skill_match * 0.25,
            factors.historical_success * 0.2,
            factors.context_favorability * 0.15,
            factors.resource_availability * 0.15,
            factors.collaboration_factor * 0.1
        ]
        
        # Negative factors (higher = worse)
        negative_factors = [
            factors.task_complexity * 0.1,
            factors.time_pressure * 0.05,
            factors.risk_factors * 0.2
        ]
        
        positive_contribution = sum(positive_factors)
        negative_contribution = sum(negative_factors)
        
        # Base probability is positive contribution minus negative impact
        base_prob = positive_contribution - (negative_contribution * 0.5)
        
        return max(0.1, min(0.9, base_prob))
    
    @staticmethod
    def _apply_contextual_modifiers(
        base_probability: float, 
        factors: ProbabilityFactors, 
        context_factors: Dict[str, Any]
    ) -> float:
        """Apply contextual modifiers to base probability"""
        modified_prob = base_probability
        
        # Skill-task alignment modifier
        if factors.user_skill_match > 0.8 and factors.task_complexity < 0.6:
            modified_prob *= 1.1  # Easy task for skilled user
        elif factors.user_skill_match < 0.4 and factors.task_complexity > 0.7:
            modified_prob *= 0.8  # Hard task for unskilled user
        
        # Historical performance trend modifier
        performance_trend = context_factors.get('performance_trend', 'stable')
        if performance_trend == 'improving':
            modified_prob *= 1.05
        elif performance_trend == 'declining':
            modified_prob *= 0.95
        
        # Environmental stability modifier
        env_stability = context_factors.get('environment_stability', 0.5)
        if env_stability > 0.8:
            modified_prob *= 1.03
        elif env_stability < 0.3:
            modified_prob *= 0.97
        
        return modified_prob
    
    @staticmethod
    def calculate_confidence_intervals(
        probability: float, 
        factors: ProbabilityFactors,
        sample_size: int = 100
    ) -> Dict[str, float]:
        """
        Calculate confidence intervals for the probability estimate
        
        Args:
            probability: Base probability estimate
            factors: Probability factors used in calculation
            sample_size: Effective sample size for confidence calculation
            
        Returns:
            Dictionary with confidence interval bounds
        """
        # Calculate uncertainty based on factor reliability
        uncertainty = OutcomeProbabilityUtils._calculate_uncertainty(factors, sample_size)
        
        # Calculate confidence intervals (95% confidence)
        margin_of_error = 1.96 * uncertainty
        
        lower_bound = max(0.0, probability - margin_of_error)
        upper_bound = min(1.0, probability + margin_of_error)
        
        return {
            "lower_95": lower_bound,
            "upper_95": upper_bound,
            "margin_of_error": margin_of_error,
            "uncertainty": uncertainty
        }
    
    @staticmethod
    def _calculate_uncertainty(factors: ProbabilityFactors, sample_size: int) -> float:
        """Calculate uncertainty in probability estimate"""
        # Base uncertainty from sample size (binomial proportion)
        base_uncertainty = math.sqrt(0.25 / sample_size)  # Maximum variance case
        
        # Adjust uncertainty based on factor reliability
        factor_uncertainty = 0.0
        
        # Historical data reliability
        if factors.historical_success == 0.5:  # No historical data
            factor_uncertainty += 0.1
        
        # Skill match uncertainty
        skill_confidence = abs(factors.user_skill_match - 0.5) * 2  # 0.5 = maximum uncertainty
        factor_uncertainty += (1 - skill_confidence) * 0.05
        
        # Context uncertainty
        if factors.context_favorability == 0.5:  # Neutral context
            factor_uncertainty += 0.03
        
        # Risk assessment uncertainty
        factor_uncertainty += factors.risk_factors * 0.02
        
        total_uncertainty = base_uncertainty + factor_uncertainty
        return min(0.5, total_uncertainty)
    
    @staticmethod
    def get_probability_explanation(
        probability: float, 
        factors: ProbabilityFactors
    ) -> Dict[str, Any]:
        """
        Generate human-readable explanation of probability calculation
        
        Args:
            probability: Calculated success probability
            factors: Factors that contributed to the calculation
            
        Returns:
            Dictionary with explanation components
        """
        explanation = {
            "overall_assessment": OutcomeProbabilityUtils._get_probability_category(probability),
            "key_strengths": [],
            "key_concerns": [],
            "primary_factors": {},
            "recommendations": []
        }
        
        # Identify key strengths
        if factors.user_skill_match > 0.7:
            explanation["key_strengths"].append("Strong skill alignment with task requirements")
        if factors.historical_success > 0.7:
            explanation["key_strengths"].append("Strong historical performance on similar tasks")
        if factors.context_favorability > 0.7:
            explanation["key_strengths"].append("Favorable working context")
        if factors.resource_availability > 0.8:
            explanation["key_strengths"].append("Good resource availability")
        
        # Identify key concerns
        if factors.user_skill_match < 0.4:
            explanation["key_concerns"].append("Skill gap for task requirements")
        if factors.task_complexity > 0.7:
            explanation["key_concerns"].append("High task complexity")
        if factors.time_pressure > 0.7:
            explanation["key_concerns"].append("High time pressure")
        if factors.risk_factors > 0.5:
            explanation["key_concerns"].append("Multiple risk factors identified")
        
        # Primary contributing factors
        explanation["primary_factors"] = {
            "skill_match": round(factors.user_skill_match, 2),
            "historical_performance": round(factors.historical_success, 2),
            "task_complexity": round(factors.task_complexity, 2),
            "context_quality": round(factors.context_favorability, 2),
            "risk_level": round(factors.risk_factors, 2)
        }
        
        # Generate recommendations
        explanation["recommendations"] = OutcomeProbabilityUtils._generate_recommendations(factors)
        
        return explanation
    
    @staticmethod
    def _get_probability_category(probability: float) -> str:
        """Convert probability to categorical assessment"""
        if probability >= 0.8:
            return "Very likely to succeed"
        elif probability >= 0.6:
            return "Likely to succeed"
        elif probability >= 0.4:
            return "Uncertain outcome"
        elif probability >= 0.2:
            return "Likely to face challenges"
        else:
            return "High risk of failure"
    
    @staticmethod
    def _generate_recommendations(factors: ProbabilityFactors) -> List[str]:
        """Generate recommendations based on factor analysis"""
        recommendations = []
        
        if factors.user_skill_match < 0.5:
            recommendations.append("Consider additional training or assistance")
        
        if factors.task_complexity > 0.7:
            recommendations.append("Break down task into smaller components")
        
        if factors.time_pressure > 0.6:
            recommendations.append("Negotiate deadline or reduce scope")
        
        if factors.context_favorability < 0.4:
            recommendations.append("Wait for more favorable conditions")
        
        if factors.resource_availability < 0.5:
            recommendations.append("Secure additional resources before proceeding")
        
        if factors.risk_factors > 0.5:
            recommendations.append("Implement risk mitigation strategies")
        
        if factors.collaboration_factor > 0.7:
            recommendations.append("Leverage team collaboration for success")
        
        return recommendations