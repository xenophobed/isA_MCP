#!/usr/bin/env python
"""
Extraction Models
Data structures for content extraction operations
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
import json


class ContentType(Enum):
    """Types of extracted content"""
    ARTICLE = "article"
    PRODUCT = "product"
    CONTACT = "contact"
    EVENT = "event"
    RESEARCH = "research"
    NEWS = "news"
    BLOG = "blog"
    FORUM = "forum"
    SOCIAL = "social"
    DOCUMENT = "document"
    CUSTOM = "custom"


@dataclass
class ExtractionMetadata:
    """Metadata for extraction operation"""
    timestamp: datetime
    extraction_method: str  # 'css', 'llm', 'regex', 'xpath'
    schema_used: str
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    tokens_used: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'extraction_method': self.extraction_method,
            'schema_used': self.schema_used,
            'confidence_score': self.confidence_score,
            'processing_time': self.processing_time,
            'tokens_used': self.tokens_used
        }


@dataclass
class ExtractedContent:
    """Single piece of extracted content"""
    content_type: ContentType
    data: Dict[str, Any]
    source_url: str
    metadata: ExtractionMetadata
    raw_html: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'content_type': self.content_type.value,
            'data': self.data,
            'source_url': self.source_url,
            'metadata': self.metadata.to_dict(),
            'raw_html': self.raw_html
        }
    
    def get_field(self, field_name: str, default: Any = None) -> Any:
        """Get a field from the extracted data"""
        return self.data.get(field_name, default)
    
    def has_field(self, field_name: str) -> bool:
        """Check if a field exists in the extracted data"""
        return field_name in self.data
    
    def get_text_content(self) -> str:
        """Get all text content concatenated"""
        text_fields = ['title', 'content', 'description', 'summary', 'abstract']
        text_parts = []
        
        for field in text_fields:
            value = self.get_field(field)
            if value:
                text_parts.append(str(value))
        
        return ' '.join(text_parts)


@dataclass
class ExtractionResult:
    """Result from content extraction operation"""
    url: str
    success: bool
    extracted_items: List[ExtractedContent] = None
    error: Optional[str] = None
    extraction_time: Optional[float] = None
    total_tokens: Optional[int] = None
    
    def __post_init__(self):
        if self.extracted_items is None:
            self.extracted_items = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'success': self.success,
            'extracted_items': [item.to_dict() for item in self.extracted_items],
            'error': self.error,
            'extraction_time': self.extraction_time,
            'total_tokens': self.total_tokens
        }
    
    def add_extracted_item(self, item: ExtractedContent):
        """Add an extracted item"""
        self.extracted_items.append(item)
    
    def get_item_count(self) -> int:
        """Get number of extracted items"""
        return len(self.extracted_items)
    
    def get_items_by_type(self, content_type: ContentType) -> List[ExtractedContent]:
        """Get items of a specific content type"""
        return [item for item in self.extracted_items if item.content_type == content_type]
    
    def get_all_text_content(self) -> str:
        """Get all text content from all items"""
        text_parts = []
        for item in self.extracted_items:
            text_parts.append(item.get_text_content())
        return '\n\n'.join(text_parts)
    
    def filter_by_confidence(self, min_confidence: float) -> List[ExtractedContent]:
        """Filter items by minimum confidence score"""
        return [
            item for item in self.extracted_items
            if item.metadata.confidence_score and item.metadata.confidence_score >= min_confidence
        ]
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# Predefined schemas for common content types
class PredefinedSchemas:
    """Predefined extraction schemas for common content types"""
    
    @staticmethod
    def get_article_schema() -> Dict[str, Any]:
        """Schema for article extraction"""
        return {
            "name": "article",
            "description": "Extract article content",
            "fields": {
                "title": {"type": "string", "required": True},
                "content": {"type": "string", "required": True},
                "author": {"type": "string", "required": False},
                "date": {"type": "string", "required": False},
                "tags": {"type": "array", "required": False},
                "summary": {"type": "string", "required": False},
                "category": {"type": "string", "required": False}
            }
        }
    
    @staticmethod
    def get_product_schema() -> Dict[str, Any]:
        """Schema for product extraction"""
        return {
            "name": "product",
            "description": "Extract product information",
            "fields": {
                "name": {"type": "string", "required": True},
                "price": {"type": "string", "required": True},
                "description": {"type": "string", "required": False},
                "images": {"type": "array", "required": False},
                "rating": {"type": "string", "required": False},
                "reviews": {"type": "array", "required": False},
                "availability": {"type": "string", "required": False},
                "sku": {"type": "string", "required": False}
            }
        }
    
    @staticmethod
    def get_contact_schema() -> Dict[str, Any]:
        """Schema for contact extraction"""
        return {
            "name": "contact",
            "description": "Extract contact information",
            "fields": {
                "name": {"type": "string", "required": True},
                "email": {"type": "string", "required": False},
                "phone": {"type": "string", "required": False},
                "address": {"type": "string", "required": False},
                "role": {"type": "string", "required": False},
                "company": {"type": "string", "required": False},
                "website": {"type": "string", "required": False}
            }
        }
    
    @staticmethod
    def get_event_schema() -> Dict[str, Any]:
        """Schema for event extraction"""
        return {
            "name": "event",
            "description": "Extract event information",
            "fields": {
                "title": {"type": "string", "required": True},
                "date": {"type": "string", "required": True},
                "location": {"type": "string", "required": False},
                "description": {"type": "string", "required": False},
                "organizer": {"type": "string", "required": False},
                "price": {"type": "string", "required": False},
                "category": {"type": "string", "required": False},
                "duration": {"type": "string", "required": False}
            }
        }
    
    @staticmethod
    def get_research_schema() -> Dict[str, Any]:
        """Schema for research content extraction"""
        return {
            "name": "research",
            "description": "Extract research content",
            "fields": {
                "title": {"type": "string", "required": True},
                "abstract": {"type": "string", "required": False},
                "authors": {"type": "array", "required": False},
                "keywords": {"type": "array", "required": False},
                "content": {"type": "string", "required": False},
                "publication_date": {"type": "string", "required": False},
                "journal": {"type": "string", "required": False},
                "doi": {"type": "string", "required": False}
            }
        }
    
    @staticmethod
    def get_news_schema() -> Dict[str, Any]:
        """Schema for news extraction"""
        return {
            "name": "news",
            "description": "Extract news content",
            "fields": {
                "headline": {"type": "string", "required": True},
                "content": {"type": "string", "required": True},
                "author": {"type": "string", "required": False},
                "publication_date": {"type": "string", "required": False},
                "source": {"type": "string", "required": False},
                "category": {"type": "string", "required": False},
                "tags": {"type": "array", "required": False},
                "summary": {"type": "string", "required": False}
            }
        }
    
    @staticmethod
    def get_schema_by_name(name: str) -> Dict[str, Any]:
        """Get schema by name"""
        schemas = {
            'article': PredefinedSchemas.get_article_schema(),
            'product': PredefinedSchemas.get_product_schema(),
            'contact': PredefinedSchemas.get_contact_schema(),
            'event': PredefinedSchemas.get_event_schema(),
            'research': PredefinedSchemas.get_research_schema(),
            'news': PredefinedSchemas.get_news_schema()
        }
        
        if name not in schemas:
            raise ValueError(f"Unknown schema: {name}")
        
        return schemas[name]
    
    @staticmethod
    def get_all_schema_names() -> List[str]:
        """Get all available schema names"""
        return ['article', 'product', 'contact', 'event', 'research', 'news']