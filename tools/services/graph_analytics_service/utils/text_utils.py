#!/usr/bin/env python3
"""
Text Processing Utilities for Graph Analytics

Common text processing functions used across the graph analytics service.
"""

import re
import string
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import unicodedata

from core.logging import get_logger

logger = get_logger(__name__)

def clean_text(text: str, 
               remove_punct: bool = False,
               remove_digits: bool = False,
               normalize_unicode: bool = True,
               lowercase: bool = False) -> str:
    """
    Clean and normalize text for processing.
    
    Args:
        text: Input text to clean
        remove_punct: Whether to remove punctuation
        remove_digits: Whether to remove digits
        normalize_unicode: Whether to normalize unicode characters
        lowercase: Whether to convert to lowercase
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Normalize unicode
    if normalize_unicode:
        text = unicodedata.normalize('NFKD', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove punctuation if requested
    if remove_punct:
        text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Remove digits if requested
    if remove_digits:
        text = re.sub(r'\d+', '', text)
    
    # Convert to lowercase if requested
    if lowercase:
        text = text.lower()
    
    return text

def extract_context(text: str, 
                   entity_start: int, 
                   entity_end: int,
                   window_size: int = 100) -> Dict[str, Any]:
    """
    Extract context around an entity in text.
    
    Args:
        text: Source text
        entity_start: Start position of entity
        entity_end: End position of entity
        window_size: Size of context window
        
    Returns:
        Context information
    """
    text_len = len(text)
    
    # Calculate context boundaries
    context_start = max(0, entity_start - window_size)
    context_end = min(text_len, entity_end + window_size)
    
    # Extract context
    left_context = text[context_start:entity_start]
    entity_text = text[entity_start:entity_end]
    right_context = text[entity_end:context_end]
    full_context = text[context_start:context_end]
    
    return {
        "left_context": left_context,
        "entity_text": entity_text,
        "right_context": right_context,
        "full_context": full_context,
        "context_start": context_start,
        "context_end": context_end,
        "entity_position": {
            "start": entity_start - context_start,
            "end": entity_end - context_start
        }
    }

def tokenize_text(text: str, 
                 method: str = "word",
                 preserve_case: bool = True) -> List[str]:
    """
    Tokenize text into words or sentences.
    
    Args:
        text: Input text
        method: Tokenization method ("word" or "sentence")
        preserve_case: Whether to preserve original case
        
    Returns:
        List of tokens
    """
    if not text:
        return []
    
    if not preserve_case:
        text = text.lower()
    
    if method == "word":
        # Simple word tokenization
        tokens = re.findall(r'\b\w+\b', text)
    elif method == "sentence":
        # Simple sentence tokenization
        tokens = re.split(r'[.!?]+', text)
        tokens = [t.strip() for t in tokens if t.strip()]
    else:
        raise ValueError(f"Unknown tokenization method: {method}")
    
    return tokens

def normalize_text(text: str, 
                  entity_type: Optional[str] = None) -> str:
    """
    Normalize text based on entity type.
    
    Args:
        text: Input text
        entity_type: Optional entity type for specific normalization
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Basic normalization
    normalized = text.strip()
    
    # Type-specific normalization
    if entity_type:
        entity_type = entity_type.upper()
        
        if entity_type == "PERSON":
            # Normalize person names
            normalized = " ".join(word.capitalize() for word in normalized.split())
        
        elif entity_type == "ORG":
            # Normalize organization names
            # Remove common suffixes/prefixes
            common_org_words = ['inc', 'corp', 'ltd', 'llc', 'company', 'co']
            words = normalized.split()
            words = [w for w in words if w.lower() not in common_org_words]
            normalized = " ".join(words)
        
        elif entity_type == "LOC":
            # Normalize location names
            normalized = " ".join(word.capitalize() for word in normalized.split())
        
        elif entity_type == "DATE":
            # Normalize dates
            normalized = re.sub(r'\s+', '-', normalized)
    
    return normalized

def calculate_text_similarity(text1: str, text2: str, method: str = "jaccard") -> float:
    """
    Calculate similarity between two texts.
    
    Args:
        text1: First text
        text2: Second text
        method: Similarity method ("jaccard", "cosine", "levenshtein")
        
    Returns:
        Similarity score (0.0 to 1.0)
    """
    if not text1 or not text2:
        return 0.0
    
    if method == "jaccard":
        return _jaccard_similarity(text1, text2)
    elif method == "cosine":
        return _cosine_similarity(text1, text2)
    elif method == "levenshtein":
        return _levenshtein_similarity(text1, text2)
    else:
        raise ValueError(f"Unknown similarity method: {method}")

def _jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    tokens1 = set(tokenize_text(text1.lower()))
    tokens2 = set(tokenize_text(text2.lower()))
    
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    
    return intersection / union if union > 0 else 0.0

def _cosine_similarity(text1: str, text2: str) -> float:
    """Calculate cosine similarity between two texts."""
    tokens1 = tokenize_text(text1.lower())
    tokens2 = tokenize_text(text2.lower())
    
    # Create frequency vectors
    all_tokens = set(tokens1 + tokens2)
    vec1 = [tokens1.count(token) for token in all_tokens]
    vec2 = [tokens2.count(token) for token in all_tokens]
    
    # Calculate cosine similarity
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def _levenshtein_similarity(text1: str, text2: str) -> float:
    """Calculate Levenshtein similarity between two texts."""
    def levenshtein_distance(s1, s2):
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    distance = levenshtein_distance(text1.lower(), text2.lower())
    max_len = max(len(text1), len(text2))
    
    return 1 - (distance / max_len) if max_len > 0 else 1.0

def extract_keywords(text: str, 
                    max_keywords: int = 10,
                    min_length: int = 3) -> List[Tuple[str, int]]:
    """
    Extract keywords from text based on frequency.
    
    Args:
        text: Input text
        max_keywords: Maximum number of keywords to return
        min_length: Minimum keyword length
        
    Returns:
        List of (keyword, frequency) tuples
    """
    if not text:
        return []
    
    # Tokenize and clean
    tokens = tokenize_text(text.lower())
    tokens = [token for token in tokens if len(token) >= min_length]
    
    # Remove common stopwords
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
        'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
        'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
        'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
    }
    
    tokens = [token for token in tokens if token not in stopwords]
    
    # Count frequencies
    keyword_counts = Counter(tokens)
    
    # Return top keywords
    return keyword_counts.most_common(max_keywords)

def segment_text(text: str, max_length: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Segment long text into chunks with optional overlap.
    
    Args:
        text: Input text
        max_length: Maximum chunk length
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text segments with metadata
    """
    if not text or len(text) <= max_length:
        return [{
            "text": text,
            "start": 0,
            "end": len(text),
            "chunk_id": 0,
            "total_chunks": 1
        }]
    
    segments = []
    start = 0
    chunk_id = 0
    
    while start < len(text):
        end = min(start + max_length, len(text))
        
        # Try to break at word boundary
        if end < len(text):
            # Look for the last space within the chunk
            last_space = text.rfind(' ', start, end)
            if last_space > start:
                end = last_space
        
        chunk_text = text[start:end]
        segments.append({
            "text": chunk_text,
            "start": start,
            "end": end,
            "chunk_id": chunk_id,
            "length": len(chunk_text)
        })
        
        # Move start position with overlap
        start = end - overlap
        chunk_id += 1
        
        # Ensure we don't go backwards
        if start <= segments[-1]["start"]:
            start = end
    
    # Add total chunks count to all segments
    for segment in segments:
        segment["total_chunks"] = len(segments)
    
    return segments