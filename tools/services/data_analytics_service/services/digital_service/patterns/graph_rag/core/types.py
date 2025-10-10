"""
Generic type system for knowledge analytics

Provides flexible, domain-agnostic data structures that can be configured
for any knowledge domain (business, medical, legal, academic, etc.)
"""

from typing import Dict, List, Any, Optional, Union, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import uuid
from datetime import datetime


@dataclass
class GenericEntity:
    """Universal entity representation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    entity_type: str = "UNKNOWN"  # Dynamic type instead of enum
    confidence: float = 0.0
    start_position: int = 0
    end_position: int = 0
    
    # Flexible properties
    properties: Dict[str, Any] = field(default_factory=dict)
    canonical_form: str = ""
    aliases: List[str] = field(default_factory=list)
    
    # AI-specific metadata
    extraction_method: str = "unknown"  # llm, vlm, hybrid, pattern
    model_version: str = ""
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.canonical_form:
            self.canonical_form = self.text
        
        # Backward compatibility
        self.start = self.start_position
        self.end = self.end_position


@dataclass 
class GenericRelation:
    """Universal relation representation"""
    subject: GenericEntity
    object: GenericEntity
    relation_type: str = "RELATES_TO"  # Dynamic type
    predicate: str = ""
    confidence: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Context and evidence
    context: str = ""
    source_text: str = ""
    evidence_span: tuple = (0, 0)
    
    # Flexible properties
    properties: Dict[str, Any] = field(default_factory=dict)
    temporal_info: Dict[str, Any] = field(default_factory=dict)
    
    # AI-specific metadata  
    extraction_method: str = "unknown"
    model_version: str = ""
    extraction_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GenericAttribute:
    """Universal attribute representation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    name: str = ""
    value: Any = None
    attribute_type: str = "TEXT"  # TEXT, NUMBER, DATE, BOOLEAN, LIST, etc.
    confidence: float = 0.0
    
    # Value processing
    normalized_value: Any = None
    original_value: Any = None
    unit: str = ""
    
    # Context
    source_text: str = ""
    extraction_context: str = ""
    
    # AI metadata
    extraction_method: str = "unknown"
    model_version: str = ""
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.normalized_value is None:
            self.normalized_value = self.value
        if self.original_value is None:
            self.original_value = self.value


class TypeRegistry(ABC):
    """Abstract base for type registries"""
    
    def __init__(self):
        self._types: Dict[str, Dict[str, Any]] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
    
    @abstractmethod
    def register_type(self, type_name: str, schema: Dict[str, Any], **kwargs):
        """Register a new type with its schema"""
        pass
    
    def get_types(self) -> Set[str]:
        """Get all registered type names"""
        return set(self._types.keys())
    
    def get_schema(self, type_name: str) -> Dict[str, Any]:
        """Get schema for a specific type"""
        return self._schemas.get(type_name, {})
    
    def type_exists(self, type_name: str) -> bool:
        """Check if type is registered"""
        return type_name in self._types


class EntityTypeRegistry(TypeRegistry):
    """Registry for entity types and their schemas"""
    
    def register_type(self, 
                     type_name: str, 
                     schema: Dict[str, Any],
                     description: str = "",
                     extraction_patterns: List[str] = None,
                     ai_prompts: Dict[str, str] = None):
        """
        Register an entity type
        
        Args:
            type_name: Name of the entity type (e.g., "PERSON", "DISEASE")
            schema: Attribute schema for this entity type
            description: Human-readable description
            extraction_patterns: Regex patterns for pattern-based extraction
            ai_prompts: Custom prompts for AI-based extraction
        """
        self._types[type_name] = {
            "description": description,
            "extraction_patterns": extraction_patterns or [],
            "ai_prompts": ai_prompts or {}
        }
        self._schemas[type_name] = schema
    
    def get_extraction_patterns(self, type_name: str) -> List[str]:
        """Get extraction patterns for entity type"""
        return self._types.get(type_name, {}).get("extraction_patterns", [])
    
    def get_ai_prompts(self, type_name: str) -> Dict[str, str]:
        """Get AI prompts for entity type"""
        return self._types.get(type_name, {}).get("ai_prompts", {})


class RelationTypeRegistry(TypeRegistry):
    """Registry for relation types and their extraction rules"""
    
    def register_type(self,
                     relation_type: str,
                     schema: Dict[str, Any],
                     predicate: str = "",
                     patterns: List[str] = None,
                     ai_prompts: Dict[str, str] = None,
                     valid_entity_pairs: List[tuple] = None):
        """
        Register a relation type
        
        Args:
            relation_type: Name of relation (e.g., "TREATS", "WORKS_FOR")
            schema: Properties schema for this relation
            predicate: Default predicate text
            patterns: Regex patterns for extraction
            ai_prompts: Custom AI prompts
            valid_entity_pairs: Valid (subject_type, object_type) pairs
        """
        self._types[relation_type] = {
            "predicate": predicate or relation_type.lower().replace("_", " "),
            "patterns": patterns or [],
            "ai_prompts": ai_prompts or {},
            "valid_entity_pairs": valid_entity_pairs or []
        }
        self._schemas[relation_type] = schema
    
    def get_patterns(self, relation_type: str) -> List[str]:
        """Get extraction patterns for relation"""
        return self._types.get(relation_type, {}).get("patterns", [])
    
    def get_predicate(self, relation_type: str) -> str:
        """Get predicate for relation type"""
        return self._types.get(relation_type, {}).get("predicate", relation_type.lower())
    
    def is_valid_pair(self, relation_type: str, subject_type: str, object_type: str) -> bool:
        """Check if entity pair is valid for this relation"""
        valid_pairs = self._types.get(relation_type, {}).get("valid_entity_pairs", [])
        if not valid_pairs:
            return True  # No restrictions
        return (subject_type, object_type) in valid_pairs
    
    def get_ai_prompts(self, relation_type: str) -> Dict[str, str]:
        """Get AI prompts for relation type"""
        return self._types.get(relation_type, {}).get("ai_prompts", {})


class AttributeTypeRegistry(TypeRegistry):
    """Registry for attribute types and their processing rules"""
    
    def register_type(self,
                     attribute_type: str,
                     schema: Dict[str, Any],
                     validation_rules: Dict[str, Any] = None,
                     normalization_rules: Dict[str, Any] = None,
                     ai_prompts: Dict[str, str] = None):
        """
        Register an attribute type
        
        Args:
            attribute_type: Type name (e.g., "AGE", "DOSAGE", "PRICE")
            schema: Schema defining this attribute type
            validation_rules: Rules for validating attribute values
            normalization_rules: Rules for normalizing values
            ai_prompts: Custom AI prompts for extraction
        """
        self._types[attribute_type] = {
            "validation_rules": validation_rules or {},
            "normalization_rules": normalization_rules or {},
            "ai_prompts": ai_prompts or {}
        }
        self._schemas[attribute_type] = schema
    
    def get_validation_rules(self, attribute_type: str) -> Dict[str, Any]:
        """Get validation rules for attribute type"""
        return self._types.get(attribute_type, {}).get("validation_rules", {})
    
    def get_normalization_rules(self, attribute_type: str) -> Dict[str, Any]:
        """Get normalization rules for attribute type"""  
        return self._types.get(attribute_type, {}).get("normalization_rules", {})