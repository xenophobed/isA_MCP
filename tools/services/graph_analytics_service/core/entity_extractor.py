#!/usr/bin/env python3
"""
Entity Extractor for Graph Analytics - Refactored Version

Extracts named entities from text using:
1. LLM-based extraction with structured output
2. Pattern-based extraction for fallback
3. Configurable entity types and confidence thresholds
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from .base_extractor import BaseExtractor

logger = get_logger(__name__)

class EntityType(Enum):
    """Entity types for classification"""
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "LOC"
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

class EntityExtractor(BaseExtractor):
    """Extract entities from text using LLM and pattern-based methods"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize entity extractor"""
        super().__init__("EntityExtractor")
        self.config = config or {}
        
        # Entity patterns for quick extraction
        self.patterns = {
            EntityType.DATE: [
                r'\b\d{4}-\d{2}-\d{2}\b',
                r'\b\d{1,2}/\d{1,2}/\d{4}\b',
                r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
            ],
            EntityType.MONEY: [
                r'\$[\d,]+\.?\d*',
                r'\b\d+\s*(dollars?|cents?|yuan|euros?)\b'
            ],
            EntityType.PERSON: [
                r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',
                r'\b(Dr|Mr|Ms|Mrs|Prof|Professor)\s+[A-Z][a-z]+\b'
            ],
            EntityType.ORGANIZATION: [
                r'\b[A-Z][a-z]+\s+(University|College|Institute|Corporation|Inc|LLC|Company|Group)\b',
                r'\b(Microsoft|Google|Apple|Amazon|Facebook|IBM|Intel)\b'
            ],
            EntityType.CONCEPT: [
                r'\b(machine learning|neural network|artificial intelligence|deep learning|algorithm|model|training|optimization)\b',
                r'\b[a-z]+ing\b',
            ]
        }
        
        logger.info("EntityExtractor initialized")
    
    async def extract_entities(self, text: str, methods: List[str] = None) -> List[Entity]:
        """Extract entities using specified methods"""
        if methods is None:
            methods = ['llm']  # Default to LLM for better accuracy
            
        # For long text, prioritize LLM long context capabilities
        if self.should_use_llm_for_text(text):
            methods = ['llm']
            
        all_entities = []
        
        for method in methods:
            if method == 'llm':
                entities = await self._extract_with_llm(text)
            elif method == 'pattern':
                entities = self._extract_with_patterns(text)
            elif method == 'hybrid':
                llm_entities = await self._extract_with_llm(text)
                pattern_entities = self._extract_with_patterns(text)
                entities = self._merge_entities(llm_entities + pattern_entities)
            else:
                logger.warning(f"Unknown extraction method: {method}")
                continue
                
            all_entities.extend(entities)
        
        # Deduplicate and merge entities
        final_entities = self._merge_entities(all_entities)
        
        logger.info(f"Extracted {len(final_entities)} entities from text ({len(text):,} chars)")
        return final_entities
    
    async def _extract_with_llm(self, text: str) -> List[Entity]:
        """Extract entities using LLM with structured output"""
        prompt = f"""Extract named entities from the provided text. Identify and classify entities into the following types:

**Entity Types:**
- PERSON: People, authors, researchers, individuals
- ORG: Organizations, companies, institutions, universities
- LOC: Locations, places, countries, cities
- EVENT: Events, conferences, meetings, occurrences
- PRODUCT: Products, tools, software, technologies
- CONCEPT: Concepts, methods, algorithms, theories
- DATE: Dates, times, temporal expressions
- MONEY: Money, financial amounts, currencies
- CUSTOM: Other domain-specific entities

**Text to analyze:**
{text}

**Required JSON format:**
{{
  "entities": [
    {{
      "text": "entity text as it appears",
      "type": "PERSON|ORG|LOC|EVENT|PRODUCT|CONCEPT|DATE|MONEY|CUSTOM",
      "start": 0,
      "end": 10,
      "confidence": 0.95,
      "properties": {{}},
      "canonical_form": "standardized form",
      "aliases": []
    }}
  ]
}}

Return only valid JSON with the entities array."""
        
        # Use base class method for LLM extraction
        items_data = await self.extract_with_llm(
            text=text,
            prompt=prompt,
            expected_wrapper="entities",
            operation_name="entity_extraction"
        )
        
        # Convert to Entity objects
        entities = []
        for item_data in items_data:
            entity = self._create_entity_from_data(item_data)
            if entity:
                entities.append(entity)
        
        return entities
    
    def _create_entity_from_data(self, item_data: Dict[str, Any]) -> Optional[Entity]:
        """Create Entity object from LLM response data"""
        try:
            text = self._clean_text_field(item_data.get('text'))
            if not text:
                return None
            
            type_str = self._get_safe_field(item_data, 'type', 'CUSTOM')
            entity_type = self._map_entity_type(str(type_str).upper())
            
            return Entity(
                text=text,
                entity_type=entity_type,
                start=self._get_safe_field(item_data, 'start', 0),
                end=self._get_safe_field(item_data, 'end', len(text)),
                confidence=self._standardize_confidence(item_data.get('confidence')),
                properties=self._get_safe_field(item_data, 'properties', {}),
                canonical_form=self._get_safe_field(item_data, 'canonical_form', text),
                aliases=self._get_safe_field(item_data, 'aliases', [])
            )
        except Exception as e:
            logger.warning(f"Failed to create entity from data: {e}")
            return None
    
    def _map_entity_type(self, type_str: str) -> EntityType:
        """Map LLM entity type string to EntityType enum"""
        type_mapping = {
            'PERSON': EntityType.PERSON,
            'PEOPLE': EntityType.PERSON,
            'ORG': EntityType.ORGANIZATION,
            'ORGANIZATION': EntityType.ORGANIZATION,
            'COMPANY': EntityType.ORGANIZATION,
            'LOC': EntityType.LOCATION,
            'LOCATION': EntityType.LOCATION,
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
        return type_mapping.get(type_str, EntityType.CUSTOM)
    
    def _extract_with_patterns(self, text: str) -> List[Entity]:
        """Extract entities using regex patterns"""
        entities = []
        
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity = Entity(
                        text=match.group(),
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9  # High confidence for pattern matches
                    )
                    entities.append(entity)
        
        return entities
    
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
    
    # Base class implementations
    def _validate_item_data(self, item_data: Dict[str, Any]) -> bool:
        """Validate entity data from LLM response"""
        return isinstance(item_data, dict) and 'text' in item_data
    
    def _process_item_data(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process entity data - just return as-is since _create_entity_from_data handles conversion"""
        return item_data
    
    def _fallback_extraction(self, text: str) -> List[Dict[str, Any]]:
        """Fallback to pattern-based extraction"""
        logger.info("Falling back to pattern-based entity extraction")
        entities = self._extract_with_patterns(text)
        # Convert Entity objects to dicts for consistency
        return [{
            'text': entity.text,
            'type': entity.entity_type.value,
            'start': entity.start,
            'end': entity.end,
            'confidence': entity.confidence,
            'properties': entity.properties,
            'canonical_form': entity.canonical_form,
            'aliases': entity.aliases
        } for entity in entities]
    
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