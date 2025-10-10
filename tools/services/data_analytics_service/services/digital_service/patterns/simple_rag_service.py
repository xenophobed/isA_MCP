#!/usr/bin/env python3
"""
Simple RAG Service - 传统向量检索RAG实现

基于multi_mode_rag_service.py中的SimpleRAGPattern，实现独立的Simple RAG服务。
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base.base_rag_service import BaseRAGService, RAGResult, RAGMode, RAGConfig

logger = logging.getLogger(__name__)

class SimpleRAGService(BaseRAGService):
    """Simple RAG服务实现 - 传统向量检索"""
    
    def __init__(self, config: RAGConfig):
        super().__init__(config)
        self.logger.info("Simple RAG Service initialized")
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """处理文档 - 简单分块和向量化"""
        start_time = time.time()
        
        try:
            # 使用基类的add_document方法进行分块和存储
            document_result = await self.add_document(
                user_id=user_id,
                document=content,
                chunk_size=self.config.chunk_size,
                overlap=self.config.overlap,
                metadata=metadata
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
            
            return RAGResult(
                success=True,
                content=f"Processed {document_result['stored_chunks']} chunks",
                sources=document_result.get('chunks', []),
                metadata={
                    'chunks_processed': document_result['stored_chunks'],
                    'total_chunks': document_result['total_chunks'],
                    'document_length': document_result['document_length']
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Simple RAG document processing failed: {e}")
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
        """查询处理 - 向量检索"""
        start_time = time.time()
        
        try:
            # 使用基类的search_knowledge方法进行搜索
            search_result = await self.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=self.config.top_k,
                enable_rerank=self.config.enable_rerank,
                search_mode="hybrid",
                use_enhanced_search=True
            )
            
            if not search_result['success'] or not search_result['search_results']:
                return RAGResult(
                    success=False,
                    content="No relevant context found",
                    sources=[],
                    metadata={'search_method': search_result.get('search_method', 'unknown')},
                    mode_used=self.mode,
                    processing_time=time.time() - start_time,
                    error=search_result.get('error', 'No relevant context found')
                )
            
            # 构建上下文（默认启用citation格式） - 使用基类方法
            context_text = self._build_context_with_citations(search_result['search_results'])
            
            # 生成响应（使用真正的LLM） - 使用基类方法
            response = await self._generate_response_with_llm(query, context_text, context)
            
            return RAGResult(
                success=True,
                content=response,
                sources=search_result['search_results'],
                metadata={
                    'retrieval_method': 'vector_similarity',
                    'context_length': len(context_text),
                    'sources_count': len(search_result['search_results']),
                    'search_method': search_result.get('search_method', 'unknown'),
                    'reranking_used': search_result.get('reranking_used', False)
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Simple RAG query failed: {e}")
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
        """获取Simple RAG能力"""
        return {
            'name': 'Simple RAG',
            'description': '传统向量检索RAG',
            'features': [
                '向量相似度检索',
                '文档分块',
                '简单上下文构建',
                '增强混合搜索',
                '可选重排序'
            ],
            'best_for': [
                '简单问答',
                '事实查询', 
                '快速检索',
                '基础文档搜索'
            ],
            'complexity': 'low',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'processing_speed': 'fast',
            'resource_usage': 'low'
        }
    
    # 注意：Citation和响应生成方法已移动到BaseRAGService基类中
    # 所有RAG模式现在都可以继承和使用这些统一的citation功能
    # 
    # 可用的基类方法:
    # - _build_context_with_citations(): 构建带引用ID的上下文
    # - _build_context_traditional(): 构建传统上下文
    # - _generate_response_with_llm(): 使用LLM生成带inline citations的响应
    # - _generate_response_fallback(): 传统响应生成（降级方法）
