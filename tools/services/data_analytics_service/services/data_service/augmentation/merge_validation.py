"""
Merge Validation Service
Step 3: Validate quality of merged/augmented data
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of merge validation"""
    success: bool
    passed: bool
    quality_score: float = 0.0
    issues_count: int = 0
    issues: List[Dict[str, Any]] = field(default_factory=list)
    validation_checks: Dict[str, bool] = field(default_factory=dict)
    duration_seconds: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'passed': self.passed,
            'quality_score': self.quality_score,
            'issues_count': self.issues_count,
            'issues': self.issues,
            'validation_checks': self.validation_checks,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message
        }

class MergeValidationService:
    """
    Merge Validation Service

    Validates quality of merged data:
    - Data completeness
    - Data consistency
    - Duplicate detection
    - Referential integrity
    - Business rule compliance
    """

    def __init__(self):
        self.validation_checks = {
            'completeness': self._check_completeness,
            'duplicates': self._check_duplicates,
            'consistency': self._check_consistency,
            'referential_integrity': self._check_referential_integrity,
            'data_types': self._check_data_types
        }
        logger.info("Merge Validation Service initialized")

    def validate_merge(self,
                      primary_data: pd.DataFrame,
                      augmented_data: pd.DataFrame,
                      validation_spec: Dict[str, Any],
                      quality_threshold: float = 0.8) -> ValidationResult:
        """
        Validate merged/augmented data quality

        Args:
            primary_data: Original primary data
            augmented_data: Augmented data after enrichment
            validation_spec: Validation configuration
            quality_threshold: Minimum acceptable quality score

        Returns:
            ValidationResult with validation status and issues
        """
        start_time = datetime.now()

        try:
            issues = []
            validation_results = {}

            # Get enabled checks
            enabled_checks = validation_spec.get('checks', list(self.validation_checks.keys()))

            # Run each validation check
            for check_name in enabled_checks:
                if check_name in self.validation_checks:
                    try:
                        logger.info(f"Running validation check: {check_name}")
                        check_method = self.validation_checks[check_name]
                        check_issues = check_method(primary_data, augmented_data, validation_spec)

                        validation_results[check_name] = len(check_issues) == 0

                        if check_issues:
                            issues.extend(check_issues)
                            logger.warning(f"Check '{check_name}' found {len(check_issues)} issues")

                    except Exception as e:
                        logger.error(f"Validation check '{check_name}' failed: {e}")
                        validation_results[check_name] = False
                        issues.append({
                            'check': check_name,
                            'severity': 'error',
                            'message': f"Check failed: {str(e)}"
                        })

            # Calculate quality score
            total_checks = len(validation_results)
            passed_checks = sum(1 for passed in validation_results.values() if passed)
            quality_score = passed_checks / total_checks if total_checks > 0 else 0.0

            # Determine if validation passed
            passed = quality_score >= quality_threshold and len(issues) == 0

            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return ValidationResult(
                success=True,
                passed=passed,
                quality_score=quality_score,
                issues_count=len(issues),
                issues=issues,
                validation_checks=validation_results,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Merge validation failed: {e}", exc_info=True)
            duration = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                success=False,
                passed=False,
                error_message=str(e),
                duration_seconds=duration
            )

    def _check_completeness(self,
                           primary_data: pd.DataFrame,
                           augmented_data: pd.DataFrame,
                           validation_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check data completeness after merge"""
        issues = []

        # Check if records were lost
        if len(augmented_data) < len(primary_data):
            issues.append({
                'check': 'completeness',
                'severity': 'error',
                'message': f"Lost records: {len(primary_data)} -> {len(augmented_data)}",
                'details': {
                    'original_count': len(primary_data),
                    'augmented_count': len(augmented_data),
                    'lost_count': len(primary_data) - len(augmented_data)
                }
            })

        # Check new fields completeness
        new_cols = [col for col in augmented_data.columns if col not in primary_data.columns]

        for col in new_cols:
            null_count = augmented_data[col].isnull().sum()
            null_rate = null_count / len(augmented_data) if len(augmented_data) > 0 else 0

            threshold = validation_spec.get('completeness_threshold', 0.5)

            if null_rate > threshold:
                issues.append({
                    'check': 'completeness',
                    'severity': 'warning',
                    'message': f"High null rate in new column '{col}': {null_rate:.1%}",
                    'details': {
                        'column': col,
                        'null_count': null_count,
                        'null_rate': null_rate,
                        'threshold': threshold
                    }
                })

        return issues

    def _check_duplicates(self,
                         primary_data: pd.DataFrame,
                         augmented_data: pd.DataFrame,
                         validation_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for duplicate records"""
        issues = []

        # Check if merge introduced duplicates
        primary_duplicates = primary_data.duplicated().sum()
        augmented_duplicates = augmented_data.duplicated().sum()

        if augmented_duplicates > primary_duplicates:
            issues.append({
                'check': 'duplicates',
                'severity': 'error',
                'message': f"Merge introduced duplicates: {primary_duplicates} -> {augmented_duplicates}",
                'details': {
                    'original_duplicates': primary_duplicates,
                    'augmented_duplicates': augmented_duplicates,
                    'new_duplicates': augmented_duplicates - primary_duplicates
                }
            })

        return issues

    def _check_consistency(self,
                          primary_data: pd.DataFrame,
                          augmented_data: pd.DataFrame,
                          validation_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check data consistency"""
        issues = []

        # Check if original columns values changed
        common_cols = [col for col in primary_data.columns if col in augmented_data.columns]

        for col in common_cols:
            if primary_data[col].dtype != augmented_data[col].dtype:
                issues.append({
                    'check': 'consistency',
                    'severity': 'warning',
                    'message': f"Data type changed for column '{col}'",
                    'details': {
                        'column': col,
                        'original_type': str(primary_data[col].dtype),
                        'augmented_type': str(augmented_data[col].dtype)
                    }
                })

            # Check value changes
            if len(primary_data) == len(augmented_data):
                matching_indices = primary_data.index[:len(augmented_data)]
                if col in primary_data.columns and col in augmented_data.columns:
                    changed_values = (primary_data.loc[matching_indices, col] != augmented_data.loc[matching_indices, col]).sum()

                    if changed_values > 0:
                        issues.append({
                            'check': 'consistency',
                            'severity': 'warning',
                            'message': f"Values changed in original column '{col}': {changed_values} records",
                            'details': {
                                'column': col,
                                'changed_count': changed_values,
                                'change_rate': changed_values / len(primary_data)
                            }
                        })

        return issues

    def _check_referential_integrity(self,
                                    primary_data: pd.DataFrame,
                                    augmented_data: pd.DataFrame,
                                    validation_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check referential integrity"""
        issues = []

        # Check foreign key constraints
        foreign_keys = validation_spec.get('foreign_keys', [])

        for fk_config in foreign_keys:
            fk_column = fk_config.get('column')
            referenced_values = fk_config.get('valid_values', [])

            if fk_column in augmented_data.columns and referenced_values:
                invalid_refs = ~augmented_data[fk_column].isin(referenced_values)
                invalid_count = invalid_refs.sum()

                if invalid_count > 0:
                    issues.append({
                        'check': 'referential_integrity',
                        'severity': 'error',
                        'message': f"Invalid foreign key values in '{fk_column}': {invalid_count} records",
                        'details': {
                            'column': fk_column,
                            'invalid_count': invalid_count,
                            'sample_invalid_values': augmented_data[invalid_refs][fk_column].unique().tolist()[:5]
                        }
                    })

        return issues

    def _check_data_types(self,
                         primary_data: pd.DataFrame,
                         augmented_data: pd.DataFrame,
                         validation_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check data types are appropriate"""
        issues = []

        # Check new columns have expected types
        expected_types = validation_spec.get('expected_types', {})

        for col, expected_type in expected_types.items():
            if col in augmented_data.columns:
                actual_type = str(augmented_data[col].dtype)

                if actual_type != expected_type:
                    issues.append({
                        'check': 'data_types',
                        'severity': 'warning',
                        'message': f"Unexpected data type for column '{col}'",
                        'details': {
                            'column': col,
                            'expected_type': expected_type,
                            'actual_type': actual_type
                        }
                    })

        return issues
