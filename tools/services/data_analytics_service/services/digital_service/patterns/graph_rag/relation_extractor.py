#!/usr/bin/env python3
"""
Generic Relation Extractor for Knowledge Analytics

Extracts relationships between entities from text using configurable domain schemas.
Uses intelligence service with domain-specific relation types from configuration.
"""

import json
import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path

from core.logging import get_logger
from tools.services.intelligence_service.language.text_extractor import extract_key_information
from .core.types import GenericEntity, GenericRelation
from .core.config import DomainConfig
from .core.dask_manager import dask_manager

logger = get_logger(__name__)

class GenericRelationExtractor:
    """Generic Relation Extractor using domain configuration"""
    
    def __init__(self, 
                 domain_config: Union[DomainConfig, str, Path],
                 confidence_threshold: float = 0.7):
        """
        Initialize Generic Relation Extractor
        
        Args:
            domain_config: Domain configuration or path to config file
            confidence_threshold: Minimum confidence threshold for relations
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
        
        # Get relation types from domain configuration
        self.relation_types = list(self.domain_config.relation_registry.get_types())
        
        # Build pattern mappings from domain configuration
        self.relation_patterns = {}
        for rel_type in self.relation_types:
            patterns = self.domain_config.relation_registry.get_patterns(rel_type)
            if patterns:
                self.relation_patterns[rel_type] = patterns
        
        logger.info(f"GenericRelationExtractor initialized for domain: {self.domain_config.domain_name}")
        logger.info(f"Available relation types: {self.relation_types}")
    
    async def extract_relations(self, 
                              text: str, 
                              entities: List[GenericEntity],
                              use_patterns: bool = True,
                              use_dask: bool = False) -> List[GenericRelation]:
        """
        Extract relationships between entities using domain configuration
        
        Args:
            text: Input text to analyze
            entities: List of entities to find relations between
            use_patterns: Whether to use pattern-based fallback
            use_dask: Whether to use Dask for parallel processing (for future batch processing)
            
        Returns:
            List of GenericRelation objects
        """
        if len(entities) < 2:
            return []
        
        try:
            # Build domain-specific context for relation extraction
            context = self._build_relation_context(entities)
            
            # Use LLM extraction with domain context
            relations = await self._extract_with_llm(text, entities, context)
            
            # If LLM failed and patterns are available, try pattern-based extraction
            if not relations and use_patterns and self.relation_patterns:
                logger.info("LLM extraction failed, falling back to pattern-based extraction")
                relations = self._extract_with_patterns(text, entities)
            
            # Filter by confidence threshold
            filtered_relations = [
                rel for rel in relations 
                if rel.confidence >= self.confidence_threshold
            ]
            
            logger.info(f"Extracted {len(filtered_relations)} relations from {len(entities)} entities")
            return filtered_relations
            
        except Exception as e:
            logger.error(f"Relation extraction failed: {e}")
            return []
    
    def _build_relation_context(self, entities: List[GenericEntity]) -> Dict[str, Any]:
        """Build domain-specific context for relation extraction"""
        
        context = {
            "domain": self.domain_config.domain_name,
            "language": self.domain_config.language,
            "relation_types": self.relation_types,
            "entities": [{"text": e.text, "type": e.entity_type} for e in entities]
        }
        
        # Add relation schemas and examples
        relation_definitions = {}
        for rel_type in self.relation_types:
            predicate = self.domain_config.relation_registry.get_predicate(rel_type)
            patterns = self.domain_config.relation_registry.get_patterns(rel_type)
            prompts = self.domain_config.relation_registry.get_ai_prompts(rel_type)
            
            relation_definitions[rel_type] = {
                "predicate": predicate,
                "patterns": patterns,
                "description": prompts.get("extraction", f"Find {rel_type} relationships")
            }
        
        context["relation_definitions"] = relation_definitions
        
        # Add domain-specific prompts if available
        if "relation_extraction" in self.domain_config.prompts:
            context["extraction_prompt"] = self.domain_config.prompts["relation_extraction"]
        
        return context

    async def _extract_with_llm(self, 
                               text: str, 
                               entities: List[GenericEntity],
                               context: Dict[str, Any]) -> List[GenericRelation]:
        """Extract relationships using LLM via intelligence service"""
        if len(entities) < 2:
            return []
        
        try:
            # Create entity context for LLM
            entity_context = []
            for i, entity in enumerate(entities):
                entity_context.append(f"{i}: {entity.text} ({entity.entity_type})")
            
            # Build extraction prompt using domain context
            relation_types = context.get("relation_types", [])
            
            extraction_text = f"""Extract relationships between the given entities from the text.

Text: {text}

Entities (reference by index):
{chr(10).join(entity_context)}

Available relation types for domain '{context.get('domain', 'generic')}':
{', '.join(relation_types)}

Return a JSON object with a 'relations' array. Each relation should have:
- subject_idx: index of subject entity
- object_idx: index of object entity  
- relation_type: one of the available relation types
- predicate: descriptive text for the relationship
- confidence: confidence score (0.0-1.0)
- context: supporting text snippet

Example format:
{{
    "relations": [
        {{
            "subject_idx": 0,
            "object_idx": 1,
            "relation_type": "WORKS_FOR",
            "predicate": "works for",
            "confidence": 0.9,
            "context": "supporting text"
        }}
    ]
}}

Extract only relationships explicitly mentioned in the text."""
            
            # Create schema for intelligence service
            schema = {"relations": "List of relationships between entities"}
            
            # Use intelligence service for extraction
            result = await extract_key_information(
                text=extraction_text,
                schema=schema
            )
            
            if not result.get('success'):
                logger.warning(f"LLM relation extraction failed: {result.get('error')}")
                return []
            
            # Extract relations from result
            relations_data = result.get('data', {}).get('relations', [])
            
            # Handle string response that needs JSON parsing
            if isinstance(relations_data, str):
                try:
                    relations_data = json.loads(relations_data)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse relations JSON, using empty list")
                    relations_data = []
            
            # Convert to GenericRelation objects
            relations = []
            for item_data in relations_data:
                relation = self._create_generic_relation(item_data, entities)
                if relation:
                    relations.append(relation)
            
            logger.info(f"LLM extracted {len(relations)} relations")
            return relations
            
        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []
    
    def _create_generic_relation(self, 
                               item_data: Dict[str, Any], 
                               entities: List[GenericEntity]) -> Optional[GenericRelation]:
        """Create GenericRelation object from LLM response data"""
        try:
            subject_idx = int(item_data.get('subject_idx', 0))
            object_idx = int(item_data.get('object_idx', 1))
            
            # Validate indices
            if (subject_idx >= len(entities) or object_idx >= len(entities) or 
                subject_idx < 0 or object_idx < 0):
                logger.warning(f"Invalid entity indices: subject={subject_idx}, object={object_idx}, total={len(entities)}")
                return None
            
            # Map relation type to domain type
            rel_type_str = str(item_data.get('relation_type', 'RELATES_TO')).upper()
            relation_type = self._map_to_domain_relation_type(rel_type_str)
            
            # Extract confidence
            confidence = float(item_data.get('confidence', 0.7))
            
            return GenericRelation(
                subject=entities[subject_idx],
                object=entities[object_idx],
                relation_type=relation_type,
                predicate=str(item_data.get('predicate', '')).strip(),
                confidence=max(0.0, min(1.0, confidence)),
                context=str(item_data.get('context', '')).strip()
            )
            
        except Exception as e:
            logger.warning(f"Failed to create relation from data: {e}")
            return None
    
    def _map_to_domain_relation_type(self, rel_type_str: str) -> str:
        """Map generic relation type to domain-specific type"""
        
        # Check if the type directly exists in domain
        if rel_type_str in self.relation_types:
            return rel_type_str
        
        # Common mappings for fallback
        common_mappings = {
            'RELATES_TO': ['RELATES_TO', 'RELATED_TO', 'CONNECTS_TO'],
            'IS_A': ['IS_A', 'TYPE_OF', 'INSTANCE_OF'],
            'PART_OF': ['PART_OF', 'BELONGS_TO', 'COMPONENT_OF']
        }
        
        # Try to find a mapping
        for domain_type in self.relation_types:
            domain_upper = domain_type.upper()
            if domain_upper in common_mappings:
                if rel_type_str in common_mappings[domain_upper]:
                    return domain_type
        
        # Default to the first available relation type, or RELATES_TO
        return self.relation_types[0] if self.relation_types else "RELATES_TO"
    
    def _extract_with_patterns(self, text: str, entities: List[GenericEntity]) -> List[GenericRelation]:
        """Extract relationships using pattern matching (fallback method)"""
        relations = []
        
        if not self.relation_patterns:
            return relations
        
        # Create entity lookup for faster searching
        entity_lookup = {entity.text.lower(): entity for entity in entities}
        
        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                try:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if len(match.groups()) >= 2:
                            subject_text = match.group(1).lower()
                            object_text = match.group(2).lower()
                            
                            # Find matching entities
                            subject = entity_lookup.get(subject_text)
                            obj = entity_lookup.get(object_text)
                            
                            if subject and obj:
                                predicate = self.domain_config.relation_registry.get_predicate(relation_type)
                                
                                relation = GenericRelation(
                                    subject=subject,
                                    object=obj,
                                    relation_type=relation_type,
                                    predicate=predicate or "relates to",
                                    confidence=0.8,  # Pattern-based confidence
                                    context=match.group(0)
                                )
                                relations.append(relation)
                except re.error:
                    continue  # Skip invalid patterns
        
        return relations
    
    def get_domain_relation_types(self) -> List[str]:
        """Get all relation types available in the current domain"""
        return self.relation_types.copy()
    
    def get_relation_statistics(self, relations: List[GenericRelation]) -> Dict[str, Any]:
        """Get statistics about extracted relations"""
        if not relations:
            return {"total": 0, "domain": self.domain_config.domain_name}
        
        type_counts = {}
        confidence_sum = 0
        subject_types = {}
        object_types = {}
        
        for relation in relations:
            rel_type = relation.relation_type
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
            confidence_sum += relation.confidence
            
            subj_type = relation.subject.entity_type
            obj_type = relation.object.entity_type
            
            subject_types[subj_type] = subject_types.get(subj_type, 0) + 1
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
        
        return {
            "domain": self.domain_config.domain_name,
            "total": len(relations),
            "by_type": type_counts,
            "average_confidence": confidence_sum / len(relations),
            "high_confidence": len([r for r in relations if r.confidence > 0.8]),
            "subject_entity_types": subject_types,
            "object_entity_types": object_types,
            "unique_subjects": len(set(r.subject.text for r in relations)),
            "unique_objects": len(set(r.object.text for r in relations)),
            "confidence_distribution": {
                "high (>0.8)": len([r for r in relations if r.confidence > 0.8]),
                "medium (0.5-0.8)": len([r for r in relations if 0.5 <= r.confidence <= 0.8]),
                "low (<0.5)": len([r for r in relations if r.confidence < 0.5])
            }
        }


# Convenience functions for quick domain setup
def create_business_relation_extractor(confidence_threshold: float = 0.7) -> GenericRelationExtractor:
    """Create a relation extractor configured for business domain"""
    from pathlib import Path
    config_path = Path(__file__).parent / "domains" / "business.yaml"
    return GenericRelationExtractor(config_path, confidence_threshold)


def create_medical_relation_extractor(confidence_threshold: float = 0.85) -> GenericRelationExtractor:
    """Create a relation extractor configured for medical domain (higher confidence)"""
    from pathlib import Path
    config_path = Path(__file__).parent / "domains" / "medical.yaml"
    return GenericRelationExtractor(config_path, confidence_threshold)
