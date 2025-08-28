"""
Context Intelligence Service

Main orchestrator for Suite 2: Context Intelligence
Coordinates context analysis and task outcome prediction
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from ..prediction_models import (
    ContextPattern,
    TaskOutcomePrediction, 
    PredictionConfidenceLevel,
    PredictionType
)
from .sub_services.context_pattern_analyzer import ContextPatternAnalyzer
from .sub_services.task_outcome_predictor import TaskOutcomePredictor

logger = logging.getLogger(__name__)


class ContextIntelligenceService:
    """
    Main service orchestrator for context intelligence
    Coordinates context pattern analysis and task outcome prediction
    """
    
    def __init__(self):
        """Initialize sub-services"""
        self.context_analyzer = ContextPatternAnalyzer()
        self.outcome_predictor = TaskOutcomePredictor()
        
        logger.info("Context Intelligence Service initialized")
    
    async def analyze_context_patterns(
        self, 
        user_id: str, 
        context_type: str = "general"
    ) -> ContextPattern:
        """
        Analyze environment-based usage patterns
        
        Args:
            user_id: User identifier
            context_type: Type of context to analyze (dev, analysis, research, etc.)
            
        Returns:
            ContextPattern: Environment-based behavioral insights
        """
        try:
            logger.info(f"Analyzing context patterns for user {user_id}, context: {context_type}")
            
            # Delegate to context analyzer
            pattern = await self.context_analyzer.analyze_patterns(user_id, context_type)
            
            logger.info(f"Context pattern analysis completed for user {user_id}")
            return pattern
            
        except Exception as e:
            logger.error(f"Error analyzing context patterns for user {user_id}: {e}")
            # Return empty pattern with low confidence
            return ContextPattern(
                user_id=user_id,
                confidence=0.1,
                confidence_level=PredictionConfidenceLevel.LOW,
                context_type=context_type,
                usage_patterns={},
                tool_combinations=[],
                success_indicators=[],
                metadata={"error": str(e)}
            )
    
    async def predict_task_outcomes(
        self, 
        user_id: str, 
        task_plan: Dict[str, Any]
    ) -> TaskOutcomePrediction:
        """
        Forecast success/failure probability of planned tasks
        
        Args:
            user_id: User identifier
            task_plan: Planned task information
            
        Returns:
            TaskOutcomePrediction: Success probability, risk factors, optimization suggestions
        """
        try:
            logger.info(f"Predicting task outcomes for user {user_id}")
            
            # Delegate to outcome predictor
            prediction = await self.outcome_predictor.predict_outcomes(user_id, task_plan)
            
            logger.info(f"Task outcome prediction completed for user {user_id}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting task outcomes for user {user_id}: {e}")
            # Return empty prediction with low confidence
            return TaskOutcomePrediction(
                user_id=user_id,
                confidence=0.1,
                confidence_level=PredictionConfidenceLevel.LOW,
                task_description=str(task_plan),
                success_probability=0.5,  # Neutral when uncertain
                risk_factors=["prediction_error"],
                optimization_suggestions=["retry_with_more_data"],
                metadata={"error": str(e)}
            )
    
    async def get_comprehensive_analysis(
        self, 
        user_id: str, 
        context_type: str = "general",
        task_plan: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive context intelligence analysis
        
        Args:
            user_id: User identifier
            context_type: Context type to analyze
            task_plan: Optional task plan for outcome prediction
            
        Returns:
            Dict containing all context intelligence results
        """
        try:
            logger.info(f"Getting comprehensive context analysis for user {user_id}")
            
            # Run analyses (context patterns always, outcomes only if task_plan provided)
            context_pattern = await self.analyze_context_patterns(user_id, context_type)
            
            task_outcome = None
            if task_plan:
                task_outcome = await self.predict_task_outcomes(user_id, task_plan)
            
            # Calculate overall confidence
            confidences = [context_pattern.confidence]
            if task_outcome:
                confidences.append(task_outcome.confidence)
            
            overall_confidence = sum(confidences) / len(confidences)
            
            result = {
                "user_id": user_id,
                "context_patterns": context_pattern,
                "overall_confidence": overall_confidence,
                "analysis_timestamp": datetime.utcnow(),
                "context_type": context_type
            }
            
            if task_outcome:
                result["task_outcomes"] = task_outcome
            
            return result
            
        except Exception as e:
            logger.error(f"Error in comprehensive context analysis for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "overall_confidence": 0.0,
                "analysis_timestamp": datetime.utcnow()
            }
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of context intelligence service"""
        try:
            # Check sub-service health
            context_health = await self.context_analyzer.health_check()
            outcome_health = await self.outcome_predictor.health_check()
            
            all_healthy = all([
                context_health.get("status") == "healthy",
                outcome_health.get("status") == "healthy"
            ])
            
            return {
                "service": "context_intelligence",
                "status": "healthy" if all_healthy else "degraded",
                "sub_services": {
                    "context_analyzer": context_health,
                    "outcome_predictor": outcome_health
                },
                "last_check": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "context_intelligence",
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow()
            }


# Import asyncio at module level to avoid issues
import asyncio