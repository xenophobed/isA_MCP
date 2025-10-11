#!/usr/bin/env python3
"""
Custom RAG Service for Multimodal PDF Processing

完整的 PDF 多模态 RAG 服务，包含：
1. Ingestion (存储): PDF 提取 → 图片 VLM 描述 → MinIO 存储 → Embedding → Supabase pgvector  
2. Retrieval (检索): 查询 → 检索相关文本和图片
3. Generation (生成): LLM 生成答案（包含图片链接）

使用现有组件：
- PDFExtractService: PDF 处理和图像提取
- ImageAnalyzer: VLM 图像描述生成
- MinIOIntegration: 图片存储和 URL 生成
- EmbeddingIntegration: 文本 embedding 生成
- VectorDBIntegration: Supabase pgvector 存储
"""

import asyncio
import logging
import time
import base64
import uuid
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# 导入现有组件
from ..pdf_extract_service import PDFExtractService
from tools.services.intelligence_service.vision.image_analyzer import analyze as vlm_analyze
from ..integrations.minio_integration import get_minio_integration
from ..integrations.embedding_integration import EmbeddingIntegration
from ..integrations.vector_db_integration import VectorDBIntegration
from ..config.analytics_config import VectorDBPolicy

logger = logging.getLogger(__name__)


class CustomRAGService:
    """
    Custom Multimodal RAG Service for PDF Processing
    
    核心功能：
    1. ingest_pdf() - 完整的 PDF 摄取流程（文本+图片）
    2. retrieve() - 检索相关内容（文本+图片）  
    3. generate() - 生成答案（带图片引用）
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.service_name = "custom_rag_service"
        self.version = "1.0.0"
        
        # 初始化组件
        self.pdf_extract_service = PDFExtractService(self.config)
        self.minio_integration = get_minio_integration(self.config)
        self.embedding_integration = EmbeddingIntegration()
        
        # 向量数据库配置
        vector_db_policy = VectorDBPolicy.STORAGE  # 使用 Supabase
        self.vector_db_integration = VectorDBIntegration(
            policy=vector_db_policy,
            config=self.config
        )
        
        # 配置参数
        self.chunk_size = self.config.get('chunk_size', 1000)
        self.chunk_overlap = self.config.get('chunk_overlap', 100)
        self.top_k = self.config.get('top_k_results', 5)
        
        logger.info(f"CustomRAGService initialized with vector DB: {vector_db_policy.value}")
    
    async def ingest_pdf(
        self,
        pdf_path: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        完整的 PDF 摄取流程
        
        流程：
        1. 使用 PDFExtractService 提取 PDF（文本 + 图片）
        2. 对每个图片使用 VLM 生成描述
        3. 上传图片到 MinIO，获取 URL
        4. 文本分块 + Embedding
        5. 存储到 Supabase pgvector（文本 chunk + 图片描述 + 图片 URL）
        
        Args:
            pdf_path: PDF 文件路径
            user_id: 用户 ID
            metadata: 额外元数据
            
        Returns:
            存储结果统计
        """
        start_time = time.time()
        
        try:
            metadata = metadata or {}
            pdf_name = Path(pdf_path).name
            
            logger.info(f"📥 开始 PDF 摄取: {pdf_name} (user: {user_id})")
            
            # ========== 阶段 1: 页面级多模态处理 ==========
            logger.info("🔧 阶段 1: 页面级多模态分析...")
            
            # 处理每一页（图+文一起）
            page_records = await self._process_pages_multimodal(
                pdf_path, user_id, pdf_name, metadata
            )
            
            logger.info(f"✅ 处理完成: {len(page_records)} 个页面")
            
            # ========== 阶段 2: 存储到 Supabase ==========
            logger.info("💾 阶段 2: 存储到 Supabase pgvector...")
            storage_result = await self._store_pages_to_vector_db(
                user_id, page_records, pdf_name
            )
            
            processing_time = time.time() - start_time
            
            # 统计信息
            total_images = sum(len(p.get('photo_urls', [])) for p in page_records)
            
            return {
                'success': True,
                'pdf_name': pdf_name,
                'user_id': user_id,
                'statistics': {
                    'pages_stored': len(page_records),
                    'images_stored': total_images,
                    'total_records': len(page_records),
                    'processing_time': processing_time
                },
                'storage_result': storage_result,
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"❌ PDF 摄取失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def _process_pages_multimodal(
        self,
        pdf_path: str,
        user_id: str,
        pdf_name: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        页面级多模态处理：每页作为一个 chunk
        
        流程：
        1. VLM 分析整页（page as photo） → summary + photo descriptions
        2. PDF Processor 提取文字
        3. PDF Processor 提取图片 → MinIO
        4. 合并: VLM_output + page_text → embedding
        
        Returns:
            页面记录列表，每个页面一条记录
        """
        from tools.services.data_analytics_service.processors.file_processors.pdf_processor import PDFProcessor
        
        pdf_processor = PDFProcessor(self.config)
        page_records = []
        
        # 1. 提取 PDF 完整信息（文字 + 图片）
        logger.info("📄 提取 PDF 内容...")
        result = await pdf_processor.process_pdf_unified(pdf_path, {
            'extract_text': True,
            'extract_images': True,
            'extract_tables': False
        })
        
        if not result.get('success'):
            logger.error(f"PDF 提取失败: {result.get('error')}")
            return []
        
        # 提取文字（按页） - 修复：使用 text_extraction 而不是 text_content
        text_extraction = result.get('text_extraction', {})
        pages_text_list = text_extraction.get('pages', [])  # 字符串列表，每个字符串是一页文字
        logger.info(f"提取到 {len(pages_text_list)} 个页面的文字")
        
        # 提取图片（按页分组）
        image_analysis = result.get('image_analysis', {})
        all_images = image_analysis.get('extracted_images', [])
        logger.info(f"提取到 {len(all_images)} 张图片")
        
        # 检查是否有页面
        if not pages_text_list:
            logger.warning("❌ 没有提取到任何页面！")
            return []
        
        # 限制处理的页面数量
        max_pages = self.config.get('max_pages')
        if max_pages and len(pages_text_list) > max_pages:
            logger.info(f"⚠️ 限制页面处理数量: {len(pages_text_list)} -> {max_pages}")
            pages_text_list = pages_text_list[:max_pages]
        
        # 2. 并发处理每一页
        logger.info(f"🔄 开始处理 {len(pages_text_list)} 个页面（页面级多模态分析）...")
        
        # 创建 semaphore 限制并发数
        max_concurrent = self.config.get('max_concurrent_pages', 3)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        tasks = []
        for page_idx, page_text in enumerate(pages_text_list, start=1):
            page_num = page_idx  # 页码从1开始
            
            # 获取该页的图片
            page_images = [
                img for img in all_images 
                if img.get('page_number') == page_num
            ]
            
            task = self._process_single_page_multimodal(
                pdf_path=pdf_path,
                page_number=page_num,
                page_text=page_text,
                page_images=page_images,
                user_id=user_id,
                pdf_name=pdf_name,
                metadata=metadata,
                semaphore=semaphore
            )
            tasks.append(task)
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查异常
        for idx, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(f"页面{idx}处理失败: {r}")
        
        # 过滤成功的结果
        page_records = [
            r for r in results 
            if r is not None and not isinstance(r, Exception)
        ]
        
        logger.info(f"✅ 页面处理完成: {len(page_records)}/{len(pages_text_list)} 成功")
        
        return page_records
    
    async def _process_single_page_multimodal(
        self,
        pdf_path: str,
        page_number: int,
        page_text: str,
        page_images: List[Dict[str, Any]],
        user_id: str,
        pdf_name: str,
        metadata: Dict[str, Any],
        semaphore: asyncio.Semaphore
    ) -> Optional[Dict[str, Any]]:
        """
        处理单个页面（多模态）
        
        Returns:
            页面记录: {
                'page_number': int,
                'text': str,  # VLM summary + page text + photo descriptions
                'embedding': List[float],
                'photo_urls': List[str],  # MinIO URLs
                'metadata': {...}
            }
        """
        async with semaphore:
            try:
                logger.info(f"📄 处理页面 {page_number}...")
                
                # 1. VLM 分析整页（可配置是否启用）
                enable_vlm = self.config.get('enable_vlm_analysis', True)
                if enable_vlm:
                    page_summary, photo_descriptions = await self._analyze_page_with_vlm(
                        pdf_path, page_number, page_text, len(page_images)
                    )
                else:
                    # 简化模式：不使用 VLM
                    page_summary = f"第{page_number}页"
                    photo_descriptions = [f"图片{i+1}" for i in range(len(page_images))]
                    logger.info(f"⚠️ VLM 分析已禁用（简化模式）")
                
                # 2. 上传页面图片到 MinIO（可配置是否启用）
                enable_minio = self.config.get('enable_minio_upload', True)
                photo_urls = []
                if enable_minio:
                    for idx, img_data in enumerate(page_images):
                        try:
                            photo_url = await self._upload_image_to_minio(
                                img_data, user_id, pdf_name, page_number, idx
                            )
                            if photo_url:
                                photo_urls.append(photo_url)
                        except Exception as e:
                            logger.warning(f"图片上传失败 (page={page_number}, img={idx}): {e}")
                            continue
                else:
                    # 简化模式：不上传 MinIO，只记录数量
                    photo_urls = [f"placeholder_url_{i}" for i in range(len(page_images))]
                    logger.info(f"⚠️ MinIO 上传已禁用（简化模式）")
                
                # 3. 合并文本：VLM summary + page text + photo descriptions
                combined_text = self._combine_page_content(
                    page_summary, page_text, photo_descriptions, photo_urls
                )
                
                # 4. 生成 embedding
                embedding = await self.embedding_integration.embed_text(combined_text)
                
                # 5. 创建页面记录
                page_record = {
                    'page_number': page_number,
                    'text': combined_text,
                    'embedding': embedding,
                    'photo_urls': photo_urls,
                    'metadata': {
                        'pdf_name': pdf_name,
                        'page_number': page_number,
                        'page_summary': page_summary,
                        'num_photos': len(photo_urls),
                        'photo_descriptions': photo_descriptions,
                        'content_type': 'page',
                        **metadata
                    }
                }
                
                logger.info(f"✅ 页面 {page_number} 处理完成 ({len(photo_urls)} 张图片)")
                return page_record
                
            except Exception as e:
                logger.error(f"❌ 页面 {page_number} 处理失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return None
    
    async def _analyze_page_with_vlm(
        self,
        pdf_path: str,
        page_number: int,
        page_text: str,
        num_photos: int
    ) -> Tuple[str, List[str]]:
        """
        VLM 分析整个页面
        
        Returns:
            (page_summary, [photo_1_description, photo_2_description, ...])
        """
        try:
            # 渲染页面为图片
            page_image_bytes = await self._render_pdf_page_as_image(pdf_path, page_number)
            
            if not page_image_bytes:
                # 如果渲染失败，使用文字生成简单 summary
                return f"页面 {page_number}", []
            
            # VLM 分析
            prompt = f"""
分析这个PDF页面（第{page_number}页）。页面包含 {num_photos} 张图片。

页面文字内容：
{page_text[:800] if page_text else '(无文字)'}...

请提供：
1. page_summary: 用1-2句话概括页面主题
2. photo_1: 第1张图片的内容描述（如果有）
3. photo_2: 第2张图片的内容描述（如果有）
...

格式：
page_summary: xxx
photo_1: xxx  
photo_2: xxx
"""
            
            result = await vlm_analyze(
                image=page_image_bytes,
                prompt=prompt,
                model="gpt-4o-mini",
                provider="yyds"
            )
            
            # 解析 VLM 输出
            if result.success:
                response_text = result.response.strip()
                page_summary, photo_descriptions = self._parse_vlm_response(response_text, num_photos)
                return page_summary, photo_descriptions
            else:
                logger.warning(f"VLM 分析失败: {result.error}")
                return f"页面 {page_number}", []
                
        except Exception as e:
            logger.error(f"VLM 页面分析失败: {e}")
            return f"页面 {page_number}", []
    
    async def _render_pdf_page_as_image(
        self,
        pdf_path: str,
        page_number: int
    ) -> Optional[bytes]:
        """将 PDF 页面渲染为图片（用于 VLM 分析）"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            page = doc[page_number - 1]  # PyMuPDF uses 0-based indexing
            
            # 渲染为图片（高质量）
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for quality
            img_bytes = pix.tobytes("png")
            
            doc.close()
            return img_bytes
            
        except Exception as e:
            logger.error(f"页面渲染失败 (page={page_number}): {e}")
            return None
    
    def _parse_vlm_response(self, response: str, num_photos: int) -> Tuple[str, List[str]]:
        """解析 VLM 输出"""
        page_summary = ""
        photo_descriptions = []
        
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('page_summary:'):
                page_summary = line.split(':', 1)[1].strip()
            elif line.startswith('photo_'):
                desc = line.split(':', 1)[1].strip() if ':' in line else ""
                photo_descriptions.append(desc)
        
        # 如果没有解析到 summary，使用第一行
        if not page_summary and lines:
            page_summary = lines[0][:200]
        
        return page_summary, photo_descriptions
    
    def _combine_page_content(
        self,
        page_summary: str,
        page_text: str,
        photo_descriptions: List[str],
        photo_urls: List[str]
    ) -> str:
        """合并页面内容为最终的文本（用于 embedding）"""
        parts = []
        
        # 1. 页面摘要
        if page_summary:
            parts.append(f"【页面概要】{page_summary}")
        
        # 2. 页面文字
        if page_text.strip():
            parts.append(f"\n【页面文字】\n{page_text}")
        
        # 3. 图片描述 + URL
        if photo_descriptions:
            parts.append("\n【页面图片】")
            for idx, (desc, url) in enumerate(zip(photo_descriptions, photo_urls), 1):
                parts.append(f"图片{idx}: {desc}")
                if url:
                    parts.append(f"  链接: {url}")
        
        return "\n".join(parts)
    
    async def _upload_image_to_minio(
        self,
        img_data: Dict[str, Any],
        user_id: str,
        pdf_name: str,
        page_number: int,
        image_index: int
    ) -> Optional[str]:
        """上传图片到 MinIO"""
        try:
            # 解码图片数据
            image_data_str = img_data.get('image_data', '')
            if not image_data_str:
                return None
            
            # 移除 Data URL 前缀
            if image_data_str.startswith('data:'):
                if ';base64,' in image_data_str:
                    image_data_base64 = image_data_str.split(';base64,', 1)[1]
                else:
                    return None
            else:
                image_data_base64 = image_data_str
            
            # 解码 base64
            image_bytes = base64.b64decode(image_data_base64)
            
            # 上传到 MinIO
            image_format = img_data.get('format', 'png')
            image_name = f"{Path(pdf_name).stem}_page{page_number}_img{image_index}.{image_format}"
            
            minio_result = await self.minio_integration.upload_image(
                image_data=image_bytes,
                user_id=user_id,
                image_name=image_name
            )
            
            if minio_result.get('success'):
                return minio_result.get('presigned_url')
            else:
                return None
                
        except Exception as e:
            logger.warning(f"图片上传失败: {e}")
            return None
    
    async def _extract_pdf_images(self, pdf_path: str) -> Dict[str, Any]:
        """提取 PDF 中的所有图片（使用 PDFProcessor）"""
        try:
            from tools.services.data_analytics_service.processors.file_processors.pdf_processor import PDFProcessor
            
            pdf_processor = PDFProcessor(self.config)
            result = await pdf_processor.process_pdf_unified(pdf_path, {
                'extract_text': False,
                'extract_images': True,
                'extract_tables': False
            })
            
            if not result.get('success'):
                return {'success': False, 'images': []}
            
            # 提取所有图片数据
            image_analysis = result.get('image_analysis', {})
            extracted_images = image_analysis.get('extracted_images', [])
            
            images_data = []
            for img in extracted_images:
                image_data_str = img.get('image_data', '')
                if image_data_str:
                    # 解码 base64 为字节
                    try:
                        # 移除 Data URL 前缀 (data:image/xxx;base64,)
                        if image_data_str.startswith('data:'):
                            # 找到 base64 数据部分
                            if ';base64,' in image_data_str:
                                image_data_base64 = image_data_str.split(';base64,', 1)[1]
                            else:
                                logger.warning(f"图片数据格式不正确: {image_data_str[:50]}")
                                continue
                        else:
                            image_data_base64 = image_data_str
                        
                        # 解码 base64
                        image_bytes = base64.b64decode(image_data_base64)
                        images_data.append({
                            'page_number': img.get('page_number', 0),
                            'image_index': img.get('image_index', 0),
                            'image_bytes': image_bytes,
                            'format': img.get('format', 'png'),
                            'size': f"{img.get('width', 0)}x{img.get('height', 0)}"
                        })
                    except Exception as e:
                        logger.warning(f"图片解码失败 (page={img.get('page_number')}, idx={img.get('image_index')}): {e}")
                        continue
            
            return {
                'success': True,
                'images': images_data
            }
            
        except Exception as e:
            logger.error(f"PDF 图片提取失败: {e}")
            return {'success': False, 'images': []}
    
    async def _process_single_image(
        self,
        img_data: Dict[str, Any],
        idx: int,
        total: int,
        user_id: str,
        pdf_name: str,
        semaphore: asyncio.Semaphore
    ) -> Optional[Dict[str, Any]]:
        """处理单张图片（并发安全）"""
        async with semaphore:
            try:
                page_num = img_data.get('page_number', 0)
                image_bytes = img_data.get('image_bytes')
                image_format = img_data.get('format', 'png')
                
                logger.info(f"处理图片 {idx+1}/{total}: 页 {page_num}")
                
                # 1. 使用 VLM 生成图片描述
                description = await self._generate_image_description(image_bytes)
                
                # 2. 上传到 MinIO
                image_name = f"{Path(pdf_name).stem}_page{page_num}_img{idx}.{image_format}"
                minio_result = await self.minio_integration.upload_image(
                    image_data=image_bytes,
                    user_id=user_id,
                    image_name=image_name
                )
                
                if not minio_result.get('success'):
                    logger.warning(f"图片上传 MinIO 失败: {image_name}")
                    return None
                
                # 3. 生成描述的 embedding
                description_embedding = await self.embedding_integration.embed_text(description)
                
                # 4. 创建图片记录
                image_record = {
                    'type': 'image',
                    'page_number': page_num,
                    'image_index': idx,
                    'description': description,
                    'embedding': description_embedding,
                    'minio_url': minio_result.get('presigned_url'),
                    'minio_path': minio_result.get('object_path'),
                    'metadata': {
                        'pdf_name': pdf_name,
                        'image_name': image_name,
                        'size': img_data.get('size', 'unknown'),
                        'format': image_format,
                        'content_type': 'image'
                    }
                }
                
                logger.info(f"✅ 图片 {idx+1} 处理完成")
                return image_record
                
            except Exception as e:
                logger.error(f"图片 {idx+1} 处理失败: {e}")
                return None
    
    async def _process_images(
        self,
        images_data: List[Dict[str, Any]],
        user_id: str,
        pdf_name: str
    ) -> List[Dict[str, Any]]:
        """
        并发处理图片：VLM 描述生成 + MinIO 存储
        
        使用 asyncio.gather + semaphore 实现并发控制
        
        Returns:
            图片记录列表，包含描述、URL、embedding
        """
        # 创建 semaphore 限制并发数（避免 API 限流）
        max_concurrent = self.config.get('max_concurrent_images', 10)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(f"开始并发处理 {len(images_data)} 张图片（最大并发数: {max_concurrent}）")
        
        # 创建所有任务
        tasks = [
            self._process_single_image(
                img_data=img_data,
                idx=idx,
                total=len(images_data),
                user_id=user_id,
                pdf_name=pdf_name,
                semaphore=semaphore
            )
            for idx, img_data in enumerate(images_data)
        ]
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉失败的结果
        image_records = [
            result for result in results 
            if result is not None and not isinstance(result, Exception)
        ]
        
        logger.info(f"✅ 图片处理完成: {len(image_records)}/{len(images_data)} 成功")
        return image_records
    
    async def _generate_image_description(self, image_bytes: bytes) -> str:
        """使用 VLM 生成图片描述"""
        try:
            # 检查图片大小（OpenAI 限制 20MB，我们设置为 5MB 安全值）
            max_size_mb = 5
            size_mb = len(image_bytes) / (1024 * 1024)
            
            if size_mb > max_size_mb:
                logger.warning(f"图片太大 ({size_mb:.2f}MB > {max_size_mb}MB)，跳过分析")
                return f"图片内容（文件过大: {size_mb:.2f}MB）"
            
            # 使用现有的 ImageAnalyzer
            prompt = """请详细描述这张图片的内容，包括：
1. 主要内容和元素
2. 图表类型（如果是图表）
3. 关键信息和数据
4. 操作说明（如果是界面截图）
5. 任何可见的文字内容

请用中文描述，保持简洁清晰。"""
            
            # 将字节数据编码为 base64（ImageAnalyzer 支持）
            import base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            result = await vlm_analyze(
                image=image_base64,
                prompt=prompt,
                model="gpt-4o-mini",  # 使用性价比高的模型
                provider="yyds"  # 使用 yyds provider 避免 OpenAI Rate Limit
            )
            
            if result.success:
                return result.response.strip()
            else:
                error_msg = str(result.error) if hasattr(result, 'error') else "未知错误"
                logger.warning(f"VLM 分析失败: {error_msg}")
                return f"图片内容（描述生成失败: {error_msg[:50]}）"
                
        except Exception as e:
            logger.error(f"图片描述生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"图片内容（处理异常: {str(e)[:50]}）"
    
    async def _process_text_chunks(
        self,
        text_chunks: List[Dict[str, Any]],
        user_id: str,
        pdf_name: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        处理文本块：生成 embedding
        
        Args:
            text_chunks: 文本块列表，每个元素包含 {'text': str, 'page_number': int}
            
        Returns:
            文本记录列表，包含文本、embedding、metadata
        """
        text_records = []
        
        for idx, chunk_data in enumerate(text_chunks):
            try:
                # 提取文本和页码
                chunk_text = chunk_data.get('text', '')
                page_number = chunk_data.get('page_number', 0)
                
                if not chunk_text.strip():
                    continue
                
                # 生成 embedding
                embedding = await self.embedding_integration.embed_text(chunk_text)
                
                # 创建文本记录
                text_record = {
                    'type': 'text',
                    'chunk_index': idx,
                    'page_number': page_number,  # ✅ 添加页码
                    'text': chunk_text,
                    'embedding': embedding,
                    'metadata': {
                        'pdf_name': pdf_name,
                        'chunk_index': idx,
                        'page_number': page_number,  # ✅ metadata 中也保存
                        'total_chunks': len(text_chunks),
                        'content_type': 'text',
                        **metadata
                    }
                }
                
                text_records.append(text_record)
                
            except Exception as e:
                logger.error(f"文本块 {idx} 处理失败: {e}")
                continue
        
        return text_records
    
    async def _store_pages_to_vector_db(
        self,
        user_id: str,
        page_records: List[Dict[str, Any]],
        source_document: str
    ) -> Dict[str, Any]:
        """
        存储页面记录到 Supabase pgvector
        
        每个页面作为一条记录，包含：
        - text: VLM summary + page text + photo descriptions
        - embedding: 文本的 embedding
        - metadata: page_number, photo_urls, etc.
        """
        try:
            vector_db = self.vector_db_integration.vector_db
            
            # 准备批量插入数据
            insert_data = []
            for page_record in page_records:
                insert_data.append({
                    'user_id': user_id,
                    'text': page_record.get('text'),
                    'embedding_vector': page_record.get('embedding'),
                    'metadata': {
                        **page_record.get('metadata', {}),
                        'source_document': source_document,
                        'record_type': 'page',  # 页面级记录
                        'photo_urls': page_record.get('photo_urls', []),
                        'page_number': page_record.get('page_number'),
                    },
                    'source_document': source_document,
                    'created_at': datetime.now().isoformat()
                })
            
            # 批量插入
            logger.info(f"批量插入 {len(insert_data)} 个页面到向量数据库...")
            
            # 使用 vector_db 的插入方法
            success_count = 0
            for idx, data in enumerate(insert_data):
                try:
                    # 生成 UUID 格式的唯一 ID
                    record_id = str(uuid.uuid4())
                    
                    await vector_db.store_vector(
                        id=record_id,
                        user_id=data['user_id'],
                        text=data['text'],
                        embedding=data['embedding_vector'],
                        metadata=data['metadata']
                    )
                    success_count += 1
                except Exception as e:
                    logger.warning(f"单条记录插入失败: {e}")
                    continue
            
            logger.info(f"✅ 成功插入 {success_count}/{len(insert_data)} 条记录")
            
            return {
                'success': True,
                'total_records': len(insert_data),
                'success_count': success_count,
                'failed_count': len(insert_data) - success_count
            }
            
        except Exception as e:
            logger.error(f"向量数据库存储失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _store_to_vector_db(
        self,
        user_id: str,
        text_records: List[Dict[str, Any]],
        image_records: List[Dict[str, Any]],
        source_document: str
    ) -> Dict[str, Any]:
        """
        存储所有记录到 Supabase pgvector
        
        文本和图片描述都存储为独立的 embedding，metadata 中标记类型
        """
        try:
            vector_db = self.vector_db_integration.vector_db
            
            # 合并所有记录
            all_records = text_records + image_records
            
            # 准备批量插入数据
            insert_data = []
            for record in all_records:
                insert_data.append({
                    'user_id': user_id,
                    'text': record.get('text') or record.get('description'),
                    'embedding_vector': record.get('embedding'),
                    'metadata': {
                        **record.get('metadata', {}),
                        'source_document': source_document,
                        'record_type': record.get('type'),  # 'text' or 'image'
                        'minio_url': record.get('minio_url'),  # 仅图片有
                        'minio_path': record.get('minio_path'),  # 仅图片有
                        'page_number': record.get('page_number'),
                        'chunk_index': record.get('chunk_index'),
                        'image_index': record.get('image_index')
                    },
                    'source_document': source_document,
                    'created_at': datetime.now().isoformat()
                })
            
            # 批量插入
            logger.info(f"批量插入 {len(insert_data)} 条记录到向量数据库...")
            
            # 使用 vector_db 的插入方法
            success_count = 0
            for idx, data in enumerate(insert_data):
                try:
                    # 生成 UUID 格式的唯一 ID
                    record_id = str(uuid.uuid4())
                    
                    await vector_db.store_vector(
                        id=record_id,
                        user_id=data['user_id'],
                        text=data['text'],
                        embedding=data['embedding_vector'],
                        metadata=data['metadata']
                    )
                    success_count += 1
                except Exception as e:
                    logger.warning(f"单条记录插入失败: {e}")
                    continue
            
            logger.info(f"✅ 成功插入 {success_count}/{len(insert_data)} 条记录")
            
            return {
                'success': True,
                'total_records': len(insert_data),
                'success_count': success_count,
                'failed_count': len(insert_data) - success_count
            }
            
        except Exception as e:
            logger.error(f"向量数据库存储失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检索相关内容（文本 + 图片）
        
        Args:
            user_id: 用户 ID
            query: 查询文本
            top_k: 返回结果数量
            filters: 额外过滤条件（如 source_document）
            
        Returns:
            检索结果，包含文本块和相关图片
        """
        try:
            top_k = top_k or self.top_k
            
            logger.info(f"🔍 检索查询: {query} (user: {user_id}, top_k: {top_k})")
            
            # 1. 生成查询 embedding
            query_embedding = await self.embedding_integration.embed_text(query)
            
            # 2. 从向量数据库检索
            from tools.services.intelligence_service.vector_db.base_vector_db import VectorSearchConfig
            
            vector_db = self.vector_db_integration.vector_db
            search_config = VectorSearchConfig(
                top_k=top_k * 2,  # 多检索一些，后续过滤
                filter_metadata=filters
            )
            search_results = await vector_db.search_vectors(
                query_embedding=query_embedding,
                user_id=user_id,
                config=search_config
            )
            
            # 3. 处理检索结果（页面级）
            page_results = []
            
            for result in search_results:
                # SearchResult 是对象，使用属性访问
                metadata = result.metadata or {}
                record_type = metadata.get('record_type', 'page')
                
                if record_type == 'page':
                    # 页面级记录
                    page_results.append({
                        'text': result.text,
                        'page_number': metadata.get('page_number'),
                        'page_summary': metadata.get('page_summary'),
                        'similarity_score': result.score,
                        'photo_urls': metadata.get('photo_urls', []),
                        'num_photos': metadata.get('num_photos', 0),
                        'metadata': metadata
                    })
                else:
                    # 兼容旧格式（text/image）
                    page_results.append({
                        'text': result.text,
                        'page_number': metadata.get('page_number'),
                        'similarity_score': result.score,
                        'photo_urls': [metadata.get('minio_url')] if metadata.get('minio_url') else [],
                        'metadata': metadata
                    })
            
            # 4. 限制返回数量
            page_results = page_results[:top_k]
            
            # 统计图片数量
            total_photos = sum(len(p.get('photo_urls', [])) for p in page_results)
            
            logger.info(f"✅ 检索完成: {len(page_results)} 个页面, {total_photos} 张图片")
            
            return {
                'success': True,
                'query': query,
                'page_results': page_results,  # 页面级结果
                'total_pages': len(page_results),
                'total_photos': total_photos,
                # 兼容旧接口
                'text_results': page_results,
                'image_results': []
            }
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'page_results': [],
                'text_results': [],
                'image_results': []
            }
    
    async def generate(
        self,
        user_id: str,
        query: str,
        retrieval_result: Dict[str, Any],
        generation_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成答案（基于检索结果）
        
        Args:
            user_id: 用户 ID
            query: 查询问题
            retrieval_result: 检索结果（来自 retrieve()）
            generation_config: 生成配置（模型、温度等）
            
        Returns:
            生成的答案，包含图片引用
        """
        try:
            generation_config = generation_config or {}
            
            logger.info(f"🤖 生成答案: {query}")
            
            # 1. 提取检索结果（页面级）
            page_results = retrieval_result.get('page_results', [])
            
            # 兼容旧格式
            if not page_results:
                page_results = retrieval_result.get('text_results', [])
            
            # 2. 构建上下文（页面级，包含图片）
            context_parts = []
            
            context_parts.append("## 相关页面内容：\n")
            for idx, result in enumerate(page_results, 1):
                page_num = result.get('page_number', '未知')
                page_summary = result.get('page_summary', '')
                text = result.get('text', '')
                photo_urls = result.get('photo_urls', [])
                
                context_parts.append(f"\n[页面 {idx}] (页码: {page_num})")
                
                # 页面摘要
                if page_summary:
                    context_parts.append(f"摘要: {page_summary}")
                
                # 页面内容（截取部分）
                if text:
                    content_preview = text[:500] if len(text) > 500 else text
                    context_parts.append(f"\n内容:\n{content_preview}...")
                
                # 页面图片
                if photo_urls:
                    context_parts.append(f"\n包含 {len(photo_urls)} 张图片:")
                    for photo_idx, url in enumerate(photo_urls, 1):
                        context_parts.append(f"  图片{photo_idx}: {url}")
            
            context = "\n".join(context_parts)
            
            # 3. 构建 prompt
            system_prompt = """你是一个专业的 CRM 系统助手。基于提供的PDF页面内容（包含文字和图片），回答用户的问题。

注意：
1. 优先使用文档中的准确信息
2. 每个页面可能包含多张图片，注意引用图片URL
3. 提供清晰的操作步骤和说明
4. 如果信息不足，诚实说明
5. 在答案中提供图片链接，方便用户查看"""
            
            user_prompt = f"""基于以下内容，回答问题：

{context}

**用户问题**: {query}

请提供详细、准确的答案。如果有相关图片，请在答案中引用并说明如何查看。"""
            
            # 4. 调用 LLM 生成答案
            from core.isa_client_factory import get_isa_client
            
            isa_client = get_isa_client()
            llm_result = await isa_client.invoke(
                input_data=user_prompt,
                task="chat",
                service_type="text",
                model=generation_config.get('model', 'gpt-4o-mini'),
                system_prompt=system_prompt,
                temperature=generation_config.get('temperature', 0.3),
                provider=generation_config.get('provider', 'yyds')  # 使用 yyds provider
            )
            
            if not llm_result.get('success'):
                return {
                    'success': False,
                    'error': f"LLM 生成失败: {llm_result.get('error')}"
                }
            
            # 提取答案文本（兼容不同的返回格式）
            answer = ""
            if 'result' in llm_result:
                result = llm_result['result']
                if isinstance(result, dict):
                    answer = result.get('text', '') or result.get('response', '')
                elif isinstance(result, str):
                    answer = result
            
            if not answer:
                answer = llm_result.get('response', '')
            
            logger.info(f"✅ 答案生成完成")
            
            # 统计来源
            total_photos = sum(len(p.get('photo_urls', [])) for p in page_results)
            
            return {
                'success': True,
                'query': query,
                'answer': answer,
                'sources': {
                    'page_count': len(page_results),
                    'photo_count': total_photos,
                    'page_sources': page_results,
                    # 兼容旧格式
                    'text_count': len(page_results),
                    'image_count': 0,
                    'text_sources': page_results,
                    'image_sources': []
                },
                'context_used': context
            }
            
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def query_with_generation(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        完整的 RAG 流程：检索 + 生成
        
        这是一个便捷方法，组合了 retrieve() 和 generate()
        """
        try:
            # 1. 检索
            retrieval_result = await self.retrieve(
                user_id=user_id,
                query=query,
                filters=filters
            )
            
            if not retrieval_result.get('success'):
                return {
                    'success': False,
                    'error': f"检索失败: {retrieval_result.get('error')}"
                }
            
            # 2. 生成
            generation_result = await self.generate(
                user_id=user_id,
                query=query,
                retrieval_result=retrieval_result,
                generation_config=generation_config
            )
            
            return generation_result
            
        except Exception as e:
            logger.error(f"RAG 查询失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# 全局单例
_custom_rag_service = None

def get_custom_rag_service(config: Optional[Dict[str, Any]] = None) -> CustomRAGService:
    """获取 CustomRAGService 单例"""
    global _custom_rag_service
    if _custom_rag_service is None:
        _custom_rag_service = CustomRAGService(config)
    return _custom_rag_service

