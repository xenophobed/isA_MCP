#!/usr/bin/env python3
"""
Multi-Mode RAG Service - 支持多种前沿RAG模式的统一服务

支持的RAG模式:
- Simple RAG: 传统向量检索
- Graph RAG: 基于知识图谱的检索
- RAPTOR RAG: 层次化文档组织
- Self-RAG: 自我反思RAG
- CRAG: 检索质量评估RAG
- Plan*RAG: 结构化推理RAG
- HM-RAG: 多智能体协作RAG
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tools.services.intelligence_service.language.embedding_generator import embed, search, chunk, rerank, hybrid_search_local, enhanced_search, store_knowledge_local
from core.database.supabase_client import get_supabase_client
from resources.graph_knowledge_resources import graph_knowledge_resources

logger = logging.getLogger(__name__)

class RAGMode(Enum):
    """RAG模式枚举"""
    SIMPLE = "simple"           # 传统向量检索RAG
    GRAPH = "graph"             # 基于知识图谱的RAG
    RAPTOR = "raptor"           # 层次化文档组织RAG
    SELF_RAG = "self_rag"       # 自我反思RAG
    CRAG = "crag"               # 检索质量评估RAG
    PLAN_RAG = "plan_rag"       # 结构化推理RAG
    HM_RAG = "hm_rag"           # 多智能体协作RAG
    HYBRID = "hybrid"           # 混合模式

@dataclass
class RAGConfig:
    """RAG配置"""
    mode: RAGMode = RAGMode.SIMPLE
    chunk_size: int = 400
    overlap: int = 50
    top_k: int = 5
    embedding_model: str = 'text-embedding-3-small'
    enable_rerank: bool = False
    similarity_threshold: float = 0.7
    max_context_length: int = 4000
    enable_self_reflection: bool = False
    enable_quality_assessment: bool = False
    enable_planning: bool = False
    enable_multi_agent: bool = False

@dataclass
class RAGResult:
    """RAG结果"""
    success: bool
    content: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    mode_used: RAGMode
    processing_time: float
    error: Optional[str] = None

class BaseRAGPattern(ABC):
    """RAG模式基类"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.supabase = get_supabase_client()
        self.table_name = "user_knowledge"
    
    @abstractmethod
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理文档"""
        pass
    
    @abstractmethod
    async def query(self, 
                   query: str, 
                   user_id: str,
                   context: Optional[str] = None) -> RAGResult:
        """查询处理"""
        pass

class SimpleRAGPattern(BaseRAGPattern):
    """传统向量检索RAG模式"""
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理文档 - 简单分块和向量化"""
        try:
            # 分块处理
            chunks = await chunk(content, 
                               chunk_size=self.config.chunk_size,
                               overlap=self.config.overlap,
                               metadata=metadata)
            
            stored_chunks = []
            for i, chunk_data in enumerate(chunks):
                # 生成嵌入
                embedding = await embed(chunk_data['text'], model=self.config.embedding_model)
                
                if embedding:
                    # 存储到数据库
                    knowledge_id = str(uuid.uuid4())
                    knowledge_data = {
                        'id': knowledge_id,
                        'user_id': user_id,
                        'text': chunk_data['text'],
                        'embedding_vector': embedding,
                        'metadata': {**(metadata or {}), 'chunk_index': i},
                        'created_at': datetime.now().isoformat()
                    }
                    
                    result = self.supabase.table(self.table_name).insert(knowledge_data).execute()
                    if result.data:
                        stored_chunks.append({
                            'chunk_id': knowledge_id,
                            'chunk_index': i,
                            'text_length': len(chunk_data['text'])
                        })
            
            return {
                'success': True,
                'mode': 'simple',
                'chunks_processed': len(stored_chunks),
                'chunks': stored_chunks
            }
            
        except Exception as e:
            logger.error(f"Simple RAG document processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def query(self, 
                   query: str, 
                   user_id: str,
                   context: Optional[str] = None) -> RAGResult:
        """查询处理 - 向量检索"""
        start_time = datetime.now()
        
        try:
            # 检索相关文档
            context_result = await self._retrieve_context(query, user_id)
            
            if not context_result['success'] or not context_result['context_items']:
                return RAGResult(
                    success=False,
                    content="",
                    sources=[],
                    metadata={},
                    mode_used=RAGMode.SIMPLE,
                    processing_time=0,
                    error="No relevant context found"
                )
            
            # 构建上下文
            context_text = self._build_context(context_result['context_items'])
            
            # 生成响应
            response = await self._generate_response(query, context_text, context)
            
            return RAGResult(
                success=True,
                content=response,
                sources=context_result['context_items'],
                metadata={
                    'retrieval_method': 'vector_similarity',
                    'context_length': len(context_text),
                    'sources_count': len(context_result['context_items'])
                },
                mode_used=RAGMode.SIMPLE,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            logger.error(f"Simple RAG query failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={},
                mode_used=RAGMode.SIMPLE,
                processing_time=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )
    
    async def _retrieve_context(self, query: str, user_id: str) -> Dict[str, Any]:
        """检索上下文"""
        # 获取用户知识库
        result = self.supabase.table(self.table_name)\
                             .select('id, text, metadata, created_at')\
                             .eq('user_id', user_id)\
                             .execute()
        
        if not result.data:
            return {'success': True, 'context_items': []}
        
        # 提取文本进行搜索
        texts = [item['text'] for item in result.data]
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
        
        return {'success': True, 'context_items': context_items}
    
    def _build_context(self, context_items: List[Dict[str, Any]]) -> str:
        """构建上下文"""
        context_texts = []
        for i, item in enumerate(context_items[:self.config.top_k]):
            context_texts.append(f"Context {i+1}: {item['text']}")
        return "\n\n".join(context_texts)
    
    async def _generate_response(self, query: str, context: str, additional_context: Optional[str] = None) -> str:
        """生成响应"""
        prompt = f"""Based on the following context, please answer the user's question accurately and comprehensively.

Context:
{context}

{f"Additional Context: {additional_context}" if additional_context else ""}

User Question: {query}

Please provide a helpful response based on the context provided."""
        
        # 这里应该调用LLM生成响应
        # 暂时返回结构化响应
        return f"Based on your knowledge base, here's what I found relevant to '{query}':\n\n{context[:500]}..."

class RAPTORRAGPattern(BaseRAGPattern):
    """RAPTOR RAG模式 - 层次化文档组织"""
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理文档 - 构建层次化树结构"""
        try:
            # 1. 初始分块
            chunks = await chunk(content, 
                               chunk_size=self.config.chunk_size,
                               overlap=self.config.overlap,
                               metadata=metadata)
            
            # 2. 构建层次化树
            tree_structure = await self._build_hierarchical_tree(chunks, user_id)
            
            # 3. 存储层次化数据到数据库
            stored_nodes = await self._store_hierarchical_data(tree_structure, user_id)
            
            return {
                'success': True,
                'mode': 'raptor',
                'tree_levels': len(tree_structure['levels']),
                'total_nodes': tree_structure['total_nodes'],
                'tree_id': tree_structure['tree_id'],
                'stored_nodes': stored_nodes
            }
            
        except Exception as e:
            logger.error(f"RAPTOR RAG document processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def query(self, 
                   query: str, 
                   user_id: str,
                   context: Optional[str] = None) -> RAGResult:
        """查询处理 - 层次化检索"""
        start_time = datetime.now()
        
        try:
            # 1. 在摘要层搜索
            summary_results = await self._search_summary_level(query, user_id)
            
            # 2. 在详细层搜索
            detail_results = await self._search_detail_level(query, user_id)
            
            # 3. 合并和排序结果
            combined_results = await self._merge_hierarchical_results(summary_results, detail_results)
            
            # 4. 生成响应
            response = await self._generate_hierarchical_response(query, combined_results, context)
            
            return RAGResult(
                success=True,
                content=response,
                sources=combined_results,
                metadata={
                    'retrieval_method': 'hierarchical_raptor',
                    'summary_matches': len(summary_results),
                    'detail_matches': len(detail_results),
                    'tree_levels_searched': 2
                },
                mode_used=RAGMode.RAPTOR,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            logger.error(f"RAPTOR RAG query failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={},
                mode_used=RAGMode.RAPTOR,
                processing_time=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )
    
    async def _build_hierarchical_tree(self, chunks: List[Dict], user_id: str) -> Dict[str, Any]:
        """构建层次化树结构"""
        tree_id = str(uuid.uuid4())
        levels = []
        
        # 叶节点层 (原始chunks)
        leaf_nodes = []
        for i, chunk in enumerate(chunks):
            embedding = await embed(chunk['text'], model=self.config.embedding_model)
            if embedding:
                node_id = str(uuid.uuid4())
                leaf_nodes.append({
                    'node_id': node_id,
                    'text': chunk['text'],
                    'embedding': embedding,
                    'level': 0,
                    'parent': None
                })
        
        levels.append(leaf_nodes)
        
        # 摘要层 (聚类和摘要)
        if len(leaf_nodes) > 1:
            summary_nodes = await self._create_summary_level(leaf_nodes, user_id, tree_id)
            levels.append(summary_nodes)
        
        # 根节点层 (最高层摘要)
        if len(levels) > 1 and len(levels[-1]) > 1:
            root_nodes = await self._create_root_level(levels[-1], user_id, tree_id)
            levels.append(root_nodes)
        
        return {
            'tree_id': tree_id,
            'levels': levels,
            'total_nodes': sum(len(level) for level in levels)
        }
    
    async def _store_hierarchical_data(self, tree_structure: Dict[str, Any], user_id: str) -> int:
        """存储层次化数据到数据库"""
        stored_count = 0
        
        try:
            for level_idx, level_nodes in enumerate(tree_structure['levels']):
                for node in level_nodes:
                    knowledge_data = {
                        'id': node['node_id'],
                        'user_id': user_id,
                        'text': node['text'],
                        'embedding_vector': node['embedding'],
                        'metadata': {
                            'level': level_idx,
                            'tree_id': tree_structure['tree_id'],
                            'parent': node.get('parent'),
                            'children': node.get('children', []),
                            'raptor_mode': True
                        },
                        'created_at': datetime.now().isoformat()
                    }
                    
                    result = self.supabase.table(self.table_name).insert(knowledge_data).execute()
                    if result.data:
                        stored_count += 1
            
            return stored_count
            
        except Exception as e:
            logger.error(f"Failed to store hierarchical data: {e}")
            return stored_count
    
    async def _create_summary_level(self, leaf_nodes: List[Dict], user_id: str, tree_id: str) -> List[Dict]:
        """创建摘要层"""
        # 聚类相似节点
        clusters = await self._cluster_nodes(leaf_nodes)
        
        summary_nodes = []
        for cluster in clusters:
            # 生成摘要
            cluster_texts = [node['text'] for node in cluster]
            summary_text = await self._generate_summary(cluster_texts)
            summary_embedding = await embed(summary_text, model=self.config.embedding_model)
            
            if summary_embedding:
                node_id = str(uuid.uuid4())
                summary_nodes.append({
                    'node_id': node_id,
                    'text': summary_text,
                    'embedding': summary_embedding,
                    'level': 1,
                    'children': [node['node_id'] for node in cluster],
                    'tree_id': tree_id
                })
        
        return summary_nodes
    
    async def _create_root_level(self, summary_nodes: List[Dict], user_id: str, tree_id: str) -> List[Dict]:
        """创建根节点层"""
        # 生成最高层摘要
        summary_texts = [node['text'] for node in summary_nodes]
        root_text = await self._generate_summary(summary_texts)
        root_embedding = await embed(root_text, model=self.config.embedding_model)
        
        if root_embedding:
            node_id = str(uuid.uuid4())
            return [{
                'node_id': node_id,
                'text': root_text,
                'embedding': root_embedding,
                'level': 2,
                'children': [node['node_id'] for node in summary_nodes],
                'tree_id': tree_id
            }]
        
        return []
    
    async def _cluster_nodes(self, nodes: List[Dict]) -> List[List[Dict]]:
        """聚类节点"""
        # 简化的聚类实现 - 基于嵌入相似度
        clusters = []
        used_nodes = set()
        
        for i, node in enumerate(nodes):
            if i in used_nodes:
                continue
            
            cluster = [node]
            used_nodes.add(i)
            
            for j, other_node in enumerate(nodes[i+1:], i+1):
                if j in used_nodes:
                    continue
                
                # 计算相似度
                similarity = self._cosine_similarity(node['embedding'], other_node['embedding'])
                if similarity > 0.8:  # 相似度阈值
                    cluster.append(other_node)
                    used_nodes.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    async def _generate_summary(self, texts: List[str]) -> str:
        """生成摘要"""
        # 简化的摘要生成 - 实际应该调用LLM
        combined_text = " ".join(texts)
        return combined_text[:500] + "..." if len(combined_text) > 500 else combined_text
    
    async def _search_summary_level(self, query: str, user_id: str) -> List[Dict[str, Any]]:
        """在摘要层搜索"""
        try:
            # 获取用户的摘要层数据
            result = self.supabase.table(self.table_name)\
                                 .select('id, text, metadata, created_at')\
                                 .eq('user_id', user_id)\
                                 .eq('metadata->>level', '1')\
                                 .execute()
            
            if not result.data:
                return []
            
            # 提取文本进行搜索
            texts = [item['text'] for item in result.data]
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
                            'created_at': item['created_at'],
                            'level': 'summary'
                        })
                        break
            
            return context_items
            
        except Exception as e:
            logger.error(f"Summary level search failed: {e}")
            return []
    
    async def _search_detail_level(self, query: str, user_id: str) -> List[Dict[str, Any]]:
        """在详细层搜索"""
        try:
            # 获取用户的详细层数据
            result = self.supabase.table(self.table_name)\
                                 .select('id, text, metadata, created_at')\
                                 .eq('user_id', user_id)\
                                 .eq('metadata->>level', '0')\
                                 .execute()
            
            if not result.data:
                return []
            
            # 提取文本进行搜索
            texts = [item['text'] for item in result.data]
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
                            'created_at': item['created_at'],
                            'level': 'detail'
                        })
                        break
            
            return context_items
            
        except Exception as e:
            logger.error(f"Detail level search failed: {e}")
            return []
    
    async def _merge_hierarchical_results(self, summary_results: List, detail_results: List) -> List[Dict[str, Any]]:
        """合并层次化结果"""
        # 合并和排序结果
        all_results = summary_results + detail_results
        return sorted(all_results, key=lambda x: x.get('score', 0), reverse=True)
    
    async def _generate_hierarchical_response(self, query: str, results: List[Dict], context: Optional[str]) -> str:
        """生成层次化响应"""
        # 生成基于层次化结果的响应
        return f"RAPTOR RAG response for '{query}' with {len(results)} hierarchical results"

class SelfRAGPattern(BaseRAGPattern):
    """Self-RAG模式 - 自我反思RAG"""
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理文档 - 添加自我反思标记"""
        try:
            # 分块处理
            chunks = await chunk(content, 
                               chunk_size=self.config.chunk_size,
                               overlap=self.config.overlap,
                               metadata=metadata)
            
            stored_chunks = []
            for i, chunk_data in enumerate(chunks):
                # 生成嵌入
                embedding = await embed(chunk_data['text'], model=self.config.embedding_model)
                
                if embedding:
                    # 添加自我反思标记
                    knowledge_id = str(uuid.uuid4())
                    knowledge_data = {
                        'id': knowledge_id,
                        'user_id': user_id,
                        'text': chunk_data['text'],
                        'embedding_vector': embedding,
                        'metadata': {
                            **(metadata or {}), 
                            'chunk_index': i,
                            'self_rag_mode': True,
                            'reflection_enabled': True
                        },
                        'created_at': datetime.now().isoformat()
                    }
                    
                    result = self.supabase.table(self.table_name).insert(knowledge_data).execute()
                    if result.data:
                        stored_chunks.append({
                            'chunk_id': knowledge_id,
                            'chunk_index': i,
                            'text_length': len(chunk_data['text'])
                        })
            
            return {
                'success': True,
                'mode': 'self_rag',
                'chunks_processed': len(stored_chunks),
                'chunks': stored_chunks
            }
            
        except Exception as e:
            logger.error(f"Self-RAG document processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def query(self, 
                   query: str, 
                   user_id: str,
                   context: Optional[str] = None) -> RAGResult:
        """查询处理 - 带自我反思的生成"""
        start_time = datetime.now()
        
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
                    'initial_response_length': len(initial_response)
                },
                mode_used=RAGMode.SELF_RAG,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            logger.error(f"Self-RAG query failed: {e}")
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={},
                mode_used=RAGMode.SELF_RAG,
                processing_time=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )
    
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
            logger.error(f"Self-RAG document retrieval failed: {e}")
            return []
    
    async def _generate_initial_response(self, query: str, docs: List[Dict]) -> str:
        """生成初始响应"""
        if not docs:
            return f"I don't have enough information to answer '{query}' accurately."
        
        # 构建上下文
        context_texts = []
        for i, doc in enumerate(docs[:3]):  # 使用前3个最相关的文档
            context_texts.append(f"Source {i+1}: {doc['text']}")
        
        context = "\n\n".join(context_texts)
        
        # 生成初始响应
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
            logger.error(f"Self-reflection failed: {e}")
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

class MultiModeRAGService:
    """多模式RAG服务"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.patterns = {
            RAGMode.SIMPLE: SimpleRAGPattern(self.config),
            RAGMode.RAPTOR: RAPTORRAGPattern(self.config),
            RAGMode.SELF_RAG: SelfRAGPattern(self.config),
            # 可以添加更多模式
        }
        
        logger.info(f"Multi-Mode RAG Service initialized with {len(self.patterns)} patterns")
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             mode: Optional[RAGMode] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理文档"""
        mode = mode or self.config.mode
        
        if mode not in self.patterns:
            return {
                'success': False,
                'error': f'RAG mode {mode} not supported',
                'available_modes': list(self.patterns.keys())
            }
        
        pattern = self.patterns[mode]
        return await pattern.process_document(content, user_id, metadata)
    
    async def query(self, 
                   query: str, 
                   user_id: str,
                   mode: Optional[RAGMode] = None,
                   context: Optional[str] = None) -> RAGResult:
        """查询处理"""
        mode = mode or self.config.mode
        
        if mode not in self.patterns:
            return RAGResult(
                success=False,
                content="",
                sources=[],
                metadata={'error': f'RAG mode {mode} not supported'},
                mode_used=mode,
                processing_time=0,
                error=f'RAG mode {mode} not supported'
            )
        
        pattern = self.patterns[mode]
        return await pattern.query(query, user_id, context)
    
    async def get_available_modes(self) -> List[RAGMode]:
        """获取可用模式"""
        return list(self.patterns.keys())
    
    async def get_mode_info(self, mode: RAGMode) -> Dict[str, Any]:
        """获取模式信息"""
        mode_info = {
            RAGMode.SIMPLE: {
                'name': 'Simple RAG',
                'description': '传统向量检索RAG',
                'features': ['向量相似度检索', '文档分块', '简单上下文构建']
            },
            RAGMode.RAPTOR: {
                'name': 'RAPTOR RAG',
                'description': '层次化文档组织RAG',
                'features': ['层次化树结构', '多级摘要', '复杂推理支持']
            },
            RAGMode.SELF_RAG: {
                'name': 'Self-RAG',
                'description': '自我反思RAG',
                'features': ['自我评估', '质量修正', '减少幻觉']
            }
        }
        
        return mode_info.get(mode, {'name': 'Unknown', 'description': 'Unknown mode'})

# 全局实例
multi_mode_rag_service = MultiModeRAGService()
