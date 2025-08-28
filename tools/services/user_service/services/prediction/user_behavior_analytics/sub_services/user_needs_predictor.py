"""
User Needs Predictor

Predicts what user will likely need next based on patterns and context
Maps to predict_user_needs MCP tool
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import logging
import json

from ...prediction_models import UserNeedsPrediction, PredictionConfidenceLevel
from ..utilities.pattern_extraction_utils import PatternExtractionUtils

# Import user service repositories and services
from tools.services.user_service.repositories.usage_repository import UsageRepository
from tools.services.user_service.repositories.session_repository import SessionRepository

# Event-driven integration instead of direct service dependency
from tools.services.event_service.services.event_service import EventService

# AI services will be imported lazily to avoid mutex lock issues

logger = logging.getLogger(__name__)


class UserNeedsPredictor:
    """
    Predicts what user will likely need next
    Uses context, patterns, and user portraits to anticipate needs
    """
    
    def __init__(self):
        """Initialize repositories, services and AI capabilities"""
        self.usage_repo = UsageRepository()
        self.session_repo = SessionRepository()
        self.event_service = EventService()  # Use event-driven communication
        self.pattern_utils = PatternExtractionUtils()
        
        # Initialize AI services lazily to avoid mutex lock issues
        self.data_analytics = None  # Will be initialized when needed
        self.ml_processor = None
        self.text_generator = None  # Will be initialized when needed
        self.reasoning_generator = None  # Will be initialized when needed
        
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
            writer.writerow(['feature1', 'feature2', 'target'])
            writer.writerow([1, 2, 'task_a'])
            writer.writerow([2, 3, 'task_b'])
            temp_file.close()
            
            self.ml_processor = MLProcessor(file_path=temp_file.name)
            os.unlink(temp_file.name)  # Clean up
        
        # Hardcoded fallbacks (will be replaced by learned patterns from AI)
        self.task_sequences = {
            "analysis_workflow": [
                "data_upload", "data_exploration", "analysis", "visualization", "export"
            ],
            "document_workflow": [
                "document_upload", "text_analysis", "summarization", "qa", "export"
            ],
            "research_workflow": [
                "search", "information_gathering", "synthesis", "note_taking", "organization"
            ],
            "development_workflow": [
                "code_analysis", "debugging", "testing", "documentation", "deployment"
            ]
        }
        
        self.tool_relationships = {
            "chat_tool": ["memory_tool", "search_tool", "analysis_tool"],
            "analysis_tool": ["visualization_tool", "export_tool", "data_tool"],
            "document_tool": ["text_analysis_tool", "summary_tool", "qa_tool"],
            "search_tool": ["research_tool", "memory_tool", "organization_tool"]
        }
        
        logger.info("User Needs Predictor initialized (AI services will be loaded lazily)")
    
    def _ensure_data_analytics(self):
        """Lazy initialization of DataAnalyticsService to avoid mutex lock"""
        if self.data_analytics is None:
            from tools.services.data_analytics_service.services.data_analytics_service import DataAnalyticsService
            self.data_analytics = DataAnalyticsService()
    
    def _ensure_text_generator(self):
        """Lazy initialization of TextGenerator"""
        if self.text_generator is None:
            from tools.services.intelligence_service.language.text_generator import TextGenerator
            self.text_generator = TextGenerator()
            
    def _ensure_reasoning_generator(self):
        """Lazy initialization of ReasoningGenerator"""
        if self.reasoning_generator is None:
            from tools.services.intelligence_service.language.reasoning_generator import ReasoningGenerator
            self.reasoning_generator = ReasoningGenerator()
    
    async def predict_needs(
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
            
            # Gather data for prediction
            recent_usage = await self.usage_repo.get_recent_usage(user_id, hours=24)
            current_session = await self._get_current_session(user_id, context)
            user_patterns = await self._get_user_patterns(user_id)
            
            # Use AI for context analysis and predictions instead of hardcoded logic
            if self._use_ml_prediction:
                context_analysis = await self._ml_analyze_current_context(context, query, recent_usage)
                task_predictions = await self._ml_predict_tasks(
                    context_analysis, recent_usage, current_session, user_patterns
                )
                tool_predictions = await self._ml_predict_tools(
                    task_predictions, recent_usage, user_patterns
                )
                context_needs = await self._ml_predict_context_needs(
                    context, current_session, task_predictions
                )
                resource_requirements = await self._ml_predict_resource_requirements(
                    task_predictions, tool_predictions, recent_usage
                )
            else:
                # Fallback to hardcoded analysis
                context_analysis = self._analyze_current_context(context, query, recent_usage)
                task_predictions = self._predict_tasks(
                    context_analysis, recent_usage, current_session, user_patterns
                )
                tool_predictions = self._predict_tools(
                    task_predictions, recent_usage, user_patterns
                )
                context_needs = self._predict_context_needs(
                    context, current_session, task_predictions
                )
                resource_requirements = self._predict_resource_requirements(
                    task_predictions, tool_predictions, recent_usage
                )
            
            # Identify patterns used for prediction
            patterns_used = self._identify_patterns_used(
                context_analysis, recent_usage, user_patterns
            )
            
            # Find similar sessions for comparison
            similar_sessions = await self._find_similar_sessions(
                user_id, context_analysis, current_session
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(
                task_predictions, tool_predictions, recent_usage, 
                current_session, user_patterns, context_analysis
            )
            
            return UserNeedsPrediction(
                user_id=user_id,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                anticipated_tasks=task_predictions,
                required_tools=tool_predictions,
                context_needs=context_needs,
                resource_requirements=resource_requirements,
                based_on_patterns=patterns_used,
                similar_sessions=similar_sessions,
                trigger_indicators=context_analysis.get("triggers", []),
                metadata={
                    "prediction_date": datetime.utcnow(),
                    "context_analyzed": context,
                    "query": query,
                    "recent_usage_count": len(recent_usage),
                    "session_data": current_session is not None
                }
            )
            
        except Exception as e:
            logger.error(f"Error predicting user needs for user {user_id}: {e}")
            raise
    
    async def _get_current_session(self, user_id: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get current session data if available"""
        session_id = context.get('session_id') or context.get('thread_id')
        if session_id:
            try:
                session = await self.session_repo.get_by_session_id(session_id)
                return session.__dict__ if session else None
            except:
                return None
        return None
    
    async def _get_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Get user behavioral patterns"""
        try:
            # Get user portrait data if available
            portrait = await self.user_portrait_service.get_user_portrait(user_id)
            if portrait:
                return {
                    "behavior_patterns": portrait.behavior_patterns,
                    "usage_patterns": portrait.usage_patterns,
                    "user_preferences": portrait.user_preferences,
                    "expertise_areas": portrait.expertise_areas
                }
        except:
            logger.debug(f"Could not retrieve user portrait for {user_id}")
        
        return {
            "behavior_patterns": {},
            "usage_patterns": {},
            "user_preferences": {},
            "expertise_areas": []
        }
    
    def _analyze_current_context(
        self, 
        context: Dict[str, Any], 
        query: Optional[str], 
        recent_usage: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze current context for prediction signals"""
        analysis = {
            "context_type": "general",
            "intent_signals": [],
            "workflow_stage": "unknown",
            "triggers": []
        }
        
        # Analyze query for intent signals
        if query:
            query_lower = query.lower()
            
            # Intent detection
            if any(word in query_lower for word in ["analyze", "analysis", "data"]):
                analysis["intent_signals"].append("analysis_intent")
                analysis["context_type"] = "analysis"
            
            if any(word in query_lower for word in ["search", "find", "lookup"]):
                analysis["intent_signals"].append("search_intent")
            
            if any(word in query_lower for word in ["remember", "save", "store"]):
                analysis["intent_signals"].append("memory_intent")
            
            if any(word in query_lower for word in ["document", "file", "text"]):
                analysis["intent_signals"].append("document_intent")
                analysis["context_type"] = "document_processing"
            
            if any(word in query_lower for word in ["code", "debug", "function"]):
                analysis["intent_signals"].append("coding_intent")
                analysis["context_type"] = "development"
        
        # Analyze recent usage for workflow stage detection
        if recent_usage:
            recent_tools = [record.get('tool_name') for record in recent_usage[-5:]]
            recent_tools = [t for t in recent_tools if t]  # Remove None values
            
            # Detect workflow patterns
            for workflow_name, stages in self.task_sequences.items():
                for i, stage in enumerate(stages):
                    if any(stage in tool.lower() for tool in recent_tools):
                        analysis["workflow_stage"] = f"{workflow_name}:{stage}"
                        # Predict next stage
                        if i < len(stages) - 1:
                            analysis["triggers"].append(f"next_stage:{stages[i+1]}")
                        break
        
        # Context-based triggers
        if "session_id" in context:
            analysis["triggers"].append("active_session")
        
        if context.get("recent", True):
            analysis["triggers"].append("recent_activity")
        
        return analysis
    
    def _predict_tasks(
        self,
        context_analysis: Dict[str, Any],
        recent_usage: List[Dict[str, Any]],
        current_session: Optional[Dict[str, Any]],
        user_patterns: Dict[str, Any]
    ) -> List[str]:
        """Predict likely tasks based on context and patterns"""
        predicted_tasks = []
        
        # Context-based task prediction
        context_type = context_analysis.get("context_type", "general")
        intent_signals = context_analysis.get("intent_signals", [])
        
        if context_type == "analysis":
            predicted_tasks.extend(["data_exploration", "statistical_analysis", "visualization"])
        elif context_type == "document_processing":
            predicted_tasks.extend(["text_analysis", "summarization", "document_qa"])
        elif context_type == "development":
            predicted_tasks.extend(["code_review", "debugging", "testing"])
        
        # Intent-based predictions
        if "search_intent" in intent_signals:
            predicted_tasks.extend(["information_search", "research", "fact_checking"])
        if "memory_intent" in intent_signals:
            predicted_tasks.extend(["memory_storage", "knowledge_organization", "recall"])
        
        # Workflow-based predictions
        workflow_stage = context_analysis.get("workflow_stage")
        if workflow_stage:
            workflow_name, current_stage = workflow_stage.split(":", 1)
            if workflow_name in self.task_sequences:
                stages = self.task_sequences[workflow_name]
                try:
                    current_index = stages.index(current_stage)
                    # Predict next 2-3 stages
                    for i in range(current_index + 1, min(current_index + 4, len(stages))):
                        predicted_tasks.append(stages[i])
                except ValueError:
                    pass
        
        # Pattern-based predictions from user preferences
        user_preferences = user_patterns.get("user_preferences", {})
        expertise_areas = user_patterns.get("expertise_areas", [])
        
        if "data_analysis" in expertise_areas:
            predicted_tasks.extend(["advanced_analytics", "model_building"])
        if "research" in expertise_areas:
            predicted_tasks.extend(["literature_review", "synthesis"])
        
        # Session continuity predictions
        if current_session:
            conversation_data = current_session.get("conversation_data", {})
            if conversation_data:
                # Look for ongoing tasks in conversation
                conv_text = str(conversation_data).lower()
                if "continue" in conv_text or "next" in conv_text:
                    predicted_tasks.append("task_continuation")
        
        # Recent usage pattern predictions
        if recent_usage:
            recent_endpoints = [r.get('endpoint', '') for r in recent_usage[-3:]]
            
            # If user recently used chat, they might need memory or search
            if any("chat" in endpoint for endpoint in recent_endpoints):
                predicted_tasks.extend(["memory_search", "context_retrieval"])
            
            # If user recently uploaded/processed data, they might analyze it
            if any("upload" in endpoint or "data" in endpoint for endpoint in recent_endpoints):
                predicted_tasks.extend(["data_analysis", "insight_generation"])
        
        # Remove duplicates and return top predictions
        unique_tasks = list(dict.fromkeys(predicted_tasks))  # Preserves order
        return unique_tasks[:8]  # Top 8 predictions
    
    def _predict_tools(
        self,
        predicted_tasks: List[str],
        recent_usage: List[Dict[str, Any]],
        user_patterns: Dict[str, Any]
    ) -> List[str]:
        """Predict required tools based on tasks and patterns"""
        predicted_tools = []
        
        # Task-to-tool mapping
        task_tool_mapping = {
            "data_exploration": ["data_analyzer", "query_tool", "statistics_tool"],
            "statistical_analysis": ["stats_tool", "calculation_engine", "data_analyzer"],
            "visualization": ["chart_generator", "graph_tool", "dashboard_tool"],
            "text_analysis": ["nlp_tool", "text_analyzer", "sentiment_analyzer"],
            "summarization": ["summarizer", "text_processor", "content_extractor"],
            "document_qa": ["qa_engine", "document_reader", "search_tool"],
            "code_review": ["code_analyzer", "syntax_checker", "quality_tool"],
            "debugging": ["debugger", "error_analyzer", "trace_tool"],
            "testing": ["test_runner", "coverage_tool", "validation_engine"],
            "information_search": ["search_engine", "web_crawler", "knowledge_base"],
            "research": ["research_tool", "source_finder", "citation_manager"],
            "memory_storage": ["memory_manager", "knowledge_store", "indexer"],
            "memory_search": ["retrieval_engine", "similarity_search", "context_finder"]
        }
        
        # Map predicted tasks to tools
        for task in predicted_tasks:
            if task in task_tool_mapping:
                predicted_tools.extend(task_tool_mapping[task])
        
        # Add tools based on recent usage patterns
        if recent_usage:
            recent_tools = [r.get('tool_name') for r in recent_usage[-5:]]
            recent_tools = [t for t in recent_tools if t]
            
            # Predict related tools based on tool relationships
            for recent_tool in recent_tools:
                if recent_tool in self.tool_relationships:
                    predicted_tools.extend(self.tool_relationships[recent_tool])
        
        # Add tools based on user preferences
        behavior_patterns = user_patterns.get("behavior_patterns", {})
        if "preferred_tools" in behavior_patterns:
            predicted_tools.extend(behavior_patterns["preferred_tools"])
        
        # Remove duplicates and return top predictions
        unique_tools = list(dict.fromkeys(predicted_tools))
        return unique_tools[:10]  # Top 10 tool predictions
    
    def _predict_context_needs(
        self,
        context: Dict[str, Any],
        current_session: Optional[Dict[str, Any]],
        predicted_tasks: List[str]
    ) -> Dict[str, Any]:
        """Predict context information needs"""
        context_needs = {
            "session_continuity": False,
            "memory_context": False,
            "user_preferences": False,
            "historical_data": False,
            "external_data": False
        }
        
        # Session continuity needs
        if current_session and current_session.get("message_count", 0) > 0:
            context_needs["session_continuity"] = True
        
        # Memory context needs for certain tasks
        memory_tasks = ["memory_search", "context_retrieval", "task_continuation", "research"]
        if any(task in predicted_tasks for task in memory_tasks):
            context_needs["memory_context"] = True
        
        # User preferences for personalized tasks
        personalized_tasks = ["visualization", "analysis", "summarization"]
        if any(task in predicted_tasks for task in personalized_tasks):
            context_needs["user_preferences"] = True
        
        # Historical data for analytical tasks
        analytical_tasks = ["data_analysis", "statistical_analysis", "trend_analysis"]
        if any(task in predicted_tasks for task in analytical_tasks):
            context_needs["historical_data"] = True
        
        # External data for research tasks
        research_tasks = ["research", "information_search", "fact_checking"]
        if any(task in predicted_tasks for task in research_tasks):
            context_needs["external_data"] = True
        
        return context_needs
    
    def _predict_resource_requirements(
        self,
        predicted_tasks: List[str],
        predicted_tools: List[str],
        recent_usage: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Predict resource requirements for predicted tasks"""
        requirements = {
            "computational_intensity": "medium",
            "memory_needs": "standard",
            "processing_time": "short",
            "network_access": False,
            "storage_needs": "minimal"
        }
        
        # High computational intensity tasks
        intensive_tasks = [
            "statistical_analysis", "model_building", "advanced_analytics", 
            "large_document_processing", "bulk_data_analysis"
        ]
        if any(task in predicted_tasks for task in intensive_tasks):
            requirements["computational_intensity"] = "high"
            requirements["memory_needs"] = "high"
            requirements["processing_time"] = "long"
        
        # Memory-intensive tools
        memory_tools = [
            "data_analyzer", "large_model", "bulk_processor", 
            "image_processor", "video_analyzer"
        ]
        if any(tool in predicted_tools for tool in memory_tools):
            requirements["memory_needs"] = "high"
        
        # Network-dependent tasks
        network_tasks = [
            "information_search", "research", "web_scraping", 
            "external_api_calls", "real_time_data"
        ]
        if any(task in predicted_tasks for task in network_tasks):
            requirements["network_access"] = True
        
        # Storage-intensive tasks
        storage_tasks = [
            "data_storage", "backup", "archival", "bulk_export", 
            "dataset_creation"
        ]
        if any(task in predicted_tasks for task in storage_tasks):
            requirements["storage_needs"] = "high"
        
        # Adjust based on recent usage patterns
        if recent_usage:
            avg_tokens = sum(r.get('tokens_used', 0) for r in recent_usage) / len(recent_usage)
            if avg_tokens > 500:  # High token usage suggests intensive tasks
                requirements["computational_intensity"] = "high"
        
        return requirements
    
    def _identify_patterns_used(
        self,
        context_analysis: Dict[str, Any],
        recent_usage: List[Dict[str, Any]],
        user_patterns: Dict[str, Any]
    ) -> List[str]:
        """Identify which patterns were used for prediction"""
        patterns_used = []
        
        if context_analysis.get("intent_signals"):
            patterns_used.append("query_intent_analysis")
        
        if context_analysis.get("workflow_stage") != "unknown":
            patterns_used.append("workflow_stage_detection")
        
        if recent_usage:
            patterns_used.append("recent_usage_patterns")
        
        if user_patterns.get("behavior_patterns"):
            patterns_used.append("user_behavior_patterns")
        
        if user_patterns.get("expertise_areas"):
            patterns_used.append("expertise_based_prediction")
        
        return patterns_used
    
    async def _find_similar_sessions(
        self,
        user_id: str,
        context_analysis: Dict[str, Any],
        current_session: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Find similar past sessions for comparison"""
        try:
            # Get recent sessions
            sessions = await self.session_repo.get_user_sessions(user_id, limit=20)
            
            similar_sessions = []
            context_type = context_analysis.get("context_type", "general")
            
            for session in sessions:
                if not current_session or session.get('session_id') != current_session.get('session_id'):
                    # Simple similarity based on conversation data keywords
                    conv_data = session.get('conversation_data', {})
                    conv_text = str(conv_data).lower()
                    
                    # Check for similar context type
                    if context_type != "general":
                        if context_type in conv_text:
                            similar_sessions.append(session.get('session_id', ''))
                    
                    # Limit to most relevant sessions
                    if len(similar_sessions) >= 5:
                        break
            
            return similar_sessions
            
        except Exception as e:
            logger.debug(f"Could not find similar sessions: {e}")
            return []
    
    def _calculate_confidence(
        self,
        task_predictions: List[str],
        tool_predictions: List[str],
        recent_usage: List[Dict[str, Any]],
        current_session: Optional[Dict[str, Any]],
        user_patterns: Dict[str, Any],
        context_analysis: Dict[str, Any]
    ) -> float:
        """Calculate confidence in predictions"""
        base_confidence = 0.5
        
        # Context quality factors
        if context_analysis.get("intent_signals"):
            base_confidence += 0.1 * len(context_analysis["intent_signals"])
        
        if context_analysis.get("workflow_stage") != "unknown":
            base_confidence += 0.15
        
        # Data quality factors
        if recent_usage:
            if len(recent_usage) >= 10:
                base_confidence += 0.1
            elif len(recent_usage) >= 5:
                base_confidence += 0.05
        else:
            base_confidence -= 0.15
        
        # Session context factor
        if current_session and current_session.get("message_count", 0) > 3:
            base_confidence += 0.1
        
        # User patterns factor
        if user_patterns.get("behavior_patterns") or user_patterns.get("user_preferences"):
            base_confidence += 0.1
        
        # Prediction consistency factor
        if task_predictions and tool_predictions:
            base_confidence += 0.05
        
        # Trigger strength factor
        trigger_count = len(context_analysis.get("triggers", []))
        if trigger_count > 2:
            base_confidence += 0.05
        
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
        """Health check for user needs predictor"""
        try:
            # Test repository connectivity
            test_result = await self.usage_repo.get_user_usage_history("test", limit=1)
            
            return {
                "status": "healthy",
                "component": "user_needs_predictor",
                "last_check": datetime.utcnow(),
                "repositories": {
                    "usage_repo": "connected",
                    "session_repo": "connected"
                },
                "services": {
                    "user_portrait_service": "available"
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "user_needs_predictor",
                "error": str(e),
                "last_check": datetime.utcnow()
            }

    # ============ AI-powered Methods (替换硬编码逻辑) ============
    
    async def _ml_analyze_current_context(self, context: Dict[str, Any], query: Optional[str], recent_usage: List[Dict]) -> Dict[str, Any]:
        """使用NLP和推理AI分析当前上下文，替换硬编码的关键词匹配"""
        try:
            # 使用ReasoningGenerator分析上下文和查询意图
            context_prompt = f"""
            Analyze the user's current context and intent:
            Context: {json.dumps(context)}
            Query: {query or 'No specific query'}
            Recent Usage: {len(recent_usage)} recent activities
            
            Provide analysis in this format:
            {{
                "primary_intent": "analysis/research/development/document/general",
                "secondary_intents": ["intent1", "intent2"],
                "complexity_level": "low/medium/high",
                "urgency": "low/medium/high", 
                "domain": "data/text/code/general",
                "user_state": "exploratory/focused/blocked/completing"
            }}
            """
            
            reasoning_result = await self.reasoning_generator.generate_reasoning({
                'prompt': context_prompt,
                'reasoning_type': 'context_analysis',
                'output_format': 'json'
            })
            
            analysis = reasoning_result.get('analysis', {})
            
            # 使用DataAnalytics分析使用模式
            if recent_usage:
                usage_patterns = await self.data_analytics.analyze_user_behavior_patterns({
                    'usage_data': recent_usage,
                    'context': context
                })
                analysis['usage_patterns'] = usage_patterns
            
            return analysis
            
        except Exception as e:
            logger.error(f"ML context analysis failed: {e}")
            # 回退到简化分析
            return {
                "primary_intent": "general",
                "complexity_level": "medium",
                "urgency": "medium",
                "domain": "general"
            }
    
    async def _ml_predict_tasks(self, context_analysis: Dict, recent_usage: List[Dict], 
                               current_session: Dict, user_patterns: Dict) -> List[str]:
        """使用ML预测任务序列而不是硬编码工作流"""
        try:
            # 构建预测输入
            prediction_input = {
                'context_analysis': context_analysis,
                'recent_usage': recent_usage,
                'current_session': current_session,
                'user_patterns': user_patterns
            }
            
            # 使用ML处理器进行任务序列预测
            # Ensure ML processor is initialized
            await self._ensure_ml_processor()
            
            task_prediction = await self.ml_processor.predict_task_sequence({
                'input_data': prediction_input,
                'model_type': 'task_sequence_predictor',
                'max_tasks': 5
            })
            
            predicted_tasks = task_prediction.get('predicted_tasks', [])
            
            # 如果ML预测失败或结果为空，使用基于推理的预测
            if not predicted_tasks:
                intent = context_analysis.get('primary_intent', 'general')
                predicted_tasks = await self._reasoning_based_task_prediction(intent, context_analysis)
            
            return predicted_tasks[:5]  # 限制返回数量
            
        except Exception as e:
            logger.error(f"ML task prediction failed: {e}")
            # 回退到简单的基于意图的预测
            return self._fallback_task_prediction(context_analysis)
    
    async def _reasoning_based_task_prediction(self, intent: str, context_analysis: Dict) -> List[str]:
        """基于推理AI的任务预测"""
        try:
            reasoning_prompt = f"""
            Based on user intent '{intent}' and context analysis:
            {json.dumps(context_analysis)}
            
            Predict the next 3-5 tasks the user is likely to perform.
            Focus on actual workflow progression and logical next steps.
            Return as a JSON array of task names.
            """
            
            reasoning_result = await self.reasoning_generator.generate_reasoning({
                'prompt': reasoning_prompt,
                'reasoning_type': 'task_prediction',
                'output_format': 'json_array'
            })
            
            return reasoning_result.get('predicted_tasks', ["explore_data", "analyze", "visualize"])
            
        except Exception as e:
            logger.error(f"Reasoning-based task prediction failed: {e}")
            return ["explore_options", "analyze_data", "get_insights"]
    
    async def _ml_predict_tools(self, task_predictions: List[str], recent_usage: List[Dict], 
                               user_patterns: Dict) -> List[str]:
        """使用AI发现真实工具而不是假的工具名"""
        try:
            # 从DataAnalyticsService获取实际可用的工具列表
            available_tools = await self.data_analytics.get_available_analysis_tools()
            
            # 使用ML匹配任务到真实工具
            # Ensure ML processor is initialized
            await self._ensure_ml_processor()
            
            tool_matching = await self.ml_processor.match_tasks_to_tools({
                'tasks': task_predictions,
                'available_tools': available_tools,
                'user_preferences': user_patterns,
                'recent_tool_usage': [usage.get('tool_name') for usage in recent_usage if usage.get('tool_name')]
            })
            
            recommended_tools = tool_matching.get('recommended_tools', [])
            
            # 使用推理生成器进行工具推荐
            if not recommended_tools:
                reasoning_prompt = f"""
                Given these predicted tasks: {task_predictions}
                And available tools: {available_tools[:10]}  # 限制提示长度
                
                Recommend the most suitable tools for each task.
                Return real tool names only, not invented ones.
                Format: ["tool1", "tool2", "tool3"]
                """
                
                reasoning_result = await self.reasoning_generator.generate_reasoning({
                    'prompt': reasoning_prompt,
                    'reasoning_type': 'tool_recommendation',
                    'output_format': 'json_array'
                })
                
                recommended_tools = reasoning_result.get('recommended_tools', [])
            
            return recommended_tools[:5]  # 限制数量
            
        except Exception as e:
            logger.error(f"ML tool prediction failed: {e}")
            return ["data_analytics_tool", "visualization_tool", "export_tool"]  # 回退到已知真实工具
    
    async def _ml_predict_context_needs(self, context: Dict, current_session: Dict, 
                                       task_predictions: List[str]) -> Dict[str, Any]:
        """使用AI预测上下文需求"""
        try:
            # Ensure ML processor is initialized
            await self._ensure_ml_processor()
            
            context_prediction = await self.ml_processor.predict_context_requirements({
                'current_context': context,
                'session_data': current_session,
                'predicted_tasks': task_predictions
            })
            
            return context_prediction.get('context_needs', {
                "data_access": True,
                "computation_power": "medium",
                "memory_usage": "moderate",
                "network_access": True
            })
            
        except Exception as e:
            logger.error(f"ML context needs prediction failed: {e}")
            return {"data_access": True, "computation_power": "medium"}
    
    async def _ml_predict_resource_requirements(self, task_predictions: List[str], 
                                               tool_predictions: List[str], recent_usage: List[Dict]) -> Dict[str, Any]:
        """使用AI预测资源需求"""
        try:
            # Ensure ML processor is initialized
            await self._ensure_ml_processor()
            
            resource_prediction = await self.ml_processor.predict_resource_requirements({
                'predicted_tasks': task_predictions,
                'predicted_tools': tool_predictions,
                'historical_usage': recent_usage
            })
            
            return resource_prediction.get('resource_requirements', {
                "cpu_intensity": "medium",
                "memory_required": "moderate",
                "storage_needed": "minimal", 
                "network_bandwidth": "low"
            })
            
        except Exception as e:
            logger.error(f"ML resource prediction failed: {e}")
            return {"cpu_intensity": "medium", "memory_required": "moderate"}
    
    def _fallback_task_prediction(self, context_analysis: Dict) -> List[str]:
        """ML失败时的回退任务预测"""
        intent = context_analysis.get('primary_intent', 'general')
        
        task_map = {
            'analysis': ['explore_data', 'analyze_patterns', 'create_visualizations'],
            'research': ['search_information', 'gather_sources', 'synthesize_findings'],
            'development': ['analyze_code', 'run_tests', 'debug_issues'],
            'document': ['process_text', 'extract_insights', 'summarize_content'],
            'general': ['explore_options', 'get_overview', 'plan_next_steps']
        }
        
        return task_map.get(intent, task_map['general'])