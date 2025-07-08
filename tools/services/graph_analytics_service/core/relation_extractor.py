#!/usr/bin/env python3
"""
Relation Extractor for Graph Analytics - Refactored Version

Extracts relationships between entities from text using:
1. LLM-based relation extraction with structured output
2. Pattern-based extraction for fallback
3. Configurable relationship types and confidence thresholds
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from .base_extractor import BaseExtractor
from .entity_extractor import Entity, EntityType

logger = get_logger(__name__)

class RelationType(Enum):
    """Relationship types for classification"""
    IS_A = "IS_A"                    # Taxonomic relationship
    PART_OF = "PART_OF"              # Compositional relationship
    LOCATED_IN = "LOCATED_IN"        # Spatial relationship
    WORKS_FOR = "WORKS_FOR"          # Employment relationship
    OWNS = "OWNS"                    # Ownership relationship
    CREATED_BY = "CREATED_BY"        # Creation relationship
    HAPPENED_AT = "HAPPENED_AT"      # Temporal/spatial event relationship
    CAUSED_BY = "CAUSED_BY"          # Causal relationship
    SIMILAR_TO = "SIMILAR_TO"        # Similarity relationship
    RELATES_TO = "RELATES_TO"        # General relationship
    DEPENDS_ON = "DEPENDS_ON"        # Dependency relationship
    CUSTOM = "CUSTOM"                # Domain-specific relationship

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

class RelationExtractor(BaseExtractor):
    """Extract relationships between entities from text"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize relation extractor"""
        super().__init__("RelationExtractor")
        self.config = config or {}
        
        # Relation patterns for quick extraction
        self.relation_patterns = {
            RelationType.IS_A: [
                r'(.+?)\s+is\s+a\s+(.+)',
                r'(.+?)\s+are\s+(.+)',
                r'(.+?),\s+a\s+(.+)',
            ],
            RelationType.WORKS_FOR: [
                r'(.+?)\s+works?\s+(?:for|at)\s+(.+)',
                r'(.+?)\s+(?:employee|staff|member)\s+(?:of|at)\s+(.+)',
                r'(.+?)\s+from\s+(.+?)\s+(?:company|organization)',
            ],
            RelationType.LOCATED_IN: [
                r'(.+?)\s+(?:in|at|located\s+in)\s+(.+)',
                r'(.+?)\s+of\s+(.+?)\s+(?:city|country|state)',
            ],
            RelationType.OWNS: [
                r'(.+?)\s+owns?\s+(.+)',
                r'(.+?)\'s\s+(.+)',
                r'(.+?)\s+belongs?\s+to\s+(.+)',
            ]
        }
        
        logger.info("RelationExtractor initialized")
    
    async def extract_relations(self, text: str, entities: List[Entity], methods: List[str] = None) -> List[Relation]:
        """Extract relationships between entities"""
        if methods is None:
            methods = ['llm']  # Default to LLM for better accuracy
            
        # For long text, prioritize LLM long context capabilities
        if self.should_use_llm_for_text(text):
            logger.info(f"🔗 Long text ({len(text):,} chars) relation extraction, using LLM long context processing")
            methods = ['llm']
        
        all_relations = []
        
        for method in methods:
            if method == 'llm':
                relations = await self._extract_with_llm(text, entities)
            elif method == 'pattern':
                relations = self._extract_with_patterns(text, entities)
            elif method == 'hybrid':
                llm_relations = await self._extract_with_llm(text, entities)
                pattern_relations = self._extract_with_patterns(text, entities)
                relations = self._merge_relations(llm_relations + pattern_relations)
            else:
                logger.warning(f"Unknown extraction method: {method}")
                continue
                
            all_relations.extend(relations)
        
        # Deduplicate and merge relations
        final_relations = self._merge_relations(all_relations)
        
        logger.info(f"Extracted {len(final_relations)} relations from {len(entities)} entities")
        return final_relations
    
    async def _extract_with_llm(self, text: str, entities: List[Entity]) -> List[Relation]:
        """Extract relationships using LLM with structured output"""
        if len(entities) < 2:
            return []
        
        # Create entity context for LLM
        entity_context = []
        for i, entity in enumerate(entities):
            entity_context.append(f"{i}: {entity.text} ({entity.entity_type.value})")
        
        prompt = f"""Extract relationships between the given entities from the text. Analyze the text to identify semantic relationships, dependencies, and connections.

**Text to analyze:**
{text}

**Entities (reference by index):**
{chr(10).join(entity_context)}

**Relationship Types:**
- IS_A: Taxonomic/classification relationships
- PART_OF: Component/compositional relationships  
- LOCATED_IN: Spatial/location relationships
- WORKS_FOR: Employment/affiliation relationships
- OWNS: Ownership relationships
- CREATED_BY: Creation/authorship relationships
- HAPPENED_AT: Temporal/event relationships
- CAUSED_BY: Causal relationships
- SIMILAR_TO: Similarity relationships
- RELATES_TO: General semantic relationships
- DEPENDS_ON: Dependency relationships
- CUSTOM: Domain-specific relationships

**Required JSON format:**
{{
  "relations": [
    {{
      "subject_idx": 0,
      "predicate": "clear relationship description",
      "object_idx": 1,
      "relation_type": "IS_A|PART_OF|LOCATED_IN|WORKS_FOR|OWNS|CREATED_BY|HAPPENED_AT|CAUSED_BY|SIMILAR_TO|RELATES_TO|DEPENDS_ON|CUSTOM",
      "confidence": 0.9,
      "context": "relevant text snippet supporting this relationship",
      "properties": {{}},
      "temporal_info": {{}}
    }}
  ]
}}

Return only valid JSON with the relations array."""
        
        # Use base class method for LLM extraction
        items_data = await self.extract_with_llm(
            text=text,
            prompt=prompt,
            expected_wrapper="relations",
            operation_name="relation_extraction"
        )
        
        # Convert to Relation objects
        relations = []
        for item_data in items_data:
            relation = self._create_relation_from_data(item_data, entities)
            if relation:
                relations.append(relation)
        
        return relations
    
    def _create_relation_from_data(self, item_data: Dict[str, Any], entities: List[Entity]) -> Optional[Relation]:
        """Create Relation object from LLM response data"""
        try:
            subject_idx = self._get_safe_field(item_data, 'subject_idx', 0)
            object_idx = self._get_safe_field(item_data, 'object_idx', 1)
            
            # Validate indices
            if (subject_idx >= len(entities) or object_idx >= len(entities) or subject_idx == object_idx):
                logger.warning(f"Invalid entity indices: subject={subject_idx}, object={object_idx}, total={len(entities)}")
                return None
            
            # Map relation type
            rel_type_str = self._get_safe_field(item_data, 'relation_type', 'RELATES_TO')
            relation_type = self._map_relation_type(str(rel_type_str).upper())
            
            return Relation(
                subject=entities[subject_idx],
                predicate=self._clean_text_field(item_data.get('predicate', '')),
                object=entities[object_idx],
                relation_type=relation_type,
                confidence=self._standardize_confidence(item_data.get('confidence')),
                context=self._clean_text_field(item_data.get('context', '')),
                properties=self._get_safe_field(item_data, 'properties', {}),
                temporal_info=self._get_safe_field(item_data, 'temporal_info', {})
            )
        except Exception as e:
            logger.warning(f"Failed to create relation from data: {e}")
            return None
    
    def _map_relation_type(self, type_str: str) -> RelationType:
        """Map LLM relation type string to RelationType enum"""
        type_mapping = {
            'IS_A': RelationType.IS_A,
            'PART_OF': RelationType.PART_OF,
            'LOCATED_IN': RelationType.LOCATED_IN,
            'WORKS_FOR': RelationType.WORKS_FOR,
            'OWNS': RelationType.OWNS,
            'CREATED_BY': RelationType.CREATED_BY,
            'HAPPENED_AT': RelationType.HAPPENED_AT,
            'CAUSED_BY': RelationType.CAUSED_BY,
            'SIMILAR_TO': RelationType.SIMILAR_TO,
            'RELATES_TO': RelationType.RELATES_TO,
            'DEPENDS_ON': RelationType.DEPENDS_ON,
            'CUSTOM': RelationType.CUSTOM,
            'RELATION': RelationType.RELATES_TO,
            'CONNECTS_TO': RelationType.RELATES_TO,
            'ASSOCIATED_WITH': RelationType.RELATES_TO
        }
        return type_mapping.get(type_str, RelationType.RELATES_TO)
    
    def _extract_with_patterns(self, text: str, entities: List[Entity]) -> List[Relation]:
        """Extract relationships using regex patterns"""
        relations = []
        
        # Create entity lookup by text
        entity_by_text = {entity.text.lower(): entity for entity in entities}
        
        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        subject_text = match.group(1).strip().lower()
                        object_text = match.group(2).strip().lower()
                        
                        # Find matching entities
                        subject_entity = None
                        object_entity = None
                        
                        for entity_text, entity in entity_by_text.items():
                            if entity_text in subject_text or subject_text in entity_text:
                                subject_entity = entity
                            if entity_text in object_text or object_text in entity_text:
                                object_entity = entity
                        
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
        
        return relations
    
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
    
    def _merge_relations(self, relations: List[Relation]) -> List[Relation]:
        """Merge duplicate or similar relations"""
        if not relations:
            return []
        
        merged = []
        
        for relation in relations:
            # Check if similar relation already exists
            similar_found = False
            for existing in merged:
                if (existing.subject.text == relation.subject.text and
                    existing.object.text == relation.object.text and
                    existing.relation_type == relation.relation_type):
                    
                    # Merge - keep higher confidence version
                    if relation.confidence > existing.confidence:
                        merged.remove(existing)
                        merged.append(relation)
                    similar_found = True
                    break
            
            if not similar_found:
                merged.append(relation)
        
        return merged
    
    # Base class implementations
    def _validate_item_data(self, item_data: Dict[str, Any]) -> bool:
        """Validate relation data from LLM response"""
        return (isinstance(item_data, dict) and 
                'subject_idx' in item_data and 
                'object_idx' in item_data)
    
    def _process_item_data(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process relation data - just return as-is since _create_relation_from_data handles conversion"""
        return item_data
    
    def _fallback_extraction(self, text: str) -> List[Dict[str, Any]]:
        """Fallback to pattern-based extraction"""
        logger.info("Falling back to pattern-based relation extraction")
        # Pattern extraction needs entities, so return empty for now
        return []
    
    def get_relation_statistics(self, relations: List[Relation]) -> Dict[str, Any]:
        """Get statistics about extracted relations"""
        if not relations:
            return {"total": 0}
        
        type_counts = {}
        confidence_sum = 0
        subject_types = {}
        object_types = {}
        
        for relation in relations:
            rel_type = relation.relation_type.value
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
            confidence_sum += relation.confidence
            
            subj_type = relation.subject.entity_type.value
            obj_type = relation.object.entity_type.value
            subject_types[subj_type] = subject_types.get(subj_type, 0) + 1
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
        
        return {
            "total": len(relations),
            "by_type": type_counts,
            "average_confidence": confidence_sum / len(relations),
            "high_confidence": len([r for r in relations if r.confidence > 0.8]),
            "subject_entity_types": subject_types,
            "object_entity_types": object_types,
            "unique_subjects": len(set(r.subject.text for r in relations)),
            "unique_objects": len(set(r.object.text for r in relations))
        }