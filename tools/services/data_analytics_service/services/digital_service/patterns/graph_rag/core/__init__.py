"""
Core components for Generic Knowledge Analytics Service

This module provides the foundation for domain-agnostic knowledge extraction,
relationship analysis, and graph construction using AI technologies (LLM, VLM).
"""

from .types import (
    GenericEntity,
    GenericRelation, 
    GenericAttribute,
    EntityTypeRegistry,
    RelationTypeRegistry,
    AttributeTypeRegistry
)

from .config import (
    DomainConfig,
    ExtractionConfig,
    AIStrategyConfig
)

from .strategies import (
    BaseExtractionStrategy,
    LLMExtractionStrategy,
    VLMExtractionStrategy,
    HybridExtractionStrategy
)

__all__ = [
    'GenericEntity',
    'GenericRelation', 
    'GenericAttribute',
    'EntityTypeRegistry',
    'RelationTypeRegistry',
    'AttributeTypeRegistry',
    'DomainConfig',
    'ExtractionConfig',
    'AIStrategyConfig',
    'BaseExtractionStrategy',
    'LLMExtractionStrategy',
    'VLMExtractionStrategy',
    'HybridExtractionStrategy'
]