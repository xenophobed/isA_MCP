#!/usr/bin/env python3
"""
RAG Factory - RAG服务工厂

替代enhanced_rag_service.py，使用Factory模式管理所有RAG服务实例。

New Architecture (Migrated):
- ✅ SimpleRAGService (basic vector retrieval)
- ✅ CRAGRAGService (quality-aware retrieval)
- ✅ SelfRAGService (self-reflection)
- ✅ RAGFusionService (multi-query + RRF)
- ✅ HyDERAGService (hypothetical document embeddings)
- ✅ RAPTORRAGService (hierarchical tree structure)
- TODO: PlanRAGService, GraphRAGService, etc.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Type
from datetime import datetime

from .base.base_rag_service import BaseRAGService
from .base.rag_models import RAGConfig, RAGResult, RAGMode
from .patterns.simple_rag_service import SimpleRAGService
from .patterns.crag_rag_service import CRAGRAGService  # ✅ Migrated
from .patterns.self_rag_service import SelfRAGService  # ✅ Migrated
from .patterns.rag_fusion_service import RAGFusionService  # ✅ Migrated
from .patterns.hyde_rag_service import HyDERAGService  # ✅ Migrated
from .patterns.raptor_rag_service import RAPTORRAGService  # ✅ Migrated
from .patterns.graph_rag_service import GraphRAGService  # ✅ Migrated

# TODO: Migrate these services to new architecture
# from .patterns.plan_rag_service import PlanRAGRAGService
# from .patterns.hm_rag_service import HMRAGRAGService

logger = logging.getLogger(__name__)


# ============================================================================
# Simple Factory Function (Used by digital_tools.py)
# ============================================================================

def get_rag_service(
    mode: str = "simple",
    config: Optional[Dict[str, Any]] = None
) -> BaseRAGService:
    """
    Get RAG service instance - Simple factory function for digital_tools.py

    Args:
        mode: RAG mode - currently only "simple" is migrated
        config: Configuration dictionary

    Returns:
        BaseRAGService instance

    Example:
        service = get_rag_service(mode='simple', config={'chunk_size': 400})
        result = await service.store(request)
    """
    config = config or {}

    if mode == "simple":
        rag_config = RAGConfig(
            mode=RAGMode.SIMPLE,
            chunk_size=config.get('chunk_size', 400),
            overlap=config.get('overlap', 50),
            top_k=config.get('top_k', 5),
            embedding_model=config.get('embedding_model', 'text-embedding-3-small'),
            enable_rerank=config.get('enable_rerank', False),
            similarity_threshold=config.get('similarity_threshold', 0.7),
            max_context_length=config.get('max_context_length', 4000)
        )
        return SimpleRAGService(rag_config)
    elif mode == "crag":
        rag_config = RAGConfig(
            mode=RAGMode.CRAG,
            chunk_size=config.get('chunk_size', 400),
            overlap=config.get('overlap', 50),
            top_k=config.get('top_k', 5),
            embedding_model=config.get('embedding_model', 'text-embedding-3-small'),
            enable_rerank=config.get('enable_rerank', False),
            similarity_threshold=config.get('similarity_threshold', 0.7),
            max_context_length=config.get('max_context_length', 4000)
        )
        return CRAGRAGService(rag_config)
    elif mode == "self_rag":
        rag_config = RAGConfig(
            mode=RAGMode.SELF_RAG,
            chunk_size=config.get('chunk_size', 400),
            overlap=config.get('overlap', 50),
            top_k=config.get('top_k', 5),
            embedding_model=config.get('embedding_model', 'text-embedding-3-small'),
            enable_rerank=config.get('enable_rerank', False),
            similarity_threshold=config.get('similarity_threshold', 0.7),
            max_context_length=config.get('max_context_length', 4000),
            enable_self_reflection=True  # Self-RAG specific
        )
        return SelfRAGService(rag_config)
    elif mode == "rag_fusion":
        rag_config = RAGConfig(
            mode=RAGMode.RAG_FUSION,
            chunk_size=config.get('chunk_size', 400),
            overlap=config.get('overlap', 50),
            top_k=config.get('top_k', 5),
            embedding_model=config.get('embedding_model', 'text-embedding-3-small'),
            enable_rerank=config.get('enable_rerank', False),
            similarity_threshold=config.get('similarity_threshold', 0.7),
            max_context_length=config.get('max_context_length', 4000),
            extra_config={
                'num_queries': config.get('num_queries', 3),
                'fusion_weight': config.get('fusion_weight', 'equal')
            }
        )
        return RAGFusionService(rag_config)
    elif mode == "hyde":
        rag_config = RAGConfig(
            mode=RAGMode.HYDE,
            chunk_size=config.get('chunk_size', 400),
            overlap=config.get('overlap', 50),
            top_k=config.get('top_k', 5),
            embedding_model=config.get('embedding_model', 'text-embedding-3-small'),
            enable_rerank=config.get('enable_rerank', False),
            similarity_threshold=config.get('similarity_threshold', 0.7),
            max_context_length=config.get('max_context_length', 4000),
            extra_config={
                'hyde_model': config.get('hyde_model', 'gpt-4.1-nano'),
                'num_hypotheses': config.get('num_hypotheses', 1)
            }
        )
        return HyDERAGService(rag_config)
    elif mode == "raptor":
        rag_config = RAGConfig(
            mode=RAGMode.RAPTOR,
            chunk_size=config.get('chunk_size', 400),
            overlap=config.get('overlap', 50),
            top_k=config.get('top_k', 5),
            embedding_model=config.get('embedding_model', 'text-embedding-3-small'),
            enable_rerank=config.get('enable_rerank', False),
            similarity_threshold=config.get('similarity_threshold', 0.7),
            max_context_length=config.get('max_context_length', 4000),
            extra_config={
                'cluster_threshold': config.get('cluster_threshold', 0.8),
                'max_summary_length': config.get('max_summary_length', 500)
            }
        )
        return RAPTORRAGService(rag_config)
    elif mode == "graph":
        rag_config = RAGConfig(
            mode=RAGMode.GRAPH,
            chunk_size=config.get('chunk_size', 400),
            overlap=config.get('overlap', 50),
            top_k=config.get('top_k', 5),
            embedding_model=config.get('embedding_model', 'text-embedding-3-small'),
            enable_rerank=config.get('enable_rerank', False),
            similarity_threshold=config.get('similarity_threshold', 0.7),
            max_context_length=config.get('max_context_length', 4000),
            extra_config={
                'neo4j_host': config.get('neo4j_host'),
                'neo4j_port': config.get('neo4j_port', 50063),
                'neo4j_database': config.get('neo4j_database', 'neo4j'),
                'graph_expansion_depth': config.get('graph_expansion_depth', 2)
            }
        )
        return GraphRAGService(rag_config)
    else:
        raise ValueError(
            f"Unknown RAG mode: {mode}. "
            f"Currently 'simple', 'crag', 'self_rag', 'rag_fusion', 'hyde', 'raptor', and 'graph' modes are supported. "
            f"Other modes need migration to new architecture."
        )


def get_simple_rag_service(config: Optional[Dict[str, Any]] = None) -> BaseRAGService:
    """Convenience function for simple RAG"""
    return get_rag_service(mode="simple", config=config)


def get_crag_rag_service(config: Optional[Dict[str, Any]] = None) -> BaseRAGService:
    """Convenience function for CRAG (quality-aware RAG)"""
    return get_rag_service(mode="crag", config=config)


def get_self_rag_service(config: Optional[Dict[str, Any]] = None) -> BaseRAGService:
    """Convenience function for Self-RAG (self-reflection)"""
    return get_rag_service(mode="self_rag", config=config)


def get_rag_fusion_service(config: Optional[Dict[str, Any]] = None) -> BaseRAGService:
    """Convenience function for RAG Fusion (multi-query + RRF)"""
    return get_rag_service(mode="rag_fusion", config=config)


def get_hyde_rag_service(config: Optional[Dict[str, Any]] = None) -> BaseRAGService:
    """Convenience function for HyDE RAG (hypothetical document embeddings)"""
    return get_rag_service(mode="hyde", config=config)


def get_raptor_rag_service(config: Optional[Dict[str, Any]] = None) -> BaseRAGService:
    """Convenience function for RAPTOR RAG (hierarchical tree structure)"""
    return get_rag_service(mode="raptor", config=config)


def get_graph_rag_service(config: Optional[Dict[str, Any]] = None) -> BaseRAGService:
    """Convenience function for Graph RAG (knowledge graph enhanced)"""
    return get_rag_service(mode="graph", config=config)


# ============================================================================
# Legacy RAGFactory Class (For backward compatibility)
# ============================================================================

class RAGFactory:
    """RAG服务工厂 (Legacy - use get_rag_service() instead)"""

    def __init__(self):
        self._services: Dict[RAGMode, Type[BaseRAGService]] = {
            RAGMode.SIMPLE: SimpleRAGService,
            RAGMode.CRAG: CRAGRAGService,  # ✅ Migrated
            RAGMode.SELF_RAG: SelfRAGService,  # ✅ Migrated
            RAGMode.RAG_FUSION: RAGFusionService,  # ✅ Migrated
            RAGMode.HYDE: HyDERAGService,  # ✅ Migrated
            RAGMode.RAPTOR: RAPTORRAGService,  # ✅ Migrated
            RAGMode.GRAPH: GraphRAGService,  # ✅ Migrated
            # TODO: Migrate other services
            # RAGMode.PLAN_RAG: PlanRAGRAGService,
            # RAGMode.HM_RAG: HMRAGRAGService,
        }
        self._instances: Dict[str, BaseRAGService] = {}

        logger.info(f"RAG Factory initialized with {len(self._services)} service types")
    
    def create_service(self, 
                      mode: RAGMode, 
                      config: Optional[RAGConfig] = None,
                      instance_id: Optional[str] = None) -> BaseRAGService:
        """
        创建RAG服务实例
        
        Args:
            mode: RAG模式
            config: 配置
            instance_id: 实例ID (用于缓存)
            
        Returns:
            RAG服务实例
        """
        if mode not in self._services:
            raise ValueError(f"Unsupported RAG mode: {mode}")
        
        # 如果提供了实例ID，尝试返回缓存的实例
        if instance_id and instance_id in self._instances:
            return self._instances[instance_id]
        
        # 创建新实例
        config = config or RAGConfig(mode=mode)
        service_class = self._services[mode]
        instance = service_class(config)
        
        # 缓存实例
        if instance_id:
            self._instances[instance_id] = instance
        
        return instance
    
    def get_available_modes(self) -> List[RAGMode]:
        """获取可用的RAG模式"""
        return list(self._services.keys())
    
    def get_service_info(self, mode: RAGMode) -> Dict[str, Any]:
        """获取服务信息"""
        if mode not in self._services:
            return {}
        
        # 创建临时实例获取能力信息
        temp_instance = self.create_service(mode)
        return temp_instance.get_capabilities()
    
    def register_service(self, mode: RAGMode, service_class: Type[BaseRAGService]):
        """注册新的RAG服务"""
        self._services[mode] = service_class
        logger.info(f"Registered new RAG service for mode: {mode}")
    
    def unregister_service(self, mode: RAGMode):
        """注销RAG服务"""
        if mode in self._services:
            del self._services[mode]
            logger.info(f"Unregistered RAG service for mode: {mode}")
    
    def clear_cache(self):
        """清空实例缓存"""
        self._instances.clear()
        logger.info("Cleared RAG service instance cache")

class RAGRegistry:
    """RAG服务注册器"""
    
    def __init__(self, factory: RAGFactory):
        self.factory = factory
        self._mode_priorities: Dict[RAGMode, int] = {}
        self._mode_requirements: Dict[RAGMode, List[str]] = {}
        
        # 设置默认优先级
        self._set_default_priorities()
        self._set_default_requirements()
    
    def _set_default_priorities(self):
        """设置默认优先级"""
        priorities = {
            RAGMode.SIMPLE: 1,
            RAGMode.SELF_RAG: 2,
            RAGMode.CRAG: 3,
            RAGMode.RAPTOR: 4,
            RAGMode.PLAN_RAG: 5,
            RAGMode.HM_RAG: 6
        }
        self._mode_priorities.update(priorities)
    
    def _set_default_requirements(self):
        """设置默认需求"""
        requirements = {
            RAGMode.SIMPLE: [],
            RAGMode.SELF_RAG: ['reflection'],
            RAGMode.CRAG: ['quality_assessment'],
            RAGMode.RAPTOR: ['hierarchical_processing'],
            RAGMode.PLAN_RAG: ['structured_reasoning'],
            RAGMode.HM_RAG: ['multi_agent_collaboration']
        }
        self._mode_requirements.update(requirements)
    
    def register_mode_priority(self, mode: RAGMode, priority: int):
        """注册模式优先级"""
        self._mode_priorities[mode] = priority
        logger.info(f"Set priority {priority} for mode {mode}")
    
    def register_mode_requirements(self, mode: RAGMode, requirements: List[str]):
        """注册模式需求"""
        self._mode_requirements[mode] = requirements
        logger.info(f"Set requirements {requirements} for mode {mode}")
    
    def get_recommended_mode(self, 
                           query: str, 
                           user_id: str,
                           available_requirements: List[str] = None) -> RAGMode:
        """
        根据查询特征推荐RAG模式
        
        Args:
            query: 查询字符串
            user_id: 用户ID
            available_requirements: 可用需求
            
        Returns:
            推荐的RAG模式
        """
        # 分析查询特征
        query_features = self._analyze_query_features(query)
        
        # 过滤可用模式
        available_modes = self._filter_available_modes(available_requirements)
        
        # 根据特征和优先级推荐模式
        recommended_mode = self._select_best_mode(query_features, available_modes)
        
        logger.info(f"Recommended mode {recommended_mode} for query: {query[:50]}...")
        return recommended_mode
    
    def get_mode_comparison(self) -> Dict[str, Any]:
        """获取模式对比信息"""
        comparison = {}
        for mode in self.factory.get_available_modes():
            info = self.factory.get_service_info(mode)
            comparison[mode.value] = {
                'name': info.get('name', mode.value),
                'description': info.get('description', ''),
                'features': info.get('features', []),
                'best_for': info.get('best_for', []),
                'complexity': info.get('complexity', 'unknown'),
                'priority': self._mode_priorities.get(mode, 0)
            }
        return comparison
    
    def _analyze_query_features(self, query: str) -> Dict[str, Any]:
        """分析查询特征"""
        features = {
            'length': len(query.split()),
            'has_questions': '?' in query,
            'has_comparisons': any(word in query.lower() for word in ['compare', 'versus', 'vs']),
            'has_why': 'why' in query.lower(),
            'has_how': 'how' in query.lower(),
            'has_explain': 'explain' in query.lower(),
            'complexity': 0.0
        }
        
        # 计算复杂度
        complexity_indicators = [
            features['has_comparisons'],
            features['has_why'] or features['has_how'],
            features['has_explain'],
            features['length'] > 10
        ]
        features['complexity'] = sum(complexity_indicators) / len(complexity_indicators)
        
        return features
    
    def _filter_available_modes(self, requirements: List[str] = None) -> List[RAGMode]:
        """过滤可用模式"""
        if not requirements:
            return self.factory.get_available_modes()
        
        available_modes = []
        for mode in self.factory.get_available_modes():
            mode_requirements = self._mode_requirements.get(mode, [])
            if all(req in requirements for req in mode_requirements):
                available_modes.append(mode)
        
        return available_modes
    
    def _select_best_mode(self, features: Dict[str, Any], available_modes: List[RAGMode]) -> RAGMode:
        """选择最佳模式"""
        if not available_modes:
            return RAGMode.SIMPLE
        
        # 根据复杂度和优先级选择
        if features['complexity'] > 0.7:
            # 复杂查询，优先选择高级模式
            for mode in [RAGMode.HM_RAG, RAGMode.PLAN_RAG, RAGMode.RAPTOR]:
                if mode in available_modes:
                    return mode
        elif features['complexity'] > 0.4:
            # 中等复杂度，选择中等模式
            for mode in [RAGMode.SELF_RAG, RAGMode.CRAG]:
                if mode in available_modes:
                    return mode
        
        # 默认返回Simple RAG
        return RAGMode.SIMPLE

class RAGService:
    """主RAG服务 - Facade模式"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.factory = RAGFactory()
        self.registry = RAGRegistry(self.factory)
        
        # 性能监控
        self.performance_metrics = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'mode_usage': {mode.value: 0 for mode in RAGMode},
            'average_response_time': 0.0,
            'mode_performance': {mode.value: [] for mode in RAGMode}
        }
        
        logger.info("Main RAG Service initialized")
    
    async def query(self, 
                   query: str, 
                   user_id: str,
                   mode: Optional[RAGMode] = None,
                   context: Optional[str] = None,
                   auto_mode_selection: bool = False) -> RAGResult:
        """
        统一查询接口
        
        Args:
            query: 查询字符串
            user_id: 用户ID
            mode: RAG模式 (如果为None则自动选择)
            context: 上下文信息
            auto_mode_selection: 是否启用自动模式选择
            
        Returns:
            RAG结果
        """
        start_time = time.time()
        
        try:
            # 自动模式选择
            if auto_mode_selection and mode is None:
                mode = self.registry.get_recommended_mode(query, user_id)
                logger.info(f"Auto-selected RAG mode: {mode}")
            
            mode = mode or self.config.mode
            
            # 获取服务实例
            service = self.factory.create_service(mode, self.config)
            
            # 执行查询
            result = await service.query(query, user_id, context)
            
            # 性能监控
            processing_time = time.time() - start_time
            self._update_performance_metrics(mode, processing_time, result.success)
            
            return result
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=mode or RAGMode.SIMPLE,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             mode: Optional[RAGMode] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """处理文档"""
        start_time = time.time()
        
        try:
            mode = mode or self.config.mode
            service = self.factory.create_service(mode, self.config)
            result = await service.process_document(content, user_id, metadata)
            
            # 性能监控
            processing_time = time.time() - start_time
            self._update_performance_metrics(mode, processing_time, result.success)
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
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
                if mode in self.factory.get_available_modes():
                    service = self.factory.create_service(mode, self.config)
                    task = service.query(query, user_id, context)
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
    
    def get_available_modes(self) -> List[RAGMode]:
        """获取可用模式"""
        return self.factory.get_available_modes()
    
    def get_mode_info(self, mode: RAGMode) -> Dict[str, Any]:
        """获取模式信息"""
        return self.factory.get_service_info(mode)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
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
    
    def get_mode_comparison(self) -> Dict[str, Any]:
        """获取模式对比"""
        return self.registry.get_mode_comparison()
    
    async def recommend_mode(self, query: str, user_id: str) -> Dict[str, Any]:
        """推荐RAG模式"""
        try:
            # 分析查询特征
            features = self.registry._analyze_query_features(query)
            
            # 推荐模式
            recommended_mode = self.registry.get_recommended_mode(query, user_id)
            
            # 获取模式信息
            mode_info = self.get_mode_info(recommended_mode)
            
            return {
                'recommended_mode': recommended_mode.value,
                'mode_info': mode_info,
                'query_features': features,
                'confidence': 0.8  # 推荐置信度
            }
            
        except Exception as e:
            logger.error(f"Mode recommendation failed: {e}")
            return {
                'recommended_mode': RAGMode.SIMPLE.value,
                'mode_info': self.get_mode_info(RAGMode.SIMPLE),
                'error': str(e)
            }
    
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

# 全局实例
rag_service = RAGService()
