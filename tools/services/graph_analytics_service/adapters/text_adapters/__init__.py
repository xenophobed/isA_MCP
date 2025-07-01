#!/usr/bin/env python3
"""
Text Adapters

Adapters for different text processing and NLP libraries.
Provides standardized interfaces for text analysis operations.
"""

from .spacy_adapter import SpacyAdapter
from .nltk_adapter import NLTKAdapter

__all__ = [
    "SpacyAdapter",
    "NLTKAdapter"
]