#!/usr/bin/env python3
"""
GraphRAG Resources Implementation
Provides resource management for Graph-based RAG services
"""

import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import spacy
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

class GraphRAGResource:
    """Resource manager for GraphRAG operations"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "your_password")
            )
        )
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.model = SentenceTransformer(model_name)
        self.nlp = spacy.load("en_core_web_sm")
        self._ensure_constraints()
    
    def _ensure_constraints(self):
        """Ensure required constraints and indexes exist in Neo4j"""
        with self.driver.session() as session:
            # Create constraints
            session.run("""
                CREATE CONSTRAINT document_id IF NOT EXISTS
                FOR (d:Document) REQUIRE d.id IS UNIQUE
            """)
            
            session.run("""
                CREATE CONSTRAINT entity_text IF NOT EXISTS
                FOR (e:Entity) REQUIRE e.text IS UNIQUE
            """)
            
            # Create vector index for documents
            session.run("""
                CALL db.index.vector.createNodeIndex(
                    'document_embeddings',
                    'Document',
                    'embedding',
                    384,
                    'cosine'
                )
            """)
    
    async def add_document(self, text: str, metadata: Optional[Dict] = None,
                         extract_entities: bool = True) -> Dict[str, Any]:
        """Add a document with graph structure"""
        try:
            # Generate document embedding
            embedding = self.model.encode(text).tolist()
            
            with self.driver.session() as session:
                # Create document node
                doc_result = session.write_transaction(
                    lambda tx: tx.run(
                        """
                        CREATE (d:Document {
                            text: $text,
                            embedding: $embedding,
                            metadata: $metadata,
                            timestamp: datetime()
                        })
                        RETURN id(d) as node_id
                        """,
                        text=text,
                        embedding=embedding,
                        metadata=metadata or {}
                    ).single()
                )
                
                doc_id = doc_result["node_id"]
                entity_count = 0
                
                if extract_entities:
                    # Process text with spaCy
                    doc = self.nlp(text)
                    
                    # Extract and create entities
                    for ent in doc.ents:
                        # Create or merge entity node
                        entity_result = session.write_transaction(
                            lambda tx: tx.run(
                                """
                                MERGE (e:Entity {text: $text})
                                ON CREATE SET 
                                    e.type = $type,
                                    e.embedding = $embedding
                                RETURN id(e) as node_id
                                """,
                                text=ent.text,
                                type=ent.label_,
                                embedding=self.model.encode(ent.text).tolist()
                            ).single()
                        )
                        
                        # Create relationship
                        session.write_transaction(
                            lambda tx: tx.run(
                                """
                                MATCH (d:Document), (e:Entity)
                                WHERE id(d) = $doc_id AND id(e) = $entity_id
                                CREATE (d)-[r:HAS_ENTITY {
                                    start: $start,
                                    end: $end
                                }]->(e)
                                """,
                                doc_id=doc_id,
                                entity_id=entity_result["node_id"],
                                start=ent.start_char,
                                end=ent.end_char
                            )
                        )
                        entity_count += 1
            
            return {
                "status": "success",
                "document_id": doc_id,
                "entity_count": entity_count
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def search_similar(self, query: str, n_results: int = 5,
                           include_related: bool = True,
                           max_hops: int = 2) -> Dict[str, Any]:
        """Search for similar content using graph structure"""
        try:
            # Generate query embedding
            query_embedding = self.model.encode(query).tolist()
            
            with self.driver.session() as session:
                # Vector similarity search
                results = session.run(
                    """
                    CALL db.index.vector.queryNodes(
                        'document_embeddings',
                        $k,
                        $embedding
                    )
                    YIELD node, score
                    RETURN 
                        node.text as text,
                        node.metadata as metadata,
                        score,
                        id(node) as node_id
                    """,
                    k=n_results,
                    embedding=query_embedding
                ).data()
                
                documents = []
                for item in results:
                    doc = {
                        "text": item["text"],
                        "metadata": item["metadata"],
                        "score": item["score"]
                    }
                    
                    if include_related:
                        # Get related nodes
                        related = session.run(
                            """
                            MATCH (d:Document)-[r:HAS_ENTITY]->(e:Entity)
                            WHERE id(d) = $node_id
                            WITH e, r
                            MATCH (e)<-[r2:HAS_ENTITY]-(d2:Document)
                            WHERE d2 <> d
                            RETURN DISTINCT
                                d2.text as text,
                                d2.metadata as metadata,
                                e.text as entity,
                                e.type as entity_type
                            LIMIT 5
                            """,
                            node_id=item["node_id"]
                        ).data()
                        
                        doc["related"] = related
                    
                    documents.append(doc)
                
                return {
                    "status": "success",
                    "results": documents,
                    "count": len(documents)
                }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def delete_document(self, doc_id: int) -> Dict[str, Any]:
        """Delete a document and its relationships"""
        try:
            with self.driver.session() as session:
                session.write_transaction(
                    lambda tx: tx.run(
                        """
                        MATCH (d:Document)
                        WHERE id(d) = $doc_id
                        DETACH DELETE d
                        """,
                        doc_id=doc_id
                    )
                )
                
                return {
                    "status": "success",
                    "document_id": doc_id
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_graph_context(self, doc_id: int, max_hops: int = 2) -> Dict[str, Any]:
        """Get graph context for a document"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (d:Document)
                    WHERE id(d) = $doc_id
                    CALL apoc.path.subgraphNodes(d, {
                        maxLevel: $max_hops,
                        relationshipFilter: 'HAS_ENTITY'
                    })
                    YIELD node
                    RETURN 
                        CASE 
                            WHEN node:Document THEN 'document'
                            WHEN node:Entity THEN 'entity'
                        END as type,
                        node.text as text,
                        node.metadata as metadata,
                        id(node) as node_id
                    """,
                    doc_id=doc_id,
                    max_hops=max_hops
                ).data()
                
                return {
                    "status": "success",
                    "context": result
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

# Global instance
graph_rag_resource = GraphRAGResource() 