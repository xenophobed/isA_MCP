#!/usr/bin/env python3
"""
Data Validation Service - Step 2 of Preprocessing Pipeline
Handles data validation and type analysis using processors
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import polars as pl

# Import processors for data validation
from ....processors.data_processors.preprocessors.validation.data_type_analyzer import DataTypeAnalyzer

logger = logging.getLogger(__name__)

class DataValidationService:
    """
    Step 2: Data Validation & Type Analysis Service
    
    Uses:
    - DataTypeAnalyzer processor for type inference and analysis
    
    Responsibilities:
    - Analyze data types and suggest conversions
    - Validate data quality metrics
    - Detect data issues and inconsistencies
    - Provide detailed validation reports
    """
    
    def __init__(self):
        self.type_analyzer = DataTypeAnalyzer()
        self.service_name = "DataValidationService"
        
        logger.info("Data Validation Service initialized")
    
    def validate_dataframe(self, df: pl.DataFrame, source_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive DataFrame validation
        
        Args:
            df: DataFrame to validate
            source_info: Optional information about data source
            
        Returns:
            Dict containing validation results
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Validating DataFrame: {df.height} rows, {df.width} columns")
            
            # Step 2.1: Basic structure validation
            structure_validation = self._validate_structure(df)
            
            # Step 2.2: Data type analysis using processor
            type_analysis = self.type_analyzer.analyze_dataframe(df)
            if not type_analysis.get('success'):
                return {
                    'success': False,
                    'error': f"Type analysis failed: {type_analysis.get('error')}",
                    'step': 'type_analysis'
                }
            
            # Step 2.3: Data quality assessment
            quality_assessment = self._assess_data_quality(df)
            
            # Step 2.4: Consistency checks
            consistency_checks = self._check_data_consistency(df)
            
            # Step 2.5: Generate validation summary
            validation_summary = self._generate_validation_summary(
                structure_validation, type_analysis, quality_assessment, consistency_checks
            )
            
            # Calculate validation time
            validation_duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'validation_duration': validation_duration,
                'dataframe_shape': (df.height, df.width),
                'source_info': source_info or {},
                'structure_validation': structure_validation,
                'type_analysis': type_analysis,
                'quality_assessment': quality_assessment,
                'consistency_checks': consistency_checks,
                'validation_summary': validation_summary
            }
            
            logger.info(f"Validation completed: Overall score {validation_summary['overall_score']:.2f}")
            return result
            
        except Exception as e:
            validation_duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Data validation failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'validation_duration': validation_duration,
                'step': 'general_error'
            }
    
    def _validate_structure(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Validate basic DataFrame structure"""
        validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'metrics': {}
        }
        
        try:
            # Check 1: Empty DataFrame
            if df.height == 0:
                validation['valid'] = False
                validation['errors'].append('DataFrame is empty')
                return validation

            # Check 2: Column names
            unnamed_cols = [col for col in df.columns if str(col).startswith('Unnamed:')]
            if unnamed_cols:
                validation['warnings'].append(f'{len(unnamed_cols)} unnamed columns detected')

            # Check 3: Duplicate column names
            duplicate_cols = [col for col, count in zip(*df.columns, [df.columns.count(c) for c in df.columns]) if count > 1]
            if duplicate_cols:
                validation['warnings'].append(f'Duplicate column names: {duplicate_cols}')

            # Check 4: Size validation
            total_cells = df.height * df.width
            if total_cells > 10_000_000:  # 10M cells
                validation['warnings'].append(f'Large dataset: {total_cells:,} cells')

            # Metrics
            validation['metrics'] = {
                'total_rows': df.height,
                'total_columns': df.width,
                'total_cells': total_cells,
                'unnamed_columns': len(unnamed_cols),
                'duplicate_columns': len(duplicate_cols),
                'memory_usage_mb': df.estimated_size('mb')
            }
            
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f'Structure validation error: {str(e)}')
        
        return validation
    
    def _assess_data_quality(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Assess overall data quality"""
        quality_assessment = {
            'overall_score': 0.0,
            'completeness_score': 0.0,
            'consistency_score': 0.0,
            'validity_score': 0.0,
            'column_quality': {},
            'issues': [],
            'recommendations': []
        }
        
        try:
            total_cells = df.height * df.width
            if total_cells == 0:
                return quality_assessment

            # Completeness: measure null values
            null_count = df.null_count().sum_horizontal()[0]
            completeness_score = 1 - (null_count / total_cells)
            quality_assessment['completeness_score'] = completeness_score

            # Consistency: measure duplicate rows
            duplicate_count = df.is_duplicated().sum()
            consistency_score = 1 - (duplicate_count / df.height) if df.height > 0 else 0
            quality_assessment['consistency_score'] = consistency_score
            
            # Validity: measure data type coherence per column
            validity_scores = []
            
            for col in df.columns:
                col_quality = self._assess_column_quality(df.get_column(col), str(col))
                quality_assessment['column_quality'][str(col)] = col_quality
                validity_scores.append(col_quality['validity_score'])

                # Add column-specific issues
                if col_quality['null_percentage'] > 30:
                    quality_assessment['issues'].append(f"High null percentage in '{col}': {col_quality['null_percentage']:.1f}%")

                if col_quality['validity_score'] < 0.7:
                    quality_assessment['issues'].append(f"Low data validity in '{col}': {col_quality['validity_score']:.2f}")
            
            # Overall validity score
            validity_score = sum(validity_scores) / len(validity_scores) if validity_scores else 0
            quality_assessment['validity_score'] = validity_score
            
            # Calculate overall score (weighted)
            overall_score = (
                completeness_score * 0.4 +
                consistency_score * 0.3 +
                validity_score * 0.3
            )
            quality_assessment['overall_score'] = round(overall_score, 3)
            
            # Generate recommendations
            if completeness_score < 0.8:
                quality_assessment['recommendations'].append('Consider handling missing values')
            if consistency_score < 0.9:
                quality_assessment['recommendations'].append('Consider removing duplicate rows')
            if validity_score < 0.7:
                quality_assessment['recommendations'].append('Consider data type conversions')
            
        except Exception as e:
            quality_assessment['issues'].append(f'Quality assessment error: {str(e)}')
        
        return quality_assessment
    
    def _assess_column_quality(self, series: pl.Series, column_name: str) -> Dict[str, Any]:
        """Assess quality of individual column"""
        col_quality = {
            'column_name': column_name,
            'data_type': str(series.dtype),
            'null_count': series.null_count(),
            'null_percentage': 0.0,
            'unique_count': 0,
            'unique_percentage': 0.0,
            'validity_score': 0.0,
            'issues': []
        }

        try:
            total_count = series.len()
            null_count = series.null_count()
            non_null_series = series.drop_nulls()

            # Calculate percentages
            col_quality['null_percentage'] = (null_count / total_count * 100) if total_count > 0 else 0
            col_quality['unique_count'] = non_null_series.n_unique()
            col_quality['unique_percentage'] = (col_quality['unique_count'] / non_null_series.len() * 100) if non_null_series.len() > 0 else 0
            
            # Calculate validity score based on data consistency
            validity_score = 1.0
            
            # Penalize high null percentage
            if col_quality['null_percentage'] > 50:
                validity_score *= 0.5
            elif col_quality['null_percentage'] > 20:
                validity_score *= 0.8
            
            # Check for data type consistency
            if non_null_series.len() > 0:
                # For string columns, check if values are consistent
                if series.dtype == pl.Utf8:
                    # Sample some values to check consistency
                    sample_size = min(100, non_null_series.len())
                    sample = non_null_series.sample(n=sample_size) if non_null_series.len() >= sample_size else non_null_series

                    # Check if all values are strings
                    string_ratio = sum(isinstance(val, str) for val in sample.to_list()) / sample.len()
                    validity_score *= string_ratio
            
            col_quality['validity_score'] = round(validity_score, 3)
            
            # Add specific issues
            if col_quality['null_percentage'] > 50:
                col_quality['issues'].append('High null percentage')
            if col_quality['unique_percentage'] < 1 and col_quality['unique_count'] > 1:
                col_quality['issues'].append('Low data variation')
            
        except Exception as e:
            col_quality['issues'].append(f'Column assessment error: {str(e)}')
            col_quality['validity_score'] = 0.0
        
        return col_quality
    
    def _check_data_consistency(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Check data consistency across columns"""
        consistency_checks = {
            'consistent': True,
            'issues': [],
            'warnings': [],
            'checks_performed': []
        }
        
        try:
            # Check 1: ID columns should be unique
            potential_id_cols = [col for col in df.columns 
                               if any(id_word in str(col).lower() for id_word in ['id', 'key', 'code'])]
            
            for col in potential_id_cols:
                non_null_df = df.filter(pl.col(col).is_not_null())
                if df.get_column(col).n_unique() != non_null_df.height:
                    consistency_checks['issues'].append(f"ID column '{col}' has duplicate values")
                    consistency_checks['consistent'] = False
                consistency_checks['checks_performed'].append(f"ID uniqueness check for '{col}'")
            
            # Check 2: Date columns should be in valid format
            date_cols = [col for col in df.columns 
                        if any(date_word in str(col).lower() for date_word in ['date', 'time', 'created', 'updated'])]
            
            for col in date_cols:
                try:
                    # Try parsing as datetime in Polars
                    df.get_column(col).str.to_datetime(strict=False)
                    consistency_checks['checks_performed'].append(f"Date format check for '{col}'")
                except:
                    consistency_checks['warnings'].append(f"Date column '{col}' may have format issues")

            # Check 3: Numeric columns should not have text values (if not object type)
            numeric_cols = [col for col in df.columns if df.get_column(col).dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.Float32, pl.Float64]]
            for col in numeric_cols:
                if df.get_column(col).null_count() < df.height:
                    consistency_checks['checks_performed'].append(f"Numeric consistency check for '{col}'")
            
        except Exception as e:
            consistency_checks['issues'].append(f'Consistency check error: {str(e)}')
            consistency_checks['consistent'] = False
        
        return consistency_checks
    
    def _generate_validation_summary(self, structure_validation: Dict[str, Any], 
                                   type_analysis: Dict[str, Any],
                                   quality_assessment: Dict[str, Any],
                                   consistency_checks: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall validation summary"""
        
        # Calculate overall score
        structure_score = 1.0 if structure_validation['valid'] else 0.0
        type_score = sum(col['confidence'] for col in type_analysis['column_analysis'].values()) / len(type_analysis['column_analysis']) if type_analysis['column_analysis'] else 0.0
        quality_score = quality_assessment['overall_score']
        consistency_score = 1.0 if consistency_checks['consistent'] else 0.8
        
        overall_score = (structure_score * 0.2 + type_score * 0.3 + quality_score * 0.4 + consistency_score * 0.1)
        
        # Collect all issues
        all_issues = []
        all_issues.extend(structure_validation.get('errors', []))
        all_issues.extend(structure_validation.get('warnings', []))
        all_issues.extend(quality_assessment.get('issues', []))
        all_issues.extend(consistency_checks.get('issues', []))
        all_issues.extend(consistency_checks.get('warnings', []))
        
        # Collect recommendations
        all_recommendations = []
        all_recommendations.extend(quality_assessment.get('recommendations', []))
        all_recommendations.extend(type_analysis.get('recommendations', []))
        
        return {
            'overall_score': round(overall_score, 3),
            'component_scores': {
                'structure': round(structure_score, 3),
                'types': round(type_score, 3),
                'quality': round(quality_score, 3),
                'consistency': round(consistency_score, 3)
            },
            'total_issues': len(all_issues),
            'total_recommendations': len(all_recommendations),
            'validation_passed': overall_score >= 0.7,
            'critical_issues': [issue for issue in all_issues if 'error' in issue.lower()],
            'top_recommendations': all_recommendations[:5]  # Top 5 recommendations
        }