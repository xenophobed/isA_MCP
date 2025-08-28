#!/usr/bin/env python3
"""
Data Cleaning Service - Step 3 of Preprocessing Pipeline
Handles data cleaning and standardization using processors
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd

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
    
    def clean_dataframe(self, df: pd.DataFrame, 
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
            logger.info(f"Cleaning DataFrame: {df.shape[0]} rows, {df.shape[1]} columns")
            
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
            
            original_shape = df.shape
            cleaning_log = []
            
            # Step 3.1: Standardize column names using processor
            if default_options['standardize_columns']:
                standardized_df, column_mapping = self.column_standardizer.standardize_columns(
                    df, target_hint=target_hint
                )
                cleaning_log.append(f"Standardized {len([k for k, v in column_mapping.items() if k != v])} column names")
            else:
                standardized_df = df.copy()
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
            final_shape = standardized_df.shape
            
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
    
    def _handle_missing_values(self, df: pd.DataFrame, validation_results: Dict[str, Any], 
                              null_threshold: float) -> Tuple[pd.DataFrame, List[str]]:
        """Handle missing values in DataFrame"""
        result_df = df.copy()
        log = []
        
        try:
            # Get quality assessment from validation results
            quality_assessment = validation_results.get('quality_assessment', {})
            column_quality = quality_assessment.get('column_quality', {})
            
            # Strategy 1: Drop columns with excessive nulls
            columns_to_drop = []
            for col in result_df.columns:
                null_percentage = result_df[col].isnull().sum() / len(result_df)
                if null_percentage > null_threshold:
                    columns_to_drop.append(col)
            
            if columns_to_drop:
                result_df = result_df.drop(columns=columns_to_drop)
                log.append(f"Dropped {len(columns_to_drop)} columns with >{null_threshold*100}% nulls: {columns_to_drop}")
            
            # Strategy 2: Handle remaining nulls by column type
            for col in result_df.columns:
                if result_df[col].isnull().any():
                    col_dtype = result_df[col].dtype
                    null_count = result_df[col].isnull().sum()
                    
                    if pd.api.types.is_numeric_dtype(col_dtype):
                        # For numeric: fill with median
                        median_val = result_df[col].median()
                        result_df[col] = result_df[col].fillna(median_val)
                        log.append(f"Filled {null_count} nulls in '{col}' with median: {median_val}")
                    
                    elif pd.api.types.is_categorical_dtype(col_dtype) or result_df[col].nunique() < 20:
                        # For categorical: fill with mode
                        mode_val = result_df[col].mode()
                        if len(mode_val) > 0:
                            result_df[col] = result_df[col].fillna(mode_val[0])
                            log.append(f"Filled {null_count} nulls in '{col}' with mode: {mode_val[0]}")
                        else:
                            result_df[col] = result_df[col].fillna('Unknown')
                            log.append(f"Filled {null_count} nulls in '{col}' with 'Unknown'")
                    
                    else:
                        # For text: fill with 'Unknown' or forward fill
                        if null_count / len(result_df) < 0.1:  # Low null percentage
                            result_df[col] = result_df[col].fillna(method='ffill').fillna('Unknown')
                            log.append(f"Forward filled {null_count} nulls in '{col}'")
                        else:
                            result_df[col] = result_df[col].fillna('Unknown')
                            log.append(f"Filled {null_count} nulls in '{col}' with 'Unknown'")
        
        except Exception as e:
            log.append(f"Error in null handling: {str(e)}")
        
        return result_df, log
    
    def _handle_duplicates(self, df: pd.DataFrame, duplicate_threshold: float) -> Tuple[pd.DataFrame, List[str]]:
        """Handle duplicate rows in DataFrame"""
        result_df = df.copy()
        log = []
        
        try:
            duplicate_count = result_df.duplicated().sum()
            duplicate_percentage = duplicate_count / len(result_df)
            
            if duplicate_percentage > 0:
                if duplicate_percentage >= duplicate_threshold:
                    log.append(f"Warning: High duplicate percentage ({duplicate_percentage:.1%}), keeping only unique rows")
                
                result_df = result_df.drop_duplicates()
                log.append(f"Removed {duplicate_count} duplicate rows ({duplicate_percentage:.1%})")
        
        except Exception as e:
            log.append(f"Error in duplicate handling: {str(e)}")
        
        return result_df, log
    
    def _apply_type_conversions(self, df: pd.DataFrame, validation_results: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str]]:
        """Apply recommended data type conversions"""
        result_df = df.copy()
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
                current_type = str(result_df[col_name].dtype)
                
                # Only convert if confidence is high and types are different
                if confidence > 0.8 and suggested_type != current_type:
                    try:
                        if suggested_type == 'datetime':
                            result_df[col_name] = pd.to_datetime(result_df[col_name], errors='coerce')
                            log.append(f"Converted '{col_name}' to datetime")
                        
                        elif suggested_type == 'int64':
                            # Clean numeric data first
                            cleaned = result_df[col_name].astype(str).str.replace(r'[$��,\s]', '', regex=True)
                            result_df[col_name] = pd.to_numeric(cleaned, errors='coerce').astype('Int64')
                            log.append(f"Converted '{col_name}' to integer")
                        
                        elif suggested_type == 'float64':
                            cleaned = result_df[col_name].astype(str).str.replace(r'[$��,\s]', '', regex=True)
                            result_df[col_name] = pd.to_numeric(cleaned, errors='coerce')
                            log.append(f"Converted '{col_name}' to float")
                        
                        elif suggested_type == 'bool':
                            bool_map = {'true': True, 'false': False, 'yes': True, 'no': False, 
                                      '1': True, '0': False, 'y': True, 'n': False}
                            result_df[col_name] = result_df[col_name].astype(str).str.lower().map(bool_map)
                            log.append(f"Converted '{col_name}' to boolean")
                        
                        elif suggested_type == 'category':
                            result_df[col_name] = result_df[col_name].astype('category')
                            log.append(f"Converted '{col_name}' to category")
                            
                    except Exception as e:
                        log.append(f"Failed to convert '{col_name}' to {suggested_type}: {str(e)}")
        
        except Exception as e:
            log.append(f"Error in type conversion: {str(e)}")
        
        return result_df, log
    
    def _final_cleanup(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Final cleanup and optimization"""
        result_df = df.copy()
        log = []
        
        try:
            # Clean string columns
            string_columns = result_df.select_dtypes(include=['object']).columns
            for col in string_columns:
                if result_df[col].dtype == 'object':
                    # Strip whitespace
                    original_unique = result_df[col].nunique()
                    result_df[col] = result_df[col].astype(str).str.strip()
                    new_unique = result_df[col].nunique()
                    
                    if original_unique != new_unique:
                        log.append(f"Cleaned whitespace in '{col}': {original_unique} � {new_unique} unique values")
            
            # Optimize memory usage
            original_memory = result_df.memory_usage(deep=True).sum() / (1024 * 1024)
            
            # Convert appropriate int64 to smaller types
            for col in result_df.select_dtypes(include=['int64']).columns:
                col_min = result_df[col].min()
                col_max = result_df[col].max()
                
                if pd.isna(col_min) or pd.isna(col_max):
                    continue
                
                if col_min >= 0 and col_max < 255:
                    result_df[col] = result_df[col].astype('uint8')
                elif col_min >= -128 and col_max < 127:
                    result_df[col] = result_df[col].astype('int8')
                elif col_min >= 0 and col_max < 65535:
                    result_df[col] = result_df[col].astype('uint16')
                elif col_min >= -32768 and col_max < 32767:
                    result_df[col] = result_df[col].astype('int16')
                elif col_min >= 0 and col_max < 4294967295:
                    result_df[col] = result_df[col].astype('uint32')
                elif col_min >= -2147483648 and col_max < 2147483647:
                    result_df[col] = result_df[col].astype('int32')
            
            new_memory = result_df.memory_usage(deep=True).sum() / (1024 * 1024)
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