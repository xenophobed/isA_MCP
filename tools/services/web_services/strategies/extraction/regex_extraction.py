#!/usr/bin/env python
"""
Regex Extraction Strategy
Pattern-based data extraction using regular expressions
Inspired by Crawl4AI's regex extraction capabilities
"""
import re
from typing import Dict, Any, List, Optional, Pattern
from playwright.async_api import Page

from core.logging import get_logger
from ..base import ExtractionStrategy

logger = get_logger(__name__)

class RegexExtractionStrategy(ExtractionStrategy):
    """Extract structured data using regular expression patterns"""
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize Regex extraction strategy
        
        Args:
            schema: Extraction schema with regex patterns
                   Format: {
                       "name": "Schema Name",
                       "fields": [
                           {"name": "email", "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "flags": "IGNORECASE"},
                           {"name": "phone", "pattern": r"\b\d{3}-\d{3}-\d{4}\b", "type": "all"},
                           {"name": "price", "pattern": r"\$\d+(?:\.\d{2})?", "type": "first"}
                       ]
                   }
        """
        self.schema = schema
        self.name = schema.get("name", "Regex Extraction")
        self.fields = schema.get("fields", [])
        
        # Compile regex patterns
        self.compiled_patterns = {}
        for field in self.fields:
            field_name = field.get("name")
            pattern = field.get("pattern")
            flags_str = field.get("flags", "")
            
            if field_name and pattern:
                # Parse flags
                flags = 0
                if "IGNORECASE" in flags_str or "I" in flags_str:
                    flags |= re.IGNORECASE
                if "MULTILINE" in flags_str or "M" in flags_str:
                    flags |= re.MULTILINE
                if "DOTALL" in flags_str or "S" in flags_str:
                    flags |= re.DOTALL
                if "VERBOSE" in flags_str or "X" in flags_str:
                    flags |= re.VERBOSE
                
                try:
                    self.compiled_patterns[field_name] = re.compile(pattern, flags)
                except re.error as e:
                    logger.warning(f"Invalid regex pattern for field '{field_name}': {e}")
    
    async def extract(self, page: Page, html: str) -> List[Dict[str, Any]]:
        """Extract data based on regex patterns"""
        logger.info(f"🔍 Extracting data using Regex strategy: {self.name}")
        
        try:
            # Get page text content
            page_text = await page.text_content("body") or ""
            
            # Also use HTML for pattern matching
            full_content = f"{page_text}\n{html}"
            
            result = {}
            
            # Extract each field using regex
            for field in self.fields:
                field_name = field.get("name")
                extraction_type = field.get("type", "all")  # "first", "all", "count"
                
                if field_name not in self.compiled_patterns:
                    continue
                
                pattern = self.compiled_patterns[field_name]
                
                try:
                    if extraction_type == "first":
                        # Extract first match
                        match = pattern.search(full_content)
                        if match:
                            result[field_name] = match.group()
                        else:
                            result[field_name] = ""
                    
                    elif extraction_type == "all":
                        # Extract all matches
                        matches = pattern.findall(full_content)
                        result[field_name] = matches
                    
                    elif extraction_type == "count":
                        # Count matches
                        matches = pattern.findall(full_content)
                        result[field_name] = len(matches)
                    
                    elif extraction_type == "groups":
                        # Extract with groups
                        matches = []
                        for match in pattern.finditer(full_content):
                            if match.groups():
                                # If there are groups, return them as dict or list
                                if len(match.groups()) == 1:
                                    matches.append(match.group(1))
                                else:
                                    matches.append(match.groups())
                            else:
                                matches.append(match.group())
                        result[field_name] = matches
                    
                    else:
                        # Default to all matches
                        matches = pattern.findall(full_content)
                        result[field_name] = matches
                
                except Exception as e:
                    logger.warning(f"Failed to extract field '{field_name}' with regex: {e}")
                    # Set default value based on type
                    if extraction_type in ["all", "groups"]:
                        result[field_name] = []
                    elif extraction_type == "count":
                        result[field_name] = 0
                    else:
                        result[field_name] = ""
            
            # Return as list for consistency with other strategies
            results = [result] if any(value for value in result.values() if value) else []
            
            logger.info(f"✅ Regex extraction completed: {len(results)} items extracted")
            return results
            
        except Exception as e:
            logger.error(f"❌ Regex extraction failed: {e}")
            return []
    
    def get_strategy_name(self) -> str:
        return f"regex_extraction_{self.name.lower().replace(' ', '_')}"

class PredefinedRegexSchemas:
    """Predefined regex extraction schemas for common data patterns"""
    
    @staticmethod
    def get_contact_extraction_schema() -> Dict[str, Any]:
        """Schema for extracting contact information"""
        return {
            "name": "Contact Information",
            "fields": [
                {
                    "name": "emails",
                    "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    "type": "all",
                    "flags": "IGNORECASE"
                },
                {
                    "name": "phone_numbers",
                    "pattern": r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}",
                    "type": "all"
                },
                {
                    "name": "urls",
                    "pattern": r"https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?",
                    "type": "all",
                    "flags": "IGNORECASE"
                }
            ]
        }
    
    @staticmethod
    def get_financial_data_schema() -> Dict[str, Any]:
        """Schema for extracting financial information"""
        return {
            "name": "Financial Data",
            "fields": [
                {
                    "name": "prices",
                    "pattern": r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?",
                    "type": "all"
                },
                {
                    "name": "percentages",
                    "pattern": r"\d+(?:\.\d+)?%",
                    "type": "all"
                },
                {
                    "name": "currency_amounts",
                    "pattern": r"(?:USD|EUR|GBP|JPY|CNY)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?",
                    "type": "all",
                    "flags": "IGNORECASE"
                },
                {
                    "name": "credit_cards",
                    "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
                    "type": "count"  # Count for security, don't extract actual numbers
                }
            ]
        }
    
    @staticmethod
    def get_datetime_schema() -> Dict[str, Any]:
        """Schema for extracting date and time information"""
        return {
            "name": "Date Time Information",
            "fields": [
                {
                    "name": "dates_mdy",
                    "pattern": r"\b(?:0?[1-9]|1[0-2])[\/\-\.](0?[1-9]|[12]\d|3[01])[\/\-\.](?:19|20)\d{2}\b",
                    "type": "all"
                },
                {
                    "name": "dates_dmy",
                    "pattern": r"\b(?:0?[1-9]|[12]\d|3[01])[\/\-\.](?:0?[1-9]|1[0-2])[\/\-\.](?:19|20)\d{2}\b",
                    "type": "all"
                },
                {
                    "name": "iso_dates",
                    "pattern": r"\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b",
                    "type": "all"
                },
                {
                    "name": "times",
                    "pattern": r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s?[AaPp][Mm])?\b",
                    "type": "all"
                }
            ]
        }
    
    @staticmethod
    def get_social_media_schema() -> Dict[str, Any]:
        """Schema for extracting social media information"""
        return {
            "name": "Social Media Data",
            "fields": [
                {
                    "name": "twitter_handles",
                    "pattern": r"@[A-Za-z0-9_]{1,15}",
                    "type": "all"
                },
                {
                    "name": "hashtags",
                    "pattern": r"#[A-Za-z0-9_]+",
                    "type": "all"
                },
                {
                    "name": "instagram_urls",
                    "pattern": r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+/?",
                    "type": "all",
                    "flags": "IGNORECASE"
                },
                {
                    "name": "linkedin_profiles",
                    "pattern": r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9-]+/?",
                    "type": "all",
                    "flags": "IGNORECASE"
                }
            ]
        }
    
    @staticmethod
    def get_technical_data_schema() -> Dict[str, Any]:
        """Schema for extracting technical information"""
        return {
            "name": "Technical Data",
            "fields": [
                {
                    "name": "ip_addresses",
                    "pattern": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
                    "type": "all"
                },
                {
                    "name": "mac_addresses",
                    "pattern": r"\b[0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5}\b",
                    "type": "all"
                },
                {
                    "name": "version_numbers",
                    "pattern": r"\bv?\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9]+)?\b",
                    "type": "all"
                },
                {
                    "name": "file_paths",
                    "pattern": r"(?:[A-Za-z]:\\|/)[^\s<>:\"|?*]+",
                    "type": "all"
                },
                {
                    "name": "api_keys",
                    "pattern": r"\b[A-Za-z0-9]{32,}\b",
                    "type": "count"  # Count for security, don't extract actual keys
                }
            ]
        }
    
    @staticmethod
    def get_address_schema() -> Dict[str, Any]:
        """Schema for extracting address information"""
        return {
            "name": "Address Information",
            "fields": [
                {
                    "name": "zip_codes_us",
                    "pattern": r"\b\d{5}(?:-\d{4})?\b",
                    "type": "all"
                },
                {
                    "name": "postal_codes_ca",
                    "pattern": r"\b[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d\b",
                    "type": "all",
                    "flags": "IGNORECASE"
                },
                {
                    "name": "street_addresses",
                    "pattern": r"\b\d+\s+[A-Za-z0-9\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Circle|Cir|Court|Ct)\b",
                    "type": "all",
                    "flags": "IGNORECASE"
                },
                {
                    "name": "po_boxes",
                    "pattern": r"\bP\.?O\.?\s+Box\s+\d+\b",
                    "type": "all",
                    "flags": "IGNORECASE"
                }
            ]
        }