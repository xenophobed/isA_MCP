#!/usr/bin/env python3
"""
Deep-Thinking RAG Service - 深度思考RAG服务
基于论文 "Building an Agentic Deep-Thinking RAG Pipeline to Solve Complex Queries"

核心特性：
1. 多阶段检索漏斗（Broad Recall → Reranking → Distillation）
2. 智能检索策略选择（Retrieval Supervisor）
3. 自我反思和循环推理（Policy Agent）
4. 多步骤计划执行和质量评估

适用场景：
- 复杂的多跳查询（multi-hop queries）
- 需要多步推理的问题
- 需要综合多个来源的信息
- 对准确性要求极高的场景
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from ..base.base_rag_service import BaseRAGService, RAGResult, RAGMode, RAGConfig
from ..integrations.retrieval_funnel import (
    MultiStageRetrievalFunnel,
    RetrievalConfig,
    create_default_funnel
)
from ..integrations.retrieval_supervisor import (
    RetrievalSupervisor,
    SearchStrategy,
    create_default_supervisor
)
from ..integrations.policy_agent import (
    PolicyAgent,
    PolicyAction,
    ResearchStep,
    create_default_policy_agent
)

logger = logging.getLogger(__name__)


@dataclass
class DeepThinkingConfig(RAGConfig):
    """Deep-Thinking RAG配置"""
    # 循环推理配置
    max_reasoning_iterations: int = 5
    enable_policy_agent: bool = True
    enable_retrieval_supervisor: bool = True

    # 检索漏斗配置
    initial_top_k: int = 10
    rerank_top_n: int = 3
    enable_distillation: bool = True

    # 质量控制
    min_quality_threshold: float = 0.3

    # LLM配置
    use_llm_for_policy: bool = False
    use_llm_for_supervisor: bool = False


class DeepThinkingRAGService(BaseRAGService):
    """
    Deep-Thinking RAG服务实现

    核心工作流：
    1. Plan Generation: 分析查询，生成多步骤研究计划
    2. Iterative Research Loop:
       a. Supervisor: 选择检索策略
       b. Retrieve: 执行检索（内部知识库）
       c. Funnel: 多阶段精炼（Broad → Rerank → Distill）
       d. Reflect: 总结当前步骤发现
       e. Policy: 决定CONTINUE或FINISH
    3. Final Synthesis: 综合所有发现，生成最终答案
    """

    def __init__(self, config: DeepThinkingConfig):
        super().__init__(config)

        # 初始化核心组件
        self._retrieval_funnel = None
        self._retrieval_supervisor = None
        self._policy_agent = None

        self.logger.info("🧠 Deep-Thinking RAG Service initialized")

    @property
    def retrieval_funnel(self) -> MultiStageRetrievalFunnel:
        """懒加载检索漏斗"""
        if self._retrieval_funnel is None:
            funnel_config = RetrievalConfig(
                initial_top_k=self.config.initial_top_k,
                enable_rerank=True,
                rerank_top_n=self.config.rerank_top_n,
                enable_distillation=self.config.enable_distillation
            )
            self._retrieval_funnel = MultiStageRetrievalFunnel(funnel_config)
        return self._retrieval_funnel

    @property
    def retrieval_supervisor(self) -> RetrievalSupervisor:
        """懒加载检索监督器"""
        if self._retrieval_supervisor is None:
            if self.config.use_llm_for_supervisor:
                # TODO: 传入LLM generator
                self._retrieval_supervisor = create_default_supervisor()
            else:
                self._retrieval_supervisor = create_default_supervisor()
        return self._retrieval_supervisor

    @property
    def policy_agent(self) -> PolicyAgent:
        """懒加载策略代理"""
        if self._policy_agent is None:
            if self.config.use_llm_for_policy:
                # TODO: 传入LLM generator
                self._policy_agent = create_default_policy_agent()
            else:
                self._policy_agent = create_default_policy_agent()

            # 更新配置
            self._policy_agent.max_iterations = self.config.max_reasoning_iterations
            self._policy_agent.min_quality_threshold = self.config.min_quality_threshold

        return self._policy_agent

    async def query(
        self,
        query: str,
        user_id: str,
        context: Optional[str] = None
    ) -> RAGResult:
        """
        Deep-Thinking查询处理 - 主入口

        执行完整的循环推理流程
        """
        start_time = time.time()

        try:
            self.logger.info(f"🧠 Deep-Thinking RAG: Processing query for user {user_id}")

            # Step 1: 生成研究计划
            plan = await self._generate_research_plan(query)
            self.logger.info(f"📋 Generated plan with {len(plan['steps'])} steps")

            # Step 2: 循环推理执行
            research_history = await self._execute_iterative_research(
                query, user_id, plan
            )
            self.logger.info(f"🔍 Completed {len(research_history)} research iterations")

            # Step 3: 综合最终答案
            final_answer = await self._synthesize_final_answer(
                query, research_history, context
            )

            # 构建结果
            return RAGResult(
                success=True,
                content=final_answer,
                sources=self._extract_all_sources(research_history),
                metadata={
                    'retrieval_method': 'deep_thinking_rag',
                    'plan_steps': len(plan['steps']),
                    'iterations_completed': len(research_history),
                    'avg_quality': sum(s.quality_score for s in research_history) / len(research_history) if research_history else 0,
                    'deep_thinking_used': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Deep-Thinking RAG query failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': str(e)},
                mode_used=self.mode,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def _generate_research_plan(self, query: str) -> Dict[str, Any]:
        """
        生成研究计划 - 将复杂查询分解为多个子问题

        Args:
            query: 用户查询

        Returns:
            包含多个步骤的研究计划
        """
        # 分析查询复杂度
        complexity = self._analyze_query_complexity(query)

        # 基于复杂度生成计划
        if complexity > 0.7:
            # 复杂查询：多步骤计划
            steps = [
                {
                    'id': 1,
                    'type': 'background_research',
                    'sub_question': f"What is the background context for: {query}?",
                    'description': '收集背景信息'
                },
                {
                    'id': 2,
                    'type': 'evidence_gathering',
                    'sub_question': f"What specific evidence or facts relate to: {query}?",
                    'description': '收集具体证据'
                },
                {
                    'id': 3,
                    'type': 'synthesis',
                    'sub_question': query,  # 原始查询
                    'description': '综合分析'
                }
            ]
        else:
            # 简单查询：直接检索
            steps = [
                {
                    'id': 1,
                    'type': 'direct_search',
                    'sub_question': query,
                    'description': '直接检索相关信息'
                }
            ]

        self.logger.info(
            f"📋 Plan: {len(steps)} steps (complexity={complexity:.2f})"
        )

        return {
            'original_query': query,
            'steps': steps,
            'estimated_complexity': complexity
        }

    def _analyze_query_complexity(self, query: str) -> float:
        """分析查询复杂度（0-1分数）"""
        indicators = {
            'multi_part': len(query.split(' and ')) > 1 or len(query.split(' or ')) > 1,
            'requires_reasoning': any(word in query.lower() for word in ['why', 'how', 'explain', 'analyze', 'compare']),
            'requires_synthesis': any(word in query.lower() for word in ['synthesize', 'integrate', 'combine', 'overall']),
            'is_long': len(query.split()) > 15,
            'has_multiple_questions': query.count('?') > 1
        }

        complexity = sum(indicators.values()) / len(indicators)
        return complexity

    async def _execute_iterative_research(
        self,
        original_query: str,
        user_id: str,
        plan: Dict[str, Any]
    ) -> List[ResearchStep]:
        """
        执行循环推理 - Deep-Thinking的核心

        循环流程：
        1. Supervisor: 选择检索策略
        2. Retrieve: 执行检索
        3. Funnel: 精炼结果
        4. Reflect: 总结发现
        5. Policy: 决定是否继续
        """
        research_history = []
        current_step_index = 0

        for iteration in range(self.config.max_reasoning_iterations):
            # 检查是否还有步骤
            if current_step_index >= len(plan['steps']):
                self.logger.info(f"✅ Plan completed after {iteration} iterations")
                break

            current_step = plan['steps'][current_step_index]
            sub_question = current_step['sub_question']

            self.logger.info(
                f"🔄 Iteration {iteration + 1}: Step {current_step_index + 1}/{len(plan['steps'])}"
            )

            # Step A: 监督器选择检索策略
            if self.config.enable_retrieval_supervisor:
                supervisor_decision = await self.retrieval_supervisor.decide_strategy(
                    sub_question
                )
                strategy = supervisor_decision.strategy
                self.logger.info(
                    f"🚦 Supervisor: Use {strategy.value} search "
                    f"(confidence={supervisor_decision.confidence:.2f})"
                )
            else:
                strategy = SearchStrategy.HYBRID

            # Step B: 执行检索
            initial_results = await self._retrieve_with_strategy(
                sub_question, user_id, strategy
            )

            # Step C: 多阶段漏斗精炼
            funnel_result = await self.retrieval_funnel.execute_funnel(
                query=sub_question,
                initial_results=initial_results,
                llm_generator=None  # TODO: 传入LLM generator用于蒸馏
            )

            reranked_docs = funnel_result['stage2_reranked']
            distilled_context = funnel_result['stage3_distilled']

            # 计算质量分数
            quality_score = self._calculate_quality_score(reranked_docs)

            # Step D: 反思 - 总结当前步骤发现
            if distilled_context:
                summary = distilled_context[:200]  # 使用蒸馏的上下文
            else:
                # 降级：使用原始文档总结
                summary = await self.policy_agent.reflect(
                    sub_question=sub_question,
                    retrieved_context="\n".join([doc.get('text', '')[:100] for doc in reranked_docs[:2]]),
                    llm_generator=None  # TODO: 传入LLM generator
                )

            # 记录研究步骤
            research_step = ResearchStep(
                step_index=current_step_index,
                sub_question=sub_question,
                summary=summary,
                sources_count=len(reranked_docs),
                quality_score=quality_score,
                timestamp=datetime.now().isoformat()
            )
            research_history.append(research_step)

            # Step E: 策略决策 - 是否继续
            if self.config.enable_policy_agent:
                policy_decision = await self.policy_agent.decide(
                    original_query=original_query,
                    plan_steps=plan['steps'],
                    research_history=research_history,
                    current_step_index=current_step_index + 1
                )

                self.logger.info(
                    f"🚦 Policy: {policy_decision.action.value.upper()} "
                    f"(confidence={policy_decision.confidence:.2f}) - {policy_decision.justification}"
                )

                if policy_decision.action == PolicyAction.FINISH:
                    break
                elif policy_decision.action == PolicyAction.CONTINUE:
                    current_step_index += 1
                elif policy_decision.action == PolicyAction.REVISE:
                    self.logger.warning("Plan revision not yet implemented, finishing")
                    break
            else:
                # 无策略代理：线性执行
                current_step_index += 1

        return research_history

    async def _retrieve_with_strategy(
        self,
        query: str,
        user_id: str,
        strategy: SearchStrategy
    ) -> List[Dict[str, Any]]:
        """根据策略执行检索"""
        try:
            # 使用基类的search_knowledge方法
            search_mode = {
                SearchStrategy.VECTOR: "semantic",
                SearchStrategy.KEYWORD: "keyword",
                SearchStrategy.HYBRID: "hybrid"
            }.get(strategy, "hybrid")

            result = await self.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=self.config.initial_top_k,
                enable_rerank=False,  # 漏斗会处理rerank
                search_mode=search_mode
            )

            if result['success'] and result.get('search_results'):
                return result['search_results']
            else:
                return []

        except Exception as e:
            self.logger.error(f"Retrieval failed: {e}")
            return []

    def _calculate_quality_score(self, documents: List[Dict[str, Any]]) -> float:
        """计算检索质量分数"""
        if not documents:
            return 0.0

        # 基于多个因素计算质量
        avg_similarity = sum(doc.get('similarity_score', 0) for doc in documents) / len(documents)
        has_rerank_scores = any('rerank_score' in doc for doc in documents)

        quality = avg_similarity * 0.7
        if has_rerank_scores:
            avg_rerank = sum(doc.get('rerank_score', 0) for doc in documents) / len(documents)
            quality += avg_rerank * 0.3

        return min(quality, 1.0)

    async def _synthesize_final_answer(
        self,
        original_query: str,
        research_history: List[ResearchStep],
        context: Optional[str]
    ) -> str:
        """综合最终答案 - 使用inline citations"""
        if not research_history:
            return f"I don't have enough information to answer '{original_query}'."

        # 构建综合上下文
        synthesis_context = "\n\n".join([
            f"Research Step {i + 1}: {step.sub_question}\n"
            f"Findings: {step.summary}\n"
            f"Quality: {step.quality_score:.2f}"
            for i, step in enumerate(research_history)
        ])

        # TODO: 使用LLM生成带引用的最终答案
        # 现在使用简单的综合
        answer = f"Based on {len(research_history)} research steps:\n\n{synthesis_context}"

        if context:
            answer = f"{answer}\n\nAdditional Context: {context}"

        return answer

    def _extract_all_sources(self, research_history: List[ResearchStep]) -> List[Dict[str, Any]]:
        """从研究历史中提取所有源"""
        # TODO: 实现从research_history中提取实际的源文档
        return [
            {
                'step': step.step_index + 1,
                'sub_question': step.sub_question,
                'summary': step.summary,
                'quality': step.quality_score
            }
            for step in research_history
        ]

    def get_capabilities(self) -> Dict[str, Any]:
        """获取Deep-Thinking RAG能力"""
        return {
            'name': 'Deep-Thinking RAG',
            'description': '深度思考RAG - 循环推理和多步骤研究',
            'features': [
                '多步骤计划生成',
                '循环推理',
                '自我反思',
                '策略决策',
                '智能检索路由',
                '多阶段精炼'
            ],
            'best_for': [
                '复杂多跳查询',
                '需要多步推理',
                '高准确性要求',
                '综合多源信息',
                '研究型问题'
            ],
            'complexity': 'very_high',
            'supports_rerank': True,
            'supports_hybrid': True,
            'processing_speed': 'slow',
            'resource_usage': 'very_high',
            'deep_thinking': True,
            'self_reflection': True,
            'iterative_reasoning': True
        }

    # 实现抽象方法占位符（由基类定义）
    async def store(self, content, user_id, content_type="text", metadata=None, options=None):
        # 使用父类的add_document方法
        return await self.add_document(
            user_id=user_id,
            document=content,
            metadata=metadata
        )

    async def retrieve(self, query, user_id, top_k=None, filters=None, options=None):
        # 使用search_knowledge
        return await self.search_knowledge(
            user_id=user_id,
            query=query,
            top_k=top_k or self.config.top_k
        )

    async def generate(self, query, user_id, context=None, retrieval_result=None, options=None):
        # 使用主query方法
        return await self.query(query, user_id, context)
