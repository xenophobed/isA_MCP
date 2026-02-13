#!/usr/bin/env python3
"""
Qdrant Vector Database Client
Re-exports isa-common QdrantClient for use in isA_MCP project
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Import and re-export isa-common clients (both sync and async)
try:
    from isa_common import QdrantClient, AsyncQdrantClient, ConsulRegistry

    logger.info("✅ isa-common Qdrant gRPC client loaded")

    __all__ = ["QdrantClient", "AsyncQdrantClient", "ConsulRegistry", "get_qdrant_client"]

except ImportError as e:
    logger.error(f"❌ Failed to import isa-common Qdrant client: {e}")
    logger.error("   Install with: pip install isa-common>=0.2.0")

    QdrantClient = None
    AsyncQdrantClient = None
    ConsulRegistry = None

    __all__ = []


# Global instance
_qdrant_client: Optional[AsyncQdrantClient] = None


async def get_qdrant_client(
    collection_name: str = "user_knowledge",
    vector_dimension: int = 1536,
    config: Optional[Dict[str, Any]] = None,
) -> AsyncQdrantClient:
    """
    Get global AsyncQdrantClient instance with lazy initialization

    Args:
        collection_name: Qdrant collection name (default: "user_knowledge")
        vector_dimension: Vector embedding dimension (default: 1536 for text-embedding-3-small)
        config: Optional configuration dict with:
            - host: Qdrant server host (default: discovered via Consul or env var)
            - port: Qdrant gRPC port (default: 50062)
            - distance_metric: 'Cosine', 'Euclid', 'Dot', 'Manhattan' (default: 'Cosine')

    Returns:
        AsyncQdrantClient instance

    Raises:
        ImportError: If isa-common is not installed

    Example:
        >>> client = await get_qdrant_client()
        >>> await client.create_collection("my_collection", vector_size=1536)
        >>> await client.upsert_points(collection_name="my_collection", points=[...])
        >>> results = await client.search(collection_name="my_collection", query_vector=[...])
    """
    global _qdrant_client

    if AsyncQdrantClient is None:
        raise ImportError(
            "isa-common Qdrant client not available. " "Install with: pip install isa-common>=0.2.0"
        )

    if _qdrant_client is None:
        default_config = {
            "collection_name": collection_name,
            "vector_dimension": vector_dimension,
            "distance_metric": "Cosine",
        }

        if config:
            default_config.update(config)

        _qdrant_client = AsyncQdrantClient(config=default_config)
        logger.info(
            f"✅ AsyncQdrantClient initialized (collection: {collection_name}, dim: {vector_dimension})"
        )

    return _qdrant_client
