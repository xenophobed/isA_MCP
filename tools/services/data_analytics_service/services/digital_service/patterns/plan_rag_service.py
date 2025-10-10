#!/usr/bin/env python3
"""
Plan*RAG Service - 结构化推理RAG实现

基于advanced_rag_patterns.py中的PlanRAGPattern，实现独立的Plan*RAG服务。
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..base.base_rag_service import BaseRAGService, RAGResult, RAGMode, RAGConfig

logger = logging.getLogger(__name__)

@dataclass
class ReasoningPlan:
    """推理计划"""
    steps: List[Dict[str, Any]]
    dependencies: List[Tuple[int, int]]
    parallel_executable: List[List[int]]
    estimated_complexity: float

class PlanRAGRAGService(BaseRAGService):
    """Plan*RAG服务实现 - 结构化推理RAG"""
    
    def __init__(self, config: RAGConfig):
        super().__init__(config)
        self.logger.info("Plan*RAG Service initialized")
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """处理文档 - 添加推理结构标记"""
        start_time = time.time()
        
        try:
            # 使用基类的add_document方法进行分块和存储
            document_result = await self.add_document(
                user_id=user_id,
                document=content,
                chunk_size=self.config.chunk_size,
                overlap=self.config.overlap,
                metadata={
                    **(metadata or {}),
                    'supports_planning': True,
                    'plan_rag_mode': True
                }
            )
            
            if not document_result['success']:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={'error': document_result.get('error')},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error=document_result.get('error')
                )
            
            # 对每个分块分析推理结构
            reasoning_structures = []
            for chunk in document_result.get('chunks', []):
                reasoning_structure = await self._analyze_reasoning_structure(chunk.get('text', ''))
                reasoning_structures.append(reasoning_structure)
            
            return RAGResult(
                success=True,
                content=f"Processed {document_result['stored_chunks']} chunks with reasoning structure analysis",
                sources=document_result.get('chunks', []),
                metadata={
                    'chunks_processed': document_result['stored_chunks'],
                    'total_chunks': document_result['total_chunks'],
                    'document_length': document_result['document_length'],
                    'reasoning_structures': reasoning_structures,
                    'plan_rag_mode': True,
                    'supports_planning': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Plan*RAG document processing failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def query(self, 
                   query: str, 
                   user_id: str,
                   context: Optional[str] = None) -> RAGResult:
        """查询处理 - 结构化推理"""
        start_time = time.time()
        
        try:
            # 1. 生成推理计划
            reasoning_plan = await self._generate_reasoning_plan(query, user_id)
            
            # 2. 执行推理计划
            plan_results = await self._execute_reasoning_plan(reasoning_plan, query, user_id)
            
            # 3. 整合结果
            integrated_results = await self._integrate_plan_results(plan_results)
            
            # 4. 生成响应
            response = await self._generate_structured_response(query, integrated_results, context)
            
            return RAGResult(
                success=True,
                content=response,
                sources=integrated_results,
                metadata={
                    'retrieval_method': 'plan_rag_structured',
                    'reasoning_plan': {
                        'steps': reasoning_plan.steps,
                        'complexity': reasoning_plan.estimated_complexity,
                        'parallel_steps': len(reasoning_plan.parallel_executable)
                    },
                    'planning_used': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Plan*RAG query failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取Plan*RAG能力"""
        return {
            'name': 'Plan*RAG',
            'description': '结构化推理RAG',
            'features': [
                '推理计划',
                '并行执行',
                '结构化思考',
                '多步分析',
                '逻辑推理'
            ],
            'best_for': [
                '复杂推理',
                '多步分析',
                '逻辑推理',
                '结构化查询'
            ],
            'complexity': 'high',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'processing_speed': 'slow',
            'resource_usage': 'high',
            'structured_reasoning': True
        }
    
    async def _analyze_reasoning_structure(self, text: str) -> Dict[str, Any]:
        """分析推理结构"""
        # 简化的推理结构分析
        structure = {
            'has_premises': any(word in text.lower() for word in ['because', 'since', 'given that']),
            'has_conclusions': any(word in text.lower() for word in ['therefore', 'thus', 'hence']),
            'has_evidence': any(word in text.lower() for word in ['evidence', 'data', 'research']),
            'has_examples': any(word in text.lower() for word in ['for example', 'such as', 'including']),
            'reasoning_type': 'deductive' if 'therefore' in text.lower() else 'inductive'
        }
        
        return structure
    
    async def _generate_reasoning_plan(self, query: str, user_id: str) -> ReasoningPlan:
        """生成推理计划"""
        # 分析查询复杂度
        complexity = await self._analyze_query_complexity(query)
        
        # 生成推理步骤
        steps = []
        if complexity > 0.7:
            steps = [
                {'id': 1, 'type': 'background_research', 'description': '收集背景信息'},
                {'id': 2, 'type': 'evidence_gathering', 'description': '收集相关证据'},
                {'id': 3, 'type': 'analysis', 'description': '分析证据'},
                {'id': 4, 'type': 'synthesis', 'description': '综合结论'}
            ]
        else:
            steps = [
                {'id': 1, 'type': 'direct_search', 'description': '直接搜索相关信息'},
                {'id': 2, 'type': 'synthesis', 'description': '综合结果'}
            ]
        
        # 确定依赖关系
        dependencies = []
        for i in range(1, len(steps)):
            dependencies.append((i, i + 1))
        
        # 确定可并行执行的步骤
        parallel_executable = []
        if len(steps) > 2:
            parallel_executable.append([1, 2])  # 前两步可以并行
        
        return ReasoningPlan(
            steps=steps,
            dependencies=dependencies,
            parallel_executable=parallel_executable,
            estimated_complexity=complexity
        )
    
    async def _analyze_query_complexity(self, query: str) -> float:
        """分析查询复杂度"""
        complexity_indicators = {
            'multi_part': len(query.split(' and ')) > 1 or len(query.split(' or ')) > 1,
            'requires_reasoning': any(word in query.lower() for word in ['why', 'how', 'explain', 'analyze']),
            'requires_comparison': any(word in query.lower() for word in ['compare', 'versus', 'difference']),
            'requires_synthesis': any(word in query.lower() for word in ['synthesize', 'integrate', 'combine']),
            'length': len(query.split()) > 10
        }
        
        return sum(complexity_indicators.values()) / len(complexity_indicators)
    
    async def _execute_reasoning_plan(self, plan: ReasoningPlan, query: str, user_id: str) -> List[Dict[str, Any]]:
        """执行推理计划"""
        results = []
        
        for step in plan.steps:
            step_result = await self._execute_reasoning_step(step, query, user_id)
            results.append(step_result)
        
        return results
    
    async def _execute_reasoning_step(self, step: Dict, query: str, user_id: str) -> Dict[str, Any]:
        """执行推理步骤"""
        step_type = step['type']
        
        if step_type == 'background_research':
            return await self._background_research(query, user_id)
        elif step_type == 'evidence_gathering':
            return await self._evidence_gathering(query, user_id)
        elif step_type == 'analysis':
            return await self._analyze_evidence(query, user_id)
        elif step_type == 'synthesis':
            return await self._synthesize_results(query, user_id)
        else:
            return await self._direct_search(query, user_id)
    
    async def _background_research(self, query: str, user_id: str) -> Dict[str, Any]:
        """背景研究"""
        # 使用基类的search_knowledge进行背景搜索
        try:
            search_result = await self.search_knowledge(
                user_id=user_id,
                query=f"background context: {query}",
                top_k=self.config.top_k,
                enable_rerank=self.config.enable_rerank,
                search_mode="hybrid"
            )
            
            if search_result['success'] and search_result['search_results']:
                return {'type': 'background_research', 'results': search_result['search_results']}
            else:
                return {'type': 'background_research', 'results': []}
                
        except Exception as e:
            self.logger.warning(f"Background research failed: {e}")
            return {'type': 'background_research', 'results': []}
    
    async def _evidence_gathering(self, query: str, user_id: str) -> Dict[str, Any]:
        """证据收集"""
        # 搜索具体证据
        try:
            search_result = await self.search_knowledge(
                user_id=user_id,
                query=f"evidence facts: {query}",
                top_k=self.config.top_k,
                enable_rerank=self.config.enable_rerank,
                search_mode="semantic"
            )
            
            if search_result['success'] and search_result['search_results']:
                return {'type': 'evidence_gathering', 'results': search_result['search_results']}
            else:
                return {'type': 'evidence_gathering', 'results': []}
                
        except Exception as e:
            self.logger.warning(f"Evidence gathering failed: {e}")
            return {'type': 'evidence_gathering', 'results': []}
    
    async def _analyze_evidence(self, query: str, user_id: str) -> Dict[str, Any]:
        """证据分析"""
        # 分析和检索相关信息
        try:
            search_result = await self.search_knowledge(
                user_id=user_id,
                query=f"analysis details: {query}",
                top_k=self.config.top_k,
                enable_rerank=True,
                search_mode="hybrid"
            )
            
            if search_result['success'] and search_result['search_results']:
                return {'type': 'analysis', 'results': search_result['search_results']}
            else:
                return {'type': 'analysis', 'results': []}
                
        except Exception as e:
            self.logger.warning(f"Evidence analysis failed: {e}")
            return {'type': 'analysis', 'results': []}
    
    async def _synthesize_results(self, query: str, user_id: str) -> Dict[str, Any]:
        """结果综合"""
        # 综合所有相关信息
        try:
            search_result = await self.search_knowledge(
                user_id=user_id,
                query=query,  # 使用原始查询进行综合搜索
                top_k=self.config.top_k,
                enable_rerank=True,
                search_mode="hybrid"
            )
            
            if search_result['success'] and search_result['search_results']:
                return {'type': 'synthesis', 'results': search_result['search_results']}
            else:
                return {'type': 'synthesis', 'results': []}
                
        except Exception as e:
            self.logger.warning(f"Results synthesis failed: {e}")
            return {'type': 'synthesis', 'results': []}
    
    async def _direct_search(self, query: str, user_id: str) -> Dict[str, Any]:
        """直接搜索"""
        # 直接使用基类的搜索功能
        try:
            search_result = await self.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=self.config.top_k,
                enable_rerank=self.config.enable_rerank,
                search_mode="hybrid",
                use_enhanced_search=True
            )
            
            if search_result['success'] and search_result['search_results']:
                return {'type': 'direct_search', 'results': search_result['search_results']}
            else:
                return {'type': 'direct_search', 'results': []}
                
        except Exception as e:
            self.logger.warning(f"Direct search failed: {e}")
            return {'type': 'direct_search', 'results': []}
    
    async def _integrate_plan_results(self, plan_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """整合计划结果"""
        # 整合所有步骤的结果，避免重复
        integrated = []
        seen_texts = set()
        
        for result in plan_results:
            results = result.get('results', [])
            for item in results:
                # 避免重复添加相同的文本
                text_key = item.get('text', '')[:100]  # 使用前100个字符作为去重键
                if text_key and text_key not in seen_texts:
                    seen_texts.add(text_key)
                    # 添加步骤信息到metadata
                    if 'metadata' not in item:
                        item['metadata'] = {}
                    item['metadata']['plan_step'] = result.get('type', 'unknown')
                    integrated.append(item)
        
        # 限制结果数量到top_k
        return integrated[:self.config.top_k]
    
    async def _generate_structured_response(self, query: str, results: List[Dict], context: Optional[str]) -> str:
        """生成结构化响应 - 现在支持inline citations!"""
        try:
            # 使用基类的统一citation方法
            citation_context = self._build_context_with_citations(results)
            
            response = await self._generate_response_with_llm(
                query=query,
                context=citation_context,
                additional_context=f"Structured Planning: This response follows a step-by-step reasoning plan. {context}" if context else "Structured Planning: This response follows a step-by-step reasoning plan.",
                use_citations=True
            )
            
            self.logger.info("✅ Plan-RAG generated structured response with inline citations")
            return response
            
        except Exception as e:
            self.logger.warning(f"Plan-RAG citation generation failed: {e}, falling back to traditional")
            
            # 降级到传统结构化响应
            response_parts = []
            
            for i, result in enumerate(results):
                response_parts.append(f"Step {i+1}: {result.get('text', '')}")
            
            response = "\n\n".join(response_parts)
            
            return f"Plan-RAG structured response for '{query}':\n\n{response}"
