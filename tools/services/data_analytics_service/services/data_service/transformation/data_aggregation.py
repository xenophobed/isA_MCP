"""
Data Aggregation Service - Step 1 of Transformation Pipeline
Uses transformation processors to perform data grouping and aggregation
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from tools.services.data_analytics_service.processors.data_processors.transformation.data_aggregator import DataAggregator
from tools.services.data_analytics_service.processors.data_processors.transformation.transform_base import (
    TransformConfig, TransformationType, AggregationFunction
)

logger = logging.getLogger(__name__)

@dataclass
class AggregationResult:
    """Result of data aggregation step"""
    success: bool
    aggregated_data: Optional[pd.DataFrame] = None
    aggregation_summary: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class DataAggregationService:
    """
    Data Aggregation Service - Step 1 of Transformation Pipeline
    
    Handles:
    - Data grouping operations
    - Statistical aggregations (sum, mean, count, etc.)
    - Pivot table creation
    - Data sampling and filtering
    """
    
    def __init__(self):
        self.aggregator = DataAggregator()
        self.execution_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_duration': 0.0
        }
        
        logger.info("Data Aggregation Service initialized")
    
    def aggregate_data(self, 
                      data: pd.DataFrame,
                      aggregation_config: Dict[str, Any]) -> AggregationResult:
        """
        Execute data aggregation operations
        
        Args:
            data: Input DataFrame to aggregate
            aggregation_config: Aggregation configuration
            
        Returns:
            AggregationResult with aggregated data
        """
        start_time = datetime.now()
        
        try:
            # Convert DataFrame to list of dicts for processor
            data_records = data.to_dict('records')
            
            # Parse aggregation configuration
            transform_config = self._parse_aggregation_config(aggregation_config)
            
            # Execute aggregation using processor
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                transform_result = loop.run_until_complete(
                    self.aggregator.transform_data(data_records, transform_config)
                )
            finally:
                loop.close()
            
            if not transform_result.success:
                return AggregationResult(
                    success=False,
                    errors=[transform_result.error_message or "Aggregation failed"]
                )
            
            # Convert result back to DataFrame
            aggregated_df = pd.DataFrame(transform_result.transformed_data)
            
            # Calculate performance metrics
            duration = (datetime.now() - start_time).total_seconds()
            performance_metrics = {
                'duration_seconds': duration,
                'input_rows': len(data),
                'output_rows': len(aggregated_df),
                'input_columns': len(data.columns),
                'output_columns': len(aggregated_df.columns),
                'execution_time_ms': transform_result.execution_time_ms,
                'data_reduction_ratio': len(aggregated_df) / len(data) if len(data) > 0 else 0
            }
            
            # Create aggregation summary
            aggregation_summary = {
                'transformation_type': transform_result.transformation_applied.value if transform_result.transformation_applied else None,
                'original_shape': data.shape,
                'aggregated_shape': aggregated_df.shape,
                'columns_added': transform_result.columns_added,
                'columns_removed': transform_result.columns_removed,
                'metadata': transform_result.metadata
            }
            
            # Update execution stats
            self._update_stats(True, duration)
            
            return AggregationResult(
                success=True,
                aggregated_data=aggregated_df,
                aggregation_summary=aggregation_summary,
                performance_metrics=performance_metrics,
                warnings=transform_result.warnings
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(False, duration)
            
            logger.error(f"Data aggregation failed: {e}")
            return AggregationResult(
                success=False,
                errors=[f"Aggregation error: {str(e)}"],
                performance_metrics={'duration_seconds': duration}
            )
    
    def _parse_aggregation_config(self, config: Dict[str, Any]) -> TransformConfig:
        """Parse aggregation configuration to TransformConfig"""
        try:
            # Determine transformation type
            transform_type = TransformationType.AGGREGATE
            
            if 'transformation_type' in config:
                type_str = config['transformation_type'].upper()
                if hasattr(TransformationType, type_str):
                    transform_type = getattr(TransformationType, type_str)
            
            # Parse group by columns
            group_by_columns = config.get('group_by_columns', [])
            
            # Parse aggregation functions
            agg_functions = {}
            if 'aggregation_functions' in config:
                for col, func_str in config['aggregation_functions'].items():
                    if isinstance(func_str, str):
                        try:
                            agg_functions[col] = AggregationFunction(func_str.lower())
                        except ValueError:
                            agg_functions[col] = AggregationFunction.SUM
                    elif isinstance(func_str, AggregationFunction):
                        agg_functions[col] = func_str
            
            # Parse filter conditions
            filter_conditions = config.get('filter_conditions', [])
            
            # Parse custom parameters
            custom_params = config.get('custom_params', {})
            
            return TransformConfig(
                transformation_type=transform_type,
                group_by_columns=group_by_columns,
                aggregation_functions=agg_functions,
                filter_conditions=filter_conditions,
                custom_params=custom_params
            )
            
        except Exception as e:
            logger.error(f"Failed to parse aggregation config: {e}")
            # Return default config
            return TransformConfig(transformation_type=TransformationType.AGGREGATE)
    
    def create_group_by_config(self, 
                              group_columns: List[str],
                              agg_functions: Dict[str, str]) -> Dict[str, Any]:
        """
        Create configuration for GROUP BY operations
        
        Args:
            group_columns: Columns to group by
            agg_functions: Aggregation functions for columns
            
        Returns:
            Configuration dictionary
        """
        return {
            'transformation_type': 'group_by',
            'group_by_columns': group_columns,
            'aggregation_functions': agg_functions
        }
    
    def create_pivot_config(self,
                           index_column: str,
                           column_column: str,
                           value_column: str) -> Dict[str, Any]:
        """
        Create configuration for PIVOT operations
        
        Args:
            index_column: Column to use as index
            column_column: Column to pivot
            value_column: Column with values
            
        Returns:
            Configuration dictionary
        """
        return {
            'transformation_type': 'pivot',
            'custom_params': {
                'index_column': index_column,
                'column_column': column_column,
                'value_column': value_column
            }
        }
    
    def create_top_n_config(self,
                           n: int,
                           sort_column: str,
                           ascending: bool = False) -> Dict[str, Any]:
        """
        Create configuration for TOP N operations
        
        Args:
            n: Number of top records
            sort_column: Column to sort by
            ascending: Sort direction
            
        Returns:
            Configuration dictionary
        """
        return {
            'transformation_type': 'top_n',
            'custom_params': {
                'n': n,
                'sort_column': sort_column,
                'ascending': ascending
            }
        }
    
    def create_filter_config(self,
                            conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create configuration for FILTER operations
        
        Args:
            conditions: List of filter conditions
            
        Returns:
            Configuration dictionary
        """
        return {
            'transformation_type': 'filter',
            'filter_conditions': conditions
        }
    
    def _update_stats(self, success: bool, duration: float):
        """Update execution statistics"""
        self.execution_stats['total_operations'] += 1
        
        if success:
            self.execution_stats['successful_operations'] += 1
        else:
            self.execution_stats['failed_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_operations']
        old_avg = self.execution_stats['average_duration']
        self.execution_stats['average_duration'] = (old_avg * (total - 1) + duration) / total
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_operations'] / 
                max(1, self.execution_stats['total_operations'])
            )
        }
    
    def get_supported_aggregations(self) -> List[str]:
        """Get list of supported aggregation functions"""
        return [func.value for func in AggregationFunction]
    
    def get_supported_transformations(self) -> List[str]:
        """Get list of supported transformation types"""
        return [trans.value for trans in self.aggregator.supported_transformations]