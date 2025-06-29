#!/usr/bin/env python3
"""
In-Memory RAG Service using ChromaDB

Provides simple document ingestion and question-answering capabilities
using ChromaDB as the vector store and local embedding models.
"""

from .memory_rag import MemoryRAGService, RAGSession
from .document_processor import DocumentProcessor as RAGDocumentProcessor

__all__ = [
    "MemoryRAGService",
    "RAGSession", 
    "RAGDocumentProcessor"
]

__version__ = "1.0.0"