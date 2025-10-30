#!/usr/bin/env python3
"""
Retrieval Supervisor - 检索策略智能路由器
自动选择最佳检索策略（vector/keyword/hybrid）

基于Deep-Thinking RAG论文：
- 概念性查询 → Vector Search (语义搜索)
- 精确术语查询 → Keyword Search (BM25/关键词)
- 混合查询 → Hybrid Search (RRF融合)
"""

import logging
import re
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """检索策略枚举"""
    VECTOR = "vector"      # 向量/语义搜索
    KEYWORD = "keyword"    # 关键词/BM25搜索
    HYBRID = "hybrid"      # 混合搜索（RRF融合）


@dataclass
class SupervisorDecision:
    """监督器决策结果"""
    strategy: SearchStrategy
    confidence: float  # 0-1, 决策置信度
    justification: str  # 决策理由
    metadata: Dict[str, Any]  # 额外信息（如检测到的特征）


class RetrievalSupervisor:
    """
    检索监督器 - 智能选择最佳检索策略

    核心逻辑：
    1. 分析查询特征（关键词、实体、概念性等）
    2. 基于规则或LLM判断最优策略
    3. 返回策略决策和理由
    """

    def __init__(
        self,
        use_llm: bool = False,
        llm_generator: Optional[Any] = None,
        fallback_strategy: SearchStrategy = SearchStrategy.HYBRID
    ):
        """
        Args:
            use_llm: 是否使用LLM进行决策（更准确但更慢）
            llm_generator: LLM生成器（如果use_llm=True）
            fallback_strategy: 无法决策时的默认策略
        """
        self.use_llm = use_llm
        self.llm_generator = llm_generator
        self.fallback_strategy = fallback_strategy
        self.logger = logging.getLogger(self.__class__.__name__)

    async def decide_strategy(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> SupervisorDecision:
        """
        决定最佳检索策略

        Args:
            query: 用户查询
            user_context: 用户上下文（如历史查询、偏好等）

        Returns:
            SupervisorDecision对象
        """
        if self.use_llm and self.llm_generator:
            return await self._llm_based_decision(query, user_context)
        else:
            return await self._rule_based_decision(query, user_context)

    async def _rule_based_decision(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> SupervisorDecision:
        """
        基于规则的策略决策（快速、无LLM调用）

        规则逻辑：
        1. 检测精确匹配特征 → Keyword Search
        2. 检测概念性特征 → Vector Search
        3. 无明显特征 → Hybrid Search
        """
        query_lower = query.lower()
        features = self._extract_query_features(query_lower)

        # 特征权重计分（使用更细粒度的评分）
        keyword_score = (
            features['has_quotes'] * 0.5 +         # 引号是强信号
            features['has_exact_terms'] * 0.4 +    # 精确术语是强信号
            features['has_codes'] * 0.3 +          # 代码/ID是强信号
            features['is_short'] * 0.15            # 短查询倾向keyword
        )

        vector_score = (
            features['is_conceptual'] * 0.5 +      # 概念性是强信号
            features['has_sentiment_words'] * 0.3 + # 情感词是强信号
            features['is_long'] * 0.2 +            # 长查询倾向vector
            features['has_abstract_words'] * 0.4   # 抽象概念是强信号
        )

        # 决策逻辑（降低阈值，使决策更敏感）
        if keyword_score > 0.3:  # 降低阈值从0.6到0.3
            strategy = SearchStrategy.KEYWORD
            confidence = min(keyword_score + 0.5, 0.95)  # 提升置信度
            justification = self._build_justification(features, "keyword")

        elif vector_score > 0.3:  # 降低阈值从0.6到0.3
            strategy = SearchStrategy.VECTOR
            confidence = min(vector_score + 0.5, 0.95)  # 提升置信度
            justification = self._build_justification(features, "vector")

        else:
            strategy = SearchStrategy.HYBRID
            confidence = 0.7  # Hybrid is safe default
            justification = "Query has mixed characteristics, using hybrid search for balanced recall and precision"

        self.logger.info(
            f"🚦 Supervisor Decision: {strategy.value.upper()} "
            f"(confidence={confidence:.2f}) - {justification[:60]}..."
        )

        return SupervisorDecision(
            strategy=strategy,
            confidence=confidence,
            justification=justification,
            metadata={
                'features': features,
                'keyword_score': keyword_score,
                'vector_score': vector_score,
                'decision_method': 'rule_based'
            }
        )

    def _extract_query_features(self, query: str) -> Dict[str, bool]:
        """提取查询特征"""
        return {
            # Keyword Search indicators
            'has_quotes': '"' in query or "'" in query,
            'has_exact_terms': any(term in query for term in ['exact:', 'term:', 'code:', 'id:']),
            'has_codes': bool(re.search(r'\b[A-Z0-9]{3,}\b', query)),  # e.g., "SKU123", "ITEM_1A"
            'is_short': len(query.split()) <= 5,

            # Vector Search indicators
            'is_conceptual': any(word in query for word in [
                'explain', 'describe', 'understand', 'concept', 'idea',
                'sentiment', 'feeling', 'opinion', 'analysis', 'overview'
            ]),
            'has_sentiment_words': any(word in query for word in [
                'good', 'bad', 'positive', 'negative', 'better', 'worse',
                'best', 'worst', 'recommend', 'suggest'
            ]),
            'has_abstract_words': any(word in query for word in [
                'strategy', 'approach', 'methodology', 'philosophy',
                'perspective', 'implication', 'significance'
            ]),
            'is_long': len(query.split()) > 15,

            # Hybrid indicators
            'has_and_or': ' and ' in query or ' or ' in query,
            'has_multiple_clauses': len(query.split(',')) > 1 or len(query.split(';')) > 1
        }

    def _build_justification(
        self,
        features: Dict[str, bool],
        decision_type: str
    ) -> str:
        """构建决策理由"""
        if decision_type == "keyword":
            reasons = []
            if features['has_quotes']:
                reasons.append("contains quoted exact phrases")
            if features['has_exact_terms']:
                reasons.append("uses exact term identifiers")
            if features['has_codes']:
                reasons.append("contains specific codes/IDs")
            if features['is_short']:
                reasons.append("is a short, precise query")

            return f"Keyword search recommended: query {', '.join(reasons)}"

        elif decision_type == "vector":
            reasons = []
            if features['is_conceptual']:
                reasons.append("is conceptual in nature")
            if features['has_sentiment_words']:
                reasons.append("involves sentiment/opinion")
            if features['has_abstract_words']:
                reasons.append("contains abstract concepts")
            if features['is_long']:
                reasons.append("is a complex, multi-part query")

            return f"Vector search recommended: query {', '.join(reasons)}"

        return "Hybrid search recommended: balanced approach for this query"

    async def _llm_based_decision(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> SupervisorDecision:
        """
        基于LLM的策略决策（更准确但更慢）

        使用LLM分析查询并选择最佳策略
        """
        try:
            prompt = f"""You are a retrieval strategy expert. Analyze the query and decide the best search strategy.

Query: "{query}"

Available strategies:
1. **vector**: Best for conceptual, semantic, or similarity-based queries
2. **keyword**: Best for queries with specific terms, codes, exact phrases, or IDs
3. **hybrid**: Combines both, good for balanced recall and precision

Choose ONE strategy and provide a brief justification (max 100 chars).

Output format (JSON):
{{
    "strategy": "vector|keyword|hybrid",
    "confidence": 0.0-1.0,
    "justification": "brief reason"
}}"""

            # 调用LLM
            if hasattr(self.llm_generator, 'generate_json'):
                response = await self.llm_generator.generate_json(prompt)
            elif callable(self.llm_generator):
                response_text = await self.llm_generator(prompt)
                # 简单JSON解析
                import json
                response = json.loads(response_text)
            else:
                raise ValueError("Invalid llm_generator")

            strategy = SearchStrategy(response['strategy'])
            confidence = float(response.get('confidence', 0.8))
            justification = response.get('justification', 'LLM-based decision')

            self.logger.info(
                f"🤖 LLM Supervisor Decision: {strategy.value.upper()} "
                f"(confidence={confidence:.2f})"
            )

            return SupervisorDecision(
                strategy=strategy,
                confidence=confidence,
                justification=justification,
                metadata={'decision_method': 'llm_based'}
            )

        except Exception as e:
            self.logger.error(f"LLM decision failed: {e}, falling back to rule-based")
            return await self._rule_based_decision(query, user_context)


# ===== 便捷工厂函数 =====

def create_default_supervisor() -> RetrievalSupervisor:
    """创建默认监督器（基于规则）"""
    return RetrievalSupervisor(
        use_llm=False,
        fallback_strategy=SearchStrategy.HYBRID
    )


def create_llm_supervisor(llm_generator: Any) -> RetrievalSupervisor:
    """创建LLM驱动的监督器（更准确）"""
    return RetrievalSupervisor(
        use_llm=True,
        llm_generator=llm_generator,
        fallback_strategy=SearchStrategy.HYBRID
    )


def create_fast_supervisor() -> RetrievalSupervisor:
    """创建快速监督器（总是使用hybrid）"""
    supervisor = RetrievalSupervisor(use_llm=False)
    # Override decide_strategy to always return hybrid
    async def fast_decide(query, ctx=None):
        return SupervisorDecision(
            strategy=SearchStrategy.HYBRID,
            confidence=0.9,
            justification="Fast mode: always use hybrid for reliability",
            metadata={'decision_method': 'fast_mode'}
        )
    supervisor.decide_strategy = fast_decide
    return supervisor
