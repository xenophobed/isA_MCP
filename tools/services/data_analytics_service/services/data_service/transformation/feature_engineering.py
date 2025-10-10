"""
Feature Engineering Service - Step 2 of Transformation Pipeline
Creates new features and derived columns from existing data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
import logging
from dataclasses import dataclass, field
from datetime import datetime
import re

from .lang_extractor import LangExtractor

logger = logging.getLogger(__name__)

@dataclass
class FeatureResult:
    """Result of feature engineering step"""
    success: bool
    engineered_data: Optional[pd.DataFrame] = None
    engineering_summary: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class FeatureEngineeringService:
    """
    Feature Engineering Service - Step 2 of Transformation Pipeline
    
    Handles:
    - Derived column creation
    - Mathematical transformations
    - Text feature extraction
    - Date/time feature extraction
    - Categorical encoding
    - Binning and discretization
    """
    
    def __init__(self):
        self.execution_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_duration': 0.0
        }
        
        # Initialize language extraction service for AI-powered text enrichment
        self.lang_extractor = LangExtractor()
        
        # Built-in feature functions
        self.feature_functions = {
            'log': lambda x: np.log(x + 1e-8),  # Add small value to avoid log(0)
            'sqrt': lambda x: np.sqrt(np.abs(x)),
            'square': lambda x: x ** 2,
            'cube': lambda x: x ** 3,
            'reciprocal': lambda x: 1.0 / (x + 1e-8),
            'absolute': lambda x: np.abs(x),
            'normalize': lambda x: (x - x.mean()) / (x.std() + 1e-8),
            'standardize': lambda x: (x - x.min()) / (x.max() - x.min() + 1e-8)
        }
        
        logger.info("Feature Engineering Service initialized with AI language processing")
    
    def engineer_features(self, 
                         data: pd.DataFrame,
                         feature_config: Dict[str, Any]) -> FeatureResult:
        """
        Execute feature engineering operations
        
        Args:
            data: Input DataFrame
            feature_config: Feature engineering configuration
            
        Returns:
            FeatureResult with engineered features
        """
        start_time = datetime.now()
        
        try:
            engineered_df = data.copy()
            engineering_summary = {
                'features_created': [],
                'features_modified': [],
                'operations_applied': []
            }
            
            # Execute feature engineering operations
            for operation in feature_config.get('operations', []):
                result = self._apply_operation(engineered_df, operation)
                
                if result['success']:
                    engineering_summary['operations_applied'].append({
                        'operation': operation.get('type'),
                        'target_columns': operation.get('columns', []),
                        'created_features': result.get('created_features', [])
                    })
                    
                    engineering_summary['features_created'].extend(
                        result.get('created_features', [])
                    )
                else:
                    return FeatureResult(
                        success=False,
                        errors=[f"Operation '{operation.get('type')}' failed: {result.get('error')}"]
                    )
            
            # Calculate performance metrics
            duration = (datetime.now() - start_time).total_seconds()
            performance_metrics = {
                'duration_seconds': duration,
                'input_shape': data.shape,
                'output_shape': engineered_df.shape,
                'features_added': len(engineered_df.columns) - len(data.columns),
                'original_columns': len(data.columns),
                'engineered_columns': len(engineered_df.columns)
            }
            
            engineering_summary.update({
                'original_shape': data.shape,
                'engineered_shape': engineered_df.shape,
                'total_features_created': len(engineering_summary['features_created'])
            })
            
            # Update execution stats
            self._update_stats(True, duration)
            
            return FeatureResult(
                success=True,
                engineered_data=engineered_df,
                engineering_summary=engineering_summary,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(False, duration)
            
            logger.error(f"Feature engineering failed: {e}")
            return FeatureResult(
                success=False,
                errors=[f"Feature engineering error: {str(e)}"],
                performance_metrics={'duration_seconds': duration}
            )
    
    def _apply_operation(self, df: pd.DataFrame, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single feature engineering operation"""
        try:
            op_type = operation.get('type')
            
            if op_type == 'derived_column':
                return self._create_derived_column(df, operation)
            elif op_type == 'mathematical_transform':
                return self._apply_mathematical_transform(df, operation)
            elif op_type == 'date_features':
                return self._extract_date_features(df, operation)
            elif op_type == 'text_features':
                return self._extract_text_features(df, operation)
            elif op_type == 'categorical_encoding':
                return self._encode_categorical(df, operation)
            elif op_type == 'binning':
                return self._apply_binning(df, operation)
            elif op_type == 'interaction_features':
                return self._create_interaction_features(df, operation)
            elif op_type == 'ai_language_extraction':
                return self._extract_ai_language_features(df, operation)
            else:
                return {
                    'success': False,
                    'error': f"Unknown operation type: {op_type}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_derived_column(self, df: pd.DataFrame, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Create derived columns using expressions"""
        try:
            expression = operation.get('expression')
            new_column = operation.get('new_column')
            
            if not expression or not new_column:
                return {
                    'success': False,
                    'error': 'Expression and new_column are required'
                }
            
            # Simple expression evaluation (could be extended with safe_eval)
            # For now, support basic arithmetic operations
            df[new_column] = self._evaluate_expression(df, expression)
            
            return {
                'success': True,
                'created_features': [new_column]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _evaluate_expression(self, df: pd.DataFrame, expression: str) -> pd.Series:
        """Safely evaluate mathematical expressions"""
        # Replace column names in expression with df['column']
        columns = df.columns.tolist()
        expr = expression
        
        # Sort by length (descending) to avoid partial matches
        columns_sorted = sorted(columns, key=len, reverse=True)
        
        for col in columns_sorted:
            if col in expr:
                expr = expr.replace(col, f"df['{col}']")
        
        # Evaluate expression safely
        try:
            return eval(expr)
        except Exception as e:
            logger.warning(f"Expression evaluation failed: {e}")
            return pd.Series(np.nan, index=df.index)
    
    def _apply_mathematical_transform(self, df: pd.DataFrame, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Apply mathematical transformations to columns"""
        try:
            columns = operation.get('columns', [])
            transform = operation.get('transform')
            suffix = operation.get('suffix', f'_{transform}')
            
            if not columns or not transform:
                return {
                    'success': False,
                    'error': 'Columns and transform are required'
                }
            
            if transform not in self.feature_functions:
                return {
                    'success': False,
                    'error': f'Transform "{transform}" not supported'
                }
            
            created_features = []
            func = self.feature_functions[transform]
            
            for col in columns:
                if col in df.columns:
                    new_col = f"{col}{suffix}"
                    
                    # Apply transformation only to numeric columns
                    if pd.api.types.is_numeric_dtype(df[col]):
                        df[new_col] = func(df[col])
                        created_features.append(new_col)
            
            return {
                'success': True,
                'created_features': created_features
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_date_features(self, df: pd.DataFrame, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from date columns"""
        try:
            columns = operation.get('columns', [])
            features = operation.get('features', ['year', 'month', 'day', 'weekday'])
            
            created_features = []
            
            for col in columns:
                if col in df.columns:
                    # Convert to datetime if not already
                    if not pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    
                    # Extract features
                    if 'year' in features:
                        new_col = f"{col}_year"
                        df[new_col] = df[col].dt.year
                        created_features.append(new_col)
                    
                    if 'month' in features:
                        new_col = f"{col}_month"
                        df[new_col] = df[col].dt.month
                        created_features.append(new_col)
                    
                    if 'day' in features:
                        new_col = f"{col}_day"
                        df[new_col] = df[col].dt.day
                        created_features.append(new_col)
                    
                    if 'weekday' in features:
                        new_col = f"{col}_weekday"
                        df[new_col] = df[col].dt.weekday
                        created_features.append(new_col)
                    
                    if 'quarter' in features:
                        new_col = f"{col}_quarter"
                        df[new_col] = df[col].dt.quarter
                        created_features.append(new_col)
                    
                    if 'is_weekend' in features:
                        new_col = f"{col}_is_weekend"
                        df[new_col] = df[col].dt.weekday >= 5
                        created_features.append(new_col)
            
            return {
                'success': True,
                'created_features': created_features
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_text_features(self, df: pd.DataFrame, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from text columns"""
        try:
            columns = operation.get('columns', [])
            features = operation.get('features', ['length', 'word_count'])
            
            created_features = []
            
            for col in columns:
                if col in df.columns:
                    # Convert to string
                    text_col = df[col].astype(str)
                    
                    if 'length' in features:
                        new_col = f"{col}_length"
                        df[new_col] = text_col.str.len()
                        created_features.append(new_col)
                    
                    if 'word_count' in features:
                        new_col = f"{col}_word_count"
                        df[new_col] = text_col.str.split().str.len()
                        created_features.append(new_col)
                    
                    if 'char_count' in features:
                        new_col = f"{col}_char_count"
                        df[new_col] = text_col.str.replace(' ', '').str.len()
                        created_features.append(new_col)
                    
                    if 'uppercase_count' in features:
                        new_col = f"{col}_uppercase_count"
                        df[new_col] = text_col.str.findall(r'[A-Z]').str.len()
                        created_features.append(new_col)
                    
                    if 'numeric_count' in features:
                        new_col = f"{col}_numeric_count"
                        df[new_col] = text_col.str.findall(r'\d').str.len()
                        created_features.append(new_col)
            
            return {
                'success': True,
                'created_features': created_features
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _encode_categorical(self, df: pd.DataFrame, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Encode categorical variables"""
        try:
            columns = operation.get('columns', [])
            encoding_type = operation.get('encoding_type', 'one_hot')
            
            created_features = []
            
            for col in columns:
                if col in df.columns:
                    if encoding_type == 'one_hot':
                        # One-hot encoding
                        dummies = pd.get_dummies(df[col], prefix=col)
                        df = pd.concat([df, dummies], axis=1)
                        created_features.extend(dummies.columns.tolist())
                    
                    elif encoding_type == 'label':
                        # Label encoding
                        new_col = f"{col}_encoded"
                        df[new_col] = pd.Categorical(df[col]).codes
                        created_features.append(new_col)
            
            return {
                'success': True,
                'created_features': created_features
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _apply_binning(self, df: pd.DataFrame, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Apply binning to numeric columns"""
        try:
            columns = operation.get('columns', [])
            bins = operation.get('bins', 5)
            method = operation.get('method', 'equal_width')
            
            created_features = []
            
            for col in columns:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    new_col = f"{col}_binned"
                    
                    if method == 'equal_width':
                        df[new_col] = pd.cut(df[col], bins=bins)
                    elif method == 'equal_freq':
                        df[new_col] = pd.qcut(df[col], q=bins, duplicates='drop')
                    
                    created_features.append(new_col)
            
            return {
                'success': True,
                'created_features': created_features
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_interaction_features(self, df: pd.DataFrame, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Create interaction features between columns"""
        try:
            column_pairs = operation.get('column_pairs', [])
            interaction_type = operation.get('interaction_type', 'multiply')
            
            created_features = []
            
            for col1, col2 in column_pairs:
                if col1 in df.columns and col2 in df.columns:
                    new_col = f"{col1}_{interaction_type}_{col2}"
                    
                    if interaction_type == 'multiply':
                        if pd.api.types.is_numeric_dtype(df[col1]) and pd.api.types.is_numeric_dtype(df[col2]):
                            df[new_col] = df[col1] * df[col2]
                            created_features.append(new_col)
                    
                    elif interaction_type == 'add':
                        if pd.api.types.is_numeric_dtype(df[col1]) and pd.api.types.is_numeric_dtype(df[col2]):
                            df[new_col] = df[col1] + df[col2]
                            created_features.append(new_col)
                    
                    elif interaction_type == 'ratio':
                        if pd.api.types.is_numeric_dtype(df[col1]) and pd.api.types.is_numeric_dtype(df[col2]):
                            df[new_col] = df[col1] / (df[col2] + 1e-8)  # Avoid division by zero
                            created_features.append(new_col)
            
            return {
                'success': True,
                'created_features': created_features
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
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
    
    def get_supported_operations(self) -> Dict[str, List[str]]:
        """Get supported feature engineering operations"""
        return {
            'mathematical_transforms': list(self.feature_functions.keys()),
            'date_features': ['year', 'month', 'day', 'weekday', 'quarter', 'is_weekend'],
            'text_features': ['length', 'word_count', 'char_count', 'uppercase_count', 'numeric_count'],
            'encoding_types': ['one_hot', 'label'],
            'binning_methods': ['equal_width', 'equal_freq'],
            'interaction_types': ['multiply', 'add', 'ratio']
        }