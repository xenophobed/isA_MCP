#!/usr/bin/env python
"""
Semantic Content Filter Strategy
Advanced content filtering using embeddings for semantic similarity
Based on isa_model inference framework
"""
import json
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

from core.logging import get_logger
from isa_model.inference import AIFactory
from ..base import FilterStrategy

logger = get_logger(__name__)

class SemanticFilter(FilterStrategy):
    """Content filter using embeddings for semantic similarity and relevance"""
    
    def __init__(self, 
                 user_query: str = "",
                 similarity_threshold: float = 0.6,
                 min_chunk_length: int = 100,
                 max_chunks: int = 20,
                 embedding_config: Optional[Dict] = None):
        """
        Initialize semantic filter
        
        Args:
            user_query: Query to calculate semantic relevance against
            similarity_threshold: Minimum similarity score for content to be kept (0.0-1.0)
            min_chunk_length: Minimum character length for text chunks
            max_chunks: Maximum number of chunks to process (for performance)
            embedding_config: Configuration for embedding service
        """
        self.user_query = user_query
        self.similarity_threshold = similarity_threshold
        self.min_chunk_length = min_chunk_length
        self.max_chunks = max_chunks
        self.embedding_config = embedding_config or {}
        
        self.ai_factory = AIFactory()
        self.embed = None
        self.query_embedding = None
    
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Filter content based on semantic similarity to query"""
        logger.info(f"🔄 Applying semantic filter for query: '{self.user_query}'")
        
        if criteria:
            self.user_query = criteria.get('query', self.user_query)
            self.similarity_threshold = criteria.get('threshold', self.similarity_threshold)
        
        if not self.user_query:
            logger.warning("No query provided for semantic filtering, returning original content")
            return content
        
        try:
            # Initialize embedding service
            if self.embed is None:
                self.embed = self.ai_factory.get_embed()
                logger.info(f"✅ Embedding service initialized: {self.embed.get_embedding_dimension()} dimensions")
            
            # Get query embedding
            if self.query_embedding is None:
                self.query_embedding = await self.embed.create_text_embedding(self.user_query)
                logger.info(f"📊 Query embedding created for: '{self.user_query}'")
            
            # Process content based on type
            if self._is_html(content):
                return await self._filter_html_by_semantic_similarity(content)
            else:
                return await self._filter_text_by_semantic_similarity(content)
            
        except Exception as e:
            logger.error(f"❌ Semantic filter failed: {e}")
            return content
    
    def _is_html(self, content: str) -> bool:
        """Check if content is HTML format"""
        return '<html>' in content.lower() or '<body>' in content.lower() or '<div>' in content.lower()
    
    async def _filter_html_by_semantic_similarity(self, content: str) -> str:
        """Filter HTML content using semantic similarity"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract meaningful text blocks
            text_blocks = []
            element_map = {}
            
            # Find content-rich elements
            content_elements = soup.find_all(['p', 'div', 'article', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote'])
            
            for i, element in enumerate(content_elements):
                text = element.get_text(strip=True)
                if len(text) >= self.min_chunk_length:
                    text_blocks.append(text)
                    element_map[len(text_blocks) - 1] = element
                    
                    if len(text_blocks) >= self.max_chunks:
                        break
            
            if not text_blocks:
                logger.warning("⚠️ No text blocks found for semantic filtering")
                return content
            
            # Get embeddings for text blocks
            logger.info(f"📊 Creating embeddings for {len(text_blocks)} text blocks...")
            block_embeddings = await self.embed.create_text_embeddings(text_blocks)
            
            # Calculate similarities
            similar_results = await self.embed.find_similar_texts(
                query_embedding=self.query_embedding,
                candidate_embeddings=block_embeddings,
                top_k=len(text_blocks)
            )
            
            # Filter elements based on similarity
            elements_to_keep = set()
            filtered_count = 0
            
            for result in similar_results:
                if result["similarity"] >= self.similarity_threshold:
                    elements_to_keep.add(result["index"])
                else:
                    filtered_count += 1
            
            # Remove low-similarity elements
            elements_to_remove = []
            for i, element in element_map.items():
                if i not in elements_to_keep:
                    elements_to_remove.append(element)
            
            for element in elements_to_remove:
                if element.parent:
                    element.decompose()
            
            kept_count = len(text_blocks) - len(elements_to_remove)
            logger.info(f"✅ Semantic filter applied: kept {kept_count}/{len(text_blocks)} elements")
            
            return str(soup)
            
        except Exception as e:
            logger.error(f"❌ HTML semantic filtering failed: {e}")
            return content
    
    async def _filter_text_by_semantic_similarity(self, content: str) -> str:
        """Filter text content using semantic similarity"""
        try:
            # Split content into chunks
            chunks = await self._create_content_chunks(content)
            
            if not chunks:
                logger.warning("⚠️ No chunks created for semantic filtering")
                return content
            
            # Get embeddings for chunks
            chunk_texts = [chunk['text'] for chunk in chunks]
            logger.info(f"📊 Creating embeddings for {len(chunk_texts)} text chunks...")
            
            chunk_embeddings = await self.embed.create_text_embeddings(chunk_texts)
            
            # Calculate similarities
            similar_results = await self.embed.find_similar_texts(
                query_embedding=self.query_embedding,
                candidate_embeddings=chunk_embeddings,
                top_k=len(chunks)
            )
            
            # Filter chunks based on similarity
            relevant_chunks = []
            for result in similar_results:
                if result["similarity"] >= self.similarity_threshold:
                    chunk_index = result["index"]
                    chunk = chunks[chunk_index]
                    chunk['similarity'] = result["similarity"]
                    relevant_chunks.append(chunk)
            
            # Sort by similarity (highest first) and reconstruct content
            relevant_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            filtered_content = '\n\n'.join([chunk['text'] for chunk in relevant_chunks])
            
            logger.info(f"✅ Semantic filter applied: kept {len(relevant_chunks)}/{len(chunks)} chunks")
            return filtered_content
            
        except Exception as e:
            logger.error(f"❌ Text semantic filtering failed: {e}")
            return content
    
    async def _create_content_chunks(self, content: str) -> List[Dict[str, Any]]:
        """Create semantic chunks from content"""
        try:
            # Use the embedding service's built-in chunking
            chunks = await self.embed.create_chunks(
                text=content,
                metadata={"source": "semantic_filter"}
            )
            
            # Filter chunks by minimum length and limit count
            filtered_chunks = []
            for chunk in chunks:
                if len(chunk['text']) >= self.min_chunk_length:
                    filtered_chunks.append(chunk)
                    if len(filtered_chunks) >= self.max_chunks:
                        break
            
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"❌ Failed to create content chunks: {e}")
            
            # Fallback: simple paragraph splitting
            paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) >= self.min_chunk_length]
            return [{'text': p, 'embedding': None} for p in paragraphs[:self.max_chunks]]
    
    async def rank_content_by_relevance(self, content_items: List[str], top_k: int = 10) -> List[Dict[str, Any]]:
        """Rank multiple content items by semantic relevance to query"""
        try:
            if not self.embed:
                self.embed = self.ai_factory.get_embed()
            
            if not self.query_embedding:
                self.query_embedding = await self.embed.create_text_embedding(self.user_query)
            
            # Get embeddings for all content items
            content_embeddings = await self.embed.create_text_embeddings(content_items)
            
            # Find most similar items
            similar_results = await self.embed.find_similar_texts(
                query_embedding=self.query_embedding,
                candidate_embeddings=content_embeddings,
                top_k=min(top_k, len(content_items))
            )
            
            # Format results with content
            ranked_items = []
            for result in similar_results:
                ranked_items.append({
                    'content': content_items[result['index']],
                    'similarity': result['similarity'],
                    'rank': len(ranked_items) + 1
                })
            
            logger.info(f"✅ Content ranking completed: {len(ranked_items)} items ranked")
            return ranked_items
            
        except Exception as e:
            logger.error(f"❌ Content ranking failed: {e}")
            return []
    
    async def deduplicate_by_similarity(self, content_items: List[str], 
                                      similarity_threshold: float = 0.8) -> List[str]:
        """Remove duplicate content based on semantic similarity"""
        try:
            if not content_items:
                return []
            
            if not self.embed:
                self.embed = self.ai_factory.get_embed()
            
            # Get embeddings for all content
            embeddings = await self.embed.create_text_embeddings(content_items)
            
            # Find unique content
            unique_content = []
            unique_embeddings = []
            
            for i, (content, embedding) in enumerate(zip(content_items, embeddings)):
                is_duplicate = False
                
                # Check against existing unique content
                if unique_embeddings:
                    similarities = []
                    for unique_emb in unique_embeddings:
                        similarity = await self.embed.compute_similarity(embedding, unique_emb)
                        similarities.append(similarity)
                    
                    # If too similar to any existing content, consider it duplicate
                    if max(similarities) >= similarity_threshold:
                        is_duplicate = True
                
                if not is_duplicate:
                    unique_content.append(content)
                    unique_embeddings.append(embedding)
            
            logger.info(f"✅ Deduplication completed: {len(unique_content)}/{len(content_items)} unique items")
            return unique_content
            
        except Exception as e:
            logger.error(f"❌ Deduplication failed: {e}")
            return content_items
    
    def get_filter_name(self) -> str:
        return "semantic"
    
    async def close(self):
        """Clean up embedding service"""
        if self.embed:
            await self.embed.close()
            self.embed = None

class SemanticSearchEnhancer:
    """Semantic search enhancement using embeddings"""
    
    def __init__(self):
        self.ai_factory = AIFactory()
        self.embed = None
    
    async def enhance_search_query(self, original_query: str, 
                                 context: Optional[str] = None) -> Dict[str, Any]:
        """Enhance search query using semantic understanding"""
        try:
            if not self.embed:
                self.embed = self.ai_factory.get_embed()
            
            # Create embedding for the query
            query_embedding = await self.embed.create_text_embedding(original_query)
            
            # Generate related terms and concepts (this would use LLM in practice)
            enhanced_query = {
                'original_query': original_query,
                'embedding': query_embedding,
                'enhanced_terms': [],  # Could be populated by LLM
                'search_strategy': 'semantic',
                'context': context
            }
            
            logger.info(f"✅ Search query enhanced: '{original_query}'")
            return enhanced_query
            
        except Exception as e:
            logger.error(f"❌ Query enhancement failed: {e}")
            return {'original_query': original_query, 'error': str(e)}
    
    async def rank_search_results(self, query: str, results: List[Dict[str, Any]], 
                                top_k: int = 10) -> List[Dict[str, Any]]:
        """Rank search results by semantic relevance"""
        try:
            if not results:
                return []
            
            if not self.embed:
                self.embed = self.ai_factory.get_embed()
            
            # Create query embedding
            query_embedding = await self.embed.create_text_embedding(query)
            
            # Extract text content from results for embedding
            result_texts = []
            for result in results:
                # Combine title, description, and any other text fields
                text_parts = []
                for key in ['title', 'description', 'content', 'snippet']:
                    if key in result and result[key]:
                        text_parts.append(str(result[key]))
                
                result_text = ' '.join(text_parts) if text_parts else str(result)
                result_texts.append(result_text)
            
            # Get embeddings for result texts
            result_embeddings = await self.embed.create_text_embeddings(result_texts)
            
            # Calculate similarities
            similarities = []
            for embedding in result_embeddings:
                similarity = await self.embed.compute_similarity(query_embedding, embedding)
                similarities.append(similarity)
            
            # Combine results with similarity scores and rank
            ranked_results = []
            for i, (result, similarity) in enumerate(zip(results, similarities)):
                enhanced_result = result.copy()
                enhanced_result['semantic_similarity'] = similarity
                enhanced_result['original_rank'] = i + 1
                ranked_results.append(enhanced_result)
            
            # Sort by semantic similarity
            ranked_results.sort(key=lambda x: x['semantic_similarity'], reverse=True)
            
            # Add new ranking
            for i, result in enumerate(ranked_results[:top_k]):
                result['semantic_rank'] = i + 1
            
            logger.info(f"✅ Search results ranked: {len(ranked_results[:top_k])} results")
            return ranked_results[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Result ranking failed: {e}")
            return results
    
    async def close(self):
        """Clean up embedding service"""
        if self.embed:
            await self.embed.close()
            self.embed = None