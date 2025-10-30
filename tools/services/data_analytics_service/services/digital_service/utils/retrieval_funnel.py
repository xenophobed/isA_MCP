#!/usr/bin/env python3
"""
Multi-Stage Retrieval Funnel
多阶段检索漏斗 - 从广泛召回到精确排序再到上下文蒸馏

基于Deep-Thinking RAG论文的核心思想：
Stage 1: Broad Recall (广泛召回) - 使用hybrid/semantic/keyword search
Stage 2: High Precision (精确重排) - 使用Cross-Encoder reranking
Stage 3: Contextual Distillation (上下文蒸馏) - 使用LLM压缩和总结
"""

import logging
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """检索配置"""
    # Stage 1: Broad Recall
    initial_top_k: int = 10  # 初始检索数量（广泛召回）
    search_strategy: Literal["auto", "vector", "keyword", "hybrid"] = "auto"

    # Stage 2: High Precision
    enable_rerank: bool = True
    rerank_top_n: int = 3  # 重排后保留的数量
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Stage 3: Contextual Distillation
    enable_distillation: bool = True
    max_distilled_length: int = 500  # 蒸馏后的最大长度


class MultiStageRetrievalFunnel:
    """
    多阶段检索漏斗

    核心流程：
    1. Broad Recall: 使用多种检索策略获取候选文档（top_k=10）
    2. High Precision: 使用Cross-Encoder对候选文档精确重排（保留top_n=3）
    3. Contextual Distillation: 使用LLM将top_n文档压缩成单一连贯段落
    """

    def __init__(self, config: RetrievalConfig):
        self.config = config
        self._reranker = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def reranker(self) -> CrossEncoder:
        """懒加载Cross-Encoder模型"""
        if self._reranker is None and self.config.enable_rerank:
            try:
                self._reranker = CrossEncoder(self.config.rerank_model)
                self.logger.info(f"✅ Cross-Encoder loaded: {self.config.rerank_model}")
            except Exception as e:
                self.logger.error(f"❌ Failed to load Cross-Encoder: {e}")
                self._reranker = None
        return self._reranker

    async def execute_funnel(
        self,
        query: str,
        initial_results: List[Dict[str, Any]],
        llm_generator: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        执行完整的三阶段检索漏斗

        Args:
            query: 用户查询
            initial_results: 初始检索结果（来自Stage 1）
            llm_generator: LLM生成器（用于Stage 3蒸馏）

        Returns:
            包含三阶段结果的字典
        """
        try:
            # Stage 1: Broad Recall (已由外部完成，这里接收)
            stage1_results = initial_results[:self.config.initial_top_k]
            self.logger.info(f"📊 Stage 1 (Broad Recall): {len(stage1_results)} candidates")

            # Stage 2: High Precision Reranking
            stage2_results = await self._stage2_rerank(query, stage1_results)
            self.logger.info(f"🎯 Stage 2 (Reranking): {len(stage2_results)} high-precision docs")

            # Stage 3: Contextual Distillation
            distilled_context = None
            if self.config.enable_distillation and llm_generator:
                distilled_context = await self._stage3_distill(
                    query, stage2_results, llm_generator
                )
                self.logger.info(f"✂️ Stage 3 (Distillation): {len(distilled_context)} chars")

            return {
                'stage1_broad_recall': stage1_results,
                'stage2_reranked': stage2_results,
                'stage3_distilled': distilled_context,
                'final_sources': stage2_results,  # 用于citation
                'funnel_metadata': {
                    'initial_count': len(stage1_results),
                    'reranked_count': len(stage2_results),
                    'distilled': distilled_context is not None
                }
            }

        except Exception as e:
            self.logger.error(f"Retrieval funnel failed: {e}")
            return {
                'stage1_broad_recall': initial_results,
                'stage2_reranked': initial_results[:self.config.rerank_top_n],
                'stage3_distilled': None,
                'final_sources': initial_results[:self.config.rerank_top_n],
                'funnel_metadata': {'error': str(e)}
            }

    async def _stage2_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: 高精度重排序

        使用Cross-Encoder对文档进行深度相关性评分，然后重新排序
        """
        if not self.config.enable_rerank or not documents:
            return documents[:self.config.rerank_top_n]

        if not self.reranker:
            self.logger.warning("Cross-Encoder not available, skipping rerank")
            return documents[:self.config.rerank_top_n]

        try:
            # 准备query-document pairs
            pairs = [(query, doc.get('text', '')) for doc in documents]

            # 使用Cross-Encoder计算相关性分数
            scores = self.reranker.predict(pairs)

            # 将文档与分数配对
            doc_scores = list(zip(documents, scores))

            # 按分数降序排序
            doc_scores.sort(key=lambda x: x[1], reverse=True)

            # 保留top_n文档
            reranked_docs = [
                {**doc, 'rerank_score': float(score)}
                for doc, score in doc_scores[:self.config.rerank_top_n]
            ]

            self.logger.debug(f"Reranked scores: {[f'{s:.3f}' for _, s in doc_scores[:3]]}")
            return reranked_docs

        except Exception as e:
            self.logger.error(f"Reranking failed: {e}")
            return documents[:self.config.rerank_top_n]

    async def _stage3_distill(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        llm_generator: Any
    ) -> Optional[str]:
        """
        Stage 3: 上下文蒸馏

        使用LLM将多个高质量文档压缩成单一、连贯的段落
        这是论文中的"Contextual Distillation"步骤
        """
        if not documents:
            return None

        try:
            # 构建上下文
            context_parts = []
            for i, doc in enumerate(documents):
                text = doc.get('text', '')
                context_parts.append(f"[Document {i+1}]\n{text}")

            full_context = "\n\n".join(context_parts)

            # 构建蒸馏prompt
            distillation_prompt = f"""You are a contextual distillation assistant.
Your task is to synthesize the following {len(documents)} document snippets into a single, concise, and coherent paragraph that directly answers the question: "{query}".

Requirements:
1. Remove redundant information
2. Organize content logically
3. Keep only the most relevant facts
4. Maximum {self.config.max_distilled_length} characters
5. DO NOT add any information not present in the documents

Documents:
{full_context}

Distilled Context (one paragraph):"""

            # 调用LLM进行蒸馏
            if hasattr(llm_generator, 'generate'):
                distilled = await llm_generator.generate(distillation_prompt)
            elif callable(llm_generator):
                distilled = await llm_generator(distillation_prompt)
            else:
                self.logger.warning("Invalid llm_generator, skipping distillation")
                return full_context[:self.config.max_distilled_length]

            # 截断到最大长度
            if len(distilled) > self.config.max_distilled_length:
                distilled = distilled[:self.config.max_distilled_length] + "..."

            return distilled

        except Exception as e:
            self.logger.error(f"Distillation failed: {e}")
            # 降级：返回拼接的原文本
            return "\n\n".join([doc.get('text', '')[:200] for doc in documents])


# ===== 便捷工厂函数 =====

def create_default_funnel() -> MultiStageRetrievalFunnel:
    """创建默认配置的检索漏斗"""
    config = RetrievalConfig(
        initial_top_k=10,
        search_strategy="auto",
        enable_rerank=True,
        rerank_top_n=3,
        enable_distillation=True,
        max_distilled_length=500
    )
    return MultiStageRetrievalFunnel(config)


def create_fast_funnel() -> MultiStageRetrievalFunnel:
    """创建快速配置（禁用蒸馏）"""
    config = RetrievalConfig(
        initial_top_k=5,
        enable_rerank=True,
        rerank_top_n=3,
        enable_distillation=False  # 快速模式不使用蒸馏
    )
    return MultiStageRetrievalFunnel(config)


def create_precision_funnel() -> MultiStageRetrievalFunnel:
    """创建高精度配置（增加初始召回和蒸馏）"""
    config = RetrievalConfig(
        initial_top_k=20,  # 更多初始候选
        enable_rerank=True,
        rerank_top_n=5,    # 保留更多高质量文档
        enable_distillation=True,
        max_distilled_length=800  # 更长的蒸馏结果
    )
    return MultiStageRetrievalFunnel(config)
