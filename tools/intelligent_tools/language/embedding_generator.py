#!/usr/bin/env python3
"""
Embedding Generator Service
Simple wrapper around ISA client for text embeddings
"""

from typing import List, Optional, Union, Tuple, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Simple embedding generation service using ISA client"""

    def __init__(self):
        self._client = None

    async def _get_client(self):
        """Lazy load ISA client with optional authentication"""
        if self._client is None:
            from core.clients.model_client import get_isa_client

            self._client = await get_isa_client()
        return self._client

    async def embed(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
        normalize: bool = True,
        **kwargs,
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
                logger.warning(
                    f"Single text too long ({len(text)} chars), truncating to 5000 chars"
                )
                text = text[:5000]

            # Prepare parameters
            params = {}
            if normalize:
                params["normalize"] = normalize
            # Use text-embedding-3-small by default for 1536 dimensions
            params["model"] = model or "text-embedding-3-small"
            params.update(kwargs)

            # Call ISA client using the standard embeddings API
            client = await self._get_client()

            # Use the OpenAI-compatible embeddings interface
            response_obj = await client.embeddings.create(
                input=text,  # Works for both single string and list of strings
                model=params.get("model", "text-embedding-3-small"),
            )

            # Extract embeddings from the response
            if is_single:
                return response_obj.data[0].embedding
            else:
                return [item.embedding for item in response_obj.data]

            # Enhanced error handling and response validation for medical text processing
            if not response.get("success") and not response.get("result"):
                error_msg = response.get("error", "Unknown error")
                logger.error(f"ISA embedding failed: {error_msg}")

                # For medical text, provide fallback mechanism
                if "medical" in str(text).lower() or any(
                    term in str(text).lower() for term in ["肺", "心脏", "血", "检查", "疾病"]
                ):
                    logger.warning(
                        "Medical text embedding failed, providing zero embedding fallback"
                    )
                    if is_single:
                        return [0.0] * 1536  # text-embedding-3-small dimension
                    else:
                        return [[0.0] * 1536 for _ in text]
                else:
                    raise Exception(f"ISA embedding failed: {error_msg}")

            result = response.get("result", {})

            # Enhanced result validation with detailed logging
            if is_single:
                # For single embedding, result is the embedding array directly
                if not result:
                    logger.error(f"Empty result for single embedding. Response: {response}")
                    return [0.0] * 1536  # Fallback zero embedding
                elif not isinstance(result, list):
                    logger.error(
                        f"Invalid result type for single embedding: {type(result)}. Expected list, got: {result}"
                    )
                    return [0.0] * 1536  # Fallback zero embedding
                elif len(result) == 0:
                    logger.warning("Empty embedding array returned, using fallback")
                    return [0.0] * 1536
                return result
            else:
                # For batch embedding, result is array of embedding arrays
                if not result:
                    logger.error(f"Empty result for batch embedding. Response: {response}")
                    return [[0.0] * 1536 for _ in text]  # Fallback zero embeddings
                elif not isinstance(result, list):
                    logger.error(
                        f"Invalid result type for batch embedding: {type(result)}. Expected list, got: {result}"
                    )
                    return [[0.0] * 1536 for _ in text]  # Fallback zero embeddings
                elif len(result) == 0:
                    logger.warning("Empty embedding batch returned, using fallback")
                    return [[0.0] * 1536 for _ in text]
                elif len(result) != len(text):
                    logger.warning(
                        f"Embedding count mismatch: expected {len(text)}, got {len(result)}"
                    )
                    # Pad or truncate to match expected length
                    if len(result) < len(text):
                        result.extend([[0.0] * 1536 for _ in range(len(text) - len(result))])
                    else:
                        result = result[: len(text)]
                return result

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def embed_single(self, text: str, model: Optional[str] = None, **kwargs) -> List[float]:
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
        **kwargs,
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

            logger.info(
                f"Processing {len(texts)} texts in batches of {max_concurrent} for ISA stability"
            )
            all_embeddings = []

            # Process in chunks to avoid overloading ISA service
            for i in range(0, len(texts), max_concurrent):
                chunk = texts[i : i + max_concurrent]
                try:
                    chunk_embeddings = await self.embed(chunk, model=model, **kwargs)
                    all_embeddings.extend(chunk_embeddings)
                except Exception as e:
                    logger.warning(
                        f"Batch chunk {i//max_concurrent + 1} failed: {e}, using fallback embeddings"
                    )
                    # Provide fallback embeddings for failed chunk
                    fallback_embeddings = [[0.0] * 1536 for _ in chunk]
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
                return [[0.0] * 1536 for _ in texts]

    async def compute_similarity(
        self, text1: str, text2: str, model: Optional[str] = None, **kwargs
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

            client = await self._get_client()

            response = await client._underlying_client.invoke(
                input_data=text1, task="similarity", service_type="embedding", **params
            )

            if not response.get("success"):
                raise Exception(f"ISA similarity failed: {response.get('error', 'Unknown error')}")

            result = response.get("result", {})
            similar_docs = result.get("similar_documents", [])

            if similar_docs:
                return similar_docs[0].get("similarity", 0.0)
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
        **kwargs,
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
            params = {"candidates": candidate_texts, "top_k": top_k}
            if model:
                params["model"] = model
            params.update(kwargs)

            client = await self._get_client()

            response = await client._underlying_client.invoke(
                input_data=query_text, task="similarity", service_type="embedding", **params
            )

            if not response.get("success"):
                raise Exception(
                    f"ISA similarity search failed: {response.get('error', 'Unknown error')}"
                )

            result = response.get("result", {})
            similar_docs = result.get("similar_documents", [])

            # Convert to tuple format
            return [(doc["text"], doc["similarity"]) for doc in similar_docs]

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
        strategy: Optional[str] = None,
        **kwargs,
    ) -> List[dict]:
        """
        Chunk text into smaller pieces with embeddings

        Now supports advanced chunking strategies via the new ChunkingService.

        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            model: Model to use for embeddings
            metadata: Additional metadata to include
            strategy: Chunking strategy to use (e.g., 'recursive', 'semantic', 'markdown_aware')
            **kwargs: Additional parameters

        Returns:
            List of chunk dictionaries with text and embeddings
        """
        try:
            # If strategy specified, use new ChunkingService
            if strategy:
                from tools.services.intelligence_service.vector_db.chunking_service import (
                    chunking_service,
                    ChunkingStrategy,
                )

                logger.info(f"Using advanced chunking strategy: {strategy}")

                # Create chunks using the new service
                chunks = await chunking_service.chunk_text(
                    text=text,
                    strategy=strategy,
                    chunk_size=chunk_size,
                    chunk_overlap=overlap,
                    metadata=metadata,
                    **kwargs,
                )

                # Generate embeddings for chunks
                chunk_texts = [chunk.text for chunk in chunks]
                embeddings = await self.embed_batch(chunk_texts, model=model)

                # Convert to expected format
                result = []
                for chunk, embedding in zip(chunks, embeddings):
                    chunk_dict = chunk.to_dict()
                    chunk_dict["embedding"] = embedding
                    result.append(chunk_dict)

                return result

            # Otherwise, use original ISA-based or local chunking
            # Check if text exceeds token limits (8192 tokens ~ 20,000 characters)
            # If so, pre-chunk locally to respect ISA limits
            max_chars_for_isa = 6000  # 更保守的估计，考虑ISA内部处理开销

            if len(text) > max_chars_for_isa:
                logger.info(f"Text length {len(text)} exceeds ISA limit, pre-chunking locally")
                return await self._chunk_large_text_locally(
                    text, chunk_size, overlap, model, metadata, **kwargs
                )

            # Always use local chunking with embedding generation
            # ISA's "chunk" task returns embeddings only, not text chunks
            logger.info(f"Using local chunking for text length {len(text)}")
            return await self._chunk_large_text_locally(
                text, chunk_size, overlap, model, metadata, **kwargs
            )

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
        **kwargs,
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
                    search_text = text[search_start : end_pos + 100]

                    # Find last sentence ending
                    sentence_endings = [".", "!", "?", "\n\n"]
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
                            "id": chunk_id,
                            "text": chunk_text,
                            "embedding": embedding,
                            "start_pos": current_pos,
                            "end_pos": end_pos,
                            "metadata": metadata or {},
                        }
                        chunks.append(chunk_data)
                        chunk_id += 1

                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for chunk {chunk_id}: {e}")
                        # Still include chunk without embedding
                        chunk_data = {
                            "id": chunk_id,
                            "text": chunk_text,
                            "embedding": [],
                            "start_pos": current_pos,
                            "end_pos": end_pos,
                            "metadata": metadata or {},
                            "error": str(e),
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
        provider: str = "isa",
        **kwargs,
    ) -> List[dict]:
        """
        Rerank documents based on relevance to query using ISA Jina Reranker

        Args:
            query: Query text
            documents: List of documents to rerank
            top_k: Number of top results to return
            return_documents: Whether to include document text in results
            model: Model to use (defaults to isa-jina-reranker-v2-service)
            provider: Provider to use (defaults to isa)
            **kwargs: Additional parameters

        Returns:
            List of reranked documents with relevance scores
        """
        try:
            # Use ISA's rerank task with correct parameters
            client = await self._get_client()

            response = await client._underlying_client.invoke(
                input_data=query,
                task="rerank",
                service_type="embedding",
                model=model or "isa-jina-reranker-v2-service",
                provider=provider,
                documents=documents,
                top_k=top_k,
                **kwargs,
            )

            if not response.get("success"):
                raise Exception(f"ISA reranking failed: {response.get('error', 'Unknown error')}")

            result = response.get("result", {})
            rerank_results = result.get("results", [])

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


async def advanced_chunk(
    text: str, strategy: str = "hybrid", chunk_size: int = 1000, chunk_overlap: int = 100, **kwargs
) -> List[dict]:
    """
    Advanced chunking with multiple strategies

    Available strategies:
    - fixed_size: Simple fixed-size chunks
    - sentence_based: Chunk by sentences
    - recursive: Recursively split with multiple separators
    - markdown_aware: Preserve Markdown structure
    - code_aware: Preserve code structure
    - semantic: Chunk based on semantic similarity
    - token_based: Chunk by token count
    - hierarchical: Create parent-child chunk relationships
    - hybrid: Automatically detect and apply best strategy

    Args:
        text: Text to chunk
        strategy: Chunking strategy to use
        chunk_size: Target size for chunks
        chunk_overlap: Overlap between chunks
        **kwargs: Additional strategy-specific parameters

    Returns:
        List of chunk dictionaries with embeddings
    """
    return await embedding_generator.chunk_text(
        text=text, strategy=strategy, chunk_size=chunk_size, overlap=chunk_overlap, **kwargs
    )


async def rerank(query: str, documents: List[str], **kwargs) -> List[dict]:
    """Rerank documents by relevance"""
    return await embedding_generator.rerank_documents(
        query, documents, model="isa-jina-reranker-v2-service", provider="isa", **kwargs
    )


# ===== NEW HYBRID SEARCH FUNCTIONALITY =====


async def hybrid_search_local(
    query_text: str,
    user_id: str,
    top_k: int = 5,
    search_mode: str = "hybrid",  # "semantic", "lexical", "hybrid"
    ranking_method: str = "rrf",  # "rrf", "weighted", "mmr"
    semantic_weight: float = 0.7,
    lexical_weight: float = 0.3,
    **kwargs,
) -> List[dict]:
    """
    Perform hybrid search using local vector database.

    This is the new enhanced search method that combines:
    - Semantic search via vector embeddings
    - Lexical search via BM25/full-text
    - Advanced result fusion algorithms

    Args:
        query_text: Search query
        user_id: User identifier for isolation
        top_k: Number of results to return
        search_mode: "semantic", "lexical", or "hybrid"
        ranking_method: "rrf", "weighted", or "mmr"
        semantic_weight: Weight for semantic scores (0-1)
        lexical_weight: Weight for lexical scores (0-1)
        **kwargs: Additional parameters

    Returns:
        List of search results with scores and metadata
    """
    try:
        from tools.services.intelligence_service.vector_db.hybrid_search_service import (
            hybrid_search_service,
        )
        from tools.services.intelligence_service.vector_db.base_vector_db import (
            VectorSearchConfig,
            SearchMode,
            RankingMethod,
        )

        # Generate embedding for the query
        query_embedding = await embedding_generator.embed_single(query_text)

        # Configure search parameters
        search_mode_enum = {
            "semantic": SearchMode.SEMANTIC,
            "lexical": SearchMode.LEXICAL,
            "hybrid": SearchMode.HYBRID,
        }.get(search_mode, SearchMode.HYBRID)

        ranking_method_enum = {
            "rrf": RankingMethod.RRF,
            "weighted": RankingMethod.WEIGHTED,
            "mmr": RankingMethod.MMR,
        }.get(ranking_method, RankingMethod.RRF)

        config = VectorSearchConfig(
            top_k=top_k,
            search_mode=search_mode_enum,
            ranking_method=ranking_method_enum,
            semantic_weight=semantic_weight,
            lexical_weight=lexical_weight,
            include_embeddings=kwargs.get("include_embeddings", False),
        )

        # Perform hybrid search
        search_result = await hybrid_search_service.hybrid_search(
            query_text=query_text,
            query_embedding=query_embedding,
            user_id=user_id,
            search_config=config,
        )

        if not search_result.get("success"):
            logger.warning(f"Hybrid search failed: {search_result.get('error')}")
            return []

        # Convert SearchResult objects to dictionaries for backward compatibility
        results = []
        for search_result_obj in search_result.get("results", []):
            result_dict = {
                "id": search_result_obj.id,
                "text": search_result_obj.text,
                "score": search_result_obj.score,
                "semantic_score": search_result_obj.semantic_score,
                "lexical_score": search_result_obj.lexical_score,
                "metadata": search_result_obj.metadata or {},
                "method": search_result.get("method", "local_hybrid"),
            }

            if kwargs.get("include_embeddings") and search_result_obj.embedding:
                result_dict["embedding"] = search_result_obj.embedding

            results.append(result_dict)

        logger.info(
            f"Hybrid search returned {len(results)} results using {search_result.get('method')}"
        )
        return results

    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        # Fallback to ISA search if local search fails
        return await _fallback_to_isa_search(query_text, user_id, top_k, **kwargs)


async def _fallback_to_isa_search(
    query_text: str, user_id: str, top_k: int = 5, **kwargs
) -> List[dict]:
    """
    Fallback to ISA search when local search fails.

    This maintains backward compatibility with the original search behavior.
    """
    try:
        # This would require getting user's knowledge base first
        # For now, return empty results as fallback
        logger.warning("Falling back to ISA search - not implemented yet")
        return []

    except Exception as e:
        logger.error(f"ISA fallback search failed: {e}")
        return []


async def store_knowledge_local(
    user_id: str, text: str, metadata: Optional[dict] = None, **kwargs
) -> dict:
    """
    Store knowledge in local vector database.

    This complements the existing RAG service by providing direct access
    to the vector database layer.

    Args:
        user_id: User identifier
        text: Text content to store
        metadata: Additional metadata
        **kwargs: Additional parameters

    Returns:
        Storage result dictionary
    """
    try:
        from tools.services.intelligence_service.vector_db.hybrid_search_service import (
            hybrid_search_service,
        )
        import uuid

        # Generate embedding for the text
        embedding = await embedding_generator.embed_single(text)

        # Generate unique ID
        knowledge_id = str(uuid.uuid4())

        # Store in vector database
        result = await hybrid_search_service.store_knowledge(
            id=knowledge_id, text=text, embedding=embedding, user_id=user_id, metadata=metadata
        )

        return {
            "success": result.get("success", False),
            "id": knowledge_id,
            "user_id": user_id,
            "text_length": len(text),
            "embedding_dimensions": len(embedding),
            "method": result.get("method", "local_db"),
            "error": result.get("error"),
        }

    except Exception as e:
        logger.error(f"Error storing knowledge locally: {e}")
        return {"success": False, "error": str(e), "method": "local_db"}


# Enhanced search function that automatically chooses the best method
async def enhanced_search(
    query_text: str,
    user_id: str,
    candidates: Optional[List[str]] = None,
    top_k: int = 5,
    search_mode: str = "hybrid",
    use_local_db: bool = True,
    **kwargs,
) -> List[dict]:
    """
    Enhanced search function that automatically chooses the best search method.

    This function provides intelligent routing between:
    1. Local hybrid search (preferred for stored knowledge)
    2. ISA search with candidates (for ad-hoc searches)
    3. Fallback mechanisms

    Args:
        query_text: Search query
        user_id: User identifier
        candidates: Optional list of candidate texts for ISA search
        top_k: Number of results to return
        search_mode: "semantic", "lexical", or "hybrid"
        use_local_db: Whether to try local database first
        **kwargs: Additional parameters

    Returns:
        List of search results
    """
    try:
        # Strategy 1: Try local hybrid search first if enabled
        if use_local_db and not candidates:
            local_results = await hybrid_search_local(
                query_text=query_text,
                user_id=user_id,
                top_k=top_k,
                search_mode=search_mode,
                **kwargs,
            )

            if local_results:
                logger.debug(f"Enhanced search using local database: {len(local_results)} results")
                return local_results

        # Strategy 2: Use ISA search with candidates
        if candidates:
            isa_results = await search(query_text, candidates, top_k=top_k, **kwargs)

            # Convert ISA results to enhanced format
            enhanced_results = []
            for text, similarity_score in isa_results:
                enhanced_results.append(
                    {
                        "id": f"isa_{hash(text)}",
                        "text": text,
                        "score": similarity_score,
                        "semantic_score": similarity_score,
                        "lexical_score": None,
                        "metadata": {},
                        "method": "isa_candidates",
                    }
                )

            logger.debug(
                f"Enhanced search using ISA with candidates: {len(enhanced_results)} results"
            )
            return enhanced_results

        # Strategy 3: Try local search anyway (might have some results)
        if use_local_db:
            local_results = await hybrid_search_local(
                query_text=query_text,
                user_id=user_id,
                top_k=top_k,
                search_mode="semantic",  # Fall back to semantic only
                **kwargs,
            )

            if local_results:
                logger.debug(
                    f"Enhanced search fallback to local semantic: {len(local_results)} results"
                )
                return local_results

        # No results found
        logger.info("Enhanced search found no results")
        return []

    except Exception as e:
        logger.error(f"Enhanced search failed: {e}")
        return []


# Backward compatibility functions
async def search_enhanced(query: str, candidates: List[str], **kwargs) -> List[Tuple[str, float]]:
    """Enhanced version of the original search function with hybrid capabilities."""
    try:
        # Try to determine user_id from kwargs or use default
        user_id = kwargs.get("user_id", "default")

        # Use enhanced search
        results = await enhanced_search(
            query_text=query, user_id=user_id, candidates=candidates, **kwargs
        )

        # Convert back to original format for compatibility
        return [(result["text"], result["score"]) for result in results]

    except Exception as e:
        logger.error(f"Enhanced search fallback to original: {e}")
        # Fallback to original implementation
        return await search(query, candidates, **kwargs)


# ===== ENHANCED RERANKING WITH MMR =====


async def mmr_rerank(
    query: str,
    documents: List[str],
    query_embedding: Optional[List[float]] = None,
    document_embeddings: Optional[List[List[float]]] = None,
    lambda_param: float = 0.5,
    top_k: int = 5,
    **kwargs,
) -> List[dict]:
    """
    Advanced reranking using Max Marginal Relevance (MMR) for diversity.

    This function combines relevance with diversity to reduce redundancy
    in search results, providing more comprehensive and useful result sets.

    Args:
        query: Query text
        documents: List of documents to rerank
        query_embedding: Pre-computed query embedding (optional)
        document_embeddings: Pre-computed document embeddings (optional)
        lambda_param: Balance between relevance (1.0) and diversity (0.0)
        top_k: Number of results to return
        **kwargs: Additional parameters

    Returns:
        List of reranked documents with MMR scores
    """
    try:
        from tools.services.intelligence_service.vector_db.mmr_reranker import mmr_reranker
        from tools.services.intelligence_service.vector_db.base_vector_db import SearchResult

        # Generate embeddings if not provided
        if not query_embedding:
            query_embedding = await embedding_generator.embed_single(query)

        if not document_embeddings:
            document_embeddings = await embedding_generator.embed_batch(documents)

        # Calculate initial relevance scores (cosine similarity)
        search_results = []
        for i, (doc, embedding) in enumerate(zip(documents, document_embeddings)):
            if embedding:
                similarity = mmr_reranker._cosine_similarity(query_embedding, embedding)

                search_result = SearchResult(
                    id=f"doc_{i}",
                    text=doc,
                    score=similarity,
                    semantic_score=similarity,
                    embedding=embedding,
                )
                search_results.append(search_result)

        # Apply MMR reranking
        mmr_results = mmr_reranker.rerank_results(
            search_results=search_results, target_count=top_k, lambda_param=lambda_param
        )

        # Convert back to dictionary format
        reranked_docs = []
        for result in mmr_results:
            reranked_docs.append(
                {
                    "document": result.text,
                    "text": result.text,  # For compatibility
                    "relevance_score": result.score,
                    "score": result.score,  # For compatibility
                    "original_score": result.semantic_score,
                    "mmr_lambda": lambda_param,
                    "rank": len(reranked_docs) + 1,
                }
            )

        logger.info(
            f"MMR reranking: {len(documents)} → {len(reranked_docs)} results, λ={lambda_param}"
        )
        return reranked_docs

    except Exception as e:
        logger.error(f"MMR reranking failed: {e}")
        # Fallback to regular reranking
        return await rerank(query, documents, top_k=top_k, **kwargs)


async def advanced_rerank(
    query: str,
    documents: List[str],
    method: str = "mmr",  # "mmr", "isa", "combined"
    lambda_param: float = 0.5,
    top_k: int = 5,
    **kwargs,
) -> List[dict]:
    """
    Advanced reranking with multiple algorithms.

    Supports different reranking strategies:
    - MMR: Max Marginal Relevance for diversity
    - ISA: Use ISA Jina reranker
    - Combined: Use both and ensemble the results

    Args:
        query: Query text
        documents: Documents to rerank
        method: Reranking method ("mmr", "isa", "combined")
        lambda_param: MMR lambda parameter
        top_k: Number of results
        **kwargs: Additional parameters

    Returns:
        Reranked documents
    """
    try:
        if method == "mmr":
            return await mmr_rerank(
                query=query, documents=documents, lambda_param=lambda_param, top_k=top_k, **kwargs
            )

        elif method == "isa":
            return await rerank(query, documents, top_k=top_k, **kwargs)

        elif method == "combined":
            # Run both methods and ensemble
            mmr_results = await mmr_rerank(
                query=query,
                documents=documents,
                lambda_param=lambda_param,
                top_k=top_k * 2,  # Get more for ensemble
                **kwargs,
            )

            isa_results = await rerank(query, documents, top_k=top_k * 2, **kwargs)

            # Simple ensemble: average scores
            combined_scores = {}

            # Add MMR scores
            for result in mmr_results:
                doc_text = result["text"]
                combined_scores[doc_text] = {
                    "mmr_score": result["score"],
                    "isa_score": 0.0,
                    "text": doc_text,
                }

            # Add ISA scores
            for result in isa_results:
                doc_text = result.get("document", result.get("text", ""))
                if doc_text in combined_scores:
                    combined_scores[doc_text]["isa_score"] = result.get(
                        "relevance_score", result.get("score", 0.0)
                    )
                else:
                    combined_scores[doc_text] = {
                        "mmr_score": 0.0,
                        "isa_score": result.get("relevance_score", result.get("score", 0.0)),
                        "text": doc_text,
                    }

            # Calculate ensemble scores
            ensemble_results = []
            for doc_text, scores in combined_scores.items():
                ensemble_score = (scores["mmr_score"] + scores["isa_score"]) / 2

                ensemble_results.append(
                    {
                        "document": doc_text,
                        "text": doc_text,
                        "relevance_score": ensemble_score,
                        "score": ensemble_score,
                        "mmr_score": scores["mmr_score"],
                        "isa_score": scores["isa_score"],
                        "method": "ensemble",
                    }
                )

            # Sort by ensemble score and return top_k
            ensemble_results.sort(key=lambda x: x["score"], reverse=True)
            return ensemble_results[:top_k]

        else:
            logger.warning(f"Unknown reranking method: {method}, falling back to ISA")
            return await rerank(query, documents, top_k=top_k, **kwargs)

    except Exception as e:
        logger.error(f"Advanced reranking failed: {e}")
        return await rerank(query, documents, top_k=top_k, **kwargs)


# Convenience function for backward compatibility
async def rerank_with_diversity(
    query: str, documents: List[str], diversity_weight: float = 0.3, **kwargs
) -> List[dict]:
    """
    Rerank documents with diversity optimization.

    Args:
        query: Query text
        documents: Documents to rerank
        diversity_weight: Weight for diversity (0-1)
        **kwargs: Additional parameters

    Returns:
        Reranked documents with diversity
    """
    # Convert diversity_weight to MMR lambda (inverse relationship)
    lambda_param = 1.0 - diversity_weight

    return await mmr_rerank(query=query, documents=documents, lambda_param=lambda_param, **kwargs)


# ===== ENHANCED PARALLEL FILE PROCESSING =====


async def process_large_files_parallel(
    file_paths: List[str],
    user_id: str,
    max_workers: int = 4,
    chunk_size: int = 1000,
    overlap_size: int = 100,
    file_types: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Process large files in parallel with advanced chunking and error handling.

    Supports:
    - PDF documents (multi-page processing)
    - Large text files (memory-efficient streaming)
    - Multiple file formats
    - Parallel processing with controlled concurrency
    - Progress tracking and resume capability

    Args:
        file_paths: List of file paths to process
        user_id: User identifier for isolation
        max_workers: Maximum parallel workers
        chunk_size: Size of text chunks in characters
        overlap_size: Overlap between chunks
        file_types: Allowed file types (auto-detect if None)
        **kwargs: Additional processing parameters

    Returns:
        Processing results with detailed statistics
    """
    try:
        import asyncio
        import os
        from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
        from pathlib import Path

        start_time = datetime.now()

        # Validate input files
        valid_files = []
        invalid_files = []

        for file_path in file_paths:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                file_ext = Path(file_path).suffix.lower()

                # Check file type if specified
                if file_types and file_ext not in file_types:
                    invalid_files.append(
                        {"path": file_path, "reason": f"Unsupported file type: {file_ext}"}
                    )
                    continue

                # Check file size (max 500MB per file)
                max_size = kwargs.get("max_file_size_mb", 500) * 1024 * 1024
                if file_size > max_size:
                    invalid_files.append(
                        {
                            "path": file_path,
                            "reason": f"File too large: {file_size / 1024 / 1024:.1f}MB",
                        }
                    )
                    continue

                valid_files.append({"path": file_path, "size": file_size, "ext": file_ext})
            else:
                invalid_files.append(
                    {"path": file_path, "reason": "File not found or not accessible"}
                )

        if not valid_files:
            return {
                "success": False,
                "error": "No valid files to process",
                "invalid_files": invalid_files,
                "total_files": len(file_paths),
            }

        logger.info(f"Processing {len(valid_files)} valid files with {max_workers} workers")

        # Create semaphore for controlling concurrency
        semaphore = asyncio.Semaphore(max_workers)

        # Process files in parallel
        async def process_file_with_semaphore(file_info):
            async with semaphore:
                return await _process_single_large_file(
                    file_info, user_id, chunk_size, overlap_size, **kwargs
                )

        # Start processing tasks
        tasks = [process_file_with_semaphore(file_info) for file_info in valid_files]

        # Process with progress tracking
        if kwargs.get("show_progress", True):
            completed_results = []
            for i, task in enumerate(asyncio.as_completed(tasks)):
                result = await task
                completed_results.append(result)
                logger.info(f"Completed {i + 1}/{len(tasks)}: {result.get('file_name', 'unknown')}")
        else:
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_files = []
        failed_files = []
        total_chunks = 0
        total_processing_time = 0

        for i, result in enumerate(completed_results):
            if isinstance(result, Exception):
                failed_files.append({"file": valid_files[i]["path"], "error": str(result)})
            elif result.get("success", False):
                successful_files.append(result)
                total_chunks += result.get("total_chunks", 0)
                total_processing_time += result.get("processing_time_seconds", 0)
            else:
                failed_files.append(
                    {"file": valid_files[i]["path"], "error": result.get("error", "Unknown error")}
                )

        overall_time = (datetime.now() - start_time).total_seconds()

        return {
            "success": True,
            "total_files_submitted": len(file_paths),
            "valid_files": len(valid_files),
            "invalid_files": len(invalid_files),
            "successful_files": len(successful_files),
            "failed_files": len(failed_files),
            "total_chunks_created": total_chunks,
            "total_processing_time_seconds": total_processing_time,
            "overall_time_seconds": overall_time,
            "average_time_per_file": (
                total_processing_time / len(successful_files) if successful_files else 0
            ),
            "parallel_efficiency": (
                (total_processing_time / overall_time) if overall_time > 0 else 0
            ),
            "results": successful_files,
            "failures": failed_files,
            "invalid_file_details": invalid_files,
            "processing_stats": {
                "max_workers": max_workers,
                "chunk_size": chunk_size,
                "overlap_size": overlap_size,
                "user_id": user_id,
            },
        }

    except Exception as e:
        logger.error(f"Parallel file processing failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_files_submitted": len(file_paths) if file_paths else 0,
        }


async def _process_single_large_file(
    file_info: Dict[str, Any], user_id: str, chunk_size: int, overlap_size: int, **kwargs
) -> Dict[str, Any]:
    """Process a single large file with memory-efficient streaming"""
    try:
        import asyncio
        from pathlib import Path

        file_path = file_info["path"]
        file_ext = file_info.get("ext", "")
        file_name = Path(file_path).name

        start_time = datetime.now()

        logger.info(f"Processing file: {file_name} ({file_info['size'] / 1024 / 1024:.1f}MB)")

        # Extract text based on file type
        if file_ext == ".pdf":
            text_content = await _extract_pdf_text_parallel(file_path, **kwargs)
        elif file_ext in [".txt", ".md", ".rst"]:
            text_content = await _extract_text_file_streaming(file_path, **kwargs)
        elif file_ext in [".doc", ".docx"]:
            text_content = await _extract_word_document(file_path, **kwargs)
        else:
            # Try as plain text
            text_content = await _extract_text_file_streaming(file_path, **kwargs)

        if not text_content or len(text_content.strip()) < 50:
            return {
                "success": False,
                "file_name": file_name,
                "file_path": file_path,
                "error": "No extractable text content found",
            }

        # Generate chunks with embeddings
        chunks_data = await embedding_generator.chunk_text(
            text=text_content,
            chunk_size=chunk_size,
            overlap=overlap_size,
            metadata={
                "source_file": file_name,
                "file_path": file_path,
                "file_size": file_info["size"],
                "processed_at": datetime.now().isoformat(),
                "user_id": user_id,
            },
        )

        # Store chunks in vector database
        stored_chunks = []
        storage_errors = []

        for i, chunk in enumerate(chunks_data):
            try:
                store_result = await store_knowledge_local(
                    user_id=user_id, text=chunk.get("text", ""), metadata=chunk.get("metadata", {})
                )

                if store_result.get("success"):
                    stored_chunks.append(
                        {
                            "chunk_id": i,
                            "storage_id": store_result.get("id"),
                            "text_length": len(chunk.get("text", "")),
                            "embedding_dimensions": store_result.get("embedding_dimensions", 0),
                        }
                    )
                else:
                    storage_errors.append(
                        {"chunk_id": i, "error": store_result.get("error", "Unknown storage error")}
                    )

            except Exception as e:
                storage_errors.append({"chunk_id": i, "error": str(e)})

        processing_time = (datetime.now() - start_time).total_seconds()

        return {
            "success": len(stored_chunks) > 0,
            "file_name": file_name,
            "file_path": file_path,
            "file_size_mb": file_info["size"] / 1024 / 1024,
            "text_length": len(text_content),
            "total_chunks": len(chunks_data),
            "stored_chunks": len(stored_chunks),
            "storage_errors": len(storage_errors),
            "processing_time_seconds": processing_time,
            "chunks_per_second": len(chunks_data) / processing_time if processing_time > 0 else 0,
            "storage_success_rate": len(stored_chunks) / len(chunks_data) if chunks_data else 0,
            "chunk_details": stored_chunks,
            "error_details": storage_errors if storage_errors else None,
        }

    except Exception as e:
        logger.error(f"Failed to process file {file_info.get('path', 'unknown')}: {e}")
        return {
            "success": False,
            "file_name": Path(file_info.get("path", "unknown")).name,
            "file_path": file_info.get("path"),
            "error": str(e),
        }


async def _extract_pdf_text_parallel(file_path: str, **kwargs) -> str:
    """Extract text from PDF with parallel page processing"""
    try:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        # Try different PDF libraries
        try:
            import PyPDF2

            pdf_lib = "pypdf2"
        except ImportError:
            try:
                import pdfplumber

                pdf_lib = "pdfplumber"
            except ImportError:
                try:
                    import fitz  # PyMuPDF

                    pdf_lib = "pymupdf"
                except ImportError:
                    logger.error(
                        "No PDF library available. Install: pip install PyPDF2 or pdfplumber or PyMuPDF"
                    )
                    return ""

        max_pages = kwargs.get("max_pdf_pages", 500)  # Limit for very large PDFs

        def extract_pdf_text_sync():
            if pdf_lib == "pypdf2":
                return _extract_with_pypdf2(file_path, max_pages)
            elif pdf_lib == "pdfplumber":
                return _extract_with_pdfplumber(file_path, max_pages)
            elif pdf_lib == "pymupdf":
                return _extract_with_pymupdf(file_path, max_pages)
            return ""

        # Run PDF extraction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            text_content = await loop.run_in_executor(executor, extract_pdf_text_sync)

        return text_content

    except Exception as e:
        logger.error(f"PDF text extraction failed for {file_path}: {e}")
        return ""


def _extract_with_pypdf2(file_path: str, max_pages: int) -> str:
    """Extract text using PyPDF2"""
    import PyPDF2

    text_content = []
    try:
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = min(len(pdf_reader.pages), max_pages)

            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text_content.append(page.extract_text())

        return "\n\n".join(text_content)
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {e}")
        return ""


def _extract_with_pdfplumber(file_path: str, max_pages: int) -> str:
    """Extract text using pdfplumber"""
    import pdfplumber

    text_content = []
    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = min(len(pdf.pages), max_pages)

            for page_num in range(total_pages):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if text:
                    text_content.append(text)

        return "\n\n".join(text_content)
    except Exception as e:
        logger.error(f"pdfplumber extraction failed: {e}")
        return ""


def _extract_with_pymupdf(file_path: str, max_pages: int) -> str:
    """Extract text using PyMuPDF"""
    import fitz

    text_content = []
    try:
        doc = fitz.open(file_path)
        total_pages = min(doc.page_count, max_pages)

        for page_num in range(total_pages):
            page = doc[page_num]
            text_content.append(page.get_text())

        doc.close()
        return "\n\n".join(text_content)
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {e}")
        return ""


async def _extract_text_file_streaming(file_path: str, **kwargs) -> str:
    """Extract text from text files using streaming for memory efficiency"""
    try:
        import asyncio
        import aiofiles

        max_size = kwargs.get("max_text_size_mb", 100) * 1024 * 1024
        encoding = kwargs.get("encoding", "utf-8")

        # Check file size
        import os

        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            logger.warning(
                f"File {file_path} too large ({file_size / 1024 / 1024:.1f}MB), truncating"
            )

        # Read file asynchronously
        try:
            async with aiofiles.open(file_path, "r", encoding=encoding) as file:
                if file_size > max_size:
                    # Read only first part of large files
                    content = await file.read(max_size)
                else:
                    content = await file.read()
                return content
        except UnicodeDecodeError:
            # Try different encodings
            for alt_encoding in ["latin-1", "cp1252", "iso-8859-1"]:
                try:
                    async with aiofiles.open(file_path, "r", encoding=alt_encoding) as file:
                        content = await file.read(max_size if file_size > max_size else -1)
                        return content
                except UnicodeDecodeError:
                    continue

            logger.error(f"Could not decode file {file_path} with any encoding")
            return ""

    except Exception as e:
        logger.error(f"Text file extraction failed for {file_path}: {e}")
        return ""


async def _extract_word_document(file_path: str, **kwargs) -> str:
    """Extract text from Word documents"""
    try:
        try:
            import docx

            doc = docx.Document(file_path)
            text_content = []

            for paragraph in doc.paragraphs:
                text_content.append(paragraph.text)

            return "\n".join(text_content)

        except ImportError:
            logger.error("python-docx not available. Install: pip install python-docx")
            return ""

    except Exception as e:
        logger.error(f"Word document extraction failed for {file_path}: {e}")
        return ""


# Convenience functions for common file processing operations
async def process_pdf_files(pdf_paths: List[str], user_id: str, **kwargs) -> Dict[str, Any]:
    """Process multiple PDF files in parallel"""
    return await process_large_files_parallel(
        file_paths=pdf_paths, user_id=user_id, file_types=[".pdf"], **kwargs
    )


async def process_text_files(text_paths: List[str], user_id: str, **kwargs) -> Dict[str, Any]:
    """Process multiple text files in parallel"""
    return await process_large_files_parallel(
        file_paths=text_paths, user_id=user_id, file_types=[".txt", ".md", ".rst"], **kwargs
    )


async def process_mixed_files(file_paths: List[str], user_id: str, **kwargs) -> Dict[str, Any]:
    """Process mixed file types in parallel"""
    return await process_large_files_parallel(
        file_paths=file_paths, user_id=user_id, file_types=None, **kwargs  # Allow all types
    )
