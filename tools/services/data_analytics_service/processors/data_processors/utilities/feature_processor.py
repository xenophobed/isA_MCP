#!/usr/bin/env python3
"""
Feature Engineering Processor
Advanced feature engineering tool building on the existing CSV processor infrastructure.
Provides feature selection, creation, encoding, and transformation capabilities.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime
import logging
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Feature engineering libraries
try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder, OneHotEncoder
    from sklearn.feature_selection import SelectKBest, chi2, f_classif, mutual_info_classif, RFE
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. Feature engineering capabilities will be limited.")

try:
    from ..preprocessors.csv_processor import CSVProcessor
    from ..analytics.statistics_processor import StatisticsProcessor
except ImportError:
    # Fallback - create minimal classes if needed
    class CSVProcessor:
        def __init__(self, file_path):
            self.file_path = file_path
            self.df = None
        def load_csv(self):
            return False
    class StatisticsProcessor:
        def __init__(self, file_path):
            self.file_path = file_path

logger = logging.getLogger(__name__)

class FeatureProcessor:
    """
    Feature engineering processor
    Builds on CSVProcessor for comprehensive feature engineering operations
    """
    
    def __init__(self, csv_processor: Optional[CSVProcessor] = None, file_path: Optional[str] = None):
        """
        Initialize feature processor
        
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
        self.original_df = None
        self.feature_transformations = []
        self.encoders = {}
        self.scalers = {}
        self._load_data()
    
    def _load_data(self) -> bool:
        """Load data from CSV processor"""
        try:
            if not self.csv_processor.load_csv():
                return False
            self.df = self.csv_processor.df.copy()
            self.original_df = self.csv_processor.df.copy()
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def get_full_feature_engineering_analysis(self, target_column: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive feature engineering analysis and recommendations
        
        Args:
            target_column: Target variable for supervised feature selection
            
        Returns:
            Complete feature engineering analysis results
        """
        if self.df is None:
            return {"error": "No data loaded"}
        
        analysis = {
            "feature_analysis": self.analyze_features(),
            "encoding_recommendations": self.recommend_encodings(),
            "scaling_recommendations": self.recommend_scaling(),
            "feature_creation_opportunities": self.identify_feature_creation_opportunities(),
            "transformation_recommendations": self.recommend_transformations(),
            "dimensionality_analysis": self.analyze_dimensionality(),
            "feature_engineering_metadata": {
                "timestamp": datetime.now().isoformat(),
                "sklearn_available": SKLEARN_AVAILABLE,
                "original_shape": list(self.original_df.shape),
                "current_shape": list(self.df.shape),
                "transformations_applied": len(self.feature_transformations)
            }
        }
        
        if target_column and target_column in self.df.columns:
            analysis["supervised_feature_analysis"] = self.analyze_features_for_target(target_column)
        
        return analysis
    
    def analyze_features(self) -> Dict[str, Any]:
        """Analyze current features and their characteristics"""
        try:
            features = {}
            
            # Basic feature statistics
            numeric_features = self.df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_features = self.df.select_dtypes(include=['object', 'category']).columns.tolist()
            datetime_features = []
            
            # Try to identify datetime columns
            for col in self.df.columns:
                try:
                    pd.to_datetime(self.df[col], errors='raise')
                    datetime_features.append(col)
                except:
                    pass
            
            features["feature_types"] = {
                "numeric_features": numeric_features,
                "categorical_features": categorical_features,
                "datetime_features": datetime_features,
                "total_features": len(self.df.columns)
            }
            
            # Feature quality analysis
            feature_quality = []
            for col in self.df.columns:
                quality_metrics = self._assess_feature_quality(self.df[col])
                quality_metrics["feature_name"] = col
                feature_quality.append(quality_metrics)
            
            features["feature_quality"] = feature_quality
            
            # Feature relationships (correlation for numeric features)
            if len(numeric_features) > 1:
                correlation_matrix = self.df[numeric_features].corr()
                
                # Find highly correlated feature pairs
                high_correlations = []
                for i, col1 in enumerate(correlation_matrix.columns):
                    for j, col2 in enumerate(correlation_matrix.columns):
                        if i < j:
                            corr_value = correlation_matrix.loc[col1, col2]
                            if abs(corr_value) > 0.8:  # High correlation threshold
                                high_correlations.append({
                                    "feature1": col1,
                                    "feature2": col2,
                                    "correlation": round(float(corr_value), 3),
                                    "strength": "very_high" if abs(corr_value) > 0.9 else "high"
                                })
                
                features["high_correlations"] = high_correlations
            
            return features
            
        except Exception as e:
            logger.error(f"Error analyzing features: {e}")
            return {"error": str(e)}
    
    def recommend_encodings(self) -> Dict[str, Any]:
        """Recommend encoding strategies for categorical variables"""
        try:
            recommendations = {
                "categorical_encoding": [],
                "datetime_encoding": [],
                "text_encoding": []
            }
            
            categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns
            
            for col in categorical_cols:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                unique_count = series.nunique()
                total_count = len(series)
                
                encoding_recommendation = {
                    "column_name": col,
                    "unique_values": unique_count,
                    "total_values": total_count,
                    "cardinality": "high" if unique_count > total_count * 0.1 else "low",
                    "recommended_encodings": []
                }
                
                # Determine best encoding strategies
                if unique_count == 2:
                    encoding_recommendation["recommended_encodings"].append({
                        "method": "Label Encoding",
                        "reason": "Binary categorical variable",
                        "priority": "high"
                    })
                elif unique_count <= 10:
                    encoding_recommendation["recommended_encodings"].append({
                        "method": "One-Hot Encoding",
                        "reason": "Low cardinality categorical variable",
                        "priority": "high"
                    })
                    encoding_recommendation["recommended_encodings"].append({
                        "method": "Label Encoding",
                        "reason": "Alternative for ordinal relationships",
                        "priority": "medium"
                    })
                elif unique_count <= 50:
                    encoding_recommendation["recommended_encodings"].append({
                        "method": "Target Encoding",
                        "reason": "Medium cardinality - target encoding can be effective",
                        "priority": "high"
                    })
                    encoding_recommendation["recommended_encodings"].append({
                        "method": "Frequency Encoding",
                        "reason": "Use frequency of categories as features",
                        "priority": "medium"
                    })
                else:
                    encoding_recommendation["recommended_encodings"].append({
                        "method": "Frequency Encoding",
                        "reason": "High cardinality - frequency encoding reduces dimensionality",
                        "priority": "high"
                    })
                    encoding_recommendation["recommended_encodings"].append({
                        "method": "Target Encoding",
                        "reason": "High cardinality - target encoding can capture patterns",
                        "priority": "medium"
                    })
                
                # Check for potential ordinal relationships
                if self._detect_ordinal_pattern(series):
                    encoding_recommendation["recommended_encodings"].insert(0, {
                        "method": "Ordinal Encoding",
                        "reason": "Detected potential ordinal relationship",
                        "priority": "high"
                    })
                
                recommendations["categorical_encoding"].append(encoding_recommendation)
            
            # Datetime encoding recommendations
            datetime_cols = [col for col in self.df.columns if any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated'])]
            
            for col in datetime_cols:
                try:
                    datetime_series = pd.to_datetime(self.df[col], errors='coerce')
                    if datetime_series.notna().sum() > 0:
                        datetime_recommendation = {
                            "column_name": col,
                            "recommended_features": [
                                {"feature": "year", "reason": "Capture yearly trends"},
                                {"feature": "month", "reason": "Capture seasonal patterns"},
                                {"feature": "day_of_week", "reason": "Capture weekly patterns"},
                                {"feature": "hour", "reason": "Capture hourly patterns (if time available)"},
                                {"feature": "is_weekend", "reason": "Boolean feature for weekend/weekday"},
                                {"feature": "days_since_epoch", "reason": "Numeric representation of date"}
                            ]
                        }
                        
                        # Add quarter if year span is significant
                        date_range = datetime_series.max() - datetime_series.min()
                        if date_range.days > 365:
                            datetime_recommendation["recommended_features"].append({
                                "feature": "quarter", 
                                "reason": "Capture quarterly patterns (multi-year data)"
                            })
                        
                        recommendations["datetime_encoding"].append(datetime_recommendation)
                        
                except Exception as e:
                    logger.warning(f"Could not analyze datetime column {col}: {e}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending encodings: {e}")
            return {"error": str(e)}
    
    def recommend_scaling(self) -> Dict[str, Any]:
        """Recommend scaling strategies for numeric variables"""
        try:
            recommendations = {"scaling_recommendations": []}
            
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) == 0:
                return {"message": "No numeric columns found"}
            
            # Analyze each numeric column
            for col in numeric_cols:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                # Calculate statistics
                mean_val = series.mean()
                std_val = series.std()
                min_val = series.min()
                max_val = series.max()
                skewness = series.skew()
                
                scaling_recommendation = {
                    "column_name": col,
                    "statistics": {
                        "mean": round(float(mean_val), 3),
                        "std": round(float(std_val), 3),
                        "min": round(float(min_val), 3),
                        "max": round(float(max_val), 3),
                        "range": round(float(max_val - min_val), 3),
                        "skewness": round(float(skewness), 3)
                    },
                    "recommended_scalers": []
                }
                
                # Determine best scaling methods
                
                # StandardScaler (z-score normalization)
                scaling_recommendation["recommended_scalers"].append({
                    "method": "StandardScaler",
                    "reason": "Good for normally distributed data",
                    "priority": "high" if abs(skewness) < 1 else "medium",
                    "use_case": "Most machine learning algorithms"
                })
                
                # MinMaxScaler
                if min_val >= 0:  # Non-negative values
                    scaling_recommendation["recommended_scalers"].append({
                        "method": "MinMaxScaler",
                        "reason": "Preserves original distribution shape, good for bounded data",
                        "priority": "high",
                        "use_case": "Neural networks, algorithms sensitive to feature scale"
                    })
                else:
                    scaling_recommendation["recommended_scalers"].append({
                        "method": "MinMaxScaler",
                        "reason": "Preserves original distribution shape",
                        "priority": "medium",
                        "use_case": "When you need features in [0,1] range"
                    })
                
                # RobustScaler for data with outliers
                outlier_threshold = 1.5
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                outliers = series[(series < Q1 - outlier_threshold * IQR) | (series > Q3 + outlier_threshold * IQR)]
                
                if len(outliers) > len(series) * 0.05:  # More than 5% outliers
                    scaling_recommendation["recommended_scalers"].append({
                        "method": "RobustScaler",
                        "reason": f"Data contains {len(outliers)} outliers ({len(outliers)/len(series)*100:.1f}%)",
                        "priority": "high",
                        "use_case": "Robust to outliers"
                    })
                
                # Log transformation for highly skewed data
                if abs(skewness) > 2 and min_val > 0:
                    scaling_recommendation["recommended_scalers"].append({
                        "method": "Log Transformation + StandardScaler",
                        "reason": f"Highly skewed data (skewness: {skewness:.2f})",
                        "priority": "high",
                        "use_case": "Reduce skewness before scaling"
                    })
                
                recommendations["scaling_recommendations"].append(scaling_recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending scaling: {e}")
            return {"error": str(e)}
    
    def identify_feature_creation_opportunities(self) -> Dict[str, Any]:
        """Identify opportunities for creating new features"""
        try:
            opportunities = {
                "mathematical_combinations": [],
                "datetime_features": [],
                "text_features": [],
                "interaction_features": [],
                "binning_opportunities": []
            }
            
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            # Mathematical combinations
            if len(numeric_cols) >= 2:
                for i, col1 in enumerate(numeric_cols):
                    for j, col2 in enumerate(numeric_cols):
                        if i < j:
                            # Only suggest meaningful combinations
                            if self._are_mathematically_related(col1, col2):
                                opportunities["mathematical_combinations"].append({
                                    "feature1": col1,
                                    "feature2": col2,
                                    "suggested_operations": [
                                        {"operation": "ratio", "formula": f"{col1} / {col2}", "use_case": "Relative comparison"},
                                        {"operation": "sum", "formula": f"{col1} + {col2}", "use_case": "Total or combined effect"},
                                        {"operation": "difference", "formula": f"{col1} - {col2}", "use_case": "Change or gap analysis"},
                                        {"operation": "product", "formula": f"{col1} * {col2}", "use_case": "Interaction effect"}
                                    ]
                                })
            
            # Datetime feature opportunities
            datetime_cols = [col for col in self.df.columns if any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated'])]
            
            for col in datetime_cols:
                try:
                    datetime_series = pd.to_datetime(self.df[col], errors='coerce')
                    if datetime_series.notna().sum() > 0:
                        opportunities["datetime_features"].append({
                            "source_column": col,
                            "extractable_features": [
                                {"feature": "age_in_days", "formula": "(today - date).days", "use_case": "Time since event"},
                                {"feature": "is_business_day", "formula": "not is_weekend(date)", "use_case": "Business logic"},
                                {"feature": "season", "formula": "map month to season", "use_case": "Seasonal patterns"},
                                {"feature": "time_of_day_category", "formula": "map hour to morning/afternoon/evening/night", "use_case": "Time-based behavior"}
                            ]
                        })
                        
                        # If multiple datetime columns, suggest time differences
                        for other_col in datetime_cols:
                            if other_col != col:
                                opportunities["datetime_features"][-1]["extractable_features"].append({
                                    "feature": f"days_between_{col}_{other_col}",
                                    "formula": f"({other_col} - {col}).days",
                                    "use_case": "Duration between events"
                                })
                                
                except Exception as e:
                    logger.warning(f"Could not analyze datetime column {col}: {e}")
            
            # Text feature opportunities
            text_cols = self.df.select_dtypes(include=['object']).columns
            
            for col in text_cols:
                series = self.df[col].dropna().astype(str)
                if len(series) == 0:
                    continue
                
                # Check if column contains text (not just categories)
                avg_length = series.str.len().mean()
                if avg_length > 10:  # Likely text, not just categorical
                    opportunities["text_features"].append({
                        "source_column": col,
                        "extractable_features": [
                            {"feature": "text_length", "formula": "len(text)", "use_case": "Content complexity"},
                            {"feature": "word_count", "formula": "len(text.split())", "use_case": "Content volume"},
                            {"feature": "has_special_chars", "formula": "bool(re.search(r'[^\\w\\s]', text))", "use_case": "Content type indicator"},
                            {"feature": "sentiment_score", "formula": "sentiment_analysis(text)", "use_case": "Emotional content (requires NLP)"},
                            {"feature": "contains_numbers", "formula": "bool(re.search(r'\\d', text))", "use_case": "Mixed content indicator"}
                        ]
                    })
            
            # Interaction features (for columns that might interact)
            categorical_cols = [col for col in self.df.select_dtypes(include=['object', 'category']).columns if self.df[col].nunique() <= 20]
            
            if len(categorical_cols) >= 2:
                for i, col1 in enumerate(categorical_cols):
                    for j, col2 in enumerate(categorical_cols):
                        if i < j:
                            opportunities["interaction_features"].append({
                                "feature1": col1,
                                "feature2": col2,
                                "interaction_type": "categorical_combination",
                                "formula": f"{col1} + '_' + {col2}",
                                "use_case": "Capture combined effect of categories"
                            })
            
            # Binning opportunities for continuous variables
            for col in numeric_cols:
                series = self.df[col].dropna()
                if len(series) > 0 and series.nunique() > 10:  # Continuous variable
                    opportunities["binning_opportunities"].append({
                        "column_name": col,
                        "binning_strategies": [
                            {"method": "equal_width", "bins": 5, "use_case": "Simple categorization"},
                            {"method": "equal_frequency", "bins": 5, "use_case": "Balanced categories"},
                            {"method": "quantile_based", "quantiles": [0, 0.25, 0.5, 0.75, 1.0], "use_case": "Statistical quartiles"},
                            {"method": "custom_business", "example": "age groups, income brackets", "use_case": "Domain-specific categories"}
                        ]
                    })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error identifying feature creation opportunities: {e}")
            return {"error": str(e)}
    
    def recommend_transformations(self) -> Dict[str, Any]:
        """Recommend data transformations to improve feature quality"""
        try:
            recommendations = {
                "normalization_transformations": [],
                "distribution_transformations": [],
                "outlier_transformations": [],
                "missing_value_transformations": []
            }
            
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            # Analyze each numeric column for transformation needs
            for col in numeric_cols:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                skewness = series.skew()
                kurtosis = series.kurtosis()
                
                # Distribution transformations
                transformation_rec = {
                    "column_name": col,
                    "current_skewness": round(float(skewness), 3),
                    "current_kurtosis": round(float(kurtosis), 3),
                    "recommended_transformations": []
                }
                
                # Highly skewed data
                if abs(skewness) > 2:
                    if series.min() > 0:
                        transformation_rec["recommended_transformations"].append({
                            "transformation": "Log Transformation",
                            "reason": f"Reduce high skewness ({skewness:.2f})",
                            "formula": "np.log(x + 1)",
                            "expected_effect": "Reduce skewness, make distribution more normal"
                        })
                        
                        transformation_rec["recommended_transformations"].append({
                            "transformation": "Square Root Transformation",
                            "reason": f"Alternative to log for positive skewed data",
                            "formula": "np.sqrt(x)",
                            "expected_effect": "Moderate skewness reduction"
                        })
                    
                    if skewness < -2:  # Negative skew
                        transformation_rec["recommended_transformations"].append({
                            "transformation": "Square Transformation",
                            "reason": f"Reduce negative skewness ({skewness:.2f})",
                            "formula": "x**2",
                            "expected_effect": "Reduce negative skewness"
                        })
                
                # High kurtosis (heavy tails)
                if abs(kurtosis) > 3:
                    transformation_rec["recommended_transformations"].append({
                        "transformation": "Yeo-Johnson Transformation",
                        "reason": f"Handle heavy tails (kurtosis: {kurtosis:.2f})",
                        "formula": "scipy.stats.yeojohnson(x)",
                        "expected_effect": "Normalize distribution, handle both positive and negative values"
                    })
                
                if transformation_rec["recommended_transformations"]:
                    recommendations["distribution_transformations"].append(transformation_rec)
                
                # Outlier handling
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                outliers = series[(series < Q1 - 1.5 * IQR) | (series > Q3 + 1.5 * IQR)]
                
                if len(outliers) > len(series) * 0.05:  # More than 5% outliers
                    outlier_rec = {
                        "column_name": col,
                        "outlier_count": len(outliers),
                        "outlier_percentage": round(len(outliers) / len(series) * 100, 2),
                        "handling_strategies": [
                            {
                                "method": "Winsorization",
                                "description": "Cap extreme values at 5th and 95th percentiles",
                                "use_case": "Preserve data points while limiting extreme values"
                            },
                            {
                                "method": "IQR Capping",
                                "description": "Cap values beyond 1.5*IQR from quartiles",
                                "use_case": "Statistical approach to outlier handling"
                            },
                            {
                                "method": "Z-score Filtering",
                                "description": "Remove values with |z-score| > 3",
                                "use_case": "When outliers are likely data errors"
                            },
                            {
                                "method": "Log Transformation",
                                "description": "Apply log transformation to reduce impact",
                                "use_case": "When outliers represent valid extreme values"
                            }
                        ]
                    }
                    recommendations["outlier_transformations"].append(outlier_rec)
            
            # Missing value handling
            columns_with_missing = self.df.columns[self.df.isnull().any()].tolist()
            
            for col in columns_with_missing:
                missing_count = self.df[col].isnull().sum()
                missing_percentage = missing_count / len(self.df) * 100
                
                missing_rec = {
                    "column_name": col,
                    "missing_count": int(missing_count),
                    "missing_percentage": round(missing_percentage, 2),
                    "column_type": str(self.df[col].dtype),
                    "handling_strategies": []
                }
                
                if missing_percentage < 5:
                    missing_rec["handling_strategies"].extend([
                        {"method": "Drop rows", "reason": "Low missing percentage, minimal data loss"},
                        {"method": "Simple imputation", "reason": "Fill with mean/mode/median"}
                    ])
                elif missing_percentage < 20:
                    if pd.api.types.is_numeric_dtype(self.df[col]):
                        missing_rec["handling_strategies"].extend([
                            {"method": "Mean/Median imputation", "reason": "Numeric data with moderate missingness"},
                            {"method": "Forward fill", "reason": "If temporal relationship exists"},
                            {"method": "Predictive imputation", "reason": "Use other features to predict missing values"}
                        ])
                    else:
                        missing_rec["handling_strategies"].extend([
                            {"method": "Mode imputation", "reason": "Categorical data with moderate missingness"},
                            {"method": "Create 'Missing' category", "reason": "Preserve information about missingness"},
                            {"method": "Predictive imputation", "reason": "Use other features to predict missing values"}
                        ])
                else:
                    missing_rec["handling_strategies"].extend([
                        {"method": "Create missing indicator", "reason": "High missingness - preserve pattern information"},
                        {"method": "Consider dropping column", "reason": "High missingness may indicate poor data quality"},
                        {"method": "Advanced imputation (KNN/MICE)", "reason": "Sophisticated imputation for high-value features"}
                    ])
                
                recommendations["missing_value_transformations"].append(missing_rec)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending transformations: {e}")
            return {"error": str(e)}
    
    def analyze_dimensionality(self) -> Dict[str, Any]:
        """Analyze dimensionality and recommend dimensionality reduction if needed"""
        try:
            analysis = {
                "current_dimensions": len(self.df.columns),
                "data_points": len(self.df),
                "dimensionality_ratio": len(self.df.columns) / len(self.df) if len(self.df) > 0 else 0,
                "recommendations": []
            }
            
            # Assess curse of dimensionality risk
            if analysis["dimensionality_ratio"] > 0.1:
                analysis["curse_of_dimensionality_risk"] = "high"
                analysis["recommendations"].append({
                    "issue": "High dimensionality relative to data points",
                    "recommendation": "Consider dimensionality reduction techniques",
                    "priority": "high"
                })
            elif analysis["dimensionality_ratio"] > 0.05:
                analysis["curse_of_dimensionality_risk"] = "medium"
                analysis["recommendations"].append({
                    "issue": "Moderate dimensionality",
                    "recommendation": "Monitor model performance, consider feature selection",
                    "priority": "medium"
                })
            else:
                analysis["curse_of_dimensionality_risk"] = "low"
            
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            if SKLEARN_AVAILABLE and len(numeric_cols) > 2:
                # PCA analysis for numeric features
                numeric_data = self.df[numeric_cols].dropna()
                
                if len(numeric_data) > 0:
                    # Standardize data for PCA
                    from sklearn.preprocessing import StandardScaler
                    scaler = StandardScaler()
                    scaled_data = scaler.fit_transform(numeric_data)
                    
                    # Fit PCA
                    pca = PCA()
                    pca.fit(scaled_data)
                    
                    # Calculate cumulative explained variance
                    cumsum_variance = np.cumsum(pca.explained_variance_ratio_)
                    
                    # Find number of components for different variance thresholds
                    components_80 = np.argmax(cumsum_variance >= 0.8) + 1
                    components_90 = np.argmax(cumsum_variance >= 0.9) + 1
                    components_95 = np.argmax(cumsum_variance >= 0.95) + 1
                    
                    analysis["pca_analysis"] = {
                        "total_components": len(numeric_cols),
                        "components_for_80_variance": int(components_80),
                        "components_for_90_variance": int(components_90),
                        "components_for_95_variance": int(components_95),
                        "explained_variance_ratio": [round(float(x), 4) for x in pca.explained_variance_ratio_[:10]],
                        "cumulative_variance_ratio": [round(float(x), 4) for x in cumsum_variance[:10]]
                    }
                    
                    # Dimensionality reduction recommendations
                    if components_80 < len(numeric_cols) * 0.5:
                        analysis["recommendations"].append({
                            "technique": "PCA",
                            "recommendation": f"Use PCA with {components_80} components to retain 80% variance",
                            "dimensionality_reduction": f"{len(numeric_cols)} -> {components_80}",
                            "priority": "medium"
                        })
            
            # Feature selection recommendations
            analysis["feature_selection_methods"] = [
                {
                    "method": "Correlation-based selection",
                    "description": "Remove highly correlated features",
                    "use_case": "When multicollinearity is a concern",
                    "sklearn_class": "Manual correlation analysis"
                },
                {
                    "method": "Univariate selection",
                    "description": "Select features based on statistical tests",
                    "use_case": "Quick feature selection with target variable",
                    "sklearn_class": "SelectKBest, SelectPercentile"
                },
                {
                    "method": "Recursive Feature Elimination",
                    "description": "Iteratively remove features and build model on remaining",
                    "use_case": "Model-based feature importance",
                    "sklearn_class": "RFE, RFECV"
                },
                {
                    "method": "Tree-based selection",
                    "description": "Use feature importance from tree-based models",
                    "use_case": "Non-linear feature importance",
                    "sklearn_class": "SelectFromModel with RandomForest"
                }
            ]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing dimensionality: {e}")
            return {"error": str(e)}
    
    def analyze_features_for_target(self, target_column: str) -> Dict[str, Any]:
        """Analyze features in relation to a target variable"""
        try:
            if target_column not in self.df.columns:
                return {"error": f"Target column '{target_column}' not found"}
            
            analysis = {
                "target_column": target_column,
                "target_type": self._determine_target_type(self.df[target_column]),
                "feature_importance": [],
                "feature_selection_recommendations": []
            }
            
            # Separate features and target
            features_df = self.df.drop(columns=[target_column])
            target_series = self.df[target_column].dropna()
            
            # Align features with non-null target values
            features_df = features_df.loc[target_series.index]
            
            if SKLEARN_AVAILABLE and len(features_df) > 0:
                
                # Numeric features analysis
                numeric_features = features_df.select_dtypes(include=[np.number]).columns
                
                if len(numeric_features) > 0:
                    numeric_data = features_df[numeric_features].fillna(features_df[numeric_features].mean())
                    
                    if analysis["target_type"] == "classification":
                        # Classification: use mutual information and f_classif
                        try:
                            # Mutual information
                            mi_scores = mutual_info_classif(numeric_data, target_series)
                            mi_results = [{"feature": feat, "score": round(float(score), 4), "method": "mutual_info"} 
                                         for feat, score in zip(numeric_features, mi_scores)]
                            
                            # F-test
                            f_scores, f_pvalues = f_classif(numeric_data, target_series)
                            f_results = [{"feature": feat, "score": round(float(score), 4), "p_value": round(float(pval), 4), "method": "f_classif"} 
                                        for feat, score, pval in zip(numeric_features, f_scores, f_pvalues)]
                            
                            analysis["feature_importance"].extend(mi_results + f_results)
                            
                        except Exception as e:
                            logger.warning(f"Could not compute feature importance: {e}")
                    
                    elif analysis["target_type"] == "regression":
                        # Regression: use correlation and mutual information
                        try:
                            # Correlation with target
                            correlations = numeric_data.corrwith(target_series).abs()
                            corr_results = [{"feature": feat, "score": round(float(score), 4), "method": "correlation"} 
                                           for feat, score in correlations.items() if not np.isnan(score)]
                            
                            # Mutual information for regression
                            mi_scores = mutual_info_classif(numeric_data, target_series)  # Note: using classif version for discretized target
                            mi_results = [{"feature": feat, "score": round(float(score), 4), "method": "mutual_info"} 
                                         for feat, score in zip(numeric_features, mi_scores)]
                            
                            analysis["feature_importance"].extend(corr_results + mi_results)
                            
                        except Exception as e:
                            logger.warning(f"Could not compute feature importance: {e}")
                
                # Tree-based feature importance
                try:
                    # Prepare all features (numeric + encoded categorical)
                    all_features = features_df.copy()
                    
                    # Simple encoding for categorical features
                    categorical_features = all_features.select_dtypes(include=['object', 'category']).columns
                    for col in categorical_features:
                        if all_features[col].nunique() <= 50:  # Reasonable cardinality
                            encoded = pd.get_dummies(all_features[col], prefix=col, dummy_na=True)
                            all_features = pd.concat([all_features.drop(columns=[col]), encoded], axis=1)
                        else:
                            # High cardinality - use frequency encoding
                            freq_encoding = all_features[col].value_counts()
                            all_features[col] = all_features[col].map(freq_encoding).fillna(0)
                    
                    # Fill remaining missing values
                    all_features = all_features.fillna(0)
                    
                    # Tree-based importance
                    if analysis["target_type"] == "classification":
                        model = RandomForestClassifier(n_estimators=100, random_state=42)
                    else:
                        model = RandomForestRegressor(n_estimators=100, random_state=42)
                    
                    model.fit(all_features, target_series)
                    
                    tree_importance = [{"feature": feat, "score": round(float(score), 4), "method": "random_forest"} 
                                      for feat, score in zip(all_features.columns, model.feature_importances_)]
                    
                    analysis["feature_importance"].extend(tree_importance)
                    
                except Exception as e:
                    logger.warning(f"Could not compute tree-based importance: {e}")
            
            # Sort feature importance by score (for each method)
            if analysis["feature_importance"]:
                # Group by method and sort
                methods = set(item["method"] for item in analysis["feature_importance"])
                sorted_importance = {}
                
                for method in methods:
                    method_results = [item for item in analysis["feature_importance"] if item["method"] == method]
                    sorted_importance[method] = sorted(method_results, key=lambda x: x["score"], reverse=True)
                
                analysis["feature_importance_by_method"] = sorted_importance
            
            # Feature selection recommendations based on target type
            if analysis["target_type"] == "classification":
                analysis["feature_selection_recommendations"] = [
                    {
                        "method": "SelectKBest with chi2",
                        "use_case": "Categorical features with categorical target",
                        "parameters": "k=10 or k='all'"
                    },
                    {
                        "method": "SelectKBest with f_classif",
                        "use_case": "Numeric features with categorical target",
                        "parameters": "k=10 or k='all'"
                    },
                    {
                        "method": "RFE with RandomForestClassifier",
                        "use_case": "Comprehensive feature selection",
                        "parameters": "n_features_to_select=10"
                    }
                ]
            else:
                analysis["feature_selection_recommendations"] = [
                    {
                        "method": "SelectKBest with f_regression",
                        "use_case": "Numeric features with numeric target",
                        "parameters": "k=10 or k='all'"
                    },
                    {
                        "method": "RFE with RandomForestRegressor",
                        "use_case": "Comprehensive feature selection",
                        "parameters": "n_features_to_select=10"
                    },
                    {
                        "method": "Lasso regularization",
                        "use_case": "Automatic feature selection through regularization",
                        "parameters": "alpha=0.01"
                    }
                ]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing features for target: {e}")
            return {"error": str(e)}
    
    # Feature Engineering Implementation Methods
    
    def apply_encoding(self, column: str, method: str, **kwargs) -> bool:
        """Apply encoding to a column"""
        try:
            if column not in self.df.columns:
                logger.error(f"Column '{column}' not found")
                return False
            
            if method == "label_encoding":
                encoder = LabelEncoder()
                self.df[f"{column}_encoded"] = encoder.fit_transform(self.df[column].fillna('missing'))
                self.encoders[f"{column}_label"] = encoder
                
            elif method == "onehot_encoding":
                if SKLEARN_AVAILABLE:
                    try:
                        # Try new parameter name first (sklearn >= 1.2)
                        encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
                    except TypeError:
                        # Fallback to old parameter name (sklearn < 1.2)
                        encoder = OneHotEncoder(sparse=False, handle_unknown='ignore')
                    encoded = encoder.fit_transform(self.df[[column]].fillna('missing'))
                    feature_names = [f"{column}_{cat}" for cat in encoder.categories_[0]]
                    
                    # Add encoded columns
                    for i, name in enumerate(feature_names):
                        self.df[name] = encoded[:, i]
                    
                    self.encoders[f"{column}_onehot"] = encoder
                else:
                    # Fallback to pandas get_dummies
                    encoded = pd.get_dummies(self.df[column], prefix=column, dummy_na=True)
                    self.df = pd.concat([self.df, encoded], axis=1)
                
            elif method == "frequency_encoding":
                frequency_map = self.df[column].value_counts().to_dict()
                self.df[f"{column}_frequency"] = self.df[column].map(frequency_map).fillna(0)
                
            self.feature_transformations.append({
                "operation": f"encoding_{method}",
                "column": column,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying {method} encoding to {column}: {e}")
            return False
    
    def apply_scaling(self, columns: Union[str, List[str]], method: str = "standard") -> bool:
        """Apply scaling to numeric columns"""
        try:
            if isinstance(columns, str):
                columns = [columns]
            
            # Validate columns exist and are numeric
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            valid_columns = [col for col in columns if col in numeric_cols]
            
            if not valid_columns:
                logger.error("No valid numeric columns found for scaling")
                return False
            
            if not SKLEARN_AVAILABLE:
                logger.error("scikit-learn not available for scaling")
                return False
            
            # Select scaler
            if method == "standard":
                scaler = StandardScaler()
            elif method == "minmax":
                scaler = MinMaxScaler()
            elif method == "robust":
                scaler = RobustScaler()
            else:
                logger.error(f"Unknown scaling method: {method}")
                return False
            
            # Apply scaling
            scaled_data = scaler.fit_transform(self.df[valid_columns])
            
            # Update dataframe
            for i, col in enumerate(valid_columns):
                self.df[f"{col}_scaled"] = scaled_data[:, i]
            
            self.scalers[f"{method}_scaler"] = scaler
            
            self.feature_transformations.append({
                "operation": f"scaling_{method}",
                "columns": valid_columns,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying {method} scaling: {e}")
            return False
    
    def create_datetime_features(self, column: str, features: List[str] = None) -> bool:
        """Extract datetime features from a datetime column"""
        try:
            if column not in self.df.columns:
                logger.error(f"Column '{column}' not found")
                return False
            
            # Convert to datetime
            datetime_series = pd.to_datetime(self.df[column], errors='coerce')
            
            if datetime_series.isna().all():
                logger.error(f"Could not convert column '{column}' to datetime")
                return False
            
            if features is None:
                features = ['year', 'month', 'day', 'dayofweek', 'hour', 'is_weekend']
            
            # Extract features
            for feature in features:
                if feature == 'year':
                    self.df[f"{column}_year"] = datetime_series.dt.year
                elif feature == 'month':
                    self.df[f"{column}_month"] = datetime_series.dt.month
                elif feature == 'day':
                    self.df[f"{column}_day"] = datetime_series.dt.day
                elif feature == 'dayofweek':
                    self.df[f"{column}_dayofweek"] = datetime_series.dt.dayofweek
                elif feature == 'hour':
                    self.df[f"{column}_hour"] = datetime_series.dt.hour
                elif feature == 'is_weekend':
                    self.df[f"{column}_is_weekend"] = (datetime_series.dt.dayofweek >= 5).astype(int)
                elif feature == 'quarter':
                    self.df[f"{column}_quarter"] = datetime_series.dt.quarter
                elif feature == 'days_since_epoch':
                    epoch = pd.Timestamp('1970-01-01')
                    self.df[f"{column}_days_since_epoch"] = (datetime_series - epoch).dt.days
            
            self.feature_transformations.append({
                "operation": "datetime_feature_extraction",
                "column": column,
                "features": features,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating datetime features for {column}: {e}")
            return False
    
    def create_interaction_features(self, columns: List[str], interaction_type: str = "multiply") -> bool:
        """Create interaction features between columns"""
        try:
            if len(columns) < 2:
                logger.error("Need at least 2 columns for interaction features")
                return False
            
            valid_columns = [col for col in columns if col in self.df.columns]
            if len(valid_columns) < 2:
                logger.error("Need at least 2 valid columns for interaction features")
                return False
            
            if interaction_type == "multiply":
                # Numeric multiplication
                numeric_cols = [col for col in valid_columns if pd.api.types.is_numeric_dtype(self.df[col])]
                for i in range(len(numeric_cols)):
                    for j in range(i + 1, len(numeric_cols)):
                        col1, col2 = numeric_cols[i], numeric_cols[j]
                        self.df[f"{col1}_x_{col2}"] = self.df[col1] * self.df[col2]
            
            elif interaction_type == "combine_categorical":
                # Categorical combination
                categorical_cols = [col for col in valid_columns if not pd.api.types.is_numeric_dtype(self.df[col])]
                for i in range(len(categorical_cols)):
                    for j in range(i + 1, len(categorical_cols)):
                        col1, col2 = categorical_cols[i], categorical_cols[j]
                        self.df[f"{col1}_combined_{col2}"] = (self.df[col1].astype(str) + "_" + 
                                                             self.df[col2].astype(str))
            
            self.feature_transformations.append({
                "operation": f"interaction_{interaction_type}",
                "columns": valid_columns,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating interaction features: {e}")
            return False
    
    def apply_binning(self, column: str, bins: Union[int, List], method: str = "equal_width") -> bool:
        """Apply binning to a numeric column"""
        try:
            if column not in self.df.columns:
                logger.error(f"Column '{column}' not found")
                return False
            
            if not pd.api.types.is_numeric_dtype(self.df[column]):
                logger.error(f"Column '{column}' is not numeric")
                return False
            
            if method == "equal_width":
                self.df[f"{column}_binned"] = pd.cut(self.df[column], bins=bins)
            elif method == "equal_frequency":
                self.df[f"{column}_binned"] = pd.qcut(self.df[column], q=bins, duplicates='drop')
            elif method == "custom":
                if not isinstance(bins, list):
                    logger.error("Custom binning requires a list of bin edges")
                    return False
                self.df[f"{column}_binned"] = pd.cut(self.df[column], bins=bins)
            
            # Convert to string labels
            self.df[f"{column}_binned"] = self.df[f"{column}_binned"].astype(str)
            
            self.feature_transformations.append({
                "operation": f"binning_{method}",
                "column": column,
                "bins": bins,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying binning to {column}: {e}")
            return False
    
    # Helper methods
    
    def _assess_feature_quality(self, series: pd.Series) -> Dict[str, Any]:
        """Assess the quality of a feature"""
        quality = {
            "completeness": 1 - (series.isnull().sum() / len(series)),
            "uniqueness": series.nunique() / len(series) if len(series) > 0 else 0,
            "data_type": str(series.dtype)
        }
        
        if pd.api.types.is_numeric_dtype(series):
            quality["variance"] = float(series.var()) if series.var() is not None else 0
            quality["skewness"] = float(series.skew()) if not series.empty else 0
        
        return quality
    
    def _detect_ordinal_pattern(self, series: pd.Series) -> bool:
        """Detect if a categorical series has ordinal properties"""
        unique_values = series.dropna().unique()
        
        # Check for common ordinal patterns
        ordinal_patterns = [
            ['low', 'medium', 'high'],
            ['small', 'medium', 'large'],
            ['bad', 'good', 'excellent'],
            ['never', 'sometimes', 'often', 'always'],
            ['strongly disagree', 'disagree', 'neutral', 'agree', 'strongly agree']
        ]
        
        unique_str = [str(val).lower() for val in unique_values]
        
        for pattern in ordinal_patterns:
            if set(unique_str).issubset(set(pattern)):
                return True
        
        # Check for numeric-like strings
        try:
            numeric_values = [float(val) for val in unique_values if str(val).replace('.', '').replace('-', '').isdigit()]
            if len(numeric_values) == len(unique_values) and len(numeric_values) > 2:
                return True
        except:
            pass
        
        return False
    
    def _are_mathematically_related(self, col1: str, col2: str) -> bool:
        """Check if two columns might be mathematically related"""
        # Basic heuristics for suggesting mathematical operations
        related_patterns = [
            ('price', 'quantity'),
            ('width', 'height'),
            ('start', 'end'),
            ('min', 'max'),
            ('old', 'new'),
            ('before', 'after')
        ]
        
        col1_lower = col1.lower()
        col2_lower = col2.lower()
        
        for pattern1, pattern2 in related_patterns:
            if (pattern1 in col1_lower and pattern2 in col2_lower) or \
               (pattern2 in col1_lower and pattern1 in col2_lower):
                return True
        
        return True  # Default to suggesting combinations for all numeric pairs
    
    def _determine_target_type(self, target_series: pd.Series) -> str:
        """Determine if target is classification or regression"""
        if pd.api.types.is_numeric_dtype(target_series):
            # If numeric, check if it looks like classes or continuous values
            unique_count = target_series.nunique()
            total_count = len(target_series)
            
            if unique_count <= 20 and unique_count < total_count * 0.1:
                return "classification"
            else:
                return "regression"
        else:
            return "classification"
    
    def get_feature_engineering_summary(self) -> Dict[str, Any]:
        """Get summary of applied feature engineering operations"""
        return {
            "original_shape": list(self.original_df.shape),
            "current_shape": list(self.df.shape),
            "features_added": self.df.shape[1] - self.original_df.shape[1],
            "transformations_applied": len(self.feature_transformations),
            "transformation_history": self.feature_transformations,
            "encoders_fitted": list(self.encoders.keys()),
            "scalers_fitted": list(self.scalers.keys())
        }
    
    def save_engineered_data(self, output_path: str) -> bool:
        """Save the engineered dataset"""
        try:
            self.df.to_csv(output_path, index=False)
            logger.info(f"Engineered data saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving engineered data: {e}")
            return False
    
    def save_analysis(self, output_path: str, analysis: Optional[Dict[str, Any]] = None) -> bool:
        """Save feature engineering analysis to JSON file"""
        try:
            if analysis is None:
                analysis = self.get_full_feature_engineering_analysis()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Feature engineering analysis saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save feature engineering analysis: {e}")
            return False

# Convenience function for simple usage
def engineer_features(file_path: str, target_column: Optional[str] = None, 
                     output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to perform feature engineering analysis
    
    Args:
        file_path: Path to CSV file
        target_column: Target variable for supervised analysis
        output_path: Optional path to save results
        
    Returns:
        Feature engineering analysis results
    """
    processor = FeatureProcessor(file_path=file_path)
    analysis = processor.get_full_feature_engineering_analysis(target_column)
    
    if output_path:
        processor.save_analysis(output_path, analysis)
    
    return analysis