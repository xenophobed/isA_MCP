"""
Prediction Service Package

Proactive AI prediction capabilities integrated into user service
Provides 8 core prediction tools across 4 service suites
"""

from .prediction_models import (
    PredictionConfidenceLevel,
    PredictionType,
    BasePredictionResult,
    TemporalPattern,
    UserBehaviorPattern,
    UserNeedsPrediction,
    ContextPattern,
    TaskOutcomePrediction,
    SystemPattern,
    ResourceNeedsPrediction,
    ComplianceRiskPrediction,
    PredictionRequest,
    PredictionResponse,
    PredictionServiceHealth
)

__version__ = "1.0.0"
__author__ = "Proactive AI Team"
__description__ = "Intelligent prediction service for proactive AI capabilities"

__all__ = [
    "PredictionConfidenceLevel",
    "PredictionType", 
    "BasePredictionResult",
    "TemporalPattern",
    "UserBehaviorPattern",
    "UserNeedsPrediction",
    "ContextPattern",
    "TaskOutcomePrediction",
    "SystemPattern",
    "ResourceNeedsPrediction",
    "ComplianceRiskPrediction",
    "PredictionRequest",
    "PredictionResponse",
    "PredictionServiceHealth"
]