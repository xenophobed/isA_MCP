#!/usr/bin/env python3
"""
BS4 Service - Clean BeautifulSoup text extraction service

Simple, focused service for extracting clean text content from HTML pages
using BeautifulSoup. Returns structured text data without complex processing.
"""

import requests
import asyncio
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BS4ExtractionResult:
    """Result from BS4 text extraction"""
    success: bool
    title: str = ""
    content: str = ""
    headings: list = None
    links: list = None
    paragraphs: list = None
    word_count: int = 0
    processing_time: float = 0.0
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.headings is None:
            self.headings = []
        if self.links is None:
            self.links = []
        if self.paragraphs is None:
            self.paragraphs = []


class BS4Service:
    """Simple BS4 text extraction service"""
    
    def __init__(self):
        logger.info(" BS4Service initialized for clean text extraction")
    
    async def extract_text(self, url: str) -> BS4ExtractionResult:
        """
        Extract clean text content from a web page using BeautifulSoup
        
        Args:
            url: Target web page URL
            
        Returns:
            BS4ExtractionResult with extracted text content
        """
        try:
            start_time = asyncio.get_event_loop().time()
            logger.info(f"=' Starting BS4 text extraction for: {url}")
            
            # Fetch the webpage
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ""
            
            # Remove script, style, nav, header, footer tags
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'meta', 'link']):
                tag.decompose()
            
            # Extract headings
            headings = []
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({
                        'level': heading.name,
                        'text': text
                    })
            
            # Extract paragraphs
            paragraphs = []
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # Only meaningful paragraphs
                    paragraphs.append(text)
            
            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True)
                href = link['href']
                if text and href:
                    links.append({
                        'text': text,
                        'url': href
                    })
            
            # Get main text content
            main_content = soup.get_text(separator=' ', strip=True)
            
            # Clean up the text
            content = self._clean_text(main_content)
            word_count = len(content.split())
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f" BS4 extraction completed in {processing_time:.2f}s - {word_count} words")
            
            return BS4ExtractionResult(
                success=True,
                title=title,
                content=content,
                headings=headings,
                links=links,
                paragraphs=paragraphs,
                word_count=word_count,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time if 'start_time' in locals() else 0
            logger.error(f"L BS4 extraction failed: {e}")
            return BS4ExtractionResult(
                success=False,
                processing_time=processing_time,
                error=str(e)
            )
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text content"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # Skip empty lines
                cleaned_lines.append(line)
        
        # Join with single spaces and normalize whitespace
        cleaned_text = ' '.join(cleaned_lines)
        
        # Remove excessive spaces
        import re
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        return cleaned_text.strip()


# Global instance for easy import
bs4_service = BS4Service()


# Convenience function
async def extract_text(url: str) -> BS4ExtractionResult:
    """Extract clean text from URL using BS4"""
    return await bs4_service.extract_text(url)