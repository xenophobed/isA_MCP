#!/usr/bin/env python
"""
CSS Selector Extraction Strategy
Fast schema-based data extraction using CSS selectors
Inspired by Crawl4AI's JsonCssExtractionStrategy
"""
from typing import Dict, Any, List, Optional
from playwright.async_api import Page

from core.logging import get_logger
from ..base import ExtractionStrategy

logger = get_logger(__name__)

class CSSExtractionStrategy(ExtractionStrategy):
    """Extract structured data using CSS selectors based on schema"""
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize CSS extraction strategy
        
        Args:
            schema: Extraction schema with selectors and field definitions
                   Format: {
                       "name": "Schema Name",
                       "baseSelector": ".container",
                       "fields": [
                           {"name": "title", "selector": "h1", "type": "text"},
                           {"name": "content", "selector": ".content", "type": "text"},
                           {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
                       ]
                   }
        """
        self.schema = schema
        self.name = schema.get("name", "CSS Extraction")
        self.base_selector = schema.get("baseSelector", "body")
        self.fields = schema.get("fields", [])
    
    async def extract(self, page: Page, html: str) -> List[Dict[str, Any]]:
        """Extract data based on CSS selectors"""
        logger.info(f"🔍 Extracting data using CSS strategy: {self.name}")
        
        try:
            results = []
            
            # Find base containers
            base_elements = page.locator(self.base_selector)
            count = await base_elements.count()
            
            logger.info(f"   Found {count} base containers with selector: {self.base_selector}")
            
            # Extract from each container
            for i in range(count):
                container = base_elements.nth(i)
                extracted_item = {}
                
                # Extract each field
                for field in self.fields:
                    field_name = field.get("name")
                    field_selector = field.get("selector")
                    field_type = field.get("type", "text")
                    field_attribute = field.get("attribute")
                    
                    if not field_name or not field_selector:
                        continue
                    
                    try:
                        # Find element within container
                        element = container.locator(field_selector).first
                        element_count = await element.count()
                        
                        if element_count > 0:
                            # Extract based on type
                            if field_type == "text":
                                value = await element.text_content()
                                extracted_item[field_name] = value.strip() if value else ""
                            
                            elif field_type == "attribute":
                                if field_attribute:
                                    value = await element.get_attribute(field_attribute)
                                    extracted_item[field_name] = value or ""
                                else:
                                    logger.warning(f"Attribute not specified for field: {field_name}")
                                    extracted_item[field_name] = ""
                            
                            elif field_type == "html":
                                value = await element.inner_html()
                                extracted_item[field_name] = value or ""
                            
                            elif field_type == "list":
                                # Extract list of items
                                list_elements = container.locator(field_selector)
                                list_count = await list_elements.count()
                                items = []
                                for j in range(list_count):
                                    item_text = await list_elements.nth(j).text_content()
                                    if item_text and item_text.strip():
                                        items.append(item_text.strip())
                                extracted_item[field_name] = items
                            
                            elif field_type == "count":
                                # Count matching elements
                                count_elements = container.locator(field_selector)
                                element_count = await count_elements.count()
                                extracted_item[field_name] = element_count
                                
                            else:
                                # Default to text extraction
                                value = await element.text_content()
                                extracted_item[field_name] = value.strip() if value else ""
                        
                        else:
                            # Element not found
                            if field_type == "list":
                                extracted_item[field_name] = []
                            elif field_type == "count":
                                extracted_item[field_name] = 0
                            else:
                                extracted_item[field_name] = ""
                    
                    except Exception as e:
                        logger.warning(f"Failed to extract field '{field_name}': {e}")
                        # Set default value based on type
                        if field_type == "list":
                            extracted_item[field_name] = []
                        elif field_type == "count":
                            extracted_item[field_name] = 0
                        else:
                            extracted_item[field_name] = ""
                
                # Only add item if it has some content
                if any(value for value in extracted_item.values() if value):
                    results.append(extracted_item)
            
            logger.info(f"✅ CSS extraction completed: {len(results)} items extracted")
            return results
            
        except Exception as e:
            logger.error(f"❌ CSS extraction failed: {e}")
            return []
    
    def get_strategy_name(self) -> str:
        return f"css_extraction_{self.name.lower().replace(' ', '_')}"

class PredefinedSchemas:
    """Predefined extraction schemas for common content types"""
    
    @staticmethod
    def get_news_articles_schema() -> Dict[str, Any]:
        """Schema for extracting news articles"""
        return {
            "name": "News Articles",
            "baseSelector": "article, .article, [class*='article'], .post, [class*='post']",
            "fields": [
                {"name": "title", "selector": "h1, h2, .title, [class*='title']", "type": "text"},
                {"name": "content", "selector": ".content, .body, p", "type": "text"},
                {"name": "author", "selector": ".author, [class*='author'], .byline", "type": "text"},
                {"name": "date", "selector": ".date, time, [class*='date']", "type": "text"},
                {"name": "tags", "selector": ".tag, .category, [class*='tag']", "type": "list"},
                {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
            ]
        }
    
    @staticmethod
    def get_product_listings_schema() -> Dict[str, Any]:
        """Schema for extracting product listings"""
        return {
            "name": "Product Listings",
            "baseSelector": ".product, [class*='product'], .item, [class*='item']",
            "fields": [
                {"name": "name", "selector": ".name, .title, h3, h4", "type": "text"},
                {"name": "price", "selector": ".price, [class*='price']", "type": "text"},
                {"name": "description", "selector": ".description, .summary", "type": "text"},
                {"name": "image", "selector": "img", "type": "attribute", "attribute": "src"},
                {"name": "rating", "selector": ".rating, [class*='rating']", "type": "text"},
                {"name": "reviews_count", "selector": ".reviews, [class*='review']", "type": "count"},
                {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
            ]
        }
    
    @staticmethod
    def get_contact_info_schema() -> Dict[str, Any]:
        """Schema for extracting contact information"""
        return {
            "name": "Contact Information",
            "baseSelector": ".contact, [class*='contact'], .info, footer",
            "fields": [
                {"name": "email", "selector": "[href^='mailto:'], .email", "type": "attribute", "attribute": "href"},
                {"name": "phone", "selector": "[href^='tel:'], .phone", "type": "text"},
                {"name": "address", "selector": ".address, [class*='address']", "type": "text"},
                {"name": "social_links", "selector": "[href*='facebook'], [href*='twitter'], [href*='linkedin']", "type": "list"}
            ]
        }
    
    @staticmethod
    def get_table_data_schema() -> Dict[str, Any]:
        """Schema for extracting table data"""
        return {
            "name": "Table Data",
            "baseSelector": "table tr",
            "fields": [
                {"name": "cells", "selector": "td, th", "type": "list"}
            ]
        }
    
    @staticmethod
    def get_navigation_links_schema() -> Dict[str, Any]:
        """Schema for extracting navigation links"""
        return {
            "name": "Navigation Links",
            "baseSelector": "nav, .nav, .menu, [class*='menu']",
            "fields": [
                {"name": "links", "selector": "a", "type": "list"},
                {"name": "urls", "selector": "a", "type": "attribute", "attribute": "href"}
            ]
        }