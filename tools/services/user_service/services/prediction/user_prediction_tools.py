#!/usr/bin/env python3
"""
User Prediction Tools
Intelligent prediction tools based on BaseTool
"""

import json
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from core.logging import get_logger

from .prediction_orchestrator_service import PredictionOrchestratorService

logger = get_logger(__name__)

class UserPredictionService(BaseTool):
    """User prediction service providing all 8 prediction MCP tools"""
    
    def __init__(self):
        super().__init__()
        self.orchestrator = PredictionOrchestratorService()
    
    async def analyze_temporal_patterns(
        self, 
        user_id: str, 
        timeframe: str = "30d"
    ) -> str:
        """Analyze user's temporal usage patterns"""
        try:
            result = await self.orchestrator.analyze_temporal_patterns(user_id, timeframe)
            
            response_data = {
                "tool": "analyze_temporal_patterns",
                "user_id": user_id,
                "prediction_type": result.prediction_type.value,
                "confidence": result.confidence,
                "confidence_level": result.confidence_level.value,
                "peak_hours": result.peak_hours,
                "session_frequency": result.session_frequency,
                "time_periods": result.time_periods,
                "data_period": result.data_period,
                "sample_size": result.sample_size,
                "metadata": result.metadata
            }
            
            return self.create_response(
                "success",
                "analyze_temporal_patterns",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "analyze_temporal_patterns",
                {},
                f"Temporal pattern analysis failed: {str(e)}"
            )
    
    async def analyze_user_patterns(
        self,
        user_id: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Analyze individual user behavior patterns"""
        try:
            result = await self.orchestrator.analyze_user_patterns(user_id, context)
            
            response_data = {
                "tool": "analyze_user_patterns",
                "user_id": user_id,
                "prediction_type": result.prediction_type.value,
                "confidence": result.confidence,
                "confidence_level": result.confidence_level.value,
                "task_preferences": result.task_preferences,
                "tool_preferences": result.tool_preferences,  # Fixed: was tool_usage
                "interaction_style": result.interaction_style,
                "success_patterns": result.success_patterns,
                "failure_patterns": result.failure_patterns,  # Fixed: was behavioral_insights
                "context_preferences": result.context_preferences,  # Added missing field
                "session_patterns": result.session_patterns,  # Added missing field
                "metadata": result.metadata
            }
            
            return self.create_response(
                "success",
                "analyze_user_patterns",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "analyze_user_patterns",
                {},
                f"User pattern analysis failed: {str(e)}"
            )
    
    async def predict_user_needs(
        self,
        user_id: str,
        current_context: Dict[str, Any],
        query: Optional[str] = None
    ) -> str:
        """Predict user needs and next actions"""
        try:
            result = await self.orchestrator.predict_user_needs(user_id, current_context, query)
            
            response_data = {
                "tool": "predict_user_needs",
                "user_id": user_id,
                "prediction_type": result.prediction_type.value,
                "confidence": result.confidence,
                "confidence_level": result.confidence_level.value,
                "anticipated_tasks": result.anticipated_tasks,  # Fixed: was suggested_actions
                "required_tools": result.required_tools,  # Fixed: was predicted_tools
                "context_needs": result.context_needs,  # Fixed: was contextual_insights
                "resource_requirements": result.resource_requirements,  # Fixed: was resource_recommendations
                "based_on_patterns": result.based_on_patterns,  # Added missing field
                "similar_sessions": result.similar_sessions,  # Added missing field
                "trigger_indicators": result.trigger_indicators,  # Added missing field
                "metadata": result.metadata
            }
            
            return self.create_response(
                "success",
                "predict_user_needs",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "predict_user_needs",
                {},
                f"User needs prediction failed: {str(e)}"
            )
    
    async def analyze_context_patterns(
        self,
        user_id: str,
        context_type: str = "general"
    ) -> str:
        """Analyze contextual usage patterns"""
        try:
            result = await self.orchestrator.analyze_context_patterns(user_id, context_type)
            
            response_data = {
                "tool": "analyze_context_patterns",
                "user_id": user_id,
                "prediction_type": result.prediction_type.value,
                "confidence": result.confidence,
                "confidence_level": result.confidence_level.value,
                "context_type": result.context_type,
                "usage_patterns": result.usage_patterns,
                "tool_combinations": result.tool_combinations,  # Fixed: was tool_preferences
                "success_indicators": result.success_indicators,  # Added missing field
                "memory_usage_patterns": result.memory_usage_patterns,  # Added missing field
                "session_characteristics": result.session_characteristics,  # Added missing field
                "metadata": result.metadata
            }
            
            return self.create_response(
                "success",
                "analyze_context_patterns",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "analyze_context_patterns",
                {},
                f"Context pattern analysis failed: {str(e)}"
            )
    
    async def predict_task_outcomes(
        self,
        user_id: str,
        task_plan: Dict[str, Any]
    ) -> str:
        """Predict task completion outcomes"""
        try:
            result = await self.orchestrator.predict_task_outcomes(user_id, task_plan)
            
            response_data = {
                "tool": "predict_task_outcomes",
                "user_id": user_id,
                "prediction_type": result.prediction_type.value,
                "confidence": result.confidence,
                "confidence_level": result.confidence_level.value,
                "task_description": result.task_description,  # Added missing field
                "success_probability": result.success_probability,
                "risk_factors": result.risk_factors,
                "optimization_suggestions": result.optimization_suggestions,
                "similar_past_tasks": result.similar_past_tasks,  # Added missing field
                "resource_conflicts": result.resource_conflicts,  # Added missing field
                "timing_considerations": result.timing_considerations,  # Added missing field
                "metadata": result.metadata
            }
            
            return self.create_response(
                "success",
                "predict_task_outcomes",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "predict_task_outcomes",
                {},
                f"Task outcome prediction failed: {str(e)}"
            )
    
    async def analyze_system_patterns(
        self,
        user_id: str,
        system_context: Optional[Dict[str, Any]] = None,
        timeframe: str = "30d"
    ) -> str:
        """Analyze system resource usage patterns"""
        try:
            result = await self.orchestrator.analyze_system_patterns(user_id, system_context, timeframe)
            
            response_data = {
                "tool": "analyze_system_patterns",
                "user_id": user_id,
                "prediction_type": result.prediction_type.value,
                "confidence": result.confidence,
                "confidence_level": result.confidence_level.value,
                "resource_usage": result.resource_usage,
                "performance_metrics": result.performance_metrics,
                "peak_usage_times": result.peak_usage_times,
                "bottlenecks": result.bottlenecks,
                "failure_patterns": result.failure_patterns,  # Added missing field
                "optimization_opportunities": result.optimization_opportunities,  # Added missing field
                "metadata": result.metadata
            }
            
            return self.create_response(
                "success",
                "analyze_system_patterns",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "analyze_system_patterns",
                {},
                f"System pattern analysis failed: {str(e)}"
            )
    
    async def predict_resource_needs(
        self,
        user_id: str,
        upcoming_workload: Dict[str, Any]
    ) -> str:
        """Predict resource requirements"""
        try:
            result = await self.orchestrator.predict_resource_needs(user_id, upcoming_workload)
            
            response_data = {
                "tool": "predict_resource_needs",
                "user_id": user_id,
                "prediction_type": result.prediction_type.value,
                "confidence": result.confidence,
                "confidence_level": result.confidence_level.value,
                "estimated_cpu": result.estimated_cpu,  # Fixed: was predicted_cpu_usage
                "estimated_memory": result.estimated_memory,  # Fixed: was predicted_memory_usage
                "estimated_duration": result.estimated_duration,  # Added missing field
                "cost_estimate": result.cost_estimate,  # Fixed: was cost_projections
                "high_cpu_usage_predicted": result.high_cpu_usage_predicted,  # Added missing field
                "memory_intensive_predicted": result.memory_intensive_predicted,  # Added missing field
                "io_intensive_predicted": result.io_intensive_predicted,  # Added missing field
                "optimization_options": result.optimization_options,  # Added missing field
                "resource_alternatives": result.resource_alternatives,  # Added missing field
                "metadata": result.metadata
            }
            
            return self.create_response(
                "success",
                "predict_resource_needs",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "predict_resource_needs",
                {},
                f"Resource needs prediction failed: {str(e)}"
            )
    
    async def predict_compliance_risks(
        self,
        user_id: str,
        compliance_context: Dict[str, Any],
        timeframe: str = "30d"
    ) -> str:
        """Predict compliance and security risks"""
        try:
            result = await self.orchestrator.predict_compliance_risks(user_id, compliance_context, timeframe)
            
            response_data = {
                "tool": "predict_compliance_risks",
                "user_id": user_id,
                "prediction_type": result.prediction_type.value,
                "confidence": result.confidence,
                "confidence_level": result.confidence_level.value,
                "risk_level": result.risk_level,
                "policy_conflicts": result.policy_conflicts,
                "access_violations": result.access_violations,
                "regulatory_concerns": result.regulatory_concerns,
                "mitigation_strategies": result.mitigation_strategies,
                "requires_approval": result.requires_approval,
                "approval_workflow": result.approval_workflow,
                "resource_permissions": result.resource_permissions,
                "organization_policies": result.organization_policies,
                "metadata": result.metadata
            }
            
            return self.create_response(
                "success",
                "predict_compliance_risks",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "predict_compliance_risks",
                {},
                f"Compliance risk prediction failed: {str(e)}"
            )
    
    async def get_comprehensive_prediction_profile(
        self,
        user_id: str,
        analysis_depth: str = "standard"
    ) -> str:
        """Get comprehensive prediction profile across all suites"""
        try:
            result = await self.orchestrator.get_comprehensive_prediction_profile(
                user_id, analysis_depth
            )
            
            response_data = {
                "tool": "comprehensive_prediction_profile",
                "user_id": user_id,
                "request_id": result.request_id,
                "overall_confidence": result.overall_confidence,
                "processing_time_ms": result.processing_time_ms,
                "predictions_count": len(result.predictions),
                "data_sources_used": result.data_sources_used,
                "analysis_summary": result.analysis_summary,
                "predictions": [
                    {
                        "type": pred.prediction_type.value,
                        "confidence": pred.confidence,
                        "confidence_level": pred.confidence_level.value
                    } for pred in result.predictions
                ]
            }
            
            return self.create_response(
                "success",
                "comprehensive_prediction_profile",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "comprehensive_prediction_profile",
                {},
                f"Comprehensive profile generation failed: {str(e)}"
            )
    
    async def get_prediction_service_health(self) -> str:
        """Check health status of all prediction services"""
        try:
            health = await self.orchestrator.get_service_health()
            
            response_data = {
                "tool": "prediction_service_health",
                "service_status": health.service_status,
                "suite_statuses": health.suite_statuses,
                "last_update": health.last_update.isoformat(),
                "data_freshness": {
                    k: v.isoformat() for k, v in health.data_freshness.items()
                },
                "performance_metrics": health.performance_metrics
            }
            
            return self.create_response(
                "success",
                "prediction_service_health",
                response_data
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "prediction_service_health",
                {},
                f"Health check failed: {str(e)}"
            )


def register_user_prediction_tools(mcp: FastMCP):
    """Register user prediction tools"""
    prediction_service = UserPredictionService()
    
    @mcp.tool()
    async def analyze_temporal_patterns(
        user_id: str, 
        timeframe: str = "30d"
    ) -> str:
        """
        Analyze user's temporal usage patterns
        
        Analyzes when and how often users interact with the system to identify peak usage hours, session frequency patterns, activity rhythms and time-based behavioral trends.
        
        Keywords: temporal, patterns, usage, time, behavior, analysis
        Category: user_prediction
        
        Args:
            user_id: User identifier
            timeframe: Analysis period (7d, 30d, 90d). Default: "30d"
        """
        return await prediction_service.analyze_temporal_patterns(user_id, timeframe)
    
    @mcp.tool()
    async def analyze_user_patterns(
        user_id: str,
        context: str = "{}"
    ) -> str:
        """
        Analyze individual user behavior patterns
        
        Examines user-specific behavioral traits, task preferences, tool usage patterns, interaction styles and success patterns to understand individual user behavior.
        
        Keywords: user, patterns, behavior, preferences, analysis
        Category: user_prediction
        
        Args:
            user_id: User identifier
            context: Additional context for analysis (JSON string)
        """
        # Parse context JSON
        try:
            context_dict = json.loads(context) if context != "{}" else None
        except:
            context_dict = None
        
        return await prediction_service.analyze_user_patterns(user_id, context_dict)
    
    @mcp.tool()
    async def predict_user_needs(
        user_id: str,
        current_context: str,
        query: str = ""
    ) -> str:
        """
        Predict user needs and next actions
        
        Anticipates what the user will likely need or want to do next by analyzing current context and providing suggested tools, actions, and proactive recommendations.
        
        Keywords: predict, needs, suggestions, proactive, recommendations
        Category: user_prediction
        
        Args:
            user_id: User identifier
            current_context: Current user context and situation (JSON string)
            query: Specific query or question from user
        """
        try:
            context_dict = json.loads(current_context)
        except:
            context_dict = {"current_task": "general"}
        
        query_param = query if query else None
        return await prediction_service.predict_user_needs(user_id, context_dict, query_param)
    
    @mcp.tool()
    async def analyze_context_patterns(
        user_id: str,
        context_type: str = "general"
    ) -> str:
        """
        Analyze contextual usage patterns
        
        Examines how context affects user behavior, environment-specific patterns, context-dependent preferences, and situational adaptation strategies.
        
        Keywords: context, patterns, environment, adaptation, analysis
        Category: user_prediction
        
        Args:
            user_id: User identifier
            context_type: Type of context (general, development, analysis, research)
        """
        return await prediction_service.analyze_context_patterns(user_id, context_type)
    
    @mcp.tool()
    async def predict_task_outcomes(
        user_id: str,
        task_plan: str
    ) -> str:
        """
        Predict task completion outcomes
        
        Forecasts likelihood of successful task completion, estimates timeline and effort, identifies potential challenges and resource requirements.
        
        Keywords: predict, task, outcomes, success, completion, timeline
        Category: user_prediction
        
        Args:
            user_id: User identifier
            task_plan: Details about the planned task (JSON string)
        """
        try:
            plan_dict = json.loads(task_plan)
        except:
            plan_dict = {"task_type": "general", "complexity": "medium"}
        
        return await prediction_service.predict_task_outcomes(user_id, plan_dict)
    
    @mcp.tool()
    async def analyze_system_patterns(
        user_id: str,
        system_context: str = "{}",
        timeframe: str = "30d"
    ) -> str:
        """
        Analyze system resource usage patterns
        
        Examines how users consume system resources, identifies usage patterns, performance metrics, peak demand periods and optimization opportunities.
        
        Keywords: system, resources, usage, performance, optimization, analysis
        Category: user_prediction
        
        Args:
            user_id: User identifier
            system_context: Current system state and constraints (JSON string)
            timeframe: Analysis period. Default: "30d"
        """
        try:
            context_dict = json.loads(system_context) if system_context != "{}" else None
        except:
            context_dict = None
        
        return await prediction_service.analyze_system_patterns(user_id, context_dict, timeframe)
    
    @mcp.tool()
    async def predict_resource_needs(
        user_id: str,
        upcoming_workload: str
    ) -> str:
        """
        Predict resource requirements
        
        Forecasts future resource needs including computational requirements, storage, bandwidth, timeline planning and cost estimates based on planned workload.
        
        Keywords: predict, resources, requirements, workload, capacity, planning
        Category: user_prediction
        
        Args:
            user_id: User identifier
            upcoming_workload: Details about planned work and tasks (JSON string)
        """
        try:
            workload_dict = json.loads(upcoming_workload)
        except:
            workload_dict = {"task_complexity": "medium", "data_size": "moderate"}
        
        return await prediction_service.predict_resource_needs(user_id, workload_dict)
    
    @mcp.tool()
    async def predict_compliance_risks(
        user_id: str,
        compliance_context: str,
        timeframe: str = "30d"
    ) -> str:
        """
        Predict compliance and security risks
        
        Assesses potential compliance violations, security risks, policy conflicts and regulatory adherence issues with mitigation strategies and recommendations.
        
        Keywords: compliance, security, risks, violations, policy, regulatory
        Category: user_prediction
        
        Args:
            user_id: User identifier
            compliance_context: User role, permissions, and regulatory context (JSON string)
            timeframe: Risk assessment period. Default: "30d"
        """
        try:
            context_dict = json.loads(compliance_context)
        except:
            context_dict = {"user_role": "user", "regulatory_frameworks": ["GDPR"]}
        
        return await prediction_service.predict_compliance_risks(user_id, context_dict, timeframe)
    
    @mcp.tool()
    async def get_comprehensive_prediction_profile(
        user_id: str,
        analysis_depth: str = "standard"
    ) -> str:
        """
        Get comprehensive prediction profile across all suites
        
        Provides unified analysis using multiple prediction tools, combines insights from all available suites and generates comprehensive recommendations.
        
        Keywords: comprehensive, profile, analysis, unified, insights, recommendations
        Category: user_prediction
        
        Args:
            user_id: User identifier
            analysis_depth: Analysis depth (basic, standard, full)
        """
        return await prediction_service.get_comprehensive_prediction_profile(user_id, analysis_depth)
    
    @mcp.tool()
    async def get_prediction_service_health() -> str:
        """
        Check health status of all prediction services
        
        Returns real-time health status, performance metrics and operational state of all prediction service suites and components.
        
        Keywords: health, status, performance, monitoring, service, diagnostics
        Category: user_prediction
        """
        return await prediction_service.get_prediction_service_health()
    
    print("🔮 User prediction tools registered successfully - 8 MCP prediction tools available")