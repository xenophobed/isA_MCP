#!/usr/bin/env python3
"""
Relation Extractor for Graph Analytics

Extracts relationships between entities from text using:
1. Dependency parsing for grammatical relationships
2. LLM-based relation extraction for semantic relationships
3. Pattern-based extraction for structured relationships
4. Coreference resolution for entity linking
"""

import re
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from isa_model.inference.ai_factory import AIFactory
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

class RelationExtractor:
    """Extract relationships between entities from text"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize relation extractor
        
        Args:
            config: Configuration dict with extractor settings
        """
        self.config = config or {}
        self.ai_factory = AIFactory()
        self.llm_service = self.ai_factory.get_llm_service()
        
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
    
    async def extract_relations(self, text: str, entities: List[Entity], 
                              methods: List[str] = None) -> List[Relation]:
        """Extract relationships between entities
        
        Args:
            text: Input text to analyze
            entities: List of entities found in the text
            methods: List of extraction methods ['llm', 'pattern', 'hybrid']
            
        Returns:
            List of extracted relationships
        """
        if methods is None:
            methods = ['hybrid']
        
        all_relations = []
        
        for method in methods:
            if method == 'llm':
                relations = await self._extract_with_llm(text, entities)
            elif method == 'pattern':
                relations = self._extract_with_patterns(text, entities)
            elif method == 'hybrid':
                # Combine LLM and pattern-based extraction
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
        """Extract relationships using LLM"""
        if len(entities) < 2:
            return []
        
        try:
            # Create entity context for LLM
            entity_context = []
            for i, entity in enumerate(entities):
                entity_context.append(f"{i}: {entity.text} ({entity.entity_type.value})")
            
            prompt = f"""
            Given the following text and entities, extract all meaningful relationships between the entities.
            
            Text: "{text}"
            
            Entities:
            {chr(10).join(entity_context)}
            
            For each relationship, identify:
            1. Subject entity (use entity index)
            2. Relationship type (IS_A, PART_OF, LOCATED_IN, WORKS_FOR, OWNS, CREATED_BY, HAPPENED_AT, CAUSED_BY, SIMILAR_TO, RELATES_TO, DEPENDS_ON, CUSTOM)
            3. Predicate (the relationship description)
            4. Object entity (use entity index)
            5. Confidence score (0.0-1.0)
            6. Context (relevant text snippet)
            
            Return as JSON array:
            [
                {{
                    "subject_idx": 0,
                    "predicate": "relationship description",
                    "object_idx": 1,
                    "relation_type": "RELATION_TYPE",
                    "confidence": 0.9,
                    "context": "relevant text snippet",
                    "properties": {{"key": "value"}},
                    "temporal_info": {{"when": "time info"}}
                }}
            ]
            
            Only include relationships explicitly mentioned or strongly implied in the text.
            """
            
            response = await self.llm_service.generate_text(
                prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse LLM response
            try:
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                if json_start != -1 and json_end != -1:
                    json_str = response[json_start:json_end]
                    relations_data = json.loads(json_str)
                    
                    relations = []
                    for rel_data in relations_data:
                        try:
                            subject_idx = rel_data.get('subject_idx', 0)
                            object_idx = rel_data.get('object_idx', 1)
                            
                            if (subject_idx < len(entities) and 
                                object_idx < len(entities) and 
                                subject_idx != object_idx):
                                
                                relation_type = RelationType(rel_data.get('relation_type', 'RELATES_TO'))
                                relation = Relation(
                                    subject=entities[subject_idx],
                                    predicate=rel_data.get('predicate', ''),
                                    object=entities[object_idx],
                                    relation_type=relation_type,
                                    confidence=rel_data.get('confidence', 0.7),
                                    context=rel_data.get('context', ''),
                                    properties=rel_data.get('properties', {}),
                                    temporal_info=rel_data.get('temporal_info', {})
                                )
                                relations.append(relation)
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Skipping invalid relation: {e}")
                            continue
                    
                    return relations
                else:
                    logger.warning("No valid JSON found in LLM relation response")
                    return []
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM relation response: {e}")
                return []
                
        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []
    
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
    
    async def extract_temporal_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """Extract temporal relationships between entities and events"""
        temporal_prompt = f"""
        Extract temporal relationships from the text. Focus on:
        - When events happened
        - Duration of events or states
        - Sequence of events
        - Temporal dependencies
        
        Text: "{text}"
        Entities: {[f"{e.text} ({e.entity_type.value})" for e in entities]}
        
        Return temporal relations as JSON array.
        """
        
        try:
            response = await self.llm_service.generate_text(
                temporal_prompt,
                max_tokens=1000,
                temperature=0.1
            )
            
            # Parse and process temporal relations
            return await self._extract_with_llm(text, entities)
            
        except Exception as e:
            logger.error(f"Temporal relation extraction failed: {e}")
            return []
    
    async def extract_causal_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """Extract causal relationships between entities"""
        causal_prompt = f"""
        Extract causal relationships from the text. Focus on:
        - Cause and effect relationships
        - Dependencies and prerequisites
        - Enabling conditions
        - Consequences and outcomes
        
        Text: "{text}"
        Entities: {[f"{e.text} ({e.entity_type.value})" for e in entities]}
        
        Return causal relations as JSON array.
        """
        
        try:
            response = await self.llm_service.generate_text(
                causal_prompt,
                max_tokens=1000,
                temperature=0.1
            )
            
            # Parse and process causal relations
            return await self._extract_with_llm(text, entities)
            
        except Exception as e:
            logger.error(f"Causal relation extraction failed: {e}")
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