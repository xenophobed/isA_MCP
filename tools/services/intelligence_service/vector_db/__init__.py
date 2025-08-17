"""
Vector Database Abstraction Layer

Provides unified interface for different vector database backends:
- Supabase pgvector (primary)
- Qdrant (high-performance option)
- ChromaDB (in-memory/lightweight option)
- Future: Weaviate, etc.
"""

from .base_vector_db import BaseVectorDB, SearchResult, VectorSearchConfig
from .vector_db_factory import get_vector_db, VectorDBType
from .supabase_vector_db import SupabaseVectorDB

# Optional imports for ChromaDB
try:
    from .chromadb_vector_db import ChromaVectorDB
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    ChromaVectorDB = None

__all__ = [
    'BaseVectorDB',
    'SearchResult', 
    'VectorSearchConfig',
    'get_vector_db',
    'VectorDBType',
    'SupabaseVectorDB'
]

if CHROMADB_AVAILABLE:
    __all__.append('ChromaVectorDB')