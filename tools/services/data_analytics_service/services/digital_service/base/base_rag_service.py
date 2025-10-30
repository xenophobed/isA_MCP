#!/usr/bin/env python3
"""
Base RAG Service - RAG服务抽象基类

职责：
1. 定义统一接口（使用 Pydantic 数据模型）
2. 提供通用工具方法
3. 不初始化任何具体存储（由子类决定用 Qdrant/Neo4j/PostgreSQL/MinIO）
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

# Pydantic 数据模型
from .rag_models import (
    RAGConfig,
    RAGStoreRequest,
    RAGRetrieveRequest,
    RAGGenerateRequest,
    RAGResult,
    RAGSource
)

# 直接使用 isa_model（无中间层）
try:
    from isa_model.inference_client import AsyncISAModel
    ISA_MODEL_AVAILABLE = True
except ImportError:
    ISA_MODEL_AVAILABLE = False
    AsyncISAModel = None

logger = logging.getLogger(__name__)


class BaseRAGService(ABC):
    """
    RAG 服务抽象基类

    所有 RAG 实现必须继承此类并实现三个核心方法：
    - store() - 存储内容
    - retrieve() - 检索相关内容
    - generate() - 生成回答

    基类职责：
    - 定义统一接口（使用 Pydantic 数据模型）
    - 提供通用工具方法（分块、embedding、LLM 等）
    - 不初始化具体存储（由子类决定用什么：Qdrant/Neo4j/PostgreSQL/MinIO）
    """

    def __init__(self, config: RAGConfig):
        """
        初始化基类

        Args:
            config: RAG 配置（Pydantic 模型）
        """
        self.config = config
        self.mode = config.mode
        self.logger = logging.getLogger(self.__class__.__name__)

        # 初始化 ISA Model 客户端（所有 RAG 都需要）
        self.isa_model: Optional[AsyncISAModel] = None
        self._init_isa_model()

        self.logger.info(f"Initialized {self.__class__.__name__} (mode={self.config.mode})")

    def _init_isa_model(self):
        """初始化 ISA Model 客户端（直接使用，无中间层）"""
        if not ISA_MODEL_AVAILABLE:
            self.logger.warning("isa_model not available")
            return

        try:
            base_url = os.getenv('ISA_API_URL', 'http://localhost:8082')
            api_key = os.getenv('ISA_API_KEY')

            self.isa_model = AsyncISAModel(
                base_url=base_url,
                api_key=api_key
            )
            self.logger.info(f"✅ ISA Model initialized: {base_url}")

        except Exception as e:
            self.logger.error(f"ISA Model initialization failed: {e}")
            self.isa_model = None

    # ========== 抽象方法 - 子类必须实现 ==========

    @abstractmethod
    async def store(self, request: RAGStoreRequest) -> RAGResult:
        """
        存储内容（子类实现）

        Args:
            request: 存储请求（Pydantic 验证）

        Returns:
            RAGResult - 统一返回格式

        示例：
            SimpleRAG → 存储到 Qdrant
            GraphRAG → 存储到 Neo4j + Qdrant
            CustomRAG → 存储到 MinIO + Qdrant
        """
        pass

    @abstractmethod
    async def retrieve(self, request: RAGRetrieveRequest) -> RAGResult:
        """
        检索相关内容（子类实现）

        Args:
            request: 检索请求（Pydantic 验证）

        Returns:
            RAGResult - 包含 sources 列表
        """
        pass

    @abstractmethod
    async def generate(self, request: RAGGenerateRequest) -> RAGResult:
        """
        生成回答（子类实现）

        Args:
            request: 生成请求（Pydantic 验证）

        Returns:
            RAGResult - 包含生成的回答
        """
        pass

    # ========== 通用工具方法 - 所有子类可用 ==========

    def _chunk_text(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        简单的文本分块（不依赖外部服务）

        Args:
            text: 要分块的文本
            chunk_size: 块大小（字符数），默认使用 config.chunk_size
            overlap: 重叠大小（字符数），默认使用 config.overlap

        Returns:
            分块列表，每个块包含 {'id', 'text', 'start_pos', 'end_pos'}
        """
        chunk_size = chunk_size or self.config.chunk_size
        overlap = overlap or self.config.overlap

        self.logger.info(f"[CHUNK_CONFIG] chunk_size={chunk_size}, overlap={overlap}, text_len={len(text)}, config.chunk_size={self.config.chunk_size}")

        chunks = []
        current_pos = 0
        chunk_id = 0

        # If text is shorter than chunk_size, return as single chunk
        if len(text) <= chunk_size:
            chunks.append({
                'id': 0,
                'text': text.strip(),
                'start_pos': 0,
                'end_pos': len(text)
            })
            self.logger.info(f"Text shorter than chunk_size ({len(text)} <= {chunk_size}), returning single chunk")
            return chunks

        while current_pos < len(text):
            # 计算结束位置
            end_pos = min(current_pos + chunk_size, len(text))

            # 如果不是最后一块，尝试在句子边界处分割
            if end_pos < len(text):
                # 在边界附近查找句子结束符
                search_start = max(current_pos, end_pos - 100)
                search_text = text[search_start:min(end_pos + 100, len(text))]

                # 查找句子结束符
                best_ending = -1
                for ending in ['. ', '! ', '? ', '\n\n', '。', '！', '？']:
                    pos = search_text.rfind(ending)
                    if pos > 50:  # 确保有足够内容
                        best_ending = max(best_ending, search_start + pos + len(ending))

                if best_ending > current_pos:
                    end_pos = best_ending

            # 提取块文本
            chunk_text = text[current_pos:end_pos].strip()

            if chunk_text:
                chunks.append({
                    'id': chunk_id,
                    'text': chunk_text,
                    'start_pos': current_pos,
                    'end_pos': end_pos
                })
                chunk_id += 1

            # 移动到下一个位置（考虑重叠）
            # FIX: Don't use max() - it causes 1-char-per-chunk bug for short texts!
            # Simply move to end_pos - overlap, or if that doesn't progress, move forward by chunk_size
            next_pos = end_pos - overlap
            if next_pos <= current_pos:
                # If overlap causes us to not progress, skip overlap and move forward
                next_pos = current_pos + chunk_size

            current_pos = next_pos

            # 防止无限循环
            if current_pos >= len(text):
                break

        return chunks

    async def _generate_embedding(self, text: str, model: Optional[str] = None) -> Optional[List[float]]:
        """
        生成文本嵌入向量（直接使用 ISA Model）

        Args:
            text: 要生成嵌入的文本
            model: 嵌入模型名称，默认使用 config.embedding_model

        Returns:
            嵌入向量列表，失败返回 None
        """
        if not self.isa_model:
            self.logger.error("ISA Model not available")
            return None

        try:
            model = model or self.config.embedding_model
            response = await self.isa_model.embeddings.create(
                input=text,
                model=model
            )

            if response and response.data and len(response.data) > 0:
                return response.data[0].embedding

            self.logger.error("Empty embedding response")
            return None

        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            return None

    async def _generate_response(self,
                                prompt: str,
                                model: Optional[str] = None,
                                temperature: float = 0.7,
                                max_tokens: int = 1000) -> Optional[str]:
        """
        使用 LLM 生成响应（直接使用 ISA Model）

        Args:
            prompt: 提示词
            model: 模型名称，默认使用 GPT-4
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            生成的文本，失败返回 None
        """
        if not self.isa_model:
            self.logger.error("ISA Model not available")
            return None

        try:
            model = model or "gpt-4o-mini"
            response = await self.isa_model.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            if response and response.choices and len(response.choices) > 0:
                return response.choices[0].message.content

            self.logger.error("Empty LLM response")
            return None

        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            return None

    def _build_context(self, sources: List[RAGSource], use_citations: bool = True) -> str:
        """
        从 RAGSource 列表构建上下文字符串

        Args:
            sources: 检索到的源列表
            use_citations: 是否使用引用格式 [1], [2] 等

        Returns:
            格式化的上下文字符串
        """
        if not sources:
            return ""

        context_texts = []
        for i, source in enumerate(sources[:self.config.top_k]):
            if use_citations:
                # 带引用 ID: [1] text...
                context_texts.append(f"[{i+1}] {source.text}")
            else:
                # 传统格式: Context 1 (Score: 0.95): text...
                context_texts.append(f"Context {i+1} (Score: {source.score:.3f}): {source.text}")

        return "\n\n".join(context_texts)

    # ========== Convenience Methods ==========

    async def query(self,
                   query: str,
                   user_id: str,
                   options: Optional[Dict[str, Any]] = None) -> RAGResult:
        """
        Convenience method: retrieve() + generate() combined

        This is the full RAG pipeline in one call.

        Args:
            query: User question
            user_id: User identifier
            options: Combined options for retrieve and generate

        Returns:
            RAG result with generated response
        """
        options = options or {}

        # 1. Retrieve
        retrieval_result = await self.retrieve(
            RAGRetrieveRequest(
                query=query,
                user_id=user_id,
                top_k=options.get('top_k'),
                filters=options.get('filters'),
                options=options
            )
        )

        if not retrieval_result.success:
            return retrieval_result

        # 2. Generate
        generation_result = await self.generate(
            RAGGenerateRequest(
                query=query,
                user_id=user_id,
                retrieval_sources=[source.dict() for source in retrieval_result.sources],
                options=options
            )
        )

        return generation_result

    def get_mode(self) -> str:
        """获取RAG模式"""
        return self.config.mode

    def get_config(self) -> RAGConfig:
        """获取配置"""
        return self.config
