"""
Vector Database Abstraction Layer

DEPRECATED: This module has been migrated to isA_Data.
Use `from services.vector_service import ...` in isA_Data instead.

Migration examples:
    # Old (isA_MCP)
    from tools.services.intelligence_service.vector_db import get_vector_db, BaseVectorDB

    # New (isA_Data)
    from services.vector_service import get_vector_db, BaseVectorDB

New features in isA_Data/services/vector_service:
- Pydantic models with validation
- Lazy initialization pattern
- Modular structure (base, backends, search, chunking, updates)
- Improved hybrid search with model_client integration
"""

import warnings

warnings.warn(
    "tools.services.intelligence_service.vector_db is deprecated and has been "
    "migrated to isA_Data. Use 'from services.vector_service import ...' in isA_Data instead. "
    "This module will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

from .base_vector_db import (
    BaseVectorDB,
    SearchResult,
    VectorSearchConfig,
    SearchMode,
    RankingMethod,
)
from .vector_db_factory import get_vector_db, VectorDBType, create_vector_db, get_default_config
from .qdrant_vector_db import QdrantVectorDB

__all__ = [
    "BaseVectorDB",
    "SearchResult",
    "VectorSearchConfig",
    "SearchMode",
    "RankingMethod",
    "get_vector_db",
    "VectorDBType",
    "create_vector_db",
    "get_default_config",
    "QdrantVectorDB",
]
