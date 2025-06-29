#!/usr/bin/env python
"""
Markdown Generation Strategy
Converts HTML to high-quality Markdown optimized for LLM consumption
Inspired by Crawl4AI's markdown generation
"""
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin, urlparse

from core.logging import get_logger
from ..base import GenerationStrategy

logger = get_logger(__name__)

class MarkdownGenerator(GenerationStrategy):
    """Convert HTML to clean, LLM-friendly Markdown"""
    
    def __init__(self, 
                 base_url: Optional[str] = None,
                 include_links: bool = True,
                 include_images: bool = True,
                 max_line_length: int = 80):
        self.base_url = base_url
        self.include_links = include_links
        self.include_images = include_images
        self.max_line_length = max_line_length
    
    async def generate(self, html: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Generate Markdown from HTML"""
        logger.info("🔄 Generating Markdown from HTML")
        
        if options:
            self.base_url = options.get('base_url', self.base_url)
            self.include_links = options.get('include_links', self.include_links)
            self.include_images = options.get('include_images', self.include_images)
        
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            self._remove_unwanted_elements(soup)
            
            # Convert to markdown
            markdown = self._convert_to_markdown(soup)
            
            # Clean up the markdown
            markdown = self._clean_markdown(markdown)
            
            logger.info("✅ Markdown generation completed")
            return markdown
            
        except Exception as e:
            logger.error(f"❌ Markdown generation failed: {e}")
            # Fallback to text extraction
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove unwanted HTML elements"""
        # Elements to remove completely
        unwanted_tags = [
            'script', 'style', 'nav', 'footer', 'aside', 'header',
            'noscript', 'iframe', 'embed', 'object', 'applet',
            'form', 'input', 'button', 'select', 'textarea'
        ]
        
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements with certain classes/ids (common ad/navigation patterns)
        unwanted_selectors = [
            '[class*="nav"]', '[class*="menu"]', '[class*="sidebar"]',
            '[class*="ad"]', '[class*="advertisement"]', '[class*="banner"]',
            '[class*="popup"]', '[class*="modal"]', '[class*="cookie"]'
        ]
        
        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()
    
    def _convert_to_markdown(self, soup: BeautifulSoup) -> str:
        """Convert BeautifulSoup to Markdown"""
        markdown_parts = []
        
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'article', 'section', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'a', 'img', 'table', 'tr', 'td', 'th']):
            md_text = self._element_to_markdown(element)
            if md_text.strip():
                markdown_parts.append(md_text)
        
        return '\n'.join(markdown_parts)
    
    def _element_to_markdown(self, element) -> str:
        """Convert individual element to Markdown"""
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(element.name[1])
            text = element.get_text(strip=True)
            return f"{'#' * level} {text}\n"
        
        elif element.name == 'p':
            text = self._process_inline_elements(element)
            return f"{text}\n" if text.strip() else ""
        
        elif element.name in ['div', 'article', 'section']:
            # Only process if it contains direct text or important elements
            if element.get_text(strip=True):
                text = self._process_inline_elements(element)
                return f"{text}\n" if text.strip() else ""
        
        elif element.name == 'ul':
            items = []
            for li in element.find_all('li', recursive=False):
                item_text = self._process_inline_elements(li)
                if item_text.strip():
                    items.append(f"- {item_text.strip()}")
            return '\n'.join(items) + '\n' if items else ""
        
        elif element.name == 'ol':
            items = []
            for i, li in enumerate(element.find_all('li', recursive=False), 1):
                item_text = self._process_inline_elements(li)
                if item_text.strip():
                    items.append(f"{i}. {item_text.strip()}")
            return '\n'.join(items) + '\n' if items else ""
        
        elif element.name == 'blockquote':
            text = element.get_text(strip=True)
            lines = text.split('\n')
            quoted_lines = [f"> {line}" for line in lines if line.strip()]
            return '\n'.join(quoted_lines) + '\n'
        
        elif element.name == 'pre':
            code_text = element.get_text()
            return f"```\n{code_text}\n```\n"
        
        elif element.name == 'code':
            code_text = element.get_text()
            return f"`{code_text}`"
        
        elif element.name == 'a' and self.include_links:
            text = element.get_text(strip=True)
            href = element.get('href', '')
            if href and text:
                # Make absolute URL if needed
                if self.base_url and not href.startswith('http'):
                    href = urljoin(self.base_url, href)
                return f"[{text}]({href})"
            return text
        
        elif element.name == 'img' and self.include_images:
            alt = element.get('alt', '')
            src = element.get('src', '')
            if src:
                # Make absolute URL if needed
                if self.base_url and not src.startswith('http'):
                    src = urljoin(self.base_url, src)
                return f"![{alt}]({src})"
        
        elif element.name == 'table':
            return self._table_to_markdown(element)
        
        return ""
    
    def _process_inline_elements(self, element) -> str:
        """Process inline elements within a container"""
        result_parts = []
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    result_parts.append(text)
            else:
                if child.name == 'a' and self.include_links:
                    text = child.get_text(strip=True)
                    href = child.get('href', '')
                    if href and text:
                        if self.base_url and not href.startswith('http'):
                            href = urljoin(self.base_url, href)
                        result_parts.append(f"[{text}]({href})")
                    else:
                        result_parts.append(text)
                elif child.name == 'strong' or child.name == 'b':
                    text = child.get_text(strip=True)
                    if text:
                        result_parts.append(f"**{text}**")
                elif child.name == 'em' or child.name == 'i':
                    text = child.get_text(strip=True)
                    if text:
                        result_parts.append(f"*{text}*")
                elif child.name == 'code':
                    text = child.get_text()
                    result_parts.append(f"`{text}`")
                else:
                    text = child.get_text(strip=True)
                    if text:
                        result_parts.append(text)
        
        return ' '.join(result_parts)
    
    def _table_to_markdown(self, table) -> str:
        """Convert table to Markdown format"""
        rows = table.find_all('tr')
        if not rows:
            return ""
        
        markdown_rows = []
        
        # Process header row
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        if headers:
            markdown_rows.append('| ' + ' | '.join(headers) + ' |')
            markdown_rows.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        
        # Process data rows
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
            if cells:
                markdown_rows.append('| ' + ' | '.join(cells) + ' |')
        
        return '\n'.join(markdown_rows) + '\n'
    
    def _clean_markdown(self, markdown: str) -> str:
        """Clean up the generated Markdown"""
        # Remove excessive whitespace
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
        
        # Remove leading/trailing whitespace from lines
        lines = [line.rstrip() for line in markdown.split('\n')]
        markdown = '\n'.join(lines)
        
        # Remove empty markdown elements
        markdown = re.sub(r'^#{1,6}\s*$', '', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'^\*\s*$', '', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'^\d+\.\s*$', '', markdown, flags=re.MULTILINE)
        
        # Clean up multiple consecutive empty lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        return markdown.strip()
    
    def get_generator_name(self) -> str:
        return "markdown"