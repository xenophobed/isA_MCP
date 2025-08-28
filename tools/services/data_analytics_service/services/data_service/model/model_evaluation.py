"""
Model Evaluation Service - Step 2 of Model Pipeline
Handles model evaluation, validation, and performance assessment
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime

try:
    from sklearn.model_selection import cross_val_score, validation_curve, learning_curve
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. Evaluation capabilities will be limited.")

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """Result of model evaluation step"""
    success: bool
    model_id: str
    evaluation_metrics: Dict[str, Any] = field(default_factory=dict)
    cross_validation_results: Dict[str, Any] = field(default_factory=dict)
    validation_analysis: Dict[str, Any] = field(default_factory=dict)
    performance_comparison: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class ModelEvaluationService:
    """
    Model Evaluation Service - Step 2 of Model Pipeline
    
    Handles:
    - Model performance evaluation using various metrics
    - Cross-validation and validation curve analysis
    - Model comparison and benchmarking
    - Performance diagnostics and recommendations
    """
    
    def __init__(self):
        self.execution_stats = {
            'total_evaluation_operations': 0,
            'successful_evaluation_operations': 0,
            'failed_evaluation_operations': 0,
            'models_evaluated': 0,
            'average_evaluation_time': 0.0
        }
        
        # Track evaluation results
        self.evaluation_results = {}
        
        logger.info("Model Evaluation Service initialized")
    
    def evaluate_model(self,
                      model_info: Dict[str, Any],
                      test_data: pd.DataFrame,
                      target_column: str,
                      evaluation_config: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        """
        Evaluate a trained model's performance
        
        Args:
            model_info: Information about the trained model
            test_data: Test dataset for evaluation
            target_column: Target variable column name
            evaluation_config: Configuration for evaluation
            
        Returns:
            EvaluationResult with comprehensive evaluation metrics
        """
        start_time = datetime.now()
        evaluation_config = evaluation_config or {}
        
        try:
            model_id = model_info.get('model_id', 'unknown')
            logger.info(f"Starting model evaluation for: {model_id}")
            
            # Initialize result
            result = EvaluationResult(
                success=False,
                model_id=model_id
            )
            
            # Validate inputs
            validation_result = self._validate_evaluation_inputs(model_info, test_data, target_column)
            if not validation_result['valid']:
                result.errors.extend(validation_result['errors'])
                return self._finalize_evaluation_result(result, start_time)
            
            # Extract model and processor
            processor = model_info.get('processor')
            model_instance = model_info.get('model_instance')
            problem_type = model_info.get('problem_type', 'classification')
            
            if not processor:
                result.errors.append("Model processor not available")
                return self._finalize_evaluation_result(result, start_time)
            
            # Prepare test data
            X_test = test_data.drop(columns=[target_column])
            y_test = test_data[target_column]
            
            # Basic evaluation metrics
            basic_metrics = self._calculate_basic_metrics(
                processor, model_instance, X_test, y_test, problem_type
            )
            
            if not basic_metrics['success']:
                result.errors.extend(basic_metrics['errors'])
                return self._finalize_evaluation_result(result, start_time)
            
            result.evaluation_metrics = basic_metrics['metrics']
            
            # Cross-validation analysis
            if evaluation_config.get('perform_cv', True) and SKLEARN_AVAILABLE:
                cv_results = self._perform_cross_validation(
                    model_info, test_data, target_column, evaluation_config
                )
                result.cross_validation_results = cv_results
            
            # Validation curve analysis
            if evaluation_config.get('validation_curves', False) and SKLEARN_AVAILABLE:
                validation_analysis = self._analyze_validation_curves(
                    model_info, test_data, target_column, evaluation_config
                )
                result.validation_analysis = validation_analysis
            
            # Performance diagnostics
            diagnostics = self._diagnose_model_performance(
                result.evaluation_metrics, problem_type, model_info
            )
            result.recommendations = diagnostics['recommendations']
            result.warnings.extend(diagnostics['warnings'])
            
            # Success
            result.success = True
            self.evaluation_results[model_id] = result
            
            return self._finalize_evaluation_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Model evaluation failed: {e}")
            result.errors.append(f"Evaluation error: {str(e)}")
            return self._finalize_evaluation_result(result, start_time)
    
    def compare_models(self,
                      model_infos: List[Dict[str, Any]],
                      test_data: pd.DataFrame,
                      target_column: str,
                      comparison_metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compare multiple models on the same test dataset"""
        try:
            comparison_metrics = comparison_metrics or ['accuracy', 'f1_score', 'r2_score']
            comparison_results = {
                'model_comparison': {},
                'ranking': {},
                'best_model': None,
                'comparison_summary': {}
            }
            
            model_performances = {}
            
            for model_info in model_infos:
                model_id = model_info.get('model_id', 'unknown')
                
                try:
                    evaluation_result = self.evaluate_model(
                        model_info, test_data, target_column, {'perform_cv': False}
                    )
                    
                    if evaluation_result.success:
                        model_performances[model_id] = {
                            'metrics': evaluation_result.evaluation_metrics,
                            'algorithm': model_info.get('training_config', {}).algorithm,
                            'problem_type': model_info.get('problem_type')
                        }
                        comparison_results['model_comparison'][model_id] = evaluation_result.evaluation_metrics
                    else:
                        logger.warning(f"Evaluation failed for model {model_id}")
                        
                except Exception as e:
                    logger.error(f"Error evaluating model {model_id}: {e}")
            
            # Rank models by performance
            if model_performances:
                rankings = self._rank_models_by_performance(model_performances, comparison_metrics)
                comparison_results['ranking'] = rankings
                
                if rankings:
                    best_model_id = rankings[0]['model_id']
                    comparison_results['best_model'] = {
                        'model_id': best_model_id,
                        'metrics': model_performances[best_model_id]['metrics'],
                        'algorithm': model_performances[best_model_id]['algorithm']
                    }
                
                # Generate comparison summary
                comparison_results['comparison_summary'] = self._generate_comparison_summary(
                    model_performances, comparison_metrics
                )
            
            return comparison_results
            
        except Exception as e:
            logger.error(f"Model comparison failed: {e}")
            return {'error': str(e)}
    
    def analyze_model_performance(self,
                                 model_id: str,
                                 detailed_analysis: bool = True) -> Dict[str, Any]:
        """Perform detailed performance analysis for a specific model"""
        try:
            if model_id not in self.evaluation_results:
                return {'error': f'No evaluation results found for model {model_id}'}
            
            result = self.evaluation_results[model_id]
            
            analysis = {
                'model_id': model_id,
                'basic_performance': result.evaluation_metrics,
                'cross_validation': result.cross_validation_results,
                'recommendations': result.recommendations,
                'warnings': result.warnings
            }
            
            if detailed_analysis:
                # Add detailed analysis
                metrics = result.evaluation_metrics
                
                # Performance categorization
                performance_category = self._categorize_performance(metrics)
                analysis['performance_category'] = performance_category
                
                # Identify potential issues
                issues = self._identify_performance_issues(metrics, result.cross_validation_results)
                analysis['potential_issues'] = issues
                
                # Improvement suggestions
                improvements = self._suggest_improvements(metrics, performance_category, issues)
                analysis['improvement_suggestions'] = improvements
            
            return analysis
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {'error': str(e)}
    
    def _validate_evaluation_inputs(self,
                                   model_info: Dict[str, Any],
                                   test_data: pd.DataFrame,
                                   target_column: str) -> Dict[str, Any]:
        """Validate evaluation inputs"""
        errors = []
        
        # Check test data
        if test_data.empty:
            errors.append("Test data is empty")
        
        # Check target column
        if target_column not in test_data.columns:
            errors.append(f"Target column '{target_column}' not found in test data")
        
        # Check model info
        if not model_info:
            errors.append("Model information is required")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _calculate_basic_metrics(self,
                                processor,
                                model_instance,
                                X_test: pd.DataFrame,
                                y_test: pd.Series,
                                problem_type: str) -> Dict[str, Any]:
        """Calculate basic evaluation metrics"""
        try:
            # Try to get predictions from the processor first
            if hasattr(processor, 'models') and model_instance:
                # Preprocess test data similar to training
                X_test_processed = processor._basic_preprocessing(X_test) if hasattr(processor, '_basic_preprocessing') else X_test
                
                # Make predictions
                y_pred = model_instance.predict(X_test_processed)
                
                # Calculate metrics based on problem type
                if problem_type == 'classification':
                    metrics = {
                        'accuracy': float(accuracy_score(y_test, y_pred)) if SKLEARN_AVAILABLE else 0.0,
                        'precision': float(precision_score(y_test, y_pred, average='weighted', zero_division=0)) if SKLEARN_AVAILABLE else 0.0,
                        'recall': float(recall_score(y_test, y_pred, average='weighted', zero_division=0)) if SKLEARN_AVAILABLE else 0.0,
                        'f1_score': float(f1_score(y_test, y_pred, average='weighted', zero_division=0)) if SKLEARN_AVAILABLE else 0.0
                    }
                    
                    # Add ROC AUC for binary classification
                    if len(np.unique(y_test)) == 2 and SKLEARN_AVAILABLE:
                        try:
                            if hasattr(model_instance, 'predict_proba'):
                                y_proba = model_instance.predict_proba(X_test_processed)[:, 1]
                                metrics['roc_auc'] = float(roc_auc_score(y_test, y_proba))
                            else:
                                metrics['roc_auc'] = float(roc_auc_score(y_test, y_pred))
                        except Exception:
                            pass  # Skip if not applicable
                    
                    # Add classification report
                    if SKLEARN_AVAILABLE:
                        try:
                            metrics['classification_report'] = classification_report(y_test, y_pred, output_dict=True)
                        except Exception:
                            pass
                
                elif problem_type in ['regression', 'time_series']:
                    metrics = {
                        'r2_score': float(r2_score(y_test, y_pred)) if SKLEARN_AVAILABLE else 0.0,
                        'mean_squared_error': float(mean_squared_error(y_test, y_pred)) if SKLEARN_AVAILABLE else 0.0,
                        'mean_absolute_error': float(mean_absolute_error(y_test, y_pred)) if SKLEARN_AVAILABLE else 0.0,
                        'root_mean_squared_error': float(np.sqrt(mean_squared_error(y_test, y_pred))) if SKLEARN_AVAILABLE else 0.0
                    }
                    
                    # Add percentage error metrics
                    if len(y_test) > 0:
                        mape = np.mean(np.abs((y_test - y_pred) / np.where(y_test != 0, y_test, 1))) * 100
                        metrics['mean_absolute_percentage_error'] = float(mape)
                
                else:
                    metrics = {
                        'error': f'Unsupported problem type: {problem_type}'
                    }
                
                return {
                    'success': True,
                    'metrics': metrics
                }
            else:
                return {
                    'success': False,
                    'errors': ['Model instance not available for evaluation']
                }
                
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Metric calculation failed: {str(e)}']
            }
    
    def _perform_cross_validation(self,
                                 model_info: Dict[str, Any],
                                 data: pd.DataFrame,
                                 target_column: str,
                                 config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform cross-validation analysis"""
        try:
            if not SKLEARN_AVAILABLE:
                return {'error': 'scikit-learn not available for cross-validation'}
            
            processor = model_info.get('processor')
            model_instance = model_info.get('model_instance')
            problem_type = model_info.get('problem_type', 'classification')
            
            if not (processor and model_instance):
                return {'error': 'Model or processor not available'}
            
            # Prepare data
            X = data.drop(columns=[target_column])
            y = data[target_column]
            X_processed = processor._basic_preprocessing(X) if hasattr(processor, '_basic_preprocessing') else X
            
            cv_folds = config.get('cv_folds', 5)
            
            # Determine scoring metric
            if problem_type == 'classification':
                scoring = 'accuracy' if y.nunique() > 2 else 'roc_auc'
            else:
                scoring = 'r2'
            
            # Perform cross-validation
            cv_scores = cross_val_score(model_instance, X_processed, y, cv=cv_folds, scoring=scoring)
            
            cv_results = {
                'scoring_metric': scoring,
                'cv_folds': cv_folds,
                'mean_score': float(cv_scores.mean()),
                'std_score': float(cv_scores.std()),
                'individual_scores': cv_scores.tolist(),
                'score_range': [float(cv_scores.min()), float(cv_scores.max())],
                'confidence_interval_95': [
                    float(cv_scores.mean() - 1.96 * cv_scores.std()),
                    float(cv_scores.mean() + 1.96 * cv_scores.std())
                ]
            }
            
            return cv_results
            
        except Exception as e:
            logger.error(f"Cross-validation failed: {e}")
            return {'error': str(e)}
    
    def _analyze_validation_curves(self,
                                  model_info: Dict[str, Any],
                                  data: pd.DataFrame,
                                  target_column: str,
                                  config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze validation curves for hyperparameter sensitivity"""
        try:
            if not SKLEARN_AVAILABLE:
                return {'error': 'scikit-learn not available for validation curves'}
            
            # This would be implemented with validation_curve from sklearn
            # For now, return placeholder
            return {
                'validation_curve_analysis': 'Not implemented in current version',
                'hyperparameter_sensitivity': {},
                'overfitting_analysis': {}
            }
            
        except Exception as e:
            logger.error(f"Validation curve analysis failed: {e}")
            return {'error': str(e)}
    
    def _diagnose_model_performance(self,
                                   metrics: Dict[str, Any],
                                   problem_type: str,
                                   model_info: Dict[str, Any]) -> Dict[str, Any]:
        """Diagnose model performance and provide recommendations"""
        recommendations = []
        warnings = []
        
        if problem_type == 'classification':
            accuracy = metrics.get('accuracy', 0)
            precision = metrics.get('precision', 0)
            recall = metrics.get('recall', 0)
            f1 = metrics.get('f1_score', 0)
            
            # Performance thresholds
            if accuracy < 0.6:
                warnings.append("Low accuracy detected")
                recommendations.append("Consider feature engineering or different algorithm")
            
            if precision < 0.5:
                warnings.append("Low precision - many false positives")
                recommendations.append("Adjust classification threshold or use precision-focused metrics")
            
            if recall < 0.5:
                warnings.append("Low recall - many false negatives")
                recommendations.append("Consider class balancing techniques or recall-focused optimization")
            
            if abs(precision - recall) > 0.2:
                warnings.append("Significant precision-recall imbalance")
                recommendations.append("Review class distribution and sampling strategy")
            
        elif problem_type in ['regression', 'time_series']:
            r2 = metrics.get('r2_score', 0)
            rmse = metrics.get('root_mean_squared_error', float('inf'))
            mae = metrics.get('mean_absolute_error', float('inf'))
            
            if r2 < 0.5:
                warnings.append("Low R² score - poor variance explanation")
                recommendations.append("Consider feature engineering or more complex models")
            
            if r2 < 0:
                warnings.append("Negative R² - model performs worse than baseline")
                recommendations.append("Review model and data preprocessing")
            
            mape = metrics.get('mean_absolute_percentage_error')
            if mape and mape > 20:
                warnings.append("High percentage error")
                recommendations.append("Consider data transformation or outlier handling")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Model performance looks good overall")
        
        return {
            'recommendations': recommendations,
            'warnings': warnings
        }
    
    def _rank_models_by_performance(self,
                                   model_performances: Dict[str, Any],
                                   metrics: List[str]) -> List[Dict[str, Any]]:
        """Rank models by performance metrics"""
        rankings = []
        
        for model_id, performance in model_performances.items():
            score = 0
            metric_count = 0
            
            model_metrics = performance['metrics']
            problem_type = performance['problem_type']
            
            # Calculate composite score
            if problem_type == 'classification':
                if 'accuracy' in model_metrics and 'accuracy' in metrics:
                    score += model_metrics['accuracy']
                    metric_count += 1
                if 'f1_score' in model_metrics and 'f1_score' in metrics:
                    score += model_metrics['f1_score']
                    metric_count += 1
            
            elif problem_type in ['regression', 'time_series']:
                if 'r2_score' in model_metrics and 'r2_score' in metrics:
                    score += max(0, model_metrics['r2_score'])  # Ensure positive
                    metric_count += 1
            
            average_score = score / max(metric_count, 1)
            
            rankings.append({
                'model_id': model_id,
                'algorithm': performance['algorithm'],
                'composite_score': average_score,
                'key_metrics': {k: v for k, v in model_metrics.items() if k in metrics}
            })
        
        # Sort by composite score (descending)
        rankings.sort(key=lambda x: x['composite_score'], reverse=True)
        
        return rankings
    
    def _generate_comparison_summary(self,
                                   model_performances: Dict[str, Any],
                                   metrics: List[str]) -> Dict[str, Any]:
        """Generate summary of model comparison"""
        summary = {
            'total_models': len(model_performances),
            'metric_summary': {},
            'performance_distribution': {}
        }
        
        # Calculate metric statistics across models
        for metric in metrics:
            metric_values = []
            for performance in model_performances.values():
                if metric in performance['metrics']:
                    metric_values.append(performance['metrics'][metric])
            
            if metric_values:
                summary['metric_summary'][metric] = {
                    'mean': float(np.mean(metric_values)),
                    'std': float(np.std(metric_values)),
                    'min': float(np.min(metric_values)),
                    'max': float(np.max(metric_values))
                }
        
        return summary
    
    def _categorize_performance(self, metrics: Dict[str, Any]) -> str:
        """Categorize model performance as excellent, good, fair, or poor"""
        # Implementation would depend on specific thresholds
        # For now, return placeholder
        return "good"
    
    def _identify_performance_issues(self,
                                   metrics: Dict[str, Any],
                                   cv_results: Dict[str, Any]) -> List[str]:
        """Identify potential performance issues"""
        issues = []
        
        # Check for overfitting signs
        if cv_results:
            cv_std = cv_results.get('std_score', 0)
            if cv_std > 0.1:
                issues.append("High variance in cross-validation scores - possible overfitting")
        
        return issues
    
    def _suggest_improvements(self,
                             metrics: Dict[str, Any],
                             performance_category: str,
                             issues: List[str]) -> List[str]:
        """Suggest specific improvements"""
        suggestions = []
        
        if performance_category in ['fair', 'poor']:
            suggestions.append("Consider hyperparameter tuning")
            suggestions.append("Try feature engineering")
            suggestions.append("Experiment with different algorithms")
        
        if 'overfitting' in ' '.join(issues).lower():
            suggestions.append("Add regularization")
            suggestions.append("Reduce model complexity")
            suggestions.append("Increase training data")
        
        return suggestions
    
    def _finalize_evaluation_result(self,
                                   result: EvaluationResult,
                                   start_time: datetime) -> EvaluationResult:
        """Finalize evaluation result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update performance metrics
        result.performance_metrics['evaluation_duration_seconds'] = duration
        result.performance_metrics['end_time'] = end_time
        
        # Update execution stats
        self.execution_stats['total_evaluation_operations'] += 1
        if result.success:
            self.execution_stats['successful_evaluation_operations'] += 1
            self.execution_stats['models_evaluated'] += 1
        else:
            self.execution_stats['failed_evaluation_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_evaluation_operations']
        old_avg = self.execution_stats['average_evaluation_time']
        self.execution_stats['average_evaluation_time'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Evaluation completed: success={result.success}, duration={duration:.2f}s")
        return result
    
    def get_evaluation_result(self, model_id: str) -> Optional[EvaluationResult]:
        """Get evaluation result for a specific model"""
        return self.evaluation_results.get(model_id)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_evaluation_operations'] / 
                max(1, self.execution_stats['total_evaluation_operations'])
            )
        }