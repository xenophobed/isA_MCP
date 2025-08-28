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
    
    # Digital Asset Processing settings
    enable_digital_asset_processing: bool = True
    enable_ai_enhancement: bool = True
    ai_enhancement_threshold: float = 0.7
    asset_processing_mode: str = "comprehensive"  # fast, comprehensive, selective
    enable_cross_asset_analysis: bool = True
    max_asset_processing_time: int = 600  # 10 minutes

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
    
    @property
    def enhanced_unified_processor(self):
        """Lazy load enhanced unified processor for digital assets"""
        if not hasattr(self, '_enhanced_unified_processor') or self._enhanced_unified_processor is None:
            if self.config.enable_digital_asset_processing:
                try:
                    from tools.services.data_analytics_service.processors.file_processors import EnhancedUnifiedProcessor
                    processor_config = {
                        'enable_ai_enhancement': self.config.enable_ai_enhancement,
                        'ai_enhancement_threshold': self.config.ai_enhancement_threshold,
                        'max_processing_time': self.config.max_asset_processing_time,
                        'unified': {
                            'processing_mode': self.config.asset_processing_mode,
                            'enable_cross_analysis': self.config.enable_cross_asset_analysis
                        },
                        'ai_enhancement': {
                            'enable_ai_enhancement': self.config.enable_ai_enhancement,
                            'ai_enhancement_threshold': self.config.ai_enhancement_threshold
                        }
                    }
                    self._enhanced_unified_processor = EnhancedUnifiedProcessor(processor_config)
                    logger.info("Enhanced unified processor initialized successfully")
                except ImportError as e:
                    logger.error(f"Failed to initialize enhanced unified processor: {e}")
                    self._enhanced_unified_processor = None
            else:
                self._enhanced_unified_processor = None
        return self._enhanced_unified_processor
    
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
    
    # === DIGITAL ASSET PROCESSING METHODS ===
    
    async def process_digital_asset(
        self,
        file_path: str,
        user_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a digital asset with enhanced capabilities.
        
        Args:
            file_path: Path to the digital asset file
            user_id: User identifier for knowledge storage
            options: Processing options
            
        Returns:
            Enhanced processing results
        """
        try:
            if not self.config.enable_digital_asset_processing:
                return {'success': False, 'error': 'Digital asset processing disabled'}
            
            if not self.enhanced_unified_processor:
                return {'success': False, 'error': 'Enhanced unified processor not available'}
            
            start_time = datetime.now()
            options = options or {}
            
            # Set default options based on service configuration
            options.setdefault('enable_ai', self.config.enable_ai_enhancement)
            options.setdefault('ai_threshold', self.config.ai_enhancement_threshold)
            options.setdefault('processing_mode', self.config.asset_processing_mode)
            
            # Process the asset
            result = await self.enhanced_unified_processor.process_asset_enhanced(file_path, options)
            
            # Store knowledge if processing was successful and contains text
            if (result.get('success') and 
                options.get('store_knowledge', True) and 
                user_id):
                
                await self._store_asset_knowledge(file_path, result, user_id)
            
            # Apply guardrails if enabled
            if self.guardrail_system and result.get('success'):
                result = await self._apply_asset_guardrails(result)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            result['service_processing_time'] = processing_time
            result['user_id'] = user_id
            
            return result
            
        except Exception as e:
            logger.error(f"Digital asset processing failed for {file_path}: {e}")
            return {
                'file_path': file_path,
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def process_multiple_assets(
        self,
        file_paths: List[str],
        user_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process multiple digital assets with cross-correlation analysis.
        
        Args:
            file_paths: List of file paths to process
            user_id: User identifier
            options: Processing options
            
        Returns:
            Batch processing results with cross-analysis
        """
        try:
            if not self.config.enable_digital_asset_processing:
                return {'success': False, 'error': 'Digital asset processing disabled'}
            
            if not self.enhanced_unified_processor:
                return {'success': False, 'error': 'Enhanced unified processor not available'}
            
            start_time = datetime.now()
            options = options or {}
            
            # Set default options
            options.setdefault('enable_ai', self.config.enable_ai_enhancement)
            options.setdefault('enable_cross_analysis', self.config.enable_cross_asset_analysis)
            options.setdefault('store_knowledge', True)
            
            # Process assets in batch
            batch_result = await self.enhanced_unified_processor.process_batch_enhanced(file_paths, options)
            
            # Store knowledge for successful results
            if options.get('store_knowledge', True) and user_id:
                successful_results = batch_result.get('successful_results', [])
                for result in successful_results:
                    try:
                        await self._store_asset_knowledge(result['file_path'], result, user_id)
                    except Exception as e:
                        logger.warning(f"Knowledge storage failed for {result.get('file_path')}: {e}")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            batch_result['service_processing_time'] = processing_time
            batch_result['user_id'] = user_id
            
            return batch_result
            
        except Exception as e:
            logger.error(f"Multiple asset processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_files': len(file_paths) if file_paths else 0,
                'user_id': user_id
            }
    
    async def analyze_asset_correlations(
        self,
        file_paths: List[str],
        user_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze correlations and relationships between multiple assets.
        
        Args:
            file_paths: List of file paths to analyze
            user_id: User identifier
            options: Analysis options
            
        Returns:
            Correlation analysis results
        """
        try:
            if not self.config.enable_cross_asset_analysis:
                return {'success': False, 'error': 'Cross-asset analysis disabled'}
            
            # Process assets first if needed
            results = await self.process_multiple_assets(file_paths, user_id, options)
            
            if not results.get('successful_results'):
                return {'success': False, 'error': 'No successful asset processing results for correlation analysis'}
            
            # Extract correlation data
            correlation_data = await self._extract_correlation_features(results['successful_results'])
            
            # Perform enhanced correlation analysis
            correlation_analysis = await self._perform_correlation_analysis(correlation_data)
            
            return {
                'success': True,
                'correlation_analysis': correlation_analysis,
                'asset_count': len(file_paths),
                'processed_count': results.get('successful_count', 0),
                'user_id': user_id
            }
            
        except Exception as e:
            logger.error(f"Asset correlation analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def get_asset_processing_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive asset processing capabilities."""
        try:
            if not self.enhanced_unified_processor:
                return {
                    'digital_asset_processing_enabled': False,
                    'error': 'Enhanced unified processor not available'
                }
            
            capabilities = await self.enhanced_unified_processor.get_comprehensive_capabilities()
            
            return {
                'digital_asset_processing_enabled': self.config.enable_digital_asset_processing,
                'ai_enhancement_enabled': self.config.enable_ai_enhancement,
                'cross_asset_analysis_enabled': self.config.enable_cross_asset_analysis,
                'asset_processing_mode': self.config.asset_processing_mode,
                'capabilities': capabilities,
                'service_integration': {
                    'vector_db_integration': True,
                    'rag_service_integration': True,
                    'guardrail_system_integration': self.config.enable_guardrails,
                    'knowledge_storage_integration': True
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get asset processing capabilities: {e}")
            return {
                'digital_asset_processing_enabled': False,
                'error': str(e)
            }
    
    # === HELPER METHODS FOR DIGITAL ASSET PROCESSING ===
    
    async def _store_asset_knowledge(
        self,
        file_path: str,
        processing_result: Dict[str, Any],
        user_id: str
    ) -> None:
        """Store knowledge extracted from digital asset processing."""
        try:
            # Extract text content from processing results
            text_content = self._extract_text_from_processing_result(processing_result)
            
            if not text_content or len(text_content.strip()) < 10:
                logger.debug(f"No significant text content to store for {file_path}")
                return
            
            # Create metadata
            metadata = {
                'source_file': Path(file_path).name,
                'file_path': file_path,
                'asset_type': processing_result.get('asset_type', 'unknown'),
                'processing_timestamp': datetime.now().isoformat(),
                'ai_enhanced': processing_result.get('ai_enhancement_enabled', False),
                'quality_score': processing_result.get('enhanced_processing', {}).get('quality_score', 0.0),
                'processing_mode': processing_result.get('enhanced_processing', {}).get('processing_mode', 'standard')
            }
            
            # Store in RAG service
            if self.rag_service:
                store_result = await self.rag_service.store_knowledge(
                    user_id=user_id,
                    text=text_content,
                    metadata=metadata
                )
                
                if store_result.get('success'):
                    logger.info(f"Successfully stored knowledge for {Path(file_path).name}")
                else:
                    logger.warning(f"Failed to store knowledge for {Path(file_path).name}: {store_result.get('error')}")
            else:
                logger.warning("RAG service not available for knowledge storage")
                
        except Exception as e:
            logger.error(f"Knowledge storage failed for {file_path}: {e}")
    
    def _extract_text_from_processing_result(self, result: Dict[str, Any]) -> str:
        """Extract all available text from processing results."""
        text_parts = []
        
        # Traditional processing results
        traditional = result.get('traditional_processing', {}).get('results', {})
        enhanced = result.get('enhanced_processing', {})
        
        # Common text fields to extract
        text_fields = [
            'text', 'combined_text', 'full_text', 'transcript', 
            'content', 'extracted_text', 'ocr_text'
        ]
        
        # Extract from traditional results
        for field in text_fields:
            if field in traditional and traditional[field]:
                text_parts.append(str(traditional[field]))
        
        # Extract from enhanced results
        for field in text_fields:
            if field in enhanced and enhanced[field]:
                text_parts.append(str(enhanced[field]))
        
        # Extract from AI analysis
        ai_analysis = enhanced.get('ai_content_analysis', {})
        if ai_analysis.get('analysis'):
            text_parts.append(str(ai_analysis['analysis']))
        
        # Extract insights and recommendations
        ai_insights = enhanced.get('ai_insights_and_recommendations', {})
        if ai_insights.get('insights'):
            text_parts.append(f"Insights: {ai_insights['insights']}")
        if ai_insights.get('recommendations'):
            text_parts.append(f"Recommendations: {ai_insights['recommendations']}")
        
        return '\n\n'.join(filter(None, text_parts))
    
    async def _apply_asset_guardrails(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply guardrails to asset processing results."""
        if not self.guardrail_system:
            return result
        
        try:
            # Extract text for guardrail validation
            text_content = self._extract_text_from_processing_result(result)
            
            if text_content:
                # Apply guardrails
                guardrail_result = await self.guardrail_system.validate_content(text_content)
                
                # Add guardrail information to result
                result['guardrail_validation'] = {
                    'validated': True,
                    'passed': guardrail_result.get('passed', True),
                    'confidence': guardrail_result.get('confidence', 1.0),
                    'warnings': guardrail_result.get('warnings', []),
                    'compliance_score': guardrail_result.get('compliance_score', 1.0)
                }
                
                if not guardrail_result.get('passed', True):
                    logger.warning(f"Guardrail validation failed for asset processing")
            
            return result
            
        except Exception as e:
            logger.error(f"Guardrail application failed: {e}")
            result['guardrail_validation'] = {
                'validated': False,
                'error': str(e)
            }
            return result
    
    async def _extract_correlation_features(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract features for correlation analysis."""
        try:
            correlation_features = {
                'assets': [],
                'content_themes': [],
                'quality_scores': [],
                'asset_types': [],
                'processing_metadata': []
            }
            
            for result in results:
                file_path = result.get('file_path', '')
                asset_type = result.get('asset_type', 'unknown')
                enhanced = result.get('enhanced_processing', {})
                
                # Extract features
                asset_features = {
                    'file_name': Path(file_path).name,
                    'asset_type': asset_type,
                    'quality_score': enhanced.get('quality_score', 0.0),
                    'text_content': self._extract_text_from_processing_result(result),
                    'ai_insights': enhanced.get('ai_insights_and_recommendations', {}),
                    'processing_time': result.get('processing_time', 0.0)
                }
                
                correlation_features['assets'].append(asset_features)
                correlation_features['quality_scores'].append(asset_features['quality_score'])
                correlation_features['asset_types'].append(asset_type)
            
            return correlation_features
            
        except Exception as e:
            logger.error(f"Feature extraction for correlation analysis failed: {e}")
            return {'error': str(e)}
    
    async def _perform_correlation_analysis(self, correlation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform enhanced correlation analysis on assets."""
        try:
            if 'error' in correlation_data:
                return correlation_data
            
            assets = correlation_data.get('assets', [])
            if len(assets) < 2:
                return {'error': 'Need at least 2 assets for correlation analysis'}
            
            # Basic statistical analysis
            quality_scores = correlation_data.get('quality_scores', [])
            asset_types = correlation_data.get('asset_types', [])
            
            analysis = {
                'statistical_summary': {
                    'asset_count': len(assets),
                    'average_quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
                    'quality_variance': self._calculate_variance(quality_scores),
                    'asset_type_distribution': self._calculate_distribution(asset_types)
                },
                'content_correlations': await self._analyze_content_correlations(assets),
                'thematic_analysis': await self._analyze_themes(assets),
                'recommendations': await self._generate_correlation_recommendations(assets)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_content_correlations(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze content correlations between assets."""
        try:
            # Simple keyword-based correlation for now
            all_texts = [asset.get('text_content', '') for asset in assets]
            
            # Extract keywords from each text
            correlations = []
            for i, text1 in enumerate(all_texts):
                for j, text2 in enumerate(all_texts[i+1:], start=i+1):
                    similarity = self._calculate_text_similarity(text1, text2)
                    correlations.append({
                        'asset1': assets[i]['file_name'],
                        'asset2': assets[j]['file_name'],
                        'similarity_score': similarity
                    })
            
            return {
                'correlations': correlations,
                'high_correlation_pairs': [c for c in correlations if c['similarity_score'] > 0.7]
            }
            
        except Exception as e:
            logger.error(f"Content correlation analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_themes(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze common themes across assets."""
        try:
            # Extract insights from all assets
            all_insights = []
            for asset in assets:
                insights = asset.get('ai_insights', {})
                if insights.get('insights'):
                    all_insights.append(insights['insights'])
            
            # Simple thematic analysis
            common_keywords = self._extract_common_keywords(all_insights)
            
            return {
                'common_themes': common_keywords[:10],  # Top 10 themes
                'theme_distribution': self._calculate_keyword_distribution(all_insights),
                'asset_theme_mapping': self._map_assets_to_themes(assets, common_keywords)
            }
            
        except Exception as e:
            logger.error(f"Thematic analysis failed: {e}")
            return {'error': str(e)}
    
    async def _generate_correlation_recommendations(self, assets: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on correlation analysis."""
        try:
            recommendations = []
            
            # Quality-based recommendations
            quality_scores = [asset.get('quality_score', 0.0) for asset in assets]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            if avg_quality < 0.6:
                recommendations.append("Consider improving asset quality through enhanced processing or better source materials")
            
            # Asset type diversity recommendations
            asset_types = [asset.get('asset_type') for asset in assets]
            type_diversity = len(set(asset_types)) / len(asset_types) if asset_types else 0.0
            
            if type_diversity > 0.7:
                recommendations.append("High asset type diversity detected - consider creating unified documentation or cross-references")
            elif type_diversity < 0.3:
                recommendations.append("Low asset type diversity - consider expanding with complementary asset types")
            
            # Content-based recommendations
            if len(assets) > 5:
                recommendations.append("Large asset collection detected - consider implementing automated categorization or indexing")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return [f"Recommendation generation failed: {str(e)}"]
    
    # === UTILITY METHODS ===
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def _calculate_distribution(self, items: List[str]) -> Dict[str, int]:
        """Calculate distribution of items."""
        distribution = {}
        for item in items:
            distribution[item] = distribution.get(item, 0) + 1
        return distribution
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_common_keywords(self, texts: List[str]) -> List[str]:
        """Extract common keywords from texts."""
        if not texts:
            return []
        
        # Simple keyword extraction
        all_words = []
        for text in texts:
            words = [w.lower() for w in text.split() if len(w) > 3]
            all_words.extend(words)
        
        # Count frequencies
        word_counts = {}
        for word in all_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Return most common words
        return sorted(word_counts.keys(), key=lambda x: word_counts[x], reverse=True)
    
    def _calculate_keyword_distribution(self, texts: List[str]) -> Dict[str, int]:
        """Calculate keyword distribution."""
        keywords = self._extract_common_keywords(texts)
        return {kw: texts.count(kw) for kw in keywords[:20]}  # Top 20
    
    def _map_assets_to_themes(self, assets: List[Dict[str, Any]], themes: List[str]) -> Dict[str, List[str]]:
        """Map assets to themes."""
        asset_theme_map = {}
        
        for asset in assets:
            file_name = asset.get('file_name', '')
            text_content = asset.get('text_content', '').lower()
            asset_themes = [theme for theme in themes[:10] if theme in text_content]
            asset_theme_map[file_name] = asset_themes
        
        return asset_theme_map

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

# === DIGITAL ASSET PROCESSING CONVENIENCE FUNCTIONS ===

async def process_digital_asset(
    file_path: str,
    user_id: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Process a digital asset with enhanced capabilities"""
    service = get_digital_analytics_service()
    return await service.process_digital_asset(file_path, user_id, options)

async def process_multiple_assets(
    file_paths: List[str],
    user_id: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Process multiple digital assets with cross-correlation analysis"""
    service = get_digital_analytics_service()
    return await service.process_multiple_assets(file_paths, user_id, options)

async def analyze_asset_correlations(
    file_paths: List[str],
    user_id: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Analyze correlations and relationships between multiple assets"""
    service = get_digital_analytics_service()
    return await service.analyze_asset_correlations(file_paths, user_id, options)

async def get_asset_processing_capabilities() -> Dict[str, Any]:
    """Get comprehensive asset processing capabilities"""
    service = get_digital_analytics_service()
    return await service.get_asset_processing_capabilities()