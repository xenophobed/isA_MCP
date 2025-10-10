#!/usr/bin/env python3
"""
Generic Attribute Extractor for Knowledge Analytics

Extracts attributes and properties of entities from text using configurable domain schemas.
Uses intelligence service with domain-specific attribute types from configuration.
"""

import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path

from core.logging import get_logger
from tools.services.intelligence_service.language.text_extractor import extract_key_information
from .core.types import GenericEntity, GenericAttribute
from .core.config import DomainConfig
from .core.dask_manager import dask_manager

logger = get_logger(__name__)

class GenericAttributeExtractor:
    """Generic Attribute Extractor using domain configuration"""
    
    def __init__(self, 
                 domain_config: Union[DomainConfig, str, Path],
                 confidence_threshold: float = 0.7):
        """
        Initialize Generic Attribute Extractor
        
        Args:
            domain_config: Domain configuration or path to config file
            confidence_threshold: Minimum confidence threshold for attributes
        """
        
        # Load domain configuration
        if isinstance(domain_config, (str, Path)):
            config_path = Path(domain_config)
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                self.domain_config = DomainConfig.from_yaml(config_path)
            elif config_path.suffix.lower() == '.json':
                self.domain_config = DomainConfig.from_json(config_path)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
        else:
            self.domain_config = domain_config
        
        self.confidence_threshold = confidence_threshold
        
        # Get attribute types from domain configuration
        self.attribute_types = list(self.domain_config.attribute_registry.get_types())
        
        logger.info(f"GenericAttributeExtractor initialized for domain: {self.domain_config.domain_name}")
        logger.info(f"Available attribute types: {self.attribute_types}")
    
    async def extract_attributes(self, 
                               text: str, 
                               entity: GenericEntity,
                               use_dask: bool = False) -> List[GenericAttribute]:
        """
        Extract attributes for a specific entity using domain configuration
        
        Args:
            text: Input text to analyze
            entity: Generic entity to extract attributes for
            use_dask: Whether to use Dask for parallel processing (for future batch processing)
            
        Returns:
            List of GenericAttribute objects
        """
        
        try:
            # Get entity schema from domain configuration
            entity_schema = self.domain_config.entity_registry.get_schema(entity.entity_type)
            
            # Build domain-specific context for attribute extraction
            context = self._build_attribute_context(entity, entity_schema)
            
            # Use LLM extraction with domain context
            attributes = await self._extract_with_llm(text, entity, context)
            
            # Filter by confidence threshold
            filtered_attributes = [
                attr for attr in attributes 
                if attr.confidence >= self.confidence_threshold
            ]
            
            logger.info(f"Extracted {len(filtered_attributes)} attributes for entity: {entity.text}")
            return filtered_attributes
            
        except Exception as e:
            logger.error(f"Attribute extraction failed: {e}")
            return []
    
    async def extract_attributes_batch(self,
                                     text: str,
                                     entities: List[GenericEntity],
                                     use_dask: bool = False) -> List[List[GenericAttribute]]:
        """Extract attributes for multiple entities, optionally using Dask"""
        if not entities:
            return []
        
        if use_dask and len(entities) > 1:
            async def process_entity(entity: GenericEntity) -> List[GenericAttribute]:
                return await self.extract_attributes(text, entity)
            
            return await dask_manager.process_in_parallel(entities, process_entity)
        else:
            results = []
            for entity in entities:
                attributes = await self.extract_attributes(text, entity)
                results.append(attributes)
            return results
    
    def _build_attribute_context(self, entity: GenericEntity, entity_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Build domain-specific context for attribute extraction"""
        
        context = {
            "entity": entity.text,
            "entity_type": entity.entity_type,
            "domain": self.domain_config.domain_name,
            "language": self.domain_config.language,
            "expected_attributes": entity_schema
        }
        
        # Add domain-specific attribute prompts if available
        if "attribute_extraction" in self.domain_config.prompts:
            context["extraction_prompt"] = self.domain_config.prompts["attribute_extraction"]
        
        return context

    async def _extract_with_llm(self, 
                               text: str, 
                               entity: GenericEntity, 
                               context: Dict[str, Any]) -> List[GenericAttribute]:
        """Extract attributes using LLM via intelligence service"""
        try:
            # Get entity context around the entity position
            entity_context = self._get_entity_context(text, entity, window=200)
            
            # Build schema based on domain configuration
            expected_attributes = context.get("expected_attributes", {})
            
            extraction_text = f"""Extract attributes and properties of the entity "{entity.text}" from the following text.
Entity type: {entity.entity_type}
Domain: {context.get('domain', 'generic')}

Expected attributes for this entity type:
{json.dumps(expected_attributes, indent=2)}

Text context: {entity_context}

Return attributes as JSON with format:
{{
  "attribute_name": {{
    "value": "actual_value",
    "attribute_type": "TYPE",
    "confidence": 0.9,
    "source_text": "supporting text"
  }}
}}

Only include attributes explicitly mentioned in the text."""
            
            # Create schema for intelligence service
            schema = {"attributes": "Dictionary of attribute names to attribute objects with value, type, confidence, and source"}
            
            # Use intelligence service for extraction
            result = await extract_key_information(
                text=extraction_text,
                schema=schema
            )
            
            if not result.get('success'):
                logger.warning(f"LLM attribute extraction failed: {result.get('error')}")
                return []
            
            # Extract attributes from result
            attributes_data = result.get('data', {}).get('attributes', {})
            
            # Convert to GenericAttribute objects
            attributes = []
            for attr_name, attr_data in attributes_data.items():
                if attr_data and isinstance(attr_data, dict):
                    attribute = self._create_generic_attribute(
                        entity, attr_name, attr_data, entity_context
                    )
                    if attribute:
                        attributes.append(attribute)
            
            logger.info(f"LLM extracted {len(attributes)} attributes for {entity.text}")
            return attributes
            
        except Exception as e:
            logger.error(f"LLM attribute extraction failed: {e}")
            return []
    
    def _create_generic_attribute(self, 
                                 entity: GenericEntity,
                                 attr_name: str, 
                                 attr_data: Dict[str, Any],
                                 source_text: str) -> Optional[GenericAttribute]:
        """Create GenericAttribute object from extracted data"""
        try:
            value = attr_data.get('value', '')
            attr_type = attr_data.get('attribute_type', 'TEXT')
            confidence = float(attr_data.get('confidence', 0.7))
            source = attr_data.get('source_text', source_text[:100])
            
            # Validate attribute type against domain configuration
            if attr_type not in self.attribute_types and self.attribute_types:
                # Try to map to a valid domain attribute type
                mapped_type = self._map_to_domain_attribute_type(attr_type)
                if mapped_type:
                    attr_type = mapped_type
                else:
                    logger.warning(f"Unknown attribute type: {attr_type}, using TEXT")
                    attr_type = "TEXT"
            
            return GenericAttribute(
                entity_id=entity.id,
                name=attr_name,
                value=value,
                attribute_type=attr_type,
                confidence=confidence,
                source_text=source,
                extraction_method="llm"
            )
            
        except Exception as e:
            logger.warning(f"Failed to create attribute {attr_name}: {e}")
            return None
    
    def _map_to_domain_attribute_type(self, attr_type: str) -> Optional[str]:
        """Map generic attribute type to domain-specific type"""
        
        # Common attribute type mappings
        generic_mappings = {
            'TEXT': ['TEXT', 'STRING', 'VARCHAR'],
            'NUMBER': ['NUMBER', 'INTEGER', 'FLOAT', 'NUMERIC'],
            'DATE': ['DATE', 'DATETIME', 'TIMESTAMP', 'TIME'],
            'BOOLEAN': ['BOOLEAN', 'BOOL', 'FLAG'],
            'URL': ['URL', 'LINK', 'URI'],
            'EMAIL': ['EMAIL', 'EMAIL_ADDRESS'],
            'PHONE': ['PHONE', 'PHONE_NUMBER', 'TEL']
        }
        
        attr_upper = attr_type.upper()
        
        # Check if the type directly exists in domain
        if attr_upper in self.attribute_types:
            return attr_upper
        
        # Try to find a mapping
        for domain_type in self.attribute_types:
            domain_upper = domain_type.upper()
            if domain_upper in generic_mappings:
                if attr_upper in generic_mappings[domain_upper]:
                    return domain_type
        
        return None
    
    def _get_entity_context(self, text: str, entity: GenericEntity, window: int = 200) -> str:
        """Get text context around an entity"""
        start = max(0, entity.start_position - window)
        end = min(len(text), entity.end_position + window)
        return text[start:end]
    
    
    def get_domain_attribute_types(self) -> List[str]:
        """Get all attribute types available in the current domain"""
        return self.attribute_types.copy()
    
    def get_attribute_statistics(self, attributes: List[GenericAttribute]) -> Dict[str, Any]:
        """Get statistics about extracted attributes"""
        if not attributes:
            return {"total": 0, "domain": self.domain_config.domain_name}
        
        type_counts = {}
        confidence_sum = 0
        extraction_methods = {}
        
        for attr in attributes:
            attr_type = attr.attribute_type
            type_counts[attr_type] = type_counts.get(attr_type, 0) + 1
            confidence_sum += attr.confidence
            
            method = attr.extraction_method
            extraction_methods[method] = extraction_methods.get(method, 0) + 1
        
        return {
            "domain": self.domain_config.domain_name,
            "total": len(attributes),
            "by_type": type_counts,
            "by_extraction_method": extraction_methods,
            "average_confidence": confidence_sum / len(attributes),
            "high_confidence": len([a for a in attributes if a.confidence > 0.8]),
            "confidence_distribution": {
                "high (>0.8)": len([a for a in attributes if a.confidence > 0.8]),
                "medium (0.5-0.8)": len([a for a in attributes if 0.5 <= a.confidence <= 0.8]),
                "low (<0.5)": len([a for a in attributes if a.confidence < 0.5])
            }
        }


# Convenience functions for quick domain setup
def create_business_attribute_extractor(confidence_threshold: float = 0.7) -> GenericAttributeExtractor:
    """Create an attribute extractor configured for business domain"""
    from pathlib import Path
    config_path = Path(__file__).parent / "domains" / "business.yaml"
    return GenericAttributeExtractor(config_path, confidence_threshold)


def create_medical_attribute_extractor(confidence_threshold: float = 0.85) -> GenericAttributeExtractor:
    """Create an attribute extractor configured for medical domain (higher confidence)"""
    from pathlib import Path
    config_path = Path(__file__).parent / "domains" / "medical.yaml"
    return GenericAttributeExtractor(config_path, confidence_threshold)
