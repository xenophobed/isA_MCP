#!/usr/bin/env python3
"""
Vector Database Factory

Factory pattern for creating vector database instances.
Supports: Qdrant (via isa_common) and Weaviate
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
import logging

from .base_vector_db import BaseVectorDB

logger = logging.getLogger(__name__)

class VectorDBType(Enum):
    """Supported vector database types"""
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"

def get_vector_db(
    db_type: Optional[VectorDBType] = None,
    config: Optional[Dict[str, Any]] = None
) -> BaseVectorDB:
    """
    Create vector database instance based on type and configuration.

    Args:
        db_type: Database type to create (defaults to QDRANT)
        config: Database-specific configuration

    Returns:
        Vector database instance

    Raises:
        ValueError: If database type is not supported
        ImportError: If required dependencies are missing
    """
    # Determine database type from environment or parameter
    if db_type is None:
        env_db_type = os.getenv('VECTOR_DB_TYPE', 'qdrant').lower()
        try:
            db_type = VectorDBType(env_db_type)
        except ValueError:
            logger.warning(f"Unknown VECTOR_DB_TYPE: {env_db_type}, falling back to qdrant")
            db_type = VectorDBType.QDRANT

    config = config or {}

    # Create database instance based on type
    if db_type == VectorDBType.QDRANT:
        try:
            from .qdrant_vector_db import QdrantVectorDB
            return QdrantVectorDB(config)
        except ImportError as e:
            logger.error(f"Qdrant dependencies missing: {e}")
            logger.info(
                "Install isa_common package from isA_Cloud:\n"
                "  cd /path/to/isA_Cloud\n"
                "  pip install -e isA_common"
            )
            raise ImportError("Qdrant client (isa_common) not available")

    elif db_type == VectorDBType.WEAVIATE:
        try:
            from .weaviate_vector_db import WeaviateVectorDB
            return WeaviateVectorDB(config)
        except ImportError as e:
            logger.error(f"Weaviate dependencies missing: {e}")
            logger.info("Install weaviate-client: pip install weaviate-client")
            raise ImportError("Weaviate client not available")

    else:
        raise ValueError(f"Unsupported vector database type: {db_type}")

def get_default_config(db_type: VectorDBType) -> Dict[str, Any]:
    """
    Get default configuration for a database type.

    Args:
        db_type: Database type

    Returns:
        Default configuration dictionary
    """
    if db_type == VectorDBType.QDRANT:
        return {
            'host': os.getenv('QDRANT_HOST', 'localhost'),
            'port': int(os.getenv('QDRANT_PORT', '50062')),  # gRPC port
            'collection_name': os.getenv('QDRANT_COLLECTION', 'user_knowledge'),
            'vector_dimension': int(os.getenv('VECTOR_DIMENSION', '1536')),
            'distance_metric': os.getenv('QDRANT_DISTANCE', 'Cosine')
        }

    elif db_type == VectorDBType.WEAVIATE:
        return {
            'url': os.getenv('WEAVIATE_URL', 'http://localhost:8080'),
            'api_key': os.getenv('WEAVIATE_API_KEY'),
            'class_name': os.getenv('WEAVIATE_CLASS', 'UserKnowledge'),
            'vector_dimension': int(os.getenv('VECTOR_DIMENSION', '1536')),
            'timeout': 60
        }

    else:
        return {}

# Global instance cache for singleton pattern
_vector_db_instances: Dict[str, BaseVectorDB] = {}

def get_singleton_vector_db(
    db_type: Optional[VectorDBType] = None,
    config: Optional[Dict[str, Any]] = None
) -> BaseVectorDB:
    """
    Get singleton vector database instance.

    Args:
        db_type: Database type
        config: Configuration

    Returns:
        Singleton vector database instance
    """
    # Determine database type
    if db_type is None:
        env_db_type = os.getenv('VECTOR_DB_TYPE', 'qdrant').lower()
        try:
            db_type = VectorDBType(env_db_type)
        except ValueError:
            db_type = VectorDBType.QDRANT

    # Create cache key
    cache_key = f"{db_type.value}_{hash(str(sorted(config.items()) if config else []))}"

    # Return cached instance or create new one
    if cache_key not in _vector_db_instances:
        _vector_db_instances[cache_key] = get_vector_db(db_type, config)

    return _vector_db_instances[cache_key]

def clear_vector_db_cache():
    """Clear the vector database instance cache."""
    global _vector_db_instances
    _vector_db_instances.clear()

# Convenience function for backward compatibility
def create_vector_db() -> BaseVectorDB:
    """Create vector database using environment configuration (defaults to Qdrant)."""
    db_type_str = os.getenv('VECTOR_DB_TYPE', 'qdrant').lower()
    try:
        db_type = VectorDBType(db_type_str)
    except ValueError:
        db_type = VectorDBType.QDRANT

    config = get_default_config(db_type)
    return get_singleton_vector_db(db_type, config)
