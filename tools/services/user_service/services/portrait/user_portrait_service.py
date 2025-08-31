"""
UserPortraitService Implementation

基于Memory Service的用户画像生成和分析服务
结合用户行为数据和记忆分析，生成智能化用户画像
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import json

from ...models import (
    UserPortrait, UserPortraitCreate, UserPortraitUpdate,
    UserPortraitAnalysisRequest, UserPortraitResponse,
    UserBehaviorInsight, UserPortraitSummary, UserPortraitStatus
)
from tools.services.user_service.repositories.user_repository import UserRepository
from tools.services.user_service.services.base import BaseService, ServiceResult
from tools.services.user_service.services.usage_service import UsageService

# Memory Service import
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools.services.memory_service.memory_service import memory_service

# Event-driven integration with prediction services
from tools.services.event_service.services.event_service import EventService

# Intelligence Service for AI-enhanced analysis
from tools.services.intelligence_service.language.text_extractor import TextExtractor
from tools.services.intelligence_service.language.reasoning_generator import ReasoningGenerator

# DataAnalyticsService for real ML/DL/Statistical analysis
from tools.services.data_analytics_service.services.data_analytics_service import DataAnalyticsService

# Event Service for real-time updates
from tools.services.event_service.event_database_service import EventDatabaseService

# Session Memory Analysis Service
from .session_memory_analysis_service import SessionMemoryAnalysisService

logger = logging.getLogger(__name__)


class UserPortraitService(BaseService):
    """用户画像服务"""
    
    def __init__(self):
        super().__init__("UserPortraitService") 
        self.user_repo = UserRepository()
        self.usage_service = UsageService()
        self.memory_service = memory_service
        
        # AI Prediction Service as the intelligent backend
        self.prediction_service = PredictionOrchestratorService()
        
        # Intelligence Service for AI-enhanced analysis
        self.text_extractor = TextExtractor()
        self.reasoning_generator = ReasoningGenerator()
        
        # DataAnalyticsService for real ML/DL/Statistical analysis
        self.data_analytics_service = DataAnalyticsService("user_behavior_analytics")
        
        # Session Memory Analysis Service
        self.session_analysis_service = SessionMemoryAnalysisService()
        
        # Event Service for real-time portrait updates
        try:
            self.event_service = EventDatabaseService()
        except Exception as e:
            logger.warning(f"Event service not available: {e}")
            self.event_service = None
        
        # Smart caching for portrait data (avoid recomputing)
        self.portrait_cache = {}  # user_id -> (portrait_data, timestamp)
        self.cache_ttl_seconds = 3600  # 1 hour cache
        
        # Event-driven portrait update flags
        self.portrait_update_flags = {}  # user_id -> {'needs_update': bool, 'last_event': timestamp}
    
    async def generate_user_portrait(
        self, 
        request: UserPortraitAnalysisRequest
    ) -> ServiceResult[UserPortrait]:
        """
        生成用户画像 - 使用AI预测服务后端
        
        Args:
            request: 用户画像分析请求
            
        Returns:
            ServiceResult with UserPortrait
        """
        try:
            # 验证用户存在
            user = await self.user_repo.get_by_user_id(request.user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {request.user_id}")
            
            self._log_operation("generate_user_portrait", f"User: {request.user_id}")
            
            # Clear cache if force regenerate
            if request.force_regenerate and request.user_id in self.portrait_cache:
                del self.portrait_cache[request.user_id]
                logger.info(f"Cleared cache for force regeneration: {request.user_id}")
            
            # Use the enhanced get_user_portrait method (which uses AI backend)
            portrait_result = await self.get_user_portrait(request.user_id)
            
            if portrait_result.is_success:
                logger.info(f"Generated AI-powered portrait for {request.user_id}")
                return portrait_result
            else:
                logger.warning(f"Failed to generate portrait for {request.user_id}: {portrait_result.message}")
                return portrait_result
            
        except Exception as e:
            return self._handle_exception(e, "generate user portrait")
    
    async def get_user_portrait(self, user_id: str) -> ServiceResult[UserPortrait]:
        """
        获取用户画像 - 使用AI预测服务作为智能后端
        
        Args:
            user_id: 用户ID
            
        Returns:
            ServiceResult with UserPortrait
        """
        try:
            # Check smart cache first
            if user_id in self.portrait_cache:
                portrait_data, timestamp = self.portrait_cache[user_id]
                if (datetime.utcnow() - timestamp).seconds < self.cache_ttl_seconds:
                    logger.info(f"Returning cached portrait for {user_id}")
                    return ServiceResult.success(portrait_data, "From cache")
            
            logger.info(f"Generating AI-powered portrait for {user_id}")
            
            # Use AI Prediction Service to generate comprehensive portrait
            prediction_profile = await self.prediction_service.get_comprehensive_prediction_profile(
                user_id=user_id,
                analysis_depth="full", 
                timeframe="30d"
            )
            
            if not prediction_profile.predictions:
                return ServiceResult.not_found(f"Insufficient data to generate portrait for {user_id}")
            
            # Transform AI predictions into portrait format
            portrait_data = await self._transform_predictions_to_portrait(user_id, prediction_profile)
            
            # Cache the result
            self.portrait_cache[user_id] = (portrait_data, datetime.utcnow())
            
            logger.info(f"Generated AI-powered portrait for {user_id} with confidence {portrait_data.confidence_score:.3f}")
            return ServiceResult.success(portrait_data, "Generated from AI predictions")
            
        except Exception as e:
            return self._handle_exception(e, "get user portrait")
    
    async def get_portrait_summary(self, user_id: str) -> ServiceResult[UserPortraitSummary]:
        """
        获取用户画像摘要
        
        Args:
            user_id: 用户ID
            
        Returns:
            ServiceResult with UserPortraitSummary
        """
        try:
            portrait_result = await self.get_user_portrait(user_id)
            
            if not portrait_result.is_success:
                # 无画像时返回基础摘要
                summary = UserPortraitSummary(
                    user_id=user_id,
                    portrait_exists=False,
                    data_freshness="none",
                    key_characteristics=[],
                    suggested_actions=["Generate initial user portrait"],
                    completeness_percentage=0.0
                )
                return ServiceResult.success(summary, "No portrait found")
            
            portrait = portrait_result.data
            
            # 生成摘要
            summary = await self._generate_portrait_summary(portrait)
            
            return ServiceResult.success(summary, "Portrait summary generated")
            
        except Exception as e:
            return self._handle_exception(e, "get portrait summary")
    
    async def update_portrait_status(
        self, 
        user_id: str, 
        status: UserPortraitStatus
    ) -> ServiceResult[UserPortrait]:
        """
        更新用户画像状态
        
        Args:
            user_id: 用户ID
            status: 新状态
            
        Returns:
            ServiceResult with updated UserPortrait
        """
        try:
            # TODO: 实现数据库更新
            return ServiceResult.error("Database update not implemented yet")
            
        except Exception as e:
            return self._handle_exception(e, "update portrait status")
    
    async def _perform_comprehensive_analysis(
        self, 
        request: UserPortraitAnalysisRequest
    ) -> Dict[str, Any]:
        """
        执行综合分析
        
        Args:
            request: 分析请求
            
        Returns:
            分析结果字典
        """
        analysis_results = {
            'memory_analysis': {},
            'usage_analysis': {},
            'behavior_analysis': {},
            'confidence_metrics': {}
        }
        
        # 1. Memory Service分析
        if request.include_memory_analysis:
            memory_stats = await self.memory_service.get_memory_statistics(request.user_id)
            analysis_results['memory_analysis'] = memory_stats
        
        # 2. 使用模式分析
        if request.include_usage_analysis:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=request.days_back)
            
            usage_stats_result = await self.usage_service.get_usage_statistics(
                request.user_id, start_date, end_date
            )
            
            if usage_stats_result.is_success:
                analysis_results['usage_analysis'] = usage_stats_result.data.model_dump()
            
            # 获取每日使用摘要
            daily_summary_result = await self.usage_service.get_daily_usage_summary(
                request.user_id, request.days_back
            )
            
            if daily_summary_result.is_success:
                analysis_results['usage_analysis']['daily_summary'] = daily_summary_result.data
        
        # 3. 行为模式分析
        if request.include_behavior_analysis:
            behavior_patterns = await self._analyze_behavior_patterns(
                request.user_id, request.days_back
            )
            analysis_results['behavior_analysis'] = behavior_patterns
        
        # 4. 计算置信度指标
        analysis_results['confidence_metrics'] = self._calculate_confidence_metrics(analysis_results)
        
        return analysis_results
    
    async def _analyze_behavior_patterns(self, user_id: str, days_back: int) -> Dict[str, Any]:
        """
        分析用户行为模式
        
        Args:
            user_id: 用户ID
            days_back: 回溯天数
            
        Returns:
            行为模式分析结果
        """
        behavior_patterns = {
            'activity_patterns': {},
            'interaction_styles': {},
            'preference_indicators': {},
            'expertise_signals': []
        }
        
        try:
            # 获取最近使用记录
            recent_usage_result = await self.usage_service.get_recent_usage(
                user_id, hours=days_back * 24
            )
            
            if recent_usage_result.is_success:
                usage_records = recent_usage_result.data
                
                # 分析活动模式
                behavior_patterns['activity_patterns'] = self._analyze_activity_patterns(usage_records)
                
                # 分析交互风格
                behavior_patterns['interaction_styles'] = self._analyze_interaction_styles(usage_records)
                
                # 分析偏好指标
                behavior_patterns['preference_indicators'] = self._analyze_preference_indicators(usage_records)
                
                # 检测专业领域信号
                behavior_patterns['expertise_signals'] = self._detect_expertise_signals(usage_records)
        
        except Exception as e:
            logger.warning(f"Behavior analysis failed for user {user_id}: {e}")
        
        return behavior_patterns
    
    def _analyze_activity_patterns(self, usage_records: List) -> Dict[str, Any]:
        """分析活动模式"""
        if not usage_records:
            return {'frequency': 'unknown', 'peak_hours': [], 'consistency': 0.0}
        
        # 简化的活动模式分析
        total_records = len(usage_records)
        
        # 按小时分组
        hourly_activity = {}
        for record in usage_records:
            if record.created_at:
                hour = record.created_at.hour
                hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
        
        # 找出活跃时段
        peak_hours = []
        if hourly_activity:
            avg_activity = sum(hourly_activity.values()) / len(hourly_activity)
            peak_hours = [hour for hour, count in hourly_activity.items() if count > avg_activity]
        
        return {
            'frequency': 'high' if total_records > 50 else 'medium' if total_records > 10 else 'low',
            'peak_hours': sorted(peak_hours),
            'consistency': min(1.0, len(set(hourly_activity.keys())) / 24.0),
            'total_activities': total_records
        }
    
    def _analyze_interaction_styles(self, usage_records: List) -> Dict[str, Any]:
        """分析交互风格"""
        if not usage_records:
            return {'style': 'unknown', 'complexity': 'unknown'}
        
        # 分析API使用模式
        api_usage = {}
        model_usage = {}
        
        for record in usage_records:
            endpoint = getattr(record, 'endpoint', 'unknown')
            model_name = getattr(record, 'model_name', 'unknown')
            
            api_usage[endpoint] = api_usage.get(endpoint, 0) + 1
            if model_name and model_name != 'unknown':
                model_usage[model_name] = model_usage.get(model_name, 0) + 1
        
        # 判断使用复杂度
        api_diversity = len(api_usage)
        model_diversity = len(model_usage)
        
        complexity = 'high' if api_diversity > 5 else 'medium' if api_diversity > 2 else 'low'
        
        return {
            'style': 'exploratory' if api_diversity > model_diversity else 'focused',
            'complexity': complexity,
            'api_diversity': api_diversity,
            'model_diversity': model_diversity,
            'preferred_apis': sorted(api_usage.items(), key=lambda x: x[1], reverse=True)[:3]
        }
    
    def _analyze_preference_indicators(self, usage_records: List) -> Dict[str, Any]:
        """分析偏好指标"""
        if not usage_records:
            return {}
        
        preferences = {
            'preferred_models': {},
            'preferred_providers': {},
            'cost_sensitivity': 'unknown',
            'token_usage_patterns': {}
        }
        
        total_cost = 0.0
        total_tokens = 0
        
        for record in usage_records:
            # 模型偏好
            model_name = getattr(record, 'model_name', None)
            if model_name:
                preferences['preferred_models'][model_name] = preferences['preferred_models'].get(model_name, 0) + 1
            
            # 提供商偏好
            provider = getattr(record, 'provider', None)
            if provider:
                preferences['preferred_providers'][provider] = preferences['preferred_providers'].get(provider, 0) + 1
            
            # 成本和token使用
            cost = getattr(record, 'cost_usd', 0.0) or 0.0
            tokens = getattr(record, 'tokens_used', 0) or 0
            
            total_cost += cost
            total_tokens += tokens
        
        # 计算成本敏感度
        avg_cost_per_request = total_cost / len(usage_records) if usage_records else 0
        preferences['cost_sensitivity'] = 'high' if avg_cost_per_request < 0.01 else 'medium' if avg_cost_per_request < 0.1 else 'low'
        
        # Token使用模式
        avg_tokens_per_request = total_tokens / len(usage_records) if usage_records else 0
        preferences['token_usage_patterns'] = {
            'average_tokens_per_request': avg_tokens_per_request,
            'total_tokens': total_tokens,
            'usage_intensity': 'high' if avg_tokens_per_request > 1000 else 'medium' if avg_tokens_per_request > 100 else 'low'
        }
        
        return preferences
    
    def _detect_expertise_signals(self, usage_records: List) -> List[str]:
        """检测专业领域信号"""
        if not usage_records:
            return []
        
        expertise_signals = []
        
        # 基于API使用模式检测专业领域
        api_usage = {}
        for record in usage_records:
            endpoint = getattr(record, 'endpoint', '')
            if endpoint:
                api_usage[endpoint] = api_usage.get(endpoint, 0) + 1
        
        # 简化的专业领域检测逻辑
        total_requests = sum(api_usage.values())
        
        for endpoint, count in api_usage.items():
            usage_percentage = count / total_requests
            
            if usage_percentage > 0.3:  # 如果某个API使用超过30%
                if 'chat' in endpoint.lower():
                    expertise_signals.append('conversational_ai')
                elif 'completion' in endpoint.lower():
                    expertise_signals.append('text_generation')
                elif 'embedding' in endpoint.lower():
                    expertise_signals.append('semantic_analysis')
                elif 'image' in endpoint.lower():
                    expertise_signals.append('image_processing')
        
        return list(set(expertise_signals))  # 去重
    
    def _calculate_confidence_metrics(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """计算置信度指标"""
        metrics = {
            'overall_confidence': 0.0,
            'memory_confidence': 0.0,
            'usage_confidence': 0.0,
            'behavior_confidence': 0.0,
            'data_completeness': 0.0
        }
        
        # Memory Service置信度
        memory_analysis = analysis_results.get('memory_analysis', {})
        if memory_analysis and 'total_memories' in memory_analysis:
            total_memories = memory_analysis.get('total_memories', 0)
            metrics['memory_confidence'] = min(1.0, total_memories / 100.0)  # 100个记忆认为是高置信度
        
        # 使用数据置信度
        usage_analysis = analysis_results.get('usage_analysis', {})
        if usage_analysis and 'total_records' in usage_analysis:
            total_records = usage_analysis.get('total_records', 0)
            metrics['usage_confidence'] = min(1.0, total_records / 50.0)  # 50个记录认为是高置信度
        
        # 行为分析置信度
        behavior_analysis = analysis_results.get('behavior_analysis', {})
        if behavior_analysis:
            activity_patterns = behavior_analysis.get('activity_patterns', {})
            total_activities = activity_patterns.get('total_activities', 0)
            metrics['behavior_confidence'] = min(1.0, total_activities / 30.0)  # 30个活动认为是高置信度
        
        # 数据完整性
        completeness_factors = []
        if memory_analysis:
            completeness_factors.append(1.0)
        if usage_analysis:
            completeness_factors.append(1.0)
        if behavior_analysis:
            completeness_factors.append(1.0)
        
        metrics['data_completeness'] = sum(completeness_factors) / 3.0  # 三个维度的平均值
        
        # 总体置信度
        confidence_scores = [
            metrics['memory_confidence'],
            metrics['usage_confidence'], 
            metrics['behavior_confidence']
        ]
        metrics['overall_confidence'] = sum(confidence_scores) / len(confidence_scores)
        
        return metrics
    
    async def _build_portrait_data(self, user_id: str, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """构建用户画像数据"""
        memory_analysis = analysis_results.get('memory_analysis', {})
        usage_analysis = analysis_results.get('usage_analysis', {})
        behavior_analysis = analysis_results.get('behavior_analysis', {})
        confidence_metrics = analysis_results.get('confidence_metrics', {})
        
        # 提取关键信息
        total_memories = memory_analysis.get('total_memories', 0)
        knowledge_diversity = memory_analysis.get('intelligence_metrics', {}).get('knowledge_diversity', 0)
        memory_distribution = memory_analysis.get('by_type', {})
        
        # 构建行为模式
        behavior_patterns = {
            'activity_frequency': behavior_analysis.get('activity_patterns', {}).get('frequency', 'unknown'),
            'peak_activity_hours': behavior_analysis.get('activity_patterns', {}).get('peak_hours', []),
            'interaction_style': behavior_analysis.get('interaction_styles', {}).get('style', 'unknown'),
            'usage_complexity': behavior_analysis.get('interaction_styles', {}).get('complexity', 'unknown')
        }
        
        # 构建使用模式
        usage_patterns = {
            'total_usage_records': usage_analysis.get('total_records', 0),
            'total_credits_used': usage_analysis.get('total_credits_charged', 0.0),
            'total_tokens_used': usage_analysis.get('total_tokens_used', 0),
            'preferred_models': usage_analysis.get('by_model', {}),
            'preferred_providers': usage_analysis.get('by_provider', {})
        }
        
        # 构建用户偏好
        preference_indicators = behavior_analysis.get('preference_indicators', {})
        user_preferences = {
            'cost_sensitivity': preference_indicators.get('cost_sensitivity', 'unknown'),
            'token_usage_intensity': preference_indicators.get('token_usage_patterns', {}).get('usage_intensity', 'unknown'),
            'preferred_models': preference_indicators.get('preferred_models', {}),
            'preferred_providers': preference_indicators.get('preferred_providers', {})
        }
        
        # 沟通风格
        interaction_styles = behavior_analysis.get('interaction_styles', {})
        communication_style = {
            'interaction_complexity': interaction_styles.get('complexity', 'unknown'),
            'exploration_tendency': interaction_styles.get('style', 'unknown'),
            'api_diversity_score': interaction_styles.get('api_diversity', 0),
            'preferred_interaction_methods': interaction_styles.get('preferred_apis', [])
        }
        
        # 专业领域
        expertise_areas = behavior_analysis.get('expertise_signals', [])
        
        portrait_data = {
            'user_id': user_id,
            'total_memories': total_memories,
            'knowledge_diversity': knowledge_diversity,
            'memory_distribution': memory_distribution,
            'intelligence_metrics': memory_analysis.get('intelligence_metrics', {}),
            'behavior_patterns': behavior_patterns,
            'usage_patterns': usage_patterns,
            'user_preferences': user_preferences,
            'communication_style': communication_style,
            'expertise_areas': expertise_areas,
            'last_analysis_date': datetime.utcnow(),
            'confidence_score': confidence_metrics.get('overall_confidence', 0.0),
            'data_completeness': confidence_metrics.get('data_completeness', 0.0),
            'portrait_version': '1.0',
            'status': UserPortraitStatus.ACTIVE
        }
        
        return portrait_data
    
    async def _create_portrait(self, user_id: str, portrait_data: Dict[str, Any]) -> Optional[UserPortrait]:
        """创建新用户画像"""
        try:
            # TODO: 实现数据库存储
            # 暂时返回内存中的对象
            portrait = UserPortrait(**portrait_data)
            return portrait
        except Exception as e:
            logger.error(f"Failed to create portrait for user {user_id}: {e}")
            return None
    
    async def _update_portrait(self, user_id: str, portrait_data: Dict[str, Any]) -> Optional[UserPortrait]:
        """更新现有用户画像"""
        try:
            # TODO: 实现数据库更新
            # 暂时返回内存中的对象
            portrait = UserPortrait(**portrait_data)
            return portrait
        except Exception as e:
            logger.error(f"Failed to update portrait for user {user_id}: {e}")
            return None
    
    async def _generate_portrait_summary(self, portrait: UserPortrait) -> UserPortraitSummary:
        """生成用户画像摘要"""
        # 计算数据新鲜度
        if portrait.last_analysis_date:
            days_since_analysis = (datetime.utcnow() - portrait.last_analysis_date).days
            if days_since_analysis == 0:
                data_freshness = "today"
            elif days_since_analysis <= 7:
                data_freshness = "recent"
            elif days_since_analysis <= 30:
                data_freshness = "moderate"
            else:
                data_freshness = "stale"
        else:
            data_freshness = "unknown"
        
        # 生成关键特征
        key_characteristics = []
        
        if portrait.total_memories > 50:
            key_characteristics.append("Active memory user")
        if portrait.knowledge_diversity > 3:
            key_characteristics.append("Diverse knowledge base")
        
        behavior_patterns = portrait.behavior_patterns or {}
        if behavior_patterns.get('activity_frequency') == 'high':
            key_characteristics.append("High activity user")
        if behavior_patterns.get('usage_complexity') == 'high':
            key_characteristics.append("Advanced user")
        
        if portrait.expertise_areas:
            key_characteristics.append(f"Expert in: {', '.join(portrait.expertise_areas[:2])}")
        
        # 生成建议行动
        suggested_actions = []
        
        if portrait.confidence_score < 0.5:
            suggested_actions.append("Collect more user interaction data")
        if portrait.data_completeness < 0.7:
            suggested_actions.append("Enable additional tracking features")
        if data_freshness in ["stale", "moderate"]:
            suggested_actions.append("Refresh user portrait analysis")
        
        if not suggested_actions:
            suggested_actions.append("Portrait is up to date")
        
        summary = UserPortraitSummary(
            user_id=portrait.user_id,
            portrait_exists=True,
            last_updated=portrait.last_analysis_date,
            data_freshness=data_freshness,
            key_characteristics=key_characteristics,
            suggested_actions=suggested_actions,
            completeness_percentage=portrait.data_completeness * 100
        )
        
        return summary

    # ============ AI Prediction Integration Methods ============

    async def _transform_predictions_to_portrait(self, user_id: str, prediction_profile) -> UserPortrait:
        """
        Transform AI prediction results into UserPortrait format using REAL data sources:
        - Memory Service (session_memories, episodic_memories)
        - Usage Repository (user_usage_records) 
        - Session Repository (sessions)
        """
        try:
            # Get real data from actual sources
            memory_stats = await self._extract_real_memory_metrics(user_id)
            usage_stats = await self._extract_real_usage_patterns(user_id)
            session_stats = await self._extract_real_session_patterns(user_id)
            
            # Calculate confidence based on actual data availability
            data_sources = [memory_stats, usage_stats, session_stats]
            data_completeness = sum(1 for source in data_sources if source and source.get('has_data')) / len(data_sources)
            
            # Apply AI-enhanced analysis
            ai_insights = await self._ai_enhanced_behavior_analysis(usage_stats, memory_stats)
            
            # Get 8-dimensional prediction analysis
            prediction_insights = await self._get_8d_prediction_analysis(user_id, memory_stats, usage_stats, session_stats)
            
            # Build portrait from real behavioral data + AI insights + 8D predictions
            portrait_data = {
                'user_id': user_id,
                'total_memories': memory_stats.get('total_memories', 0),
                'knowledge_diversity': memory_stats.get('diversity_score', 0.3),
                'memory_distribution': memory_stats.get('distribution', {}),
                'intelligence_metrics': self._build_real_intelligence_metrics(memory_stats, usage_stats),
                'behavior_patterns': {
                    **self._extract_real_behavior_patterns(usage_stats, session_stats),
                    'ai_insights': ai_insights,
                    'prediction_insights': prediction_insights
                },
                'usage_patterns': usage_stats.get('patterns', {}),
                'user_preferences': memory_stats.get('preferences', {}),
                'communication_style': self._infer_communication_style(session_stats, memory_stats),
                'expertise_areas': self._infer_expertise_from_usage(usage_stats),
                'prediction_dimensions': prediction_insights.get('dimensions', {}),
                'last_analysis_date': datetime.utcnow(),
                'confidence_score': max(0.3, data_completeness * 0.9),  # Real confidence based on data
                'data_completeness': data_completeness,
                'portrait_version': '2.2_8d_predictions_integrated',
                'status': UserPortraitStatus.ACTIVE
            }
            
            portrait = UserPortrait(**portrait_data)
            logger.info(f"Built portrait from real data for {user_id}: completeness={data_completeness:.2f}")
            
            return portrait
            
        except Exception as e:
            logger.error(f"Failed to build portrait from real data for {user_id}: {e}")
            # Return minimal portrait
            return UserPortrait(
                user_id=user_id,
                confidence_score=0.2,
                portrait_version='2.1_real_data_fallback',
                status=UserPortraitStatus.ACTIVE,
                last_analysis_date=datetime.utcnow()
            )

    async def _extract_real_memory_metrics(self, user_id: str) -> Dict[str, Any]:
        """Extract real memory metrics from memory service using correct API"""
        try:
            # Use Memory Service's comprehensive statistics API
            memory_stats = await self.memory_service.get_memory_statistics(user_id)
            
            # Check if statistics were retrieved successfully  
            if 'error' in memory_stats:
                logger.warning(f"Memory stats error for {user_id}: {memory_stats['error']}")
                return {'has_data': False, 'total_memories': 0}
            
            # Extract core metrics
            total_memories = memory_stats.get('total_memories', 0)
            by_type = memory_stats.get('by_type', {})
            intelligence_metrics = memory_stats.get('intelligence_metrics', {})
            
            # Get session memories for preference extraction
            preferences = {}
            try:
                # Get session memories data directly from database for preferences
                session_memory_data = await self.memory_service.get_memory_resource_data(
                    'session', user_id, is_active=True, limit=10
                )
                for memory_data in session_memory_data:
                    user_prefs = memory_data.get('user_preferences', {})
                    if isinstance(user_prefs, dict):
                        preferences.update(user_prefs)
            except Exception as e:
                logger.warning(f"Failed to extract preferences for {user_id}: {e}")
            
            # Calculate enhanced diversity score based on 6 memory types
            active_memory_types = len([count for count in by_type.values() if count > 0])
            diversity_score = min(1.0, active_memory_types / 6.0)  # 6 memory types max
            
            return {
                'has_data': total_memories > 0,
                'total_memories': total_memories,
                'session_memories': by_type.get('session', 0),
                'episodic_memories': by_type.get('episodic', 0),
                'factual_memories': by_type.get('factual', 0),
                'semantic_memories': by_type.get('semantic', 0),
                'procedural_memories': by_type.get('procedural', 0),
                'working_memories': by_type.get('working', 0),
                'diversity_score': diversity_score,
                'knowledge_diversity': intelligence_metrics.get('knowledge_diversity', 0),
                'preferences': preferences,
                'distribution': by_type,
                'intelligence_metrics': intelligence_metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to extract memory metrics for {user_id}: {e}")
            return {'has_data': False, 'total_memories': 0}

    async def _extract_real_usage_patterns(self, user_id: str) -> Dict[str, Any]:
        """Extract real usage patterns from user_usage_records"""
        try:
            # Get usage statistics (last 30 days)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            usage_stats = await self.usage_repository.get_usage_statistics(user_id, start_date, end_date)
            
            if not usage_stats or usage_stats.total_records == 0:
                return {'has_data': False, 'patterns': {}}
            
            # Analyze real usage patterns
            patterns = {
                'llm_usage_ratio': usage_stats.by_event_type.get('llm_call', 0) / max(1, usage_stats.total_records),
                'ai_chat_ratio': usage_stats.by_event_type.get('ai_chat', 0) / max(1, usage_stats.total_records),
                'average_cost_per_interaction': usage_stats.total_cost_usd / max(1, usage_stats.total_records),
                'average_tokens_per_interaction': usage_stats.total_tokens_used / max(1, usage_stats.total_records),
                'cost_efficiency_tier': self._categorize_cost_efficiency(usage_stats.total_cost_usd, usage_stats.total_records),
                'usage_intensity': self._categorize_usage_intensity(usage_stats.total_records),
                'preferred_models': list(usage_stats.by_model.keys()) if usage_stats.by_model else [],
                'preferred_providers': list(usage_stats.by_provider.keys()) if usage_stats.by_provider else []
            }
            
            return {
                'has_data': True,
                'patterns': patterns,
                'raw_stats': {
                    'total_records': usage_stats.total_records,
                    'total_cost': usage_stats.total_cost_usd,
                    'total_tokens': usage_stats.total_tokens_used,
                    'by_event_type': usage_stats.by_event_type
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to extract usage patterns for {user_id}: {e}")
            return {'has_data': False, 'patterns': {}}

    async def _extract_real_session_patterns(self, user_id: str) -> Dict[str, Any]:
        """Extract real session patterns from sessions table"""
        try:
            # Get recent sessions (last 30 days)
            recent_sessions = await self.session_repository.get_user_recent_sessions(user_id, days=30)
            
            if not recent_sessions:
                return {'has_data': False, 'patterns': {}}
            
            # Analyze session patterns
            active_sessions = [s for s in recent_sessions if s.is_active]
            total_messages = sum(s.message_count for s in recent_sessions if s.message_count)
            total_cost = sum(float(s.total_cost) for s in recent_sessions if s.total_cost)
            
            patterns = {
                'session_frequency': len(recent_sessions) / 30.0,  # sessions per day
                'average_session_length': total_messages / max(1, len(recent_sessions)),
                'session_completion_rate': len(active_sessions) / max(1, len(recent_sessions)),
                'average_session_cost': total_cost / max(1, len(recent_sessions)),
                'engagement_score': min(1.0, total_messages / max(1, len(recent_sessions) * 10)),  # normalized
                'activity_level': self._categorize_activity_level(len(recent_sessions), total_messages)
            }
            
            return {
                'has_data': True,
                'patterns': patterns,
                'raw_stats': {
                    'total_sessions': len(recent_sessions),
                    'active_sessions': len(active_sessions),
                    'total_messages': total_messages,
                    'total_cost': total_cost
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to extract session patterns for {user_id}: {e}")
            return {'has_data': False, 'patterns': {}}

    def _categorize_cost_efficiency(self, total_cost: float, total_records: int) -> str:
        """Categorize user's cost efficiency based on spending patterns"""
        if total_records == 0:
            return 'unknown'
        
        avg_cost = total_cost / total_records
        if avg_cost < 0.01:
            return 'high_efficiency'
        elif avg_cost < 0.05:
            return 'moderate_efficiency'
        else:
            return 'low_efficiency'

    def _categorize_usage_intensity(self, total_records: int) -> str:
        """Categorize usage intensity based on interaction frequency"""
        daily_avg = total_records / 30.0  # assuming 30-day window
        
        if daily_avg >= 5:
            return 'high_intensity'
        elif daily_avg >= 1:
            return 'moderate_intensity'
        else:
            return 'low_intensity'

    def _categorize_activity_level(self, session_count: int, message_count: int) -> str:
        """Categorize user activity level"""
        if session_count >= 10 and message_count >= 50:
            return 'highly_active'
        elif session_count >= 5 and message_count >= 20:
            return 'moderately_active'
        else:
            return 'low_activity'

    def _build_real_intelligence_metrics(self, memory_stats: Dict, usage_stats: Dict) -> Dict[str, Any]:
        """Build intelligence metrics from real data"""
        return {
            'memory_richness': memory_stats.get('diversity_score', 0.3),
            'usage_sophistication': min(1.0, len(usage_stats.get('patterns', {}).get('preferred_models', [])) / 3.0),
            'interaction_complexity': usage_stats.get('patterns', {}).get('average_tokens_per_interaction', 0) / 1000.0,
            'learning_indicators': memory_stats.get('episodic_memories', 0) / max(1, memory_stats.get('total_memories', 1))
        }

    def _extract_real_behavior_patterns(self, usage_stats: Dict, session_stats: Dict) -> Dict[str, Any]:
        """Extract behavior patterns from real usage and session data"""
        return {
            'interaction_style': self._infer_interaction_style(usage_stats, session_stats),
            'usage_consistency': session_stats.get('patterns', {}).get('session_frequency', 0),
            'cost_consciousness': usage_stats.get('patterns', {}).get('cost_efficiency_tier', 'unknown'),
            'engagement_depth': session_stats.get('patterns', {}).get('engagement_score', 0.3)
        }

    def _infer_interaction_style(self, usage_stats: Dict, session_stats: Dict) -> str:
        """Infer interaction style from usage patterns"""
        patterns = usage_stats.get('patterns', {})
        llm_ratio = patterns.get('llm_usage_ratio', 0)
        chat_ratio = patterns.get('ai_chat_ratio', 0)
        
        if llm_ratio > 0.7:
            return 'analytical'
        elif chat_ratio > 0.6:
            return 'conversational'
        else:
            return 'mixed'

    def _infer_communication_style(self, session_stats: Dict, memory_stats: Dict) -> Dict[str, str]:
        """Infer communication style from session and memory data"""
        patterns = session_stats.get('patterns', {})
        avg_length = patterns.get('average_session_length', 5)
        
        if avg_length > 15:
            style = 'detailed'
        elif avg_length > 8:
            style = 'moderate'
        else:
            style = 'concise'
            
        return {'primary_style': style}

    def _infer_expertise_from_usage(self, usage_stats: Dict) -> List[str]:
        """Infer expertise areas from usage patterns"""
        patterns = usage_stats.get('patterns', {})
        models = patterns.get('preferred_models', [])
        
        # Simple heuristics based on model preferences
        expertise = []
        if any('gpt-4' in str(model).lower() for model in models):
            expertise.append('advanced_ai_usage')
        if patterns.get('usage_intensity') == 'high_intensity':
            expertise.append('power_user')
        if patterns.get('cost_efficiency_tier') == 'high_efficiency':
            expertise.append('cost_optimization')
            
        return expertise if expertise else ['general_user']

    async def _ai_enhanced_behavior_analysis(self, usage_stats: Dict, memory_stats: Dict) -> Dict[str, Any]:
        """Use AI to perform enhanced behavior analysis"""
        try:
            # Prepare analysis context
            analysis_context = {
                'usage_patterns': usage_stats.get('patterns', {}),
                'memory_distribution': memory_stats.get('distribution', {}),
                'total_memories': memory_stats.get('total_memories', 0),
                'intelligence_metrics': memory_stats.get('intelligence_metrics', {})
            }
            
            # Use TextExtractor for pattern analysis
            context_text = json.dumps(analysis_context, indent=2)
            patterns_result = await self.text_extractor.analyze_patterns(
                context_text,
                pattern_types=['behavior', 'learning', 'preference']
            )
            
            ai_insights = {}
            if patterns_result.get('success'):
                patterns = patterns_result.get('patterns', [])
                for pattern in patterns:
                    if pattern.get('type') == 'behavior':
                        ai_insights['behavior_complexity'] = pattern.get('confidence', 0.5)
                    elif pattern.get('type') == 'learning':
                        ai_insights['learning_velocity'] = pattern.get('confidence', 0.5)
                    elif pattern.get('type') == 'preference':
                        ai_insights['preference_stability'] = pattern.get('confidence', 0.5)
            
            # Use reasoning for deeper insights
            reasoning_prompt = f"""
            Analyze user behavior based on:
            - Usage intensity: {usage_stats.get('patterns', {}).get('usage_intensity', 'unknown')}
            - Memory types: {memory_stats.get('distribution', {})}
            - Cost efficiency: {usage_stats.get('patterns', {}).get('cost_efficiency_tier', 'unknown')}
            
            Provide insights on user's learning style, expertise level, and growth potential.
            """
            
            reasoning_result = await self.reasoning_generator.generate_reasoning(
                prompt=reasoning_prompt,
                context=analysis_context
            )
            
            if reasoning_result.get('success'):
                ai_insights['reasoning_insights'] = reasoning_result.get('reasoning', 'No insights generated')
            
            return ai_insights
            
        except Exception as e:
            logger.warning(f"AI behavior analysis failed: {e}")
            return {'ai_analysis_available': False}

    async def _get_8d_prediction_analysis(self, user_id: str, memory_stats: Dict, usage_stats: Dict, session_stats: Dict) -> Dict[str, Any]:
        """Get 8-dimensional analysis using DataAnalyticsService for real ML/DL capabilities"""
        try:
            dimensions = {}
            
            # Prepare user behavior data for ML analysis
            user_data = await self._prepare_user_data_for_ml(user_id, memory_stats, usage_stats, session_stats)
            
            if not user_data.get('success'):
                logger.warning(f"Failed to prepare user data for ML analysis: {user_data.get('error')}")
                return {'dimensions': {}, 'overall_confidence': 0.2, 'error': 'Data preparation failed'}
            
            # 1. Temporal Patterns Analysis (使用统计分析)
            try:
                temporal_analysis = await self.data_analytics_service.perform_statistical_analysis(
                    data_path=user_data['temporal_data_path'],
                    analysis_type="comprehensive",
                    target_columns=['session_frequency', 'activity_hours'],
                    request_id=f"temporal_{user_id}"
                )
                if temporal_analysis.get('success'):
                    dimensions['temporal_patterns'] = {
                        'confidence': 0.8,
                        'patterns': temporal_analysis.get('statistical_results', {}),
                        'analysis_type': 'statistical_temporal_analysis',
                        'insights': temporal_analysis.get('business_insights', [])
                    }
            except Exception as e:
                logger.warning(f"Temporal analysis failed: {e}")
                dimensions['temporal_patterns'] = {'confidence': 0.3, 'error': str(e)}
            
            # 2. Usage Pattern Analysis (使用EDA分析)  
            try:
                usage_eda = await self.data_analytics_service.perform_exploratory_data_analysis(
                    data_path=user_data['usage_data_path'],
                    target_column='credits_charged',
                    include_ai_insights=True,
                    request_id=f"usage_eda_{user_id}"
                )
                if usage_eda.get('success'):
                    dimensions['usage_patterns'] = {
                        'confidence': 0.9,
                        'patterns': usage_eda.get('eda_results', {}),
                        'analysis_type': 'exploratory_data_analysis',
                        'insights': usage_eda.get('business_insights', [])
                    }
            except Exception as e:
                logger.warning(f"Usage EDA failed: {e}")
                dimensions['usage_patterns'] = {'confidence': 0.3, 'error': str(e)}
            
            # 3. User Behavior Clustering (使用ML模型)
            try:
                behavior_model = await self.data_analytics_service.develop_machine_learning_model(
                    data_path=user_data['behavior_data_path'],
                    target_column='user_type',
                    problem_type='classification',
                    include_feature_engineering=True,
                    request_id=f"behavior_ml_{user_id}"
                )
                if behavior_model.get('success'):
                    dimensions['user_clustering'] = {
                        'confidence': 0.85,
                        'model_results': behavior_model.get('results', {}),
                        'analysis_type': 'machine_learning_clustering',
                        'features': behavior_model.get('data_preprocessing', {})
                    }
            except Exception as e:
                logger.warning(f"Behavior clustering failed: {e}")
                dimensions['user_clustering'] = {'confidence': 0.3, 'error': str(e)}
            
            # 4. Cost Efficiency Analysis (使用A/B testing framework)
            try:
                if user_data.get('has_comparison_data'):
                    ab_test_result = await self.data_analytics_service.perform_ab_testing(
                        data_path=user_data['efficiency_data_path'],
                        control_group_column='is_baseline_user',
                        treatment_group_column='is_optimized_user', 
                        metric_column='cost_per_interaction',
                        request_id=f"efficiency_ab_{user_id}"
                    )
                    if ab_test_result.get('success'):
                        dimensions['cost_efficiency'] = {
                            'confidence': 0.9,
                            'ab_results': ab_test_result.get('ab_testing_results', {}),
                            'analysis_type': 'ab_testing_analysis',
                            'interpretation': ab_test_result.get('interpretation', {})
                        }
            except Exception as e:
                logger.warning(f"Cost efficiency analysis failed: {e}")
                dimensions['cost_efficiency'] = {'confidence': 0.4, 'fallback_analysis': usage_stats.get('patterns', {})}
            
            # 5. Session Success Prediction (使用时间序列或回归)
            try:
                session_prediction = await self.data_analytics_service.develop_machine_learning_model(
                    data_path=user_data['session_data_path'],
                    target_column='session_success_score',
                    problem_type='regression',
                    include_ai_guidance=True,
                    request_id=f"session_pred_{user_id}"
                )
                if session_prediction.get('success'):
                    dimensions['session_prediction'] = {
                        'confidence': 0.8,
                        'model_results': session_prediction.get('results', {}),
                        'analysis_type': 'regression_prediction',
                        'preprocessing': session_prediction.get('data_preprocessing', {})
                    }
            except Exception as e:
                logger.warning(f"Session prediction failed: {e}")
                dimensions['session_prediction'] = {'confidence': 0.3, 'error': str(e)}
            
            # 6. Memory Pattern Analysis (使用统计和相关性分析)
            try:
                memory_stats_analysis = await self.data_analytics_service.perform_statistical_analysis(
                    data_path=user_data['memory_data_path'],
                    analysis_type="correlations",
                    target_columns=['memory_diversity', 'knowledge_growth'],
                    request_id=f"memory_stats_{user_id}"
                )
                if memory_stats_analysis.get('success'):
                    dimensions['memory_patterns'] = {
                        'confidence': 0.85,
                        'statistical_results': memory_stats_analysis.get('statistical_results', {}),
                        'analysis_type': 'correlation_analysis',
                        'insights': memory_stats_analysis.get('business_insights', [])
                    }
            except Exception as e:
                logger.warning(f"Memory pattern analysis failed: {e}")
                dimensions['memory_patterns'] = {'confidence': 0.3, 'error': str(e)}
            
            # 7. Learning Trajectory Analysis (使用趋势分析)
            try:
                learning_analysis = await self.data_analytics_service.perform_statistical_analysis(
                    data_path=user_data['learning_data_path'],
                    analysis_type="hypothesis_testing",
                    request_id=f"learning_trends_{user_id}"
                )
                if learning_analysis.get('success'):
                    dimensions['learning_trajectory'] = {
                        'confidence': 0.8,
                        'trend_results': learning_analysis.get('statistical_results', {}),
                        'analysis_type': 'hypothesis_testing_trends',
                        'insights': learning_analysis.get('business_insights', [])
                    }
            except Exception as e:
                logger.warning(f"Learning trajectory analysis failed: {e}")
                dimensions['learning_trajectory'] = {'confidence': 0.3, 'error': str(e)}
            
            # 8. Recommendation System Analysis (使用特征重要性和推荐算法)
            try:
                recommendation_model = await self.data_analytics_service.develop_machine_learning_model(
                    data_path=user_data['recommendation_data_path'],
                    target_column='tool_preference_score',
                    problem_type='regression',
                    include_feature_engineering=True,
                    request_id=f"recommendation_{user_id}"
                )
                if recommendation_model.get('success'):
                    dimensions['recommendations'] = {
                        'confidence': 0.9,
                        'model_results': recommendation_model.get('results', {}),
                        'analysis_type': 'recommendation_ml_model',
                        'feature_importance': recommendation_model.get('results', {}).get('feature_importance', {})
                    }
            except Exception as e:
                logger.warning(f"Recommendation analysis failed: {e}")
                dimensions['recommendations'] = {'confidence': 0.3, 'error': str(e)}
            
            # Calculate overall confidence based on successful analyses
            valid_dimensions = [d for d in dimensions.values() if d.get('confidence', 0) > 0.5]
            overall_confidence = sum(d.get('confidence', 0) for d in valid_dimensions) / max(1, len(valid_dimensions))
            
            return {
                'dimensions': dimensions,
                'overall_confidence': overall_confidence,
                'active_dimensions': len(valid_dimensions),
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'data_sources_used': ['DataAnalyticsService_ML', 'DataAnalyticsService_Stats', 'DataAnalyticsService_EDA'],
                'ml_powered': True
            }
            
        except Exception as e:
            logger.error(f"8D ML analysis failed for {user_id}: {e}")
            return {
                'dimensions': {},
                'overall_confidence': 0.2,
                'active_dimensions': 0,
                'error': str(e),
                'ml_powered': False
            }

    async def _prepare_user_data_for_ml(self, user_id: str, memory_stats: Dict, usage_stats: Dict, session_stats: Dict) -> Dict[str, Any]:
        """Prepare user data as CSV files for DataAnalyticsService ML analysis"""
        try:
            import tempfile
            import csv
            import os
            from pathlib import Path
            
            # Create temporary directory for user data
            temp_dir = Path(tempfile.mkdtemp(prefix=f"user_analysis_{user_id}_"))
            
            # 1. Temporal patterns data (from session data)
            temporal_data_path = temp_dir / "temporal_patterns.csv"
            temporal_data = [
                {
                    'user_id': user_id,
                    'session_frequency': session_stats.get('patterns', {}).get('session_frequency', 0),
                    'activity_hours': session_stats.get('patterns', {}).get('average_session_length', 0),
                    'engagement_score': session_stats.get('patterns', {}).get('engagement_score', 0.3),
                    'activity_level': session_stats.get('patterns', {}).get('activity_level', 'low_activity'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            ]
            
            with open(temporal_data_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=temporal_data[0].keys())
                writer.writeheader()
                writer.writerows(temporal_data)
            
            # 2. Usage patterns data (from usage statistics)
            usage_data_path = temp_dir / "usage_patterns.csv"
            usage_raw = usage_stats.get('raw_stats', {})
            usage_patterns = usage_stats.get('patterns', {})
            usage_data = [
                {
                    'user_id': user_id,
                    'total_records': usage_raw.get('total_records', 0),
                    'total_cost': usage_raw.get('total_cost', 0.0),
                    'total_tokens': usage_raw.get('total_tokens', 0),
                    'credits_charged': usage_raw.get('total_cost', 0.0) * 1000,  # Convert to credits
                    'llm_usage_ratio': usage_patterns.get('llm_usage_ratio', 0),
                    'ai_chat_ratio': usage_patterns.get('ai_chat_ratio', 0),
                    'cost_efficiency_tier': usage_patterns.get('cost_efficiency_tier', 'unknown'),
                    'usage_intensity': usage_patterns.get('usage_intensity', 'low_intensity')
                }
            ]
            
            with open(usage_data_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=usage_data[0].keys())
                writer.writeheader()
                writer.writerows(usage_data)
            
            # 3. Behavior clustering data (combine memory and usage)
            behavior_data_path = temp_dir / "behavior_patterns.csv"
            behavior_data = [
                {
                    'user_id': user_id,
                    'memory_diversity': memory_stats.get('diversity_score', 0.3),
                    'total_memories': memory_stats.get('total_memories', 0),
                    'session_memories': memory_stats.get('session_memories', 0),
                    'episodic_memories': memory_stats.get('episodic_memories', 0),
                    'usage_intensity_score': 0.3 if usage_patterns.get('usage_intensity') == 'low_intensity' else 0.7 if usage_patterns.get('usage_intensity') == 'moderate_intensity' else 0.9,
                    'cost_efficiency_score': 0.9 if usage_patterns.get('cost_efficiency_tier') == 'high_efficiency' else 0.5 if usage_patterns.get('cost_efficiency_tier') == 'moderate_efficiency' else 0.2,
                    'user_type': 'analytical' if usage_patterns.get('llm_usage_ratio', 0) > 0.7 else 'conversational' if usage_patterns.get('ai_chat_ratio', 0) > 0.6 else 'mixed'
                }
            ]
            
            with open(behavior_data_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=behavior_data[0].keys())
                writer.writeheader()
                writer.writerows(behavior_data)
            
            # 4. Session success data
            session_data_path = temp_dir / "session_analysis.csv"
            session_data = [
                {
                    'user_id': user_id,
                    'session_completion_rate': session_stats.get('patterns', {}).get('session_completion_rate', 0.5),
                    'average_session_length': session_stats.get('patterns', {}).get('average_session_length', 5),
                    'engagement_score': session_stats.get('patterns', {}).get('engagement_score', 0.3),
                    'total_sessions': session_stats.get('raw_stats', {}).get('total_sessions', 0),
                    'session_success_score': min(1.0, session_stats.get('patterns', {}).get('engagement_score', 0.3) * session_stats.get('patterns', {}).get('session_completion_rate', 0.5) * 2)
                }
            ]
            
            with open(session_data_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=session_data[0].keys())
                writer.writeheader()
                writer.writerows(session_data)
            
            # 5. Memory patterns data
            memory_data_path = temp_dir / "memory_analysis.csv"
            memory_data = [
                {
                    'user_id': user_id,
                    'memory_diversity': memory_stats.get('diversity_score', 0.3),
                    'knowledge_diversity': memory_stats.get('knowledge_diversity', 0),
                    'total_memories': memory_stats.get('total_memories', 0),
                    'knowledge_growth': memory_stats.get('total_memories', 0) / max(1, memory_stats.get('session_memories', 1)),  # Growth ratio
                    'factual_ratio': memory_stats.get('factual_memories', 0) / max(1, memory_stats.get('total_memories', 1)),
                    'episodic_ratio': memory_stats.get('episodic_memories', 0) / max(1, memory_stats.get('total_memories', 1))
                }
            ]
            
            with open(memory_data_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=memory_data[0].keys())
                writer.writeheader()
                writer.writerows(memory_data)
            
            # 6. Learning trajectory data
            learning_data_path = temp_dir / "learning_trajectory.csv"
            learning_data = [
                {
                    'user_id': user_id,
                    'learning_velocity': memory_stats.get('total_memories', 0) / max(1, session_stats.get('raw_stats', {}).get('total_sessions', 1)),
                    'knowledge_retention': memory_stats.get('diversity_score', 0.3),
                    'skill_development': usage_patterns.get('usage_intensity', 'low_intensity') == 'high_intensity',
                    'adaptation_rate': session_stats.get('patterns', {}).get('engagement_score', 0.3)
                }
            ]
            
            with open(learning_data_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=learning_data[0].keys())
                writer.writeheader()
                writer.writerows(learning_data)
            
            # 7. Recommendation data
            recommendation_data_path = temp_dir / "recommendation_analysis.csv"
            recommendation_data = [
                {
                    'user_id': user_id,
                    'preferred_models': len(usage_patterns.get('preferred_models', [])),
                    'model_diversity': min(1.0, len(usage_patterns.get('preferred_models', [])) / 3.0),
                    'tool_usage_breadth': usage_patterns.get('llm_usage_ratio', 0) + usage_patterns.get('ai_chat_ratio', 0),
                    'cost_sensitivity': 0.9 if usage_patterns.get('cost_efficiency_tier') == 'high_efficiency' else 0.3,
                    'tool_preference_score': session_stats.get('patterns', {}).get('engagement_score', 0.3) * usage_raw.get('total_records', 1) / 10.0
                }
            ]
            
            with open(recommendation_data_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=recommendation_data[0].keys())
                writer.writeheader()
                writer.writerows(recommendation_data)
            
            return {
                'success': True,
                'temp_directory': str(temp_dir),
                'temporal_data_path': str(temporal_data_path),
                'usage_data_path': str(usage_data_path),
                'behavior_data_path': str(behavior_data_path),
                'session_data_path': str(session_data_path),
                'memory_data_path': str(memory_data_path),
                'learning_data_path': str(learning_data_path),
                'recommendation_data_path': str(recommendation_data_path),
                'efficiency_data_path': str(usage_data_path),  # Reuse usage data for efficiency analysis
                'has_comparison_data': usage_raw.get('total_records', 0) > 5  # Need enough data for A/B testing
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare ML data for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}

    def _extract_user_preferences(self, predictions_by_type: Dict) -> Dict[str, Any]:
        """Extract user preferences from AI predictions"""
        preferences = {}
        
        # From user needs predictions
        if 'user_needs' in predictions_by_type:
            needs = predictions_by_type['user_needs']
            preferences.update({
                'preferred_tools': needs.required_tools,
                'workflow_style': self._infer_workflow_style(needs),
                'automation_preference': self._assess_automation_preference(needs),
                'complexity_preference': self._assess_complexity_preference(needs)
            })
        
        # From task outcomes
        if 'task_outcomes' in predictions_by_type:
            outcomes = predictions_by_type['task_outcomes']
            preferences.update({
                'risk_tolerance': self._assess_risk_tolerance(outcomes),
                'success_optimization': self._extract_success_strategies(outcomes),
                'planning_style': self._infer_planning_style(outcomes)
            })
        
        return preferences

    def _extract_communication_style(self, predictions_by_type: Dict) -> Dict[str, Any]:
        """Extract communication style from AI predictions"""
        comm_style = {}
        
        # Infer from context patterns
        if 'context_patterns' in predictions_by_type:
            context = predictions_by_type['context_patterns']
            comm_style.update({
                'context_awareness': context.usage_patterns.get('context_sensitivity', 'medium'),
                'information_processing': self._assess_info_processing_style(context),
                'interaction_depth': self._assess_interaction_depth(context),
                'feedback_responsiveness': context.success_indicators.get('feedback_adoption', 'moderate')
            })
        
        return comm_style

    def _extract_expertise_areas(self, predictions_by_type: Dict) -> List[str]:
        """Extract expertise areas from AI predictions"""
        expertise = []
        
        # From multiple prediction sources
        for pred_type, prediction in predictions_by_type.items():
            if hasattr(prediction, 'domain_indicators'):
                expertise.extend(prediction.domain_indicators)
            
            # Infer expertise from tool usage patterns
            if pred_type == 'user_needs' and hasattr(prediction, 'required_tools'):
                expertise.extend(self._infer_expertise_from_tools(prediction.required_tools))
        
        # Deduplicate and return top areas
        return list(set(expertise))[:5]

    def _build_intelligence_metrics(self, predictions_by_type: Dict) -> Dict[str, Any]:
        """Build intelligence metrics from AI predictions"""
        return {
            'prediction_accuracy': sum(p.confidence for p in predictions_by_type.values()) / len(predictions_by_type),
            'pattern_recognition': len(predictions_by_type),
            'adaptability_score': self._calculate_adaptability_score(predictions_by_type),
            'learning_velocity': self._calculate_learning_velocity(predictions_by_type),
            'decision_quality': self._assess_decision_quality(predictions_by_type)
        }

    async def _extract_memory_metrics(self, user_id: str) -> int:
        """Extract memory metrics from memory service"""
        try:
            memory_stats = await self.memory_service.get_memory_statistics(user_id)
            return memory_stats.get('total_memories', 0)
        except:
            return 0

    async def _calculate_knowledge_diversity(self, predictions_by_type: Dict) -> int:
        """Calculate knowledge diversity from predictions"""
        diversity_indicators = len(predictions_by_type)
        for prediction in predictions_by_type.values():
            if hasattr(prediction, 'domain_coverage'):
                diversity_indicators += len(prediction.domain_coverage)
        return min(10, diversity_indicators)

    async def _extract_memory_distribution(self, user_id: str) -> Dict[str, int]:
        """Extract memory distribution from memory service"""
        try:
            memory_stats = await self.memory_service.get_memory_statistics(user_id)
            return memory_stats.get('by_type', {})
        except:
            return {}

    # Helper methods for pattern analysis
    def _categorize_frequency(self, frequency_data: Dict) -> str:
        """Categorize usage frequency from temporal data"""
        if isinstance(frequency_data, dict):
            avg_frequency = frequency_data.get('daily_average', 1.0)
            if avg_frequency > 5:
                return 'very_high'
            elif avg_frequency > 3:
                return 'high'
            elif avg_frequency > 1:
                return 'medium'
            else:
                return 'low'
        return 'unknown'

    def _assess_complexity_from_patterns(self, user_patterns) -> str:
        """Assess complexity handling from user patterns"""
        if hasattr(user_patterns, 'task_preferences'):
            complex_tasks = len([t for t in user_patterns.task_preferences if 'advanced' in t.lower() or 'complex' in t.lower()])
            return 'high' if complex_tasks > 2 else 'medium' if complex_tasks > 0 else 'low'
        return 'medium'

    def _assess_learning_pace(self, user_patterns) -> str:
        """Assess learning pace from patterns"""
        # Simplified assessment based on tool diversity and success patterns
        if hasattr(user_patterns, 'tool_preferences') and hasattr(user_patterns, 'success_patterns'):
            tool_diversity = len(user_patterns.tool_preferences)
            success_rate = user_patterns.success_patterns.get('overall_rate', 0.5) if isinstance(user_patterns.success_patterns, dict) else 0.5
            
            if tool_diversity > 5 and success_rate > 0.8:
                return 'fast'
            elif tool_diversity > 2 and success_rate > 0.6:
                return 'moderate'
            else:
                return 'gradual'
        return 'moderate'

    def _calculate_cost_efficiency(self, resource) -> str:
        """Calculate cost efficiency from resource usage"""
        if hasattr(resource, 'cost_estimate'):
            cost = resource.cost_estimate
            if isinstance(cost, (int, float)):
                return 'high' if cost < 0.1 else 'medium' if cost < 1.0 else 'low'
        return 'unknown'

    def _infer_workflow_style(self, needs) -> str:
        """Infer workflow style from user needs"""
        if hasattr(needs, 'anticipated_tasks'):
            sequential_indicators = len([t for t in needs.anticipated_tasks if any(word in t.lower() for word in ['step', 'sequence', 'order'])])
            return 'sequential' if sequential_indicators > 0 else 'flexible'
        return 'adaptive'

    def _assess_automation_preference(self, needs) -> str:
        """Assess automation preference from needs"""
        if hasattr(needs, 'required_tools'):
            automation_tools = len([t for t in needs.required_tools if 'auto' in t.lower() or 'batch' in t.lower()])
            return 'high' if automation_tools > 2 else 'medium' if automation_tools > 0 else 'low'
        return 'medium'

    def _assess_complexity_preference(self, needs) -> str:
        """Assess complexity preference"""
        if hasattr(needs, 'context_needs'):
            complex_contexts = needs.context_needs.get('complexity_tolerance', 'medium') if isinstance(needs.context_needs, dict) else 'medium'
            return complex_contexts
        return 'medium'

    def _assess_risk_tolerance(self, outcomes) -> str:
        """Assess risk tolerance from task outcomes"""
        if hasattr(outcomes, 'success_probability'):
            return 'high' if outcomes.success_probability > 0.8 else 'medium' if outcomes.success_probability > 0.6 else 'low'
        return 'medium'

    def _extract_success_strategies(self, outcomes) -> List[str]:
        """Extract success strategies from outcomes"""
        if hasattr(outcomes, 'optimization_suggestions'):
            return outcomes.optimization_suggestions[:3]
        return []

    def _infer_planning_style(self, outcomes) -> str:
        """Infer planning style from outcomes"""
        if hasattr(outcomes, 'similar_past_tasks'):
            return 'experience_based' if len(outcomes.similar_past_tasks) > 2 else 'analytical'
        return 'balanced'

    def _assess_info_processing_style(self, context) -> str:
        """Assess information processing style"""
        return 'systematic'  # Simplified

    def _assess_interaction_depth(self, context) -> str:
        """Assess interaction depth preference"""
        return 'detailed'  # Simplified

    def _infer_expertise_from_tools(self, tools: List[str]) -> List[str]:
        """Infer expertise areas from tool usage"""
        expertise_mapping = {
            'data': ['data_analysis', 'statistics', 'visualization'],
            'ml': ['machine_learning', 'ai', 'modeling'],
            'code': ['programming', 'software_development', 'debugging'],
            'text': ['nlp', 'content_analysis', 'writing']
        }
        
        expertise = []
        for tool in tools:
            tool_lower = tool.lower()
            for domain, skills in expertise_mapping.items():
                if domain in tool_lower:
                    expertise.extend(skills)
        
        return list(set(expertise))

    def _calculate_adaptability_score(self, predictions_by_type: Dict) -> float:
        """Calculate adaptability score from predictions"""
        return min(1.0, len(predictions_by_type) / 8.0)

    def _calculate_learning_velocity(self, predictions_by_type: Dict) -> float:
        """Calculate learning velocity from predictions"""
        confidence_scores = [p.confidence for p in predictions_by_type.values()]
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5

    def _assess_decision_quality(self, predictions_by_type: Dict) -> float:
        """Assess decision quality from predictions"""
        if 'task_outcomes' in predictions_by_type:
            outcomes = predictions_by_type['task_outcomes']
            if hasattr(outcomes, 'success_probability'):
                return outcomes.success_probability
        return 0.6
    
    # ===========================================
    # Event-Driven Smart Portrait Updates
    # ===========================================
    
    async def handle_user_event(self, user_id: str, event_type: str, event_data: Dict[str, Any]) -> ServiceResult[bool]:
        """
        处理用户事件并触发智能画像更新
        
        Args:
            user_id: 用户ID
            event_type: 事件类型 (llm_call, ai_chat, session_start, etc.)
            event_data: 事件数据
            
        Returns:
            ServiceResult with success status
        """
        try:
            # 记录事件时间戳
            event_timestamp = datetime.utcnow()
            
            # 更新事件标记
            if user_id not in self.portrait_update_flags:
                self.portrait_update_flags[user_id] = {'needs_update': False, 'last_event': None}
            
            self.portrait_update_flags[user_id]['last_event'] = event_timestamp
            
            # 判断是否需要更新画像
            should_update = await self._should_trigger_portrait_update(user_id, event_type, event_data)
            
            if should_update:
                self.portrait_update_flags[user_id]['needs_update'] = True
                
                # 异步触发画像更新 (避免阻塞主流程)
                await self._trigger_background_portrait_update(user_id, event_type, event_data)
                
                logger.info(f"Triggered portrait update for {user_id} due to {event_type}")
            
            # 存储事件到Event Service (如果可用)
            if self.event_service:
                try:
                    await self.event_service.store_event({
                        'event_type': f'user_portrait_{event_type}',
                        'user_id': user_id,
                        'data': event_data,
                        'timestamp': event_timestamp.isoformat(),
                        'portrait_update_triggered': should_update
                    })
                except Exception as e:
                    logger.warning(f"Failed to store event: {e}")
            
            return ServiceResult.success(should_update, "Event processed successfully")
            
        except Exception as e:
            logger.error(f"Error handling user event {event_type} for {user_id}: {e}")
            return ServiceResult.error(f"Failed to handle user event: {str(e)}")
    
    async def _should_trigger_portrait_update(self, user_id: str, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        智能判断是否需要更新用户画像
        
        基于事件类型、频率和重要性进行判断
        """
        try:
            # 立即触发更新的高优先级事件
            high_priority_events = {
                'session_start',      # 新会话开始
                'first_time_user',    # 首次使用
                'subscription_change', # 订阅变更
                'preference_update'   # 偏好设置更新
            }
            
            if event_type in high_priority_events:
                return True
            
            # 基于用户活跃度的智能触发
            user_flags = self.portrait_update_flags.get(user_id, {})
            last_update = user_flags.get('last_event')
            
            # 如果超过1小时没有更新，且有新活动，则触发更新
            if last_update is None or (datetime.utcnow() - last_update).total_seconds() > 3600:
                return True
            
            # 基于事件数据重要性判断
            if event_type == 'llm_call':
                tokens_used = event_data.get('tokens_used', 0)
                cost_usd = event_data.get('cost_usd', 0)
                # 高消耗调用触发更新
                if tokens_used > 1000 or cost_usd > 0.1:
                    return True
            
            if event_type == 'ai_chat':
                # 长对话或复杂对话触发更新
                message_length = len(event_data.get('message', ''))
                if message_length > 500:
                    return True
            
            # 默认不触发更新
            return False
            
        except Exception as e:
            logger.warning(f"Error in portrait update decision for {user_id}: {e}")
            return False
    
    async def _trigger_background_portrait_update(self, user_id: str, event_type: str, event_data: Dict[str, Any]):
        """
        后台异步更新用户画像
        """
        try:
            # 清除缓存强制重新生成
            if user_id in self.portrait_cache:
                del self.portrait_cache[user_id]
            
            # 创建更新请求
            update_request = UserPortraitAnalysisRequest(
                user_id=user_id,
                analysis_depth='comprehensive',
                include_predictions=True,
                force_regenerate=True
            )
            
            # 执行更新
            portrait_result = await self.generate_user_portrait(update_request)
            
            if portrait_result.is_success:
                # 重置更新标记
                self.portrait_update_flags[user_id]['needs_update'] = False
                
                # 记录更新成功事件
                if self.event_service:
                    await self.event_service.store_event({
                        'event_type': 'portrait_updated',
                        'user_id': user_id,
                        'data': {
                            'trigger_event': event_type,
                            'confidence_score': portrait_result.data.confidence_score,
                            'portrait_version': portrait_result.data.portrait_version
                        },
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
                logger.info(f"Background portrait update completed for {user_id}")
            else:
                logger.warning(f"Background portrait update failed for {user_id}: {portrait_result.message}")
                
        except Exception as e:
            logger.error(f"Error in background portrait update for {user_id}: {e}")
    
    async def get_user_event_timeline(self, user_id: str, limit: int = 50) -> ServiceResult[List[Dict[str, Any]]]:
        """
        获取用户事件时间线
        
        Args:
            user_id: 用户ID
            limit: 返回事件数量限制
            
        Returns:
            ServiceResult with event timeline
        """
        try:
            if not self.event_service:
                return ServiceResult.error("Event service not available")
            
            # 获取用户相关事件
            events = await self.event_service.get_user_events(user_id, limit=limit)
            
            # 按时间排序并格式化
            timeline = []
            for event in events:
                timeline.append({
                    'event_id': event.get('id'),
                    'event_type': event.get('event_type'),
                    'timestamp': event.get('timestamp'),
                    'data': event.get('data', {}),
                    'portrait_impact': event.get('portrait_update_triggered', False)
                })
            
            # 按时间倒序排列
            timeline.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return ServiceResult.success(timeline, f"Retrieved {len(timeline)} events")
            
        except Exception as e:
            logger.error(f"Error getting event timeline for {user_id}: {e}")
            return ServiceResult.error(f"Failed to get event timeline: {str(e)}")
    
    async def force_portrait_refresh_for_all_active_users(self) -> ServiceResult[Dict[str, Any]]:
        """
        为所有活跃用户强制刷新画像 (管理员功能)
        
        Returns:
            ServiceResult with refresh statistics
        """
        try:
            # 获取所有有更新标记的用户
            users_to_refresh = [
                user_id for user_id, flags in self.portrait_update_flags.items()
                if flags.get('needs_update', False)
            ]
            
            # 同时获取最近活跃的用户
            if self.event_service:
                recent_active_users = await self.event_service.get_active_users(hours=24)
                users_to_refresh.extend(recent_active_users)
            
            # 去重
            users_to_refresh = list(set(users_to_refresh))
            
            refresh_stats = {
                'total_users': len(users_to_refresh),
                'successful_refreshes': 0,
                'failed_refreshes': 0,
                'start_time': datetime.utcnow().isoformat()
            }
            
            # 并发刷新画像 (限制并发数避免过载)
            import asyncio
            semaphore = asyncio.Semaphore(5)  # 最多5个并发
            
            async def refresh_single_user(user_id):
                async with semaphore:
                    try:
                        request = UserPortraitAnalysisRequest(
                            user_id=user_id,
                            analysis_depth='comprehensive',
                            force_regenerate=True
                        )
                        result = await self.generate_user_portrait(request)
                        if result.is_success:
                            refresh_stats['successful_refreshes'] += 1
                        else:
                            refresh_stats['failed_refreshes'] += 1
                    except Exception as e:
                        logger.error(f"Failed to refresh portrait for {user_id}: {e}")
                        refresh_stats['failed_refreshes'] += 1
            
            # 执行并发刷新
            await asyncio.gather(*[refresh_single_user(uid) for uid in users_to_refresh])
            
            refresh_stats['end_time'] = datetime.utcnow().isoformat()
            
            logger.info(f"Batch portrait refresh completed: {refresh_stats}")
            return ServiceResult.success(refresh_stats, "Batch refresh completed")
            
        except Exception as e:
            logger.error(f"Error in batch portrait refresh: {e}")
            return ServiceResult.error(f"Failed to batch refresh portraits: {str(e)}")
    
    # ===========================================
    # Session Memory Analysis Integration
    # ===========================================
    
    async def analyze_user_session_memory(self, user_id: str, session_id: str, analysis_depth: str = "comprehensive") -> ServiceResult[Dict[str, Any]]:
        """
        分析用户的特定会话记忆
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            analysis_depth: 分析深度级别
            
        Returns:
            ServiceResult with session memory analysis
        """
        try:
            # 验证用户存在
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # 创建分析请求
            from ..models import SessionAnalysisRequest
            analysis_request = SessionAnalysisRequest(
                session_id=session_id,
                analysis_types=["memory_patterns", "learning_metrics", "cognitive_load"],
                include_ai_analysis=True,
                depth_level=analysis_depth
            )
            
            # 执行Session记忆分析
            analysis_result = await self.session_analysis_service.analyze_session_memory(analysis_request)
            
            if not analysis_result.is_success:
                return ServiceResult.error(f"Session analysis failed: {analysis_result.message}")
            
            # 将分析结果集成到用户画像中
            integration_result = await self._integrate_session_analysis_to_portrait(user_id, analysis_result.data)
            
            return ServiceResult.success({
                'session_analysis': analysis_result.data.model_dump(),
                'portrait_integration': integration_result,
                'analysis_metadata': {
                    'user_id': user_id,
                    'session_id': session_id,
                    'analysis_depth': analysis_depth,
                    'analyzed_at': datetime.utcnow().isoformat()
                }
            }, "Session memory analysis completed")
            
        except Exception as e:
            logger.error(f"Error analyzing user session memory {user_id}/{session_id}: {e}")
            return ServiceResult.error(f"Failed to analyze session memory: {str(e)}")
    
    async def get_user_session_memory_insights(self, user_id: str, limit: int = 10) -> ServiceResult[Dict[str, Any]]:
        """
        获取用户的会话记忆洞察总结
        
        Args:
            user_id: 用户ID
            limit: 分析会话数量限制
            
        Returns:
            ServiceResult with session memory insights
        """
        try:
            # 验证用户存在
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found(f"User not found: {user_id}")
            
            # 获取用户最近的会话
            from ..repositories.session_repository import SessionRepository
            session_repo = SessionRepository()
            recent_sessions = await session_repo.get_user_recent_sessions(user_id, days=30)
            
            if not recent_sessions:
                return ServiceResult.success({
                    'session_count': 0,
                    'insights': [],
                    'summary': "No recent sessions found"
                }, "No recent sessions for analysis")
            
            # 限制分析的会话数量
            sessions_to_analyze = recent_sessions[:limit]
            
            # 并发分析多个会话
            import asyncio
            analysis_tasks = []
            
            for session in sessions_to_analyze:
                analysis_request = SessionAnalysisRequest(
                    session_id=session.session_id,
                    analysis_types=["memory_patterns", "learning_metrics"],
                    include_ai_analysis=False,  # 快速分析，不包含AI增强
                    depth_level="basic"
                )
                task = self.session_analysis_service.analyze_session_memory(analysis_request)
                analysis_tasks.append(task)
            
            # 执行并发分析
            analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # 汇总分析结果
            successful_analyses = []
            for i, result in enumerate(analysis_results):
                if not isinstance(result, Exception) and result.is_success:
                    successful_analyses.append({
                        'session_id': sessions_to_analyze[i].session_id,
                        'analysis': result.data
                    })
            
            # 生成综合洞察
            comprehensive_insights = await self._generate_comprehensive_session_insights(user_id, successful_analyses)
            
            return ServiceResult.success({
                'session_count': len(sessions_to_analyze),
                'analyzed_sessions': len(successful_analyses),
                'insights': comprehensive_insights,
                'analysis_summary': {
                    'total_sessions_analyzed': len(successful_analyses),
                    'analysis_period_days': 30,
                    'insight_categories': len(comprehensive_insights.get('categories', [])),
                    'confidence_score': comprehensive_insights.get('confidence_score', 0.5)
                }
            }, f"Analyzed {len(successful_analyses)} sessions")
            
        except Exception as e:
            logger.error(f"Error getting session memory insights for {user_id}: {e}")
            return ServiceResult.error(f"Failed to get session memory insights: {str(e)}")
    
    async def _integrate_session_analysis_to_portrait(self, user_id: str, session_analysis: Any) -> Dict[str, Any]:
        """
        将会话分析结果集成到用户画像中
        
        Args:
            user_id: 用户ID
            session_analysis: 会话分析结果
            
        Returns:
            Integration result
        """
        try:
            integration_result = {
                'memory_patterns_integrated': False,
                'learning_metrics_updated': False,
                'cognitive_profile_enhanced': False,
                'portrait_version_bumped': False
            }
            
            # 清除缓存以触发画像重新生成
            if user_id in self.portrait_cache:
                del self.portrait_cache[user_id]
                integration_result['portrait_version_bumped'] = True
            
            # 标记需要更新
            if user_id not in self.portrait_update_flags:
                self.portrait_update_flags[user_id] = {'needs_update': False, 'last_event': None}
            
            self.portrait_update_flags[user_id]['needs_update'] = True
            self.portrait_update_flags[user_id]['last_event'] = datetime.utcnow()
            
            # 分析结果影响判断
            if hasattr(session_analysis, 'memory_patterns') and session_analysis.memory_patterns:
                integration_result['memory_patterns_integrated'] = True
            
            if hasattr(session_analysis, 'learning_indicators') and session_analysis.learning_indicators:
                integration_result['learning_metrics_updated'] = True
            
            if hasattr(session_analysis, 'cognitive_load') and session_analysis.cognitive_load:
                integration_result['cognitive_profile_enhanced'] = True
            
            return integration_result
            
        except Exception as e:
            logger.warning(f"Error integrating session analysis: {e}")
            return {'error': str(e)}
    
    async def _generate_comprehensive_session_insights(self, user_id: str, session_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成综合会话记忆洞察
        
        Args:
            user_id: 用户ID
            session_analyses: 会话分析结果列表
            
        Returns:
            Comprehensive insights
        """
        try:
            if not session_analyses:
                return {'categories': [], 'confidence_score': 0.0}
            
            insights = {
                'categories': [],
                'patterns': {},
                'trends': {},
                'recommendations': [],
                'confidence_score': 0.0
            }
            
            # 1. 学习模式分析
            learning_patterns = []
            for analysis in session_analyses:
                session_data = analysis.get('analysis')
                if hasattr(session_data, 'learning_indicators'):
                    learning_indicators = session_data.learning_indicators
                    if isinstance(learning_indicators, dict):
                        concept_acquisition = learning_indicators.get('concept_acquisition', {})
                        if concept_acquisition.get('new_concepts_count', 0) > 0:
                            learning_patterns.append('active_learning')
                        if concept_acquisition.get('reinforced_concepts_count', 0) > 0:
                            learning_patterns.append('knowledge_reinforcement')
            
            if learning_patterns:
                insights['categories'].append('learning_patterns')
                insights['patterns']['learning'] = {
                    'dominant_patterns': list(set(learning_patterns)),
                    'frequency': len(learning_patterns)
                }
            
            # 2. 认知负荷趋势
            cognitive_loads = []
            for analysis in session_analyses:
                session_data = analysis.get('analysis')
                if hasattr(session_data, 'cognitive_load'):
                    cognitive_load = session_data.cognitive_load
                    if isinstance(cognitive_load, dict):
                        total_load = cognitive_load.get('total_cognitive_load', 0)
                        if total_load > 0:
                            cognitive_loads.append(total_load)
            
            if cognitive_loads:
                avg_cognitive_load = sum(cognitive_loads) / len(cognitive_loads)
                insights['categories'].append('cognitive_trends')
                insights['trends']['cognitive_load'] = {
                    'average_load': avg_cognitive_load,
                    'load_stability': 1.0 - (max(cognitive_loads) - min(cognitive_loads)) if len(cognitive_loads) > 1 else 1.0,
                    'overload_sessions': len([load for load in cognitive_loads if load > 0.8])
                }
            
            # 3. 参与度分析
            engagement_indicators = []
            for analysis in session_analyses:
                session_data = analysis.get('analysis')
                if hasattr(session_data, 'total_messages'):
                    message_count = session_data.total_messages
                    duration = getattr(session_data, 'duration_minutes', 0)
                    if message_count > 0 and duration > 0:
                        engagement_score = min(1.0, (message_count / duration) * 0.5)  # messages per minute
                        engagement_indicators.append(engagement_score)
            
            if engagement_indicators:
                avg_engagement = sum(engagement_indicators) / len(engagement_indicators)
                insights['categories'].append('engagement_patterns')
                insights['patterns']['engagement'] = {
                    'average_engagement': avg_engagement,
                    'engagement_consistency': 1.0 - (max(engagement_indicators) - min(engagement_indicators)) if len(engagement_indicators) > 1 else 1.0
                }
            
            # 4. 生成建议
            if insights['patterns'].get('learning', {}).get('frequency', 0) > len(session_analyses) * 0.7:
                insights['recommendations'].append("用户表现出强烈的学习意愿，建议提供更多挑战性内容")
            
            if insights['trends'].get('cognitive_load', {}).get('average_load', 0) > 0.8:
                insights['recommendations'].append("用户认知负荷较高，建议分解复杂任务")
            
            if insights['patterns'].get('engagement', {}).get('average_engagement', 0) < 0.3:
                insights['recommendations'].append("用户参与度较低，建议增加互动性内容")
            
            # 5. 计算置信度
            confidence_factors = [
                min(1.0, len(session_analyses) / 5.0),  # 会话数量因子
                1.0 if len(insights['categories']) > 0 else 0.0,  # 分析完整性因子
                min(1.0, len(insights['recommendations']) / 3.0)  # 建议质量因子
            ]
            insights['confidence_score'] = sum(confidence_factors) / len(confidence_factors)
            
            return insights
            
        except Exception as e:
            logger.warning(f"Error generating comprehensive insights: {e}")
            return {'categories': [], 'confidence_score': 0.0, 'error': str(e)}