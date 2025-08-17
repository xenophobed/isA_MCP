#!/usr/bin/env python3
"""
Digital Analytics Service with Enhanced RAG and Policy-Based Vector Database Selection

This service integrates the enhanced RAG system with policy-based configuration for 
vector database selection, parallel processing, and comprehensive analytics capabilities.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class VectorDBPolicy(Enum):
    """Policy for selecting vector database backend"""
    AUTO = "auto"  # Automatic selection based on data size and requirements
    PERFORMANCE = "performance"  # Prefer high-performance options (Qdrant)
    STORAGE = "storage"  # Prefer persistent storage (Supabase)
    MEMORY = "memory"  # Prefer in-memory options (ChromaDB)
    COST_OPTIMIZED = "cost_optimized"  # Prefer cost-effective options

class ProcessingMode(Enum):
    """Processing mode for different workloads"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"
    STREAMING = "streaming"

@dataclass
class AnalyticsConfig:
    """Configuration for digital analytics service"""
    vector_db_policy: VectorDBPolicy = VectorDBPolicy.AUTO
    processing_mode: ProcessingMode = ProcessingMode.PARALLEL
    max_parallel_workers: int = 4
    enable_guardrails: bool = True
    guardrail_confidence_threshold: float = 0.7
    enable_mmr_reranking: bool = True
    mmr_lambda: float = 0.5
    enable_incremental_updates: bool = True
    chunk_size: int = 1000
    overlap_size: int = 100
    
    # RAG specific settings
    hybrid_search_enabled: bool = True
    semantic_weight: float = 0.7
    lexical_weight: float = 0.3
    top_k_results: int = 5
    
    # Performance tuning
    enable_caching: bool = True
    cache_ttl_minutes: int = 30
    enable_async_processing: bool = True
    
    # Integration settings
    enable_pdf_processing: bool = True
    enable_large_file_processing: bool = True
    max_file_size_mb: int = 100

class DigitalAnalyticsService:
    """
    Enhanced Digital Analytics Service
    
    Provides intelligent analytics with:
    - Policy-based vector database selection
    - Parallel file processing
    - Advanced RAG with hybrid search
    - Guardrail system for quality control
    - Comprehensive knowledge management
    - Integrated RAG service component
    """
    
    def __init__(self, config: Optional[AnalyticsConfig] = None):
        """
        Initialize Digital Analytics Service
        
        Args:
            config: Service configuration
        """
        self.config = config or AnalyticsConfig()
        self._vector_db = None
        self._embedding_generator = None
        self._guardrail_system = None
        self._rag_service = None
        
        # Initialize components lazily
        self._setup_logging()
        
        logger.info(f"DigitalAnalyticsService initialized with policy: {self.config.vector_db_policy.value}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    
    @property
    def vector_db(self):
        """Lazy load vector database based on policy"""
        if self._vector_db is None:
            self._vector_db = self._select_vector_db()
        return self._vector_db
    
    @property
    def embedding_generator(self):
        """Lazy load embedding generator"""
        if self._embedding_generator is None:
            from tools.services.intelligence_service.language.embedding_generator import embedding_generator
            self._embedding_generator = embedding_generator
        return self._embedding_generator
    
    @property 
    def guardrail_system(self):
        """Lazy load guardrail system"""
        if self._guardrail_system is None:
            self._guardrail_system = self._create_guardrail_system()
        return self._guardrail_system
    
    @property
    def rag_service(self):
        """Lazy load RAG service"""
        if self._rag_service is None:
            self._rag_service = self._create_rag_service()
        return self._rag_service
    
    def _select_vector_db(self):
        """
        Select vector database based on policy
        
        Returns:
            Vector database instance
        """
        try:
            from tools.services.intelligence_service.vector_db import (
                get_vector_db, VectorDBType, get_default_config
            )
            
            # Policy-based selection
            if self.config.vector_db_policy == VectorDBPolicy.AUTO:
                # Auto-select based on environment and requirements
                db_type = self._auto_select_db_type()
            elif self.config.vector_db_policy == VectorDBPolicy.PERFORMANCE:
                db_type = VectorDBType.QDRANT
            elif self.config.vector_db_policy == VectorDBPolicy.STORAGE:
                db_type = VectorDBType.SUPABASE
            elif self.config.vector_db_policy == VectorDBPolicy.MEMORY:
                db_type = VectorDBType.CHROMADB
            elif self.config.vector_db_policy == VectorDBPolicy.COST_OPTIMIZED:
                db_type = VectorDBType.SUPABASE  # Usually most cost-effective
            else:
                db_type = VectorDBType.SUPABASE  # Default fallback
            
            # Get appropriate configuration
            config = get_default_config(db_type)
            
            # Apply service-specific overrides
            if db_type == VectorDBType.SUPABASE:
                config.update({
                    'enable_hybrid_search': self.config.hybrid_search_enabled,
                    'semantic_weight': self.config.semantic_weight,
                    'lexical_weight': self.config.lexical_weight
                })
            
            logger.info(f"Selected vector database: {db_type.value} (policy: {self.config.vector_db_policy.value})")
            return get_vector_db(db_type, config)
            
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            # Fallback to default
            from tools.services.intelligence_service.vector_db import get_vector_db
            return get_vector_db()
    
    def _auto_select_db_type(self):
        """
        Automatically select database type based on environment
        
        Returns:
            VectorDBType: Selected database type
        """
        from tools.services.intelligence_service.vector_db import VectorDBType
        
        # Check environment variables for explicit configuration
        env_db_type = os.getenv('VECTOR_DB_TYPE')
        if env_db_type:
            try:
                return VectorDBType(env_db_type.lower())
            except ValueError:
                pass
        
        # Check what's available and prefer in order: Supabase > Qdrant > ChromaDB
        try:
            # Test Supabase availability
            supabase_url = os.getenv('SUPABASE_URL')
            if supabase_url:
                return VectorDBType.SUPABASE
        except:
            pass
        
        try:
            # Test Qdrant availability
            import qdrant_client
            return VectorDBType.QDRANT
        except ImportError:
            pass
        
        try:
            # Test ChromaDB availability
            import chromadb
            return VectorDBType.CHROMADB
        except ImportError:
            pass
        
        # Final fallback
        return VectorDBType.SUPABASE
    
    def _create_guardrail_system(self):
        """
        Create guardrail system for quality control
        
        Returns:
            Guardrail system instance
        """
        if not self.config.enable_guardrails:
            return None
        
        try:
            from tools.services.intelligence_service.guardrails.guardrail_system import GuardrailSystem, GuardrailConfig
            
            config = GuardrailConfig(
                confidence_threshold=self.config.guardrail_confidence_threshold
            )
            return GuardrailSystem(config)
        except ImportError:
            logger.warning("Guardrail system not available, proceeding without guardrails")
            return None
    
    def _create_rag_service(self):
        """
        Create RAG service component
        
        Returns:
            RAG service instance
        """
        try:
            from tools.services.data_analytics_service.services.digital_service.rag_service import RAGService
            
            # Configure RAG service with analytics service settings
            rag_config = {
                'chunk_size': self.config.chunk_size,
                'overlap': self.config.overlap_size,
                'top_k': self.config.top_k_results,
                'embedding_model': 'text-embedding-3-small',
                'enable_rerank': self.config.enable_mmr_reranking
            }
            
            return RAGService(rag_config)
        except ImportError as e:
            logger.error(f"Failed to load RAG service: {e}")
            return None
    
    async def enhanced_search(
        self,
        query: str,
        user_id: str,
        search_mode: str = "hybrid",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform enhanced search with policy-based backend selection
        
        Args:
            query: Search query
            user_id: User identifier
            search_mode: Search mode ("semantic", "lexical", "hybrid")
            **kwargs: Additional search parameters
            
        Returns:
            Search results with metadata
        """
        try:
            start_time = datetime.now()
            
            # Use enhanced search with automatic method selection
            from tools.services.intelligence_service.language.embedding_generator import enhanced_search
            
            results = await enhanced_search(
                query_text=query,
                user_id=user_id,
                top_k=kwargs.get('top_k', self.config.top_k_results),
                search_mode=search_mode,
                use_local_db=True,
                **kwargs
            )
            
            # Apply MMR reranking if enabled
            if self.config.enable_mmr_reranking and results:
                from tools.services.intelligence_service.language.embedding_generator import mmr_rerank
                
                documents = [result['text'] for result in results]
                mmr_results = await mmr_rerank(
                    query=query,
                    documents=documents,
                    lambda_param=self.config.mmr_lambda,
                    top_k=len(results)
                )
                
                # Merge MMR scores with original results
                for i, result in enumerate(results):
                    if i < len(mmr_results):
                        result['mmr_score'] = mmr_results[i]['score']
                        result['final_score'] = (result['score'] + mmr_results[i]['score']) / 2
                    else:
                        result['mmr_score'] = result['score']
                        result['final_score'] = result['score']
            
            # Apply guardrails if enabled
            if self.guardrail_system:
                results = await self._apply_guardrails(query, results)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'results': results,
                'query': query,
                'user_id': user_id,
                'search_mode': search_mode,
                'processing_time_seconds': processing_time,
                'vector_db_type': self.vector_db.__class__.__name__,
                'policy': self.config.vector_db_policy.value,
                'total_results': len(results),
                'mmr_enabled': self.config.enable_mmr_reranking,
                'guardrails_enabled': self.config.enable_guardrails
            }
            
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'user_id': user_id
            }
    
    async def process_documents_parallel(
        self,
        documents: List[Dict[str, Any]],
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process multiple documents in parallel
        
        Args:
            documents: List of documents to process
            user_id: User identifier
            **kwargs: Additional processing parameters
            
        Returns:
            Processing results
        """
        try:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            start_time = datetime.now()
            
            if self.config.processing_mode == ProcessingMode.SEQUENTIAL:
                results = []
                for doc in documents:
                    result = await self._process_single_document(doc, user_id, **kwargs)
                    results.append(result)
            
            elif self.config.processing_mode == ProcessingMode.PARALLEL:
                # Process in parallel batches
                semaphore = asyncio.Semaphore(self.config.max_parallel_workers)
                
                async def process_with_semaphore(doc):
                    async with semaphore:
                        return await self._process_single_document(doc, user_id, **kwargs)
                
                tasks = [process_with_semaphore(doc) for doc in documents]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle exceptions
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Document {i} processing failed: {result}")
                        processed_results.append({
                            'success': False,
                            'error': str(result),
                            'document_index': i
                        })
                    else:
                        processed_results.append(result)
                results = processed_results
            
            else:
                # Batch processing
                batch_size = kwargs.get('batch_size', self.config.chunk_size)
                results = []
                
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    batch_results = await self._process_document_batch(batch, user_id, **kwargs)
                    results.extend(batch_results)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            successful_count = sum(1 for r in results if r.get('success', False))
            
            return {
                'success': True,
                'total_documents': len(documents),
                'successful_count': successful_count,
                'failed_count': len(documents) - successful_count,
                'processing_time_seconds': processing_time,
                'processing_mode': self.config.processing_mode.value,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Parallel document processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_documents': len(documents)
            }
    
    async def _process_single_document(
        self,
        document: Dict[str, Any],
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a single document"""
        try:
            doc_text = document.get('text', document.get('content', ''))
            doc_metadata = document.get('metadata', {})
            
            # Check file size limits
            if len(doc_text) > self.config.max_file_size_mb * 1024 * 1024:
                return {
                    'success': False,
                    'error': 'Document too large',
                    'document': document.get('id', 'unknown')
                }
            
            # Generate chunks if document is large
            if len(doc_text) > self.config.chunk_size:
                chunks = await self.embedding_generator.chunk_text(
                    text=doc_text,
                    chunk_size=self.config.chunk_size,
                    overlap=self.config.overlap_size,
                    metadata=doc_metadata
                )
                
                # Store each chunk
                stored_chunks = []
                for chunk in chunks:
                    store_result = await self._store_chunk(chunk, user_id)
                    stored_chunks.append(store_result)
                
                return {
                    'success': True,
                    'document': document.get('id', 'unknown'),
                    'chunks_stored': len(stored_chunks),
                    'chunks': stored_chunks
                }
            else:
                # Store as single document
                from tools.services.intelligence_service.language.embedding_generator import store_knowledge_local
                
                result = await store_knowledge_local(
                    user_id=user_id,
                    text=doc_text,
                    metadata=doc_metadata
                )
                
                return {
                    'success': result.get('success', False),
                    'document': document.get('id', 'unknown'),
                    'storage_result': result
                }
                
        except Exception as e:
            logger.error(f"Single document processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'document': document.get('id', 'unknown')
            }
    
    async def _store_chunk(self, chunk: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Store a document chunk"""
        try:
            from tools.services.intelligence_service.language.embedding_generator import store_knowledge_local
            
            return await store_knowledge_local(
                user_id=user_id,
                text=chunk.get('text', ''),
                metadata=chunk.get('metadata', {})
            )
        except Exception as e:
            logger.error(f"Chunk storage failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _process_document_batch(
        self,
        batch: List[Dict[str, Any]],
        user_id: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Process a batch of documents"""
        results = []
        for doc in batch:
            result = await self._process_single_document(doc, user_id, **kwargs)
            results.append(result)
        return results
    
    async def _apply_guardrails(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply guardrails to filter and validate results"""
        if not self.guardrail_system:
            return results
        
        try:
            # Apply guardrail validation
            validated_results = []
            for result in results:
                if await self.guardrail_system.validate_result(query, result):
                    validated_results.append(result)
                else:
                    logger.debug(f"Guardrail filtered result: {result.get('id', 'unknown')}")
            
            return validated_results
        except Exception as e:
            logger.error(f"Guardrail application failed: {e}")
            return results
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        try:
            stats = {
                'service_name': 'DigitalAnalyticsService',
                'config': {
                    'vector_db_policy': self.config.vector_db_policy.value,
                    'processing_mode': self.config.processing_mode.value,
                    'max_parallel_workers': self.config.max_parallel_workers,
                    'hybrid_search_enabled': self.config.hybrid_search_enabled,
                    'mmr_reranking_enabled': self.config.enable_mmr_reranking,
                    'guardrails_enabled': self.config.enable_guardrails
                },
                'vector_db_type': self.vector_db.__class__.__name__ if self._vector_db else 'Not initialized',
                'components': {
                    'vector_db_initialized': self._vector_db is not None,
                    'embedding_generator_initialized': self._embedding_generator is not None,
                    'guardrail_system_initialized': self._guardrail_system is not None,
                    'rag_service_initialized': self._rag_service is not None
                }
            }
            
            # Get vector DB stats if available
            if self._vector_db:
                try:
                    vector_stats = await self._vector_db.get_stats()
                    stats['vector_db_stats'] = vector_stats
                except:
                    stats['vector_db_stats'] = {'error': 'Stats not available'}
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get service stats: {e}")
            return {'error': str(e)}
    
    async def configure_policy(
        self,
        policy: VectorDBPolicy,
        additional_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Dynamically reconfigure vector database policy
        
        Args:
            policy: New vector database policy
            additional_config: Additional configuration parameters
            
        Returns:
            Configuration result
        """
        try:
            old_policy = self.config.vector_db_policy
            self.config.vector_db_policy = policy
            
            # Apply additional configuration
            if additional_config:
                for key, value in additional_config.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
            
            # Reset vector DB to force reinitialization with new policy
            self._vector_db = None
            
            logger.info(f"Policy changed from {old_policy.value} to {policy.value}")
            
            return {
                'success': True,
                'old_policy': old_policy.value,
                'new_policy': policy.value,
                'additional_config': additional_config
            }
            
        except Exception as e:
            logger.error(f"Policy configuration failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # RAG Service Integration Methods
    async def store_knowledge(
        self,
        user_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store knowledge using integrated RAG service"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            result = await self.rag_service.store_knowledge(user_id, text, metadata)
            
            # Apply guardrails if enabled
            if self.guardrail_system and result.get('success'):
                # Validate stored content
                guardrail_result = await self._apply_guardrails(text, [{'text': text}])
                if not guardrail_result:
                    logger.warning(f"Guardrail validation failed for stored knowledge: {user_id}")
            
            return result
        except Exception as e:
            logger.error(f"Knowledge storage failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def search_knowledge(
        self,
        user_id: str,
        query: str,
        top_k: int = None,
        enable_rerank: bool = None,
        search_mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """Search knowledge using integrated RAG service with analytics enhancements"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            # Use service defaults if not specified
            top_k = top_k or self.config.top_k_results
            enable_rerank = enable_rerank if enable_rerank is not None else self.config.enable_mmr_reranking
            
            result = await self.rag_service.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=top_k,
                enable_rerank=enable_rerank,
                search_mode=search_mode,
                use_enhanced_search=False  # Use traditional search by default for compatibility
            )
            
            # Apply guardrails to results if enabled
            if self.guardrail_system and result.get('success') and result.get('search_results'):
                filtered_results = await self._apply_guardrails(query, result['search_results'])
                result['search_results'] = filtered_results
                result['guardrails_applied'] = True
            
            return result
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def generate_rag_response(
        self,
        user_id: str,
        query: str,
        context_limit: int = None
    ) -> Dict[str, Any]:
        """Generate RAG response using integrated service"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            context_limit = context_limit or 3
            result = await self.rag_service.generate_response(user_id, query, context_limit)
            
            # Apply guardrails to generated response if enabled
            if self.guardrail_system and result.get('success') and result.get('response'):
                guardrail_result = await self._apply_guardrails(query, [{'text': result['response']}])
                if not guardrail_result:
                    result['guardrail_warning'] = 'Generated response may not meet quality standards'
            
            return result
        except Exception as e:
            logger.error(f"RAG response generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def add_document(
        self,
        user_id: str,
        document: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add document using integrated RAG service"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            # Use service defaults if not specified
            chunk_size = chunk_size or self.config.chunk_size
            overlap = overlap or self.config.overlap_size
            
            result = await self.rag_service.add_document(user_id, document, chunk_size, overlap, metadata)
            return result
        except Exception as e:
            logger.error(f"Document addition failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def list_user_knowledge(self, user_id: str) -> Dict[str, Any]:
        """List user knowledge using integrated RAG service"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            result = await self.rag_service.list_user_knowledge(user_id)
            return result
        except Exception as e:
            logger.error(f"Knowledge listing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_knowledge_item(self, user_id: str, knowledge_id: str) -> Dict[str, Any]:
        """Get knowledge item using integrated RAG service"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            result = await self.rag_service.get_knowledge(user_id, knowledge_id)
            return result
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def delete_knowledge_item(self, user_id: str, knowledge_id: str) -> Dict[str, Any]:
        """Delete knowledge item using integrated RAG service"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            result = await self.rag_service.delete_knowledge(user_id, knowledge_id)
            return result
        except Exception as e:
            logger.error(f"Knowledge deletion failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        top_k: int = None,
        search_mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """Retrieve context using integrated RAG service"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            top_k = top_k or self.config.top_k_results
            result = await self.rag_service.retrieve_context(
                user_id=user_id,
                query=query,
                top_k=top_k,
                search_mode=search_mode,
                use_enhanced_search=True
            )
            return result
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return {'success': False, 'error': str(e)}

# Global service instance
_digital_analytics_service = None

def get_digital_analytics_service(config: Optional[AnalyticsConfig] = None) -> DigitalAnalyticsService:
    """Get singleton instance of Digital Analytics Service"""
    global _digital_analytics_service
    if _digital_analytics_service is None:
        _digital_analytics_service = DigitalAnalyticsService(config)
    return _digital_analytics_service

def create_digital_analytics_service(config: Optional[AnalyticsConfig] = None) -> DigitalAnalyticsService:
    """Create new instance of Digital Analytics Service"""
    global _digital_analytics_service
    _digital_analytics_service = DigitalAnalyticsService(config)
    return _digital_analytics_service

# Convenience functions for common operations
async def search_with_policy(
    query: str,
    user_id: str,
    policy: VectorDBPolicy = VectorDBPolicy.AUTO,
    **kwargs
) -> Dict[str, Any]:
    """Search with specific vector database policy"""
    service = get_digital_analytics_service()
    await service.configure_policy(policy)
    return await service.enhanced_search(query, user_id, **kwargs)

async def process_files_parallel(
    files: List[Dict[str, Any]],
    user_id: str,
    processing_mode: ProcessingMode = ProcessingMode.PARALLEL,
    **kwargs
) -> Dict[str, Any]:
    """Process files with specified processing mode"""
    config = AnalyticsConfig(processing_mode=processing_mode)
    service = get_digital_analytics_service(config)
    return await service.process_documents_parallel(files, user_id, **kwargs)

# RAG Service Integration Methods
async def store_knowledge(
    user_id: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Store knowledge using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.store_knowledge(user_id, text, metadata)

async def search_knowledge(
    user_id: str,
    query: str,
    top_k: int = 5,
    enable_rerank: bool = False,
    search_mode: str = "hybrid"
) -> Dict[str, Any]:
    """Search knowledge using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.search_knowledge(user_id, query, top_k, enable_rerank, search_mode)

async def generate_rag_response(
    user_id: str,
    query: str,
    context_limit: int = 3
) -> Dict[str, Any]:
    """Generate RAG response using integrated service"""
    service = get_digital_analytics_service()
    return await service.generate_rag_response(user_id, query, context_limit)

async def add_document(
    user_id: str,
    document: str,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Add document using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.add_document(user_id, document, chunk_size, overlap, metadata)

async def list_user_knowledge(user_id: str) -> Dict[str, Any]:
    """List user knowledge using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.list_user_knowledge(user_id)

async def get_knowledge_item(user_id: str, knowledge_id: str) -> Dict[str, Any]:
    """Get knowledge item using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.get_knowledge_item(user_id, knowledge_id)

async def delete_knowledge_item(user_id: str, knowledge_id: str) -> Dict[str, Any]:
    """Delete knowledge item using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.delete_knowledge_item(user_id, knowledge_id)

async def retrieve_context(
    user_id: str,
    query: str,
    top_k: int = 5,
    search_mode: str = "hybrid"
) -> Dict[str, Any]:
    """Retrieve context using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.retrieve_context(user_id, query, top_k, search_mode)