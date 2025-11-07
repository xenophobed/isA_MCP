#!/usr/bin/env python3
"""
Data Cleaning Service - Step 3 of Preprocessing Pipeline
Handles data cleaning and standardization using processors
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import polars as pl

# Import processors for data cleaning
from ....processors.data_processors.preprocessors.cleaning.column_standardizer import ColumnStandardizer

logger = logging.getLogger(__name__)

class DataCleaningService:
    """
    Step 3: Data Cleaning & Standardization Service
    
    Uses:
    - ColumnStandardizer processor for column name standardization
    
    Responsibilities:
    - Clean and standardize column names
    - Handle missing values
    - Remove duplicates
    - Apply data type conversions
    - Prepare clean, analysis-ready data
    """
    
    def __init__(self):
        self.column_standardizer = ColumnStandardizer()
        self.service_name = "DataCleaningService"
        
        logger.info("Data Cleaning Service initialized")
    
    def clean_dataframe(self, df: pl.DataFrame,
                       validation_results: Dict[str, Any],
                       target_hint: Optional[str] = None,
                       cleaning_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive DataFrame cleaning
        
        Args:
            df: DataFrame to clean
            validation_results: Results from validation service
            target_hint: Optional target column hint
            cleaning_options: Optional cleaning configuration
            
        Returns:
            Dict containing cleaning results
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Cleaning DataFrame: {df.height} rows, {df.width} columns")
            
            # Default cleaning options
            options = cleaning_options or {}
            default_options = {
                'handle_nulls': True,
                'remove_duplicates': True,
                'standardize_columns': True,
                'convert_types': True,
                'null_threshold': 0.5,  # Drop columns with >50% nulls
                'duplicate_threshold': 0.9  # Remove duplicates if >90% are duplicates
            }
            default_options.update(options)

            original_shape = (df.height, df.width)
            cleaning_log = []

            # Step 3.1: Standardize column names using processor
            if default_options['standardize_columns']:
                standardized_df, column_mapping = self.column_standardizer.standardize_columns(
                    df, target_hint=target_hint
                )
                cleaning_log.append(f"Standardized {len([k for k, v in column_mapping.items() if k != v])} column names")
            else:
                standardized_df = df.clone()
                column_mapping = {col: col for col in df.columns}
            
            # Step 3.2: Handle missing values
            if default_options['handle_nulls']:
                standardized_df, null_handling_log = self._handle_missing_values(
                    standardized_df, validation_results, default_options['null_threshold']
                )
                cleaning_log.extend(null_handling_log)
            
            # Step 3.3: Remove duplicates
            if default_options['remove_duplicates']:
                standardized_df, duplicate_log = self._handle_duplicates(
                    standardized_df, default_options['duplicate_threshold']
                )
                cleaning_log.extend(duplicate_log)
            
            # Step 3.4: Apply data type conversions
            if default_options['convert_types']:
                standardized_df, conversion_log = self._apply_type_conversions(
                    standardized_df, validation_results
                )
                cleaning_log.extend(conversion_log)
            
            # Step 3.5: Final validation and cleanup
            standardized_df, final_cleanup_log = self._final_cleanup(standardized_df)
            cleaning_log.extend(final_cleanup_log)
            
            # Calculate cleaning time
            cleaning_duration = (datetime.now() - start_time).total_seconds()
            final_shape = (standardized_df.height, standardized_df.width)
            
            # Generate cleaning summary
            cleaning_summary = self._generate_cleaning_summary(
                original_shape, final_shape, cleaning_log, column_mapping
            )
            
            result = {
                'success': True,
                'original_shape': original_shape,
                'final_shape': final_shape,
                'cleaned_dataframe': standardized_df,
                'column_mapping': column_mapping,
                'cleaning_duration': cleaning_duration,
                'cleaning_log': cleaning_log,
                'cleaning_summary': cleaning_summary,
                'cleaning_options_used': default_options
            }
            
            logger.info(f"Cleaning completed: {original_shape} -> {final_shape} in {cleaning_duration:.2f}s")
            return result
            
        except Exception as e:
            cleaning_duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Data cleaning failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'cleaning_duration': cleaning_duration,
                'step': 'general_error'
            }
    
    def _handle_missing_values(self, df: pl.DataFrame, validation_results: Dict[str, Any],
                              null_threshold: float) -> Tuple[pl.DataFrame, List[str]]:
        """Handle missing values in DataFrame"""
        result_df = df.clone()
        log = []

        try:
            # Get quality assessment from validation results
            quality_assessment = validation_results.get('quality_assessment', {})
            column_quality = quality_assessment.get('column_quality', {})

            # Strategy 1: Drop columns with excessive nulls
            columns_to_drop = []
            for col in result_df.columns:
                null_percentage = result_df.get_column(col).null_count() / result_df.height
                if null_percentage > null_threshold:
                    columns_to_drop.append(col)

            if columns_to_drop:
                result_df = result_df.drop(columns_to_drop)
                log.append(f"Dropped {len(columns_to_drop)} columns with >{null_threshold*100}% nulls: {columns_to_drop}")
            
            # Strategy 2: Handle remaining nulls by column type
            for col in result_df.columns:
                col_series = result_df.get_column(col)
                if col_series.null_count() > 0:
                    col_dtype = col_series.dtype
                    null_count = col_series.null_count()

                    # Check if numeric type
                    if col_dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64, pl.Float32, pl.Float64]:
                        # For numeric: fill with median
                        median_val = col_series.median()
                        result_df = result_df.with_columns(pl.col(col).fill_null(median_val))
                        log.append(f"Filled {null_count} nulls in '{col}' with median: {median_val}")

                    elif col_dtype == pl.Categorical or col_series.n_unique() < 20:
                        # For categorical: fill with mode
                        mode_series = col_series.drop_nulls().mode()
                        if mode_series.len() > 0:
                            mode_val = mode_series[0]
                            result_df = result_df.with_columns(pl.col(col).fill_null(mode_val))
                            log.append(f"Filled {null_count} nulls in '{col}' with mode: {mode_val}")
                        else:
                            result_df = result_df.with_columns(pl.col(col).fill_null('Unknown'))
                            log.append(f"Filled {null_count} nulls in '{col}' with 'Unknown'")

                    else:
                        # For text: fill with 'Unknown' or forward fill
                        if null_count / result_df.height < 0.1:  # Low null percentage
                            result_df = result_df.with_columns(pl.col(col).forward_fill().fill_null('Unknown'))
                            log.append(f"Forward filled {null_count} nulls in '{col}'")
                        else:
                            result_df = result_df.with_columns(pl.col(col).fill_null('Unknown'))
                            log.append(f"Filled {null_count} nulls in '{col}' with 'Unknown'")
        
        except Exception as e:
            log.append(f"Error in null handling: {str(e)}")
        
        return result_df, log
    
    def _handle_duplicates(self, df: pl.DataFrame, duplicate_threshold: float) -> Tuple[pl.DataFrame, List[str]]:
        """Handle duplicate rows in DataFrame"""
        result_df = df.clone()
        log = []

        try:
            duplicate_count = result_df.is_duplicated().sum()
            duplicate_percentage = duplicate_count / result_df.height

            if duplicate_percentage > 0:
                if duplicate_percentage >= duplicate_threshold:
                    log.append(f"Warning: High duplicate percentage ({duplicate_percentage:.1%}), keeping only unique rows")

                result_df = result_df.unique()
                log.append(f"Removed {duplicate_count} duplicate rows ({duplicate_percentage:.1%})")
        
        except Exception as e:
            log.append(f"Error in duplicate handling: {str(e)}")
        
        return result_df, log
    
    def _apply_type_conversions(self, df: pl.DataFrame, validation_results: Dict[str, Any]) -> Tuple[pl.DataFrame, List[str]]:
        """Apply recommended data type conversions"""
        result_df = df.clone()
        log = []
        
        try:
            # Get type analysis from validation results
            type_analysis = validation_results.get('type_analysis', {})
            column_analysis = type_analysis.get('column_analysis', {})
            
            for col_name, analysis in column_analysis.items():
                if col_name not in result_df.columns:
                    continue
                
                suggested_type = analysis.get('suggested_type')
                confidence = analysis.get('confidence', 0)
                current_type = str(result_df.get_column(col_name).dtype)
                
                # Only convert if confidence is high and types are different
                if confidence > 0.8 and suggested_type != current_type:
                    try:
                        if suggested_type == 'datetime':
                            result_df = result_df.with_columns(
                                pl.col(col_name).str.to_datetime(strict=False)
                            )
                            log.append(f"Converted '{col_name}' to datetime")
                        
                        elif suggested_type == 'int64':
                            # Clean numeric data first and convert
                            result_df = result_df.with_columns(
                                pl.col(col_name).cast(pl.Utf8).str.replace_all(r'[$��,\s]', '').cast(pl.Int64, strict=False)
                            )
                            log.append(f"Converted '{col_name}' to integer")
                        
                        elif suggested_type == 'float64':
                            result_df = result_df.with_columns(
                                pl.col(col_name).cast(pl.Utf8).str.replace_all(r'[$��,\s]', '').cast(pl.Float64, strict=False)
                            )
                            log.append(f"Converted '{col_name}' to float")
                        
                        elif suggested_type == 'bool':
                            # Map string values to boolean
                            result_df = result_df.with_columns(
                                pl.col(col_name).cast(pl.Utf8).str.to_lowercase().replace({
                                    'true': True, 'false': False, 'yes': True, 'no': False,
                                    '1': True, '0': False, 'y': True, 'n': False
                                })
                            )
                            log.append(f"Converted '{col_name}' to boolean")
                        
                        elif suggested_type == 'category':
                            result_df = result_df.with_columns(
                                pl.col(col_name).cast(pl.Categorical)
                            )
                            log.append(f"Converted '{col_name}' to category")
                            
                    except Exception as e:
                        log.append(f"Failed to convert '{col_name}' to {suggested_type}: {str(e)}")
        
        except Exception as e:
            log.append(f"Error in type conversion: {str(e)}")
        
        return result_df, log
    
    def _final_cleanup(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, List[str]]:
        """Final cleanup and optimization"""
        result_df = df.clone()
        log = []
        
        try:
            # Clean string columns
            string_columns = [col for col in result_df.columns if result_df.get_column(col).dtype == pl.Utf8]
            for col in string_columns:
                if result_df.get_column(col).dtype == pl.Utf8:
                    # Strip whitespace
                    original_unique = result_df.get_column(col).n_unique()
                    result_df = result_df.with_columns(pl.col(col).cast(pl.Utf8).str.strip_chars())
                    new_unique = result_df.get_column(col).n_unique()
                    
                    if original_unique != new_unique:
                        log.append(f"Cleaned whitespace in '{col}': {original_unique} � {new_unique} unique values")
            
            # Optimize memory usage
            original_memory = result_df.estimated_size('mb')
            
            # Convert appropriate int64 to smaller types
            for col in [c for c in result_df.columns if result_df.get_column(c).dtype == pl.Int64]:
                col_min = result_df.get_column(col).min()
                col_max = result_df.get_column(col).max()
                
                if col_min is None or col_max is None:
                    continue
                
                if col_min >= 0 and col_max < 255:
                    result_df = result_df.with_columns(pl.col(col).cast(pl.UInt8))
                elif col_min >= -128 and col_max < 127:
                    result_df = result_df.with_columns(pl.col(col).cast(pl.Int8))
                elif col_min >= 0 and col_max < 65535:
                    result_df = result_df.with_columns(pl.col(col).cast(pl.UInt16))
                elif col_min >= -32768 and col_max < 32767:
                    result_df = result_df.with_columns(pl.col(col).cast(pl.Int16))
                elif col_min >= 0 and col_max < 4294967295:
                    result_df = result_df.with_columns(pl.col(col).cast(pl.UInt32))
                elif col_min >= -2147483648 and col_max < 2147483647:
                    result_df = result_df.with_columns(pl.col(col).cast(pl.Int32))
            
            new_memory = result_df.estimated_size('mb')
            if original_memory != new_memory:
                log.append(f"Optimized memory usage: {original_memory:.1f}MB � {new_memory:.1f}MB")
        
        except Exception as e:
            log.append(f"Error in final cleanup: {str(e)}")
        
        return result_df, log
    
    def _generate_cleaning_summary(self, original_shape: Tuple[int, int], 
                                 final_shape: Tuple[int, int],
                                 cleaning_log: List[str],
                                 column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Generate comprehensive cleaning summary"""
        
        rows_removed = original_shape[0] - final_shape[0]
        columns_removed = original_shape[1] - final_shape[1]
        columns_renamed = len([k for k, v in column_mapping.items() if k != v])
        
        return {
            'data_shape_change': {
                'original': original_shape,
                'final': final_shape,
                'rows_removed': rows_removed,
                'columns_removed': columns_removed,
                'rows_retention_rate': final_shape[0] / original_shape[0] if original_shape[0] > 0 else 0,
                'columns_retention_rate': final_shape[1] / original_shape[1] if original_shape[1] > 0 else 0
            },
            'column_standardization': {
                'total_columns': len(column_mapping),
                'columns_renamed': columns_renamed,
                'column_mapping': column_mapping
            },
            'cleaning_operations': {
                'total_operations': len(cleaning_log),
                'operations_log': cleaning_log
            },
            'data_ready_for_analysis': final_shape[0] > 0 and final_shape[1] > 0,
            'quality_improvement': {
                'shape_optimized': rows_removed >= 0 and columns_removed >= 0,
                'columns_standardized': columns_renamed > 0,
                'operations_successful': len([log for log in cleaning_log if 'error' not in log.lower()])
            }
        }