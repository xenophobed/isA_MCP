#!/usr/bin/env python3
"""
gRPC Clients Factory
Provides unified access to isa-common gRPC clients
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def get_client(
    service_name: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    user_id: str = "system",
    **kwargs,
) -> Optional[Any]:
    """
    Get gRPC client for specified service

    Args:
        service_name: Name of service ('minio', etc.)
        host: Service host (optional, uses Consul discovery if not provided)
        port: Service port (optional, uses Consul discovery if not provided)
        user_id: User ID for client session
        **kwargs: Additional client-specific arguments

    Returns:
        gRPC client instance or None if unavailable
    """
    service_name = service_name.lower()

    if service_name == "minio":
        from .minio_client import MinIOClient, ConsulRegistry

        if MinIOClient is None:
            logger.error("❌ MinIO client not available")
            return None

        try:
            # Create Consul registry for service discovery if host not provided
            consul = None
            if host is None:
                try:
                    consul = ConsulRegistry()
                    logger.debug("Using Consul for MinIO service discovery")
                except Exception as e:
                    logger.warning(f"Consul registry creation failed: {e}")

            # Create MinIO client
            client = MinIOClient(
                host=host,
                port=port,
                user_id=user_id,
                lazy_connect=True,
                enable_compression=True,
                enable_retry=True,
                consul_registry=consul,
                service_name_override="minio",
            )

            logger.info(f"✅ Created MinIO gRPC client for user: {user_id}")
            return client

        except Exception as e:
            logger.error(f"Failed to create MinIO client: {e}")
            import traceback

            traceback.print_exc()
            return None

    else:
        logger.error(f"Unknown service: {service_name}")
        return None


__all__ = ["get_client"]
