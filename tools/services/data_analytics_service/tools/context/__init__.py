"""
Context utilities for digital and data analytics tools

Provides progress tracking and type detection for universal pipelines:
- Digital assets (PDF, images, documents)
- Data analytics (CSV, Parquet, datasets)
"""

from .digital_progress_context import (
    DigitalAssetProgressReporter,
    AssetTypeDetector
)

from .data_progress_context import (
    DataProgressReporter,
    DataSourceDetector
)

__all__ = [
    # Digital asset context
    "DigitalAssetProgressReporter",
    "AssetTypeDetector",
    # Data analytics context
    "DataProgressReporter",
    "DataSourceDetector"
]
