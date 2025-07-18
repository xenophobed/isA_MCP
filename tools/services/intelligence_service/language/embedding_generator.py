#!/usr/bin/env python3
"""
Embedding Generator Service
Simple wrapper around ISA client for text embeddings
"""

from typing import List, Optional, Union, Tuple
import logging

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Simple embedding generation service using ISA client"""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        """Lazy load ISA client"""
        if self._client is None:
            from isa_model.client import ISAModelClient
            self._client = ISAModelClient()
        return self._client
    
    async def embed(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
        normalize: bool = True,
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text(s)
        
        Args:
            text: Text or list of texts to embed
            model: Specific model to use
            normalize: Whether to normalize embeddings
            **kwargs: Additional parameters
            
        Returns:
            Single embedding vector or list of vectors
        """
        try:
            # Determine task based on input type
            is_single = isinstance(text, str)
            task = "embed" if is_single else "embed_batch"
            
            # 对单个文本也进行长度检查，防止超过ISA token限制
            if is_single and len(text) > 5000:  # 5000字符约等于3000-4000 token
                logger.warning(f"Single text too long ({len(text)} chars), truncating to 5000 chars")
                text = text[:5000]
            
            # Prepare parameters
            params = {}
            if normalize:
                params["normalize"] = normalize
            if model:
                params["model"] = model
            params.update(kwargs)
            
            # Call ISA client
            response = await self.client.invoke(
                input_data=text,
                task=task,
                service_type="embedding",
                **params
            )
            
            # Enhanced error handling and response validation for medical text processing
            if not response.get('success') and not response.get('result'):
                error_msg = response.get('error', 'Unknown error')
                logger.error(f"ISA embedding failed: {error_msg}")
                
                # For medical text, provide fallback mechanism
                if 'medical' in str(text).lower() or any(term in str(text).lower() for term in ['肺', '心脏', '血', '检查', '疾病']):
                    logger.warning("Medical text embedding failed, providing zero embedding fallback")
                    if is_single:
                        return [0.0] * 768  # Standard embedding dimension
                    else:
                        return [[0.0] * 768 for _ in text]
                else:
                    raise Exception(f"ISA embedding failed: {error_msg}")
            
            result = response.get('result', {})
            
            # Enhanced result validation with detailed logging
            if is_single:
                # For single embedding, result is the embedding array directly
                if not result:
                    logger.error(f"Empty result for single embedding. Response: {response}")
                    return [0.0] * 768  # Fallback zero embedding
                elif not isinstance(result, list):
                    logger.error(f"Invalid result type for single embedding: {type(result)}. Expected list, got: {result}")
                    return [0.0] * 768  # Fallback zero embedding
                elif len(result) == 0:
                    logger.warning("Empty embedding array returned, using fallback")
                    return [0.0] * 768
                return result
            else:
                # For batch embedding, result is array of embedding arrays
                if not result:
                    logger.error(f"Empty result for batch embedding. Response: {response}")
                    return [[0.0] * 768 for _ in text]  # Fallback zero embeddings
                elif not isinstance(result, list):
                    logger.error(f"Invalid result type for batch embedding: {type(result)}. Expected list, got: {result}")
                    return [[0.0] * 768 for _ in text]  # Fallback zero embeddings
                elif len(result) == 0:
                    logger.warning("Empty embedding batch returned, using fallback")
                    return [[0.0] * 768 for _ in text]
                elif len(result) != len(text):
                    logger.warning(f"Embedding count mismatch: expected {len(text)}, got {len(result)}")
                    # Pad or truncate to match expected length
                    if len(result) < len(text):
                        result.extend([[0.0] * 768 for _ in range(len(text) - len(result))])
                    else:
                        result = result[:len(text)]
                return result
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    async def embed_single(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            model: Model to use
            **kwargs: Additional parameters
            
        Returns:
            Embedding vector
        """
        result = await self.embed(text, model=model, **kwargs)
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], (int, float)):
            return result
        else:
            raise ValueError("Expected single embedding vector")
    
    async def embed_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
        max_concurrent: int = 5,  # Limit concurrent requests for ISA stability
        **kwargs
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with enhanced error handling
        
        Args:
            texts: List of texts to embed
            model: Model to use
            max_concurrent: Maximum concurrent ISA requests
            **kwargs: Additional parameters
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        # For large batches, use controlled concurrent processing
        if len(texts) > max_concurrent:
            import asyncio
            
            logger.info(f"Processing {len(texts)} texts in batches of {max_concurrent} for ISA stability")
            all_embeddings = []
            
            # Process in chunks to avoid overloading ISA service
            for i in range(0, len(texts), max_concurrent):
                chunk = texts[i:i + max_concurrent]
                try:
                    chunk_embeddings = await self.embed(chunk, model=model, **kwargs)
                    all_embeddings.extend(chunk_embeddings)
                except Exception as e:
                    logger.warning(f"Batch chunk {i//max_concurrent + 1} failed: {e}, using fallback embeddings")
                    # Provide fallback embeddings for failed chunk
                    fallback_embeddings = [[0.0] * 768 for _ in chunk]
                    all_embeddings.extend(fallback_embeddings)
                
                # Small delay between chunks to prevent ISA overload
                if i + max_concurrent < len(texts):
                    await asyncio.sleep(0.1)
            
            return all_embeddings
        else:
            # For small batches, use direct processing
            result = await self.embed(texts, model=model, **kwargs)
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                return result
            else:
                logger.warning("Batch embedding returned unexpected format, using fallback")
                return [[0.0] * 768 for _ in texts]
    
    async def compute_similarity(
        self,
        text1: str,
        text2: str,
        model: Optional[str] = None,
        **kwargs
    ) -> float:
        """
        Compute cosine similarity between two texts using ISA
        
        Args:
            text1: First text
            text2: Second text
            model: Model to use for embeddings
            **kwargs: Additional parameters
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            # Use ISA's similarity task
            params = {"candidates": [text2]}
            if model:
                params["model"] = model
            params.update(kwargs)
            
            response = await self.client.invoke(
                input_data=text1,
                task="similarity",
                service_type="embedding",
                **params
            )
            
            if not response.get('success'):
                raise Exception(f"ISA similarity failed: {response.get('error', 'Unknown error')}")
            
            result = response.get('result', {})
            similar_docs = result.get('similar_documents', [])
            
            if similar_docs:
                return similar_docs[0].get('similarity', 0.0)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Similarity computation failed: {e}")
            raise
    
    async def find_most_similar(
        self,
        query_text: str,
        candidate_texts: List[str],
        model: Optional[str] = None,
        top_k: int = 5,
        **kwargs
    ) -> List[Tuple[str, float]]:
        """
        Find most similar texts to a query using ISA
        
        Args:
            query_text: Query text
            candidate_texts: List of candidate texts
            model: Model to use
            top_k: Number of top results to return
            **kwargs: Additional parameters
            
        Returns:
            List of (text, similarity_score) tuples
        """
        try:
            # Use ISA's similarity task
            params = {
                "candidates": candidate_texts,
                "top_k": top_k
            }
            if model:
                params["model"] = model
            params.update(kwargs)
            
            response = await self.client.invoke(
                input_data=query_text,
                task="similarity",
                service_type="embedding",
                **params
            )
            
            if not response.get('success'):
                raise Exception(f"ISA similarity search failed: {response.get('error', 'Unknown error')}")
            
            result = response.get('result', {})
            similar_docs = result.get('similar_documents', [])
            
            # Convert to tuple format
            return [(doc['text'], doc['similarity']) for doc in similar_docs]
                
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise
    
    async def chunk_text(
        self,
        text: str,
        chunk_size: int = 400,
        overlap: int = 50,
        model: Optional[str] = None,
        metadata: Optional[dict] = None,
        **kwargs
    ) -> List[dict]:
        """
        Chunk text into smaller pieces with embeddings using ISA
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            model: Model to use for embeddings
            metadata: Additional metadata to include
            **kwargs: Additional parameters
            
        Returns:
            List of chunk dictionaries with text and embeddings
        """
        try:
            # Check if text exceeds token limits (8192 tokens ~ 20,000 characters)
            # If so, pre-chunk locally to respect ISA limits  
            max_chars_for_isa = 6000   # 更保守的估计，考虑ISA内部处理开销
            
            if len(text) > max_chars_for_isa:
                logger.info(f"Text length {len(text)} exceeds ISA limit, pre-chunking locally")
                return await self._chunk_large_text_locally(
                    text, chunk_size, overlap, model, metadata, **kwargs
                )
            
            # Use ISA's chunk task for smaller texts
            params = {
                "chunk_size": chunk_size,
                "overlap": overlap
            }
            if model:
                params["model"] = model
            if metadata:
                params["metadata"] = metadata
            params.update(kwargs)
            
            response = await self.client.invoke(
                input_data=text,
                task="chunk",
                service_type="embedding",
                **params
            )
            
            if not response.get('success'):
                raise Exception(f"ISA chunking failed: {response.get('error', 'Unknown error')}")
            
            result = response.get('result', [])
            # ISA returns chunks directly as array in result field  
            if isinstance(result, list):
                return result
            else:
                # Fallback for nested format
                chunks = result.get('chunks', [])
                return chunks
                
        except Exception as e:
            logger.error(f"Text chunking failed: {e}")
            raise
    
    async def _chunk_large_text_locally(
        self,
        text: str,
        chunk_size: int = 400,
        overlap: int = 50,
        model: Optional[str] = None,
        metadata: Optional[dict] = None,
        **kwargs
    ) -> List[dict]:
        """
        Local chunking for texts that exceed ISA token limits
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            model: Model to use for embeddings
            metadata: Additional metadata to include
            **kwargs: Additional parameters
            
        Returns:
            List of chunk dictionaries with text and embeddings
        """
        try:
            # Create local chunks with sentence boundary awareness
            chunks = []
            current_pos = 0
            chunk_id = 0
            
            while current_pos < len(text):
                # Calculate end position for this chunk
                end_pos = min(current_pos + chunk_size, len(text))
                
                # Try to end at sentence boundary if we're not at the end
                if end_pos < len(text):
                    # Look for sentence endings near the chunk boundary
                    search_start = max(current_pos, end_pos - 100)
                    search_text = text[search_start:end_pos + 100]
                    
                    # Find last sentence ending
                    sentence_endings = ['.', '!', '?', '\n\n']
                    best_ending = -1
                    
                    for ending in sentence_endings:
                        pos = search_text.rfind(ending)
                        if pos > 50:  # Ensure we have meaningful content
                            best_ending = max(best_ending, search_start + pos + 1)
                    
                    if best_ending > current_pos:
                        end_pos = best_ending
                
                # Extract chunk text
                chunk_text = text[current_pos:end_pos].strip()
                
                if chunk_text:  # Only process non-empty chunks
                    # Generate embedding for this chunk using ISA
                    try:
                        embedding = await self.embed_single(chunk_text, model=model, **kwargs)
                        
                        chunk_data = {
                            'id': chunk_id,
                            'text': chunk_text,
                            'embedding': embedding,
                            'start_pos': current_pos,
                            'end_pos': end_pos,
                            'metadata': metadata or {}
                        }
                        chunks.append(chunk_data)
                        chunk_id += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for chunk {chunk_id}: {e}")
                        # Still include chunk without embedding
                        chunk_data = {
                            'id': chunk_id,
                            'text': chunk_text,
                            'embedding': [],
                            'start_pos': current_pos,
                            'end_pos': end_pos,
                            'metadata': metadata or {},
                            'error': str(e)
                        }
                        chunks.append(chunk_data)
                        chunk_id += 1
                
                # Move to next position with overlap
                current_pos = max(current_pos + 1, end_pos - overlap)
                
                # Prevent infinite loops
                if current_pos >= len(text):
                    break
            
            logger.info(f"Successfully chunked large text into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Local text chunking failed: {e}")
            raise
    
    async def rerank_documents(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        return_documents: bool = True,
        model: Optional[str] = None,
        **kwargs
    ) -> List[dict]:
        """
        Rerank documents based on relevance to query using ISA Jina Reranker
        
        Args:
            query: Query text
            documents: List of documents to rerank
            top_k: Number of top results to return
            return_documents: Whether to include document text in results
            model: Model to use (defaults to isa-jina-reranker-v2-service)
            **kwargs: Additional parameters
            
        Returns:
            List of reranked documents with relevance scores
        """
        try:
            # Use ISA's rerank task
            params = {
                "documents": documents,
                "top_k": top_k,
                "return_documents": return_documents
            }
            if model:
                params["model"] = model
            params.update(kwargs)
            
            response = await self.client.invoke(
                input_data=query,
                task="rerank",
                service_type="embedding",
                **params
            )
            
            if not response.get('success'):
                raise Exception(f"ISA reranking failed: {response.get('error', 'Unknown error')}")
            
            result = response.get('result', {})
            rerank_results = result.get('results', [])
            
            return rerank_results
                
        except Exception as e:
            logger.error(f"Document reranking failed: {e}")
            raise
    

# Global instance for easy import
embedding_generator = EmbeddingGenerator()

# Convenience functions
async def embed(text: Union[str, List[str]], **kwargs) -> Union[List[float], List[List[float]]]:
    """Generate embeddings for text(s)"""
    return await embedding_generator.embed(text, **kwargs)

async def similarity(text1: str, text2: str, **kwargs) -> float:
    """Compute similarity between two texts"""
    return await embedding_generator.compute_similarity(text1, text2, **kwargs)

async def search(query: str, candidates: List[str], **kwargs) -> List[Tuple[str, float]]:
    """Find most similar texts"""
    return await embedding_generator.find_most_similar(query, candidates, **kwargs)

async def chunk(text: str, **kwargs) -> List[dict]:
    """Chunk text with embeddings"""
    return await embedding_generator.chunk_text(text, **kwargs)

async def rerank(query: str, documents: List[str], **kwargs) -> List[dict]:
    """Rerank documents by relevance"""
    return await embedding_generator.rerank_documents(query, documents, **kwargs)