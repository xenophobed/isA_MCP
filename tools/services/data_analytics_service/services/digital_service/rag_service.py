#!/usr/bin/env python3
"""
RAG Service - Retrieval-Augmented Generation with User-Based Knowledge Management

Provides a complete RAG pipeline with embedding generation, storage, retrieval, and generation.
Integrates with embedding generator, Supabase database, and graph knowledge resources.
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from tools.services.intelligence_service.language.embedding_generator import embed, search, chunk, rerank, hybrid_search_local, enhanced_search, store_knowledge_local
from core.database.supabase_client import get_supabase_client
from resources.graph_knowledge_resources import graph_knowledge_resources

logger = logging.getLogger(__name__)

class RAGService:
    """
    Complete RAG (Retrieval-Augmented Generation) service with user-based knowledge management.
    
    Features:
    - User-isolated knowledge bases
    - Automatic embedding generation and storage
    - Semantic search and retrieval
    - Document chunking for long texts
    - MCP resource registration
    - Full RAG pipeline with context retrieval and generation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize RAG service.
        
        Args:
            config: Service configuration options
        """
        self.config = config or {}
        self.supabase = get_supabase_client()
        self.table_name = "user_knowledge"
        
        # Default configuration
        self.default_chunk_size = self.config.get('chunk_size', 400)
        self.default_overlap = self.config.get('overlap', 50)
        self.default_top_k = self.config.get('top_k', 5)
        self.embedding_model = self.config.get('embedding_model', 'text-embedding-3-small')
        self.enable_rerank = self.config.get('enable_rerank', False)  # Default: no rerank
        
        logger.info("RAG Service initialized")
    
    async def store_knowledge(self, 
                            user_id: str, 
                            text: str, 
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Store text as knowledge with embedding generation and MCP registration.
        
        Args:
            user_id: User identifier
            text: Text content to store
            metadata: Optional metadata for the knowledge item
            
        Returns:
            Dict containing storage result and MCP address
        """
        try:
            # Use doc_id from metadata if provided by Storage Service, otherwise generate new UUID
            knowledge_id = (metadata or {}).get('doc_id', str(uuid.uuid4()))
            now = datetime.now().isoformat()
            
            # Generate embedding
            logger.info(f"Generating embedding for user {user_id}, text length: {len(text)}")
            embedding = await embed(text, model=self.embedding_model)
            
            if not embedding:
                return {
                    'success': False,
                    'error': 'Failed to generate embedding',
                    'user_id': user_id
                }
            
            # Prepare knowledge data
            knowledge_data = {
                'id': knowledge_id,
                'user_id': user_id,
                'text': text,
                'embedding_vector': embedding,
                'metadata': metadata or {},
                'chunk_index': 0,
                'source_document': metadata.get('source') if metadata else None,
                'created_at': now,
                'updated_at': now
            }
            
            # Store in database
            result = self.supabase.table(self.table_name).insert(knowledge_data).execute()
            
            if not result.data:
                return {
                    'success': False,
                    'error': 'Failed to store knowledge in database',
                    'user_id': user_id
                }
            
            # Also store in enhanced vector database for hybrid search capabilities
            try:
                enhanced_result = await store_knowledge_local(
                    user_id=user_id,
                    text=text,
                    metadata={
                        'knowledge_id': knowledge_id,
                        'source': metadata.get('source') if metadata else None,
                        'stored_at': now,
                        **((metadata or {}))
                    }
                )
                enhanced_storage_success = enhanced_result.get('success', False)
                logger.info(f"Enhanced vector storage {'succeeded' if enhanced_storage_success else 'failed'} for knowledge {knowledge_id}")
            except Exception as e:
                logger.warning(f"Enhanced vector storage failed for knowledge {knowledge_id}: {e}")
                enhanced_storage_success = False
            
            # Register MCP resource
            mcp_result = await graph_knowledge_resources.register_resource(
                resource_id=knowledge_id,
                user_id=int(user_id) if user_id.isdigit() else hash(user_id) % (2**31),
                resource_data={
                    'type': 'knowledge_base_item',
                    'text_preview': text[:100] + "..." if len(text) > 100 else text,
                    'metadata': metadata or {},
                    'source_file': metadata.get('source') if metadata else None,
                    'embedding_model': self.embedding_model,
                    'text_length': len(text)
                }
            )
            
            mcp_address = f"mcp://rag/{user_id}/{knowledge_id}"
            
            logger.info(f"Knowledge stored successfully for user {user_id}: {knowledge_id}")
            
            return {
                'success': True,
                'knowledge_id': knowledge_id,
                'mcp_address': mcp_address,
                'user_id': user_id,
                'text_length': len(text),
                'embedding_dimensions': len(embedding),
                'mcp_registration': mcp_result.get('success', False),
                'enhanced_storage': enhanced_storage_success
            }
            
        except Exception as e:
            logger.error(f"Error storing knowledge for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def retrieve_context(self, 
                             user_id: str, 
                             query: str, 
                             top_k: int = None,
                             search_mode: str = "hybrid",
                             use_enhanced_search: bool = True) -> Dict[str, Any]:
        """
        Retrieve relevant context from user's knowledge base using enhanced hybrid search.
        
        Args:
            user_id: User identifier
            query: Search query
            top_k: Number of results to return (default: 5)
            search_mode: "semantic", "lexical", or "hybrid" (default: "hybrid")
            use_enhanced_search: Whether to use the new enhanced search capabilities
            
        Returns:
            Dict containing retrieved context items
        """
        try:
            top_k = top_k or self.default_top_k
            
            # Strategy 1: Try enhanced hybrid search first
            if use_enhanced_search:
                try:
                    enhanced_results = await enhanced_search(
                        query_text=query,
                        user_id=user_id,
                        top_k=top_k,
                        search_mode=search_mode
                    )
                    
                    if enhanced_results:
                        # Convert enhanced search results to context format
                        context_items = []
                        for result in enhanced_results:
                            context_items.append({
                                'knowledge_id': result.get('id'),
                                'text': result.get('text'),
                                'similarity_score': result.get('score', 0),
                                'semantic_score': result.get('semantic_score'),
                                'lexical_score': result.get('lexical_score'),
                                'metadata': result.get('metadata', {}),
                                'created_at': result.get('metadata', {}).get('created_at'),
                                'search_method': result.get('method', 'enhanced')
                            })
                        
                        logger.info(f"Retrieved {len(context_items)} context items using enhanced search for user {user_id}")
                        
                        return {
                            'success': True,
                            'user_id': user_id,
                            'query': query,
                            'context_items': context_items,
                            'total_knowledge_items': len(context_items),
                            'search_method': 'enhanced_hybrid'
                        }
                        
                except Exception as e:
                    logger.warning(f"Enhanced search failed for user {user_id}: {e}, falling back to traditional search")
            
            # Strategy 2: Fallback to traditional database search
            # Get user's knowledge base
            result = self.supabase.table(self.table_name)\
                                 .select('id, text, metadata, created_at')\
                                 .eq('user_id', user_id)\
                                 .execute()
            
            if not result.data:
                return {
                    'success': True,
                    'user_id': user_id,
                    'query': query,
                    'context_items': [],
                    'total_knowledge_items': 0,
                    'search_method': 'traditional_fallback'
                }
            
            # Extract texts for search
            knowledge_items = result.data
            texts = [item['text'] for item in knowledge_items]
            
            # Perform semantic search
            search_results = await search(query, texts, top_k=top_k)
            
            # Match results back to knowledge items
            context_items = []
            for text, similarity_score in search_results:
                # Find matching knowledge item
                for item in knowledge_items:
                    if item['text'] == text:
                        context_items.append({
                            'knowledge_id': item['id'],
                            'text': text,
                            'similarity_score': similarity_score,
                            'semantic_score': similarity_score,
                            'lexical_score': None,
                            'metadata': item['metadata'],
                            'created_at': item['created_at'],
                            'search_method': 'traditional_isa'
                        })
                        break
            
            logger.info(f"Retrieved {len(context_items)} context items using traditional search for user {user_id}")
            
            return {
                'success': True,
                'user_id': user_id,
                'query': query,
                'context_items': context_items,
                'total_knowledge_items': len(knowledge_items),
                'search_method': 'traditional_isa'
            }
            
        except Exception as e:
            logger.error(f"Error retrieving context for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query
            }
    
    async def search_knowledge(self, 
                             user_id: str, 
                             query: str, 
                             top_k: int = None,
                             enable_rerank: bool = None,
                             search_mode: str = "hybrid",
                             use_enhanced_search: bool = True) -> Dict[str, Any]:
        """
        Search user's knowledge base with enhanced hybrid search and optional ranking.
        
        Args:
            user_id: User identifier
            query: Search query
            top_k: Number of results to return
            enable_rerank: Enable reranking (overrides default setting)
            search_mode: "semantic", "lexical", or "hybrid" search mode
            use_enhanced_search: Whether to use enhanced search capabilities
            
        Returns:
            Dict containing search results with relevance scores
        """
        try:
            # Get search results using enhanced context retrieval
            context_result = await self.retrieve_context(
                user_id=user_id, 
                query=query, 
                top_k=top_k,
                search_mode=search_mode,
                use_enhanced_search=use_enhanced_search
            )
            
            if not context_result['success'] or not context_result['context_items']:
                # Return the search results in the expected format
                return {
                    'success': context_result['success'],
                    'user_id': user_id,
                    'query': query,
                    'search_results': [],
                    'total_knowledge_items': context_result.get('total_knowledge_items', 0),
                    'search_method': context_result.get('search_method', 'unknown'),
                    'error': context_result.get('error')
                }
            
            context_items = context_result['context_items']
            search_method = context_result.get('search_method', 'unknown')
            
            # Check if reranking is enabled
            use_rerank = enable_rerank if enable_rerank is not None else self.enable_rerank
            
            if use_rerank:
                # Extract texts for reranking
                documents = [item['text'] for item in context_items]
                
                try:
                    # Use advanced reranking with MMR for diversity
                    from tools.services.intelligence_service.language.embedding_generator import advanced_rerank
                    
                    reranked_results = await advanced_rerank(
                        query=query,
                        documents=documents,
                        method="combined",  # Use both MMR and ISA reranking
                        top_k=top_k or self.default_top_k
                    )
                    
                    # Combine reranking with original context items
                    final_results = []
                    for rerank_result in reranked_results:
                        document_text = rerank_result.get('document', rerank_result.get('text', ''))
                        relevance_score = rerank_result.get('relevance_score', rerank_result.get('score', 0))
                        
                        # Find matching context item
                        for item in context_items:
                            if item['text'] == document_text:
                                final_results.append({
                                    'knowledge_id': item['knowledge_id'],
                                    'text': document_text,
                                    'relevance_score': relevance_score,
                                    'similarity_score': item.get('similarity_score', 0),
                                    'semantic_score': item.get('semantic_score'),
                                    'lexical_score': item.get('lexical_score'),
                                    'mmr_score': rerank_result.get('mmr_score'),
                                    'isa_score': rerank_result.get('isa_score'),
                                    'metadata': item['metadata'],
                                    'created_at': item['created_at'],
                                    'mcp_address': f"mcp://rag/{user_id}/{item['knowledge_id']}",
                                    'rerank_method': rerank_result.get('method', 'combined')
                                })
                                break
                    
                    logger.info(f"Enhanced search with advanced reranking completed for user {user_id}, {len(final_results)} results")
                    
                except Exception as rerank_error:
                    logger.warning(f"Advanced reranking failed for user {user_id}: {rerank_error}, falling back to original scores")
                    # Fall back to original search scores
                    final_results = []
                    for item in context_items:
                        final_results.append({
                            'knowledge_id': item['knowledge_id'],
                            'text': item['text'],
                            'relevance_score': item.get('similarity_score', item.get('semantic_score', 0)),
                            'similarity_score': item.get('similarity_score'),
                            'semantic_score': item.get('semantic_score'),
                            'lexical_score': item.get('lexical_score'),
                            'metadata': item['metadata'],
                            'created_at': item['created_at'],
                            'mcp_address': f"mcp://rag/{user_id}/{item['knowledge_id']}",
                            'search_method': item.get('search_method', search_method)
                        })
            else:
                # No reranking, use search results directly
                final_results = []
                for item in context_items:
                    final_results.append({
                        'knowledge_id': item['knowledge_id'],
                        'text': item['text'],
                        'relevance_score': item.get('similarity_score', item.get('semantic_score', 0)),
                        'similarity_score': item.get('similarity_score'),
                        'semantic_score': item.get('semantic_score'),
                        'lexical_score': item.get('lexical_score'),
                        'metadata': item['metadata'],
                        'created_at': item['created_at'],
                        'mcp_address': f"mcp://rag/{user_id}/{item['knowledge_id']}",
                        'search_method': item.get('search_method', search_method)
                    })
                
                logger.info(f"Enhanced search without reranking completed for user {user_id}, {len(final_results)} results")
            
            return {
                'success': True,
                'user_id': user_id,
                'query': query,
                'search_results': final_results,
                'total_knowledge_items': context_result['total_knowledge_items'],
                'search_method': search_method,
                'search_mode': search_mode,
                'reranking_used': use_rerank,
                'enhanced_search_used': use_enhanced_search
            }
            
        except Exception as e:
            logger.error(f"Error searching knowledge for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query
            }
    
    async def generate_response(self, 
                              user_id: str, 
                              query: str, 
                              context_limit: int = 3,
                              model: str = None) -> Dict[str, Any]:
        """
        Full RAG pipeline: retrieve context and generate response.
        
        Args:
            user_id: User identifier
            query: User query
            context_limit: Maximum number of context items to use
            model: LLM model to use for generation
            
        Returns:
            Dict containing generated response with context
        """
        try:
            # Retrieve relevant context
            context_result = await self.retrieve_context(user_id, query, top_k=context_limit)
            
            if not context_result['success']:
                return {
                    'success': False,
                    'error': 'Failed to retrieve context',
                    'user_id': user_id,
                    'query': query,
                    'context_error': context_result.get('error')
                }
            
            context_items = context_result['context_items']
            
            if not context_items:
                return {
                    'success': True,
                    'user_id': user_id,
                    'query': query,
                    'response': f"I don't have any relevant knowledge to answer your question: '{query}'. Please add some knowledge to your knowledge base first.",
                    'context_items': [],
                    'context_used': 0
                }
            
            # Build context for generation
            context_texts = []
            for i, item in enumerate(context_items[:context_limit]):
                context_texts.append(f"Context {i+1}: {item['text']}")
            
            context_string = "\n\n".join(context_texts)
            
            # Create prompt for generation
            prompt = f"""Based on the following context, please answer the user's question accurately and comprehensively.

Context:
{context_string}

User Question: {query}

Please provide a helpful response based on the context provided. If the context doesn't contain enough information to fully answer the question, acknowledge this limitation."""
            
            # For now, return structured response
            # In a full implementation, you would call an LLM here
            response = f"Based on your knowledge base, here's what I found relevant to '{query}':\n\n"
            
            for i, item in enumerate(context_items[:context_limit]):
                score = item.get('similarity_score', 0)
                response += f"{i+1}. (Relevance: {score:.3f}) {item['text'][:200]}{'...' if len(item['text']) > 200 else ''}\n\n"
            
            response += f"This response is based on {len(context_items[:context_limit])} relevant items from your knowledge base."
            
            logger.info(f"Generated response for user {user_id}, used {len(context_items[:context_limit])} context items")
            
            return {
                'success': True,
                'user_id': user_id,
                'query': query,
                'response': response,
                'context_items': context_items[:context_limit],
                'context_used': len(context_items[:context_limit]),
                'total_available_context': len(context_items)
            }
            
        except Exception as e:
            logger.error(f"Error generating response for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query
            }
    
    async def add_document(self, 
                         user_id: str, 
                         document: str, 
                         chunk_size: int = None,
                         overlap: int = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add a long document by chunking it into smaller pieces.
        
        Args:
            user_id: User identifier
            document: Document text to add
            chunk_size: Size of each chunk (default: 400)
            overlap: Overlap between chunks (default: 50)
            metadata: Metadata for all chunks
            
        Returns:
            Dict containing chunking and storage results
        """
        try:
            chunk_size = chunk_size or self.default_chunk_size
            overlap = overlap or self.default_overlap
            
            # Chunk the document
            logger.info(f"Chunking document for user {user_id}, length: {len(document)}")
            chunks = await chunk(document, chunk_size=chunk_size, overlap=overlap, metadata=metadata)
            
            if not chunks:
                return {
                    'success': False,
                    'error': 'Failed to chunk document',
                    'user_id': user_id
                }
            
            # Store each chunk
            stored_chunks = []
            document_id = str(uuid.uuid4())
            
            for i, chunk_data in enumerate(chunks):
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    'document_id': document_id,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_size': chunk_size,
                    'overlap': overlap
                })
                
                result = await self.store_knowledge(
                    user_id=user_id,
                    text=chunk_data['text'],
                    metadata=chunk_metadata
                )
                
                if result['success']:
                    stored_chunks.append({
                        'chunk_index': i,
                        'knowledge_id': result['knowledge_id'],
                        'mcp_address': result['mcp_address'],
                        'text_length': len(chunk_data['text'])
                    })
                else:
                    logger.warning(f"Failed to store chunk {i} for user {user_id}: {result.get('error')}")
            
            logger.info(f"Document added for user {user_id}: {len(stored_chunks)}/{len(chunks)} chunks stored")
            
            return {
                'success': True,
                'user_id': user_id,
                'document_id': document_id,
                'total_chunks': len(chunks),
                'stored_chunks': len(stored_chunks),
                'chunks': stored_chunks,
                'document_length': len(document)
            }
            
        except Exception as e:
            logger.error(f"Error adding document for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def list_user_knowledge(self, user_id: str) -> Dict[str, Any]:
        """
        List all knowledge items for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict containing user's knowledge items
        """
        try:
            result = self.supabase.table(self.table_name)\
                                 .select('id, text, metadata, created_at, updated_at')\
                                 .eq('user_id', user_id)\
                                 .order('created_at', desc=True)\
                                 .execute()
            
            knowledge_items = []
            for item in result.data or []:
                knowledge_items.append({
                    'knowledge_id': item['id'],
                    'text_preview': item['text'][:100] + "..." if len(item['text']) > 100 else item['text'],
                    'text_length': len(item['text']),
                    'metadata': item['metadata'],
                    'created_at': item['created_at'],
                    'updated_at': item['updated_at'],
                    'mcp_address': f"mcp://rag/{user_id}/{item['id']}"
                })
            
            logger.info(f"Listed {len(knowledge_items)} knowledge items for user {user_id}")
            
            return {
                'success': True,
                'user_id': user_id,
                'knowledge_items': knowledge_items,
                'total_count': len(knowledge_items)
            }
            
        except Exception as e:
            logger.error(f"Error listing knowledge for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def delete_knowledge(self, user_id: str, knowledge_id: str) -> Dict[str, Any]:
        """
        Delete a knowledge item.
        
        Args:
            user_id: User identifier
            knowledge_id: Knowledge item identifier
            
        Returns:
            Dict containing deletion result
        """
        try:
            # Check if knowledge exists and belongs to user
            result = self.supabase.table(self.table_name)\
                                 .select('id')\
                                 .eq('id', knowledge_id)\
                                 .eq('user_id', user_id)\
                                 .execute()
            
            if not result.data:
                return {
                    'success': False,
                    'error': 'Knowledge item not found or access denied',
                    'user_id': user_id,
                    'knowledge_id': knowledge_id
                }
            
            # Delete from database
            delete_result = self.supabase.table(self.table_name)\
                                        .delete()\
                                        .eq('id', knowledge_id)\
                                        .eq('user_id', user_id)\
                                        .execute()
            
            # Delete MCP resource
            user_id_int = int(user_id) if user_id.isdigit() else hash(user_id) % (2**31)
            mcp_result = await graph_knowledge_resources.delete_resource(
                resource_id=knowledge_id,
                user_id=user_id_int
            )
            
            logger.info(f"Knowledge deleted for user {user_id}: {knowledge_id}")
            
            return {
                'success': True,
                'user_id': user_id,
                'knowledge_id': knowledge_id,
                'mcp_deletion': mcp_result.get('success', False)
            }
            
        except Exception as e:
            logger.error(f"Error deleting knowledge for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'knowledge_id': knowledge_id
            }
    
    async def get_knowledge(self, user_id: str, knowledge_id: str) -> Dict[str, Any]:
        """
        Get a specific knowledge item.
        
        Args:
            user_id: User identifier
            knowledge_id: Knowledge item identifier
            
        Returns:
            Dict containing knowledge item data
        """
        try:
            result = self.supabase.table(self.table_name)\
                                 .select('*')\
                                 .eq('id', knowledge_id)\
                                 .eq('user_id', user_id)\
                                 .single()\
                                 .execute()
            
            if not result.data:
                return {
                    'success': False,
                    'error': 'Knowledge item not found or access denied',
                    'user_id': user_id,
                    'knowledge_id': knowledge_id
                }
            
            knowledge = result.data
            return {
                'success': True,
                'user_id': user_id,
                'knowledge_id': knowledge_id,
                'knowledge': {
                    'id': knowledge['id'],
                    'text': knowledge['text'],
                    'metadata': knowledge['metadata'],
                    'chunk_index': knowledge.get('chunk_index'),
                    'source_document': knowledge.get('source_document'),
                    'created_at': knowledge['created_at'],
                    'updated_at': knowledge['updated_at'],
                    'mcp_address': f"mcp://rag/{user_id}/{knowledge_id}"
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'knowledge_id': knowledge_id
            }

# Global instance
rag_service = RAGService()