#!/usr/bin/env python3
"""
模型导入服务 (Model Import Service)
统一管理所有机器学习库的懒加载，防止 mutex 锁和启动时的性能问题
"""

import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MLLibrary(Enum):
    """支持的机器学习库枚举"""
    SKLEARN = "sklearn"
    XGBOOST = "xgboost" 
    LIGHTGBM = "lightgbm"
    TENSORFLOW = "tensorflow"
    PYTORCH = "torch"
    PROPHET = "prophet"
    STATSMODELS = "statsmodels"
    UMAP = "umap"
    HDBSCAN = "hdbscan"

@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    library: MLLibrary
    components: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class ModelImportService:
    """
    模型导入服务
    
    职责：
    - 统一管理所有ML库的懒加载
    - 避免启动时的mutex锁问题
    - 提供统一的导入接口
    - 缓存已导入的组件
    """
    
    def __init__(self):
        self._import_cache: Dict[MLLibrary, ImportResult] = {}
        self._availability_cache: Dict[MLLibrary, Optional[bool]] = {}
        logger.info("🔧 ModelImportService initialized with lazy loading")
    
    def is_available(self, library: MLLibrary) -> bool:
        """检查库是否可用（懒检查）"""
        if library in self._availability_cache:
            return self._availability_cache[library] or False
        
        # 懒检查
        result = self._import_library(library)
        self._availability_cache[library] = result.success
        return result.success
    
    def import_library(self, library: MLLibrary) -> ImportResult:
        """导入指定的机器学习库"""
        if library in self._import_cache:
            return self._import_cache[library]
        
        result = self._import_library(library)
        self._import_cache[library] = result
        return result
    
    def get_component(self, library: MLLibrary, component_name: str) -> Optional[Any]:
        """获取特定库的特定组件"""
        result = self.import_library(library)
        if not result.success or not result.components:
            return None
        return result.components.get(component_name)
    
    def get_components(self, library: MLLibrary) -> Optional[Dict[str, Any]]:
        """获取特定库的所有组件"""
        result = self.import_library(library)
        if not result.success:
            return None
        return result.components
    
    def _import_library(self, library: MLLibrary) -> ImportResult:
        """实际执行库的导入"""
        try:
            if library == MLLibrary.SKLEARN:
                return self._import_sklearn()
            elif library == MLLibrary.XGBOOST:
                return self._import_xgboost()
            elif library == MLLibrary.LIGHTGBM:
                return self._import_lightgbm()
            elif library == MLLibrary.TENSORFLOW:
                return self._import_tensorflow()
            elif library == MLLibrary.PYTORCH:
                return self._import_pytorch()
            elif library == MLLibrary.PROPHET:
                return self._import_prophet()
            elif library == MLLibrary.STATSMODELS:
                return self._import_statsmodels()
            elif library == MLLibrary.UMAP:
                return self._import_umap()
            elif library == MLLibrary.HDBSCAN:
                return self._import_hdbscan()
            else:
                return ImportResult(
                    success=False,
                    library=library,
                    error_message=f"Unsupported library: {library}"
                )
        except Exception as e:
            logger.warning(f"Failed to import {library.value}: {e}")
            return ImportResult(
                success=False,
                library=library,
                error_message=str(e)
            )
    
    def _import_sklearn(self) -> ImportResult:
        """导入 sklearn 组件"""
        try:
            # Core components
            from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, RandomizedSearchCV, StratifiedKFold, KFold
            from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler, RobustScaler
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
                mean_squared_error, mean_absolute_error, r2_score,
                silhouette_score, calinski_harabasz_score, davies_bouldin_score
            )
            
            # Models
            from sklearn.ensemble import (
                RandomForestClassifier, RandomForestRegressor,
                VotingClassifier, VotingRegressor, BaggingClassifier, BaggingRegressor,
                ExtraTreesClassifier, ExtraTreesRegressor, AdaBoostClassifier, AdaBoostRegressor,
                GradientBoostingClassifier, GradientBoostingRegressor,
                StackingClassifier, StackingRegressor, IsolationForest
            )
            from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge, Lasso
            from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
            from sklearn.svm import SVC, SVR, OneClassSVM
            from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor, NearestNeighbors, LocalOutlierFactor
            from sklearn.naive_bayes import GaussianNB
            from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, SpectralClustering, MeanShift, OPTICS, Birch, MiniBatchKMeans
            from sklearn.mixture import GaussianMixture
            from sklearn.decomposition import PCA, TruncatedSVD, FactorAnalysis, FastICA, NMF, LatentDirichletAllocation
            from sklearn.manifold import TSNE, MDS, Isomap, LocallyLinearEmbedding
            from sklearn.covariance import EllipticEnvelope
            from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin, clone
            
            components = {
                # Data processing
                'train_test_split': train_test_split, 'cross_val_score': cross_val_score,
                'GridSearchCV': GridSearchCV, 'RandomizedSearchCV': RandomizedSearchCV,
                'StratifiedKFold': StratifiedKFold, 'KFold': KFold,
                'StandardScaler': StandardScaler, 'LabelEncoder': LabelEncoder,
                'MinMaxScaler': MinMaxScaler, 'RobustScaler': RobustScaler,
                
                # Metrics
                'accuracy_score': accuracy_score, 'precision_score': precision_score,
                'recall_score': recall_score, 'f1_score': f1_score, 'roc_auc_score': roc_auc_score,
                'mean_squared_error': mean_squared_error, 'mean_absolute_error': mean_absolute_error,
                'r2_score': r2_score, 'silhouette_score': silhouette_score,
                'calinski_harabasz_score': calinski_harabasz_score, 'davies_bouldin_score': davies_bouldin_score,
                
                # Ensemble methods
                'RandomForestClassifier': RandomForestClassifier, 'RandomForestRegressor': RandomForestRegressor,
                'VotingClassifier': VotingClassifier, 'VotingRegressor': VotingRegressor,
                'BaggingClassifier': BaggingClassifier, 'BaggingRegressor': BaggingRegressor,
                'ExtraTreesClassifier': ExtraTreesClassifier, 'ExtraTreesRegressor': ExtraTreesRegressor,
                'AdaBoostClassifier': AdaBoostClassifier, 'AdaBoostRegressor': AdaBoostRegressor,
                'GradientBoostingClassifier': GradientBoostingClassifier, 'GradientBoostingRegressor': GradientBoostingRegressor,
                'StackingClassifier': StackingClassifier, 'StackingRegressor': StackingRegressor,
                
                # Basic models
                'LogisticRegression': LogisticRegression, 'LinearRegression': LinearRegression,
                'Ridge': Ridge, 'Lasso': Lasso, 'DecisionTreeClassifier': DecisionTreeClassifier,
                'DecisionTreeRegressor': DecisionTreeRegressor, 'SVC': SVC, 'SVR': SVR,
                'KNeighborsClassifier': KNeighborsClassifier, 'KNeighborsRegressor': KNeighborsRegressor,
                'GaussianNB': GaussianNB,
                
                # Clustering
                'KMeans': KMeans, 'DBSCAN': DBSCAN, 'AgglomerativeClustering': AgglomerativeClustering,
                'SpectralClustering': SpectralClustering, 'MeanShift': MeanShift, 'OPTICS': OPTICS,
                'Birch': Birch, 'MiniBatchKMeans': MiniBatchKMeans, 'GaussianMixture': GaussianMixture,
                
                # Dimensionality reduction
                'PCA': PCA, 'TruncatedSVD': TruncatedSVD, 'FactorAnalysis': FactorAnalysis,
                'FastICA': FastICA, 'NMF': NMF, 'LatentDirichletAllocation': LatentDirichletAllocation,
                'TSNE': TSNE, 'MDS': MDS, 'Isomap': Isomap, 'LocallyLinearEmbedding': LocallyLinearEmbedding,
                
                # Anomaly detection
                'IsolationForest': IsolationForest, 'OneClassSVM': OneClassSVM,
                'EllipticEnvelope': EllipticEnvelope, 'LocalOutlierFactor': LocalOutlierFactor,
                'NearestNeighbors': NearestNeighbors,
                
                # Base classes
                'BaseEstimator': BaseEstimator, 'ClassifierMixin': ClassifierMixin,
                'RegressorMixin': RegressorMixin, 'clone': clone
            }
            
            return ImportResult(success=True, library=MLLibrary.SKLEARN, components=components)
            
        except ImportError as e:
            return ImportResult(
                success=False,
                library=MLLibrary.SKLEARN,
                error_message=f"sklearn not available: {e}"
            )
    
    def _import_xgboost(self) -> ImportResult:
        """导入 XGBoost 组件"""
        try:
            import xgboost as xgb
            
            components = {
                'XGBClassifier': xgb.XGBClassifier,
                'XGBRegressor': xgb.XGBRegressor,
                'XGBRanker': xgb.XGBRanker if hasattr(xgb, 'XGBRanker') else None,
                'DMatrix': xgb.DMatrix,
                'train': xgb.train,
                'cv': xgb.cv
            }
            
            # Remove None values
            components = {k: v for k, v in components.items() if v is not None}
            
            return ImportResult(success=True, library=MLLibrary.XGBOOST, components=components)
            
        except ImportError as e:
            return ImportResult(
                success=False,
                library=MLLibrary.XGBOOST,
                error_message=f"XGBoost not available: {e}"
            )
    
    def _import_lightgbm(self) -> ImportResult:
        """导入 LightGBM 组件"""
        try:
            import lightgbm as lgb
            
            components = {
                'LGBMClassifier': lgb.LGBMClassifier,
                'LGBMRegressor': lgb.LGBMRegressor,
                'LGBMRanker': lgb.LGBMRanker if hasattr(lgb, 'LGBMRanker') else None,
                'Dataset': lgb.Dataset,
                'train': lgb.train,
                'cv': lgb.cv
            }
            
            # Remove None values
            components = {k: v for k, v in components.items() if v is not None}
            
            return ImportResult(success=True, library=MLLibrary.LIGHTGBM, components=components)
            
        except ImportError as e:
            return ImportResult(
                success=False,
                library=MLLibrary.LIGHTGBM,
                error_message=f"LightGBM not available: {e}"
            )
    
    def _import_tensorflow(self) -> ImportResult:
        """导入 TensorFlow 组件"""
        try:
            import tensorflow as tf
            
            components = {
                'tf': tf,
                'keras': tf.keras,
                'layers': tf.keras.layers,
                'models': tf.keras.models,
                'optimizers': tf.keras.optimizers,
                'losses': tf.keras.losses,
                'metrics': tf.keras.metrics,
                'callbacks': tf.keras.callbacks
            }
            
            return ImportResult(success=True, library=MLLibrary.TENSORFLOW, components=components)
            
        except ImportError as e:
            return ImportResult(
                success=False,
                library=MLLibrary.TENSORFLOW,
                error_message=f"TensorFlow not available: {e}"
            )
    
    def _import_pytorch(self) -> ImportResult:
        """导入 PyTorch 组件"""
        try:
            import torch
            import torch.nn as nn
            import torch.optim as optim
            
            components = {
                'torch': torch,
                'nn': nn,
                'optim': optim,
                'functional': torch.nn.functional
            }
            
            return ImportResult(success=True, library=MLLibrary.PYTORCH, components=components)
            
        except ImportError as e:
            return ImportResult(
                success=False,
                library=MLLibrary.PYTORCH,
                error_message=f"PyTorch not available: {e}"
            )
    
    def _import_prophet(self) -> ImportResult:
        """导入 Prophet 组件"""
        try:
            from prophet import Prophet
            from prophet.diagnostics import cross_validation, performance_metrics
            
            components = {
                'Prophet': Prophet,
                'cross_validation': cross_validation,
                'performance_metrics': performance_metrics
            }
            
            return ImportResult(success=True, library=MLLibrary.PROPHET, components=components)
            
        except ImportError as e:
            return ImportResult(
                success=False,
                library=MLLibrary.PROPHET,
                error_message=f"Prophet not available: {e}"
            )
    
    def _import_statsmodels(self) -> ImportResult:
        """导入 Statsmodels 组件"""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.seasonal import seasonal_decompose
            from statsmodels.tsa.stattools import adfuller, kpss
            from statsmodels.tsa.api import ExponentialSmoothing
            from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
            
            components = {
                'ARIMA': ARIMA,
                'seasonal_decompose': seasonal_decompose,
                'adfuller': adfuller,
                'kpss': kpss,
                'ExponentialSmoothing': ExponentialSmoothing,
                'plot_acf': plot_acf,
                'plot_pacf': plot_pacf
            }
            
            return ImportResult(success=True, library=MLLibrary.STATSMODELS, components=components)
            
        except ImportError as e:
            return ImportResult(
                success=False,
                library=MLLibrary.STATSMODELS,
                error_message=f"Statsmodels not available: {e}"
            )
    
    def _import_umap(self) -> ImportResult:
        """导入 UMAP 组件"""
        try:
            import umap.umap_ as umap
            
            components = {
                'UMAP': umap.UMAP
            }
            
            return ImportResult(success=True, library=MLLibrary.UMAP, components=components)
            
        except ImportError as e:
            return ImportResult(
                success=False,
                library=MLLibrary.UMAP,
                error_message=f"UMAP not available: {e}"
            )
    
    def _import_hdbscan(self) -> ImportResult:
        """导入 HDBSCAN 组件"""
        try:
            from hdbscan import HDBSCAN
            
            components = {
                'HDBSCAN': HDBSCAN
            }
            
            return ImportResult(success=True, library=MLLibrary.HDBSCAN, components=components)
            
        except ImportError as e:
            return ImportResult(
                success=False,
                library=MLLibrary.HDBSCAN,
                error_message=f"HDBSCAN not available: {e}"
            )
    
    def get_library_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有库的状态信息"""
        status = {}
        for library in MLLibrary:
            is_available = self.is_available(library)
            import_result = self._import_cache.get(library)
            
            status[library.value] = {
                'available': is_available,
                'imported': library in self._import_cache,
                'error_message': import_result.error_message if import_result and not import_result.success else None,
                'component_count': len(import_result.components) if import_result and import_result.components else 0
            }
        
        return status
    
    def clear_cache(self):
        """清空所有缓存"""
        self._import_cache.clear()
        self._availability_cache.clear()
        logger.info("🧹 ModelImportService cache cleared")


# 全局单例实例
_model_import_service: Optional[ModelImportService] = None

def get_model_import_service() -> ModelImportService:
    """获取全局模型导入服务实例"""
    global _model_import_service
    if _model_import_service is None:
        _model_import_service = ModelImportService()
    return _model_import_service

# 便捷函数
def is_library_available(library: MLLibrary) -> bool:
    """检查库是否可用"""
    return get_model_import_service().is_available(library)

def import_ml_library(library: MLLibrary) -> ImportResult:
    """导入机器学习库"""
    return get_model_import_service().import_library(library)

def get_ml_component(library: MLLibrary, component_name: str) -> Optional[Any]:
    """获取机器学习组件"""
    return get_model_import_service().get_component(library, component_name)

def get_ml_components(library: MLLibrary) -> Optional[Dict[str, Any]]:
    """获取机器学习库的所有组件"""
    return get_model_import_service().get_components(library)