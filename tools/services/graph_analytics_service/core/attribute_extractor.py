#!/usr/bin/env python3
"""
Attribute Extractor for Graph Analytics

Extracts attributes and properties of entities from text using:
1. Pattern-based extraction for structured attributes
2. LLM-based extraction for semantic attributes
3. Type inference for attribute values
4. Attribute validation and normalization
"""

import re
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from tools.base_service import BaseService
from .entity_extractor import Entity, EntityType

logger = get_logger(__name__)

class AttributeType(Enum):
    """Attribute value types"""
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"
    LIST = "LIST"
    OBJECT = "OBJECT"
    URL = "URL"
    EMAIL = "EMAIL"
    PHONE = "PHONE"

@dataclass
class Attribute:
    """Attribute data structure"""
    name: str
    value: Any
    attribute_type: AttributeType
    confidence: float
    source_text: str = ""
    normalized_value: Any = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.normalized_value is None:
            self.normalized_value = self.value

class AttributeExtractor(BaseService):
    """Extract attributes and properties of entities from text"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize attribute extractor
        
        Args:
            config: Configuration dict with extractor settings
        """
        super().__init__("AttributeExtractor")
        self.config = config or {}
        
        # Attribute patterns for different types
        self.attribute_patterns = {
            'age': [
                r'(\d+)\s*years?\s*old',
                r'age\s*:?\s*(\d+)',
                r'(\d+)\s*-year-old'
            ],
            'founded': [
                r'founded\s+in\s+(\d{4})',
                r'established\s+in\s+(\d{4})',
                r'started\s+in\s+(\d{4})'
            ],
            'location': [
                r'(?:located|based)\s+in\s+([^,\.]+)',
                r'headquarters\s+in\s+([^,\.]+)'
            ],
            'size': [
                r'(\d+(?:,\d+)*)\s*(?:employees?|people|staff)',
                r'team\s+of\s+(\d+(?:,\d+)*)',
            ],
            'revenue': [
                r'\$(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:million|billion)?',
                r'revenue\s+of\s+\$(\d+(?:,\d+)*(?:\.\d+)?)'
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'phone': [
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                r'\b\d{3}-\d{3}-\d{4}\b'
            ],
            'url': [
                r'https?://[^\s<>"]+',
                r'www\.[^\s<>"]+\.[a-z]{2,}'
            ]
        }
        
        logger.info("AttributeExtractor initialized")
    
    async def extract_attributes(self, text: str, entity: Entity, 
                               methods: List[str] = None) -> Dict[str, Attribute]:
        """Extract attributes for a specific entity
        
        Args:
            text: Input text to analyze
            entity: Entity to extract attributes for
            methods: List of extraction methods ['llm', 'pattern', 'hybrid']
            
        Returns:
            Dictionary of attribute name to Attribute object
        """
        if methods is None:
            methods = ['hybrid']
        
        all_attributes = {}
        
        for method in methods:
            if method == 'llm':
                attributes = await self._extract_with_llm(text, entity)
            elif method == 'pattern':
                attributes = self._extract_with_patterns(text, entity)
            elif method == 'hybrid':
                # Combine LLM and pattern-based extraction
                llm_attributes = await self._extract_with_llm(text, entity)
                pattern_attributes = self._extract_with_patterns(text, entity)
                attributes = self._merge_attributes(llm_attributes, pattern_attributes)
            else:
                logger.warning(f"Unknown extraction method: {method}")
                continue
                
            all_attributes.update(attributes)
        
        # Normalize and validate attributes
        normalized_attributes = self._normalize_attributes(all_attributes)
        
        logger.info(f"Extracted {len(normalized_attributes)} attributes for entity: {entity.text}")
        return normalized_attributes
    
    async def _extract_with_llm(self, text: str, entity: Entity) -> Dict[str, Attribute]:
        """Extract attributes using LLM"""
        try:
            prompt = f"""
            Extract all attributes and properties of the entity "{entity.text}" from the following text.
            The entity type is: {entity.entity_type.value}
            
            Text: "{text}"
            
            For each attribute, identify:
            1. Attribute name
            2. Attribute value
            3. Attribute type (TEXT, NUMBER, DATE, BOOLEAN, LIST, OBJECT, URL, EMAIL, PHONE)
            4. Confidence score (0.0-1.0)
            5. Source text where the attribute was found
            
            Return as JSON object:
            {{
                "attribute_name": {{
                    "value": "attribute value",
                    "type": "ATTRIBUTE_TYPE",
                    "confidence": 0.9,
                    "source_text": "relevant text snippet",
                    "metadata": {{"additional": "info"}}
                }}
            }}
            
            Only include attributes explicitly mentioned in the text.
            Common attributes to look for:
            - For PERSON: age, occupation, location, education, skills
            - For ORG: founded, size, location, industry, revenue, website
            - For PRODUCT: price, features, manufacturer, category
            - For EVENT: date, location, duration, participants
            """
            
            response, billing_info = await self.call_isa_with_billing(
                input_data=prompt,
                task="chat",
                service_type="text",
                parameters={"max_tokens": 1500, "temperature": 0.1},
                operation_name="attribute_extraction"
            )
            
            if 'text' in response:
                response_text = response['text']
            else:
                raise Exception("Invalid response format from ISA API")
            
            # Parse LLM response
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = response_text[json_start:json_end]
                    attributes_data = json.loads(json_str)
                    
                    attributes = {}
                    for attr_name, attr_data in attributes_data.items():
                        try:
                            attribute_type = AttributeType(attr_data.get('type', 'TEXT'))
                            attribute = Attribute(
                                name=attr_name,
                                value=attr_data.get('value'),
                                attribute_type=attribute_type,
                                confidence=attr_data.get('confidence', 0.7),
                                source_text=attr_data.get('source_text', ''),
                                metadata=attr_data.get('metadata', {})
                            )
                            attributes[attr_name] = attribute
                        except ValueError as e:
                            logger.warning(f"Invalid attribute type: {e}")
                            continue
                    
                    return attributes
                else:
                    logger.warning("No valid JSON found in LLM attribute response")
                    return {}
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM attribute response: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"LLM attribute extraction failed: {e}")
            return {}
    
    def _extract_with_patterns(self, text: str, entity: Entity) -> Dict[str, Attribute]:
        """Extract attributes using regex patterns"""
        attributes = {}
        
        # Get text context around the entity
        entity_context = self._get_entity_context(text, entity)
        
        for attr_name, patterns in self.attribute_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, entity_context, re.IGNORECASE)
                for match in matches:
                    try:
                        value = match.group(1) if match.groups() else match.group()
                        
                        # Infer attribute type
                        attr_type = self._infer_attribute_type(attr_name, value)
                        
                        attribute = Attribute(
                            name=attr_name,
                            value=value,
                            attribute_type=attr_type,
                            confidence=0.85,  # Good confidence for pattern matches
                            source_text=match.group()
                        )
                        
                        # Only keep highest confidence match for each attribute
                        if (attr_name not in attributes or 
                            attribute.confidence > attributes[attr_name].confidence):
                            attributes[attr_name] = attribute
                            
                    except (IndexError, AttributeError) as e:
                        logger.debug(f"Pattern match error: {e}")
                        continue
        
        return attributes
    
    def _get_entity_context(self, text: str, entity: Entity, window: int = 100) -> str:
        """Get text context around an entity"""
        start = max(0, entity.start - window)
        end = min(len(text), entity.end + window)
        return text[start:end]
    
    def _infer_attribute_type(self, attr_name: str, value: str) -> AttributeType:
        """Infer attribute type from name and value"""
        # Type inference based on attribute name
        name_type_map = {
            'age': AttributeType.NUMBER,
            'founded': AttributeType.DATE,
            'size': AttributeType.NUMBER,
            'revenue': AttributeType.NUMBER,
            'email': AttributeType.EMAIL,
            'phone': AttributeType.PHONE,
            'url': AttributeType.URL,
            'website': AttributeType.URL
        }
        
        if attr_name.lower() in name_type_map:
            return name_type_map[attr_name.lower()]
        
        # Type inference based on value patterns
        if re.match(r'^\d+$', value):
            return AttributeType.NUMBER
        elif re.match(r'^\d{4}$', value):
            return AttributeType.DATE
        elif re.match(r'^https?://', value):
            return AttributeType.URL
        elif '@' in value and '.' in value:
            return AttributeType.EMAIL
        elif re.match(r'^\d{3}-\d{3}-\d{4}$', value):
            return AttributeType.PHONE
        elif value.lower() in ['true', 'false', 'yes', 'no']:
            return AttributeType.BOOLEAN
        else:
            return AttributeType.TEXT
    
    def _merge_attributes(self, *attribute_dicts: Dict[str, Attribute]) -> Dict[str, Attribute]:
        """Merge multiple attribute dictionaries"""
        merged = {}
        
        for attr_dict in attribute_dicts:
            for attr_name, attribute in attr_dict.items():
                if (attr_name not in merged or 
                    attribute.confidence > merged[attr_name].confidence):
                    merged[attr_name] = attribute
        
        return merged
    
    def _normalize_attributes(self, attributes: Dict[str, Attribute]) -> Dict[str, Attribute]:
        """Normalize and validate attribute values"""
        normalized = {}
        
        for attr_name, attribute in attributes.items():
            try:
                normalized_value = self._normalize_value(attribute.value, attribute.attribute_type)
                attribute.normalized_value = normalized_value
                normalized[attr_name] = attribute
            except Exception as e:
                logger.warning(f"Failed to normalize attribute {attr_name}: {e}")
                # Keep original value if normalization fails
                normalized[attr_name] = attribute
        
        return normalized
    
    def _normalize_value(self, value: Any, attr_type: AttributeType) -> Any:
        """Normalize attribute value based on type"""
        if attr_type == AttributeType.NUMBER:
            # Remove commas and convert to number
            if isinstance(value, str):
                clean_value = value.replace(',', '')
                return float(clean_value) if '.' in clean_value else int(clean_value)
            return value
        
        elif attr_type == AttributeType.BOOLEAN:
            if isinstance(value, str):
                return value.lower() in ['true', 'yes', '1', 'on']
            return bool(value)
        
        elif attr_type == AttributeType.DATE:
            # Normalize date formats
            if isinstance(value, str):
                # Handle year format
                if re.match(r'^\d{4}$', value):
                    return f"{value}-01-01"
            return value
        
        elif attr_type == AttributeType.EMAIL:
            if isinstance(value, str):
                return value.lower().strip()
            return value
        
        elif attr_type == AttributeType.PHONE:
            if isinstance(value, str):
                # Normalize phone number format
                digits = re.sub(r'\D', '', value)
                if len(digits) == 10:
                    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
                elif len(digits) == 11 and digits[0] == '1':
                    return f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
            return value
        
        elif attr_type == AttributeType.LIST:
            if isinstance(value, str):
                # Split by common delimiters
                return [item.strip() for item in re.split(r'[,;]', value) if item.strip()]
            return value
        
        else:
            return value
    
    async def extract_entity_attributes_batch(self, text: str, 
                                            entities: List[Entity]) -> Dict[str, Dict[str, Attribute]]:
        """Extract attributes for multiple entities efficiently"""
        entity_attributes = {}
        
        for entity in entities:
            try:
                attributes = await self.extract_attributes(text, entity)
                entity_attributes[entity.text] = attributes
            except Exception as e:
                logger.error(f"Failed to extract attributes for {entity.text}: {e}")
                entity_attributes[entity.text] = {}
        
        return entity_attributes
    
    def get_attribute_statistics(self, entity_attributes: Dict[str, Dict[str, Attribute]]) -> Dict[str, Any]:
        """Get statistics about extracted attributes"""
        total_attributes = 0
        attribute_types = {}
        confidence_sum = 0
        attribute_names = set()
        
        for entity_name, attributes in entity_attributes.items():
            total_attributes += len(attributes)
            for attr_name, attribute in attributes.items():
                attribute_names.add(attr_name)
                attr_type = attribute.attribute_type.value
                attribute_types[attr_type] = attribute_types.get(attr_type, 0) + 1
                confidence_sum += attribute.confidence
        
        return {
            "total_attributes": total_attributes,
            "entities_with_attributes": len([e for e, a in entity_attributes.items() if a]),
            "unique_attribute_names": len(attribute_names),
            "attribute_names": list(attribute_names),
            "by_type": attribute_types,
            "average_confidence": confidence_sum / total_attributes if total_attributes > 0 else 0,
            "high_confidence": len([
                attr for attrs in entity_attributes.values() 
                for attr in attrs.values() if attr.confidence > 0.8
            ])
        }