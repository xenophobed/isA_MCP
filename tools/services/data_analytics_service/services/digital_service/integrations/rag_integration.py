#!/usr/bin/env python3
"""
RAG Integration Module

Handles RAG service integration with multi-mode support
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class RAGIntegration:
    """RAG Service Integration Manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._rag_factory = None
        self._rag_registry = None
        self._rag_service = None
    
    @property
    def rag_factory(self):
        """Lazy load RAG factory"""
        if self._rag_factory is None:
            from ..rag_factory import RAGFactory
            self._rag_factory = RAGFactory()
        return self._rag_factory
    
    @property
    def rag_registry(self):
        """Lazy load RAG registry"""
        if self._rag_registry is None:
            from ..rag_factory import RAGRegistry
            self._rag_registry = RAGRegistry(self.rag_factory)
        return self._rag_registry
    
    @property
    def rag_service(self):
        """Lazy load RAG service"""
        if self._rag_service is None:
            self._rag_service = self._create_rag_service()
        return self._rag_service
    
    def _create_rag_service(self):
        """Create RAG service using latest Factory architecture"""
        try:
            from ..base.base_rag_service import RAGConfig, RAGMode
            
            # Configure RAG service
            rag_config = RAGConfig(
                mode=RAGMode.SIMPLE,
                chunk_size=self.config.get('chunk_size', 1000),
                overlap=self.config.get('overlap_size', 100),
                top_k=self.config.get('top_k_results', 5),
                embedding_model='text-embedding-3-small',
                enable_rerank=self.config.get('enable_mmr_reranking', True),
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
            
            from ..base.base_rag_service import RAGMode
            
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
            
            # Execute queries in parallel
            tasks = []
            for mode in modes:
                task = self.query_with_mode(user_id, query, mode, **kwargs)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        'mode': modes[i],
                        'error': str(result)
                    })
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
            from ..base.base_rag_service import RAGMode
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
            
            # Get available modes
            available_modes = self.rag_factory.get_available_modes()
            capabilities['available_modes'] = [mode.value for mode in available_modes]
            
            # Get details for each mode
            for mode in available_modes:
                mode_info = self.rag_factory.get_service_info(mode)
                capabilities['mode_details'][mode.value] = mode_info
            
            # Get factory info
            capabilities['factory_info'] = {
                'total_modes': len(available_modes),
                'cached_instances': len(self.rag_factory._instances),
                'factory_type': self.rag_factory.__class__.__name__
            }
            
            # Get performance metrics if available
            if hasattr(self.rag_service, 'get_performance_metrics'):
                capabilities['performance_metrics'] = self.rag_service.get_performance_metrics()
            
            return {
                'success': True,
                'capabilities': capabilities
            }
            
        except Exception as e:
            logger.error(f"Failed to get RAG capabilities: {e}")
            return {'success': False, 'error': str(e)}
    
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
            top_k = top_k or self.config.get('top_k_results', 5)
            enable_rerank = enable_rerank if enable_rerank is not None else self.config.get('enable_mmr_reranking', True)
            
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
                if hasattr(self.rag_service, 'generate_response'):
                    result = await self.rag_service.generate_response(user_id, query, context_limit)
                else:
                    # Fallback to query method
                    rag_result = await self.rag_service.query(query, user_id)
                    result = {
                        'success': rag_result.success,
                        'response': rag_result.content,
                        'sources': rag_result.sources,
                        'metadata': rag_result.metadata
                    }
            
            # Apply inline citations if enabled
            if enable_inline_citations and result.get('success') and result.get('response'):
                try:
                    from tools.services.intelligence_service.vector_db.citation_service import CitationService
                    citation_service = CitationService()
                    
                    enhanced_response = await citation_service.create_inline_citations(
                        rag_result={
                            'response': result['response'],
                            'sources': result.get('sources', [])
                        },
                        citation_style='inline',
                        include_confidence=True
                    )
                    
                    if enhanced_response.get('success'):
                        result['response'] = enhanced_response['enhanced_response']
                        result['citations'] = enhanced_response.get('citations', [])
                        result['inline_citations_enabled'] = True
                        
                except Exception as e:
                    logger.warning(f"Failed to add inline citations: {e}")
                    result['citation_warning'] = 'Inline citations could not be added'
            
            return result
        except Exception as e:
            logger.error(f"RAG response generation failed: {e}")
            return {'success': False, 'error': str(e)}











