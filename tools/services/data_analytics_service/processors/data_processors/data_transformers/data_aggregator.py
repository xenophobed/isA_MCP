#!/usr/bin/env python3
"""
Data Aggregator Processor
Handles grouping, aggregation, and summarization operations for visualization data
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict, Counter
import logging

from .transform_base import (
    DataTransformerBase, TransformationType, TransformConfig, 
    TransformResult, AggregationFunction
)

logger = logging.getLogger(__name__)


class DataAggregator(DataTransformerBase):
    """Data aggregation processor for visualization preparation"""
    
    def __init__(self):
        super().__init__()
        logger.info("DataAggregator initialized")
    
    def _get_supported_transformations(self) -> List[TransformationType]:
        """Return supported transformation types"""
        return [
            TransformationType.GROUP_BY,
            TransformationType.AGGREGATE,
            TransformationType.TOP_N,
            TransformationType.PIVOT,
            TransformationType.FILTER
        ]
    
    async def transform_data(self, data: List[Dict[str, Any]], 
                           config: TransformConfig) -> TransformResult:
        """Transform data using aggregation operations"""
        start_time = datetime.now()
        original_count = len(data)
        
        try:
            # Validate configuration
            validation = await self.validate_config(data, config)
            if not validation['is_valid']:
                return self._create_error_result(
                    f"Validation failed: {', '.join(validation['errors'])}",
                    original_count
                )
            
            # Route to specific transformation method
            if config.transformation_type == TransformationType.GROUP_BY:
                result_data = await self._group_by_transform(data, config)
            elif config.transformation_type == TransformationType.AGGREGATE:
                result_data = await self._aggregate_transform(data, config)
            elif config.transformation_type == TransformationType.TOP_N:
                result_data = await self._top_n_transform(data, config)
            elif config.transformation_type == TransformationType.PIVOT:
                result_data = await self._pivot_transform(data, config)
            elif config.transformation_type == TransformationType.FILTER:
                result_data = await self._filter_transform(data, config)
            else:
                return self._create_error_result(
                    f"Unsupported transformation: {config.transformation_type.value}",
                    original_count
                )
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return self._create_success_result(
                transformed_data=result_data,
                transformation_type=config.transformation_type,
                original_row_count=original_count,
                execution_time_ms=execution_time,
                metadata={
                    'aggregation_method': config.transformation_type.value,
                    'group_by_columns': config.group_by_columns,
                    'aggregation_functions': {k: v.value for k, v in config.aggregation_functions.items()}
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Data aggregation failed: {e}")
            return self._create_error_result(str(e), original_count, execution_time)
    
    async def _group_by_transform(self, data: List[Dict[str, Any]], 
                                config: TransformConfig) -> List[Dict[str, Any]]:
        """Group data by specified columns"""
        if not config.group_by_columns:
            return data
        
        # Group data
        groups = defaultdict(list)
        
        for row in data:
            # Create group key
            group_key = tuple(row.get(col) for col in config.group_by_columns)
            groups[group_key].append(row)
        
        # Convert groups back to list format
        result = []
        for group_key, group_rows in groups.items():
            # Create representative row for the group
            group_row = {}
            
            # Add grouping columns
            for i, col in enumerate(config.group_by_columns):
                group_row[col] = group_key[i]
            
            # Add count
            group_row['count'] = len(group_rows)
            
            # Add first non-grouping columns as examples
            first_row = group_rows[0]
            for col, value in first_row.items():
                if col not in config.group_by_columns and col not in group_row:
                    group_row[f"{col}_example"] = value
            
            result.append(group_row)
        
        return result
    
    async def _aggregate_transform(self, data: List[Dict[str, Any]], 
                                 config: TransformConfig) -> List[Dict[str, Any]]:
        """Aggregate data with specified functions"""
        if not config.group_by_columns and not config.aggregation_functions:
            return data
        
        # If no grouping, treat entire dataset as one group
        if not config.group_by_columns:
            return [await self._calculate_aggregations(data, config.aggregation_functions)]
        
        # Group data first
        groups = defaultdict(list)
        
        for row in data:
            group_key = tuple(row.get(col) for col in config.group_by_columns)
            groups[group_key].append(row)
        
        # Calculate aggregations for each group
        result = []
        for group_key, group_rows in groups.items():
            group_row = {}
            
            # Add grouping columns
            for i, col in enumerate(config.group_by_columns):
                group_row[col] = group_key[i]
            
            # Calculate aggregations
            aggregated_values = await self._calculate_aggregations(group_rows, config.aggregation_functions)
            group_row.update(aggregated_values)
            
            result.append(group_row)
        
        return result
    
    async def _calculate_aggregations(self, group_data: List[Dict[str, Any]], 
                                    agg_functions: Dict[str, AggregationFunction]) -> Dict[str, Any]:
        """Calculate aggregation functions for a group of data"""
        result = {}
        
        for column, agg_func in agg_functions.items():
            values = [row.get(column) for row in group_data if row.get(column) is not None]
            
            if not values:
                result[f"{column}_{agg_func.value}"] = None
                continue
            
            try:
                if agg_func == AggregationFunction.SUM:
                    result[f"{column}_{agg_func.value}"] = sum(values)
                elif agg_func == AggregationFunction.COUNT:
                    result[f"{column}_{agg_func.value}"] = len(values)
                elif agg_func == AggregationFunction.AVG:
                    result[f"{column}_{agg_func.value}"] = sum(values) / len(values)
                elif agg_func == AggregationFunction.MIN:
                    result[f"{column}_{agg_func.value}"] = min(values)
                elif agg_func == AggregationFunction.MAX:
                    result[f"{column}_{agg_func.value}"] = max(values)
                elif agg_func == AggregationFunction.MEDIAN:
                    sorted_values = sorted(values)
                    n = len(sorted_values)
                    if n % 2 == 0:
                        result[f"{column}_{agg_func.value}"] = (sorted_values[n//2-1] + sorted_values[n//2]) / 2
                    else:
                        result[f"{column}_{agg_func.value}"] = sorted_values[n//2]
                elif agg_func == AggregationFunction.STD:
                    if len(values) > 1:
                        mean = sum(values) / len(values)
                        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
                        result[f"{column}_{agg_func.value}"] = variance ** 0.5
                    else:
                        result[f"{column}_{agg_func.value}"] = 0
                elif agg_func == AggregationFunction.VAR:
                    if len(values) > 1:
                        mean = sum(values) / len(values)
                        result[f"{column}_{agg_func.value}"] = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
                    else:
                        result[f"{column}_{agg_func.value}"] = 0
                elif agg_func == AggregationFunction.FIRST:
                    result[f"{column}_{agg_func.value}"] = values[0]
                elif agg_func == AggregationFunction.LAST:
                    result[f"{column}_{agg_func.value}"] = values[-1]
                    
            except (TypeError, ValueError) as e:
                logger.warning(f"Aggregation failed for {column} with {agg_func.value}: {e}")
                result[f"{column}_{agg_func.value}"] = None
        
        return result
    
    async def _top_n_transform(self, data: List[Dict[str, Any]], 
                             config: TransformConfig) -> List[Dict[str, Any]]:
        """Get top N records based on specified criteria"""
        n = config.custom_params.get('n', 10)
        sort_column = config.custom_params.get('sort_column')
        ascending = config.custom_params.get('ascending', False)
        
        if not sort_column:
            # If no sort column specified, use first numeric column or return first N
            numeric_columns = []
            if data:
                for col, value in data[0].items():
                    if isinstance(value, (int, float)):
                        numeric_columns.append(col)
                
                if numeric_columns:
                    sort_column = numeric_columns[0]
        
        if sort_column:
            # Sort by specified column
            try:
                sorted_data = sorted(data, 
                                   key=lambda x: x.get(sort_column, 0) or 0, 
                                   reverse=not ascending)
                return sorted_data[:n]
            except Exception as e:
                logger.warning(f"Sorting failed: {e}, returning first {n} records")
        
        # Fallback: return first N records
        return data[:n]
    
    async def _pivot_transform(self, data: List[Dict[str, Any]], 
                             config: TransformConfig) -> List[Dict[str, Any]]:
        """Create pivot table structure"""
        index_column = config.custom_params.get('index_column')
        column_column = config.custom_params.get('column_column') 
        value_column = config.custom_params.get('value_column')
        
        if not all([index_column, column_column, value_column]):
            logger.warning("Pivot requires index_column, column_column, and value_column")
            return data
        
        # Create pivot structure
        pivot_data = defaultdict(dict)
        
        for row in data:
            index_val = row.get(index_column)
            column_val = row.get(column_column)
            value_val = row.get(value_column)
            
            if all(v is not None for v in [index_val, column_val, value_val]):
                pivot_data[index_val][column_val] = value_val
        
        # Convert to list of dictionaries
        result = []
        for index_val, columns in pivot_data.items():
            row = {index_column: index_val}
            row.update(columns)
            result.append(row)
        
        return result
    
    async def _filter_transform(self, data: List[Dict[str, Any]], 
                              config: TransformConfig) -> List[Dict[str, Any]]:
        """Filter data based on conditions"""
        if not config.filter_conditions:
            return data
        
        result = []
        
        for row in data:
            include_row = True
            
            for condition in config.filter_conditions:
                column = condition.get('column')
                operator = condition.get('operator', '==')
                value = condition.get('value')
                
                if column not in row:
                    include_row = False
                    break
                
                row_value = row[column]
                
                # Apply filter condition
                try:
                    if operator == '==':
                        if row_value != value:
                            include_row = False
                            break
                    elif operator == '!=':
                        if row_value == value:
                            include_row = False
                            break
                    elif operator == '>':
                        if not (row_value > value):
                            include_row = False
                            break
                    elif operator == '>=':
                        if not (row_value >= value):
                            include_row = False
                            break
                    elif operator == '<':
                        if not (row_value < value):
                            include_row = False
                            break
                    elif operator == '<=':
                        if not (row_value <= value):
                            include_row = False
                            break
                    elif operator == 'in':
                        if row_value not in value:
                            include_row = False
                            break
                    elif operator == 'not_in':
                        if row_value in value:
                            include_row = False
                            break
                    elif operator == 'contains':
                        if str(value).lower() not in str(row_value).lower():
                            include_row = False
                            break
                            
                except (TypeError, ValueError) as e:
                    logger.warning(f"Filter condition failed: {e}")
                    include_row = False
                    break
            
            if include_row:
                result.append(row)
        
        return result
    
    async def smart_aggregate_for_chart(self, data: List[Dict[str, Any]], 
                                      chart_type: str,
                                      max_categories: int = 20) -> List[Dict[str, Any]]:
        """Smart aggregation optimized for specific chart types"""
        try:
            if not data:
                return data
            
            # Analyze data structure
            characteristics = self.analyze_data_characteristics(data)
            columns = characteristics['columns']
            data_types = characteristics['data_types']
            unique_counts = characteristics['unique_counts']
            
            # Find categorical and numeric columns
            categorical_cols = [col for col, dtype in data_types.items() 
                              if dtype == 'str' and unique_counts.get(col, 0) <= max_categories]
            numeric_cols = [col for col, dtype in data_types.items() 
                          if dtype in ['int', 'float']]
            
            if chart_type in ['bar', 'column', 'pie']:
                # For categorical charts, aggregate by category
                if categorical_cols and numeric_cols:
                    config = TransformConfig(
                        transformation_type=TransformationType.AGGREGATE,
                        group_by_columns=[categorical_cols[0]],
                        aggregation_functions={
                            numeric_cols[0]: AggregationFunction.SUM
                        }
                    )
                    result = await self.transform_data(data, config)
                    return result.transformed_data if result.success else data
            
            elif chart_type in ['line', 'area']:
                # For line charts, might want time-based aggregation or sorting
                if len(data) > 100:
                    # Sample data for performance
                    return data[::len(data)//100]  # Take every nth record
            
            elif chart_type == 'scatter':
                # For scatter plots, limit data points for performance
                if len(data) > 1000:
                    return data[::len(data)//1000]  # Sample data
            
            return data
            
        except Exception as e:
            logger.error(f"Smart aggregation failed: {e}")
            return data


# Convenience functions
def create_data_aggregator() -> DataAggregator:
    """Create a data aggregator instance"""
    return DataAggregator()


async def quick_group_by(data: List[Dict[str, Any]], 
                        group_columns: List[str],
                        agg_functions: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Quick grouping operation"""
    try:
        aggregator = create_data_aggregator()
        
        # Convert string agg functions to enum
        agg_enum_functions = {}
        if agg_functions:
            for col, func_str in agg_functions.items():
                try:
                    agg_enum_functions[col] = AggregationFunction(func_str)
                except ValueError:
                    agg_enum_functions[col] = AggregationFunction.SUM  # Default
        
        config = TransformConfig(
            transformation_type=TransformationType.AGGREGATE,
            group_by_columns=group_columns,
            aggregation_functions=agg_enum_functions
        )
        
        result = await aggregator.transform_data(data, config)
        return result.transformed_data if result.success else data
        
    except Exception as e:
        logger.error(f"Quick group by failed: {e}")
        return data


async def quick_top_n(data: List[Dict[str, Any]], 
                     n: int = 10,
                     sort_column: Optional[str] = None,
                     ascending: bool = False) -> List[Dict[str, Any]]:
    """Quick top N operation"""
    try:
        aggregator = create_data_aggregator()
        
        config = TransformConfig(
            transformation_type=TransformationType.TOP_N,
            custom_params={
                'n': n,
                'sort_column': sort_column,
                'ascending': ascending
            }
        )
        
        result = await aggregator.transform_data(data, config)
        return result.transformed_data if result.success else data
        
    except Exception as e:
        logger.error(f"Quick top N failed: {e}")
        return data