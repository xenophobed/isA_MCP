#!/usr/bin/env python3
"""
PostgreSQL Client
Re-exports isa-common PostgresClient for use in isA_MCP project
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import and re-export isa-common clients (both sync and async)
try:
    from isa_common import PostgresClient, AsyncPostgresClient, ConsulRegistry

    logger.info("✅ isa-common PostgreSQL client loaded")

    __all__ = ['PostgresClient', 'AsyncPostgresClient', 'ConsulRegistry', 'get_postgres_client']

except ImportError as e:
    logger.error(f"❌ Failed to import isa-common PostgreSQL client: {e}")
    logger.error("   Install with: pip install isa-common>=0.2.0")

    PostgresClient = None
    AsyncPostgresClient = None
    ConsulRegistry = None

    __all__ = []


# Global instance
_postgres_client: Optional[AsyncPostgresClient] = None


async def get_postgres_client() -> AsyncPostgresClient:
    """
    Get global AsyncPostgresClient instance with lazy initialization

    Returns:
        AsyncPostgresClient instance

    Raises:
        ImportError: If isa-common is not installed
    """
    global _postgres_client

    if AsyncPostgresClient is None:
        raise ImportError(
            "isa-common PostgreSQL client not available. "
            "Install with: pip install isa-common>=0.2.0"
        )

    if _postgres_client is None:
        _postgres_client = AsyncPostgresClient()
        logger.info("✅ AsyncPostgresClient initialized")

    return _postgres_client
