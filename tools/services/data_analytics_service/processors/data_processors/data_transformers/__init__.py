"""
Data Transformers Package
Atomic processors for data transformation operations in visualization pipeline

Provides:
- Base data transformer interface
- Data aggregation and grouping
- Time series processing
- Geospatial data processing
"""

from .transform_base import (
    DataTransformerBase,
    TransformationType,
    TransformConfig,
    TransformResult,
    AggregationFunction
)

from .data_aggregator import (
    DataAggregator,
    create_data_aggregator,
    quick_group_by,
    quick_top_n
)

__all__ = [
    'DataTransformerBase',
    'TransformationType',
    'TransformConfig',
    'TransformResult',
    'AggregationFunction',
    'DataAggregator',
    'create_data_aggregator',
    'quick_group_by',
    'quick_top_n'
]