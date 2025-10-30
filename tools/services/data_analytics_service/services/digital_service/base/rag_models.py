#!/usr/bin/env python3
"""
RAG Data Models - Pydantic 数据契约

定义所有 RAG 实现必须遵守的统一数据模型。
"""

from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator


class RAGMode(str, Enum):
    """RAG 模式枚举"""
    SIMPLE = "simple"           # 传统向量检索
    GRAPH = "graph"             # 知识图谱
    RAPTOR = "raptor"           # 层次化文档
    SELF_RAG = "self_rag"       # 自我反思
    CRAG = "crag"               # 检索质量评估
    PLAN_RAG = "plan_rag"       # 结构化推理
    HM_RAG = "hm_rag"           # 多智能体协作
    CUSTOM = "custom"           # 自定义多模态
    HYBRID = "hybrid"           # 混合模式


class RAGConfig(BaseModel):
    """RAG 配置模型"""
    mode: RAGMode = RAGMode.SIMPLE
    chunk_size: int = Field(default=400, ge=100, le=2000)
    overlap: int = Field(default=50, ge=0)
    top_k: int = Field(default=5, ge=1, le=100)
    embedding_model: str = Field(default='text-embedding-3-small')
    enable_rerank: bool = False
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_context_length: int = Field(default=4000, ge=100)

    # 可选功能开关
    enable_self_reflection: bool = False
    enable_quality_assessment: bool = False
    enable_planning: bool = False
    enable_multi_agent: bool = False

    class Config:
        use_enum_values = True


class RAGStoreRequest(BaseModel):
    """存储请求数据模型"""
    content: Union[str, bytes, Any]  # 文本、文件路径、或二进制数据
    user_id: str
    content_type: str = Field(default="text", description="text, pdf, image, document")
    metadata: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('user_id cannot be empty')
        return v.strip()


class RAGRetrieveRequest(BaseModel):
    """检索请求数据模型"""
    query: str
    user_id: str
    top_k: Optional[int] = Field(default=5, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('query cannot be empty')
        return v.strip()


class RAGGenerateRequest(BaseModel):
    """生成请求数据模型"""
    query: str
    user_id: str
    context: Optional[Union[str, List[Dict]]] = None
    retrieval_sources: Optional[List[Dict[str, Any]]] = None  # 来自 retrieve 的结果
    options: Optional[Dict[str, Any]] = None

    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('query cannot be empty')
        return v.strip()


class RAGSource(BaseModel):
    """检索来源数据模型"""
    text: str
    score: float = Field(ge=0.0, le=1.0)
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 多模态字段（可选）
    photo_urls: Optional[List[str]] = None
    image_descriptions: Optional[List[str]] = None


class RAGResult(BaseModel):
    """统一返回结果数据模型"""
    success: bool
    content: str = Field(default="")
    sources: List[RAGSource] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    mode_used: RAGMode
    processing_time: float = Field(ge=0.0)
    error: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True

    @validator('sources', pre=True)
    def validate_sources(cls, v):
        """自动转换 dict 为 RAGSource"""
        if v is None:
            return []
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, dict):
                    # 转换为 RAGSource
                    result.append(RAGSource(
                        text=item.get('text', ''),
                        score=item.get('score', item.get('similarity_score', item.get('relevance_score', 0.0))),
                        page_number=item.get('page_number'),
                        chunk_index=item.get('chunk_index'),
                        metadata=item.get('metadata', {}),
                        photo_urls=item.get('photo_urls'),
                        image_descriptions=item.get('image_descriptions')
                    ))
                elif isinstance(item, RAGSource):
                    result.append(item)
            return result
        return []


class VectorRecord(BaseModel):
    """向量记录数据模型（存储层）"""
    id: str
    user_id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    @validator('embedding')
    def validate_embedding(cls, v):
        if not v or len(v) == 0:
            raise ValueError('embedding cannot be empty')
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError('embedding must contain only numbers')
        return v


class GraphRecord(BaseModel):
    """图记录数据模型（Graph RAG）"""
    node_id: str
    node_type: str  # entity, attribute, relation
    properties: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)


class MultimodalRecord(BaseModel):
    """多模态记录数据模型（Custom RAG）"""
    id: str
    user_id: str
    text: str
    embedding: List[float]
    image_urls: Optional[List[str]] = None
    image_descriptions: Optional[List[str]] = None
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


__all__ = [
    'RAGMode',
    'RAGConfig',
    'RAGStoreRequest',
    'RAGRetrieveRequest',
    'RAGGenerateRequest',
    'RAGSource',
    'RAGResult',
    'VectorRecord',
    'GraphRecord',
    'MultimodalRecord'
]
