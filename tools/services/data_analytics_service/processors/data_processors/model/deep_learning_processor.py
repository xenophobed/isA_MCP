#!/usr/bin/env python3
"""
Deep Learning Processor
Advanced deep learning capabilities with TensorFlow/Keras and PyTorch support
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime
import logging
import warnings
warnings.filterwarnings('ignore')

# Deep Learning libraries - LAZY LOADING TO PREVENT MUTEX LOCK
def _check_tensorflow():
    """Lazy check for TensorFlow availability"""
    try:
        import tensorflow as tf
        return True
    except ImportError:
        return False

def _check_pytorch():
    """Lazy check for PyTorch availability"""
    try:
        import torch
        return True
    except ImportError:
        return False

TENSORFLOW_AVAILABLE = None  # Will be checked lazily
PYTORCH_AVAILABLE = None     # Will be checked lazily

# Placeholder for lazy imports - will be imported in functions when needed

# Lazy sklearn import to prevent mutex locks during startup
SKLEARN_AVAILABLE = None

def _lazy_import_sklearn():
    """Lazy import sklearn components only when needed"""
    global SKLEARN_AVAILABLE
    if SKLEARN_AVAILABLE is None:
        try:
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            SKLEARN_AVAILABLE = True
            return {
                'train_test_split': train_test_split,
                'StandardScaler': StandardScaler,
                'LabelEncoder': LabelEncoder,
                'MinMaxScaler': MinMaxScaler,
                'accuracy_score': accuracy_score,
                'precision_score': precision_score,
                'recall_score': recall_score,
                'f1_score': f1_score,
                'mean_squared_error': mean_squared_error,
                'mean_absolute_error': mean_absolute_error,
                'r2_score': r2_score
            }
        except ImportError:
            SKLEARN_AVAILABLE = False
            return None
    elif SKLEARN_AVAILABLE:
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        return {
            'train_test_split': train_test_split,
            'StandardScaler': StandardScaler,
            'LabelEncoder': LabelEncoder,
            'MinMaxScaler': MinMaxScaler,
            'accuracy_score': accuracy_score,
            'precision_score': precision_score,
            'recall_score': recall_score,
            'f1_score': f1_score,
            'mean_squared_error': mean_squared_error,
            'mean_absolute_error': mean_absolute_error,
            'r2_score': r2_score
        }
    else:
        return None

try:
    from ..preprocessors.csv_processor import CSVProcessor
except ImportError:
    from csv_processor import CSVProcessor

logger = logging.getLogger(__name__)

class DeepLearningProcessor:
    """
    Deep Learning processor with TensorFlow/Keras and PyTorch support
    Provides neural networks, CNNs, RNNs, and automated model architectures
    """
    
    def __init__(self, csv_processor: Optional[CSVProcessor] = None, file_path: Optional[str] = None):
        """
        Initialize deep learning processor
        
        Args:
            csv_processor: Existing CSVProcessor instance
            file_path: Path to CSV file (if csv_processor not provided)
        """
        if csv_processor:
            self.csv_processor = csv_processor
        elif file_path:
            self.csv_processor = CSVProcessor(file_path)
        else:
            raise ValueError("Either csv_processor or file_path must be provided")
        
        self.df = None
        self.models = {}
        self.training_history = {}
        self.scalers = {}
        self.encoders = {}
        
        # Set random seeds for reproducibility
        if TENSORFLOW_AVAILABLE:
            tf.random.set_seed(42)
        if PYTORCH_AVAILABLE:
            torch.manual_seed(42)
        
        self._load_data()
    
    def _load_data(self) -> bool:
        """Load data from CSV processor"""
        try:
            if not self.csv_processor.load_csv():
                return False
            self.df = self.csv_processor.df.copy()
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def get_deep_learning_recommendations(self, target_column: str, problem_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get deep learning model recommendations based on data characteristics
        
        Args:
            target_column: Target variable
            problem_type: 'classification', 'regression', or 'time_series'
            
        Returns:
            Deep learning recommendations and architecture suggestions
        """
        try:
            if self.df is None:
                return {"error": "No data loaded"}
            
            if target_column not in self.df.columns:
                return {"error": f"Target column '{target_column}' not found"}
            
            # Auto-detect problem type if not specified
            if problem_type is None:
                problem_type = self._detect_problem_type(self.df[target_column])
            
            # Analyze data characteristics
            data_analysis = self._analyze_data_for_dl(target_column, problem_type)
            
            recommendations = {
                "problem_type": problem_type,
                "data_analysis": data_analysis,
                "architecture_recommendations": self._recommend_architectures(data_analysis, problem_type),
                "preprocessing_recommendations": self._recommend_dl_preprocessing(data_analysis),
                "training_recommendations": self._recommend_training_strategy(data_analysis),
                "framework_availability": {
                    "tensorflow": TENSORFLOW_AVAILABLE,
                    "pytorch": PYTORCH_AVAILABLE,
                    "sklearn": SKLEARN_AVAILABLE
                }
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting deep learning recommendations: {e}")
            return {"error": str(e)}
    
    def _analyze_data_for_dl(self, target_column: str, problem_type: str) -> Dict[str, Any]:
        """Analyze data characteristics for deep learning suitability"""
        try:
            features_df = self.df.drop(columns=[target_column])
            target_series = self.df[target_column]
            
            analysis = {
                "data_shape": list(self.df.shape),
                "feature_analysis": {},
                "target_analysis": {},
                "complexity_assessment": {},
                "suitability_for_dl": {}
            }
            
            # Feature analysis
            numeric_features = features_df.select_dtypes(include=[np.number]).columns
            categorical_features = features_df.select_dtypes(include=['object', 'category']).columns
            
            analysis["feature_analysis"] = {
                "total_features": len(features_df.columns),
                "numeric_features": len(numeric_features),
                "categorical_features": len(categorical_features),
                "missing_values": features_df.isnull().sum().sum(),
                "high_cardinality_cats": [
                    col for col in categorical_features 
                    if features_df[col].nunique() > 50
                ]
            }
            
            # Target analysis
            if problem_type == "classification":
                unique_classes = target_series.nunique()
                class_distribution = target_series.value_counts()
                
                analysis["target_analysis"] = {
                    "num_classes": unique_classes,
                    "is_binary": unique_classes == 2,
                    "is_multiclass": unique_classes > 2,
                    "class_imbalance": self._check_class_imbalance(class_distribution),
                    "dominant_class_ratio": float(class_distribution.iloc[0] / len(target_series))
                }
            else:  # regression
                analysis["target_analysis"] = {
                    "target_range": float(target_series.max() - target_series.min()),
                    "target_std": float(target_series.std()),
                    "target_skewness": float(target_series.skew()),
                    "outlier_ratio": self._calculate_outlier_ratio(target_series)
                }
            
            # Complexity assessment
            n_samples, n_features = self.df.shape
            
            analysis["complexity_assessment"] = {
                "sample_to_feature_ratio": n_samples / n_features if n_features > 0 else 0,
                "data_size_category": self._categorize_data_size(n_samples),
                "feature_dimensionality": self._categorize_feature_dimensionality(n_features),
                "recommended_complexity": self._recommend_model_complexity(n_samples, n_features)
            }
            
            # Deep learning suitability
            dl_suitability = self._assess_dl_suitability(n_samples, n_features, problem_type)
            analysis["suitability_for_dl"] = dl_suitability
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing data for DL: {e}")
            return {"error": str(e)}
    
    def _recommend_architectures(self, data_analysis: Dict[str, Any], problem_type: str) -> Dict[str, Any]:
        """Recommend neural network architectures based on data analysis"""
        try:
            architectures = {
                "recommended_models": [],
                "architecture_details": {},
                "alternative_approaches": []
            }
            
            n_samples = data_analysis["data_shape"][0]
            n_features = data_analysis["data_shape"][1] - 1  # Excluding target
            complexity = data_analysis["complexity_assessment"]["recommended_complexity"]
            
            # Basic feedforward networks
            if problem_type in ["classification", "regression"]:
                # Multi-layer perceptron
                mlp_config = {
                    "name": "Multi-Layer Perceptron (MLP)",
                    "description": "Standard feedforward neural network",
                    "architecture": self._generate_mlp_architecture(n_features, problem_type, complexity),
                    "use_case": "General purpose, good baseline",
                    "priority": "high"
                }
                architectures["recommended_models"].append(mlp_config)
                
                # Deep neural network (if enough data)
                if n_samples > 10000:
                    deep_config = {
                        "name": "Deep Neural Network",
                        "description": "Deeper architecture with regularization",
                        "architecture": self._generate_deep_architecture(n_features, problem_type),
                        "use_case": "Large datasets, complex patterns",
                        "priority": "medium"
                    }
                    architectures["recommended_models"].append(deep_config)
            
            # Specialized architectures
            if n_features > 100:
                # Autoencoder for dimensionality reduction
                autoencoder_config = {
                    "name": "Autoencoder",
                    "description": "Unsupervised feature learning",
                    "architecture": self._generate_autoencoder_architecture(n_features),
                    "use_case": "Dimensionality reduction, feature learning",
                    "priority": "medium"
                }
                architectures["alternative_approaches"].append(autoencoder_config)
            
            # Time series architectures (if temporal data detected)
            if self._has_temporal_features(data_analysis):
                lstm_config = {
                    "name": "LSTM Network",
                    "description": "Long Short-Term Memory for sequences",
                    "architecture": self._generate_lstm_architecture(n_features, problem_type),
                    "use_case": "Time series, sequential data",
                    "priority": "high"
                }
                architectures["recommended_models"].append(lstm_config)
            
            return architectures
            
        except Exception as e:
            logger.error(f"Error recommending architectures: {e}")
            return {"error": str(e)}
    
    def build_tensorflow_model(self, architecture_config: Dict[str, Any], 
                             input_shape: Tuple[int], output_shape: int,
                             problem_type: str) -> Dict[str, Any]:
        """
        Build TensorFlow/Keras model based on architecture configuration
        
        Args:
            architecture_config: Model architecture configuration
            input_shape: Shape of input features
            output_shape: Number of output units
            problem_type: 'classification' or 'regression'
            
        Returns:
            Built model and configuration details
        """
        try:
            if not TENSORFLOW_AVAILABLE:
                return {"error": "TensorFlow not available"}
            
            model_name = architecture_config.get("name", "unknown")
            architecture = architecture_config.get("architecture", {})
            
            if "lstm" in model_name.lower():
                model = self._build_lstm_model(input_shape, output_shape, problem_type, architecture)
            elif "autoencoder" in model_name.lower():
                model = self._build_autoencoder_model(input_shape, architecture)
            else:
                model = self._build_mlp_model(input_shape, output_shape, problem_type, architecture)
            
            # Compile model
            if problem_type == "classification":
                if output_shape == 1:
                    loss = 'binary_crossentropy'
                    metrics = ['accuracy']
                else:
                    loss = 'categorical_crossentropy'
                    metrics = ['accuracy']
            else:  # regression
                loss = 'mse'
                metrics = ['mae']
            
            optimizer = architecture.get("optimizer", "adam")
            learning_rate = architecture.get("learning_rate", 0.001)
            
            if optimizer == "adam":
                opt = optimizers.Adam(learning_rate=learning_rate)
            elif optimizer == "sgd":
                opt = optimizers.SGD(learning_rate=learning_rate)
            else:
                opt = optimizer
            
            model.compile(optimizer=opt, loss=loss, metrics=metrics)
            
            # Store model
            model_key = f"tf_{model_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.models[model_key] = model
            
            result = {
                "model_key": model_key,
                "framework": "tensorflow",
                "model_summary": self._get_model_summary(model),
                "architecture_config": architecture_config,
                "compilation_config": {
                    "optimizer": optimizer,
                    "loss": loss,
                    "metrics": metrics,
                    "learning_rate": learning_rate
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error building TensorFlow model: {e}")
            return {"error": str(e)}
    
    def train_tensorflow_model(self, model_key: str, target_column: str,
                             epochs: int = 100, batch_size: int = 32,
                             validation_split: float = 0.2,
                             early_stopping: bool = True) -> Dict[str, Any]:
        """
        Train TensorFlow model
        
        Args:
            model_key: Key identifying the model
            target_column: Target variable
            epochs: Number of training epochs
            batch_size: Training batch size
            validation_split: Fraction of data for validation
            early_stopping: Whether to use early stopping
            
        Returns:
            Training results and metrics
        """
        try:
            if not TENSORFLOW_AVAILABLE:
                return {"error": "TensorFlow not available"}
            
            if model_key not in self.models:
                return {"error": f"Model '{model_key}' not found"}
            
            model = self.models[model_key]
            
            # Prepare data
            X, y = self._prepare_data_for_training(target_column)
            if isinstance(X, dict) and "error" in X:
                return X
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=validation_split, random_state=42
            )
            
            # Setup callbacks
            callback_list = []
            
            if early_stopping:
                early_stop = callbacks.EarlyStopping(
                    monitor='val_loss',
                    patience=10,
                    restore_best_weights=True
                )
                callback_list.append(early_stop)
            
            # Reduce learning rate on plateau
            reduce_lr = callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.2,
                patience=5,
                min_lr=0.001
            )
            callback_list.append(reduce_lr)
            
            # Train model
            start_time = datetime.now()
            history = model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=batch_size,
                validation_data=(X_test, y_test),
                callbacks=callback_list,
                verbose=0
            )
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Evaluate model
            train_loss = model.evaluate(X_train, y_train, verbose=0)
            test_loss = model.evaluate(X_test, y_test, verbose=0)
            
            # Generate predictions for detailed metrics
            y_pred = model.predict(X_test)
            
            # Calculate detailed metrics
            problem_type = self._detect_problem_type(self.df[target_column])
            detailed_metrics = self._calculate_detailed_metrics(y_test, y_pred, problem_type)
            
            # Store training history
            self.training_history[model_key] = history
            
            results = {
                "model_key": model_key,
                "training_time_seconds": round(training_time, 3),
                "epochs_trained": len(history.history['loss']),
                "final_metrics": {
                    "train_loss": float(train_loss[0]),
                    "test_loss": float(test_loss[0]),
                    "train_accuracy": float(train_loss[1]) if len(train_loss) > 1 else None,
                    "test_accuracy": float(test_loss[1]) if len(test_loss) > 1 else None
                },
                "detailed_metrics": detailed_metrics,
                "training_config": {
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "validation_split": validation_split,
                    "early_stopping": early_stopping
                },
                "data_split": {
                    "train_samples": len(X_train),
                    "test_samples": len(X_test)
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error training TensorFlow model: {e}")
            return {"error": str(e)}
    
    def build_pytorch_model(self, architecture_config: Dict[str, Any],
                          input_size: int, output_size: int,
                          problem_type: str) -> Dict[str, Any]:
        """
        Build PyTorch model based on architecture configuration
        
        Args:
            architecture_config: Model architecture configuration
            input_size: Number of input features
            output_size: Number of output units
            problem_type: 'classification' or 'regression'
            
        Returns:
            Built model and configuration details
        """
        try:
            if not PYTORCH_AVAILABLE:
                return {"error": "PyTorch not available"}
            
            model_name = architecture_config.get("name", "unknown")
            architecture = architecture_config.get("architecture", {})
            
            # Build PyTorch model
            if "lstm" in model_name.lower():
                model = self._build_pytorch_lstm(input_size, output_size, problem_type, architecture)
            else:
                model = self._build_pytorch_mlp(input_size, output_size, problem_type, architecture)
            
            # Store model
            model_key = f"torch_{model_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.models[model_key] = model
            
            # Count parameters
            total_params = sum(p.numel() for p in model.parameters())
            trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            
            result = {
                "model_key": model_key,
                "framework": "pytorch",
                "model_info": {
                    "total_parameters": total_params,
                    "trainable_parameters": trainable_params,
                    "architecture": str(model)
                },
                "architecture_config": architecture_config
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error building PyTorch model: {e}")
            return {"error": str(e)}
    
    def train_pytorch_model(self, model_key: str, target_column: str,
                          epochs: int = 100, batch_size: int = 32,
                          learning_rate: float = 0.001,
                          validation_split: float = 0.2) -> Dict[str, Any]:
        """
        Train PyTorch model
        
        Args:
            model_key: Key identifying the model
            target_column: Target variable
            epochs: Number of training epochs
            batch_size: Training batch size
            learning_rate: Learning rate for optimizer
            validation_split: Fraction of data for validation
            
        Returns:
            Training results and metrics
        """
        try:
            if not PYTORCH_AVAILABLE:
                return {"error": "PyTorch not available"}
            
            if model_key not in self.models:
                return {"error": f"Model '{model_key}' not found"}
            
            model = self.models[model_key]
            
            # Prepare data
            X, y = self._prepare_data_for_training(target_column)
            if isinstance(X, dict) and "error" in X:
                return X
            
            # Convert to PyTorch tensors
            X_tensor = torch.FloatTensor(X.values if hasattr(X, 'values') else X)
            y_tensor = torch.FloatTensor(y.values if hasattr(y, 'values') else y)
            
            # Split data
            train_size = int((1 - validation_split) * len(X_tensor))
            
            X_train, X_test = X_tensor[:train_size], X_tensor[train_size:]
            y_train, y_test = y_tensor[:train_size], y_tensor[train_size:]
            
            # Create data loaders
            train_dataset = TensorDataset(X_train, y_train)
            test_dataset = TensorDataset(X_test, y_test)
            
            train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
            test_loader = DataLoader(test_dataset, batch_size=batch_size)
            
            # Setup optimizer and loss function
            optimizer = optim.Adam(model.parameters(), lr=learning_rate)
            
            problem_type = self._detect_problem_type(self.df[target_column])
            if problem_type == "classification":
                criterion = nn.CrossEntropyLoss() if len(torch.unique(y_tensor)) > 2 else nn.BCEWithLogitsLoss()
            else:
                criterion = nn.MSELoss()
            
            # Training loop
            train_losses = []
            test_losses = []
            
            start_time = datetime.now()
            
            for epoch in range(epochs):
                # Training
                model.train()
                train_loss = 0.0
                
                for batch_X, batch_y in train_loader:
                    optimizer.zero_grad()
                    outputs = model(batch_X)
                    
                    if problem_type == "classification" and len(outputs.shape) > 1 and outputs.shape[1] == 1:
                        outputs = outputs.squeeze()
                    
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()
                
                # Validation
                model.eval()
                test_loss = 0.0
                
                with torch.no_grad():
                    for batch_X, batch_y in test_loader:
                        outputs = model(batch_X)
                        
                        if problem_type == "classification" and len(outputs.shape) > 1 and outputs.shape[1] == 1:
                            outputs = outputs.squeeze()
                        
                        loss = criterion(outputs, batch_y)
                        test_loss += loss.item()
                
                train_losses.append(train_loss / len(train_loader))
                test_losses.append(test_loss / len(test_loader))
                
                # Early stopping check
                if epoch > 10 and test_losses[-1] > test_losses[-5]:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break
            
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Final evaluation
            model.eval()
            with torch.no_grad():
                y_pred = model(X_test)
                if problem_type == "classification" and len(y_pred.shape) > 1 and y_pred.shape[1] == 1:
                    y_pred = y_pred.squeeze()
            
            # Calculate detailed metrics
            y_test_np = y_test.numpy()
            y_pred_np = y_pred.numpy()
            
            detailed_metrics = self._calculate_detailed_metrics(y_test_np, y_pred_np, problem_type)
            
            results = {
                "model_key": model_key,
                "training_time_seconds": round(training_time, 3),
                "epochs_trained": len(train_losses),
                "final_metrics": {
                    "train_loss": train_losses[-1],
                    "test_loss": test_losses[-1]
                },
                "detailed_metrics": detailed_metrics,
                "training_history": {
                    "train_losses": train_losses,
                    "test_losses": test_losses
                },
                "training_config": {
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "learning_rate": learning_rate,
                    "validation_split": validation_split
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error training PyTorch model: {e}")
            return {"error": str(e)}
    
    def comprehensive_deep_learning_analysis(self, target_column: str,
                                           problem_type: Optional[str] = None,
                                           frameworks: List[str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive deep learning analysis with multiple frameworks
        
        Args:
            target_column: Target variable
            problem_type: 'classification', 'regression', or auto-detect
            frameworks: List of frameworks to use ['tensorflow', 'pytorch']
            
        Returns:
            Complete deep learning analysis results
        """
        try:
            if frameworks is None:
                frameworks = []
                if TENSORFLOW_AVAILABLE:
                    frameworks.append("tensorflow")
                if PYTORCH_AVAILABLE:
                    frameworks.append("pytorch")
            
            analysis_results = {
                "recommendations": {},
                "models_built": {},
                "training_results": {},
                "model_comparison": {},
                "best_model": None
            }
            
            # 1. Get recommendations
            logger.info("Getting deep learning recommendations...")
            recommendations = self.get_deep_learning_recommendations(target_column, problem_type)
            analysis_results["recommendations"] = recommendations
            
            if "error" in recommendations:
                return analysis_results
            
            problem_type = recommendations["problem_type"]
            
            # 2. Build and train models for each framework
            input_shape = (recommendations["data_analysis"]["feature_analysis"]["total_features"],)
            
            if problem_type == "classification":
                output_shape = recommendations["data_analysis"]["target_analysis"]["num_classes"]
                if output_shape == 2:
                    output_shape = 1  # Binary classification
            else:
                output_shape = 1  # Regression
            
            for framework in frameworks:
                try:
                    logger.info(f"Working with {framework}...")
                    
                    # Select best architecture recommendation
                    arch_recommendations = recommendations["architecture_recommendations"]["recommended_models"]
                    if not arch_recommendations:
                        continue
                    
                    best_arch = arch_recommendations[0]  # Take highest priority
                    
                    # Build model
                    if framework == "tensorflow":
                        build_result = self.build_tensorflow_model(
                            best_arch, input_shape, output_shape, problem_type
                        )
                    elif framework == "pytorch":
                        build_result = self.build_pytorch_model(
                            best_arch, input_shape[0], output_shape, problem_type
                        )
                    else:
                        continue
                    
                    if "error" in build_result:
                        logger.warning(f"Failed to build {framework} model: {build_result['error']}")
                        continue
                    
                    analysis_results["models_built"][framework] = build_result
                    
                    # Train model
                    model_key = build_result["model_key"]
                    
                    if framework == "tensorflow":
                        train_result = self.train_tensorflow_model(model_key, target_column)
                    elif framework == "pytorch":
                        train_result = self.train_pytorch_model(model_key, target_column)
                    
                    if "error" in train_result:
                        logger.warning(f"Failed to train {framework} model: {train_result['error']}")
                        continue
                    
                    analysis_results["training_results"][framework] = train_result
                    
                except Exception as e:
                    logger.warning(f"Error with {framework}: {e}")
            
            # 3. Compare models
            if len(analysis_results["training_results"]) > 1:
                comparison = self._compare_dl_models(analysis_results["training_results"], problem_type)
                analysis_results["model_comparison"] = comparison
                analysis_results["best_model"] = comparison.get("best_model")
            elif len(analysis_results["training_results"]) == 1:
                framework = list(analysis_results["training_results"].keys())[0]
                analysis_results["best_model"] = {
                    "framework": framework,
                    "model_key": analysis_results["training_results"][framework]["model_key"]
                }
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in comprehensive deep learning analysis: {e}")
            return {"error": str(e)}
    
    # Helper methods for model building
    
    def _build_mlp_model(self, input_shape: Tuple[int], output_shape: int, 
                        problem_type: str, architecture: Dict[str, Any]):
        """Build MLP model with TensorFlow/Keras"""
        model = Sequential()
        
        # Input layer
        model.add(Dense(architecture.get("hidden_units", [128, 64])[0], 
                       activation='relu', input_shape=input_shape))
        model.add(Dropout(architecture.get("dropout_rate", 0.3)))
        
        # Hidden layers
        hidden_units = architecture.get("hidden_units", [128, 64])
        for units in hidden_units[1:]:
            model.add(Dense(units, activation='relu'))
            model.add(BatchNormalization())
            model.add(Dropout(architecture.get("dropout_rate", 0.3)))
        
        # Output layer
        if problem_type == "classification":
            if output_shape == 1:
                model.add(Dense(1, activation='sigmoid'))
            else:
                model.add(Dense(output_shape, activation='softmax'))
        else:
            model.add(Dense(1, activation='linear'))
        
        return model
    
    def _build_lstm_model(self, input_shape: Tuple[int], output_shape: int,
                         problem_type: str, architecture: Dict[str, Any]):
        """Build LSTM model with TensorFlow/Keras"""
        model = Sequential()
        
        # Reshape for LSTM (add time dimension)
        model.add(layers.Reshape((1, input_shape[0]), input_shape=input_shape))
        
        # LSTM layers
        lstm_units = architecture.get("lstm_units", [50, 50])
        for i, units in enumerate(lstm_units):
            return_sequences = i < len(lstm_units) - 1
            model.add(LSTM(units, return_sequences=return_sequences))
            model.add(Dropout(architecture.get("dropout_rate", 0.2)))
        
        # Dense layers
        model.add(Dense(architecture.get("dense_units", 25), activation='relu'))
        model.add(Dropout(architecture.get("dropout_rate", 0.2)))
        
        # Output layer
        if problem_type == "classification":
            if output_shape == 1:
                model.add(Dense(1, activation='sigmoid'))
            else:
                model.add(Dense(output_shape, activation='softmax'))
        else:
            model.add(Dense(1, activation='linear'))
        
        return model
    
    def _build_autoencoder_model(self, input_shape: Tuple[int], architecture: Dict[str, Any]):
        """Build autoencoder model with TensorFlow/Keras"""
        encoding_dim = architecture.get("encoding_dim", input_shape[0] // 2)
        
        # Encoder
        input_layer = keras.Input(shape=input_shape)
        encoded = Dense(encoding_dim, activation='relu')(input_layer)
        encoded = Dropout(0.2)(encoded)
        
        # Decoder
        decoded = Dense(input_shape[0], activation='sigmoid')(encoded)
        
        autoencoder = Model(input_layer, decoded)
        return autoencoder
    
    def _build_pytorch_mlp(self, input_size: int, output_size: int,
                          problem_type: str, architecture: Dict[str, Any]):
        """Build MLP model with PyTorch"""
        
        class MLPModel(nn.Module):
            def __init__(self, input_size, output_size, hidden_units, dropout_rate):
                super(MLPModel, self).__init__()
                self.layers = nn.ModuleList()
                
                # Input layer
                self.layers.append(nn.Linear(input_size, hidden_units[0]))
                
                # Hidden layers
                for i in range(len(hidden_units) - 1):
                    self.layers.append(nn.Linear(hidden_units[i], hidden_units[i + 1]))
                
                # Output layer
                self.layers.append(nn.Linear(hidden_units[-1], output_size))
                
                self.dropout = nn.Dropout(dropout_rate)
                self.relu = nn.ReLU()
                
            def forward(self, x):
                for i, layer in enumerate(self.layers[:-1]):
                    x = self.relu(layer(x))
                    x = self.dropout(x)
                
                x = self.layers[-1](x)
                return x
        
        hidden_units = architecture.get("hidden_units", [128, 64])
        dropout_rate = architecture.get("dropout_rate", 0.3)
        
        return MLPModel(input_size, output_size, hidden_units, dropout_rate)
    
    def _build_pytorch_lstm(self, input_size: int, output_size: int,
                           problem_type: str, architecture: Dict[str, Any]):
        """Build LSTM model with PyTorch"""
        
        class LSTMModel(nn.Module):
            def __init__(self, input_size, hidden_size, output_size, num_layers, dropout_rate):
                super(LSTMModel, self).__init__()
                self.hidden_size = hidden_size
                self.num_layers = num_layers
                
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                                  batch_first=True, dropout=dropout_rate)
                self.fc = nn.Linear(hidden_size, output_size)
                
            def forward(self, x):
                # Add sequence dimension
                if len(x.shape) == 2:
                    x = x.unsqueeze(1)
                
                lstm_out, _ = self.lstm(x)
                out = self.fc(lstm_out[:, -1, :])
                return out
        
        hidden_size = architecture.get("lstm_units", [50])[0]
        num_layers = len(architecture.get("lstm_units", [50]))
        dropout_rate = architecture.get("dropout_rate", 0.2)
        
        return LSTMModel(input_size, hidden_size, output_size, num_layers, dropout_rate)
    
    # Additional helper methods would continue here...
    # (Due to length constraints, I'm including the key methods)
    
    def _detect_problem_type(self, target_series: pd.Series) -> str:
        """Detect if problem is classification or regression"""
        if pd.api.types.is_numeric_dtype(target_series):
            unique_count = target_series.nunique()
            total_count = len(target_series)
            
            if unique_count <= 20 and unique_count < total_count * 0.1:
                return "classification"
            else:
                return "regression"
        else:
            return "classification"
    
    def _check_class_imbalance(self, class_distribution: pd.Series) -> bool:
        """Check if classes are imbalanced"""
        if len(class_distribution) <= 1:
            return False
        
        majority_count = class_distribution.iloc[0]
        minority_count = class_distribution.iloc[-1]
        
        return minority_count < majority_count * 0.3
    
    def _calculate_outlier_ratio(self, series: pd.Series) -> float:
        """Calculate ratio of outliers using IQR method"""
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        outliers = series[(series < Q1 - 1.5 * IQR) | (series > Q3 + 1.5 * IQR)]
        return len(outliers) / len(series)
    
    def _categorize_data_size(self, n_samples: int) -> str:
        """Categorize dataset size"""
        if n_samples < 1000:
            return "small"
        elif n_samples < 10000:
            return "medium"
        elif n_samples < 100000:
            return "large"
        else:
            return "very_large"
    
    def _categorize_feature_dimensionality(self, n_features: int) -> str:
        """Categorize feature dimensionality"""
        if n_features < 10:
            return "low"
        elif n_features < 100:
            return "medium"
        elif n_features < 1000:
            return "high"
        else:
            return "very_high"
    
    def _recommend_model_complexity(self, n_samples: int, n_features: int) -> str:
        """Recommend model complexity based on data characteristics"""
        ratio = n_samples / n_features if n_features > 0 else 0
        
        if ratio > 100:
            return "high"
        elif ratio > 20:
            return "medium"
        else:
            return "low"
    
    def _assess_dl_suitability(self, n_samples: int, n_features: int, problem_type: str) -> Dict[str, Any]:
        """Assess whether deep learning is suitable for this dataset"""
        suitability = {
            "suitable": False,
            "confidence": "low",
            "reasons": [],
            "recommendations": []
        }
        
        # Size considerations
        if n_samples >= 1000:
            suitability["reasons"].append(f"Sufficient data size ({n_samples} samples)")
            suitability["suitable"] = True
        else:
            suitability["reasons"].append(f"Small dataset ({n_samples} samples) - consider traditional ML")
            suitability["recommendations"].append("Consider using traditional ML algorithms (Random Forest, SVM)")
        
        # Complexity considerations
        if n_features >= 10:
            suitability["reasons"].append(f"Adequate feature dimensionality ({n_features} features)")
        else:
            suitability["reasons"].append(f"Low dimensionality ({n_features} features) - deep learning may not be necessary")
        
        # Problem type considerations
        if problem_type in ["classification", "regression"]:
            suitability["reasons"].append(f"Standard {problem_type} problem suitable for neural networks")
        
        # Overall assessment
        if suitability["suitable"] and n_samples >= 5000:
            suitability["confidence"] = "high"
        elif suitability["suitable"]:
            suitability["confidence"] = "medium"
        
        return suitability
    
    def _has_temporal_features(self, data_analysis: Dict[str, Any]) -> bool:
        """Check if data might have temporal characteristics"""
        # Simple heuristic - in practice you'd want more sophisticated detection
        return False  # Placeholder
    
    def _generate_mlp_architecture(self, n_features: int, problem_type: str, complexity: str) -> Dict[str, Any]:
        """Generate MLP architecture configuration"""
        if complexity == "low":
            hidden_units = [64, 32]
            dropout_rate = 0.2
        elif complexity == "medium":
            hidden_units = [128, 64, 32]
            dropout_rate = 0.3
        else:  # high
            hidden_units = [256, 128, 64, 32]
            dropout_rate = 0.4
        
        return {
            "hidden_units": hidden_units,
            "dropout_rate": dropout_rate,
            "optimizer": "adam",
            "learning_rate": 0.001
        }
    
    def _generate_deep_architecture(self, n_features: int, problem_type: str) -> Dict[str, Any]:
        """Generate deep neural network architecture"""
        return {
            "hidden_units": [512, 256, 128, 64, 32],
            "dropout_rate": 0.5,
            "optimizer": "adam",
            "learning_rate": 0.0001,
            "batch_normalization": True
        }
    
    def _generate_autoencoder_architecture(self, n_features: int) -> Dict[str, Any]:
        """Generate autoencoder architecture"""
        return {
            "encoding_dim": max(n_features // 4, 10),
            "hidden_units": [n_features // 2, n_features // 4],
            "dropout_rate": 0.2
        }
    
    def _generate_lstm_architecture(self, n_features: int, problem_type: str) -> Dict[str, Any]:
        """Generate LSTM architecture"""
        return {
            "lstm_units": [50, 50],
            "dense_units": 25,
            "dropout_rate": 0.2,
            "optimizer": "adam",
            "learning_rate": 0.001
        }
    
    def _prepare_data_for_training(self, target_column: str) -> Tuple[Any, Any]:
        """Prepare data for training"""
        try:
            if self.df is None:
                return {"error": "No data loaded"}, None
            
            # Separate features and target
            X = self.df.drop(columns=[target_column])
            y = self.df[target_column]
            
            # Handle missing values
            X = X.fillna(X.mean() if X.select_dtypes(include=[np.number]).shape[1] > 0 else X.mode().iloc[0])
            y = y.fillna(y.mean() if pd.api.types.is_numeric_dtype(y) else y.mode().iloc[0])
            
            # Encode categorical variables
            categorical_columns = X.select_dtypes(include=['object', 'category']).columns
            
            for col in categorical_columns:
                if col not in self.encoders:
                    self.encoders[col] = LabelEncoder()
                    X[col] = self.encoders[col].fit_transform(X[col].astype(str))
                else:
                    X[col] = self.encoders[col].transform(X[col].astype(str))
            
            # Scale features
            if "scaler" not in self.scalers:
                self.scalers["scaler"] = StandardScaler()
                X_scaled = self.scalers["scaler"].fit_transform(X)
            else:
                X_scaled = self.scalers["scaler"].transform(X)
            
            X_scaled = pd.DataFrame(X_scaled, columns=X.columns)
            
            # Encode target for classification
            problem_type = self._detect_problem_type(y)
            if problem_type == "classification":
                if "target_encoder" not in self.encoders:
                    self.encoders["target_encoder"] = LabelEncoder()
                    y_encoded = self.encoders["target_encoder"].fit_transform(y.astype(str))
                else:
                    y_encoded = self.encoders["target_encoder"].transform(y.astype(str))
                
                # Convert to categorical for multi-class
                if len(np.unique(y_encoded)) > 2:
                    y_encoded = to_categorical(y_encoded) if TENSORFLOW_AVAILABLE else y_encoded
                
                return X_scaled, y_encoded
            else:
                return X_scaled, y
                
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return {"error": str(e)}, None
    
    def _calculate_detailed_metrics(self, y_true, y_pred, problem_type: str) -> Dict[str, float]:
        """Calculate detailed performance metrics"""
        try:
            metrics = {}
            
            if not SKLEARN_AVAILABLE:
                return {"error": "Scikit-learn not available for metrics calculation"}
            
            if problem_type == "classification":
                # Handle different prediction formats
                if len(y_pred.shape) > 1:
                    if y_pred.shape[1] > 1:
                        y_pred_classes = np.argmax(y_pred, axis=1)
                    else:
                        y_pred_classes = (y_pred > 0.5).astype(int).flatten()
                else:
                    y_pred_classes = (y_pred > 0.5).astype(int) if y_pred.dtype == float else y_pred
                
                # Handle different true label formats
                if len(y_true.shape) > 1 and y_true.shape[1] > 1:
                    y_true_classes = np.argmax(y_true, axis=1)
                else:
                    y_true_classes = y_true.flatten() if hasattr(y_true, 'flatten') else y_true
                
                metrics["accuracy"] = float(accuracy_score(y_true_classes, y_pred_classes))
                metrics["precision"] = float(precision_score(y_true_classes, y_pred_classes, average='weighted', zero_division=0))
                metrics["recall"] = float(recall_score(y_true_classes, y_pred_classes, average='weighted', zero_division=0))
                metrics["f1_score"] = float(f1_score(y_true_classes, y_pred_classes, average='weighted', zero_division=0))
                
            else:  # regression
                y_pred_values = y_pred.flatten() if hasattr(y_pred, 'flatten') else y_pred
                y_true_values = y_true.flatten() if hasattr(y_true, 'flatten') else y_true
                
                metrics["r2_score"] = float(r2_score(y_true_values, y_pred_values))
                metrics["mean_squared_error"] = float(mean_squared_error(y_true_values, y_pred_values))
                metrics["mean_absolute_error"] = float(mean_absolute_error(y_true_values, y_pred_values))
                metrics["root_mean_squared_error"] = float(np.sqrt(mean_squared_error(y_true_values, y_pred_values)))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating detailed metrics: {e}")
            return {"error": str(e)}
    
    def _compare_dl_models(self, training_results: Dict[str, Any], problem_type: str) -> Dict[str, Any]:
        """Compare deep learning models across frameworks"""
        try:
            comparison = {
                "model_rankings": [],
                "best_model": None,
                "performance_summary": {}
            }
            
            model_performances = []
            
            for framework, result in training_results.items():
                detailed_metrics = result.get("detailed_metrics", {})
                
                if problem_type == "classification" and "accuracy" in detailed_metrics:
                    primary_metric = detailed_metrics["accuracy"]
                    metric_name = "accuracy"
                elif problem_type == "regression" and "r2_score" in detailed_metrics:
                    primary_metric = detailed_metrics["r2_score"]
                    metric_name = "r2_score"
                else:
                    continue
                
                model_performances.append({
                    "framework": framework,
                    "model_key": result["model_key"],
                    "primary_metric": primary_metric,
                    "metric_name": metric_name,
                    "training_time": result["training_time_seconds"]
                })
            
            # Sort by primary metric (higher is better for both accuracy and R²)
            model_performances.sort(key=lambda x: x["primary_metric"], reverse=True)
            
            comparison["model_rankings"] = model_performances
            
            if model_performances:
                best = model_performances[0]
                comparison["best_model"] = {
                    "framework": best["framework"],
                    "model_key": best["model_key"],
                    "performance": best["primary_metric"]
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing DL models: {e}")
            return {"error": str(e)}
    
    def _get_model_summary(self, model) -> Dict[str, Any]:
        """Get summary of TensorFlow model"""
        try:
            summary_lines = []
            model.summary(print_fn=lambda x: summary_lines.append(x))
            
            total_params = model.count_params()
            
            return {
                "total_parameters": total_params,
                "summary": "\n".join(summary_lines),
                "layers": len(model.layers)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _recommend_dl_preprocessing(self, data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend preprocessing steps for deep learning"""
        return {
            "feature_scaling": "StandardScaler recommended for neural networks",
            "categorical_encoding": "Label encoding for high-cardinality, one-hot for low-cardinality",
            "missing_values": "Mean/median imputation for numeric, mode for categorical",
            "outlier_handling": "Consider robust scaling if many outliers detected"
        }
    
    def _recommend_training_strategy(self, data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend training strategy based on data characteristics"""
        data_size = data_analysis["data_shape"][0]
        
        if data_size < 1000:
            return {
                "epochs": 50,
                "batch_size": 16,
                "validation_split": 0.3,
                "early_stopping": True,
                "learning_rate": 0.01
            }
        elif data_size < 10000:
            return {
                "epochs": 100,
                "batch_size": 32,
                "validation_split": 0.2,
                "early_stopping": True,
                "learning_rate": 0.001
            }
        else:
            return {
                "epochs": 200,
                "batch_size": 64,
                "validation_split": 0.2,
                "early_stopping": True,
                "learning_rate": 0.0001
            }
    
    def get_model_results(self, model_key: Optional[str] = None) -> Dict[str, Any]:
        """Get results for specific model or all models"""
        if model_key:
            return {
                "model": self.models.get(model_key),
                "training_history": self.training_history.get(model_key)
            }
        else:
            return {
                "models": list(self.models.keys()),
                "frameworks_available": {
                    "tensorflow": TENSORFLOW_AVAILABLE,
                    "pytorch": PYTORCH_AVAILABLE
                }
            }

# Convenience functions
def analyze_with_deep_learning(file_path: str, target_column: str, 
                              problem_type: Optional[str] = None,
                              frameworks: List[str] = None) -> Dict[str, Any]:
    """
    Convenience function for comprehensive deep learning analysis
    
    Args:
        file_path: Path to data file
        target_column: Target variable
        problem_type: 'classification', 'regression', or auto-detect
        frameworks: List of frameworks to use
        
    Returns:
        Complete deep learning analysis results
    """
    processor = DeepLearningProcessor(file_path=file_path)
    return processor.comprehensive_deep_learning_analysis(target_column, problem_type, frameworks)

def quick_neural_network(file_path: str, target_column: str, 
                        framework: str = "tensorflow") -> Dict[str, Any]:
    """
    Convenience function for quick neural network training
    
    Args:
        file_path: Path to data file
        target_column: Target variable
        framework: 'tensorflow' or 'pytorch'
        
    Returns:
        Quick neural network results
    """
    processor = DeepLearningProcessor(file_path=file_path)
    
    # Get recommendations
    recommendations = processor.get_deep_learning_recommendations(target_column)
    if "error" in recommendations:
        return recommendations
    
    # Use first recommended architecture
    arch_recommendations = recommendations["architecture_recommendations"]["recommended_models"]
    if not arch_recommendations:
        return {"error": "No suitable architecture found"}
    
    best_arch = arch_recommendations[0]
    problem_type = recommendations["problem_type"]
    
    # Build and train model
    if framework == "tensorflow" and TENSORFLOW_AVAILABLE:
        input_shape = (recommendations["data_analysis"]["feature_analysis"]["total_features"],)
        output_shape = 1 if problem_type == "regression" else recommendations["data_analysis"]["target_analysis"]["num_classes"]
        
        build_result = processor.build_tensorflow_model(best_arch, input_shape, output_shape, problem_type)
        if "error" in build_result:
            return build_result
        
        return processor.train_tensorflow_model(build_result["model_key"], target_column)
    
    elif framework == "pytorch" and PYTORCH_AVAILABLE:
        input_size = recommendations["data_analysis"]["feature_analysis"]["total_features"]
        output_size = 1 if problem_type == "regression" else recommendations["data_analysis"]["target_analysis"]["num_classes"]
        
        build_result = processor.build_pytorch_model(best_arch, input_size, output_size, problem_type)
        if "error" in build_result:
            return build_result
        
        return processor.train_pytorch_model(build_result["model_key"], target_column)
    
    else:
        return {"error": f"Framework '{framework}' not available"}