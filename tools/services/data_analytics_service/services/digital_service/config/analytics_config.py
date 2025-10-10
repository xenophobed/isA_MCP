#!/usr/bin/env python3
"""
Analytics Configuration Module

Configuration classes and enums for Digital Analytics Service
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class VectorDBPolicy(Enum):
    """Policy for selecting vector database backend"""
    AUTO = "auto"
    PERFORMANCE = "performance"
    STORAGE = "storage"
    MEMORY = "memory"
    COST_OPTIMIZED = "cost_optimized"


class ProcessingMode(Enum):
    """Processing mode for different workloads"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"
    STREAMING = "streaming"


@dataclass
class AnalyticsConfig:
    """Configuration for digital analytics service"""
    # Vector Database Settings
    vector_db_policy: VectorDBPolicy = VectorDBPolicy.AUTO
    processing_mode: ProcessingMode = ProcessingMode.PARALLEL
    max_parallel_workers: int = 4
    
    # Quality Control Settings
    enable_guardrails: bool = True
    guardrail_confidence_threshold: float = 0.7
    
    # Reranking Settings
    enable_mmr_reranking: bool = True
    mmr_lambda: float = 0.5
    
    # Document Processing Settings
    enable_incremental_updates: bool = True
    chunk_size: int = 1000
    overlap_size: int = 100
    
    # RAG specific settings
    hybrid_search_enabled: bool = True
    semantic_weight: float = 0.7
    lexical_weight: float = 0.3
    top_k_results: int = 5
    
    # Performance tuning
    enable_caching: bool = True
    cache_ttl_minutes: int = 30
    enable_async_processing: bool = True
    
    # Integration settings
    enable_pdf_processing: bool = True
    enable_large_file_processing: bool = True
    max_file_size_mb: int = 100
    
    # Digital Asset Processing settings
    enable_digital_asset_processing: bool = True
    enable_ai_enhancement: bool = True
    ai_enhancement_threshold: float = 0.7
    asset_processing_mode: str = "comprehensive"  # fast, comprehensive, selective
    enable_cross_asset_analysis: bool = True
    max_asset_processing_time: int = 600  # 10 minutes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'vector_db_policy': self.vector_db_policy.value,
            'processing_mode': self.processing_mode.value,
            'max_parallel_workers': self.max_parallel_workers,
            'enable_guardrails': self.enable_guardrails,
            'guardrail_confidence_threshold': self.guardrail_confidence_threshold,
            'enable_mmr_reranking': self.enable_mmr_reranking,
            'mmr_lambda': self.mmr_lambda,
            'enable_incremental_updates': self.enable_incremental_updates,
            'chunk_size': self.chunk_size,
            'overlap_size': self.overlap_size,
            'hybrid_search_enabled': self.hybrid_search_enabled,
            'semantic_weight': self.semantic_weight,
            'lexical_weight': self.lexical_weight,
            'top_k_results': self.top_k_results,
            'enable_caching': self.enable_caching,
            'cache_ttl_minutes': self.cache_ttl_minutes,
            'enable_async_processing': self.enable_async_processing,
            'enable_pdf_processing': self.enable_pdf_processing,
            'enable_large_file_processing': self.enable_large_file_processing,
            'max_file_size_mb': self.max_file_size_mb,
            'enable_digital_asset_processing': self.enable_digital_asset_processing,
            'enable_ai_enhancement': self.enable_ai_enhancement,
            'ai_enhancement_threshold': self.ai_enhancement_threshold,
            'asset_processing_mode': self.asset_processing_mode,
            'enable_cross_asset_analysis': self.enable_cross_asset_analysis,
            'max_asset_processing_time': self.max_asset_processing_time
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AnalyticsConfig':
        """Create config from dictionary"""
        return cls(**config_dict)

