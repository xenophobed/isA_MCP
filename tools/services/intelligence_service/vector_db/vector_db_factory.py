#!/usr/bin/env python3
"""
Vector Database Factory

Factory pattern for creating vector database instances based on configuration.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
import logging

from .base_vector_db import BaseVectorDB

logger = logging.getLogger(__name__)

class VectorDBType(Enum):
    """Supported vector database types"""
    SUPABASE = "supabase"
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"
    CHROMADB = "chromadb"

def get_vector_db(
    db_type: Optional[VectorDBType] = None,
    config: Optional[Dict[str, Any]] = None
) -> BaseVectorDB:
    """
    Create vector database instance based on type and configuration.
    
    Args:
        db_type: Database type to create (defaults to environment variable)
        config: Database-specific configuration
        
    Returns:
        Vector database instance
        
    Raises:
        ValueError: If database type is not supported
        ImportError: If required dependencies are missing
    """
    # Determine database type from environment or parameter
    if db_type is None:
        env_db_type = os.getenv('VECTOR_DB_TYPE', 'supabase').lower()
        try:
            db_type = VectorDBType(env_db_type)
        except ValueError:
            logger.warning(f"Unknown VECTOR_DB_TYPE: {env_db_type}, falling back to supabase")
            db_type = VectorDBType.SUPABASE
    
    config = config or {}
    
    # Create database instance based on type
    if db_type == VectorDBType.SUPABASE:
        from .supabase_vector_db import SupabaseVectorDB
        return SupabaseVectorDB(config)
    
    elif db_type == VectorDBType.QDRANT:
        try:
            from .qdrant_vector_db import QdrantVectorDB
            return QdrantVectorDB(config)
        except ImportError as e:
            logger.error(f"Qdrant dependencies missing: {e}")
            logger.info("Install qdrant-client: pip install qdrant-client")
            raise ImportError("Qdrant client not available")
    
    elif db_type == VectorDBType.WEAVIATE:
        try:
            from .weaviate_vector_db import WeaviateVectorDB
            return WeaviateVectorDB(config)
        except ImportError as e:
            logger.error(f"Weaviate dependencies missing: {e}")
            logger.info("Install weaviate-client: pip install weaviate-client")
            raise ImportError("Weaviate client not available")
    
    elif db_type == VectorDBType.CHROMADB:
        try:
            from .chromadb_vector_db import ChromaVectorDB
            return ChromaVectorDB(config)
        except ImportError as e:
            logger.error(f"ChromaDB dependencies missing: {e}")
            logger.info("Install chromadb: pip install chromadb")
            raise ImportError("ChromaDB client not available")
    
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
    if db_type == VectorDBType.SUPABASE:
        return {
            'table_name': os.getenv('SUPABASE_KNOWLEDGE_TABLE', 'user_knowledge'),
            'schema': os.getenv('SUPABASE_SCHEMA', 'dev'),
            'vector_dimension': 1536,
            'distance_metric': 'cosine'
        }
    
    elif db_type == VectorDBType.QDRANT:
        return {
            'host': os.getenv('QDRANT_HOST', 'localhost'),
            'port': int(os.getenv('QDRANT_PORT', '6333')),
            'collection_name': os.getenv('QDRANT_COLLECTION', 'user_knowledge'),
            'vector_dimension': 1536,
            'distance_metric': 'Cosine',
            'api_key': os.getenv('QDRANT_API_KEY'),
            'timeout': 60
        }
    
    elif db_type == VectorDBType.WEAVIATE:
        return {
            'url': os.getenv('WEAVIATE_URL', 'http://localhost:8080'),
            'api_key': os.getenv('WEAVIATE_API_KEY'),
            'class_name': os.getenv('WEAVIATE_CLASS', 'UserKnowledge'),
            'vector_dimension': 1536,
            'timeout': 60
        }
    
    elif db_type == VectorDBType.CHROMADB:
        return {
            'host': os.getenv('CHROMADB_HOST', 'localhost'),
            'port': int(os.getenv('CHROMADB_PORT', '8000')),
            'collection_name': os.getenv('CHROMADB_COLLECTION', 'user_knowledge'),
            'vector_dimension': 1536,
            'distance_metric': 'cosine'
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
        env_db_type = os.getenv('VECTOR_DB_TYPE', 'supabase').lower()
        try:
            db_type = VectorDBType(env_db_type)
        except ValueError:
            db_type = VectorDBType.SUPABASE
    
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
    """Create vector database using environment configuration."""
    db_type_str = os.getenv('VECTOR_DB_TYPE', 'supabase').lower()
    try:
        db_type = VectorDBType(db_type_str)
    except ValueError:
        db_type = VectorDBType.SUPABASE
    
    config = get_default_config(db_type)
    return get_singleton_vector_db(db_type, config)