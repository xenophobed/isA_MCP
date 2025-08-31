"""
Model Training Service - Step 1 of Model Pipeline
Handles ML model training using existing model processors
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime

# Lazy import to avoid mutex locks from ML libraries
def _get_ml_processor():
    from tools.services.data_analytics_service.processors.data_processors.model import MLProcessor
    return MLProcessor

def _get_time_series_processor():
    from tools.services.data_analytics_service.processors.data_processors.model import TimeSeriesProcessor
    return TimeSeriesProcessor

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuration for model training"""
    algorithm: str
    problem_type: Optional[str] = None  # auto-detect if None
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    cross_validation: bool = True
    cv_folds: int = 5
    test_size: float = 0.2
    preprocessing_options: Dict[str, Any] = field(default_factory=dict)
    feature_selection: bool = False
    feature_selection_method: str = "auto"

@dataclass
class TrainingResult:
    """Result of model training step"""
    success: bool
    model_info: Optional[Dict[str, Any]] = None
    training_metrics: Dict[str, Any] = field(default_factory=dict)
    model_metadata: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class ModelTrainingService:
    """
    Model Training Service - Step 1 of Model Pipeline
    
    Handles:
    - ML model training using various algorithms
    - Problem type detection and algorithm recommendation
    - Hyperparameter tuning
    - Cross-validation and model selection
    """
    
    def __init__(self):
        self.execution_stats = {
            'total_training_operations': 0,
            'successful_training_operations': 0,
            'failed_training_operations': 0,
            'models_trained': 0,
            'average_training_time': 0.0
        }
        
        # Track trained models
        self.trained_models = {}
        
        logger.info("Model Training Service initialized")
    
    def train_model(self,
                   data: pd.DataFrame,
                   target_column: str,
                   training_config: TrainingConfig) -> TrainingResult:
        """
        Train a machine learning model
        
        Args:
            data: Training dataset
            target_column: Target variable column name
            training_config: Training configuration
            
        Returns:
            TrainingResult with model information and metrics
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting model training: {training_config.algorithm}")
            
            # Initialize result
            result = TrainingResult(
                success=False,
                model_metadata={
                    'start_time': start_time,
                    'target_column': target_column,
                    'algorithm': training_config.algorithm,
                    'data_shape': data.shape
                }
            )
            
            # Validate inputs
            validation_result = self._validate_training_inputs(data, target_column, training_config)
            if not validation_result['valid']:
                result.errors.extend(validation_result['errors'])
                return self._finalize_training_result(result, start_time)
            
            # Select appropriate processor based on algorithm/problem type
            processor_result = self._get_model_processor(data, target_column, training_config)
            if not processor_result['success']:
                result.errors.extend(processor_result['errors'])
                return self._finalize_training_result(result, start_time)
            
            processor = processor_result['processor']
            detected_problem_type = processor_result['problem_type']
            
            # Execute training
            training_result = self._execute_training(
                processor, data, target_column, training_config, detected_problem_type
            )
            
            if not training_result['success']:
                result.errors.extend(training_result['errors'])
                return self._finalize_training_result(result, start_time)
            
            # Store model information
            model_id = training_result['model_id']
            self.trained_models[model_id] = {
                'processor': processor,
                'model_instance': training_result.get('model_instance'),
                'training_config': training_config,
                'target_column': target_column,
                'problem_type': detected_problem_type,
                'created_at': start_time
            }
            
            # Success
            result.success = True
            result.model_info = {
                'model_id': model_id,
                'algorithm': training_config.algorithm,
                'problem_type': detected_problem_type
            }
            result.training_metrics = training_result.get('training_metrics', {})
            result.model_metadata.update(training_result.get('metadata', {}))
            
            return self._finalize_training_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            result.errors.append(f"Training error: {str(e)}")
            return self._finalize_training_result(result, start_time)
    
    def train_multiple_models(self,
                             data: pd.DataFrame,
                             target_column: str,
                             algorithm_configs: List[TrainingConfig]) -> Dict[str, TrainingResult]:
        """Train multiple models for comparison"""
        results = {}
        
        for i, config in enumerate(algorithm_configs):
            algorithm_name = config.algorithm
            logger.info(f"Training model {i+1}/{len(algorithm_configs)}: {algorithm_name}")
            
            try:
                result = self.train_model(data, target_column, config)
                results[algorithm_name] = result
            except Exception as e:
                logger.error(f"Failed to train {algorithm_name}: {e}")
                results[algorithm_name] = TrainingResult(
                    success=False,
                    errors=[str(e)]
                )
        
        return results
    
    def get_algorithm_recommendations(self,
                                    data: pd.DataFrame,
                                    target_column: str) -> Dict[str, Any]:
        """Get ML algorithm recommendations for the dataset"""
        try:
            # Use MLProcessor for comprehensive analysis
            MLProcessor = _get_ml_processor()
            MLProcessor = _get_ml_processor()
            processor = MLProcessor(csv_processor=None, file_path=None)
            processor.df = data
            
            # Get ML analysis and recommendations
            analysis = processor.get_ml_analysis(target_column)
            
            if 'error' in analysis:
                return {'success': False, 'error': analysis['error']}
            
            return {
                'success': True,
                'problem_analysis': analysis.get('problem_analysis', {}),
                'algorithm_recommendations': analysis.get('algorithm_recommendations', {}),
                'preprocessing_recommendations': analysis.get('preprocessing_recommendations', {}),
                'data_preparation_needs': analysis.get('data_preparation', {})
            }
            
        except Exception as e:
            logger.error(f"Algorithm recommendation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def tune_hyperparameters(self,
                           data: pd.DataFrame,
                           target_column: str,
                           algorithm: str,
                           param_grid: Optional[Dict[str, Any]] = None,
                           search_type: str = "grid",
                           cv_folds: int = 5) -> TrainingResult:
        """Perform hyperparameter tuning for a specific algorithm"""
        start_time = datetime.now()
        
        try:
            # Create processor
            MLProcessor = _get_ml_processor()
            processor = MLProcessor(csv_processor=None, file_path=None)
            processor.df = data
            
            # Perform hyperparameter tuning
            tuning_result = processor.hyperparameter_tuning(
                target_column=target_column,
                algorithm=algorithm,
                param_grid=param_grid,
                search_type=search_type,
                cv_folds=cv_folds
            )
            
            if 'error' in tuning_result:
                return TrainingResult(
                    success=False,
                    errors=[tuning_result['error']]
                )
            
            # Store tuned model
            model_id = tuning_result['model_id']
            self.trained_models[model_id] = {
                'processor': processor,
                'model_instance': processor.models.get(model_id),
                'training_config': TrainingConfig(
                    algorithm=algorithm,
                    hyperparameters=tuning_result['best_parameters']
                ),
                'target_column': target_column,
                'problem_type': 'auto_detected',
                'created_at': start_time,
                'is_tuned': True
            }
            
            result = TrainingResult(
                success=True,
                model_info={
                    'model_id': model_id,
                    'algorithm': algorithm,
                    'is_hyperparameter_tuned': True
                },
                training_metrics=tuning_result,
                model_metadata={
                    'tuning_method': search_type,
                    'cv_folds': cv_folds,
                    'best_parameters': tuning_result['best_parameters'],
                    'best_score': tuning_result['best_score']
                }
            )
            
            return self._finalize_training_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Hyperparameter tuning failed: {e}")
            return TrainingResult(
                success=False,
                errors=[str(e)]
            )
    
    def _validate_training_inputs(self,
                                 data: pd.DataFrame,
                                 target_column: str,
                                 config: TrainingConfig) -> Dict[str, Any]:
        """Validate training inputs"""
        errors = []
        
        # Check data
        if data.empty:
            errors.append("Training data is empty")
        
        # Check target column
        if target_column not in data.columns:
            errors.append(f"Target column '{target_column}' not found in data")
        
        # Check algorithm
        supported_algorithms = [
            'logistic_regression', 'linear_regression', 'ridge', 'lasso',
            'random_forest_classifier', 'random_forest_regressor',
            'decision_tree_classifier', 'decision_tree_regressor',
            'svm_classifier', 'svm_regressor', 'knn_classifier', 'knn_regressor',
            'naive_bayes', 'xgboost_classifier', 'xgboost_regressor', 'prophet'
        ]
        
        if config.algorithm.lower() not in supported_algorithms:
            errors.append(f"Unsupported algorithm: {config.algorithm}")
        
        # Check test size
        if not 0 < config.test_size < 1:
            errors.append("Test size must be between 0 and 1")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _get_model_processor(self,
                           data: pd.DataFrame,
                           target_column: str,
                           config: TrainingConfig) -> Dict[str, Any]:
        """Get appropriate model processor based on algorithm and problem type"""
        try:
            algorithm = config.algorithm.lower()
            
            # Check if it's a time series problem
            if algorithm == 'prophet' or 'ds' in data.columns:
                try:
                    TimeSeriesProcessor = _get_time_series_processor()
                    processor = TimeSeriesProcessor(csv_processor=None, file_path=None)
                except Exception:
                    # Use MLProcessor for time series if TimeSeriesProcessor not available
                    MLProcessor = _get_ml_processor()
                    processor = MLProcessor(csv_processor=None, file_path=None)
                    processor.df = data
                    return {
                        'success': True,
                        'processor': processor,
                        'problem_type': 'time_series'
                    }
                processor.df = data
                return {
                    'success': True,
                    'processor': processor,
                    'problem_type': 'time_series'
                }
            
            # MLProcessor causes mutex locks due to complex dependency chains
            # Use lightweight DataFrameMLProcessor instead
            class DataFrameMLProcessor:
                """Lightweight ML processor that works directly with DataFrames"""
                def __init__(self, dataframe):
                    self.df = dataframe
                    
                def train_model(self, target_column, algorithm, test_size=0.2, **hyperparameters):
                    """Train model using sklearn directly"""
                    try:
                        from sklearn.model_selection import train_test_split
                        from sklearn.metrics import accuracy_score, r2_score, mean_squared_error
                        from sklearn.linear_model import LogisticRegression, LinearRegression
                        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
                        from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
                        import time
                        
                        start_time = time.time()
                        
                        # Prepare data
                        X = self.df.drop(columns=[target_column])
                        y = self.df[target_column]
                        
                        # Select numeric features only
                        numeric_features = X.select_dtypes(include=['int64', 'float64']).columns
                        X = X[numeric_features]
                        
                        if len(X.columns) == 0:
                            return {'error': 'No numeric features available for training'}
                        
                        # Split data
                        X_train, X_test, y_train, y_test = train_test_split(
                            X, y, test_size=test_size, random_state=42
                        )
                        
                        # Detect problem type
                        if y.dtype in ['int64', 'float64'] and y.nunique() > 10:
                            problem_type = 'regression'
                        else:
                            problem_type = 'classification'
                        
                        # Select and train model
                        if problem_type == 'classification':
                            if algorithm.lower() in ['logistic_regression', 'logistic']:
                                model = LogisticRegression(random_state=42, max_iter=1000, **hyperparameters)
                            elif algorithm.lower() in ['random_forest', 'rf']:
                                model = RandomForestClassifier(random_state=42, n_estimators=100, **hyperparameters)
                            elif algorithm.lower() in ['decision_tree', 'tree']:
                                model = DecisionTreeClassifier(random_state=42, **hyperparameters)
                            else:
                                model = LogisticRegression(random_state=42, max_iter=1000)
                        else:  # regression
                            if algorithm.lower() in ['linear_regression', 'linear']:
                                model = LinearRegression(**hyperparameters)
                            elif algorithm.lower() in ['random_forest', 'rf']:
                                model = RandomForestRegressor(random_state=42, n_estimators=100, **hyperparameters)
                            elif algorithm.lower() in ['decision_tree', 'tree']:
                                model = DecisionTreeRegressor(random_state=42, **hyperparameters)
                            else:
                                model = LinearRegression()
                        
                        # Train
                        model.fit(X_train, y_train)
                        
                        # Evaluate
                        y_pred = model.predict(X_test)
                        if problem_type == 'classification':
                            score = accuracy_score(y_test, y_pred)
                            metrics = {
                                'accuracy': float(score),
                                'test_samples': len(y_test)
                            }
                        else:
                            r2 = r2_score(y_test, y_pred)
                            mse = mean_squared_error(y_test, y_pred)
                            metrics = {
                                'r2_score': float(r2),
                                'mse': float(mse),
                                'test_samples': len(y_test)
                            }
                        
                        training_time = time.time() - start_time
                        
                        # Generate model ID
                        from datetime import datetime
                        model_id = f'{algorithm}_{int(datetime.now().timestamp())}'
                        
                        return {
                            'model_id': model_id,
                            'model_instance': model,
                            'problem_type': problem_type,
                            'metrics': metrics,
                            'features_used': list(X.columns),
                            'n_samples': len(X),
                            'train_size': len(X_train),
                            'test_size': len(X_test),
                            'training_time_seconds': training_time,
                            'algorithm': algorithm
                        }
                        
                    except Exception as e:
                        return {'error': f'Model training failed: {str(e)}'}
            
            processor = DataFrameMLProcessor(data)
            
            return {
                'success': True,
                'processor': processor,
                'problem_type': 'classification'  # Will be detected during training
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Processor initialization failed: {str(e)}"]
            }
    
    def _execute_training(self,
                         processor,
                         data: pd.DataFrame,
                         target_column: str,
                         config: TrainingConfig,
                         problem_type: str) -> Dict[str, Any]:
        """Execute the actual model training"""
        try:
            if hasattr(processor, 'train_model'):
                # Use processor's train_model method
                training_result = processor.train_model(
                    target_column=target_column,
                    algorithm=config.algorithm,
                    test_size=config.test_size,
                    **config.hyperparameters
                )
                
                if 'error' in training_result:
                    return {
                        'success': False,
                        'errors': [training_result['error']]
                    }
                
                return {
                    'success': True,
                    'model_id': training_result['model_id'],
                    'training_metrics': training_result,
                    'metadata': {
                        'algorithm': config.algorithm,
                        'problem_type': problem_type,
                        'training_time': training_result.get('training_time_seconds', 0)
                    }
                }
            else:
                return {
                    'success': False,
                    'errors': [f"Processor does not support training method"]
                }
                
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Training execution failed: {str(e)}"]
            }
    
    def _finalize_training_result(self,
                                 result: TrainingResult,
                                 start_time: datetime) -> TrainingResult:
        """Finalize training result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update performance metrics
        result.performance_metrics['training_duration_seconds'] = duration
        result.performance_metrics['end_time'] = end_time
        result.model_metadata['end_time'] = end_time
        result.model_metadata['duration_seconds'] = duration
        
        # Update execution stats
        self.execution_stats['total_training_operations'] += 1
        if result.success:
            self.execution_stats['successful_training_operations'] += 1
            self.execution_stats['models_trained'] += 1
        else:
            self.execution_stats['failed_training_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_training_operations']
        old_avg = self.execution_stats['average_training_time']
        self.execution_stats['average_training_time'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Training completed: success={result.success}, duration={duration:.2f}s")
        return result
    
    def get_trained_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a trained model"""
        return self.trained_models.get(model_id)
    
    def list_trained_models(self) -> List[Dict[str, Any]]:
        """List all trained models"""
        models_info = []
        for model_id, model_data in self.trained_models.items():
            models_info.append({
                'model_id': model_id,
                'algorithm': model_data.get('training_config').algorithm,
                'problem_type': model_data.get('problem_type'),
                'target_column': model_data.get('target_column'),
                'created_at': model_data.get('created_at'),
                'is_tuned': model_data.get('is_tuned', False)
            })
        return models_info
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_training_operations'] / 
                max(1, self.execution_stats['total_training_operations'])
            )
        }