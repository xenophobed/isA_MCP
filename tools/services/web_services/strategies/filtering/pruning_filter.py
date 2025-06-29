#!/usr/bin/env python
"""
Pruning Content Filter Strategy
Filters content based on text density, link density, and tag importance
Inspired by Crawl4AI's PruningContentFilter
"""
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, NavigableString

from core.logging import get_logger
from ..base import FilterStrategy

logger = get_logger(__name__)

class PruningFilter(FilterStrategy):
    """Content filter that removes low-quality content based on scoring"""
    
    def __init__(self, 
                 threshold: float = 0.5,
                 threshold_type: str = "fixed",
                 min_word_threshold: int = 10,
                 tag_weights: Optional[Dict[str, float]] = None):
        """
        Initialize pruning filter
        
        Args:
            threshold: Minimum score threshold for content to be kept
            threshold_type: 'fixed' or 'adaptive' threshold
            min_word_threshold: Minimum words required for text blocks
            tag_weights: Custom weights for HTML tags
        """
        self.threshold = threshold
        self.threshold_type = threshold_type
        self.min_word_threshold = min_word_threshold
        
        # Default tag importance weights
        self.tag_weights = tag_weights or {
            'h1': 3.0, 'h2': 2.5, 'h3': 2.0, 'h4': 1.5, 'h5': 1.2, 'h6': 1.0,
            'p': 1.0, 'div': 0.5, 'span': 0.3,
            'article': 2.0, 'section': 1.5, 'main': 2.5,
            'blockquote': 1.5, 'pre': 1.0, 'code': 0.8,
            'ul': 1.0, 'ol': 1.0, 'li': 0.8,
            'table': 1.2, 'tr': 0.5, 'td': 0.5, 'th': 0.8,
            'nav': 0.1, 'footer': 0.1, 'aside': 0.2, 'header': 0.3,
            'a': 0.5, 'img': 0.3, 'figure': 0.8, 'figcaption': 0.6
        }
    
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Filter content by removing low-quality elements"""
        logger.info("🔄 Applying pruning filter to content")
        
        if criteria:
            self.threshold = criteria.get('threshold', self.threshold)
            self.min_word_threshold = criteria.get('min_word_threshold', self.min_word_threshold)
        
        try:
            # If content is already markdown, convert back to HTML for processing
            if self._is_markdown(content):
                return self._filter_markdown(content)
            
            # Parse HTML content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Calculate scores for all elements
            element_scores = self._calculate_element_scores(soup)
            
            # Determine threshold (adaptive or fixed)
            if self.threshold_type == "adaptive":
                threshold = self._calculate_adaptive_threshold(element_scores)
            else:
                threshold = self.threshold
            
            # Remove low-scoring elements
            filtered_soup = self._remove_low_scoring_elements(soup, element_scores, threshold)
            
            # Return filtered HTML
            filtered_content = str(filtered_soup)
            
            logger.info(f"✅ Pruning filter applied (threshold: {threshold:.2f})")
            return filtered_content
            
        except Exception as e:
            logger.error(f"❌ Pruning filter failed: {e}")
            return content  # Return original content on error
    
    def _is_markdown(self, content: str) -> bool:
        """Check if content is markdown format"""
        markdown_patterns = [
            r'^#{1,6}\s+',  # Headers
            r'^\*\s+',      # Unordered lists
            r'^\d+\.\s+',   # Ordered lists
            r'\[.*\]\(.*\)', # Links
            r'```',         # Code blocks
        ]
        
        lines = content.split('\n')[:10]  # Check first 10 lines
        for line in lines:
            for pattern in markdown_patterns:
                if re.search(pattern, line.strip()):
                    return True
        return False
    
    def _filter_markdown(self, markdown_content: str) -> str:
        """Filter markdown content by removing low-quality sections"""
        lines = markdown_content.split('\n')
        filtered_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Keep headers
            if re.match(r'^#{1,6}\s+', line):
                filtered_lines.append(line)
                continue
            
            # Keep substantial paragraphs
            word_count = len(line.split())
            if word_count >= self.min_word_threshold:
                filtered_lines.append(line)
                continue
            
            # Keep lists with substance
            if re.match(r'^[\*\-\+]\s+', line) or re.match(r'^\d+\.\s+', line):
                if word_count >= 3:  # Lower threshold for list items
                    filtered_lines.append(line)
                continue
            
            # Keep code blocks
            if line.startswith('```') or line.startswith('    '):
                filtered_lines.append(line)
                continue
            
            # Keep links with meaningful text
            if '[' in line and '](' in line:
                filtered_lines.append(line)
                continue
            
            # Skip very short or empty lines
            if word_count < 2:
                continue
            
            # Keep everything else that passed the filters
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _calculate_element_scores(self, soup: BeautifulSoup) -> Dict[Any, float]:
        """Calculate quality scores for all elements"""
        scores = {}
        
        for element in soup.find_all():
            score = self._score_element(element)
            scores[element] = score
        
        return scores
    
    def _score_element(self, element) -> float:
        """Calculate quality score for a single element"""
        score = 0.0
        
        # Base score from tag importance
        tag_name = element.name.lower()
        score += self.tag_weights.get(tag_name, 0.1)
        
        # Text density score
        text = element.get_text(strip=True)
        if text:
            word_count = len(text.split())
            char_count = len(text)
            
            # Reward substantial text content
            if word_count >= self.min_word_threshold:
                score += min(word_count / 50.0, 2.0)  # Cap at 2.0
            
            # Text density (words per character)
            if char_count > 0:
                density = word_count / char_count
                score += density * 5.0  # Scale density score
        
        # Link density penalty (too many links = likely navigation/ads)
        links = element.find_all('a')
        total_text_length = len(element.get_text(strip=True))
        if total_text_length > 0 and links:
            link_text_length = sum(len(link.get_text(strip=True)) for link in links)
            link_density = link_text_length / total_text_length
            score -= link_density * 1.0  # Penalty for high link density
        
        # Class/ID based scoring
        class_names = element.get('class', [])
        element_id = element.get('id', '')
        
        # Penalty for likely navigation/ad elements
        negative_patterns = [
            'nav', 'menu', 'sidebar', 'ad', 'advertisement', 'banner',
            'popup', 'modal', 'cookie', 'footer', 'header', 'social'
        ]
        
        for pattern in negative_patterns:
            if any(pattern in str(cls).lower() for cls in class_names):
                score -= 0.5
            if pattern in element_id.lower():
                score -= 0.5
        
        # Bonus for content-indicating classes
        positive_patterns = [
            'content', 'article', 'post', 'story', 'main', 'body', 'text'
        ]
        
        for pattern in positive_patterns:
            if any(pattern in str(cls).lower() for cls in class_names):
                score += 0.5
            if pattern in element_id.lower():
                score += 0.5
        
        return max(score, 0.0)  # Ensure non-negative score
    
    def _calculate_adaptive_threshold(self, scores: Dict[Any, float]) -> float:
        """Calculate adaptive threshold based on score distribution"""
        if not scores:
            return self.threshold
        
        score_values = list(scores.values())
        score_values.sort(reverse=True)
        
        # Use median as adaptive threshold
        mid_index = len(score_values) // 2
        adaptive_threshold = score_values[mid_index] if score_values else self.threshold
        
        # Ensure threshold is within reasonable bounds
        return max(min(adaptive_threshold, 2.0), 0.1)
    
    def _remove_low_scoring_elements(self, soup: BeautifulSoup, scores: Dict[Any, float], threshold: float) -> BeautifulSoup:
        """Remove elements below threshold score"""
        elements_to_remove = []
        
        for element, score in scores.items():
            if score < threshold:
                # Don't remove if it contains high-scoring children
                has_good_children = any(
                    scores.get(child, 0) >= threshold 
                    for child in element.find_all()
                )
                
                if not has_good_children:
                    elements_to_remove.append(element)
        
        # Remove low-scoring elements
        for element in elements_to_remove:
            if element.parent:  # Make sure element still exists
                element.decompose()
        
        return soup
    
    def get_filter_name(self) -> str:
        return "pruning"