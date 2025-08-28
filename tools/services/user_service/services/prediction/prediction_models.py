"""
Prediction Service Models

Comprehensive data models for the proactive prediction system
Based on analysis of user_service and memory_service data structures
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class PredictionConfidenceLevel(str, Enum):
    """Confidence levels for predictions with thresholds"""
    LOW = "low"              # 0.0 - 0.3: Setup reactive triggers
    MEDIUM = "medium"        # 0.3 - 0.6: Collaborative workflow  
    HIGH = "high"            # 0.6 - 0.8: Involve human
    VERY_HIGH = "very_high"  # 0.8 - 1.0: Proactive action


class PredictionType(str, Enum):
    """Types of predictions the system can make"""
    TEMPORAL_PATTERNS = "temporal_patterns"
    USER_PATTERNS = "user_patterns"
    CONTEXT_PATTERNS = "context_patterns"
    SYSTEM_PATTERNS = "system_patterns"
    USER_NEEDS = "user_needs"
    TASK_OUTCOMES = "task_outcomes"
    RESOURCE_NEEDS = "resource_needs"
    COMPLIANCE_RISKS = "compliance_risks"


class BasePredictionResult(BaseModel):
    """Base prediction result with common fields"""
    prediction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID for the prediction")
    prediction_type: PredictionType = Field(..., description="Type of prediction")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence score")
    confidence_level: PredictionConfidenceLevel = Field(..., description="Confidence level category")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="When this prediction expires")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def get_confidence_level(self) -> PredictionConfidenceLevel:
        """Determine confidence level from score"""
        if self.confidence >= 0.8:
            return PredictionConfidenceLevel.VERY_HIGH
        elif self.confidence >= 0.6:
            return PredictionConfidenceLevel.HIGH
        elif self.confidence >= 0.3:
            return PredictionConfidenceLevel.MEDIUM
        else:
            return PredictionConfidenceLevel.LOW


# ============ Suite 1: User Behavior Analytics Models ============

class TemporalPattern(BasePredictionResult):
    """Temporal behavior patterns for users"""
    prediction_type: PredictionType = Field(PredictionType.TEMPORAL_PATTERNS, description="Prediction type")
    
    # Pattern data
    time_periods: Dict[str, float] = Field(..., description="Usage patterns by time period")
    peak_hours: List[int] = Field(..., description="Peak usage hours (0-23)")
    session_frequency: Dict[str, float] = Field(..., description="Session frequency patterns")
    cyclical_patterns: Dict[str, Any] = Field(default_factory=dict, description="Weekly/monthly cycles")
    
    # Analysis metadata
    data_period: str = Field(..., description="Time period analyzed (e.g., '30d')")
    sample_size: int = Field(..., description="Number of sessions analyzed")


class UserBehaviorPattern(BasePredictionResult):
    """Individual user behavior patterns"""
    prediction_type: PredictionType = Field(PredictionType.USER_PATTERNS, description="Prediction type")
    
    # Behavior data
    task_preferences: List[str] = Field(..., description="Preferred task types")
    tool_preferences: List[str] = Field(..., description="Most used tools")
    interaction_style: Dict[str, Any] = Field(..., description="Communication patterns")
    success_patterns: Dict[str, float] = Field(..., description="Success rates by task type")
    failure_patterns: List[str] = Field(..., description="Common failure modes")
    
    # Contextual patterns
    context_preferences: Dict[str, Any] = Field(default_factory=dict, description="Preferred contexts")
    session_patterns: Dict[str, Any] = Field(default_factory=dict, description="Session behavior patterns")


class UserNeedsPrediction(BasePredictionResult):
    """Prediction of what user will likely need next"""
    prediction_type: PredictionType = Field(PredictionType.USER_NEEDS, description="Prediction type")
    
    # Predicted needs
    anticipated_tasks: List[str] = Field(..., description="Tasks user likely to perform")
    required_tools: List[str] = Field(..., description="Tools user will likely need")
    context_needs: Dict[str, Any] = Field(..., description="Context information needed")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict, description="Resource needs")
    
    # Prediction basis
    based_on_patterns: List[str] = Field(..., description="Pattern IDs used for prediction")
    similar_sessions: List[str] = Field(default_factory=list, description="Similar past sessions")
    trigger_indicators: List[str] = Field(default_factory=list, description="What triggered prediction")


# ============ Suite 2: Context Intelligence Models ============

class ContextPattern(BasePredictionResult):
    """Environment-based usage patterns"""
    prediction_type: PredictionType = Field(PredictionType.CONTEXT_PATTERNS, description="Prediction type")
    
    # Context analysis
    context_type: str = Field(..., description="Type of context (dev, analysis, research)")
    usage_patterns: Dict[str, Any] = Field(..., description="Usage patterns in this context")
    tool_combinations: List[List[str]] = Field(..., description="Common tool combinations")
    success_indicators: List[str] = Field(..., description="Indicators of successful sessions")
    
    # Environmental factors
    memory_usage_patterns: Dict[str, Any] = Field(default_factory=dict, description="Memory type usage")
    session_characteristics: Dict[str, Any] = Field(default_factory=dict, description="Session patterns")


class TaskOutcomePrediction(BasePredictionResult):
    """Prediction of task success/failure probability"""
    prediction_type: PredictionType = Field(PredictionType.TASK_OUTCOMES, description="Prediction type")
    
    # Outcome prediction
    task_description: str = Field(..., description="Description of the task")
    success_probability: float = Field(..., ge=0.0, le=1.0, description="Probability of success")
    risk_factors: List[str] = Field(..., description="Identified risk factors")
    optimization_suggestions: List[str] = Field(..., description="Ways to improve success rate")
    
    # Supporting data
    similar_past_tasks: List[str] = Field(default_factory=list, description="Similar historical tasks")
    resource_conflicts: List[str] = Field(default_factory=list, description="Potential resource conflicts")
    timing_considerations: Dict[str, Any] = Field(default_factory=dict, description="Timing factors")


# ============ Suite 3: Resource Intelligence Models ============

class SystemPattern(BasePredictionResult):
    """Infrastructure usage patterns"""
    prediction_type: PredictionType = Field(PredictionType.SYSTEM_PATTERNS, description="Prediction type")
    
    # Resource usage
    resource_usage: Dict[str, float] = Field(..., description="Current resource usage patterns")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance indicators")
    bottlenecks: List[str] = Field(..., description="Identified bottlenecks")
    peak_usage_times: Dict[str, float] = Field(..., description="Peak usage periods")
    
    # System health
    failure_patterns: List[str] = Field(default_factory=list, description="Common failure modes")
    optimization_opportunities: List[str] = Field(default_factory=list, description="Optimization suggestions")


class ResourceNeedsPrediction(BasePredictionResult):
    """Computational resource requirements prediction"""
    prediction_type: PredictionType = Field(PredictionType.RESOURCE_NEEDS, description="Prediction type")
    
    # Resource estimates
    estimated_cpu: float = Field(..., description="Estimated CPU usage (0.0-1.0)")
    estimated_memory: float = Field(..., description="Estimated memory usage (GB)")
    estimated_duration: int = Field(..., description="Estimated duration (seconds)")
    cost_estimate: float = Field(..., description="Estimated cost in USD")
    
    # Resource characteristics
    high_cpu_usage_predicted: bool = Field(False, description="CPU intensive operation")
    memory_intensive_predicted: bool = Field(False, description="Memory intensive operation")
    io_intensive_predicted: bool = Field(False, description="I/O intensive operation")
    
    # Optimization options
    optimization_options: List[str] = Field(default_factory=list, description="Available optimizations")
    resource_alternatives: Dict[str, Any] = Field(default_factory=dict, description="Alternative approaches")


# ============ Suite 4: Risk Management Models ============

class ComplianceRiskPrediction(BasePredictionResult):
    """Policy and regulatory compliance risk assessment"""
    prediction_type: PredictionType = Field(PredictionType.COMPLIANCE_RISKS, description="Prediction type")
    
    # Risk assessment
    risk_level: str = Field(..., description="Overall risk level (low/medium/high/critical)")
    policy_conflicts: List[str] = Field(..., description="Identified policy conflicts")
    access_violations: List[str] = Field(..., description="Potential access violations")
    regulatory_concerns: List[str] = Field(default_factory=list, description="Regulatory compliance issues")
    
    # Mitigation
    mitigation_strategies: List[str] = Field(..., description="Recommended mitigation actions")
    requires_approval: bool = Field(False, description="Whether approval is needed")
    approval_workflow: Optional[str] = Field(None, description="Required approval workflow")
    
    # Additional context
    resource_permissions: Dict[str, str] = Field(default_factory=dict, description="Current permissions")
    organization_policies: List[str] = Field(default_factory=list, description="Applicable policies")


# ============ Orchestrator Models ============

class PredictionRequest(BaseModel):
    """Request for predictions"""
    user_id: str = Field(..., description="User ID")
    prediction_types: List[PredictionType] = Field(..., description="Types of predictions requested")
    context: Dict[str, Any] = Field(default_factory=dict, description="Request context")
    timeframe: Optional[str] = Field("30d", description="Analysis timeframe")
    include_low_confidence: bool = Field(False, description="Include low confidence predictions")


class PredictionResponse(BaseModel):
    """Response containing multiple predictions"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID")
    predictions: List[BasePredictionResult] = Field(..., description="Generated predictions")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    data_sources_used: List[str] = Field(default_factory=list, description="Data sources consulted")
    analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="Analysis summary")


class PredictionServiceHealth(BaseModel):
    """Health status of prediction service"""
    service_status: str = Field(..., description="Service status")
    suite_statuses: Dict[str, str] = Field(..., description="Status of each prediction suite")
    last_update: datetime = Field(default_factory=datetime.utcnow)
    data_freshness: Dict[str, datetime] = Field(default_factory=dict, description="Data freshness by source")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics")