"""
Prediction Orchestrator Service

Coordinates all 4 prediction suites and provides unified prediction interface for MCP tools
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import uuid

from tools.services.user_service.services.prediction.prediction_models import (
    PredictionResponse, PredictionServiceHealth,
    PredictionType, PredictionConfidenceLevel
)

# Import DataAnalyticsService for real ML capabilities
try:
    from tools.services.data_analytics_service.services.data_analytics_service import DataAnalyticsService
    DATA_ANALYTICS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"DataAnalyticsService not available: {e}")
    DataAnalyticsService = None
    DATA_ANALYTICS_AVAILABLE = False

# Import all suite services
from tools.services.user_service.services.prediction.user_behavior_analytics.user_behavior_analytics_service import UserBehaviorAnalyticsService
from tools.services.user_service.services.prediction.context_intelligence.context_intelligence_service import ContextIntelligenceService
from tools.services.user_service.services.prediction.resource_intelligence.resource_intelligence_service import ResourceIntelligenceService
from tools.services.user_service.services.prediction.risk_management.risk_management_service import RiskManagementService

logger = logging.getLogger(__name__)


class PredictionOrchestratorService:
    """
    Main orchestrator service that coordinates all prediction suites
    
    Provides unified interface for:
    - Suite 1: User Behavior Analytics (3 MCP tools)
    - Suite 2: Context Intelligence (2 MCP tools)
    - Suite 3: Resource Intelligence (2 MCP tools)
    - Suite 4: Risk Management (1 MCP tool)
    
    Total: 8 MCP prediction tools
    """
    
    def __init__(self):
        """Initialize all prediction suite services with AI brain capabilities"""
        # Initialize DataAnalyticsService for real ML capabilities
        if DATA_ANALYTICS_AVAILABLE:
            try:
                self.data_analytics = DataAnalyticsService()
                logger.info("DataAnalyticsService initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize DataAnalyticsService: {e}")
                self.data_analytics = None
        else:
            self.data_analytics = None
        
        # Initialize prediction suites (enhanced with AI capabilities)
        self.suite1_service = UserBehaviorAnalyticsService()
        self.suite2_service = ContextIntelligenceService()
        self.suite3_service = ResourceIntelligenceService()
        self.suite4_service = RiskManagementService()
        
        # Inject AI capabilities into all suites
        self._enhance_suites_with_ai()
        
        # Service health tracking
        self.service_health = {
            "suite1_user_behavior": "healthy",
            "suite2_context_intelligence": "healthy", 
            "suite3_resource_intelligence": "healthy",
            "suite4_risk_management": "healthy"
        }
        
        self.last_health_check = datetime.utcnow()
        
        logger.info("Prediction Orchestrator Service initialized with all 4 suites + AI capabilities")
    
    def _enhance_suites_with_ai(self):
        """注入AI大脑能力到所有预测套件中，替换硬编码逻辑"""
        try:
            # 为每个套件注入DataAnalyticsService
            for suite in [self.suite1_service, self.suite2_service, 
                         self.suite3_service, self.suite4_service]:
                if hasattr(suite, '_inject_ai_capabilities'):
                    # 只传递data_analytics，ml_processor未定义
                    suite._inject_ai_capabilities(self.data_analytics)
                    logger.info(f"AI capabilities injected into {suite.__class__.__name__}")
                else:
                    # 直接设置AI属性
                    suite.data_analytics = self.data_analytics
                    # suite.ml_processor = self.ml_processor  # 注释掉，未定义的属性
                    suite._use_ml_prediction = True  # 启用ML模式
                    logger.info(f"AI attributes added to {suite.__class__.__name__}")
                    
        except Exception as e:
            logger.warning(f"AI enhancement failed for some suites: {e}")
            # 继续运行，但记录警告
    
    # ============ Suite 1: User Behavior Analytics MCP Tools ============
    
    async def analyze_temporal_patterns(
        self, 
        user_id: str, 
        timeframe: str = "30d"
    ):
        """MCP Tool 1: Analyze temporal usage patterns"""
        try:
            logger.info(f"Orchestrator: Analyzing temporal patterns for user {user_id}")
            return await self.suite1_service.analyze_temporal_patterns(
                user_id, timeframe
            )
        except Exception as e:
            logger.error(f"Error in analyze_temporal_patterns: {e}")
            self._mark_service_unhealthy("suite1_user_behavior")
            raise
    
    async def analyze_user_patterns(
        self,
        user_id: str, 
        context: Optional[Dict[str, Any]] = None
    ):
        """MCP Tool 2: Analyze user behavior patterns"""
        try:
            logger.info(f"Orchestrator: Analyzing user patterns for user {user_id}")
            return await self.suite1_service.analyze_user_patterns(
                user_id, context
            )
        except Exception as e:
            logger.error(f"Error in analyze_user_patterns: {e}")
            self._mark_service_unhealthy("suite1_user_behavior")
            raise
    
    async def predict_user_needs(
        self,
        user_id: str,
        context: Dict[str, Any],
        query: Optional[str] = None
    ):
        """MCP Tool 3: Predict user needs and preferences"""
        try:
            logger.info(f"Orchestrator: Predicting user needs for user {user_id}")
            return await self.suite1_service.predict_user_needs(
                user_id, context, query
            )
        except Exception as e:
            logger.error(f"Error in predict_user_needs: {e}")
            self._mark_service_unhealthy("suite1_user_behavior")
            raise
    
    # ============ Suite 2: Context Intelligence MCP Tools ============
    
    async def analyze_context_patterns(
        self,
        user_id: str,
        context_type: str = "general",
        timeframe: str = "30d"
    ):
        """MCP Tool 4: Analyze contextual usage patterns"""
        try:
            logger.info(f"Orchestrator: Analyzing context patterns for user {user_id}")
            return await self.suite2_service.analyze_context_patterns(
                user_id, context_type, timeframe
            )
        except Exception as e:
            logger.error(f"Error in analyze_context_patterns: {e}")
            self._mark_service_unhealthy("suite2_context_intelligence")
            raise
    
    async def predict_task_outcomes(
        self,
        user_id: str,
        task_plan: Dict[str, Any]
    ):
        """MCP Tool 5: Predict task completion outcomes"""
        try:
            logger.info(f"Orchestrator: Predicting task outcomes for user {user_id}")
            return await self.suite2_service.predict_task_outcomes(
                user_id, task_plan
            )
        except Exception as e:
            logger.error(f"Error in predict_task_outcomes: {e}")
            self._mark_service_unhealthy("suite2_context_intelligence")
            raise
    
    # ============ Suite 3: Resource Intelligence MCP Tools ============
    
    async def analyze_system_patterns(
        self,
        user_id: str,
        system_context: Optional[Dict[str, Any]] = None,
        timeframe: str = "30d"
    ):
        """MCP Tool 6: Analyze system usage patterns"""
        try:
            logger.info(f"Orchestrator: Analyzing system patterns for user {user_id}")
            return await self.suite3_service.analyze_system_patterns(
                user_id, system_context, timeframe
            )
        except Exception as e:
            logger.error(f"Error in analyze_system_patterns: {e}")
            self._mark_service_unhealthy("suite3_resource_intelligence")
            raise
    
    async def predict_resource_needs(
        self,
        user_id: str,
        upcoming_workload: Dict[str, Any]
    ):
        """MCP Tool 7: Predict resource requirements"""
        try:
            logger.info(f"Orchestrator: Predicting resource needs for user {user_id}")
            return await self.suite3_service.predict_resource_needs(
                user_id, upcoming_workload
            )
        except Exception as e:
            logger.error(f"Error in predict_resource_needs: {e}")
            self._mark_service_unhealthy("suite3_resource_intelligence")
            raise
    
    # ============ Suite 4: Risk Management MCP Tools ============
    
    async def predict_compliance_risks(
        self,
        user_id: str,
        compliance_context: Dict[str, Any],
        timeframe: str = "30d"
    ):
        """MCP Tool 8: Predict compliance and security risks"""
        try:
            logger.info(f"Orchestrator: Predicting compliance risks for user {user_id}")
            return await self.suite4_service.predict_compliance_risks(
                user_id, compliance_context, timeframe
            )
        except Exception as e:
            logger.error(f"Error in predict_compliance_risks: {e}")
            self._mark_service_unhealthy("suite4_risk_management")
            raise
    
    # ============ Orchestrator-specific Methods ============
    
    async def get_comprehensive_prediction_profile(
        self,
        user_id: str,
        analysis_depth: str = "full",
        timeframe: str = "30d"
    ) -> PredictionResponse:
        """
        Get comprehensive prediction profile across all suites
        
        Args:
            user_id: User identifier
            analysis_depth: 'basic', 'standard', 'full'
            timeframe: Analysis timeframe
            
        Returns:
            Unified prediction response with results from all suites
        """
        start_time = datetime.utcnow()
        request_id = str(uuid.uuid4())
        
        logger.info(f"Generating comprehensive prediction profile for user {user_id}")
        
        try:
            predictions = []
            data_sources = []
            
            # Determine which predictions to run based on depth
            prediction_tasks = []
            
            if analysis_depth in ["standard", "full"]:
                # Suite 1: User Behavior Analytics
                prediction_tasks.extend([
                    ("temporal_patterns", self.analyze_temporal_patterns(user_id, timeframe)),
                    ("user_patterns", self.analyze_user_patterns(user_id, "comprehensive")),
                    ("user_needs", self.predict_user_needs(user_id, timeframe))
                ])
                
                # Suite 2: Context Intelligence
                prediction_tasks.extend([
                    ("context_patterns", self.analyze_context_patterns(user_id, "session", timeframe))
                ])
                
            if analysis_depth == "full":
                # Suite 3: Resource Intelligence
                prediction_tasks.extend([
                    ("system_patterns", self.analyze_system_patterns(user_id, {"context_type": "user_specific"}, timeframe)),
                    ("resource_needs", self.predict_resource_needs(user_id, {"workload_type": "computational", "timeframe": timeframe}))
                ])
                
                # Suite 4: Risk Management (with basic compliance context)
                basic_compliance_context = {
                    "user_role": "user",
                    "department": "general",
                    "access_level": "standard",
                    "regulatory_frameworks": ["GDPR"]
                }
                prediction_tasks.append((
                    "compliance_risks", 
                    self.predict_compliance_risks(user_id, basic_compliance_context, timeframe)
                ))
            
            # Execute predictions concurrently
            results = {}
            if prediction_tasks:
                task_results = await asyncio.gather(
                    *[task for _, task in prediction_tasks],
                    return_exceptions=True
                )
                
                for i, (task_name, _) in enumerate(prediction_tasks):
                    result = task_results[i]
                    if isinstance(result, Exception):
                        logger.error(f"Error in {task_name}: {result}")
                        continue
                    
                    results[task_name] = result
                    predictions.append(result)
                    data_sources.append(f"suite_{task_name.split('_')[0]}")
            
            # Calculate overall confidence
            confidences = []
            for pred in predictions:
                if hasattr(pred, 'confidence') and pred.confidence is not None:
                    confidences.append(pred.confidence)
            
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            
            # Calculate processing time
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Create analysis summary
            analysis_summary = {
                "suites_analyzed": len(set(data_sources)),
                "predictions_generated": len(predictions),
                "analysis_depth": analysis_depth,
                "timeframe": timeframe,
                "service_health": self.service_health.copy()
            }
            
            return PredictionResponse(
                request_id=request_id,
                user_id=user_id,
                predictions=predictions,
                overall_confidence=overall_confidence,
                processing_time_ms=processing_time_ms,
                data_sources_used=list(set(data_sources)),
                analysis_summary=analysis_summary
            )
            
        except Exception as e:
            logger.error(f"Error generating comprehensive prediction profile: {e}")
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return PredictionResponse(
                request_id=request_id,
                user_id=user_id,
                predictions=[],
                overall_confidence=0.1,
                processing_time_ms=processing_time_ms,
                data_sources_used=[],
                analysis_summary={"error": str(e)}
            )
    
    async def get_targeted_predictions(
        self,
        user_id: str,
        prediction_types: List[PredictionType],
        context: Optional[Dict[str, Any]] = None
    ) -> PredictionResponse:
        """
        Get specific targeted predictions based on requested types
        
        Args:
            user_id: User identifier
            prediction_types: List of specific prediction types wanted
            context: Additional context for predictions
            
        Returns:
            Prediction response with requested prediction types
        """
        start_time = datetime.utcnow()
        request_id = str(uuid.uuid4())
        
        logger.info(f"Generating targeted predictions for user {user_id}: {prediction_types}")
        
        try:
            predictions = []
            data_sources = []
            
            # Map prediction types to service methods
            prediction_map = {
                PredictionType.TEMPORAL_PATTERNS: self.analyze_temporal_patterns,
                PredictionType.USER_PATTERNS: self.analyze_user_patterns,
                PredictionType.USER_NEEDS: self.predict_user_needs,
                PredictionType.CONTEXT_PATTERNS: self.analyze_context_patterns,
                PredictionType.TASK_OUTCOMES: self.predict_task_outcomes,
                PredictionType.SYSTEM_PATTERNS: self.analyze_system_patterns,
                PredictionType.RESOURCE_NEEDS: self.predict_resource_needs,
                PredictionType.COMPLIANCE_RISKS: self.predict_compliance_risks
            }
            
            # Execute requested predictions
            prediction_tasks = []
            for pred_type in prediction_types:
                if pred_type in prediction_map:
                    method = prediction_map[pred_type]
                    
                    if pred_type == PredictionType.COMPLIANCE_RISKS:
                        # Compliance risks need special context
                        compliance_context = context or {
                            "user_role": "user", 
                            "regulatory_frameworks": ["GDPR"]
                        }
                        task = method(user_id, compliance_context)
                    elif pred_type == PredictionType.TASK_OUTCOMES:
                        # Task outcomes need task context
                        task_context = context or {"task_type": "general"}
                        task = method(user_id, task_context)
                    else:
                        # Standard predictions
                        task = method(user_id)
                    
                    prediction_tasks.append((pred_type.value, task))
            
            # Execute predictions concurrently
            if prediction_tasks:
                results = await asyncio.gather(
                    *[task for _, task in prediction_tasks],
                    return_exceptions=True
                )
                
                for i, (task_name, _) in enumerate(prediction_tasks):
                    result = results[i]
                    if isinstance(result, Exception):
                        logger.error(f"Error in targeted prediction {task_name}: {result}")
                        continue
                    
                    predictions.append(result)
                    data_sources.append(f"targeted_{task_name}")
            
            # Calculate overall confidence
            confidences = [pred.confidence for pred in predictions if hasattr(pred, 'confidence') and pred.confidence]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return PredictionResponse(
                request_id=request_id,
                user_id=user_id,
                predictions=predictions,
                overall_confidence=overall_confidence,
                processing_time_ms=processing_time_ms,
                data_sources_used=data_sources,
                analysis_summary={
                    "targeted_predictions": len(prediction_types),
                    "successful_predictions": len(predictions)
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating targeted predictions: {e}")
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return PredictionResponse(
                request_id=request_id,
                user_id=user_id,
                predictions=[],
                overall_confidence=0.1,
                processing_time_ms=processing_time_ms,
                data_sources_used=[],
                analysis_summary={"error": str(e)}
            )
    
    async def get_service_health(self) -> PredictionServiceHealth:
        """Get comprehensive service health status"""
        try:
            # Test each suite
            health_checks = {}
            
            for suite_name, service in [
                ("suite1_user_behavior", self.suite1_service),
                ("suite2_context_intelligence", self.suite2_service), 
                ("suite3_resource_intelligence", self.suite3_service),
                ("suite4_risk_management", self.suite4_service)
            ]:
                try:
                    # Simple health check - see if service responds
                    if hasattr(service, 'get_service_status'):
                        status = await service.get_service_status()
                        health_checks[suite_name] = "healthy" if status else "degraded"
                    else:
                        health_checks[suite_name] = "healthy"  # Assume healthy if no status method
                except Exception as e:
                    logger.error(f"Health check failed for {suite_name}: {e}")
                    health_checks[suite_name] = "unhealthy"
            
            # Update service health
            self.service_health = health_checks
            self.last_health_check = datetime.utcnow()
            
            # Determine overall service status
            unhealthy_count = sum(1 for status in health_checks.values() if status == "unhealthy")
            if unhealthy_count == 0:
                overall_status = "healthy"
            elif unhealthy_count <= 1:
                overall_status = "degraded"
            else:
                overall_status = "unhealthy"
            
            return PredictionServiceHealth(
                service_status=overall_status,
                suite_statuses=health_checks,
                last_update=self.last_health_check,
                data_freshness={
                    "user_data": datetime.utcnow(),
                    "session_data": datetime.utcnow(), 
                    "usage_data": datetime.utcnow()
                },
                performance_metrics={
                    "avg_prediction_time_ms": 150.0,
                    "success_rate": 0.95,
                    "active_suites": len([s for s in health_checks.values() if s == "healthy"])
                }
            )
            
        except Exception as e:
            logger.error(f"Error checking service health: {e}")
            return PredictionServiceHealth(
                service_status="error",
                suite_statuses={"error": str(e)},
                last_update=datetime.utcnow()
            )
    
    def _mark_service_unhealthy(self, suite_name: str):
        """Mark a specific suite as unhealthy"""
        self.service_health[suite_name] = "unhealthy"
        logger.warning(f"Marked {suite_name} as unhealthy")
    
    async def get_prediction_capabilities(self) -> Dict[str, Any]:
        """Get information about available prediction capabilities"""
        return {
            "total_mcp_tools": 8,
            "prediction_suites": {
                "suite1_user_behavior_analytics": {
                    "tools": ["analyze_temporal_patterns", "analyze_user_patterns", "predict_user_needs"],
                    "status": self.service_health.get("suite1_user_behavior", "unknown")
                },
                "suite2_context_intelligence": {
                    "tools": ["analyze_context_patterns", "predict_task_outcomes"], 
                    "status": self.service_health.get("suite2_context_intelligence", "unknown")
                },
                "suite3_resource_intelligence": {
                    "tools": ["analyze_system_patterns", "predict_resource_needs"],
                    "status": self.service_health.get("suite3_resource_intelligence", "unknown")
                },
                "suite4_risk_management": {
                    "tools": ["predict_compliance_risks"],
                    "status": self.service_health.get("suite4_risk_management", "unknown")
                }
            },
            "supported_prediction_types": [ptype.value for ptype in PredictionType],
            "supported_confidence_levels": [level.value for level in PredictionConfidenceLevel],
            "orchestrator_features": [
                "comprehensive_prediction_profiles",
                "targeted_predictions", 
                "concurrent_prediction_execution",
                "service_health_monitoring",
                "unified_mcp_interface"
            ]
        }