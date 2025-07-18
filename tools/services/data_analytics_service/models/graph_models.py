#!/usr/bin/env python3
"""
Graph Models for Analytics Service

Comprehensive models for graph entities, relationships, and operations.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class GraphEntityType(Enum):
    """Graph entity types"""
    PERSON = "person"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    DOCUMENT = "document"
    EVENT = "event"
    LOCATION = "location"
    PRODUCT = "product"
    TOPIC = "topic"
    UNKNOWN = "unknown"

class GraphRelationshipType(Enum):
    """Graph relationship types"""
    CONTAINS = "contains"
    RELATES_TO = "relates_to"
    PART_OF = "part_of"
    SIMILAR_TO = "similar_to"
    MENTIONS = "mentions"
    CREATED_BY = "created_by"
    LOCATED_IN = "located_in"
    WORKS_FOR = "works_for"
    CUSTOM = "custom"

class GraphQueryType(Enum):
    """Graph query types"""
    ENTITY_SEARCH = "entity_search"
    RELATIONSHIP_SEARCH = "relationship_search"
    PATH_FINDING = "path_finding"
    NEIGHBORHOOD = "neighborhood"
    SIMILARITY = "similarity"
    SEMANTIC = "semantic"
    CYPHER = "cypher"

@dataclass
class GraphEntity:
    """Graph entity model"""
    id: str
    name: str
    type: GraphEntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    embeddings: Optional[List[float]] = None
    confidence: float = 1.0
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate entity data"""
        if not self.id or not self.name:
            raise ValueError("Entity must have id and name")
        
        # Ensure confidence is between 0 and 1
        self.confidence = max(0.0, min(1.0, self.confidence))

@dataclass
class GraphRelationship:
    """Graph relationship model"""
    id: str
    source_id: str
    target_id: str
    type: GraphRelationshipType
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    confidence: float = 1.0
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate relationship data"""
        if not self.id or not self.source_id or not self.target_id:
            raise ValueError("Relationship must have id, source_id, and target_id")
        
        # Ensure weight and confidence are valid
        self.weight = max(0.0, self.weight)
        self.confidence = max(0.0, min(1.0, self.confidence))

@dataclass
class GraphQuery:
    """Graph query model"""
    query: str
    query_type: GraphQueryType
    parameters: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: Optional[int] = None
    include_embeddings: bool = False
    include_metadata: bool = True
    request_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class GraphResult:
    """Graph query result model"""
    request_id: str
    success: bool
    entities: List[GraphEntity] = field(default_factory=list)
    relationships: List[GraphRelationship] = field(default_factory=list)
    paths: List[List[str]] = field(default_factory=list)
    total_count: Optional[int] = None
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class GraphSchema:
    """Graph schema definition"""
    name: str
    entity_types: List[Dict[str, Any]] = field(default_factory=list)
    relationship_types: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_entity_type_names(self) -> List[str]:
        """Get list of entity type names"""
        return [et['name'] for et in self.entity_types if 'name' in et and et['name']]
    
    def get_relationship_type_names(self) -> List[str]:
        """Get list of relationship type names"""
        return [rt['name'] for rt in self.relationship_types if 'name' in rt and rt['name']]

@dataclass
class KnowledgeGraph:
    """Knowledge graph model"""
    name: str
    schema: GraphSchema
    entities: List[GraphEntity] = field(default_factory=list)
    relationships: List[GraphRelationship] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get_entity_count(self) -> int:
        """Get total number of entities"""
        return len(self.entities)
    
    def get_relationship_count(self) -> int:
        """Get total number of relationships"""
        return len(self.relationships)
    
    def get_entity_by_id(self, entity_id: str) -> Optional[GraphEntity]:
        """Get entity by ID"""
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None
    
    def get_relationships_for_entity(self, entity_id: str) -> List[GraphRelationship]:
        """Get all relationships for an entity"""
        return [
            rel for rel in self.relationships
            if rel.source_id == entity_id or rel.target_id == entity_id
        ]
    
    def update_statistics(self):
        """Update graph statistics"""
        self.statistics = {
            'total_entities': self.get_entity_count(),
            'total_relationships': self.get_relationship_count(),
            'entity_types': {},
            'relationship_types': {},
            'updated_at': datetime.now().isoformat()
        }
        
        # Count entity types
        for entity in self.entities:
            entity_type = entity.type.value
            self.statistics['entity_types'][entity_type] = \
                self.statistics['entity_types'].get(entity_type, 0) + 1
        
        # Count relationship types
        for relationship in self.relationships:
            rel_type = relationship.type.value
            self.statistics['relationship_types'][rel_type] = \
                self.statistics['relationship_types'].get(rel_type, 0) + 1
        
        self.updated_at = datetime.now() 