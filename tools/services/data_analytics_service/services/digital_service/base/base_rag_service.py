#!/usr/bin/env python3
"""
Base RAG Service - RAG服务抽象基类

基于当前rag_service.py的核心功能，定义所有RAG服务的通用接口和基础实现。
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
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
    citations: List[Dict[str, Any]] = None
    error: Optional[str] = None

class BaseRAGService(ABC):
    """
    RAG服务抽象基类
    
    基于当前rag_service.py的核心功能，提供所有RAG服务的通用接口和基础实现。
    """
    
    def __init__(self, config: RAGConfig):
        """
        Initialize RAG service.
        
        Args:
            config: RAG configuration
        """
        self.config = config
        self.mode = config.mode
        self.supabase = get_supabase_client()
        self.table_name = "user_knowledge"
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置"""
        if self.config.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.config.overlap < 0:
            raise ValueError("overlap must be non-negative")
        if self.config.top_k <= 0:
            raise ValueError("top_k must be positive")
        if not 0 <= self.config.similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
    
    @abstractmethod
    async def process_document(self, 
                             content: str, 
                             user_id: str,
                             metadata: Optional[Dict[str, Any]] = None) -> RAGResult:
        """
        处理文档 - 子类必须实现
        
        Args:
            content: 文档内容
            user_id: 用户ID
            metadata: 元数据
            
        Returns:
            RAG结果
        """
        pass
    
    @abstractmethod
    async def query(self, 
                   query: str, 
                   user_id: str,
                   context: Optional[str] = None) -> RAGResult:
        """
        查询处理 - 子类必须实现
        
        Args:
            query: 查询字符串
            user_id: 用户ID
            context: 上下文信息
            
        Returns:
            RAG结果
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取服务能力 - 子类必须实现
        
        Returns:
            服务能力信息
        """
        pass
    
    def get_mode(self) -> RAGMode:
        """获取RAG模式"""
        return self.mode
    
    def get_config(self) -> RAGConfig:
        """获取配置"""
        return self.config
    
    # 以下是从当前rag_service.py提取的通用方法
    
    async def store_knowledge(self, 
                            user_id: str, 
                            text: str, 
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        存储知识 - 从rag_service.py提取
        
        Args:
            user_id: 用户ID
            text: 文本内容
            metadata: 元数据
            
        Returns:
            存储结果
        """
        try:
            # Use doc_id from metadata if provided by Storage Service, otherwise generate new UUID
            knowledge_id = (metadata or {}).get('doc_id', str(uuid.uuid4()))
            now = datetime.now().isoformat()
            
            # 生成嵌入
            self.logger.info(f"Generating embedding for user {user_id}, text length: {len(text)}")
            embedding = await embed(text, model=self.config.embedding_model)
            
            if not embedding:
                return {
                    'success': False,
                    'error': 'Failed to generate embedding',
                    'user_id': user_id
                }
            
            # 准备知识数据
            knowledge_data = {
                'id': knowledge_id,
                'user_id': user_id,
                'text': text,
                'embedding_vector': embedding,
                'metadata': metadata or {},
                'chunk_index': 0,
                'source_document': metadata.get('source') if metadata else None,
                'created_at': now,
                'updated_at': now
            }
            
            # 存储到数据库
            result = self.supabase.table(self.table_name).insert(knowledge_data).execute()
            
            if not result.data:
                return {
                    'success': False,
                    'error': 'Failed to store knowledge in database',
                    'user_id': user_id
                }
            
            # 也存储到增强向量数据库
            try:
                enhanced_result = await store_knowledge_local(
                    user_id=user_id,
                    text=text,
                    metadata={
                        'knowledge_id': knowledge_id,
                        'source': metadata.get('source') if metadata else None,
                        'stored_at': now,
                        **((metadata or {}))
                    }
                )
                enhanced_storage_success = enhanced_result.get('success', False)
                self.logger.info(f"Enhanced vector storage {'succeeded' if enhanced_storage_success else 'failed'} for knowledge {knowledge_id}")
            except Exception as e:
                self.logger.warning(f"Enhanced vector storage failed for knowledge {knowledge_id}: {e}")
                enhanced_storage_success = False
            
            # 注册MCP资源
            mcp_result = await graph_knowledge_resources.register_resource(
                resource_id=knowledge_id,
                user_id=int(user_id) if user_id.isdigit() else hash(user_id) % (2**31),
                resource_data={
                    'type': 'knowledge_base_item',
                    'text_preview': text[:100] + "..." if len(text) > 100 else text,
                    'metadata': metadata or {},
                    'source_file': metadata.get('source') if metadata else None,
                    'embedding_model': self.config.embedding_model,
                    'text_length': len(text)
                }
            )
            
            mcp_address = f"mcp://rag/{user_id}/{knowledge_id}"
            
            self.logger.info(f"Knowledge stored successfully for user {user_id}: {knowledge_id}")
            
            return {
                'success': True,
                'knowledge_id': knowledge_id,
                'mcp_address': mcp_address,
                'user_id': user_id,
                'text_length': len(text),
                'embedding_dimensions': len(embedding),
                'mcp_registration': mcp_result.get('success', False),
                'enhanced_storage': enhanced_storage_success
            }
            
        except Exception as e:
            self.logger.error(f"Error storing knowledge for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def retrieve_context(self, 
                             user_id: str, 
                             query: str, 
                             top_k: int = None,
                             search_mode: str = "hybrid",
                             use_enhanced_search: bool = True) -> Dict[str, Any]:
        """
        检索上下文 - 从rag_service.py提取
        
        Args:
            user_id: 用户ID
            query: 查询字符串
            top_k: 返回结果数量
            search_mode: 搜索模式
            use_enhanced_search: 是否使用增强搜索
            
        Returns:
            检索结果
        """
        try:
            top_k = top_k or self.config.top_k
            
            # 策略1: 尝试增强混合搜索
            if use_enhanced_search:
                try:
                    enhanced_results = await enhanced_search(
                        query_text=query,
                        user_id=user_id,
                        top_k=top_k,
                        search_mode=search_mode
                    )
                    
                    if enhanced_results:
                        # 转换增强搜索结果到上下文格式
                        context_items = []
                        for result in enhanced_results:
                            context_items.append({
                                'knowledge_id': result.get('id'),
                                'text': result.get('text'),
                                'similarity_score': result.get('score', 0),
                                'semantic_score': result.get('semantic_score'),
                                'lexical_score': result.get('lexical_score'),
                                'metadata': result.get('metadata', {}),
                                'created_at': result.get('metadata', {}).get('created_at'),
                                'search_method': result.get('method', 'enhanced')
                            })
                        
                        self.logger.info(f"Retrieved {len(context_items)} context items using enhanced search for user {user_id}")
                        
                        return {
                            'success': True,
                            'user_id': user_id,
                            'query': query,
                            'context_items': context_items,
                            'total_knowledge_items': len(context_items),
                            'search_method': 'enhanced_hybrid'
                        }
                        
                except Exception as e:
                    self.logger.warning(f"Enhanced search failed for user {user_id}: {e}, falling back to traditional search")
            
            # 策略2: 回退到传统数据库搜索
            result = self.supabase.table(self.table_name)\
                                 .select('id, text, metadata, created_at')\
                                 .eq('user_id', user_id)\
                                 .execute()
            
            if not result.data:
                return {
                    'success': True,
                    'user_id': user_id,
                    'query': query,
                    'context_items': [],
                    'total_knowledge_items': 0,
                    'search_method': 'traditional_fallback'
                }
            
            # 提取文本进行搜索
            knowledge_items = result.data
            texts = [item['text'] for item in knowledge_items]
            
            # 执行语义搜索
            search_results = await search(query, texts, top_k=top_k)
            
            # 匹配结果回到知识项
            context_items = []
            for text, similarity_score in search_results:
                # 找到匹配的知识项
                for item in knowledge_items:
                    if item['text'] == text:
                        context_items.append({
                            'knowledge_id': item['id'],
                            'text': text,
                            'similarity_score': similarity_score,
                            'semantic_score': similarity_score,
                            'lexical_score': None,
                            'metadata': item['metadata'],
                            'created_at': item['created_at'],
                            'search_method': 'traditional_isa'
                        })
                        break
            
            self.logger.info(f"Retrieved {len(context_items)} context items using traditional search for user {user_id}")
            
            return {
                'success': True,
                'user_id': user_id,
                'query': query,
                'context_items': context_items,
                'total_knowledge_items': len(knowledge_items),
                'search_method': 'traditional_isa'
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving context for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query
            }
    
    async def search_knowledge(self, 
                             user_id: str, 
                             query: str, 
                             top_k: int = None,
                             enable_rerank: bool = None,
                             search_mode: str = "hybrid",
                             use_enhanced_search: bool = True) -> Dict[str, Any]:
        """
        搜索知识 - 从rag_service.py提取
        
        Args:
            user_id: 用户ID
            query: 查询字符串
            top_k: 返回结果数量
            enable_rerank: 启用重排序
            search_mode: 搜索模式
            use_enhanced_search: 是否使用增强搜索
            
        Returns:
            搜索结果
        """
        try:
            # 获取搜索结果使用增强上下文检索
            context_result = await self.retrieve_context(
                user_id=user_id, 
                query=query, 
                top_k=top_k,
                search_mode=search_mode,
                use_enhanced_search=use_enhanced_search
            )
            
            if not context_result['success'] or not context_result['context_items']:
                # 返回预期格式的搜索结果
                return {
                    'success': context_result['success'],
                    'user_id': user_id,
                    'query': query,
                    'search_results': [],
                    'total_knowledge_items': context_result.get('total_knowledge_items', 0),
                    'search_method': context_result.get('search_method', 'unknown'),
                    'error': context_result.get('error')
                }
            
            context_items = context_result['context_items']
            search_method = context_result.get('search_method', 'unknown')
            
            # 检查是否启用重排序
            use_rerank = enable_rerank if enable_rerank is not None else self.config.enable_rerank
            
            if use_rerank:
                # 提取文本进行重排序
                documents = [item['text'] for item in context_items]
                
                try:
                    # 使用高级重排序与MMR进行多样性
                    from tools.services.intelligence_service.language.embedding_generator import advanced_rerank
                    
                    reranked_results = await advanced_rerank(
                        query=query,
                        documents=documents,
                        method="combined",  # 使用MMR和ISA重排序
                        top_k=top_k or self.config.top_k
                    )
                    
                    # 结合重排序与原始上下文项
                    final_results = []
                    for rerank_result in reranked_results:
                        document_text = rerank_result.get('document', rerank_result.get('text', ''))
                        relevance_score = rerank_result.get('relevance_score', rerank_result.get('score', 0))
                        
                        # 找到匹配的上下文项
                        for item in context_items:
                            if item['text'] == document_text:
                                final_results.append({
                                    'knowledge_id': item['knowledge_id'],
                                    'text': document_text,
                                    'relevance_score': relevance_score,
                                    'similarity_score': item.get('similarity_score', 0),
                                    'semantic_score': item.get('semantic_score'),
                                    'lexical_score': item.get('lexical_score'),
                                    'mmr_score': rerank_result.get('mmr_score'),
                                    'isa_score': rerank_result.get('isa_score'),
                                    'metadata': item['metadata'],
                                    'created_at': item['created_at'],
                                    'mcp_address': f"mcp://rag/{user_id}/{item['knowledge_id']}",
                                    'rerank_method': rerank_result.get('method', 'combined')
                                })
                                break
                    
                    self.logger.info(f"Enhanced search with advanced reranking completed for user {user_id}, {len(final_results)} results")
                    
                except Exception as rerank_error:
                    self.logger.warning(f"Advanced reranking failed for user {user_id}: {rerank_error}, falling back to original scores")
                    # 回退到原始搜索分数
                    final_results = []
                    for item in context_items:
                        final_results.append({
                            'knowledge_id': item['knowledge_id'],
                            'text': item['text'],
                            'relevance_score': item.get('similarity_score', item.get('semantic_score', 0)),
                            'similarity_score': item.get('similarity_score'),
                            'semantic_score': item.get('semantic_score'),
                            'lexical_score': item.get('lexical_score'),
                            'metadata': item['metadata'],
                            'created_at': item['created_at'],
                            'mcp_address': f"mcp://rag/{user_id}/{item['knowledge_id']}",
                            'search_method': item.get('search_method', search_method)
                        })
            else:
                # 无重排序，直接使用搜索结果
                final_results = []
                for item in context_items:
                    final_results.append({
                        'knowledge_id': item['knowledge_id'],
                        'text': item['text'],
                        'relevance_score': item.get('similarity_score', item.get('semantic_score', 0)),
                        'similarity_score': item.get('similarity_score'),
                        'semantic_score': item.get('semantic_score'),
                        'lexical_score': item.get('lexical_score'),
                        'metadata': item['metadata'],
                        'created_at': item['created_at'],
                        'mcp_address': f"mcp://rag/{user_id}/{item['knowledge_id']}",
                        'search_method': item.get('search_method', search_method)
                    })
                
                self.logger.info(f"Enhanced search without reranking completed for user {user_id}, {len(final_results)} results")
            
            return {
                'success': True,
                'user_id': user_id,
                'query': query,
                'search_results': final_results,
                'total_knowledge_items': context_result['total_knowledge_items'],
                'search_method': search_method,
                'search_mode': search_mode,
                'reranking_used': use_rerank,
                'enhanced_search_used': use_enhanced_search
            }
            
        except Exception as e:
            self.logger.error(f"Error searching knowledge for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query
            }
    
    async def add_document(self, 
                         user_id: str, 
                         document: str, 
                         chunk_size: int = None,
                         overlap: int = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        添加文档 - 从rag_service.py提取
        
        Args:
            user_id: 用户ID
            document: 文档文本
            chunk_size: 分块大小
            overlap: 重叠大小
            metadata: 元数据
            
        Returns:
            添加结果
        """
        try:
            chunk_size = chunk_size or self.config.chunk_size
            overlap = overlap or self.config.overlap
            
            # 分块文档
            self.logger.info(f"Chunking document for user {user_id}, length: {len(document)}")
            chunks = await chunk(document, chunk_size=chunk_size, overlap=overlap, metadata=metadata)
            
            if not chunks:
                return {
                    'success': False,
                    'error': 'Failed to chunk document',
                    'user_id': user_id
                }
            
            # 存储每个分块
            stored_chunks = []
            document_id = str(uuid.uuid4())
            
            for i, chunk_data in enumerate(chunks):
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    'document_id': document_id,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_size': chunk_size,
                    'overlap': overlap
                })
                
                result = await self.store_knowledge(
                    user_id=user_id,
                    text=chunk_data['text'],
                    metadata=chunk_metadata
                )
                
                if result['success']:
                    stored_chunks.append({
                        'chunk_index': i,
                        'knowledge_id': result['knowledge_id'],
                        'mcp_address': result['mcp_address'],
                        'text_length': len(chunk_data['text'])
                    })
                else:
                    self.logger.warning(f"Failed to store chunk {i} for user {user_id}: {result.get('error')}")
            
            self.logger.info(f"Document added for user {user_id}: {len(stored_chunks)}/{len(chunks)} chunks stored")
            
            return {
                'success': True,
                'user_id': user_id,
                'document_id': document_id,
                'total_chunks': len(chunks),
                'stored_chunks': len(stored_chunks),
                'chunks': stored_chunks,
                'document_length': len(document)
            }
            
        except Exception as e:
            self.logger.error(f"Error adding document for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    # ===============================
    # Inline Citation Methods - 统一的Citation功能
    # ===============================
    
    def _build_context_with_citations(self, context_items: List[Dict[str, Any]]) -> str:
        """
        构建带引用ID的上下文 - 所有RAG模式统一使用
        
        Args:
            context_items: 上下文项列表
            
        Returns:
            带引用ID的上下文字符串
        """
        context_texts = []
        for i, item in enumerate(context_items[:self.config.top_k]):
            # 为每个上下文分配引用ID [1], [2], [3] 等
            context_texts.append(f"[{i+1}] {item['text']}")
        return "\n\n".join(context_texts)
    
    def _build_context_traditional(self, context_items: List[Dict[str, Any]]) -> str:
        """
        构建传统上下文（保持兼容性） - 无引用ID
        
        Args:
            context_items: 上下文项列表
            
        Returns:
            传统格式上下文字符串
        """
        context_texts = []
        for i, item in enumerate(context_items[:self.config.top_k]):
            score = item.get('relevance_score', item.get('similarity_score', 0))
            context_texts.append(f"Context {i+1} (Score: {score:.3f}): {item['text']}")
        return "\n\n".join(context_texts)
    
    async def _generate_response_with_llm(self, 
                                        query: str, 
                                        context: str, 
                                        additional_context: Optional[str] = None,
                                        use_citations: bool = True) -> str:
        """
        使用真正的LLM生成响应 - 支持inline citations
        
        Args:
            query: 用户查询
            context: 上下文（带或不带引用ID）
            additional_context: 附加上下文
            use_citations: 是否使用引用格式
            
        Returns:
            LLM生成的响应
        """
        
        if use_citations:
            # 构建包含citation指导的prompt
            prompt = f"""You are an AI assistant that provides accurate answers with inline citations. When you reference information from the provided sources, immediately insert the citation number in square brackets after the relevant statement.

SOURCES:
{context}

CITATION RULES:
1. When you use information from a source, insert [1], [2], etc. immediately after the statement
2. Place citations naturally within sentences, not at the end of responses  
3. Multiple sources can support the same claim: [1][2]
4. Only cite sources that directly support your statements
5. Be precise about which source supports which claim

{f"Additional Context: {additional_context}" if additional_context else ""}

USER QUESTION: {query}

Please provide a comprehensive answer with proper inline citations following the rules above. Write naturally but ensure every factual claim is properly cited."""
        else:
            # 传统prompt without citations
            prompt = f"""Based on the following context, please answer the user's question accurately and comprehensively.

Context:
{context}

{f"Additional Context: {additional_context}" if additional_context else ""}

User Question: {query}

Please provide a helpful response based on the context provided."""

        try:
            # 使用真正的LLM生成响应
            from tools.services.intelligence_service.language.text_generator import generate
            
            response = await generate(
                prompt=prompt,
                temperature=0.7,  # 平衡创造性和准确性
                max_tokens=1000   # 限制响应长度
            )
            
            if response and response.strip():
                citation_info = " with inline citations" if use_citations else ""
                self.logger.info(f"✅ LLM successfully generated response{citation_info}")
                return response
            else:
                self.logger.warning("LLM returned empty response, falling back to traditional method")
                return await self._generate_response_fallback(query, context, additional_context)
            
        except Exception as e:
            self.logger.error(f"❌ LLM generation failed: {e}")
            # 降级到传统方法
            return await self._generate_response_fallback(query, context, additional_context)
    
    async def _generate_response_fallback(self, 
                                        query: str, 
                                        context: str, 
                                        additional_context: Optional[str] = None) -> str:
        """
        传统响应生成（降级方法）
        
        Args:
            query: 用户查询
            context: 上下文
            additional_context: 附加上下文
            
        Returns:
            简单的结构化响应
        """
        return f"Based on your knowledge base, here's what I found relevant to '{query}':\n\n{context[:500]}..."
    
    # ===============================
    # Graph RAG Integration - 图RAG集成
    # ===============================
    
    async def _query_graph_rag(self, 
                             query: str, 
                             user_id: str,
                             context: Optional[str] = None,
                             options: Optional[Dict[str, Any]] = None) -> Optional[RAGResult]:
        """
        图RAG查询 - 集成graph_analytics_service的功能
        
        Args:
            query: 查询字符串
            user_id: 用户ID
            context: 附加上下文
            options: 查询选项
            
        Returns:
            图RAG结果或None（如果不可用）
        """
        try:
            # 尝试导入和使用GraphAnalyticsService
            from tools.services.data_analytics_service.services.graph_analytics_service import GraphAnalyticsService
            
            # 创建临时的UserService（实际应用中应该注入）
            class TempUserService:
                async def get_user_by_id(self, user_id: int):
                    class User:
                        def __init__(self, user_id):
                            self.id = user_id
                            self.email = f"user_{user_id}@test.com"
                            self.is_active = True
                    return User(user_id)
            
            graph_service = GraphAnalyticsService(
                user_service=TempUserService(),
                config=options or {}
            )
            
            # 执行GraphRAG查询
            result = await graph_service.graphrag_query(
                query=query,
                user_id=int(user_id) if user_id.isdigit() else hash(user_id) % (2**31),
                context_text=context,
                options=options
            )
            
            if result and result.get('success'):
                return RAGResult(
                    success=True,
                    content=result.get('response', ''),
                    sources=result.get('sources', []),
                    metadata={
                        'graph_rag_used': True,
                        'entities_found': result.get('entities_found', 0),
                        'relationships_found': result.get('relationships_found', 0),
                        'search_method': 'graph_rag'
                    },
                    mode_used=RAGMode.GRAPH,
                    processing_time=result.get('processing_time', 0)
                )
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Graph RAG query failed: {e}")
            return None
    
    async def _process_document_with_graph(self, 
                                         content: str, 
                                         user_id: str,
                                         metadata: Optional[Dict[str, Any]] = None) -> Optional[RAGResult]:
        """
        使用图RAG处理文档
        
        Args:
            content: 文档内容
            user_id: 用户ID
            metadata: 元数据
            
        Returns:
            图RAG处理结果或None（如果不可用）
        """
        try:
            from tools.services.data_analytics_service.services.graph_analytics_service import GraphAnalyticsService
            
            class TempUserService:
                async def get_user_by_id(self, user_id: int):
                    class User:
                        def __init__(self, user_id):
                            self.id = user_id
                            self.email = f"user_{user_id}@test.com"
                            self.is_active = True
                    return User(user_id)
            
            graph_service = GraphAnalyticsService(
                user_service=TempUserService(),
                config={}
            )
            
            # 执行图处理
            result = await graph_service.process_text_to_knowledge_graph(
                text_content=content,
                user_id=int(user_id) if user_id.isdigit() else hash(user_id) % (2**31),
                source_metadata=metadata or {}
            )
            
            if result and result.get('success'):
                return RAGResult(
                    success=True,
                    content=f"Processed {result.get('entities_count', 0)} entities and {result.get('relationships_count', 0)} relationships",
                    sources=[],
                    metadata={
                        'graph_processing_used': True,
                        'entities_count': result.get('entities_count', 0),
                        'relationships_count': result.get('relationships_count', 0),
                        'mcp_address': result.get('mcp_address')
                    },
                    mode_used=RAGMode.GRAPH,
                    processing_time=result.get('processing_time', 0)
                )
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Graph document processing failed: {e}")
            return None
