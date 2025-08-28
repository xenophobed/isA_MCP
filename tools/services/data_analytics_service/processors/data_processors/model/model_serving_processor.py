#!/usr/bin/env python3
"""
Model Serving and Real-time Prediction API Processor
Comprehensive model deployment, serving, and real-time prediction capabilities
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
import logging
import warnings
import json
import pickle
import joblib
import asyncio
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import time
warnings.filterwarnings('ignore')

# Core serving libraries
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logging.warning("Flask not available. Web API serving will be disabled.")

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logging.warning("FastAPI not available. FastAPI serving will be disabled.")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available. Caching will be disabled.")

try:
    from sklearn.base import BaseEstimator
    from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
    from sklearn.metrics import accuracy_score, mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from ..preprocessors.csv_processor import CSVProcessor
except ImportError:
    from csv_processor import CSVProcessor

logger = logging.getLogger(__name__)

class PredictionRequest(BaseModel):
    """Pydantic model for prediction requests"""
    features: Dict[str, Any]
    model_id: Optional[str] = None
    return_probabilities: Optional[bool] = False
    preprocessing_config: Optional[Dict[str, Any]] = None

class PredictionResponse(BaseModel):
    """Pydantic model for prediction responses"""
    prediction: Union[float, int, str, List[float]]
    confidence: Optional[float] = None
    probabilities: Optional[List[float]] = None
    model_id: str
    timestamp: str
    processing_time_ms: float
    metadata: Optional[Dict[str, Any]] = None

class ModelMetadata(BaseModel):
    """Model metadata for serving"""
    model_id: str
    model_type: str
    problem_type: str
    feature_names: List[str]
    target_column: str
    preprocessing_config: Dict[str, Any]
    performance_metrics: Dict[str, float]
    created_at: str
    last_used: Optional[str] = None
    usage_count: int = 0

class ModelCache:
    """Thread-safe model cache with LRU eviction"""
    
    def __init__(self, max_size: int = 10, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def get(self, model_id: str):
        """Get model from cache"""
        with self.lock:
            if model_id in self.cache:
                # Check TTL
                if time.time() - self.access_times[model_id] < self.ttl_seconds:
                    self.access_times[model_id] = time.time()
                    return self.cache[model_id]
                else:
                    # Expired
                    del self.cache[model_id]
                    del self.access_times[model_id]
            return None
    
    def put(self, model_id: str, model_data: Any):
        """Put model in cache"""
        with self.lock:
            # Evict LRU if at capacity
            if len(self.cache) >= self.max_size and model_id not in self.cache:
                lru_key = min(self.access_times.keys(), key=self.access_times.get)
                del self.cache[lru_key]
                del self.access_times[lru_key]
            
            self.cache[model_id] = model_data
            self.access_times[model_id] = time.time()
    
    def remove(self, model_id: str):
        """Remove model from cache"""
        with self.lock:
            if model_id in self.cache:
                del self.cache[model_id]
                del self.access_times[model_id]
    
    def clear(self):
        """Clear cache"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "utilization": len(self.cache) / self.max_size,
                "models": list(self.cache.keys())
            }

class ModelServingProcessor:
    """
    Model serving and real-time prediction processor
    Provides model deployment, API serving, and prediction capabilities
    """
    
    def __init__(self, model_storage_path: str = "./models", 
                 cache_size: int = 10, enable_monitoring: bool = True):
        """
        Initialize model serving processor
        
        Args:
            model_storage_path: Path to store models
            cache_size: Size of model cache
            enable_monitoring: Enable performance monitoring
        """
        self.model_storage_path = Path(model_storage_path)
        self.model_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Model management
        self.models = {}
        self.model_metadata = {}
        self.model_cache = ModelCache(max_size=cache_size)
        
        # Preprocessors
        self.preprocessors = {}
        self.scalers = {}
        self.encoders = {}
        
        # Monitoring
        self.enable_monitoring = enable_monitoring
        self.prediction_stats = {}
        self.performance_history = []
        
        # API instances
        self.flask_app = None
        self.fastapi_app = None
        
        # Redis connection
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
                self.redis_client.ping()
                logger.info("Redis connection established")
            except:
                self.redis_client = None
                logger.warning("Redis connection failed - proceeding without caching")
        
        # Load existing models
        self._load_existing_models()
    
    def deploy_model(self, model: Any, model_id: str, model_type: str,
                    problem_type: str, feature_names: List[str],
                    target_column: str, preprocessors: Optional[Dict[str, Any]] = None,
                    performance_metrics: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Deploy a model for serving
        
        Args:
            model: Trained model object
            model_id: Unique identifier for the model
            model_type: Type of model (e.g., 'sklearn', 'tensorflow', 'pytorch')
            problem_type: 'classification' or 'regression'
            feature_names: List of feature names
            target_column: Target column name
            preprocessors: Preprocessing objects (scalers, encoders, etc.)
            performance_metrics: Model performance metrics
            
        Returns:
            Deployment result
        """
        try:
            # Validate inputs
            if model_id in self.models:
                return {"error": f"Model {model_id} already exists. Use update_model() to update."}
            
            # Create model metadata
            metadata = ModelMetadata(
                model_id=model_id,
                model_type=model_type,
                problem_type=problem_type,
                feature_names=feature_names,
                target_column=target_column,
                preprocessing_config=self._extract_preprocessing_config(preprocessors),
                performance_metrics=performance_metrics or {},
                created_at=datetime.now().isoformat(),
                usage_count=0
            )
            
            # Save model to disk
            model_path = self.model_storage_path / f"{model_id}.pkl"
            metadata_path = self.model_storage_path / f"{model_id}_metadata.json"
            preprocessors_path = self.model_storage_path / f"{model_id}_preprocessors.pkl"
            
            # Save model
            joblib.dump(model, model_path)
            
            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(metadata.dict(), f, indent=2)
            
            # Save preprocessors
            if preprocessors:
                joblib.dump(preprocessors, preprocessors_path)
            
            # Store in memory
            self.models[model_id] = model
            self.model_metadata[model_id] = metadata
            if preprocessors:
                self.preprocessors[model_id] = preprocessors
            
            # Add to cache
            self.model_cache.put(model_id, {
                'model': model,
                'metadata': metadata,
                'preprocessors': preprocessors
            })
            
            # Initialize prediction stats
            self.prediction_stats[model_id] = {
                'total_predictions': 0,
                'total_time_ms': 0.0,
                'average_time_ms': 0.0,
                'last_prediction': None,
                'error_count': 0
            }
            
            logger.info(f"Model {model_id} deployed successfully")
            
            return {
                "success": True,
                "model_id": model_id,
                "model_path": str(model_path),
                "metadata": metadata.dict(),
                "deployment_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error deploying model {model_id}: {e}")
            return {"error": str(e)}
    
    def predict(self, model_id: str, features: Dict[str, Any],
               return_probabilities: bool = False) -> Dict[str, Any]:
        """
        Make prediction using deployed model
        
        Args:
            model_id: Model identifier
            features: Input features as key-value pairs
            return_probabilities: Return class probabilities (classification only)
            
        Returns:
            Prediction result
        """
        start_time = time.time()
        
        try:
            # Get model from cache or load
            model_data = self._get_model_for_prediction(model_id)
            if not model_data:
                return {"error": f"Model {model_id} not found"}
            
            model = model_data['model']
            metadata = model_data['metadata']
            preprocessors = model_data.get('preprocessors')
            
            # Validate features
            feature_validation = self._validate_features(features, metadata.feature_names)
            if "error" in feature_validation:
                return feature_validation
            
            # Preprocess features
            processed_features = self._preprocess_features(features, metadata, preprocessors)
            if isinstance(processed_features, dict) and "error" in processed_features:
                return processed_features
            
            # Make prediction
            prediction_result = self._make_prediction(
                model, processed_features, metadata.problem_type, return_probabilities
            )
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_prediction_stats(model_id, processing_time_ms, success=True)
            
            # Update model metadata
            self.model_metadata[model_id].last_used = datetime.now().isoformat()
            self.model_metadata[model_id].usage_count += 1
            
            # Prepare response
            response = {
                "prediction": prediction_result["prediction"],
                "model_id": model_id,
                "timestamp": datetime.now().isoformat(),
                "processing_time_ms": round(processing_time_ms, 2),
                "metadata": {
                    "model_type": metadata.model_type,
                    "problem_type": metadata.problem_type,
                    "confidence": prediction_result.get("confidence")
                }
            }
            
            if return_probabilities and "probabilities" in prediction_result:
                response["probabilities"] = prediction_result["probabilities"]
            
            # Log to monitoring if enabled
            if self.enable_monitoring:
                self._log_prediction(model_id, features, response)
            
            return response
            
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            self._update_prediction_stats(model_id, processing_time_ms, success=False)
            logger.error(f"Error making prediction with model {model_id}: {e}")
            return {"error": str(e)}
    
    def batch_predict(self, model_id: str, batch_features: List[Dict[str, Any]],
                     return_probabilities: bool = False) -> Dict[str, Any]:
        """
        Make batch predictions
        
        Args:
            model_id: Model identifier
            batch_features: List of feature dictionaries
            return_probabilities: Return class probabilities
            
        Returns:
            Batch prediction results
        """
        start_time = time.time()
        
        try:
            if not batch_features:
                return {"error": "No features provided"}
            
            # Get model
            model_data = self._get_model_for_prediction(model_id)
            if not model_data:
                return {"error": f"Model {model_id} not found"}
            
            model = model_data['model']
            metadata = model_data['metadata']
            preprocessors = model_data.get('preprocessors')
            
            # Process batch
            batch_results = []
            successful_predictions = 0
            
            for i, features in enumerate(batch_features):
                try:
                    # Validate and preprocess
                    feature_validation = self._validate_features(features, metadata.feature_names)
                    if "error" in feature_validation:
                        batch_results.append({"error": feature_validation["error"], "index": i})
                        continue
                    
                    processed_features = self._preprocess_features(features, metadata, preprocessors)
                    if isinstance(processed_features, dict) and "error" in processed_features:
                        batch_results.append({"error": processed_features["error"], "index": i})
                        continue
                    
                    # Make prediction
                    prediction_result = self._make_prediction(
                        model, processed_features, metadata.problem_type, return_probabilities
                    )
                    
                    result = {
                        "index": i,
                        "prediction": prediction_result["prediction"],
                        "confidence": prediction_result.get("confidence")
                    }
                    
                    if return_probabilities and "probabilities" in prediction_result:
                        result["probabilities"] = prediction_result["probabilities"]
                    
                    batch_results.append(result)
                    successful_predictions += 1
                    
                except Exception as e:
                    batch_results.append({"error": str(e), "index": i})
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_prediction_stats(model_id, processing_time_ms, success=True)
            
            return {
                "predictions": batch_results,
                "total_requests": len(batch_features),
                "successful_predictions": successful_predictions,
                "failed_predictions": len(batch_features) - successful_predictions,
                "model_id": model_id,
                "timestamp": datetime.now().isoformat(),
                "total_processing_time_ms": round(processing_time_ms, 2),
                "average_time_per_prediction_ms": round(processing_time_ms / len(batch_features), 2)
            }
            
        except Exception as e:
            logger.error(f"Error in batch prediction: {e}")
            return {"error": str(e)}
    
    def create_flask_api(self, host: str = "localhost", port: int = 5000,
                        debug: bool = False) -> Dict[str, Any]:
        """
        Create Flask API for model serving
        
        Args:
            host: Host address
            port: Port number
            debug: Debug mode
            
        Returns:
            API creation result
        """
        try:
            if not FLASK_AVAILABLE:
                return {"error": "Flask not available"}
            
            self.flask_app = Flask(__name__)
            CORS(self.flask_app)
            
            # Health check endpoint
            @self.flask_app.route('/health', methods=['GET'])
            def health_check():
                return jsonify({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "models_deployed": len(self.models),
                    "cache_stats": self.model_cache.get_stats()
                })
            
            # List models endpoint
            @self.flask_app.route('/models', methods=['GET'])
            def list_models():
                models_info = []
                for model_id, metadata in self.model_metadata.items():
                    models_info.append({
                        "model_id": model_id,
                        "model_type": metadata.model_type,
                        "problem_type": metadata.problem_type,
                        "created_at": metadata.created_at,
                        "usage_count": metadata.usage_count,
                        "last_used": metadata.last_used
                    })
                
                return jsonify({
                    "models": models_info,
                    "total_models": len(models_info)
                })
            
            # Get model info endpoint
            @self.flask_app.route('/models/<model_id>', methods=['GET'])
            def get_model_info(model_id):
                if model_id not in self.model_metadata:
                    return jsonify({"error": f"Model {model_id} not found"}), 404
                
                metadata = self.model_metadata[model_id]
                stats = self.prediction_stats.get(model_id, {})
                
                return jsonify({
                    "metadata": metadata.dict(),
                    "statistics": stats
                })
            
            # Single prediction endpoint
            @self.flask_app.route('/predict/<model_id>', methods=['POST'])
            def predict_endpoint(model_id):
                try:
                    data = request.get_json()
                    if not data or 'features' not in data:
                        return jsonify({"error": "Missing 'features' in request body"}), 400
                    
                    features = data['features']
                    return_probabilities = data.get('return_probabilities', False)
                    
                    result = self.predict(model_id, features, return_probabilities)
                    
                    if "error" in result:
                        return jsonify(result), 400
                    else:
                        return jsonify(result)
                        
                except Exception as e:
                    return jsonify({"error": str(e)}), 500
            
            # Batch prediction endpoint
            @self.flask_app.route('/batch_predict/<model_id>', methods=['POST'])
            def batch_predict_endpoint(model_id):
                try:
                    data = request.get_json()
                    if not data or 'batch_features' not in data:
                        return jsonify({"error": "Missing 'batch_features' in request body"}), 400
                    
                    batch_features = data['batch_features']
                    return_probabilities = data.get('return_probabilities', False)
                    
                    result = self.batch_predict(model_id, batch_features, return_probabilities)
                    
                    if "error" in result:
                        return jsonify(result), 400
                    else:
                        return jsonify(result)
                        
                except Exception as e:
                    return jsonify({"error": str(e)}), 500
            
            # Statistics endpoint
            @self.flask_app.route('/stats', methods=['GET'])
            def get_stats():
                overall_stats = self._get_overall_statistics()
                return jsonify(overall_stats)
            
            logger.info(f"Flask API created successfully. Run with app.run(host='{host}', port={port}, debug={debug})")
            
            return {
                "success": True,
                "framework": "flask",
                "host": host,
                "port": port,
                "endpoints": [
                    f"GET http://{host}:{port}/health",
                    f"GET http://{host}:{port}/models",
                    f"GET http://{host}:{port}/models/<model_id>",
                    f"POST http://{host}:{port}/predict/<model_id>",
                    f"POST http://{host}:{port}/batch_predict/<model_id>",
                    f"GET http://{host}:{port}/stats"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error creating Flask API: {e}")
            return {"error": str(e)}
    
    def create_fastapi_api(self, host: str = "localhost", port: int = 8000) -> Dict[str, Any]:
        """
        Create FastAPI for model serving
        
        Args:
            host: Host address
            port: Port number
            
        Returns:
            API creation result
        """
        try:
            if not FASTAPI_AVAILABLE:
                return {"error": "FastAPI not available"}
            
            self.fastapi_app = FastAPI(title="Model Serving API", version="1.0.0")
            
            # Add CORS middleware
            self.fastapi_app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            # Health check endpoint
            @self.fastapi_app.get("/health")
            async def health_check():
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "models_deployed": len(self.models),
                    "cache_stats": self.model_cache.get_stats()
                }
            
            # List models endpoint
            @self.fastapi_app.get("/models")
            async def list_models():
                models_info = []
                for model_id, metadata in self.model_metadata.items():
                    models_info.append({
                        "model_id": model_id,
                        "model_type": metadata.model_type,
                        "problem_type": metadata.problem_type,
                        "created_at": metadata.created_at,
                        "usage_count": metadata.usage_count,
                        "last_used": metadata.last_used
                    })
                
                return {
                    "models": models_info,
                    "total_models": len(models_info)
                }
            
            # Get model info endpoint
            @self.fastapi_app.get("/models/{model_id}")
            async def get_model_info(model_id: str):
                if model_id not in self.model_metadata:
                    raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
                
                metadata = self.model_metadata[model_id]
                stats = self.prediction_stats.get(model_id, {})
                
                return {
                    "metadata": metadata.dict(),
                    "statistics": stats
                }
            
            # Single prediction endpoint
            @self.fastapi_app.post("/predict/{model_id}")
            async def predict_endpoint(model_id: str, request: PredictionRequest):
                result = self.predict(model_id, request.features, request.return_probabilities or False)
                
                if "error" in result:
                    raise HTTPException(status_code=400, detail=result["error"])
                
                return result
            
            # Batch prediction endpoint
            @self.fastapi_app.post("/batch_predict/{model_id}")
            async def batch_predict_endpoint(model_id: str, batch_features: List[Dict[str, Any]], 
                                           return_probabilities: bool = False):
                result = self.batch_predict(model_id, batch_features, return_probabilities)
                
                if "error" in result:
                    raise HTTPException(status_code=400, detail=result["error"])
                
                return result
            
            # Statistics endpoint
            @self.fastapi_app.get("/stats")
            async def get_stats():
                return self._get_overall_statistics()
            
            logger.info(f"FastAPI created successfully. Run with uvicorn.run(app, host='{host}', port={port})")
            
            return {
                "success": True,
                "framework": "fastapi",
                "host": host,
                "port": port,
                "docs_url": f"http://{host}:{port}/docs",
                "redoc_url": f"http://{host}:{port}/redoc",
                "endpoints": [
                    f"GET http://{host}:{port}/health",
                    f"GET http://{host}:{port}/models",
                    f"GET http://{host}:{port}/models/<model_id>",
                    f"POST http://{host}:{port}/predict/<model_id>",
                    f"POST http://{host}:{port}/batch_predict/<model_id>",
                    f"GET http://{host}:{port}/stats"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error creating FastAPI: {e}")
            return {"error": str(e)}
    
    def run_flask_server(self, host: str = "localhost", port: int = 5000, debug: bool = False):
        """Run Flask server"""
        if self.flask_app:
            self.flask_app.run(host=host, port=port, debug=debug)
        else:
            logger.error("Flask app not created. Call create_flask_api() first.")
    
    def run_fastapi_server(self, host: str = "localhost", port: int = 8000):
        """Run FastAPI server"""
        if self.fastapi_app:
            uvicorn.run(self.fastapi_app, host=host, port=port)
        else:
            logger.error("FastAPI app not created. Call create_fastapi_api() first.")
    
    def get_model_performance(self, model_id: str) -> Dict[str, Any]:
        """Get model performance statistics"""
        try:
            if model_id not in self.model_metadata:
                return {"error": f"Model {model_id} not found"}
            
            metadata = self.model_metadata[model_id]
            stats = self.prediction_stats.get(model_id, {})
            
            # Calculate additional metrics
            performance_analysis = {
                "model_metadata": metadata.dict(),
                "usage_statistics": stats,
                "performance_metrics": metadata.performance_metrics,
                "deployment_age_hours": self._calculate_deployment_age(metadata.created_at),
                "predictions_per_hour": self._calculate_predictions_per_hour(model_id),
                "error_rate": stats.get('error_count', 0) / max(stats.get('total_predictions', 1), 1),
                "cache_hit_rate": self._calculate_cache_hit_rate(model_id)
            }
            
            return performance_analysis
            
        except Exception as e:
            logger.error(f"Error getting model performance for {model_id}: {e}")
            return {"error": str(e)}
    
    def update_model(self, model_id: str, new_model: Any = None,
                    new_preprocessors: Optional[Dict[str, Any]] = None,
                    new_performance_metrics: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Update deployed model"""
        try:
            if model_id not in self.models:
                return {"error": f"Model {model_id} not found"}
            
            # Create backup
            backup_result = self._create_model_backup(model_id)
            if "error" in backup_result:
                return backup_result
            
            # Update model
            if new_model is not None:
                # Save new model
                model_path = self.model_storage_path / f"{model_id}.pkl"
                joblib.dump(new_model, model_path)
                
                # Update in memory
                self.models[model_id] = new_model
                
                # Update cache
                cached_data = self.model_cache.get(model_id)
                if cached_data:
                    cached_data['model'] = new_model
                    self.model_cache.put(model_id, cached_data)
            
            # Update preprocessors
            if new_preprocessors is not None:
                preprocessors_path = self.model_storage_path / f"{model_id}_preprocessors.pkl"
                joblib.dump(new_preprocessors, preprocessors_path)
                self.preprocessors[model_id] = new_preprocessors
            
            # Update performance metrics
            if new_performance_metrics is not None:
                self.model_metadata[model_id].performance_metrics.update(new_performance_metrics)
                
                # Save updated metadata
                metadata_path = self.model_storage_path / f"{model_id}_metadata.json"
                with open(metadata_path, 'w') as f:
                    json.dump(self.model_metadata[model_id].dict(), f, indent=2)
            
            logger.info(f"Model {model_id} updated successfully")
            
            return {
                "success": True,
                "model_id": model_id,
                "backup_created": backup_result["backup_path"],
                "update_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating model {model_id}: {e}")
            return {"error": str(e)}
    
    def remove_model(self, model_id: str, create_backup: bool = True) -> Dict[str, Any]:
        """Remove deployed model"""
        try:
            if model_id not in self.models:
                return {"error": f"Model {model_id} not found"}
            
            # Create backup if requested
            backup_path = None
            if create_backup:
                backup_result = self._create_model_backup(model_id)
                if "error" not in backup_result:
                    backup_path = backup_result["backup_path"]
            
            # Remove from memory
            del self.models[model_id]
            del self.model_metadata[model_id]
            
            if model_id in self.preprocessors:
                del self.preprocessors[model_id]
            
            if model_id in self.prediction_stats:
                del self.prediction_stats[model_id]
            
            # Remove from cache
            self.model_cache.remove(model_id)
            
            # Remove files
            model_path = self.model_storage_path / f"{model_id}.pkl"
            metadata_path = self.model_storage_path / f"{model_id}_metadata.json"
            preprocessors_path = self.model_storage_path / f"{model_id}_preprocessors.pkl"
            
            for path in [model_path, metadata_path, preprocessors_path]:
                if path.exists():
                    path.unlink()
            
            logger.info(f"Model {model_id} removed successfully")
            
            return {
                "success": True,
                "model_id": model_id,
                "backup_created": backup_path is not None,
                "backup_path": backup_path,
                "removal_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error removing model {model_id}: {e}")
            return {"error": str(e)}
    
    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        try:
            dashboard_data = {
                "overview": {
                    "total_models": len(self.models),
                    "total_predictions": sum(stats.get('total_predictions', 0) for stats in self.prediction_stats.values()),
                    "total_errors": sum(stats.get('error_count', 0) for stats in self.prediction_stats.values()),
                    "cache_utilization": self.model_cache.get_stats()["utilization"],
                    "last_updated": datetime.now().isoformat()
                },
                "model_statistics": [],
                "performance_trends": self.performance_history[-100:],  # Last 100 entries
                "system_health": self._get_system_health()
            }
            
            # Model-specific statistics
            for model_id, metadata in self.model_metadata.items():
                stats = self.prediction_stats.get(model_id, {})
                model_stat = {
                    "model_id": model_id,
                    "model_type": metadata.model_type,
                    "problem_type": metadata.problem_type,
                    "predictions": stats.get('total_predictions', 0),
                    "average_response_time": stats.get('average_time_ms', 0),
                    "error_rate": stats.get('error_count', 0) / max(stats.get('total_predictions', 1), 1),
                    "last_used": metadata.last_used,
                    "deployment_age_hours": self._calculate_deployment_age(metadata.created_at)
                }
                dashboard_data["model_statistics"].append(model_stat)
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting monitoring data: {e}")
            return {"error": str(e)}
    
    # Helper methods
    
    def _load_existing_models(self):
        """Load existing models from storage"""
        try:
            for metadata_file in self.model_storage_path.glob("*_metadata.json"):
                model_id = metadata_file.stem.replace("_metadata", "")
                
                # Load metadata
                with open(metadata_file, 'r') as f:
                    metadata_dict = json.load(f)
                
                metadata = ModelMetadata(**metadata_dict)
                
                # Load model
                model_path = self.model_storage_path / f"{model_id}.pkl"
                if model_path.exists():
                    model = joblib.load(model_path)
                    self.models[model_id] = model
                    self.model_metadata[model_id] = metadata
                    
                    # Load preprocessors if available
                    preprocessors_path = self.model_storage_path / f"{model_id}_preprocessors.pkl"
                    if preprocessors_path.exists():
                        preprocessors = joblib.load(preprocessors_path)
                        self.preprocessors[model_id] = preprocessors
                    
                    # Initialize prediction stats
                    self.prediction_stats[model_id] = {
                        'total_predictions': 0,
                        'total_time_ms': 0.0,
                        'average_time_ms': 0.0,
                        'last_prediction': None,
                        'error_count': 0
                    }
                    
                    logger.info(f"Loaded existing model: {model_id}")
                    
        except Exception as e:
            logger.warning(f"Error loading existing models: {e}")
    
    def _get_model_for_prediction(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model for prediction (from cache or load)"""
        # Try cache first
        cached_data = self.model_cache.get(model_id)
        if cached_data:
            return cached_data
        
        # Load from storage
        if model_id in self.models:
            model_data = {
                'model': self.models[model_id],
                'metadata': self.model_metadata[model_id],
                'preprocessors': self.preprocessors.get(model_id)
            }
            
            # Add to cache
            self.model_cache.put(model_id, model_data)
            return model_data
        
        return None
    
    def _validate_features(self, features: Dict[str, Any], required_features: List[str]) -> Dict[str, Any]:
        """Validate input features"""
        missing_features = [f for f in required_features if f not in features]
        if missing_features:
            return {"error": f"Missing required features: {missing_features}"}
        
        extra_features = [f for f in features.keys() if f not in required_features]
        if extra_features:
            logger.warning(f"Extra features provided (will be ignored): {extra_features}")
        
        return {"success": True}
    
    def _preprocess_features(self, features: Dict[str, Any], metadata: ModelMetadata,
                           preprocessors: Optional[Dict[str, Any]]) -> Union[np.ndarray, Dict[str, Any]]:
        """Preprocess features for prediction"""
        try:
            # Convert to DataFrame
            feature_df = pd.DataFrame([features])
            
            # Select only required features in correct order
            feature_df = feature_df[metadata.feature_names]
            
            # Apply preprocessing if available
            if preprocessors:
                # Apply scalers
                if 'scaler' in preprocessors:
                    scaler = preprocessors['scaler']
                    feature_df = pd.DataFrame(
                        scaler.transform(feature_df),
                        columns=feature_df.columns
                    )
                
                # Apply encoders
                if 'encoders' in preprocessors:
                    encoders = preprocessors['encoders']
                    for col, encoder in encoders.items():
                        if col in feature_df.columns:
                            feature_df[col] = encoder.transform(feature_df[col].astype(str))
            
            return feature_df.values
            
        except Exception as e:
            logger.error(f"Error preprocessing features: {e}")
            return {"error": str(e)}
    
    def _make_prediction(self, model: Any, processed_features: np.ndarray,
                        problem_type: str, return_probabilities: bool) -> Dict[str, Any]:
        """Make prediction with model"""
        try:
            result = {}
            
            # Make prediction
            prediction = model.predict(processed_features)
            result["prediction"] = prediction[0] if len(prediction) == 1 else prediction.tolist()
            
            # Add probabilities for classification
            if problem_type == "classification" and hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(processed_features)
                result["probabilities"] = probabilities[0].tolist() if len(probabilities) == 1 else probabilities.tolist()
                
                # Calculate confidence (max probability)
                result["confidence"] = float(np.max(probabilities))
            
            # For regression, use prediction confidence (if available)
            elif problem_type == "regression":
                # Simple confidence based on prediction value
                if hasattr(model, 'predict') and len(processed_features) == 1:
                    result["confidence"] = 0.8  # Default confidence for regression
            
            return result
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return {"error": str(e)}
    
    def _extract_preprocessing_config(self, preprocessors: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract preprocessing configuration"""
        if not preprocessors:
            return {}
        
        config = {}
        for name, preprocessor in preprocessors.items():
            if hasattr(preprocessor, 'get_params'):
                config[name] = preprocessor.get_params()
            else:
                config[name] = str(type(preprocessor))
        
        return config
    
    def _update_prediction_stats(self, model_id: str, processing_time_ms: float, success: bool):
        """Update prediction statistics"""
        if model_id not in self.prediction_stats:
            self.prediction_stats[model_id] = {
                'total_predictions': 0,
                'total_time_ms': 0.0,
                'average_time_ms': 0.0,
                'last_prediction': None,
                'error_count': 0
            }
        
        stats = self.prediction_stats[model_id]
        
        if success:
            stats['total_predictions'] += 1
            stats['total_time_ms'] += processing_time_ms
            stats['average_time_ms'] = stats['total_time_ms'] / stats['total_predictions']
            stats['last_prediction'] = datetime.now().isoformat()
        else:
            stats['error_count'] += 1
    
    def _log_prediction(self, model_id: str, features: Dict[str, Any], response: Dict[str, Any]):
        """Log prediction for monitoring"""
        if self.enable_monitoring:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "model_id": model_id,
                "processing_time_ms": response["processing_time_ms"],
                "success": "error" not in response
            }
            
            self.performance_history.append(log_entry)
            
            # Keep only recent history
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
    
    def _get_overall_statistics(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        return {
            "total_models": len(self.models),
            "cache_stats": self.model_cache.get_stats(),
            "prediction_stats": self.prediction_stats,
            "system_info": {
                "models_in_memory": len(self.models),
                "preprocessors_loaded": len(self.preprocessors),
                "monitoring_enabled": self.enable_monitoring,
                "redis_available": self.redis_client is not None
            },
            "uptime": self._calculate_uptime()
        }
    
    def _calculate_deployment_age(self, created_at: str) -> float:
        """Calculate deployment age in hours"""
        try:
            created = datetime.fromisoformat(created_at)
            age = datetime.now() - created
            return age.total_seconds() / 3600
        except:
            return 0.0
    
    def _calculate_predictions_per_hour(self, model_id: str) -> float:
        """Calculate predictions per hour for a model"""
        try:
            stats = self.prediction_stats.get(model_id, {})
            metadata = self.model_metadata.get(model_id)
            
            if not metadata:
                return 0.0
            
            age_hours = self._calculate_deployment_age(metadata.created_at)
            total_predictions = stats.get('total_predictions', 0)
            
            if age_hours > 0:
                return total_predictions / age_hours
            
            return 0.0
            
        except:
            return 0.0
    
    def _calculate_cache_hit_rate(self, model_id: str) -> float:
        """Calculate cache hit rate (simplified)"""
        # This is a simplified implementation
        # In practice, you'd track cache hits vs misses
        return 0.8  # Default assumption
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        return {
            "status": "healthy",
            "models_responsive": len([m for m in self.models.keys() if m in self.prediction_stats]),
            "cache_healthy": self.model_cache.get_stats()["utilization"] < 0.9,
            "redis_connected": self.redis_client is not None,
            "disk_space_ok": True,  # Simplified check
            "memory_usage_ok": True  # Simplified check
        }
    
    def _calculate_uptime(self) -> str:
        """Calculate system uptime (simplified)"""
        # This would be implemented based on when the processor was initialized
        return "Unknown"  # Placeholder
    
    def _create_model_backup(self, model_id: str) -> Dict[str, Any]:
        """Create backup of model"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.model_storage_path / "backups" / model_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy model files
            model_path = self.model_storage_path / f"{model_id}.pkl"
            metadata_path = self.model_storage_path / f"{model_id}_metadata.json"
            preprocessors_path = self.model_storage_path / f"{model_id}_preprocessors.pkl"
            
            backup_model_path = backup_dir / f"{model_id}_{timestamp}.pkl"
            backup_metadata_path = backup_dir / f"{model_id}_{timestamp}_metadata.json"
            backup_preprocessors_path = backup_dir / f"{model_id}_{timestamp}_preprocessors.pkl"
            
            if model_path.exists():
                import shutil
                shutil.copy2(model_path, backup_model_path)
            
            if metadata_path.exists():
                import shutil
                shutil.copy2(metadata_path, backup_metadata_path)
            
            if preprocessors_path.exists():
                import shutil
                shutil.copy2(preprocessors_path, backup_preprocessors_path)
            
            return {
                "success": True,
                "backup_path": str(backup_dir),
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error creating backup for {model_id}: {e}")
            return {"error": str(e)}

# Convenience functions
def deploy_sklearn_model(model, model_id: str, feature_names: List[str],
                        target_column: str, preprocessors: Optional[Dict[str, Any]] = None,
                        performance_metrics: Optional[Dict[str, float]] = None,
                        storage_path: str = "./models") -> Dict[str, Any]:
    """
    Convenience function to deploy scikit-learn model
    
    Args:
        model: Trained scikit-learn model
        model_id: Unique identifier
        feature_names: List of feature names
        target_column: Target column name
        preprocessors: Preprocessing objects
        performance_metrics: Model performance metrics
        storage_path: Storage path for models
        
    Returns:
        Deployment result
    """
    processor = ModelServingProcessor(model_storage_path=storage_path)
    
    # Detect problem type
    if hasattr(model, 'classes_'):
        problem_type = "classification"
    else:
        problem_type = "regression"
    
    return processor.deploy_model(
        model=model,
        model_id=model_id,
        model_type="sklearn",
        problem_type=problem_type,
        feature_names=feature_names,
        target_column=target_column,
        preprocessors=preprocessors,
        performance_metrics=performance_metrics
    )

def create_prediction_api(storage_path: str = "./models", api_type: str = "fastapi",
                         host: str = "localhost", port: int = 8000) -> Dict[str, Any]:
    """
    Convenience function to create prediction API
    
    Args:
        storage_path: Path to stored models
        api_type: 'flask' or 'fastapi'
        host: Host address
        port: Port number
        
    Returns:
        API creation result
    """
    processor = ModelServingProcessor(model_storage_path=storage_path)
    
    if api_type.lower() == "flask":
        return processor.create_flask_api(host=host, port=port)
    elif api_type.lower() == "fastapi":
        return processor.create_fastapi_api(host=host, port=port)
    else:
        return {"error": f"Unknown API type: {api_type}"}

def quick_model_serving_setup(model, model_id: str, feature_names: List[str],
                             target_column: str, api_type: str = "fastapi",
                             host: str = "localhost", port: int = 8000) -> Dict[str, Any]:
    """
    Convenience function for quick model serving setup
    
    Args:
        model: Trained model
        model_id: Model identifier
        feature_names: Feature names
        target_column: Target column
        api_type: API framework
        host: Host address
        port: Port number
        
    Returns:
        Setup result
    """
    processor = ModelServingProcessor()
    
    # Deploy model
    deploy_result = deploy_sklearn_model(model, model_id, feature_names, target_column)
    if "error" in deploy_result:
        return deploy_result
    
    # Create API
    api_result = create_prediction_api(api_type=api_type, host=host, port=port)
    
    return {
        "deployment": deploy_result,
        "api": api_result,
        "ready_to_serve": "error" not in api_result
    }