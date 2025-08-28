"""
Quality Management Service Suite
Main orchestrator for data quality operations following 3-step pipeline pattern
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime

from .quality_assessment import QualityAssessmentService, AssessmentConfig, AssessmentResult
from .quality_improvement import QualityImprovementService, ImprovementConfig, ImprovementResult
from .quality_monitoring import QualityMonitoringService, MonitoringConfig, MonitoringResult

logger = logging.getLogger(__name__)

@dataclass
class QualityConfig:
    """Configuration for complete quality management operations"""
    assessment_enabled: bool = True
    improvement_enabled: bool = True
    monitoring_enabled: bool = True
    assessment_config: Optional[AssessmentConfig] = None
    improvement_config: Optional[ImprovementConfig] = None
    monitoring_config: Optional[MonitoringConfig] = None
    quality_threshold: float = 0.7
    auto_improvement: bool = False
    continuous_monitoring: bool = True

@dataclass
class QualityResult:
    """Result of complete quality management pipeline"""
    success: bool
    quality_summary: Dict[str, Any] = field(default_factory=dict)
    assessment_results: Optional[AssessmentResult] = None
    improvement_results: Optional[ImprovementResult] = None
    monitoring_results: Optional[MonitoringResult] = None
    final_data: Optional[pd.DataFrame] = None
    pipeline_summary: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class QualityManagementService:
    """
    Quality Management Service Suite
    
    Orchestrates data quality operations through 3 steps:
    1. Quality Assessment (analyze and assess data quality issues)
    2. Quality Improvement (apply fixes and improvements to data)
    3. Quality Monitoring (monitor and track quality over time)
    
    Follows the same pattern as preprocessor, transformation, storage, and model services.
    """
    
    def __init__(self, config: Optional[QualityConfig] = None, monitoring_storage_path: Optional[str] = None):
        self.config = config or QualityConfig()
        
        # Initialize step services
        self.assessment_service = QualityAssessmentService()
        self.improvement_service = QualityImprovementService()
        self.monitoring_service = QualityMonitoringService(storage_path=monitoring_storage_path)
        
        # Performance tracking
        self.execution_stats = {
            'total_quality_operations': 0,
            'successful_quality_operations': 0,
            'failed_quality_operations': 0,
            'datasets_processed': 0,
            'average_quality_improvement': 0.0,
            'average_duration': 0.0
        }
        
        logger.info("Quality Management Service initialized")
    
    def manage_data_quality(self,
                           data: pd.DataFrame,
                           dataset_info: Dict[str, Any],
                           quality_spec: Dict[str, Any],
                           config: Optional[QualityConfig] = None) -> QualityResult:
        """
        Execute complete quality management pipeline
        
        Args:
            data: Input DataFrame to manage quality for
            dataset_info: Information about the dataset (name, source, etc.)
            quality_spec: Specification of quality requirements and constraints
            config: Optional configuration override
            
        Returns:
            QualityResult with complete quality management information
        """
        start_time = datetime.now()
        config = config or self.config
        
        try:
            logger.info(f"Starting quality management for dataset: {dataset_info.get('name', 'unknown')}")
            
            # Initialize result
            result = QualityResult(
                success=False,
                metadata={
                    'start_time': start_time,
                    'dataset_name': dataset_info.get('name', 'unknown'),
                    'data_shape': data.shape,
                    'quality_spec': quality_spec
                }
            )
            
            pipeline_summary = {}
            performance_metrics = {}
            current_data = data.copy()
            
            # Step 1: Quality Assessment
            assessment_results = None
            if config.assessment_enabled:
                logger.info("Executing Step 1: Quality Assessment")
                assessment_config = self._prepare_assessment_config(quality_spec, config)
                
                assessment_results = self.assessment_service.assess_data_quality(
                    data=current_data,
                    config=assessment_config,
                    column_metadata=quality_spec.get('column_metadata')
                )
                
                if assessment_results.success:
                    pipeline_summary['assessment'] = {
                        'overall_quality_score': assessment_results.overall_quality_score,
                        'quality_issues_found': len(assessment_results.quality_issues),
                        'recommendations': assessment_results.recommendations[:3]  # Top 3
                    }
                    performance_metrics['assessment'] = assessment_results.performance_metrics
                    result.assessment_results = assessment_results
                    if assessment_results.warnings:
                        result.warnings.extend(assessment_results.warnings)
                else:
                    result.errors.extend(assessment_results.errors)
                    result.errors.append("Step 1 (Quality Assessment) failed")
                    return self._finalize_result(result, start_time, data)
            
            # Step 2: Quality Improvement (conditional based on assessment)
            improvement_results = None
            if config.improvement_enabled and assessment_results:
                logger.info("Executing Step 2: Quality Improvement")
                
                # Decide whether to apply improvements
                should_improve = (
                    config.auto_improvement or
                    assessment_results.overall_quality_score < config.quality_threshold or
                    len(assessment_results.quality_issues) > 0
                )
                
                if should_improve:
                    improvement_config = self._prepare_improvement_config(quality_spec, config, assessment_results)
                    
                    improvement_results = self.improvement_service.improve_data_quality(
                        data=current_data,
                        assessment_result=assessment_results.quality_metrics,
                        config=improvement_config,
                        constraints=quality_spec.get('constraints')
                    )
                    
                    if improvement_results.success:
                        current_data = improvement_results.improved_data
                        pipeline_summary['improvement'] = {
                            'fixes_applied': len(improvement_results.applied_fixes),
                            'quality_improvement': improvement_results.improvement_metrics.get('overall_improvement_score', 0),
                            'data_shape_change': {
                                'before': data.shape,
                                'after': current_data.shape
                            }
                        }
                        performance_metrics['improvement'] = improvement_results.performance_metrics
                        result.improvement_results = improvement_results
                        if improvement_results.warnings:
                            result.warnings.extend(improvement_results.warnings)
                    else:
                        result.errors.extend(improvement_results.errors)
                        result.warnings.append("Step 2 (Quality Improvement) failed but assessment was successful")
                        logger.warning("Quality improvement failed but assessment was successful")
                else:
                    result.warnings.append("Quality improvement skipped - quality already meets threshold")
            
            # Step 3: Quality Monitoring
            monitoring_results = None
            if config.monitoring_enabled and assessment_results:
                logger.info("Executing Step 3: Quality Monitoring")
                monitoring_config = self._prepare_monitoring_config(quality_spec, config)
                
                # Use improved data metrics if available, otherwise original assessment
                monitoring_metrics = assessment_results.quality_metrics
                if improvement_results and improvement_results.success:
                    # Perform quick assessment on improved data for monitoring
                    improved_assessment = self.assessment_service.assess_data_quality(
                        data=current_data,
                        config=assessment_config,
                        column_metadata=quality_spec.get('column_metadata')
                    )
                    if improved_assessment.success:
                        monitoring_metrics = improved_assessment.quality_metrics
                
                monitoring_results = self.monitoring_service.monitor_quality(
                    current_metrics=monitoring_metrics,
                    dataset_info=dataset_info,
                    config=monitoring_config
                )
                
                if monitoring_results.success:
                    pipeline_summary['monitoring'] = {
                        'alerts_generated': len(monitoring_results.alerts_generated),
                        'compliance_status': monitoring_results.compliance_status.get('overall_compliant', False),
                        'trending': monitoring_results.quality_trends.get('trend_analysis', 'unknown')
                    }
                    performance_metrics['monitoring'] = monitoring_results.performance_metrics
                    result.monitoring_results = monitoring_results
                    if monitoring_results.warnings:
                        result.warnings.extend(monitoring_results.warnings)
                else:
                    result.errors.extend(monitoring_results.errors)
                    result.warnings.append("Step 3 (Quality Monitoring) failed but assessment/improvement were successful")
                    logger.warning("Quality monitoring failed but assessment/improvement were successful")
            
            # Generate quality summary
            quality_summary = self._generate_quality_summary(
                assessment_results, improvement_results, monitoring_results, data, current_data
            )
            
            # Success
            result.success = True
            result.quality_summary = quality_summary
            result.final_data = current_data
            result.pipeline_summary = pipeline_summary
            result.performance_metrics = performance_metrics
            
            return self._finalize_result(result, start_time, current_data)
            
        except Exception as e:
            logger.error(f"Quality management pipeline failed: {e}")
            result.errors.append(f"Pipeline error: {str(e)}")
            return self._finalize_result(result, start_time, data)
    
    def assess_data_quality_only(self,
                                data: pd.DataFrame,
                                assessment_spec: Dict[str, Any]) -> AssessmentResult:
        """Perform quality assessment only (Step 1)"""
        try:
            assessment_config = AssessmentConfig(
                check_missing_values=assessment_spec.get('check_missing_values', True),
                check_duplicates=assessment_spec.get('check_duplicates', True),
                check_data_types=assessment_spec.get('check_data_types', True),
                check_outliers=assessment_spec.get('check_outliers', True),
                check_consistency=assessment_spec.get('check_consistency', True),
                check_completeness=assessment_spec.get('check_completeness', True),
                check_validity=assessment_spec.get('check_validity', True),
                outlier_method=assessment_spec.get('outlier_method', 'iqr')
            )
            
            return self.assessment_service.assess_data_quality(
                data=data,
                config=assessment_config,
                column_metadata=assessment_spec.get('column_metadata')
            )
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return AssessmentResult(
                success=False,
                errors=[str(e)]
            )
    
    def improve_data_quality_only(self,
                                 data: pd.DataFrame,
                                 improvement_spec: Dict[str, Any],
                                 assessment_result: Optional[Dict[str, Any]] = None) -> ImprovementResult:
        """Perform quality improvement only (Step 2)"""
        try:
            improvement_config = ImprovementConfig(
                handle_missing_values=improvement_spec.get('handle_missing_values', True),
                missing_strategy=improvement_spec.get('missing_strategy', 'auto'),
                handle_duplicates=improvement_spec.get('handle_duplicates', True),
                duplicate_strategy=improvement_spec.get('duplicate_strategy', 'remove'),
                handle_outliers=improvement_spec.get('handle_outliers', True),
                outlier_strategy=improvement_spec.get('outlier_strategy', 'cap'),
                handle_inconsistencies=improvement_spec.get('handle_inconsistencies', True),
                normalize_text=improvement_spec.get('normalize_text', True),
                validate_constraints=improvement_spec.get('validate_constraints', True)
            )
            
            # If no assessment result provided, perform quick assessment
            if assessment_result is None:
                quick_assessment = self.assess_data_quality_only(data, {})
                assessment_result = quick_assessment.quality_metrics if quick_assessment.success else {}
            
            return self.improvement_service.improve_data_quality(
                data=data,
                assessment_result=assessment_result,
                config=improvement_config,
                constraints=improvement_spec.get('constraints')
            )
            
        except Exception as e:
            logger.error(f"Quality improvement failed: {e}")
            return ImprovementResult(
                success=False,
                errors=[str(e)]
            )
    
    def get_quality_dashboard(self, dataset_name: Optional[str] = None) -> Dict[str, Any]:
        """Get quality management dashboard data"""
        try:
            return self.monitoring_service.get_quality_dashboard_data(dataset_name)
        except Exception as e:
            logger.error(f"Dashboard data retrieval failed: {e}")
            return {'error': str(e)}
    
    def get_quality_trends(self, dataset_name: str, days: int = 30) -> Dict[str, Any]:
        """Get quality trends for a specific dataset"""
        try:
            # Get historical data from monitoring service
            dashboard_data = self.monitoring_service.get_quality_dashboard_data(dataset_name)
            
            if 'quality_trends' in dashboard_data:
                return {
                    'dataset_name': dataset_name,
                    'trend_period_days': days,
                    'trends': dashboard_data['quality_trends'],
                    'latest_score': dashboard_data.get('latest_quality_scores', {}).get(dataset_name, 0)
                }
            else:
                return {'message': f'No trend data available for {dataset_name}'}
                
        except Exception as e:
            logger.error(f"Quality trends retrieval failed: {e}")
            return {'error': str(e)}
    
    def _prepare_assessment_config(self,
                                  quality_spec: Dict[str, Any],
                                  config: QualityConfig) -> AssessmentConfig:
        """Prepare assessment configuration from quality specification"""
        assessment_spec = quality_spec.get('assessment', {})
        
        return AssessmentConfig(
            check_missing_values=assessment_spec.get('check_missing_values', True),
            check_duplicates=assessment_spec.get('check_duplicates', True),
            check_data_types=assessment_spec.get('check_data_types', True),
            check_outliers=assessment_spec.get('check_outliers', True),
            check_consistency=assessment_spec.get('check_consistency', True),
            check_completeness=assessment_spec.get('check_completeness', True),
            check_validity=assessment_spec.get('check_validity', True),
            outlier_method=assessment_spec.get('outlier_method', 'iqr'),
            missing_threshold=assessment_spec.get('missing_threshold', 0.05),
            duplicate_threshold=assessment_spec.get('duplicate_threshold', 0.01)
        )
    
    def _prepare_improvement_config(self,
                                   quality_spec: Dict[str, Any],
                                   config: QualityConfig,
                                   assessment_results: AssessmentResult) -> ImprovementConfig:
        """Prepare improvement configuration based on assessment results"""
        improvement_spec = quality_spec.get('improvement', {})
        
        # Auto-configure based on assessment if not specified
        auto_missing_strategy = "auto"
        if assessment_results.quality_issues.get('missing_values'):
            missing_pct = assessment_results.quality_metrics.get('missing_values', {}).get('missing_percentage', 0)
            if missing_pct > 20:
                auto_missing_strategy = "drop"
            elif missing_pct > 10:
                auto_missing_strategy = "median"
            else:
                auto_missing_strategy = "mode"
        
        return ImprovementConfig(
            handle_missing_values=improvement_spec.get('handle_missing_values', True),
            missing_strategy=improvement_spec.get('missing_strategy', auto_missing_strategy),
            handle_duplicates=improvement_spec.get('handle_duplicates', True),
            duplicate_strategy=improvement_spec.get('duplicate_strategy', 'remove'),
            handle_outliers=improvement_spec.get('handle_outliers', True),
            outlier_strategy=improvement_spec.get('outlier_strategy', 'cap'),
            handle_inconsistencies=improvement_spec.get('handle_inconsistencies', True),
            normalize_text=improvement_spec.get('normalize_text', True),
            validate_constraints=improvement_spec.get('validate_constraints', True),
            create_backup=improvement_spec.get('create_backup', True)
        )
    
    def _prepare_monitoring_config(self,
                                  quality_spec: Dict[str, Any],
                                  config: QualityConfig) -> MonitoringConfig:
        """Prepare monitoring configuration"""
        monitoring_spec = quality_spec.get('monitoring', {})
        
        return MonitoringConfig(
            enable_alerts=monitoring_spec.get('enable_alerts', True),
            alert_thresholds=monitoring_spec.get('alert_thresholds', {
                'missing_percentage': 10.0,
                'duplicate_percentage': 5.0,
                'completeness_drop': 10.0,
                'quality_score_drop': 0.1
            }),
            monitoring_frequency=monitoring_spec.get('monitoring_frequency', 'daily'),
            store_history=monitoring_spec.get('store_history', True),
            history_retention_days=monitoring_spec.get('history_retention_days', 90),
            enable_trend_analysis=monitoring_spec.get('enable_trend_analysis', True),
            comparison_baseline=monitoring_spec.get('comparison_baseline', 'previous')
        )
    
    def _generate_quality_summary(self,
                                 assessment_results: Optional[AssessmentResult],
                                 improvement_results: Optional[ImprovementResult],
                                 monitoring_results: Optional[MonitoringResult],
                                 original_data: pd.DataFrame,
                                 final_data: pd.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive quality summary"""
        summary = {
            'quality_pipeline_executed': True,
            'original_data_shape': original_data.shape,
            'final_data_shape': final_data.shape,
            'steps_completed': []
        }
        
        # Assessment summary
        if assessment_results and assessment_results.success:
            summary['steps_completed'].append('assessment')
            summary['initial_quality_score'] = assessment_results.overall_quality_score
            summary['quality_issues_identified'] = len(assessment_results.quality_issues)
            summary['assessment_recommendations'] = assessment_results.recommendations[:5]
        
        # Improvement summary
        if improvement_results and improvement_results.success:
            summary['steps_completed'].append('improvement')
            summary['improvements_applied'] = len(improvement_results.applied_fixes)
            summary['quality_improvement_score'] = improvement_results.improvement_metrics.get('overall_improvement_score', 0)
            summary['final_quality_score'] = improvement_results.quality_after.get('overall_quality_score', 
                                                                                   assessment_results.overall_quality_score if assessment_results else 0)
        else:
            summary['final_quality_score'] = assessment_results.overall_quality_score if assessment_results else 0
        
        # Monitoring summary
        if monitoring_results and monitoring_results.success:
            summary['steps_completed'].append('monitoring')
            summary['alerts_generated'] = len(monitoring_results.alerts_generated)
            summary['compliance_status'] = monitoring_results.compliance_status.get('overall_compliant', False)
            summary['monitoring_recommendations'] = monitoring_results.recommendations[:3]
        
        # Overall assessment
        final_score = summary.get('final_quality_score', 0)
        if final_score >= 0.9:
            summary['overall_quality_level'] = 'excellent'
        elif final_score >= 0.7:
            summary['overall_quality_level'] = 'good'
        elif final_score >= 0.5:
            summary['overall_quality_level'] = 'fair'
        else:
            summary['overall_quality_level'] = 'poor'
        
        # Data changes
        if original_data.shape != final_data.shape:
            summary['data_modified'] = True
            summary['rows_changed'] = final_data.shape[0] - original_data.shape[0]
            summary['columns_changed'] = final_data.shape[1] - original_data.shape[1]
        else:
            summary['data_modified'] = False
        
        return summary
    
    def _finalize_result(self,
                        result: QualityResult,
                        start_time: datetime,
                        data: pd.DataFrame) -> QualityResult:
        """Finalize quality result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update performance metrics
        result.performance_metrics['total_duration'] = duration
        result.performance_metrics['end_time'] = end_time
        result.metadata['end_time'] = end_time
        result.metadata['duration_seconds'] = duration
        
        # Calculate quality improvement if possible
        quality_improvement = 0.0
        if result.assessment_results and result.improvement_results:
            initial_score = result.assessment_results.overall_quality_score
            final_score = result.improvement_results.quality_after.get('overall_quality_score', initial_score)
            quality_improvement = final_score - initial_score
        
        # Update execution stats
        self.execution_stats['total_quality_operations'] += 1
        if result.success:
            self.execution_stats['successful_quality_operations'] += 1
            self.execution_stats['datasets_processed'] += 1
            
            # Update average quality improvement
            old_avg = self.execution_stats['average_quality_improvement']
            successful_count = self.execution_stats['successful_quality_operations']
            self.execution_stats['average_quality_improvement'] = (old_avg * (successful_count - 1) + quality_improvement) / successful_count
        else:
            self.execution_stats['failed_quality_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_quality_operations']
        old_avg = self.execution_stats['average_duration']
        self.execution_stats['average_duration'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Quality management completed: success={result.success}, duration={duration:.2f}s, improvement={quality_improvement:.3f}")
        return result
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        try:
            return {
                'service_stats': self.get_execution_stats(),
                'individual_service_stats': {
                    'assessment': self.assessment_service.get_execution_stats(),
                    'improvement': self.improvement_service.get_execution_stats(),
                    'monitoring': self.monitoring_service.get_execution_stats()
                },
                'quality_overview': {
                    'total_datasets_processed': self.execution_stats['datasets_processed'],
                    'average_quality_improvement': self.execution_stats['average_quality_improvement']
                }
            }
        except Exception as e:
            logger.error(f"Failed to get service statistics: {e}")
            return {'error': str(e)}
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_quality_operations'] / 
                max(1, self.execution_stats['total_quality_operations'])
            )
        }
    
    def cleanup(self):
        """Cleanup all service resources"""
        try:
            # Quality management services don't require explicit cleanup
            logger.info("Quality Management Service cleanup completed")
        except Exception as e:
            logger.warning(f"Quality service cleanup warning: {e}")
    
    def create_quality_spec(self,
                           assessment_checks: Optional[Dict[str, bool]] = None,
                           improvement_strategies: Optional[Dict[str, str]] = None,
                           monitoring_thresholds: Optional[Dict[str, float]] = None,
                           constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Helper to create quality specification
        
        Args:
            assessment_checks: Which quality checks to perform
            improvement_strategies: Strategies for quality improvement
            monitoring_thresholds: Thresholds for quality monitoring
            constraints: Data constraints for validation
            
        Returns:
            Complete quality specification
        """
        spec = {}
        
        # Assessment configuration
        if assessment_checks:
            spec['assessment'] = assessment_checks
        else:
            spec['assessment'] = {
                'check_missing_values': True,
                'check_duplicates': True,
                'check_data_types': True,
                'check_outliers': True,
                'check_consistency': True,
                'check_completeness': True,
                'check_validity': True
            }
        
        # Improvement configuration
        if improvement_strategies:
            spec['improvement'] = improvement_strategies
        else:
            spec['improvement'] = {
                'missing_strategy': 'auto',
                'duplicate_strategy': 'remove',
                'outlier_strategy': 'cap',
                'normalize_text': True,
                'validate_constraints': True
            }
        
        # Monitoring configuration
        if monitoring_thresholds:
            spec['monitoring'] = {'alert_thresholds': monitoring_thresholds}
        else:
            spec['monitoring'] = {
                'alert_thresholds': {
                    'missing_percentage': 10.0,
                    'duplicate_percentage': 5.0,
                    'quality_score_drop': 0.1
                },
                'enable_trend_analysis': True,
                'store_history': True
            }
        
        # Constraints
        if constraints:
            spec['constraints'] = constraints
        
        return spec