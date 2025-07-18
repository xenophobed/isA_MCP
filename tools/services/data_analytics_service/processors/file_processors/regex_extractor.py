#!/usr/bin/env python3
"""
Regex-based Relation Extractor
Provides pattern-based relationship extraction as fallback method
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger

logger = get_logger(__name__)

class RelationType(Enum):
    """Relationship types for classification"""
    IS_A = "IS_A"
    PART_OF = "PART_OF"
    LOCATED_IN = "LOCATED_IN"
    WORKS_FOR = "WORKS_FOR"
    OWNS = "OWNS"
    CREATED_BY = "CREATED_BY"
    HAPPENED_AT = "HAPPENED_AT"
    CAUSED_BY = "CAUSED_BY"
    SIMILAR_TO = "SIMILAR_TO"
    RELATES_TO = "RELATES_TO"
    DEPENDS_ON = "DEPENDS_ON"
    CUSTOM = "CUSTOM"

@dataclass
class Entity:
    """Entity data structure"""
    text: str
    entity_type: str
    start_pos: int = 0
    end_pos: int = 0
    confidence: float = 1.0

@dataclass
class Relation:
    """Relationship data structure"""
    subject: Entity
    predicate: str
    object: Entity
    relation_type: RelationType
    confidence: float
    context: str = ""
    properties: Dict[str, Any] = None
    temporal_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.temporal_info is None:
            self.temporal_info = {}

class RegexExtractor:
    """Extract relationships using regex patterns"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize regex extractor"""
        self.config = config or {}
        
        # Relation patterns for quick extraction
        self.relation_patterns = {
            RelationType.IS_A: [
                r'(.+?)\s+is\s+a\s+(.+)',
                r'(.+?)\s+are\s+(.+)',
                r'(.+?),\s+a\s+(.+)',
                r'(.+?)\s+:\s+a\s+(.+)',
            ],
            RelationType.WORKS_FOR: [
                r'(.+?)\s+works?\s+(?:for|at)\s+(.+)',
                r'(.+?)\s+(?:employee|staff|member)\s+(?:of|at)\s+(.+)',
                r'(.+?)\s+from\s+(.+?)(?:\s+(?:company|organization|corp))?',
                r'(.+?),\s+(?:CEO|CTO|manager|director)\s+(?:of|at)\s+(.+)',
            ],
            RelationType.LOCATED_IN: [
                r'(.+?)\s+(?:in|at|located\s+in)\s+(.+)',
                r'(.+?)\s+of\s+(.+?)(?:\s+(?:city|country|state))?',
                r'(.+?)\s+headquarters\s+(?:in|at)\s+(.+)',
                r'(.+?),\s+(.+?)(?:\s+(?:based|located))?',
            ],
            RelationType.OWNS: [
                r'(.+?)\s+owns?\s+(.+)',
                r'(.+?)\'s\s+(.+)',
                r'(.+?)\s+belongs?\s+to\s+(.+)',
                r'(.+?)\s+(?:possesses|has)\s+(.+)',
            ],
            RelationType.PART_OF: [
                r'(.+?)\s+(?:is\s+)?part\s+of\s+(.+)',
                r'(.+?)\s+(?:within|inside)\s+(.+)',
                r'(.+?)\s+component\s+of\s+(.+)',
                r'(.+?)\s+division\s+of\s+(.+)',
            ],
            RelationType.CREATED_BY: [
                r'(.+?)\s+(?:created|made|built|developed)\s+by\s+(.+)',
                r'(.+?)\s+(?:author|creator|developer):\s+(.+)',
                r'(.+?)\s+from\s+(.+?)(?:\s+(?:studios?|company))?',
            ],
            RelationType.CAUSED_BY: [
                r'(.+?)\s+(?:caused|triggered|resulted)\s+by\s+(.+)',
                r'(.+?)\s+due\s+to\s+(.+)',
                r'(.+?)\s+because\s+of\s+(.+)',
            ],
            RelationType.SIMILAR_TO: [
                r'(.+?)\s+(?:similar|like|resembles)\s+(.+)',
                r'(.+?)\s+compared\s+to\s+(.+)',
                r'(.+?)\s+as\s+(.+)',
            ]
        }
        
        logger.info("RegexExtractor initialized with pattern-based relation extraction")
    
    def extract_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """Extract relationships using regex patterns"""
        if len(entities) < 2:
            return []
        
        relations = []
        
        # Create entity lookup by text (case-insensitive)
        entity_by_text = {entity.text.lower(): entity for entity in entities}
        
        # Extract using patterns
        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        subject_text = match.group(1).strip()
                        object_text = match.group(2).strip()
                        
                        # Find matching entities
                        subject_entity = self._find_matching_entity(subject_text, entity_by_text)
                        object_entity = self._find_matching_entity(object_text, entity_by_text)
                        
                        if subject_entity and object_entity and subject_entity != object_entity:
                            relation = Relation(
                                subject=subject_entity,
                                predicate=self._get_predicate_for_type(relation_type),
                                object=object_entity,
                                relation_type=relation_type,
                                confidence=0.8,  # Good confidence for pattern matches
                                context=match.group()
                            )
                            relations.append(relation)
                            
                    except (IndexError, AttributeError) as e:
                        logger.debug(f"Pattern match error: {e}")
                        continue
        
        # Remove duplicates
        unique_relations = self._deduplicate_relations(relations)
        
        logger.info(f"Extracted {len(unique_relations)} relations using regex patterns")
        return unique_relations
    
    def _find_matching_entity(self, text: str, entity_lookup: Dict[str, Entity]) -> Optional[Entity]:
        """Find entity that matches the given text"""
        text_lower = text.lower()
        
        # Exact match first
        if text_lower in entity_lookup:
            return entity_lookup[text_lower]
        
        # Partial matching
        for entity_text, entity in entity_lookup.items():
            # Check if entity text is contained in the match or vice versa
            if (entity_text in text_lower or text_lower in entity_text) and len(text_lower) > 2:
                return entity
                
        return None
    
    def _get_predicate_for_type(self, relation_type: RelationType) -> str:
        """Get default predicate for relation type"""
        predicate_map = {
            RelationType.IS_A: "is a",
            RelationType.PART_OF: "is part of",
            RelationType.LOCATED_IN: "is located in",
            RelationType.WORKS_FOR: "works for",
            RelationType.OWNS: "owns",
            RelationType.CREATED_BY: "was created by",
            RelationType.HAPPENED_AT: "happened at",
            RelationType.CAUSED_BY: "was caused by",
            RelationType.SIMILAR_TO: "is similar to",
            RelationType.RELATES_TO: "relates to",
            RelationType.DEPENDS_ON: "depends on",
            RelationType.CUSTOM: "relates to"
        }
        return predicate_map.get(relation_type, "relates to")
    
    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        """Remove duplicate relations"""
        if not relations:
            return []
        
        unique_relations = []
        seen_relations = set()
        
        for relation in relations:
            # Create a unique key for the relation
            key = (
                relation.subject.text.lower(),
                relation.object.text.lower(),
                relation.relation_type.value
            )
            
            if key not in seen_relations:
                seen_relations.add(key)
                unique_relations.append(relation)
            else:
                # If duplicate, keep the one with higher confidence
                for i, existing in enumerate(unique_relations):
                    existing_key = (
                        existing.subject.text.lower(),
                        existing.object.text.lower(),
                        existing.relation_type.value
                    )
                    if existing_key == key and relation.confidence > existing.confidence:
                        unique_relations[i] = relation
                        break
        
        return unique_relations
    
    def get_supported_patterns(self) -> Dict[str, List[str]]:
        """Get all supported relation patterns"""
        return {rel_type.value: patterns for rel_type, patterns in self.relation_patterns.items()}
    
    def add_custom_pattern(self, relation_type: RelationType, pattern: str) -> None:
        """Add a custom pattern for a relation type"""
        if relation_type not in self.relation_patterns:
            self.relation_patterns[relation_type] = []
        
        self.relation_patterns[relation_type].append(pattern)
        logger.info(f"Added custom pattern for {relation_type.value}: {pattern}")
    
    def validate_pattern(self, pattern: str, test_text: str) -> bool:
        """Validate a regex pattern against test text"""
        try:
            matches = re.findall(pattern, test_text, re.IGNORECASE)
            return len(matches) > 0
        except re.error as e:
            logger.error(f"Invalid regex pattern: {pattern}, error: {e}")
            return False