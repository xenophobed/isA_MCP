#!/usr/bin/env python3
"""
Embedding Integration Module

Handles embedding generation and text processing
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class EmbeddingIntegration:
    """Embedding Generation Integration Manager"""
    
    def __init__(self):
        self._embedding_generator = None
    
    @property
    def embedding_generator(self):
        """Lazy load embedding generator"""
        if self._embedding_generator is None:
            try:
                from tools.services.intelligence_service.language.embedding_generator import embedding_generator
                self._embedding_generator = embedding_generator
                logger.info("Embedding generator initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize embedding generator: {e}")
                self._embedding_generator = self._create_mock_embedding_generator()
        return self._embedding_generator
    
    def _create_mock_embedding_generator(self):
        """Create a mock embedding generator for testing"""
        class MockEmbeddingGenerator:
            def __init__(self):
                self.name = "MockEmbeddingGenerator"
            
            async def embed(self, text: str) -> List[float]:
                """Return a mock embedding"""
                return [0.1] * 1536  # Mock 1536-dimensional embedding
            
            async def chunk_text(self, text: str, chunk_size: int = 400, 
                               overlap: int = 50, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
                """Simple text chunking"""
                chunks = []
                start = 0
                while start < len(text):
                    end = min(start + chunk_size, len(text))
                    chunk_text = text[start:end]
                    chunks.append({
                        'text': chunk_text,
                        'metadata': metadata or {},
                        'start': start,
                        'end': end
                    })
                    start = end - overlap
                return chunks
        
        logger.warning("Using mock embedding generator due to initialization failure")
        return MockEmbeddingGenerator()
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            return await self.embedding_generator.embed(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * 1536  # Return zero vector on failure
    
    async def chunk_text(self, text: str, chunk_size: int = 400, 
                        overlap: int = 50, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Chunk text into smaller pieces"""
        try:
            return await self.embedding_generator.chunk_text(text, chunk_size, overlap, metadata)
        except Exception as e:
            logger.error(f"Failed to chunk text: {e}")
            # Fallback to simple chunking
            return self._simple_chunk_text(text, chunk_size, overlap, metadata)
    
    def _simple_chunk_text(self, text: str, chunk_size: int, overlap: int, 
                          metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Simple text chunking fallback"""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            chunks.append({
                'text': chunk_text,
                'metadata': metadata or {},
                'start': start,
                'end': end
            })
            start = end - overlap
        return chunks












