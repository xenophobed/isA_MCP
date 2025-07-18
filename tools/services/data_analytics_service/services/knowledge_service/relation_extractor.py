#!/usr/bin/env python3
"""
Relation Extractor for Graph Analytics - Refactored Version

Extracts relationships between entities from text using:
1. LLM-based relation extraction with structured output via intelligence service
2. Pattern-based extraction for fallback via regex extractor
3. Configurable relationship types and confidence thresholds
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from tools.services.intelligence_service.language.text_extractor import text_extractor
from tools.services.data_analytics_service.processors.file_processors.regex_extractor import RegexExtractor, RelationType, Entity, Relation

logger = get_logger(__name__)

class RelationExtractor:
    """Extract relationships between entities from text"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize relation extractor"""
        self.config = config or {}
        
        # Initialize regex extractor for pattern-based extraction
        self.regex_extractor = RegexExtractor(config)
        
        # LLM extraction settings
        self.use_llm = self.config.get('use_llm', True)
        self.fallback_to_patterns = self.config.get('fallback_to_patterns', True)
        
        logger.info("RelationExtractor initialized with intelligence service and regex fallback")
    
    async def extract_relations(self, text: str, entities: List[Entity], methods: List[str] = None) -> List[Relation]:
        """Extract relationships between entities"""
        if len(entities) < 2:
            return []
            
        if methods is None:
            methods = ['llm'] if self.use_llm else ['pattern']
            
        # For long text, prioritize LLM
        if len(text) > 3000 and self.use_llm:
            logger.info(f"🔗 Long text ({len(text):,} chars) relation extraction, using LLM processing")
            methods = ['llm']
        
        all_relations = []
        
        for method in methods:
            if method == 'llm' and self.use_llm:
                relations = await self._extract_with_llm(text, entities)
            elif method == 'pattern':
                relations = self._extract_with_patterns(text, entities)
            elif method == 'hybrid':
                llm_relations = await self._extract_with_llm(text, entities) if self.use_llm else []
                pattern_relations = self._extract_with_patterns(text, entities)
                relations = self._merge_relations(llm_relations + pattern_relations)
            else:
                logger.warning(f"Unknown extraction method: {method}")
                continue
                
            all_relations.extend(relations)
            
            # If LLM failed and fallback is enabled, try patterns
            if method == 'llm' and not relations and self.fallback_to_patterns:
                logger.info("LLM extraction failed, falling back to pattern-based extraction")
                pattern_relations = self._extract_with_patterns(text, entities)
                all_relations.extend(pattern_relations)
        
        # Deduplicate and merge relations
        final_relations = self._merge_relations(all_relations)
        
        logger.info(f"Extracted {len(final_relations)} relations from {len(entities)} entities")
        return final_relations
    
    async def _extract_with_llm(self, text: str, entities: List[Entity]) -> List[Relation]:
        """Extract relationships using LLM via intelligence service"""
        if len(entities) < 2:
            return []
        
        try:
            # Create entity context for LLM
            entity_context = []
            for i, entity in enumerate(entities):
                entity_type = getattr(entity, 'entity_type', 'UNKNOWN')
                if hasattr(entity_type, 'value'):
                    entity_type = entity_type.value
                entity_context.append(f"{i}: {entity.text} ({entity_type})")
            
            # Create custom schema for relation extraction
            schema = {
                "relations": "List of relations found between entities. Each relation should have: subject_idx (integer), predicate (string), object_idx (integer), relation_type (string), confidence (float), context (string)"
            }
            
            extraction_text = f"""Extract relationships between the given entities from the text. Return a JSON object with a 'relations' array.

Text: {text}

Entities (reference by index):
{chr(10).join(entity_context)}

IMPORTANT: Return ONLY a valid JSON object. Do not include any explanation or additional text.

Example for medical text:
Input: "患者检查发现双肺多发结节，建议在深圳平安医院进一步检查。"
Entities: 0: 患者 (PERSON), 1: 双肺多发结节 (MEDICAL_CONDITION), 2: 深圳平安医院 (ORGANIZATION)
Output:
{{
    "relations": [
        {{
            "subject_idx": 0,
            "predicate": "has_condition",
            "object_idx": 1,
            "relation_type": "HAS_CONDITION", 
            "confidence": 0.9,
            "context": "患者检查发现双肺多发结节"
        }},
        {{
            "subject_idx": 0,
            "predicate": "should_visit",
            "object_idx": 2,
            "relation_type": "RELATES_TO",
            "confidence": 0.8,
            "context": "建议在深圳平安医院进一步检查"
        }}
    ]
}}

Relationship Types: IS_A, PART_OF, LOCATED_IN, WORKS_FOR, OWNS, CREATED_BY, HAPPENED_AT, CAUSED_BY, SIMILAR_TO, RELATES_TO, DEPENDS_ON, CUSTOM, HAS_CONDITION

Now extract relationships from the text above and return the JSON response:"""
            
            # Use intelligence service for extraction (now using gpt-4.1-mini)
            result = await text_extractor.extract_key_information(
                text=extraction_text,
                schema=schema
            )
            
            if not result.get('success'):
                logger.warning(f"LLM relation extraction failed: {result.get('error')}")
                return []
            
            # Extract relations from result with enhanced JSON parsing
            relations_data = result.get('data', {}).get('relations', [])
            if isinstance(relations_data, str):
                try:
                    relations_data = json.loads(relations_data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Initial JSON parsing failed: {e}")
                    try:
                        # Try to extract JSON from text with better regex
                        import re
                        json_match = re.search(r'\{.*\}', relations_data, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            result_data = json.loads(json_str)
                            relations_data = result_data.get('relations', [])
                        else:
                            # Try to clean malformed JSON
                            cleaned_json = self._clean_malformed_json(relations_data)
                            if cleaned_json:
                                result_data = json.loads(cleaned_json)
                                relations_data = result_data.get('relations', [])
                            else:
                                logger.error("Could not parse relations data as JSON, using empty array")
                                relations_data = []
                    except (json.JSONDecodeError, Exception) as fallback_error:
                        logger.error(f"All JSON parsing attempts failed: {fallback_error}")
                        relations_data = []
            
            # Convert to Relation objects
            relations = []
            for item_data in relations_data:
                relation = self._create_relation_from_data(item_data, entities)
                if relation:
                    relations.append(relation)
            
            logger.info(f"LLM extracted {len(relations)} relations")
            return relations
            
        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []
    
    def _create_relation_from_data(self, item_data: Dict[str, Any], entities: List[Entity]) -> Optional[Relation]:
        """Create Relation object from LLM response data"""
        try:
            # Handle None values safely
            subject_idx_val = item_data.get('subject_idx', 0)
            object_idx_val = item_data.get('object_idx', 1)
            
            if subject_idx_val is None or object_idx_val is None:
                logger.warning(f"Missing indices in relation data: subject_idx={subject_idx_val}, object_idx={object_idx_val}")
                return None
            
            subject_idx = int(subject_idx_val)
            object_idx = int(object_idx_val)
            
            # Validate indices (allow self-references but ensure indices are within bounds)
            if (subject_idx >= len(entities) or object_idx >= len(entities) or 
                subject_idx < 0 or object_idx < 0):
                logger.warning(f"Invalid entity indices: subject={subject_idx}, object={object_idx}, total={len(entities)}")
                return None
            
            # Log self-reference relations but allow them
            if subject_idx == object_idx:
                logger.debug(f"Self-reference relation detected: entity {subject_idx} ({entities[subject_idx].text})")
            
            # Map relation type
            rel_type_str = str(item_data.get('relation_type', 'RELATES_TO')).upper()
            relation_type = self._map_relation_type(rel_type_str)
            
            # Extract confidence
            confidence = item_data.get('confidence', 0.7)
            if isinstance(confidence, str):
                try:
                    confidence = float(confidence)
                except ValueError:
                    confidence = 0.7
            
            return Relation(
                subject=entities[subject_idx],
                predicate=str(item_data.get('predicate', '')).strip(),
                object=entities[object_idx],
                relation_type=relation_type,
                confidence=max(0.0, min(1.0, float(confidence))),
                context=str(item_data.get('context', '')).strip(),
                properties=item_data.get('properties', {}),
                temporal_info=item_data.get('temporal_info', {})
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
        """Extract relationships using regex patterns via regex extractor"""
        return self.regex_extractor.extract_relations(text, entities)
    
    def _get_predicate_for_type(self, relation_type: RelationType) -> str:
        """Get default predicate for relation type"""
        return self.regex_extractor._get_predicate_for_type(relation_type)
    
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
    
    def _clean_malformed_json(self, text: str) -> Optional[str]:
        """Clean common malformed JSON issues from LLM responses"""
        try:
            import re
            
            # First, try to parse as-is - maybe it's already valid
            try:
                json.loads(text)
                return text  # Already valid JSON
            except json.JSONDecodeError:
                pass  # Need to clean it
            
            # Extract potential JSON block
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if not json_match:
                return None
                
            json_str = json_match.group()
            
            # Test if extracted JSON is already valid
            try:
                json.loads(json_str)
                return json_str  # Extracted JSON is valid
            except json.JSONDecodeError:
                pass  # Need to clean it
            
            # Common fixes for malformed JSON
            # Fix missing commas between objects/arrays
            json_str = re.sub(r'}\s*{', '},{', json_str)
            json_str = re.sub(r']\s*\[', '],[', json_str)
            json_str = re.sub(r'}\s*\[', '},[', json_str)
            json_str = re.sub(r']\s*{', '],{', json_str)
            
            # Fix missing commas after values
            json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
            json_str = re.sub(r'"\s*\n\s*{', '",\n{', json_str)
            json_str = re.sub(r'}\s*\n\s*"', '},\n"', json_str)
            
            # Fix trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # Fix unquoted property names (only if not already quoted)
            # Look for word characters followed by colon, but not preceded by quote
            json_str = re.sub(r'(?<!")(\w+):\s*', r'"\1": ', json_str)
            
            # Fix single quotes to double quotes (be more careful with nested quotes)
            json_str = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', json_str)
            
            # Test the cleaned JSON
            try:
                json.loads(json_str)
                return json_str  # Successfully cleaned
            except json.JSONDecodeError as e:
                logger.debug(f"JSON cleaning failed: {e}, original: {text[:200]}...")
                return None
            
        except Exception as e:
            logger.debug(f"JSON cleaning exception: {e}")
            return None
    
    def should_use_llm_for_text(self, text: str) -> bool:
        """Determine if LLM should be used for the given text"""
        return len(text) > 1000 and self.use_llm
    
    def add_custom_pattern(self, relation_type: RelationType, pattern: str) -> None:
        """Add custom pattern to regex extractor"""
        self.regex_extractor.add_custom_pattern(relation_type, pattern)
    
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
            
            subj_type = getattr(relation.subject, 'entity_type', 'UNKNOWN')
            if hasattr(subj_type, 'value'):
                subj_type = subj_type.value
            obj_type = getattr(relation.object, 'entity_type', 'UNKNOWN')
            if hasattr(obj_type, 'value'):
                obj_type = obj_type.value
                
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