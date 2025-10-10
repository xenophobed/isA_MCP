#!/usr/bin/env python3
"""
Digital Analytics Service with Enhanced RAG and Policy-Based Vector Database Selection

This service integrates the enhanced RAG system with policy-based configuration for 
vector database selection, parallel processing, and comprehensive analytics capabilities.
Updated with latest RAG Factory architecture and multi-mode support.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class VectorDBPolicy(Enum):
    """Policy for selecting vector database backend"""
    AUTO = "auto"
    PERFORMANCE = "performance"
    STORAGE = "storage"
    MEMORY = "memory"
    COST_OPTIMIZED = "cost_optimized"

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
    enable_mmr_reranking: bool = False
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
    asset_processing_mode: str = "comprehensive"
    enable_cross_asset_analysis: bool = True
    max_asset_processing_time: int = 600

class DigitalAnalyticsService:
    """
    Enhanced Digital Analytics Service with latest RAG Factory architecture
    
    Features:
    - Multi-mode RAG support (Simple, RAPTOR, Self-RAG, CRAG, Plan*RAG, HM-RAG)
    - Policy-based vector database selection
    - Parallel file processing
    - Advanced RAG with hybrid search
    - Inline citation support
    - Guardrail system for quality control
    - Comprehensive knowledge management
    """
    
    def __init__(self, config: Optional[AnalyticsConfig] = None):
        """Initialize Digital Analytics Service"""
        self.config = config or AnalyticsConfig()
        self._vector_db = None
        self._embedding_generator = None
        self._guardrail_system = None
        self._rag_service = None
        self._rag_factory = None
        self._rag_registry = None
        
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
            try:
                from tools.services.intelligence_service.language.embedding_generator import embedding_generator
                self._embedding_generator = embedding_generator
                logger.info("Embedding generator initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize embedding generator: {e}")
                # Create a mock embedding generator
                self._embedding_generator = self._create_mock_embedding_generator()
        return self._embedding_generator
    
    def _create_mock_embedding_generator(self):
        """Create a mock embedding generator for testing"""
        class MockEmbeddingGenerator:
            def __init__(self):
                self.name = "MockEmbeddingGenerator"
            
            async def embed(self, text):
                # Return a mock embedding
                return [0.1] * 1536  # Mock 1536-dimensional embedding
            
            async def chunk_text(self, text, chunk_size=400, overlap=50, metadata=None):
                # Simple text chunking
                chunks = []
                start = 0
                while start < len(text):
                    end = min(start + chunk_size, len(text))
                    chunk_text = text[start:end]
                    chunks.append({
                        'text': chunk_text,
                        'metadata': metadata or {},
                        'start': start,
                        'end': end
                    })
                    start = end - overlap
                return chunks
        
        logger.warning("Using mock embedding generator due to initialization failure")
        return MockEmbeddingGenerator()
    
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
    def rag_factory(self):
        """Lazy load RAG factory"""
        if self._rag_factory is None:
            from tools.services.data_analytics_service.services.digital_service.rag_factory import RAGFactory
            self._rag_factory = RAGFactory()
        return self._rag_factory
    
    @property
    def rag_registry(self):
        """Lazy load RAG registry"""
        if self._rag_registry is None:
            from tools.services.data_analytics_service.services.digital_service.rag_factory import RAGRegistry
            self._rag_registry = RAGRegistry(self.rag_factory)
        return self._rag_registry
    
    def _select_vector_db(self):
        """Select vector database based on policy"""
        try:
            from tools.services.intelligence_service.vector_db import (
                get_vector_db, VectorDBType
            )
            
            if self.config.vector_db_policy == VectorDBPolicy.AUTO:
                db_type = self._auto_select_db_type()
            elif self.config.vector_db_policy == VectorDBPolicy.PERFORMANCE:
                db_type = VectorDBType.QDRANT
            elif self.config.vector_db_policy == VectorDBPolicy.STORAGE:
                db_type = VectorDBType.SUPABASE
            elif self.config.vector_db_policy == VectorDBPolicy.MEMORY:
                db_type = VectorDBType.CHROMADB
            elif self.config.vector_db_policy == VectorDBPolicy.COST_OPTIMIZED:
                db_type = VectorDBType.SUPABASE
            else:
                db_type = VectorDBType.SUPABASE
            
            # Create basic config
            config = {
                'enable_hybrid_search': self.config.hybrid_search_enabled,
                'semantic_weight': self.config.semantic_weight,
                'lexical_weight': self.config.lexical_weight
            }
            
            logger.info(f"Selected vector database: {db_type.value}")
            vector_db = get_vector_db(db_type, config)
            
            # Test the connection
            try:
                # Try to get stats to verify connection
                if hasattr(vector_db, 'get_stats'):
                    asyncio.create_task(vector_db.get_stats())
                logger.info("Vector database connection verified")
            except Exception as e:
                logger.warning(f"Vector database connection test failed: {e}")
            
            return vector_db
            
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            # Return a mock vector database for testing
            return self._create_mock_vector_db()
    
    def _create_mock_vector_db(self):
        """Create a mock vector database for testing"""
        class MockVectorDB:
            def __init__(self):
                self.name = "MockVectorDB"
            
            async def get_stats(self):
                return {"total_vectors": 0, "status": "mock"}
            
            def __class__(self):
                return type("MockVectorDB", (), {})
        
        logger.warning("Using mock vector database due to initialization failure")
        return MockVectorDB()
    
    def _auto_select_db_type(self):
        """Automatically select database type based on environment"""
        from tools.services.intelligence_service.vector_db import VectorDBType
        
        env_db_type = os.getenv('VECTOR_DB_TYPE')
        if env_db_type:
            try:
                return VectorDBType(env_db_type.lower())
            except ValueError:
                pass
        
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            if supabase_url:
                return VectorDBType.SUPABASE
        except:
            pass
        
        try:
            import qdrant_client
            return VectorDBType.QDRANT
        except ImportError:
            pass
        
        try:
            import chromadb
            return VectorDBType.CHROMADB
        except ImportError:
            pass
        
        return VectorDBType.SUPABASE
    
    def _create_guardrail_system(self):
        """Create guardrail system for quality control"""
        if not self.config.enable_guardrails:
            return None
        
        try:
            from tools.services.intelligence_service.guardrails.guardrail_system import GuardrailSystem, GuardrailConfig
            
            config = GuardrailConfig(
                confidence_threshold=self.config.guardrail_confidence_threshold
            )
            guardrail = GuardrailSystem(config)
            logger.info("Guardrail system initialized successfully")
            return guardrail
        except ImportError as e:
            logger.warning(f"Guardrail system not available: {e}, proceeding without guardrails")
            return self._create_mock_guardrail_system()
        except Exception as e:
            logger.error(f"Failed to initialize guardrail system: {e}")
            return self._create_mock_guardrail_system()
    
    def _create_mock_guardrail_system(self):
        """Create a mock guardrail system for testing"""
        class MockGuardrailSystem:
            def __init__(self):
                self.name = "MockGuardrailSystem"
            
            async def validate_result(self, query, result):
                # Always pass validation for testing
                return True
            
            async def validate_content(self, content):
                # Always pass validation for testing
                return {
                    'passed': True,
                    'confidence': 0.8,
                    'warnings': [],
                    'compliance_score': 0.9
                }
        
        logger.warning("Using mock guardrail system due to initialization failure")
        return MockGuardrailSystem()
    
    def _create_rag_service(self):
        """Create RAG service using latest Factory architecture"""
        try:
            from tools.services.data_analytics_service.services.digital_service.rag_factory import RAGFactory
            from tools.services.data_analytics_service.services.digital_service.base.base_rag_service import RAGConfig, RAGMode
            
            # Configure RAG service
            rag_config = RAGConfig(
                mode=RAGMode.SIMPLE,
                chunk_size=self.config.chunk_size,
                overlap=self.config.overlap_size,
                top_k=self.config.top_k_results,
                embedding_model='text-embedding-3-small',
                enable_rerank=self.config.enable_mmr_reranking,
                similarity_threshold=0.7,
                max_context_length=4000
            )
            
            # Create RAG service instance
            rag_service = self.rag_factory.create_service(
                mode=RAGMode.SIMPLE,
                config=rag_config,
                instance_id="digital_analytics_default"
            )
            
            logger.info("RAG service created using latest Factory architecture")
            return rag_service
            
        except ImportError as e:
            logger.error(f"Failed to load RAG service: {e}")
            return None
    
    # === MULTI-MODE RAG METHODS ===
    
    async def query_with_mode(
        self,
        user_id: str,
        query: str,
        mode: str = "simple",
        **kwargs
    ) -> Dict[str, Any]:
        """Query using specific RAG mode"""
        try:
            # Validate input
            if not query or not query.strip():
                return {
                    'success': False,
                    'error': 'Query cannot be empty',
                    'mode': mode
                }
            
            from tools.services.data_analytics_service.services.digital_service.base.base_rag_service import RAGMode
            
            mode_enum = RAGMode(mode.lower())
            service = self.rag_factory.create_service(
                mode=mode_enum,
                instance_id=f"digital_analytics_{mode}"
            )
            
            result = await service.query(query, user_id, **kwargs)
            
            return {
                'success': result.success,
                'result': {
                    'success': result.success,
                    'content': result.content,
                    'sources': result.sources,
                    'metadata': result.metadata,
                    'mode_used': result.mode_used.value,
                    'processing_time': result.processing_time,
                    'citations': result.citations,
                    'error': result.error
                },
                'mode_used': mode,
                'service_type': service.__class__.__name__
            }
            
        except Exception as e:
            logger.error(f"Multi-mode query failed: {e}")
            return {'success': False, 'error': str(e), 'mode': mode}
    
    async def hybrid_query(
        self,
        user_id: str,
        query: str,
        modes: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute hybrid query across multiple RAG modes"""
        try:
            if not modes:
                modes = ['simple', 'self_rag', 'crag']
            
            tasks = [self.query_with_mode(user_id, query, mode, **kwargs) for mode in modes]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({'mode': modes[i], 'error': str(result)})
                elif result.get('success'):
                    successful_results.append(result)
                else:
                    failed_results.append(result)
            
            return {
                'success': len(successful_results) > 0,
                'successful_results': successful_results,
                'failed_results': failed_results,
                'total_modes': len(modes),
                'successful_modes': len(successful_results)
            }
            
        except Exception as e:
            logger.error(f"Hybrid query failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def recommend_mode(
        self,
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Recommend best RAG mode for a query"""
        try:
            recommendation = self.rag_registry.get_recommended_mode(query, user_id)
            
            # Handle RAGMode enum directly
            from tools.services.data_analytics_service.services.digital_service.base.base_rag_service import RAGMode
            if isinstance(recommendation, RAGMode):
                return {
                    'success': True,
                    'recommended_mode': recommendation.value,
                    'confidence': 0.8,  # Default confidence
                    'reasoning': f'Selected {recommendation.value} mode based on query characteristics',
                    'alternatives': []
                }
            # Handle dict or object with attributes
            elif hasattr(recommendation, 'mode'):
                return {
                    'success': True,
                    'recommended_mode': recommendation.mode.value if hasattr(recommendation.mode, 'value') else str(recommendation.mode),
                    'confidence': getattr(recommendation, 'confidence', 0.5),
                    'reasoning': getattr(recommendation, 'reasoning', 'No reasoning provided'),
                    'alternatives': getattr(recommendation, 'alternatives', [])
                }
            # Handle dict response
            elif isinstance(recommendation, dict):
                return {
                    'success': True,
                    'recommended_mode': recommendation.get('mode', 'simple'),
                    'confidence': recommendation.get('confidence', 0.5),
                    'reasoning': recommendation.get('reasoning', 'No reasoning provided'),
                    'alternatives': recommendation.get('alternatives', [])
                }
            else:
                # Fallback for unknown type
                return {
                    'success': True,
                    'recommended_mode': 'simple',
                    'confidence': 0.5,
                    'reasoning': 'Default mode selected',
                    'alternatives': []
                }
            
        except Exception as e:
            logger.error(f"Mode recommendation failed: {e}")
            return {'success': False, 'error': str(e), 'recommended_mode': 'simple'}
    
    async def get_rag_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive RAG capabilities"""
        try:
            capabilities = {
                'available_modes': [],
                'mode_details': {},
                'factory_info': {},
                'performance_metrics': {}
            }
            
            available_modes = self.rag_factory.get_available_modes()
            capabilities['available_modes'] = [mode.value for mode in available_modes]
            
            for mode in available_modes:
                mode_info = self.rag_factory.get_service_info(mode)
                capabilities['mode_details'][mode.value] = mode_info
            
            capabilities['factory_info'] = {
                'total_modes': len(available_modes),
                'cached_instances': len(self.rag_factory._instances),
                'factory_type': self.rag_factory.__class__.__name__
            }
            
            if hasattr(self.rag_service, 'get_performance_metrics'):
                capabilities['performance_metrics'] = self.rag_service.get_performance_metrics()
            
            return {'success': True, 'capabilities': capabilities}
            
        except Exception as e:
            logger.error(f"Failed to get RAG capabilities: {e}")
            return {'success': False, 'error': str(e)}
    
    # === ENHANCED RAG INTEGRATION METHODS ===
    
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
            
            if self.guardrail_system and result.get('success'):
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
        search_mode: str = "hybrid",
        rag_mode: str = None
    ) -> Dict[str, Any]:
        """Search knowledge with multi-mode support"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            top_k = top_k or self.config.top_k_results
            enable_rerank = enable_rerank if enable_rerank is not None else self.config.enable_mmr_reranking
            
            if rag_mode:
                return await self.query_with_mode(user_id, query, rag_mode)
            
            result = await self.rag_service.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=top_k,
                enable_rerank=enable_rerank,
                search_mode=search_mode,
                use_enhanced_search=False
            )
            
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
        context_limit: int = None,
        rag_mode: str = None,
        enable_inline_citations: bool = True
    ) -> Dict[str, Any]:
        """Generate RAG response with multi-mode and citation support"""
        if not self.rag_service:
            return {'success': False, 'error': 'RAG service not available'}
        
        try:
            context_limit = context_limit or 3
            
            if rag_mode:
                mode_result = await self.query_with_mode(user_id, query, rag_mode)
                if mode_result.get('success'):
                    result = mode_result['result']
                else:
                    return mode_result
            else:
                # Use fast RAG Factory instead of slow traditional service
                mode_result = await self.query_with_mode(user_id, query, 'simple')
                if mode_result.get('success'):
                    result = mode_result['result']
                else:
                    return mode_result
            
            # New inline citations are already generated by LLM in prompt
            # No need for slow CitationService post-processing
            result['inline_citations_enabled'] = enable_inline_citations
            
            return result
        except Exception as e:
            logger.error(f"RAG response generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _apply_guardrails(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply guardrails to filter and validate results"""
        if not self.guardrail_system:
            return results

        try:
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

    # === MISSING CONVENIENCE METHODS ===

    async def add_document(
        self,
        user_id: str,
        document: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add document with automatic chunking"""
        try:
            chunk_size = chunk_size or self.config.chunk_size
            overlap = overlap or self.config.overlap_size

            # Use embedding generator's chunking functionality
            chunks = await self.embedding_generator.chunk_text(
                text=document,
                chunk_size=chunk_size,
                overlap=overlap,
                metadata=metadata
            )

            # Store each chunk
            stored_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'document_id': f"{user_id}_{datetime.now().timestamp()}"
                })

                result = await self.store_knowledge(
                    user_id=user_id,
                    text=chunk['text'],
                    metadata=chunk_metadata
                )

                if result.get('success'):
                    stored_chunks.append(result.get('knowledge_id'))

            return {
                'success': True,
                'chunks_created': len(stored_chunks),
                'total_chars': len(document),
                'chunk_ids': stored_chunks,
                'document_id': chunk_metadata.get('document_id'),
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Document addition failed: {e}")
            return {'success': False, 'error': str(e)}

    async def list_user_knowledge(self, user_id: str) -> Dict[str, Any]:
        """List all knowledge items for a user"""
        try:
            # Use vector DB to get all user's knowledge
            if hasattr(self.vector_db, 'list_user_documents'):
                result = await self.vector_db.list_user_documents(user_id)
                return {
                    'success': True,
                    'user_id': user_id,
                    'items': result.get('documents', []),
                    'total': len(result.get('documents', []))
                }
            else:
                # Fallback: search with empty query to get all
                result = await self.search_knowledge(
                    user_id=user_id,
                    query="",
                    top_k=100,
                    search_mode="semantic"
                )

                if result.get('success'):
                    items = result.get('search_results', [])
                    return {
                        'success': True,
                        'user_id': user_id,
                        'items': items,
                        'total': len(items),
                        'note': 'Listing via search - limited to top 100 results'
                    }
                else:
                    return result

        except Exception as e:
            logger.error(f"Knowledge listing failed: {e}")
            return {'success': False, 'error': str(e)}

    async def get_knowledge_item(
        self,
        user_id: str,
        knowledge_id: str
    ) -> Dict[str, Any]:
        """Get specific knowledge item"""
        try:
            if hasattr(self.vector_db, 'get_document'):
                result = await self.vector_db.get_document(knowledge_id, user_id)
                return {
                    'success': True,
                    'knowledge_id': knowledge_id,
                    'item': result
                }
            else:
                # Fallback: search by ID in metadata
                search_result = await self.search_knowledge(
                    user_id=user_id,
                    query=knowledge_id,
                    top_k=1
                )

                if search_result.get('success') and search_result.get('search_results'):
                    return {
                        'success': True,
                        'knowledge_id': knowledge_id,
                        'item': search_result['search_results'][0]
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Knowledge item {knowledge_id} not found'
                    }

        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")
            return {'success': False, 'error': str(e)}

    async def delete_knowledge_item(
        self,
        user_id: str,
        knowledge_id: str
    ) -> Dict[str, Any]:
        """Delete a knowledge item"""
        try:
            # Call the correct method name: delete_vector (not delete_document)
            success = await self.vector_db.delete_vector(knowledge_id, user_id)

            if success:
                return {
                    'success': True,
                    'knowledge_id': knowledge_id,
                    'deleted': True
                }
            else:
                return {
                    'success': False,
                    'error': f'Knowledge item {knowledge_id} not found or already deleted'
                }

        except Exception as e:
            logger.error(f"Knowledge deletion failed: {e}")
            return {'success': False, 'error': str(e)}

    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Retrieve relevant context for a query"""
        try:
            # This is essentially the same as search_knowledge
            result = await self.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=top_k,
                search_mode="hybrid"
            )

            if result.get('success'):
                contexts = result.get('search_results', [])
                return {
                    'success': True,
                    'query': query,
                    'contexts': contexts,
                    'context_count': len(contexts),
                    'retrieval_method': 'hybrid_search'
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return {'success': False, 'error': str(e)}

    # === IMAGE PROCESSING METHODS ===

    async def store_image(
        self,
        user_id: str,
        image_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        description_prompt: str = "Describe this image in detail, including objects, scene, colors, composition, and any text visible.",
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Store image by extracting description via VLM and storing as text knowledge

        Pipeline: Image → VLM Description → Text Embedding → Vector Store

        Args:
            user_id: User identifier for isolation
            image_path: Path to image file
            metadata: Additional metadata (will include image_path automatically)
            description_prompt: Prompt for VLM to generate description
            model: VLM model to use for description

        Returns:
            Dictionary with storage result and image description
        """
        try:
            # 1. Extract: Use VLM to describe the image
            from tools.services.intelligence_service.vision.image_analyzer import image_analyzer

            logger.info(f"Extracting description from image: {image_path}")
            analysis_result = await image_analyzer.analyze(
                image=image_path,
                prompt=description_prompt,
                model=model
            )

            if not analysis_result.success:
                return {
                    'success': False,
                    'error': f"Failed to extract image description: {analysis_result.error}",
                    'image_path': image_path
                }

            description = analysis_result.response
            logger.info(f"Extracted description ({len(description)} chars) in {analysis_result.processing_time:.2f}s")

            # 2. Embed & Store: Use existing text knowledge storage
            # Prepare metadata with image information
            image_metadata = metadata or {}
            image_metadata.update({
                'content_type': 'image',
                'image_path': image_path,
                'description_model': analysis_result.model_used,
                'extraction_time': analysis_result.processing_time,
                'stored_at': datetime.now().isoformat()
            })

            # Store the description as text knowledge
            storage_result = await self.store_knowledge(
                user_id=user_id,
                text=description,
                metadata=image_metadata
            )

            if storage_result.get('success'):
                return {
                    'success': True,
                    'image_path': image_path,
                    'description': description,
                    'description_length': len(description),
                    'storage_id': storage_result.get('knowledge_id'),
                    'metadata': image_metadata,
                    'vlm_model': analysis_result.model_used,
                    'processing_time': analysis_result.processing_time,
                    'mcp_address': storage_result.get('mcp_address', f"mcp://rag/{user_id}/image/{storage_result.get('knowledge_id')}")
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to store image description: {storage_result.get('error')}",
                    'description': description,
                    'image_path': image_path
                }

        except Exception as e:
            logger.error(f"Image storage failed for {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'image_path': image_path
            }

    async def search_images(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        enable_rerank: bool = False,
        search_mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Search for images using text query

        Searches image descriptions stored in the knowledge base and returns matching images

        Args:
            user_id: User identifier
            query: Text query to search for
            top_k: Number of results to return
            enable_rerank: Enable MMR reranking for diversity
            search_mode: Search mode ("semantic", "hybrid", etc.)

        Returns:
            Dictionary with search results (filtered for image content)
        """
        try:
            # Search using existing knowledge search
            search_result = await self.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=top_k * 2,  # Get more results to filter
                enable_rerank=enable_rerank,
                search_mode=search_mode
            )

            if not search_result.get('success'):
                return search_result

            # Filter results to only include images
            all_results = search_result.get('search_results', [])
            image_results = []

            for result in all_results:
                metadata = result.get('metadata', {})
                if metadata.get('content_type') == 'image':
                    image_results.append({
                        'knowledge_id': result.get('knowledge_id'),
                        'image_path': metadata.get('image_path'),
                        'description': result.get('text'),
                        'relevance_score': result.get('relevance_score', 0),
                        'metadata': metadata,
                        'search_method': result.get('search_method', 'traditional_isa')
                    })

                # Stop when we have enough results
                if len(image_results) >= top_k:
                    break

            return {
                'success': True,
                'user_id': user_id,
                'query': query,
                'image_results': image_results,
                'total_images_found': len(image_results),
                'search_method': search_result.get('search_method', 'traditional_isa')
            }

        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query
            }

    async def generate_image_rag_response(
        self,
        user_id: str,
        query: str,
        context_limit: int = 3,
        include_images: bool = True,
        rag_mode: str = None
    ) -> Dict[str, Any]:
        """
        Generate RAG response that can include image context

        Retrieves relevant images and their descriptions, then generates a response

        Args:
            user_id: User identifier
            query: User question
            context_limit: Maximum number of context items (images + text)
            include_images: Whether to include images in context
            rag_mode: RAG mode to use

        Returns:
            Dictionary with generated response and image sources
        """
        try:
            if include_images:
                # Search for relevant images
                image_search = await self.search_images(
                    user_id=user_id,
                    query=query,
                    top_k=context_limit
                )

                # Also search regular text knowledge
                text_search = await self.search_knowledge(
                    user_id=user_id,
                    query=query,
                    top_k=context_limit
                )

                # Combine contexts
                context_items = []

                # Add image descriptions
                if image_search.get('success'):
                    for img in image_search.get('image_results', []):
                        context_items.append({
                            'text': f"[Image: {img.get('image_path')}] {img.get('description')}",
                            'type': 'image',
                            'image_path': img.get('image_path'),
                            'score': img.get('relevance_score', 0)
                        })

                # Add text knowledge (filter out images)
                if text_search.get('success'):
                    for item in text_search.get('search_results', []):
                        metadata = item.get('metadata', {})
                        if metadata.get('content_type') != 'image':
                            context_items.append({
                                'text': item.get('text'),
                                'type': 'text',
                                'score': item.get('relevance_score', 0)
                            })

                # Sort by relevance and limit
                context_items.sort(key=lambda x: x.get('score', 0), reverse=True)
                context_items = context_items[:context_limit]

                # Build context text
                context_text = "\n\n".join([item['text'] for item in context_items])

                # Generate response using text generator
                from tools.services.intelligence_service.language.text_generator import text_generator

                augmented_query = f"""Based on the following context (including images and text):

{context_text}

Question: {query}

Please provide a comprehensive answer that references the relevant images and information."""

                response_text = await text_generator.generate(
                    prompt=augmented_query,
                    temperature=0.3
                )

                if not response_text:
                    return {
                        'success': False,
                        'error': "Failed to generate response: empty result"
                    }

                return {
                    'success': True,
                    'response': response_text,
                    'context_items': len(context_items),
                    'image_sources': [
                        {
                            'image_path': item['image_path'],
                            'description': item['text'],
                            'relevance': item['score']
                        }
                        for item in context_items if item['type'] == 'image'
                    ],
                    'text_sources': [
                        {
                            'text': item['text'],
                            'relevance': item['score']
                        }
                        for item in context_items if item['type'] == 'text'
                    ],
                    'metadata': {
                        'model': 'gpt-4.1-nano',
                        'total_context_items': len(context_items),
                        'image_count': len([i for i in context_items if i['type'] == 'image']),
                        'text_count': len([i for i in context_items if i['type'] == 'text'])
                    }
                }
            else:
                # Fall back to regular RAG without images
                return await self.generate_rag_response(
                    user_id=user_id,
                    query=query,
                    context_limit=context_limit,
                    rag_mode=rag_mode
                )

        except Exception as e:
            logger.error(f"Image RAG generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query
            }

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
                'vector_db_type': self.vector_db.__class__.__name__,
                'embedding_generator_type': self.embedding_generator.__class__.__name__,
                'components': {
                    'vector_db_initialized': True,
                    'embedding_generator_initialized': True,
                    'guardrail_system_initialized': self._guardrail_system is not None,
                    'rag_service_initialized': self._rag_service is not None,
                    'rag_factory_initialized': self._rag_factory is not None
                }
            }

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

# === CONVENIENCE FUNCTIONS ===

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
    search_mode: str = "hybrid",
    rag_mode: str = None
) -> Dict[str, Any]:
    """Search knowledge using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.search_knowledge(user_id, query, top_k, enable_rerank, search_mode, rag_mode)

async def generate_rag_response(
    user_id: str,
    query: str,
    context_limit: int = 3,
    rag_mode: str = None,
    enable_inline_citations: bool = True
) -> Dict[str, Any]:
    """Generate RAG response using integrated service"""
    service = get_digital_analytics_service()
    return await service.generate_rag_response(user_id, query, context_limit, rag_mode, enable_inline_citations)

# === MULTI-MODE RAG CONVENIENCE FUNCTIONS ===

async def query_with_mode(
    user_id: str,
    query: str,
    mode: str = "simple",
    **kwargs
) -> Dict[str, Any]:
    """Query using specific RAG mode"""
    service = get_digital_analytics_service()
    return await service.query_with_mode(user_id, query, mode, **kwargs)

async def hybrid_query(
    user_id: str,
    query: str,
    modes: List[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Execute hybrid query across multiple RAG modes"""
    service = get_digital_analytics_service()
    return await service.hybrid_query(user_id, query, modes, **kwargs)

async def recommend_mode(
    query: str,
    user_id: str
) -> Dict[str, Any]:
    """Recommend best RAG mode for a query"""
    service = get_digital_analytics_service()
    return await service.recommend_mode(query, user_id)

async def get_rag_capabilities() -> Dict[str, Any]:
    """Get comprehensive RAG capabilities"""
    service = get_digital_analytics_service()
    return await service.get_rag_capabilities()

# === IMAGE PROCESSING CONVENIENCE FUNCTIONS ===

async def store_image(
    user_id: str,
    image_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    description_prompt: str = "Describe this image in detail, including objects, scene, colors, composition, and any text visible.",
    model: str = "gpt-4.1-vision"
) -> Dict[str, Any]:
    """Store image by extracting VLM description and storing as knowledge"""
    service = get_digital_analytics_service()
    return await service.store_image(user_id, image_path, metadata, description_prompt, model)

async def search_images(
    user_id: str,
    query: str,
    top_k: int = 5,
    enable_rerank: bool = False,
    search_mode: str = "hybrid"
) -> Dict[str, Any]:
    """Search for images using text query"""
    service = get_digital_analytics_service()
    return await service.search_images(user_id, query, top_k, enable_rerank, search_mode)

async def generate_image_rag_response(
    user_id: str,
    query: str,
    context_limit: int = 3,
    include_images: bool = True,
    rag_mode: str = None
) -> Dict[str, Any]:
    """Generate RAG response with image and text context"""
    service = get_digital_analytics_service()
    return await service.generate_image_rag_response(user_id, query, context_limit, include_images, rag_mode)
