#!/usr/bin/env python
"""
BM25 Content Filter Strategy
Filters content based on BM25 ranking algorithm for query relevance
Inspired by Crawl4AI's BM25ContentFilter
"""
import re
import math
from typing import Dict, Any, Optional, List
from collections import Counter, defaultdict
from bs4 import BeautifulSoup

from core.logging import get_logger
from ..base import FilterStrategy

logger = get_logger(__name__)

class BM25Filter(FilterStrategy):
    """Content filter using BM25 algorithm for relevance scoring"""
    
    def __init__(self, 
                 user_query: str = "",
                 bm25_threshold: float = 1.0,
                 k1: float = 1.5,
                 b: float = 0.75,
                 min_words: int = 5):
        """
        Initialize BM25 filter
        
        Args:
            user_query: Query to calculate relevance against
            bm25_threshold: Minimum BM25 score for content to be kept
            k1: BM25 parameter (term frequency saturation)
            b: BM25 parameter (length normalization)
            min_words: Minimum words required for text blocks
        """
        self.user_query = user_query
        self.bm25_threshold = bm25_threshold
        self.k1 = k1
        self.b = b
        self.min_words = min_words
        
        # Preprocess query
        self.query_terms = self._preprocess_text(user_query) if user_query else []
    
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Filter content based on BM25 relevance to query"""
        logger.info(f"🔄 Applying BM25 filter for query: '{self.user_query}'")
        
        if criteria:
            self.user_query = criteria.get('query', self.user_query)
            self.bm25_threshold = criteria.get('threshold', self.bm25_threshold)
            self.query_terms = self._preprocess_text(self.user_query)
        
        if not self.query_terms:
            logger.warning("No query terms provided, returning original content")
            return content
        
        try:
            # If content is markdown, filter by paragraphs
            if self._is_markdown(content):
                return self._filter_markdown_by_bm25(content)
            
            # Parse HTML and filter by elements
            soup = BeautifulSoup(content, 'html.parser')
            return self._filter_html_by_bm25(soup)
            
        except Exception as e:
            logger.error(f"❌ BM25 filter failed: {e}")
            return content
    
    def _is_markdown(self, content: str) -> bool:
        """Check if content is markdown format"""
        markdown_indicators = ['#', '*', '-', '```', '[', ']', '(', ')']
        return any(indicator in content[:100] for indicator in markdown_indicators)
    
    def _filter_markdown_by_bm25(self, content: str) -> str:
        """Filter markdown content using BM25 scoring"""
        # Split into paragraphs and sections
        sections = self._split_markdown_sections(content)
        
        if not sections:
            return content
        
        # Calculate BM25 scores for each section
        scores = self._calculate_bm25_scores(sections)
        
        # Filter sections based on scores
        filtered_sections = []
        for i, section in enumerate(sections):
            if scores[i] >= self.bm25_threshold or len(section.split()) < self.min_words:
                filtered_sections.append(section)
        
        filtered_content = '\n\n'.join(filtered_sections)
        
        logger.info(f"✅ BM25 filter applied: kept {len(filtered_sections)}/{len(sections)} sections")
        return filtered_content
    
    def _filter_html_by_bm25(self, soup: BeautifulSoup) -> str:
        """Filter HTML content using BM25 scoring"""
        # Extract text blocks from meaningful elements
        text_elements = soup.find_all(['p', 'div', 'article', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
        
        # Get text content from elements
        text_blocks = []
        element_map = {}
        
        for i, element in enumerate(text_elements):
            text = element.get_text(strip=True)
            if len(text.split()) >= self.min_words:
                text_blocks.append(text)
                element_map[i] = element
        
        if not text_blocks:
            return str(soup)
        
        # Calculate BM25 scores
        scores = self._calculate_bm25_scores(text_blocks)
        
        # Remove low-scoring elements
        elements_to_remove = []
        for i, score in enumerate(scores):
            if score < self.bm25_threshold and i in element_map:
                elements_to_remove.append(element_map[i])
        
        # Remove elements
        for element in elements_to_remove:
            if element.parent:
                element.decompose()
        
        kept_count = len(text_blocks) - len(elements_to_remove)
        logger.info(f"✅ BM25 filter applied: kept {kept_count}/{len(text_blocks)} elements")
        
        return str(soup)
    
    def _split_markdown_sections(self, content: str) -> List[str]:
        """Split markdown content into logical sections"""
        # Split by headers and double newlines
        sections = []
        current_section = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # New section on headers
            if re.match(r'^#{1,6}\s+', line):
                if current_section:
                    sections.append('\n'.join(current_section))
                    current_section = [line]
                else:
                    current_section.append(line)
            # New section on significant breaks
            elif not line and current_section:
                # Check if next lines are substantial
                continue
            else:
                current_section.append(line)
        
        # Add final section
        if current_section:
            sections.append('\n'.join(current_section))
        
        # Filter out very short sections
        sections = [s for s in sections if len(s.split()) >= self.min_words]
        
        return sections
    
    def _calculate_bm25_scores(self, documents: List[str]) -> List[float]:
        """Calculate BM25 scores for documents against query"""
        if not documents or not self.query_terms:
            return [0.0] * len(documents)
        
        # Preprocess all documents
        processed_docs = [self._preprocess_text(doc) for doc in documents]
        
        # Calculate document frequencies
        doc_freqs = defaultdict(int)
        for doc in processed_docs:
            unique_terms = set(doc)
            for term in unique_terms:
                doc_freqs[term] += 1
        
        # Calculate average document length
        total_length = sum(len(doc) for doc in processed_docs)
        avg_doc_length = total_length / len(processed_docs) if processed_docs else 1
        
        # Calculate BM25 scores
        scores = []
        num_docs = len(processed_docs)
        
        for doc in processed_docs:
            score = 0.0
            doc_length = len(doc)
            term_counts = Counter(doc)
            
            for term in self.query_terms:
                if term in term_counts:
                    # Term frequency in document
                    tf = term_counts[term]
                    
                    # Document frequency
                    df = doc_freqs[term]
                    
                    # IDF calculation
                    idf = math.log((num_docs - df + 0.5) / (df + 0.5))
                    
                    # BM25 formula
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / avg_doc_length))
                    
                    score += idf * (numerator / denominator)
            
            scores.append(score)
        
        return scores
    
    def _preprocess_text(self, text: str) -> List[str]:
        """Preprocess text for BM25 calculation"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and split
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'this', 'that', 'these', 'those'
        }
        
        # Filter stop words and short words
        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        return filtered_words
    
    def get_filter_name(self) -> str:
        return "bm25"