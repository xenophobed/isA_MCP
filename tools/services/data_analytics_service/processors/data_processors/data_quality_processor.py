#!/usr/bin/env python3
"""
Data Quality Processor
Advanced data quality assessment tool building on the existing CSV processor infrastructure.
Provides anomaly detection, data validation, and quality metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import logging
import re
import json
from pathlib import Path

# Anomaly detection libraries
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import DBSCAN
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. Some anomaly detection methods will be disabled.")

try:
    from .csv_processor import CSVProcessor
except ImportError:
    from csv_processor import CSVProcessor

logger = logging.getLogger(__name__)

class DataQualityProcessor:
    """
    Data quality assessment processor
    Builds on CSVProcessor for comprehensive data quality analysis
    """
    
    def __init__(self, csv_processor: Optional[CSVProcessor] = None, file_path: Optional[str] = None):
        """
        Initialize data quality processor
        
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
        self._load_data()
    
    def _load_data(self) -> bool:
        """Load data from CSV processor"""
        try:
            if not self.csv_processor.load_csv():
                return False
            self.df = self.csv_processor.df
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def get_full_quality_assessment(self) -> Dict[str, Any]:
        """
        Get comprehensive data quality assessment
        
        Returns:
            Complete data quality assessment results
        """
        if self.df is None:
            return {"error": "No data loaded"}
        
        return {
            "overview": self.assess_overall_quality(),
            "completeness": self.assess_completeness(),
            "consistency": self.assess_consistency(),
            "validity": self.assess_validity(),
            "uniqueness": self.assess_uniqueness(),
            "accuracy": self.assess_accuracy(),
            "anomalies": self.detect_anomalies(),
            "data_profiling": self.profile_data_patterns(),
            "recommendations": self.generate_quality_recommendations(),
            "assessment_metadata": {
                "timestamp": datetime.now().isoformat(),
                "sklearn_available": SKLEARN_AVAILABLE,
                "data_shape": list(self.df.shape),
                "total_cells": self.df.size
            }
        }
    
    def assess_overall_quality(self) -> Dict[str, Any]:
        """Assess overall data quality with composite scores"""
        try:
            total_cells = self.df.size
            if total_cells == 0:
                return {"error": "No data to assess"}
            
            # Completeness score
            missing_cells = self.df.isnull().sum().sum()
            completeness_score = 1 - (missing_cells / total_cells)
            
            # Uniqueness score (for columns that should be unique)
            uniqueness_scores = []
            for col in self.df.columns:
                if any(keyword in col.lower() for keyword in ['id', 'key', 'identifier']):
                    uniqueness = self.df[col].nunique() / len(self.df[col])
                    uniqueness_scores.append(uniqueness)
            avg_uniqueness = np.mean(uniqueness_scores) if uniqueness_scores else 1.0
            
            # Validity score (basic format validation)
            validity_scores = []
            for col in self.df.columns:
                col_validity = self._assess_column_validity(self.df[col])
                validity_scores.append(col_validity)
            avg_validity = np.mean(validity_scores)
            
            # Consistency score (data type consistency)
            consistency_scores = []
            for col in self.df.columns:
                consistency = self._assess_column_consistency(self.df[col])
                consistency_scores.append(consistency)
            avg_consistency = np.mean(consistency_scores)
            
            # Overall composite score
            weights = {
                'completeness': 0.3,
                'uniqueness': 0.2,
                'validity': 0.3,
                'consistency': 0.2
            }
            
            overall_score = (
                completeness_score * weights['completeness'] +
                avg_uniqueness * weights['uniqueness'] +
                avg_validity * weights['validity'] +
                avg_consistency * weights['consistency']
            )
            
            return {
                "overall_quality_score": round(overall_score, 3),
                "quality_grade": self._score_to_grade(overall_score),
                "component_scores": {
                    "completeness": round(completeness_score, 3),
                    "uniqueness": round(avg_uniqueness, 3),
                    "validity": round(avg_validity, 3),
                    "consistency": round(avg_consistency, 3)
                },
                "score_weights": weights,
                "assessment_summary": self._generate_quality_summary(overall_score)
            }
            
        except Exception as e:
            logger.error(f"Error assessing overall quality: {e}")
            return {"error": str(e)}
    
    def assess_completeness(self) -> Dict[str, Any]:
        """Assess data completeness"""
        try:
            completeness = {}
            
            # Overall completeness
            total_cells = self.df.size
            missing_cells = self.df.isnull().sum().sum()
            overall_completeness = 1 - (missing_cells / total_cells) if total_cells > 0 else 0
            
            completeness["overall"] = {
                "completeness_rate": round(overall_completeness, 3),
                "missing_cells": int(missing_cells),
                "total_cells": int(total_cells),
                "missing_percentage": round((missing_cells / total_cells) * 100, 2)
            }
            
            # Column-wise completeness
            column_completeness = []
            for col in self.df.columns:
                missing_count = self.df[col].isnull().sum()
                total_count = len(self.df[col])
                completeness_rate = 1 - (missing_count / total_count) if total_count > 0 else 0
                
                column_completeness.append({
                    "column_name": col,
                    "completeness_rate": round(completeness_rate, 3),
                    "missing_count": int(missing_count),
                    "total_count": int(total_count),
                    "missing_percentage": round((missing_count / total_count) * 100, 2),
                    "quality_level": self._completeness_level(completeness_rate)
                })
            
            completeness["by_column"] = column_completeness
            
            # Row-wise completeness patterns
            rows_missing_data = self.df.isnull().any(axis=1).sum()
            rows_complete = len(self.df) - rows_missing_data
            
            completeness["by_row"] = {
                "complete_rows": int(rows_complete),
                "rows_with_missing": int(rows_missing_data),
                "complete_row_percentage": round((rows_complete / len(self.df)) * 100, 2) if len(self.df) > 0 else 0
            }
            
            # Missing data patterns
            missing_patterns = self._analyze_missing_patterns()
            completeness["missing_patterns"] = missing_patterns
            
            return completeness
            
        except Exception as e:
            logger.error(f"Error assessing completeness: {e}")
            return {"error": str(e)}
    
    def assess_consistency(self) -> Dict[str, Any]:
        """Assess data consistency"""
        try:
            consistency = {}
            
            # Data type consistency
            type_consistency = []
            for col in self.df.columns:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                # Check if values can be consistently parsed as the expected type
                consistency_score = self._assess_column_consistency(series)
                
                type_consistency.append({
                    "column_name": col,
                    "declared_type": str(series.dtype),
                    "consistency_score": round(consistency_score, 3),
                    "inconsistent_values": self._find_type_inconsistencies(series),
                    "recommendation": self._recommend_type_fix(series)
                })
            
            consistency["data_types"] = type_consistency
            
            # Format consistency for text columns
            format_consistency = []
            text_cols = self.df.select_dtypes(include=['object']).columns
            
            for col in text_cols:
                series = self.df[col].dropna().astype(str)
                if len(series) == 0:
                    continue
                
                format_analysis = self._analyze_text_format_consistency(series)
                if format_analysis:
                    format_analysis["column_name"] = col
                    format_consistency.append(format_analysis)
            
            consistency["text_formats"] = format_consistency
            
            # Value range consistency for numeric columns
            numeric_consistency = []
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                range_analysis = self._analyze_numeric_range_consistency(series, col)
                range_analysis["column_name"] = col
                numeric_consistency.append(range_analysis)
            
            consistency["numeric_ranges"] = numeric_consistency
            
            return consistency
            
        except Exception as e:
            logger.error(f"Error assessing consistency: {e}")
            return {"error": str(e)}
    
    def assess_validity(self) -> Dict[str, Any]:
        """Assess data validity against expected formats and rules"""
        try:
            validity = {}
            
            # Email validation
            email_columns = [col for col in self.df.columns if 'email' in col.lower()]
            email_validation = []
            
            for col in email_columns:
                series = self.df[col].dropna().astype(str)
                if len(series) == 0:
                    continue
                
                valid_emails = series.str.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
                
                email_validation.append({
                    "column_name": col,
                    "total_values": len(series),
                    "valid_emails": int(valid_emails.sum()),
                    "invalid_emails": int((~valid_emails).sum()),
                    "validity_rate": round(valid_emails.mean(), 3),
                    "invalid_examples": series[~valid_emails].head(5).tolist()
                })
            
            validity["email_validation"] = email_validation
            
            # Phone number validation
            phone_columns = [col for col in self.df.columns if any(keyword in col.lower() for keyword in ['phone', 'tel', 'mobile'])]
            phone_validation = []
            
            for col in phone_columns:
                series = self.df[col].dropna().astype(str)
                if len(series) == 0:
                    continue
                
                # Basic phone number pattern (flexible)
                valid_phones = series.str.match(r'^[\+]?[1-9][\d\-\(\)\s]{7,15}$')
                
                phone_validation.append({
                    "column_name": col,
                    "total_values": len(series),
                    "valid_phones": int(valid_phones.sum()),
                    "invalid_phones": int((~valid_phones).sum()),
                    "validity_rate": round(valid_phones.mean(), 3),
                    "invalid_examples": series[~valid_phones].head(5).tolist()
                })
            
            validity["phone_validation"] = phone_validation
            
            # Date validation
            date_columns = [col for col in self.df.columns if 'date' in col.lower() or 'time' in col.lower()]
            date_validation = []
            
            for col in date_columns:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                parsed_dates = pd.to_datetime(series, errors='coerce')
                valid_dates = ~parsed_dates.isnull()
                
                date_validation.append({
                    "column_name": col,
                    "total_values": len(series),
                    "valid_dates": int(valid_dates.sum()),
                    "invalid_dates": int((~valid_dates).sum()),
                    "validity_rate": round(valid_dates.mean(), 3),
                    "date_range": {
                        "earliest": parsed_dates.min().isoformat() if valid_dates.any() else None,
                        "latest": parsed_dates.max().isoformat() if valid_dates.any() else None
                    }
                })
            
            validity["date_validation"] = date_validation
            
            # Numeric range validation
            numeric_range_validation = []
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                range_validation = self._validate_numeric_ranges(series, col)
                range_validation["column_name"] = col
                numeric_range_validation.append(range_validation)
            
            validity["numeric_ranges"] = numeric_range_validation
            
            return validity
            
        except Exception as e:
            logger.error(f"Error assessing validity: {e}")
            return {"error": str(e)}
    
    def assess_uniqueness(self) -> Dict[str, Any]:
        """Assess data uniqueness and identify duplicates"""
        try:
            uniqueness = {}
            
            # Overall duplicate analysis
            duplicate_rows = self.df.duplicated()
            total_duplicates = duplicate_rows.sum()
            
            uniqueness["overall"] = {
                "total_rows": len(self.df),
                "duplicate_rows": int(total_duplicates),
                "unique_rows": len(self.df) - int(total_duplicates),
                "uniqueness_rate": round((len(self.df) - total_duplicates) / len(self.df), 3) if len(self.df) > 0 else 1.0,
                "duplicate_percentage": round((total_duplicates / len(self.df)) * 100, 2) if len(self.df) > 0 else 0.0
            }
            
            # Column-wise uniqueness
            column_uniqueness = []
            for col in self.df.columns:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                unique_count = series.nunique()
                total_count = len(series)
                uniqueness_rate = unique_count / total_count if total_count > 0 else 0
                
                # Check if this should be a unique identifier
                is_identifier = any(keyword in col.lower() for keyword in ['id', 'key', 'identifier', 'uuid'])
                
                column_uniqueness.append({
                    "column_name": col,
                    "unique_values": int(unique_count),
                    "total_values": int(total_count),
                    "uniqueness_rate": round(uniqueness_rate, 3),
                    "duplicate_count": int(total_count - unique_count),
                    "is_likely_identifier": is_identifier,
                    "uniqueness_expectation": "high" if is_identifier else "varies",
                    "quality_assessment": self._assess_uniqueness_quality(uniqueness_rate, is_identifier)
                })
            
            uniqueness["by_column"] = column_uniqueness
            
            # Identify potential composite keys
            composite_keys = self._identify_composite_keys()
            uniqueness["composite_key_candidates"] = composite_keys
            
            return uniqueness
            
        except Exception as e:
            logger.error(f"Error assessing uniqueness: {e}")
            return {"error": str(e)}
    
    def assess_accuracy(self) -> Dict[str, Any]:
        """Assess data accuracy through various heuristics"""
        try:
            accuracy = {}
            
            # Statistical outlier detection (potential accuracy issues)
            outlier_analysis = []
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                series = self.df[col].dropna()
                if len(series) < 4:
                    continue
                
                # IQR method for outlier detection
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = series[(series < lower_bound) | (series > upper_bound)]
                
                outlier_analysis.append({
                    "column_name": col,
                    "outlier_count": len(outliers),
                    "outlier_percentage": round(len(outliers) / len(series) * 100, 2),
                    "potential_accuracy_issues": len(outliers) > len(series) * 0.05,  # More than 5% outliers
                    "outlier_values": outliers.head(10).tolist()
                })
            
            accuracy["outlier_analysis"] = outlier_analysis
            
            # Cross-field validation (basic relationships)
            cross_field_validation = []
            
            # Check for impossible date relationships
            date_cols = [col for col in self.df.columns if 'date' in col.lower()]
            if len(date_cols) >= 2:
                for i, col1 in enumerate(date_cols):
                    for col2 in date_cols[i+1:]:
                        validation = self._validate_date_relationship(col1, col2)
                        if validation:
                            cross_field_validation.append(validation)
            
            accuracy["cross_field_validation"] = cross_field_validation
            
            # Value distribution analysis (detect unusual patterns)
            distribution_analysis = []
            for col in self.df.select_dtypes(include=['object']).columns:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                value_counts = series.value_counts()
                
                # Check for suspicious patterns
                suspicious_patterns = []
                
                # Too many identical values
                if len(value_counts) > 0:
                    max_freq = value_counts.iloc[0]
                    if max_freq > len(series) * 0.8 and len(value_counts) > 10:
                        suspicious_patterns.append("dominant_single_value")
                
                # Sequential or pattern-based values
                if self._detect_sequential_pattern(value_counts.index[:10]):
                    suspicious_patterns.append("sequential_pattern")
                
                distribution_analysis.append({
                    "column_name": col,
                    "unique_values": len(value_counts),
                    "most_common_value": value_counts.index[0] if len(value_counts) > 0 else None,
                    "most_common_frequency": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                    "suspicious_patterns": suspicious_patterns,
                    "accuracy_concern_level": "high" if suspicious_patterns else "low"
                })
            
            accuracy["distribution_analysis"] = distribution_analysis
            
            return accuracy
            
        except Exception as e:
            logger.error(f"Error assessing accuracy: {e}")
            return {"error": str(e)}
    
    def detect_anomalies(self) -> Dict[str, Any]:
        """Detect anomalies using various methods"""
        try:
            anomalies = {}
            
            # Statistical anomalies (already covered in accuracy)
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            if SKLEARN_AVAILABLE and len(numeric_cols) > 0:
                # Isolation Forest for multivariate anomaly detection
                numeric_data = self.df[numeric_cols].dropna()
                
                if len(numeric_data) > 10:
                    scaler = StandardScaler()
                    scaled_data = scaler.fit_transform(numeric_data)
                    
                    # Isolation Forest
                    iso_forest = IsolationForest(contamination=0.1, random_state=42)
                    anomaly_labels = iso_forest.fit_predict(scaled_data)
                    
                    anomaly_indices = numeric_data.index[anomaly_labels == -1]
                    
                    anomalies["isolation_forest"] = {
                        "method": "Isolation Forest",
                        "total_records": len(numeric_data),
                        "anomaly_count": len(anomaly_indices),
                        "anomaly_percentage": round(len(anomaly_indices) / len(numeric_data) * 100, 2),
                        "anomalous_record_indices": anomaly_indices.tolist()[:20]  # Limit output
                    }
                    
                    # DBSCAN clustering for density-based anomalies
                    if len(numeric_data) <= 1000:  # Limit for performance
                        dbscan = DBSCAN(eps=0.5, min_samples=5)
                        cluster_labels = dbscan.fit_predict(scaled_data)
                        
                        noise_points = numeric_data.index[cluster_labels == -1]
                        
                        anomalies["dbscan_clustering"] = {
                            "method": "DBSCAN Clustering",
                            "total_records": len(numeric_data),
                            "noise_points": len(noise_points),
                            "noise_percentage": round(len(noise_points) / len(numeric_data) * 100, 2),
                            "clusters_found": len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0),
                            "noise_point_indices": noise_points.tolist()[:20]
                        }
            
            # Text anomalies
            text_anomalies = []
            text_cols = self.df.select_dtypes(include=['object']).columns
            
            for col in text_cols:
                series = self.df[col].dropna().astype(str)
                if len(series) == 0:
                    continue
                
                # Length-based anomalies
                lengths = series.str.len()
                length_mean = lengths.mean()
                length_std = lengths.std()
                
                if length_std > 0:
                    length_outliers = series[abs(lengths - length_mean) > 3 * length_std]
                    
                    text_anomalies.append({
                        "column_name": col,
                        "anomaly_type": "unusual_length",
                        "anomaly_count": len(length_outliers),
                        "anomaly_percentage": round(len(length_outliers) / len(series) * 100, 2),
                        "examples": length_outliers.head(5).tolist()
                    })
                
                # Character pattern anomalies
                # Find values with unusual character patterns
                unusual_patterns = []
                for value in series.sample(min(100, len(series))):  # Sample for performance
                    if self._is_unusual_text_pattern(value, series):
                        unusual_patterns.append(value)
                
                if unusual_patterns:
                    text_anomalies.append({
                        "column_name": col,
                        "anomaly_type": "unusual_pattern",
                        "examples": unusual_patterns[:5]
                    })
            
            anomalies["text_anomalies"] = text_anomalies
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {"error": str(e)}
    
    def profile_data_patterns(self) -> Dict[str, Any]:
        """Profile common data patterns and structures"""
        try:
            patterns = {}
            
            # Pattern detection for each column
            column_patterns = []
            
            for col in self.df.columns:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                col_patterns = {
                    "column_name": col,
                    "data_type": str(series.dtype),
                    "patterns": []
                }
                
                if series.dtype == 'object':
                    # Text pattern analysis
                    text_patterns = self._analyze_text_patterns(series.astype(str))
                    col_patterns["patterns"].extend(text_patterns)
                
                elif pd.api.types.is_numeric_dtype(series):
                    # Numeric pattern analysis
                    numeric_patterns = self._analyze_numeric_patterns(series)
                    col_patterns["patterns"].extend(numeric_patterns)
                
                column_patterns.append(col_patterns)
            
            patterns["column_patterns"] = column_patterns
            
            # Data structure patterns
            structure_patterns = {
                "has_header_row": True,  # Assumed since we're using pandas
                "consistent_column_count": True,  # CSV format ensures this
                "nested_structure": False,  # CSV is flat
                "hierarchical_columns": self._detect_hierarchical_columns(),
                "time_series_structure": self._detect_time_series_structure()
            }
            
            patterns["structure_patterns"] = structure_patterns
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error profiling data patterns: {e}")
            return {"error": str(e)}
    
    def generate_quality_recommendations(self) -> Dict[str, Any]:
        """Generate actionable recommendations for improving data quality"""
        try:
            recommendations = {
                "high_priority": [],
                "medium_priority": [],
                "low_priority": [],
                "data_cleaning_steps": [],
                "validation_rules": []
            }
            
            # Analyze completeness issues
            missing_analysis = self.assess_completeness()
            if "by_column" in missing_analysis:
                for col_info in missing_analysis["by_column"]:
                    if col_info["missing_percentage"] > 20:
                        recommendations["high_priority"].append({
                            "issue": f"High missing data in column '{col_info['column_name']}'",
                            "details": f"{col_info['missing_percentage']:.1f}% missing values",
                            "recommendation": "Consider data imputation, removal, or additional data collection",
                            "category": "completeness"
                        })
                    elif col_info["missing_percentage"] > 5:
                        recommendations["medium_priority"].append({
                            "issue": f"Moderate missing data in column '{col_info['column_name']}'",
                            "details": f"{col_info['missing_percentage']:.1f}% missing values",
                            "recommendation": "Consider data imputation strategies",
                            "category": "completeness"
                        })
            
            # Analyze uniqueness issues
            uniqueness_analysis = self.assess_uniqueness()
            if "by_column" in uniqueness_analysis:
                for col_info in uniqueness_analysis["by_column"]:
                    if col_info["is_likely_identifier"] and col_info["uniqueness_rate"] < 0.95:
                        recommendations["high_priority"].append({
                            "issue": f"Identifier column '{col_info['column_name']}' has duplicates",
                            "details": f"Only {col_info['uniqueness_rate']:.1%} unique values",
                            "recommendation": "Remove or merge duplicate records",
                            "category": "uniqueness"
                        })
            
            # Analyze consistency issues
            consistency_analysis = self.assess_consistency()
            if "data_types" in consistency_analysis:
                for type_info in consistency_analysis["data_types"]:
                    if type_info["consistency_score"] < 0.9:
                        recommendations["medium_priority"].append({
                            "issue": f"Data type inconsistency in column '{type_info['column_name']}'",
                            "details": f"Consistency score: {type_info['consistency_score']:.1%}",
                            "recommendation": type_info["recommendation"],
                            "category": "consistency"
                        })
            
            # Generate data cleaning steps
            recommendations["data_cleaning_steps"] = [
                {
                    "step": 1,
                    "action": "Handle missing values",
                    "methods": ["Remove rows/columns with high missingness", "Impute missing values", "Mark missing as explicit category"]
                },
                {
                    "step": 2,
                    "action": "Remove duplicates",
                    "methods": ["Identify exact duplicates", "Find near-duplicates", "Resolve record conflicts"]
                },
                {
                    "step": 3,
                    "action": "Standardize formats",
                    "methods": ["Normalize text cases", "Standardize date formats", "Clean numeric formats"]
                },
                {
                    "step": 4,
                    "action": "Validate data types",
                    "methods": ["Convert to appropriate types", "Handle type conversion errors", "Validate ranges"]
                }
            ]
            
            # Generate validation rules
            recommendations["validation_rules"] = self._generate_validation_rules()
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {"error": str(e)}
    
    # Helper methods
    def _assess_column_validity(self, series: pd.Series) -> float:
        """Assess validity of a column's values"""
        if len(series) == 0:
            return 1.0
        
        # Basic validity checks
        if pd.api.types.is_numeric_dtype(series):
            # Check for infinite or extremely large values
            invalid_count = sum(np.isinf(series.fillna(0)) | (abs(series.fillna(0)) > 1e15))
        else:
            # For text, check for extremely long or suspicious values
            text_series = series.astype(str)
            invalid_count = sum(text_series.str.len() > 1000)  # Very long text might be invalid
        
        return 1 - (invalid_count / len(series))
    
    def _assess_column_consistency(self, series: pd.Series) -> float:
        """Assess consistency of a column's data types"""
        if len(series) == 0:
            return 1.0
        
        if pd.api.types.is_numeric_dtype(series):
            # All numeric values are considered consistent
            return 1.0
        
        # For object columns, check type consistency
        types = series.apply(type).value_counts()
        dominant_type_ratio = types.iloc[0] / len(series) if len(types) > 0 else 1.0
        
        return dominant_type_ratio
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to quality grade"""
        if score >= 0.9:
            return "Excellent"
        elif score >= 0.8:
            return "Good"
        elif score >= 0.7:
            return "Fair"
        elif score >= 0.6:
            return "Poor"
        else:
            return "Critical"
    
    def _generate_quality_summary(self, score: float) -> str:
        """Generate a summary based on quality score"""
        if score >= 0.9:
            return "Data quality is excellent with minimal issues"
        elif score >= 0.8:
            return "Data quality is good with minor issues to address"
        elif score >= 0.7:
            return "Data quality is fair with several issues requiring attention"
        elif score >= 0.6:
            return "Data quality is poor with significant issues"
        else:
            return "Data quality is critical and requires immediate attention"
    
    def _completeness_level(self, rate: float) -> str:
        """Categorize completeness level"""
        if rate >= 0.95:
            return "excellent"
        elif rate >= 0.90:
            return "good"
        elif rate >= 0.80:
            return "acceptable"
        elif rate >= 0.70:
            return "poor"
        else:
            return "critical"
    
    def _analyze_missing_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in missing data"""
        try:
            patterns = {}
            
            # Missing data correlation
            missing_df = self.df.isnull()
            missing_corr = missing_df.corr()
            
            # Find columns with correlated missingness
            high_corr_pairs = []
            for i, col1 in enumerate(missing_corr.columns):
                for j, col2 in enumerate(missing_corr.columns):
                    if i < j and abs(missing_corr.loc[col1, col2]) > 0.5:
                        high_corr_pairs.append({
                            "column1": col1,
                            "column2": col2,
                            "correlation": round(missing_corr.loc[col1, col2], 3)
                        })
            
            patterns["correlated_missingness"] = high_corr_pairs
            
            # Common missing patterns
            missing_patterns = missing_df.value_counts().head(5)
            patterns["common_patterns"] = [
                {
                    "pattern": list(pattern),
                    "count": int(count),
                    "percentage": round(count / len(self.df) * 100, 2)
                }
                for pattern, count in missing_patterns.items()
            ]
            
            return patterns
            
        except Exception as e:
            logger.warning(f"Could not analyze missing patterns: {e}")
            return {}
    
    def _find_type_inconsistencies(self, series: pd.Series) -> List[Any]:
        """Find values that don't match the expected type"""
        inconsistencies = []
        
        if pd.api.types.is_numeric_dtype(series):
            # For numeric, find non-numeric strings if any
            try:
                pd.to_numeric(series)
            except:
                for val in series.sample(min(10, len(series))):
                    try:
                        pd.to_numeric(val)
                    except:
                        inconsistencies.append(val)
        
        return inconsistencies[:5]  # Limit examples
    
    def _recommend_type_fix(self, series: pd.Series) -> str:
        """Recommend how to fix type inconsistencies"""
        if pd.api.types.is_numeric_dtype(series):
            return "Convert to appropriate numeric type"
        elif pd.api.types.is_string_dtype(series):
            return "Standardize string format"
        else:
            return "Review and convert to consistent type"
    
    def _analyze_text_format_consistency(self, series: pd.Series) -> Optional[Dict[str, Any]]:
        """Analyze format consistency for text columns"""
        if len(series) < 2:
            return None
        
        # Check for common format patterns
        patterns = {
            "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            "phone": r'^[\+]?[1-9][\d\-\(\)\s]{7,15}$',
            "url": r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$',
            "date": r'^\d{4}-\d{2}-\d{2}$|^\d{2}\/\d{2}\/\d{4}$|^\d{2}-\d{2}-\d{4}$'
        }
        
        for pattern_name, pattern in patterns.items():
            matches = series.str.match(pattern, na=False)
            match_rate = matches.mean()
            
            if match_rate > 0.8:  # If most values match a pattern
                return {
                    "detected_format": pattern_name,
                    "format_consistency": round(match_rate, 3),
                    "non_matching_count": int((~matches).sum()),
                    "examples_non_matching": series[~matches].head(3).tolist()
                }
        
        return None
    
    def _analyze_numeric_range_consistency(self, series: pd.Series, column_name: str) -> Dict[str, Any]:
        """Analyze if numeric values fall within expected ranges"""
        analysis = {
            "min_value": float(series.min()),
            "max_value": float(series.max()),
            "range_span": float(series.max() - series.min()),
            "potential_issues": []
        }
        
        # Check for common range issues
        if column_name.lower().find('age') >= 0:
            if series.min() < 0 or series.max() > 150:
                analysis["potential_issues"].append("Age values outside realistic range (0-150)")
        
        elif column_name.lower().find('percentage') >= 0 or column_name.lower().find('percent') >= 0:
            if series.min() < 0 or series.max() > 100:
                analysis["potential_issues"].append("Percentage values outside 0-100 range")
        
        elif column_name.lower().find('price') >= 0 or column_name.lower().find('cost') >= 0:
            if series.min() < 0:
                analysis["potential_issues"].append("Negative price/cost values")
        
        return analysis
    
    def _validate_numeric_ranges(self, series: pd.Series, column_name: str) -> Dict[str, Any]:
        """Validate numeric ranges against business rules"""
        validation = {
            "total_values": len(series),
            "out_of_range_count": 0,
            "out_of_range_percentage": 0.0,
            "validation_rules": []
        }
        
        # Apply business rules based on column name
        out_of_range_mask = pd.Series([False] * len(series), index=series.index)
        
        if 'age' in column_name.lower():
            rule_mask = (series < 0) | (series > 150)
            validation["validation_rules"].append("Age should be between 0 and 150")
            out_of_range_mask |= rule_mask
        
        elif any(word in column_name.lower() for word in ['percentage', 'percent', 'rate']):
            rule_mask = (series < 0) | (series > 100)
            validation["validation_rules"].append("Percentage should be between 0 and 100")
            out_of_range_mask |= rule_mask
        
        elif any(word in column_name.lower() for word in ['price', 'cost', 'amount']):
            rule_mask = series < 0
            validation["validation_rules"].append("Price/cost/amount should be non-negative")
            out_of_range_mask |= rule_mask
        
        validation["out_of_range_count"] = int(out_of_range_mask.sum())
        validation["out_of_range_percentage"] = round(out_of_range_mask.mean() * 100, 2)
        
        return validation
    
    def _assess_uniqueness_quality(self, uniqueness_rate: float, is_identifier: bool) -> str:
        """Assess the quality of uniqueness for a column"""
        if is_identifier:
            if uniqueness_rate >= 0.99:
                return "excellent"
            elif uniqueness_rate >= 0.95:
                return "good"
            else:
                return "poor"
        else:
            if uniqueness_rate >= 0.8:
                return "high_diversity"
            elif uniqueness_rate >= 0.5:
                return "moderate_diversity"
            else:
                return "low_diversity"
    
    def _identify_composite_keys(self) -> List[Dict[str, Any]]:
        """Identify potential composite key combinations"""
        composite_keys = []
        
        # Try combinations of 2-3 columns
        from itertools import combinations
        
        columns = list(self.df.columns)
        
        # Try pairs
        for col_pair in combinations(columns[:min(10, len(columns))], 2):  # Limit for performance
            combined_uniqueness = len(self.df.drop_duplicates(subset=list(col_pair))) / len(self.df)
            if combined_uniqueness > 0.95:
                composite_keys.append({
                    "columns": list(col_pair),
                    "uniqueness_rate": round(combined_uniqueness, 3),
                    "is_potential_key": True
                })
        
        return composite_keys[:5]  # Limit output
    
    def _validate_date_relationship(self, col1: str, col2: str) -> Optional[Dict[str, Any]]:
        """Validate logical relationships between date columns"""
        try:
            date1 = pd.to_datetime(self.df[col1], errors='coerce')
            date2 = pd.to_datetime(self.df[col2], errors='coerce')
            
            valid_mask = ~(date1.isnull() | date2.isnull())
            if valid_mask.sum() < 2:
                return None
            
            # Check if col1 should be before col2 based on names
            if any(word in col1.lower() for word in ['start', 'begin', 'create']) and \
               any(word in col2.lower() for word in ['end', 'finish', 'update', 'modify']):
                violations = (date1[valid_mask] > date2[valid_mask]).sum()
                return {
                    "column1": col1,
                    "column2": col2,
                    "expected_relationship": f"{col1} should be before {col2}",
                    "violations": int(violations),
                    "violation_percentage": round(violations / valid_mask.sum() * 100, 2)
                }
            
        except Exception:
            pass
        
        return None
    
    def _detect_sequential_pattern(self, values: List[Any]) -> bool:
        """Detect if values follow a sequential pattern"""
        try:
            # Convert to string and check for numeric sequences
            str_values = [str(v) for v in values]
            
            # Check for numeric sequences
            try:
                numeric_values = [float(v) for v in str_values]
                if len(numeric_values) >= 3:
                    diffs = [numeric_values[i+1] - numeric_values[i] for i in range(len(numeric_values)-1)]
                    # Check if differences are consistent (arithmetic sequence)
                    return len(set(diffs)) == 1 and diffs[0] != 0
            except:
                pass
            
            # Check for alphabetical sequences
            if len(str_values) >= 3:
                return all(str_values[i] < str_values[i+1] for i in range(len(str_values)-1))
            
        except:
            pass
        
        return False
    
    def _is_unusual_text_pattern(self, value: str, series: pd.Series) -> bool:
        """Check if a text value has an unusual pattern compared to others"""
        # Very basic heuristic - check if length is very different from median
        lengths = series.astype(str).str.len()
        median_length = lengths.median()
        
        return abs(len(value) - median_length) > 3 * lengths.std()
    
    def _analyze_text_patterns(self, series: pd.Series) -> List[Dict[str, Any]]:
        """Analyze patterns in text data"""
        patterns = []
        
        # Length distribution
        lengths = series.str.len()
        patterns.append({
            "pattern_type": "length_distribution",
            "min_length": int(lengths.min()),
            "max_length": int(lengths.max()),
            "avg_length": round(lengths.mean(), 1),
            "length_std": round(lengths.std(), 1)
        })
        
        # Character patterns
        has_numbers = series.str.contains(r'\d', na=False).mean()
        has_special_chars = series.str.contains(r'[^a-zA-Z0-9\s]', na=False).mean()
        all_caps = series.str.isupper().mean()
        all_lower = series.str.islower().mean()
        
        patterns.append({
            "pattern_type": "character_composition",
            "contains_numbers_rate": round(has_numbers, 3),
            "contains_special_chars_rate": round(has_special_chars, 3),
            "all_caps_rate": round(all_caps, 3),
            "all_lower_rate": round(all_lower, 3)
        })
        
        return patterns
    
    def _analyze_numeric_patterns(self, series: pd.Series) -> List[Dict[str, Any]]:
        """Analyze patterns in numeric data"""
        patterns = []
        
        # Distribution characteristics
        patterns.append({
            "pattern_type": "distribution",
            "mean": round(float(series.mean()), 3),
            "median": round(float(series.median()), 3),
            "std": round(float(series.std()), 3),
            "skewness": round(float(series.skew()), 3),
            "kurtosis": round(float(series.kurtosis()), 3)
        })
        
        # Value patterns
        integer_rate = (series == series.astype(int)).mean()
        positive_rate = (series > 0).mean()
        zero_rate = (series == 0).mean()
        
        patterns.append({
            "pattern_type": "value_characteristics",
            "integer_rate": round(integer_rate, 3),
            "positive_rate": round(positive_rate, 3),
            "zero_rate": round(zero_rate, 3)
        })
        
        return patterns
    
    def _detect_hierarchical_columns(self) -> bool:
        """Detect if column names suggest hierarchical structure"""
        column_names = [col.lower() for col in self.df.columns]
        
        # Look for patterns like category/subcategory, level1/level2, etc.
        hierarchical_patterns = ['level', 'category', 'class', 'group', 'type']
        
        for pattern in hierarchical_patterns:
            matching_cols = [col for col in column_names if pattern in col]
            if len(matching_cols) > 1:
                return True
        
        return False
    
    def _detect_time_series_structure(self) -> bool:
        """Detect if data has time series structure"""
        # Look for temporal columns
        temporal_indicators = ['date', 'time', 'timestamp', 'created', 'updated']
        
        for col in self.df.columns:
            if any(indicator in col.lower() for indicator in temporal_indicators):
                return True
        
        return False
    
    def _generate_validation_rules(self) -> List[Dict[str, Any]]:
        """Generate data validation rules based on analysis"""
        rules = []
        
        # Completeness rules
        missing_analysis = self.assess_completeness()
        if "by_column" in missing_analysis:
            for col_info in missing_analysis["by_column"]:
                if col_info["missing_percentage"] < 5:  # Columns with low missing rates
                    rules.append({
                        "rule_type": "completeness",
                        "column": col_info["column_name"],
                        "rule": "required",
                        "description": f"Column should not be empty (currently {col_info['missing_percentage']:.1f}% missing)"
                    })
        
        # Uniqueness rules
        uniqueness_analysis = self.assess_uniqueness()
        if "by_column" in uniqueness_analysis:
            for col_info in uniqueness_analysis["by_column"]:
                if col_info["is_likely_identifier"]:
                    rules.append({
                        "rule_type": "uniqueness",
                        "column": col_info["column_name"],
                        "rule": "unique",
                        "description": f"Column should contain unique values (identifier column)"
                    })
        
        # Format rules based on detected patterns
        for col in self.df.select_dtypes(include=['object']).columns:
            if 'email' in col.lower():
                rules.append({
                    "rule_type": "format",
                    "column": col,
                    "rule": "email_format",
                    "description": "Values should follow valid email format"
                })
            elif any(word in col.lower() for word in ['phone', 'tel']):
                rules.append({
                    "rule_type": "format",
                    "column": col,
                    "rule": "phone_format",
                    "description": "Values should follow valid phone number format"
                })
        
        return rules
    
    def save_assessment(self, output_path: str, assessment: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save data quality assessment to JSON file
        
        Args:
            output_path: Path to save the assessment
            assessment: Assessment results (if None, runs full assessment)
            
        Returns:
            Success status
        """
        try:
            if assessment is None:
                assessment = self.get_full_quality_assessment()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(assessment, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Data quality assessment saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save data quality assessment: {e}")
            return False

# Convenience function for simple usage
def assess_data_quality(file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to perform data quality assessment
    
    Args:
        file_path: Path to CSV file
        output_path: Optional path to save results
        
    Returns:
        Data quality assessment results
    """
    processor = DataQualityProcessor(file_path=file_path)
    assessment = processor.get_full_quality_assessment()
    
    if output_path:
        processor.save_assessment(output_path, assessment)
    
    return assessment