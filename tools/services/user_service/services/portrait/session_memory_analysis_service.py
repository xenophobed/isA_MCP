"""
Session Memory Analysis Service Implementation

综合的Session记忆分析服务
结合AI分析、ML模型和认知科学理论，深度分析用户会话中的记忆模式
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import json
import asyncio
from collections import defaultdict, Counter
import re

from tools.services.user_service.models import (
    Session, SessionMessage, SessionMemory,
    SessionAnalysisResult, SessionMemoryPattern, SessionLearningMetrics,
    SessionCognitiveLoad, SessionAnalysisRequest
)
from tools.services.user_service.repositories.session_repository import SessionRepository, SessionMessageRepository, SessionMemoryRepository
from tools.services.user_service.services.base import BaseService, ServiceResult

# Memory Service integration
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools.services.memory_service.memory_service import memory_service

# Intelligence Service for NLP analysis
from tools.services.intelligence_service.language.text_extractor import TextExtractor
from tools.services.intelligence_service.language.reasoning_generator import ReasoningGenerator

# DataAnalyticsService for ML-powered analysis
from tools.services.data_analytics_service.services.data_analytics_service import DataAnalyticsService

logger = logging.getLogger(__name__)


class SessionMemoryAnalysisService(BaseService):
    """Session记忆分析服务"""
    
    def __init__(self):
        super().__init__("SessionMemoryAnalysisService")
        
        # Repository层
        self.session_repo = SessionRepository()
        self.message_repo = SessionMessageRepository()
        self.memory_repo = SessionMemoryRepository()
        
        # AI服务集成
        self.memory_service = memory_service
        self.text_extractor = TextExtractor()
        self.reasoning_generator = ReasoningGenerator()
        self.data_analytics_service = DataAnalyticsService("session_memory_analytics")
        
        # 认知负荷理论参数
        self.cognitive_load_thresholds = {
            'intrinsic': 0.6,    # 内在认知负荷阈值
            'extraneous': 0.3,   # 外在认知负荷阈值
            'germane': 0.8,      # 有效认知负荷目标
            'total': 1.0         # 总认知负荷上限
        }
        
        # 学习指标权重
        self.learning_metrics_weights = {
            'concept_acquisition': 0.3,
            'skill_development': 0.25,
            'problem_solving': 0.2,
            'critical_thinking': 0.15,
            'creativity': 0.1
        }
    
    async def analyze_session_memory(self, request: SessionAnalysisRequest) -> ServiceResult[SessionAnalysisResult]:
        """
        综合分析Session记忆
        
        Args:
            request: 分析请求
            
        Returns:
            ServiceResult with SessionAnalysisResult
        """
        try:
            session_id = request.session_id
            
            # 获取会话基础信息
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                return ServiceResult.not_found(f"Session not found: {session_id}")
            
            # 获取会话消息
            messages = await self.message_repo.get_session_messages(session_id, limit=1000)
            if not messages:
                return ServiceResult.error("No messages found for analysis")
            
            self._log_operation("analyze_session_memory", f"Session: {session_id}, Messages: {len(messages)}")
            
            # 执行多维度分析
            analysis_results = {}
            
            # 1. 基础会话指标
            basic_metrics = await self._calculate_basic_metrics(session, messages)
            analysis_results.update(basic_metrics)
            
            # 2. 记忆模式分析
            if "memory_patterns" in request.analysis_types:
                memory_patterns = await self._analyze_memory_patterns(session_id, messages)
                analysis_results["memory_patterns"] = memory_patterns
            
            # 3. 学习指标分析
            if "learning_metrics" in request.analysis_types:
                learning_metrics = await self._analyze_learning_metrics(session_id, messages)
                analysis_results["learning_indicators"] = learning_metrics
            
            # 4. 认知负荷分析
            if "cognitive_load" in request.analysis_types:
                cognitive_load = await self._analyze_cognitive_load(session_id, messages)
                analysis_results["cognitive_load"] = cognitive_load
            
            # 5. AI增强分析 (如果启用)
            if request.include_ai_analysis:
                ai_analysis = await self._perform_ai_enhanced_analysis(session_id, messages, request.depth_level)
                analysis_results.update(ai_analysis)
            
            # 6. 综合评分
            comprehensive_scores = await self._calculate_comprehensive_scores(analysis_results)
            analysis_results.update(comprehensive_scores)
            
            # 构建结果
            result = SessionAnalysisResult(
                session_id=session_id,
                user_id=session.user_id,
                analysis_type="comprehensive_memory_analysis",
                confidence_score=self._calculate_analysis_confidence(analysis_results),
                **analysis_results
            )
            
            logger.info(f"Session memory analysis completed for {session_id}")
            return ServiceResult.success(result, "Session memory analysis completed")
            
        except Exception as e:
            logger.error(f"Error analyzing session memory {request.session_id}: {e}")
            return ServiceResult.error(f"Failed to analyze session memory: {str(e)}")
    
    async def _calculate_basic_metrics(self, session: Session, messages: List[SessionMessage]) -> Dict[str, Any]:
        """计算基础会话指标"""
        try:
            # 基础统计
            total_messages = len(messages)
            total_tokens = sum(msg.tokens_used or 0 for msg in messages)
            total_cost = sum(msg.cost_usd or 0.0 for msg in messages)
            
            # 计算会话时长
            if messages and len(messages) > 1:
                first_message_time = min(msg.created_at for msg in messages if msg.created_at)
                last_message_time = max(msg.created_at for msg in messages if msg.created_at)
                duration_minutes = (last_message_time - first_message_time).total_seconds() / 60
            else:
                duration_minutes = 0.0
            
            return {
                'total_messages': total_messages,
                'total_tokens': total_tokens,
                'total_cost': total_cost,
                'duration_minutes': duration_minutes
            }
            
        except Exception as e:
            logger.warning(f"Error calculating basic metrics: {e}")
            return {
                'total_messages': 0,
                'total_tokens': 0,
                'total_cost': 0.0,
                'duration_minutes': 0.0
            }
    
    async def _analyze_memory_patterns(self, session_id: str, messages: List[SessionMessage]) -> Dict[str, Any]:
        """分析会话中的记忆模式"""
        try:
            patterns = {
                'repetition_patterns': [],
                'concept_evolution': [],
                'knowledge_building': {},
                'context_switching': [],
                'pattern_strength_distribution': {}
            }
            
            # 1. 重复模式分析
            message_contents = [msg.content for msg in messages if msg.content]
            word_frequency = Counter()
            
            for content in message_contents:
                words = re.findall(r'\b\w+\b', content.lower())
                word_frequency.update(words)
            
            # 找出高频概念
            high_freq_concepts = [
                {'concept': word, 'frequency': freq}
                for word, freq in word_frequency.most_common(10)
                if freq > 2 and len(word) > 3
            ]
            patterns['repetition_patterns'] = high_freq_concepts
            
            # 2. 概念演进分析
            concept_timeline = defaultdict(list)
            for i, msg in enumerate(messages):
                if msg.role == 'user':
                    # 提取用户消息中的关键概念
                    key_concepts = await self._extract_key_concepts(msg.content)
                    for concept in key_concepts:
                        concept_timeline[concept].append(i)
            
            # 分析概念发展轨迹
            for concept, appearances in concept_timeline.items():
                if len(appearances) > 1:
                    patterns['concept_evolution'].append({
                        'concept': concept,
                        'first_mention': appearances[0],
                        'last_mention': appearances[-1],
                        'development_span': appearances[-1] - appearances[0],
                        'frequency': len(appearances)
                    })
            
            # 3. 知识构建模式
            patterns['knowledge_building'] = await self._analyze_knowledge_building_patterns(messages)
            
            # 4. 上下文切换分析
            patterns['context_switching'] = await self._analyze_context_switching(messages)
            
            # 5. 模式强度分布
            patterns['pattern_strength_distribution'] = self._calculate_pattern_strength_distribution(patterns)
            
            return patterns
            
        except Exception as e:
            logger.warning(f"Error analyzing memory patterns: {e}")
            return {'error': str(e)}
    
    async def _analyze_learning_metrics(self, session_id: str, messages: List[SessionMessage]) -> Dict[str, Any]:
        """分析学习指标"""
        try:
            metrics = {
                'concept_acquisition': {},
                'skill_development': {},
                'problem_solving': {},
                'critical_thinking': {},
                'learning_trajectory': {}
            }
            
            user_messages = [msg for msg in messages if msg.role == 'user']
            assistant_messages = [msg for msg in messages if msg.role == 'assistant']
            
            # 1. 概念获取分析
            new_concepts = set()
            reinforced_concepts = set()
            
            for msg in assistant_messages:
                concepts = await self._extract_key_concepts(msg.content)
                if len(concepts) > 0:
                    # 简化的新概念识别逻辑
                    for concept in concepts:
                        if any(concept.lower() in prev_msg.content.lower() for prev_msg in user_messages[:user_messages.index(msg)] if prev_msg in user_messages):
                            reinforced_concepts.add(concept)
                        else:
                            new_concepts.add(concept)
            
            metrics['concept_acquisition'] = {
                'new_concepts_count': len(new_concepts),
                'reinforced_concepts_count': len(reinforced_concepts),
                'concept_diversity': len(new_concepts) + len(reinforced_concepts),
                'new_concepts': list(new_concepts)[:10],  # 限制返回数量
                'reinforced_concepts': list(reinforced_concepts)[:10]
            }
            
            # 2. 技能发展分析
            skill_indicators = await self._analyze_skill_development_indicators(messages)
            metrics['skill_development'] = skill_indicators
            
            # 3. 问题解决能力分析
            problem_solving_analysis = await self._analyze_problem_solving_patterns(messages)
            metrics['problem_solving'] = problem_solving_analysis
            
            # 4. 批判性思维分析
            critical_thinking_analysis = await self._analyze_critical_thinking_indicators(messages)
            metrics['critical_thinking'] = critical_thinking_analysis
            
            # 5. 学习轨迹分析
            metrics['learning_trajectory'] = await self._analyze_learning_trajectory(messages)
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Error analyzing learning metrics: {e}")
            return {'error': str(e)}
    
    async def _analyze_cognitive_load(self, session_id: str, messages: List[SessionMessage]) -> Dict[str, Any]:
        """分析认知负荷"""
        try:
            load_analysis = {
                'intrinsic_load': 0.0,
                'extraneous_load': 0.0,
                'germane_load': 0.0,
                'total_cognitive_load': 0.0,
                'load_progression': [],
                'overload_indicators': []
            }
            
            # 按消息分析认知负荷变化
            for i, msg in enumerate(messages):
                if msg.role == 'user':
                    # 分析用户消息的认知负荷指标
                    message_load = await self._calculate_message_cognitive_load(msg, i, messages)
                    load_analysis['load_progression'].append({
                        'message_index': i,
                        'intrinsic': message_load['intrinsic'],
                        'extraneous': message_load['extraneous'],
                        'germane': message_load['germane'],
                        'total': message_load['total']
                    })
                    
                    # 检测过载指标
                    if message_load['total'] > self.cognitive_load_thresholds['total']:
                        load_analysis['overload_indicators'].append({
                            'message_index': i,
                            'load_level': message_load['total'],
                            'load_type': 'total_overload'
                        })
            
            # 计算平均认知负荷
            if load_analysis['load_progression']:
                avg_intrinsic = sum(item['intrinsic'] for item in load_analysis['load_progression']) / len(load_analysis['load_progression'])
                avg_extraneous = sum(item['extraneous'] for item in load_analysis['load_progression']) / len(load_analysis['load_progression'])
                avg_germane = sum(item['germane'] for item in load_analysis['load_progression']) / len(load_analysis['load_progression'])
                
                load_analysis['intrinsic_load'] = avg_intrinsic
                load_analysis['extraneous_load'] = avg_extraneous
                load_analysis['germane_load'] = avg_germane
                load_analysis['total_cognitive_load'] = avg_intrinsic + avg_extraneous + avg_germane
            
            # 生成优化建议
            load_analysis['optimization_suggestions'] = self._generate_cognitive_load_suggestions(load_analysis)
            
            return load_analysis
            
        except Exception as e:
            logger.warning(f"Error analyzing cognitive load: {e}")
            return {'error': str(e)}
    
    async def _perform_ai_enhanced_analysis(self, session_id: str, messages: List[SessionMessage], depth_level: str) -> Dict[str, Any]:
        """执行AI增强分析"""
        try:
            ai_analysis = {
                'semantic_coherence': 0.0,
                'knowledge_extraction': {},
                'behavioral_insights': []
            }
            
            # 准备会话内容用于AI分析
            conversation_text = self._prepare_conversation_for_analysis(messages)
            
            if not conversation_text.strip():
                return ai_analysis
            
            # 1. 语义连贯性分析 (使用TextExtractor)
            try:
                semantic_analysis = await self.text_extractor.extract_semantic_features(conversation_text)
                if semantic_analysis and 'coherence_score' in semantic_analysis:
                    ai_analysis['semantic_coherence'] = semantic_analysis['coherence_score']
            except Exception as e:
                logger.warning(f"Semantic analysis failed: {e}")
            
            # 2. 知识提取 (使用ReasoningGenerator)
            try:
                knowledge_extraction = await self.reasoning_generator.extract_knowledge_patterns(conversation_text)
                ai_analysis['knowledge_extraction'] = knowledge_extraction or {}
            except Exception as e:
                logger.warning(f"Knowledge extraction failed: {e}")
            
            # 3. 行为洞察生成
            try:
                behavioral_insights = await self._generate_behavioral_insights(messages, depth_level)
                ai_analysis['behavioral_insights'] = behavioral_insights
            except Exception as e:
                logger.warning(f"Behavioral insights generation failed: {e}")
            
            # 4. 使用DataAnalyticsService进行ML增强分析
            if depth_level == "comprehensive":
                try:
                    ml_analysis = await self._perform_ml_enhanced_session_analysis(session_id, messages)
                    ai_analysis.update(ml_analysis)
                except Exception as e:
                    logger.warning(f"ML enhanced analysis failed: {e}")
            
            return ai_analysis
            
        except Exception as e:
            logger.warning(f"Error in AI enhanced analysis: {e}")
            return {'error': str(e)}
    
    async def _calculate_comprehensive_scores(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """计算综合评分"""
        try:
            scores = {
                'session_quality_score': 0.0,
                'engagement_level': 'medium',
                'satisfaction_prediction': 0.5
            }
            
            # 计算会话质量评分 (基于多个维度)
            quality_factors = []
            
            # 基于消息数量和时长
            if analysis_results.get('total_messages', 0) > 0:
                message_density = analysis_results.get('total_messages', 0) / max(analysis_results.get('duration_minutes', 1), 1)
                quality_factors.append(min(1.0, message_density / 2.0))  # 理想密度 2 messages/min
            
            # 基于学习指标
            learning_metrics = analysis_results.get('learning_indicators', {})
            if learning_metrics and 'concept_acquisition' in learning_metrics:
                concept_score = min(1.0, learning_metrics['concept_acquisition'].get('concept_diversity', 0) / 10.0)
                quality_factors.append(concept_score)
            
            # 基于认知负荷
            cognitive_load = analysis_results.get('cognitive_load', {})
            if cognitive_load and 'total_cognitive_load' in cognitive_load:
                load_score = max(0.0, 1.0 - cognitive_load['total_cognitive_load'])
                quality_factors.append(load_score)
            
            # 基于语义连贯性
            semantic_score = analysis_results.get('semantic_coherence', 0.0)
            if semantic_score > 0:
                quality_factors.append(semantic_score)
            
            # 计算加权平均
            if quality_factors:
                scores['session_quality_score'] = sum(quality_factors) / len(quality_factors)
            
            # 参与度级别判断
            if scores['session_quality_score'] > 0.8:
                scores['engagement_level'] = 'high'
            elif scores['session_quality_score'] > 0.6:
                scores['engagement_level'] = 'medium'
            else:
                scores['engagement_level'] = 'low'
            
            # 满意度预测 (基于质量评分和参与度)
            satisfaction_base = scores['session_quality_score']
            
            # 调整因素
            if analysis_results.get('total_messages', 0) > 20:  # 长对话通常满意度更高
                satisfaction_base += 0.1
            
            if cognitive_load.get('overload_indicators'):  # 认知过载降低满意度
                satisfaction_base -= 0.2
            
            scores['satisfaction_prediction'] = max(0.0, min(1.0, satisfaction_base))
            
            return scores
            
        except Exception as e:
            logger.warning(f"Error calculating comprehensive scores: {e}")
            return {
                'session_quality_score': 0.5,
                'engagement_level': 'medium',
                'satisfaction_prediction': 0.5
            }
    
    # ===========================================
    # 辅助方法
    # ===========================================
    
    async def _extract_key_concepts(self, text: str) -> List[str]:
        """提取文本中的关键概念"""
        try:
            if not text or not text.strip():
                return []
            
            # 使用TextExtractor提取关键概念
            features = await self.text_extractor.extract_semantic_features(text)
            if features and 'key_concepts' in features:
                return features['key_concepts'][:10]  # 限制数量
            
            # 回退到简单的关键词提取
            words = re.findall(r'\b[A-Za-z]{4,}\b', text)
            return list(set(words))[:10]
            
        except Exception as e:
            logger.warning(f"Error extracting key concepts: {e}")
            return []
    
    def _prepare_conversation_for_analysis(self, messages: List[SessionMessage]) -> str:
        """准备会话内容用于AI分析"""
        try:
            conversation_parts = []
            for msg in messages[-50:]:  # 只分析最后50条消息
                if msg.content and msg.content.strip():
                    role_prefix = f"[{msg.role.upper()}]"
                    conversation_parts.append(f"{role_prefix} {msg.content}")
            
            return "\n".join(conversation_parts)
            
        except Exception as e:
            logger.warning(f"Error preparing conversation: {e}")
            return ""
    
    def _calculate_analysis_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """计算分析置信度"""
        try:
            confidence_factors = []
            
            # 基于消息数量
            message_count = analysis_results.get('total_messages', 0)
            message_confidence = min(1.0, message_count / 20.0)  # 20条消息达到最高置信度
            confidence_factors.append(message_confidence)
            
            # 基于分析完整性
            completed_analyses = 0
            total_analyses = 4  # memory_patterns, learning_indicators, cognitive_load, ai_analysis
            
            if analysis_results.get('memory_patterns'):
                completed_analyses += 1
            if analysis_results.get('learning_indicators'):
                completed_analyses += 1
            if analysis_results.get('cognitive_load'):
                completed_analyses += 1
            if analysis_results.get('semantic_coherence', 0) > 0:
                completed_analyses += 1
            
            analysis_completeness = completed_analyses / total_analyses
            confidence_factors.append(analysis_completeness)
            
            # 基于数据质量
            if analysis_results.get('duration_minutes', 0) > 5:  # 有意义的对话时长
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.5)
            
            return sum(confidence_factors) / len(confidence_factors)
            
        except Exception as e:
            logger.warning(f"Error calculating confidence: {e}")
            return 0.5
    
    # 占位符方法 - 实际实现可以更加复杂
    async def _analyze_knowledge_building_patterns(self, messages: List[SessionMessage]) -> Dict[str, Any]:
        """分析知识构建模式"""
        return {
            'building_blocks': [],
            'connection_patterns': [],
            'depth_progression': 0.0
        }
    
    async def _analyze_context_switching(self, messages: List[SessionMessage]) -> List[Dict[str, Any]]:
        """分析上下文切换"""
        return []
    
    def _calculate_pattern_strength_distribution(self, patterns: Dict[str, Any]) -> Dict[str, float]:
        """计算模式强度分布"""
        return {
            'strong_patterns': 0.0,
            'medium_patterns': 0.0,
            'weak_patterns': 0.0
        }
    
    async def _analyze_skill_development_indicators(self, messages: List[SessionMessage]) -> Dict[str, Any]:
        """分析技能发展指标"""
        return {
            'technical_skills': [],
            'soft_skills': [],
            'progression_rate': 0.0
        }
    
    async def _analyze_problem_solving_patterns(self, messages: List[SessionMessage]) -> Dict[str, Any]:
        """分析问题解决模式"""
        return {
            'problem_identification': 0.0,
            'solution_exploration': 0.0,
            'implementation_success': 0.0
        }
    
    async def _analyze_critical_thinking_indicators(self, messages: List[SessionMessage]) -> Dict[str, Any]:
        """分析批判性思维指标"""
        return {
            'questioning_patterns': [],
            'evidence_evaluation': 0.0,
            'logical_reasoning': 0.0
        }
    
    async def _analyze_learning_trajectory(self, messages: List[SessionMessage]) -> Dict[str, Any]:
        """分析学习轨迹"""
        return {
            'learning_curve': [],
            'mastery_progression': 0.0,
            'retention_indicators': []
        }
    
    async def _calculate_message_cognitive_load(self, message: SessionMessage, index: int, all_messages: List[SessionMessage]) -> Dict[str, float]:
        """计算单个消息的认知负荷"""
        # 简化实现
        content_length = len(message.content) if message.content else 0
        complexity_factor = min(1.0, content_length / 500.0)
        
        return {
            'intrinsic': complexity_factor * 0.4,
            'extraneous': 0.2,  # 固定值
            'germane': complexity_factor * 0.3,
            'total': complexity_factor * 0.7 + 0.2
        }
    
    def _generate_cognitive_load_suggestions(self, load_analysis: Dict[str, Any]) -> List[str]:
        """生成认知负荷优化建议"""
        suggestions = []
        
        if load_analysis.get('total_cognitive_load', 0) > 0.8:
            suggestions.append("考虑将复杂问题分解为更小的步骤")
            suggestions.append("增加解释性内容以降低内在认知负荷")
        
        if load_analysis.get('extraneous_load', 0) > 0.4:
            suggestions.append("减少不相关信息的干扰")
            suggestions.append("优化信息呈现方式")
        
        return suggestions
    
    async def _generate_behavioral_insights(self, messages: List[SessionMessage], depth_level: str) -> List[str]:
        """生成行为洞察"""
        insights = []
        
        user_messages = [msg for msg in messages if msg.role == 'user']
        if len(user_messages) > 10:
            insights.append("用户表现出高参与度的对话行为")
        
        # 基于消息模式的简单洞察
        avg_message_length = sum(len(msg.content or '') for msg in user_messages) / max(len(user_messages), 1)
        if avg_message_length > 100:
            insights.append("用户倾向于提供详细的问题描述")
        
        return insights
    
    async def _perform_ml_enhanced_session_analysis(self, session_id: str, messages: List[SessionMessage]) -> Dict[str, Any]:
        """执行ML增强的会话分析"""
        try:
            # 准备数据用于ML分析
            session_data = self._prepare_session_data_for_ml(session_id, messages)
            
            # 使用DataAnalyticsService进行统计分析
            analysis_result = await self.data_analytics_service.perform_statistical_analysis(
                data=session_data,
                analysis_type="comprehensive",
                request_id=f"session_analysis_{session_id}"
            )
            
            return {
                'ml_insights': analysis_result.get('insights', []),
                'statistical_patterns': analysis_result.get('patterns', {}),
                'predictive_indicators': analysis_result.get('predictions', {})
            }
            
        except Exception as e:
            logger.warning(f"ML enhanced analysis failed: {e}")
            return {}
    
    def _prepare_session_data_for_ml(self, session_id: str, messages: List[SessionMessage]) -> Dict[str, Any]:
        """为ML分析准备会话数据"""
        return {
            'session_id': session_id,
            'message_count': len(messages),
            'user_message_count': len([m for m in messages if m.role == 'user']),
            'assistant_message_count': len([m for m in messages if m.role == 'assistant']),
            'total_tokens': sum(m.tokens_used or 0 for m in messages),
            'total_cost': sum(m.cost_usd or 0.0 for m in messages),
            'avg_message_length': sum(len(m.content or '') for m in messages) / max(len(messages), 1)
        }