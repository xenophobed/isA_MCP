#!/usr/bin/env python3
"""
CRAG RAG Service - 检索质量评估RAG实现

基于advanced_rag_patterns.py中的CRAGRAGPattern，实现独立的CRAG RAG服务。
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
class QualityAssessment:
    """检索质量评估结果"""
    relevance_score: float
    completeness_score: float
    accuracy_score: float
    overall_score: float
    needs_refinement: bool
    refinement_suggestions: List[str]

class CRAGRAGService(BaseRAGService):
    """CRAG RAG服务实现 - 检索质量评估RAG"""
    
    def __init__(self, config: RAGConfig):
        super().__init__(config)
        self.quality_threshold = 0.3  # 进一步降低阈值，避免过度过滤
        self.logger.info("CRAG RAG Service initialized")
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """处理文档 - 添加质量评估标记"""
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
                    'quality_assessed': True,
                    'crag_mode': True
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
            
            # 对每个分块进行质量预评估
            quality_scores = []
            for chunk in document_result.get('chunks', []):
                quality_score = await self._assess_chunk_quality(chunk.get('text', ''))
                quality_scores.append(quality_score)
            
            average_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            return RAGResult(
                success=True,
                content=f"Processed {document_result['stored_chunks']} chunks with quality assessment",
                sources=document_result.get('chunks', []),
                metadata={
                    'chunks_processed': document_result['stored_chunks'],
                    'total_chunks': document_result['total_chunks'],
                    'document_length': document_result['document_length'],
                    'average_quality': average_quality,
                    'crag_mode': True,
                    'quality_assessed': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"CRAG RAG document processing failed: {e}")
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
        """查询处理 - 带质量评估的检索"""
        start_time = time.time()
        
        try:
            # 1. 初始检索
            initial_results = await self._retrieve_initial_results(query, user_id)
            
            # 2. 质量评估
            quality_assessments = await self._assess_retrieval_quality(query, initial_results)
            
            # 3. 质量过滤和重排序
            filtered_results = await self._filter_and_rerank(initial_results, quality_assessments)
            
            # 4. 低质量结果处理
            if any(assessment.needs_refinement for assessment in quality_assessments):
                refined_results = await self._refine_low_quality_results(query, filtered_results, quality_assessments)
                filtered_results = refined_results
            
            # 5. 生成响应
            response = await self._generate_quality_aware_response(query, filtered_results, context)
            
            return RAGResult(
                success=True,
                content=response,
                sources=filtered_results,
                metadata={
                    'retrieval_method': 'crag_quality_assessed',
                    'quality_metrics': {
                        'average_quality': sum(a.overall_score for a in quality_assessments) / len(quality_assessments) if quality_assessments else 0,
                        'high_quality_count': sum(1 for a in quality_assessments if a.overall_score > self.quality_threshold),
                        'refined_count': sum(1 for a in quality_assessments if a.needs_refinement)
                    },
                    'quality_assessments_used': True
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"CRAG RAG query failed: {e}")
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
        """获取CRAG RAG能力"""
        return {
            'name': 'CRAG RAG',
            'description': '检索质量评估RAG',
            'features': [
                '质量评估',
                '动态调整',
                '噪声过滤',
                '质量感知检索',
                '结果细化'
            ],
            'best_for': [
                '大规模检索',
                '质量要求高',
                '噪声数据',
                '精确检索'
            ],
            'complexity': 'medium',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'processing_speed': 'medium',
            'resource_usage': 'medium',
            'quality_assessment': True
        }
    
    async def _assess_chunk_quality(self, text: str) -> float:
        """评估文档块质量"""
        # 简化的质量评估 - 实际应该使用更复杂的评估模型
        factors = {
            'length': min(len(text) / 200, 1.0),  # 长度因子
            'completeness': 1.0 if text.endswith('.') else 0.8,  # 完整性因子
            'clarity': 1.0 if len(text.split()) > 10 else 0.6  # 清晰度因子
        }
        
        return sum(factors.values()) / len(factors)
    
    async def _retrieve_initial_results(self, query: str, user_id: str) -> List[Dict[str, Any]]:
        """初始检索结果"""
        result = self.supabase.table(self.table_name)\
                             .select('id, text, metadata, created_at')\
                             .eq('user_id', user_id)\
                             .execute()
        
        if not result.data:
            return []
        
        texts = [item['text'] for item in result.data]
        from tools.services.intelligence_service.language.embedding_generator import search
        search_results = await search(query, texts, top_k=self.config.top_k * 2)  # 检索更多结果用于质量评估
        
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
    
    async def _assess_retrieval_quality(self, query: str, results: List[Dict[str, Any]]) -> List[QualityAssessment]:
        """评估检索质量"""
        assessments = []
        
        for result in results:
            # 相关性评估
            relevance_score = result.get('similarity_score', 0)
            
            # 完整性评估
            completeness_score = await self._assess_completeness(query, result['text'])
            
            # 准确性评估
            accuracy_score = await self._assess_accuracy(result['text'])
            
            # 综合评分
            overall_score = (relevance_score + completeness_score + accuracy_score) / 3
            
            # 是否需要细化
            needs_refinement = overall_score < self.quality_threshold
            
            # 细化建议
            refinement_suggestions = []
            if relevance_score < 0.7:
                refinement_suggestions.append("提高相关性")
            if completeness_score < 0.7:
                refinement_suggestions.append("增加完整性")
            if accuracy_score < 0.7:
                refinement_suggestions.append("提高准确性")
            
            assessments.append(QualityAssessment(
                relevance_score=relevance_score,
                completeness_score=completeness_score,
                accuracy_score=accuracy_score,
                overall_score=overall_score,
                needs_refinement=needs_refinement,
                refinement_suggestions=refinement_suggestions
            ))
        
        return assessments
    
    async def _assess_completeness(self, query: str, text: str) -> float:
        """评估完整性"""
        # 简化的完整性评估
        query_terms = set(query.lower().split())
        text_terms = set(text.lower().split())
        overlap = len(query_terms.intersection(text_terms))
        return min(overlap / len(query_terms), 1.0) if query_terms else 0
    
    async def _assess_accuracy(self, text: str) -> float:
        """评估准确性"""
        # 简化的准确性评估 - 基于文本特征
        accuracy_indicators = {
            'has_facts': any(word in text.lower() for word in ['according to', 'research shows', 'studies indicate']),
            'has_sources': any(word in text.lower() for word in ['source:', 'reference:', 'cited']),
            'is_detailed': len(text.split()) > 50,
            'has_structure': any(char in text for char in ['1.', '2.', '•', '-'])
        }
        
        return sum(accuracy_indicators.values()) / len(accuracy_indicators)
    
    async def _filter_and_rerank(self, results: List[Dict], assessments: List[QualityAssessment]) -> List[Dict[str, Any]]:
        """过滤和重排序"""
        # 合并结果和质量评估
        combined = list(zip(results, assessments))
        
        # 过滤低质量结果
        filtered = [(result, assessment) for result, assessment in combined 
                   if assessment.overall_score >= self.quality_threshold]
        
        # 如果过滤后没有结果，返回质量最高的几个
        if not filtered:
            self.logger.warning(f"CRAG: All results below quality threshold {self.quality_threshold}, using top results anyway")
            combined.sort(key=lambda x: x[1].overall_score, reverse=True)
            filtered = combined
        
        # 按质量评分排序
        filtered.sort(key=lambda x: x[1].overall_score, reverse=True)
        
        # 返回前top_k个结果
        return [result for result, _ in filtered[:self.config.top_k]]
    
    async def _refine_low_quality_results(self, query: str, results: List[Dict], assessments: List[QualityAssessment]) -> List[Dict[str, Any]]:
        """细化低质量结果"""
        # 实现细化逻辑 - 例如重新检索、扩展查询等
        refined_results = []
        
        for result, assessment in zip(results, assessments):
            if assessment.needs_refinement:
                # 尝试细化
                refined_result = await self._refine_single_result(query, result, assessment)
                if refined_result:
                    refined_results.append(refined_result)
                else:
                    refined_results.append(result)  # 保持原结果
            else:
                refined_results.append(result)
        
        return refined_results
    
    async def _refine_single_result(self, query: str, result: Dict, assessment: QualityAssessment) -> Optional[Dict]:
        """细化单个结果"""
        # 实现单个结果的细化逻辑
        # 例如：扩展查询、重新检索、上下文增强等
        return result
    
    async def _generate_quality_aware_response(self, query: str, results: List[Dict], context: Optional[str]) -> str:
        """生成质量感知的响应 - 现在支持inline citations!"""
        
        # 使用基类的统一citation方法构建上下文
        citation_context = self._build_context_with_citations(results)
        
        # 可选：添加质量分数信息到传统格式
        quality_context = self._build_context_traditional(results)
        
        # 使用基类的LLM生成方法，自动支持inline citations
        try:
            response = await self._generate_response_with_llm(
                query=query, 
                context=citation_context,  # 使用带引用ID的上下文
                additional_context=f"Quality Assessment: This context has been pre-filtered for quality. {context}" if context else "Quality Assessment: This context has been pre-filtered for quality.",
                use_citations=True  # 启用citations
            )
            
            self.logger.info("✅ CRAG successfully generated response with inline citations")
            return response
            
        except Exception as e:
            self.logger.warning(f"CRAG citation generation failed: {e}, falling back to quality-aware traditional response")
            # 降级到带质量分数的传统响应
            return f"CRAG response for '{query}' based on {len(results)} quality-assessed sources:\n\n{quality_context[:500]}..."
