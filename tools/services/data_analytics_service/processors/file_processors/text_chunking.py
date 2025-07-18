#!/usr/bin/env python3
"""
Text Chunking Processor - Advanced Text Splitting and Chunking

Provides intelligent text chunking strategies for optimal embedding and retrieval.
Supports multiple chunking methods including sentence-based, paragraph-based, and token-based splitting.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ChunkingStrategy(Enum):
    """Available chunking strategies."""
    CHARACTER = "character"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    TOKEN = "token"
    SEMANTIC = "semantic"

@dataclass
class ChunkConfig:
    """Configuration for text chunking."""
    strategy: ChunkingStrategy = ChunkingStrategy.CHARACTER
    chunk_size: int = 400
    overlap: int = 50
    min_chunk_size: int = 50
    max_chunk_size: int = 1000
    preserve_sentences: bool = True
    preserve_paragraphs: bool = False
    respect_word_boundaries: bool = True

@dataclass
class TextChunk:
    """Represents a text chunk with metadata."""
    text: str
    index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]
    overlap_with_previous: int = 0
    overlap_with_next: int = 0

class TextChunkingProcessor:
    """
    Advanced text chunking processor with multiple strategies.
    
    Features:
    - Multiple chunking strategies (character, sentence, paragraph, token)
    - Intelligent overlap handling
    - Sentence and paragraph boundary preservation
    - Configurable chunk sizes and overlap
    - Rich metadata for each chunk
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        Initialize text chunking processor.
        
        Args:
            config: Chunking configuration
        """
        self.config = config or ChunkConfig()
        
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]+(?:\s+|$)')
        self.paragraph_pattern = re.compile(r'\n\s*\n')
        
        logger.info(f"Text chunking processor initialized with strategy: {self.config.strategy.value}")
    
    def chunk_text(self, 
                   text: str, 
                   metadata: Optional[Dict[str, Any]] = None,
                   config: Optional[ChunkConfig] = None) -> List[TextChunk]:
        """
        Chunk text using the configured strategy.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to include with chunks
            config: Optional config override
            
        Returns:
            List of text chunks with metadata
        """
        if not text or not text.strip():
            return []
        
        config = config or self.config
        metadata = metadata or {}
        
        # Clean text
        text = self._clean_text(text)
        
        # Choose chunking strategy
        if config.strategy == ChunkingStrategy.CHARACTER:
            chunks = self._chunk_by_character(text, config)
        elif config.strategy == ChunkingStrategy.SENTENCE:
            chunks = self._chunk_by_sentence(text, config)
        elif config.strategy == ChunkingStrategy.PARAGRAPH:
            chunks = self._chunk_by_paragraph(text, config)
        elif config.strategy == ChunkingStrategy.TOKEN:
            chunks = self._chunk_by_token(text, config)
        elif config.strategy == ChunkingStrategy.SEMANTIC:
            chunks = self._chunk_by_semantic(text, config)
        else:
            chunks = self._chunk_by_character(text, config)
        
        # Add metadata to chunks
        for i, chunk in enumerate(chunks):
            chunk.metadata.update(metadata)
            chunk.metadata.update({
                'chunking_strategy': config.strategy.value,
                'chunk_size': config.chunk_size,
                'overlap': config.overlap,
                'total_chunks': len(chunks),
                'original_text_length': len(text)
            })
        
        logger.info(f"Chunked text into {len(chunks)} chunks using {config.strategy.value} strategy")
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
    
    def _chunk_by_character(self, text: str, config: ChunkConfig) -> List[TextChunk]:
        """Chunk text by character count with overlap."""
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Calculate end position
            end = min(start + config.chunk_size, len(text))
            
            # Respect word boundaries if configured
            if config.respect_word_boundaries and end < len(text):
                # Find last word boundary
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            # Respect sentence boundaries if configured
            if config.preserve_sentences and end < len(text):
                # Look for sentence ending near the end
                sentence_end = self._find_sentence_boundary(text, start, end)
                if sentence_end:
                    end = sentence_end
            
            # Extract chunk text
            chunk_text = text[start:end].strip()
            
            # Skip if chunk is too small
            if len(chunk_text) < config.min_chunk_size and start > 0:
                break
            
            # Calculate overlaps
            overlap_prev = config.overlap if chunk_index > 0 else 0
            overlap_next = config.overlap if end < len(text) else 0
            
            chunks.append(TextChunk(
                text=chunk_text,
                index=chunk_index,
                start_char=start,
                end_char=end,
                metadata={},
                overlap_with_previous=overlap_prev,
                overlap_with_next=overlap_next
            ))
            
            # Move to next chunk with overlap
            start = max(start + 1, end - config.overlap)
            chunk_index += 1
        
        return chunks
    
    def _chunk_by_sentence(self, text: str, config: ChunkConfig) -> List[TextChunk]:
        """Chunk text by sentences."""
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = ""
        current_sentences = []
        chunk_index = 0
        char_start = 0
        
        for sentence in sentences:
            # Check if adding this sentence would exceed chunk size
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) > config.chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_text = current_chunk.strip()
                char_end = char_start + len(chunk_text)
                
                chunks.append(TextChunk(
                    text=chunk_text,
                    index=chunk_index,
                    start_char=char_start,
                    end_char=char_end,
                    metadata={'sentences': current_sentences.copy()}
                ))
                
                # Start new chunk with overlap
                overlap_sentences = current_sentences[-1:] if config.overlap > 0 else []
                current_chunk = " ".join(overlap_sentences)
                current_sentences = overlap_sentences.copy()
                char_start = char_end - len(current_chunk)
                chunk_index += 1
            
            # Add sentence to current chunk
            current_chunk = potential_chunk
            current_sentences.append(sentence)
        
        # Add final chunk if it exists
        if current_chunk.strip():
            chunks.append(TextChunk(
                text=current_chunk.strip(),
                index=chunk_index,
                start_char=char_start,
                end_char=char_start + len(current_chunk),
                metadata={'sentences': current_sentences}
            ))
        
        return chunks
    
    def _chunk_by_paragraph(self, text: str, config: ChunkConfig) -> List[TextChunk]:
        """Chunk text by paragraphs."""
        paragraphs = self.paragraph_pattern.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = ""
        current_paragraphs = []
        chunk_index = 0
        char_start = 0
        
        for paragraph in paragraphs:
            potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if len(potential_chunk) > config.chunk_size and current_chunk:
                # Create chunk from current paragraphs
                chunk_text = current_chunk.strip()
                char_end = char_start + len(chunk_text)
                
                chunks.append(TextChunk(
                    text=chunk_text,
                    index=chunk_index,
                    start_char=char_start,
                    end_char=char_end,
                    metadata={'paragraphs': current_paragraphs.copy()}
                ))
                
                # Start new chunk with overlap
                overlap_paragraphs = current_paragraphs[-1:] if config.overlap > 0 else []
                current_chunk = "\n\n".join(overlap_paragraphs)
                current_paragraphs = overlap_paragraphs.copy()
                char_start = char_end - len(current_chunk)
                chunk_index += 1
            
            # Add paragraph to current chunk
            current_chunk = potential_chunk
            current_paragraphs.append(paragraph)
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(TextChunk(
                text=current_chunk.strip(),
                index=chunk_index,
                start_char=char_start,
                end_char=char_start + len(current_chunk),
                metadata={'paragraphs': current_paragraphs}
            ))
        
        return chunks
    
    def _chunk_by_token(self, text: str, config: ChunkConfig) -> List[TextChunk]:
        """Chunk text by approximate token count (words)."""
        words = text.split()
        chunks = []
        chunk_index = 0
        
        # Approximate tokens per chunk (1 token H 0.75 words)
        words_per_chunk = int(config.chunk_size * 0.75)
        overlap_words = int(config.overlap * 0.75)
        
        start_word = 0
        
        while start_word < len(words):
            end_word = min(start_word + words_per_chunk, len(words))
            
            # Extract chunk words
            chunk_words = words[start_word:end_word]
            chunk_text = " ".join(chunk_words)
            
            # Calculate character positions (approximate)
            char_start = len(" ".join(words[:start_word])) + (1 if start_word > 0 else 0)
            char_end = char_start + len(chunk_text)
            
            chunks.append(TextChunk(
                text=chunk_text,
                index=chunk_index,
                start_char=char_start,
                end_char=char_end,
                metadata={
                    'word_count': len(chunk_words),
                    'start_word': start_word,
                    'end_word': end_word
                }
            ))
            
            # Move to next chunk with overlap
            start_word = max(start_word + 1, end_word - overlap_words)
            chunk_index += 1
        
        return chunks
    
    def _chunk_by_semantic(self, text: str, config: ChunkConfig) -> List[TextChunk]:
        """Chunk text by semantic boundaries (fallback to sentence-based)."""
        # For now, use sentence-based chunking as semantic baseline
        # In a full implementation, this could use NLP models to find semantic boundaries
        return self._chunk_by_sentence(text, config)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            
            # Check for sentence ending
            if char in '.!?':
                # Look ahead to see if this is really a sentence ending
                if self._is_sentence_end(current_sentence):
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
        
        # Add remaining text as sentence
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return [s for s in sentences if s]
    
    def _is_sentence_end(self, text: str) -> bool:
        """Check if text ends with a sentence boundary."""
        text = text.strip()
        if not text:
            return False
        
        # Simple heuristics for sentence ending
        last_char = text[-1]
        if last_char not in '.!?':
            return False
        
        # Avoid common abbreviations
        common_abbrevs = ['Mr.', 'Mrs.', 'Dr.', 'Prof.', 'Inc.', 'Ltd.', 'etc.', 'vs.']
        for abbrev in common_abbrevs:
            if text.endswith(abbrev):
                return False
        
        return True
    
    def _find_sentence_boundary(self, text: str, start: int, end: int) -> Optional[int]:
        """Find the nearest sentence boundary before the end position."""
        # Look for sentence endings in the last part of the chunk
        search_start = max(start, end - 100)  # Look in last 100 chars
        
        matches = list(self.sentence_endings.finditer(text, search_start, end))
        if matches:
            return matches[-1].end()
        
        return None
    
    def merge_chunks(self, chunks: List[TextChunk], max_size: int) -> List[TextChunk]:
        """Merge small chunks together up to max_size."""
        if not chunks:
            return []
        
        merged_chunks = []
        current_chunk = chunks[0]
        
        for next_chunk in chunks[1:]:
            # Check if we can merge
            potential_text = current_chunk.text + " " + next_chunk.text
            
            if len(potential_text) <= max_size:
                # Merge chunks
                current_chunk = TextChunk(
                    text=potential_text,
                    index=current_chunk.index,
                    start_char=current_chunk.start_char,
                    end_char=next_chunk.end_char,
                    metadata={
                        **current_chunk.metadata,
                        'merged_from': [current_chunk.index, next_chunk.index]
                    }
                )
            else:
                # Can't merge, add current chunk and start new one
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk
        
        # Add the last chunk
        merged_chunks.append(current_chunk)
        
        # Reindex chunks
        for i, chunk in enumerate(merged_chunks):
            chunk.index = i
        
        return merged_chunks
    
    def get_chunk_stats(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Get statistics about the chunks."""
        if not chunks:
            return {'total_chunks': 0}
        
        chunk_sizes = [len(chunk.text) for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'total_characters': sum(chunk_sizes),
            'avg_chunk_size': sum(chunk_sizes) / len(chunks),
            'min_chunk_size': min(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'strategy_used': chunks[0].metadata.get('chunking_strategy', 'unknown')
        }

# Convenience functions
def chunk_text_simple(text: str, 
                     chunk_size: int = 400, 
                     overlap: int = 50,
                     strategy: ChunkingStrategy = ChunkingStrategy.CHARACTER) -> List[Dict[str, Any]]:
    """
    Simple text chunking function.
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk
        overlap: Overlap between chunks
        strategy: Chunking strategy
        
    Returns:
        List of chunk dictionaries
    """
    config = ChunkConfig(
        strategy=strategy,
        chunk_size=chunk_size,
        overlap=overlap
    )
    
    processor = TextChunkingProcessor(config)
    chunks = processor.chunk_text(text)
    
    return [{
        'text': chunk.text,
        'index': chunk.index,
        'start_char': chunk.start_char,
        'end_char': chunk.end_char,
        'metadata': chunk.metadata
    } for chunk in chunks]

def smart_chunk_text(text: str, 
                    target_size: int = 400,
                    max_size: int = 600,
                    preserve_sentences: bool = True) -> List[Dict[str, Any]]:
    """
    Smart text chunking with automatic strategy selection.
    
    Args:
        text: Text to chunk
        target_size: Target chunk size
        max_size: Maximum chunk size
        preserve_sentences: Whether to preserve sentence boundaries
        
    Returns:
        List of chunk dictionaries
    """
    # Choose strategy based on text characteristics
    if '\n\n' in text and len(text) > 1000:
        strategy = ChunkingStrategy.PARAGRAPH
    elif preserve_sentences and len(text) > 500:
        strategy = ChunkingStrategy.SENTENCE
    else:
        strategy = ChunkingStrategy.CHARACTER
    
    config = ChunkConfig(
        strategy=strategy,
        chunk_size=target_size,
        overlap=50,
        max_chunk_size=max_size,
        preserve_sentences=preserve_sentences
    )
    
    processor = TextChunkingProcessor(config)
    chunks = processor.chunk_text(text)
    
    # Merge small chunks if needed
    chunks = processor.merge_chunks(chunks, max_size)
    
    return [{
        'text': chunk.text,
        'index': chunk.index,
        'start_char': chunk.start_char,
        'end_char': chunk.end_char,
        'metadata': chunk.metadata
    } for chunk in chunks]