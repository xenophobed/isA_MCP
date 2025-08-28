"""
Quality Improvement Service - Step 2 of Quality Management Pipeline
Applies fixes and improvements to address data quality issues
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
import logging
from dataclasses import dataclass, field
from datetime import datetime
import re

logger = logging.getLogger(__name__)

@dataclass
class ImprovementConfig:
    """Configuration for quality improvement"""
    handle_missing_values: bool = True
    missing_strategy: str = "auto"  # auto, drop, mean, median, mode, forward_fill, backward_fill
    handle_duplicates: bool = True
    duplicate_strategy: str = "remove"  # remove, keep_first, keep_last
    handle_outliers: bool = True
    outlier_strategy: str = "cap"  # cap, remove, transform
    handle_inconsistencies: bool = True
    normalize_text: bool = True
    validate_constraints: bool = True
    create_backup: bool = True

@dataclass
class ImprovementResult:
    """Result of quality improvement step"""
    success: bool
    improved_data: Optional[pd.DataFrame] = None
    improvement_summary: Dict[str, Any] = field(default_factory=dict)
    applied_fixes: List[str] = field(default_factory=list)
    quality_before: Dict[str, Any] = field(default_factory=dict)
    quality_after: Dict[str, Any] = field(default_factory=dict)
    improvement_metrics: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class QualityImprovementService:
    """
    Quality Improvement Service - Step 2 of Quality Management Pipeline
    
    Handles:
    - Missing value treatment and imputation
    - Duplicate record removal and merging
    - Outlier detection and treatment
    - Data standardization and normalization
    - Format consistency improvements
    - Constraint validation and enforcement
    """
    
    def __init__(self):
        self.execution_stats = {
            'total_improvements': 0,
            'successful_improvements': 0,
            'failed_improvements': 0,
            'total_records_improved': 0,
            'average_improvement_time': 0.0
        }
        
        # Track improvement operations
        self.improvement_history = {}
        
        logger.info("Quality Improvement Service initialized")
    
    def improve_data_quality(self,
                           data: pd.DataFrame,
                           assessment_result: Dict[str, Any],
                           config: ImprovementConfig,
                           constraints: Optional[Dict[str, Any]] = None) -> ImprovementResult:
        """
        Apply quality improvements to data based on assessment results
        
        Args:
            data: DataFrame to improve
            assessment_result: Results from quality assessment
            config: Improvement configuration
            constraints: Optional constraints for validation
            
        Returns:
            ImprovementResult with improved data and metrics
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting quality improvement for dataset shape: {data.shape}")
            
            # Initialize result
            result = ImprovementResult(success=False)
            
            # Create backup if requested
            original_data = data.copy() if config.create_backup else None
            improved_data = data.copy()
            
            # Store quality before improvement
            result.quality_before = self._calculate_basic_quality_metrics(improved_data)
            
            applied_fixes = []
            improvement_summary = {}
            
            # 1. Handle Missing Values
            if config.handle_missing_values:
                missing_result = self._handle_missing_values(
                    improved_data, assessment_result, config
                )
                if missing_result['success']:
                    improved_data = missing_result['data']
                    applied_fixes.extend(missing_result['fixes'])
                    improvement_summary['missing_values'] = missing_result['summary']
                else:
                    result.warnings.extend(missing_result.get('warnings', []))
            
            # 2. Handle Duplicates
            if config.handle_duplicates:
                duplicate_result = self._handle_duplicates(
                    improved_data, assessment_result, config
                )
                if duplicate_result['success']:
                    improved_data = duplicate_result['data']
                    applied_fixes.extend(duplicate_result['fixes'])
                    improvement_summary['duplicates'] = duplicate_result['summary']
                else:
                    result.warnings.extend(duplicate_result.get('warnings', []))
            
            # 3. Handle Outliers
            if config.handle_outliers:
                outlier_result = self._handle_outliers(
                    improved_data, assessment_result, config
                )
                if outlier_result['success']:
                    improved_data = outlier_result['data']
                    applied_fixes.extend(outlier_result['fixes'])
                    improvement_summary['outliers'] = outlier_result['summary']
                else:
                    result.warnings.extend(outlier_result.get('warnings', []))
            
            # 4. Handle Inconsistencies
            if config.handle_inconsistencies:
                consistency_result = self._handle_inconsistencies(
                    improved_data, assessment_result, config
                )
                if consistency_result['success']:
                    improved_data = consistency_result['data']
                    applied_fixes.extend(consistency_result['fixes'])
                    improvement_summary['consistency'] = consistency_result['summary']
                else:
                    result.warnings.extend(consistency_result.get('warnings', []))
            
            # 5. Normalize Text
            if config.normalize_text:
                normalization_result = self._normalize_text_data(improved_data, config)
                if normalization_result['success']:
                    improved_data = normalization_result['data']
                    applied_fixes.extend(normalization_result['fixes'])
                    improvement_summary['text_normalization'] = normalization_result['summary']
                else:
                    result.warnings.extend(normalization_result.get('warnings', []))
            
            # 6. Validate Constraints
            if config.validate_constraints and constraints:
                validation_result = self._validate_and_fix_constraints(
                    improved_data, constraints, config
                )
                if validation_result['success']:
                    improved_data = validation_result['data']
                    applied_fixes.extend(validation_result['fixes'])
                    improvement_summary['constraint_validation'] = validation_result['summary']
                else:
                    result.warnings.extend(validation_result.get('warnings', []))
            
            # Calculate quality after improvement
            quality_after = self._calculate_basic_quality_metrics(improved_data)
            
            # Calculate improvement metrics
            improvement_metrics = self._calculate_improvement_metrics(
                result.quality_before, quality_after, original_data, improved_data
            )
            
            # Store improvement operation
            improvement_id = f"improvement_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.improvement_history[improvement_id] = {
                'original_shape': data.shape,
                'improved_shape': improved_data.shape,
                'applied_fixes': applied_fixes,
                'improvement_metrics': improvement_metrics,
                'timestamp': start_time
            }
            
            # Success
            result.success = True
            result.improved_data = improved_data
            result.improvement_summary = improvement_summary
            result.applied_fixes = applied_fixes
            result.quality_after = quality_after
            result.improvement_metrics = improvement_metrics
            
            return self._finalize_improvement_result(result, start_time, len(data))
            
        except Exception as e:
            logger.error(f"Quality improvement failed: {e}")
            result.errors.append(f"Improvement error: {str(e)}")
            return self._finalize_improvement_result(result, start_time, 0)
    
    def _handle_missing_values(self,
                              data: pd.DataFrame,
                              assessment_result: Dict[str, Any],
                              config: ImprovementConfig) -> Dict[str, Any]:
        """Handle missing values in the dataset"""
        try:
            fixes = []
            summary = {}
            original_missing = data.isnull().sum().sum()
            
            if original_missing == 0:
                return {
                    'success': True,
                    'data': data,
                    'fixes': [],
                    'summary': {'no_missing_values': True}
                }
            
            strategy = config.missing_strategy
            
            # Auto strategy: choose best strategy per column
            if strategy == "auto":
                for col in data.columns:
                    missing_count = data[col].isnull().sum()
                    if missing_count == 0:
                        continue
                    
                    missing_pct = (missing_count / len(data)) * 100
                    
                    # Drop columns with >70% missing
                    if missing_pct > 70:
                        data = data.drop(columns=[col])
                        fixes.append(f"Dropped column '{col}' (>70% missing)")
                        continue
                    
                    # Strategy based on data type and missing percentage
                    if data[col].dtype in ['int64', 'float64']:
                        if missing_pct < 10:
                            data[col] = data[col].fillna(data[col].median())
                            fixes.append(f"Filled '{col}' missing values with median")
                        else:
                            data[col] = data[col].fillna(data[col].mean())
                            fixes.append(f"Filled '{col}' missing values with mean")
                    else:  # String/object columns
                        if missing_pct < 10:
                            mode_val = data[col].mode()
                            if len(mode_val) > 0:
                                data[col] = data[col].fillna(mode_val[0])
                                fixes.append(f"Filled '{col}' missing values with mode")
                            else:
                                data[col] = data[col].fillna('Unknown')
                                fixes.append(f"Filled '{col}' missing values with 'Unknown'")
                        else:
                            data[col] = data[col].fillna('Missing')
                            fixes.append(f"Filled '{col}' missing values with 'Missing'")
            
            # Specific strategies
            elif strategy == "drop":
                original_rows = len(data)
                data = data.dropna()
                dropped_rows = original_rows - len(data)
                fixes.append(f"Dropped {dropped_rows} rows with missing values")
            
            elif strategy == "mean":
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    if data[col].isnull().any():
                        data[col] = data[col].fillna(data[col].mean())
                        fixes.append(f"Filled '{col}' with mean")
            
            elif strategy == "median":
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    if data[col].isnull().any():
                        data[col] = data[col].fillna(data[col].median())
                        fixes.append(f"Filled '{col}' with median")
            
            elif strategy == "mode":
                for col in data.columns:
                    if data[col].isnull().any():
                        mode_val = data[col].mode()
                        if len(mode_val) > 0:
                            data[col] = data[col].fillna(mode_val[0])
                            fixes.append(f"Filled '{col}' with mode")
            
            elif strategy == "forward_fill":
                data = data.fillna(method='ffill')
                fixes.append("Applied forward fill for missing values")
            
            elif strategy == "backward_fill":
                data = data.fillna(method='bfill')
                fixes.append("Applied backward fill for missing values")
            
            final_missing = data.isnull().sum().sum()
            
            summary = {
                'original_missing_values': original_missing,
                'final_missing_values': final_missing,
                'missing_values_fixed': original_missing - final_missing,
                'strategy_used': strategy
            }
            
            return {
                'success': True,
                'data': data,
                'fixes': fixes,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Missing values handling failed: {e}")
            return {
                'success': False,
                'warnings': [f"Missing values handling failed: {str(e)}"]
            }
    
    def _handle_duplicates(self,
                          data: pd.DataFrame,
                          assessment_result: Dict[str, Any],
                          config: ImprovementConfig) -> Dict[str, Any]:
        """Handle duplicate records in the dataset"""
        try:
            fixes = []
            summary = {}
            original_rows = len(data)
            original_duplicates = data.duplicated().sum()
            
            if original_duplicates == 0:
                return {
                    'success': True,
                    'data': data,
                    'fixes': [],
                    'summary': {'no_duplicates': True}
                }
            
            strategy = config.duplicate_strategy
            
            if strategy == "remove":
                data = data.drop_duplicates()
                fixes.append("Removed duplicate rows")
            
            elif strategy == "keep_first":
                data = data.drop_duplicates(keep='first')
                fixes.append("Removed duplicates, kept first occurrence")
            
            elif strategy == "keep_last":
                data = data.drop_duplicates(keep='last')
                fixes.append("Removed duplicates, kept last occurrence")
            
            final_rows = len(data)
            removed_rows = original_rows - final_rows
            
            summary = {
                'original_rows': original_rows,
                'final_rows': final_rows,
                'duplicate_rows_removed': removed_rows,
                'strategy_used': strategy
            }
            
            return {
                'success': True,
                'data': data,
                'fixes': fixes,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Duplicate handling failed: {e}")
            return {
                'success': False,
                'warnings': [f"Duplicate handling failed: {str(e)}"]
            }
    
    def _handle_outliers(self,
                        data: pd.DataFrame,
                        assessment_result: Dict[str, Any],
                        config: ImprovementConfig) -> Dict[str, Any]:
        """Handle outliers in numeric columns"""
        try:
            fixes = []
            summary = {}
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            outliers_handled = 0
            strategy = config.outlier_strategy
            
            for col in numeric_columns:
                col_data = data[col].dropna()
                if len(col_data) == 0:
                    continue
                
                # Detect outliers using IQR method
                Q1 = col_data.quantile(0.25)
                Q3 = col_data.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outlier_mask = (data[col] < lower_bound) | (data[col] > upper_bound)
                outlier_count = outlier_mask.sum()
                
                if outlier_count == 0:
                    continue
                
                if strategy == "cap":
                    # Cap outliers to bounds
                    data.loc[data[col] < lower_bound, col] = lower_bound
                    data.loc[data[col] > upper_bound, col] = upper_bound
                    fixes.append(f"Capped {outlier_count} outliers in '{col}'")
                
                elif strategy == "remove":
                    # Remove rows with outliers
                    data = data[~outlier_mask]
                    fixes.append(f"Removed {outlier_count} outlier rows in '{col}'")
                
                elif strategy == "transform":
                    # Log transformation for positive values
                    if (data[col] > 0).all():
                        data[col] = np.log1p(data[col])
                        fixes.append(f"Applied log transformation to '{col}'")
                    else:
                        # Use z-score capping for mixed values
                        mean_val = col_data.mean()
                        std_val = col_data.std()
                        data.loc[data[col] < mean_val - 3*std_val, col] = mean_val - 3*std_val
                        data.loc[data[col] > mean_val + 3*std_val, col] = mean_val + 3*std_val
                        fixes.append(f"Applied z-score capping to '{col}'")
                
                outliers_handled += outlier_count
            
            summary = {
                'numeric_columns_processed': len(numeric_columns),
                'outliers_handled': outliers_handled,
                'strategy_used': strategy
            }
            
            return {
                'success': True,
                'data': data,
                'fixes': fixes,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Outlier handling failed: {e}")
            return {
                'success': False,
                'warnings': [f"Outlier handling failed: {str(e)}"]
            }
    
    def _handle_inconsistencies(self,
                               data: pd.DataFrame,
                               assessment_result: Dict[str, Any],
                               config: ImprovementConfig) -> Dict[str, Any]:
        """Handle format inconsistencies in the data"""
        try:
            fixes = []
            summary = {}
            string_columns = data.select_dtypes(include=['object']).columns
            
            inconsistencies_fixed = 0
            
            for col in string_columns:
                col_data = data[col].dropna()
                if len(col_data) == 0:
                    continue
                
                original_values = set(col_data.astype(str))
                
                # Standardize case (convert to title case for names, uppercase for codes)
                if any(keyword in col.lower() for keyword in ['name', 'title', 'city', 'country']):
                    data[col] = data[col].astype(str).str.title()
                    fixes.append(f"Standardized case in '{col}' to title case")
                elif any(keyword in col.lower() for keyword in ['code', 'id', 'key']):
                    data[col] = data[col].astype(str).str.upper()
                    fixes.append(f"Standardized case in '{col}' to uppercase")
                
                # Remove leading/trailing whitespace
                original_length = len(data[col].astype(str).str.strip())
                data[col] = data[col].astype(str).str.strip()
                whitespace_fixed = original_length - len(data[col])
                if whitespace_fixed > 0:
                    fixes.append(f"Removed whitespace from '{col}'")
                    inconsistencies_fixed += whitespace_fixed
                
                # Standardize common inconsistencies
                if col.lower() in ['gender', 'sex']:
                    # Standardize gender values
                    gender_mapping = {
                        'male': 'Male', 'm': 'Male', 'man': 'Male',
                        'female': 'Female', 'f': 'Female', 'woman': 'Female'
                    }
                    data[col] = data[col].astype(str).str.lower().map(gender_mapping).fillna(data[col])
                    fixes.append(f"Standardized gender values in '{col}'")
                
                elif col.lower() in ['status', 'state']:
                    # Standardize status values
                    data[col] = data[col].astype(str).str.title()
                    fixes.append(f"Standardized status values in '{col}'")
                
                new_values = set(data[col].dropna().astype(str))
                if len(original_values) != len(new_values):
                    inconsistencies_fixed += len(original_values) - len(new_values)
            
            summary = {
                'string_columns_processed': len(string_columns),
                'inconsistencies_fixed': inconsistencies_fixed
            }
            
            return {
                'success': True,
                'data': data,
                'fixes': fixes,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Inconsistency handling failed: {e}")
            return {
                'success': False,
                'warnings': [f"Inconsistency handling failed: {str(e)}"]
            }
    
    def _normalize_text_data(self,
                           data: pd.DataFrame,
                           config: ImprovementConfig) -> Dict[str, Any]:
        """Normalize text data for consistency"""
        try:
            fixes = []
            summary = {}
            string_columns = data.select_dtypes(include=['object']).columns
            
            normalizations_applied = 0
            
            for col in string_columns:
                col_data = data[col].dropna()
                if len(col_data) == 0:
                    continue
                
                # Email normalization
                if 'email' in col.lower():
                    data[col] = data[col].astype(str).str.lower().str.strip()
                    fixes.append(f"Normalized email format in '{col}'")
                    normalizations_applied += 1
                
                # Phone number normalization
                elif 'phone' in col.lower():
                    # Remove common separators and spaces
                    data[col] = data[col].astype(str).str.replace(r'[^\d+]', '', regex=True)
                    fixes.append(f"Normalized phone format in '{col}'")
                    normalizations_applied += 1
                
                # URL normalization
                elif 'url' in col.lower() or 'website' in col.lower():
                    data[col] = data[col].astype(str).str.lower().str.strip()
                    # Add http:// if missing
                    mask = ~data[col].str.startswith(('http://', 'https://'))
                    data.loc[mask, col] = 'http://' + data.loc[mask, col]
                    fixes.append(f"Normalized URL format in '{col}'")
                    normalizations_applied += 1
                
                # Address normalization
                elif 'address' in col.lower():
                    # Standardize common abbreviations
                    address_mapping = {
                        r'\bSt\b': 'Street', r'\bAve\b': 'Avenue', 
                        r'\bRd\b': 'Road', r'\bBlvd\b': 'Boulevard'
                    }
                    for pattern, replacement in address_mapping.items():
                        data[col] = data[col].astype(str).str.replace(pattern, replacement, regex=True)
                    fixes.append(f"Normalized address format in '{col}'")
                    normalizations_applied += 1
            
            summary = {
                'columns_normalized': normalizations_applied,
                'text_columns_processed': len(string_columns)
            }
            
            return {
                'success': True,
                'data': data,
                'fixes': fixes,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Text normalization failed: {e}")
            return {
                'success': False,
                'warnings': [f"Text normalization failed: {str(e)}"]
            }
    
    def _validate_and_fix_constraints(self,
                                    data: pd.DataFrame,
                                    constraints: Dict[str, Any],
                                    config: ImprovementConfig) -> Dict[str, Any]:
        """Validate and fix constraint violations"""
        try:
            fixes = []
            summary = {}
            violations_fixed = 0
            
            for col, constraint_def in constraints.items():
                if col not in data.columns:
                    continue
                
                # Min/max constraints
                if 'min' in constraint_def:
                    min_val = constraint_def['min']
                    violations = data[col] < min_val
                    violation_count = violations.sum()
                    if violation_count > 0:
                        data.loc[violations, col] = min_val
                        fixes.append(f"Fixed {violation_count} min constraint violations in '{col}'")
                        violations_fixed += violation_count
                
                if 'max' in constraint_def:
                    max_val = constraint_def['max']
                    violations = data[col] > max_val
                    violation_count = violations.sum()
                    if violation_count > 0:
                        data.loc[violations, col] = max_val
                        fixes.append(f"Fixed {violation_count} max constraint violations in '{col}'")
                        violations_fixed += violation_count
                
                # Allowed values constraint
                if 'allowed_values' in constraint_def:
                    allowed_values = constraint_def['allowed_values']
                    violations = ~data[col].isin(allowed_values)
                    violation_count = violations.sum()
                    if violation_count > 0:
                        # Replace with most common allowed value
                        if allowed_values:
                            replacement_value = allowed_values[0]
                            data.loc[violations, col] = replacement_value
                            fixes.append(f"Fixed {violation_count} allowed values violations in '{col}'")
                            violations_fixed += violation_count
                
                # Data type constraint
                if 'data_type' in constraint_def:
                    expected_type = constraint_def['data_type']
                    try:
                        if expected_type == 'int':
                            data[col] = pd.to_numeric(data[col], errors='coerce').astype('Int64')
                        elif expected_type == 'float':
                            data[col] = pd.to_numeric(data[col], errors='coerce')
                        elif expected_type == 'string':
                            data[col] = data[col].astype(str)
                        elif expected_type == 'datetime':
                            data[col] = pd.to_datetime(data[col], errors='coerce')
                        
                        fixes.append(f"Enforced {expected_type} data type for '{col}'")
                    except Exception as type_error:
                        logger.warning(f"Could not enforce data type {expected_type} for {col}: {type_error}")
            
            summary = {
                'constraints_checked': len(constraints),
                'violations_fixed': violations_fixed
            }
            
            return {
                'success': True,
                'data': data,
                'fixes': fixes,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Constraint validation failed: {e}")
            return {
                'success': False,
                'warnings': [f"Constraint validation failed: {str(e)}"]
            }
    
    def _calculate_basic_quality_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic quality metrics for before/after comparison"""
        try:
            total_cells = data.size
            missing_cells = data.isnull().sum().sum()
            duplicate_rows = data.duplicated().sum()
            
            return {
                'total_rows': len(data),
                'total_columns': len(data.columns),
                'total_cells': total_cells,
                'missing_cells': missing_cells,
                'missing_percentage': (missing_cells / total_cells) * 100 if total_cells > 0 else 0,
                'duplicate_rows': duplicate_rows,
                'duplicate_percentage': (duplicate_rows / len(data)) * 100 if len(data) > 0 else 0,
                'completeness': ((total_cells - missing_cells) / total_cells) * 100 if total_cells > 0 else 0
            }
        except Exception as e:
            logger.error(f"Quality metrics calculation failed: {e}")
            return {}
    
    def _calculate_improvement_metrics(self,
                                     quality_before: Dict[str, Any],
                                     quality_after: Dict[str, Any],
                                     original_data: Optional[pd.DataFrame],
                                     improved_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate improvement metrics"""
        try:
            metrics = {}
            
            # Missing values improvement
            missing_before = quality_before.get('missing_percentage', 0)
            missing_after = quality_after.get('missing_percentage', 0)
            metrics['missing_values_improvement'] = missing_before - missing_after
            
            # Duplicate improvement
            duplicate_before = quality_before.get('duplicate_percentage', 0)
            duplicate_after = quality_after.get('duplicate_percentage', 0)
            metrics['duplicate_improvement'] = duplicate_before - duplicate_after
            
            # Completeness improvement
            completeness_before = quality_before.get('completeness', 0)
            completeness_after = quality_after.get('completeness', 0)
            metrics['completeness_improvement'] = completeness_after - completeness_before
            
            # Overall improvement score
            improvements = [
                metrics.get('missing_values_improvement', 0),
                metrics.get('duplicate_improvement', 0),
                metrics.get('completeness_improvement', 0) / 100  # Normalize to 0-1 scale
            ]
            metrics['overall_improvement_score'] = sum(improvements) / len(improvements)
            
            # Data shape changes
            if original_data is not None:
                metrics['rows_changed'] = len(improved_data) - len(original_data)
                metrics['columns_changed'] = len(improved_data.columns) - len(original_data.columns)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Improvement metrics calculation failed: {e}")
            return {}
    
    def get_improvement_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent improvement operations history"""
        try:
            # Sort by timestamp and return most recent
            sorted_history = sorted(
                self.improvement_history.items(),
                key=lambda x: x[1]['timestamp'],
                reverse=True
            )
            
            return [
                {
                    'improvement_id': imp_id,
                    **imp_data
                }
                for imp_id, imp_data in sorted_history[:limit]
            ]
            
        except Exception as e:
            logger.error(f"Failed to get improvement history: {e}")
            return []
    
    def _finalize_improvement_result(self,
                                   result: ImprovementResult,
                                   start_time: datetime,
                                   records_processed: int) -> ImprovementResult:
        """Finalize improvement result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update performance metrics
        result.performance_metrics['improvement_duration_seconds'] = duration
        result.performance_metrics['end_time'] = end_time
        result.performance_metrics['records_processed'] = records_processed
        
        # Update execution stats
        self.execution_stats['total_improvements'] += 1
        if result.success:
            self.execution_stats['successful_improvements'] += 1
            self.execution_stats['total_records_improved'] += records_processed
        else:
            self.execution_stats['failed_improvements'] += 1
        
        # Update average duration
        total = self.execution_stats['total_improvements']
        old_avg = self.execution_stats['average_improvement_time']
        self.execution_stats['average_improvement_time'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Quality improvement completed: success={result.success}, duration={duration:.2f}s, fixes={len(result.applied_fixes)}")
        return result
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_improvements'] / 
                max(1, self.execution_stats['total_improvements'])
            ),
            'average_records_per_improvement': (
                self.execution_stats['total_records_improved'] / 
                max(1, self.execution_stats['successful_improvements'])
            )
        }