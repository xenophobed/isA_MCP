#!/usr/bin/env python3
"""
Enhanced RAG Service - 升级版多模式RAG服务

整合所有前沿RAG模式:
- Simple RAG: 传统向量检索
- Graph RAG: 基于知识图谱的检索  
- RAPTOR RAG: 层次化文档组织
- Self-RAG: 自我反思RAG
- CRAG: 检索质量评估RAG
- Plan*RAG: 结构化推理RAG
- HM-RAG: 多智能体协作RAG
- Hybrid RAG: 混合模式
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import time

from tools.services.intelligence_service.language.embedding_generator import embed, search, chunk, rerank, hybrid_search_local, enhanced_search, store_knowledge_local
from core.database.supabase_client import get_supabase_client
from resources.graph_knowledge_resources import graph_knowledge_resources

# 导入所有RAG模式
from .multi_mode_rag_service import (
    RAGMode, RAGConfig, RAGResult, BaseRAGPattern,
    SimpleRAGPattern, RAPTORRAGPattern, SelfRAGPattern
)
from .advanced_rag_patterns import (
    CRAGRAGPattern, PlanRAGPattern, HMRAGPattern
)

logger = logging.getLogger(__name__)

class EnhancedRAGService:
    """增强版多模式RAG服务"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.supabase = get_supabase_client()
        self.table_name = "user_knowledge"
        
        # 初始化所有RAG模式
        self.patterns = {
            RAGMode.SIMPLE: SimpleRAGPattern(self.config),
            RAGMode.RAPTOR: RAPTORRAGPattern(self.config),
            RAGMode.SELF_RAG: SelfRAGPattern(self.config),
            RAGMode.CRAG: CRAGRAGPattern(self.config),
            RAGMode.PLAN_RAG: PlanRAGPattern(self.config),
            RAGMode.HM_RAG: HMRAGPattern(self.config),
        }
        
        # 性能监控
        self.performance_metrics = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'mode_usage': {mode.value: 0 for mode in RAGMode},
            'average_response_time': 0.0,
            'mode_performance': {mode.value: [] for mode in RAGMode}
        }
        
        logger.info(f"Enhanced RAG Service initialized with {len(self.patterns)} patterns")
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             mode: Optional[RAGMode] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理文档 - 支持多种RAG模式
        
        Args:
            content: 文档内容
            user_id: 用户ID
            mode: RAG模式，如果为None则使用默认模式
            metadata: 元数据
            
        Returns:
            处理结果
        """
        mode = mode or self.config.mode
        start_time = time.time()
        
        try:
            if mode not in self.patterns:
                return {
                    'success': False,
                    'error': f'RAG mode {mode} not supported',
                    'available_modes': [m.value for m in self.patterns.keys()]
                }
            
            pattern = self.patterns[mode]
            result = await pattern.process_document(content, user_id, metadata)
            
            # 更新性能指标
            processing_time = time.time() - start_time
            self._update_performance_metrics(mode, processing_time, result['success'])
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed for mode {mode}: {e}")
            return {
                'success': False,
                'error': str(e),
                'mode_used': mode.value if mode else 'unknown'
            }
    
    async def query(self, 
                   query: str, 
                   user_id: str,
                   mode: Optional[RAGMode] = None,
                   context: Optional[str] = None,
                   auto_mode_selection: bool = False) -> RAGResult:
        """
        查询处理 - 支持多种RAG模式和自动模式选择
        
        Args:
            query: 查询字符串
            user_id: 用户ID
            mode: RAG模式，如果为None则使用默认模式或自动选择
            context: 上下文信息
            auto_mode_selection: 是否启用自动模式选择
            
        Returns:
            RAG结果
        """
        start_time = time.time()
        
        try:
            # 自动模式选择
            if auto_mode_selection and mode is None:
                mode = await self._select_optimal_mode(query, user_id)
                logger.info(f"Auto-selected RAG mode: {mode}")
            
            mode = mode or self.config.mode
            
            if mode not in self.patterns:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': f'RAG mode {mode} not supported'},
                    mode_used=mode,
                    processing_time=0,
                    error=f'RAG mode {mode} not supported'
                )
            
            pattern = self.patterns[mode]
            result = await pattern.query(query, user_id, context)
            
            # 更新性能指标
            processing_time = time.time() - start_time
            self._update_performance_metrics(mode, processing_time, result.success)
            
            return result
            
        except Exception as e:
            logger.error(f"Query failed for mode {mode}: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=mode or RAGMode.SIMPLE,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def hybrid_query(self, 
                          query: str, 
                          user_id: str,
                          modes: Optional[List[RAGMode]] = None,
                          context: Optional[str] = None) -> RAGResult:
        """
        混合查询 - 使用多个RAG模式并整合结果
        
        Args:
            query: 查询字符串
            user_id: 用户ID
            modes: 要使用的RAG模式列表
            context: 上下文信息
            
        Returns:
            整合的RAG结果
        """
        start_time = time.time()
        
        try:
            # 默认使用所有可用模式
            if modes is None:
                modes = [RAGMode.SIMPLE, RAGMode.RAPTOR, RAGMode.SELF_RAG]
            
            # 并行执行多个模式
            tasks = []
            for mode in modes:
                if mode in self.patterns:
                    task = self.patterns[mode].query(query, user_id, context)
                    tasks.append((mode, task))
            
            # 等待所有任务完成
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # 整合结果
            mode_results = {}
            for i, (mode, _) in enumerate(tasks):
                if isinstance(results[i], Exception):
                    logger.error(f"Mode {mode} failed: {results[i]}")
                    mode_results[mode] = None
                else:
                    mode_results[mode] = results[i]
            
            # 合并结果
            integrated_result = await self._integrate_hybrid_results(query, mode_results)
            
            return RAGResult(
                success=True,
                content=integrated_result['content'],
                sources=integrated_result['sources'],
                metadata={
                    'hybrid_mode': True,
                    'modes_used': [mode.value for mode in modes],
                    'mode_results': {mode.value: result.success if result else False for mode, result in mode_results.items()},
                    'integration_method': 'weighted_average'
                },
                mode_used=RAGMode.HYBRID,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Hybrid query failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=RAGMode.HYBRID,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def _select_optimal_mode(self, query: str, user_id: str) -> RAGMode:
        """
        自动选择最优RAG模式
        
        Args:
            query: 查询字符串
            user_id: 用户ID
            
        Returns:
            最优RAG模式
        """
        try:
            # 分析查询特征
            query_features = await self._analyze_query_features(query)
            
            # 检查用户知识库中是否有数据
            has_data = await self._check_user_has_data(user_id)
            if not has_data:
                logger.warning(f"No data found for user {user_id}, using Simple RAG")
                return RAGMode.SIMPLE
            
            # 基于特征选择模式
            if query_features['complexity'] > 0.7:
                if query_features['requires_reasoning']:
                    return RAGMode.PLAN_RAG
                elif query_features['requires_analysis']:
                    return RAGMode.HM_RAG
                else:
                    return RAGMode.RAPTOR
            elif query_features['requires_quality']:
                return RAGMode.CRAG
            elif query_features['requires_reflection']:
                return RAGMode.SELF_RAG
            else:
                return RAGMode.SIMPLE
                
        except Exception as e:
            logger.error(f"Mode selection failed: {e}")
            return RAGMode.SIMPLE
    
    async def _check_user_has_data(self, user_id: str) -> bool:
        """检查用户是否有数据"""
        try:
            result = self.supabase.table(self.table_name)\
                                 .select('id')\
                                 .eq('user_id', user_id)\
                                 .limit(1)\
                                 .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to check user data: {e}")
            return False
    
    async def _analyze_query_features(self, query: str) -> Dict[str, Any]:
        """分析查询特征"""
        features = {
            'complexity': 0.0,
            'requires_reasoning': False,
            'requires_analysis': False,
            'requires_quality': False,
            'requires_reflection': False,
            'length': len(query.split()),
            'has_questions': '?' in query,
            'has_comparisons': any(word in query.lower() for word in ['compare', 'versus', 'vs', 'difference']),
            'has_why': 'why' in query.lower(),
            'has_how': 'how' in query.lower(),
            'has_explain': 'explain' in query.lower()
        }
        
        # 计算复杂度
        complexity_indicators = [
            features['has_comparisons'],
            features['has_why'] or features['has_how'],
            features['has_explain'],
            features['length'] > 10
        ]
        features['complexity'] = sum(complexity_indicators) / len(complexity_indicators)
        
        # 设置特征标志
        features['requires_reasoning'] = features['has_why'] or features['has_how']
        features['requires_analysis'] = features['has_comparisons'] or features['has_explain']
        features['requires_quality'] = 'accurate' in query.lower() or 'precise' in query.lower()
        features['requires_reflection'] = 'think' in query.lower() or 'consider' in query.lower()
        
        return features
    
    async def _integrate_hybrid_results(self, query: str, mode_results: Dict[RAGMode, RAGResult]) -> Dict[str, Any]:
        """整合混合结果"""
        # 收集所有成功的结果
        successful_results = {mode: result for mode, result in mode_results.items() if result and result.success}
        
        if not successful_results:
            return {
                'content': "No successful results from any RAG mode",
                'sources': [],
                'confidence': 0.0
            }
        
        # 合并内容
        content_parts = []
        all_sources = []
        confidence_scores = []
        
        for mode, result in successful_results.items():
            content_parts.append(f"[{mode.value.upper()}] {result.content}")
            all_sources.extend(result.sources)
            
            # 计算置信度
            confidence = self._calculate_result_confidence(result)
            confidence_scores.append(confidence)
        
        # 生成整合内容
        integrated_content = self._generate_integrated_content(query, content_parts, confidence_scores)
        
        # 去重和排序源
        unique_sources = self._deduplicate_sources(all_sources)
        
        return {
            'content': integrated_content,
            'sources': unique_sources,
            'confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
            'mode_count': len(successful_results)
        }
    
    def _calculate_result_confidence(self, result: RAGResult) -> float:
        """计算结果置信度"""
        confidence = 0.5  # 基础置信度
        
        # 基于源数量
        if result.sources:
            confidence += min(len(result.sources) * 0.1, 0.3)
        
        # 基于处理时间（越快越好）
        if result.processing_time < 1.0:
            confidence += 0.1
        elif result.processing_time > 5.0:
            confidence -= 0.1
        
        # 基于内容长度
        if len(result.content) > 100:
            confidence += 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    def _generate_integrated_content(self, query: str, content_parts: List[str], confidence_scores: List[float]) -> str:
        """生成整合内容"""
        if not content_parts:
            return f"No relevant information found for query: '{query}'"
        
        # 按置信度排序
        sorted_parts = sorted(zip(content_parts, confidence_scores), key=lambda x: x[1], reverse=True)
        
        # 构建整合内容
        integrated = f"Based on multiple RAG analysis methods, here's what I found for '{query}':\n\n"
        
        for i, (content, confidence) in enumerate(sorted_parts):
            integrated += f"Analysis {i+1} (Confidence: {confidence:.2f}):\n{content}\n\n"
        
        return integrated
    
    def _deduplicate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重源"""
        seen = set()
        unique_sources = []
        
        for source in sources:
            source_key = source.get('knowledge_id', source.get('text', ''))
            if source_key not in seen:
                seen.add(source_key)
                unique_sources.append(source)
        
        return unique_sources
    
    def _update_performance_metrics(self, mode: RAGMode, processing_time: float, success: bool):
        """更新性能指标"""
        self.performance_metrics['total_queries'] += 1
        
        if success:
            self.performance_metrics['successful_queries'] += 1
        else:
            self.performance_metrics['failed_queries'] += 1
        
        self.performance_metrics['mode_usage'][mode.value] += 1
        self.performance_metrics['mode_performance'][mode.value].append(processing_time)
        
        # 更新平均响应时间
        total_time = sum(
            sum(times) for times in self.performance_metrics['mode_performance'].values()
        )
        total_queries = self.performance_metrics['total_queries']
        self.performance_metrics['average_response_time'] = total_time / total_queries if total_queries > 0 else 0.0
    
    async def get_available_modes(self) -> List[RAGMode]:
        """获取可用模式"""
        return list(self.patterns.keys())
    
    async def get_mode_info(self, mode: RAGMode) -> Dict[str, Any]:
        """获取模式信息"""
        mode_info = {
            RAGMode.SIMPLE: {
                'name': 'Simple RAG',
                'description': '传统向量检索RAG',
                'features': ['向量相似度检索', '文档分块', '简单上下文构建'],
                'best_for': ['简单问答', '事实查询', '快速检索'],
                'complexity': 'low'
            },
            RAGMode.RAPTOR: {
                'name': 'RAPTOR RAG',
                'description': '层次化文档组织RAG',
                'features': ['层次化树结构', '多级摘要', '复杂推理支持'],
                'best_for': ['长文档分析', '复杂推理', '多层次信息检索'],
                'complexity': 'high'
            },
            RAGMode.SELF_RAG: {
                'name': 'Self-RAG',
                'description': '自我反思RAG',
                'features': ['自我评估', '质量修正', '减少幻觉'],
                'best_for': ['高质量回答', '准确性要求高', '减少错误'],
                'complexity': 'medium'
            },
            RAGMode.CRAG: {
                'name': 'CRAG',
                'description': '检索质量评估RAG',
                'features': ['质量评估', '动态调整', '噪声过滤'],
                'best_for': ['大规模检索', '质量要求高', '噪声数据'],
                'complexity': 'medium'
            },
            RAGMode.PLAN_RAG: {
                'name': 'Plan*RAG',
                'description': '结构化推理RAG',
                'features': ['推理计划', '并行执行', '结构化思考'],
                'best_for': ['复杂推理', '多步分析', '逻辑推理'],
                'complexity': 'high'
            },
            RAGMode.HM_RAG: {
                'name': 'HM-RAG',
                'description': '多智能体协作RAG',
                'features': ['多智能体', '协作处理', '多模态支持'],
                'best_for': ['复杂任务', '多模态数据', '协作分析'],
                'complexity': 'high'
            },
            RAGMode.HYBRID: {
                'name': 'Hybrid RAG',
                'description': '混合模式RAG',
                'features': ['多模式整合', '自动选择', '结果融合'],
                'best_for': ['复杂查询', '最佳性能', '自适应处理'],
                'complexity': 'adaptive'
            }
        }
        
        return mode_info.get(mode, {'name': 'Unknown', 'description': 'Unknown mode'})
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        # 计算各模式的平均性能
        mode_averages = {}
        for mode, times in self.performance_metrics['mode_performance'].items():
            if times:
                mode_averages[mode] = {
                    'average_time': sum(times) / len(times),
                    'query_count': len(times),
                    'success_rate': self.performance_metrics['successful_queries'] / max(self.performance_metrics['total_queries'], 1)
                }
        
        return {
            'total_queries': self.performance_metrics['total_queries'],
            'successful_queries': self.performance_metrics['successful_queries'],
            'failed_queries': self.performance_metrics['failed_queries'],
            'success_rate': self.performance_metrics['successful_queries'] / max(self.performance_metrics['total_queries'], 1),
            'average_response_time': self.performance_metrics['average_response_time'],
            'mode_usage': self.performance_metrics['mode_usage'],
            'mode_performance': mode_averages
        }
    
    async def recommend_mode(self, query: str, user_id: str) -> Dict[str, Any]:
        """推荐RAG模式"""
        try:
            # 分析查询特征
            features = await self._analyze_query_features(query)
            
            # 获取用户历史偏好
            user_preferences = await self._get_user_preferences(user_id)
            
            # 推荐模式
            recommended_mode = await self._select_optimal_mode(query, user_id)
            
            # 获取模式信息
            mode_info = await self.get_mode_info(recommended_mode)
            
            return {
                'recommended_mode': recommended_mode.value,
                'mode_info': mode_info,
                'query_features': features,
                'user_preferences': user_preferences,
                'confidence': 0.8  # 推荐置信度
            }
            
        except Exception as e:
            logger.error(f"Mode recommendation failed: {e}")
            return {
                'recommended_mode': RAGMode.SIMPLE.value,
                'mode_info': await self.get_mode_info(RAGMode.SIMPLE),
                'error': str(e)
            }
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好"""
        # 从数据库获取用户历史偏好
        try:
            result = self.supabase.table('user_preferences')\
                                 .select('rag_mode_preferences, performance_preferences')\
                                 .eq('user_id', user_id)\
                                 .single()\
                                 .execute()
            
            if result.data:
                return result.data
            else:
                return {'rag_mode_preferences': {}, 'performance_preferences': {}}
                
        except Exception as e:
            logger.warning(f"Failed to get user preferences: {e}")
            return {'rag_mode_preferences': {}, 'performance_preferences': {}}

# 全局实例
enhanced_rag_service = EnhancedRAGService()
