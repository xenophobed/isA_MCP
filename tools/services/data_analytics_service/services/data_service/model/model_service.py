"""
Model Service Suite
Main orchestrator for machine learning model operations following 3-step pipeline pattern
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime

from .model_training import ModelTrainingService, TrainingConfig, TrainingResult
from .model_evaluation import ModelEvaluationService, EvaluationResult
from .model_serving import ModelServingService, ServingConfig, ServingResult

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for complete model operations"""
    training_enabled: bool = True
    evaluation_enabled: bool = True
    serving_enabled: bool = False
    training_config: Optional[TrainingConfig] = None
    evaluation_config: Optional[Dict[str, Any]] = None
    serving_config: Optional[ServingConfig] = None
    validation_level: str = "standard"  # basic, standard, strict

@dataclass
class ModelResult:
    """Result of complete model pipeline"""
    success: bool
    model_info: Optional[Dict[str, Any]] = None
    training_results: Optional[TrainingResult] = None
    evaluation_results: Optional[EvaluationResult] = None
    serving_results: Optional[ServingResult] = None
    pipeline_summary: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ModelService:
    """
    Model Service Suite
    
    Orchestrates machine learning model operations through 3 steps:
    1. Model Training (build and train ML models)
    2. Model Evaluation (evaluate and validate models)
    3. Model Serving (deploy and serve models)
    
    Follows the same pattern as preprocessor, transformation, and storage services.
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        
        # Initialize step services
        self.training_service = ModelTrainingService()
        self.evaluation_service = ModelEvaluationService()
        self.serving_service = ModelServingService()
        
        # Performance tracking
        self.execution_stats = {
            'total_model_operations': 0,
            'successful_model_operations': 0,
            'failed_model_operations': 0,
            'models_created': 0,
            'models_deployed': 0,
            'average_duration': 0.0
        }
        
        logger.info("Model Service initialized")
    
    def create_model(self,
                    training_data: pd.DataFrame,
                    target_column: str,
                    model_spec: Dict[str, Any],
                    config: Optional[ModelConfig] = None) -> ModelResult:
        """
        Execute complete model pipeline
        
        Args:
            training_data: Dataset for model training
            target_column: Target variable column name
            model_spec: Specification of model requirements
            config: Optional configuration override
            
        Returns:
            ModelResult with complete model information
        """
        start_time = datetime.now()
        config = config or self.config
        
        try:
            logger.info(f"Starting model pipeline for target: {target_column}")
            
            # Initialize result
            result = ModelResult(
                success=False,
                metadata={
                    'start_time': start_time,
                    'target_column': target_column,
                    'data_shape': training_data.shape,
                    'model_spec': model_spec
                }
            )
            
            pipeline_summary = {}
            performance_metrics = {}
            model_info = None
            
            # Step 1: Model Training
            if config.training_enabled:
                logger.info("Executing Step 1: Model Training")
                training_config = self._prepare_training_config(model_spec, config)
                
                training_result = self.training_service.train_model(
                    data=training_data,
                    target_column=target_column,
                    training_config=training_config
                )
                
                if training_result.success:
                    model_info = training_result.model_info
                    pipeline_summary['training'] = {
                        'model_id': model_info['model_id'],
                        'algorithm': model_info['algorithm'],
                        'problem_type': model_info['problem_type']
                    }
                    performance_metrics['training'] = training_result.performance_metrics
                    result.training_results = training_result
                    if training_result.warnings:
                        result.warnings.extend(training_result.warnings)
                else:
                    result.errors.extend(training_result.errors)
                    result.errors.append("Step 1 (Model Training) failed")
                    return self._finalize_result(result, start_time)
            
            # Step 2: Model Evaluation
            if config.evaluation_enabled and model_info:
                logger.info("Executing Step 2: Model Evaluation")
                
                # Split data for evaluation if not provided
                evaluation_data = self._prepare_evaluation_data(training_data, target_column, model_spec)
                evaluation_config = self._prepare_evaluation_config(model_spec, config)
                
                # Get trained model information
                trained_model = self.training_service.get_trained_model(model_info['model_id'])
                
                if trained_model:
                    evaluation_result = self.evaluation_service.evaluate_model(
                        model_info=trained_model,
                        test_data=evaluation_data,
                        target_column=target_column,
                        evaluation_config=evaluation_config
                    )
                    
                    if evaluation_result.success:
                        pipeline_summary['evaluation'] = {
                            'evaluation_metrics': evaluation_result.evaluation_metrics,
                            'cross_validation': evaluation_result.cross_validation_results
                        }
                        performance_metrics['evaluation'] = evaluation_result.performance_metrics
                        result.evaluation_results = evaluation_result
                        if evaluation_result.warnings:
                            result.warnings.extend(evaluation_result.warnings)
                    else:
                        result.errors.extend(evaluation_result.errors)
                        result.errors.append("Step 2 (Model Evaluation) failed")
                        # Don't fail the entire operation for evaluation errors
                        logger.warning("Evaluation failed but training was successful")
                else:
                    result.warnings.append("Trained model not available for evaluation")
            
            # Step 3: Model Serving (optional)
            serving_results = None
            if config.serving_enabled and model_info:
                logger.info("Executing Step 3: Model Serving")
                serving_config = self._prepare_serving_config(model_spec, config, model_info['model_id'])
                
                # Get trained model information
                trained_model = self.training_service.get_trained_model(model_info['model_id'])
                
                if trained_model:
                    serving_result = self.serving_service.deploy_model(
                        model_info=trained_model,
                        serving_config=serving_config
                    )
                    
                    if serving_result.success:
                        pipeline_summary['serving'] = {
                            'deployment_status': 'active',
                            'serving_mode': serving_config.serving_mode,
                            'serving_info': serving_result.serving_info
                        }
                        performance_metrics['serving'] = serving_result.performance_metrics
                        result.serving_results = serving_result
                        if serving_result.warnings:
                            result.warnings.extend(serving_result.warnings)
                    else:
                        result.errors.extend(serving_result.errors)
                        result.warnings.append("Step 3 (Model Serving) failed but model was trained successfully")
                        logger.warning("Serving failed but training was successful")
                else:
                    result.warnings.append("Trained model not available for serving")
            
            # Success
            result.success = True
            result.model_info = model_info
            result.pipeline_summary = pipeline_summary
            result.performance_metrics = performance_metrics
            
            return self._finalize_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Model pipeline failed: {e}")
            result.errors.append(f"Pipeline error: {str(e)}")
            return self._finalize_result(result, start_time)
    
    def compare_algorithms(self,
                          training_data: pd.DataFrame,
                          target_column: str,
                          algorithms: List[str],
                          comparison_config: Optional[Dict[str, Any]] = None) -> Dict[str, ModelResult]:
        """Create and compare multiple models with different algorithms"""
        comparison_config = comparison_config or {}
        results = {}
        
        logger.info(f"Comparing {len(algorithms)} algorithms")
        
        for algorithm in algorithms:
            algorithm_spec = {
                'training': {
                    'algorithm': algorithm,
                    'hyperparameters': comparison_config.get('hyperparameters', {}).get(algorithm, {})
                },
                'evaluation': comparison_config.get('evaluation', {}),
                'serving': comparison_config.get('serving', {})
            }
            
            try:
                result = self.create_model(
                    training_data=training_data,
                    target_column=target_column,
                    model_spec=algorithm_spec,
                    config=ModelConfig(
                        training_enabled=True,
                        evaluation_enabled=True,
                        serving_enabled=False  # Don't deploy during comparison
                    )
                )
                results[algorithm] = result
                
            except Exception as e:
                logger.error(f"Algorithm comparison failed for {algorithm}: {e}")
                results[algorithm] = ModelResult(
                    success=False,
                    errors=[str(e)]
                )
        
        return results
    
    def get_algorithm_recommendations(self,
                                    training_data: pd.DataFrame,
                                    target_column: str,
                                    preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get ML algorithm recommendations for the dataset"""
        try:
            return self.training_service.get_algorithm_recommendations(
                training_data, target_column
            )
        except Exception as e:
            logger.error(f"Algorithm recommendations failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def predict_with_model(self,
                          model_id: str,
                          input_data: pd.DataFrame,
                          prediction_config: Optional[Dict[str, Any]] = None) -> ServingResult:
        """Make predictions using a trained and deployed model"""
        try:
            return self.serving_service.predict(
                model_id=model_id,
                input_data=input_data,
                prediction_config=prediction_config
            )
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return ServingResult(
                success=False,
                errors=[str(e)]
            )
    
    def deploy_existing_model(self,
                            model_id: str,
                            serving_config: ServingConfig) -> ServingResult:
        """Deploy an existing trained model for serving"""
        try:
            # Get trained model info
            trained_model = self.training_service.get_trained_model(model_id)
            if not trained_model:
                return ServingResult(
                    success=False,
                    errors=[f"Model {model_id} not found"]
                )
            
            return self.serving_service.deploy_model(
                model_info=trained_model,
                serving_config=serving_config
            )
            
        except Exception as e:
            logger.error(f"Model deployment failed: {e}")
            return ServingResult(
                success=False,
                errors=[str(e)]
            )
    
    def get_model_performance(self, model_id: str) -> Dict[str, Any]:
        """Get comprehensive performance analysis for a model"""
        try:
            # Get evaluation results
            evaluation_result = self.evaluation_service.get_evaluation_result(model_id)
            
            # Get serving status if deployed
            serving_status = self.serving_service.get_serving_status(model_id)
            
            # Get training info
            training_info = self.training_service.get_trained_model(model_id)
            
            return {
                'model_id': model_id,
                'training_info': {
                    'algorithm': training_info.get('training_config').algorithm if training_info else None,
                    'problem_type': training_info.get('problem_type') if training_info else None,
                    'created_at': training_info.get('created_at') if training_info else None
                },
                'evaluation_metrics': evaluation_result.evaluation_metrics if evaluation_result else {},
                'serving_status': serving_status if not serving_status.get('error') else 'not_deployed',
                'performance_summary': self._generate_performance_summary(evaluation_result, serving_status)
            }
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {'error': str(e)}
    
    def list_models(self, include_performance: bool = False) -> List[Dict[str, Any]]:
        """List all models with optional performance information"""
        try:
            models = self.training_service.list_trained_models()
            
            if include_performance:
                for model in models:
                    model_id = model['model_id']
                    performance = self.get_model_performance(model_id)
                    model['performance'] = performance
            
            return models
            
        except Exception as e:
            logger.error(f"Model listing failed: {e}")
            return []
    
    def _prepare_training_config(self,
                               model_spec: Dict[str, Any],
                               config: ModelConfig) -> TrainingConfig:
        """Prepare training configuration from model specification"""
        training_spec = model_spec.get('training', {})
        
        return TrainingConfig(
            algorithm=training_spec.get('algorithm', 'random_forest_classifier'),
            problem_type=training_spec.get('problem_type'),
            hyperparameters=training_spec.get('hyperparameters', {}),
            cross_validation=training_spec.get('cross_validation', True),
            cv_folds=training_spec.get('cv_folds', 5),
            test_size=training_spec.get('test_size', 0.2),
            preprocessing_options=training_spec.get('preprocessing_options', {}),
            feature_selection=training_spec.get('feature_selection', False)
        )
    
    def _prepare_evaluation_config(self,
                                 model_spec: Dict[str, Any],
                                 config: ModelConfig) -> Dict[str, Any]:
        """Prepare evaluation configuration"""
        evaluation_spec = model_spec.get('evaluation', {})
        
        return {
            'perform_cv': evaluation_spec.get('perform_cv', True),
            'cv_folds': evaluation_spec.get('cv_folds', 5),
            'validation_curves': evaluation_spec.get('validation_curves', False),
            'comparison_metrics': evaluation_spec.get('metrics', ['accuracy', 'f1_score', 'r2_score'])
        }
    
    def _prepare_serving_config(self,
                              model_spec: Dict[str, Any],
                              config: ModelConfig,
                              model_id: str) -> ServingConfig:
        """Prepare serving configuration"""
        serving_spec = model_spec.get('serving', {})
        
        return ServingConfig(
            model_id=model_id,
            serving_mode=serving_spec.get('serving_mode', 'batch'),
            cache_predictions=serving_spec.get('cache_predictions', True),
            cache_ttl_seconds=serving_spec.get('cache_ttl', 3600),
            batch_size=serving_spec.get('batch_size', 1000),
            enable_monitoring=serving_spec.get('enable_monitoring', True),
            preprocessing_required=serving_spec.get('preprocessing_required', True)
        )
    
    def _prepare_evaluation_data(self,
                               training_data: pd.DataFrame,
                               target_column: str,
                               model_spec: Dict[str, Any]) -> pd.DataFrame:
        """Prepare evaluation data (use training data for now, in practice would be separate test set)"""
        # In a production system, this would use a separate test dataset
        # For now, return the training data (the evaluation service will handle train/test split)
        return training_data
    
    def _generate_performance_summary(self,
                                    evaluation_result: Optional[EvaluationResult],
                                    serving_status: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a performance summary"""
        summary = {
            'overall_score': 'unknown',
            'key_metrics': {},
            'deployment_status': 'not_deployed',
            'recommendations': []
        }
        
        if evaluation_result and evaluation_result.success:
            metrics = evaluation_result.evaluation_metrics
            
            # Determine overall performance score
            if 'accuracy' in metrics:
                score = metrics['accuracy']
            elif 'r2_score' in metrics:
                score = max(0, metrics['r2_score'])  # Ensure non-negative
            else:
                score = 0.5  # Default
            
            if score >= 0.8:
                summary['overall_score'] = 'excellent'
            elif score >= 0.7:
                summary['overall_score'] = 'good'
            elif score >= 0.6:
                summary['overall_score'] = 'fair'
            else:
                summary['overall_score'] = 'poor'
            
            summary['key_metrics'] = metrics
            summary['recommendations'] = evaluation_result.recommendations
        
        if not serving_status.get('error'):
            summary['deployment_status'] = 'deployed'
        
        return summary
    
    def _finalize_result(self,
                        result: ModelResult,
                        start_time: datetime) -> ModelResult:
        """Finalize model result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update performance metrics
        result.performance_metrics['total_duration'] = duration
        result.performance_metrics['end_time'] = end_time
        result.metadata['end_time'] = end_time
        result.metadata['duration_seconds'] = duration
        
        # Update execution stats
        self.execution_stats['total_model_operations'] += 1
        if result.success:
            self.execution_stats['successful_model_operations'] += 1
            self.execution_stats['models_created'] += 1
            
            # Count deployed models
            if result.serving_results and result.serving_results.success:
                self.execution_stats['models_deployed'] += 1
        else:
            self.execution_stats['failed_model_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_model_operations']
        old_avg = self.execution_stats['average_duration']
        self.execution_stats['average_duration'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Model pipeline completed: success={result.success}, duration={duration:.2f}s")
        return result
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        try:
            return {
                'service_stats': self.get_execution_stats(),
                'individual_service_stats': {
                    'training': self.training_service.get_execution_stats(),
                    'evaluation': self.evaluation_service.get_execution_stats(),
                    'serving': self.serving_service.get_execution_stats()
                },
                'model_overview': {
                    'total_models': len(self.training_service.list_trained_models()),
                    'deployed_models': len(self.serving_service.serving_configs),
                    'serving_cache_stats': self.serving_service.model_cache.get_stats()
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
                self.execution_stats['successful_model_operations'] / 
                max(1, self.execution_stats['total_model_operations'])
            ),
            'deployment_rate': (
                self.execution_stats['models_deployed'] / 
                max(1, self.execution_stats['models_created'])
            )
        }
    
    def cleanup(self):
        """Cleanup all service resources"""
        try:
            self.serving_service.cleanup()
            logger.info("Model Service cleanup completed")
        except Exception as e:
            logger.warning(f"Model service cleanup warning: {e}")
    
    def create_model_spec(self,
                         algorithm: str,
                         serving_mode: str = "batch",
                         hyperparameters: Optional[Dict[str, Any]] = None,
                         evaluation_metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Helper to create model specification
        
        Args:
            algorithm: ML algorithm to use
            serving_mode: How to serve the model
            hyperparameters: Algorithm hyperparameters
            evaluation_metrics: Metrics for evaluation
            
        Returns:
            Complete model specification
        """
        spec = {
            'training': {
                'algorithm': algorithm,
                'hyperparameters': hyperparameters or {},
                'cross_validation': True,
                'cv_folds': 5,
                'test_size': 0.2
            },
            'evaluation': {
                'perform_cv': True,
                'cv_folds': 5,
                'metrics': evaluation_metrics or ['accuracy', 'f1_score', 'r2_score']
            },
            'serving': {
                'serving_mode': serving_mode,
                'cache_predictions': True,
                'batch_size': 1000,
                'enable_monitoring': True
            }
        }
        
        return spec