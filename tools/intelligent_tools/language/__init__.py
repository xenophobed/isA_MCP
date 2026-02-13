#!/usr/bin/env python3
"""
Language Intelligence Service - Natural Language Processing AI capabilities

Provides atomic language-based AI capabilities:
- Text Extraction: Extract and understand text content using AI
- Entity Extraction: Extract named entities from text
- Text Classification: Classify text into categories
- Summarization: Generate summaries of text content
- Content Generation: Generate text content based on prompts
- Semantic Analysis: Analyze semantic meaning and relationships
- Embedding Generation: Generate embeddings for text
"""

from .text_generator import TextGenerator
from .text_summarizer import TextSummarizer

__version__ = "1.0.0"
__all__ = [
    # Text generation
    "TextGenerator",
    # Text summarization
    "TextSummarizer",
]
