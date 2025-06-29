#!/usr/bin/env python3
"""
Data Analytics Service for MCP Server
Provides metadata discovery, semantic analysis, and data visualization capabilities
"""

__version__ = "1.0.0"
__author__ = "MCP Data Analytics Team"

# Core services
from .services.metadata_service import MetadataDiscoveryService

# Core components
from .core.metadata_extractor import MetadataExtractor

__all__ = [
    "MetadataDiscoveryService",
    "MetadataExtractor"
]