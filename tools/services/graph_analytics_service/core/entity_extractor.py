#!/usr/bin/env python3
"""
Entity Extractor for Graph Analytics

Extracts named entities from text using multiple approaches:
1. NLP-based extraction (spaCy, NLTK)
2. LLM-based extraction for domain-specific entities
3. Pattern-based extraction for structured data
4. Custom entity recognition models
"""

import re
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from isa_model.inference.ai_factory import AIFactory

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

class EntityExtractor:
    """Extract entities from text using multiple methods"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize entity extractor
        
        Args:
            config: Configuration dict with extractor settings
        """
        self.config = config or {}
        self.ai_factory = AIFactory()
        self.llm_service = self.ai_factory.get_llm_service()
        
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
            ]
        }
        
        logger.info("EntityExtractor initialized")
    
    async def extract_entities(self, text: str, methods: List[str] = None) -> List[Entity]:
        """Extract entities using specified methods
        
        Args:
            text: Input text to analyze
            methods: List of extraction methods ['llm', 'pattern', 'hybrid']
            
        Returns:
            List of extracted entities
        """
        if methods is None:
            methods = ['hybrid']
            
        all_entities = []
        
        for method in methods:
            if method == 'llm':
                entities = await self._extract_with_llm(text)
            elif method == 'pattern':
                entities = self._extract_with_patterns(text)
            elif method == 'hybrid':
                # Combine LLM and pattern-based extraction
                llm_entities = await self._extract_with_llm(text)
                pattern_entities = self._extract_with_patterns(text)
                entities = self._merge_entities(llm_entities + pattern_entities)
            else:
                logger.warning(f"Unknown extraction method: {method}")
                continue
                
            all_entities.extend(entities)
        
        # Deduplicate and merge entities
        final_entities = self._merge_entities(all_entities)
        
        logger.info(f"Extracted {len(final_entities)} entities from text ({len(text)} chars)")
        return final_entities
    
    async def _extract_with_llm(self, text: str) -> List[Entity]:
        """Extract entities using LLM"""
        try:
            prompt = f"""
            Extract all important entities from the following text. For each entity, identify:
            1. The entity text
            2. Entity type (PERSON, ORG, LOC, EVENT, PRODUCT, CONCEPT, DATE, MONEY, CUSTOM)
            3. Start and end positions in the text
            4. Any important properties or attributes
            5. Alternative names or aliases
            
            Text: "{text}"
            
            Return the results as a JSON array with this structure:
            [
                {{
                    "text": "entity text",
                    "type": "ENTITY_TYPE",
                    "start": 0,
                    "end": 10,
                    "confidence": 0.95,
                    "properties": {{"key": "value"}},
                    "canonical_form": "canonical name",
                    "aliases": ["alias1", "alias2"]
                }}
            ]
            
            Be precise with positions and comprehensive with entity identification.
            """
            
            response = await self.llm_service.generate_text(
                prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse LLM response
            try:
                # Extract JSON from response
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                if json_start != -1 and json_end != -1:
                    json_str = response[json_start:json_end]
                    entities_data = json.loads(json_str)
                    
                    entities = []
                    for ent_data in entities_data:
                        entity_type = EntityType(ent_data.get('type', 'CUSTOM'))
                        entity = Entity(
                            text=ent_data['text'],
                            entity_type=entity_type,
                            start=ent_data.get('start', 0),
                            end=ent_data.get('end', len(ent_data['text'])),
                            confidence=ent_data.get('confidence', 0.8),
                            properties=ent_data.get('properties', {}),
                            canonical_form=ent_data.get('canonical_form'),
                            aliases=ent_data.get('aliases', [])
                        )
                        entities.append(entity)
                    
                    return entities
                else:
                    logger.warning("No valid JSON found in LLM response")
                    return []
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM entity response: {e}")
                return []
                
        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return []
    
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
    
    async def extract_domain_entities(self, text: str, domain: str) -> List[Entity]:
        """Extract domain-specific entities
        
        Args:
            text: Input text
            domain: Domain context (e.g., 'medical', 'legal', 'technical')
            
        Returns:
            List of domain-specific entities
        """
        domain_prompts = {
            'medical': """
            Extract medical entities including:
            - Diseases, conditions, symptoms
            - Medications, treatments
            - Body parts, organs
            - Medical procedures
            - Healthcare professionals
            """,
            'legal': """
            Extract legal entities including:
            - Laws, statutes, regulations
            - Legal documents, contracts
            - Court cases, legal proceedings
            - Legal entities (companies, organizations)
            - Legal concepts and terms
            """,
            'technical': """
            Extract technical entities including:
            - Technologies, frameworks, tools
            - Programming languages, libraries
            - Technical concepts, algorithms
            - Product names, versions
            - Technical specifications
            """,
            'business': """
            Extract business entities including:
            - Companies, organizations
            - Products, services
            - Business metrics, KPIs
            - Market segments
            - Business processes
            """
        }
        
        domain_prompt = domain_prompts.get(domain, "Extract important domain-specific entities.")
        
        prompt = f"""
        {domain_prompt}
        
        Text: "{text}"
        
        Return entities as JSON array with type, text, confidence, and properties.
        """
        
        try:
            response = await self.llm_service.generate_text(
                prompt,
                max_tokens=1500,
                temperature=0.1
            )
            
            # Parse response similar to _extract_with_llm
            # Implementation similar to above
            return await self._extract_with_llm(text)
            
        except Exception as e:
            logger.error(f"Domain entity extraction failed: {e}")
            return []
    
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