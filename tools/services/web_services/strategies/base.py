#!/usr/bin/env python
"""
Base Strategy Classes for Web Services
Inspired by Crawl4AI's strategy pattern implementation
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from playwright.async_api import Page

class ExtractionStrategy(ABC):
    """Base class for content extraction strategies"""
    
    @abstractmethod
    async def extract(self, page: Page, html: str) -> List[Dict[str, Any]]:
        """Extract structured data from page"""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name"""
        pass

class FilterStrategy(ABC):
    """Base class for content filtering strategies"""
    
    @abstractmethod
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Filter content based on criteria"""
        pass
    
    @abstractmethod
    def get_filter_name(self) -> str:
        """Get filter name"""
        pass

class GenerationStrategy(ABC):
    """Base class for content generation strategies"""
    
    @abstractmethod
    async def generate(self, html: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Generate formatted content from HTML"""
        pass
    
    @abstractmethod
    def get_generator_name(self) -> str:
        """Get generator name"""
        pass

class DetectionStrategy(ABC):
    """Base class for element detection strategies"""
    
    @abstractmethod
    async def detect(self, page: Page, target_type: str) -> Dict[str, Any]:
        """Detect elements on page"""
        pass
    
    @abstractmethod
    def get_detection_name(self) -> str:
        """Get detection strategy name"""
        pass