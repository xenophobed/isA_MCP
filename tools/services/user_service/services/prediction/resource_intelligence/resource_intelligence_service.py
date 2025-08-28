"""
Resource Intelligence Service

Main orchestrator for Suite 3: Resource Intelligence
Coordinates system resource analysis and resource need prediction
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from ..prediction_models import (
    SystemPattern,
    ResourceNeedsPrediction, 
    PredictionConfidenceLevel,
    PredictionType
)
from .sub_services.system_pattern_analyzer import SystemPatternAnalyzer
from .sub_services.resource_needs_predictor import ResourceNeedsPredictor

logger = logging.getLogger(__name__)


class ResourceIntelligenceService:
    """
    Main service orchestrator for resource intelligence
    Coordinates system pattern analysis and resource needs prediction
    """
    
    def __init__(self):
        """Initialize sub-services"""
        self.system_analyzer = SystemPatternAnalyzer()
        self.resource_predictor = ResourceNeedsPredictor()
        
        logger.info("Resource Intelligence Service initialized")
    
    async def analyze_system_patterns(
        self, 
        user_id: str, 
        system_context: Optional[Dict[str, Any]] = None,
        timeframe: str = "30d"
    ) -> SystemPattern:
        """
        Analyze system resource usage patterns
        
        Args:
            user_id: User identifier
            system_context: Current system context information
            timeframe: Analysis timeframe (default: 30d)
            
        Returns:
            SystemPattern: System resource usage insights
        """
        try:
            logger.info(f"Analyzing system patterns for user {user_id}, timeframe: {timeframe}")
            
            # Delegate to system analyzer
            pattern = await self.system_analyzer.analyze_patterns(
                user_id, system_context or {}, timeframe
            )
            
            logger.info(f"System pattern analysis completed for user {user_id}")
            return pattern
            
        except Exception as e:
            logger.error(f"Error analyzing system patterns for user {user_id}: {e}")
            # Return empty pattern with low confidence
            return SystemPattern(
                user_id=user_id,
                confidence=0.1,
                confidence_level=PredictionConfidenceLevel.LOW,
                prediction_type=PredictionType.SYSTEM_PATTERNS,
                resource_utilization={},
                bottlenecks=[],
                optimization_opportunities=[],
                cost_analysis={},
                metadata={"error": str(e)}
            )
    
    async def predict_resource_needs(
        self, 
        user_id: str, 
        upcoming_workload: Dict[str, Any]
    ) -> ResourceNeedsPrediction:
        """
        Predict future resource requirements based on workload
        
        Args:
            user_id: User identifier
            upcoming_workload: Planned workload information
            
        Returns:
            ResourcePrediction: Resource requirements and recommendations
        """
        try:
            logger.info(f"Predicting resource needs for user {user_id}")
            
            # Delegate to resource predictor
            prediction = await self.resource_predictor.predict_needs(
                user_id, upcoming_workload
            )
            
            logger.info(f"Resource needs prediction completed for user {user_id}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting resource needs for user {user_id}: {e}")
            # Return empty prediction with low confidence
            return ResourceNeedsPrediction(
                user_id=user_id,
                confidence=0.1,
                confidence_level=PredictionConfidenceLevel.LOW,
                estimated_cpu=0.1,
                estimated_memory=1.0,
                estimated_duration=3600,
                cost_estimate=1.0,
                metadata={"error": str(e)}
            )
    
    async def get_comprehensive_analysis(
        self, 
        user_id: str, 
        system_context: Optional[Dict[str, Any]] = None,
        upcoming_workload: Optional[Dict[str, Any]] = None,
        timeframe: str = "30d"
    ) -> Dict[str, Any]:
        """
        Get comprehensive resource intelligence analysis
        
        Args:
            user_id: User identifier
            system_context: Current system context
            upcoming_workload: Planned workload for prediction
            timeframe: Analysis timeframe
            
        Returns:
            Dict containing all resource intelligence results
        """
        try:
            logger.info(f"Getting comprehensive resource analysis for user {user_id}")
            
            # Run analyses
            system_pattern = await self.analyze_system_patterns(
                user_id, system_context, timeframe
            )
            
            resource_prediction = None
            if upcoming_workload:
                resource_prediction = await self.predict_resource_needs(
                    user_id, upcoming_workload
                )
            
            # Calculate overall confidence
            confidences = [system_pattern.confidence]
            if resource_prediction:
                confidences.append(resource_prediction.confidence)
            
            overall_confidence = sum(confidences) / len(confidences)
            
            # Generate insights and recommendations
            insights = self._generate_resource_insights(
                system_pattern, resource_prediction
            )
            recommendations = self._generate_resource_recommendations(
                system_pattern, resource_prediction
            )
            
            result = {
                "user_id": user_id,
                "system_patterns": system_pattern,
                "overall_confidence": overall_confidence,
                "analysis_timestamp": datetime.utcnow(),
                "timeframe": timeframe,
                "insights": insights,
                "recommendations": recommendations
            }
            
            if resource_prediction:
                result["resource_predictions"] = resource_prediction
            
            return result
            
        except Exception as e:
            logger.error(f"Error in comprehensive resource analysis for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "overall_confidence": 0.0,
                "analysis_timestamp": datetime.utcnow()
            }
    
    def _generate_resource_insights(
        self, 
        system_pattern: SystemPattern,
        resource_prediction: Optional[ResourceNeedsPrediction]
    ) -> List[str]:
        """Generate actionable resource insights"""
        insights = []
        
        # System pattern insights
        if system_pattern.confidence > 0.6:
            if system_pattern.bottlenecks:
                insights.append(f"Identified {len(system_pattern.bottlenecks)} system bottlenecks")
            
            if system_pattern.optimization_opportunities:
                insights.append(f"Found {len(system_pattern.optimization_opportunities)} optimization opportunities")
            
            # Resource utilization insights
            utilization = system_pattern.resource_utilization
            if utilization:
                high_usage = [k for k, v in utilization.items() if isinstance(v, (int, float)) and v > 0.8]
                if high_usage:
                    insights.append(f"High resource utilization detected in: {', '.join(high_usage)}")
        
        # Resource prediction insights
        if resource_prediction and resource_prediction.confidence > 0.6:
            if resource_prediction.resource_alerts:
                insights.append(f"Generated {len(resource_prediction.resource_alerts)} resource alerts")
            
            if resource_prediction.scaling_recommendations:
                insights.append(f"Recommended {len(resource_prediction.scaling_recommendations)} scaling actions")
        
        return insights
    
    def _generate_resource_recommendations(
        self, 
        system_pattern: SystemPattern,
        resource_prediction: Optional[ResourceNeedsPrediction]
    ) -> List[str]:
        """Generate actionable resource recommendations"""
        recommendations = []
        
        # System optimization recommendations
        if system_pattern.optimization_opportunities:
            for opportunity in system_pattern.optimization_opportunities[:3]:  # Top 3
                recommendations.append(f"Optimize: {opportunity}")
        
        # Bottleneck resolution
        if system_pattern.bottlenecks:
            for bottleneck in system_pattern.bottlenecks[:2]:  # Top 2
                recommendations.append(f"Resolve bottleneck: {bottleneck}")
        
        # Resource scaling recommendations
        if resource_prediction and resource_prediction.scaling_recommendations:
            recommendations.extend(resource_prediction.scaling_recommendations[:3])
        
        # Cost optimization
        if system_pattern.cost_analysis:
            cost_data = system_pattern.cost_analysis
            if cost_data.get("potential_savings", 0) > 0:
                recommendations.append(f"Potential cost savings: ${cost_data.get('potential_savings', 0):.2f}")
        
        return recommendations
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of resource intelligence service"""
        try:
            # Check sub-service health
            system_health = await self.system_analyzer.health_check()
            resource_health = await self.resource_predictor.health_check()
            
            all_healthy = all([
                system_health.get("status") == "healthy",
                resource_health.get("status") == "healthy"
            ])
            
            return {
                "service": "resource_intelligence",
                "status": "healthy" if all_healthy else "degraded",
                "sub_services": {
                    "system_analyzer": system_health,
                    "resource_predictor": resource_health
                },
                "last_check": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "resource_intelligence",
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow()
            }


# Import asyncio at module level to avoid issues
import asyncio