#!/usr/bin/env python3
"""
Advanced Ensemble Learning Processor
Comprehensive ensemble methods including Voting, Bagging, Boosting, Stacking, and Blending
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime
import logging
import warnings
warnings.filterwarnings('ignore')

# Core ensemble learning libraries - LAZY LOADING TO PREVENT MUTEX LOCKS
SKLEARN_AVAILABLE = None

def _lazy_import_sklearn():
    """Lazy import sklearn components only when needed"""
    global SKLEARN_AVAILABLE
    if SKLEARN_AVAILABLE is None:
        try:
            from sklearn.ensemble import (
                VotingClassifier, VotingRegressor,
                BaggingClassifier, BaggingRegressor,
                RandomForestClassifier, RandomForestRegressor,
                ExtraTreesClassifier, ExtraTreesRegressor,
                AdaBoostClassifier, AdaBoostRegressor,
                GradientBoostingClassifier, GradientBoostingRegressor,
                StackingClassifier, StackingRegressor
            )
            from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
            from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
            from sklearn.svm import SVC, SVR
            from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
            from sklearn.naive_bayes import GaussianNB
            from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, KFold
            from sklearn.preprocessing import StandardScaler, LabelEncoder
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin, clone
            
            SKLEARN_AVAILABLE = True
            return {
                'VotingClassifier': VotingClassifier,
                'VotingRegressor': VotingRegressor,
                'BaggingClassifier': BaggingClassifier,
                'BaggingRegressor': BaggingRegressor,
                'RandomForestClassifier': RandomForestClassifier,
                'RandomForestRegressor': RandomForestRegressor,
                'ExtraTreesClassifier': ExtraTreesClassifier,
                'ExtraTreesRegressor': ExtraTreesRegressor,
                'AdaBoostClassifier': AdaBoostClassifier,
                'AdaBoostRegressor': AdaBoostRegressor,
                'GradientBoostingClassifier': GradientBoostingClassifier,
                'GradientBoostingRegressor': GradientBoostingRegressor,
                'StackingClassifier': StackingClassifier,
                'StackingRegressor': StackingRegressor,
                'LogisticRegression': LogisticRegression,
                'LinearRegression': LinearRegression,
                'Ridge': Ridge,
                'DecisionTreeClassifier': DecisionTreeClassifier,
                'DecisionTreeRegressor': DecisionTreeRegressor,
                'SVC': SVC,
                'SVR': SVR,
                'KNeighborsClassifier': KNeighborsClassifier,
                'KNeighborsRegressor': KNeighborsRegressor,
                'GaussianNB': GaussianNB,
                'train_test_split': train_test_split,
                'cross_val_score': cross_val_score,
                'StratifiedKFold': StratifiedKFold,
                'KFold': KFold,
                'StandardScaler': StandardScaler,
                'LabelEncoder': LabelEncoder,
                'accuracy_score': accuracy_score,
                'precision_score': precision_score,
                'recall_score': recall_score,
                'f1_score': f1_score,
                'roc_auc_score': roc_auc_score,
                'mean_squared_error': mean_squared_error,
                'mean_absolute_error': mean_absolute_error,
                'r2_score': r2_score,
                'BaseEstimator': BaseEstimator,
                'ClassifierMixin': ClassifierMixin,
                'RegressorMixin': RegressorMixin,
                'clone': clone
            }
        except ImportError:
            SKLEARN_AVAILABLE = False
            logging.warning("Scikit-learn not available. Ensemble learning capabilities will be disabled.")
            return None
    elif SKLEARN_AVAILABLE:
        # Re-import if available
        from sklearn.ensemble import (
            VotingClassifier, VotingRegressor,
            BaggingClassifier, BaggingRegressor,
            RandomForestClassifier, RandomForestRegressor,
            ExtraTreesClassifier, ExtraTreesRegressor,
            AdaBoostClassifier, AdaBoostRegressor,
            GradientBoostingClassifier, GradientBoostingRegressor,
            StackingClassifier, StackingRegressor
        )
        from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
        from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
        from sklearn.svm import SVC, SVR
        from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
        from sklearn.naive_bayes import GaussianNB
        from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, KFold
        from sklearn.preprocessing import StandardScaler, LabelEncoder
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin, clone
        
        return {
            'VotingClassifier': VotingClassifier,
            'VotingRegressor': VotingRegressor,
            'BaggingClassifier': BaggingClassifier,
            'BaggingRegressor': BaggingRegressor,
            'RandomForestClassifier': RandomForestClassifier,
            'RandomForestRegressor': RandomForestRegressor,
            'ExtraTreesClassifier': ExtraTreesClassifier,
            'ExtraTreesRegressor': ExtraTreesRegressor,
            'AdaBoostClassifier': AdaBoostClassifier,
            'AdaBoostRegressor': AdaBoostRegressor,
            'GradientBoostingClassifier': GradientBoostingClassifier,
            'GradientBoostingRegressor': GradientBoostingRegressor,
            'StackingClassifier': StackingClassifier,
            'StackingRegressor': StackingRegressor,
            'LogisticRegression': LogisticRegression,
            'LinearRegression': LinearRegression,
            'Ridge': Ridge,
            'DecisionTreeClassifier': DecisionTreeClassifier,
            'DecisionTreeRegressor': DecisionTreeRegressor,
            'SVC': SVC,
            'SVR': SVR,
            'KNeighborsClassifier': KNeighborsClassifier,
            'KNeighborsRegressor': KNeighborsRegressor,
            'GaussianNB': GaussianNB,
            'train_test_split': train_test_split,
            'cross_val_score': cross_val_score,
            'StratifiedKFold': StratifiedKFold,
            'KFold': KFold,
            'StandardScaler': StandardScaler,
            'LabelEncoder': LabelEncoder,
            'accuracy_score': accuracy_score,
            'precision_score': precision_score,
            'recall_score': recall_score,
            'f1_score': f1_score,
            'roc_auc_score': roc_auc_score,
            'mean_squared_error': mean_squared_error,
            'mean_absolute_error': mean_absolute_error,
            'r2_score': r2_score,
            'BaseEstimator': BaseEstimator,
            'ClassifierMixin': ClassifierMixin,
            'RegressorMixin': RegressorMixin,
            'clone': clone
        }
    else:
        return None

def _check_sklearn_available():
    return _lazy_import_sklearn() is not None

# Lazy imports to prevent mutex locks during startup
XGBOOST_AVAILABLE = None
LIGHTGBM_AVAILABLE = None

def _lazy_import_xgboost():
    """Lazy import XGBoost only when needed"""
    global XGBOOST_AVAILABLE
    if XGBOOST_AVAILABLE is None:
        try:
            import xgboost as xgb
            XGBOOST_AVAILABLE = True
            return xgb
        except ImportError:
            XGBOOST_AVAILABLE = False
            logging.warning("XGBoost not available. XGBoost ensemble methods will be disabled.")
            return None
    elif XGBOOST_AVAILABLE:
        import xgboost as xgb
        return xgb
    else:
        return None

def _lazy_import_lightgbm():
    """Lazy import LightGBM only when needed"""
    global LIGHTGBM_AVAILABLE
    if LIGHTGBM_AVAILABLE is None:
        try:
            import lightgbm as lgb
            LIGHTGBM_AVAILABLE = True
            return lgb
        except ImportError:
            LIGHTGBM_AVAILABLE = False
            logging.warning("LightGBM not available. LightGBM ensemble methods will be disabled.")
            return None
    elif LIGHTGBM_AVAILABLE:
        import lightgbm as lgb
        return lgb
    else:
        return None

# Keep backward compatibility - will be evaluated only when accessed
def _check_xgboost_available():
    return _lazy_import_xgboost() is not None

def _check_lightgbm_available():
    return _lazy_import_lightgbm() is not None

try:
    from ..preprocessors.csv_processor import CSVProcessor
    from .ml_processor import MLProcessor
except ImportError:
    from csv_processor import CSVProcessor
    from ml_processor import MLProcessor

logger = logging.getLogger(__name__)

# 暂时注释掉复杂的自定义类，避免导入问题
# TODO: 在完成基础架构重构后，使用新的基类重新实现

# 注释掉 AdvancedStackingClassifier 类定义，避免导入问题
# 将在后续使用新的基础架构重新实现

class EnsembleProcessor:
    
    def __init__(self, base_models: List[Any], meta_model: Any, 
                 cv_folds: int = 5, use_probabilities: bool = True,
                 blending_ratio: float = 0.0):
        self.base_models = base_models
        self.meta_model = meta_model
        self.cv_folds = cv_folds
        self.use_probabilities = use_probabilities
        self.blending_ratio = blending_ratio
        self.fitted_base_models = []
        self.fitted_meta_model = None
        
    def fit(self, X, y):
        """Fit the stacking classifier"""
        try:
            X = np.array(X)
            y = np.array(y)
            
            # Create meta-features using cross-validation
            meta_features = np.zeros((X.shape[0], len(self.base_models)))
            
            # K-fold cross-validation for meta-features
            kf = StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=42)
            
            for i, model in enumerate(self.base_models):
                model_predictions = np.zeros(X.shape[0])
                
                for train_idx, val_idx in kf.split(X, y):
                    X_train, X_val = X[train_idx], X[val_idx]
                    y_train = y[train_idx]
                    
                    # Clone and fit model
                    cloned_model = clone(model)
                    cloned_model.fit(X_train, y_train)
                    
                    # Generate predictions for validation set
                    if self.use_probabilities and hasattr(cloned_model, 'predict_proba'):
                        predictions = cloned_model.predict_proba(X_val)
                        if predictions.shape[1] == 2:  # Binary classification
                            predictions = predictions[:, 1]
                        else:  # Multiclass - use max probability
                            predictions = np.max(predictions, axis=1)
                    else:
                        predictions = cloned_model.predict(X_val)
                    
                    model_predictions[val_idx] = predictions
                
                meta_features[:, i] = model_predictions
            
            # Add blending with original features if specified
            if self.blending_ratio > 0:
                # Normalize original features
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                # Select subset of original features
                n_features_to_blend = int(X.shape[1] * self.blending_ratio)
                feature_indices = np.random.choice(X.shape[1], n_features_to_blend, replace=False)
                X_blend = X_scaled[:, feature_indices]
                
                # Combine meta-features with blended original features
                meta_features = np.hstack([meta_features, X_blend])
                self.feature_indices = feature_indices
                self.scaler = scaler
            
            # Fit meta-model on meta-features
            self.fitted_meta_model = clone(self.meta_model)
            self.fitted_meta_model.fit(meta_features, y)
            
            # Fit base models on full dataset
            self.fitted_base_models = []
            for model in self.base_models:
                fitted_model = clone(model)
                fitted_model.fit(X, y)
                self.fitted_base_models.append(fitted_model)
            
            return self
            
        except Exception as e:
            logger.error(f"Error fitting stacking classifier: {e}")
            raise
    
    def predict(self, X):
        """Make predictions using the stacked model"""
        try:
            X = np.array(X)
            
            # Generate meta-features from base models
            meta_features = np.zeros((X.shape[0], len(self.fitted_base_models)))
            
            for i, model in enumerate(self.fitted_base_models):
                if self.use_probabilities and hasattr(model, 'predict_proba'):
                    predictions = model.predict_proba(X)
                    if predictions.shape[1] == 2:  # Binary classification
                        predictions = predictions[:, 1]
                    else:  # Multiclass - use max probability
                        predictions = np.max(predictions, axis=1)
                else:
                    predictions = model.predict(X)
                
                meta_features[:, i] = predictions
            
            # Add blended features if used during training
            if self.blending_ratio > 0 and hasattr(self, 'feature_indices'):
                X_scaled = self.scaler.transform(X)
                X_blend = X_scaled[:, self.feature_indices]
                meta_features = np.hstack([meta_features, X_blend])
            
            # Use meta-model for final prediction
            return self.fitted_meta_model.predict(meta_features)
            
        except Exception as e:
            logger.error(f"Error predicting with stacking classifier: {e}")
            raise
    
    def predict_proba(self, X):
        """Predict class probabilities"""
        if hasattr(self.fitted_meta_model, 'predict_proba'):
            X = np.array(X)
            
            # Generate meta-features
            meta_features = np.zeros((X.shape[0], len(self.fitted_base_models)))
            
            for i, model in enumerate(self.fitted_base_models):
                if self.use_probabilities and hasattr(model, 'predict_proba'):
                    predictions = model.predict_proba(X)
                    if predictions.shape[1] == 2:
                        predictions = predictions[:, 1]
                    else:
                        predictions = np.max(predictions, axis=1)
                else:
                    predictions = model.predict(X)
                
                meta_features[:, i] = predictions
            
            # Add blended features if used
            if self.blending_ratio > 0 and hasattr(self, 'feature_indices'):
                X_scaled = self.scaler.transform(X)
                X_blend = X_scaled[:, self.feature_indices]
                meta_features = np.hstack([meta_features, X_blend])
            
            return self.fitted_meta_model.predict_proba(meta_features)
        else:
            raise AttributeError("Meta-model does not support probability prediction")

# 暂时注释掉复杂的自定义类，避免导入问题
# TODO: 在完成基础架构重构后，使用新的基类重新实现
# class AdvancedStackingRegressor(BaseEstimator, RegressorMixin):
    """
    Advanced stacking regressor with cross-validation and blending
    """
    
    def __init__(self, base_models: List[Any], meta_model: Any, 
                 cv_folds: int = 5, blending_ratio: float = 0.0):
        self.base_models = base_models
        self.meta_model = meta_model
        self.cv_folds = cv_folds
        self.blending_ratio = blending_ratio
        self.fitted_base_models = []
        self.fitted_meta_model = None
        
    def fit(self, X, y):
        """Fit the stacking regressor"""
        try:
            X = np.array(X)
            y = np.array(y)
            
            # Create meta-features using cross-validation
            meta_features = np.zeros((X.shape[0], len(self.base_models)))
            
            # K-fold cross-validation for meta-features
            kf = KFold(n_splits=self.cv_folds, shuffle=True, random_state=42)
            
            for i, model in enumerate(self.base_models):
                model_predictions = np.zeros(X.shape[0])
                
                for train_idx, val_idx in kf.split(X):
                    X_train, X_val = X[train_idx], X[val_idx]
                    y_train = y[train_idx]
                    
                    # Clone and fit model
                    cloned_model = clone(model)
                    cloned_model.fit(X_train, y_train)
                    
                    # Generate predictions for validation set
                    predictions = cloned_model.predict(X_val)
                    model_predictions[val_idx] = predictions
                
                meta_features[:, i] = model_predictions
            
            # Add blending with original features if specified
            if self.blending_ratio > 0:
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                n_features_to_blend = int(X.shape[1] * self.blending_ratio)
                feature_indices = np.random.choice(X.shape[1], n_features_to_blend, replace=False)
                X_blend = X_scaled[:, feature_indices]
                
                meta_features = np.hstack([meta_features, X_blend])
                self.feature_indices = feature_indices
                self.scaler = scaler
            
            # Fit meta-model on meta-features
            self.fitted_meta_model = clone(self.meta_model)
            self.fitted_meta_model.fit(meta_features, y)
            
            # Fit base models on full dataset
            self.fitted_base_models = []
            for model in self.base_models:
                fitted_model = clone(model)
                fitted_model.fit(X, y)
                self.fitted_base_models.append(fitted_model)
            
            return self
            
        except Exception as e:
            logger.error(f"Error fitting stacking regressor: {e}")
            raise
    
    def predict(self, X):
        """Make predictions using the stacked model"""
        try:
            X = np.array(X)
            
            # Generate meta-features from base models
            meta_features = np.zeros((X.shape[0], len(self.fitted_base_models)))
            
            for i, model in enumerate(self.fitted_base_models):
                predictions = model.predict(X)
                meta_features[:, i] = predictions
            
            # Add blended features if used during training
            if self.blending_ratio > 0 and hasattr(self, 'feature_indices'):
                X_scaled = self.scaler.transform(X)
                X_blend = X_scaled[:, self.feature_indices]
                meta_features = np.hstack([meta_features, X_blend])
            
            # Use meta-model for final prediction
            return self.fitted_meta_model.predict(meta_features)
            
        except Exception as e:
            logger.error(f"Error predicting with stacking regressor: {e}")
            raise

class EnsembleProcessor:
    """
    Advanced ensemble learning processor
    Provides voting, bagging, boosting, stacking, and blending methods
    """
    
    def __init__(self, csv_processor: Optional[CSVProcessor] = None, file_path: Optional[str] = None):
        """
        Initialize ensemble learning processor
        
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
        self.ml_processor = None
        self.ensemble_models = {}
        self.base_models = {}
        self.ensemble_results = {}
        self.scalers = {}
        self.encoders = {}
        
        self._load_data()
    
    def _load_data(self) -> bool:
        """Load data from CSV processor"""
        try:
            if not self.csv_processor.load_csv():
                return False
            self.df = self.csv_processor.df.copy()
            self.ml_processor = MLProcessor(self.csv_processor)
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def get_ensemble_recommendations(self, target_column: str, problem_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get ensemble learning recommendations based on data characteristics
        
        Args:
            target_column: Target variable
            problem_type: 'classification' or 'regression'
            
        Returns:
            Ensemble recommendations and strategy suggestions
        """
        try:
            if self.df is None:
                return {"error": "No data loaded"}
            
            if not SKLEARN_AVAILABLE:
                return {"error": "Scikit-learn not available for ensemble learning"}
            
            if target_column not in self.df.columns:
                return {"error": f"Target column '{target_column}' not found"}
            
            # Auto-detect problem type if not specified
            if problem_type is None:
                problem_type = self._detect_problem_type(self.df[target_column])
            
            # Get basic ML analysis
            ml_analysis = self.ml_processor.get_ml_analysis(target_column, problem_type)
            
            recommendations = {
                "problem_type": problem_type,
                "data_analysis": ml_analysis,
                "ensemble_strategies": self._recommend_ensemble_strategies(ml_analysis, problem_type),
                "base_model_recommendations": self._recommend_base_models(ml_analysis, problem_type),
                "meta_model_recommendations": self._recommend_meta_models(problem_type),
                "ensemble_configurations": self._generate_ensemble_configs(ml_analysis, problem_type),
                "library_availability": {
                    "sklearn": SKLEARN_AVAILABLE,
                    "xgboost": _check_xgboost_available(),
                    "lightgbm": _check_lightgbm_available()
                }
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting ensemble recommendations: {e}")
            return {"error": str(e)}
    
    def _recommend_ensemble_strategies(self, ml_analysis: Dict[str, Any], problem_type: str) -> Dict[str, Any]:
        """Recommend ensemble strategies based on data characteristics"""
        try:
            data_shape = ml_analysis.get("ml_metadata", {}).get("data_shape", [0, 0])
            n_samples, n_features = data_shape
            
            strategies = {
                "recommended_methods": [],
                "method_priorities": {},
                "ensemble_complexity": {}
            }
            
            # Voting ensembles (always recommended as baseline)
            voting_strategy = {
                "method": "Voting",
                "description": "Combine predictions from multiple models",
                "suitability": "high",
                "pros": ["Simple", "Robust", "Improves generalization"],
                "cons": ["Limited by weakest model", "No learning from combination"],
                "priority": "high",
                "complexity": "low"
            }
            strategies["recommended_methods"].append(voting_strategy)
            
            # Bagging methods
            bagging_strategy = {
                "method": "Bagging",
                "description": "Bootstrap aggregating with Random Forest",
                "suitability": "high",
                "pros": ["Reduces overfitting", "Handles noise well", "Parallel training"],
                "cons": ["May increase bias", "Less interpretable"],
                "priority": "high",
                "complexity": "medium"
            }
            strategies["recommended_methods"].append(bagging_strategy)
            
            # Boosting methods
            boosting_strategy = {
                "method": "Boosting",
                "description": "Sequential learning with AdaBoost/Gradient Boosting",
                "suitability": "medium",
                "pros": ["Reduces bias", "Adaptive learning", "Often high performance"],
                "cons": ["Prone to overfitting", "Sequential training", "Sensitive to noise"],
                "priority": "medium",
                "complexity": "medium"
            }
            strategies["recommended_methods"].append(boosting_strategy)
            
            # Stacking (if sufficient data)
            if n_samples > 1000:
                stacking_strategy = {
                    "method": "Stacking",
                    "description": "Meta-learning with cross-validation",
                    "suitability": "high",
                    "pros": ["Learns optimal combination", "Can capture complex interactions", "Often best performance"],
                    "cons": ["More complex", "Requires more data", "Risk of overfitting"],
                    "priority": "high" if n_samples > 5000 else "medium",
                    "complexity": "high"
                }
                strategies["recommended_methods"].append(stacking_strategy)
            
            # Blending (alternative to stacking)
            blending_strategy = {
                "method": "Blending",
                "description": "Holdout-based meta-learning",
                "suitability": "medium",
                "pros": ["Simpler than stacking", "Less prone to overfitting", "Faster training"],
                "cons": ["Uses less data for base models", "May be less optimal than stacking"],
                "priority": "medium",
                "complexity": "medium"
            }
            strategies["recommended_methods"].append(blending_strategy)
            
            # Adjust recommendations based on data characteristics
            if n_samples < 500:
                # Small dataset - prefer simpler methods
                for strategy in strategies["recommended_methods"]:
                    if strategy["complexity"] == "high":
                        strategy["priority"] = "low"
                        strategy["suitability"] = "low"
            
            if n_features > n_samples // 10:
                # High-dimensional data - be cautious with complex ensembles
                strategies["preprocessing_recommendation"] = "Consider feature selection or dimensionality reduction"
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error recommending ensemble strategies: {e}")
            return {"error": str(e)}
    
    def _recommend_base_models(self, ml_analysis: Dict[str, Any], problem_type: str) -> Dict[str, Any]:
        """Recommend base models for ensemble"""
        try:
            data_shape = ml_analysis.get("ml_metadata", {}).get("data_shape", [0, 0])
            n_samples, n_features = data_shape
            
            base_models = {
                "diverse_models": [],
                "fast_models": [],
                "high_performance_models": [],
                "model_diversity_strategy": {}
            }
            
            if problem_type == "classification":
                # Diverse models for good ensemble performance
                diverse_models = [
                    {
                        "name": "Logistic Regression",
                        "type": "linear",
                        "strengths": ["Fast", "Interpretable", "Different bias"],
                        "sklearn_class": "LogisticRegression"
                    },
                    {
                        "name": "Random Forest",
                        "type": "tree_ensemble",
                        "strengths": ["Non-linear", "Feature importance", "Robust"],
                        "sklearn_class": "RandomForestClassifier"
                    },
                    {
                        "name": "Support Vector Machine",
                        "type": "kernel",
                        "strengths": ["Different decision boundary", "Kernel methods"],
                        "sklearn_class": "SVC"
                    },
                    {
                        "name": "Naive Bayes",
                        "type": "probabilistic",
                        "strengths": ["Fast", "Probabilistic", "Different assumptions"],
                        "sklearn_class": "GaussianNB"
                    }
                ]
                
                # Add advanced models if available
                if _check_xgboost_available():
                    diverse_models.append({
                        "name": "XGBoost",
                        "type": "gradient_boosting",
                        "strengths": ["High performance", "Handle missing values", "Feature importance"],
                        "sklearn_class": "XGBClassifier"
                    })
                
                if _check_lightgbm_available():
                    diverse_models.append({
                        "name": "LightGBM",
                        "type": "gradient_boosting",
                        "strengths": ["Fast", "Memory efficient", "High accuracy"],
                        "sklearn_class": "LGBMClassifier"
                    })
                
                base_models["diverse_models"] = diverse_models
                
                # Fast models for large datasets
                if n_samples > 10000:
                    fast_models = [
                        {"name": "Logistic Regression", "sklearn_class": "LogisticRegression"},
                        {"name": "Naive Bayes", "sklearn_class": "GaussianNB"},
                        {"name": "Linear SVM", "sklearn_class": "LinearSVC"}
                    ]
                    base_models["fast_models"] = fast_models
                
            else:  # regression
                diverse_models = [
                    {
                        "name": "Linear Regression",
                        "type": "linear",
                        "strengths": ["Fast", "Interpretable", "Linear bias"],
                        "sklearn_class": "LinearRegression"
                    },
                    {
                        "name": "Random Forest",
                        "type": "tree_ensemble", 
                        "strengths": ["Non-linear", "Feature importance", "Robust"],
                        "sklearn_class": "RandomForestRegressor"
                    },
                    {
                        "name": "Support Vector Regression",
                        "type": "kernel",
                        "strengths": ["Non-linear", "Robust to outliers"],
                        "sklearn_class": "SVR"
                    },
                    {
                        "name": "Ridge Regression",
                        "type": "regularized_linear",
                        "strengths": ["Regularization", "Handles multicollinearity"],
                        "sklearn_class": "Ridge"
                    }
                ]
                
                # Add advanced models
                if _check_xgboost_available():
                    diverse_models.append({
                        "name": "XGBoost",
                        "type": "gradient_boosting",
                        "strengths": ["High performance", "Non-linear", "Feature importance"],
                        "sklearn_class": "XGBRegressor"
                    })
                
                base_models["diverse_models"] = diverse_models
            
            # Model diversity strategy
            base_models["model_diversity_strategy"] = {
                "algorithm_diversity": "Use different algorithm types (linear, tree, kernel)",
                "hyperparameter_diversity": "Vary hyperparameters within same algorithm",
                "data_diversity": "Use different feature subsets or sampling strategies",
                "training_diversity": "Different random seeds and initialization"
            }
            
            return base_models
            
        except Exception as e:
            logger.error(f"Error recommending base models: {e}")
            return {"error": str(e)}
    
    def _recommend_meta_models(self, problem_type: str) -> Dict[str, Any]:
        """Recommend meta-models for stacking"""
        try:
            meta_models = {
                "recommended_meta_models": [],
                "selection_criteria": {}
            }
            
            if problem_type == "classification":
                recommended = [
                    {
                        "name": "Logistic Regression",
                        "suitability": "high",
                        "pros": ["Simple", "Fast", "Interpretable", "Probabilistic"],
                        "cons": ["Linear assumptions"],
                        "sklearn_class": "LogisticRegression",
                        "priority": "high"
                    },
                    {
                        "name": "Ridge Classifier",
                        "suitability": "medium",
                        "pros": ["Regularization", "Handles multicollinearity"],
                        "cons": ["Linear assumptions"],
                        "sklearn_class": "RidgeClassifier",
                        "priority": "medium"
                    },
                    {
                        "name": "Random Forest",
                        "suitability": "medium",
                        "pros": ["Non-linear", "Feature importance"],
                        "cons": ["More complex", "May overfit meta-features"],
                        "sklearn_class": "RandomForestClassifier",
                        "priority": "low"
                    }
                ]
            else:  # regression
                recommended = [
                    {
                        "name": "Linear Regression",
                        "suitability": "high",
                        "pros": ["Simple", "Fast", "Interpretable"],
                        "cons": ["Linear assumptions"],
                        "sklearn_class": "LinearRegression",
                        "priority": "high"
                    },
                    {
                        "name": "Ridge Regression",
                        "suitability": "high",
                        "pros": ["Regularization", "Stable"],
                        "cons": ["Linear assumptions"],
                        "sklearn_class": "Ridge",
                        "priority": "high"
                    },
                    {
                        "name": "Random Forest",
                        "suitability": "medium",
                        "pros": ["Non-linear", "Robust"],
                        "cons": ["May overfit meta-features"],
                        "sklearn_class": "RandomForestRegressor",
                        "priority": "medium"
                    }
                ]
            
            meta_models["recommended_meta_models"] = recommended
            
            meta_models["selection_criteria"] = {
                "simplicity": "Prefer simple models to avoid overfitting meta-features",
                "speed": "Meta-model training should be fast",
                "interpretability": "Linear models provide better insight into base model contributions",
                "regularization": "Consider regularization to prevent overfitting"
            }
            
            return meta_models
            
        except Exception as e:
            logger.error(f"Error recommending meta models: {e}")
            return {"error": str(e)}
    
    def create_voting_ensemble(self, target_column: str, base_models: List[str] = None,
                             voting: str = "soft", weights: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Create voting ensemble
        
        Args:
            target_column: Target variable
            base_models: List of base model names
            voting: 'hard' or 'soft' voting
            weights: Optional weights for models
            
        Returns:
            Voting ensemble results
        """
        try:
            if not SKLEARN_AVAILABLE:
                return {"error": "Scikit-learn not available"}
            
            problem_type = self._detect_problem_type(self.df[target_column])
            
            # Default base models if not specified
            if base_models is None:
                if problem_type == "classification":
                    base_models = ["logistic_regression", "random_forest_classifier", "naive_bayes"]
                else:
                    base_models = ["linear_regression", "random_forest_regressor", "ridge"]
            
            # Prepare data
            X, y = self._prepare_data_for_training(target_column)
            if isinstance(X, dict) and "error" in X:
                return X
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Create base models
            models = []
            model_performances = {}
            
            for model_name in base_models:
                try:
                    model = self._get_model_instance(model_name, problem_type)
                    if model is None:
                        logger.warning(f"Skipping unknown model: {model_name}")
                        continue
                    
                    # Train individual model and get performance
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)
                    
                    # Calculate performance
                    if problem_type == "classification":
                        score = accuracy_score(y_test, y_pred)
                    else:
                        score = r2_score(y_test, y_pred)
                    
                    models.append((model_name, model))
                    model_performances[model_name] = score
                    
                except Exception as e:
                    logger.warning(f"Failed to create model {model_name}: {e}")
            
            if len(models) < 2:
                return {"error": "Need at least 2 models for ensemble"}
            
            # Create voting ensemble
            if problem_type == "classification":
                ensemble = VotingClassifier(estimators=models, voting=voting, weights=weights)
            else:
                ensemble = VotingRegressor(estimators=models, weights=weights)
            
            # Train ensemble
            start_time = datetime.now()
            ensemble.fit(X_train, y_train)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Evaluate ensemble
            y_pred_ensemble = ensemble.predict(X_test)
            
            # Calculate metrics
            ensemble_metrics = self._calculate_metrics(y_test, y_pred_ensemble, problem_type)
            
            # Store ensemble
            ensemble_key = f"voting_{problem_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.ensemble_models[ensemble_key] = ensemble
            
            results = {
                "ensemble_key": ensemble_key,
                "ensemble_type": "voting",
                "voting_type": voting,
                "base_models": base_models,
                "model_weights": weights,
                "individual_performances": model_performances,
                "ensemble_metrics": ensemble_metrics,
                "training_time_seconds": round(training_time, 3),
                "improvement_analysis": self._analyze_ensemble_improvement(
                    model_performances, ensemble_metrics, problem_type
                )
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error creating voting ensemble: {e}")
            return {"error": str(e)}
    
    def create_stacking_ensemble(self, target_column: str, base_models: List[str] = None,
                               meta_model: str = None, cv_folds: int = 5,
                               use_probabilities: bool = True, blending_ratio: float = 0.0) -> Dict[str, Any]:
        """
        Create stacking ensemble with advanced features
        
        Args:
            target_column: Target variable
            base_models: List of base model names
            meta_model: Meta-model name
            cv_folds: Number of CV folds for meta-features
            use_probabilities: Use probabilities for classification meta-features
            blending_ratio: Ratio of original features to blend (0.0 = no blending)
            
        Returns:
            Stacking ensemble results
        """
        try:
            if not SKLEARN_AVAILABLE:
                return {"error": "Scikit-learn not available"}
            
            problem_type = self._detect_problem_type(self.df[target_column])
            
            # Default configurations
            if base_models is None:
                if problem_type == "classification":
                    base_models = ["logistic_regression", "random_forest_classifier", "svm_classifier", "naive_bayes"]
                else:
                    base_models = ["linear_regression", "random_forest_regressor", "ridge", "svm_regressor"]
            
            if meta_model is None:
                meta_model = "logistic_regression" if problem_type == "classification" else "ridge"
            
            # Prepare data
            X, y = self._prepare_data_for_training(target_column)
            if isinstance(X, dict) and "error" in X:
                return X
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Create base models
            base_model_instances = []
            base_model_performances = {}
            
            for model_name in base_models:
                try:
                    model = self._get_model_instance(model_name, problem_type)
                    if model is None:
                        logger.warning(f"Skipping unknown model: {model_name}")
                        continue
                    
                    # Test individual model performance
                    model_clone = clone(model)
                    model_clone.fit(X_train, y_train)
                    y_pred = model_clone.predict(X_test)
                    
                    if problem_type == "classification":
                        score = accuracy_score(y_test, y_pred)
                    else:
                        score = r2_score(y_test, y_pred)
                    
                    base_model_instances.append(model)
                    base_model_performances[model_name] = score
                    
                except Exception as e:
                    logger.warning(f"Failed to create base model {model_name}: {e}")
            
            if len(base_model_instances) < 2:
                return {"error": "Need at least 2 base models for stacking"}
            
            # Create meta-model
            meta_model_instance = self._get_model_instance(meta_model, problem_type)
            if meta_model_instance is None:
                return {"error": f"Unknown meta-model: {meta_model}"}
            
            # Create advanced stacking ensemble
            if problem_type == "classification":
                ensemble = AdvancedStackingClassifier(
                    base_models=base_model_instances,
                    meta_model=meta_model_instance,
                    cv_folds=cv_folds,
                    use_probabilities=use_probabilities,
                    blending_ratio=blending_ratio
                )
            else:
                ensemble = AdvancedStackingRegressor(
                    base_models=base_model_instances,
                    meta_model=meta_model_instance,
                    cv_folds=cv_folds,
                    blending_ratio=blending_ratio
                )
            
            # Train ensemble
            start_time = datetime.now()
            ensemble.fit(X_train, y_train)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Evaluate ensemble
            y_pred_ensemble = ensemble.predict(X_test)
            ensemble_metrics = self._calculate_metrics(y_test, y_pred_ensemble, problem_type)
            
            # Store ensemble
            ensemble_key = f"stacking_{problem_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.ensemble_models[ensemble_key] = ensemble
            
            results = {
                "ensemble_key": ensemble_key,
                "ensemble_type": "stacking",
                "base_models": base_models,
                "meta_model": meta_model,
                "cv_folds": cv_folds,
                "use_probabilities": use_probabilities,
                "blending_ratio": blending_ratio,
                "base_model_performances": base_model_performances,
                "ensemble_metrics": ensemble_metrics,
                "training_time_seconds": round(training_time, 3),
                "improvement_analysis": self._analyze_ensemble_improvement(
                    base_model_performances, ensemble_metrics, problem_type
                ),
                "stacking_analysis": self._analyze_stacking_performance(ensemble, X_test, y_test)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error creating stacking ensemble: {e}")
            return {"error": str(e)}
    
    def create_bagging_ensemble(self, target_column: str, base_estimator: str = None,
                              n_estimators: int = 10, max_samples: float = 1.0,
                              max_features: float = 1.0) -> Dict[str, Any]:
        """
        Create bagging ensemble
        
        Args:
            target_column: Target variable
            base_estimator: Base estimator name
            n_estimators: Number of estimators
            max_samples: Fraction of samples to use
            max_features: Fraction of features to use
            
        Returns:
            Bagging ensemble results
        """
        try:
            if not SKLEARN_AVAILABLE:
                return {"error": "Scikit-learn not available"}
            
            problem_type = self._detect_problem_type(self.df[target_column])
            
            # Default base estimator
            if base_estimator is None:
                base_estimator = "decision_tree_classifier" if problem_type == "classification" else "decision_tree_regressor"
            
            # Prepare data
            X, y = self._prepare_data_for_training(target_column)
            if isinstance(X, dict) and "error" in X:
                return X
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Create base estimator
            base_model = self._get_model_instance(base_estimator, problem_type)
            if base_model is None:
                return {"error": f"Unknown base estimator: {base_estimator}"}
            
            # Create bagging ensemble
            if problem_type == "classification":
                ensemble = BaggingClassifier(
                    base_estimator=base_model,
                    n_estimators=n_estimators,
                    max_samples=max_samples,
                    max_features=max_features,
                    random_state=42
                )
            else:
                ensemble = BaggingRegressor(
                    base_estimator=base_model,
                    n_estimators=n_estimators,
                    max_samples=max_samples,
                    max_features=max_features,
                    random_state=42
                )
            
            # Train ensemble
            start_time = datetime.now()
            ensemble.fit(X_train, y_train)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Evaluate ensemble vs base estimator
            base_model.fit(X_train, y_train)
            y_pred_base = base_model.predict(X_test)
            y_pred_ensemble = ensemble.predict(X_test)
            
            base_metrics = self._calculate_metrics(y_test, y_pred_base, problem_type)
            ensemble_metrics = self._calculate_metrics(y_test, y_pred_ensemble, problem_type)
            
            # Store ensemble
            ensemble_key = f"bagging_{problem_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.ensemble_models[ensemble_key] = ensemble
            
            results = {
                "ensemble_key": ensemble_key,
                "ensemble_type": "bagging",
                "base_estimator": base_estimator,
                "n_estimators": n_estimators,
                "max_samples": max_samples,
                "max_features": max_features,
                "base_model_metrics": base_metrics,
                "ensemble_metrics": ensemble_metrics,
                "training_time_seconds": round(training_time, 3),
                "variance_reduction_analysis": self._analyze_variance_reduction(
                    base_metrics, ensemble_metrics, problem_type
                )
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error creating bagging ensemble: {e}")
            return {"error": str(e)}
    
    def create_boosting_ensemble(self, target_column: str, boosting_type: str = "adaboost",
                               n_estimators: int = 50, learning_rate: float = 1.0) -> Dict[str, Any]:
        """
        Create boosting ensemble
        
        Args:
            target_column: Target variable
            boosting_type: 'adaboost' or 'gradient_boosting'
            n_estimators: Number of estimators
            learning_rate: Learning rate
            
        Returns:
            Boosting ensemble results
        """
        try:
            if not SKLEARN_AVAILABLE:
                return {"error": "Scikit-learn not available"}
            
            problem_type = self._detect_problem_type(self.df[target_column])
            
            # Prepare data
            X, y = self._prepare_data_for_training(target_column)
            if isinstance(X, dict) and "error" in X:
                return X
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Create boosting ensemble
            if boosting_type == "adaboost":
                if problem_type == "classification":
                    ensemble = AdaBoostClassifier(
                        n_estimators=n_estimators,
                        learning_rate=learning_rate,
                        random_state=42
                    )
                else:
                    ensemble = AdaBoostRegressor(
                        n_estimators=n_estimators,
                        learning_rate=learning_rate,
                        random_state=42
                    )
            elif boosting_type == "gradient_boosting":
                if problem_type == "classification":
                    ensemble = GradientBoostingClassifier(
                        n_estimators=n_estimators,
                        learning_rate=learning_rate,
                        random_state=42
                    )
                else:
                    ensemble = GradientBoostingRegressor(
                        n_estimators=n_estimators,
                        learning_rate=learning_rate,
                        random_state=42
                    )
            else:
                return {"error": f"Unknown boosting type: {boosting_type}"}
            
            # Train ensemble
            start_time = datetime.now()
            ensemble.fit(X_train, y_train)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Evaluate ensemble
            y_pred_ensemble = ensemble.predict(X_test)
            ensemble_metrics = self._calculate_metrics(y_test, y_pred_ensemble, problem_type)
            
            # Analyze feature importance
            feature_importance = None
            if hasattr(ensemble, 'feature_importances_'):
                feature_names = X.columns if hasattr(X, 'columns') else [f"feature_{i}" for i in range(X.shape[1])]
                feature_importance = dict(zip(feature_names, ensemble.feature_importances_))
                feature_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Store ensemble
            ensemble_key = f"boosting_{boosting_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.ensemble_models[ensemble_key] = ensemble
            
            results = {
                "ensemble_key": ensemble_key,
                "ensemble_type": "boosting",
                "boosting_type": boosting_type,
                "n_estimators": n_estimators,
                "learning_rate": learning_rate,
                "ensemble_metrics": ensemble_metrics,
                "training_time_seconds": round(training_time, 3),
                "feature_importance": feature_importance,
                "boosting_analysis": self._analyze_boosting_performance(ensemble, boosting_type)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error creating boosting ensemble: {e}")
            return {"error": str(e)}
    
    def comprehensive_ensemble_analysis(self, target_column: str, problem_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive ensemble analysis with all methods
        
        Args:
            target_column: Target variable
            problem_type: 'classification' or 'regression'
            
        Returns:
            Complete ensemble analysis results
        """
        try:
            comprehensive_results = {
                "recommendations": {},
                "voting_ensemble": {},
                "stacking_ensemble": {},
                "bagging_ensemble": {},
                "boosting_ensemble": {},
                "ensemble_comparison": {},
                "best_ensemble": None,
                "insights": []
            }
            
            # 1. Get recommendations
            logger.info("Getting ensemble recommendations...")
            recommendations = self.get_ensemble_recommendations(target_column, problem_type)
            comprehensive_results["recommendations"] = recommendations
            
            if "error" in recommendations:
                return comprehensive_results
            
            problem_type = recommendations["problem_type"]
            
            # 2. Create and test different ensemble types
            ensemble_results = {}
            
            # Voting ensemble
            try:
                logger.info("Creating voting ensemble...")
                voting_result = self.create_voting_ensemble(target_column)
                if "error" not in voting_result:
                    comprehensive_results["voting_ensemble"] = voting_result
                    ensemble_results["voting"] = voting_result["ensemble_metrics"]
            except Exception as e:
                logger.warning(f"Voting ensemble failed: {e}")
            
            # Stacking ensemble
            try:
                logger.info("Creating stacking ensemble...")
                stacking_result = self.create_stacking_ensemble(target_column)
                if "error" not in stacking_result:
                    comprehensive_results["stacking_ensemble"] = stacking_result
                    ensemble_results["stacking"] = stacking_result["ensemble_metrics"]
            except Exception as e:
                logger.warning(f"Stacking ensemble failed: {e}")
            
            # Bagging ensemble
            try:
                logger.info("Creating bagging ensemble...")
                bagging_result = self.create_bagging_ensemble(target_column)
                if "error" not in bagging_result:
                    comprehensive_results["bagging_ensemble"] = bagging_result
                    ensemble_results["bagging"] = bagging_result["ensemble_metrics"]
            except Exception as e:
                logger.warning(f"Bagging ensemble failed: {e}")
            
            # Boosting ensemble
            try:
                logger.info("Creating boosting ensemble...")
                boosting_result = self.create_boosting_ensemble(target_column)
                if "error" not in boosting_result:
                    comprehensive_results["boosting_ensemble"] = boosting_result
                    ensemble_results["boosting"] = boosting_result["ensemble_metrics"]
            except Exception as e:
                logger.warning(f"Boosting ensemble failed: {e}")
            
            # 3. Compare ensemble methods
            if len(ensemble_results) > 1:
                comparison = self._compare_ensemble_methods(ensemble_results, problem_type)
                comprehensive_results["ensemble_comparison"] = comparison
                comprehensive_results["best_ensemble"] = comparison.get("best_method")
            
            # 4. Generate insights
            insights = self._generate_ensemble_insights(comprehensive_results, problem_type)
            comprehensive_results["insights"] = insights
            
            return comprehensive_results
            
        except Exception as e:
            logger.error(f"Error in comprehensive ensemble analysis: {e}")
            return {"error": str(e)}
    
    # Helper methods
    
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
    
    def _prepare_data_for_training(self, target_column: str) -> Tuple[Any, Any]:
        """Prepare data for training"""
        try:
            if self.df is None:
                return {"error": "No data loaded"}, None
            
            # Use MLProcessor's data preparation
            X = self.df.drop(columns=[target_column])
            y = self.df[target_column]
            
            # Basic preprocessing
            X = self.ml_processor._basic_preprocessing(X)
            
            return X, y
            
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return {"error": str(e)}, None
    
    def _get_model_instance(self, model_name: str, problem_type: str):
        """Get model instance for given name and problem type"""
        try:
            if problem_type == "classification":
                model_map = {
                    "logistic_regression": LogisticRegression(random_state=42, max_iter=1000),
                    "random_forest_classifier": RandomForestClassifier(random_state=42, n_estimators=100),
                    "decision_tree_classifier": DecisionTreeClassifier(random_state=42),
                    "svm_classifier": SVC(random_state=42, probability=True),
                    "knn_classifier": KNeighborsClassifier(),
                    "naive_bayes": GaussianNB(),
                    "ridge_classifier": LogisticRegression(random_state=42, C=1.0, penalty='l2')
                }
                
                # Add advanced models if available
                xgb = _lazy_import_xgboost()
                if xgb is not None:
                    model_map["xgb_classifier"] = xgb.XGBClassifier(random_state=42)
                
                lgb = _lazy_import_lightgbm()
                if lgb is not None:
                    model_map["lgb_classifier"] = lgb.LGBMClassifier(random_state=42)
                    
            else:  # regression
                model_map = {
                    "linear_regression": LinearRegression(),
                    "ridge": Ridge(random_state=42),
                    "random_forest_regressor": RandomForestRegressor(random_state=42, n_estimators=100),
                    "decision_tree_regressor": DecisionTreeRegressor(random_state=42),
                    "svm_regressor": SVR(),
                    "knn_regressor": KNeighborsRegressor()
                }
                
                # Add advanced models if available  
                xgb = _lazy_import_xgboost()
                if xgb is not None:
                    model_map["xgb_regressor"] = xgb.XGBRegressor(random_state=42)
                
                lgb = _lazy_import_lightgbm()
                if lgb is not None:
                    model_map["lgb_regressor"] = lgb.LGBMRegressor(random_state=42)
            
            return model_map.get(model_name.lower())
            
        except Exception as e:
            logger.error(f"Error getting model instance for {model_name}: {e}")
            return None
    
    def _calculate_metrics(self, y_true, y_pred, problem_type: str) -> Dict[str, float]:
        """Calculate appropriate metrics based on problem type"""
        try:
            metrics = {}
            
            if problem_type == "classification":
                metrics["accuracy"] = float(accuracy_score(y_true, y_pred))
                metrics["precision"] = float(precision_score(y_true, y_pred, average='weighted', zero_division=0))
                metrics["recall"] = float(recall_score(y_true, y_pred, average='weighted', zero_division=0))
                metrics["f1_score"] = float(f1_score(y_true, y_pred, average='weighted', zero_division=0))
                
                # Add ROC AUC for binary classification
                if len(np.unique(y_true)) == 2:
                    try:
                        metrics["roc_auc"] = float(roc_auc_score(y_true, y_pred))
                    except ValueError:
                        pass
            else:  # regression
                metrics["r2_score"] = float(r2_score(y_true, y_pred))
                metrics["mean_squared_error"] = float(mean_squared_error(y_true, y_pred))
                metrics["mean_absolute_error"] = float(mean_absolute_error(y_true, y_pred))
                metrics["root_mean_squared_error"] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {"error": str(e)}
    
    def _analyze_ensemble_improvement(self, individual_performances: Dict[str, float],
                                    ensemble_metrics: Dict[str, float], problem_type: str) -> Dict[str, Any]:
        """Analyze improvement from ensemble over individual models"""
        try:
            analysis = {
                "improvement_over_best": 0.0,
                "improvement_over_average": 0.0,
                "improvement_over_worst": 0.0,
                "consistency_improvement": 0.0
            }
            
            if not individual_performances:
                return analysis
            
            # Get primary metric
            if problem_type == "classification":
                primary_metric = "accuracy"
            else:
                primary_metric = "r2_score"
            
            ensemble_score = ensemble_metrics.get(primary_metric, 0)
            individual_scores = list(individual_performances.values())
            
            if individual_scores:
                best_individual = max(individual_scores)
                avg_individual = np.mean(individual_scores)
                worst_individual = min(individual_scores)
                
                analysis["improvement_over_best"] = ensemble_score - best_individual
                analysis["improvement_over_average"] = ensemble_score - avg_individual
                analysis["improvement_over_worst"] = ensemble_score - worst_individual
                analysis["consistency_improvement"] = np.std(individual_scores)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing ensemble improvement: {e}")
            return {"error": str(e)}
    
    def _analyze_stacking_performance(self, ensemble, X_test, y_test) -> Dict[str, Any]:
        """Analyze stacking-specific performance characteristics"""
        try:
            analysis = {
                "meta_feature_analysis": {},
                "base_model_contributions": {}
            }
            
            # Analyze meta-features if possible
            if hasattr(ensemble, 'fitted_base_models'):
                meta_features = np.zeros((X_test.shape[0], len(ensemble.fitted_base_models)))
                
                for i, model in enumerate(ensemble.fitted_base_models):
                    if hasattr(model, 'predict_proba') and ensemble.use_probabilities:
                        predictions = model.predict_proba(X_test)
                        if predictions.shape[1] == 2:
                            predictions = predictions[:, 1]
                        else:
                            predictions = np.max(predictions, axis=1)
                    else:
                        predictions = model.predict(X_test)
                    
                    meta_features[:, i] = predictions
                
                # Analyze meta-feature correlations
                meta_corr_matrix = np.corrcoef(meta_features.T)
                analysis["meta_feature_analysis"] = {
                    "average_correlation": float(np.mean(meta_corr_matrix)),
                    "max_correlation": float(np.max(meta_corr_matrix)),
                    "diversity_score": 1 - float(np.mean(np.abs(meta_corr_matrix)))
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing stacking performance: {e}")
            return {"error": str(e)}
    
    def _analyze_variance_reduction(self, base_metrics: Dict[str, float],
                                  ensemble_metrics: Dict[str, float], problem_type: str) -> Dict[str, Any]:
        """Analyze variance reduction in bagging"""
        analysis = {
            "variance_reduction_achieved": False,
            "performance_improvement": 0.0,
            "stability_improvement": "Cannot measure from single run"
        }
        
        # Get primary metric
        if problem_type == "classification":
            primary_metric = "accuracy"
        else:
            primary_metric = "r2_score"
        
        base_score = base_metrics.get(primary_metric, 0)
        ensemble_score = ensemble_metrics.get(primary_metric, 0)
        
        analysis["performance_improvement"] = ensemble_score - base_score
        analysis["variance_reduction_achieved"] = ensemble_score > base_score
        
        return analysis
    
    def _analyze_boosting_performance(self, ensemble, boosting_type: str) -> Dict[str, Any]:
        """Analyze boosting-specific performance"""
        analysis = {
            "boosting_type": boosting_type,
            "sequential_learning": True,
            "feature_importance_available": hasattr(ensemble, 'feature_importances_')
        }
        
        # Add more specific analysis based on boosting type
        if boosting_type == "adaboost":
            analysis["algorithm_focus"] = "Focuses on misclassified examples"
            analysis["weight_adaptation"] = "Adapts sample weights"
        elif boosting_type == "gradient_boosting":
            analysis["algorithm_focus"] = "Fits residuals of previous models"
            analysis["gradient_optimization"] = "Uses gradient descent optimization"
        
        return analysis
    
    def _compare_ensemble_methods(self, ensemble_results: Dict[str, Dict[str, float]],
                                problem_type: str) -> Dict[str, Any]:
        """Compare different ensemble methods"""
        try:
            comparison = {
                "method_rankings": [],
                "best_method": None,
                "performance_analysis": {}
            }
            
            # Get primary metric
            if problem_type == "classification":
                primary_metric = "accuracy"
            else:
                primary_metric = "r2_score"
            
            # Rank methods by primary metric
            method_scores = []
            for method, metrics in ensemble_results.items():
                if primary_metric in metrics:
                    method_scores.append({
                        "method": method,
                        "score": metrics[primary_metric],
                        "all_metrics": metrics
                    })
            
            # Sort by primary metric (higher is better)
            method_scores.sort(key=lambda x: x["score"], reverse=True)
            comparison["method_rankings"] = method_scores
            
            if method_scores:
                comparison["best_method"] = method_scores[0]["method"]
                
                # Analyze performance gaps
                best_score = method_scores[0]["score"]
                worst_score = method_scores[-1]["score"] if len(method_scores) > 1 else best_score
                
                comparison["performance_analysis"] = {
                    "best_score": best_score,
                    "worst_score": worst_score,
                    "performance_gap": best_score - worst_score,
                    "relative_improvement": (best_score - worst_score) / worst_score * 100 if worst_score > 0 else 0
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing ensemble methods: {e}")
            return {"error": str(e)}
    
    def _generate_ensemble_insights(self, comprehensive_results: Dict[str, Any], problem_type: str) -> List[str]:
        """Generate insights about ensemble performance"""
        insights = []
        
        try:
            # Best method insight
            comparison = comprehensive_results.get("ensemble_comparison", {})
            best_method = comparison.get("best_method")
            
            if best_method:
                insights.append(f"Best performing ensemble method: {best_method}")
            
            # Performance improvement insights
            performance_analysis = comparison.get("performance_analysis", {})
            if "relative_improvement" in performance_analysis:
                improvement = performance_analysis["relative_improvement"]
                if improvement > 5:
                    insights.append(f"Significant performance variation between methods ({improvement:.1f}% improvement)")
                elif improvement < 1:
                    insights.append("All ensemble methods show similar performance")
            
            # Method-specific insights
            if "stacking_ensemble" in comprehensive_results:
                stacking_result = comprehensive_results["stacking_ensemble"]
                improvement = stacking_result.get("improvement_analysis", {}).get("improvement_over_best", 0)
                if improvement > 0.02:  # More than 2% improvement
                    insights.append("Stacking shows strong meta-learning capability")
            
            if "voting_ensemble" in comprehensive_results:
                insights.append("Voting ensemble provides robust baseline performance")
            
            # Recommendations based on results
            if len(comprehensive_results) > 2:  # Multiple successful ensembles
                insights.append("Multiple ensemble methods successful - consider ensemble of ensembles")
            
        except Exception as e:
            logger.error(f"Error generating ensemble insights: {e}")
            insights.append("Error generating insights")
        
        return insights
    
    def _generate_ensemble_configs(self, ml_analysis: Dict[str, Any], problem_type: str) -> Dict[str, Any]:
        """Generate ensemble configuration recommendations"""
        configs = {
            "voting_config": {},
            "stacking_config": {},
            "bagging_config": {},
            "boosting_config": {}
        }
        
        data_shape = ml_analysis.get("ml_metadata", {}).get("data_shape", [0, 0])
        n_samples, n_features = data_shape
        
        # Voting configuration
        configs["voting_config"] = {
            "voting": "soft" if problem_type == "classification" else None,
            "weights": None,  # Equal weights by default
            "recommended_models": 3 if n_samples < 1000 else 5
        }
        
        # Stacking configuration
        configs["stacking_config"] = {
            "cv_folds": 5 if n_samples > 1000 else 3,
            "use_probabilities": True if problem_type == "classification" else False,
            "blending_ratio": 0.1 if n_features > 20 else 0.0,
            "meta_model": "logistic_regression" if problem_type == "classification" else "ridge"
        }
        
        # Bagging configuration
        configs["bagging_config"] = {
            "n_estimators": min(100, n_samples // 10),
            "max_samples": 0.8,
            "max_features": 0.8 if n_features > 10 else 1.0
        }
        
        # Boosting configuration
        configs["boosting_config"] = {
            "n_estimators": 50 if n_samples < 5000 else 100,
            "learning_rate": 1.0,  # AdaBoost default
            "preferred_type": "gradient_boosting" if n_samples > 1000 else "adaboost"
        }
        
        return configs
    
    def get_model_results(self, ensemble_key: Optional[str] = None) -> Dict[str, Any]:
        """Get results for specific ensemble or all ensembles"""
        if ensemble_key:
            return {
                "ensemble": self.ensemble_models.get(ensemble_key),
                "results": self.ensemble_results.get(ensemble_key)
            }
        else:
            return {
                "ensembles": list(self.ensemble_models.keys()),
                "library_availability": {
                    "sklearn": SKLEARN_AVAILABLE,
                    "xgboost": _check_xgboost_available(),
                    "lightgbm": _check_lightgbm_available()
                }
            }

# Convenience functions
def analyze_ensemble_performance(file_path: str, target_column: str, 
                               problem_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function for comprehensive ensemble analysis
    
    Args:
        file_path: Path to data file
        target_column: Target variable
        problem_type: 'classification' or 'regression'
        
    Returns:
        Complete ensemble analysis results
    """
    processor = EnsembleProcessor(file_path=file_path)
    return processor.comprehensive_ensemble_analysis(target_column, problem_type)

def quick_voting_ensemble(file_path: str, target_column: str,
                         models: List[str] = None) -> Dict[str, Any]:
    """
    Convenience function for quick voting ensemble
    
    Args:
        file_path: Path to data file
        target_column: Target variable
        models: List of model names to use
        
    Returns:
        Voting ensemble results
    """
    processor = EnsembleProcessor(file_path=file_path)
    return processor.create_voting_ensemble(target_column, models)

def advanced_stacking_ensemble(file_path: str, target_column: str,
                             base_models: List[str] = None,
                             meta_model: str = None) -> Dict[str, Any]:
    """
    Convenience function for advanced stacking ensemble
    
    Args:
        file_path: Path to data file
        target_column: Target variable
        base_models: List of base model names
        meta_model: Meta-model name
        
    Returns:
        Stacking ensemble results
    """
    processor = EnsembleProcessor(file_path=file_path)
    return processor.create_stacking_ensemble(target_column, base_models, meta_model)