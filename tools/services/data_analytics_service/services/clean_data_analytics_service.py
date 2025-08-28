#!/usr/bin/env python3
"""
Clean Data Analytics Service - Proper Service Suite Orchestration
Uses the service suite architecture from data_service/
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class AnalyticsRequest:
    """Clean analytics request structure"""
    request_id: str
    request_type: str  # 'ingest', 'query', 'transform', 'analyze'
    source_data: Optional[str] = None
    query_text: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

@dataclass
class AnalyticsResult:
    """Clean analytics result structure"""
    request_id: str
    success: bool
    result_data: Dict[str, Any]
    processing_time_ms: float
    service_chain: List[str]  # Which services were used
    error_message: Optional[str] = None
    warnings: List[str] = None

class CleanDataAnalyticsService:
    """
    Clean Data Analytics Service - Thin Orchestration Layer
    
    Properly delegates to service suite components:
    - management/: MetadataStoreService (Steps 1-3)
    - search/: SQLQueryService (Steps 4-6) 
    - preprocessor/: Data preprocessing and validation
    - transformation/: Data transformation and feature engineering
    - storage/: Data storage and persistence
    - model/: Machine learning model operations
    - quality/: Data quality management
    - analytics/: EDA and statistical analysis
    - visualization/: Chart and visualization generation
    """
    
    def __init__(self, database_name: str = "analytics_db"):
        """Initialize with service suite components"""
        self.database_name = database_name
        self.service_name = "CleanDataAnalyticsService"
        
        # Service suite components (lazy initialization)
        self._metadata_service = None      # management/metadata/
        self._query_service = None         # search/
        self._preprocessor_service = None  # preprocessor/
        self._transformation_service = None # transformation/
        self._storage_service = None       # storage/
        self._model_service = None         # model/
        self._quality_service = None       # quality/
        self._analytics_service = None     # analytics/
        self._visualization_service = None # visualization/
        
        # Request tracking
        self._request_history = []
        self._service_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0
        }
        
        logger.info(f"Clean Data Analytics Service initialized for database: {database_name}")
    
    # === Core Analytics Operations ===
    
    async def ingest_data_source(self, source_path: str, 
                               source_type: Optional[str] = None,
                               request_id: Optional[str] = None) -> AnalyticsResult:
        """
        Data Ingestion (Steps 1-3) - Delegate to MetadataStoreService
        """
        if not request_id:
            request_id = f"ingest_{int(datetime.now().timestamp())}"
        
        start_time = datetime.now()
        service_chain = ['MetadataStoreService']
        
        try:
            # Get metadata service (Steps 1-3)
            metadata_service = await self._get_metadata_service()
            
            # Delegate to metadata pipeline
            pipeline_result = await metadata_service.process_data_source(
                source_path, source_type, request_id
            )
            
            # Extract result data
            result_data = {
                'source_path': source_path,
                'pipeline_success': pipeline_result.success,
                'tables_found': pipeline_result.tables_found,
                'columns_found': pipeline_result.columns_found,
                'embeddings_stored': pipeline_result.embeddings_stored,
                'sqlite_database_path': pipeline_result.raw_metadata.get('csv_database_path') if pipeline_result.raw_metadata else None,
                'processing_time_ms': pipeline_result.total_duration * 1000,  # Convert to ms
                'cost_usd': getattr(pipeline_result, 'pipeline_cost', 0.0)
            }
            
            processing_time = self._calculate_processing_time(start_time)
            
            result = AnalyticsResult(
                request_id=request_id,
                success=pipeline_result.success,
                result_data=result_data,
                processing_time_ms=processing_time,
                service_chain=service_chain,
                error_message=pipeline_result.error_message if not pipeline_result.success else None
            )
            
            await self._record_request(result)
            return result
            
        except Exception as e:
            processing_time = self._calculate_processing_time(start_time)
            logger.error(f"Ingestion failed: {e}")
            
            result = AnalyticsResult(
                request_id=request_id,
                success=False,
                result_data={},
                processing_time_ms=processing_time,
                service_chain=service_chain,
                error_message=str(e)
            )
            
            await self._record_request(result)
            return result
    
    async def query_with_language(self, natural_language_query: str,
                                sqlite_database_path: str,
                                request_id: Optional[str] = None) -> AnalyticsResult:
        """
        Natural Language Query (Steps 4-6) - Delegate to SQLQueryService
        """
        if not request_id:
            request_id = f"query_{int(datetime.now().timestamp())}"
        
        start_time = datetime.now()
        service_chain = ['SQLQueryService']
        
        try:
            # Get query service (Steps 4-6) 
            query_service = await self._get_query_service(sqlite_database_path)
            
            # Get metadata from metadata service
            metadata_service = await self._get_metadata_service()
            semantic_metadata = await self._get_latest_semantic_metadata(metadata_service)
            
            if not semantic_metadata:
                return AnalyticsResult(
                    request_id=request_id,
                    success=False,
                    result_data={},
                    processing_time_ms=self._calculate_processing_time(start_time),
                    service_chain=service_chain,
                    error_message="No metadata available. Please ingest data first."
                )
            
            # Delegate to query pipeline
            query_result = await query_service.process_query(
                natural_language_query, semantic_metadata
            )
            
            # Extract result data
            result_data = {
                'original_query': natural_language_query,
                'query_success': query_result.success,
                'generated_sql': query_result.sql_result.sql if query_result.sql_result else None,
                'sql_confidence': query_result.sql_result.confidence_score if query_result.sql_result else 0,
                'execution_success': query_result.execution_result.success if query_result.execution_result else False,
                'row_count': query_result.execution_result.row_count if query_result.execution_result else 0,
                'result_data': query_result.execution_result.data if query_result.execution_result else [],
                'processing_time_ms': query_result.processing_time_ms,
                'fallback_attempts': len(query_result.fallback_attempts)
            }
            
            processing_time = self._calculate_processing_time(start_time)
            
            result = AnalyticsResult(
                request_id=request_id,
                success=query_result.success,
                result_data=result_data,
                processing_time_ms=processing_time,
                service_chain=service_chain,
                error_message=query_result.error_message if not query_result.success else None,
                warnings=query_result.warnings or []
            )
            
            await self._record_request(result)
            return result
            
        except Exception as e:
            processing_time = self._calculate_processing_time(start_time)
            logger.error(f"Query failed: {e}")
            
            result = AnalyticsResult(
                request_id=request_id,
                success=False,
                result_data={},
                processing_time_ms=processing_time,
                service_chain=service_chain,
                error_message=str(e)
            )
            
            await self._record_request(result)
            return result
    
    async def perform_data_analysis(self, data_path: str,
                                  analysis_type: str = "eda",
                                  target_column: Optional[str] = None,
                                  request_id: Optional[str] = None) -> AnalyticsResult:
        """
        Data Analysis - Delegate to analytics/ service suite
        """
        if not request_id:
            request_id = f"analysis_{int(datetime.now().timestamp())}"
        
        start_time = datetime.now()
        service_chain = ['AnalyticsService']
        
        try:
            # Get analytics service
            analytics_service = await self._get_analytics_service()
            
            # Delegate based on analysis type
            if analysis_type == "eda":
                analysis_result = await analytics_service.perform_comprehensive_eda(
                    data_path, target_column
                )
            else:
                raise ValueError(f"Unsupported analysis type: {analysis_type}")
            
            result_data = {
                'analysis_type': analysis_type,
                'data_path': data_path,
                'target_column': target_column,
                'analysis_results': analysis_result
            }
            
            processing_time = self._calculate_processing_time(start_time)
            
            result = AnalyticsResult(
                request_id=request_id,
                success=True,
                result_data=result_data,
                processing_time_ms=processing_time,
                service_chain=service_chain
            )
            
            await self._record_request(result)
            return result
            
        except Exception as e:
            processing_time = self._calculate_processing_time(start_time)
            logger.error(f"Analysis failed: {e}")
            
            result = AnalyticsResult(
                request_id=request_id,
                success=False,
                result_data={},
                processing_time_ms=processing_time,
                service_chain=service_chain,
                error_message=str(e)
            )
            
            await self._record_request(result)
            return result
    
    # === Service Suite Access (Lazy Initialization) ===
    
    async def _get_metadata_service(self):
        """Get metadata service (Steps 1-3)"""
        if self._metadata_service is None:
            from .data_service.management.metadata.metadata_store_service import MetadataStoreService
            self._metadata_service = MetadataStoreService(self.database_name)
            logger.info("MetadataStoreService initialized")
        return self._metadata_service
    
    async def _get_query_service(self, sqlite_database_path: str):
        """Get query service (Steps 4-6)"""
        if self._query_service is None:
            from .data_service.search.sql_query_service import SQLQueryService
            
            database_config = {
                'type': 'sqlite',
                'database': sqlite_database_path,
                'max_execution_time': 30,
                'max_rows': 10000
            }
            
            self._query_service = SQLQueryService(database_config, self.database_name)
            await self._query_service.initialize()
            logger.info("SQLQueryService initialized")
        
        return self._query_service
    
    async def _get_analytics_service(self):
        """Get analytics service"""
        if self._analytics_service is None:
            from .data_service.analytics.data_eda import DataEDAService
            self._analytics_service = DataEDAService()
            logger.info("DataEDAService initialized")
        return self._analytics_service
    
    async def _get_preprocessing_service(self):
        """Get preprocessing service"""
        if self._preprocessor_service is None:
            from .data_service.preprocessor.preprocessor_service import PreprocessorService
            self._preprocessor_service = PreprocessorService()
            logger.info("PreprocessorService initialized")
        return self._preprocessor_service
    
    async def _get_transformation_service(self):
        """Get transformation service"""
        if self._transformation_service is None:
            from .data_service.transformation.transformation_service import TransformationService
            self._transformation_service = TransformationService()
            logger.info("TransformationService initialized")
        return self._transformation_service
    
    async def _get_model_service(self):
        """Get model service"""
        if self._model_service is None:
            from .data_service.model.model_service import ModelService
            self._model_service = ModelService()
            logger.info("ModelService initialized")
        return self._model_service
    
    # === Utility Methods ===
    
    async def _get_latest_semantic_metadata(self, metadata_service):
        """Get latest semantic metadata from metadata service or embeddings"""
        try:
            # Try to get from recent pipelines
            pipeline_stats = metadata_service.get_pipeline_stats()
            recent_pipelines = pipeline_stats.get('recent_pipelines', [])
            
            for pipeline_info in reversed(recent_pipelines):
                if pipeline_info['success']:
                    pipeline_result = metadata_service.get_pipeline_result(pipeline_info['pipeline_id'])
                    if pipeline_result and pipeline_result.semantic_metadata:
                        return pipeline_result.semantic_metadata
            
            # If no recent pipelines, try to reconstruct from embeddings (like the old service)
            logger.info("No recent pipelines found, attempting metadata reconstruction")
            from .data_service.management.metadata.metadata_embedding import get_embedding_service
            from .data_service.management.metadata.semantic_enricher import SemanticMetadata
            
            embedding_service = get_embedding_service(self.database_name)
            await embedding_service.initialize()
            
            # Search for existing metadata
            table_results = await embedding_service.search_similar_entities(
                "table data", entity_type="table", limit=50, similarity_threshold=0.0
            )
            
            if not table_results:
                return None
            
            # Reconstruct basic metadata
            tables = []
            for table_result in table_results:
                tables.append({
                    'table_name': table_result.entity_name,
                    'table_comment': 'Reconstructed from embeddings'
                })
            
            return SemanticMetadata(
                original_metadata={'tables': tables, 'columns': []},
                business_entities=[t['table_name'] for t in tables],
                semantic_tags={},
                data_patterns=[],
                business_rules=[],
                domain_classification={'domain': 'reconstructed', 'confidence': 0.7},
                confidence_scores={'overall': 0.7},
                ai_analysis={'context': 'Reconstructed from embeddings'}
            )
            
        except Exception as e:
            logger.error(f"Failed to get semantic metadata: {e}")
            return None
    
    def _calculate_processing_time(self, start_time: datetime) -> float:
        """Calculate processing time in milliseconds"""
        return (datetime.now() - start_time).total_seconds() * 1000
    
    async def _record_request(self, result: AnalyticsResult):
        """Record request for tracking"""
        self._request_history.append({
            'timestamp': datetime.now().isoformat(),
            'request_id': result.request_id,
            'success': result.success,
            'processing_time_ms': result.processing_time_ms,
            'service_chain': result.service_chain
        })
        
        # Update stats
        self._service_stats['total_requests'] += 1
        if result.success:
            self._service_stats['successful_requests'] += 1
        else:
            self._service_stats['failed_requests'] += 1
        
        # Keep only recent history
        if len(self._request_history) > 100:
            self._request_history = self._request_history[-100:]
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'service_info': {
                'service_name': self.service_name,
                'database_name': self.database_name
            },
            'service_stats': self._service_stats.copy(),
            'recent_requests': self._request_history[-10:],
            'active_services': {
                'metadata_service': self._metadata_service is not None,
                'query_service': self._query_service is not None,
                'analytics_service': self._analytics_service is not None,
                'preprocessor_service': self._preprocessor_service is not None,
                'transformation_service': self._transformation_service is not None,
                'model_service': self._model_service is not None
            }
        }

# Factory method for easy instantiation
def create_analytics_service(database_name: str = "analytics_db") -> CleanDataAnalyticsService:
    """Create a clean analytics service instance"""
    return CleanDataAnalyticsService(database_name)