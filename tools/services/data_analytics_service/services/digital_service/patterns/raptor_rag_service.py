#!/usr/bin/env python3
"""
RAPTOR RAG Service - 层次化文档组织RAG实现

基于multi_mode_rag_service.py中的RAPTORRAGPattern，实现独立的RAPTOR RAG服务。
"""

import asyncio
import logging
import time
import uuid
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base.base_rag_service import BaseRAGService, RAGResult, RAGMode, RAGConfig

logger = logging.getLogger(__name__)

class RAPTORRAGService(BaseRAGService):
    """RAPTOR RAG服务实现 - 层次化文档组织"""
    
    def __init__(self, config: RAGConfig):
        super().__init__(config)
        self.logger.info("RAPTOR RAG Service initialized")
    
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """处理文档 - 构建层次化树结构"""
        start_time = time.time()
        
        try:
            # 1. 初始分块
            from tools.services.intelligence_service.language.embedding_generator import chunk
            chunks = await chunk(content, 
                               chunk_size=self.config.chunk_size,
                               overlap=self.config.overlap,
                               metadata=metadata)
            
            # 2. 构建层次化树
            tree_structure = await self._build_hierarchical_tree(chunks, user_id)
            
            # 3. 存储层次化数据到数据库
            stored_nodes = await self._store_hierarchical_data(tree_structure, user_id)
            
            return RAGResult(
                success=True,
                content=f"Processed {stored_nodes} hierarchical nodes",
                sources=[],
                metadata={
                    'tree_levels': len(tree_structure['levels']),
                    'total_nodes': tree_structure['total_nodes'],
                    'tree_id': tree_structure['tree_id'],
                    'stored_nodes': stored_nodes
                },
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"RAPTOR RAG document processing failed: {e}")
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
        """查询处理 - 层次化检索"""
        start_time = time.time()
        
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
                mode_used=self.mode,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"RAPTOR RAG query failed: {e}")
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
        """获取RAPTOR RAG能力"""
        return {
            'name': 'RAPTOR RAG',
            'description': '层次化文档组织RAG',
            'features': [
                '层次化树结构',
                '多级摘要',
                '复杂推理支持',
                '层次化检索',
                '文档聚类'
            ],
            'best_for': [
                '长文档分析',
                '复杂推理',
                '多层次信息检索',
                '文档结构理解'
            ],
            'complexity': 'high',
            'supports_rerank': True,
            'supports_hybrid': True,
            'supports_enhanced_search': True,
            'processing_speed': 'medium',
            'resource_usage': 'high'
        }
    
    async def _build_hierarchical_tree(self, chunks: List[Dict], user_id: str) -> Dict[str, Any]:
        """构建层次化树结构"""
        tree_id = str(uuid.uuid4())
        levels = []
        
        # 叶节点层 (原始chunks)
        leaf_nodes = []
        for i, chunk in enumerate(chunks):
            from tools.services.intelligence_service.language.embedding_generator import embed
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
            self.logger.error(f"Failed to store hierarchical data: {e}")
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
            from tools.services.intelligence_service.language.embedding_generator import embed
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
        from tools.services.intelligence_service.language.embedding_generator import embed
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
                            'created_at': item['created_at'],
                            'level': 'summary'
                        })
                        break
            
            return context_items
            
        except Exception as e:
            self.logger.error(f"Summary level search failed: {e}")
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
                            'created_at': item['created_at'],
                            'level': 'detail'
                        })
                        break
            
            return context_items
            
        except Exception as e:
            self.logger.error(f"Detail level search failed: {e}")
            return []
    
    async def _merge_hierarchical_results(self, summary_results: List, detail_results: List) -> List[Dict[str, Any]]:
        """合并层次化结果"""
        # 合并和排序结果
        all_results = summary_results + detail_results
        return sorted(all_results, key=lambda x: x.get('similarity_score', 0), reverse=True)
    
    async def _generate_hierarchical_response(self, query: str, results: List[Dict], context: Optional[str]) -> str:
        """生成层次化响应 - 现在支持inline citations!"""
        try:
            # 使用基类的统一citation方法
            citation_context = self._build_context_with_citations(results)
            
            response = await self._generate_response_with_llm(
                query=query,
                context=citation_context,
                additional_context=f"Hierarchical Tree Structure: Results from multiple abstraction levels. {context}" if context else "Hierarchical Tree Structure: Results from multiple abstraction levels.",
                use_citations=True
            )
            
            self.logger.info("✅ RAPTOR RAG generated response with inline citations")
            return response
            
        except Exception as e:
            self.logger.warning(f"RAPTOR citation generation failed: {e}, falling back to traditional")
            return f"RAPTOR RAG response for '{query}' with {len(results)} hierarchical results"
