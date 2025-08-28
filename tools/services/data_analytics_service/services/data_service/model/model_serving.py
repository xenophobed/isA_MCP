"""
Model Serving Service - Step 3 of Model Pipeline
Handles model deployment, serving, and real-time predictions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logging.warning("joblib not available. Model serialization will be limited.")

try:
    import pickle
    PICKLE_AVAILABLE = True
except ImportError:
    PICKLE_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ServingConfig:
    """Configuration for model serving"""
    model_id: str
    serving_mode: str = "batch"  # batch, real_time, api
    cache_predictions: bool = True
    cache_ttl_seconds: int = 3600
    batch_size: int = 1000
    enable_monitoring: bool = True
    preprocessing_required: bool = True

@dataclass
class ServingResult:
    """Result of model serving operations"""
    success: bool
    serving_info: Dict[str, Any] = field(default_factory=dict)
    predictions: Optional[Union[List, np.ndarray, pd.DataFrame]] = None
    serving_metadata: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class ModelCache:
    """Thread-safe model cache with TTL"""
    
    def __init__(self, max_size: int = 10, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = {}
        self.access_times = {}
        self.creation_times = {}
        self._lock = threading.RLock()
    
    def get(self, model_id: str) -> Optional[Any]:
        """Get model from cache"""
        with self._lock:
            if model_id in self.cache:
                # Check TTL
                if time.time() - self.creation_times[model_id] > self.default_ttl:
                    self._remove(model_id)
                    return None
                
                # Update access time
                self.access_times[model_id] = time.time()
                return self.cache[model_id]
            return None
    
    def put(self, model_id: str, model: Any) -> None:
        """Put model in cache"""
        with self._lock:
            # Check if we need to evict
            if len(self.cache) >= self.max_size and model_id not in self.cache:
                self._evict_lru()
            
            self.cache[model_id] = model
            self.access_times[model_id] = time.time()
            self.creation_times[model_id] = time.time()
    
    def remove(self, model_id: str) -> bool:
        """Remove model from cache"""
        with self._lock:
            return self._remove(model_id)
    
    def _remove(self, model_id: str) -> bool:
        """Internal remove method"""
        if model_id in self.cache:
            del self.cache[model_id]
            del self.access_times[model_id]
            del self.creation_times[model_id]
            return True
        return False
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if self.access_times:
            lru_model = min(self.access_times.items(), key=lambda x: x[1])[0]
            self._remove(lru_model)
    
    def clear(self) -> None:
        """Clear all cached models"""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
            self.creation_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'cache_size': len(self.cache),
                'max_size': self.max_size,
                'cached_models': list(self.cache.keys()),
                'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_access_count', 1), 1)
            }

class ModelServingService:
    """
    Model Serving Service - Step 3 of Model Pipeline
    
    Handles:
    - Model deployment and serving infrastructure
    - Real-time and batch predictions
    - Model caching and performance optimization
    - Serving monitoring and analytics
    """
    
    def __init__(self, cache_size: int = 10, cache_ttl: int = 3600):
        self.execution_stats = {
            'total_serving_operations': 0,
            'successful_serving_operations': 0,
            'failed_serving_operations': 0,
            'total_predictions_made': 0,
            'average_prediction_time': 0.0
        }
        
        # Model cache for fast serving
        self.model_cache = ModelCache(max_size=cache_size, default_ttl=cache_ttl)
        
        # Serving configuration for each model
        self.serving_configs = {}
        
        # Prediction history for monitoring
        self.prediction_history = {}
        
        # Thread pool for concurrent predictions (lazy initialized)
        self._thread_pool = None
        self._thread_pool_lock = threading.Lock()
        
        logger.info("Model Serving Service initialized")
    
    @property
    def thread_pool(self):
        """Lazy initialization of thread pool to avoid mutex issues"""
        if self._thread_pool is None:
            with self._thread_pool_lock:
                if self._thread_pool is None:
                    self._thread_pool = ThreadPoolExecutor(max_workers=4)
        return self._thread_pool
    
    def deploy_model(self,
                    model_info: Dict[str, Any],
                    serving_config: ServingConfig) -> ServingResult:
        """
        Deploy a trained model for serving
        
        Args:
            model_info: Information about the trained model
            serving_config: Configuration for serving
            
        Returns:
            ServingResult with deployment information
        """
        start_time = datetime.now()
        
        try:
            model_id = serving_config.model_id
            logger.info(f"Deploying model for serving: {model_id}")
            
            # Initialize result
            result = ServingResult(
                success=False,
                serving_metadata={
                    'start_time': start_time,
                    'model_id': model_id,
                    'serving_mode': serving_config.serving_mode
                }
            )
            
            # Validate model info
            if not model_info or 'processor' not in model_info:
                result.errors.append("Valid model information required for deployment")
                return self._finalize_serving_result(result, start_time)
            
            # Store serving configuration
            self.serving_configs[model_id] = serving_config
            
            # Load model into cache
            cache_result = self._load_model_to_cache(model_info, serving_config)
            if not cache_result['success']:
                result.errors.extend(cache_result['errors'])
                return self._finalize_serving_result(result, start_time)
            
            # Initialize prediction history
            self.prediction_history[model_id] = {
                'total_predictions': 0,
                'successful_predictions': 0,
                'failed_predictions': 0,
                'last_prediction': None,
                'deployment_time': start_time,
                'performance_metrics': {}
            }
            
            # Setup serving endpoint based on mode
            serving_setup = self._setup_serving_endpoint(serving_config)
            
            # Success
            result.success = True
            result.serving_info = {
                'model_id': model_id,
                'serving_mode': serving_config.serving_mode,
                'cache_enabled': serving_config.cache_predictions,
                'deployment_status': 'active',
                'serving_endpoint': serving_setup.get('endpoint'),
                'batch_size': serving_config.batch_size
            }
            
            return self._finalize_serving_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Model deployment failed: {e}")
            result.errors.append(f"Deployment error: {str(e)}")
            return self._finalize_serving_result(result, start_time)
    
    def predict(self,
               model_id: str,
               input_data: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]],
               prediction_config: Optional[Dict[str, Any]] = None) -> ServingResult:
        """
        Make predictions using a deployed model
        
        Args:
            model_id: ID of the deployed model
            input_data: Input data for prediction
            prediction_config: Optional configuration for prediction
            
        Returns:
            ServingResult with predictions
        """
        start_time = datetime.now()
        prediction_config = prediction_config or {}
        
        try:
            logger.info(f"Making predictions with model: {model_id}")
            
            # Initialize result
            result = ServingResult(
                success=False,
                serving_metadata={
                    'start_time': start_time,
                    'model_id': model_id,
                    'prediction_mode': 'single' if isinstance(input_data, dict) else 'batch'
                }
            )
            
            # Check if model is deployed
            if model_id not in self.serving_configs:
                result.errors.append(f"Model {model_id} is not deployed")
                return self._finalize_serving_result(result, start_time)
            
            # Get model from cache
            cached_model = self.model_cache.get(model_id)
            if not cached_model:
                result.errors.append(f"Model {model_id} not found in cache")
                return self._finalize_serving_result(result, start_time)
            
            # Prepare input data
            prepared_data = self._prepare_input_data(input_data, cached_model, prediction_config)
            if not prepared_data['success']:
                result.errors.extend(prepared_data['errors'])
                return self._finalize_serving_result(result, start_time)
            
            X_input = prepared_data['data']
            
            # Make predictions
            prediction_result = self._make_predictions(
                cached_model, X_input, model_id, prediction_config
            )
            
            if not prediction_result['success']:
                result.errors.extend(prediction_result['errors'])
                return self._finalize_serving_result(result, start_time)
            
            # Update serving statistics
            self._update_prediction_statistics(model_id, True, start_time)
            
            # Success
            result.success = True
            result.predictions = prediction_result['predictions']
            result.serving_info = {
                'model_id': model_id,
                'prediction_count': prediction_result['prediction_count'],
                'prediction_type': prediction_result['prediction_type'],
                'confidence_scores': prediction_result.get('confidence_scores'),
                'preprocessing_applied': prepared_data.get('preprocessing_applied', False)
            }
            
            return self._finalize_serving_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            result.errors.append(f"Prediction error: {str(e)}")
            self._update_prediction_statistics(model_id, False, start_time)
            return self._finalize_serving_result(result, start_time)
    
    def batch_predict(self,
                     model_id: str,
                     input_data: pd.DataFrame,
                     batch_config: Optional[Dict[str, Any]] = None) -> ServingResult:
        """Make batch predictions efficiently"""
        batch_config = batch_config or {}
        serving_config = self.serving_configs.get(model_id)
        
        if not serving_config:
            return ServingResult(
                success=False,
                errors=[f"Model {model_id} not deployed"]
            )
        
        batch_size = batch_config.get('batch_size', serving_config.batch_size)
        
        # Process in batches for large datasets
        if len(input_data) > batch_size:
            return self._process_large_batch(model_id, input_data, batch_size, batch_config)
        else:
            return self.predict(model_id, input_data, batch_config)
    
    def get_serving_status(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get serving status for models"""
        try:
            if model_id:
                # Status for specific model
                if model_id not in self.serving_configs:
                    return {'error': f'Model {model_id} not deployed'}
                
                config = self.serving_configs[model_id]
                history = self.prediction_history.get(model_id, {})
                
                return {
                    'model_id': model_id,
                    'serving_mode': config.serving_mode,
                    'deployment_time': history.get('deployment_time'),
                    'total_predictions': history.get('total_predictions', 0),
                    'success_rate': self._calculate_success_rate(history),
                    'last_prediction': history.get('last_prediction'),
                    'cache_status': 'cached' if self.model_cache.get(model_id) else 'not_cached',
                    'performance_metrics': history.get('performance_metrics', {})
                }
            else:
                # Status for all deployed models
                all_status = {}
                for mid in self.serving_configs.keys():
                    all_status[mid] = self.get_serving_status(mid)
                
                return {
                    'deployed_models': len(self.serving_configs),
                    'cache_stats': self.model_cache.get_stats(),
                    'service_stats': self.get_execution_stats(),
                    'individual_models': all_status
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def undeploy_model(self, model_id: str) -> bool:
        """Remove model from serving"""
        try:
            # Remove from cache
            self.model_cache.remove(model_id)
            
            # Remove serving config
            if model_id in self.serving_configs:
                del self.serving_configs[model_id]
            
            # Clean up prediction history
            if model_id in self.prediction_history:
                del self.prediction_history[model_id]
            
            logger.info(f"Model {model_id} undeployed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to undeploy model {model_id}: {e}")
            return False
    
    def save_model(self,
                  model_id: str,
                  file_path: str,
                  format: str = "joblib") -> bool:
        """Save a deployed model to disk"""
        try:
            cached_model = self.model_cache.get(model_id)
            if not cached_model:
                logger.error(f"Model {model_id} not found in cache")
                return False
            
            if format == "joblib" and JOBLIB_AVAILABLE:
                joblib.dump(cached_model['model_instance'], file_path)
            elif format == "pickle" and PICKLE_AVAILABLE:
                with open(file_path, 'wb') as f:
                    pickle.dump(cached_model['model_instance'], f)
            else:
                logger.error(f"Unsupported format {format} or library not available")
                return False
            
            logger.info(f"Model {model_id} saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def load_model_from_file(self,
                           model_id: str,
                           file_path: str,
                           format: str = "joblib",
                           serving_config: Optional[ServingConfig] = None) -> bool:
        """Load a model from disk for serving"""
        try:
            if format == "joblib" and JOBLIB_AVAILABLE:
                model_instance = joblib.load(file_path)
            elif format == "pickle" and PICKLE_AVAILABLE:
                with open(file_path, 'rb') as f:
                    model_instance = pickle.load(f)
            else:
                logger.error(f"Unsupported format {format} or library not available")
                return False
            
            # Create model info structure
            model_info = {
                'model_instance': model_instance,
                'processor': None,  # Would need to be provided separately
                'model_id': model_id,
                'loaded_from_file': True,
                'file_path': file_path
            }
            
            # Use default serving config if not provided
            if not serving_config:
                serving_config = ServingConfig(model_id=model_id)
            
            # Deploy the loaded model
            result = self.deploy_model(model_info, serving_config)
            return result.success
            
        except Exception as e:
            logger.error(f"Failed to load model from file: {e}")
            return False
    
    def _load_model_to_cache(self,
                           model_info: Dict[str, Any],
                           serving_config: ServingConfig) -> Dict[str, Any]:
        """Load model to cache for serving"""
        try:
            model_id = serving_config.model_id
            
            # Package model with metadata
            cached_model = {
                'model_instance': model_info.get('model_instance'),
                'processor': model_info.get('processor'),
                'problem_type': model_info.get('problem_type'),
                'target_column': model_info.get('target_column'),
                'training_config': model_info.get('training_config'),
                'loaded_at': datetime.now()
            }
            
            # Add to cache
            self.model_cache.put(model_id, cached_model)
            
            return {'success': True}
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Failed to load model to cache: {str(e)}']
            }
    
    def _setup_serving_endpoint(self, serving_config: ServingConfig) -> Dict[str, Any]:
        """Setup serving endpoint based on configuration"""
        # For now, return basic endpoint info
        # In a full implementation, this would setup REST API endpoints
        return {
            'endpoint': f'/predict/{serving_config.model_id}',
            'methods': ['POST'],
            'serving_mode': serving_config.serving_mode
        }
    
    def _prepare_input_data(self,
                          input_data: Union[pd.DataFrame, Dict, List],
                          cached_model: Dict[str, Any],
                          config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input data for prediction"""
        try:
            # Convert input to DataFrame if needed
            if isinstance(input_data, dict):
                df_input = pd.DataFrame([input_data])
            elif isinstance(input_data, list):
                df_input = pd.DataFrame(input_data)
            else:
                df_input = input_data.copy()
            
            # Apply preprocessing if available and required
            preprocessing_applied = False
            processor = cached_model.get('processor')
            
            if processor and hasattr(processor, '_basic_preprocessing'):
                df_input = processor._basic_preprocessing(df_input)
                preprocessing_applied = True
            
            return {
                'success': True,
                'data': df_input,
                'preprocessing_applied': preprocessing_applied
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Data preparation failed: {str(e)}']
            }
    
    def _make_predictions(self,
                         cached_model: Dict[str, Any],
                         X_input: pd.DataFrame,
                         model_id: str,
                         config: Dict[str, Any]) -> Dict[str, Any]:
        """Make actual predictions"""
        try:
            model_instance = cached_model['model_instance']
            
            if not model_instance:
                return {
                    'success': False,
                    'errors': ['Model instance not available']
                }
            
            # Make predictions
            predictions = model_instance.predict(X_input)
            
            result = {
                'success': True,
                'predictions': predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
                'prediction_count': len(predictions) if hasattr(predictions, '__len__') else 1,
                'prediction_type': 'batch' if len(X_input) > 1 else 'single'
            }
            
            # Add confidence scores if available
            if config.get('include_probabilities', False) and hasattr(model_instance, 'predict_proba'):
                try:
                    probabilities = model_instance.predict_proba(X_input)
                    result['confidence_scores'] = probabilities.tolist()
                except:
                    pass  # Skip if not applicable
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Prediction execution failed: {str(e)}']
            }
    
    def _process_large_batch(self,
                           model_id: str,
                           input_data: pd.DataFrame,
                           batch_size: int,
                           config: Dict[str, Any]) -> ServingResult:
        """Process large datasets in batches"""
        all_predictions = []
        total_batches = (len(input_data) + batch_size - 1) // batch_size
        
        start_time = datetime.now()
        
        try:
            for i in range(0, len(input_data), batch_size):
                batch_data = input_data.iloc[i:i+batch_size]
                
                batch_result = self.predict(model_id, batch_data, config)
                
                if batch_result.success:
                    all_predictions.extend(batch_result.predictions)
                else:
                    return ServingResult(
                        success=False,
                        errors=[f"Batch {i//batch_size + 1} failed: {batch_result.errors}"]
                    )
            
            return ServingResult(
                success=True,
                predictions=all_predictions,
                serving_info={
                    'model_id': model_id,
                    'total_predictions': len(all_predictions),
                    'batch_count': total_batches,
                    'batch_size': batch_size
                },
                performance_metrics={
                    'total_duration': (datetime.now() - start_time).total_seconds(),
                    'predictions_per_second': len(all_predictions) / max((datetime.now() - start_time).total_seconds(), 0.001)
                }
            )
            
        except Exception as e:
            return ServingResult(
                success=False,
                errors=[f"Batch processing failed: {str(e)}"]
            )
    
    def _update_prediction_statistics(self,
                                    model_id: str,
                                    success: bool,
                                    start_time: datetime):
        """Update prediction statistics"""
        if model_id in self.prediction_history:
            history = self.prediction_history[model_id]
            history['total_predictions'] += 1
            history['last_prediction'] = datetime.now()
            
            if success:
                history['successful_predictions'] += 1
            else:
                history['failed_predictions'] += 1
            
            # Update average prediction time
            duration = (datetime.now() - start_time).total_seconds()
            old_avg = history['performance_metrics'].get('average_prediction_time', 0)
            total = history['total_predictions']
            history['performance_metrics']['average_prediction_time'] = (old_avg * (total - 1) + duration) / total
    
    def _calculate_success_rate(self, history: Dict[str, Any]) -> float:
        """Calculate success rate for predictions"""
        total = history.get('total_predictions', 0)
        successful = history.get('successful_predictions', 0)
        return successful / max(total, 1)
    
    def _finalize_serving_result(self,
                               result: ServingResult,
                               start_time: datetime) -> ServingResult:
        """Finalize serving result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update performance metrics
        result.performance_metrics['serving_duration_seconds'] = duration
        result.performance_metrics['end_time'] = end_time
        result.serving_metadata['end_time'] = end_time
        result.serving_metadata['duration_seconds'] = duration
        
        # Update execution stats
        self.execution_stats['total_serving_operations'] += 1
        if result.success:
            self.execution_stats['successful_serving_operations'] += 1
            
            # Count predictions
            if result.predictions is not None:
                if hasattr(result.predictions, '__len__'):
                    self.execution_stats['total_predictions_made'] += len(result.predictions)
                else:
                    self.execution_stats['total_predictions_made'] += 1
        else:
            self.execution_stats['failed_serving_operations'] += 1
        
        # Update average prediction time
        total = self.execution_stats['total_serving_operations']
        old_avg = self.execution_stats['average_prediction_time']
        self.execution_stats['average_prediction_time'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Serving completed: success={result.success}, duration={duration:.2f}s")
        return result
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_serving_operations'] / 
                max(1, self.execution_stats['total_serving_operations'])
            ),
            'average_predictions_per_operation': (
                self.execution_stats['total_predictions_made'] / 
                max(1, self.execution_stats['successful_serving_operations'])
            )
        }
    
    def cleanup(self):
        """Cleanup serving resources"""
        try:
            # Clear model cache
            self.model_cache.clear()
            
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=True)
            
            logger.info("Model Serving Service cleanup completed")
        except Exception as e:
            logger.warning(f"Serving service cleanup warning: {e}")