#!/usr/bin/env python3
"""
Custom exceptions for data analytics service
"""

class SemanticAnalysisError(Exception):
    """Exception raised during semantic analysis operations"""
    pass

class EmbeddingError(Exception):
    """Exception raised during embedding operations"""
    pass

class QueryMatchingError(Exception):
    """Exception raised during query matching operations"""
    pass

class SQLGenerationError(Exception):
    """Exception raised during SQL generation operations"""
    pass

class SQLExecutionError(Exception):
    """Exception raised during SQL execution operations"""
    pass