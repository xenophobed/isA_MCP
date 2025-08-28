#!/usr/bin/env python3
"""
Text Processor

Handles plain text and markdown files for digital asset processing.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TextAnalysisResult:
    """Text analysis result"""
    text: str
    word_count: int
    character_count: int
    line_count: int
    language: str
    encoding: str
    file_type: str
    processing_time: float

class TextProcessor:
    """
    Text processor for plain text and markdown files.
    
    Capabilities:
    - Text extraction and encoding detection
    - Word and character count analysis
    - Language detection (basic)
    - Markdown parsing (if applicable)
    - Content structure analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Processing settings
        self.max_file_size_mb = self.config.get('max_file_size_mb', 50)
        self.default_encoding = self.config.get('default_encoding', 'utf-8')
        self.enable_language_detection = self.config.get('enable_language_detection', False)
    
    async def analyze_text(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze text file.
        
        Args:
            file_path: Path to text file
            options: Analysis options
            
        Returns:
            Text analysis results
        """
        try:
            options = options or {}
            
            # Validate file
            if not Path(file_path).exists():
                return {'error': 'Text file not found', 'success': False}
            
            # Check file size
            file_size = Path(file_path).stat().st_size
            if file_size > self.max_file_size_mb * 1024 * 1024:
                return {'error': f'File too large (>{self.max_file_size_mb}MB)', 'success': False}
            
            # Read and analyze text
            text_result = await self._read_and_analyze_text(file_path, options)
            
            # Additional analysis based on file type
            file_extension = Path(file_path).suffix.lower()
            if file_extension in ['.md', '.markdown']:
                markdown_analysis = await self._analyze_markdown(text_result.text, options)
                text_result_dict = self._text_result_to_dict(text_result)
                text_result_dict['markdown_analysis'] = markdown_analysis
            else:
                text_result_dict = self._text_result_to_dict(text_result)
            
            return {
                'file_path': file_path,
                'analysis': text_result_dict,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Text analysis failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def extract_text(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract text content from file.
        
        Args:
            file_path: Path to text file
            options: Extraction options
            
        Returns:
            Extracted text content
        """
        try:
            options = options or {}
            
            # Read text with encoding detection
            text_content, encoding = await self._read_text_with_encoding(file_path)
            
            return {
                'file_path': file_path,
                'text': text_content,
                'encoding': encoding,
                'character_count': len(text_content),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def _read_and_analyze_text(self, file_path: str, options: Dict[str, Any]) -> TextAnalysisResult:
        """Read and analyze text file."""
        import time
        start_time = time.time()
        
        try:
            # Read text with encoding detection
            text_content, encoding = await self._read_text_with_encoding(file_path)
            
            # Basic analysis
            word_count = len(text_content.split())
            character_count = len(text_content)
            line_count = len(text_content.splitlines())
            
            # Detect language (basic)
            language = await self._detect_language(text_content) if self.enable_language_detection else 'unknown'
            
            # Determine file type
            file_extension = Path(file_path).suffix.lower()
            if file_extension in ['.md', '.markdown']:
                file_type = 'markdown'
            elif file_extension in ['.txt']:
                file_type = 'plain_text'
            else:
                file_type = 'text'
            
            return TextAnalysisResult(
                text=text_content,
                word_count=word_count,
                character_count=character_count,
                line_count=line_count,
                language=language,
                encoding=encoding,
                file_type=file_type,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Text reading and analysis failed: {e}")
            raise
    
    async def _read_text_with_encoding(self, file_path: str) -> tuple[str, str]:
        """Read text file with automatic encoding detection."""
        try:
            # Try UTF-8 first (most common)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content, 'utf-8'
            except UnicodeDecodeError:
                pass
            
            # Try other common encodings
            encodings = ['latin-1', 'cp1252', 'iso-8859-1', 'ascii']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    return content, encoding
                except UnicodeDecodeError:
                    continue
            
            # If all else fails, read as binary and decode with errors='replace'
            with open(file_path, 'rb') as f:
                raw_content = f.read()
            content = raw_content.decode('utf-8', errors='replace')
            return content, 'utf-8-with-errors'
            
        except Exception as e:
            logger.error(f"Text reading failed: {e}")
            raise
    
    async def _detect_language(self, text: str) -> str:
        """Detect language of text (basic implementation)."""
        try:
            # Very basic language detection based on common words
            text_lower = text.lower()
            
            # English indicators
            english_words = ['the', 'and', 'is', 'are', 'was', 'were', 'this', 'that', 'with', 'for']
            english_count = sum(1 for word in english_words if word in text_lower)
            
            # Simple heuristic
            if english_count >= 3:
                return 'en'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return 'unknown'
    
    async def _analyze_markdown(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze markdown-specific features."""
        try:
            analysis = {
                'has_headers': '# ' in text or '## ' in text,
                'has_links': '[' in text and '](' in text,
                'has_code_blocks': '```' in text,
                'has_lists': '- ' in text or '* ' in text or text.count('\n1. ') > 0,
                'has_images': '![' in text,
                'has_tables': '|' in text,
                'header_count': text.count('\n# ') + text.count('\n## ') + text.count('\n### '),
                'link_count': text.count(']('),
                'code_block_count': text.count('```') // 2,
                'estimated_reading_time_minutes': max(1, len(text.split()) // 200)  # 200 WPM
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Markdown analysis failed: {e}")
            return {'error': str(e)}
    
    def _text_result_to_dict(self, result: TextAnalysisResult) -> Dict[str, Any]:
        """Convert TextAnalysisResult to dictionary."""
        return {
            'text': result.text,
            'word_count': result.word_count,
            'character_count': result.character_count,
            'line_count': result.line_count,
            'language': result.language,
            'encoding': result.encoding,
            'file_type': result.file_type,
            'processing_time': result.processing_time,
            'estimated_reading_time_minutes': max(1, result.word_count // 200)  # 200 WPM
        }
    
    def get_supported_formats(self) -> list[str]:
        """Get supported text formats."""
        return ['txt', 'md', 'markdown', 'text']
    
    def set_max_file_size(self, size_mb: int):
        """Set maximum file size for processing."""
        self.max_file_size_mb = max(1, size_mb)
    
    def set_default_encoding(self, encoding: str):
        """Set default text encoding."""
        self.default_encoding = encoding