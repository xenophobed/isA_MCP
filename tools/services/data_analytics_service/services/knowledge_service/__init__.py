"""
Knowledge Extraction Service

Provides relation extraction between entities from text using LLM and pattern-based methods.
Currently only exports tested and documented components.
"""

from .relation_extractor import RelationExtractor
from .entity_extractor import EntityExtractor
from .attribute_extractor import AttributeExtractor

__all__ = [
    'RelationExtractor',
    'EntityExtractor',
    'AttributeExtractor'
]
    