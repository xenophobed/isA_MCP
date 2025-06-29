#!/usr/bin/env python
"""
XPath Extraction Strategy
Powerful data extraction using XPath expressions
Inspired by Crawl4AI's extraction capabilities
"""
from typing import Dict, Any, List, Optional
from playwright.async_api import Page

from core.logging import get_logger
from ..base import ExtractionStrategy

logger = get_logger(__name__)

class XPathExtractionStrategy(ExtractionStrategy):
    """Extract structured data using XPath expressions"""
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize XPath extraction strategy
        
        Args:
            schema: Extraction schema with XPath expressions
                   Format: {
                       "name": "Schema Name",
                       "baseXPath": "//div[@class='container']",
                       "fields": [
                           {"name": "title", "xpath": ".//h1", "type": "text"},
                           {"name": "content", "xpath": ".//p", "type": "text"},
                           {"name": "link", "xpath": ".//a/@href", "type": "attribute"}
                       ]
                   }
        """
        self.schema = schema
        self.name = schema.get("name", "XPath Extraction")
        self.base_xpath = schema.get("baseXPath", "//body")
        self.fields = schema.get("fields", [])
    
    async def extract(self, page: Page, html: str) -> List[Dict[str, Any]]:
        """Extract data based on XPath expressions"""
        logger.info(f"🔍 Extracting data using XPath strategy: {self.name}")
        
        try:
            results = []
            
            # Find base containers using XPath
            base_elements = page.locator(f"xpath={self.base_xpath}")
            count = await base_elements.count()
            
            logger.info(f"   Found {count} base containers with XPath: {self.base_xpath}")
            
            # Extract from each container
            for i in range(count):
                container = base_elements.nth(i)
                extracted_item = {}
                
                # Extract each field
                for field in self.fields:
                    field_name = field.get("name")
                    field_xpath = field.get("xpath")
                    field_type = field.get("type", "text")
                    
                    if not field_name or not field_xpath:
                        continue
                    
                    try:
                        # For Playwright, we need to handle XPath differently
                        # Use page.locator with xpath= for absolute paths
                        if field_xpath.startswith(".//") or field_xpath.startswith("./"):
                            # Relative XPath - find within container
                            elements = container.locator(f"xpath={field_xpath}")
                        elif field_xpath.startswith("@"):
                            # Attribute on current element - this won't work with locator
                            # Skip for now as Playwright handles attributes differently
                            continue
                        elif "@" in field_xpath:
                            # XPath with attribute - need special handling
                            # For now, try to convert to simpler form
                            if field_xpath.endswith("/@href"):
                                simple_xpath = field_xpath.replace("/@href", "")
                                elements = container.locator(f"xpath={simple_xpath}")
                            elif field_xpath.endswith("/@content"):
                                simple_xpath = field_xpath.replace("/@content", "")
                                elements = container.locator(f"xpath={simple_xpath}")
                            else:
                                # Use the full xpath from base element
                                elements = page.locator(f"xpath={field_xpath}")
                        else:
                            # Use relative XPath from container
                            full_xpath = f".//{field_xpath.lstrip('/')}" if not field_xpath.startswith(".//") else field_xpath
                            elements = container.locator(f"xpath={full_xpath}")
                        element_count = await elements.count()
                        
                        if element_count > 0:
                            # Extract based on type
                            if field_type == "text":
                                value = await elements.first.text_content()
                                extracted_item[field_name] = value.strip() if value else ""
                            
                            elif field_type == "attribute":
                                # For attribute extraction with Playwright
                                if field_xpath.endswith("/@href"):
                                    value = await elements.first.get_attribute("href")
                                    extracted_item[field_name] = value or ""
                                elif field_xpath.endswith("/@content") or "meta[@name" in field_xpath or "meta[@property" in field_xpath:
                                    value = await elements.first.get_attribute("content")
                                    extracted_item[field_name] = value or ""
                                elif field_xpath.endswith("/@src"):
                                    value = await elements.first.get_attribute("src")
                                    extracted_item[field_name] = value or ""
                                elif "link[@rel" in field_xpath:
                                    value = await elements.first.get_attribute("href")
                                    extracted_item[field_name] = value or ""
                                elif field_name == "action":
                                    value = await elements.first.get_attribute("action")
                                    extracted_item[field_name] = value or ""
                                elif field_name == "method":
                                    value = await elements.first.get_attribute("method")
                                    extracted_item[field_name] = value or ""
                                else:
                                    # Try to extract as text for now
                                    value = await elements.first.text_content()
                                    extracted_item[field_name] = value or ""
                            
                            elif field_type == "html":
                                value = await elements.first.inner_html()
                                extracted_item[field_name] = value or ""
                            
                            elif field_type == "list":
                                # Extract list of text from all matching elements
                                items = []
                                for j in range(element_count):
                                    item_text = await elements.nth(j).text_content()
                                    if item_text and item_text.strip():
                                        items.append(item_text.strip())
                                extracted_item[field_name] = items
                            
                            elif field_type == "attribute_list":
                                # Extract specific attribute from all matching elements
                                attribute_name = field.get("attribute", "")
                                items = []
                                for j in range(element_count):
                                    item_value = await elements.nth(j).get_attribute(attribute_name)
                                    if item_value:
                                        items.append(item_value)
                                extracted_item[field_name] = items
                            
                            elif field_type == "count":
                                # Count matching elements
                                extracted_item[field_name] = element_count
                            
                            elif field_type == "all_text":
                                # Concatenate text from all matching elements
                                texts = []
                                for j in range(element_count):
                                    item_text = await elements.nth(j).text_content()
                                    if item_text and item_text.strip():
                                        texts.append(item_text.strip())
                                extracted_item[field_name] = " ".join(texts)
                                
                            else:
                                # Default to text extraction
                                value = await elements.first.text_content()
                                extracted_item[field_name] = value.strip() if value else ""
                        
                        else:
                            # Element not found
                            if field_type in ["list", "attribute_list"]:
                                extracted_item[field_name] = []
                            elif field_type == "count":
                                extracted_item[field_name] = 0
                            else:
                                extracted_item[field_name] = ""
                    
                    except Exception as e:
                        logger.warning(f"Failed to extract field '{field_name}' with XPath '{field_xpath}': {e}")
                        # Set default value based on type
                        if field_type in ["list", "attribute_list"]:
                            extracted_item[field_name] = []
                        elif field_type == "count":
                            extracted_item[field_name] = 0
                        else:
                            extracted_item[field_name] = ""
                
                # Only add item if it has some content
                if any(value for value in extracted_item.values() if value):
                    results.append(extracted_item)
            
            logger.info(f"✅ XPath extraction completed: {len(results)} items extracted")
            return results
            
        except Exception as e:
            logger.error(f"❌ XPath extraction failed: {e}")
            return []
    
    def get_strategy_name(self) -> str:
        return f"xpath_extraction_{self.name.lower().replace(' ', '_')}"

class PredefinedXPathSchemas:
    """Predefined XPath extraction schemas for common content types"""
    
    @staticmethod
    def get_structured_data_schema() -> Dict[str, Any]:
        """Schema for extracting structured data (JSON-LD, microdata)"""
        return {
            "name": "Structured Data",
            "baseXPath": "//script[@type='application/ld+json'] | //*[@itemtype]",
            "fields": [
                {"name": "json_ld", "xpath": "./text()", "type": "text"},
                {"name": "microdata_type", "xpath": "./@itemtype", "type": "attribute"},
                {"name": "microdata_props", "xpath": ".//*[@itemprop]/@itemprop", "type": "list"}
            ]
        }
    
    @staticmethod
    def get_meta_information_schema() -> Dict[str, Any]:
        """Schema for extracting meta information"""
        return {
            "name": "Meta Information",
            "baseXPath": "//head",
            "fields": [
                {"name": "title", "xpath": ".//title", "type": "text"},
                {"name": "description", "xpath": ".//meta[@name='description']", "type": "attribute"},
                {"name": "keywords", "xpath": ".//meta[@name='keywords']", "type": "attribute"},
                {"name": "og_title", "xpath": ".//meta[@property='og:title']", "type": "attribute"},
                {"name": "og_description", "xpath": ".//meta[@property='og:description']", "type": "attribute"},
                {"name": "canonical", "xpath": ".//link[@rel='canonical']", "type": "attribute"}
            ]
        }
    
    @staticmethod
    def get_form_fields_schema() -> Dict[str, Any]:
        """Schema for extracting form fields"""
        return {
            "name": "Form Fields",
            "baseXPath": "//form",
            "fields": [
                {"name": "action", "xpath": ".", "type": "attribute"},  # Will get action attribute from form
                {"name": "method", "xpath": ".", "type": "attribute"},  # Will get method attribute from form  
                {"name": "input_names", "xpath": ".//input", "type": "attribute_list", "attribute": "name"},
                {"name": "input_types", "xpath": ".//input", "type": "attribute_list", "attribute": "type"},
                {"name": "labels", "xpath": ".//label", "type": "list"},
                {"name": "buttons", "xpath": ".//button", "type": "list"}
            ]
        }
    
    @staticmethod
    def get_media_content_schema() -> Dict[str, Any]:
        """Schema for extracting media content"""
        return {
            "name": "Media Content",
            "baseXPath": "//body",
            "fields": [
                {"name": "images", "xpath": ".//img/@src", "type": "list"},
                {"name": "image_alts", "xpath": ".//img/@alt", "type": "list"},
                {"name": "videos", "xpath": ".//video/@src | .//video/source/@src", "type": "list"},
                {"name": "audio", "xpath": ".//audio/@src | .//audio/source/@src", "type": "list"},
                {"name": "iframes", "xpath": ".//iframe/@src", "type": "list"}
            ]
        }
    
    @staticmethod
    def get_link_analysis_schema() -> Dict[str, Any]:
        """Schema for analyzing links"""
        return {
            "name": "Link Analysis",
            "baseXPath": "//body",
            "fields": [
                {"name": "internal_links", "xpath": ".//a[starts-with(@href, '/') or contains(@href, window.location.hostname)]/@href", "type": "list"},
                {"name": "external_links", "xpath": ".//a[starts-with(@href, 'http') and not(contains(@href, window.location.hostname))]/@href", "type": "list"},
                {"name": "email_links", "xpath": ".//a[starts-with(@href, 'mailto:')]/@href", "type": "list"},
                {"name": "phone_links", "xpath": ".//a[starts-with(@href, 'tel:')]/@href", "type": "list"},
                {"name": "download_links", "xpath": ".//a[contains(@href, '.pdf') or contains(@href, '.doc') or contains(@href, '.zip')]/@href", "type": "list"}
            ]
        }