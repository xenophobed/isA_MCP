"""
Vector Database Abstraction Layer

Provides unified interface for vector database backends:
- Qdrant (via isa_common.qdrant_client) - primary, high-performance
- Weaviate - alternative option
"""

from .base_vector_db import BaseVectorDB, SearchResult, VectorSearchConfig, SearchMode, RankingMethod
from .vector_db_factory import get_vector_db, VectorDBType, create_vector_db, get_default_config
from .qdrant_vector_db import QdrantVectorDB

__all__ = [
    'BaseVectorDB',
    'SearchResult',
    'VectorSearchConfig',
    'SearchMode',
    'RankingMethod',
    'get_vector_db',
    'VectorDBType',
    'create_vector_db',
    'get_default_config',
    'QdrantVectorDB'
]
