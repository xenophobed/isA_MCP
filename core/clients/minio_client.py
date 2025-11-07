#!/usr/bin/env python3
"""
MinIO Client for Object Storage
Re-exports isa-common MinIOClient for use in isA_MCP project
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import and re-export isa-common MinIOClient
try:
    from isa_common.minio_client import MinIOClient
    logger.info("✅ isa-common MinIO gRPC client loaded")
    MINIO_AVAILABLE = True
    __all__ = ['MinIOClient', 'get_minio_client']
except ImportError as e:
    logger.error(f"❌ Failed to import isa-common MinIO client: {e}")
    logger.error("   Install with: pip install -e /path/to/isA_Cloud/isA_common")
    MinIOClient = None
    MINIO_AVAILABLE = False
    __all__ = []


# Global instance
_minio_client: Optional[MinIOClient] = None


def get_minio_client(
    host: str = 'isa-minio-grpc',
    port: int = 50051
) -> Optional[MinIOClient]:
    """
    Get global MinIO client instance with lazy initialization

    Args:
        host: MinIO gRPC server host (default: discovered via Consul or 'isa-minio-grpc')
        port: MinIO gRPC port (default: 50051)

    Returns:
        MinIOClient instance or None if unavailable
    """
    global _minio_client

    if not MINIO_AVAILABLE:
        logger.warning("isa-common MinIO client not available")
        return None

    if _minio_client is None:
        try:
            _minio_client = MinIOClient(host=host, port=port)
            logger.info(f"✅ MinIO gRPC client initialized: {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            return None

    return _minio_client
