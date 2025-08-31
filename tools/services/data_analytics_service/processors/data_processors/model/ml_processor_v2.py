#!/usr/bin/env python3
"""
Machine Learning Processor V2
基于新的 BaseDataProcessor 的统一机器学习接口
使用统一的模型导入服务，完全避免 mutex 锁问题
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import logging
import json
from pathlib import Path

# 导入新的基类
from tools.services.data_analytics_service.processors.data_processors.base_data_processor import MLModelProcessor, ProcessorCapabilities
from tools.services.data_analytics_service.services.model_import_service import MLLibrary

logger = logging.getLogger(__name__)

class MLProcessor(MLModelProcessor):
    """
    机器学习处理器
    
    提供统一的机器学习接口，支持：
    - 模型训练和预测
    - 自动算法推荐
    - 超参数优化
    - 模型评估
    """
    
    def __init__(self, csv_processor=None, file_path: Optional[str] = None):
        """初始化ML处理器"""
        super().__init__(csv_processor, file_path)
        
        # ML特定的配置
        self.execution_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'models_trained': 0
        }
        
        logger.info(f"🤖 MLProcessor initialized with libraries: {self._get_available_libraries()}")
    
    def _define_capabilities(self) -> ProcessorCapabilities:
        """定义ML处理器的具体能力"""
        return ProcessorCapabilities(
            required_libraries=[MLLibrary.SKLEARN],
            optional_libraries=[MLLibrary.XGBOOST, MLLibrary.LIGHTGBM, MLLibrary.PYTORCH, MLLibrary.TENSORFLOW],
            supports_training=True,
            supports_prediction=True,
            supports_evaluation=True,
            supports_visualization=False
        )
    
    def _get_available_libraries(self) -> List[str]:
        """获取可用的库列表"""
        available = []
        if self.sklearn_available:
            available.append("sklearn")
        if self.xgboost_available:
            available.append("xgboost")
        if self.lightgbm_available:
            available.append("lightgbm")
        if self.pytorch_available:
            available.append("pytorch")
        if self.tensorflow_available:
            available.append("tensorflow")
        return available
    
    # ==================== 数据预处理 ====================
    
    def prepare_data(self, target_column: str, test_size: float = 0.2, random_state: int = 42) -> Dict[str, Any]:
        """
        准备训练数据
        
        Args:
            target_column: 目标列名
            test_size: 测试集比例
            random_state: 随机种子
        
        Returns:
            包含训练测试数据的字典
        """
        if not self.validate_data():
            raise ValueError("No valid data available")
        
        if target_column not in self.df.columns:
            raise ValueError(f"Target column '{target_column}' not found in data")
        
        # 分离特征和目标
        X = self.df.drop(columns=[target_column])
        y = self.df[target_column]
        
        # 获取数据分割函数
        train_test_split = self.get_train_test_split()
        if train_test_split is None:
            raise ImportError("sklearn train_test_split not available")
        
        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        return {
            'X_train': X_train,
            'X_test': X_test,
            'y_train': y_train,
            'y_test': y_test,
            'feature_names': X.columns.tolist(),
            'target_name': target_column,
            'data_shape': X.shape,
            'target_type': self._detect_target_type(y)
        }
    
    def _detect_target_type(self, y) -> str:
        """检测目标变量类型"""
        if pd.api.types.is_numeric_dtype(y):
            unique_values = y.nunique()
            if unique_values <= 10:
                return 'classification'
            else:
                return 'regression'
        else:
            return 'classification'
    
    # ==================== 算法推荐 ====================
    
    def recommend_algorithms(self, target_column: str, problem_type: Optional[str] = None) -> Dict[str, Any]:
        """
        推荐合适的算法
        
        Args:
            target_column: 目标列名
            problem_type: 问题类型 ('classification' 或 'regression')
        
        Returns:
            算法推荐结果
        """
        if not self.validate_data():
            return {'error': 'No valid data available'}
        
        # 自动检测问题类型
        if problem_type is None:
            y = self.df[target_column] if target_column in self.df.columns else None
            if y is not None:
                problem_type = self._detect_target_type(y)
            else:
                problem_type = 'classification'
        
        recommendations = {
            'problem_type': problem_type,
            'data_info': {
                'shape': self.df.shape,
                'features': len(self.df.columns) - 1,
                'samples': len(self.df)
            },
            'algorithms': []
        }
        
        # 基于sklearn的算法推荐
        if self.sklearn_available:
            if problem_type == 'classification':
                recommendations['algorithms'].extend([
                    {
                        'name': 'RandomForest',
                        'library': 'sklearn',
                        'complexity': 'medium',
                        'interpretability': 'medium',
                        'performance': 'high',
                        'pros': ['Good default performance', 'Handles missing values', 'Feature importance'],
                        'cons': ['Can overfit', 'Memory intensive']
                    },
                    {
                        'name': 'LogisticRegression', 
                        'library': 'sklearn',
                        'complexity': 'low',
                        'interpretability': 'high',
                        'performance': 'medium',
                        'pros': ['Fast', 'Interpretable', 'Probabilistic output'],
                        'cons': ['Assumes linear relationship', 'Sensitive to outliers']
                    }
                ])
            else:
                recommendations['algorithms'].extend([
                    {
                        'name': 'RandomForestRegressor',
                        'library': 'sklearn', 
                        'complexity': 'medium',
                        'interpretability': 'medium',
                        'performance': 'high',
                        'pros': ['Robust', 'Feature importance', 'Non-linear'],
                        'cons': ['Can overfit', 'Not good for extrapolation']
                    },
                    {
                        'name': 'LinearRegression',
                        'library': 'sklearn',
                        'complexity': 'low',
                        'interpretability': 'high', 
                        'performance': 'medium',
                        'pros': ['Fast', 'Interpretable', 'Simple'],
                        'cons': ['Assumes linear relationship', 'Sensitive to outliers']
                    }
                ])
        
        # XGBoost推荐
        if self.xgboost_available:
            xgb_rec = {
                'name': 'XGBoost',
                'library': 'xgboost',
                'complexity': 'high',
                'interpretability': 'low',
                'performance': 'very_high',
                'pros': ['Excellent performance', 'Feature importance', 'Handles missing values'],
                'cons': ['Requires tuning', 'Can overfit', 'Complex']
            }
            recommendations['algorithms'].append(xgb_rec)
        
        # LightGBM推荐
        if self.lightgbm_available:
            lgb_rec = {
                'name': 'LightGBM',
                'library': 'lightgbm',
                'complexity': 'high', 
                'interpretability': 'low',
                'performance': 'very_high',
                'pros': ['Fast training', 'Memory efficient', 'High performance'],
                'cons': ['Requires tuning', 'Can overfit on small data']
            }
            recommendations['algorithms'].append(lgb_rec)
        
        return recommendations
    
    # ==================== 模型训练 ====================
    
    def train_model(self, algorithm: str, target_column: str, **kwargs) -> Dict[str, Any]:
        """
        训练模型
        
        Args:
            algorithm: 算法名称
            target_column: 目标列名
            **kwargs: 模型参数
        
        Returns:
            训练结果
        """
        try:
            self.execution_stats['total_operations'] += 1
            
            # 准备数据
            data = self.prepare_data(target_column)
            
            # 创建模型
            model = self._create_model(algorithm, data['target_type'], **kwargs)
            if model is None:
                raise ValueError(f"Algorithm '{algorithm}' not available")
            
            # 训练模型
            start_time = datetime.now()
            model.fit(data['X_train'], data['y_train'])
            training_time = (datetime.now() - start_time).total_seconds()
            
            # 评估模型
            evaluation = self._evaluate_model(model, data)
            
            result = {
                'success': True,
                'algorithm': algorithm,
                'model': model,
                'training_time': training_time,
                'data_info': {
                    'features': len(data['feature_names']),
                    'samples': len(data['X_train']),
                    'target_type': data['target_type']
                },
                'evaluation': evaluation,
                'timestamp': datetime.now().isoformat()
            }
            
            self.execution_stats['successful_operations'] += 1
            self.execution_stats['models_trained'] += 1
            
            logger.info(f"✅ Model {algorithm} trained successfully in {training_time:.2f}s")
            return result
            
        except Exception as e:
            self.execution_stats['failed_operations'] += 1
            logger.error(f"❌ Model training failed: {e}")
            return {
                'success': False,
                'algorithm': algorithm,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _create_model(self, algorithm: str, target_type: str, **kwargs) -> Optional[Any]:
        """创建模型实例"""
        algo_lower = algorithm.lower()
        
        # sklearn 模型
        if 'randomforest' in algo_lower:
            if target_type == 'classification':
                return self.create_random_forest('classification', **kwargs)
            else:
                return self.create_random_forest('regression', **kwargs)
        
        elif 'logistic' in algo_lower:
            LogisticRegression = self.get_sklearn_component('LogisticRegression')
            return LogisticRegression(**kwargs) if LogisticRegression else None
        
        elif 'linear' in algo_lower:
            LinearRegression = self.get_sklearn_component('LinearRegression')
            return LinearRegression(**kwargs) if LinearRegression else None
        
        # XGBoost 模型
        elif 'xgb' in algo_lower or 'xgboost' in algo_lower:
            return self.create_xgboost_model(target_type, **kwargs)
        
        # LightGBM 模型
        elif 'lgb' in algo_lower or 'lightgbm' in algo_lower:
            if target_type == 'classification':
                LGBMClassifier = self.get_lightgbm_component('LGBMClassifier')
                return LGBMClassifier(**kwargs) if LGBMClassifier else None
            else:
                LGBMRegressor = self.get_lightgbm_component('LGBMRegressor')
                return LGBMRegressor(**kwargs) if LGBMRegressor else None
        
        return None
    
    def _evaluate_model(self, model, data: Dict[str, Any]) -> Dict[str, float]:
        """评估模型性能"""
        try:
            # 预测
            y_pred = model.predict(data['X_test'])
            
            metrics = {}
            
            if data['target_type'] == 'classification':
                # 分类指标
                accuracy_score = self.get_accuracy_score()
                if accuracy_score:
                    metrics['accuracy'] = accuracy_score(data['y_test'], y_pred)
                
                # 其他分类指标
                precision_score = self.get_sklearn_component('precision_score')
                if precision_score:
                    try:
                        metrics['precision'] = precision_score(data['y_test'], y_pred, average='weighted')
                    except:
                        pass
                
                recall_score = self.get_sklearn_component('recall_score')
                if recall_score:
                    try:
                        metrics['recall'] = recall_score(data['y_test'], y_pred, average='weighted')
                    except:
                        pass
            
            else:
                # 回归指标
                mean_squared_error = self.get_sklearn_component('mean_squared_error')
                if mean_squared_error:
                    metrics['mse'] = mean_squared_error(data['y_test'], y_pred)
                
                mean_absolute_error = self.get_sklearn_component('mean_absolute_error')
                if mean_absolute_error:
                    metrics['mae'] = mean_absolute_error(data['y_test'], y_pred)
                
                r2_score = self.get_sklearn_component('r2_score')
                if r2_score:
                    metrics['r2'] = r2_score(data['y_test'], y_pred)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Model evaluation failed: {e}")
            return {}
    
    # ==================== 主处理方法 ====================
    
    def process(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        主处理入口
        
        Args:
            operation: 操作类型 ('recommend', 'train', 'predict', 'evaluate')
            **kwargs: 操作参数
        """
        if operation == 'recommend':
            return self.recommend_algorithms(**kwargs)
        elif operation == 'train':
            return self.train_model(**kwargs)
        elif operation == 'status':
            return self.get_status()
        else:
            return {'error': f"Unknown operation: {operation}"}
    
    def get_status(self) -> Dict[str, Any]:
        """获取处理器状态"""
        return {
            'class_name': self.__class__.__name__,
            'available_libraries': self._get_available_libraries(),
            'library_status': self.get_library_status(),
            'capabilities': {
                'training': self.can_perform_task('training'),
                'prediction': self.can_perform_task('prediction'),
                'evaluation': self.can_perform_task('evaluation')
            },
            'execution_stats': self.execution_stats,
            'data_loaded': self.df is not None and not self.df.empty
        }