#!/usr/bin/env python3
"""
Metadata Store Service - Integrated Steps 1-3 Pipeline
Combines metadata extraction, semantic enrichment, and embedding storage
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Import pipeline components
from ...processors.data_processors.metadata_extractor import extract_metadata, MetadataExtractor
from .semantic_enricher import enrich_metadata, AISemanticEnricher
from .metadata_embedding import get_embedding_service, AIMetadataEmbeddingService

logger = logging.getLogger(__name__)

@dataclass
class PipelineResult:
    """Result from the complete metadata processing pipeline"""
    success: bool
    pipeline_id: str
    source_path: str
    database_name: str
    
    # Step 1: Metadata Extraction
    raw_metadata: Dict[str, Any]
    extraction_duration: float
    tables_found: int
    columns_found: int
    
    # Step 2: Semantic Enrichment
    semantic_metadata: Any  # SemanticMetadata object
    enrichment_duration: float
    ai_analysis_source: str
    business_entities: int
    semantic_tags: int
    
    # Step 3: Embedding Storage
    storage_results: Dict[str, Any]
    storage_duration: float
    embeddings_stored: int
    search_ready: bool
    
    # Overall Pipeline
    total_duration: float
    pipeline_cost: float
    created_at: datetime
    error_message: Optional[str] = None

class MetadataStoreService:
    """
    Integrated metadata store service combining Steps 1-3
    Provides complete pipeline from raw data to searchable embeddings
    """
    
    def __init__(self, database_name: str = "default_db"):
        self.database_name = database_name
        self.service_name = "MetadataStoreService"
        
        # Initialize pipeline components
        self.metadata_extractor = MetadataExtractor()
        self.semantic_enricher = AISemanticEnricher()
        self.embedding_service = get_embedding_service(database_name)
        
        # Pipeline tracking
        self.processed_sources = {}
        self.pipeline_stats = {
            'total_pipelines': 0,
            'successful_pipelines': 0,
            'failed_pipelines': 0,
            'total_embeddings_stored': 0,
            'total_cost_usd': 0.0
        }
        
        logger.info(f"Metadata Store Service initialized for database: {database_name}")
    
    async def process_data_source(self, source_path: str, 
                                source_type: Optional[str] = None,
                                pipeline_id: Optional[str] = None) -> PipelineResult:
        """
        Process a complete data source through the 3-step pipeline
        
        Args:
            source_path: Path to data source (CSV, Excel, JSON, or database connection)
            source_type: Optional source type override
            pipeline_id: Optional custom pipeline identifier
            
        Returns:
            PipelineResult with complete pipeline information
        """
        pipeline_start = datetime.now()
        
        if not pipeline_id:
            pipeline_id = f"pipeline_{int(pipeline_start.timestamp())}"
        
        logger.info(f"Starting pipeline {pipeline_id} for source: {source_path}")
        
        try:
            # Step 1: Metadata Extraction
            step1_start = datetime.now()
            logger.info(f"Pipeline {pipeline_id}: Step 1 - Extracting metadata")
            
            raw_metadata = self.metadata_extractor.extract_metadata(source_path, source_type)
            
            if 'error' in raw_metadata:
                raise Exception(f"Metadata extraction failed: {raw_metadata['error']}")
            
            step1_duration = (datetime.now() - step1_start).total_seconds()
            tables_found = len(raw_metadata.get('tables', []))
            columns_found = len(raw_metadata.get('columns', []))
            
            logger.info(f"Pipeline {pipeline_id}: Step 1 completed - {tables_found} tables, {columns_found} columns ({step1_duration:.2f}s)")
            
            # Step 2: Semantic Enrichment
            step2_start = datetime.now()
            logger.info(f"Pipeline {pipeline_id}: Step 2 - AI semantic enrichment")
            
            semantic_metadata = await self.semantic_enricher.enrich_metadata(raw_metadata)
            
            step2_duration = (datetime.now() - step2_start).total_seconds()
            ai_analysis_source = semantic_metadata.ai_analysis.get('source', 'unknown')
            business_entities = len(semantic_metadata.business_entities)
            semantic_tags = len(semantic_metadata.semantic_tags)
            
            logger.info(f"Pipeline {pipeline_id}: Step 2 completed - {business_entities} entities, {semantic_tags} tag groups ({step2_duration:.2f}s)")
            logger.info(f"Pipeline {pipeline_id}: AI analysis source: {ai_analysis_source}")
            
            # Step 3: Embedding Storage
            step3_start = datetime.now()
            logger.info(f"Pipeline {pipeline_id}: Step 3 - Generating and storing embeddings")
            
            storage_results = await self.embedding_service.store_semantic_metadata(semantic_metadata)
            
            step3_duration = (datetime.now() - step3_start).total_seconds()
            embeddings_stored = storage_results.get('stored_embeddings', 0)
            search_ready = embeddings_stored > 0
            
            logger.info(f"Pipeline {pipeline_id}: Step 3 completed - {embeddings_stored} embeddings stored ({step3_duration:.2f}s)")
            
            # Calculate totals
            pipeline_end = datetime.now()
            total_duration = (pipeline_end - pipeline_start).total_seconds()
            pipeline_cost = storage_results.get('billing_info', {}).get('cost_usd', 0.0)
            
            # Create result
            result = PipelineResult(
                success=True,
                pipeline_id=pipeline_id,
                source_path=source_path,
                database_name=self.database_name,
                
                raw_metadata=raw_metadata,
                extraction_duration=step1_duration,
                tables_found=tables_found,
                columns_found=columns_found,
                
                semantic_metadata=semantic_metadata,
                enrichment_duration=step2_duration,
                ai_analysis_source=ai_analysis_source,
                business_entities=business_entities,
                semantic_tags=semantic_tags,
                
                storage_results=storage_results,
                storage_duration=step3_duration,
                embeddings_stored=embeddings_stored,
                search_ready=search_ready,
                
                total_duration=total_duration,
                pipeline_cost=pipeline_cost,
                created_at=pipeline_start
            )
            
            # Update tracking
            self.processed_sources[pipeline_id] = result
            self._update_stats(result)
            
            logger.info(f"Pipeline {pipeline_id} completed successfully in {total_duration:.2f}s (cost: ${pipeline_cost:.4f})")
            return result
            
        except Exception as e:
            error_duration = (datetime.now() - pipeline_start).total_seconds()
            error_message = str(e)
            
            logger.error(f"Pipeline {pipeline_id} failed after {error_duration:.2f}s: {error_message}")
            
            # Create error result
            result = PipelineResult(
                success=False,
                pipeline_id=pipeline_id,
                source_path=source_path,
                database_name=self.database_name,
                
                raw_metadata={},
                extraction_duration=0,
                tables_found=0,
                columns_found=0,
                
                semantic_metadata=None,
                enrichment_duration=0,
                ai_analysis_source='error',
                business_entities=0,
                semantic_tags=0,
                
                storage_results={},
                storage_duration=0,
                embeddings_stored=0,
                search_ready=False,
                
                total_duration=error_duration,
                pipeline_cost=0.0,
                created_at=pipeline_start,
                error_message=error_message
            )
            
            self.processed_sources[pipeline_id] = result
            self.pipeline_stats['failed_pipelines'] += 1
            
            return result
    
    async def process_multiple_sources(self, sources: List[Dict[str, Any]], 
                                     concurrent_limit: int = 3) -> List[PipelineResult]:
        """
        Process multiple data sources with controlled concurrency
        
        Args:
            sources: List of source configurations [{'path': '...', 'type': '...', 'id': '...'}]
            concurrent_limit: Maximum concurrent pipeline executions
            
        Returns:
            List of PipelineResult objects
        """
        logger.info(f"Processing {len(sources)} sources with concurrency limit: {concurrent_limit}")
        
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def process_with_semaphore(source_config):
            async with semaphore:
                return await self.process_data_source(
                    source_config['path'],
                    source_config.get('type'),
                    source_config.get('id')
                )
        
        # Execute with controlled concurrency
        tasks = [process_with_semaphore(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = PipelineResult(
                    success=False,
                    pipeline_id=f"error_{i}",
                    source_path=sources[i]['path'],
                    database_name=self.database_name,
                    raw_metadata={}, extraction_duration=0, tables_found=0, columns_found=0,
                    semantic_metadata=None, enrichment_duration=0, ai_analysis_source='error',
                    business_entities=0, semantic_tags=0,
                    storage_results={}, storage_duration=0, embeddings_stored=0, search_ready=False,
                    total_duration=0, pipeline_cost=0.0, created_at=datetime.now(),
                    error_message=str(result)
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        successful = sum(1 for r in final_results if r.success)
        failed = len(final_results) - successful
        
        logger.info(f"Batch processing completed: {successful} successful, {failed} failed")
        
        return final_results
    
    async def search_metadata(self, query: str, 
                            entity_type: Optional[str] = None,
                            limit: int = 10,
                            use_ai_reranking: bool = True) -> List[Dict[str, Any]]:
        """
        Search across all stored metadata using AI-powered similarity
        
        Args:
            query: Natural language search query
            entity_type: Optional filter by entity type
            limit: Maximum number of results
            use_ai_reranking: Whether to use AI reranking for better relevance
            
        Returns:
            List of search results with metadata context
        """
        logger.info(f"Searching metadata for query: '{query}' (type: {entity_type}, limit: {limit})")
        
        try:
            if use_ai_reranking:
                results = await self.embedding_service.search_with_reranking(
                    query, entity_type, limit
                )
            else:
                results = await self.embedding_service.search_similar_entities(
                    query, entity_type, limit
                )
            
            # Enrich results with context
            enriched_results = []
            for result in results:
                enriched_result = {
                    'entity_name': result.entity_name,
                    'entity_type': result.entity_type,
                    'similarity_score': result.similarity_score,
                    'content': result.content,
                    'metadata': result.metadata,
                    'semantic_tags': result.semantic_tags,
                    'database_source': self.database_name,
                    'search_method': 'ai_reranking' if use_ai_reranking else 'similarity'
                }
                enriched_results.append(enriched_result)
            
            logger.info(f"Found {len(enriched_results)} results for query: '{query}'")
            return enriched_results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        return {
            'service_info': {
                'service_name': self.service_name,
                'database_name': self.database_name,
                'total_processed_sources': len(self.processed_sources)
            },
            'pipeline_stats': self.pipeline_stats.copy(),
            'recent_pipelines': [
                {
                    'pipeline_id': result.pipeline_id,
                    'source_path': Path(result.source_path).name,
                    'success': result.success,
                    'duration': result.total_duration,
                    'embeddings_stored': result.embeddings_stored,
                    'cost': result.pipeline_cost,
                    'created_at': result.created_at.isoformat()
                }
                for result in list(self.processed_sources.values())[-10:]  # Last 10
            ]
        }
    
    def get_pipeline_result(self, pipeline_id: str) -> Optional[PipelineResult]:
        """Get detailed result for a specific pipeline"""
        return self.processed_sources.get(pipeline_id)
    
    async def get_database_summary(self) -> Dict[str, Any]:
        """Get summary of stored metadata in the database"""
        try:
            stats = await self.embedding_service.get_metadata_stats()
            
            return {
                'database_name': self.database_name,
                'embedding_stats': stats,
                'pipeline_stats': self.pipeline_stats,
                'service_status': 'active',
                'ai_services': {
                    'semantic_enricher': 'available' if self.semantic_enricher.text_extractor else 'fallback',
                    'embedding_generator': 'available' if self.embedding_service.embedding_generator else 'fallback'
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get database summary: {e}")
            return {
                'database_name': self.database_name,
                'error': str(e),
                'service_status': 'error'
            }
    
    def _update_stats(self, result: PipelineResult):
        """Update internal pipeline statistics"""
        self.pipeline_stats['total_pipelines'] += 1
        
        if result.success:
            self.pipeline_stats['successful_pipelines'] += 1
            self.pipeline_stats['total_embeddings_stored'] += result.embeddings_stored
            self.pipeline_stats['total_cost_usd'] += result.pipeline_cost
        else:
            self.pipeline_stats['failed_pipelines'] += 1

# Global instances for different databases
_store_services = {}

def get_metadata_store_service(database_name: str = "default_db") -> MetadataStoreService:
    """Get metadata store service instance for a specific database"""
    global _store_services
    
    if database_name not in _store_services:
        _store_services[database_name] = MetadataStoreService(database_name)
    
    return _store_services[database_name]

# Convenience functions
async def process_data_source(source_path: str, database_name: str = "default_db", 
                            source_type: Optional[str] = None) -> PipelineResult:
    """Convenience function to process a single data source"""
    service = get_metadata_store_service(database_name)
    return await service.process_data_source(source_path, source_type)

async def search_metadata(query: str, database_name: str = "default_db", 
                        limit: int = 10) -> List[Dict[str, Any]]:
    """Convenience function to search metadata"""
    service = get_metadata_store_service(database_name)
    return await service.search_metadata(query, limit=limit)