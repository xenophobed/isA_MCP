#!/usr/bin/env python3
"""
Advanced Unsupervised Learning Processor
Comprehensive unsupervised learning with clustering, dimensionality reduction, 
anomaly detection, and pattern discovery
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import logging
import warnings
warnings.filterwarnings('ignore')

# Core unsupervised learning libraries - LAZY LOADING TO PREVENT MUTEX LOCKS
SKLEARN_AVAILABLE = None

def _lazy_import_sklearn():
    """Lazy import sklearn components only when needed"""
    global SKLEARN_AVAILABLE
    if SKLEARN_AVAILABLE is None:
        try:
            from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, SpectralClustering
            from sklearn.cluster import MeanShift, OPTICS, Birch, MiniBatchKMeans
            from sklearn.mixture import GaussianMixture
            from sklearn.decomposition import PCA, TruncatedSVD, FactorAnalysis, FastICA
            from sklearn.decomposition import NMF, LatentDirichletAllocation
            from sklearn.manifold import TSNE, MDS, Isomap, LocallyLinearEmbedding
            from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
            from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
            from sklearn.neighbors import NearestNeighbors
            from sklearn.ensemble import IsolationForest
            from sklearn.svm import OneClassSVM
            from sklearn.covariance import EllipticEnvelope
            from sklearn.neighbors import LocalOutlierFactor
            SKLEARN_AVAILABLE = True
            return {
                'KMeans': KMeans, 'DBSCAN': DBSCAN, 'AgglomerativeClustering': AgglomerativeClustering,
                'SpectralClustering': SpectralClustering, 'MeanShift': MeanShift, 'OPTICS': OPTICS,
                'Birch': Birch, 'MiniBatchKMeans': MiniBatchKMeans, 'GaussianMixture': GaussianMixture,
                'PCA': PCA, 'TruncatedSVD': TruncatedSVD, 'FactorAnalysis': FactorAnalysis,
                'FastICA': FastICA, 'NMF': NMF, 'LatentDirichletAllocation': LatentDirichletAllocation,
                'TSNE': TSNE, 'MDS': MDS, 'Isomap': Isomap, 'LocallyLinearEmbedding': LocallyLinearEmbedding,
                'StandardScaler': StandardScaler, 'MinMaxScaler': MinMaxScaler, 'RobustScaler': RobustScaler,
                'silhouette_score': silhouette_score, 'calinski_harabasz_score': calinski_harabasz_score,
                'davies_bouldin_score': davies_bouldin_score, 'NearestNeighbors': NearestNeighbors,
                'IsolationForest': IsolationForest, 'OneClassSVM': OneClassSVM,
                'EllipticEnvelope': EllipticEnvelope, 'LocalOutlierFactor': LocalOutlierFactor
            }
        except ImportError:
            SKLEARN_AVAILABLE = False
            logging.warning("Scikit-learn not available. Unsupervised learning capabilities will be disabled.")
            return None
    elif SKLEARN_AVAILABLE:
        from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, SpectralClustering
        from sklearn.cluster import MeanShift, OPTICS, Birch, MiniBatchKMeans
        from sklearn.mixture import GaussianMixture
        from sklearn.decomposition import PCA, TruncatedSVD, FactorAnalysis, FastICA
        from sklearn.decomposition import NMF, LatentDirichletAllocation
        from sklearn.manifold import TSNE, MDS, Isomap, LocallyLinearEmbedding
        from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
        from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
        from sklearn.neighbors import NearestNeighbors
        from sklearn.ensemble import IsolationForest
        from sklearn.svm import OneClassSVM
        from sklearn.covariance import EllipticEnvelope
        from sklearn.neighbors import LocalOutlierFactor
        return {
            'KMeans': KMeans, 'DBSCAN': DBSCAN, 'AgglomerativeClustering': AgglomerativeClustering,
            'SpectralClustering': SpectralClustering, 'MeanShift': MeanShift, 'OPTICS': OPTICS,
            'Birch': Birch, 'MiniBatchKMeans': MiniBatchKMeans, 'GaussianMixture': GaussianMixture,
            'PCA': PCA, 'TruncatedSVD': TruncatedSVD, 'FactorAnalysis': FactorAnalysis,
            'FastICA': FastICA, 'NMF': NMF, 'LatentDirichletAllocation': LatentDirichletAllocation,
            'TSNE': TSNE, 'MDS': MDS, 'Isomap': Isomap, 'LocallyLinearEmbedding': LocallyLinearEmbedding,
            'StandardScaler': StandardScaler, 'MinMaxScaler': MinMaxScaler, 'RobustScaler': RobustScaler,
            'silhouette_score': silhouette_score, 'calinski_harabasz_score': calinski_harabasz_score,
            'davies_bouldin_score': davies_bouldin_score, 'NearestNeighbors': NearestNeighbors,
            'IsolationForest': IsolationForest, 'OneClassSVM': OneClassSVM,
            'EllipticEnvelope': EllipticEnvelope, 'LocalOutlierFactor': LocalOutlierFactor
        }
    else:
        return None

# Additional libraries - LAZY LOADING 
UMAP_AVAILABLE = None
HDBSCAN_AVAILABLE = None

def _lazy_import_umap():
    """Lazy import UMAP only when needed"""
    global UMAP_AVAILABLE
    if UMAP_AVAILABLE is None:
        try:
            import umap.umap_ as umap
            UMAP_AVAILABLE = True
            return umap
        except ImportError:
            UMAP_AVAILABLE = False
            logging.warning("UMAP not available. UMAP dimensionality reduction will be disabled.")
            return None
    elif UMAP_AVAILABLE:
        import umap.umap_ as umap
        return umap
    else:
        return None

def _lazy_import_hdbscan():
    """Lazy import HDBSCAN only when needed"""
    global HDBSCAN_AVAILABLE
    if HDBSCAN_AVAILABLE is None:
        try:
            from hdbscan import HDBSCAN
            HDBSCAN_AVAILABLE = True
            return HDBSCAN
        except ImportError:
            HDBSCAN_AVAILABLE = False
            logging.warning("HDBSCAN not available. HDBSCAN clustering will be disabled.")
            return None
    elif HDBSCAN_AVAILABLE:
        from hdbscan import HDBSCAN
        return HDBSCAN
    else:
        return None

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    logging.warning("Matplotlib/Seaborn not available. Plotting capabilities will be limited.")

try:
    from ..preprocessors.csv_processor import CSVProcessor
except ImportError:
    from csv_processor import CSVProcessor

logger = logging.getLogger(__name__)

class UnsupervisedProcessor:
    """
    Advanced unsupervised learning processor
    Provides clustering, dimensionality reduction, anomaly detection, and pattern discovery
    """
    
    def __init__(self, csv_processor: Optional[CSVProcessor] = None, file_path: Optional[str] = None):
        """
        Initialize unsupervised learning processor
        
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
        self.processed_data = None
        self.scalers = {}
        self.clustering_models = {}
        self.reduction_models = {}
        self.anomaly_models = {}
        self.clustering_results = {}
        self.reduction_results = {}
        self.anomaly_results = {}
        
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
    
    def get_unsupervised_analysis(self, target_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get comprehensive unsupervised learning analysis and recommendations
        
        Args:
            target_columns: Specific columns to analyze (all numeric if None)
            
        Returns:
            Complete unsupervised learning analysis and recommendations
        """
        try:
            if self.df is None:
                return {"error": "No data loaded"}
            
            if not SKLEARN_AVAILABLE:
                return {"error": "Scikit-learn not available for unsupervised learning"}
            
            # Prepare data for analysis
            data_prep_result = self._prepare_data_for_unsupervised(target_columns)
            if "error" in data_prep_result:
                return data_prep_result
            
            analysis = {
                "data_preparation": data_prep_result,
                "clustering_recommendations": self._recommend_clustering_methods(data_prep_result),
                "dimensionality_reduction_recommendations": self._recommend_reduction_methods(data_prep_result),
                "anomaly_detection_recommendations": self._recommend_anomaly_methods(data_prep_result),
                "data_characteristics": self._analyze_data_characteristics(data_prep_result),
                "library_availability": {
                    "sklearn": SKLEARN_AVAILABLE,
                    "umap": UMAP_AVAILABLE,
                    "hdbscan": HDBSCAN_AVAILABLE,
                    "plotting": PLOTTING_AVAILABLE
                }
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error getting unsupervised analysis: {e}")
            return {"error": str(e)}
    
    def _prepare_data_for_unsupervised(self, target_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Prepare data for unsupervised learning"""
        try:
            if target_columns:
                # Use specified columns
                missing_cols = [col for col in target_columns if col not in self.df.columns]
                if missing_cols:
                    return {"error": f"Columns not found: {missing_cols}"}
                data = self.df[target_columns].copy()
            else:
                # Use all numeric columns
                data = self.df.select_dtypes(include=[np.number]).copy()
            
            if data.empty:
                return {"error": "No numeric data available for analysis"}
            
            # Handle missing values
            initial_shape = data.shape
            missing_info = {
                "columns_with_missing": data.columns[data.isnull().any()].tolist(),
                "missing_percentage": (data.isnull().sum() / len(data) * 100).to_dict()
            }
            
            # Fill missing values with median (robust to outliers)
            data_filled = data.fillna(data.median())
            
            # Remove columns with too many missing values (>50%)
            high_missing_cols = [col for col, pct in missing_info["missing_percentage"].items() if pct > 50]
            if high_missing_cols:
                data_filled = data_filled.drop(columns=high_missing_cols)
                logger.warning(f"Removed columns with >50% missing values: {high_missing_cols}")
            
            # Remove constant columns
            constant_cols = [col for col in data_filled.columns if data_filled[col].nunique() <= 1]
            if constant_cols:
                data_filled = data_filled.drop(columns=constant_cols)
                logger.warning(f"Removed constant columns: {constant_cols}")
            
            if data_filled.empty:
                return {"error": "No valid data remaining after preprocessing"}
            
            # Store processed data
            self.processed_data = data_filled
            
            return {
                "success": True,
                "original_shape": initial_shape,
                "processed_shape": data_filled.shape,
                "columns_used": data_filled.columns.tolist(),
                "columns_removed": {
                    "high_missing": high_missing_cols,
                    "constant": constant_cols
                },
                "missing_value_info": missing_info,
                "data_summary": {
                    "mean": data_filled.mean().to_dict(),
                    "std": data_filled.std().to_dict(),
                    "min": data_filled.min().to_dict(),
                    "max": data_filled.max().to_dict()
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing data for unsupervised learning: {e}")
            return {"error": str(e)}
    
    def _analyze_data_characteristics(self, data_prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data characteristics for unsupervised learning"""
        try:
            data = self.processed_data
            n_samples, n_features = data.shape
            
            characteristics = {
                "dataset_size": {
                    "samples": n_samples,
                    "features": n_features,
                    "size_category": self._categorize_dataset_size(n_samples, n_features)
                },
                "feature_analysis": {},
                "correlation_analysis": {},
                "distribution_analysis": {},
                "scalability_analysis": {}
            }
            
            # Feature analysis
            feature_ranges = (data.max() - data.min()).to_dict()
            feature_variances = data.var().to_dict()
            
            characteristics["feature_analysis"] = {
                "feature_ranges": feature_ranges,
                "feature_variances": feature_variances,
                "max_range": max(feature_ranges.values()),
                "min_range": min(feature_ranges.values()),
                "range_ratio": max(feature_ranges.values()) / min(feature_ranges.values()) if min(feature_ranges.values()) > 0 else float('inf'),
                "scaling_needed": max(feature_ranges.values()) / min(feature_ranges.values()) > 10 if min(feature_ranges.values()) > 0 else True
            }
            
            # Correlation analysis
            correlation_matrix = data.corr()
            high_correlations = []
            
            for i in range(len(correlation_matrix.columns)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    corr_val = correlation_matrix.iloc[i, j]
                    if abs(corr_val) > 0.8:
                        high_correlations.append({
                            "feature1": correlation_matrix.columns[i],
                            "feature2": correlation_matrix.columns[j],
                            "correlation": float(corr_val)
                        })
            
            characteristics["correlation_analysis"] = {
                "high_correlations": high_correlations,
                "max_correlation": float(correlation_matrix.abs().max().max()),
                "multicollinearity_detected": len(high_correlations) > 0
            }
            
            # Distribution analysis
            skewness = data.skew().to_dict()
            kurtosis = data.kurtosis().to_dict()
            
            characteristics["distribution_analysis"] = {
                "skewness": skewness,
                "kurtosis": kurtosis,
                "highly_skewed_features": [col for col, skew in skewness.items() if abs(skew) > 2],
                "normal_like_features": [col for col, skew in skewness.items() if abs(skew) < 0.5]
            }
            
            # Scalability analysis
            characteristics["scalability_analysis"] = {
                "suitable_for_large_scale": n_samples > 10000,
                "suitable_for_high_dimensional": n_features > 50,
                "curse_of_dimensionality_risk": n_features > n_samples / 10,
                "recommended_preprocessing": self._recommend_preprocessing(characteristics)
            }
            
            return characteristics
            
        except Exception as e:
            logger.error(f"Error analyzing data characteristics: {e}")
            return {"error": str(e)}
    
    def _recommend_clustering_methods(self, data_prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend clustering methods based on data characteristics"""
        try:
            data = self.processed_data
            n_samples, n_features = data.shape
            
            recommendations = {
                "recommended_methods": [],
                "method_details": {},
                "parameter_suggestions": {}
            }
            
            # K-Means (always include as baseline)
            kmeans_rec = {
                "method": "K-Means",
                "suitability": "high",
                "pros": ["Fast", "Scalable", "Well-understood"],
                "cons": ["Assumes spherical clusters", "Requires number of clusters"],
                "best_for": "Spherical clusters, large datasets",
                "priority": "high"
            }
            recommendations["recommended_methods"].append(kmeans_rec)
            recommendations["parameter_suggestions"]["kmeans"] = {
                "n_clusters": list(range(2, min(11, n_samples // 10))),
                "init": "k-means++",
                "random_state": 42
            }
            
            # DBSCAN for density-based clustering
            dbscan_rec = {
                "method": "DBSCAN",
                "suitability": "medium",
                "pros": ["No need to specify clusters", "Finds arbitrary shapes", "Handles noise"],
                "cons": ["Sensitive to parameters", "Struggles with varying densities"],
                "best_for": "Arbitrary cluster shapes, noise detection",
                "priority": "medium"
            }
            recommendations["recommended_methods"].append(dbscan_rec)
            
            # HDBSCAN if available
            if HDBSCAN_AVAILABLE:
                hdbscan_rec = {
                    "method": "HDBSCAN",
                    "suitability": "high",
                    "pros": ["Hierarchical DBSCAN", "Robust to parameters", "Handles varying densities"],
                    "cons": ["Slower than DBSCAN", "Complex parameters"],
                    "best_for": "Hierarchical clustering, varying cluster densities",
                    "priority": "high"
                }
                recommendations["recommended_methods"].append(hdbscan_rec)
            
            # Agglomerative clustering for hierarchical needs
            if n_samples < 10000:  # Memory intensive
                agg_rec = {
                    "method": "Agglomerative Clustering",
                    "suitability": "medium",
                    "pros": ["Hierarchical structure", "Various linkage criteria", "No cluster number assumption"],
                    "cons": ["Memory intensive", "O(n³) complexity"],
                    "best_for": "Hierarchical relationships, small to medium datasets",
                    "priority": "medium"
                }
                recommendations["recommended_methods"].append(agg_rec)
            
            # Gaussian Mixture Models for probabilistic clustering
            if n_samples > 100:
                gmm_rec = {
                    "method": "Gaussian Mixture Model",
                    "suitability": "medium",
                    "pros": ["Probabilistic", "Soft clustering", "Handles overlapping clusters"],
                    "cons": ["Assumes Gaussian distributions", "EM algorithm can get stuck"],
                    "best_for": "Overlapping clusters, probabilistic assignments",
                    "priority": "medium"
                }
                recommendations["recommended_methods"].append(gmm_rec)
            
            # Spectral clustering for non-linear structures
            if n_samples < 5000:  # Computationally expensive
                spectral_rec = {
                    "method": "Spectral Clustering",
                    "suitability": "low",
                    "pros": ["Handles non-linear structures", "Works with similarity matrices"],
                    "cons": ["Computationally expensive", "Sensitive to parameters"],
                    "best_for": "Non-linear cluster structures, graph-based data",
                    "priority": "low"
                }
                recommendations["recommended_methods"].append(spectral_rec)
            
            # Adjust recommendations based on data characteristics
            if n_features > 20:
                # High-dimensional data - recommend dimensionality reduction first
                recommendations["preprocessing_recommendation"] = "Consider dimensionality reduction before clustering"
            
            if n_samples > 50000:
                # Large datasets - recommend scalable methods
                recommendations["scalability_note"] = "Large dataset detected - prioritize scalable methods like MiniBatchKMeans"
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending clustering methods: {e}")
            return {"error": str(e)}
    
    def _recommend_reduction_methods(self, data_prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend dimensionality reduction methods"""
        try:
            data = self.processed_data
            n_samples, n_features = data.shape
            
            recommendations = {
                "recommended_methods": [],
                "method_details": {},
                "target_dimensions": min(10, n_features // 2, n_samples // 10)
            }
            
            # PCA (always include as baseline)
            pca_rec = {
                "method": "PCA",
                "suitability": "high",
                "pros": ["Linear", "Interpretable", "Fast", "Preserves variance"],
                "cons": ["Linear assumptions", "All components needed for reconstruction"],
                "best_for": "Linear relationships, variance preservation",
                "priority": "high"
            }
            recommendations["recommended_methods"].append(pca_rec)
            
            # t-SNE for visualization
            if n_samples < 10000:  # t-SNE is slow on large datasets
                tsne_rec = {
                    "method": "t-SNE",
                    "suitability": "medium",
                    "pros": ["Great for visualization", "Preserves local structure", "Non-linear"],
                    "cons": ["Slow", "Not deterministic", "Mainly for visualization"],
                    "best_for": "2D/3D visualization, local structure preservation",
                    "priority": "medium"
                }
                recommendations["recommended_methods"].append(tsne_rec)
            
            # UMAP if available
            if UMAP_AVAILABLE:
                umap_rec = {
                    "method": "UMAP",
                    "suitability": "high",
                    "pros": ["Fast", "Preserves local and global structure", "Scalable"],
                    "cons": ["Hyperparameter sensitive", "Newer method"],
                    "best_for": "Visualization and general dimensionality reduction",
                    "priority": "high"
                }
                recommendations["recommended_methods"].append(umap_rec)
            
            # Truncated SVD for sparse data
            svd_rec = {
                "method": "Truncated SVD",
                "suitability": "medium",
                "pros": ["Works with sparse data", "Fast", "No centering needed"],
                "cons": ["Linear", "May not preserve variance as well as PCA"],
                "best_for": "Sparse data, text data, large datasets",
                "priority": "medium"
            }
            recommendations["recommended_methods"].append(svd_rec)
            
            # ICA for independent components
            ica_rec = {
                "method": "Independent Component Analysis (ICA)",
                "suitability": "low",
                "pros": ["Finds independent sources", "Good for signal separation"],
                "cons": ["Assumes independence", "Sensitive to preprocessing"],
                "best_for": "Signal separation, independent source identification",
                "priority": "low"
            }
            recommendations["recommended_methods"].append(ica_rec)
            
            # Factor Analysis for latent factors
            fa_rec = {
                "method": "Factor Analysis",
                "suitability": "medium",
                "pros": ["Probabilistic", "Identifies latent factors", "Handles noise"],
                "cons": ["Assumes Gaussian factors", "More complex than PCA"],
                "best_for": "Latent factor identification, noisy data",
                "priority": "medium"
            }
            recommendations["recommended_methods"].append(fa_rec)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending reduction methods: {e}")
            return {"error": str(e)}
    
    def _recommend_anomaly_methods(self, data_prep_result: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend anomaly detection methods"""
        try:
            data = self.processed_data
            n_samples, n_features = data.shape
            
            recommendations = {
                "recommended_methods": [],
                "contamination_estimates": [0.01, 0.05, 0.1],  # Common contamination rates
                "method_details": {}
            }
            
            # Isolation Forest (good general purpose method)
            iforest_rec = {
                "method": "Isolation Forest",
                "suitability": "high",
                "pros": ["Fast", "Scalable", "No assumptions about distribution"],
                "cons": ["May struggle with very high dimensions", "Random"],
                "best_for": "General anomaly detection, large datasets",
                "priority": "high"
            }
            recommendations["recommended_methods"].append(iforest_rec)
            
            # Local Outlier Factor
            if n_samples < 10000:  # Memory intensive
                lof_rec = {
                    "method": "Local Outlier Factor (LOF)",
                    "suitability": "medium",
                    "pros": ["Considers local density", "Good for varying densities"],
                    "cons": ["Memory intensive", "Sensitive to parameters"],
                    "best_for": "Local anomalies, varying cluster densities",
                    "priority": "medium"
                }
                recommendations["recommended_methods"].append(lof_rec)
            
            # One-Class SVM
            if n_samples < 5000:  # Computationally expensive
                ocsvm_rec = {
                    "method": "One-Class SVM",
                    "suitability": "medium",
                    "pros": ["Flexible kernel methods", "Robust"],
                    "cons": ["Computationally expensive", "Parameter tuning needed"],
                    "best_for": "Non-linear boundaries, robust detection",
                    "priority": "medium"
                }
                recommendations["recommended_methods"].append(ocsvm_rec)
            
            # Elliptic Envelope (assumes Gaussian)
            elliptic_rec = {
                "method": "Elliptic Envelope",
                "suitability": "low",
                "pros": ["Fast", "Robust covariance estimation"],
                "cons": ["Assumes Gaussian distribution", "May not work with multimodal data"],
                "best_for": "Gaussian-distributed data, covariance-based outliers",
                "priority": "low"
            }
            recommendations["recommended_methods"].append(elliptic_rec)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending anomaly methods: {e}")
            return {"error": str(e)}
    
    def perform_clustering_analysis(self, methods: List[str] = None, 
                                  n_clusters_range: Tuple[int, int] = (2, 10)) -> Dict[str, Any]:
        """
        Perform comprehensive clustering analysis
        
        Args:
            methods: List of clustering methods to try
            n_clusters_range: Range of cluster numbers to try (for applicable methods)
            
        Returns:
            Clustering analysis results
        """
        try:
            if self.processed_data is None:
                return {"error": "No processed data. Run get_unsupervised_analysis first."}
            
            if methods is None:
                methods = ["kmeans", "dbscan", "agglomerative", "gaussian_mixture"]
                if HDBSCAN_AVAILABLE:
                    methods.append("hdbscan")
            
            # Scale data for clustering
            scaler = StandardScaler()
            data_scaled = scaler.fit_transform(self.processed_data)
            self.scalers["clustering"] = scaler
            
            clustering_results = {
                "methods_tested": methods,
                "results": {},
                "best_method": None,
                "evaluation_metrics": {},
                "recommendations": []
            }
            
            best_score = -1
            best_method = None
            
            for method in methods:
                try:
                    logger.info(f"Testing clustering method: {method}")
                    method_results = self._perform_single_clustering(data_scaled, method, n_clusters_range)
                    clustering_results["results"][method] = method_results
                    
                    # Track best method based on silhouette score
                    if method_results.get("best_silhouette_score", -1) > best_score:
                        best_score = method_results["best_silhouette_score"]
                        best_method = method
                        
                except Exception as e:
                    logger.warning(f"Clustering method {method} failed: {e}")
                    clustering_results["results"][method] = {"error": str(e)}
            
            clustering_results["best_method"] = best_method
            clustering_results["evaluation_metrics"] = self._evaluate_clustering_results(clustering_results["results"])
            clustering_results["recommendations"] = self._generate_clustering_recommendations(clustering_results)
            
            # Store results
            self.clustering_results = clustering_results
            
            return clustering_results
            
        except Exception as e:
            logger.error(f"Error in clustering analysis: {e}")
            return {"error": str(e)}
    
    def perform_dimensionality_reduction(self, methods: List[str] = None,
                                       target_dimensions: int = None) -> Dict[str, Any]:
        """
        Perform dimensionality reduction analysis
        
        Args:
            methods: List of reduction methods to try
            target_dimensions: Target number of dimensions
            
        Returns:
            Dimensionality reduction results
        """
        try:
            if self.processed_data is None:
                return {"error": "No processed data. Run get_unsupervised_analysis first."}
            
            if methods is None:
                methods = ["pca", "tsne", "truncated_svd"]
                if UMAP_AVAILABLE:
                    methods.append("umap")
            
            if target_dimensions is None:
                target_dimensions = min(10, self.processed_data.shape[1] // 2)
            
            # Scale data for dimensionality reduction
            scaler = StandardScaler()
            data_scaled = scaler.fit_transform(self.processed_data)
            self.scalers["reduction"] = scaler
            
            reduction_results = {
                "methods_tested": methods,
                "target_dimensions": target_dimensions,
                "results": {},
                "comparison": {},
                "recommendations": []
            }
            
            for method in methods:
                try:
                    logger.info(f"Testing reduction method: {method}")
                    method_results = self._perform_single_reduction(data_scaled, method, target_dimensions)
                    reduction_results["results"][method] = method_results
                    
                except Exception as e:
                    logger.warning(f"Reduction method {method} failed: {e}")
                    reduction_results["results"][method] = {"error": str(e)}
            
            # Compare methods
            reduction_results["comparison"] = self._compare_reduction_methods(reduction_results["results"])
            reduction_results["recommendations"] = self._generate_reduction_recommendations(reduction_results)
            
            # Store results
            self.reduction_results = reduction_results
            
            return reduction_results
            
        except Exception as e:
            logger.error(f"Error in dimensionality reduction: {e}")
            return {"error": str(e)}
    
    def perform_anomaly_detection(self, methods: List[str] = None,
                                contamination: float = 0.1) -> Dict[str, Any]:
        """
        Perform anomaly detection analysis
        
        Args:
            methods: List of anomaly detection methods to try
            contamination: Expected fraction of anomalies
            
        Returns:
            Anomaly detection results
        """
        try:
            if self.processed_data is None:
                return {"error": "No processed data. Run get_unsupervised_analysis first."}
            
            if methods is None:
                methods = ["isolation_forest", "lof", "one_class_svm", "elliptic_envelope"]
            
            # Scale data for anomaly detection
            scaler = RobustScaler()  # Robust to outliers
            data_scaled = scaler.fit_transform(self.processed_data)
            self.scalers["anomaly"] = scaler
            
            anomaly_results = {
                "methods_tested": methods,
                "contamination": contamination,
                "results": {},
                "consensus_anomalies": [],
                "summary": {},
                "recommendations": []
            }
            
            all_anomalies = {}
            
            for method in methods:
                try:
                    logger.info(f"Testing anomaly detection method: {method}")
                    method_results = self._perform_single_anomaly_detection(data_scaled, method, contamination)
                    anomaly_results["results"][method] = method_results
                    
                    # Collect anomaly indices
                    if "anomaly_indices" in method_results:
                        all_anomalies[method] = set(method_results["anomaly_indices"])
                        
                except Exception as e:
                    logger.warning(f"Anomaly detection method {method} failed: {e}")
                    anomaly_results["results"][method] = {"error": str(e)}
            
            # Find consensus anomalies (detected by multiple methods)
            if len(all_anomalies) > 1:
                consensus = self._find_consensus_anomalies(all_anomalies)
                anomaly_results["consensus_anomalies"] = consensus
            
            # Generate summary
            anomaly_results["summary"] = self._summarize_anomaly_results(anomaly_results)
            anomaly_results["recommendations"] = self._generate_anomaly_recommendations(anomaly_results)
            
            # Store results
            self.anomaly_results = anomaly_results
            
            return anomaly_results
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return {"error": str(e)}
    
    def comprehensive_unsupervised_analysis(self, target_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Perform comprehensive unsupervised learning analysis
        
        Args:
            target_columns: Specific columns to analyze
            
        Returns:
            Complete unsupervised learning results
        """
        try:
            comprehensive_results = {
                "data_analysis": {},
                "clustering_analysis": {},
                "dimensionality_reduction": {},
                "anomaly_detection": {},
                "pattern_insights": {},
                "recommendations": []
            }
            
            # 1. Initial data analysis
            logger.info("Performing initial unsupervised data analysis...")
            data_analysis = self.get_unsupervised_analysis(target_columns)
            comprehensive_results["data_analysis"] = data_analysis
            
            if "error" in data_analysis:
                return comprehensive_results
            
            # 2. Clustering analysis
            logger.info("Performing clustering analysis...")
            clustering_results = self.perform_clustering_analysis()
            comprehensive_results["clustering_analysis"] = clustering_results
            
            # 3. Dimensionality reduction
            logger.info("Performing dimensionality reduction...")
            reduction_results = self.perform_dimensionality_reduction()
            comprehensive_results["dimensionality_reduction"] = reduction_results
            
            # 4. Anomaly detection
            logger.info("Performing anomaly detection...")
            anomaly_results = self.perform_anomaly_detection()
            comprehensive_results["anomaly_detection"] = anomaly_results
            
            # 5. Generate pattern insights
            logger.info("Generating pattern insights...")
            pattern_insights = self._generate_pattern_insights(comprehensive_results)
            comprehensive_results["pattern_insights"] = pattern_insights
            
            # 6. Overall recommendations
            recommendations = self._generate_comprehensive_recommendations(comprehensive_results)
            comprehensive_results["recommendations"] = recommendations
            
            return comprehensive_results
            
        except Exception as e:
            logger.error(f"Error in comprehensive unsupervised analysis: {e}")
            return {"error": str(e)}
    
    # Helper methods for specific algorithms
    
    def _perform_single_clustering(self, data: np.ndarray, method: str, 
                                 n_clusters_range: Tuple[int, int]) -> Dict[str, Any]:
        """Perform clustering with a single method"""
        try:
            results = {
                "method": method,
                "best_silhouette_score": -1,
                "best_n_clusters": None,
                "best_labels": None,
                "all_results": []
            }
            
            if method == "kmeans":
                for n_clusters in range(n_clusters_range[0], n_clusters_range[1] + 1):
                    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    labels = model.fit_predict(data)
                    
                    if len(set(labels)) > 1:  # More than one cluster
                        silhouette = silhouette_score(data, labels)
                        
                        result = {
                            "n_clusters": n_clusters,
                            "silhouette_score": float(silhouette),
                            "inertia": float(model.inertia_),
                            "labels": labels.tolist()
                        }
                        results["all_results"].append(result)
                        
                        if silhouette > results["best_silhouette_score"]:
                            results["best_silhouette_score"] = silhouette
                            results["best_n_clusters"] = n_clusters
                            results["best_labels"] = labels
                
                # Store best model
                if results["best_n_clusters"]:
                    best_model = KMeans(n_clusters=results["best_n_clusters"], random_state=42)
                    best_model.fit(data)
                    self.clustering_models[f"{method}_best"] = best_model
            
            elif method == "dbscan":
                # Try different eps values
                eps_values = [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]
                
                for eps in eps_values:
                    model = DBSCAN(eps=eps, min_samples=5)
                    labels = model.fit_predict(data)
                    
                    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                    if n_clusters > 1:
                        try:
                            silhouette = silhouette_score(data, labels)
                            
                            result = {
                                "eps": eps,
                                "n_clusters": n_clusters,
                                "silhouette_score": float(silhouette),
                                "n_noise": int(list(labels).count(-1)),
                                "labels": labels.tolist()
                            }
                            results["all_results"].append(result)
                            
                            if silhouette > results["best_silhouette_score"]:
                                results["best_silhouette_score"] = silhouette
                                results["best_n_clusters"] = n_clusters
                                results["best_labels"] = labels
                                
                        except ValueError:
                            # All points in one cluster
                            pass
            
            elif method == "hdbscan" and HDBSCAN_AVAILABLE:
                min_cluster_sizes = [5, 10, 15, 20]
                
                for min_cluster_size in min_cluster_sizes:
                    model = HDBSCAN(min_cluster_size=min_cluster_size)
                    labels = model.fit_predict(data)
                    
                    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                    if n_clusters > 1:
                        try:
                            silhouette = silhouette_score(data, labels)
                            
                            result = {
                                "min_cluster_size": min_cluster_size,
                                "n_clusters": n_clusters,
                                "silhouette_score": float(silhouette),
                                "n_noise": int(list(labels).count(-1)),
                                "labels": labels.tolist()
                            }
                            results["all_results"].append(result)
                            
                            if silhouette > results["best_silhouette_score"]:
                                results["best_silhouette_score"] = silhouette
                                results["best_n_clusters"] = n_clusters
                                results["best_labels"] = labels
                                
                        except ValueError:
                            pass
            
            elif method == "agglomerative":
                for n_clusters in range(n_clusters_range[0], n_clusters_range[1] + 1):
                    model = AgglomerativeClustering(n_clusters=n_clusters)
                    labels = model.fit_predict(data)
                    
                    silhouette = silhouette_score(data, labels)
                    
                    result = {
                        "n_clusters": n_clusters,
                        "silhouette_score": float(silhouette),
                        "labels": labels.tolist()
                    }
                    results["all_results"].append(result)
                    
                    if silhouette > results["best_silhouette_score"]:
                        results["best_silhouette_score"] = silhouette
                        results["best_n_clusters"] = n_clusters
                        results["best_labels"] = labels
            
            elif method == "gaussian_mixture":
                for n_components in range(n_clusters_range[0], n_clusters_range[1] + 1):
                    model = GaussianMixture(n_components=n_components, random_state=42)
                    model.fit(data)
                    labels = model.predict(data)
                    
                    silhouette = silhouette_score(data, labels)
                    
                    result = {
                        "n_components": n_components,
                        "silhouette_score": float(silhouette),
                        "aic": float(model.aic(data)),
                        "bic": float(model.bic(data)),
                        "labels": labels.tolist()
                    }
                    results["all_results"].append(result)
                    
                    if silhouette > results["best_silhouette_score"]:
                        results["best_silhouette_score"] = silhouette
                        results["best_n_clusters"] = n_components
                        results["best_labels"] = labels
            
            return results
            
        except Exception as e:
            logger.error(f"Error in {method} clustering: {e}")
            return {"error": str(e)}
    
    def _perform_single_reduction(self, data: np.ndarray, method: str, 
                                target_dimensions: int) -> Dict[str, Any]:
        """Perform dimensionality reduction with a single method"""
        try:
            results = {
                "method": method,
                "target_dimensions": target_dimensions,
                "original_dimensions": data.shape[1],
                "transformed_data": None,
                "variance_explained": None,
                "metadata": {}
            }
            
            if method == "pca":
                model = PCA(n_components=target_dimensions, random_state=42)
                transformed = model.fit_transform(data)
                
                results["transformed_data"] = transformed.tolist()
                results["variance_explained"] = model.explained_variance_ratio_.tolist()
                results["cumulative_variance"] = np.cumsum(model.explained_variance_ratio_).tolist()
                results["metadata"] = {
                    "total_variance_explained": float(np.sum(model.explained_variance_ratio_)),
                    "components": model.components_.tolist()
                }
                
                self.reduction_models[f"{method}"] = model
            
            elif method == "tsne":
                # t-SNE typically reduces to 2D or 3D
                n_components = min(target_dimensions, 3)
                model = TSNE(n_components=n_components, random_state=42, perplexity=min(30, data.shape[0]-1))
                transformed = model.fit_transform(data)
                
                results["transformed_data"] = transformed.tolist()
                results["target_dimensions"] = n_components
                results["metadata"] = {
                    "kl_divergence": float(model.kl_divergence_),
                    "n_iter": int(model.n_iter_)
                }
            
            elif method == "umap" and UMAP_AVAILABLE:
                n_components = min(target_dimensions, data.shape[1])
                model = umap.UMAP(n_components=n_components, random_state=42)
                transformed = model.fit_transform(data)
                
                results["transformed_data"] = transformed.tolist()
                results["metadata"] = {
                    "n_neighbors": model.n_neighbors,
                    "min_dist": model.min_dist
                }
                
                self.reduction_models[f"{method}"] = model
            
            elif method == "truncated_svd":
                model = TruncatedSVD(n_components=target_dimensions, random_state=42)
                transformed = model.fit_transform(data)
                
                results["transformed_data"] = transformed.tolist()
                results["variance_explained"] = model.explained_variance_ratio_.tolist()
                results["cumulative_variance"] = np.cumsum(model.explained_variance_ratio_).tolist()
                results["metadata"] = {
                    "total_variance_explained": float(np.sum(model.explained_variance_ratio_))
                }
                
                self.reduction_models[f"{method}"] = model
            
            return results
            
        except Exception as e:
            logger.error(f"Error in {method} reduction: {e}")
            return {"error": str(e)}
    
    def _perform_single_anomaly_detection(self, data: np.ndarray, method: str,
                                        contamination: float) -> Dict[str, Any]:
        """Perform anomaly detection with a single method"""
        try:
            results = {
                "method": method,
                "contamination": contamination,
                "n_anomalies": 0,
                "anomaly_indices": [],
                "anomaly_scores": None,
                "metadata": {}
            }
            
            if method == "isolation_forest":
                model = IsolationForest(contamination=contamination, random_state=42)
                predictions = model.fit_predict(data)
                scores = model.score_samples(data)
                
                anomaly_indices = np.where(predictions == -1)[0]
                results["n_anomalies"] = len(anomaly_indices)
                results["anomaly_indices"] = anomaly_indices.tolist()
                results["anomaly_scores"] = scores.tolist()
                results["metadata"] = {
                    "n_estimators": model.n_estimators,
                    "max_samples": model.max_samples
                }
                
                self.anomaly_models[f"{method}"] = model
            
            elif method == "lof":
                n_neighbors = min(20, data.shape[0] - 1)
                model = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
                predictions = model.fit_predict(data)
                scores = model.negative_outlier_factor_
                
                anomaly_indices = np.where(predictions == -1)[0]
                results["n_anomalies"] = len(anomaly_indices)
                results["anomaly_indices"] = anomaly_indices.tolist()
                results["anomaly_scores"] = scores.tolist()
                results["metadata"] = {
                    "n_neighbors": n_neighbors
                }
            
            elif method == "one_class_svm":
                model = OneClassSVM(nu=contamination, gamma='auto')
                predictions = model.fit_predict(data)
                scores = model.score_samples(data)
                
                anomaly_indices = np.where(predictions == -1)[0]
                results["n_anomalies"] = len(anomaly_indices)
                results["anomaly_indices"] = anomaly_indices.tolist()
                results["anomaly_scores"] = scores.tolist()
                results["metadata"] = {
                    "kernel": model.kernel,
                    "nu": model.nu
                }
                
                self.anomaly_models[f"{method}"] = model
            
            elif method == "elliptic_envelope":
                model = EllipticEnvelope(contamination=contamination, random_state=42)
                predictions = model.fit_predict(data)
                scores = model.score_samples(data)
                
                anomaly_indices = np.where(predictions == -1)[0]
                results["n_anomalies"] = len(anomaly_indices)
                results["anomaly_indices"] = anomaly_indices.tolist()
                results["anomaly_scores"] = scores.tolist()
                results["metadata"] = {
                    "support_fraction": model.support_fraction_
                }
                
                self.anomaly_models[f"{method}"] = model
            
            return results
            
        except Exception as e:
            logger.error(f"Error in {method} anomaly detection: {e}")
            return {"error": str(e)}
    
    # Additional helper methods would continue...
    # (Due to length constraints, including key methods only)
    
    def _categorize_dataset_size(self, n_samples: int, n_features: int) -> str:
        """Categorize dataset size"""
        if n_samples < 1000:
            return "small"
        elif n_samples < 10000:
            return "medium"
        elif n_samples < 100000:
            return "large"
        else:
            return "very_large"
    
    def _recommend_preprocessing(self, characteristics: Dict[str, Any]) -> List[str]:
        """Recommend preprocessing steps"""
        recommendations = []
        
        if characteristics["feature_analysis"]["scaling_needed"]:
            recommendations.append("Feature scaling (StandardScaler or MinMaxScaler)")
        
        if characteristics["correlation_analysis"]["multicollinearity_detected"]:
            recommendations.append("Consider removing highly correlated features")
        
        if characteristics["distribution_analysis"]["highly_skewed_features"]:
            recommendations.append("Consider log transformation for skewed features")
        
        if characteristics["scalability_analysis"]["curse_of_dimensionality_risk"]:
            recommendations.append("Dimensionality reduction strongly recommended")
        
        return recommendations
    
    def _evaluate_clustering_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate and compare clustering results"""
        evaluation = {
            "method_comparison": [],
            "best_overall": None
        }
        
        for method, result in results.items():
            if "error" not in result and result.get("best_silhouette_score") is not None:
                evaluation["method_comparison"].append({
                    "method": method,
                    "silhouette_score": result["best_silhouette_score"],
                    "n_clusters": result.get("best_n_clusters")
                })
        
        # Sort by silhouette score
        evaluation["method_comparison"].sort(key=lambda x: x["silhouette_score"], reverse=True)
        
        if evaluation["method_comparison"]:
            evaluation["best_overall"] = evaluation["method_comparison"][0]["method"]
        
        return evaluation
    
    def _compare_reduction_methods(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare dimensionality reduction methods"""
        comparison = {
            "variance_preservation": {},
            "computational_efficiency": {},
            "recommendation": None
        }
        
        for method, result in results.items():
            if "error" not in result:
                if "variance_explained" in result:
                    total_variance = result["metadata"].get("total_variance_explained", 0)
                    comparison["variance_preservation"][method] = total_variance
        
        # Recommend method with best variance preservation
        if comparison["variance_preservation"]:
            best_method = max(comparison["variance_preservation"], 
                            key=comparison["variance_preservation"].get)
            comparison["recommendation"] = best_method
        
        return comparison
    
    def _find_consensus_anomalies(self, all_anomalies: Dict[str, set]) -> List[int]:
        """Find anomalies detected by multiple methods"""
        if len(all_anomalies) < 2:
            return []
        
        # Find intersection of anomalies detected by at least 2 methods
        consensus = set()
        methods = list(all_anomalies.keys())
        
        for i in range(len(methods)):
            for j in range(i + 1, len(methods)):
                consensus.update(all_anomalies[methods[i]] & all_anomalies[methods[j]])
        
        return sorted(list(consensus))
    
    def _generate_pattern_insights(self, comprehensive_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights about discovered patterns"""
        insights = {
            "clustering_insights": [],
            "dimensionality_insights": [],
            "anomaly_insights": [],
            "overall_patterns": []
        }
        
        # Clustering insights
        clustering_results = comprehensive_results.get("clustering_analysis", {})
        best_method = clustering_results.get("best_method")
        
        if best_method:
            insights["clustering_insights"].append(
                f"Best clustering method: {best_method} with optimal cluster structure detected"
            )
        
        # Dimensionality insights
        reduction_results = comprehensive_results.get("dimensionality_reduction", {})
        if "comparison" in reduction_results:
            recommended_method = reduction_results["comparison"].get("recommendation")
            if recommended_method:
                insights["dimensionality_insights"].append(
                    f"Recommended dimensionality reduction: {recommended_method}"
                )
        
        # Anomaly insights
        anomaly_results = comprehensive_results.get("anomaly_detection", {})
        consensus_anomalies = anomaly_results.get("consensus_anomalies", [])
        
        if consensus_anomalies:
            insights["anomaly_insights"].append(
                f"Found {len(consensus_anomalies)} consensus anomalies detected by multiple methods"
            )
        
        return insights
    
    def _generate_clustering_recommendations(self, clustering_results: Dict[str, Any]) -> List[str]:
        """Generate clustering-specific recommendations"""
        recommendations = []
        
        best_method = clustering_results.get("best_method")
        if best_method:
            recommendations.append(f"Use {best_method} for clustering this dataset")
        
        evaluation = clustering_results.get("evaluation_metrics", {})
        comparison = evaluation.get("method_comparison", [])
        
        if comparison and len(comparison) > 1:
            best_score = comparison[0]["silhouette_score"]
            second_score = comparison[1]["silhouette_score"]
            
            if best_score - second_score < 0.1:
                recommendations.append("Multiple methods show similar performance - consider ensemble approach")
        
        return recommendations
    
    def _generate_reduction_recommendations(self, reduction_results: Dict[str, Any]) -> List[str]:
        """Generate dimensionality reduction recommendations"""
        recommendations = []
        
        comparison = reduction_results.get("comparison", {})
        recommended_method = comparison.get("recommendation")
        
        if recommended_method:
            recommendations.append(f"Use {recommended_method} for dimensionality reduction")
        
        # Check variance preservation
        variance_preservation = comparison.get("variance_preservation", {})
        if variance_preservation:
            best_variance = max(variance_preservation.values())
            if best_variance < 0.8:
                recommendations.append("Consider using more components to preserve more variance")
        
        return recommendations
    
    def _generate_anomaly_recommendations(self, anomaly_results: Dict[str, Any]) -> List[str]:
        """Generate anomaly detection recommendations"""
        recommendations = []
        
        consensus_anomalies = anomaly_results.get("consensus_anomalies", [])
        
        if consensus_anomalies:
            recommendations.append(f"Investigate {len(consensus_anomalies)} consensus anomalies")
        
        # Check if methods agree
        results = anomaly_results.get("results", {})
        n_anomalies_per_method = [
            result.get("n_anomalies", 0) for result in results.values() 
            if "error" not in result
        ]
        
        if n_anomalies_per_method and max(n_anomalies_per_method) - min(n_anomalies_per_method) > len(consensus_anomalies) * 2:
            recommendations.append("Methods show significant disagreement - consider adjusting contamination parameter")
        
        return recommendations
    
    def _generate_comprehensive_recommendations(self, comprehensive_results: Dict[str, Any]) -> List[str]:
        """Generate overall recommendations"""
        recommendations = []
        
        # Combine specific recommendations
        for analysis_type in ["clustering_analysis", "dimensionality_reduction", "anomaly_detection"]:
            analysis_results = comprehensive_results.get(analysis_type, {})
            method_recommendations = analysis_results.get("recommendations", [])
            recommendations.extend(method_recommendations)
        
        # Add high-level recommendations
        data_analysis = comprehensive_results.get("data_analysis", {})
        if "data_characteristics" in data_analysis:
            characteristics = data_analysis["data_characteristics"]
            
            if characteristics.get("scalability_analysis", {}).get("curse_of_dimensionality_risk"):
                recommendations.append("High dimensionality detected - prioritize dimensionality reduction")
            
            if characteristics.get("correlation_analysis", {}).get("multicollinearity_detected"):
                recommendations.append("Multicollinearity detected - consider feature selection")
        
        return recommendations
    
    def _summarize_anomaly_results(self, anomaly_results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize anomaly detection results"""
        summary = {
            "total_methods": len(anomaly_results["results"]),
            "successful_methods": 0,
            "average_anomalies_detected": 0,
            "consensus_strength": 0
        }
        
        successful_results = [
            result for result in anomaly_results["results"].values() 
            if "error" not in result
        ]
        
        summary["successful_methods"] = len(successful_results)
        
        if successful_results:
            n_anomalies_list = [result["n_anomalies"] for result in successful_results]
            summary["average_anomalies_detected"] = np.mean(n_anomalies_list)
            
            # Consensus strength
            consensus_anomalies = anomaly_results.get("consensus_anomalies", [])
            if n_anomalies_list:
                summary["consensus_strength"] = len(consensus_anomalies) / max(n_anomalies_list) if max(n_anomalies_list) > 0 else 0
        
        return summary
    
    def get_model_results(self, analysis_type: Optional[str] = None) -> Dict[str, Any]:
        """Get results for specific analysis type or all analyses"""
        if analysis_type == "clustering":
            return self.clustering_results
        elif analysis_type == "reduction":
            return self.reduction_results
        elif analysis_type == "anomaly":
            return self.anomaly_results
        else:
            return {
                "clustering": self.clustering_results,
                "reduction": self.reduction_results,
                "anomaly": self.anomaly_results,
                "models": {
                    "clustering_models": list(self.clustering_models.keys()),
                    "reduction_models": list(self.reduction_models.keys()),
                    "anomaly_models": list(self.anomaly_models.keys())
                }
            }

# Convenience functions
def analyze_unsupervised_patterns(file_path: str, target_columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convenience function for comprehensive unsupervised pattern analysis
    
    Args:
        file_path: Path to data file
        target_columns: Specific columns to analyze
        
    Returns:
        Complete unsupervised analysis results
    """
    processor = UnsupervisedProcessor(file_path=file_path)
    return processor.comprehensive_unsupervised_analysis(target_columns)

def quick_clustering_analysis(file_path: str, target_columns: Optional[List[str]] = None,
                             methods: List[str] = None) -> Dict[str, Any]:
    """
    Convenience function for quick clustering analysis
    
    Args:
        file_path: Path to data file
        target_columns: Specific columns to analyze
        methods: Clustering methods to try
        
    Returns:
        Clustering analysis results
    """
    processor = UnsupervisedProcessor(file_path=file_path)
    
    # Prepare data
    data_analysis = processor.get_unsupervised_analysis(target_columns)
    if "error" in data_analysis:
        return data_analysis
    
    # Perform clustering
    return processor.perform_clustering_analysis(methods)

def detect_anomalies(file_path: str, target_columns: Optional[List[str]] = None,
                    contamination: float = 0.1) -> Dict[str, Any]:
    """
    Convenience function for anomaly detection
    
    Args:
        file_path: Path to data file
        target_columns: Specific columns to analyze
        contamination: Expected fraction of anomalies
        
    Returns:
        Anomaly detection results
    """
    processor = UnsupervisedProcessor(file_path=file_path)
    
    # Prepare data
    data_analysis = processor.get_unsupervised_analysis(target_columns)
    if "error" in data_analysis:
        return data_analysis
    
    # Perform anomaly detection
    return processor.perform_anomaly_detection(contamination=contamination)