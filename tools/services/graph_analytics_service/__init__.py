#!/usr/bin/env python3
"""
Graph Analytics Service

A comprehensive service for extracting entities, relationships, and attributes 
from text and storing them in Neo4j graph database with vector support for GraphRAG.

Components:
- Entity, Relation, Attribute extraction from text
- Neo4j Aura integration with vector support
- GraphRAG query capabilities
- Vector similarity search
- Knowledge graph construction and querying
"""

from .core.entity_extractor import EntityExtractor
from .core.relation_extractor import RelationExtractor
from .core.attribute_extractor import AttributeExtractor
from .core.graph_constructor import GraphConstructor
from .services.neo4j_graphrag_client import Neo4jGraphRAGClient, get_neo4j_graphrag_client
from .services.graphrag_retriever import GraphRAGRetriever
from .services.knowledge_graph import KnowledgeGraph

__all__ = [
    "EntityExtractor",
    "RelationExtractor", 
    "AttributeExtractor",
    "GraphConstructor",
    "Neo4jGraphRAGClient",
    "get_neo4j_graphrag_client",
    "GraphRAGRetriever",
    "KnowledgeGraph"
]

__version__ = "1.0.0"