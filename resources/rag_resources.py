#!/usr/bin/env python3
"""
RAG Resources Implementation
Provides resource management for RAG services
"""

import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import weaviate
from sentence_transformers import SentenceTransformer

class RAGResource:
    """Resource manager for RAG operations"""
    
    def __init__(self):
        self.client = weaviate.Client(
            url=os.getenv("WEAVIATE_URL", "http://localhost:8080")
        )
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.model = SentenceTransformer(model_name)
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure required schema exists in Weaviate"""
        # Define the Document class if it doesn't exist
        if not self.client.schema.exists("Document"):
            class_obj = {
                "class": "Document",
                "description": "A document with vector embedding",
                "vectorizer": "text2vec-transformers",
                "moduleConfig": {
                    "text2vec-transformers": {
                        "vectorizeClassName": False
                    }
                },
                "properties": [
                    {
                        "name": "text",
                        "dataType": ["text"],
                        "description": "The document text",
                        "moduleConfig": {
                            "text2vec-transformers": {
                                "skip": False,
                                "vectorizePropertyName": False
                            }
                        }
                    },
                    {
                        "name": "metadata",
                        "dataType": ["object"],
                        "description": "Additional metadata"
                    },
                    {
                        "name": "source",
                        "dataType": ["text"],
                        "description": "Document source"
                    },
                    {
                        "name": "timestamp",
                        "dataType": ["date"],
                        "description": "When the document was added"
                    }
                ]
            }
            self.client.schema.create_class(class_obj)
    
    async def add_documents(self, documents: List[str], 
                          metadatas: Optional[List[Dict]] = None,
                          source: Optional[str] = None) -> Dict[str, Any]:
        """Add documents to the vector store"""
        try:
            # Prepare batch data
            with self.client.batch as batch:
                for i, doc in enumerate(documents):
                    # Create data object
                    data_object = {
                        "text": doc,
                        "timestamp": "2024-03-19T00:00:00Z"  # Use current time in production
                    }
                    
                    # Add metadata if provided
                    if metadatas and i < len(metadatas):
                        data_object["metadata"] = metadatas[i]
                    
                    # Add source if provided
                    if source:
                        data_object["source"] = source
                    
                    # Add to batch
                    batch.add_data_object(
                        data_object=data_object,
                        class_name="Document"
                    )
            
            return {
                "status": "success",
                "added_count": len(documents)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def search_similar(self, query: str, n_results: int = 5,
                           where_filter: Optional[Dict] = None) -> Dict[str, Any]:
        """Search for similar documents"""
        try:
            # Prepare query
            vector_query = {
                "concepts": [query]
            }
            
            # Build query
            query = (
                self.client.query
                .get("Document", ["text", "metadata", "source"])
                .with_near_text(vector_query)
                .with_limit(n_results)
            )
            
            # Add filter if provided
            if where_filter:
                query = query.with_where(where_filter)
            
            # Execute query
            result = query.do()
            
            # Extract results
            documents = []
            if "data" in result and "Get" in result["data"]:
                for item in result["data"]["Get"]["Document"]:
                    doc = {
                        "text": item["text"],
                        "metadata": item.get("metadata", {}),
                        "source": item.get("source")
                    }
                    if "_additional" in item:
                        doc["certainty"] = item["_additional"]["certainty"]
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
    
    async def delete_documents(self, where_filter: Optional[Dict] = None) -> Dict[str, Any]:
        """Delete documents from the vector store"""
        try:
            if where_filter:
                self.client.batch.delete_objects(
                    class_name="Document",
                    where=where_filter
                )
                status = "deleted_by_filter"
            else:
                # Delete all documents (use with caution)
                self.client.schema.delete_all()
                self._ensure_schema()
                status = "deleted_all"
            
            return {
                "status": status
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_embedding(self, text: str) -> Dict[str, Any]:
        """Generate embedding for text"""
        try:
            embedding = self.model.encode(text)
            return {
                "status": "success",
                "embedding": embedding.tolist(),
                "dimension": len(embedding)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

# Global instance
rag_resource = RAGResource() 