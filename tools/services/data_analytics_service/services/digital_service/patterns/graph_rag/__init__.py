"""
Knowledge Extraction Service

Provides relation extraction between entities from text using LLM and pattern-based methods.
Currently only exports tested and documented components.
"""

# Temporarily commented out to fix imports
# from .relation_extractor import RelationExtractor
from .entity_extractor import GenericEntityExtractor
from .attribute_extractor import GenericAttributeExtractor

__all__ = [
    # 'RelationExtractor',
    'GenericEntityExtractor', 
    'GenericAttributeExtractor'
]
    