#!/usr/bin/env python3
"""
Generic Entity Extractor for Knowledge Analytics

Extracts named entities from text using configurable domain schemas.
Uses intelligence service with domain-specific entity types from configuration.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path

from core.logging import get_logger
from tools.services.intelligence_service.language.text_extractor import extract_entities as extract_entities_service
from .core.types import GenericEntity
from .core.config import DomainConfig
from .core.dask_manager import dask_manager

logger = get_logger(__name__)

class GenericEntityExtractor:
    """Generic Entity Extractor using domain configuration"""
    
    def __init__(self, 
                 domain_config: Union[DomainConfig, str, Path],
                 confidence_threshold: float = 0.7):
        """
        Initialize Generic Entity Extractor
        
        Args:
            domain_config: Domain configuration or path to config file
            confidence_threshold: Minimum confidence threshold for entities
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
        
        # Get entity types from domain configuration
        self.entity_types = list(self.domain_config.entity_registry.get_types())
        
        logger.info(f"GenericEntityExtractor initialized for domain: {self.domain_config.domain_name}")
        logger.info(f"Available entity types: {self.entity_types}")
    
    async def extract_entities(self, 
                             text: str,
                             filter_types: List[str] = None,
                             use_dask: bool = False) -> List[GenericEntity]:
        """
        Extract entities using intelligence service with domain-specific types
        
        Args:
            text: Input text to analyze
            filter_types: Optional list of specific entity types to extract
            use_dask: Whether to use Dask for parallel processing (currently for future chunking)
            
        Returns:
            List of GenericEntity objects
        """
        
        try:
            # Determine which entity types to extract
            target_types = filter_types or self.entity_types
            
            # Build domain-specific context for the LLM
            context = self._build_extraction_context(target_types)
            
            # Use intelligence service for entity extraction with domain context
            result = await extract_entities_service(
                text=text,
                confidence_threshold=self.confidence_threshold
            )
            
            if not result.get('success'):
                logger.warning(f"Entity extraction failed: {result.get('error')}")
                return []
            
            # Convert to GenericEntity objects using domain configuration
            entities = self._convert_to_generic_entities(result, text)
            
            # Filter by confidence threshold
            filtered_entities = [
                e for e in entities 
                if e.confidence >= self.confidence_threshold
            ]
            
            logger.info(f"Extracted {len(filtered_entities)} entities from text ({len(text):,} chars)")
            return filtered_entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    async def extract_entities_batch(self, 
                                   texts: List[str],
                                   filter_types: List[str] = None,
                                   use_dask: bool = False) -> List[List[GenericEntity]]:
        """Extract entities from multiple texts, optionally using Dask"""
        if not texts:
            return []
        
        if use_dask and len(texts) > 1:
            async def process_text(text: str) -> List[GenericEntity]:
                return await self.extract_entities(text, filter_types)
            
            return await dask_manager.process_in_parallel(texts, process_text)
        else:
            results = []
            for text in texts:
                entities = await self.extract_entities(text, filter_types)
                results.append(entities)
            return results
    
    def _build_extraction_context(self, target_types: List[str]) -> Dict[str, Any]:
        """Build domain-specific context for entity extraction"""
        
        context = {
            "domain": self.domain_config.domain_name,
            "language": self.domain_config.language,
            "entity_types": target_types
        }
        
        # Add entity schemas and examples
        entity_definitions = {}
        for entity_type in target_types:
            schema = self.domain_config.entity_registry.get_schema(entity_type)
            patterns = self.domain_config.entity_registry.get_extraction_patterns(entity_type)
            prompts = self.domain_config.entity_registry.get_ai_prompts(entity_type)
            
            entity_definitions[entity_type] = {
                "schema": schema,
                "patterns": patterns,
                "description": prompts.get("extraction", f"Extract {entity_type} entities")
            }
        
        context["entity_definitions"] = entity_definitions
        
        # Add domain-specific prompts if available
        if "entity_extraction" in self.domain_config.prompts:
            context["extraction_prompt"] = self.domain_config.prompts["entity_extraction"]
        
        return context
    
    def _convert_to_generic_entities(self, result: Dict[str, Any], source_text: str) -> List[GenericEntity]:
        """Convert intelligence service result to GenericEntity objects"""
        
        entities = []
        entities_data = result.get('data', {}).get('entities', {})
        
        for entity_type_name, entity_list in entities_data.items():
            # Validate entity type against domain configuration
            if entity_type_name not in self.entity_types:
                # Try to map to a valid domain entity type
                mapped_type = self._map_to_domain_type(entity_type_name)
                if mapped_type:
                    entity_type_name = mapped_type
                else:
                    logger.warning(f"Unknown entity type: {entity_type_name}, skipping")
                    continue
            
            for entity_item in entity_list:
                try:
                    # Handle both string format and object format
                    if isinstance(entity_item, str):
                        entity_text = entity_item
                        confidence = result.get('confidence', 0.8)
                        position = self._find_text_position(entity_text, source_text)
                    else:
                        entity_text = entity_item.get('name', entity_item.get('text', ''))
                        confidence = entity_item.get('confidence', 0.7)
                        position = entity_item.get('position', self._find_text_position(entity_text, source_text))
                    
                    # Handle position data
                    start_pos = position[0] if len(position) > 0 else 0
                    end_pos = position[1] if len(position) > 1 else start_pos + len(entity_text)
                    
                    # Create GenericEntity
                    entity = GenericEntity(
                        text=entity_text,
                        entity_type=entity_type_name,
                        confidence=confidence,
                        start_position=start_pos,
                        end_position=end_pos,
                        extraction_method="llm"
                    )
                    
                    if entity.text.strip():
                        entities.append(entity)
                        
                except Exception as e:
                    logger.warning(f"Failed to create entity from data: {e}")
                    continue
        
        return entities
    
    def _map_to_domain_type(self, type_str: str) -> Optional[str]:
        """Map generic entity type to domain-specific type"""
        
        # Common mappings that work across domains
        generic_mappings = {
            'PERSON': ['PERSON', 'PEOPLE', 'INDIVIDUAL'],
            'ORGANIZATION': ['ORGANIZATION', 'ORG', 'COMPANY', 'INSTITUTION'],
            'LOCATION': ['LOCATION', 'LOC', 'PLACE', 'GEOGRAPHY'],
            'DATE': ['DATE', 'TIME', 'TEMPORAL'],
            'MONEY': ['MONEY', 'CURRENCY', 'FINANCIAL']
        }
        
        type_upper = type_str.upper()
        
        # Check if the type directly exists in domain
        if type_upper in self.entity_types:
            return type_upper
        
        # Try to find a mapping
        for domain_type in self.entity_types:
            domain_upper = domain_type.upper()
            if domain_upper in generic_mappings:
                if type_upper in generic_mappings[domain_upper]:
                    return domain_type
        
        return None
    
    def _find_text_position(self, entity_text: str, source_text: str) -> List[int]:
        """Find the position of entity text in source text"""
        try:
            start = source_text.lower().find(entity_text.lower())
            if start != -1:
                return [start, start + len(entity_text)]
            else:
                return [0, len(entity_text)]
        except:
            return [0, len(entity_text)]
    
    def get_domain_entity_types(self) -> List[str]:
        """Get all entity types available in the current domain"""
        return self.entity_types.copy()
    
    def get_entity_schema(self, entity_type: str) -> Dict[str, Any]:
        """Get schema definition for a specific entity type"""
        if entity_type not in self.entity_types:
            raise ValueError(f"Entity type '{entity_type}' not available in domain '{self.domain_config.domain_name}'")
        
        return self.domain_config.entity_registry.get_schema(entity_type)
    
    def add_entity_type(self, 
                       type_name: str,
                       schema: Dict[str, Any],
                       patterns: List[str] = None,
                       ai_prompts: Dict[str, str] = None):
        """Dynamically add a new entity type to the domain"""
        
        self.domain_config.entity_registry.register_type(
            type_name=type_name,
            schema=schema,
            extraction_patterns=patterns or [],
            ai_prompts=ai_prompts or {}
        )
        
        # Update local entity types list
        self.entity_types = list(self.domain_config.entity_registry.get_types())
        
        logger.info(f"Added new entity type: {type_name}")
    
    def get_entity_statistics(self, entities: List[GenericEntity]) -> Dict[str, Any]:
        """Get statistics about extracted entities"""
        if not entities:
            return {"total": 0, "domain": self.domain_config.domain_name}
        
        type_counts = {}
        confidence_sum = 0
        extraction_methods = {}
        
        for entity in entities:
            entity_type = entity.entity_type
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
            confidence_sum += entity.confidence
            
            method = entity.extraction_method
            extraction_methods[method] = extraction_methods.get(method, 0) + 1
        
        return {
            "domain": self.domain_config.domain_name,
            "total": len(entities),
            "by_type": type_counts,
            "by_extraction_method": extraction_methods,
            "average_confidence": confidence_sum / len(entities),
            "high_confidence": len([e for e in entities if e.confidence > 0.8]),
            "unique_entities": len(set(e.text.lower() for e in entities)),
            "confidence_distribution": {
                "high (>0.8)": len([e for e in entities if e.confidence > 0.8]),
                "medium (0.5-0.8)": len([e for e in entities if 0.5 <= e.confidence <= 0.8]),
                "low (<0.5)": len([e for e in entities if e.confidence < 0.5])
            }
        }
    
    def merge_duplicate_entities(self, entities: List[GenericEntity]) -> List[GenericEntity]:
        """Merge duplicate entities, keeping the highest confidence version"""
        
        entity_map = {}
        
        for entity in entities:
            # Create a key based on text and type
            key = (entity.text.lower().strip(), entity.entity_type)
            
            if key not in entity_map or entity.confidence > entity_map[key].confidence:
                entity_map[key] = entity
        
        merged_entities = list(entity_map.values())
        
        if len(merged_entities) < len(entities):
            logger.info(f"Merged entities: {len(entities)} → {len(merged_entities)} (removed {len(entities) - len(merged_entities)} duplicates)")
        
        return merged_entities


# Convenience functions for quick domain setup
def create_business_entity_extractor(confidence_threshold: float = 0.7) -> GenericEntityExtractor:
    """Create an entity extractor configured for business domain"""
    from pathlib import Path
    config_path = Path(__file__).parent / "domains" / "business.yaml"
    return GenericEntityExtractor(config_path, confidence_threshold)


def create_medical_entity_extractor(confidence_threshold: float = 0.85) -> GenericEntityExtractor:
    """Create an entity extractor configured for medical domain (higher confidence)"""
    from pathlib import Path
    config_path = Path(__file__).parent / "domains" / "medical.yaml"
    return GenericEntityExtractor(config_path, confidence_threshold)