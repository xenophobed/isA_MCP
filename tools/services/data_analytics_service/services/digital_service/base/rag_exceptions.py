#!/usr/bin/env python3
"""
RAG Exceptions - RAG服务异常定义
"""

class RAGException(Exception):
    """RAG服务基础异常"""
    pass

class RAGValidationError(RAGException):
    """RAG验证异常"""
    pass

class RAGProcessingError(RAGException):
    """RAG处理异常"""
    pass

class RAGModeNotSupportedError(RAGException):
    """RAG模式不支持异常"""
    pass

class RAGConfigurationError(RAGException):
    """RAG配置异常"""
    pass
