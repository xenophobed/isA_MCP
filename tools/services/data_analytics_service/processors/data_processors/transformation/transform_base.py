#!/usr/bin/env python3
"""
Data Transformer Base Class
Abstract base class for data transformation processors used in visualization pipeline
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TransformationType(Enum):
    """Types of data transformations"""
    # Aggregation
    GROUP_BY = "group_by"
    AGGREGATE = "aggregate"
    PIVOT = "pivot"
    UNPIVOT = "unpivot"
    
    # Filtering
    FILTER = "filter"
    SAMPLE = "sample"
    TOP_N = "top_n"
    
    # Sorting
    SORT = "sort"
    RANK = "rank"
    
    # Time Series
    TIME_RESAMPLE = "time_resample"
    TIME_WINDOW = "time_window"
    MOVING_AVERAGE = "moving_average"
    
    # Mathematical
    NORMALIZE = "normalize"
    STANDARDIZE = "standardize"
    LOG_TRANSFORM = "log_transform"
    
    # Geospatial
    GEO_AGGREGATE = "geo_aggregate"
    GEO_FILTER = "geo_filter"
    
    # Custom
    CUSTOM = "custom"


class AggregationFunction(Enum):
    """Aggregation functions"""
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    STD = "std"
    VAR = "var"
    FIRST = "first"
    LAST = "last"


@dataclass
class TransformConfig:
    """Configuration for data transformation"""
    transformation_type: TransformationType
    
    # Grouping/Aggregation
    group_by_columns: List[str] = field(default_factory=list)
    aggregation_functions: Dict[str, AggregationFunction] = field(default_factory=dict)
    
    # Filtering
    filter_conditions: List[Dict[str, Any]] = field(default_factory=list)
    sample_size: Optional[int] = None
    sample_method: str = "random"  # random, systematic, stratified
    
    # Sorting
    sort_columns: List[str] = field(default_factory=list)
    sort_ascending: List[bool] = field(default_factory=list)
    
    # Time Series
    time_column: Optional[str] = None
    time_frequency: Optional[str] = None  # D, H, M, etc.
    window_size: Optional[int] = None
    
    # Mathematical
    normalize_method: str = "min_max"  # min_max, z_score, robust
    log_base: float = 10
    
    # Geospatial
    geo_column: Optional[str] = None
    geo_level: Optional[str] = None  # country, state, city, etc.
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformResult:
    """Result of data transformation"""
    success: bool
    transformed_data: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    transformation_applied: Optional[TransformationType] = None
    original_row_count: int = 0
    transformed_row_count: int = 0
    columns_added: List[str] = field(default_factory=list)
    columns_removed: List[str] = field(default_factory=list)
    execution_time_ms: float = 0
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class DataTransformerBase(ABC):
    """Abstract base class for data transformers"""
    
    def __init__(self):
        self.supported_transformations = self._get_supported_transformations()
        
    @abstractmethod
    def _get_supported_transformations(self) -> List[TransformationType]:
        """Return list of transformation types supported by this transformer"""
        pass
    
    @abstractmethod
    async def transform_data(self, data: List[Dict[str, Any]], 
                           config: TransformConfig) -> TransformResult:
        """Transform data according to configuration"""
        pass
    
    def supports_transformation(self, transformation_type: TransformationType) -> bool:
        """Check if this transformer supports the given transformation type"""
        return transformation_type in self.supported_transformations
    
    async def validate_config(self, data: List[Dict[str, Any]], 
                            config: TransformConfig) -> Dict[str, Any]:
        """Validate transformation configuration"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        try:
            # Check if transformation is supported
            if not self.supports_transformation(config.transformation_type):
                validation_result['errors'].append(
                    f"Transformation type {config.transformation_type.value} not supported"
                )
                validation_result['is_valid'] = False
            
            # Validate data exists
            if not data:
                validation_result['errors'].append("Input data cannot be empty")
                validation_result['is_valid'] = False
                return validation_result
            
            # Get available columns
            available_columns = set(data[0].keys()) if data else set()
            
            # Validate group by columns
            if config.group_by_columns:
                missing_cols = set(config.group_by_columns) - available_columns
                if missing_cols:
                    validation_result['errors'].append(
                        f"Group by columns not found: {missing_cols}"
                    )
                    validation_result['is_valid'] = False
            
            # Validate aggregation functions
            if config.aggregation_functions:
                missing_agg_cols = set(config.aggregation_functions.keys()) - available_columns
                if missing_agg_cols:
                    validation_result['errors'].append(
                        f"Aggregation columns not found: {missing_agg_cols}"
                    )
                    validation_result['is_valid'] = False
            
            # Validate sort columns
            if config.sort_columns:
                missing_sort_cols = set(config.sort_columns) - available_columns
                if missing_sort_cols:
                    validation_result['errors'].append(
                        f"Sort columns not found: {missing_sort_cols}"
                    )
                    validation_result['is_valid'] = False
            
            # Validate time column
            if config.time_column and config.time_column not in available_columns:
                validation_result['errors'].append(
                    f"Time column not found: {config.time_column}"
                )
                validation_result['is_valid'] = False
            
            # Validate geo column
            if config.geo_column and config.geo_column not in available_columns:
                validation_result['errors'].append(
                    f"Geographic column not found: {config.geo_column}"
                )
                validation_result['is_valid'] = False
            
            # Performance warnings
            if len(data) > 100000:
                validation_result['warnings'].append(
                    "Large dataset detected - transformation may be slow"
                )
            
            # Sample size validation
            if config.sample_size and config.sample_size > len(data):
                validation_result['warnings'].append(
                    f"Sample size ({config.sample_size}) larger than dataset ({len(data)})"
                )
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def analyze_data_characteristics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze data to suggest appropriate transformations"""
        if not data:
            return {'error': 'No data provided'}
        
        try:
            characteristics = {
                'row_count': len(data),
                'column_count': len(data[0]),
                'columns': list(data[0].keys()),
                'data_types': {},
                'null_counts': {},
                'unique_counts': {},
                'suggested_transformations': []
            }
            
            # Analyze each column
            for column in characteristics['columns']:
                values = [row.get(column) for row in data]
                non_null_values = [v for v in values if v is not None]
                
                # Data type analysis
                if non_null_values:
                    sample_value = non_null_values[0]
                    characteristics['data_types'][column] = type(sample_value).__name__
                
                # Null count
                characteristics['null_counts'][column] = len(values) - len(non_null_values)
                
                # Unique count
                characteristics['unique_counts'][column] = len(set(non_null_values))
            
            # Generate transformation suggestions
            suggestions = self._generate_transformation_suggestions(characteristics)
            characteristics['suggested_transformations'] = suggestions
            
            return characteristics
            
        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return {'error': str(e)}
    
    def _generate_transformation_suggestions(self, characteristics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate transformation suggestions based on data characteristics"""
        suggestions = []
        
        try:
            row_count = characteristics['row_count']
            columns = characteristics['columns']
            data_types = characteristics['data_types']
            unique_counts = characteristics['unique_counts']
            
            # Large dataset - suggest sampling
            if row_count > 10000:
                suggestions.append({
                    'transformation': TransformationType.SAMPLE,
                    'reason': 'Large dataset - sampling recommended for better performance',
                    'suggested_config': {'sample_size': min(5000, row_count // 2)}
                })
            
            # High cardinality categorical columns - suggest top N
            for column in columns:
                if (data_types.get(column) == 'str' and 
                    unique_counts.get(column, 0) > 20):
                    suggestions.append({
                        'transformation': TransformationType.TOP_N,
                        'reason': f'High cardinality in {column} - consider top N filtering',
                        'suggested_config': {'group_by_columns': [column]}
                    })
            
            # Multiple categorical columns - suggest grouping
            categorical_columns = [col for col, dtype in data_types.items() 
                                 if dtype == 'str' and unique_counts.get(col, 0) < 50]
            
            if len(categorical_columns) >= 2:
                suggestions.append({
                    'transformation': TransformationType.GROUP_BY,
                    'reason': 'Multiple categorical columns suitable for grouping',
                    'suggested_config': {'group_by_columns': categorical_columns[:2]}
                })
            
            # Numeric columns - suggest aggregation
            numeric_columns = [col for col, dtype in data_types.items() 
                             if dtype in ['int', 'float']]
            
            if numeric_columns and categorical_columns:
                suggestions.append({
                    'transformation': TransformationType.AGGREGATE,
                    'reason': 'Numeric columns available for aggregation',
                    'suggested_config': {
                        'group_by_columns': categorical_columns[:1],
                        'aggregation_functions': {col: AggregationFunction.SUM for col in numeric_columns[:3]}
                    }
                })
            
            # Time-like columns - suggest time series operations
            time_columns = [col for col in columns 
                          if any(time_word in col.lower() 
                               for time_word in ['date', 'time', 'timestamp', 'created', 'updated'])]
            
            if time_columns:
                suggestions.append({
                    'transformation': TransformationType.TIME_RESAMPLE,
                    'reason': f'Time column detected: {time_columns[0]}',
                    'suggested_config': {
                        'time_column': time_columns[0],
                        'time_frequency': 'D'
                    }
                })
            
        except Exception as e:
            logger.error(f"Transformation suggestion generation failed: {e}")
        
        return suggestions
    
    def prepare_for_visualization(self, data: List[Dict[str, Any]], 
                                chart_type: str) -> TransformConfig:
        """Prepare transformation config optimized for specific chart types"""
        try:
            if chart_type == "bar" or chart_type == "column":
                # For bar charts, often want to aggregate categorical data
                return TransformConfig(
                    transformation_type=TransformationType.GROUP_BY,
                    custom_params={'optimize_for': 'categorical_aggregation'}
                )
            
            elif chart_type == "line" or chart_type == "time_series":
                # For line charts, often want time-based aggregation
                return TransformConfig(
                    transformation_type=TransformationType.TIME_RESAMPLE,
                    custom_params={'optimize_for': 'time_series'}
                )
            
            elif chart_type == "scatter":
                # For scatter plots, might want sampling for large datasets
                if len(data) > 1000:
                    return TransformConfig(
                        transformation_type=TransformationType.SAMPLE,
                        sample_size=1000,
                        sample_method="random"
                    )
            
            elif chart_type == "heatmap":
                # For heatmaps, need pivot-like structure
                return TransformConfig(
                    transformation_type=TransformationType.PIVOT,
                    custom_params={'optimize_for': 'matrix_structure'}
                )
            
            # Default: no transformation
            return TransformConfig(transformation_type=TransformationType.CUSTOM)
            
        except Exception as e:
            logger.error(f"Visualization preparation failed: {e}")
            return TransformConfig(transformation_type=TransformationType.CUSTOM)
    
    def _create_error_result(self, error_message: str, 
                           original_row_count: int = 0,
                           execution_time_ms: float = 0) -> TransformResult:
        """Create error result"""
        return TransformResult(
            success=False,
            error_message=error_message,
            original_row_count=original_row_count,
            execution_time_ms=execution_time_ms
        )
    
    def _create_success_result(self, transformed_data: List[Dict[str, Any]],
                             transformation_type: TransformationType,
                             original_row_count: int,
                             execution_time_ms: float = 0,
                             metadata: Dict[str, Any] = None,
                             columns_added: List[str] = None,
                             columns_removed: List[str] = None,
                             warnings: List[str] = None) -> TransformResult:
        """Create success result"""
        return TransformResult(
            success=True,
            transformed_data=transformed_data,
            transformation_applied=transformation_type,
            original_row_count=original_row_count,
            transformed_row_count=len(transformed_data),
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
            columns_added=columns_added or [],
            columns_removed=columns_removed or [],
            warnings=warnings or []
        )