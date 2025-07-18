#!/usr/bin/env python3
"""
Markdown Generator

Handles basic conversion of extracted content to well-formatted markdown.
Focuses on formatting only - no AI processing.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MarkdownStructure:
    """Markdown structure metadata"""
    documents: List[Dict[str, Any]]
    total_pages: int
    total_images: int
    total_tables: int

@dataclass
class MarkdownResult:
    """Markdown generation result"""
    markdown: str
    structure: MarkdownStructure
    success: bool
    error: Optional[str] = None
    processing_time: float = 0.0

class MarkdownProcessor:
    """
    Basic markdown generator for content formatting.
    
    Handles:
    - Basic text formatting to markdown
    - Image placeholders and metadata
    - Table structure formatting
    - Multi-document markdown generation
    - Document headers and structure
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.include_images = self.config.get('include_images', True)
        self.include_tables = self.config.get('include_tables', True)
        self.include_metadata = self.config.get('include_metadata', True)
        
        logger.info("Basic Markdown Generator initialized")
    
    def generate_markdown(
        self, 
        content: Dict[str, Any], 
        options: Optional[Dict[str, Any]] = None
    ) -> MarkdownResult:
        """
        Generate basic markdown content from extracted content.
        
        Args:
            content: Extracted content (text, images, tables, etc.)
            options: Markdown generation options
            
        Returns:
            MarkdownResult containing generated markdown and structure info
        """
        import time
        start_time = time.time()
        
        try:
            options = options or {}
            
            markdown_parts = []
            structure = MarkdownStructure(
                documents=[],
                total_pages=0,
                total_images=0,
                total_tables=0
            )
            
            # Document header
            title = content.get('title', 'Document')
            source = content.get('source', 'Unknown')
            
            markdown_parts.append(f"# {title}\n\n")
            
            if self.include_metadata:
                markdown_parts.append(f"**Source:** `{source}`\n")
                if content.get('processing_method'):
                    markdown_parts.append(f"**Processing Method:** {content['processing_method']}\n")
                if content.get('total_pages'):
                    markdown_parts.append(f"**Total Pages:** {content['total_pages']}\n")
                markdown_parts.append("\n")
            
            # Add basic text content
            self._add_text_content(markdown_parts, content)
            
            # Add images section
            if self.include_images:
                self._add_image_content(markdown_parts, content, structure)
            
            # Add tables section
            if self.include_tables:
                self._add_table_content(markdown_parts, content)
            
            # Update structure info
            self._update_structure(structure, content, title, source)
            
            final_markdown = "".join(markdown_parts)
            processing_time = time.time() - start_time
            
            return MarkdownResult(
                markdown=final_markdown,
                structure=structure,
                success=True,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Basic markdown generation failed: {e}")
            return MarkdownResult(
                markdown="",
                structure=MarkdownStructure([], 0, 0, 0),
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    def _add_text_content(
        self, 
        markdown_parts: List[str], 
        content: Dict[str, Any]
    ) -> None:
        """Add basic text content to markdown."""
        text = content.get('text', content.get('full_text', ''))
        if not text:
            return
        
        # Basic formatting - just add content section
        markdown_parts.append("## Content\n\n")
        
        # Split into paragraphs and add basic formatting
        paragraphs = text.split('\n\n')
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                markdown_parts.append(f"{paragraph}\n\n")
    
    def _add_image_content(
        self, 
        markdown_parts: List[str], 
        content: Dict[str, Any], 
        structure: MarkdownStructure
    ) -> None:
        """Add basic image content to markdown."""
        images = content.get('images', [])
        if not images:
            return
        
        markdown_parts.append("## Images\n\n")
        
        for i, img in enumerate(images):
            page_num = img.get('page_number', 'unknown')
            img_index = img.get('image_index', i)
            width = img.get('width', 'unknown')
            height = img.get('height', 'unknown')
            description = img.get('description', 'Image from document')
            
            markdown_parts.append(f"### Image {img_index} - Page {page_num}\n\n")
            markdown_parts.append(f"**Description:** {description}\n\n")
            markdown_parts.append(f"**Dimensions:** {width}x{height} pixels\n\n")
            markdown_parts.append("*[Image data available]*\n\n")
    
    def _add_table_content(
        self, 
        markdown_parts: List[str], 
        content: Dict[str, Any]
    ) -> None:
        """Add basic table information to markdown."""
        tables = content.get('tables', [])
        if not tables:
            return
        
        markdown_parts.append("## Tables\n\n")
        markdown_parts.append(f"**Total Tables:** {len(tables)}\n\n")
        
        # Add basic table information
        for i, table in enumerate(tables, 1):
            markdown_parts.append(f"### Table {i}\n\n")
            
            page_num = table.get('page_number', 'unknown')
            table_type = table.get('table_type', 'unknown')
            confidence = table.get('confidence', 0.0)
            
            markdown_parts.append(f"**Page:** {page_num}\n")
            markdown_parts.append(f"**Type:** {table_type}\n")
            markdown_parts.append(f"**Confidence:** {confidence:.2f}\n")
            
            # Add table content if available
            if table.get('content'):
                markdown_parts.append(f"**Content:**\n{table['content']}\n")
            
            markdown_parts.append("\n")
    
    def _update_structure(
        self, 
        structure: MarkdownStructure, 
        content: Dict[str, Any], 
        title: str, 
        source: str
    ) -> None:
        """Update structure metadata."""
        pages = content.get('total_pages', content.get('pages', 0))
        # Only count images/tables if they are enabled in config
        images = len(content.get('images', [])) if self.include_images else 0
        tables = len(content.get('tables', [])) if self.include_tables else 0
        
        structure.documents.append({
            "title": title,
            "source": source,
            "pages": pages,
            "images": images,
            "tables": tables
        })
        
        structure.total_pages += pages
        structure.total_images += images
        structure.total_tables += tables
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get generator capabilities."""
        return {
            "processor": "markdown_processor",
            "version": "1.0.0",
            "description": "Basic markdown formatting - no AI processing",
            "features": [
                "basic_text_formatting",
                "image_placeholders",
                "table_structure_formatting",
                "document_headers",
                "metadata_inclusion"
            ],
            "output_format": "markdown",
            "configuration_options": [
                "include_images",
                "include_tables", 
                "include_metadata"
            ]
        }