"""
Risk Management Service

Main orchestrator for Suite 4: Risk Management
Coordinates compliance risk prediction and security analysis
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from ..prediction_models import (
    ComplianceRiskPrediction,
    PredictionConfidenceLevel,
    PredictionType
)
from .sub_services.compliance_risk_predictor import ComplianceRiskPredictor

logger = logging.getLogger(__name__)


class RiskManagementService:
    """
    Main service orchestrator for risk management
    Coordinates compliance risk analysis and security predictions
    """
    
    def __init__(self):
        """Initialize sub-services"""
        self.compliance_predictor = ComplianceRiskPredictor()
        
        logger.info("Risk Management Service initialized")
    
    async def predict_compliance_risks(
        self, 
        user_id: str, 
        compliance_context: Dict[str, Any],
        timeframe: str = "30d"
    ) -> ComplianceRiskPrediction:
        """
        Predict compliance risks based on user behavior and context
        
        Args:
            user_id: User identifier
            compliance_context: Compliance and security context
            timeframe: Analysis timeframe (default: 30d)
            
        Returns:
            ComplianceRiskPrediction: Risk assessment and recommendations
        """
        try:
            logger.info(f"Predicting compliance risks for user {user_id}")
            
            # Delegate to compliance predictor
            prediction = await self.compliance_predictor.predict_risks(
                user_id, compliance_context, timeframe
            )
            
            logger.info(f"Compliance risk prediction completed for user {user_id}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting compliance risks for user {user_id}: {e}")
            # Return safe default with low confidence
            return ComplianceRiskPrediction(
                user_id=user_id,
                confidence=0.1,
                confidence_level=PredictionConfidenceLevel.LOW,
                risk_level="low",
                policy_conflicts=[],
                access_violations=[],
                mitigation_strategies=["Review user permissions", "Conduct security audit"],
                compliance_score=0.8,
                security_score=0.7,
                data_governance_score=0.75,
                metadata={"error": str(e)}
            )
    
    async def get_comprehensive_risk_analysis(
        self, 
        user_id: str, 
        compliance_context: Optional[Dict[str, Any]] = None,
        timeframe: str = "30d"
    ) -> Dict[str, Any]:
        """
        Get comprehensive risk management analysis
        
        Args:
            user_id: User identifier
            compliance_context: Compliance context information
            timeframe: Analysis timeframe
            
        Returns:
            Dict containing all risk management results
        """
        try:
            logger.info(f"Getting comprehensive risk analysis for user {user_id}")
            
            # Run compliance risk analysis
            compliance_prediction = await self.predict_compliance_risks(
                user_id, compliance_context or {}, timeframe
            )
            
            # Generate insights and recommendations
            insights = self._generate_risk_insights(compliance_prediction)
            recommendations = self._generate_risk_recommendations(compliance_prediction)
            
            result = {
                "user_id": user_id,
                "compliance_risks": compliance_prediction,
                "overall_confidence": compliance_prediction.confidence,
                "analysis_timestamp": datetime.utcnow(),
                "timeframe": timeframe,
                "insights": insights,
                "recommendations": recommendations,
                "risk_summary": {
                    "overall_risk_level": compliance_prediction.risk_level,
                    "compliance_score": compliance_prediction.compliance_score,
                    "security_score": compliance_prediction.security_score,
                    "data_governance_score": compliance_prediction.data_governance_score
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in comprehensive risk analysis for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "overall_confidence": 0.0,
                "analysis_timestamp": datetime.utcnow()
            }
    
    def _generate_risk_insights(
        self, 
        compliance_prediction: ComplianceRiskPrediction
    ) -> List[str]:
        """Generate actionable risk insights"""
        insights = []
        
        # Risk level insights
        risk_level = compliance_prediction.risk_level
        confidence = compliance_prediction.confidence
        
        if confidence > 0.7:
            if risk_level == "high":
                insights.append("High compliance risk detected - immediate attention required")
            elif risk_level == "medium":
                insights.append("Moderate compliance risk - monitoring recommended")
            elif risk_level == "low":
                insights.append("Low compliance risk - maintain current practices")
        
        # Score-based insights
        compliance_score = compliance_prediction.compliance_score
        security_score = compliance_prediction.security_score
        data_governance_score = compliance_prediction.data_governance_score
        
        if compliance_score < 0.6:
            insights.append("Compliance score below acceptable threshold")
        
        if security_score < 0.6:
            insights.append("Security posture needs improvement")
        
        if data_governance_score < 0.6:
            insights.append("Data governance practices require attention")
        
        # Risk factor insights
        risk_factors = compliance_prediction.metadata.get('risk_factors', [])
        if len(risk_factors) > 3:
            insights.append(f"Multiple risk factors identified: {len(risk_factors)} areas of concern")
        
        return insights
    
    def _generate_risk_recommendations(
        self, 
        compliance_prediction: ComplianceRiskPrediction
    ) -> List[str]:
        """Generate actionable risk management recommendations"""
        recommendations = []
        
        risk_level = compliance_prediction.risk_level
        compliance_score = compliance_prediction.compliance_score
        security_score = compliance_prediction.security_score
        data_governance_score = compliance_prediction.data_governance_score
        
        # Risk level based recommendations
        if risk_level == "high":
            recommendations.append("Implement immediate risk mitigation measures")
            recommendations.append("Schedule compliance audit within 30 days")
        elif risk_level == "medium":
            recommendations.append("Review and update compliance procedures")
            recommendations.append("Increase monitoring frequency")
        
        # Score-based recommendations
        if compliance_score < 0.6:
            recommendations.append("Enhance compliance training and procedures")
            recommendations.append("Implement automated compliance monitoring")
        
        if security_score < 0.6:
            recommendations.append("Strengthen security controls and access management")
            recommendations.append("Conduct security assessment")
        
        if data_governance_score < 0.6:
            recommendations.append("Improve data classification and handling procedures")
            recommendations.append("Implement data loss prevention measures")
        
        # General recommendations
        recommendations.append("Regular compliance monitoring and reporting")
        recommendations.append("Maintain incident response procedures")
        
        return recommendations[:6]  # Limit to top 6 recommendations
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of risk management service"""
        try:
            # Check sub-service health
            compliance_health = await self.compliance_predictor.health_check()
            
            all_healthy = compliance_health.get("status") == "healthy"
            
            return {
                "service": "risk_management",
                "status": "healthy" if all_healthy else "degraded",
                "sub_services": {
                    "compliance_predictor": compliance_health
                },
                "last_check": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "risk_management",
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow()
            }


# Import asyncio at module level to avoid issues
import asyncio