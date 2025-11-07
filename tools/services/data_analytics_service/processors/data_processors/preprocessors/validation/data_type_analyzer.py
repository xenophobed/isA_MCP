#!/usr/bin/env python3
"""
Data Type Analysis Processor
Analyzes and infers proper data types for columns
"""

import polars as pl
# import numpy as np  # Not needed with Polars
from typing import Dict, List, Any, Optional, Tuple
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DataTypeAnalyzer:
    """Analyzes data types and suggests conversions"""
    
    def __init__(self):
        self.date_patterns = [
            r'\d{4}-\d{2}-\d{2}',                    # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',                    # MM/DD/YYYY
            r'\d{4}/\d{2}/\d{2}',                    # YYYY/MM/DD
            r'\d{2}-\d{2}-\d{4}',                    # MM-DD-YYYY
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # YYYY-MM-DD HH:MM:SS
        ]
        
        self.numeric_patterns = [
            r'^-?\d+$',                              # Integer
            r'^-?\d+\.\d+$',                         # Float
            r'^-?\d{1,3}(,\d{3})*$',                 # Integer with commas
            r'^-?\d{1,3}(,\d{3})*\.\d+$',           # Float with commas
        ]
        
        self.currency_patterns = [
            r'^\$\d+\.?\d*$',                        # $123.45
            r'^¥\d+\.?\d*$',                         # ¥123.45
            r'^€\d+\.?\d*$',                         # €123.45
            r'^\d+\.?\d*\s?(USD|EUR|GBP|JPY)$',      # 123.45 USD
        ]
    
    def analyze_dataframe(self, df: pl.DataFrame) -> Dict[str, Any]:
        """
        Analyze data types for entire DataFrame
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dict with analysis results
        """
        try:
            analysis_result = {
                'success': True,
                'total_columns': df.width,
                'total_rows': df.height,
                'column_analysis': {},
                'type_summary': {},
                'recommendations': []
            }
            
            # Analyze each column
            for column in df.columns:
                column_analysis = self._analyze_column(df.get_column(column), str(column))
                analysis_result['column_analysis'][str(column)] = column_analysis
            
            # Create type summary
            type_counts = {}
            for col_analysis in analysis_result['column_analysis'].values():
                suggested_type = col_analysis['suggested_type']
                type_counts[suggested_type] = type_counts.get(suggested_type, 0) + 1
            
            analysis_result['type_summary'] = type_counts
            
            # Generate recommendations
            analysis_result['recommendations'] = self._generate_recommendations(
                analysis_result['column_analysis']
            )
            
            return analysis_result
            
        except Exception as e:
            import traceback
            logger.error(f"DataFrame analysis failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_column(self, series: pl.Series, column_name: str) -> Dict[str, Any]:
        """Analyze a single column"""
        
        # Basic statistics
        total_count = series.len()
        null_count = series.null_count()
        non_null_series = series.drop_nulls()
        unique_count = non_null_series.n_unique()
        
        analysis = {
            'column_name': column_name,
            'current_type': str(series.dtype),
            'total_count': total_count,
            'null_count': null_count,
            'null_percentage': null_count / total_count if total_count > 0 else 0,
            'unique_count': unique_count,
            'unique_percentage': unique_count / non_null_series.len() if non_null_series.len() > 0 else 0,
            'sample_values': non_null_series.head(5).to_list() if non_null_series.len() > 0 else [],
            'suggested_type': 'object',
            'confidence': 0.0,
            'conversion_possible': False,
            'issues': []
        }
        
        if non_null_series.len() == 0:
            analysis['suggested_type'] = 'object'
            analysis['issues'].append('All values are null')
            return analysis
        
        # Analyze data type patterns
        type_scores = self._score_data_types(non_null_series)
        
        # Select best type
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            analysis['suggested_type'] = best_type
            analysis['confidence'] = type_scores[best_type]
            analysis['conversion_possible'] = type_scores[best_type] > 0.7
        
        # Add specific analysis for suggested type
        if analysis['suggested_type'] == 'datetime':
            analysis['datetime_info'] = self._analyze_datetime_column(non_null_series)
        elif analysis['suggested_type'] in ['int64', 'float64']:
            analysis['numeric_info'] = self._analyze_numeric_column(non_null_series)
        elif analysis['suggested_type'] == 'category':
            analysis['category_info'] = self._analyze_categorical_column(non_null_series)
        
        return analysis
    
    def _score_data_types(self, series: pl.Series) -> Dict[str, float]:
        """Score how well the series fits different data types"""
        scores = {}
        
        # Convert to string for pattern matching
        str_series = series.cast(pl.Utf8)
        
        # Score datetime
        datetime_score = self._score_datetime(str_series)
        if datetime_score > 0:
            scores['datetime'] = datetime_score
        
        # Score numeric types
        numeric_score = self._score_numeric(str_series)
        if numeric_score > 0:
            # Determine if int or float
            if self._is_integer_like(str_series):
                scores['int64'] = numeric_score
            else:
                scores['float64'] = numeric_score
        
        # Score boolean
        boolean_score = self._score_boolean(str_series)
        if boolean_score > 0:
            scores['bool'] = boolean_score
        
        # Score categorical
        categorical_score = self._score_categorical(series)
        if categorical_score > 0:
            scores['category'] = categorical_score
        
        # Default to object
        scores['object'] = 0.1
        
        return scores
    
    def _score_datetime(self, str_series: pl.Series) -> float:
        """Score how likely the series is datetime"""
        matches = 0
        total = len(str_series)
        
        for value in str_series:
            for pattern in self.date_patterns:
                if re.search(pattern, str(value)):
                    matches += 1
                    break
        
        return matches / total if total > 0 else 0
    
    def _score_numeric(self, str_series: pl.Series) -> float:
        """Score how likely the series is numeric"""
        matches = 0
        total = len(str_series)
        
        for value in str_series:
            # Remove currency symbols and commas for testing
            clean_value = re.sub(r'[$¥€,\s]', '', str(value))
            
            try:
                float(clean_value)
                matches += 1
            except ValueError:
                # Check patterns
                for pattern in self.numeric_patterns:
                    if re.match(pattern, str(value)):
                        matches += 1
                        break
        
        return matches / total if total > 0 else 0
    
    def _score_boolean(self, str_series: pl.Series) -> float:
        """Score how likely the series is boolean"""
        boolean_values = {'true', 'false', 'yes', 'no', '1', '0', 'y', 'n', 
                         'True', 'False', 'YES', 'NO', 'Y', 'N'}
        
        matches = sum(1 for value in str_series if str(value).strip() in boolean_values)
        total = len(str_series)
        
        return matches / total if total > 0 else 0
    
    def _score_categorical(self, series: pl.Series) -> float:
        """Score how likely the series is categorical"""
        unique_ratio = series.n_unique() / series.len() if series.len() > 0 else 0

        # High uniqueness suggests not categorical
        if unique_ratio > 0.5:
            return 0

        # Low uniqueness with reasonable number of categories
        if unique_ratio < 0.1 and series.n_unique() < 50:
            return 0.8
        elif unique_ratio < 0.3 and series.n_unique() < 20:
            return 0.6

        return 0
    
    def _is_integer_like(self, str_series: pl.Series) -> bool:
        """Check if numeric series represents integers"""
        try:
            for value in str_series.head(10):  # Check first 10 values
                clean_value = re.sub(r'[$¥€,\s]', '', str(value))
                float_val = float(clean_value)
                if float_val != int(float_val):
                    return False
            return True
        except:
            return False
    
    def _analyze_datetime_column(self, series: pl.Series) -> Dict[str, Any]:
        """Analyze datetime-specific properties"""
        try:
            # Try to convert and analyze using polars
            try:
                dt_series = series.str.strptime(pl.Datetime, format="%Y-%m-%d", strict=False)
            except:
                # Try multiple formats
                dt_series = None
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        dt_series = series.str.strptime(pl.Datetime, format=fmt, strict=False)
                        break
                    except:
                        continue

            if dt_series is None:
                return {'error': 'No valid dates found'}

            valid_dates = dt_series.drop_nulls()

            if valid_dates.len() == 0:
                return {'error': 'No valid dates found'}

            return {
                'date_range': {
                    'min': str(valid_dates.min()),
                    'max': str(valid_dates.max())
                },
                'valid_dates': valid_dates.len(),
                'invalid_dates': series.len() - valid_dates.len(),
                'common_format': self._detect_date_format(series)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_numeric_column(self, series: pl.Series) -> Dict[str, Any]:
        """Analyze numeric-specific properties"""
        try:
            # Convert to numeric using polars
            numeric_series = (
                series.cast(pl.Utf8)
                .str.replace_all(r'[$¥€,\s]', '')
                .cast(pl.Float64, strict=False)
            )
            valid_numbers = numeric_series.drop_nulls()

            if valid_numbers.len() == 0:
                return {'error': 'No valid numbers found'}

            return {
                'range': {
                    'min': float(valid_numbers.min()),
                    'max': float(valid_numbers.max()),
                    'mean': float(valid_numbers.mean()),
                    'std': float(valid_numbers.std())
                },
                'valid_numbers': valid_numbers.len(),
                'invalid_numbers': series.len() - valid_numbers.len(),
                'has_currency_symbols': any('$' in str(val) or '¥' in str(val) or '€' in str(val) 
                                          for val in series.head(10))
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_categorical_column(self, series: pl.Series) -> Dict[str, Any]:
        """Analyze categorical-specific properties"""
        value_counts = series.value_counts()

        # Get the counts column for distribution analysis (polars value_counts returns DataFrame)
        counts_col = value_counts.get_column('count') if 'count' in value_counts.columns else value_counts.get_column(value_counts.columns[1])
        count_std = float(counts_col.std()) if counts_col.len() > 1 else 0.0
        count_mean = float(counts_col.mean())

        return {
            'unique_values': len(value_counts),
            'most_common': value_counts.head(5).to_dicts(),
            'least_common': value_counts.tail(5).to_dicts(),
            'distribution_type': 'balanced' if count_std < count_mean else 'skewed'
        }
    
    def _detect_date_format(self, series: pl.Series) -> str:
        """Detect most common date format"""
        sample = series.head(10).cast(pl.Utf8)
        
        format_patterns = {
            'YYYY-MM-DD': r'\d{4}-\d{2}-\d{2}',
            'MM/DD/YYYY': r'\d{2}/\d{2}/\d{4}',
            'DD/MM/YYYY': r'\d{2}/\d{2}/\d{4}',
            'YYYY/MM/DD': r'\d{4}/\d{2}/\d{2}',
            'YYYY-MM-DD HH:MM:SS': r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        }
        
        for format_name, pattern in format_patterns.items():
            matches = sum(1 for val in sample if re.search(pattern, str(val)))
            if matches > len(sample) * 0.8:  # 80% match
                return format_name
        
        return 'unknown'
    
    def _generate_recommendations(self, column_analysis: Dict[str, Any]) -> List[str]:
        """Generate conversion recommendations"""
        recommendations = []
        
        for col_name, analysis in column_analysis.items():
            current_type = analysis['current_type']
            suggested_type = analysis['suggested_type']
            confidence = analysis['confidence']
            
            if current_type != suggested_type and confidence > 0.8:
                recommendations.append(
                    f"Convert '{col_name}' from {current_type} to {suggested_type} "
                    f"(confidence: {confidence:.2f})"
                )
            
            if analysis['null_percentage'] > 0.3:
                recommendations.append(
                    f"Handle missing values in '{col_name}' "
                    f"({analysis['null_percentage']:.1%} null values)"
                )
        
        return recommendations