#!/usr/bin/env python3
"""
Advanced Chunking Strategies

Specialized chunkers for specific use cases and document types.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import logging
from datetime import datetime
from chunking_service import BaseChunker, Chunk, ChunkConfig

logger = logging.getLogger(__name__)


class ParagraphChunker(BaseChunker):
    """Chunk text by paragraphs with intelligent merging"""
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split text by paragraphs and merge small ones"""
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk_text = ""
        current_chunk_start = 0
        position = 0
        char_position = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                char_position += 2  # Account for the double newline
                continue
            
            para_length = len(para)
            
            # Check if we should start a new chunk
            if current_chunk_text and (
                len(current_chunk_text) + para_length > self.config.chunk_size or
                (len(current_chunk_text) > self.config.min_chunk_size and 
                 self._is_topic_boundary(current_chunk_text, para))
            ):
                # Save current chunk
                chunks.append(self._create_chunk(
                    current_chunk_text, position, 
                    current_chunk_start, char_position - 2,
                    metadata
                ))
                position += 1
                
                # Start new chunk with overlap if configured
                if self.config.chunk_overlap > 0:
                    # Keep last part of previous chunk
                    overlap_start = max(0, len(current_chunk_text) - self.config.chunk_overlap)
                    current_chunk_text = current_chunk_text[overlap_start:] + "\n\n" + para
                else:
                    current_chunk_text = para
                    current_chunk_start = char_position
            else:
                # Add to current chunk
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para
                else:
                    current_chunk_text = para
                    current_chunk_start = char_position
            
            char_position += para_length + 2  # +2 for double newline
        
        # Add final chunk
        if current_chunk_text:
            chunks.append(self._create_chunk(
                current_chunk_text, position,
                current_chunk_start, char_position,
                metadata
            ))
        
        return chunks
    
    def _is_topic_boundary(self, current_text: str, new_text: str) -> bool:
        """Detect if there's a topic change between texts"""
        # Simple heuristic: Check for heading indicators
        heading_patterns = [
            r'^#{1,6}\s',  # Markdown headers
            r'^[A-Z][^.!?]*:$',  # Title-like patterns
            r'^\d+\.\s',  # Numbered sections
            r'^Chapter\s+\d+',  # Chapter markers
            r'^Section\s+\d+',  # Section markers
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, new_text):
                return True
        
        return False


class TopicChunker(BaseChunker):
    """Chunk text based on topic changes using embeddings"""
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split text based on detected topic boundaries"""
        # First, split into sentences
        sentences = self._split_sentences(text)
        
        if not sentences:
            return []
        
        # Generate embeddings if available
        embeddings = None
        if self.config.use_embeddings:
            try:
                from tools.intelligent_tools.language.embedding_generator import EmbeddingGenerator
                embedder = EmbeddingGenerator()
                embeddings = await embedder.embed_batch(
                    sentences,
                    model=self.config.embedding_model
                )
            except Exception as e:
                logger.warning(f"Could not generate embeddings: {e}")
        
        # Detect topic boundaries
        boundaries = self._detect_topic_boundaries(sentences, embeddings)
        
        # Create chunks from topic segments
        chunks = []
        position = 0
        char_position = 0
        
        for i, boundary_idx in enumerate(boundaries):
            start_idx = boundaries[i - 1] if i > 0 else 0
            end_idx = boundary_idx
            
            # Get sentences for this topic
            topic_sentences = sentences[start_idx:end_idx]
            if not topic_sentences:
                continue
            
            chunk_text = ' '.join(topic_sentences)
            
            # Split if too large
            if len(chunk_text) > self.config.chunk_size:
                sub_chunks = await self._split_large_topic(
                    topic_sentences, position, char_position, metadata
                )
                chunks.extend(sub_chunks)
                position += len(sub_chunks)
            else:
                chunks.append(self._create_chunk(
                    chunk_text, position, char_position,
                    char_position + len(chunk_text),
                    metadata
                ))
                position += 1
            
            char_position += len(chunk_text) + 1
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Improved sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _detect_topic_boundaries(
        self,
        sentences: List[str],
        embeddings: Optional[List[List[float]]] = None
    ) -> List[int]:
        """Detect topic boundaries in text"""
        boundaries = []
        
        if embeddings:
            # Use embedding similarity
            threshold = self.config.similarity_threshold
            
            for i in range(1, len(embeddings)):
                similarity = self._calculate_similarity(
                    embeddings[i - 1], embeddings[i]
                )
                
                # Topic boundary if similarity drops
                if similarity < threshold:
                    boundaries.append(i)
        else:
            # Use heuristics
            for i, sentence in enumerate(sentences):
                # Check for topic indicators
                if any([
                    re.match(r'^#{1,6}\s', sentence),  # Headers
                    re.match(r'^\d+\.\s', sentence),    # Numbered sections
                    re.match(r'^[A-Z][^.!?]*:$', sentence),  # Titles
                    len(sentence) < 50 and sentence.isupper(),  # All caps headers
                ]):
                    boundaries.append(i)
        
        # Add final boundary
        boundaries.append(len(sentences))
        
        return boundaries
    
    def _calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        import numpy as np
        
        vec1 = np.array(emb1)
        vec2 = np.array(emb2)
        
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    async def _split_large_topic(
        self,
        sentences: List[str],
        position: int,
        char_position: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Split a large topic into smaller chunks"""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.config.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    chunk_text, position + len(chunks),
                    char_position, char_position + len(chunk_text),
                    metadata
                ))
                
                current_chunk = []
                current_size = 0
                char_position += len(chunk_text) + 1
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Add remaining sentences
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(self._create_chunk(
                chunk_text, position + len(chunks),
                char_position, char_position + len(chunk_text),
                metadata
            ))
        
        return chunks


class SlidingWindowChunker(BaseChunker):
    """Chunk with a sliding window approach for maximum context preservation"""
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Create overlapping chunks with sliding window"""
        chunks = []
        text_length = len(text)
        
        # Calculate step size (chunk_size - overlap)
        step_size = max(1, self.config.chunk_size - self.config.chunk_overlap)
        
        position = 0
        start = 0
        
        while start < text_length:
            # Calculate end position
            end = min(start + self.config.chunk_size, text_length)
            
            # Adjust to word boundaries
            if end < text_length:
                # Find last complete word
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            # Extract chunk
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk_metadata = metadata or {}
                chunk_metadata['window_position'] = position
                chunk_metadata['overlap_ratio'] = self.config.chunk_overlap / self.config.chunk_size
                
                chunks.append(self._create_chunk(
                    chunk_text, position, start, end, chunk_metadata
                ))
                position += 1
            
            # Slide window
            start += step_size
            
            # Ensure we don't miss the end
            if start < text_length and start + self.config.chunk_size >= text_length:
                start = text_length - self.config.chunk_size
        
        return chunks


class TableAwareChunker(BaseChunker):
    """Chunk text while preserving table structures"""
    
    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        # Pattern to detect tables (Markdown, CSV-like, etc.)
        self.table_patterns = [
            re.compile(r'^\|.*\|$', re.MULTILINE),  # Markdown tables
            re.compile(r'^[\w\s,]+\t[\w\s,]+', re.MULTILINE),  # Tab-separated
            re.compile(r'^\s*\w+\s*,\s*\w+', re.MULTILINE),  # CSV-like
        ]
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split text while keeping tables intact"""
        # Find all tables in the text
        tables = self._extract_tables(text)
        
        # Split text preserving tables
        chunks = []
        position = 0
        current_pos = 0
        
        for table_start, table_end, table_text in tables:
            # Process text before table
            if current_pos < table_start:
                before_text = text[current_pos:table_start]
                before_chunks = await self._chunk_regular_text(
                    before_text, position, current_pos, metadata
                )
                chunks.extend(before_chunks)
                position += len(before_chunks)
            
            # Add table as a single chunk (or split if too large)
            if len(table_text) <= self.config.chunk_size:
                table_metadata = metadata or {}
                table_metadata['contains_table'] = True
                
                chunks.append(self._create_chunk(
                    table_text, position, table_start, table_end, table_metadata
                ))
                position += 1
            else:
                # Split large table by rows
                table_chunks = await self._split_large_table(
                    table_text, position, table_start, metadata
                )
                chunks.extend(table_chunks)
                position += len(table_chunks)
            
            current_pos = table_end
        
        # Process remaining text
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            remaining_chunks = await self._chunk_regular_text(
                remaining_text, position, current_pos, metadata
            )
            chunks.extend(remaining_chunks)
        
        return chunks
    
    def _extract_tables(self, text: str) -> List[Tuple[int, int, str]]:
        """Extract table regions from text"""
        tables = []
        
        # Find Markdown tables
        lines = text.split('\n')
        in_table = False
        table_start = 0
        table_lines = []
        char_pos = 0
        
        for i, line in enumerate(lines):
            is_table_line = bool(re.match(r'^\|.*\|$', line))
            
            if is_table_line and not in_table:
                # Start of table
                in_table = True
                table_start = char_pos
                table_lines = [line]
            elif in_table and is_table_line:
                # Continue table
                table_lines.append(line)
            elif in_table and not is_table_line:
                # End of table
                table_text = '\n'.join(table_lines)
                tables.append((table_start, char_pos - 1, table_text))
                in_table = False
                table_lines = []
            
            char_pos += len(line) + 1  # +1 for newline
        
        # Handle table at end of text
        if in_table and table_lines:
            table_text = '\n'.join(table_lines)
            tables.append((table_start, char_pos, table_text))
        
        return tables
    
    async def _chunk_regular_text(
        self,
        text: str,
        start_position: int,
        char_offset: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Chunk non-table text"""
        if not text.strip():
            return []
        
        # Use recursive chunking for regular text
        from chunking_service import RecursiveChunker
        chunker = RecursiveChunker(self.config)
        chunks = await chunker.chunk(text, metadata)
        
        # Adjust positions
        for i, chunk in enumerate(chunks):
            chunk.position = start_position + i
            chunk.start_char += char_offset
            chunk.end_char += char_offset
        
        return chunks
    
    async def _split_large_table(
        self,
        table_text: str,
        position: int,
        char_offset: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Split large tables by rows while preserving headers"""
        lines = table_text.split('\n')
        
        # Assume first 2-3 lines are headers
        header_lines = lines[:3] if len(lines) > 3 else lines[:1]
        header_text = '\n'.join(header_lines)
        
        chunks = []
        current_chunk = header_text
        current_size = len(header_text)
        
        for line in lines[len(header_lines):]:
            line_size = len(line) + 1
            
            if current_size + line_size > self.config.chunk_size and current_chunk != header_text:
                # Save current chunk
                table_metadata = metadata or {}
                table_metadata['contains_table'] = True
                table_metadata['is_partial_table'] = True
                
                chunks.append(self._create_chunk(
                    current_chunk, position + len(chunks),
                    char_offset, char_offset + len(current_chunk),
                    table_metadata
                ))
                
                # Start new chunk with headers
                current_chunk = header_text + '\n' + line
                current_size = len(current_chunk)
            else:
                current_chunk += '\n' + line
                current_size += line_size
        
        # Add final chunk
        if current_chunk and current_chunk != header_text:
            table_metadata = metadata or {}
            table_metadata['contains_table'] = True
            table_metadata['is_partial_table'] = len(chunks) > 0
            
            chunks.append(self._create_chunk(
                current_chunk, position + len(chunks),
                char_offset, char_offset + len(current_chunk),
                table_metadata
            ))
        
        return chunks


class ConversationChunker(BaseChunker):
    """Chunk conversational data (chat logs, interviews, etc.)"""
    
    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        # Patterns for detecting speakers/turns
        self.speaker_patterns = [
            re.compile(r'^([A-Z][A-Za-z]+):\s*(.*)$'),  # "Name: message"
            re.compile(r'^\[([^\]]+)\]\s*(.*)$'),  # "[Name] message"
            re.compile(r'^<([^>]+)>\s*(.*)$'),  # "<Name> message"
        ]
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split conversation by turns and logical breaks"""
        # Extract conversation turns
        turns = self._extract_turns(text)
        
        if not turns:
            # Fall back to paragraph chunking
            para_chunker = ParagraphChunker(self.config)
            return await para_chunker.chunk(text, metadata)
        
        # Group turns into chunks
        chunks = []
        current_chunk_turns = []
        current_size = 0
        position = 0
        
        for turn in turns:
            turn_text = f"{turn['speaker']}: {turn['message']}"
            turn_size = len(turn_text)
            
            # Check if we should start a new chunk
            if current_size + turn_size > self.config.chunk_size and current_chunk_turns:
                # Create chunk from current turns
                chunk_text = '\n'.join([
                    f"{t['speaker']}: {t['message']}"
                    for t in current_chunk_turns
                ])
                
                conv_metadata = metadata or {}
                conv_metadata.update({
                    'conversation_turns': len(current_chunk_turns),
                    'speakers': list(set(t['speaker'] for t in current_chunk_turns))
                })
                
                chunks.append(self._create_chunk(
                    chunk_text, position, 0, len(chunk_text), conv_metadata
                ))
                position += 1
                
                # Keep context with overlap
                if self.config.chunk_overlap > 0:
                    # Keep last few turns
                    overlap_turns = []
                    overlap_size = 0
                    for t in reversed(current_chunk_turns):
                        t_size = len(f"{t['speaker']}: {t['message']}")
                        if overlap_size + t_size > self.config.chunk_overlap:
                            break
                        overlap_turns.insert(0, t)
                        overlap_size += t_size
                    current_chunk_turns = overlap_turns
                    current_size = overlap_size
                else:
                    current_chunk_turns = []
                    current_size = 0
            
            current_chunk_turns.append(turn)
            current_size += turn_size
        
        # Add final chunk
        if current_chunk_turns:
            chunk_text = '\n'.join([
                f"{t['speaker']}: {t['message']}"
                for t in current_chunk_turns
            ])
            
            conv_metadata = metadata or {}
            conv_metadata.update({
                'conversation_turns': len(current_chunk_turns),
                'speakers': list(set(t['speaker'] for t in current_chunk_turns))
            })
            
            chunks.append(self._create_chunk(
                chunk_text, position, 0, len(chunk_text), conv_metadata
            ))
        
        return chunks
    
    def _extract_turns(self, text: str) -> List[Dict[str, Any]]:
        """Extract conversation turns from text"""
        turns = []
        lines = text.split('\n')
        
        current_speaker = None
        current_message = []
        
        for line in lines:
            # Check if this is a new speaker
            speaker_found = False
            for pattern in self.speaker_patterns:
                match = pattern.match(line)
                if match:
                    # Save previous turn
                    if current_speaker and current_message:
                        turns.append({
                            'speaker': current_speaker,
                            'message': ' '.join(current_message).strip()
                        })
                    
                    # Start new turn
                    current_speaker = match.group(1)
                    current_message = [match.group(2)] if match.group(2) else []
                    speaker_found = True
                    break
            
            if not speaker_found and current_speaker:
                # Continue current turn
                current_message.append(line)
        
        # Add final turn
        if current_speaker and current_message:
            turns.append({
                'speaker': current_speaker,
                'message': ' '.join(current_message).strip()
            })
        
        return turns


class JSONChunker(BaseChunker):
    """Chunk JSON data while preserving structure"""
    
    async def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split JSON data into logical chunks"""
        try:
            import json
            data = json.loads(text)
            
            # Convert to chunks based on structure
            if isinstance(data, list):
                return await self._chunk_json_array(data, metadata)
            elif isinstance(data, dict):
                return await self._chunk_json_object(data, metadata)
            else:
                # Simple value
                return [self._create_chunk(
                    json.dumps(data, indent=2), 0, 0, len(text), metadata
                )]
                
        except json.JSONDecodeError:
            # Not valid JSON, fall back to regular chunking
            logger.warning("Invalid JSON, falling back to recursive chunking")
            from chunking_service import RecursiveChunker
            chunker = RecursiveChunker(self.config)
            return await chunker.chunk(text, metadata)
    
    async def _chunk_json_array(
        self,
        data: list,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Chunk JSON array"""
        import json
        
        chunks = []
        current_items = []
        current_size = 2  # For "[]"
        position = 0
        
        for item in data:
            item_json = json.dumps(item, indent=2)
            item_size = len(item_json) + 1  # +1 for comma
            
            if current_size + item_size > self.config.chunk_size and current_items:
                # Create chunk
                chunk_data = current_items
                chunk_json = json.dumps(chunk_data, indent=2)
                
                json_metadata = metadata or {}
                json_metadata.update({
                    'json_type': 'array',
                    'item_count': len(chunk_data)
                })
                
                chunks.append(self._create_chunk(
                    chunk_json, position, 0, len(chunk_json), json_metadata
                ))
                position += 1
                
                current_items = []
                current_size = 2
            
            current_items.append(item)
            current_size += item_size
        
        # Add remaining items
        if current_items:
            chunk_json = json.dumps(current_items, indent=2)
            
            json_metadata = metadata or {}
            json_metadata.update({
                'json_type': 'array',
                'item_count': len(current_items)
            })
            
            chunks.append(self._create_chunk(
                chunk_json, position, 0, len(chunk_json), json_metadata
            ))
        
        return chunks
    
    async def _chunk_json_object(
        self,
        data: dict,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Chunk JSON object"""
        import json
        
        chunks = []
        current_obj = {}
        current_size = 2  # For "{}"
        position = 0
        
        for key, value in data.items():
            item_json = json.dumps({key: value}, indent=2)
            item_size = len(item_json)
            
            if current_size + item_size > self.config.chunk_size and current_obj:
                # Create chunk
                chunk_json = json.dumps(current_obj, indent=2)
                
                json_metadata = metadata or {}
                json_metadata.update({
                    'json_type': 'object',
                    'key_count': len(current_obj),
                    'keys': list(current_obj.keys())
                })
                
                chunks.append(self._create_chunk(
                    chunk_json, position, 0, len(chunk_json), json_metadata
                ))
                position += 1
                
                current_obj = {}
                current_size = 2
            
            current_obj[key] = value
            current_size += item_size
        
        # Add remaining items
        if current_obj:
            chunk_json = json.dumps(current_obj, indent=2)
            
            json_metadata = metadata or {}
            json_metadata.update({
                'json_type': 'object',
                'key_count': len(current_obj),
                'keys': list(current_obj.keys())
            })
            
            chunks.append(self._create_chunk(
                chunk_json, position, 0, len(chunk_json), json_metadata
            ))
        
        return chunks