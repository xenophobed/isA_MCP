#!/usr/bin/env python3
"""
Machine Learning Processor
Unified machine learning interface building on the existing processor infrastructure.
Provides sklearn, XGBoost, and other ML algorithms with consistent API and automated workflows.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import logging
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Core ML libraries
try:
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, RandomizedSearchCV
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge, Lasso
    from sklearn.svm import SVC, SVR
    from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
    from sklearn.naive_bayes import GaussianNB
    from sklearn.cluster import KMeans, DBSCAN
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. ML capabilities will be disabled.")

# Advanced ML libraries
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not available. XGBoost models will be disabled.")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logging.warning("LightGBM not available. LightGBM models will be disabled.")

try:
    from ..core.csv_processor import CSVProcessor
    from ..utilities.feature_processor import FeatureProcessor
    from ..analysis_engines.statistics_processor import StatisticsProcessor
except ImportError:
    from csv_processor import CSVProcessor
    from feature_processor import FeatureProcessor
    from statistics_processor import StatisticsProcessor

logger = logging.getLogger(__name__)

class MLProcessor:
    """
    Machine Learning processor
    Provides unified interface for various ML algorithms and automated workflows
    """
    
    def __init__(self, csv_processor: Optional[CSVProcessor] = None, file_path: Optional[str] = None):
        """
        Initialize ML processor
        
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
        self.feature_processor = None
        self.models = {}
        self.model_results = {}
        self.preprocessors = {}
        self._load_data()
    
    def _load_data(self) -> bool:
        """Load data from CSV processor"""
        try:
            if not self.csv_processor.load_csv():
                return False
            self.df = self.csv_processor.df.copy()
            self.feature_processor = FeatureProcessor(self.csv_processor)
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def get_ml_analysis(self, target_column: str, problem_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive ML analysis and recommendations
        
        Args:
            target_column: Target variable for ML
            problem_type: 'classification', 'regression', or 'clustering' (auto-detected if None)
            
        Returns:
            Complete ML analysis and recommendations
        """
        if self.df is None:
            return {"error": "No data loaded"}
        
        if target_column not in self.df.columns:
            return {"error": f"Target column '{target_column}' not found"}
        
        # Auto-detect problem type if not specified
        if problem_type is None:
            problem_type = self._detect_problem_type(self.df[target_column])
        
        analysis = {
            "problem_analysis": self.analyze_ml_problem(target_column, problem_type),
            "data_preparation": self.analyze_data_preparation_needs(target_column),
            "algorithm_recommendations": self.recommend_algorithms(target_column, problem_type),
            "preprocessing_recommendations": self.recommend_preprocessing(target_column),
            "evaluation_strategy": self.recommend_evaluation_strategy(problem_type),
            "ml_metadata": {
                "timestamp": datetime.now().isoformat(),
                "sklearn_available": SKLEARN_AVAILABLE,
                "xgboost_available": XGBOOST_AVAILABLE,
                "lightgbm_available": LIGHTGBM_AVAILABLE,
                "target_column": target_column,
                "problem_type": problem_type,
                "data_shape": list(self.df.shape)
            }
        }
        
        return analysis
    
    def analyze_ml_problem(self, target_column: str, problem_type: str) -> Dict[str, Any]:
        """Analyze the ML problem characteristics"""
        try:
            target_series = self.df[target_column].dropna()
            
            analysis = {
                "problem_type": problem_type,
                "target_column": target_column,
                "target_statistics": {}
            }
            
            if problem_type == "classification":
                unique_classes = target_series.nunique()
                class_distribution = target_series.value_counts()
                
                analysis["target_statistics"] = {
                    "num_classes": unique_classes,
                    "class_distribution": class_distribution.to_dict(),
                    "is_binary": unique_classes == 2,
                    "is_imbalanced": self._check_class_imbalance(class_distribution),
                    "dominant_class_percentage": round(class_distribution.iloc[0] / len(target_series) * 100, 2)
                }
                
                # Classification complexity assessment
                if unique_classes == 2:
                    analysis["complexity"] = "binary_classification"
                elif unique_classes <= 10:
                    analysis["complexity"] = "multiclass_classification"
                else:
                    analysis["complexity"] = "high_cardinality_classification"
                
            elif problem_type == "regression":
                analysis["target_statistics"] = {
                    "mean": float(target_series.mean()),
                    "std": float(target_series.std()),
                    "min": float(target_series.min()),
                    "max": float(target_series.max()),
                    "skewness": float(target_series.skew()),
                    "kurtosis": float(target_series.kurtosis()),
                    "range": float(target_series.max() - target_series.min())
                }
                
                # Regression complexity assessment
                if abs(target_series.skew()) > 2:
                    analysis["complexity"] = "skewed_regression"
                elif target_series.std() / target_series.mean() > 1 if target_series.mean() != 0 else False:
                    analysis["complexity"] = "high_variance_regression"
                else:
                    analysis["complexity"] = "standard_regression"
            
            # Feature analysis
            features_df = self.df.drop(columns=[target_column])
            numeric_features = features_df.select_dtypes(include=[np.number]).columns
            categorical_features = features_df.select_dtypes(include=['object', 'category']).columns
            
            analysis["feature_analysis"] = {
                "total_features": len(features_df.columns),
                "numeric_features": len(numeric_features),
                "categorical_features": len(categorical_features),
                "feature_to_sample_ratio": len(features_df.columns) / len(self.df) if len(self.df) > 0 else 0,
                "high_dimensionality": len(features_df.columns) > len(self.df) * 0.1
            }
            
            # Data quality for ML
            analysis["data_quality_for_ml"] = {
                "missing_values": features_df.isnull().sum().sum(),
                "missing_percentage": round(features_df.isnull().sum().sum() / features_df.size * 100, 2),
                "duplicated_rows": self.df.duplicated().sum(),
                "target_missing": target_series.isnull().sum()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing ML problem: {e}")
            return {"error": str(e)}
    
    def analyze_data_preparation_needs(self, target_column: str) -> Dict[str, Any]:
        """Analyze what data preparation is needed for ML"""
        try:
            features_df = self.df.drop(columns=[target_column])
            preparation_needs = {
                "missing_value_handling": [],
                "encoding_needs": [],
                "scaling_needs": [],
                "outlier_handling": [],
                "feature_selection_needs": []
            }
            
            # Missing value analysis
            missing_cols = features_df.columns[features_df.isnull().any()].tolist()
            for col in missing_cols:
                missing_pct = features_df[col].isnull().sum() / len(features_df) * 100
                
                if missing_pct > 50:
                    strategy = "Consider dropping column"
                elif missing_pct > 20:
                    strategy = "Advanced imputation (KNN, iterative)"
                elif pd.api.types.is_numeric_dtype(features_df[col]):
                    strategy = "Mean/median imputation"
                else:
                    strategy = "Mode imputation or create 'missing' category"
                
                preparation_needs["missing_value_handling"].append({
                    "column": col,
                    "missing_percentage": round(missing_pct, 2),
                    "recommended_strategy": strategy
                })
            
            # Encoding needs
            categorical_cols = features_df.select_dtypes(include=['object', 'category']).columns
            for col in categorical_cols:
                unique_count = features_df[col].nunique()
                
                if unique_count == 2:
                    encoding = "Label encoding"
                elif unique_count <= 10:
                    encoding = "One-hot encoding"
                elif unique_count <= 50:
                    encoding = "Target encoding"
                else:
                    encoding = "Frequency encoding or embeddings"
                
                preparation_needs["encoding_needs"].append({
                    "column": col,
                    "unique_values": unique_count,
                    "recommended_encoding": encoding
                })
            
            # Scaling needs
            numeric_cols = features_df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                # Check for different scales
                ranges = {}
                for col in numeric_cols:
                    col_data = features_df[col].dropna()
                    if len(col_data) > 0:
                        ranges[col] = col_data.max() - col_data.min()
                
                if len(ranges) > 1:
                    max_range = max(ranges.values())
                    min_range = min(ranges.values())
                    
                    if max_range / min_range > 100:  # Significant scale difference
                        preparation_needs["scaling_needs"].append({
                            "issue": "Features have very different scales",
                            "max_range": float(max_range),
                            "min_range": float(min_range),
                            "recommended_scaling": "StandardScaler or MinMaxScaler"
                        })
            
            # Outlier analysis
            for col in numeric_cols:
                col_data = features_df[col].dropna()
                if len(col_data) > 4:
                    Q1 = col_data.quantile(0.25)
                    Q3 = col_data.quantile(0.75)
                    IQR = Q3 - Q1
                    outliers = col_data[(col_data < Q1 - 1.5 * IQR) | (col_data > Q3 + 1.5 * IQR)]
                    
                    if len(outliers) > len(col_data) * 0.05:  # More than 5% outliers
                        preparation_needs["outlier_handling"].append({
                            "column": col,
                            "outlier_count": len(outliers),
                            "outlier_percentage": round(len(outliers) / len(col_data) * 100, 2),
                            "recommended_handling": "Winsorization, IQR capping, or robust scaling"
                        })
            
            # Feature selection needs
            if len(features_df.columns) > 20:
                preparation_needs["feature_selection_needs"].append({
                    "issue": "High number of features may lead to curse of dimensionality",
                    "feature_count": len(features_df.columns),
                    "sample_count": len(features_df),
                    "recommended_methods": ["Univariate selection", "RFE", "Tree-based importance", "L1 regularization"]
                })
            
            return preparation_needs
            
        except Exception as e:
            logger.error(f"Error analyzing data preparation needs: {e}")
            return {"error": str(e)}
    
    def recommend_algorithms(self, target_column: str, problem_type: str) -> Dict[str, Any]:
        """Recommend algorithms based on problem characteristics"""
        try:
            recommendations = {
                "recommended_algorithms": [],
                "algorithm_rationale": {},
                "ensemble_recommendations": [],
                "advanced_algorithms": []
            }
            
            # Get problem characteristics
            data_size = len(self.df)
            feature_count = len(self.df.columns) - 1
            target_series = self.df[target_column].dropna()
            
            if problem_type == "classification":
                unique_classes = target_series.nunique()
                
                # Basic algorithms
                basic_algorithms = [
                    {
                        "name": "Logistic Regression",
                        "sklearn_class": "LogisticRegression",
                        "pros": ["Fast", "Interpretable", "Good baseline", "Handles linear relationships"],
                        "cons": ["Assumes linear relationship", "Sensitive to outliers"],
                        "best_for": "Linear relationships, baseline model",
                        "priority": "high"
                    },
                    {
                        "name": "Random Forest",
                        "sklearn_class": "RandomForestClassifier",
                        "pros": ["Handles non-linear relationships", "Feature importance", "Robust to outliers"],
                        "cons": ["Can overfit", "Less interpretable"],
                        "best_for": "Non-linear relationships, mixed data types",
                        "priority": "high"
                    },
                    {
                        "name": "Decision Tree",
                        "sklearn_class": "DecisionTreeClassifier",
                        "pros": ["Highly interpretable", "Handles non-linear relationships"],
                        "cons": ["Prone to overfitting", "Unstable"],
                        "best_for": "Need interpretability, rule-based decisions",
                        "priority": "medium"
                    }
                ]
                
                # Add more algorithms based on characteristics
                if data_size < 1000:
                    basic_algorithms.append({
                        "name": "K-Nearest Neighbors",
                        "sklearn_class": "KNeighborsClassifier",
                        "pros": ["Simple", "No assumptions about data", "Good for small datasets"],
                        "cons": ["Computationally expensive", "Sensitive to irrelevant features"],
                        "best_for": "Small datasets, non-parametric problems",
                        "priority": "medium"
                    })
                
                if unique_classes == 2:
                    basic_algorithms.append({
                        "name": "Support Vector Machine",
                        "sklearn_class": "SVC",
                        "pros": ["Effective in high dimensions", "Memory efficient"],
                        "cons": ["Slow on large datasets", "Requires feature scaling"],
                        "best_for": "High-dimensional data, binary classification",
                        "priority": "medium" if data_size < 10000 else "low"
                    })
                
                if feature_count < 50:  # For datasets where Naive Bayes assumptions might hold
                    basic_algorithms.append({
                        "name": "Naive Bayes",
                        "sklearn_class": "GaussianNB",
                        "pros": ["Fast", "Good with small data", "Handles missing values"],
                        "cons": ["Strong independence assumption"],
                        "best_for": "Text classification, small datasets",
                        "priority": "medium"
                    })
                
                recommendations["recommended_algorithms"] = basic_algorithms
                
                # Ensemble methods
                ensemble_methods = [
                    {
                        "name": "Voting Classifier",
                        "description": "Combine predictions from multiple algorithms",
                        "use_case": "Improve performance by averaging predictions"
                    },
                    {
                        "name": "Bagging",
                        "description": "Bootstrap aggregating for variance reduction",
                        "use_case": "Reduce overfitting of high-variance models"
                    }
                ]
                
                recommendations["ensemble_recommendations"] = ensemble_methods
                
                # Advanced algorithms
                advanced_algorithms = []
                
                if XGBOOST_AVAILABLE:
                    advanced_algorithms.append({
                        "name": "XGBoost",
                        "library": "xgboost",
                        "pros": ["High performance", "Feature importance", "Handles missing values"],
                        "cons": ["Hyperparameter tuning needed", "Can overfit"],
                        "best_for": "Tabular data competitions, high performance needed"
                    })
                
                if LIGHTGBM_AVAILABLE:
                    advanced_algorithms.append({
                        "name": "LightGBM",
                        "library": "lightgbm",
                        "pros": ["Fast training", "Lower memory usage", "Good accuracy"],
                        "cons": ["Can overfit on small datasets"],
                        "best_for": "Large datasets, speed important"
                    })
                
                recommendations["advanced_algorithms"] = advanced_algorithms
                
            elif problem_type == "regression":
                # Regression algorithms
                basic_algorithms = [
                    {
                        "name": "Linear Regression",
                        "sklearn_class": "LinearRegression",
                        "pros": ["Simple", "Interpretable", "Fast", "Good baseline"],
                        "cons": ["Assumes linear relationship", "Sensitive to outliers"],
                        "best_for": "Linear relationships, baseline model",
                        "priority": "high"
                    },
                    {
                        "name": "Ridge Regression",
                        "sklearn_class": "Ridge",
                        "pros": ["Handles multicollinearity", "Prevents overfitting"],
                        "cons": ["Still assumes linearity"],
                        "best_for": "Many correlated features, regularization needed",
                        "priority": "high"
                    },
                    {
                        "name": "Random Forest Regressor",
                        "sklearn_class": "RandomForestRegressor",
                        "pros": ["Handles non-linearity", "Feature importance", "Robust"],
                        "cons": ["Less interpretable", "Can overfit"],
                        "best_for": "Non-linear relationships, robust predictions",
                        "priority": "high"
                    }
                ]
                
                if feature_count > 50 or data_size > 1000:
                    basic_algorithms.append({
                        "name": "Lasso Regression",
                        "sklearn_class": "Lasso",
                        "pros": ["Feature selection", "Prevents overfitting"],
                        "cons": ["Can eliminate useful features"],
                        "best_for": "Feature selection, sparse solutions",
                        "priority": "medium"
                    })
                
                if data_size < 5000:
                    basic_algorithms.append({
                        "name": "Support Vector Regression",
                        "sklearn_class": "SVR",
                        "pros": ["Effective in high dimensions", "Robust to outliers"],
                        "cons": ["Slow on large datasets", "Hyperparameter sensitive"],
                        "best_for": "High-dimensional data, non-linear relationships",
                        "priority": "medium"
                    })
                
                recommendations["recommended_algorithms"] = basic_algorithms
                
                # Advanced regression algorithms
                advanced_algorithms = []
                
                if XGBOOST_AVAILABLE:
                    advanced_algorithms.append({
                        "name": "XGBoost Regressor",
                        "library": "xgboost",
                        "pros": ["High performance", "Handles missing values", "Feature importance"],
                        "cons": ["Hyperparameter tuning needed"],
                        "best_for": "Tabular regression, competition-level performance"
                    })
                
                recommendations["advanced_algorithms"] = advanced_algorithms
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending algorithms: {e}")
            return {"error": str(e)}
    
    def recommend_preprocessing(self, target_column: str) -> Dict[str, Any]:
        """Recommend preprocessing pipeline"""
        try:
            preprocessing_pipeline = {
                "steps": [],
                "order": "Recommended execution order",
                "alternatives": {}
            }
            
            features_df = self.df.drop(columns=[target_column])
            
            # Step 1: Handle missing values
            if features_df.isnull().any().any():
                preprocessing_pipeline["steps"].append({
                    "step": 1,
                    "name": "Handle Missing Values",
                    "sklearn_transformers": ["SimpleImputer", "IterativeImputer", "KNNImputer"],
                    "custom_options": ["Drop rows/columns", "Domain-specific imputation"],
                    "priority": "high"
                })
            
            # Step 2: Encode categorical variables
            categorical_cols = features_df.select_dtypes(include=['object', 'category']).columns
            if len(categorical_cols) > 0:
                preprocessing_pipeline["steps"].append({
                    "step": 2,
                    "name": "Encode Categorical Variables",
                    "sklearn_transformers": ["OneHotEncoder", "LabelEncoder", "OrdinalEncoder"],
                    "custom_options": ["Target encoding", "Frequency encoding"],
                    "priority": "high"
                })
            
            # Step 3: Feature scaling
            numeric_cols = features_df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 1:
                preprocessing_pipeline["steps"].append({
                    "step": 3,
                    "name": "Scale Numeric Features",
                    "sklearn_transformers": ["StandardScaler", "MinMaxScaler", "RobustScaler"],
                    "when_needed": "For algorithms sensitive to scale (SVM, KNN, Neural Networks)",
                    "priority": "medium"
                })
            
            # Step 4: Feature selection (optional)
            if len(features_df.columns) > 20:
                preprocessing_pipeline["steps"].append({
                    "step": 4,
                    "name": "Feature Selection (Optional)",
                    "sklearn_transformers": ["SelectKBest", "RFE", "SelectFromModel"],
                    "when_needed": "High-dimensional data, curse of dimensionality",
                    "priority": "low"
                })
            
            # Step 5: Handle outliers (optional)
            preprocessing_pipeline["steps"].append({
                "step": 5,
                "name": "Handle Outliers (Optional)",
                "sklearn_transformers": ["None built-in"],
                "custom_options": ["Winsorization", "IQR capping", "Isolation Forest"],
                "priority": "low"
            })
            
            # Alternative pipelines
            preprocessing_pipeline["alternatives"] = {
                "minimal_pipeline": ["Handle missing values", "Encode categoricals"],
                "standard_pipeline": ["Handle missing values", "Encode categoricals", "Scale features"],
                "comprehensive_pipeline": ["Handle missing values", "Encode categoricals", "Scale features", "Feature selection", "Handle outliers"]
            }
            
            # Sklearn Pipeline example
            preprocessing_pipeline["sklearn_pipeline_example"] = {
                "code": """
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

# Define transformers
numeric_features = [...] # list of numeric columns
categorical_features = [...] # list of categorical columns

numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

# Combine transformers
preprocessor = ColumnTransformer([
    ('num', numeric_transformer, numeric_features),
    ('cat', categorical_transformer, categorical_features)
])
""",
                "description": "Complete preprocessing pipeline using sklearn"
            }
            
            return preprocessing_pipeline
            
        except Exception as e:
            logger.error(f"Error recommending preprocessing: {e}")
            return {"error": str(e)}
    
    def recommend_evaluation_strategy(self, problem_type: str) -> Dict[str, Any]:
        """Recommend evaluation strategy and metrics"""
        try:
            evaluation_strategy = {
                "cross_validation": {},
                "metrics": {},
                "validation_approach": {},
                "interpretation_methods": {}
            }
            
            data_size = len(self.df)
            
            # Cross-validation recommendations
            if data_size < 1000:
                cv_method = "Leave-One-Out or 5-fold CV"
                cv_folds = 5
            elif data_size < 10000:
                cv_method = "5-fold or 10-fold CV"
                cv_folds = 10
            else:
                cv_method = "5-fold CV (for speed) or Hold-out validation"
                cv_folds = 5
            
            evaluation_strategy["cross_validation"] = {
                "recommended_method": cv_method,
                "recommended_folds": cv_folds,
                "sklearn_implementation": f"cross_val_score(model, X, y, cv={cv_folds})",
                "alternatives": ["StratifiedKFold", "TimeSeriesSplit", "Hold-out validation"]
            }
            
            # Metrics based on problem type
            if problem_type == "classification":
                target_series = self.df.iloc[:, -1]  # Assuming last column is target
                unique_classes = target_series.nunique() if hasattr(target_series, 'nunique') else len(set(target_series))
                
                if unique_classes == 2:
                    # Binary classification
                    evaluation_strategy["metrics"] = {
                        "primary_metrics": [
                            {"metric": "ROC-AUC", "use_case": "Overall performance", "sklearn_function": "roc_auc_score"},
                            {"metric": "F1-Score", "use_case": "Balance precision/recall", "sklearn_function": "f1_score"},
                            {"metric": "Precision", "use_case": "Minimize false positives", "sklearn_function": "precision_score"},
                            {"metric": "Recall", "use_case": "Minimize false negatives", "sklearn_function": "recall_score"}
                        ],
                        "secondary_metrics": [
                            {"metric": "Accuracy", "use_case": "Overall correctness", "sklearn_function": "accuracy_score"},
                            {"metric": "Precision-Recall AUC", "use_case": "Imbalanced datasets", "sklearn_function": "average_precision_score"}
                        ]
                    }
                else:
                    # Multi-class classification
                    evaluation_strategy["metrics"] = {
                        "primary_metrics": [
                            {"metric": "Accuracy", "use_case": "Overall correctness", "sklearn_function": "accuracy_score"},
                            {"metric": "Macro F1-Score", "use_case": "Average performance across classes", "sklearn_function": "f1_score(average='macro')"},
                            {"metric": "Weighted F1-Score", "use_case": "Class-imbalanced datasets", "sklearn_function": "f1_score(average='weighted')"}
                        ],
                        "secondary_metrics": [
                            {"metric": "Classification Report", "use_case": "Per-class performance", "sklearn_function": "classification_report"},
                            {"metric": "Confusion Matrix", "use_case": "Error analysis", "sklearn_function": "confusion_matrix"}
                        ]
                    }
                
            elif problem_type == "regression":
                evaluation_strategy["metrics"] = {
                    "primary_metrics": [
                        {"metric": "R² Score", "use_case": "Proportion of variance explained", "sklearn_function": "r2_score"},
                        {"metric": "Mean Absolute Error (MAE)", "use_case": "Average absolute error", "sklearn_function": "mean_absolute_error"},
                        {"metric": "Root Mean Squared Error (RMSE)", "use_case": "Penalize large errors", "sklearn_function": "sqrt(mean_squared_error)"}
                    ],
                    "secondary_metrics": [
                        {"metric": "Mean Squared Error (MSE)", "use_case": "Squared error penalty", "sklearn_function": "mean_squared_error"},
                        {"metric": "Mean Absolute Percentage Error (MAPE)", "use_case": "Percentage-based error", "sklearn_function": "mean_absolute_percentage_error"}
                    ]
                }
            
            # Validation approach
            if data_size > 10000:
                evaluation_strategy["validation_approach"] = {
                    "recommended": "Hold-out validation (70-20-10 or 80-20 split)",
                    "train_size": 0.7,
                    "validation_size": 0.2,
                    "test_size": 0.1,
                    "advantages": ["Faster than CV", "Mimics production scenario"],
                    "sklearn_implementation": "train_test_split(X, y, test_size=0.3, random_state=42)"
                }
            else:
                evaluation_strategy["validation_approach"] = {
                    "recommended": "Cross-validation",
                    "advantages": ["Better use of limited data", "More robust estimates"],
                    "sklearn_implementation": f"cross_val_score(model, X, y, cv={cv_folds}, scoring='accuracy')"
                }
            
            # Model interpretation methods
            interpretation_methods = [
                {"method": "Feature Importance", "applicable_to": "Tree-based models", "sklearn_access": "model.feature_importances_"},
                {"method": "Coefficients", "applicable_to": "Linear models", "sklearn_access": "model.coef_"},
                {"method": "Permutation Importance", "applicable_to": "Any model", "sklearn_function": "permutation_importance"},
                {"method": "Partial Dependence Plots", "applicable_to": "Any model", "sklearn_function": "plot_partial_dependence"}
            ]
            
            evaluation_strategy["interpretation_methods"] = interpretation_methods
            
            return evaluation_strategy
            
        except Exception as e:
            logger.error(f"Error recommending evaluation strategy: {e}")
            return {"error": str(e)}
    
    def train_model(self, target_column: str, algorithm: str, test_size: float = 0.2, **kwargs) -> Dict[str, Any]:
        """Train a specific model"""
        try:
            if not SKLEARN_AVAILABLE:
                return {"error": "scikit-learn not available"}
            
            if target_column not in self.df.columns:
                return {"error": f"Target column '{target_column}' not found"}
            
            # Prepare data
            X = self.df.drop(columns=[target_column])
            y = self.df[target_column]
            
            # Basic preprocessing
            X_processed = self._basic_preprocessing(X)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_processed, y, test_size=test_size, random_state=42
            )
            
            # Select and train model
            model = self._get_model(algorithm, **kwargs)
            if model is None:
                return {"error": f"Unknown algorithm: {algorithm}"}
            
            # Train model
            start_time = datetime.now()
            model.fit(X_train, y_train)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Make predictions
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            problem_type = self._detect_problem_type(y)
            metrics = self._calculate_metrics(y_test, y_pred, problem_type)
            
            # Store model and results
            model_id = f"{algorithm}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.models[model_id] = model
            
            results = {
                "model_id": model_id,
                "algorithm": algorithm,
                "problem_type": problem_type,
                "training_time_seconds": round(training_time, 3),
                "data_split": {
                    "train_size": len(X_train),
                    "test_size": len(X_test),
                    "test_ratio": test_size
                },
                "metrics": metrics,
                "feature_count": X_processed.shape[1],
                "hyperparameters": model.get_params()
            }
            
            # Add feature importance if available
            if hasattr(model, 'feature_importances_'):
                feature_names = X_processed.columns if hasattr(X_processed, 'columns') else [f"feature_{i}" for i in range(X_processed.shape[1])]
                importance_dict = dict(zip(feature_names, model.feature_importances_))
                sorted_importance = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
                results["feature_importance"] = sorted_importance[:10]  # Top 10 features
            
            # Add coefficients for linear models
            if hasattr(model, 'coef_'):
                feature_names = X_processed.columns if hasattr(X_processed, 'columns') else [f"feature_{i}" for i in range(X_processed.shape[1])]
                if len(model.coef_.shape) == 1:  # Binary classification or regression
                    coef_dict = dict(zip(feature_names, model.coef_))
                    sorted_coef = sorted(coef_dict.items(), key=lambda x: abs(x[1]), reverse=True)
                    results["coefficients"] = sorted_coef[:10]
            
            self.model_results[model_id] = results
            
            return results
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return {"error": str(e)}
    
    def compare_models(self, target_column: str, algorithms: List[str], cv_folds: int = 5) -> Dict[str, Any]:
        """Compare multiple models using cross-validation"""
        try:
            if not SKLEARN_AVAILABLE:
                return {"error": "scikit-learn not available"}
            
            # Prepare data
            X = self.df.drop(columns=[target_column])
            y = self.df[target_column]
            X_processed = self._basic_preprocessing(X)
            
            problem_type = self._detect_problem_type(y)
            
            # Determine scoring metric
            if problem_type == "classification":
                scoring = 'accuracy' if y.nunique() > 2 else 'roc_auc'
            else:
                scoring = 'r2'
            
            comparison_results = {
                "problem_type": problem_type,
                "scoring_metric": scoring,
                "cv_folds": cv_folds,
                "model_comparison": [],
                "best_model": None,
                "data_shape": X_processed.shape
            }
            
            model_scores = {}
            
            for algorithm in algorithms:
                try:
                    model = self._get_model(algorithm)
                    if model is None:
                        logger.warning(f"Skipping unknown algorithm: {algorithm}")
                        continue
                    
                    # Cross-validation
                    scores = cross_val_score(model, X_processed, y, cv=cv_folds, scoring=scoring)
                    
                    model_result = {
                        "algorithm": algorithm,
                        "mean_score": float(scores.mean()),
                        "std_score": float(scores.std()),
                        "individual_scores": scores.tolist(),
                        "score_range": [float(scores.min()), float(scores.max())]
                    }
                    
                    comparison_results["model_comparison"].append(model_result)
                    model_scores[algorithm] = scores.mean()
                    
                except Exception as e:
                    logger.warning(f"Error training {algorithm}: {e}")
            
            # Identify best model
            if model_scores:
                best_algorithm = max(model_scores.items(), key=lambda x: x[1])
                comparison_results["best_model"] = {
                    "algorithm": best_algorithm[0],
                    "score": float(best_algorithm[1])
                }
                
                # Sort results by performance
                comparison_results["model_comparison"].sort(key=lambda x: x["mean_score"], reverse=True)
            
            return comparison_results
            
        except Exception as e:
            logger.error(f"Error comparing models: {e}")
            return {"error": str(e)}
    
    def hyperparameter_tuning(self, target_column: str, algorithm: str, param_grid: Dict[str, Any] = None, 
                             search_type: str = "grid", cv_folds: int = 5) -> Dict[str, Any]:
        """Perform hyperparameter tuning"""
        try:
            if not SKLEARN_AVAILABLE:
                return {"error": "scikit-learn not available"}
            
            # Prepare data
            X = self.df.drop(columns=[target_column])
            y = self.df[target_column]
            X_processed = self._basic_preprocessing(X)
            
            # Get model
            model = self._get_model(algorithm)
            if model is None:
                return {"error": f"Unknown algorithm: {algorithm}"}
            
            # Default parameter grids
            if param_grid is None:
                param_grid = self._get_default_param_grid(algorithm)
            
            # Choose search strategy
            if search_type == "grid":
                search = GridSearchCV(model, param_grid, cv=cv_folds, scoring='accuracy', n_jobs=-1)
            else:  # randomized
                search = RandomizedSearchCV(model, param_grid, cv=cv_folds, scoring='accuracy', n_jobs=-1, n_iter=50)
            
            # Perform search
            start_time = datetime.now()
            search.fit(X_processed, y)
            search_time = (datetime.now() - start_time).total_seconds()
            
            results = {
                "algorithm": algorithm,
                "search_type": search_type,
                "search_time_seconds": round(search_time, 3),
                "best_score": float(search.best_score_),
                "best_parameters": search.best_params_,
                "cv_folds": cv_folds,
                "total_fits": len(search.cv_results_['mean_test_score'])
            }
            
            # Store best model
            model_id = f"{algorithm}_tuned_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.models[model_id] = search.best_estimator_
            results["model_id"] = model_id
            
            # Top parameter combinations
            results_df = pd.DataFrame(search.cv_results_)
            top_results = results_df.nlargest(5, 'mean_test_score')[['params', 'mean_test_score', 'std_test_score']]
            results["top_parameter_combinations"] = top_results.to_dict('records')
            
            return results
            
        except Exception as e:
            logger.error(f"Error in hyperparameter tuning: {e}")
            return {"error": str(e)}
    
    # Helper methods
    
    def _detect_problem_type(self, target_series: pd.Series) -> str:
        """Detect if problem is classification or regression"""
        if pd.api.types.is_numeric_dtype(target_series):
            unique_count = target_series.nunique()
            total_count = len(target_series)
            
            # If unique values are less than 10% of total and less than 20 unique values, treat as classification
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
        
        # Check if minority class is less than 30% of majority class
        majority_count = class_distribution.iloc[0]
        minority_count = class_distribution.iloc[-1]
        
        return minority_count < majority_count * 0.3
    
    def _basic_preprocessing(self, X: pd.DataFrame) -> pd.DataFrame:
        """Apply basic preprocessing to features"""
        X_processed = X.copy()
        
        # Handle missing values
        numeric_cols = X_processed.select_dtypes(include=[np.number]).columns
        categorical_cols = X_processed.select_dtypes(include=['object', 'category']).columns
        
        # Fill missing values
        for col in numeric_cols:
            X_processed[col] = X_processed[col].fillna(X_processed[col].median())
        
        for col in categorical_cols:
            X_processed[col] = X_processed[col].fillna('missing')
        
        # Encode categorical variables
        for col in categorical_cols:
            if X_processed[col].nunique() <= 10:  # One-hot encode low cardinality
                dummies = pd.get_dummies(X_processed[col], prefix=col)
                X_processed = pd.concat([X_processed, dummies], axis=1)
                X_processed = X_processed.drop(columns=[col])
            else:  # Frequency encode high cardinality
                freq_map = X_processed[col].value_counts().to_dict()
                X_processed[col] = X_processed[col].map(freq_map)
        
        return X_processed
    
    def _get_model(self, algorithm: str, **kwargs):
        """Get model instance for given algorithm"""
        model_map = {
            "logistic_regression": LogisticRegression(random_state=42, **kwargs),
            "linear_regression": LinearRegression(**kwargs),
            "ridge": Ridge(random_state=42, **kwargs),
            "lasso": Lasso(random_state=42, **kwargs),
            "random_forest_classifier": RandomForestClassifier(random_state=42, **kwargs),
            "random_forest_regressor": RandomForestRegressor(random_state=42, **kwargs),
            "decision_tree_classifier": DecisionTreeClassifier(random_state=42, **kwargs),
            "decision_tree_regressor": DecisionTreeRegressor(random_state=42, **kwargs),
            "svm_classifier": SVC(random_state=42, **kwargs),
            "svm_regressor": SVR(**kwargs),
            "knn_classifier": KNeighborsClassifier(**kwargs),
            "knn_regressor": KNeighborsRegressor(**kwargs),
            "naive_bayes": GaussianNB(**kwargs)
        }
        
        # Add XGBoost models if available
        if XGBOOST_AVAILABLE:
            model_map.update({
                "xgboost_classifier": xgb.XGBClassifier(random_state=42, **kwargs),
                "xgboost_regressor": xgb.XGBRegressor(random_state=42, **kwargs)
            })
        
        return model_map.get(algorithm.lower())
    
    def _calculate_metrics(self, y_true, y_pred, problem_type: str) -> Dict[str, float]:
        """Calculate appropriate metrics based on problem type"""
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
                    pass  # Skip if not applicable
        
        else:  # regression
            metrics["r2_score"] = float(r2_score(y_true, y_pred))
            metrics["mean_squared_error"] = float(mean_squared_error(y_true, y_pred))
            metrics["mean_absolute_error"] = float(mean_absolute_error(y_true, y_pred))
            metrics["root_mean_squared_error"] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        
        return metrics
    
    def _get_default_param_grid(self, algorithm: str) -> Dict[str, Any]:
        """Get default parameter grid for hyperparameter tuning"""
        param_grids = {
            "random_forest_classifier": {
                "n_estimators": [50, 100, 200],
                "max_depth": [None, 10, 20, 30],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4]
            },
            "random_forest_regressor": {
                "n_estimators": [50, 100, 200],
                "max_depth": [None, 10, 20, 30],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4]
            },
            "logistic_regression": {
                "C": [0.1, 1, 10, 100],
                "solver": ["lbfgs", "liblinear"]
            },
            "svm_classifier": {
                "C": [0.1, 1, 10, 100],
                "kernel": ["linear", "rbf"],
                "gamma": ["scale", "auto"]
            },
            "knn_classifier": {
                "n_neighbors": [3, 5, 7, 9, 11],
                "weights": ["uniform", "distance"]
            }
        }
        
        return param_grids.get(algorithm, {})
    
    def get_model_results(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get results for a specific model or all models"""
        if model_id:
            return self.model_results.get(model_id, {"error": "Model not found"})
        else:
            return self.model_results
    
    def save_model(self, model_id: str, filepath: str) -> bool:
        """Save a trained model"""
        try:
            import joblib
            if model_id not in self.models:
                logger.error(f"Model {model_id} not found")
                return False
            
            joblib.dump(self.models[model_id], filepath)
            logger.info(f"Model saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def save_analysis(self, output_path: str, analysis: Optional[Dict[str, Any]] = None) -> bool:
        """Save ML analysis to JSON file"""
        try:
            if analysis is None:
                # Need target column for analysis - this should be called after get_ml_analysis
                logger.error("Analysis data required for saving")
                return False
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"ML analysis saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save ML analysis: {e}")
            return False

# Convenience functions
def analyze_ml_problem(file_path: str, target_column: str, problem_type: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to analyze ML problem"""
    processor = MLProcessor(file_path=file_path)
    return processor.get_ml_analysis(target_column, problem_type)

def quick_model_comparison(file_path: str, target_column: str, algorithms: List[str] = None) -> Dict[str, Any]:
    """Convenience function to compare models quickly"""
    if algorithms is None:
        algorithms = ["logistic_regression", "random_forest_classifier", "decision_tree_classifier"]
    
    processor = MLProcessor(file_path=file_path)
    return processor.compare_models(target_column, algorithms)