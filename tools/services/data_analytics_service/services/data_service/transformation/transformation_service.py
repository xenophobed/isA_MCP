"""
Data Transformation Service Suite
Main orchestrator for data transformation operations following 3-step pipeline pattern
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Union
import logging
from dataclasses import dataclass, field
from datetime import datetime

from .data_aggregation import DataAggregationService
from .feature_engineering import FeatureEngineeringService  
from .business_rules import BusinessRulesService

logger = logging.getLogger(__name__)

@dataclass
class TransformationConfig:
    """Configuration for transformation operations"""
    aggregation_enabled: bool = True
    feature_engineering_enabled: bool = True
    business_rules_enabled: bool = True
    validation_level: str = "standard"  # basic, standard, strict
    preserve_original: bool = True
    batch_size: Optional[int] = None

@dataclass
class TransformationResult:
    """Result of transformation process"""
    success: bool
    transformed_data: Optional[pd.DataFrame] = None
    original_data: Optional[pd.DataFrame] = None
    transformation_summary: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class TransformationService:
    """
    Data Transformation Service Suite
    
    Orchestrates data transformation through 3 steps:
    1. Data Aggregation (grouping, summarizing, pivoting)
    2. Feature Engineering (new columns, derived metrics, encoding)
    3. Business Rules Application (domain-specific transformations)
    
    Follows the same pattern as preprocessor service for consistency.
    """
    
    def __init__(self, config: Optional[TransformationConfig] = None):
        self.config = config or TransformationConfig()
        
        # Initialize step services
        self.aggregation_service = DataAggregationService()
        self.feature_service = FeatureEngineeringService()
        self.business_service = BusinessRulesService()
        
        # Performance tracking
        self.execution_stats = {
            'total_transformations': 0,
            'successful_transformations': 0,
            'failed_transformations': 0,
            'average_duration': 0.0
        }
        
        logger.info("Data Transformation Service initialized")
    
    def transform_data(self, 
                      data: pd.DataFrame,
                      transformation_spec: Dict[str, Any],
                      config: Optional[TransformationConfig] = None) -> TransformationResult:
        """
        Execute complete transformation pipeline
        
        Args:
            data: Input DataFrame to transform
            transformation_spec: Specification of transformations to apply
            config: Optional configuration override
            
        Returns:
            TransformationResult with transformed data and metadata
        """
        start_time = datetime.now()
        config = config or self.config
        
        try:
            logger.info(f"Starting transformation pipeline for data shape: {data.shape}")
            
            # Initialize result
            result = TransformationResult(
                success=False,
                original_data=data.copy() if config.preserve_original else None,
                metadata={
                    'start_time': start_time,
                    'input_shape': data.shape,
                    'input_columns': list(data.columns),
                    'transformation_spec': transformation_spec
                }
            )
            
            current_data = data.copy()
            transformation_summary = {}
            performance_metrics = {}
            
            # Step 1: Data Aggregation
            if config.aggregation_enabled and 'aggregation' in transformation_spec:
                logger.info("Executing Step 1: Data Aggregation")
                agg_result = self.aggregation_service.aggregate_data(
                    current_data, 
                    transformation_spec['aggregation']
                )
                
                if agg_result.success:
                    current_data = agg_result.aggregated_data
                    transformation_summary['aggregation'] = agg_result.aggregation_summary
                    performance_metrics['aggregation'] = agg_result.performance_metrics
                    if agg_result.warnings:
                        result.warnings.extend(agg_result.warnings)
                else:
                    result.errors.extend(agg_result.errors)
                    result.errors.append("Step 1 (Aggregation) failed")
                    return self._finalize_result(result, start_time)
            
            # Step 2: Feature Engineering
            if config.feature_engineering_enabled and 'feature_engineering' in transformation_spec:
                logger.info("Executing Step 2: Feature Engineering")
                feature_result = self.feature_service.engineer_features(
                    current_data,
                    transformation_spec['feature_engineering']
                )
                
                if feature_result.success:
                    current_data = feature_result.engineered_data
                    transformation_summary['feature_engineering'] = feature_result.engineering_summary
                    performance_metrics['feature_engineering'] = feature_result.performance_metrics
                    if feature_result.warnings:
                        result.warnings.extend(feature_result.warnings)
                else:
                    result.errors.extend(feature_result.errors)
                    result.errors.append("Step 2 (Feature Engineering) failed")
                    return self._finalize_result(result, start_time)
            
            # Step 3: Business Rules Application
            if config.business_rules_enabled and 'business_rules' in transformation_spec:
                logger.info("Executing Step 3: Business Rules")
                rules_result = self.business_service.apply_rules(
                    current_data,
                    transformation_spec['business_rules']
                )
                
                if rules_result.success:
                    current_data = rules_result.transformed_data
                    transformation_summary['business_rules'] = rules_result.rules_summary
                    performance_metrics['business_rules'] = rules_result.performance_metrics
                    if rules_result.warnings:
                        result.warnings.extend(rules_result.warnings)
                else:
                    result.errors.extend(rules_result.errors)
                    result.errors.append("Step 3 (Business Rules) failed")
                    return self._finalize_result(result, start_time)
            
            # Final validation
            validation_results = self._validate_transformation(data, current_data, config)
            
            # Success
            result.success = True
            result.transformed_data = current_data
            result.transformation_summary = transformation_summary
            result.performance_metrics = performance_metrics
            result.validation_results = validation_results
            
            return self._finalize_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Transformation pipeline failed: {e}")
            result.errors.append(f"Pipeline error: {str(e)}")
            return self._finalize_result(result, start_time)
    
    def _validate_transformation(self, 
                                original_data: pd.DataFrame, 
                                transformed_data: pd.DataFrame,
                                config: TransformationConfig) -> Dict[str, Any]:
        """Validate transformation results"""
        try:
            validation = {
                'data_shape_changed': original_data.shape != transformed_data.shape,
                'original_shape': original_data.shape,
                'transformed_shape': transformed_data.shape,
                'columns_added': len(transformed_data.columns) - len(original_data.columns),
                'rows_changed': len(transformed_data) - len(original_data),
                'new_columns': list(set(transformed_data.columns) - set(original_data.columns)),
                'removed_columns': list(set(original_data.columns) - set(transformed_data.columns)),
                'data_types_changed': {},
                'null_counts_changed': {},
                'validation_level': config.validation_level,
                'passed': True,
                'issues': []
            }
            
            # Check data types
            common_cols = set(original_data.columns) & set(transformed_data.columns)
            for col in common_cols:
                orig_dtype = str(original_data[col].dtype)
                trans_dtype = str(transformed_data[col].dtype)
                if orig_dtype != trans_dtype:
                    validation['data_types_changed'][col] = {
                        'original': orig_dtype,
                        'transformed': trans_dtype
                    }
            
            # Check null counts
            for col in common_cols:
                orig_nulls = original_data[col].isna().sum()
                trans_nulls = transformed_data[col].isna().sum()
                if orig_nulls != trans_nulls:
                    validation['null_counts_changed'][col] = {
                        'original': orig_nulls,
                        'transformed': trans_nulls
                    }
            
            # Validation level checks
            if config.validation_level in ['standard', 'strict']:
                # Check for excessive data loss
                if len(transformed_data) < len(original_data) * 0.5:
                    validation['issues'].append("Significant data loss detected (>50%)")
                    if config.validation_level == 'strict':
                        validation['passed'] = False
                
                # Check for excessive null introduction
                for col, change in validation['null_counts_changed'].items():
                    null_increase = change['transformed'] - change['original']
                    if null_increase > len(original_data) * 0.1:
                        validation['issues'].append(f"Column '{col}' has significant null increase")
                        if config.validation_level == 'strict':
                            validation['passed'] = False
            
            return validation
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'validation_level': config.validation_level
            }
    
    def _finalize_result(self, result: TransformationResult, start_time: datetime) -> TransformationResult:
        """Finalize transformation result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update performance metrics
        result.performance_metrics['total_duration'] = duration
        result.performance_metrics['end_time'] = end_time
        result.metadata['end_time'] = end_time
        result.metadata['duration_seconds'] = duration
        
        if result.transformed_data is not None:
            result.metadata['output_shape'] = result.transformed_data.shape
            result.metadata['output_columns'] = list(result.transformed_data.columns)
        
        # Update execution stats
        self.execution_stats['total_transformations'] += 1
        if result.success:
            self.execution_stats['successful_transformations'] += 1
        else:
            self.execution_stats['failed_transformations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_transformations']
        old_avg = self.execution_stats['average_duration']
        self.execution_stats['average_duration'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Transformation completed: success={result.success}, duration={duration:.2f}s")
        return result
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_transformations'] / 
                max(1, self.execution_stats['total_transformations'])
            ),
            'individual_service_stats': {
                'aggregation': self.aggregation_service.get_execution_stats(),
                'feature_engineering': self.feature_service.get_execution_stats(),
                'business_rules': self.business_service.get_execution_stats()
            }
        }
    
    def create_transformation_spec(self, 
                                  aggregation_config: Optional[Dict] = None,
                                  feature_config: Optional[Dict] = None,
                                  business_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Helper to create transformation specification
        
        Args:
            aggregation_config: Configuration for aggregation step
            feature_config: Configuration for feature engineering step
            business_config: Configuration for business rules step
            
        Returns:
            Complete transformation specification
        """
        spec = {}
        
        if aggregation_config:
            spec['aggregation'] = aggregation_config
        if feature_config:
            spec['feature_engineering'] = feature_config
        if business_config:
            spec['business_rules'] = business_config
        
        return spec