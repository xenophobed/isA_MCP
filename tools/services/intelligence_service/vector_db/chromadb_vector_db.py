#!/usr/bin/env python3
"""
ChromaDB Vector Database Implementation

Integration of the existing ChromaDB service into the unified vector database abstraction layer.
"""

from typing import List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime

from .base_vector_db import BaseVectorDB, SearchResult, VectorSearchConfig, SearchMode

logger = logging.getLogger(__name__)

class ChromaVectorDB(BaseVectorDB):
    """
    ChromaDB implementation integrated with the vector database abstraction layer.
    
    Wraps the existing ChromaService to provide a unified interface.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ChromaDB vector database.
        
        Args:
            config: Configuration including collection settings
        """
        super().__init__(config)
        
        self.collection_name = self.config.get('collection_name', 'default_collection')
        self.embedding_model = self.config.get('embedding_model', 'all-MiniLM-L6-v2')
        self.cleanup_interval = self.config.get('cleanup_interval_minutes', 30)
        self.collection_ttl = self.config.get('collection_ttl_minutes', 120)
        
        # Initialize ChromaDB directly without deprecated service
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Initialize ChromaDB client directly
            self.chroma_client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=None  # Pure in-memory mode
            ))
            
            # Create default collection if it doesn't exist
            try:
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={'created_by': 'vector_db_abstraction', 'embedding_model': self.embedding_model}
                )
            except Exception:
                # Collection might already exist, get it
                try:
                    self.collection = self.chroma_client.get_collection(name=self.collection_name)
                except Exception:
                    # If still fails, create with unique name
                    import uuid
                    self.collection_name = f"{self.collection_name}_{uuid.uuid4().hex[:8]}"
                    self.collection = self.chroma_client.create_collection(
                        name=self.collection_name,
                        metadata={'created_by': 'vector_db_abstraction'}
                    )
                
            self.logger.info(f"ChromaVectorDB initialized with collection: {self.collection_name}")
            
        except ImportError as e:
            self.logger.error(f"ChromaDB not available: {e}")
            raise ImportError("ChromaDB dependencies missing. Install with: pip install chromadb")
    
    async def store_vector(
        self,
        id: str,
        text: str,
        embedding: List[float],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store a vector in ChromaDB."""
        try:
            # Prepare metadata with user isolation
            full_metadata = {
                'user_id': user_id,
                'stored_at': datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # Add document directly to ChromaDB collection
            self.collection.add(
                ids=[id],
                documents=[text],
                metadatas=[full_metadata],
                embeddings=[embedding]  # Use provided embedding
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing vector {id}: {e}")
            return False
    
    async def search_vectors(
        self,
        query_embedding: List[float],
        user_id: str,
        config: VectorSearchConfig
    ) -> List[SearchResult]:
        """Search vectors using ChromaDB semantic search."""
        try:
            # Direct embedding query with ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=config.top_k * 2,  # Get more for user filtering
                include=["documents", "metadatas", "distances", "embeddings"]
            )
            
            if not results or not results.get('documents'):
                return []
            
            # Filter by user_id and convert to SearchResult objects
            search_results = []
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            ids = results.get('ids', [[]])[0]
            embeddings = results.get('embeddings', [[]])[0] if results.get('embeddings') else []
            
            for i, (doc, metadata, distance, doc_id) in enumerate(zip(documents, metadatas, distances, ids)):
                if metadata and metadata.get('user_id') == user_id:
                    # Convert distance to similarity score (ChromaDB uses L2 distance)
                    similarity = 1.0 / (1.0 + distance) if distance > 0 else 1.0
                    
                    search_result = SearchResult(
                        id=doc_id,
                        text=doc,
                        score=similarity,
                        semantic_score=similarity,
                        metadata=metadata,
                        embedding=embeddings[i] if i < len(embeddings) else None
                    )
                    search_results.append(search_result)
            
            # Sort by score and return top_k
            search_results.sort(key=lambda x: x.score, reverse=True)
            return search_results[:config.top_k]
            
        except Exception as e:
            self.logger.error(f"Vector search failed for user {user_id}: {e}")
            # Fallback to text-based search
            return await self.search_text("", user_id, config)
    
    async def search_text(
        self,
        query_text: str,
        user_id: str,
        config: VectorSearchConfig
    ) -> List[SearchResult]:
        """Search text using ChromaDB query."""
        try:
            # Direct text query with ChromaDB
            results = self.collection.query(
                query_texts=[query_text],
                n_results=config.top_k * 2,  # Get more for filtering
                include=["documents", "metadatas", "distances"]
            )
            
            if not results or not results.get('documents'):
                return []
            
            # Filter results by user_id
            search_results = []
            
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            ids = results.get('ids', [[]])[0]
            
            for doc, metadata, distance, doc_id in zip(documents, metadatas, distances, ids):
                if metadata.get('user_id') == user_id:
                    # Convert distance to similarity score
                    similarity = 1.0 / (1.0 + distance) if distance > 0 else 1.0
                    
                    search_result = SearchResult(
                        id=doc_id,
                        text=doc,
                        score=similarity,
                        lexical_score=similarity,
                        metadata=metadata
                    )
                    search_results.append(search_result)
            
            return search_results[:config.top_k]
            
        except Exception as e:
            self.logger.error(f"Text search failed for user {user_id}: {e}")
            return []
    
    async def delete_vector(self, id: str, user_id: str) -> bool:
        """Delete a vector by ID."""
        try:
            # First verify the vector belongs to the user
            vector = await self.get_vector(id, user_id)
            if not vector:
                self.logger.warning(f"Vector {id} not found or doesn't belong to user {user_id}")
                return False
            
            # Delete from ChromaDB collection
            self.collection.delete(ids=[id])
            
            self.logger.info(f"Deleted vector {id} for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting vector {id}: {e}")
            return False
    
    async def get_vector(self, id: str, user_id: str) -> Optional[SearchResult]:
        """Get a specific vector by ID."""
        try:
            # Get document by ID from ChromaDB
            results = self.collection.get(
                ids=[id],
                include=["documents", "metadatas", "embeddings"]
            )
            
            if not results or not results.get('documents'):
                return None
            
            documents = results.get('documents', [])
            metadatas = results.get('metadatas', [])
            embeddings = results.get('embeddings', [])
            
            if not documents or len(documents) == 0:
                return None
            
            doc = documents[0]
            metadata = metadatas[0] if metadatas else {}
            embedding = embeddings[0] if embeddings else None
            
            # Verify user ownership
            if metadata.get('user_id') != user_id:
                self.logger.warning(f"Vector {id} doesn't belong to user {user_id}")
                return None
            
            return SearchResult(
                id=id,
                text=doc,
                score=1.0,  # Perfect match score
                semantic_score=1.0,
                metadata=metadata,
                embedding=embedding
            )
            
        except Exception as e:
            self.logger.error(f"Error getting vector {id}: {e}")
            return None
    
    async def list_vectors(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[SearchResult]:
        """List vectors for a user."""
        try:
            # ChromaDB doesn't have direct pagination, so we'll get all and filter
            # Get all documents (this could be optimized for large collections)
            results = self.collection.get(
                include=["documents", "metadatas", "embeddings"]
            )
            
            if not results or not results.get('documents'):
                return []
            
            # Filter by user and apply pagination
            user_vectors = []
            documents = results.get('documents', [])
            metadatas = results.get('metadatas', [])
            ids = results.get('ids', [])
            embeddings = results.get('embeddings', [])
            
            for i, (doc, metadata, doc_id) in enumerate(zip(documents, metadatas, ids)):
                if metadata and metadata.get('user_id') == user_id:
                    embedding = embeddings[i] if i < len(embeddings) else None
                    
                    search_result = SearchResult(
                        id=doc_id,
                        text=doc,
                        score=1.0,
                        semantic_score=1.0,
                        metadata=metadata,
                        embedding=embedding
                    )
                    user_vectors.append(search_result)
            
            # Apply pagination
            start_idx = offset
            end_idx = offset + limit
            return user_vectors[start_idx:end_idx]
            
        except Exception as e:
            self.logger.error(f"Error listing vectors for user {user_id}: {e}")
            return []
    
    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            # Get basic ChromaDB stats
            collection_count = self.collection.count()
            
            stats = {
                'database_type': 'chromadb',
                'collection_name': self.collection_name,
                'embedding_model': self.embedding_model,
                'total_vectors': collection_count,
                'chromadb_available': True
            }
            
            if user_id:
                stats['user_id'] = user_id
                # Would need to implement user-specific stats
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {'error': str(e), 'database_type': 'chromadb'}