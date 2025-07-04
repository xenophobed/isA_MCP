#!/usr/bin/env python3
"""
Embedding Generation and Processing Utilities

Utilities for generating and working with embeddings in the graph analytics service.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import json

from core.logging import get_logger
from tools.base_service import BaseService

logger = get_logger(__name__)

class EmbeddingService(BaseService):
    """Service for generating and processing embeddings"""
    
    def __init__(self, model_name: str = "text-embedding-3-small"):
        """Initialize embedding service
        
        Args:
            model_name: Name of the embedding model to use
        """
        super().__init__("EmbeddingService")
        self.model_name = model_name
        self.cache = {}
        
    async def generate_embeddings(self, 
                                texts: List[str],
                                batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Check cache first
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for j, text in enumerate(batch):
                text_hash = hash(text)
                if text_hash in self.cache:
                    cached_embeddings.append((i + j, self.cache[text_hash]))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i + j)
            
            # Generate embeddings for uncached texts
            if uncached_texts:
                try:
                    response, billing_info = await self.call_isa_with_billing(
                        input_data=uncached_texts,
                        task="embed",
                        service_type="embedding",
                        parameters={"model": self.model_name},
                        operation_name="batch_embedding_generation"
                    )
                    
                    if 'embeddings' in response:
                        batch_embeddings = response['embeddings']
                        
                        # Cache new embeddings
                        for text, embedding in zip(uncached_texts, batch_embeddings):
                            self.cache[hash(text)] = embedding
                        
                        # Combine cached and new embeddings
                        all_batch_embeddings = [None] * len(batch)
                        
                        # Add cached embeddings
                        for idx, embedding in cached_embeddings:
                            all_batch_embeddings[idx - i] = embedding
                        
                        # Add new embeddings
                        for local_idx, embedding in zip(range(len(uncached_indices)), batch_embeddings):
                            global_idx = uncached_indices[local_idx]
                            all_batch_embeddings[global_idx - i] = embedding
                        
                        embeddings.extend(all_batch_embeddings)
                    else:
                        logger.error("Invalid response format from embedding API")
                        # Return zero embeddings for this batch
                        embeddings.extend([[0.0] * 1536] * len(batch))
                        
                except Exception as e:
                    logger.error(f"Failed to generate embeddings for batch: {e}")
                    # Return zero embeddings for failed batch
                    embeddings.extend([[0.0] * 1536] * len(batch))
            else:
                # All embeddings were cached
                batch_embeddings = [None] * len(batch)
                for idx, embedding in cached_embeddings:
                    batch_embeddings[idx - i] = embedding
                embeddings.extend(batch_embeddings)
        
        logger.info(f"Generated embeddings for {len(texts)} texts")
        return embeddings
    
    async def generate_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else [0.0] * 1536
    
    def calculate_similarity(self, 
                           embedding1: List[float], 
                           embedding2: List[float],
                           metric: str = "cosine") -> float:
        """
        Calculate similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            metric: Similarity metric ("cosine", "euclidean", "dot")
            
        Returns:
            Similarity score
        """
        if not embedding1 or not embedding2:
            return 0.0
        
        if len(embedding1) != len(embedding2):
            logger.warning("Embedding dimensions don't match")
            return 0.0
        
        arr1 = np.array(embedding1).reshape(1, -1)
        arr2 = np.array(embedding2).reshape(1, -1)
        
        if metric == "cosine":
            return float(cosine_similarity(arr1, arr2)[0, 0])
        elif metric == "euclidean":
            # Convert euclidean distance to similarity (0-1)
            distance = np.linalg.norm(arr1 - arr2)
            return 1 / (1 + distance)
        elif metric == "dot":
            return float(np.dot(arr1, arr2.T)[0, 0])
        else:
            raise ValueError(f"Unknown similarity metric: {metric}")
    
    def find_similar_embeddings(self, 
                               query_embedding: List[float],
                               candidate_embeddings: List[List[float]],
                               top_k: int = 10,
                               threshold: float = 0.7) -> List[Tuple[int, float]]:
        """
        Find most similar embeddings to a query embedding.
        
        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embeddings
            top_k: Number of top results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of (index, similarity_score) tuples
        """
        if not query_embedding or not candidate_embeddings:
            return []
        
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.calculate_similarity(query_embedding, candidate)
            if similarity >= threshold:
                similarities.append((i, similarity))
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def cluster_embeddings(self, 
                          embeddings: List[List[float]],
                          n_clusters: int = None,
                          method: str = "kmeans") -> Dict[str, Any]:
        """
        Cluster embeddings into groups.
        
        Args:
            embeddings: List of embedding vectors
            n_clusters: Number of clusters (auto-detect if None)
            method: Clustering method ("kmeans")
            
        Returns:
            Clustering results
        """
        if not embeddings:
            return {"labels": [], "centroids": [], "n_clusters": 0}
        
        embeddings_array = np.array(embeddings)
        
        # Auto-detect number of clusters if not specified
        if n_clusters is None:
            n_clusters = min(10, max(2, len(embeddings) // 10))
        
        if method == "kmeans":
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings_array)
            centroids = kmeans.cluster_centers_.tolist()
            
            return {
                "labels": labels.tolist(),
                "centroids": centroids,
                "n_clusters": n_clusters,
                "inertia": float(kmeans.inertia_)
            }
        else:
            raise ValueError(f"Unknown clustering method: {method}")
    
    def reduce_dimensions(self, 
                         embeddings: List[List[float]],
                         n_components: int = 2,
                         method: str = "pca") -> List[List[float]]:
        """
        Reduce dimensionality of embeddings for visualization.
        
        Args:
            embeddings: List of embedding vectors
            n_components: Number of dimensions to reduce to
            method: Dimensionality reduction method ("pca")
            
        Returns:
            Reduced embeddings
        """
        if not embeddings:
            return []
        
        embeddings_array = np.array(embeddings)
        
        if method == "pca":
            pca = PCA(n_components=n_components, random_state=42)
            reduced = pca.fit_transform(embeddings_array)
            
            logger.info(f"PCA explained variance ratio: {pca.explained_variance_ratio_}")
            return reduced.tolist()
        else:
            raise ValueError(f"Unknown dimensionality reduction method: {method}")
    
    def create_embedding_index(self, 
                              embeddings: List[List[float]],
                              metadata: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a searchable index of embeddings.
        
        Args:
            embeddings: List of embedding vectors
            metadata: Optional metadata for each embedding
            
        Returns:
            Embedding index structure
        """
        if not embeddings:
            return {"embeddings": [], "metadata": [], "index_type": "simple"}
        
        # For now, create a simple linear search index
        # In production, you might want to use Faiss or similar
        
        embedding_index = {
            "embeddings": embeddings,
            "metadata": metadata or [{} for _ in embeddings],
            "index_type": "simple",
            "size": len(embeddings),
            "dimension": len(embeddings[0]) if embeddings else 0
        }
        
        return embedding_index
    
    def search_index(self, 
                    index: Dict[str, Any],
                    query_embedding: List[float],
                    top_k: int = 10,
                    threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Search embedding index for similar vectors.
        
        Args:
            index: Embedding index created by create_embedding_index
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of search results with metadata
        """
        if not index or not index.get("embeddings") or not query_embedding:
            return []
        
        # Find similar embeddings
        similar_indices = self.find_similar_embeddings(
            query_embedding=query_embedding,
            candidate_embeddings=index["embeddings"],
            top_k=top_k,
            threshold=threshold
        )
        
        # Format results with metadata
        results = []
        for idx, similarity in similar_indices:
            result = {
                "index": idx,
                "similarity": similarity,
                "metadata": index["metadata"][idx] if idx < len(index["metadata"]) else {}
            }
            results.append(result)
        
        return results
    
    def save_embeddings(self, 
                       embeddings: List[List[float]],
                       filepath: str,
                       metadata: List[Dict[str, Any]] = None) -> bool:
        """
        Save embeddings to file.
        
        Args:
            embeddings: List of embedding vectors
            filepath: Path to save file
            metadata: Optional metadata for each embedding
            
        Returns:
            True if successful
        """
        try:
            data = {
                "embeddings": embeddings,
                "metadata": metadata or [],
                "model_name": self.model_name,
                "timestamp": str(datetime.now()),
                "size": len(embeddings),
                "dimension": len(embeddings[0]) if embeddings else 0
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(embeddings)} embeddings to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
            return False
    
    def load_embeddings(self, filepath: str) -> Dict[str, Any]:
        """
        Load embeddings from file.
        
        Args:
            filepath: Path to embedding file
            
        Returns:
            Loaded embedding data
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Loaded {len(data.get('embeddings', []))} embeddings from {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            return {"embeddings": [], "metadata": []}

# Global embedding service instance
_embedding_service = None

def get_embedding_service(model_name: str = "text-embedding-3-small") -> EmbeddingService:
    """Get or create the global embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service

# Convenience functions
async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts"""
    service = get_embedding_service()
    return await service.generate_embeddings(texts)

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    service = get_embedding_service()
    return service.calculate_similarity(embedding1, embedding2)

def cluster_embeddings(embeddings: List[List[float]], n_clusters: int = None) -> Dict[str, Any]:
    """Cluster embeddings into groups"""
    service = get_embedding_service()
    return service.cluster_embeddings(embeddings, n_clusters)

def reduce_dimensions(embeddings: List[List[float]], n_components: int = 2) -> List[List[float]]:
    """Reduce dimensionality of embeddings"""
    service = get_embedding_service()
    return service.reduce_dimensions(embeddings, n_components)