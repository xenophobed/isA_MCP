#!/usr/bin/env python3
"""
DuckDB gRPC Client
Re-exports isa-common DuckDBClient for use in isA_MCP project
"""

import logging

logger = logging.getLogger(__name__)

# Import and re-export isa-common DuckDBClient
try:
    from isa_common.duckdb_client import DuckDBClient
    from isa_common.consul_client import ConsulRegistry

    logger.info("✅ isa-common DuckDB gRPC client loaded")

    __all__ = ['DuckDBClient', 'ConsulRegistry']

except ImportError as e:
    logger.error(f"❌ Failed to import isa-common DuckDB client: {e}")
    logger.error("   Install with: pip install -e /path/to/isA_Cloud/isA_common")

    DuckDBClient = None
    ConsulRegistry = None

    __all__ = []






