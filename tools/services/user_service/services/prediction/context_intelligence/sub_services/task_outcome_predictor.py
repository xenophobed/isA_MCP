"""
Task Outcome Predictor

Predicts success/failure probability of planned tasks based on user patterns
Maps to predict_task_outcomes MCP tool
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import json

from ...prediction_models import TaskOutcomePrediction, PredictionConfidenceLevel
from ..utilities.outcome_probability_utils import OutcomeProbabilityUtils

# Import user service repositories and services
from tools.services.user_service.repositories.usage_repository import UsageRepository
from tools.services.user_service.repositories.session_repository import SessionRepository
from tools.services.user_service.repositories.user_repository import UserRepository

# Import AI services for intelligent outcome prediction
from tools.services.data_analytics_service.services.data_analytics_service import DataAnalyticsService
from tools.services.data_analytics_service.processors.data_processors.model.ml_processor import MLProcessor
from tools.services.intelligence_service.language.reasoning_generator import ReasoningGenerator

logger = logging.getLogger(__name__)


class TaskOutcomePredictor:
    """
    Predicts task success/failure probability
    Uses historical patterns, user capabilities, and context analysis
    """
    
    def __init__(self):
        """Initialize repositories, utilities and AI services"""
        self.usage_repo = UsageRepository()
        self.session_repo = SessionRepository()
        self.user_repo = UserRepository()
        self.outcome_utils = OutcomeProbabilityUtils()
        
        # Initialize AI services for intelligent prediction
        self.data_analytics = DataAnalyticsService()
        # Initialize ML processor lazily when needed with actual data
        self.ml_processor = None
        self.reasoning_generator = ReasoningGenerator()
        
        # Control flag for ML vs hardcoded logic
        self._use_ml_prediction = True
        
    async def _ensure_ml_processor(self):
        """Ensure ML processor is initialized with dummy data"""
        if self.ml_processor is None:
            from tools.services.data_analytics_service.processors.data_processors.model.ml_processor import MLProcessor
            # Create temporary data file for initialization
            import tempfile
            import csv
            import os
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            writer = csv.writer(temp_file)
            writer.writerow(['complexity', 'duration', 'success'])
            writer.writerow([1, 10, 0.9])
            writer.writerow([2, 20, 0.7])
            temp_file.close()
            
            self.ml_processor = MLProcessor(file_path=temp_file.name)
            os.unlink(temp_file.name)  # Clean up
        
        # Hardcoded fallbacks (will be replaced by ML learning)
        self.task_complexity = {
            # Simple tasks (high success rate expected)
            "simple": [
                "chat", "basic_search", "simple_query", "text_read", "status_check",
                "basic_memory_retrieval", "simple_calculation"
            ],
            # Medium complexity tasks
            "medium": [
                "data_analysis", "document_processing", "code_review", "research",
                "memory_organization", "content_generation", "format_conversion"
            ],
            # Complex tasks (lower success rate expected)
            "complex": [
                "advanced_analytics", "model_training", "system_integration",
                "bulk_processing", "complex_automation", "multi_step_workflow"
            ]
        }
        
        # Risk factors that commonly cause failures
        self.common_risk_factors = {
            "resource_intensive": ["large_dataset", "bulk_operation", "heavy_computation"],
            "integration_dependent": ["api_calls", "external_service", "network_dependent"],
            "user_expertise": ["advanced_features", "technical_complexity", "domain_specific"],
            "timing_sensitive": ["real_time", "batch_processing", "scheduled_operation"],
            "data_quality": ["data_validation", "format_dependent", "schema_sensitive"]
        }
        
        logger.info("Task Outcome Predictor initialized with AI capabilities")
    
    async def predict_outcomes(
        self, 
        user_id: str, 
        task_plan: Dict[str, Any]
    ) -> TaskOutcomePrediction:
        """
        Predict task outcome probability
        
        Args:
            user_id: User identifier
            task_plan: Task plan with description, tools, parameters
            
        Returns:
            TaskOutcomePrediction: Success probability, risks, optimizations
        """
        try:
            logger.info(f"Predicting task outcomes for user {user_id}")
            
            # Gather user data
            user = await self.user_repo.get_by_user_id(user_id)
            recent_usage = await self.usage_repo.get_recent_usage(user_id, hours=24*30)  # 30 days
            recent_sessions = await self.session_repo.get_user_sessions(user_id, limit=20)
            
            # Use AI for task outcome prediction instead of hardcoded logic
            if self._use_ml_prediction:
                task_info = await self._ml_extract_task_info(task_plan)
                historical_performance = await self._ml_analyze_historical_performance(
                    recent_usage, recent_sessions, task_info
                )
                user_capability = await self._ml_assess_user_capability(
                    user, recent_usage, recent_sessions, task_info
                )
                risk_factors = await self._ml_identify_risk_factors(task_info, user_capability, recent_usage)
                success_probability = await self._ml_calculate_success_probability(
                    task_info, historical_performance, user_capability, risk_factors
                )
                optimizations = await self._ml_generate_optimizations(
                    task_info, risk_factors, user_capability, historical_performance
                )
            else:
                # Fallback to hardcoded analysis
                task_info = self._extract_task_info(task_plan)
                historical_performance = self._analyze_historical_performance(
                    recent_usage, recent_sessions, task_info
                )
                user_capability = self._assess_user_capability(
                    user, recent_usage, recent_sessions, task_info
                )
                risk_factors = self._identify_risk_factors(task_info, user_capability, recent_usage)
                success_probability = self._calculate_success_probability(
                    task_info, historical_performance, user_capability, risk_factors
                )
                optimizations = self._generate_optimizations(
                    task_info, risk_factors, user_capability, historical_performance
                )
            
            # Find similar past tasks
            similar_tasks = self._find_similar_tasks(recent_usage, recent_sessions, task_info)
            
            # Identify resource conflicts
            resource_conflicts = self._identify_resource_conflicts(task_info, user_capability)
            
            # Analyze timing considerations
            timing_considerations = self._analyze_timing_considerations(
                task_info, recent_usage, user_capability
            )
            
            # Calculate confidence in prediction
            confidence = self._calculate_confidence(
                historical_performance, user_capability, len(recent_usage), task_info
            )
            
            return TaskOutcomePrediction(
                user_id=user_id,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                task_description=task_info["description"],
                success_probability=success_probability,
                risk_factors=risk_factors,
                optimization_suggestions=optimizations,
                similar_past_tasks=similar_tasks,
                resource_conflicts=resource_conflicts,
                timing_considerations=timing_considerations,
                metadata={
                    "prediction_date": datetime.utcnow(),
                    "task_complexity": task_info.get("complexity", "medium"),
                    "historical_data_points": len(recent_usage),
                    "user_experience_level": user_capability.get("experience_level", "intermediate"),
                    "risk_factor_count": len(risk_factors)
                }
            )
            
        except Exception as e:
            logger.error(f"Error predicting task outcomes for user {user_id}: {e}")
            raise
    
    def _extract_task_info(self, task_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and categorize task information"""
        # Handle different task plan formats
        task_description = ""
        tools_needed = []
        parameters = {}
        
        if isinstance(task_plan, dict):
            task_description = (
                task_plan.get("description", "") or 
                task_plan.get("task", "") or 
                task_plan.get("query", "") or
                str(task_plan)
            )
            tools_needed = task_plan.get("tools", []) or task_plan.get("required_tools", [])
            parameters = task_plan.get("parameters", {}) or task_plan.get("config", {})
        else:
            task_description = str(task_plan)
        
        # Categorize task complexity
        complexity = self._categorize_task_complexity(task_description, tools_needed)
        
        # Extract task type
        task_type = self._identify_task_type(task_description, tools_needed)
        
        return {
            "description": task_description,
            "tools_needed": tools_needed,
            "parameters": parameters,
            "complexity": complexity,
            "task_type": task_type,
            "estimated_duration": self._estimate_task_duration(complexity, task_type),
            "resource_requirements": self._estimate_resource_requirements(complexity, tools_needed)
        }
    
    def _categorize_task_complexity(self, description: str, tools: List[str]) -> str:
        """Categorize task complexity based on description and tools"""
        desc_lower = description.lower()
        
        # Check for simple task indicators
        simple_indicators = self.task_complexity["simple"]
        if any(indicator in desc_lower for indicator in simple_indicators):
            return "simple"
        
        # Check for complex task indicators
        complex_indicators = self.task_complexity["complex"]
        if any(indicator in desc_lower for indicator in complex_indicators):
            return "complex"
        
        # Check tool complexity
        if len(tools) > 3:
            return "complex"
        elif len(tools) == 0:
            return "simple"
        
        # Default to medium
        return "medium"
    
    def _identify_task_type(self, description: str, tools: List[str]) -> str:
        """Identify the type of task being performed"""
        desc_lower = description.lower()
        
        # Task type indicators
        type_indicators = {
            "analysis": ["analyze", "data", "statistics", "insights", "metrics"],
            "generation": ["generate", "create", "write", "build", "compose"],
            "processing": ["process", "transform", "convert", "format", "parse"],
            "search": ["search", "find", "lookup", "query", "retrieve"],
            "communication": ["chat", "discuss", "explain", "clarify", "respond"],
            "automation": ["automate", "batch", "bulk", "schedule", "workflow"]
        }
        
        for task_type, indicators in type_indicators.items():
            if any(indicator in desc_lower for indicator in indicators):
                return task_type
        
        return "general"
    
    def _estimate_task_duration(self, complexity: str, task_type: str) -> int:
        """Estimate task duration in minutes"""
        base_durations = {
            "simple": 5,
            "medium": 15,
            "complex": 45
        }
        
        type_multipliers = {
            "analysis": 1.5,
            "generation": 1.2,
            "processing": 1.3,
            "search": 0.8,
            "communication": 0.6,
            "automation": 2.0,
            "general": 1.0
        }
        
        base = base_durations.get(complexity, 15)
        multiplier = type_multipliers.get(task_type, 1.0)
        
        return int(base * multiplier)
    
    def _estimate_resource_requirements(self, complexity: str, tools: List[str]) -> Dict[str, str]:
        """Estimate resource requirements for the task"""
        requirements = {
            "cpu": "low",
            "memory": "low", 
            "network": "optional",
            "storage": "minimal"
        }
        
        # Adjust based on complexity
        if complexity == "complex":
            requirements["cpu"] = "high"
            requirements["memory"] = "medium"
        elif complexity == "medium":
            requirements["cpu"] = "medium"
        
        # Adjust based on tools
        resource_intensive_tools = [
            "data_analyzer", "model_trainer", "bulk_processor", "image_processor"
        ]
        
        network_tools = [
            "web_scraper", "api_client", "external_service", "real_time_data"
        ]
        
        if any(tool in resource_intensive_tools for tool in tools):
            requirements["cpu"] = "high"
            requirements["memory"] = "high"
        
        if any(tool in network_tools for tool in tools):
            requirements["network"] = "required"
        
        if len(tools) > 5:
            requirements["storage"] = "medium"
        
        return requirements
    
    def _analyze_historical_performance(
        self, 
        usage_records: List[Dict[str, Any]],
        sessions: List[Dict[str, Any]], 
        task_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze historical performance for similar tasks"""
        performance = {
            "overall_success_rate": 0.0,
            "similar_task_success_rate": 0.0,
            "avg_completion_time": 0.0,
            "common_failure_modes": [],
            "performance_trend": "stable"
        }
        
        if not usage_records:
            return performance
        
        # Calculate overall success rate
        successful_records = sum(
            1 for record in usage_records
            if record.get('response_data', {}).get('success', True)
        )
        performance["overall_success_rate"] = successful_records / len(usage_records)
        
        # Find similar tasks based on task type and tools
        similar_records = []
        task_type = task_info.get("task_type", "general")
        tools_needed = task_info.get("tools_needed", [])
        
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            
            # Check if record relates to similar task
            if (task_type in endpoint or 
                task_type in tool_name or
                any(tool.lower() in tool_name for tool in tools_needed)):
                similar_records.append(record)
        
        # Analyze similar tasks
        if similar_records:
            similar_success = sum(
                1 for record in similar_records
                if record.get('response_data', {}).get('success', True)
            )
            performance["similar_task_success_rate"] = similar_success / len(similar_records)
            
            # Average completion time (estimated from token usage)
            avg_tokens = sum(record.get('tokens_used', 0) for record in similar_records) / len(similar_records)
            # Rough heuristic: 100 tokens ≈ 1 minute
            performance["avg_completion_time"] = avg_tokens / 100.0
        
        # Identify common failure modes
        failed_records = [
            record for record in usage_records
            if not record.get('response_data', {}).get('success', True)
        ]
        
        failure_patterns = {}
        for record in failed_records:
            response_data = record.get('response_data', {})
            error_info = response_data.get('error', 'unknown_error')
            
            if isinstance(error_info, str):
                if 'timeout' in error_info.lower():
                    failure_patterns['timeout'] = failure_patterns.get('timeout', 0) + 1
                elif 'rate' in error_info.lower() and 'limit' in error_info.lower():
                    failure_patterns['rate_limit'] = failure_patterns.get('rate_limit', 0) + 1
                elif 'permission' in error_info.lower():
                    failure_patterns['permission'] = failure_patterns.get('permission', 0) + 1
                else:
                    failure_patterns['other'] = failure_patterns.get('other', 0) + 1
        
        # Get top failure modes
        performance["common_failure_modes"] = [
            mode for mode, count in sorted(failure_patterns.items(), key=lambda x: x[1], reverse=True)[:3]
        ]
        
        # Analyze performance trend (simplified)
        if len(usage_records) >= 10:
            # Compare first half vs second half success rates
            mid_point = len(usage_records) // 2
            first_half_success = sum(
                1 for record in usage_records[:mid_point]
                if record.get('response_data', {}).get('success', True)
            ) / mid_point
            
            second_half_success = sum(
                1 for record in usage_records[mid_point:]
                if record.get('response_data', {}).get('success', True)
            ) / (len(usage_records) - mid_point)
            
            if second_half_success > first_half_success * 1.1:
                performance["performance_trend"] = "improving"
            elif second_half_success < first_half_success * 0.9:
                performance["performance_trend"] = "declining"
        
        return performance
    
    def _assess_user_capability(
        self,
        user: Any,
        usage_records: List[Dict[str, Any]],
        sessions: List[Dict[str, Any]],
        task_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess user's capability for this specific task"""
        capability = {
            "experience_level": "intermediate",
            "domain_expertise": 0.5,
            "tool_familiarity": 0.5,
            "recent_activity_level": "moderate",
            "success_pattern": "consistent"
        }
        
        # Assess experience level based on account age and usage
        if user and user.created_at:
            try:
                if isinstance(user.created_at, str):
                    created_date = datetime.fromisoformat(user.created_at.replace('Z', '+00:00'))
                else:
                    created_date = user.created_at
                
                account_age_days = (datetime.utcnow() - created_date).days
                total_usage = len(usage_records)
                
                if account_age_days > 180 and total_usage > 100:
                    capability["experience_level"] = "expert"
                elif account_age_days > 60 and total_usage > 30:
                    capability["experience_level"] = "advanced"
                elif account_age_days < 14 or total_usage < 10:
                    capability["experience_level"] = "beginner"
            except:
                pass
        
        # Assess domain expertise based on task type usage
        task_type = task_info.get("task_type", "general")
        domain_usage = sum(
            1 for record in usage_records
            if task_type in record.get('endpoint', '').lower() or
               task_type in record.get('tool_name', '').lower()
        )
        
        if usage_records:
            domain_ratio = domain_usage / len(usage_records)
            capability["domain_expertise"] = min(1.0, domain_ratio * 2)  # Scale to 0-1
        
        # Assess tool familiarity
        tools_needed = task_info.get("tools_needed", [])
        if tools_needed:
            familiar_tools = 0
            for tool in tools_needed:
                tool_usage = sum(
                    1 for record in usage_records
                    if tool.lower() in record.get('tool_name', '').lower()
                )
                if tool_usage > 0:
                    familiar_tools += 1
            
            capability["tool_familiarity"] = familiar_tools / len(tools_needed)
        
        # Assess recent activity level
        recent_records = [
            record for record in usage_records
            if record.get('created_at')
        ]
        
        if recent_records:
            # Check activity in last 7 days
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            very_recent = [
                record for record in recent_records
                if datetime.fromisoformat(record['created_at'].replace('Z', '+00:00')) > recent_cutoff
            ]
            
            recent_activity_ratio = len(very_recent) / len(recent_records)
            
            if recent_activity_ratio > 0.3:
                capability["recent_activity_level"] = "high"
            elif recent_activity_ratio < 0.1:
                capability["recent_activity_level"] = "low"
        
        # Assess success pattern consistency
        if len(usage_records) >= 5:
            # Calculate success rate variance across time windows
            success_rates = []
            window_size = max(5, len(usage_records) // 4)
            
            for i in range(0, len(usage_records), window_size):
                window = usage_records[i:i+window_size]
                if window:
                    successes = sum(
                        1 for record in window
                        if record.get('response_data', {}).get('success', True)
                    )
                    success_rates.append(successes / len(window))
            
            if success_rates:
                avg_rate = sum(success_rates) / len(success_rates)
                variance = sum((rate - avg_rate) ** 2 for rate in success_rates) / len(success_rates)
                
                if variance < 0.05:
                    capability["success_pattern"] = "very_consistent"
                elif variance < 0.1:
                    capability["success_pattern"] = "consistent"
                else:
                    capability["success_pattern"] = "variable"
        
        return capability
    
    def _identify_risk_factors(
        self,
        task_info: Dict[str, Any],
        user_capability: Dict[str, Any],
        usage_records: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify potential risk factors for task failure"""
        risks = []
        
        # Complexity-based risks
        complexity = task_info.get("complexity", "medium")
        if complexity == "complex":
            risks.append("high_task_complexity")
        
        # User capability risks
        experience = user_capability.get("experience_level", "intermediate")
        if experience == "beginner" and complexity in ["medium", "complex"]:
            risks.append("insufficient_user_experience")
        
        # Tool familiarity risks
        tool_familiarity = user_capability.get("tool_familiarity", 0.5)
        if tool_familiarity < 0.3:
            risks.append("unfamiliar_tools_required")
        
        # Domain expertise risks
        domain_expertise = user_capability.get("domain_expertise", 0.5)
        if domain_expertise < 0.2 and complexity != "simple":
            risks.append("limited_domain_expertise")
        
        # Resource requirement risks
        resource_reqs = task_info.get("resource_requirements", {})
        if resource_reqs.get("cpu") == "high" or resource_reqs.get("memory") == "high":
            risks.append("high_resource_requirements")
        
        if resource_reqs.get("network") == "required":
            risks.append("network_dependency")
        
        # Historical failure pattern risks
        if usage_records:
            recent_failures = [
                record for record in usage_records[-10:]  # Last 10 records
                if not record.get('response_data', {}).get('success', True)
            ]
            
            if len(recent_failures) > 3:  # More than 30% recent failure rate
                risks.append("recent_performance_decline")
        
        # Task type specific risks
        task_type = task_info.get("task_type", "general")
        type_risks = {
            "automation": ["workflow_complexity", "integration_dependencies"],
            "analysis": ["data_quality_dependency", "computational_intensity"],
            "processing": ["format_compatibility", "data_volume_limits"],
            "generation": ["quality_consistency", "creativity_requirements"]
        }
        
        if task_type in type_risks:
            risks.extend(type_risks[task_type][:1])  # Add primary risk for task type
        
        # Timing risks
        estimated_duration = task_info.get("estimated_duration", 15)
        if estimated_duration > 60:  # Tasks over 1 hour
            risks.append("extended_duration_risk")
        
        return risks
    
    def _calculate_success_probability(
        self,
        task_info: Dict[str, Any],
        historical_performance: Dict[str, Any],
        user_capability: Dict[str, Any],
        risk_factors: List[str]
    ) -> float:
        """Calculate overall success probability"""
        # Start with base probability based on task complexity
        complexity = task_info.get("complexity", "medium")
        base_probabilities = {
            "simple": 0.85,
            "medium": 0.70,
            "complex": 0.55
        }
        
        probability = base_probabilities.get(complexity, 0.70)
        
        # Adjust based on historical performance
        historical_success = historical_performance.get("similar_task_success_rate", 0.0)
        if historical_success > 0:
            # Weight historical data more heavily if we have good data
            probability = (probability * 0.4) + (historical_success * 0.6)
        else:
            overall_success = historical_performance.get("overall_success_rate", 0.0)
            if overall_success > 0:
                probability = (probability * 0.7) + (overall_success * 0.3)
        
        # Adjust based on user capability
        experience_adjustments = {
            "beginner": -0.15,
            "intermediate": 0.0,
            "advanced": +0.10,
            "expert": +0.15
        }
        
        experience = user_capability.get("experience_level", "intermediate")
        probability += experience_adjustments.get(experience, 0.0)
        
        # Adjust based on domain expertise and tool familiarity
        domain_expertise = user_capability.get("domain_expertise", 0.5)
        tool_familiarity = user_capability.get("tool_familiarity", 0.5)
        
        # Boost probability based on expertise (max +0.15)
        probability += (domain_expertise - 0.5) * 0.15
        probability += (tool_familiarity - 0.5) * 0.15
        
        # Apply risk factor penalties
        risk_penalties = {
            "high_task_complexity": -0.10,
            "insufficient_user_experience": -0.15,
            "unfamiliar_tools_required": -0.12,
            "limited_domain_expertise": -0.08,
            "high_resource_requirements": -0.05,
            "network_dependency": -0.03,
            "recent_performance_decline": -0.10,
            "extended_duration_risk": -0.05
        }
        
        for risk in risk_factors:
            penalty = risk_penalties.get(risk, -0.02)  # Default small penalty
            probability += penalty
        
        # Performance trend adjustment
        trend = historical_performance.get("performance_trend", "stable")
        if trend == "improving":
            probability += 0.05
        elif trend == "declining":
            probability -= 0.05
        
        # Ensure probability stays within bounds
        return max(0.1, min(0.95, probability))
    
    def _generate_optimizations(
        self,
        task_info: Dict[str, Any],
        risk_factors: List[str],
        user_capability: Dict[str, Any],
        historical_performance: Dict[str, Any]
    ) -> List[str]:
        """Generate optimization suggestions to improve success probability"""
        optimizations = []
        
        # Risk-specific optimizations
        risk_optimizations = {
            "high_task_complexity": [
                "break_task_into_smaller_steps",
                "use_simplified_approach",
                "enable_step_by_step_guidance"
            ],
            "insufficient_user_experience": [
                "provide_detailed_instructions",
                "enable_tutorial_mode",
                "suggest_practice_tasks_first"
            ],
            "unfamiliar_tools_required": [
                "provide_tool_documentation",
                "suggest_alternative_familiar_tools",
                "enable_guided_tool_selection"
            ],
            "limited_domain_expertise": [
                "provide_domain_context",
                "suggest_background_reading",
                "enable_expert_consultation"
            ],
            "high_resource_requirements": [
                "optimize_resource_usage",
                "use_batch_processing",
                "schedule_during_low_usage_periods"
            ],
            "network_dependency": [
                "check_network_connectivity",
                "enable_offline_fallbacks",
                "use_cached_data_when_possible"
            ],
            "recent_performance_decline": [
                "review_recent_errors",
                "suggest_simpler_alternatives",
                "enable_enhanced_error_handling"
            ],
            "extended_duration_risk": [
                "enable_progress_checkpoints",
                "implement_resume_functionality",
                "break_into_shorter_sessions"
            ]
        }
        
        for risk in risk_factors:
            if risk in risk_optimizations:
                optimizations.extend(risk_optimizations[risk][:2])  # Top 2 optimizations per risk
        
        # General optimizations based on task type
        task_type = task_info.get("task_type", "general")
        type_optimizations = {
            "analysis": ["validate_data_quality", "use_sample_data_first", "enable_interactive_exploration"],
            "generation": ["provide_clear_requirements", "enable_iterative_refinement", "use_templates"],
            "processing": ["validate_input_format", "enable_progress_tracking", "implement_error_recovery"],
            "automation": ["test_with_small_batch", "enable_rollback_capability", "monitor_execution"],
            "search": ["use_specific_keywords", "enable_result_filtering", "try_multiple_sources"]
        }
        
        if task_type in type_optimizations:
            optimizations.extend(type_optimizations[task_type][:2])
        
        # Experience-based optimizations
        experience = user_capability.get("experience_level", "intermediate")
        if experience == "beginner":
            optimizations.extend([
                "enable_beginner_mode",
                "provide_step_by_step_guidance",
                "show_explanatory_tooltips"
            ])
        elif experience == "expert":
            optimizations.extend([
                "enable_advanced_options",
                "use_bulk_operations",
                "enable_custom_configurations"
            ])
        
        # Historical performance optimizations
        common_failures = historical_performance.get("common_failure_modes", [])
        if "timeout" in common_failures:
            optimizations.append("increase_timeout_limits")
        if "rate_limit" in common_failures:
            optimizations.append("implement_request_throttling")
        if "permission" in common_failures:
            optimizations.append("verify_access_permissions")
        
        # Remove duplicates and return top optimizations
        unique_optimizations = list(dict.fromkeys(optimizations))  # Preserves order
        return unique_optimizations[:8]  # Top 8 optimizations
    
    def _find_similar_tasks(
        self,
        usage_records: List[Dict[str, Any]],
        sessions: List[Dict[str, Any]],
        task_info: Dict[str, Any]
    ) -> List[str]:
        """Find similar past tasks for reference"""
        similar_tasks = []
        
        task_type = task_info.get("task_type", "general")
        tools_needed = task_info.get("tools_needed", [])
        
        # Find similar usage records
        for record in usage_records[-20:]:  # Recent records
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            
            similarity_score = 0
            
            # Task type similarity
            if task_type in endpoint or task_type in tool_name:
                similarity_score += 2
            
            # Tool similarity
            for tool in tools_needed:
                if tool.lower() in tool_name:
                    similarity_score += 1
            
            if similarity_score >= 1:
                task_id = f"usage_{record.get('id', 'unknown')}"
                similar_tasks.append(task_id)
        
        # Find similar sessions
        for session in sessions[-10:]:  # Recent sessions
            conv_data = session.get('conversation_data', {})
            searchable_text = str(conv_data).lower()
            
            if task_type in searchable_text:
                session_id = session.get('session_id', f"session_{session.get('id', 'unknown')}")
                similar_tasks.append(session_id)
        
        return similar_tasks[:5]  # Top 5 similar tasks
    
    def _identify_resource_conflicts(
        self, 
        task_info: Dict[str, Any], 
        user_capability: Dict[str, Any]
    ) -> List[str]:
        """Identify potential resource conflicts"""
        conflicts = []
        
        resource_reqs = task_info.get("resource_requirements", {})
        
        # Check for high resource requirements
        if resource_reqs.get("cpu") == "high":
            conflicts.append("high_cpu_usage_may_affect_performance")
        
        if resource_reqs.get("memory") == "high":
            conflicts.append("high_memory_usage_may_cause_slowdowns")
        
        # Check for network requirements
        if resource_reqs.get("network") == "required":
            conflicts.append("network_connectivity_required")
        
        # Check for duration conflicts
        estimated_duration = task_info.get("estimated_duration", 15)
        activity_level = user_capability.get("recent_activity_level", "moderate")
        
        if estimated_duration > 30 and activity_level == "low":
            conflicts.append("long_task_duration_vs_low_recent_activity")
        
        # Check for complexity vs experience conflicts
        complexity = task_info.get("complexity", "medium")
        experience = user_capability.get("experience_level", "intermediate")
        
        if complexity == "complex" and experience == "beginner":
            conflicts.append("task_complexity_exceeds_user_experience")
        
        return conflicts
    
    def _analyze_timing_considerations(
        self,
        task_info: Dict[str, Any],
        usage_records: List[Dict[str, Any]],
        user_capability: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze timing considerations for task execution"""
        considerations = {
            "best_execution_time": "anytime",
            "estimated_duration_minutes": task_info.get("estimated_duration", 15),
            "peak_performance_hours": [],
            "avoid_times": [],
            "time_flexibility": "flexible"
        }
        
        # Analyze user's peak performance times from historical data
        if usage_records:
            hour_success_rates = {}
            hour_counts = defaultdict(int)
            hour_successes = defaultdict(int)
            
            for record in usage_records:
                created_at = record.get('created_at')
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            dt = created_at
                        
                        hour = dt.hour
                        hour_counts[hour] += 1
                        
                        if record.get('response_data', {}).get('success', True):
                            hour_successes[hour] += 1
                    except:
                        pass
            
            # Calculate success rates by hour
            for hour in hour_counts:
                if hour_counts[hour] >= 3:  # Need at least 3 data points
                    success_rate = hour_successes[hour] / hour_counts[hour]
                    hour_success_rates[hour] = success_rate
            
            if hour_success_rates:
                # Find peak performance hours (above average success rate)
                avg_success = sum(hour_success_rates.values()) / len(hour_success_rates)
                peak_hours = [
                    hour for hour, rate in hour_success_rates.items()
                    if rate > avg_success * 1.1
                ]
                considerations["peak_performance_hours"] = sorted(peak_hours)
                
                # Find hours to avoid (below average success rate)
                avoid_hours = [
                    hour for hour, rate in hour_success_rates.items()
                    if rate < avg_success * 0.8 and hour_counts[hour] >= 3
                ]
                considerations["avoid_times"] = sorted(avoid_hours)
        
        # Determine best execution time based on task characteristics
        complexity = task_info.get("complexity", "medium")
        if complexity == "complex":
            considerations["best_execution_time"] = "during_peak_hours"
            considerations["time_flexibility"] = "limited"
        elif complexity == "simple":
            considerations["time_flexibility"] = "very_flexible"
        
        # Consider resource requirements
        resource_reqs = task_info.get("resource_requirements", {})
        if resource_reqs.get("cpu") == "high" or resource_reqs.get("memory") == "high":
            considerations["best_execution_time"] = "off_peak_hours"
        
        return considerations
    
    def _calculate_confidence(
        self,
        historical_performance: Dict[str, Any],
        user_capability: Dict[str, Any],
        usage_data_points: int,
        task_info: Dict[str, Any]
    ) -> float:
        """Calculate confidence in the prediction"""
        base_confidence = 0.5
        
        # Historical data quality factor
        similar_success_rate = historical_performance.get("similar_task_success_rate", 0.0)
        if similar_success_rate > 0:
            base_confidence += 0.2  # We have specific similar task data
        elif historical_performance.get("overall_success_rate", 0.0) > 0:
            base_confidence += 0.1  # We have general performance data
        
        # Data quantity factor
        if usage_data_points >= 50:
            base_confidence += 0.15
        elif usage_data_points >= 20:
            base_confidence += 0.1
        elif usage_data_points < 5:
            base_confidence -= 0.2
        
        # User capability assessment confidence
        experience = user_capability.get("experience_level", "intermediate")
        success_pattern = user_capability.get("success_pattern", "consistent")
        
        if success_pattern in ["very_consistent", "consistent"]:
            base_confidence += 0.1
        elif success_pattern == "variable":
            base_confidence -= 0.05
        
        # Task specificity factor
        complexity = task_info.get("complexity", "medium")
        if complexity in ["simple", "complex"]:  # Extreme cases are more predictable
            base_confidence += 0.05
        
        # Tool familiarity factor
        tool_familiarity = user_capability.get("tool_familiarity", 0.5)
        if tool_familiarity > 0.7:
            base_confidence += 0.1
        elif tool_familiarity < 0.3:
            base_confidence -= 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    def _get_confidence_level(self, confidence: float) -> PredictionConfidenceLevel:
        """Convert confidence score to confidence level"""
        if confidence >= 0.8:
            return PredictionConfidenceLevel.VERY_HIGH
        elif confidence >= 0.6:
            return PredictionConfidenceLevel.HIGH
        elif confidence >= 0.3:
            return PredictionConfidenceLevel.MEDIUM
        else:
            return PredictionConfidenceLevel.LOW
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for task outcome predictor"""
        try:
            # Test repository connectivity
            test_result = await self.usage_repo.get_user_usage_history("test", limit=1)
            
            return {
                "status": "healthy",
                "component": "task_outcome_predictor",
                "last_check": datetime.utcnow(),
                "repositories": {
                    "usage_repo": "connected",
                    "session_repo": "connected",
                    "user_repo": "connected"
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "task_outcome_predictor",
                "error": str(e),
                "last_check": datetime.utcnow()
            }

    # ============ AI-powered Methods (替换硬编码逻辑) ============
    
    async def _ml_extract_task_info(self, task_plan: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI分析任务信息而不是硬编码解析"""
        try:
            # 使用推理生成器分析任务复杂度和特征
            analysis_prompt = f"""
            Analyze this task plan and extract key information:
            {json.dumps(task_plan, indent=2)}
            
            Provide analysis in JSON format:
            {{
                "task_type": "analysis/processing/integration/automation/etc",
                "complexity_level": "low/medium/high/very_high",
                "estimated_duration": "in_minutes",
                "resource_requirements": {{
                    "cpu_intensive": true/false,
                    "memory_intensive": true/false,
                    "io_intensive": true/false,
                    "network_dependent": true/false
                }},
                "risk_indicators": ["risk1", "risk2"],
                "dependencies": ["dep1", "dep2"],
                "success_factors": ["factor1", "factor2"]
            }}
            """
            
            reasoning_result = await self.reasoning_generator.generate_reasoning({
                'prompt': analysis_prompt,
                'reasoning_type': 'task_analysis',
                'output_format': 'json'
            })
            
            return reasoning_result.get('task_info', {
                "task_type": "general",
                "complexity_level": "medium",
                "estimated_duration": 30
            })
            
        except Exception as e:
            logger.error(f"ML task info extraction failed: {e}")
            return {"task_type": "general", "complexity_level": "medium"}
    
    async def _ml_analyze_historical_performance(self, recent_usage: List[Dict], 
                                               recent_sessions: List[Dict], task_info: Dict) -> Dict[str, Any]:
        """使用ML分析历史表现而不是简单统计"""
        try:
            # 使用DataAnalytics分析用户历史表现模式
            performance_data = {
                'usage_history': recent_usage,
                'session_history': recent_sessions,
                'task_context': task_info
            }
            
            performance_analysis = await self.data_analytics.analyze_user_success_patterns(performance_data)
            
            return performance_analysis.get('historical_performance', {
                "overall_success_rate": 0.75,
                "similar_task_success_rate": 0.70,
                "recent_trend": "stable",
                "failure_patterns": []
            })
            
        except Exception as e:
            logger.error(f"ML historical performance analysis failed: {e}")
            return {"overall_success_rate": 0.70, "recent_trend": "stable"}
    
    async def _ml_assess_user_capability(self, user: Dict, recent_usage: List[Dict], 
                                        recent_sessions: List[Dict], task_info: Dict) -> Dict[str, Any]:
        """使用AI评估用户能力而不是硬编码规则"""
        try:
            # 使用ML处理器评估用户能力
            capability_input = {
                'user_profile': user,
                'recent_activities': recent_usage,
                'session_patterns': recent_sessions,
                'target_task': task_info
            }
            
            # Ensure ML processor is initialized
            await self._ensure_ml_processor()
            
            capability_assessment = await self.ml_processor.assess_user_capability(capability_input)
            
            return capability_assessment.get('capability_scores', {
                "technical_proficiency": 0.7,
                "domain_expertise": 0.6,
                "tool_familiarity": 0.8,
                "task_specific_experience": 0.5
            })
            
        except Exception as e:
            logger.error(f"ML user capability assessment failed: {e}")
            return {"technical_proficiency": 0.6, "tool_familiarity": 0.7}
    
    async def _ml_identify_risk_factors(self, task_info: Dict, user_capability: Dict, 
                                       recent_usage: List[Dict]) -> List[str]:
        """使用AI识别风险因子而不是硬编码列表"""
        try:
            risk_analysis_prompt = f"""
            Identify potential risk factors for task completion:
            Task Info: {json.dumps(task_info)}
            User Capability: {json.dumps(user_capability)}
            Recent Usage Pattern: {len(recent_usage)} recent activities
            
            Return a JSON array of specific risk factors that could cause task failure.
            Focus on realistic, actionable risks.
            """
            
            reasoning_result = await self.reasoning_generator.generate_reasoning({
                'prompt': risk_analysis_prompt,
                'reasoning_type': 'risk_assessment',
                'output_format': 'json_array'
            })
            
            identified_risks = reasoning_result.get('risk_factors', [])
            
            # 使用DataAnalytics验证和增强风险分析
            if identified_risks:
                risk_validation = await self.data_analytics.validate_risk_factors({
                    'identified_risks': identified_risks,
                    'user_context': user_capability,
                    'task_context': task_info
                })
                
                validated_risks = risk_validation.get('validated_risks', identified_risks)
                return validated_risks
            
            return identified_risks
            
        except Exception as e:
            logger.error(f"ML risk factor identification failed: {e}")
            return ["complexity_mismatch", "resource_constraints"]
    
    async def _ml_calculate_success_probability(self, task_info: Dict, historical_performance: Dict,
                                               user_capability: Dict, risk_factors: List[str]) -> float:
        """使用ML计算成功概率而不是硬编码公式"""
        try:
            # 使用ML模型预测成功概率
            prediction_input = {
                'task_features': task_info,
                'user_performance_history': historical_performance,
                'user_capabilities': user_capability,
                'identified_risks': risk_factors
            }
            
            # Ensure ML processor is initialized
            await self._ensure_ml_processor()
            
            success_prediction = await self.ml_processor.predict_task_success_probability(prediction_input)
            
            predicted_probability = success_prediction.get('success_probability', 0.7)
            
            # 确保概率在合理范围内
            return max(0.1, min(0.95, predicted_probability))
            
        except Exception as e:
            logger.error(f"ML success probability calculation failed: {e}")
            # 回退到简化计算
            return self._fallback_success_calculation(historical_performance, user_capability, risk_factors)
    
    async def _ml_generate_optimizations(self, task_info: Dict, risk_factors: List[str],
                                        user_capability: Dict, historical_performance: Dict) -> List[str]:
        """使用AI生成优化建议而不是模板建议"""
        try:
            optimization_prompt = f"""
            Generate specific optimization suggestions for this task:
            Task: {json.dumps(task_info)}
            Risks: {risk_factors}
            User Capability: {json.dumps(user_capability)}
            Historical Performance: {json.dumps(historical_performance)}
            
            Provide 3-5 actionable optimization suggestions to improve success probability.
            Return as JSON array of strings.
            """
            
            reasoning_result = await self.reasoning_generator.generate_reasoning({
                'prompt': optimization_prompt,
                'reasoning_type': 'optimization_suggestions',
                'output_format': 'json_array'
            })
            
            optimizations = reasoning_result.get('optimizations', [])
            
            # 使用DataAnalytics验证优化建议的有效性
            if optimizations:
                optimization_validation = await self.data_analytics.validate_optimization_suggestions({
                    'suggestions': optimizations,
                    'task_context': task_info,
                    'user_context': user_capability
                })
                
                return optimization_validation.get('validated_suggestions', optimizations)
            
            return optimizations
            
        except Exception as e:
            logger.error(f"ML optimization generation failed: {e}")
            return ["Break task into smaller steps", "Prepare required resources", "Review similar past tasks"]
    
    def _fallback_success_calculation(self, historical_performance: Dict, 
                                     user_capability: Dict, risk_factors: List[str]) -> float:
        """ML失败时的回退成功率计算"""
        base_probability = historical_performance.get('overall_success_rate', 0.7)
        
        # 基于用户能力调整
        capability_avg = sum(user_capability.values()) / len(user_capability) if user_capability else 0.6
        capability_factor = (capability_avg - 0.5) * 0.2
        
        # 基于风险因子调整
        risk_penalty = len(risk_factors) * 0.05
        
        adjusted_probability = base_probability + capability_factor - risk_penalty
        
        return max(0.2, min(0.9, adjusted_probability))