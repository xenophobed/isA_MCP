#!/usr/bin/env python3
"""
Base Data Processor
统一的数据处理器基类，负责控制所有机器学习模型的导入问题
所有需要使用 ML 库的 processor 都应该继承这个基类
"""

import logging
from typing import Dict, Any, Optional, Union, List, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd

# 导入我们的模型导入服务
from tools.services.data_analytics_service.services.model_import_service import (
    ModelImportService,
    MLLibrary, 
    ImportResult,
    get_model_import_service,
    get_ml_component,
    get_ml_components,
    is_library_available
)

logger = logging.getLogger(__name__)

@dataclass
class ProcessorCapabilities:
    """处理器能力描述"""
    required_libraries: List[MLLibrary]
    optional_libraries: List[MLLibrary] 
    supports_training: bool = False
    supports_prediction: bool = False
    supports_evaluation: bool = False
    supports_visualization: bool = False

class BaseDataProcessor(ABC):
    """
    数据处理器基类
    
    职责：
    1. 统一管理所有 ML 库的导入
    2. 提供安全的组件获取接口
    3. 处理库不可用的情况
    4. 为子类提供一致的ML库访问模式
    """
    
    def __init__(self, csv_processor=None, file_path: Optional[str] = None):
        """
        初始化基础数据处理器
        
        Args:
            csv_processor: CSV处理器实例
            file_path: 可选的文件路径
        """
        self.csv_processor = csv_processor
        self.file_path = file_path
        self.df: Optional[pd.DataFrame] = None
        
        # 获取全局模型导入服务实例
        self._model_import_service = get_model_import_service()
        
        # 缓存已导入的组件
        self._component_cache: Dict[str, Any] = {}
        
        # 初始化处理器特定的能力
        self._capabilities = self._define_capabilities()
        
        # 验证必需的库是否可用
        self._validate_required_libraries()
        
        logger.debug(f"🔧 {self.__class__.__name__} initialized with model import service")
    
    @abstractmethod
    def _define_capabilities(self) -> ProcessorCapabilities:
        """
        定义处理器的能力和依赖
        子类必须实现此方法
        """
        pass
    
    def _validate_required_libraries(self):
        """验证必需的库是否可用"""
        missing_libraries = []
        for library in self._capabilities.required_libraries:
            if not self.is_library_available(library):
                missing_libraries.append(library.value)
        
        if missing_libraries:
            logger.warning(f"⚠️ {self.__class__.__name__} missing required libraries: {missing_libraries}")
    
    # ==================== ML 库访问接口 ====================
    
    def is_library_available(self, library: MLLibrary) -> bool:
        """检查库是否可用"""
        return self._model_import_service.is_available(library)
    
    def get_ml_component(self, library: MLLibrary, component_name: str) -> Optional[Any]:
        """
        安全地获取机器学习组件
        
        Args:
            library: ML库枚举
            component_name: 组件名称
            
        Returns:
            组件对象或None（如果不可用）
        """
        cache_key = f"{library.value}.{component_name}"
        
        # 先查缓存
        if cache_key in self._component_cache:
            return self._component_cache[cache_key]
        
        # 获取组件
        component = self._model_import_service.get_component(library, component_name)
        
        # 缓存结果
        if component is not None:
            self._component_cache[cache_key] = component
        
        return component
    
    def get_ml_components(self, library: MLLibrary) -> Optional[Dict[str, Any]]:
        """获取库的所有组件"""
        return self._model_import_service.get_components(library)
    
    def require_component(self, library: MLLibrary, component_name: str) -> Any:
        """
        要求组件必须可用，如果不可用则抛出异常
        
        Args:
            library: ML库枚举
            component_name: 组件名称
            
        Returns:
            组件对象
            
        Raises:
            ImportError: 如果组件不可用
        """
        component = self.get_ml_component(library, component_name)
        if component is None:
            raise ImportError(f"Required component {component_name} from {library.value} is not available")
        return component
    
    # ==================== 常用组件快捷访问 ====================
    
    @property
    def sklearn_available(self) -> bool:
        """sklearn是否可用"""
        return self.is_library_available(MLLibrary.SKLEARN)
    
    @property  
    def xgboost_available(self) -> bool:
        """XGBoost是否可用"""
        return self.is_library_available(MLLibrary.XGBOOST)
    
    @property
    def lightgbm_available(self) -> bool:
        """LightGBM是否可用"""
        return self.is_library_available(MLLibrary.LIGHTGBM)
    
    @property
    def pytorch_available(self) -> bool:
        """PyTorch是否可用"""
        return self.is_library_available(MLLibrary.PYTORCH)
    
    @property
    def tensorflow_available(self) -> bool:
        """TensorFlow是否可用"""
        return self.is_library_available(MLLibrary.TENSORFLOW)
    
    # ==================== 快捷组件获取方法 ====================
    
    def get_sklearn_component(self, component_name: str) -> Optional[Any]:
        """获取sklearn组件"""
        return self.get_ml_component(MLLibrary.SKLEARN, component_name)
    
    def get_xgboost_component(self, component_name: str) -> Optional[Any]:
        """获取XGBoost组件"""
        return self.get_ml_component(MLLibrary.XGBOOST, component_name)
    
    def get_lightgbm_component(self, component_name: str) -> Optional[Any]:
        """获取LightGBM组件"""
        return self.get_ml_component(MLLibrary.LIGHTGBM, component_name)
    
    # ==================== 常用模型快捷方法 ====================
    
    def create_random_forest(self, task_type: str = "classification", **kwargs) -> Optional[Any]:
        """创建随机森林模型"""
        if not self.sklearn_available:
            logger.warning("sklearn not available, cannot create RandomForest")
            return None
        
        if task_type.lower() == "classification":
            RandomForestClassifier = self.get_sklearn_component('RandomForestClassifier')
            return RandomForestClassifier(**kwargs) if RandomForestClassifier else None
        else:
            RandomForestRegressor = self.get_sklearn_component('RandomForestRegressor')
            return RandomForestRegressor(**kwargs) if RandomForestRegressor else None
    
    def create_xgboost_model(self, task_type: str = "classification", **kwargs) -> Optional[Any]:
        """创建XGBoost模型"""
        if not self.xgboost_available:
            logger.warning("XGBoost not available, cannot create XGBoost model")
            return None
        
        if task_type.lower() == "classification":
            XGBClassifier = self.get_xgboost_component('XGBClassifier')
            return XGBClassifier(**kwargs) if XGBClassifier else None
        else:
            XGBRegressor = self.get_xgboost_component('XGBRegressor')  
            return XGBRegressor(**kwargs) if XGBRegressor else None
    
    def get_train_test_split(self):
        """获取数据分割函数"""
        return self.get_sklearn_component('train_test_split')
    
    def get_standard_scaler(self):
        """获取标准化器"""
        return self.get_sklearn_component('StandardScaler')
    
    def get_accuracy_score(self):
        """获取准确率计算函数"""
        return self.get_sklearn_component('accuracy_score')
    
    # ==================== 数据处理通用方法 ====================
    
    def load_data(self, file_path: Optional[str] = None) -> bool:
        """
        加载数据
        子类可以重写此方法来实现特定的数据加载逻辑
        """
        if file_path:
            self.file_path = file_path
        
        if self.csv_processor and hasattr(self.csv_processor, 'load_csv'):
            try:
                result = self.csv_processor.load_csv()
                if hasattr(self.csv_processor, 'df') and self.csv_processor.df is not None:
                    self.df = self.csv_processor.df
                    return True
            except Exception as e:
                logger.error(f"Failed to load data: {e}")
        
        return False
    
    def validate_data(self) -> bool:
        """验证数据是否有效"""
        if self.df is None or self.df.empty:
            logger.warning("No data available for processing")
            return False
        return True
    
    # ==================== 能力查询方法 ====================
    
    def get_capabilities(self) -> ProcessorCapabilities:
        """获取处理器能力"""
        return self._capabilities
    
    def get_library_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有相关库的状态"""
        all_libraries = self._capabilities.required_libraries + self._capabilities.optional_libraries
        status = {}
        
        for library in all_libraries:
            is_required = library in self._capabilities.required_libraries
            is_available = self.is_library_available(library)
            
            status[library.value] = {
                'available': is_available,
                'required': is_required,
                'status': 'OK' if is_available else ('MISSING' if is_required else 'OPTIONAL_MISSING')
            }
        
        return status
    
    def can_perform_task(self, task: str) -> bool:
        """检查是否可以执行特定任务"""
        task_map = {
            'training': self._capabilities.supports_training,
            'prediction': self._capabilities.supports_prediction,  
            'evaluation': self._capabilities.supports_evaluation,
            'visualization': self._capabilities.supports_visualization
        }
        
        return task_map.get(task.lower(), False)
    
    # ==================== 抽象方法 ====================
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """
        处理主入口方法
        子类必须实现此方法
        """
        pass
    
    def __str__(self) -> str:
        """字符串表示"""
        status = self.get_library_status()
        available_libs = [lib for lib, info in status.items() if info['available']]
        return f"{self.__class__.__name__}(available_libraries={available_libs})"


# ==================== 特化的基类 ====================

class MLModelProcessor(BaseDataProcessor):
    """
    机器学习模型处理器基类
    专门用于需要ML建模功能的处理器
    """
    
    def _define_capabilities(self) -> ProcessorCapabilities:
        """默认的ML处理器能力"""
        return ProcessorCapabilities(
            required_libraries=[MLLibrary.SKLEARN],
            optional_libraries=[MLLibrary.XGBOOST, MLLibrary.LIGHTGBM],
            supports_training=True,
            supports_prediction=True,
            supports_evaluation=True
        )

class TimeSeriesProcessor(BaseDataProcessor):
    """
    时间序列处理器基类
    专门用于时间序列分析的处理器
    """
    
    def _define_capabilities(self) -> ProcessorCapabilities:
        """时间序列处理器能力"""
        return ProcessorCapabilities(
            required_libraries=[MLLibrary.SKLEARN],
            optional_libraries=[MLLibrary.PROPHET, MLLibrary.STATSMODELS],
            supports_training=True,
            supports_prediction=True,
            supports_evaluation=True
        )

class UnsupervisedProcessor(BaseDataProcessor):
    """
    无监督学习处理器基类
    专门用于聚类、降维等无监督学习的处理器
    """
    
    def _define_capabilities(self) -> ProcessorCapabilities:
        """无监督学习处理器能力"""
        return ProcessorCapabilities(
            required_libraries=[MLLibrary.SKLEARN],
            optional_libraries=[MLLibrary.UMAP, MLLibrary.HDBSCAN],
            supports_training=True,
            supports_prediction=False,
            supports_evaluation=True
        )