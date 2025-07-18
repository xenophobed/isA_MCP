#!/usr/bin/env python3
"""
Entity Extractor for Graph Analytics - Simplified Version

Extracts named entities from text using intelligence service text extractor.
Keeps the same function interface for backward compatibility.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from tools.services.intelligence_service.language.text_extractor import text_extractor

logger = get_logger(__name__)

class EntityType(Enum):
    """Entity types for classification"""
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    PRODUCT = "PRODUCT"
    CONCEPT = "CONCEPT"
    DATE = "DATE"
    MONEY = "MONEY"
    CUSTOM = "CUSTOM"

@dataclass
class Entity:
    """Entity data structure"""
    text: str
    entity_type: EntityType
    start: int
    end: int
    confidence: float
    properties: Dict[str, Any] = None
    canonical_form: str = None
    aliases: List[str] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.aliases is None:
            self.aliases = []
        if self.canonical_form is None:
            self.canonical_form = self.text

class EntityExtractor:
    """Extract entities from text using intelligence service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize entity extractor"""
        self.config = config or {}
        
        # Configuration settings
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
        self.use_llm = self.config.get('use_llm', True)
        
        logger.info("EntityExtractor initialized with intelligence service")
    
    async def extract_entities(self, text: str, methods: List[str] = None) -> List[Entity]:
        """Extract entities using intelligence service"""
        if not self.use_llm:
            logger.warning("LLM disabled, returning empty entity list")
            return []
        
        try:
            # Use intelligence service for entity extraction
            result = await text_extractor.extract_entities(
                text=text,
                confidence_threshold=self.confidence_threshold
            )
            
            if not result.get('success'):
                logger.warning(f"Entity extraction failed: {result.get('error')}")
                return []
            
            # Extract entities from result
            entities_data = result.get('data', {}).get('entities', {})
            
            # Convert to Entity objects
            entities = []
            for entity_type_name, entity_list in entities_data.items():
                # Map entity type names
                entity_type = self._map_entity_type(entity_type_name)
                
                for entity_data in entity_list:
                    try:
                        # Handle position data
                        position = entity_data.get('position', [0, 0])
                        start_pos = position[0] if len(position) > 0 else 0
                        end_pos = position[1] if len(position) > 1 else start_pos + len(entity_data.get('name', ''))
                        
                        entity = Entity(
                            text=entity_data.get('name', ''),
                            entity_type=entity_type,
                            start=start_pos,
                            end=end_pos,
                            confidence=entity_data.get('confidence', 0.7),
                            properties={},
                            canonical_form=entity_data.get('name', ''),
                            aliases=[]
                        )
                        if entity.text.strip():
                            entities.append(entity)
                    except Exception as e:
                        logger.warning(f"Failed to create entity from data: {e}")
                        continue
            
            logger.info(f"Extracted {len(entities)} entities from text ({len(text):,} chars)")
            return entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    def _map_entity_type(self, type_str: str) -> EntityType:
        """Map intelligence service entity type string to EntityType enum"""
        type_mapping = {
            'PERSON': EntityType.PERSON,
            'PEOPLE': EntityType.PERSON,
            'ORGANIZATION': EntityType.ORGANIZATION,
            'ORG': EntityType.ORGANIZATION,
            'COMPANY': EntityType.ORGANIZATION,
            'LOCATION': EntityType.LOCATION,
            'LOC': EntityType.LOCATION,
            'PLACE': EntityType.LOCATION,
            'EVENT': EntityType.EVENT,
            'PRODUCT': EntityType.PRODUCT,
            'CONCEPT': EntityType.CONCEPT,
            'DATE': EntityType.DATE,
            'TIME': EntityType.DATE,
            'MONEY': EntityType.MONEY,
            'CURRENCY': EntityType.MONEY,
            'CUSTOM': EntityType.CUSTOM,
            'ENTITY': EntityType.CUSTOM,
            'MISC': EntityType.CUSTOM,
            'OTHER': EntityType.CUSTOM
        }
        return type_mapping.get(type_str.upper(), EntityType.CUSTOM)
    
    def _merge_entities(self, entities: List[Entity]) -> List[Entity]:
        """Merge overlapping or duplicate entities"""
        if not entities:
            return []
        
        # Sort by start position
        sorted_entities = sorted(entities, key=lambda x: x.start)
        merged = []
        
        for entity in sorted_entities:
            if not merged:
                merged.append(entity)
                continue
            
            last_entity = merged[-1]
            
            # Check for overlap
            if (entity.start <= last_entity.end and 
                entity.end >= last_entity.start):
                
                # Merge entities - keep the one with higher confidence
                if entity.confidence > last_entity.confidence:
                    merged[-1] = entity
                # If same confidence, prefer longer entity
                elif (entity.confidence == last_entity.confidence and 
                      len(entity.text) > len(last_entity.text)):
                    merged[-1] = entity
            else:
                merged.append(entity)
        
        return merged
    
    async def extract_entity_attributes_batch(self, text: str, 
                                            entities: List[Entity]) -> Dict[str, Dict[str, Any]]:
        """Extract attributes for multiple entities efficiently"""
        entity_attributes = {}
        
        for entity in entities:
            try:
                # For now, just return basic entity info
                # This can be extended to use attribute extractor
                entity_attributes[entity.text] = {
                    'type': entity.entity_type.value,
                    'confidence': entity.confidence,
                    'position': [entity.start, entity.end],
                    'canonical_form': entity.canonical_form,
                    'aliases': entity.aliases
                }
            except Exception as e:
                logger.error(f"Failed to extract attributes for {entity.text}: {e}")
                entity_attributes[entity.text] = {}
        
        return entity_attributes
    
    def should_use_llm_for_text(self, text: str) -> bool:
        """Determine if LLM should be used for the given text"""
        return len(text) > 100 and self.use_llm
    
    def get_entity_statistics(self, entities: List[Entity]) -> Dict[str, Any]:
        """Get statistics about extracted entities"""
        if not entities:
            return {"total": 0}
        
        type_counts = {}
        confidence_sum = 0
        
        for entity in entities:
            entity_type = entity.entity_type.value
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
            confidence_sum += entity.confidence
        
        return {
            "total": len(entities),
            "by_type": type_counts,
            "average_confidence": confidence_sum / len(entities),
            "high_confidence": len([e for e in entities if e.confidence > 0.8]),
            "unique_entities": len(set(e.canonical_form for e in entities))
        }