#!/usr/bin/env python3
"""
PostgreSQL Client
Re-exports isa-common PostgresClient for use in isA_MCP project
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import and re-export isa-common PostgresClient
try:
    from isa_common.postgres_client import PostgresClient
    from isa_common.consul_client import ConsulRegistry

    logger.info("✅ isa-common PostgreSQL client loaded")

    __all__ = ['PostgresClient', 'ConsulRegistry', 'get_postgres_client']

except ImportError as e:
    logger.error(f"❌ Failed to import isa-common PostgreSQL client: {e}")
    logger.error("   Install with: pip install -e /path/to/isA_Cloud/isA_common")

    PostgresClient = None
    ConsulRegistry = None

    __all__ = []


# Global instance
_postgres_client: Optional[PostgresClient] = None


async def get_postgres_client() -> PostgresClient:
    """
    Get global PostgreSQL client instance with lazy initialization

    Returns:
        PostgresClient instance

    Raises:
        ImportError: If isa-common is not installed
    """
    global _postgres_client

    if PostgresClient is None:
        raise ImportError(
            "isa-common PostgreSQL client not available. "
            "Install with: pip install -e /path/to/isA_Cloud/isA_common"
        )

    if _postgres_client is None:
        _postgres_client = PostgresClient()
        logger.info("✅ PostgreSQL client initialized")

    return _postgres_client
