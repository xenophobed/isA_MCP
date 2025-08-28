"""
Risk Assessment Utilities

Utilities for assessing and analyzing various types of risks
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import math


class RiskAssessmentUtils:
    """Utilities for risk assessment and analysis"""
    
    @staticmethod
    def calculate_risk_score(
        risk_factors: Dict[str, List[str]], 
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate overall risk score based on identified risk factors
        
        Args:
            risk_factors: Dictionary of risk categories and their factors
            weights: Optional weights for each risk category
            
        Returns:
            Dictionary with risk scores and analysis
        """
        if not weights:
            weights = {
                "data_access_risks": 0.3,
                "security_risks": 0.25,
                "compliance_risks": 0.25,
                "behavioral_risks": 0.15,
                "temporal_risks": 0.05
            }
        
        category_scores = {}
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for category, factors in risk_factors.items():
            # Calculate category score based on number of factors
            factor_count = len(factors)
            
            if factor_count == 0:
                category_score = 0.0
            elif factor_count <= 2:
                category_score = 0.3  # Low risk
            elif factor_count <= 4:
                category_score = 0.6  # Medium risk
            else:
                category_score = 1.0  # High risk
            
            category_scores[category] = category_score
            
            # Apply weight if available
            weight = weights.get(category, 0.1)
            total_weighted_score += category_score * weight
            total_weight += weight
        
        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        
        return {
            "overall_risk_score": overall_score,
            "category_scores": category_scores,
            "risk_level": RiskAssessmentUtils._classify_risk_level(overall_score),
            "highest_risk_category": max(category_scores, key=category_scores.get) if category_scores else None,
            "factor_counts": {cat: len(factors) for cat, factors in risk_factors.items()}
        }
    
    @staticmethod
    def _classify_risk_level(score: float) -> str:
        """Classify numerical risk score into categorical level"""
        if score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    def analyze_risk_trends(
        historical_risk_data: List[Dict[str, Any]], 
        time_window_days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze trends in risk levels over time
        
        Args:
            historical_risk_data: List of historical risk assessments
            time_window_days: Window size for trend analysis
            
        Returns:
            Dictionary with trend analysis
        """
        if len(historical_risk_data) < 2:
            return {
                "trend_direction": "insufficient_data",
                "trend_strength": 0.0,
                "risk_volatility": 0.0
            }
        
        # Sort by timestamp
        sorted_data = sorted(
            historical_risk_data, 
            key=lambda x: x.get('timestamp', datetime.min)
        )
        
        # Extract risk scores over time
        risk_scores = [item.get('overall_risk_score', 0.0) for item in sorted_data]
        
        # Calculate trend
        trend_result = RiskAssessmentUtils._calculate_linear_trend(risk_scores)
        
        # Calculate volatility
        if len(risk_scores) > 1:
            volatility = statistics.stdev(risk_scores) / statistics.mean(risk_scores) if statistics.mean(risk_scores) > 0 else 0
        else:
            volatility = 0.0
        
        return {
            "trend_direction": trend_result["direction"],
            "trend_strength": trend_result["strength"],
            "trend_slope": trend_result["slope"],
            "risk_volatility": volatility,
            "volatility_level": RiskAssessmentUtils._classify_volatility(volatility)
        }
    
    @staticmethod
    def _calculate_linear_trend(values: List[float]) -> Dict[str, Any]:
        """Calculate linear trend from a series of values"""
        if len(values) < 2:
            return {"direction": "insufficient_data", "strength": 0.0, "slope": 0.0}
        
        n = len(values)
        x_values = list(range(n))
        
        # Calculate linear regression
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Determine trend direction and strength
        if abs(slope) < 0.05:
            direction = "stable"
            strength = 0.0
        elif slope > 0:
            direction = "increasing"
            strength = min(1.0, abs(slope) * 10)  # Scale for visibility
        else:
            direction = "decreasing"
            strength = min(1.0, abs(slope) * 10)
        
        return {
            "direction": direction,
            "strength": strength,
            "slope": slope
        }
    
    @staticmethod
    def _classify_volatility(volatility: float) -> str:
        """Classify volatility level"""
        if volatility < 0.1:
            return "low"
        elif volatility < 0.3:
            return "moderate"
        elif volatility < 0.5:
            return "high"
        else:
            return "very_high"
    
    @staticmethod
    def assess_risk_impact(
        risk_factors: Dict[str, List[str]], 
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess the potential impact of identified risks on business operations
        
        Args:
            risk_factors: Identified risk factors by category
            business_context: Business context information
            
        Returns:
            Impact assessment results
        """
        impact_assessment = {
            "financial_impact": "low",
            "operational_impact": "low", 
            "reputational_impact": "low",
            "regulatory_impact": "low",
            "overall_impact": "low"
        }
        
        # Assess impact based on risk categories and business context
        
        # Financial impact assessment
        data_risks = len(risk_factors.get("data_access_risks", []))
        security_risks = len(risk_factors.get("security_risks", []))
        
        if data_risks > 3 or security_risks > 3:
            impact_assessment["financial_impact"] = "high"
        elif data_risks > 1 or security_risks > 1:
            impact_assessment["financial_impact"] = "medium"
        
        # Operational impact assessment
        behavioral_risks = len(risk_factors.get("behavioral_risks", []))
        temporal_risks = len(risk_factors.get("temporal_risks", []))
        
        if behavioral_risks > 2 or temporal_risks > 2:
            impact_assessment["operational_impact"] = "medium"
        
        # Regulatory impact assessment
        compliance_risks = len(risk_factors.get("compliance_risks", []))
        
        if compliance_risks > 2:
            impact_assessment["regulatory_impact"] = "high"
        elif compliance_risks > 0:
            impact_assessment["regulatory_impact"] = "medium"
        
        # Reputational impact (tied to compliance and security)
        if compliance_risks > 1 or security_risks > 2:
            impact_assessment["reputational_impact"] = "medium"
        if compliance_risks > 3 or security_risks > 4:
            impact_assessment["reputational_impact"] = "high"
        
        # Overall impact (highest of individual impacts)
        impact_levels = {"low": 1, "medium": 2, "high": 3}
        max_impact_level = max(
            impact_levels[impact] for impact in [
                impact_assessment["financial_impact"],
                impact_assessment["operational_impact"],
                impact_assessment["reputational_impact"],
                impact_assessment["regulatory_impact"]
            ]
        )
        
        impact_assessment["overall_impact"] = {v: k for k, v in impact_levels.items()}[max_impact_level]
        
        # Business context adjustments
        industry = business_context.get("industry", "general")
        if industry in ["healthcare", "finance", "government"]:
            # High-regulation industries have amplified regulatory impact
            if impact_assessment["regulatory_impact"] == "medium":
                impact_assessment["regulatory_impact"] = "high"
                impact_assessment["overall_impact"] = "high"
        
        return impact_assessment
    
    @staticmethod
    def generate_risk_mitigation_priorities(
        risk_factors: Dict[str, List[str]], 
        impact_assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate prioritized risk mitigation recommendations
        
        Args:
            risk_factors: Identified risk factors
            impact_assessment: Impact assessment results
            
        Returns:
            List of prioritized mitigation actions
        """
        priorities = []
        
        # Priority scoring based on risk count and impact
        impact_weights = {"high": 3, "medium": 2, "low": 1}
        
        for category, factors in risk_factors.items():
            if not factors:
                continue
            
            # Determine category priority
            category_impact_map = {
                "compliance_risks": impact_assessment.get("regulatory_impact", "low"),
                "security_risks": impact_assessment.get("financial_impact", "low"),
                "data_access_risks": impact_assessment.get("reputational_impact", "low"),
                "behavioral_risks": impact_assessment.get("operational_impact", "low"),
                "temporal_risks": impact_assessment.get("operational_impact", "low")
            }
            
            category_impact = category_impact_map.get(category, "low")
            risk_count = len(factors)
            
            # Calculate priority score
            priority_score = risk_count * impact_weights[category_impact]
            
            priorities.append({
                "category": category,
                "risk_count": risk_count,
                "impact_level": category_impact,
                "priority_score": priority_score,
                "factors": factors,
                "urgency": RiskAssessmentUtils._determine_urgency(priority_score),
                "recommended_actions": RiskAssessmentUtils._get_category_actions(category)
            })
        
        # Sort by priority score (highest first)
        priorities.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return priorities
    
    @staticmethod
    def _determine_urgency(priority_score: int) -> str:
        """Determine urgency level based on priority score"""
        if priority_score >= 9:
            return "critical"
        elif priority_score >= 6:
            return "high"
        elif priority_score >= 3:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    def _get_category_actions(category: str) -> List[str]:
        """Get recommended actions for specific risk categories"""
        action_map = {
            "compliance_risks": [
                "Review compliance policies and procedures",
                "Conduct compliance training",
                "Implement automated compliance monitoring",
                "Schedule regulatory audit"
            ],
            "security_risks": [
                "Strengthen access controls",
                "Update security policies",
                "Implement additional authentication",
                "Conduct security assessment"
            ],
            "data_access_risks": [
                "Review data access permissions",
                "Implement data loss prevention",
                "Enhance data classification",
                "Monitor data export activities"
            ],
            "behavioral_risks": [
                "Implement user behavior monitoring",
                "Provide security awareness training",
                "Review user access patterns",
                "Establish usage baselines"
            ],
            "temporal_risks": [
                "Implement time-based access controls",
                "Monitor after-hours activities", 
                "Set up usage alerts",
                "Review scheduling policies"
            ]
        }
        
        return action_map.get(category, ["Review and assess category-specific risks"])
    
    @staticmethod
    def calculate_residual_risk(
        initial_risk_score: float, 
        mitigation_effectiveness: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate residual risk after applying mitigation measures
        
        Args:
            initial_risk_score: Initial risk score (0-1)
            mitigation_effectiveness: Effectiveness of each mitigation (0-1)
            
        Returns:
            Residual risk analysis
        """
        if not mitigation_effectiveness:
            return {
                "residual_risk_score": initial_risk_score,
                "risk_reduction": 0.0,
                "mitigation_impact": "none"
            }
        
        # Calculate combined mitigation effectiveness
        # Use geometric mean to avoid over-optimistic combinations
        effectiveness_values = list(mitigation_effectiveness.values())
        if effectiveness_values:
            combined_effectiveness = math.prod(effectiveness_values) ** (1.0 / len(effectiveness_values))
        else:
            combined_effectiveness = 0.0
        
        # Calculate residual risk
        residual_risk_score = initial_risk_score * (1.0 - combined_effectiveness)
        risk_reduction = initial_risk_score - residual_risk_score
        
        # Classify mitigation impact
        if risk_reduction >= initial_risk_score * 0.7:
            impact = "significant"
        elif risk_reduction >= initial_risk_score * 0.4:
            impact = "moderate"
        elif risk_reduction >= initial_risk_score * 0.1:
            impact = "minimal"
        else:
            impact = "negligible"
        
        return {
            "residual_risk_score": residual_risk_score,
            "risk_reduction": risk_reduction,
            "risk_reduction_percentage": (risk_reduction / initial_risk_score * 100) if initial_risk_score > 0 else 0,
            "mitigation_impact": impact,
            "combined_effectiveness": combined_effectiveness
        }
    
    @staticmethod
    def benchmark_risk_levels(
        user_risk_score: float, 
        industry_benchmarks: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Benchmark user risk levels against industry standards
        
        Args:
            user_risk_score: User's risk score
            industry_benchmarks: Optional industry benchmark data
            
        Returns:
            Benchmarking analysis
        """
        # Default industry benchmarks if not provided
        if not industry_benchmarks:
            industry_benchmarks = {
                "technology": 0.3,
                "finance": 0.2,
                "healthcare": 0.25,
                "retail": 0.35,
                "manufacturing": 0.4,
                "general": 0.3
            }
        
        benchmark_results = {}
        
        for industry, benchmark_score in industry_benchmarks.items():
            difference = user_risk_score - benchmark_score
            
            if difference <= -0.1:
                performance = "significantly_better"
            elif difference <= 0:
                performance = "better"
            elif difference <= 0.1:
                performance = "comparable"
            elif difference <= 0.2:
                performance = "worse"
            else:
                performance = "significantly_worse"
            
            benchmark_results[industry] = {
                "benchmark_score": benchmark_score,
                "difference": difference,
                "performance": performance
            }
        
        # Find best matching industry
        closest_industry = min(
            industry_benchmarks.items(), 
            key=lambda x: abs(x[1] - user_risk_score)
        )
        
        return {
            "user_risk_score": user_risk_score,
            "industry_comparisons": benchmark_results,
            "closest_industry": closest_industry[0],
            "closest_benchmark": closest_industry[1],
            "overall_position": benchmark_results.get("general", {}).get("performance", "unknown")
        }