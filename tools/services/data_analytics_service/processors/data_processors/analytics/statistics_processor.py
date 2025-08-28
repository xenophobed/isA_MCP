#!/usr/bin/env python3
"""
Statistics Processor
Advanced statistical analysis tool building on the existing CSV processor infrastructure.
Provides correlation analysis, hypothesis testing, and distribution analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from pathlib import Path
import json

# Statistics libraries
try:
    from scipy import stats
    from scipy.stats import chi2_contingency, pearsonr, spearmanr, kendalltau
    from scipy.stats import normaltest, shapiro, jarque_bera, anderson, kstest
    from scipy.stats import ttest_ind, ttest_1samp, mannwhitneyu, kruskal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. Some statistical tests will be disabled.")

try:
    from ..preprocessors.csv_processor import CSVProcessor
except ImportError:
    try:
        from csv_processor import CSVProcessor
    except ImportError:
        # Fallback - will need to be provided externally
        CSVProcessor = None

logger = logging.getLogger(__name__)

class StatisticsProcessor:
    """
    Advanced statistical analysis processor
    Builds on CSVProcessor for comprehensive statistical analysis
    """
    
    def __init__(self, csv_processor: Optional[CSVProcessor] = None, file_path: Optional[str] = None):
        """
        Initialize statistics processor
        
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
    
    def get_full_statistical_analysis(self) -> Dict[str, Any]:
        """
        Get comprehensive statistical analysis
        
        Returns:
            Complete statistical analysis results
        """
        if self.df is None:
            return {"error": "No data loaded"}
        
        return {
            "basic_statistics": self.calculate_basic_statistics(),
            "correlation_analysis": self.analyze_correlations(),
            "distribution_analysis": self.analyze_distributions(),
            "hypothesis_tests": self.run_hypothesis_tests(),
            "outlier_analysis": self.detect_outliers(),
            "temporal_patterns": self.analyze_temporal_patterns(),
            "categorical_analysis": self.analyze_categorical_variables(),
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "scipy_available": SCIPY_AVAILABLE,
                "data_shape": list(self.df.shape)
            }
        }
    
    def calculate_basic_statistics(self) -> Dict[str, Any]:
        """Calculate basic descriptive statistics"""
        try:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) == 0:
                return {"message": "No numeric columns found"}
            
            basic_stats = {}
            
            # Overall statistics
            description = self.df[numeric_cols].describe()
            basic_stats["descriptive_statistics"] = description.to_dict()
            
            # Additional statistics for each numeric column
            detailed_stats = {}
            for col in numeric_cols:
                series = self.df[col].dropna()
                if len(series) > 0:
                    detailed_stats[col] = {
                        "count": int(series.count()),
                        "mean": float(series.mean()),
                        "median": float(series.median()),
                        "mode": float(series.mode().iloc[0]) if len(series.mode()) > 0 else None,
                        "std": float(series.std()),
                        "var": float(series.var()),
                        "skewness": float(series.skew()),
                        "kurtosis": float(series.kurtosis()),
                        "range": float(series.max() - series.min()),
                        "iqr": float(series.quantile(0.75) - series.quantile(0.25)),
                        "coefficient_of_variation": float(series.std() / series.mean()) if series.mean() != 0 else None
                    }
                    
                    # Quantiles
                    quantiles = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
                    detailed_stats[col]["quantiles"] = {
                        f"q{int(q*100)}": float(series.quantile(q)) for q in quantiles
                    }
            
            basic_stats["detailed_statistics"] = detailed_stats
            return basic_stats
            
        except Exception as e:
            logger.error(f"Error calculating basic statistics: {e}")
            return {"error": str(e)}
    
    def analyze_correlations(self) -> Dict[str, Any]:
        """Analyze correlations between variables"""
        try:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) < 2:
                return {"message": "Need at least 2 numeric columns for correlation analysis"}
            
            correlations = {}
            
            # Pearson correlation matrix
            pearson_corr = self.df[numeric_cols].corr(method='pearson')
            correlations["pearson_correlation_matrix"] = pearson_corr.to_dict()
            
            if SCIPY_AVAILABLE:
                # Spearman correlation matrix  
                spearman_corr = self.df[numeric_cols].corr(method='spearman')
                correlations["spearman_correlation_matrix"] = spearman_corr.to_dict()
                
                # Kendall correlation matrix
                kendall_corr = self.df[numeric_cols].corr(method='kendall')
                correlations["kendall_correlation_matrix"] = kendall_corr.to_dict()
                
                # Detailed pairwise correlations with p-values
                pairwise_correlations = []
                for i, col1 in enumerate(numeric_cols):
                    for j, col2 in enumerate(numeric_cols):
                        if i < j:  # Avoid duplicates
                            data1 = self.df[col1].dropna()
                            data2 = self.df[col2].dropna()
                            
                            # Align data (remove rows where either is NaN)
                            common_idx = data1.index.intersection(data2.index)
                            if len(common_idx) > 3:
                                aligned_data1 = data1[common_idx]
                                aligned_data2 = data2[common_idx]
                                
                                # Pearson correlation with p-value
                                pearson_r, pearson_p = pearsonr(aligned_data1, aligned_data2)
                                
                                # Spearman correlation with p-value
                                spearman_r, spearman_p = spearmanr(aligned_data1, aligned_data2)
                                
                                pairwise_correlations.append({
                                    "variable1": col1,
                                    "variable2": col2,
                                    "sample_size": len(aligned_data1),
                                    "pearson": {
                                        "correlation": float(pearson_r),
                                        "p_value": float(pearson_p),
                                        "significant": pearson_p < 0.05
                                    },
                                    "spearman": {
                                        "correlation": float(spearman_r), 
                                        "p_value": float(spearman_p),
                                        "significant": spearman_p < 0.05
                                    },
                                    "interpretation": self._interpret_correlation(pearson_r)
                                })
                
                correlations["pairwise_analysis"] = pairwise_correlations
            
            # Find strongest correlations
            abs_corr = pearson_corr.abs()
            np.fill_diagonal(abs_corr.values, 0)  # Remove diagonal
            
            if not abs_corr.empty:
                max_corr_idx = abs_corr.stack().idxmax()
                max_corr_value = abs_corr.stack().max()
                
                correlations["strongest_correlation"] = {
                    "variables": list(max_corr_idx),
                    "correlation": float(pearson_corr.loc[max_corr_idx]),
                    "absolute_correlation": float(max_corr_value)
                }
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error analyzing correlations: {e}")
            return {"error": str(e)}
    
    def analyze_distributions(self) -> Dict[str, Any]:
        """Analyze distribution characteristics of variables"""
        try:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) == 0:
                return {"message": "No numeric columns found"}
            
            distributions = {}
            
            for col in numeric_cols:
                series = self.df[col].dropna()
                if len(series) < 8:  # Need minimum data for tests
                    continue
                
                col_analysis = {
                    "sample_size": len(series),
                    "distribution_shape": {
                        "skewness": float(series.skew()),
                        "kurtosis": float(series.kurtosis()),
                        "is_symmetric": abs(series.skew()) < 0.5,
                        "is_normal_kurtosis": abs(series.kurtosis()) < 0.5
                    }
                }
                
                if SCIPY_AVAILABLE and len(series) >= 8:
                    # Normality tests
                    normality_tests = {}
                    
                    # Shapiro-Wilk test (best for small samples < 5000)
                    if len(series) <= 5000:
                        shapiro_stat, shapiro_p = shapiro(series)
                        normality_tests["shapiro_wilk"] = {
                            "statistic": float(shapiro_stat),
                            "p_value": float(shapiro_p),
                            "is_normal": shapiro_p > 0.05
                        }
                    
                    # D'Agostino normality test
                    if len(series) >= 20:
                        dagostino_stat, dagostino_p = normaltest(series)
                        normality_tests["dagostino"] = {
                            "statistic": float(dagostino_stat),
                            "p_value": float(dagostino_p),
                            "is_normal": dagostino_p > 0.05
                        }
                    
                    # Jarque-Bera test
                    if len(series) >= 10:
                        jb_stat, jb_p = jarque_bera(series)
                        normality_tests["jarque_bera"] = {
                            "statistic": float(jb_stat),
                            "p_value": float(jb_p),
                            "is_normal": jb_p > 0.05
                        }
                    
                    # Kolmogorov-Smirnov test against normal distribution
                    normalized_data = (series - series.mean()) / series.std()
                    ks_stat, ks_p = kstest(normalized_data, 'norm')
                    normality_tests["kolmogorov_smirnov"] = {
                        "statistic": float(ks_stat),
                        "p_value": float(ks_p),
                        "is_normal": ks_p > 0.05
                    }
                    
                    col_analysis["normality_tests"] = normality_tests
                    
                    # Overall normality assessment
                    normal_count = sum(1 for test in normality_tests.values() if test.get("is_normal", False))
                    col_analysis["likely_normal"] = normal_count >= len(normality_tests) / 2
                
                # Distribution recommendations
                col_analysis["distribution_recommendations"] = self._recommend_distribution(series)
                
                distributions[col] = col_analysis
            
            return distributions
            
        except Exception as e:
            logger.error(f"Error analyzing distributions: {e}")
            return {"error": str(e)}
    
    def run_hypothesis_tests(self) -> Dict[str, Any]:
        """Run various hypothesis tests"""
        try:
            if not SCIPY_AVAILABLE:
                return {"message": "SciPy not available for hypothesis testing"}
            
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) < 2:
                return {"message": "Need at least 2 numeric columns for hypothesis testing"}
            
            hypothesis_tests = {}
            
            # Two-sample tests between numeric variables
            two_sample_tests = []
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols):
                    if i < j:
                        data1 = self.df[col1].dropna()
                        data2 = self.df[col2].dropna()
                        
                        if len(data1) >= 3 and len(data2) >= 3:
                            # Independent t-test
                            t_stat, t_p = ttest_ind(data1, data2)
                            
                            # Mann-Whitney U test (non-parametric alternative)
                            u_stat, u_p = mannwhitneyu(data1, data2, alternative='two-sided')
                            
                            two_sample_tests.append({
                                "variable1": col1,
                                "variable2": col2,
                                "sample1_size": len(data1),
                                "sample2_size": len(data2),
                                "t_test": {
                                    "statistic": float(t_stat),
                                    "p_value": float(t_p),
                                    "significant_difference": t_p < 0.05
                                },
                                "mann_whitney_u": {
                                    "statistic": float(u_stat),
                                    "p_value": float(u_p),
                                    "significant_difference": u_p < 0.05
                                }
                            })
            
            hypothesis_tests["two_sample_tests"] = two_sample_tests
            
            # One-sample tests (test if mean differs from 0)
            one_sample_tests = []
            for col in numeric_cols:
                data = self.df[col].dropna()
                if len(data) >= 3:
                    # One-sample t-test against 0
                    t_stat, t_p = ttest_1samp(data, 0)
                    
                    one_sample_tests.append({
                        "variable": col,
                        "sample_size": len(data),
                        "sample_mean": float(data.mean()),
                        "t_test_vs_zero": {
                            "statistic": float(t_stat),
                            "p_value": float(t_p),
                            "significantly_different_from_zero": t_p < 0.05
                        }
                    })
            
            hypothesis_tests["one_sample_tests"] = one_sample_tests
            
            return hypothesis_tests
            
        except Exception as e:
            logger.error(f"Error running hypothesis tests: {e}")
            return {"error": str(e)}
    
    def detect_outliers(self) -> Dict[str, Any]:
        """Detect outliers using multiple methods"""
        try:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) == 0:
                return {"message": "No numeric columns found"}
            
            outliers = {}
            
            for col in numeric_cols:
                series = self.df[col].dropna()
                if len(series) < 4:
                    continue
                
                col_outliers = {}
                
                # IQR method
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                iqr_outliers = series[(series < lower_bound) | (series > upper_bound)]
                col_outliers["iqr_method"] = {
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound),
                    "outlier_count": len(iqr_outliers),
                    "outlier_percentage": round(len(iqr_outliers) / len(series) * 100, 2),
                    "outlier_values": iqr_outliers.tolist()[:20]  # Limit to 20 values
                }
                
                # Z-score method
                z_scores = np.abs(stats.zscore(series))
                z_outliers = series[z_scores > 3]
                col_outliers["z_score_method"] = {
                    "threshold": 3.0,
                    "outlier_count": len(z_outliers),
                    "outlier_percentage": round(len(z_outliers) / len(series) * 100, 2),
                    "outlier_values": z_outliers.tolist()[:20]
                }
                
                # Modified Z-score method (using median)
                median = series.median()
                mad = np.median(np.abs(series - median))
                modified_z_scores = 0.6745 * (series - median) / mad if mad != 0 else np.zeros_like(series)
                modified_z_outliers = series[np.abs(modified_z_scores) > 3.5]
                
                col_outliers["modified_z_score_method"] = {
                    "threshold": 3.5,
                    "outlier_count": len(modified_z_outliers),
                    "outlier_percentage": round(len(modified_z_outliers) / len(series) * 100, 2),
                    "outlier_values": modified_z_outliers.tolist()[:20]
                }
                
                # Summary
                col_outliers["summary"] = {
                    "total_values": len(series),
                    "methods_agree_count": len(set(iqr_outliers.index) & set(z_outliers.index) & set(modified_z_outliers.index)),
                    "any_method_outlier_count": len(set(iqr_outliers.index) | set(z_outliers.index) | set(modified_z_outliers.index))
                }
                
                outliers[col] = col_outliers
            
            return outliers
            
        except Exception as e:
            logger.error(f"Error detecting outliers: {e}")
            return {"error": str(e)}
    
    def analyze_temporal_patterns(self) -> Dict[str, Any]:
        """Analyze temporal patterns if date/time columns are present"""
        try:
            temporal_analysis = {}
            
            # Try to identify temporal columns
            temporal_cols = []
            for col in self.df.columns:
                if any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated', 'timestamp']):
                    temporal_cols.append(col)
            
            if not temporal_cols:
                return {"message": "No temporal columns identified"}
            
            for col in temporal_cols:
                try:
                    # Try to parse as datetime
                    datetime_series = pd.to_datetime(self.df[col], errors='coerce')
                    valid_dates = datetime_series.dropna()
                    
                    if len(valid_dates) > 0:
                        col_analysis = {
                            "valid_dates": len(valid_dates),
                            "invalid_dates": len(self.df[col]) - len(valid_dates),
                            "date_range": {
                                "earliest": valid_dates.min().isoformat(),
                                "latest": valid_dates.max().isoformat(),
                                "span_days": (valid_dates.max() - valid_dates.min()).days
                            }
                        }
                        
                        # Temporal patterns
                        if len(valid_dates) > 10:
                            patterns = {}
                            
                            # Day of week patterns
                            day_counts = valid_dates.dt.day_name().value_counts()
                            patterns["day_of_week"] = day_counts.to_dict()
                            
                            # Month patterns
                            month_counts = valid_dates.dt.month_name().value_counts()
                            patterns["month"] = month_counts.to_dict()
                            
                            # Year patterns
                            year_counts = valid_dates.dt.year.value_counts().sort_index()
                            patterns["year"] = year_counts.to_dict()
                            
                            # Hour patterns (if time information available)
                            if valid_dates.dt.hour.nunique() > 1:
                                hour_counts = valid_dates.dt.hour.value_counts().sort_index()
                                patterns["hour"] = hour_counts.to_dict()
                            
                            col_analysis["patterns"] = patterns
                        
                        temporal_analysis[col] = col_analysis
                        
                except Exception as e:
                    logger.warning(f"Could not parse temporal column {col}: {e}")
            
            return temporal_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing temporal patterns: {e}")
            return {"error": str(e)}
    
    def analyze_categorical_variables(self) -> Dict[str, Any]:
        """Analyze categorical variables"""
        try:
            categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns
            
            if len(categorical_cols) == 0:
                return {"message": "No categorical columns found"}
            
            categorical_analysis = {}
            
            for col in categorical_cols:
                series = self.df[col].dropna()
                if len(series) == 0:
                    continue
                
                value_counts = series.value_counts()
                
                col_analysis = {
                    "unique_values": int(series.nunique()),
                    "most_frequent": {
                        "value": value_counts.index[0],
                        "count": int(value_counts.iloc[0]),
                        "percentage": round(value_counts.iloc[0] / len(series) * 100, 2)
                    },
                    "value_distribution": value_counts.head(10).to_dict(),
                    "entropy": float(-sum((p := value_counts / len(series)) * np.log2(p))),
                    "concentration_ratio": round(value_counts.head(3).sum() / len(series), 3)
                }
                
                # Chi-square test against uniform distribution if applicable
                if SCIPY_AVAILABLE and len(value_counts) > 1 and len(value_counts) <= 20:
                    expected = len(series) / len(value_counts)
                    if expected >= 5:  # Chi-square test requirement
                        chi2_stat, chi2_p = stats.chisquare(value_counts)
                        col_analysis["uniformity_test"] = {
                            "chi2_statistic": float(chi2_stat),
                            "p_value": float(chi2_p),
                            "is_uniform": chi2_p > 0.05
                        }
                
                categorical_analysis[col] = col_analysis
            
            # Cross-tabulation analysis for pairs of categorical variables
            if len(categorical_cols) >= 2 and SCIPY_AVAILABLE:
                crosstab_analysis = []
                for i, col1 in enumerate(categorical_cols):
                    for j, col2 in enumerate(categorical_cols):
                        if i < j:
                            try:
                                crosstab = pd.crosstab(self.df[col1], self.df[col2])
                                if crosstab.size > 0:
                                    chi2, p_value, dof, expected = chi2_contingency(crosstab)
                                    
                                    crosstab_analysis.append({
                                        "variable1": col1,
                                        "variable2": col2,
                                        "chi2_statistic": float(chi2),
                                        "p_value": float(p_value),
                                        "degrees_of_freedom": int(dof),
                                        "significant_association": p_value < 0.05,
                                        "cramers_v": float(np.sqrt(chi2 / (crosstab.sum().sum() * min(crosstab.shape[0]-1, crosstab.shape[1]-1))))
                                    })
                            except Exception as e:
                                logger.warning(f"Could not perform chi-square test for {col1} x {col2}: {e}")
                
                categorical_analysis["association_tests"] = crosstab_analysis
            
            return categorical_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing categorical variables: {e}")
            return {"error": str(e)}
    
    def _interpret_correlation(self, correlation: float) -> str:
        """Interpret correlation strength"""
        abs_corr = abs(correlation)
        if abs_corr >= 0.9:
            return "Very strong"
        elif abs_corr >= 0.7:
            return "Strong"
        elif abs_corr >= 0.5:
            return "Moderate"
        elif abs_corr >= 0.3:
            return "Weak"
        else:
            return "Very weak"
    
    def _recommend_distribution(self, series: pd.Series) -> List[str]:
        """Recommend potential distributions based on data characteristics"""
        recommendations = []
        
        skew = series.skew()
        kurtosis = series.kurtosis()
        
        # Normal distribution
        if abs(skew) < 0.5 and abs(kurtosis) < 0.5:
            recommendations.append("Normal")
        
        # Log-normal (if positive values and right-skewed)
        if series.min() > 0 and skew > 1:
            recommendations.append("Log-normal")
        
        # Exponential (if positive values and highly right-skewed)
        if series.min() >= 0 and skew > 2:
            recommendations.append("Exponential")
        
        # Uniform (if low variance and bounded)
        cv = series.std() / series.mean() if series.mean() != 0 else float('inf')
        if cv < 0.3 and abs(kurtosis) > 1:
            recommendations.append("Uniform")
        
        # Beta (if values are between 0 and 1)
        if 0 <= series.min() and series.max() <= 1:
            recommendations.append("Beta")
        
        if not recommendations:
            recommendations.append("Unknown - consider non-parametric methods")
        
        return recommendations
    
    def save_analysis(self, output_path: str, analysis: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save statistical analysis to JSON file
        
        Args:
            output_path: Path to save the analysis
            analysis: Analysis results (if None, runs full analysis)
            
        Returns:
            Success status
        """
        try:
            if analysis is None:
                analysis = self.get_full_statistical_analysis()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Statistical analysis saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save statistical analysis: {e}")
            return False

# Convenience function for simple usage
def analyze_statistics(file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to perform statistical analysis
    
    Args:
        file_path: Path to CSV file
        output_path: Optional path to save results
        
    Returns:
        Statistical analysis results
    """
    processor = StatisticsProcessor(file_path=file_path)
    analysis = processor.get_full_statistical_analysis()
    
    if output_path:
        processor.save_analysis(output_path, analysis)
    
    return analysis