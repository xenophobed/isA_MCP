"""
Machine Learning and Deep Learning Models
Advanced ML/DL algorithms, model training, and serving
"""

# LAZY LOADING to prevent hanging on import
# Import processors only when actually needed

def _get_time_series_processor():
    from .time_series_processor import TimeSeriesProcessor
    return TimeSeriesProcessor

def _get_deep_learning_processor():
    from .deep_learning_processor import DeepLearningProcessor
    return DeepLearningProcessor

def _get_unsupervised_processor():
    from .unsupervised_processor import UnsupervisedProcessor
    return UnsupervisedProcessor

def _get_ensemble_processor():
    from .ensemble_processor import EnsembleProcessor
    return EnsembleProcessor

def _get_ml_processor():
    from .ml_processor import MLProcessor
    return MLProcessor

def _get_model_serving_processor():
    from .model_serving_processor import ModelServingProcessor
    return ModelServingProcessor

# Lazy loading properties
class _LazyLoader:
    @property
    def TimeSeriesProcessor(self):
        return _get_time_series_processor()
    
    @property 
    def DeepLearningProcessor(self):
        return _get_deep_learning_processor()
    
    @property
    def UnsupervisedProcessor(self):
        return _get_unsupervised_processor()
    
    @property
    def EnsembleProcessor(self):
        return _get_ensemble_processor()
    
    @property
    def MLProcessor(self):
        return _get_ml_processor()
    
    @property
    def ModelServingProcessor(self):
        return _get_model_serving_processor()

# Create a lazy loader instance
_loader = _LazyLoader()

# Export through the loader
TimeSeriesProcessor = _loader.TimeSeriesProcessor
DeepLearningProcessor = _loader.DeepLearningProcessor
UnsupervisedProcessor = _loader.UnsupervisedProcessor
EnsembleProcessor = _loader.EnsembleProcessor
MLProcessor = _loader.MLProcessor
ModelServingProcessor = _loader.ModelServingProcessor

__all__ = [
    'TimeSeriesProcessor',
    'DeepLearningProcessor',
    'UnsupervisedProcessor', 
    'EnsembleProcessor',
    'MLProcessor',
    'ModelServingProcessor'
]