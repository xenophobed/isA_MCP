#!/usr/bin/env python
"""
Semantic Content Filter Strategy
Advanced content filtering using embeddings for semantic similarity
Based on isa_model inference framework
"""
import json
import math
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

from core.logging import get_logger
from tools.base_service import BaseService
from ..base import FilterStrategy

logger = get_logger(__name__)

class SemanticFilter(FilterStrategy, BaseService):
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
        BaseService.__init__(self, "SemanticFilter")
        self.user_query = user_query
        self.similarity_threshold = similarity_threshold
        self.min_chunk_length = min_chunk_length
        self.max_chunks = max_chunks
        self.embedding_config = embedding_config or {}
        
        self.query_embedding = None
    
    async def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using ISA client"""
        try:
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=text,
                task="embed",
                service_type="embedding",
                operation_name="create_embedding"
            )
            return result_data
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2) or len(vec1) == 0:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
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
            # Get query embedding
            if self.query_embedding is None:
                self.query_embedding = await self._create_embedding(self.user_query)
                if not self.query_embedding:
                    logger.error("Failed to create query embedding, returning original content")
                    return content
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
            elements_to_keep = set()
            
            for i, text in enumerate(text_blocks):
                embedding = await self._create_embedding(text)
                if embedding:
                    similarity = self._cosine_similarity(self.query_embedding, embedding)
                    if similarity >= self.similarity_threshold:
                        elements_to_keep.add(i)
            
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
            chunks = self._create_content_chunks(content)
            
            if not chunks:
                logger.warning("⚠️ No chunks created for semantic filtering")
                return content
            
            # Process chunks and calculate similarities
            logger.info(f"📊 Processing {len(chunks)} text chunks...")
            relevant_chunks = []
            
            for i, chunk in enumerate(chunks):
                embedding = await self._create_embedding(chunk['text'])
                if embedding:
                    similarity = self._cosine_similarity(self.query_embedding, embedding)
                    if similarity >= self.similarity_threshold:
                        chunk['similarity'] = similarity
                        relevant_chunks.append(chunk)
            
            if not relevant_chunks:
                logger.warning("⚠️ No chunks met similarity threshold")
                return content
            
            # Sort by similarity (highest first) and reconstruct content
            relevant_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            filtered_content = '\n\n'.join([chunk['text'] for chunk in relevant_chunks])
            
            logger.info(f"✅ Semantic filter applied: kept {len(relevant_chunks)}/{len(chunks)} chunks")
            return filtered_content
            
        except Exception as e:
            logger.error(f"❌ Text semantic filtering failed: {e}")
            return content
    
    def _create_content_chunks(self, content: str) -> List[Dict[str, Any]]:
        """Create chunks from content"""
        try:
            # Try multiple chunking strategies
            chunks = []
            
            # Strategy 1: Split by double newlines (paragraphs)
            paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) >= self.min_chunk_length]
            if paragraphs:
                chunks = [{'text': p} for p in paragraphs[:self.max_chunks]]
            
            # Strategy 2: If no paragraphs found, try single newlines
            if not chunks:
                lines = [l.strip() for l in content.split('\n') if len(l.strip()) >= self.min_chunk_length]
                if lines:
                    chunks = [{'text': l} for l in lines[:self.max_chunks]]
            
            # Strategy 3: If still no chunks, treat entire content as one chunk if it's long enough
            if not chunks and len(content.strip()) >= self.min_chunk_length:
                chunks = [{'text': content.strip()}]
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Failed to create content chunks: {e}")
            return []
    
    async def rank_content_by_relevance(self, content_items: List[str], top_k: int = 10) -> List[Dict[str, Any]]:
        """Rank multiple content items by semantic relevance to query"""
        try:
            if not self.query_embedding:
                self.query_embedding = await self._create_embedding(self.user_query)
                if not self.query_embedding:
                    logger.error("Failed to create query embedding")
                    return []
            
            # Process and rank content items
            ranked_items = []
            for i, content in enumerate(content_items):
                embedding = await self._create_embedding(content)
                if embedding:
                    similarity = self._cosine_similarity(self.query_embedding, embedding)
                    ranked_items.append({
                        'content': content,
                        'similarity': similarity,
                        'index': i
                    })
            
            # Sort by similarity and take top_k
            ranked_items.sort(key=lambda x: x['similarity'], reverse=True)
            result = []
            for i, item in enumerate(ranked_items[:top_k]):
                result.append({
                    'content': item['content'],
                    'similarity': item['similarity'],
                    'rank': i + 1
                })
            
            logger.info(f"✅ Content ranking completed: {len(result)} items ranked")
            return result
            
        except Exception as e:
            logger.error(f"❌ Content ranking failed: {e}")
            return []
    
    async def deduplicate_by_similarity(self, content_items: List[str], 
                                      similarity_threshold: float = 0.8) -> List[str]:
        """Remove duplicate content based on semantic similarity"""
        try:
            if not content_items:
                return []
            
            # Get embeddings for all content
            embeddings = []
            for content in content_items:
                embedding = await self._create_embedding(content)
                embeddings.append(embedding)
            
            # Find unique content
            unique_content = []
            unique_embeddings = []
            
            for i, (content, embedding) in enumerate(zip(content_items, embeddings)):
                if not embedding:  # Skip if embedding failed
                    continue
                    
                is_duplicate = False
                
                # Check against existing unique content
                for unique_emb in unique_embeddings:
                    similarity = self._cosine_similarity(embedding, unique_emb)
                    if similarity >= similarity_threshold:
                        is_duplicate = True
                        break
                
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
        """Clean up resources"""
        pass
    
    def get_service_billing_info(self) -> Dict[str, Any]:
        """Get billing information for this service"""
        return self.get_billing_summary()


class SemanticSearchEnhancer(BaseService):
    """Semantic search enhancement using embeddings"""
    
    def __init__(self):
        super().__init__("SemanticSearchEnhancer")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2) or len(vec1) == 0:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using ISA client"""
        try:
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=text,
                task="embed",
                service_type="embedding",
                operation_name="create_embedding"
            )
            return result_data
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return []
    
    async def enhance_search_query(self, original_query: str, 
                                 context: Optional[str] = None) -> Dict[str, Any]:
        """Enhance search query using semantic understanding"""
        try:
            # Create embedding for the query using ISA client
            query_embedding = await self._create_embedding(original_query)
            
            if not query_embedding:
                raise Exception("Failed to create query embedding")
            
            # Generate enhanced query
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
            
            # Create query embedding
            query_embedding = await self._create_embedding(query)
            if not query_embedding:
                logger.error("Failed to create query embedding")
                return results
            
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
            
            # Get embeddings and calculate similarities
            ranked_results = []
            for i, (result, text) in enumerate(zip(results, result_texts)):
                embedding = await self._create_embedding(text)
                if embedding:
                    similarity = self._cosine_similarity(query_embedding, embedding)
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
        """Clean up resources"""
        pass
    
    def get_service_billing_info(self) -> Dict[str, Any]:
        """Get billing information for this service"""
        return self.get_billing_summary()