"""
User Behavior Analytics Service

Main orchestrator for Suite 1: User Behavior Analytics
Coordinates temporal analysis, user patterns, and needs prediction
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from ..prediction_models import (
    TemporalPattern, 
    UserBehaviorPattern, 
    UserNeedsPrediction,
    PredictionConfidenceLevel,
    PredictionType
)
from .sub_services.temporal_pattern_analyzer import TemporalPatternAnalyzer
from .sub_services.user_pattern_analyzer import UserPatternAnalyzer
from .sub_services.user_needs_predictor import UserNeedsPredictor

logger = logging.getLogger(__name__)


class UserBehaviorAnalyticsService:
    """
    Main service orchestrator for user behavior analytics
    Coordinates temporal patterns, user patterns, and needs prediction
    """
    
    def __init__(self):
        """Initialize sub-services"""
        self.temporal_analyzer = TemporalPatternAnalyzer()
        self.user_pattern_analyzer = UserPatternAnalyzer()
        self.user_needs_predictor = UserNeedsPredictor()
        
        logger.info("User Behavior Analytics Service initialized")
    
    async def analyze_temporal_patterns(
        self, 
        user_id: str, 
        timeframe: str = "30d"
    ) -> TemporalPattern:
        """
        Analyze time-based behavior patterns for user
        
        Args:
            user_id: User identifier
            timeframe: Analysis timeframe (e.g., "30d", "7d", "1d")
            
        Returns:
            TemporalPattern: Time-based usage patterns
        """
        try:
            logger.info(f"Analyzing temporal patterns for user {user_id}, timeframe: {timeframe}")
            
            # Delegate to temporal analyzer
            pattern = await self.temporal_analyzer.analyze_patterns(user_id, timeframe)
            
            logger.info(f"Temporal pattern analysis completed for user {user_id}")
            return pattern
            
        except Exception as e:
            logger.error(f"Error analyzing temporal patterns for user {user_id}: {e}")
            # Return empty pattern with low confidence
            return TemporalPattern(
                user_id=user_id,
                confidence=0.1,
                confidence_level=PredictionConfidenceLevel.LOW,
                time_periods={},
                peak_hours=[],
                session_frequency={},
                data_period=timeframe,
                sample_size=0,
                metadata={"error": str(e)}
            )
    
    async def analyze_user_patterns(
        self, 
        user_id: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> UserBehaviorPattern:
        """
        Analyze individual user behavior patterns
        
        Args:
            user_id: User identifier
            context: Additional context for analysis
            
        Returns:
            UserBehaviorPattern: Individual user preferences and patterns
        """
        try:
            logger.info(f"Analyzing user patterns for user {user_id}")
            
            # Delegate to user pattern analyzer
            pattern = await self.user_pattern_analyzer.analyze_patterns(user_id, context or {})
            
            logger.info(f"User pattern analysis completed for user {user_id}")
            return pattern
            
        except Exception as e:
            logger.error(f"Error analyzing user patterns for user {user_id}: {e}")
            # Return empty pattern with low confidence
            return UserBehaviorPattern(
                user_id=user_id,
                confidence=0.1,
                confidence_level=PredictionConfidenceLevel.LOW,
                task_preferences=[],
                tool_preferences=[],
                interaction_style={},
                success_patterns={},
                failure_patterns=[],
                metadata={"error": str(e)}
            )
    
    async def predict_user_needs(
        self, 
        user_id: str, 
        context: Dict[str, Any], 
        query: Optional[str] = None
    ) -> UserNeedsPrediction:
        """
        Predict what user will likely need next
        
        Args:
            user_id: User identifier
            context: Current context information
            query: Optional current user query
            
        Returns:
            UserNeedsPrediction: Anticipated tasks, tools, and resources
        """
        try:
            logger.info(f"Predicting user needs for user {user_id}")
            
            # Delegate to user needs predictor
            prediction = await self.user_needs_predictor.predict_needs(
                user_id, context, query
            )
            
            logger.info(f"User needs prediction completed for user {user_id}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting user needs for user {user_id}: {e}")
            # Return empty prediction with low confidence
            return UserNeedsPrediction(
                user_id=user_id,
                confidence=0.1,
                confidence_level=PredictionConfidenceLevel.LOW,
                anticipated_tasks=[],
                required_tools=[],
                context_needs={},
                based_on_patterns=[],
                metadata={"error": str(e)}
            )
    
    async def get_comprehensive_analysis(
        self, 
        user_id: str, 
        context: Optional[Dict[str, Any]] = None,
        timeframe: str = "30d"
    ) -> Dict[str, Any]:
        """
        Get comprehensive behavior analysis combining all sub-services
        
        Args:
            user_id: User identifier
            context: Analysis context
            timeframe: Analysis timeframe
            
        Returns:
            Dict containing all behavior analytics results
        """
        try:
            logger.info(f"Getting comprehensive behavior analysis for user {user_id}")
            
            # Run all analyses in parallel
            temporal_pattern, user_pattern, user_needs = await asyncio.gather(
                self.analyze_temporal_patterns(user_id, timeframe),
                self.analyze_user_patterns(user_id, context),
                self.predict_user_needs(user_id, context or {})
            )
            
            # Calculate overall confidence
            confidences = [
                temporal_pattern.confidence,
                user_pattern.confidence,
                user_needs.confidence
            ]
            overall_confidence = sum(confidences) / len(confidences)
            
            return {
                "user_id": user_id,
                "temporal_patterns": temporal_pattern,
                "user_patterns": user_pattern,
                "user_needs": user_needs,
                "overall_confidence": overall_confidence,
                "analysis_timestamp": datetime.utcnow(),
                "timeframe": timeframe
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "overall_confidence": 0.0,
                "analysis_timestamp": datetime.utcnow()
            }
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of user behavior analytics service"""
        try:
            # Check sub-service health
            temporal_health = await self.temporal_analyzer.health_check()
            pattern_health = await self.user_pattern_analyzer.health_check()
            needs_health = await self.user_needs_predictor.health_check()
            
            all_healthy = all([
                temporal_health.get("status") == "healthy",
                pattern_health.get("status") == "healthy", 
                needs_health.get("status") == "healthy"
            ])
            
            return {
                "service": "user_behavior_analytics",
                "status": "healthy" if all_healthy else "degraded",
                "sub_services": {
                    "temporal_analyzer": temporal_health,
                    "user_pattern_analyzer": pattern_health,
                    "user_needs_predictor": needs_health
                },
                "last_check": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "user_behavior_analytics",
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow()
            }


# Import asyncio at module level to avoid issues
import asyncio