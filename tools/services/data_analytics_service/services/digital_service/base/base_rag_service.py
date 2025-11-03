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

# 使用配置系统
try:
    from core.config.mcp_config import MCPConfig
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    MCPConfig = None

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

        # 初始化 File Processors（可选，支持多模态）
        self._init_file_processors()

        self.logger.info(f"Initialized {self.__class__.__name__} (mode={self.config.mode})")

    def _init_isa_model(self):
        """初始化 ISA Model 客户端（直接使用，无中间层）"""
        if not ISA_MODEL_AVAILABLE:
            self.logger.warning("isa_model not available")
            return

        try:
            # 优先使用配置系统，回退到环境变量
            if CONFIG_AVAILABLE:
                config = MCPConfig.from_env()
                base_url = config.isa_service_url
                api_key = config.isa_api_key
            else:
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

    def _init_file_processors(self):
        """
        初始化文件处理器（可选，支持多模态）

        安全初始化：如果依赖不可用，降级处理，不影响原有功能
        """
        try:
            from tools.services.data_analytics_service.processors.file_processors import (
                PDFProcessor,
                TextProcessor,
                IMAGE_PROCESSOR_AVAILABLE,
                ImageProcessor,
                AUDIO_PROCESSOR_AVAILABLE,
                AudioProcessor,
                VIDEO_PROCESSOR_AVAILABLE,
                VideoProcessor
            )

            extra_config = self.config.extra_config or {}

            # 必需的处理器
            self.pdf_processor = PDFProcessor(extra_config)
            self.text_processor = TextProcessor(extra_config)

            # 可选的处理器（根据依赖可用性）
            self.image_processor = ImageProcessor(extra_config) if IMAGE_PROCESSOR_AVAILABLE else None
            self.audio_processor = AudioProcessor(extra_config) if AUDIO_PROCESSOR_AVAILABLE else None
            self.video_processor = VideoProcessor(extra_config) if VIDEO_PROCESSOR_AVAILABLE else None

            # 标记已初始化
            self.file_processors_available = True

            processors_status = []
            processors_status.append("pdf")
            processors_status.append("text")
            if IMAGE_PROCESSOR_AVAILABLE:
                processors_status.append("image")
            if AUDIO_PROCESSOR_AVAILABLE:
                processors_status.append("audio")
            if VIDEO_PROCESSOR_AVAILABLE:
                processors_status.append("video")

            self.logger.info(f"✅ File processors initialized: {', '.join(processors_status)}")

        except Exception as e:
            # 安全降级：初始化失败不影响原有功能
            self.logger.warning(f"File processors initialization failed (will fallback to text-only): {e}")
            self.pdf_processor = None
            self.text_processor = None
            self.image_processor = None
            self.audio_processor = None
            self.video_processor = None
            self.file_processors_available = False

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
                retrieval_sources=[source.model_dump() for source in retrieval_result.sources],
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

    # ========== File Processing Methods (多模态支持) ==========

    async def _process_content(self, request: RAGStoreRequest) -> str:
        """
        统一处理所有类型的内容 → 提取文本

        支持的类型：
        - text: 直接返回（默认，保持向后兼容）
        - pdf: PDF文本 + 可选图片描述
        - image: 图片描述 + OCR
        - audio: 音频转文本
        - video: 视频转文本

        Args:
            request: 存储请求（包含 content 和 content_type）

        Returns:
            提取的文本内容

        注意：
        - 对于 text 类型，直接返回，保持原有行为（向后兼容）
        - 对于其他类型，如果对应的 processor 不可用，降级返回简化文本
        """
        content_type = request.content_type

        # 默认类型：text（向后兼容）
        if content_type == 'text' or not content_type:
            return request.content

        # 如果 file processors 不可用，降级处理
        if not self.file_processors_available:
            self.logger.warning(f"File processors not available, treating {content_type} as text")
            return str(request.content)

        # 根据类型路由
        try:
            if content_type == 'pdf':
                return await self._extract_text_from_pdf(request)

            elif content_type == 'image':
                return await self._extract_text_from_image(request)

            elif content_type == 'audio':
                return await self._extract_text_from_audio(request)

            elif content_type == 'video':
                return await self._extract_text_from_video(request)

            else:
                self.logger.warning(f"Unknown content_type: {content_type}, treating as text")
                return str(request.content)

        except Exception as e:
            # 处理失败时降级
            self.logger.error(f"Failed to process {content_type}: {e}, falling back to text")
            return str(request.content)

    async def _extract_text_from_pdf(self, request: RAGStoreRequest) -> str:
        """
        PDF → 文本（+ 可选图片描述）

        Args:
            request: 存储请求，content 为 PDF 文件路径

        Returns:
            提取的文本内容
        """
        if not self.pdf_processor:
            self.logger.warning("PDF processor not available")
            return f"PDF file: {request.content}"

        try:
            result = await self.pdf_processor.process_pdf_unified(
                request.content,  # pdf_path
                {'extract_text': True, 'extract_images': True}
            )

            if not result.get('success'):
                raise ValueError(f"PDF processing failed: {result.get('error')}")

            # 提取文本
            text_extraction = result.get('text_extraction', {})
            full_text = text_extraction.get('full_text', '')

            if not full_text or not full_text.strip():
                self.logger.warning("PDF text extraction returned empty result")
                return f"PDF file: {request.content} (empty content)"

            # TODO: 可选处理图片（使用 VLM）
            # enable_vlm = self.config.extra_config.get('enable_vlm_analysis', False)
            # if enable_vlm:
            #     images = result.get('image_analysis', {}).get('extracted_images', [])
            #     if images:
            #         image_descriptions = await self._process_images_with_vlm(images)
            #         full_text += "\n\n图片内容:\n" + "\n".join(image_descriptions)

            return full_text

        except Exception as e:
            self.logger.error(f"PDF text extraction failed: {e}")
            raise

    async def _extract_text_from_image(self, request: RAGStoreRequest) -> str:
        """
        Image → 文本描述（OCR + VLM）

        Args:
            request: 存储请求，content 为图片文件路径

        Returns:
            图片的文本描述
        """
        if not self.image_processor:
            self.logger.warning("Image processor not available")
            return f"Image file: {request.content}"

        try:
            result = await self.image_processor.analyze_image(request.content)

            description = result.get('description', '')
            ocr_text = result.get('ocr_text', '')

            if ocr_text:
                return f"{description}\n\nOCR Text:\n{ocr_text}"
            else:
                return description or f"Image file: {request.content}"

        except Exception as e:
            self.logger.error(f"Image text extraction failed: {e}")
            return f"Image file: {request.content} (processing failed)"

    async def _extract_text_from_audio(self, request: RAGStoreRequest) -> str:
        """
        Audio → 转录文本

        Args:
            request: 存储请求，content 为音频文件路径

        Returns:
            音频转录的文本
        """
        if not self.audio_processor:
            self.logger.warning("Audio processor not available")
            return f"Audio file: {request.content}"

        try:
            result = await self.audio_processor.transcribe(request.content)
            transcript = result.get('transcript', '')

            if not transcript or not transcript.strip():
                return f"Audio file: {request.content} (empty transcript)"

            return transcript

        except Exception as e:
            self.logger.error(f"Audio transcription failed: {e}")
            return f"Audio file: {request.content} (transcription failed)"

    async def _extract_text_from_video(self, request: RAGStoreRequest) -> str:
        """
        Video → 转录文本（音频 + 可选字幕）

        Args:
            request: 存储请求，content 为视频文件路径

        Returns:
            视频转录的文本
        """
        if not self.video_processor:
            self.logger.warning("Video processor not available")
            return f"Video file: {request.content}"

        try:
            result = await self.video_processor.extract_transcript(request.content)
            transcript = result.get('transcript', '')

            if not transcript or not transcript.strip():
                return f"Video file: {request.content} (empty transcript)"

            return transcript

        except Exception as e:
            self.logger.error(f"Video transcription failed: {e}")
            return f"Video file: {request.content} (transcription failed)"
