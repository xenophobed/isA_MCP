"""
Quality Assessment Service - Step 1 of Quality Management Pipeline
Analyzes and assesses data quality issues and metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class AssessmentConfig:
    """Configuration for quality assessment"""
    check_missing_values: bool = True
    check_duplicates: bool = True
    check_data_types: bool = True
    check_outliers: bool = True
    check_consistency: bool = True
    check_completeness: bool = True
    check_validity: bool = True
    outlier_method: str = "iqr"  # iqr, zscore, isolation_forest
    missing_threshold: float = 0.05  # 5% threshold for missing values
    duplicate_threshold: float = 0.01  # 1% threshold for duplicates

@dataclass
class AssessmentResult:
    """Result of quality assessment step"""
    success: bool
    overall_quality_score: float = 0.0
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    quality_issues: Dict[str, List[str]] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    detailed_analysis: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class QualityAssessmentService:
    """
    Quality Assessment Service - Step 1 of Quality Management Pipeline
    
    Handles:
    - Comprehensive data quality analysis
    - Missing value detection and analysis
    - Duplicate detection and assessment
    - Data type validation and consistency checks
    - Outlier detection and analysis
    - Quality scoring and metrics calculation
    """
    
    def __init__(self):
        self.execution_stats = {
            'total_assessments': 0,
            'successful_assessments': 0,
            'failed_assessments': 0,
            'average_assessment_time': 0.0,
            'total_datasets_assessed': 0
        }
        
        logger.info("Quality Assessment Service initialized")
    
    def assess_data_quality(self,
                           data: pd.DataFrame,
                           config: AssessmentConfig,
                           column_metadata: Optional[Dict[str, Any]] = None) -> AssessmentResult:
        """
        Perform comprehensive data quality assessment
        
        Args:
            data: DataFrame to assess
            config: Assessment configuration
            column_metadata: Optional metadata about expected column types/constraints
            
        Returns:
            AssessmentResult with quality metrics and issues
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting quality assessment for dataset shape: {data.shape}")
            
            # Initialize result
            result = AssessmentResult(success=False)
            quality_metrics = {}
            quality_issues = {}
            detailed_analysis = {}
            
            # 1. Missing Values Assessment
            if config.check_missing_values:
                missing_analysis = self._assess_missing_values(data, config)
                quality_metrics['missing_values'] = missing_analysis['metrics']
                if missing_analysis['issues']:
                    quality_issues['missing_values'] = missing_analysis['issues']
                detailed_analysis['missing_values'] = missing_analysis['details']
            
            # 2. Duplicate Assessment
            if config.check_duplicates:
                duplicate_analysis = self._assess_duplicates(data, config)
                quality_metrics['duplicates'] = duplicate_analysis['metrics']
                if duplicate_analysis['issues']:
                    quality_issues['duplicates'] = duplicate_analysis['issues']
                detailed_analysis['duplicates'] = duplicate_analysis['details']
            
            # 3. Data Types Assessment
            if config.check_data_types:
                types_analysis = self._assess_data_types(data, column_metadata)
                quality_metrics['data_types'] = types_analysis['metrics']
                if types_analysis['issues']:
                    quality_issues['data_types'] = types_analysis['issues']
                detailed_analysis['data_types'] = types_analysis['details']
            
            # 4. Outliers Assessment
            if config.check_outliers:
                outliers_analysis = self._assess_outliers(data, config)
                quality_metrics['outliers'] = outliers_analysis['metrics']
                if outliers_analysis['issues']:
                    quality_issues['outliers'] = outliers_analysis['issues']
                detailed_analysis['outliers'] = outliers_analysis['details']
            
            # 5. Consistency Assessment
            if config.check_consistency:
                consistency_analysis = self._assess_consistency(data)
                quality_metrics['consistency'] = consistency_analysis['metrics']
                if consistency_analysis['issues']:
                    quality_issues['consistency'] = consistency_analysis['issues']
                detailed_analysis['consistency'] = consistency_analysis['details']
            
            # 6. Completeness Assessment
            if config.check_completeness:
                completeness_analysis = self._assess_completeness(data)
                quality_metrics['completeness'] = completeness_analysis['metrics']
                if completeness_analysis['issues']:
                    quality_issues['completeness'] = completeness_analysis['issues']
                detailed_analysis['completeness'] = completeness_analysis['details']
            
            # 7. Validity Assessment
            if config.check_validity:
                validity_analysis = self._assess_validity(data, column_metadata)
                quality_metrics['validity'] = validity_analysis['metrics']
                if validity_analysis['issues']:
                    quality_issues['validity'] = validity_analysis['issues']
                detailed_analysis['validity'] = validity_analysis['details']
            
            # Calculate overall quality score
            overall_score = self._calculate_overall_quality_score(quality_metrics)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(quality_issues, quality_metrics)
            
            # Success
            result.success = True
            result.overall_quality_score = overall_score
            result.quality_metrics = quality_metrics
            result.quality_issues = quality_issues
            result.recommendations = recommendations
            result.detailed_analysis = detailed_analysis
            
            return self._finalize_assessment_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            result.errors.append(f"Assessment error: {str(e)}")
            return self._finalize_assessment_result(result, start_time)
    
    def _assess_missing_values(self, data: pd.DataFrame, config: AssessmentConfig) -> Dict[str, Any]:
        """Assess missing values in the dataset"""
        try:
            missing_counts = data.isnull().sum()
            missing_percentages = (missing_counts / len(data)) * 100
            
            # Identify problematic columns
            problematic_columns = missing_percentages[
                missing_percentages > (config.missing_threshold * 100)
            ].to_dict()
            
            metrics = {
                'total_missing_values': int(missing_counts.sum()),
                'missing_percentage': float(missing_counts.sum() / data.size * 100),
                'columns_with_missing': int((missing_counts > 0).sum()),
                'worst_column': missing_percentages.idxmax() if missing_counts.sum() > 0 else None,
                'worst_column_percentage': float(missing_percentages.max()) if missing_counts.sum() > 0 else 0.0
            }
            
            issues = []
            if problematic_columns:
                issues.append(f"High missing values in columns: {list(problematic_columns.keys())}")
            
            details = {
                'missing_by_column': missing_counts.to_dict(),
                'missing_percentages_by_column': missing_percentages.to_dict(),
                'problematic_columns': problematic_columns
            }
            
            return {
                'metrics': metrics,
                'issues': issues,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Missing values assessment failed: {e}")
            return {'metrics': {}, 'issues': [str(e)], 'details': {}}
    
    def _assess_duplicates(self, data: pd.DataFrame, config: AssessmentConfig) -> Dict[str, Any]:
        """Assess duplicate records in the dataset"""
        try:
            # Full row duplicates
            duplicate_rows = data.duplicated()
            duplicate_count = duplicate_rows.sum()
            duplicate_percentage = (duplicate_count / len(data)) * 100
            
            # Check for duplicates in key columns (if identifiable)
            potential_id_columns = []
            for col in data.columns:
                if 'id' in col.lower() or col.lower().endswith('_key'):
                    potential_id_columns.append(col)
            
            id_duplicates = {}
            for col in potential_id_columns:
                if data[col].dtype in ['object', 'int64', 'float64']:
                    id_dups = data[col].duplicated().sum()
                    if id_dups > 0:
                        id_duplicates[col] = int(id_dups)
            
            metrics = {
                'duplicate_rows': int(duplicate_count),
                'duplicate_percentage': float(duplicate_percentage),
                'unique_rows': int(len(data) - duplicate_count),
                'id_column_duplicates': id_duplicates
            }
            
            issues = []
            if duplicate_percentage > (config.duplicate_threshold * 100):
                issues.append(f"High number of duplicate rows: {duplicate_count} ({duplicate_percentage:.2f}%)")
            
            if id_duplicates:
                issues.append(f"Duplicates found in ID columns: {list(id_duplicates.keys())}")
            
            details = {
                'duplicate_row_indices': duplicate_rows[duplicate_rows].index.tolist()[:100],  # First 100
                'potential_id_columns': potential_id_columns,
                'id_column_duplicates': id_duplicates
            }
            
            return {
                'metrics': metrics,
                'issues': issues,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Duplicate assessment failed: {e}")
            return {'metrics': {}, 'issues': [str(e)], 'details': {}}
    
    def _assess_data_types(self, data: pd.DataFrame, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess data types and type consistency"""
        try:
            type_info = data.dtypes.to_dict()
            type_counts = data.dtypes.value_counts().to_dict()
            
            # Check for mixed types
            mixed_type_columns = []
            for col in data.columns:
                if data[col].dtype == 'object':
                    # Check if column contains mixed numeric/string data
                    sample_values = data[col].dropna().head(100)
                    numeric_count = 0
                    string_count = 0
                    
                    for val in sample_values:
                        try:
                            float(val)
                            numeric_count += 1
                        except (ValueError, TypeError):
                            string_count += 1
                    
                    if numeric_count > 0 and string_count > 0:
                        mixed_type_columns.append(col)
            
            # Check against expected types if metadata provided
            type_mismatches = {}
            if metadata and 'expected_types' in metadata:
                for col, expected_type in metadata['expected_types'].items():
                    if col in data.columns:
                        actual_type = str(data[col].dtype)
                        if expected_type != actual_type:
                            type_mismatches[col] = {
                                'expected': expected_type,
                                'actual': actual_type
                            }
            
            metrics = {
                'total_columns': len(data.columns),
                'numeric_columns': int((data.dtypes == 'float64').sum() + (data.dtypes == 'int64').sum()),
                'string_columns': int((data.dtypes == 'object').sum()),
                'datetime_columns': int((data.dtypes == 'datetime64[ns]').sum()),
                'mixed_type_columns': len(mixed_type_columns),
                'type_mismatch_columns': len(type_mismatches)
            }
            
            issues = []
            if mixed_type_columns:
                issues.append(f"Mixed data types in columns: {mixed_type_columns}")
            
            if type_mismatches:
                issues.append(f"Type mismatches in columns: {list(type_mismatches.keys())}")
            
            details = {
                'column_types': {str(k): str(v) for k, v in type_info.items()},
                'type_distribution': {str(k): int(v) for k, v in type_counts.items()},
                'mixed_type_columns': mixed_type_columns,
                'type_mismatches': type_mismatches
            }
            
            return {
                'metrics': metrics,
                'issues': issues,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Data types assessment failed: {e}")
            return {'metrics': {}, 'issues': [str(e)], 'details': {}}
    
    def _assess_outliers(self, data: pd.DataFrame, config: AssessmentConfig) -> Dict[str, Any]:
        """Assess outliers in numeric columns"""
        try:
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            outlier_info = {}
            total_outliers = 0
            
            for col in numeric_columns:
                col_data = data[col].dropna()
                if len(col_data) == 0:
                    continue
                
                if config.outlier_method == "iqr":
                    Q1 = col_data.quantile(0.25)
                    Q3 = col_data.quantile(0.75)
                    IQR = Q3 - Q1
                    outliers = col_data[(col_data < Q1 - 1.5 * IQR) | (col_data > Q3 + 1.5 * IQR)]
                    
                elif config.outlier_method == "zscore":
                    z_scores = np.abs((col_data - col_data.mean()) / col_data.std())
                    outliers = col_data[z_scores > 3]
                    
                else:  # Default to IQR
                    Q1 = col_data.quantile(0.25)
                    Q3 = col_data.quantile(0.75)
                    IQR = Q3 - Q1
                    outliers = col_data[(col_data < Q1 - 1.5 * IQR) | (col_data > Q3 + 1.5 * IQR)]
                
                if len(outliers) > 0:
                    outlier_info[col] = {
                        'count': len(outliers),
                        'percentage': (len(outliers) / len(col_data)) * 100,
                        'min_outlier': float(outliers.min()),
                        'max_outlier': float(outliers.max())
                    }
                    total_outliers += len(outliers)
            
            metrics = {
                'total_outliers': total_outliers,
                'columns_with_outliers': len(outlier_info),
                'outlier_percentage': (total_outliers / len(data)) * 100 if len(data) > 0 else 0,
                'outlier_method_used': config.outlier_method
            }
            
            issues = []
            high_outlier_columns = [col for col, info in outlier_info.items() 
                                  if info['percentage'] > 5]  # More than 5% outliers
            if high_outlier_columns:
                issues.append(f"High outlier percentage in columns: {high_outlier_columns}")
            
            details = {
                'outliers_by_column': outlier_info,
                'numeric_columns_analyzed': list(numeric_columns)
            }
            
            return {
                'metrics': metrics,
                'issues': issues,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Outliers assessment failed: {e}")
            return {'metrics': {}, 'issues': [str(e)], 'details': {}}
    
    def _assess_consistency(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Assess data consistency patterns"""
        try:
            consistency_issues = []
            
            # Check for consistent formatting in string columns
            string_columns = data.select_dtypes(include=['object']).columns
            format_inconsistencies = {}
            
            for col in string_columns:
                col_data = data[col].dropna()
                if len(col_data) == 0:
                    continue
                
                # Check for mixed case patterns
                has_upper = any(val.isupper() for val in col_data if isinstance(val, str))
                has_lower = any(val.islower() for val in col_data if isinstance(val, str))
                has_mixed = any(val != val.upper() and val != val.lower() 
                              for val in col_data if isinstance(val, str))
                
                if sum([has_upper, has_lower, has_mixed]) > 1:
                    format_inconsistencies[col] = 'mixed_case'
                
                # Check for whitespace inconsistencies
                has_leading_space = any(val.startswith(' ') for val in col_data if isinstance(val, str))
                has_trailing_space = any(val.endswith(' ') for val in col_data if isinstance(val, str))
                
                if has_leading_space or has_trailing_space:
                    format_inconsistencies[col] = format_inconsistencies.get(col, '') + '_whitespace'
            
            metrics = {
                'string_columns_checked': len(string_columns),
                'format_inconsistent_columns': len(format_inconsistencies),
                'consistency_score': max(0, (len(string_columns) - len(format_inconsistencies)) / max(len(string_columns), 1))
            }
            
            issues = []
            if format_inconsistencies:
                issues.append(f"Format inconsistencies in columns: {list(format_inconsistencies.keys())}")
            
            details = {
                'format_inconsistencies': format_inconsistencies,
                'string_columns_analyzed': list(string_columns)
            }
            
            return {
                'metrics': metrics,
                'issues': issues,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Consistency assessment failed: {e}")
            return {'metrics': {}, 'issues': [str(e)], 'details': {}}
    
    def _assess_completeness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Assess data completeness"""
        try:
            total_cells = data.size
            filled_cells = total_cells - data.isnull().sum().sum()
            completeness_percentage = (filled_cells / total_cells) * 100
            
            # Column-level completeness
            column_completeness = {}
            for col in data.columns:
                col_filled = len(data[col].dropna())
                col_total = len(data)
                column_completeness[col] = (col_filled / col_total) * 100
            
            # Identify sparse columns
            sparse_columns = [col for col, comp in column_completeness.items() if comp < 50]
            
            metrics = {
                'overall_completeness': float(completeness_percentage),
                'total_cells': total_cells,
                'filled_cells': filled_cells,
                'sparse_columns': len(sparse_columns),
                'complete_columns': len([col for col, comp in column_completeness.items() if comp == 100])
            }
            
            issues = []
            if completeness_percentage < 80:
                issues.append(f"Low overall completeness: {completeness_percentage:.2f}%")
            
            if sparse_columns:
                issues.append(f"Sparse columns (< 50% complete): {sparse_columns}")
            
            details = {
                'column_completeness': column_completeness,
                'sparse_columns': sparse_columns
            }
            
            return {
                'metrics': metrics,
                'issues': issues,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Completeness assessment failed: {e}")
            return {'metrics': {}, 'issues': [str(e)], 'details': {}}
    
    def _assess_validity(self, data: pd.DataFrame, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess data validity against constraints"""
        try:
            validity_issues = {}
            
            # Basic validity checks
            for col in data.columns:
                col_issues = []
                
                # Check for negative values in columns that shouldn't have them
                if col.lower() in ['age', 'price', 'amount', 'quantity', 'count']:
                    if data[col].dtype in ['int64', 'float64']:
                        negative_count = (data[col] < 0).sum()
                        if negative_count > 0:
                            col_issues.append(f"Negative values: {negative_count}")
                
                # Check for unrealistic values
                if col.lower() == 'age':
                    if data[col].dtype in ['int64', 'float64']:
                        unrealistic_ages = ((data[col] < 0) | (data[col] > 150)).sum()
                        if unrealistic_ages > 0:
                            col_issues.append(f"Unrealistic ages: {unrealistic_ages}")
                
                # Email validation for email columns
                if 'email' in col.lower():
                    import re
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    invalid_emails = 0
                    for email in data[col].dropna():
                        if not re.match(email_pattern, str(email)):
                            invalid_emails += 1
                    if invalid_emails > 0:
                        col_issues.append(f"Invalid email format: {invalid_emails}")
                
                if col_issues:
                    validity_issues[col] = col_issues
            
            # Check against metadata constraints if provided
            if metadata and 'constraints' in metadata:
                for col, constraints in metadata['constraints'].items():
                    if col not in data.columns:
                        continue
                    
                    col_data = data[col].dropna()
                    
                    # Min/max constraints
                    if 'min' in constraints:
                        violations = (col_data < constraints['min']).sum()
                        if violations > 0:
                            validity_issues.setdefault(col, []).append(f"Min constraint violations: {violations}")
                    
                    if 'max' in constraints:
                        violations = (col_data > constraints['max']).sum()
                        if violations > 0:
                            validity_issues.setdefault(col, []).append(f"Max constraint violations: {violations}")
                    
                    # Allowed values constraints
                    if 'allowed_values' in constraints:
                        invalid_values = ~col_data.isin(constraints['allowed_values'])
                        violations = invalid_values.sum()
                        if violations > 0:
                            validity_issues.setdefault(col, []).append(f"Invalid values: {violations}")
            
            metrics = {
                'columns_with_validity_issues': len(validity_issues),
                'total_validity_issues': sum(len(issues) for issues in validity_issues.values()),
                'validity_score': max(0, (len(data.columns) - len(validity_issues)) / max(len(data.columns), 1))
            }
            
            issues = []
            if validity_issues:
                issues.append(f"Data validity issues in columns: {list(validity_issues.keys())}")
            
            details = {
                'validity_issues_by_column': validity_issues
            }
            
            return {
                'metrics': metrics,
                'issues': issues,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Validity assessment failed: {e}")
            return {'metrics': {}, 'issues': [str(e)], 'details': {}}
    
    def _calculate_overall_quality_score(self, quality_metrics: Dict[str, Any]) -> float:
        """Calculate overall quality score from individual metrics"""
        try:
            scores = []
            weights = []
            
            # Missing values score (weight: 0.25)
            if 'missing_values' in quality_metrics:
                missing_pct = quality_metrics['missing_values'].get('missing_percentage', 0)
                missing_score = max(0, 1 - (missing_pct / 100))
                scores.append(missing_score)
                weights.append(0.25)
            
            # Duplicates score (weight: 0.15)
            if 'duplicates' in quality_metrics:
                dup_pct = quality_metrics['duplicates'].get('duplicate_percentage', 0)
                dup_score = max(0, 1 - (dup_pct / 100))
                scores.append(dup_score)
                weights.append(0.15)
            
            # Completeness score (weight: 0.20)
            if 'completeness' in quality_metrics:
                comp_pct = quality_metrics['completeness'].get('overall_completeness', 0)
                comp_score = comp_pct / 100
                scores.append(comp_score)
                weights.append(0.20)
            
            # Consistency score (weight: 0.15)
            if 'consistency' in quality_metrics:
                consistency_score = quality_metrics['consistency'].get('consistency_score', 0)
                scores.append(consistency_score)
                weights.append(0.15)
            
            # Validity score (weight: 0.15)
            if 'validity' in quality_metrics:
                validity_score = quality_metrics['validity'].get('validity_score', 0)
                scores.append(validity_score)
                weights.append(0.15)
            
            # Outliers score (weight: 0.10)
            if 'outliers' in quality_metrics:
                outlier_pct = quality_metrics['outliers'].get('outlier_percentage', 0)
                outlier_score = max(0, 1 - (outlier_pct / 100))
                scores.append(outlier_score)
                weights.append(0.10)
            
            if not scores:
                return 0.0
            
            # Weighted average
            weighted_score = sum(score * weight for score, weight in zip(scores, weights))
            total_weight = sum(weights)
            
            return weighted_score / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Quality score calculation failed: {e}")
            return 0.0
    
    def _generate_recommendations(self, 
                                quality_issues: Dict[str, List[str]], 
                                quality_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on quality issues"""
        recommendations = []
        
        # Missing values recommendations
        if 'missing_values' in quality_issues:
            recommendations.append("Address missing values through imputation or removal")
            recommendations.append("Consider data collection improvements to reduce missing values")
        
        # Duplicates recommendations
        if 'duplicates' in quality_issues:
            recommendations.append("Remove or merge duplicate records")
            recommendations.append("Implement data deduplication processes")
        
        # Data types recommendations
        if 'data_types' in quality_issues:
            recommendations.append("Standardize data types and formats")
            recommendations.append("Implement data validation at ingestion")
        
        # Outliers recommendations
        if 'outliers' in quality_issues:
            recommendations.append("Investigate and validate outlier values")
            recommendations.append("Consider outlier treatment methods (capping, transformation)")
        
        # Consistency recommendations
        if 'consistency' in quality_issues:
            recommendations.append("Standardize text formatting and case")
            recommendations.append("Implement data normalization procedures")
        
        # Validity recommendations
        if 'validity' in quality_issues:
            recommendations.append("Implement business rule validation")
            recommendations.append("Add constraint checks during data entry")
        
        # Overall recommendations based on score
        overall_score = quality_metrics.get('overall_quality_score', 0)
        if overall_score < 0.6:
            recommendations.append("Consider comprehensive data quality remediation")
            recommendations.append("Implement data quality monitoring and alerts")
        
        return recommendations
    
    def _finalize_assessment_result(self,
                                  result: AssessmentResult,
                                  start_time: datetime) -> AssessmentResult:
        """Finalize assessment result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update performance metrics
        result.performance_metrics['assessment_duration_seconds'] = duration
        result.performance_metrics['end_time'] = end_time
        
        # Update execution stats
        self.execution_stats['total_assessments'] += 1
        if result.success:
            self.execution_stats['successful_assessments'] += 1
            self.execution_stats['total_datasets_assessed'] += 1
        else:
            self.execution_stats['failed_assessments'] += 1
        
        # Update average duration
        total = self.execution_stats['total_assessments']
        old_avg = self.execution_stats['average_assessment_time']
        self.execution_stats['average_assessment_time'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Quality assessment completed: success={result.success}, duration={duration:.2f}s, score={result.overall_quality_score:.3f}")
        return result
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_assessments'] / 
                max(1, self.execution_stats['total_assessments'])
            )
        }