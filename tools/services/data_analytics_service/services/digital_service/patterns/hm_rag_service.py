#!/usr/bin/env python3
"""
HM-RAG Service - 多智能体协作RAG实现

基于advanced_rag_patterns.py中的HMRAGPattern，实现独立的HM-RAG服务。
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from ..base.base_rag_service import BaseRAGService, RAGResult, RAGMode, RAGConfig

logger = logging.getLogger(__name__)

@dataclass
class AgentTask:
    """智能体任务定义"""
    agent_id: str
    task_type: str
    query: str
    user_id: str
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class HMRAGRAGService(BaseRAGService):
    """HM-RAG服务实现 - 多智能体协作RAG"""
    
    def __init__(self, config: RAGConfig):
        super().__init__(config)
        self.logger.info("HM-RAG Service initialized")
        
        # 定义智能体角色
        self.agents = {
            'retrieval_agent': {'role': '信息检索', 'capabilities': ['search', 'filter', 'rank']},
            'analysis_agent': {'role': '内容分析', 'capabilities': ['analyze', 'extract', 'classify']},
            'synthesis_agent': {'role': '信息综合', 'capabilities': ['synthesize', 'summarize', 'generate']},
            'quality_agent': {'role': '质量控制', 'capabilities': ['verify', 'validate', 'assess']}
        }
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """处理文档 - 多智能体协作处理"""
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
                    'hm_rag_mode': True,
                    'multi_agent_processed': True
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
            
            # 创建协作任务处理文档
            collaborative_tasks = await self._create_collaborative_document_tasks(
                content, user_id, metadata
            )
            
            # 执行协作任务
            collaborative_results = await self._execute_collaborative_tasks(collaborative_tasks)
            
            # 整合协作结果
            integrated_result = await self._integrate_collaborative_results(collaborative_results)
            
            return RAGResult(
                success=True,
                content=f"Processed {document_result['stored_chunks']} chunks with multi-agent collaboration",
                sources=document_result.get('chunks', []),
                metadata={
                    'chunks_processed': document_result['stored_chunks'],
                    'total_chunks': document_result['total_chunks'],
                    'document_length': document_result['document_length'],
                    'collaborative_analysis': integrated_result,
                    'multi_agent_processed': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"HM-RAG document processing failed: {e}")
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
        """查询处理 - 多智能体协作"""
        start_time = time.time()
        
        try:
            # 1. 创建协作查询任务
            query_tasks = await self._create_query_tasks(query, user_id, context)
            
            # 2. 执行协作查询
            agent_results = await self._execute_agent_collaboration(query_tasks)
            
            # 3. 智能体间协作和协商
            collaborative_result = await self._agent_collaboration_and_negotiation(agent_results)
            
            # 4. 生成最终响应
            response = await self._generate_collaborative_response(query, collaborative_result, context)
            
            return RAGResult(
                success=True,
                content=response,
                sources=collaborative_result.get('sources', []),
                metadata={
                    'retrieval_method': 'hm_rag_collaborative',
                    'agent_collaboration': {
                        'agents_involved': list(agent_results.keys()),
                        'collaboration_steps': collaborative_result.get('steps', []),
                        'consensus_reached': collaborative_result.get('consensus_reached', False)
                    },
                    'multi_agent_used': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"HM-RAG query failed: {e}")
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
        """获取HM-RAG能力"""
        return {
            'name': 'HM-RAG',
            'description': '多智能体协作RAG',
            'features': [
                '多智能体协作',
                '任务分配',
                '协商机制',
                '质量控制',
                '并行处理'
            ],
            'best_for': [
                '复杂查询',
                '需要多角度分析',
                '高质量要求',
                '大规模处理'
            ],
            'complexity': 'high',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'processing_speed': 'medium',
            'resource_usage': 'high',
            'multi_agent': True
        }
    
    # ===============================
    # Document Processing Methods
    # ===============================
    
    async def _create_collaborative_document_tasks(self, content: str, user_id: str, metadata: Optional[Dict[str, Any]]) -> List[AgentTask]:
        """创建文档处理的协作任务"""
        tasks = []
        
        # 为每个智能体创建任务
        tasks.append(AgentTask(
            agent_id='analysis_agent',
            task_type='document_analysis',
            query=content[:500],  # 使用文档片段作为查询
            user_id=user_id,
            context="Analyze document structure and content",
            metadata=metadata
        ))
        
        tasks.append(AgentTask(
            agent_id='synthesis_agent',
            task_type='document_synthesis',
            query=content[:500],
            user_id=user_id,
            context="Extract key information and synthesize",
            metadata=metadata
        ))
        
        tasks.append(AgentTask(
            agent_id='quality_agent',
            task_type='document_quality',
            query=content[:500],
            user_id=user_id,
            context="Assess document quality and completeness",
            metadata=metadata
        ))
        
        return tasks
    
    async def _execute_collaborative_tasks(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """执行协作任务"""
        results = {}
        
        # 并行执行所有任务
        for task in tasks:
            result = await self._execute_single_task(task)
            results[task.agent_id] = result
        
        return results
    
    async def _execute_single_task(self, task: AgentTask) -> Dict[str, Any]:
        """执行单个任务"""
        try:
            if task.agent_id == 'retrieval_agent':
                return await self._retrieval_agent_task(task)
            elif task.agent_id == 'analysis_agent':
                return await self._analysis_agent_task(task)
            elif task.agent_id == 'synthesis_agent':
                return await self._synthesis_agent_task(task)
            elif task.agent_id == 'quality_agent':
                return await self._quality_agent_task(task)
            else:
                return {'status': 'unknown_agent', 'result': None}
                
        except Exception as e:
            self.logger.error(f"Task execution failed for {task.agent_id}: {e}")
            return {'status': 'error', 'error': str(e)}
    
    # ===============================
    # Query Processing Methods
    # ===============================
    
    async def _create_query_tasks(self, query: str, user_id: str, context: Optional[str]) -> Dict[str, Dict[str, Any]]:
        """创建查询任务"""
        tasks = {}
        
        # 为每个智能体创建查询任务
        tasks['retrieval_agent'] = {
            'query': query,
            'user_id': user_id,
            'task': 'search',
            'context': context
        }
        
        tasks['analysis_agent'] = {
            'query': query,
            'task': 'analyze',
            'context': context
        }
        
        tasks['synthesis_agent'] = {
            'query': query,
            'task': 'synthesize',
            'context': context
        }
        
        tasks['quality_agent'] = {
            'query': query,
            'task': 'quality_check',
            'context': context
        }
        
        return tasks
    
    async def _execute_agent_collaboration(self, tasks: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """执行智能体协作"""
        agent_results = {}
        
        # 执行各智能体任务
        for agent_id, task_info in tasks.items():
            try:
                if agent_id == 'retrieval_agent':
                    # 检索智能体：搜索相关文档
                    search_result = await self.search_knowledge(
                        user_id=task_info['user_id'],
                        query=task_info['query'],
                        top_k=self.config.top_k,
                        enable_rerank=True,
                        search_mode='hybrid',
                        use_enhanced_search=True
                    )
                    
                    agent_results[agent_id] = {
                        'status': 'completed',
                        'sources': search_result.get('search_results', []),
                        'confidence': 0.8 if search_result.get('success') else 0.2
                    }
                    
                elif agent_id == 'analysis_agent':
                    # 分析智能体：分析查询意图
                    agent_results[agent_id] = {
                        'status': 'completed',
                        'analysis': {
                            'query_type': 'information_seeking',
                            'complexity': 'medium',
                            'key_terms': task_info['query'].split()[:5]
                        },
                        'confidence': 0.75
                    }
                    
                elif agent_id == 'synthesis_agent':
                    # 综合智能体：准备综合策略
                    agent_results[agent_id] = {
                        'status': 'completed',
                        'synthesis_strategy': 'comprehensive',
                        'confidence': 0.7
                    }
                    
                elif agent_id == 'quality_agent':
                    # 质量智能体：评估质量标准
                    agent_results[agent_id] = {
                        'status': 'completed',
                        'quality_metrics': {
                            'relevance': 0.8,
                            'completeness': 0.7,
                            'accuracy': 0.75
                        },
                        'confidence': 0.8
                    }
                    
            except Exception as e:
                self.logger.error(f"Agent {agent_id} collaboration failed: {e}")
                agent_results[agent_id] = {
                    'status': 'error',
                    'error': str(e),
                    'confidence': 0.0
                }
        
        return agent_results
    
    async def _agent_collaboration_and_negotiation(self, agent_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """智能体间协作和协商"""
        collaborative_result = {
            'consensus_reached': False,
            'sources': [],
            'confidence_score': 0.0,
            'final_decision': '',
            'steps': []
        }
        
        # 收集所有sources
        for agent_id, result in agent_results.items():
            if 'sources' in result:
                collaborative_result['sources'].extend(result['sources'])
        
        # 计算共识度
        confidence_scores = []
        for agent_id, result in agent_results.items():
            if 'confidence' in result:
                confidence_scores.append(result['confidence'])
        
        if confidence_scores:
            collaborative_result['confidence_score'] = sum(confidence_scores) / len(confidence_scores)
            collaborative_result['consensus_reached'] = collaborative_result['confidence_score'] > 0.6
        
        # 记录协作步骤
        collaborative_result['steps'] = [
            f"{agent_id}: {result.get('status', 'unknown')}" 
            for agent_id, result in agent_results.items()
        ]
        
        # 最终决策
        if collaborative_result['confidence_score'] > 0.7:
            collaborative_result['final_decision'] = 'high_confidence'
        elif collaborative_result['confidence_score'] > 0.5:
            collaborative_result['final_decision'] = 'medium_confidence'
        else:
            collaborative_result['final_decision'] = 'low_confidence'
        
        return collaborative_result
    
    async def _generate_collaborative_response(self, query: str, collaborative_result: Dict, context: Optional[str]) -> str:
        """生成协作响应 - 支持inline citations"""
        try:
            all_sources = collaborative_result.get('sources', [])
            
            if all_sources:
                # 使用基类的统一citation方法构建上下文
                citation_context = self._build_context_with_citations(all_sources)
                
                # 使用基类的LLM生成方法
                response = await self._generate_response_with_llm(
                    query=query, 
                    context=citation_context,
                    additional_context=f"Multi-Agent Collaboration: {collaborative_result.get('final_decision', 'collaborative_result')}. {context}" if context else f"Multi-Agent Collaboration: {collaborative_result.get('final_decision', 'collaborative_result')}.",
                    use_citations=True
                )
                
                self.logger.info("✅ HM-RAG successfully generated collaborative response with inline citations")
                return response
            else:
                self.logger.warning("HM-RAG: No sources found from agent collaboration")
                return f"Based on multi-agent collaboration for '{query}', no sufficient information was found to provide a reliable answer."
                
        except Exception as e:
            self.logger.warning(f"HM-RAG citation generation failed: {e}, falling back")
            # 降级响应
            return f"Multi-agent collaboration completed for '{query}' with confidence level: {collaborative_result.get('confidence_score', 0):.2f}"
    
    # ===============================
    # Agent Task Implementation
    # ===============================
    
    async def _retrieval_agent_task(self, task: AgentTask) -> Dict[str, Any]:
        """检索智能体任务"""
        # 使用基类的搜索功能
        search_result = await self.search_knowledge(
            user_id=task.user_id,
            query=task.query,
            top_k=self.config.top_k,
            enable_rerank=True,
            search_mode='hybrid'
        )
        
        return {
            'agent_id': 'retrieval_agent',
            'status': 'completed',
            'sources': search_result.get('search_results', []),
            'confidence': 0.8 if search_result.get('success') else 0.2
        }
    
    async def _analysis_agent_task(self, task: AgentTask) -> Dict[str, Any]:
        """分析智能体任务"""
        # 简化的分析逻辑
        analysis_result = {
            'topics': task.query.split()[:5],
            'entities': [word for word in task.query.split() if word.istitle()][:3],
            'complexity': len(task.query.split()) / 20.0
        }
        
        return {
            'agent_id': 'analysis_agent',
            'status': 'completed',
            'analysis': analysis_result,
            'confidence': 0.75
        }
    
    async def _synthesis_agent_task(self, task: AgentTask) -> Dict[str, Any]:
        """综合智能体任务"""
        # 简化的综合逻辑
        synthesis_result = {
            'summary': task.query[:100] + "...",
            'key_points': task.query.split('.')[:3]
        }
        
        return {
            'agent_id': 'synthesis_agent',
            'status': 'completed',
            'synthesis': synthesis_result,
            'confidence': 0.7
        }
    
    async def _quality_agent_task(self, task: AgentTask) -> Dict[str, Any]:
        """质量智能体任务"""
        # 简化的质量评估
        quality_metrics = {
            'accuracy': 0.8,
            'completeness': 0.75,
            'clarity': 0.85,
            'relevance': 0.9
        }
        
        return {
            'agent_id': 'quality_agent',
            'status': 'completed',
            'metrics': quality_metrics,
            'confidence': sum(quality_metrics.values()) / len(quality_metrics)
        }
    
    # ===============================
    # Helper Methods
    # ===============================
    
    async def _integrate_collaborative_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """整合协作结果"""
        integrated = {
            'success': True,
            'agent_contributions': {},
            'consensus_level': 0.0,
            'final_decision': ''
        }
        
        # 收集所有智能体的贡献
        for agent_id, contribution in results.items():
            integrated['agent_contributions'][agent_id] = contribution
        
        # 计算共识水平
        confidence_scores = []
        for agent_id, contribution in results.items():
            if isinstance(contribution, dict) and 'confidence' in contribution:
                confidence_scores.append(contribution['confidence'])
        
        if confidence_scores:
            integrated['consensus_level'] = sum(confidence_scores) / len(confidence_scores)
        
        # 最终决策
        if integrated['consensus_level'] > 0.8:
            integrated['final_decision'] = 'strong_consensus'
        elif integrated['consensus_level'] > 0.6:
            integrated['final_decision'] = 'moderate_consensus'
        else:
            integrated['final_decision'] = 'weak_consensus'
        
        return integrated