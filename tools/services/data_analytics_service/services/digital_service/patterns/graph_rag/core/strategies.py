"""
AI-powered extraction strategies for Generic Knowledge Analytics

Provides abstract base classes and concrete implementations for different
AI-based knowledge extraction approaches (LLM, VLM, hybrid, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
import asyncio
import json
import time
from datetime import datetime

from .types import GenericEntity, GenericRelation, GenericAttribute
from .config import DomainConfig, AIStrategyConfig


@dataclass
class ExtractionResult:
    """Result of an extraction operation"""
    entities: List[GenericEntity]
    relations: List[GenericRelation]
    attributes: List[GenericAttribute]
    
    # Metadata
    success: bool = True
    error: Optional[str] = None
    processing_time: float = 0.0
    confidence_avg: float = 0.0
    extraction_method: str = "unknown"
    model_version: str = ""
    
    # Source information
    source_text: str = ""
    source_length: int = 0
    chunk_index: int = 0
    
    def merge_with(self, other: 'ExtractionResult') -> 'ExtractionResult':
        """Merge this result with another extraction result"""
        return ExtractionResult(
            entities=self.entities + other.entities,
            relations=self.relations + other.relations,
            attributes=self.attributes + other.attributes,
            success=self.success and other.success,
            error=self.error or other.error,
            processing_time=self.processing_time + other.processing_time,
            confidence_avg=(self.confidence_avg + other.confidence_avg) / 2,
            extraction_method=f"{self.extraction_method}+{other.extraction_method}",
            source_length=self.source_length + other.source_length
        )


class BaseExtractionStrategy(ABC):
    """Abstract base class for knowledge extraction strategies"""
    
    def __init__(self, domain_config: DomainConfig, strategy_config: AIStrategyConfig):
        self.domain_config = domain_config
        self.strategy_config = strategy_config
        self.strategy_name = "base"
        
    @abstractmethod
    async def extract_entities(self, text: str, context: Dict[str, Any] = None) -> List[GenericEntity]:
        """Extract entities from text"""
        pass
    
    @abstractmethod
    async def extract_relations(self, 
                              text: str, 
                              entities: List[GenericEntity],
                              context: Dict[str, Any] = None) -> List[GenericRelation]:
        """Extract relations between entities"""
        pass
    
    @abstractmethod
    async def extract_attributes(self,
                               text: str,
                               entities: List[GenericEntity],
                               context: Dict[str, Any] = None) -> List[GenericAttribute]:
        """Extract attributes for entities"""
        pass
    
    async def extract_knowledge(self, 
                              text: str, 
                              context: Dict[str, Any] = None) -> ExtractionResult:
        """Extract complete knowledge from text"""
        start_time = time.time()
        
        try:
            # Extract entities first
            entities = await self.extract_entities(text, context)
            
            # Extract relations using found entities
            relations = await self.extract_relations(text, entities, context)
            
            # Extract attributes for entities
            attributes = await self.extract_attributes(text, entities, context)
            
            # Calculate average confidence
            all_items = entities + relations + attributes
            avg_confidence = sum(item.confidence for item in all_items) / len(all_items) if all_items else 0.0
            
            return ExtractionResult(
                entities=entities,
                relations=relations,
                attributes=attributes,
                success=True,
                processing_time=time.time() - start_time,
                confidence_avg=avg_confidence,
                extraction_method=self.strategy_name,
                model_version=self.strategy_config.model_version,
                source_text=text[:500],  # Store snippet
                source_length=len(text)
            )
            
        except Exception as e:
            return ExtractionResult(
                entities=[],
                relations=[],
                attributes=[],
                success=False,
                error=str(e),
                processing_time=time.time() - start_time,
                extraction_method=self.strategy_name,
                source_text=text[:500],
                source_length=len(text)
            )
    
    def _build_entity_prompt(self, text: str, context: Dict[str, Any] = None) -> str:
        """Build prompt for entity extraction"""
        entity_types = list(self.domain_config.entity_registry.get_types())
        
        base_prompt = self.domain_config.prompts.get('entity_extraction', 
                                                   "Extract entities from the following text:")
        
        prompt = f"""{self.strategy_config.system_prompt}

{self.strategy_config.domain_context}

{base_prompt}

Entity Types to Extract:
{', '.join(entity_types)}

Text: {text}

Return JSON format:
{{
  "entities": [
    {{
      "text": "entity name",
      "entity_type": "TYPE_NAME",
      "confidence": 0.95,
      "start_position": 0,
      "end_position": 10
    }}
  ]
}}"""
        return prompt
    
    def _build_relation_prompt(self, 
                             text: str, 
                             entities: List[GenericEntity],
                             context: Dict[str, Any] = None) -> str:
        """Build prompt for relation extraction"""
        relation_types = list(self.domain_config.relation_registry.get_types())
        entity_list = [f"- {e.text} ({e.entity_type})" for e in entities]
        
        base_prompt = self.domain_config.prompts.get('relation_extraction',
                                                   "Find relationships between entities:")
        
        prompt = f"""{self.strategy_config.system_prompt}

{base_prompt}

Relation Types to Find:
{', '.join(relation_types)}

Entities Found:
{chr(10).join(entity_list)}

Text: {text}

Return JSON format:
{{
  "relations": [
    {{
      "subject": "entity1",
      "object": "entity2", 
      "relation_type": "RELATION_TYPE",
      "predicate": "descriptive text",
      "confidence": 0.90,
      "context": "supporting text"
    }}
  ]
}}"""
        return prompt
    
    def _build_attribute_prompt(self,
                              text: str,
                              entities: List[GenericEntity],
                              context: Dict[str, Any] = None) -> str:
        """Build prompt for attribute extraction"""
        entity_schemas = {}
        for entity in entities:
            schema = self.domain_config.entity_registry.get_schema(entity.entity_type)
            entity_schemas[entity.text] = schema
        
        base_prompt = self.domain_config.prompts.get('attribute_extraction',
                                                   "Extract attributes for entities:")
        
        prompt = f"""{self.strategy_config.system_prompt}

{base_prompt}

Entity Schemas:
{json.dumps(entity_schemas, indent=2)}

Text: {text}

Return JSON format:
{{
  "attributes": {{
    "entity_name": {{
      "attribute_name": {{
        "value": "attribute_value",
        "attribute_type": "TEXT|NUMBER|DATE|BOOLEAN",
        "confidence": 0.85
      }}
    }}
  }}
}}"""
        return prompt


class LLMExtractionStrategy(BaseExtractionStrategy):
    """LLM-based knowledge extraction strategy"""
    
    def __init__(self, domain_config: DomainConfig, strategy_config: AIStrategyConfig):
        super().__init__(domain_config, strategy_config)
        self.strategy_name = "llm"
        
        # Import LLM service dynamically to avoid circular imports
        try:
            from tools.services.intelligence_service.language.text_extractor import extract_key_information
            self.llm_extract = extract_key_information
        except ImportError:
            raise ImportError("LLM extraction service not available")
    
    async def extract_entities(self, text: str, context: Dict[str, Any] = None) -> List[GenericEntity]:
        """Extract entities using LLM"""
        prompt = self._build_entity_prompt(text, context)
        
        try:
            # Use intelligence service for extraction
            result = await self.llm_extract(
                text=prompt,
                schema={"entities": "List of entities with their types and positions"}
            )
            
            if not result.get('success'):
                return []
            
            entities_data = result.get('data', {}).get('entities', [])
            entities = []
            
            for entity_data in entities_data:
                if isinstance(entity_data, dict):
                    entity = GenericEntity(
                        text=entity_data.get('text', ''),
                        entity_type=entity_data.get('entity_type', 'UNKNOWN'),
                        confidence=entity_data.get('confidence', 0.7),
                        start_position=entity_data.get('start_position', 0),
                        end_position=entity_data.get('end_position', 0),
                        extraction_method="llm",
                        model_version=self.strategy_config.model_version
                    )
                    entities.append(entity)
            
            return entities
            
        except Exception as e:
            print(f"LLM entity extraction failed: {e}")
            return []
    
    async def extract_relations(self, 
                              text: str, 
                              entities: List[GenericEntity],
                              context: Dict[str, Any] = None) -> List[GenericRelation]:
        """Extract relations using LLM"""
        if len(entities) < 2:
            return []
        
        prompt = self._build_relation_prompt(text, entities, context)
        
        try:
            result = await self.llm_extract(
                text=prompt,
                schema={"relations": "List of relationships between entities"}
            )
            
            if not result.get('success'):
                return []
            
            relations_data = result.get('data', {}).get('relations', [])
            relations = []
            
            # Create entity lookup
            entity_lookup = {e.text.lower(): e for e in entities}
            
            for rel_data in relations_data:
                if isinstance(rel_data, dict):
                    subject_text = rel_data.get('subject', '').lower()
                    object_text = rel_data.get('object', '').lower()
                    
                    subject = entity_lookup.get(subject_text)
                    obj = entity_lookup.get(object_text)
                    
                    if subject and obj:
                        relation = GenericRelation(
                            subject=subject,
                            object=obj,
                            relation_type=rel_data.get('relation_type', 'RELATES_TO'),
                            predicate=rel_data.get('predicate', ''),
                            confidence=rel_data.get('confidence', 0.7),
                            context=rel_data.get('context', ''),
                            extraction_method="llm",
                            model_version=self.strategy_config.model_version
                        )
                        relations.append(relation)
            
            return relations
            
        except Exception as e:
            print(f"LLM relation extraction failed: {e}")
            return []
    
    async def extract_attributes(self,
                               text: str,
                               entities: List[GenericEntity],
                               context: Dict[str, Any] = None) -> List[GenericAttribute]:
        """Extract attributes using LLM"""
        if not entities:
            return []
        
        prompt = self._build_attribute_prompt(text, entities, context)
        
        try:
            result = await self.llm_extract(
                text=prompt,
                schema={"attributes": "Attributes for each entity"}
            )
            
            if not result.get('success'):
                return []
            
            attributes_data = result.get('data', {}).get('attributes', {})
            attributes = []
            
            # Create entity lookup
            entity_lookup = {e.text.lower(): e for e in entities}
            
            for entity_name, entity_attrs in attributes_data.items():
                entity = entity_lookup.get(entity_name.lower())
                if not entity:
                    continue
                
                for attr_name, attr_data in entity_attrs.items():
                    if isinstance(attr_data, dict):
                        attribute = GenericAttribute(
                            entity_id=entity.id,
                            name=attr_name,
                            value=attr_data.get('value'),
                            attribute_type=attr_data.get('attribute_type', 'TEXT'),
                            confidence=attr_data.get('confidence', 0.7),
                            extraction_method="llm",
                            model_version=self.strategy_config.model_version
                        )
                        attributes.append(attribute)
            
            return attributes
            
        except Exception as e:
            print(f"LLM attribute extraction failed: {e}")
            return []


class VLMExtractionStrategy(BaseExtractionStrategy):
    """Vision-Language Model extraction strategy for multimodal content"""
    
    def __init__(self, domain_config: DomainConfig, strategy_config: AIStrategyConfig):
        super().__init__(domain_config, strategy_config)
        self.strategy_name = "vlm"
        
        # TODO: Implement VLM service integration
        # This would integrate with models like GPT-4V, LLaVA, etc.
    
    async def extract_entities(self, text: str, context: Dict[str, Any] = None) -> List[GenericEntity]:
        """Extract entities from text and images using VLM"""
        # TODO: Implement VLM entity extraction
        # This would process both text and visual content
        return []
    
    async def extract_relations(self, 
                              text: str, 
                              entities: List[GenericEntity],
                              context: Dict[str, Any] = None) -> List[GenericRelation]:
        """Extract relations using VLM multimodal understanding"""
        # TODO: Implement VLM relation extraction
        return []
    
    async def extract_attributes(self,
                               text: str,
                               entities: List[GenericEntity],
                               context: Dict[str, Any] = None) -> List[GenericAttribute]:
        """Extract attributes using VLM multimodal analysis"""
        # TODO: Implement VLM attribute extraction
        return []


class PatternExtractionStrategy(BaseExtractionStrategy):
    """Pattern-based extraction strategy using regex and rules"""
    
    def __init__(self, domain_config: DomainConfig, strategy_config: AIStrategyConfig):
        super().__init__(domain_config, strategy_config)
        self.strategy_name = "pattern"
    
    async def extract_entities(self, text: str, context: Dict[str, Any] = None) -> List[GenericEntity]:
        """Extract entities using pattern matching"""
        import re
        entities = []
        
        for entity_type in self.domain_config.entity_registry.get_types():
            patterns = self.domain_config.entity_registry.get_extraction_patterns(entity_type)
            
            for pattern in patterns:
                try:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        entity = GenericEntity(
                            text=match.group(1) if match.groups() else match.group(0),
                            entity_type=entity_type,
                            confidence=0.8,  # Pattern-based confidence
                            start_position=match.start(),
                            end_position=match.end(),
                            extraction_method="pattern"
                        )
                        entities.append(entity)
                except re.error:
                    continue  # Skip invalid patterns
        
        return entities
    
    async def extract_relations(self, 
                              text: str, 
                              entities: List[GenericEntity],
                              context: Dict[str, Any] = None) -> List[GenericRelation]:
        """Extract relations using pattern matching"""
        import re
        relations = []
        
        if len(entities) < 2:
            return relations
        
        # Create entity lookup
        entity_lookup = {e.text.lower(): e for e in entities}
        
        for relation_type in self.domain_config.relation_registry.get_types():
            patterns = self.domain_config.relation_registry.get_patterns(relation_type)
            predicate = self.domain_config.relation_registry.get_predicate(relation_type)
            
            for pattern in patterns:
                try:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if len(match.groups()) >= 2:
                            subject_text = match.group(1).lower()
                            object_text = match.group(2).lower()
                            
                            subject = entity_lookup.get(subject_text)
                            obj = entity_lookup.get(object_text)
                            
                            if subject and obj:
                                relation = GenericRelation(
                                    subject=subject,
                                    object=obj,
                                    relation_type=relation_type,
                                    predicate=predicate,
                                    confidence=0.8,
                                    context=match.group(0),
                                    extraction_method="pattern"
                                )
                                relations.append(relation)
                except re.error:
                    continue
        
        return relations
    
    async def extract_attributes(self,
                               text: str,
                               entities: List[GenericEntity],
                               context: Dict[str, Any] = None) -> List[GenericAttribute]:
        """Extract attributes using pattern matching"""
        # TODO: Implement pattern-based attribute extraction
        # This would use regex patterns to find structured data
        return []


class HybridExtractionStrategy(BaseExtractionStrategy):
    """Hybrid strategy combining multiple extraction approaches"""
    
    def __init__(self, domain_config: DomainConfig, strategy_config: AIStrategyConfig):
        super().__init__(domain_config, strategy_config)
        self.strategy_name = "hybrid"
        
        # Initialize sub-strategies
        self.llm_strategy = LLMExtractionStrategy(domain_config, strategy_config)
        self.pattern_strategy = PatternExtractionStrategy(domain_config, strategy_config)
        
    async def extract_knowledge(self, 
                              text: str, 
                              context: Dict[str, Any] = None) -> ExtractionResult:
        """Extract knowledge using hybrid approach"""
        
        # Run both strategies in parallel
        llm_task = self.llm_strategy.extract_knowledge(text, context)
        pattern_task = self.pattern_strategy.extract_knowledge(text, context)
        
        llm_result, pattern_result = await asyncio.gather(llm_task, pattern_task)
        
        # Merge results intelligently
        merged_result = self._merge_results(llm_result, pattern_result)
        merged_result.extraction_method = "hybrid"
        
        return merged_result
    
    def _merge_results(self, llm_result: ExtractionResult, pattern_result: ExtractionResult) -> ExtractionResult:
        """Intelligently merge results from different strategies"""
        
        # Combine entities, prioritizing higher confidence
        all_entities = llm_result.entities + pattern_result.entities
        merged_entities = self._deduplicate_entities(all_entities)
        
        # Combine relations
        all_relations = llm_result.relations + pattern_result.relations
        merged_relations = self._deduplicate_relations(all_relations)
        
        # Combine attributes
        all_attributes = llm_result.attributes + pattern_result.attributes
        merged_attributes = self._deduplicate_attributes(all_attributes)
        
        return ExtractionResult(
            entities=merged_entities,
            relations=merged_relations,
            attributes=merged_attributes,
            success=llm_result.success or pattern_result.success,
            processing_time=llm_result.processing_time + pattern_result.processing_time,
            extraction_method="hybrid",
            source_text=llm_result.source_text,
            source_length=llm_result.source_length
        )
    
    def _deduplicate_entities(self, entities: List[GenericEntity]) -> List[GenericEntity]:
        """Remove duplicate entities, keeping highest confidence"""
        entity_map = {}
        
        for entity in entities:
            key = (entity.text.lower(), entity.entity_type)
            if key not in entity_map or entity.confidence > entity_map[key].confidence:
                entity_map[key] = entity
        
        return list(entity_map.values())
    
    def _deduplicate_relations(self, relations: List[GenericRelation]) -> List[GenericRelation]:
        """Remove duplicate relations"""
        relation_map = {}
        
        for relation in relations:
            key = (relation.subject.text.lower(), relation.object.text.lower(), relation.relation_type)
            if key not in relation_map or relation.confidence > relation_map[key].confidence:
                relation_map[key] = relation
        
        return list(relation_map.values())
    
    def _deduplicate_attributes(self, attributes: List[GenericAttribute]) -> List[GenericAttribute]:
        """Remove duplicate attributes"""
        attr_map = {}
        
        for attr in attributes:
            key = (attr.entity_id, attr.name)
            if key not in attr_map or attr.confidence > attr_map[key].confidence:
                attr_map[key] = attr
        
        return list(attr_map.values())
    
    # Delegate individual extraction methods to LLM strategy
    async def extract_entities(self, text: str, context: Dict[str, Any] = None) -> List[GenericEntity]:
        return await self.llm_strategy.extract_entities(text, context)
    
    async def extract_relations(self, text: str, entities: List[GenericEntity], context: Dict[str, Any] = None) -> List[GenericRelation]:
        return await self.llm_strategy.extract_relations(text, entities, context)
    
    async def extract_attributes(self, text: str, entities: List[GenericEntity], context: Dict[str, Any] = None) -> List[GenericAttribute]:
        return await self.llm_strategy.extract_attributes(text, entities, context)