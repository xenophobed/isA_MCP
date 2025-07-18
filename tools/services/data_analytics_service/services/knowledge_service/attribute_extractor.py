#!/usr/bin/env python3
"""
Attribute Extractor for Graph Analytics - Refactored Version

Extracts attributes and properties of entities from text using:
1. LLM-based extraction for semantic attributes via intelligence service
2. Type inference for attribute values
3. Attribute validation and normalization
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from tools.services.intelligence_service.language.text_extractor import text_extractor
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

class AttributeExtractor:
    """Extract attributes and properties of entities from text using intelligence service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize attribute extractor
        
        Args:
            config: Configuration dict with extractor settings
        """
        self.config = config or {}
        
        # Configuration settings
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
        self.use_llm = self.config.get('use_llm', True)
        
        logger.info("AttributeExtractor initialized with intelligence service")
    
    async def extract_attributes(self, text: str, entity: Entity, 
                               methods: List[str] = None) -> Dict[str, Attribute]:
        """Extract attributes for a specific entity
        
        Args:
            text: Input text to analyze
            entity: Entity to extract attributes for
            methods: List of extraction methods (only 'llm' supported for now)
            
        Returns:
            Dictionary of attribute name to Attribute object
        """
        if not self.use_llm:
            logger.warning("LLM disabled, returning empty attribute list")
            return {}
        
        if methods is None:
            methods = ['llm']
        
        # Only use LLM extraction now
        attributes = await self._extract_with_llm(text, entity)
        
        # Normalize and validate attributes
        normalized_attributes = self._normalize_attributes(attributes)
        
        logger.info(f"Extracted {len(normalized_attributes)} attributes for entity: {entity.text}")
        return normalized_attributes
    
    async def _extract_with_llm(self, text: str, entity: Entity) -> Dict[str, Attribute]:
        """Extract attributes using LLM via intelligence service"""
        try:
            # Create custom schema for attribute extraction based on entity type
            schema = self._get_schema_for_entity_type(entity.entity_type)
            
            # Get text context around the entity
            entity_context = self._get_entity_context(text, entity, window=200)
            
            extraction_text = f"""Extract attributes and properties of the entity "{entity.text}" from the following text.
Entity type: {entity.entity_type.value}

Text context: {entity_context}

For each attribute found, provide:
- Clear attribute name
- Attribute value  
- Attribute type (TEXT, NUMBER, DATE, BOOLEAN, LIST, OBJECT, URL, EMAIL, PHONE)
- Confidence score (0.0-1.0)
- Source text snippet where found

Only include attributes explicitly mentioned in the text."""
            
            # Use intelligence service for extraction
            result = await text_extractor.extract_key_information(
                text=extraction_text,
                schema=schema
            )
            
            if not result.get('success'):
                logger.warning(f"LLM attribute extraction failed: {result.get('error')}")
                return {}
            
            # Extract attributes from result
            attributes_data = result.get('data', {})
            
            # Convert to Attribute objects
            attributes = {}
            for attr_name, attr_value in attributes_data.items():
                if attr_value and str(attr_value).strip():
                    attribute = self._create_attribute_from_data(
                        attr_name, attr_value, entity_context
                    )
                    if attribute:
                        attributes[attr_name] = attribute
            
            logger.info(f"LLM extracted {len(attributes)} attributes for {entity.text}")
            return attributes
            
        except Exception as e:
            logger.error(f"LLM attribute extraction failed: {e}")
            return {}
    
    def _get_schema_for_entity_type(self, entity_type: EntityType) -> Dict[str, str]:
        """Get attribute extraction schema based on entity type"""
        schemas = {
            EntityType.PERSON: {
                "age": "Age in years",
                "occupation": "Job title or profession",
                "location": "Current location or residence",
                "education": "Educational background",
                "skills": "Professional skills or expertise",
                "company": "Current employer or organization",
                "nationality": "Country of origin or citizenship"
            },
            EntityType.ORGANIZATION: {
                "founded": "Year founded or established",
                "size": "Number of employees or scale",
                "location": "Headquarters or main location",
                "industry": "Business sector or industry",
                "revenue": "Annual revenue or financial information",
                "website": "Official website URL",
                "ceo": "Chief Executive Officer or leader",
                "products": "Main products or services"
            },
            EntityType.PRODUCT: {
                "price": "Cost or pricing information",
                "features": "Key features or capabilities",
                "manufacturer": "Company that makes the product",
                "category": "Product category or type",
                "release_date": "When the product was launched",
                "specifications": "Technical specifications"
            },
            EntityType.EVENT: {
                "date": "When the event occurred or will occur",
                "location": "Where the event takes place",
                "duration": "How long the event lasts",
                "participants": "Who is involved in the event",
                "organizer": "Who organized the event",
                "purpose": "Reason or goal of the event"
            },
            EntityType.LOCATION: {
                "population": "Number of residents",
                "country": "Country the location is in",
                "region": "State, province, or region",
                "coordinates": "Geographic coordinates",
                "notable_features": "Famous landmarks or characteristics"
            }
        }
        
        return schemas.get(entity_type, {
            "description": "General description or information",
            "type": "Classification or category",
            "related_entities": "Associated entities or connections"
        })
    
    def _create_attribute_from_data(self, attr_name: str, attr_value: Any, 
                                  source_text: str) -> Optional[Attribute]:
        """Create Attribute object from extracted data"""
        try:
            # Infer attribute type
            attr_type = self._infer_attribute_type(attr_name, str(attr_value))
            
            # Determine confidence based on attribute type and value quality
            confidence = self._calculate_confidence(attr_name, attr_value, attr_type)
            
            return Attribute(
                name=attr_name,
                value=attr_value,
                attribute_type=attr_type,
                confidence=confidence,
                source_text=source_text[:100],  # Limit source text length
                metadata={"extraction_method": "llm"}
            )
        except Exception as e:
            logger.warning(f"Failed to create attribute {attr_name}: {e}")
            return None
    
    def _calculate_confidence(self, attr_name: str, attr_value: Any, 
                            attr_type: AttributeType) -> float:
        """Calculate confidence score for an attribute"""
        base_confidence = 0.8  # Base LLM confidence
        
        # Boost confidence for structured data
        if attr_type in [AttributeType.EMAIL, AttributeType.PHONE, AttributeType.URL]:
            return min(0.95, base_confidence + 0.1)
        
        # Boost confidence for numeric data
        if attr_type == AttributeType.NUMBER and str(attr_value).replace(',', '').replace('.', '').isdigit():
            return min(0.9, base_confidence + 0.05)
        
        # Lower confidence for very short or generic values
        if len(str(attr_value).strip()) < 3:
            return max(0.5, base_confidence - 0.2)
        
        return base_confidence
    
    def _get_entity_context(self, text: str, entity: Entity, window: int = 200) -> str:
        """Get text context around an entity"""
        start = max(0, entity.start - window)
        end = min(len(text), entity.end + window)
        return text[start:end]
    
    def _infer_attribute_type(self, attr_name: str, value: str) -> AttributeType:
        """Infer attribute type from name and value"""
        import re
        
        # Type inference based on attribute name
        name_type_map = {
            'age': AttributeType.NUMBER,
            'founded': AttributeType.DATE,
            'size': AttributeType.NUMBER,
            'revenue': AttributeType.NUMBER,
            'email': AttributeType.EMAIL,
            'phone': AttributeType.PHONE,
            'url': AttributeType.URL,
            'website': AttributeType.URL,
            'price': AttributeType.NUMBER,
            'date': AttributeType.DATE,
            'year': AttributeType.DATE,
            'population': AttributeType.NUMBER
        }
        
        if attr_name.lower() in name_type_map:
            return name_type_map[attr_name.lower()]
        
        # Type inference based on value patterns
        if re.match(r'^\d+$', str(value)):
            return AttributeType.NUMBER
        elif re.match(r'^\d{4}$', str(value)):
            return AttributeType.DATE
        elif re.match(r'^https?://', str(value)):
            return AttributeType.URL
        elif '@' in str(value) and '.' in str(value):
            return AttributeType.EMAIL
        elif re.match(r'^\d{3}-\d{3}-\d{4}$', str(value)):
            return AttributeType.PHONE
        elif str(value).lower() in ['true', 'false', 'yes', 'no']:
            return AttributeType.BOOLEAN
        elif ',' in str(value) and len(str(value).split(',')) > 2:
            return AttributeType.LIST
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
        import re
        
        if attr_type == AttributeType.NUMBER:
            # Remove commas and convert to number
            if isinstance(value, str):
                clean_value = value.replace(',', '').replace('$', '').strip()
                try:
                    return float(clean_value) if '.' in clean_value else int(clean_value)
                except ValueError:
                    return value
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
        
        elif attr_type == AttributeType.URL:
            if isinstance(value, str):
                # Ensure URL has protocol
                if not value.startswith(('http://', 'https://')):
                    return f"https://{value}"
                return value.strip()
            return value
        
        else:
            return str(value).strip() if value else value
    
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