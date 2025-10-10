#!/usr/bin/env python3
"""
Neo4j Store

Focused Neo4j client for knowledge graph storage operations.
Handles storing entities, relations, and complete graphs with embeddings.
"""

from core.logging import get_logger
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import json
from datetime import datetime

from .neo4j_client import Neo4jClient
from tools.services.data_analytics_service.services.knowledge_service.graph_constructor import GraphConstructor
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator

logger = get_logger(__name__)

class Neo4jStore:
    """
    Neo4j storage client for knowledge graphs.
    
    Focused on storage operations: storing entities, relations, and complete graphs.
    Does not handle retrieval - that's handled by KnowledgeRetriever.
    """
    
    def __init__(self, neo4j_client: Neo4jClient):
        """Initialize store with Neo4j connection."""
        self.neo4j_client = neo4j_client
        self.graph_constructor = GraphConstructor()
        self.embedding_generator = EmbeddingGenerator()
            
    async def store_knowledge_graph(self, graph_data: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        """
        Store complete knowledge graph with embeddings in Neo4j.
        Includes entities, relations, document chunks, and attribute nodes.
        
        Args:
            graph_data: Graph data in Neo4j format from GraphConstructor.export_for_neo4j_storage()
            user_id: Optional user ID for isolation
            
        Returns:
            Storage statistics for all components
        """
        try:
            stored_entities = 0
            stored_relations = 0
            stored_documents = 0
            stored_attributes = 0
            
            # Store entities with embeddings
            for entity in graph_data.get("entities", []):
                try:
                    print(f"DEBUG: Storing entity: {entity['name']} (type: {entity['type']})")
                    result = await self.neo4j_client.store_entity(
                        name=entity["name"],
                        entity_type=entity["type"],
                        properties={
                            "canonical_form": entity["canonical_form"],
                            "confidence": entity["confidence"],
                            "source_document": entity.get("source_document", ""),
                            # Remove problematic attributes processing
                            # **{f"attr_{k}": v["value"] for k, v in entity.get("attributes", {}).items()}
                        },
                        embedding=entity["embedding"],
                        user_id=user_id
                    )
                    print(f"DEBUG: Entity storage result: {result}")
                    if result.get("success"):
                        stored_entities += 1
                    else:
                        print(f"DEBUG: Entity storage failed: {result}")
                except Exception as e:
                    logger.warning(f"Failed to store entity {entity.get('name', 'unknown')}: {e}")
            
            # Store relations with embeddings
            for relation in graph_data.get("relations", []):
                try:
                    # Find entity names from IDs (simplified mapping)
                    source_entity = next((e["name"] for e in graph_data["entities"] if e["id"] == relation["source_id"]), "unknown")
                    target_entity = next((e["name"] for e in graph_data["entities"] if e["id"] == relation["target_id"]), "unknown")
                    
                    await self.neo4j_client.store_relationship(
                        source_entity=source_entity,
                        target_entity=target_entity,
                        relationship_type=relation["type"],
                        properties={
                            "predicate": relation["predicate"],
                            "confidence": relation["confidence"],
                            "context": relation.get("context", "")
                        },
                        embedding=relation["embedding"],
                        user_id=user_id
                    )
                    stored_relations += 1
                except Exception as e:
                    logger.warning(f"Failed to store relation: {e}")
            
            # Store document chunks with embeddings (NEW)
            for document in graph_data.get("documents", []):
                try:
                    await self.neo4j_client.store_document_chunk(
                        chunk_id=document["id"],
                        text=document["text"],
                        properties={
                            "user_id": user_id,  # Add user_id for proper isolation
                            "chunk_index": document["chunk_index"],
                            "source_document": document["source_document"]
                        },
                        embedding=document["embedding"]
                    )
                    stored_documents += 1
                except Exception as e:
                    logger.warning(f"Failed to store document chunk {document.get('id', 'unknown')}: {e}")
            
            # Store attribute nodes with embeddings (NEW) - TEMPORARILY DISABLED
            # Attributes contain complex nested objects that Neo4j can't handle
            # TODO: Fix attribute data format to be Neo4j compatible
            stored_attributes = 0  # Skip attribute storage for now
            # for attribute in graph_data.get("attributes", []):
            #     try:
            #         await self.neo4j_client.store_attribute_node(
            #             attr_id=attribute["id"],
            #             entity_id=attribute["entity_id"],
            #             name=attribute["name"],
            #             value=attribute["value"],
            #             properties={
            #                 "type": attribute["type"],
            #                 "confidence": attribute["confidence"]
            #             },
            #             embedding=attribute["embedding"]
            #         )
            #         stored_attributes += 1
            #     except Exception as e:
            #         logger.warning(f"Failed to store attribute {attribute.get('id', 'unknown')}: {e}")
            
            return {
                "success": True,
                "nodes_created": stored_entities,
                "relationships_created": stored_relations,
                "processing_time": 0.1,  # Placeholder timing
                "entities_stored": stored_entities,
                "relations_stored": stored_relations,
                "documents_stored": stored_documents,
                "attributes_stored": stored_attributes,
                "total_entities": len(graph_data.get("entities", [])),
                "total_relations": len(graph_data.get("relations", [])),
                "total_documents": len(graph_data.get("documents", [])),
                "total_attributes": len(graph_data.get("attributes", []))
            }
            
        except Exception as e:
            logger.error(f"Knowledge graph storage failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "nodes_created": 0,
                "relationships_created": 0,
                "processing_time": 0,
                "entities_stored": 0,
                "relations_stored": 0,
                "documents_stored": 0,
                "attributes_stored": 0
            }

    async def extract_and_store_from_text(
        self,
        text: str,
        source_id: str,
        chunk_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract entities and relationships from text using GraphConstructor and store in graph.
        
        Args:
            text: Input text to process
            source_id: Identifier for the source document
            chunk_id: Optional chunk identifier
            
        Returns:
            Summary of extracted and stored data
        """
        try:
            logger.info(f"🧠 Starting text extraction and storage: {len(text):,} characters")
            
            # Use GraphConstructor to build complete graph with embeddings
            graph_data = await self.graph_constructor.construct_from_text(
                text=text,
                source_metadata={"source_id": source_id, "chunk_id": chunk_id}
            )
            
            # Export for Neo4j storage
            neo4j_data = self.graph_constructor.export_for_neo4j_storage(graph_data)
            
            # Store using our main storage method
            storage_result = await self.store_knowledge_graph(neo4j_data)
            
            # Add source tracking to result
            storage_result.update({
                "source_id": source_id,
                "chunk_id": chunk_id,
                "text_length": len(text)
            })
            
            return storage_result
            
        except Exception as e:
            logger.error(f"Text processing and storage failed: {e}")
            return {
                "entities_stored": 0,
                "relations_stored": 0,
                "documents_stored": 0,  # NEW
                "attributes_stored": 0,  # NEW
                "error": str(e),
                "source_id": source_id,
                "chunk_id": chunk_id
            }
            
    async def close(self):
        """Close the Neo4j connection."""
        await self.neo4j_client.close()


# Global store instance
_neo4j_store: Optional[Neo4jStore] = None

async def get_neo4j_store() -> Optional[Neo4jStore]:
    """Get or create the global Neo4j store instance."""
    global _neo4j_store
    
    if _neo4j_store is None:
        try:
            from .neo4j_client import get_neo4j_client
            neo4j_client = await get_neo4j_client()
            
            if neo4j_client:
                _neo4j_store = Neo4jStore(neo4j_client)
                logger.info("Neo4j store initialized successfully")
            else:
                logger.warning("Neo4j client not available, store not created")
                
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j store: {e}")
            
    return _neo4j_store