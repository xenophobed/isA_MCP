#!/usr/bin/env python3
"""
Self-RAG Service - 自我反思RAG实现

基于multi_mode_rag_service.py中的SelfRAGPattern，实现独立的Self-RAG服务。
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base.base_rag_service import BaseRAGService, RAGResult, RAGMode, RAGConfig

logger = logging.getLogger(__name__)

class SelfRAGService(BaseRAGService):
    """Self-RAG服务实现 - 自我反思RAG"""
    
    def __init__(self, config: RAGConfig):
        super().__init__(config)
        self.logger.info("Self-RAG Service initialized")
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """处理文档 - 添加自我反思标记"""
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
                    'self_rag_mode': True,
                    'reflection_enabled': True
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
            
            return RAGResult(
                success=True,
                content=f"Processed {document_result['stored_chunks']} chunks with self-reflection",
                sources=document_result.get('chunks', []),
                metadata={
                    'chunks_processed': document_result['stored_chunks'],
                    'total_chunks': document_result['total_chunks'],
                    'document_length': document_result['document_length'],
                    'self_rag_mode': True,
                    'reflection_enabled': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Self-RAG document processing failed: {e}")
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
        """查询处理 - 带自我反思的生成"""
        start_time = time.time()
        
        try:
            # 1. 检索相关文档
            retrieved_docs = await self._retrieve_documents(query, user_id)
            
            # 2. 生成初始响应
            initial_response = await self._generate_initial_response(query, retrieved_docs)
            
            # 3. 自我反思和修正
            final_response = await self._self_reflect_and_refine(query, initial_response, retrieved_docs)
            
            return RAGResult(
                success=True,
                content=final_response,
                sources=retrieved_docs,
                metadata={
                    'retrieval_method': 'self_rag',
                    'reflection_steps': 1,
                    'initial_response_length': len(initial_response),
                    'self_reflection_used': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Self-RAG query failed: {e}")
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
        """获取Self-RAG能力"""
        return {
            'name': 'Self-RAG',
            'description': '自我反思RAG',
            'features': [
                '自我评估',
                '质量修正',
                '减少幻觉',
                '响应反思',
                '质量保证'
            ],
            'best_for': [
                '高质量回答',
                '准确性要求高',
                '减少错误',
                '复杂推理'
            ],
            'complexity': 'medium',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'processing_speed': 'medium',
            'resource_usage': 'medium',
            'self_reflection': True
        }
    
    async def _retrieve_documents(self, query: str, user_id: str) -> List[Dict[str, Any]]:
        """检索文档"""
        try:
            # 获取用户知识库
            result = self.supabase.table(self.table_name)\
                                 .select('id, text, metadata, created_at')\
                                 .eq('user_id', user_id)\
                                 .eq('metadata->>self_rag_mode', 'true')\
                                 .execute()
            
            if not result.data:
                return []
            
            # 提取文本进行搜索
            texts = [item['text'] for item in result.data]
            from tools.services.intelligence_service.language.embedding_generator import search
            search_results = await search(query, texts, top_k=self.config.top_k)
            
            # 匹配结果
            context_items = []
            for text, similarity_score in search_results:
                for item in result.data:
                    if item['text'] == text:
                        context_items.append({
                            'knowledge_id': item['id'],
                            'text': text,
                            'similarity_score': similarity_score,
                            'metadata': item['metadata'],
                            'created_at': item['created_at']
                        })
                        break
            
            return context_items
            
        except Exception as e:
            self.logger.error(f"Self-RAG document retrieval failed: {e}")
            return []
    
    async def _generate_initial_response(self, query: str, docs: List[Dict]) -> str:
        """生成初始响应 - 现在支持inline citations!"""
        if not docs:
            return f"I don't have enough information to answer '{query}' accurately."
        
        # 使用基类的统一citation方法
        try:
            citation_context = self._build_context_with_citations(docs[:3])
            
            response = await self._generate_response_with_llm(
                query=query,
                context=citation_context,
                additional_context="Self-RAG Initial Response: This is the first generation before self-reflection.",
                use_citations=True
            )
            
            self.logger.info("✅ Self-RAG initial response generated with inline citations")
            return response
            
        except Exception as e:
            self.logger.warning(f"Self-RAG citation generation failed: {e}, falling back to traditional")
            # 降级到传统格式
            context_texts = []
            for i, doc in enumerate(docs[:3]):
                context_texts.append(f"Source {i+1}: {doc['text']}")
            context = "\n\n".join(context_texts)
            return f"Based on the available information, here's my initial response to '{query}':\n\n{context[:300]}..."
    
    async def _self_reflect_and_refine(self, query: str, response: str, docs: List[Dict]) -> str:
        """自我反思和修正"""
        try:
            # 1. 反思响应质量
            quality_assessment = await self._assess_response_quality(query, response, docs)
            
            # 2. 如果需要修正，进行修正
            if quality_assessment['needs_improvement']:
                refined_response = await self._refine_response(query, response, docs, quality_assessment)
                return refined_response
            else:
                return response
                
        except Exception as e:
            self.logger.error(f"Self-reflection failed: {e}")
            return response
    
    async def _assess_response_quality(self, query: str, response: str, docs: List[Dict]) -> Dict[str, Any]:
        """评估响应质量"""
        # 简化的质量评估
        quality_indicators = {
            'has_relevant_info': any(doc['similarity_score'] > 0.7 for doc in docs),
            'response_length': len(response) > 50,
            'mentions_sources': any('Source' in response for _ in docs),
            'answers_question': any(word in response.lower() for word in query.lower().split()[:3])
        }
        
        quality_score = sum(quality_indicators.values()) / len(quality_indicators)
        needs_improvement = quality_score < 0.6
        
        return {
            'quality_score': quality_score,
            'needs_improvement': needs_improvement,
            'indicators': quality_indicators
        }
    
    async def _refine_response(self, query: str, response: str, docs: List[Dict], quality_assessment: Dict) -> str:
        """修正响应"""
        # 基于质量评估结果进行修正
        improvements = []
        
        if not quality_assessment['indicators']['has_relevant_info']:
            improvements.append("I need to find more relevant information.")
        
        if not quality_assessment['indicators']['response_length']:
            improvements.append("I should provide more detailed information.")
        
        if not quality_assessment['indicators']['mentions_sources']:
            improvements.append("I should reference the sources more clearly.")
        
        if not quality_assessment['indicators']['answers_question']:
            improvements.append("I should better address the specific question.")
        
        # 生成修正后的响应
        refined_parts = [response]
        if improvements:
            refined_parts.append(f"\n\nReflection: {', '.join(improvements)}")
            refined_parts.append(f"\nRefined response: Let me provide a more comprehensive answer to '{query}' based on the available sources.")
        
        return "\n".join(refined_parts)
