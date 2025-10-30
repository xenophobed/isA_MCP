#!/usr/bin/env python3
"""
Policy Agent - 策略代理（Deep-Thinking RAG的核心大脑）

实现自我反思和循环推理：
1. Reflection: 总结当前步骤的发现
2. Policy Decision: 决定是否继续研究（CONTINUE）或结束（FINISH）
3. Plan Revision: 如果遇到死胡同，修改计划

基于Deep-Thinking RAG论文的核心循环：
Plan → Retrieve → Reflect → Policy Decision → Loop (or Finish)
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class PolicyAction(Enum):
    """策略决策动作"""
    CONTINUE = "continue"  # 继续执行计划
    FINISH = "finish"      # 完成研究，生成最终答案
    REVISE = "revise"      # 修改计划（遇到死胡同）


@dataclass
class ResearchStep:
    """单个研究步骤的记录"""
    step_index: int
    sub_question: str
    summary: str  # 该步骤的发现总结
    sources_count: int
    quality_score: float  # 0-1, 该步骤检索质量
    timestamp: str


@dataclass
class PolicyDecision:
    """策略决策结果"""
    action: PolicyAction
    confidence: float  # 0-1, 决策置信度
    justification: str  # 决策理由
    next_step_index: Optional[int] = None  # 如果CONTINUE，下一步的索引
    plan_revision: Optional[Dict[str, Any]] = None  # 如果REVISE，修改后的计划


class PolicyAgent:
    """
    策略代理 - Deep-Thinking RAG的自我反思和控制流核心

    核心职责：
    1. 在每个研究步骤后进行反思（Reflection）
    2. 决定是否继续、完成、或修改计划（Policy Decision）
    3. 防止无限循环（max_iterations保护）
    """

    def __init__(
        self,
        max_iterations: int = 5,
        min_quality_threshold: float = 0.3,
        use_llm: bool = False,
        llm_generator: Optional[Any] = None
    ):
        """
        Args:
            max_iterations: 最大循环次数（防止无限循环）
            min_quality_threshold: 最低质量阈值（低于此值可能触发REVISE）
            use_llm: 是否使用LLM进行策略决策
            llm_generator: LLM生成器
        """
        self.max_iterations = max_iterations
        self.min_quality_threshold = min_quality_threshold
        self.use_llm = use_llm
        self.llm_generator = llm_generator
        self.logger = logging.getLogger(self.__class__.__name__)

    async def reflect(
        self,
        sub_question: str,
        retrieved_context: str,
        llm_generator: Optional[Any] = None
    ) -> str:
        """
        反思步骤 - 总结当前研究步骤的发现

        Args:
            sub_question: 子问题
            retrieved_context: 检索到的上下文
            llm_generator: LLM生成器（如果不使用self.llm_generator）

        Returns:
            简洁的一句话总结
        """
        generator = llm_generator or self.llm_generator

        if not generator:
            # 降级：使用简单的截断总结
            summary = retrieved_context[:200].replace('\n', ' ') + "..."
            self.logger.warning("No LLM available for reflection, using truncated context")
            return f"Found information about: {summary}"

        try:
            reflection_prompt = f"""You are a research assistant. Based on the retrieved context for the sub-question, write a concise, one-sentence summary of the key findings.

Sub-question: {sub_question}

Retrieved Context:
{retrieved_context[:1000]}

Summary (one sentence, max 150 chars):"""

            if hasattr(generator, 'generate'):
                summary = await generator.generate(reflection_prompt)
            elif callable(generator):
                summary = await generator(reflection_prompt)
            else:
                raise ValueError("Invalid LLM generator")

            # 清理和截断
            summary = summary.strip().replace('\n', ' ')
            if len(summary) > 200:
                summary = summary[:197] + "..."

            self.logger.info(f"🤔 Reflected: {summary}")
            return summary

        except Exception as e:
            self.logger.error(f"Reflection failed: {e}")
            return f"Found relevant information for: {sub_question}"

    async def decide(
        self,
        original_query: str,
        plan_steps: List[Dict[str, Any]],
        research_history: List[ResearchStep],
        current_step_index: int
    ) -> PolicyDecision:
        """
        策略决策 - Deep-Thinking RAG的核心控制流

        分析研究历史，决定下一步行动：CONTINUE、FINISH、或REVISE

        Args:
            original_query: 原始用户查询
            plan_steps: 完整的研究计划
            research_history: 已完成的研究步骤历史
            current_step_index: 当前步骤索引

        Returns:
            PolicyDecision对象
        """
        # 基本停止条件检查
        basic_decision = self._check_basic_stop_conditions(
            plan_steps, research_history, current_step_index
        )
        if basic_decision:
            return basic_decision

        # 使用LLM或规则进行策略决策
        if self.use_llm and self.llm_generator:
            return await self._llm_based_decision(
                original_query, plan_steps, research_history, current_step_index
            )
        else:
            return await self._rule_based_decision(
                original_query, plan_steps, research_history, current_step_index
            )

    def _check_basic_stop_conditions(
        self,
        plan_steps: List[Dict[str, Any]],
        research_history: List[ResearchStep],
        current_step_index: int
    ) -> Optional[PolicyDecision]:
        """检查基本停止条件"""
        # 条件1：超过最大迭代次数
        if len(research_history) >= self.max_iterations:
            self.logger.warning(f"🚦 Max iterations ({self.max_iterations}) reached, forcing FINISH")
            return PolicyDecision(
                action=PolicyAction.FINISH,
                confidence=1.0,
                justification=f"Reached maximum iteration limit ({self.max_iterations})",
                next_step_index=None
            )

        # 条件2：计划中所有步骤已完成
        if current_step_index >= len(plan_steps):
            self.logger.info("🚦 Plan completed, all steps finished")
            return PolicyDecision(
                action=PolicyAction.FINISH,
                confidence=0.95,
                justification="All planned research steps have been completed",
                next_step_index=None
            )

        # 条件3：最后一步检索失败（没有找到任何文档）
        if research_history and research_history[-1].sources_count == 0:
            self.logger.warning("🚦 Last retrieval failed, attempting to continue with next step")
            # 不直接失败，而是尝试继续下一步
            if current_step_index < len(plan_steps) - 1:
                return PolicyDecision(
                    action=PolicyAction.CONTINUE,
                    confidence=0.5,
                    justification="Previous step found no results, trying next step in plan",
                    next_step_index=current_step_index + 1
                )

        return None  # 没有基本停止条件，继续进行策略决策

    async def _rule_based_decision(
        self,
        original_query: str,
        plan_steps: List[Dict[str, Any]],
        research_history: List[ResearchStep],
        current_step_index: int
    ) -> PolicyDecision:
        """
        基于规则的策略决策（快速、无LLM调用）

        规则逻辑：
        1. 如果所有步骤质量>阈值，且收集了足够信息 → FINISH
        2. 如果当前步骤质量低，但还有其他步骤 → CONTINUE
        3. 如果多个步骤质量都低 → REVISE（重新规划）
        """
        # 计算整体质量
        avg_quality = sum(s.quality_score for s in research_history) / len(research_history) if research_history else 0
        low_quality_count = sum(1 for s in research_history if s.quality_score < self.min_quality_threshold)

        # 决策逻辑
        # Case 1: 质量良好，已收集足够信息 → FINISH
        if avg_quality > 0.6 and len(research_history) >= 2:
            return PolicyDecision(
                action=PolicyAction.FINISH,
                confidence=0.85,
                justification=f"Sufficient high-quality information collected (avg quality: {avg_quality:.2f})",
                next_step_index=None
            )

        # Case 2: 还有步骤未完成 → CONTINUE
        if current_step_index < len(plan_steps):
            confidence = 0.8 if avg_quality > 0.5 else 0.6
            return PolicyDecision(
                action=PolicyAction.CONTINUE,
                confidence=confidence,
                justification=f"Continuing with step {current_step_index + 1}/{len(plan_steps)}",
                next_step_index=current_step_index
            )

        # Case 3: 多个步骤质量低 → REVISE
        if low_quality_count >= 2:
            self.logger.warning(f"🔄 {low_quality_count} steps with low quality, consider revision")
            return PolicyDecision(
                action=PolicyAction.REVISE,
                confidence=0.7,
                justification=f"{low_quality_count} steps had low retrieval quality",
                next_step_index=None,
                plan_revision={'suggestion': 'expand search scope or simplify query'}
            )

        # Default: FINISH with moderate confidence
        return PolicyDecision(
            action=PolicyAction.FINISH,
            confidence=0.7,
            justification="Plan completed, proceeding to final synthesis",
            next_step_index=None
        )

    async def _llm_based_decision(
        self,
        original_query: str,
        plan_steps: List[Dict[str, Any]],
        research_history: List[ResearchStep],
        current_step_index: int
    ) -> PolicyDecision:
        """
        基于LLM的策略决策（更智能但更慢）

        让LLM作为"master strategist"分析研究进展并做出决策
        """
        try:
            # 构建研究历史总结
            history_summary = "\n".join([
                f"Step {s.step_index + 1}: {s.sub_question}\n  Summary: {s.summary}\n  Quality: {s.quality_score:.2f}"
                for s in research_history
            ])

            # 构建计划总结
            plan_summary = "\n".join([
                f"{i + 1}. {step.get('sub_question', step.get('description', 'N/A'))}"
                for i, step in enumerate(plan_steps)
            ])

            prompt = f"""You are a master research strategist. Analyze the research progress and decide the next action.

Original Question: {original_query}

Research Plan:
{plan_summary}

Completed Steps ({len(research_history)}/{len(plan_steps)}):
{history_summary}

Current Step Index: {current_step_index}

Based on the research history, decide:
- **FINISH**: If sufficient information has been gathered to answer the original question
- **CONTINUE**: If more research steps are needed
- **REVISE**: If the current plan is not working (multiple low-quality results)

Output format (JSON):
{{
    "action": "FINISH|CONTINUE|REVISE",
    "confidence": 0.0-1.0,
    "justification": "brief reason (max 150 chars)"
}}"""

            if hasattr(self.llm_generator, 'generate_json'):
                response = await self.llm_generator.generate_json(prompt)
            elif callable(self.llm_generator):
                response_text = await self.llm_generator(prompt)
                import json
                response = json.loads(response_text)
            else:
                raise ValueError("Invalid LLM generator")

            action = PolicyAction(response['action'].lower())
            confidence = float(response.get('confidence', 0.8))
            justification = response.get('justification', 'LLM-based decision')

            next_step = current_step_index if action == PolicyAction.CONTINUE else None

            self.logger.info(
                f"🤖 LLM Policy Decision: {action.value.upper()} "
                f"(confidence={confidence:.2f})"
            )

            return PolicyDecision(
                action=action,
                confidence=confidence,
                justification=justification,
                next_step_index=next_step
            )

        except Exception as e:
            self.logger.error(f"LLM policy decision failed: {e}, falling back to rule-based")
            return await self._rule_based_decision(
                original_query, plan_steps, research_history, current_step_index
            )


# ===== 便捷工厂函数 =====

def create_default_policy_agent() -> PolicyAgent:
    """创建默认策略代理（基于规则）"""
    return PolicyAgent(
        max_iterations=5,
        min_quality_threshold=0.3,
        use_llm=False
    )


def create_llm_policy_agent(llm_generator: Any) -> PolicyAgent:
    """创建LLM驱动的策略代理（更智能）"""
    return PolicyAgent(
        max_iterations=7,  # LLM模式可以允许更多迭代
        min_quality_threshold=0.3,
        use_llm=True,
        llm_generator=llm_generator
    )


def create_conservative_policy_agent() -> PolicyAgent:
    """创建保守的策略代理（更快结束）"""
    return PolicyAgent(
        max_iterations=3,  # 更快结束
        min_quality_threshold=0.5,  # 更高质量要求
        use_llm=False
    )
