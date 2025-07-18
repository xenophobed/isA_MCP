#!/usr/bin/env python3
"""
Data Analytics Service Package

A comprehensive data analytics service implementing the MCP architecture.
Provides tools and services for data extraction, processing, and analysis.
"""

# Package metadata
__version__ = "1.0.0"
__author__ = "Data Analytics Team"

# Core functionality - only import what actually exists and works
try:
    from .models.base_models import AssetType
    
    # Only import working components
    __all__ = [
        "AssetType"
    ]
    
except ImportError as e:
    # Graceful fallback if imports fail
    __all__ = []
    print(f"Warning: Some data analytics components not available: {e}")

def get_version():
    """Get package version."""
    return __version__