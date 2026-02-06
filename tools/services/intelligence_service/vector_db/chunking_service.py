#!/usr/bin/env python3
"""
Comprehensive Text Chunking Service

Provides multiple chunking strategies for different document types and use cases.
Integrates with the vector database and embedding services.
"""

from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import logging
from abc import ABC, abstractmethod
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


# ============ Configuration Classes ============

class ChunkingStrategy(Enum):
    """Available chunking strategies"""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    DOCUMENT_AWARE = "document_aware"
    CODE_AWARE = "code_aware"
    MARKDOWN_AWARE = "markdown_aware"
    SENTENCE_BASED = "sentence_based"
    TOKEN_BASED = "token_based"
    SLIDING_WINDOW = "sliding_window"
    HIERARCHICAL = "hierarchical"
    PARAGRAPH_BASED = "paragraph_based"
    TOPIC_BASED = "topic_based"
    HYBRID = "hybrid"


@dataclass
class ChunkConfig:
    """Configuration for chunking operations"""
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 1000  # Characters for most strategies, tokens for token-based
    chunk_overlap: int = 100
    min_chunk_size: int = 100
    max_chunk_size: int = 3000
    
    # Strategy-specific parameters
    separators: List[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""])
    keep_separator: bool = True
    strip_whitespace: bool = True
    
    # Semantic chunking parameters
    similarity_threshold: float = 0.7
    use_embeddings: bool = False
    embedding_model: Optional[str] = "text-embedding-3-small"
    
    # Document-aware parameters
    preserve_tables: bool = True
    preserve_lists: bool = True
    preserve_code_blocks: bool = True
    
    # Token-based parameters
    tokenizer: Optional[str] = "cl100k_base"  # For OpenAI models
    token_limit: int = 512
    
    # Hierarchical parameters
    hierarchy_levels: int = 3
    create_summaries: bool = False
    
    # Metadata
    add_metadata: bool = True
    metadata_fields: List[str] = field(default_factory=lambda: ["position", "source", "chunk_id", "parent_id"])


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    chunk_id: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    position: int = 0
    start_char: int = 0
    end_char: int = 0
    
    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique chunk ID based on content"""
        content_hash = hashlib.md5(self.text.encode()).hexdigest()[:8]
        return f"chunk_{self.position}_{content_hash}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary"""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "chunk_id": self.chunk_id,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "position": self.position,
            "start_char": self.start_char,
            "end_char": self.end_char
        }


# ============ Base Chunker Class ============

class BaseChunker(ABC):
    """Abstract base class for all chunking strategies"""
    
    def __init__(self, config: ChunkConfig):
        self.config = config
        self.chunks_created = 0
    
    @abstractmethod
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split text into chunks"""
        pass
    
    def _create_chunk(
        self, 
        text: str, 
        position: int, 
        start_char: int, 
        end_char: int,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None
    ) -> Chunk:
        """Create a chunk with metadata"""
        chunk_metadata = metadata or {}
        chunk_metadata.update({
            "strategy": self.config.strategy.value,
            "position": position,
            "created_at": datetime.now().isoformat()
        })
        
        chunk = Chunk(
            text=text.strip() if self.config.strip_whitespace else text,
            metadata=chunk_metadata,
            position=position,
            start_char=start_char,
            end_char=end_char,
            parent_id=parent_id
        )
        
        self.chunks_created += 1
        return chunk
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove zero-width characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        return text.strip()


# ============ Chunking Strategy Implementations ============

class FixedSizeChunker(BaseChunker):
    """Simple fixed-size chunking based on character count"""
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split text into fixed-size chunks"""
        chunks = []
        text_length = len(text)
        
        position = 0
        start = 0
        
        while start < text_length:
            # Calculate end position
            end = min(start + self.config.chunk_size, text_length)
            
            # Try to break at a word boundary
            if end < text_length:
                # Look for the last space before the chunk size
                last_space = text.rfind(' ', start, end)
                if last_space > start and last_space - start > self.config.min_chunk_size:
                    end = last_space
            
            chunk_text = text[start:end]
            
            if len(chunk_text.strip()) > 0:
                chunks.append(self._create_chunk(
                    chunk_text, position, start, end, metadata
                ))
                position += 1
            
            # Move to next chunk with overlap
            start = max(start + 1, end - self.config.chunk_overlap)
        
        return chunks


class SentenceChunker(BaseChunker):
    """Chunk text by sentences"""
    
    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        # Improved sentence detection pattern
        self.sentence_pattern = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z])|'  # Standard sentence endings
            r'(?<=\.\.\.)\s+|'           # Ellipsis
            r'(?<=[。！？])\s*'           # Chinese/Japanese punctuation
        )
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split text into sentence-based chunks"""
        # Split into sentences
        sentences = self.sentence_pattern.split(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        position = 0
        char_position = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence)
            
            # Check if adding this sentence would exceed chunk size
            if current_length + sentence_length > self.config.chunk_size and current_chunk:
                # Create chunk from accumulated sentences
                chunk_text = ' '.join(current_chunk)
                start_char = char_position - sum(len(s) + 1 for s in current_chunk)
                
                chunks.append(self._create_chunk(
                    chunk_text, position, start_char, char_position, metadata
                ))
                position += 1
                
                # Keep overlap sentences if configured
                if self.config.chunk_overlap > 0:
                    overlap_sentences = []
                    overlap_length = 0
                    for sent in reversed(current_chunk):
                        overlap_length += len(sent)
                        if overlap_length >= self.config.chunk_overlap:
                            break
                        overlap_sentences.insert(0, sent)
                    current_chunk = overlap_sentences
                    current_length = sum(len(s) for s in current_chunk)
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length
            char_position += sentence_length + 1
        
        # Add remaining sentences as final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            start_char = char_position - sum(len(s) + 1 for s in current_chunk)
            chunks.append(self._create_chunk(
                chunk_text, position, start_char, char_position, metadata
            ))
        
        return chunks


class RecursiveChunker(BaseChunker):
    """Recursively split text using multiple separators"""
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Recursively split text with fallback separators"""
        chunks = await self._recursive_split(text, self.config.separators, metadata)
        return self._merge_small_chunks(chunks)
    
    async def _recursive_split(
        self, 
        text: str, 
        separators: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Recursively split text using separators"""
        chunks = []
        
        # Base case: text is small enough
        if len(text) <= self.config.chunk_size:
            if text.strip():
                return [self._create_chunk(text, 0, 0, len(text), metadata)]
            return []
        
        # Try each separator
        for separator in separators:
            if separator in text:
                parts = text.split(separator)
                current_position = 0
                
                for i, part in enumerate(parts):
                    if not part.strip():
                        continue
                    
                    # Add separator back if configured
                    if self.config.keep_separator and i < len(parts) - 1:
                        part += separator
                    
                    # Recursively split if still too large
                    if len(part) > self.config.chunk_size:
                        sub_chunks = await self._recursive_split(
                            part,
                            separators[separators.index(separator) + 1:],
                            metadata
                        )
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(self._create_chunk(
                            part, len(chunks), current_position, 
                            current_position + len(part), metadata
                        ))
                    
                    current_position += len(part) + len(separator)
                
                return chunks
        
        # If no separator works, fall back to fixed size
        chunker = FixedSizeChunker(self.config)
        return await chunker.chunk(text, metadata)
    
    def _merge_small_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Merge chunks that are too small"""
        if not chunks:
            return chunks
        
        merged = []
        current = chunks[0]
        
        for next_chunk in chunks[1:]:
            combined_length = len(current.text) + len(next_chunk.text)
            
            if combined_length <= self.config.chunk_size and len(current.text) < self.config.min_chunk_size:
                # Merge chunks
                current.text += " " + next_chunk.text
                current.end_char = next_chunk.end_char
                current.children_ids.extend(next_chunk.children_ids)
            else:
                merged.append(current)
                current = next_chunk
        
        merged.append(current)
        
        # Update positions
        for i, chunk in enumerate(merged):
            chunk.position = i
        
        return merged


class MarkdownChunker(BaseChunker):
    """Chunk Markdown documents while preserving structure"""
    
    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        self.header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.code_block_pattern = re.compile(r'```[^`]*```', re.DOTALL)
        self.list_pattern = re.compile(r'^(\s*[-*+]|\s*\d+\.)\s+', re.MULTILINE)
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split Markdown text preserving structure"""
        chunks = []
        
        # Extract code blocks to preserve them
        code_blocks = []
        
        def replace_code_block(match):
            placeholder = f"__CODE_BLOCK_{len(code_blocks)}__"
            code_blocks.append(match.group(0))
            return placeholder
        
        text_with_placeholders = self.code_block_pattern.sub(replace_code_block, text)
        
        # Split by headers
        sections = self._split_by_headers(text_with_placeholders)
        
        position = 0
        for section in sections:
            # Restore code blocks
            for i, code_block in enumerate(code_blocks):
                section['content'] = section['content'].replace(f"__CODE_BLOCK_{i}__", code_block)
            
            # Check section size
            if len(section['content']) <= self.config.chunk_size:
                # Create single chunk for section
                chunk_metadata = metadata or {}
                chunk_metadata.update({
                    'section_level': section['level'],
                    'section_title': section['title']
                })
                
                chunks.append(self._create_chunk(
                    section['content'], position, 
                    section['start'], section['end'], 
                    chunk_metadata
                ))
                position += 1
            else:
                # Split large sections
                sub_chunks = await self._split_large_section(section, metadata)
                for sub_chunk in sub_chunks:
                    sub_chunk.position = position
                    chunks.append(sub_chunk)
                    position += 1
        
        return chunks
    
    def _split_by_headers(self, text: str) -> List[Dict[str, Any]]:
        """Split text by Markdown headers"""
        sections = []
        current_section = {
            'level': 0,
            'title': 'Introduction',
            'content': '',
            'start': 0,
            'end': 0
        }
        
        lines = text.split('\n')
        current_pos = 0
        
        for line in lines:
            header_match = self.header_pattern.match(line)
            
            if header_match:
                # Save current section if it has content
                if current_section['content'].strip():
                    current_section['end'] = current_pos
                    sections.append(current_section)
                
                # Start new section
                level = len(header_match.group(1))
                current_section = {
                    'level': level,
                    'title': header_match.group(2),
                    'content': line + '\n',
                    'start': current_pos,
                    'end': 0
                }
            else:
                current_section['content'] += line + '\n'
            
            current_pos += len(line) + 1
        
        # Add last section
        if current_section['content'].strip():
            current_section['end'] = current_pos
            sections.append(current_section)
        
        return sections
    
    async def _split_large_section(
        self, 
        section: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Split large Markdown section into smaller chunks"""
        # Use paragraph-based splitting for large sections
        paragraphs = section['content'].split('\n\n')
        
        chunks = []
        current_chunk = f"{'#' * section['level']} {section['title']}\n\n"
        current_length = len(current_chunk)
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_length = len(para)
            
            if current_length + para_length > self.config.chunk_size and current_chunk:
                chunk_metadata = metadata or {}
                chunk_metadata.update({
                    'section_level': section['level'],
                    'section_title': section['title']
                })
                
                chunks.append(self._create_chunk(
                    current_chunk, 0, 0, len(current_chunk), chunk_metadata
                ))
                
                # Start new chunk with section header for context
                current_chunk = f"{'#' * section['level']} {section['title']}\n\n"
                current_length = len(current_chunk)
            
            current_chunk += para + '\n\n'
            current_length += para_length + 2
        
        # Add remaining content
        if current_chunk.strip():
            chunk_metadata = metadata or {}
            chunk_metadata.update({
                'section_level': section['level'],
                'section_title': section['title']
            })
            
            chunks.append(self._create_chunk(
                current_chunk, 0, 0, len(current_chunk), chunk_metadata
            ))
        
        return chunks


class CodeChunker(BaseChunker):
    """Chunk code files while preserving syntax and structure"""
    
    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        # Patterns for different code structures
        self.function_patterns = {
            'python': re.compile(r'^(async\s+)?def\s+\w+\([^)]*\):', re.MULTILINE),
            'javascript': re.compile(r'^(async\s+)?function\s+\w+\([^)]*\)|^const\s+\w+\s*=\s*(async\s*)?\([^)]*\)\s*=>', re.MULTILINE),
            'java': re.compile(r'^(public|private|protected)?\s*(static\s+)?[\w<>]+\s+\w+\([^)]*\)', re.MULTILINE),
        }
        self.class_patterns = {
            'python': re.compile(r'^class\s+\w+(\([^)]*\))?:', re.MULTILINE),
            'javascript': re.compile(r'^class\s+\w+(\s+extends\s+\w+)?', re.MULTILINE),
            'java': re.compile(r'^(public\s+)?class\s+\w+', re.MULTILINE),
        }
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split code while preserving functions and classes"""
        # Detect language
        language = self._detect_language(text, metadata)
        
        if language in self.function_patterns:
            return await self._chunk_by_structure(text, language, metadata)
        else:
            # Fall back to line-aware chunking
            return await self._chunk_by_lines(text, metadata)
    
    def _detect_language(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Detect programming language"""
        if metadata and 'language' in metadata:
            return metadata['language']
        
        # Simple heuristics
        if 'import ' in text and 'from ' in text:
            return 'python'
        elif 'function ' in text or 'const ' in text:
            return 'javascript'
        elif 'public class' in text or 'public static void' in text:
            return 'java'
        
        return 'unknown'
    
    async def _chunk_by_structure(
        self, 
        text: str, 
        language: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Chunk code by structural elements (functions, classes)"""
        chunks = []
        
        # Find all functions and classes
        structures = []
        
        # Find classes
        if language in self.class_patterns:
            for match in self.class_patterns[language].finditer(text):
                structures.append({
                    'type': 'class',
                    'start': match.start(),
                    'match': match.group(0)
                })
        
        # Find functions
        if language in self.function_patterns:
            for match in self.function_patterns[language].finditer(text):
                structures.append({
                    'type': 'function',
                    'start': match.start(),
                    'match': match.group(0)
                })
        
        # Sort by position
        structures.sort(key=lambda x: x['start'])
        
        # Extract each structure
        position = 0
        last_end = 0
        
        for i, struct in enumerate(structures):
            # Get the content before this structure (imports, comments, etc.)
            if struct['start'] > last_end:
                prefix = text[last_end:struct['start']]
                if prefix.strip():
                    chunk_metadata = metadata or {}
                    chunk_metadata['code_type'] = 'preamble'
                    
                    chunks.append(self._create_chunk(
                        prefix, position, last_end, struct['start'], chunk_metadata
                    ))
                    position += 1
            
            # Find the end of this structure
            if i < len(structures) - 1:
                end = structures[i + 1]['start']
            else:
                end = len(text)
            
            # Extract structure content
            content = text[struct['start']:end]
            
            # Check if it needs further splitting
            if len(content) > self.config.chunk_size:
                # Split large functions/classes
                sub_chunks = await self._split_large_code_block(content, struct['type'], metadata)
                for sub_chunk in sub_chunks:
                    sub_chunk.position = position
                    chunks.append(sub_chunk)
                    position += 1
            else:
                chunk_metadata = metadata or {}
                chunk_metadata.update({
                    'code_type': struct['type'],
                    'signature': struct['match']
                })
                
                chunks.append(self._create_chunk(
                    content, position, struct['start'], end, chunk_metadata
                ))
                position += 1
            
            last_end = end
        
        # Add any remaining code
        if last_end < len(text):
            remainder = text[last_end:]
            if remainder.strip():
                chunk_metadata = metadata or {}
                chunk_metadata['code_type'] = 'remainder'
                
                chunks.append(self._create_chunk(
                    remainder, position, last_end, len(text), chunk_metadata
                ))
        
        return chunks
    
    async def _chunk_by_lines(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Chunk code by lines, preserving indentation blocks"""
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        position = 0
        char_position = 0
        chunk_start = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            # Check if adding this line would exceed chunk size
            if current_size + line_size > self.config.chunk_size and current_chunk:
                # Create chunk
                chunk_text = '\n'.join(current_chunk)
                chunks.append(self._create_chunk(
                    chunk_text, position, chunk_start, char_position, metadata
                ))
                position += 1
                
                # Handle overlap
                if self.config.chunk_overlap > 0:
                    # Keep last few lines for context
                    overlap_lines = []
                    overlap_size = 0
                    for l in reversed(current_chunk):
                        overlap_size += len(l) + 1
                        if overlap_size >= self.config.chunk_overlap:
                            break
                        overlap_lines.insert(0, l)
                    current_chunk = overlap_lines
                    current_size = overlap_size
                    chunk_start = char_position - overlap_size
                else:
                    current_chunk = []
                    current_size = 0
                    chunk_start = char_position
            
            current_chunk.append(line)
            current_size += line_size
            char_position += line_size
        
        # Add remaining lines
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append(self._create_chunk(
                chunk_text, position, chunk_start, char_position, metadata
            ))
        
        return chunks
    
    async def _split_large_code_block(
        self, 
        content: str, 
        code_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Split large code blocks intelligently"""
        # For now, use line-based splitting
        # TODO: Implement more intelligent splitting based on code structure
        return await self._chunk_by_lines(content, metadata)


class SemanticChunker(BaseChunker):
    """Chunk text based on semantic similarity between sentences"""
    
    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        self.embedding_generator = None
    
    async def _get_embedding_generator(self):
        """Lazy load embedding generator"""
        if self.embedding_generator is None:
            from tools.intelligent_tools.language.embedding_generator import EmbeddingGenerator
            self.embedding_generator = EmbeddingGenerator()
        return self.embedding_generator
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split text based on semantic boundaries"""
        # Split into sentences first
        sentence_chunker = SentenceChunker(self.config)
        sentence_chunks = await sentence_chunker.chunk(text, metadata)
        
        if not self.config.use_embeddings:
            # Fall back to sentence chunking if embeddings disabled
            return sentence_chunks
        
        # Generate embeddings for sentences
        embedder = await self._get_embedding_generator()
        sentence_texts = [chunk.text for chunk in sentence_chunks]
        
        try:
            embeddings = await embedder.embed_batch(
                sentence_texts,
                model=self.config.embedding_model
            )
        except Exception as e:
            logger.warning(f"Failed to generate embeddings: {e}. Falling back to sentence chunking.")
            return sentence_chunks
        
        # Group sentences by semantic similarity
        grouped_chunks = await self._group_by_similarity(
            sentence_chunks, embeddings, metadata
        )
        
        return grouped_chunks
    
    async def _group_by_similarity(
        self,
        sentences: List[Chunk],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Group sentences based on embedding similarity"""
        if not sentences or not embeddings:
            return sentences
        
        chunks = []
        current_group = [sentences[0]]
        current_embedding = embeddings[0]
        current_size = len(sentences[0].text)
        position = 0
        
        for i in range(1, len(sentences)):
            sentence = sentences[i]
            embedding = embeddings[i]
            
            # Calculate similarity
            similarity = self._cosine_similarity(current_embedding, embedding)
            
            # Check if we should add to current group
            should_add = (
                similarity >= self.config.similarity_threshold and
                current_size + len(sentence.text) <= self.config.chunk_size
            )
            
            if should_add:
                current_group.append(sentence)
                current_size += len(sentence.text)
                # Update group embedding (average)
                current_embedding = self._average_embeddings([current_embedding, embedding])
            else:
                # Create chunk from current group
                chunk_text = ' '.join([s.text for s in current_group])
                start_char = current_group[0].start_char
                end_char = current_group[-1].end_char
                
                chunk_metadata = metadata or {}
                chunk_metadata.update({
                    'sentence_count': len(current_group),
                    'avg_similarity': similarity
                })
                
                chunks.append(self._create_chunk(
                    chunk_text, position, start_char, end_char, chunk_metadata
                ))
                position += 1
                
                # Start new group
                current_group = [sentence]
                current_embedding = embedding
                current_size = len(sentence.text)
        
        # Add last group
        if current_group:
            chunk_text = ' '.join([s.text for s in current_group])
            start_char = current_group[0].start_char
            end_char = current_group[-1].end_char
            
            chunk_metadata = metadata or {}
            chunk_metadata['sentence_count'] = len(current_group)
            
            chunks.append(self._create_chunk(
                chunk_text, position, start_char, end_char, chunk_metadata
            ))
        
        return chunks
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Calculate average of multiple embeddings"""
        import numpy as np
        return np.mean(embeddings, axis=0).tolist()


class TokenChunker(BaseChunker):
    """Chunk text based on token count for LLM compatibility"""
    
    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        self.tokenizer = None
        self._init_tokenizer()
    
    def _init_tokenizer(self):
        """Initialize tokenizer based on configuration"""
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding(self.config.tokenizer or "cl100k_base")
        except (ImportError, ModuleNotFoundError):
            logger.info("tiktoken not available - using character-based approximation for token chunking")
            self.tokenizer = None
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split text based on token count"""
        if not self.tokenizer:
            # Fall back to character-based approximation
            return await self._approximate_token_chunking(text, metadata)
        
        # Encode text to tokens
        tokens = self.tokenizer.encode(text)
        total_tokens = len(tokens)
        
        chunks = []
        position = 0
        start_idx = 0
        
        while start_idx < total_tokens:
            # Calculate end index
            end_idx = min(start_idx + self.config.token_limit, total_tokens)
            
            # Get chunk tokens
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back to text
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            # Calculate character positions (approximate)
            start_char = len(self.tokenizer.decode(tokens[:start_idx]))
            end_char = len(self.tokenizer.decode(tokens[:end_idx]))
            
            chunks.append(self._create_chunk(
                chunk_text, position, start_char, end_char, metadata
            ))
            position += 1
            
            # Move to next chunk with overlap
            overlap_tokens = int(self.config.chunk_overlap * 0.25)  # Approximate chars to tokens
            start_idx = max(start_idx + 1, end_idx - overlap_tokens)
        
        return chunks
    
    async def _approximate_token_chunking(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Approximate token chunking using character count"""
        # Rough approximation: 1 token ≈ 4 characters for English
        char_limit = self.config.token_limit * 4
        char_overlap = int(self.config.chunk_overlap * 0.25 * 4)
        
        # Create a temporary config for fixed size chunking
        temp_config = ChunkConfig(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=char_limit,
            chunk_overlap=char_overlap
        )
        
        chunker = FixedSizeChunker(temp_config)
        return await chunker.chunk(text, metadata)


class HierarchicalChunker(BaseChunker):
    """Create hierarchical chunks for multi-level retrieval"""
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Create hierarchical chunks with parent-child relationships"""
        all_chunks = []
        
        # Level 0: Full document
        root_chunk = self._create_chunk(
            text[:self.config.max_chunk_size],
            0, 0, min(len(text), self.config.max_chunk_size),
            metadata
        )
        root_chunk.metadata['hierarchy_level'] = 0
        all_chunks.append(root_chunk)
        
        # Level 1: Major sections
        section_chunker = RecursiveChunker(ChunkConfig(
            chunk_size=self.config.chunk_size * 2,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n\n", "\n\n"]
        ))
        
        sections = await section_chunker.chunk(text, metadata)
        
        for section in sections:
            section.parent_id = root_chunk.chunk_id
            section.metadata['hierarchy_level'] = 1
            root_chunk.children_ids.append(section.chunk_id)
            all_chunks.append(section)
            
            # Level 2: Paragraphs within sections
            if len(section.text) > self.config.chunk_size:
                para_chunker = RecursiveChunker(self.config)
                paragraphs = await para_chunker.chunk(section.text, metadata)
                
                for para in paragraphs:
                    para.parent_id = section.chunk_id
                    para.metadata['hierarchy_level'] = 2
                    section.children_ids.append(para.chunk_id)
                    all_chunks.append(para)
        
        # Update positions
        for i, chunk in enumerate(all_chunks):
            chunk.position = i
        
        return all_chunks


class HybridChunker(BaseChunker):
    """Combine multiple chunking strategies based on content type"""
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Apply different chunking strategies based on content detection"""
        content_type = self._detect_content_type(text, metadata)
        
        # Select appropriate chunker
        if content_type == 'code':
            chunker = CodeChunker(self.config)
        elif content_type == 'markdown':
            chunker = MarkdownChunker(self.config)
        elif content_type == 'structured':
            chunker = HierarchicalChunker(self.config)
        else:
            # Default to recursive chunking
            chunker = RecursiveChunker(self.config)
        
        chunks = await chunker.chunk(text, metadata)
        
        # Add content type to metadata
        for chunk in chunks:
            chunk.metadata['content_type'] = content_type
        
        return chunks
    
    def _detect_content_type(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Detect the type of content"""
        if metadata and 'content_type' in metadata:
            return metadata['content_type']
        
        # Code detection
        code_indicators = ['def ', 'function ', 'class ', 'import ', 'const ', 'var ', 'let ']
        code_score = sum(1 for indicator in code_indicators if indicator in text)
        
        # Markdown detection
        md_indicators = ['# ', '## ', '```', '**', '[', ']', '![']
        md_score = sum(1 for indicator in md_indicators if indicator in text)
        
        # Structured detection (tables, lists, etc.)
        structure_indicators = ['\t', '|', '1.', '2.', '•', '◦']
        structure_score = sum(1 for indicator in structure_indicators if indicator in text)
        
        scores = {
            'code': code_score,
            'markdown': md_score,
            'structured': structure_score,
            'plain': 1  # Default score
        }
        
        return max(scores, key=scores.get)


# ============ Main Chunking Service ============

class ChunkingService:
    """Comprehensive chunking service with multiple strategies"""
    
    def __init__(self):
        self.strategies = {
            ChunkingStrategy.FIXED_SIZE: FixedSizeChunker,
            ChunkingStrategy.SENTENCE_BASED: SentenceChunker,
            ChunkingStrategy.RECURSIVE: RecursiveChunker,
            ChunkingStrategy.MARKDOWN_AWARE: MarkdownChunker,
            ChunkingStrategy.CODE_AWARE: CodeChunker,
            ChunkingStrategy.SEMANTIC: SemanticChunker,
            ChunkingStrategy.TOKEN_BASED: TokenChunker,
            ChunkingStrategy.HIERARCHICAL: HierarchicalChunker,
            ChunkingStrategy.HYBRID: HybridChunker,
        }
        
        self._chunker_cache = {}
    
    def get_chunker(self, config: ChunkConfig) -> BaseChunker:
        """Get a chunker instance based on configuration"""
        strategy = config.strategy
        
        # Check cache
        cache_key = f"{strategy.value}_{id(config)}"
        if cache_key in self._chunker_cache:
            return self._chunker_cache[cache_key]
        
        # Create new chunker
        if strategy not in self.strategies:
            logger.warning(f"Unknown strategy {strategy}, falling back to recursive")
            strategy = ChunkingStrategy.RECURSIVE
        
        chunker_class = self.strategies[strategy]
        chunker = chunker_class(config)
        
        # Cache it
        self._chunker_cache[cache_key] = chunker
        
        return chunker
    
    async def chunk_text(
        self,
        text: str,
        strategy: Union[str, ChunkingStrategy] = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Chunk]:
        """
        Chunk text using specified strategy
        
        Args:
            text: Text to chunk
            strategy: Chunking strategy to use
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            metadata: Additional metadata
            **kwargs: Strategy-specific parameters
            
        Returns:
            List of chunks
        """
        # Convert string strategy to enum
        if isinstance(strategy, str):
            try:
                strategy = ChunkingStrategy(strategy)
            except ValueError:
                logger.warning(f"Invalid strategy '{strategy}', using RECURSIVE")
                strategy = ChunkingStrategy.RECURSIVE
        
        # Create configuration
        config = ChunkConfig(
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            **kwargs
        )
        
        # Get chunker and process text
        chunker = self.get_chunker(config)
        chunks = await chunker.chunk(text, metadata)
        
        logger.info(
            f"Chunked text using {strategy.value}: "
            f"{len(text)} chars -> {len(chunks)} chunks"
        )
        
        return chunks
    
    async def chunk_document(
        self,
        file_path: str,
        strategy: Union[str, ChunkingStrategy] = ChunkingStrategy.HYBRID,
        **kwargs
    ) -> List[Chunk]:
        """
        Chunk a document file
        
        Args:
            file_path: Path to document
            strategy: Chunking strategy
            **kwargs: Additional parameters
            
        Returns:
            List of chunks
        """
        import os
        from pathlib import Path
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file content
        file_ext = Path(file_path).suffix.lower()
        
        # Detect content type from extension
        content_type = 'plain'
        if file_ext in ['.py', '.js', '.java', '.cpp', '.cs']:
            content_type = 'code'
        elif file_ext in ['.md', '.markdown']:
            content_type = 'markdown'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Add file metadata
        metadata = kwargs.pop('metadata', {})
        metadata.update({
            'source': file_path,
            'file_extension': file_ext,
            'content_type': content_type,
            'file_size': len(text)
        })
        
        return await self.chunk_text(
            text=text,
            strategy=strategy,
            metadata=metadata,
            **kwargs
        )
    
    async def chunk_batch(
        self,
        texts: List[str],
        strategy: Union[str, ChunkingStrategy] = ChunkingStrategy.RECURSIVE,
        max_concurrent: int = 5,
        **kwargs
    ) -> List[List[Chunk]]:
        """
        Chunk multiple texts in parallel
        
        Args:
            texts: List of texts to chunk
            strategy: Chunking strategy
            max_concurrent: Maximum concurrent operations
            **kwargs: Additional parameters
            
        Returns:
            List of chunk lists
        """
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def chunk_with_semaphore(text: str, index: int) -> List[Chunk]:
            async with semaphore:
                metadata = kwargs.get('metadata', {})
                metadata['batch_index'] = index
                return await self.chunk_text(
                    text=text,
                    strategy=strategy,
                    metadata=metadata,
                    **kwargs
                )
        
        tasks = [
            chunk_with_semaphore(text, i)
            for i, text in enumerate(texts)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle errors
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to chunk text {i}: {result}")
                final_results.append([])
            else:
                final_results.append(result)
        
        return final_results
    
    def get_optimal_strategy(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChunkingStrategy:
        """
        Recommend optimal chunking strategy based on content
        
        Args:
            text: Text to analyze
            metadata: Additional metadata
            
        Returns:
            Recommended chunking strategy
        """
        # Quick content analysis
        lines = text.split('\n')
        avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0
        
        # Check for code
        if any(keyword in text for keyword in ['def ', 'function ', 'class ', 'import ']):
            return ChunkingStrategy.CODE_AWARE
        
        # Check for markdown
        if any(marker in text for marker in ['# ', '## ', '```', '**']):
            return ChunkingStrategy.MARKDOWN_AWARE
        
        # Check for structured content
        if avg_line_length < 80 and len(lines) > 10:
            return ChunkingStrategy.HIERARCHICAL
        
        # Long form text
        if len(text) > 5000:
            return ChunkingStrategy.SEMANTIC
        
        # Default
        return ChunkingStrategy.RECURSIVE


# ============ Convenience Functions ============

# Global service instance
chunking_service = ChunkingService()

async def chunk(
    text: str,
    strategy: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Convenience function for chunking text
    
    Returns list of chunk dictionaries for easy integration
    """
    chunks = await chunking_service.chunk_text(
        text=text,
        strategy=strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs
    )
    
    return [chunk.to_dict() for chunk in chunks]

async def smart_chunk(text: str, **kwargs) -> List[Dict[str, Any]]:
    """
    Automatically select best chunking strategy
    """
    strategy = chunking_service.get_optimal_strategy(text)
    
    chunks = await chunking_service.chunk_text(
        text=text,
        strategy=strategy,
        **kwargs
    )
    
    return [chunk.to_dict() for chunk in chunks]