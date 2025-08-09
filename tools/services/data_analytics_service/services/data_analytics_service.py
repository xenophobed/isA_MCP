#!/usr/bin/env python3
"""
Data Analytics Service - Complete End-to-End Pipeline
Combines metadata processing (Steps 1-3) and query processing (Steps 4-6)
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Import the three main sub-services
from .data_service.metadata_store_service import MetadataStoreService, PipelineResult
from .data_service.sql_query_service import SQLQueryService, QueryResult
from .data_service.data_visualization import DataVisualizationService, VisualizationSpec
from .data_service.semantic_enricher import SemanticMetadata

logger = logging.getLogger(__name__)

@dataclass
class AnalyticsResult:
    """Complete analytics processing result combining all services"""
    success: bool
    request_id: str
    
    # Metadata processing (Steps 1-3)
    metadata_pipeline: Optional[PipelineResult]
    
    # Query processing (Steps 4-6) 
    query_result: Optional[QueryResult]
    
    # Visualization processing (Step 7)
    visualization_result: Optional[Dict[str, Any]]
    
    # Overall metrics
    total_processing_time_ms: float
    total_cost_usd: float
    created_at: datetime
    error_message: Optional[str] = None

class DataAnalyticsService:
    """
    Complete Data Analytics Service - End-to-End Pipeline
    
    Combines three main sub-services:
    1. MetadataStoreService (Steps 1-3): Extract, enrich, embed, store metadata
    2. SQLQueryService (Steps 4-6): Query match, SQL generation, SQL execution
    3. DataVisualizationService (Step 7): Chart generation and data visualization
    
    Provides unified interface for:
    - Data source ingestion and preparation
    - Natural language querying
    - Data visualization and chart generation
    - Complete analytics workflows
    """
    
    def __init__(self, database_name: str = "analytics_db"):
        """
        Initialize Data Analytics Service
        
        Args:
            database_name: Name of the database for metadata storage
        """
        self.database_name = database_name
        self.service_name = "DataAnalyticsService"
        
        # Initialize sub-services
        self.metadata_service = MetadataStoreService(database_name)
        self.query_service = None  # Initialized when database config is provided
        self.visualization_service = DataVisualizationService()  # Initialized immediately
        
        # Service tracking
        self.analytics_history = []
        self.service_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_data_sources_processed': 0,
            'total_queries_executed': 0,
            'total_visualizations_generated': 0,
            'total_cost_usd': 0.0
        }
        
        logger.info(f"Data Analytics Service initialized for database: {database_name}")
    
    async def initialize_query_service(self, database_config: Dict[str, Any]):
        """
        Initialize query service with database configuration
        
        Args:
            database_config: Database connection configuration for SQL execution
        """
        try:
            self.query_service = SQLQueryService(database_config, self.database_name)
            await self.query_service.initialize()
            logger.info("Query service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize query service: {e}")
            raise
    
    async def ingest_data_source(self,
                                source_path: str,
                                source_type: Optional[str] = None,
                                request_id: Optional[str] = None,
                                user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Function 1: Data Ingestion (Steps 1-3)
        Process data source and store in SQLite + pgvector embeddings
        
        Args:
            source_path: Path to data source (CSV, Excel, JSON, database)
            source_type: Optional source type override
            request_id: Optional custom request identifier
            user_id: Optional user ID for resource isolation and MCP registration
            
        Returns:
            Dictionary with SQLite database path and pgvector storage info
        """
        start_time = datetime.now()
        
        if not request_id:
            request_id = f"ingest_{int(start_time.timestamp())}"
        
        logger.info(f"Starting data ingestion request {request_id}")
        logger.info(f"Source: {source_path}")
        
        try:
            # Step 1-3: Process data source through metadata pipeline
            logger.info(f"Request {request_id}: Processing data source through metadata pipeline")
            metadata_pipeline = await self.metadata_service.process_data_source(
                source_path, source_type, f"{request_id}_metadata"
            )
            
            if not metadata_pipeline.success:
                return {
                    "success": False,
                    "request_id": request_id,
                    "error_message": f"Data ingestion failed: {metadata_pipeline.error_message}",
                    "processing_time_ms": self._calculate_processing_time(start_time)
                }
            
            # Extract SQLite database path from metadata pipeline
            sqlite_database_path = None
            if hasattr(metadata_pipeline, 'raw_metadata') and metadata_pipeline.raw_metadata:
                sqlite_database_path = metadata_pipeline.raw_metadata.get('csv_database_path')
            
            # If not found, construct from source path (for CSV files)
            if not sqlite_database_path and source_path.lower().endswith('.csv'):
                from pathlib import Path
                csv_name = Path(source_path).stem
                project_root = Path(__file__).resolve()
                while project_root.name != "isA_MCP":
                    project_root = project_root.parent
                    if project_root == project_root.parent:
                        break
                sqlite_dir = project_root / "resources" / "dbs" / "sqlite"
                sqlite_database_path = str(sqlite_dir / f"{csv_name}.db")
            
            # Calculate processing time and cost
            processing_time = self._calculate_processing_time(start_time)
            
            result = {
                "success": True,
                "request_id": request_id,
                "source_path": source_path,
                "sqlite_database_path": sqlite_database_path,
                "pgvector_database": self.database_name,
                "metadata_pipeline": {
                    "tables_found": metadata_pipeline.tables_found,
                    "columns_found": metadata_pipeline.columns_found,
                    "business_entities": metadata_pipeline.business_entities,
                    "semantic_tags": metadata_pipeline.semantic_tags,
                    "embeddings_stored": metadata_pipeline.embeddings_stored,
                    "search_ready": metadata_pipeline.search_ready,
                    "ai_analysis_source": metadata_pipeline.ai_analysis_source
                },
                "processing_time_ms": processing_time,
                "cost_usd": metadata_pipeline.pipeline_cost,
                "created_at": start_time.isoformat()
            }
            
            logger.info(f"Request {request_id} completed successfully: SQLite DB at {sqlite_database_path}, {metadata_pipeline.embeddings_stored} embeddings stored")
            
            # Register MCP resource for the data source if user_id provided
            if user_id:
                try:
                    await self._register_data_source_resource(
                        resource_id=request_id,
                        user_id=user_id,
                        result_data=result
                    )
                    logger.info(f"MCP resource registered for data source: {request_id}")
                except Exception as e:
                    logger.warning(f"Failed to register MCP resource: {e}")
            
            return result
            
        except Exception as e:
            processing_time = self._calculate_processing_time(start_time)
            error_message = str(e)
            
            logger.error(f"Request {request_id} failed after {processing_time:.1f}ms: {error_message}")
            
            return {
                "success": False,
                "request_id": request_id,
                "error_message": error_message,
                "processing_time_ms": processing_time
            }
    
    async def query_with_language(self,
                                 natural_language_query: str,
                                 sqlite_database_path: str,
                                 pgvector_database: Optional[str] = None,
                                 request_id: Optional[str] = None,
                                 user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Function 2: Query Processing (Steps 4-6)
        Process natural language query using SQLite database + pgvector embeddings
        
        Args:
            natural_language_query: User's natural language query
            sqlite_database_path: Path to SQLite database with the data
            pgvector_database: Name of pgvector database (defaults to service database)
            request_id: Optional request identifier
            user_id: Optional user ID for resource isolation and MCP registration
            
        Returns:
            Query processing result with SQL execution results
        """
        start_time = datetime.now()
        
        if not request_id:
            request_id = f"query_{int(start_time.timestamp())}"
        
        if not pgvector_database:
            pgvector_database = self.database_name
            
        logger.info(f"Processing query request {request_id}: {natural_language_query}")
        logger.info(f"SQLite DB: {sqlite_database_path}")
        logger.info(f"pgvector DB: {pgvector_database}")
        
        try:
            # Create database config for the specific SQLite database
            database_config = {
                'type': 'sqlite',
                'database': sqlite_database_path,
                'max_execution_time': 30,
                'max_rows': 10000
            }
            
            # Initialize query service with the correct database config
            if not self.query_service:
                await self.initialize_query_service(database_config)
            
            # Get available metadata from pgvector storage
            available_metadata = await self._get_available_metadata()
            
            if not available_metadata:
                return {
                    "success": False,
                    "request_id": request_id,
                    "original_query": natural_language_query,
                    "error_message": "No metadata available. Please ingest data first using ingest_data_source().",
                    "processing_time_ms": self._calculate_processing_time(start_time)
                }
            
            # Execute query against available metadata
            query_result = await self.query_service.process_query(
                natural_language_query,
                available_metadata
            )
            
            # Update stats
            self.service_stats['total_queries_executed'] += 1
            
            processing_time = self._calculate_processing_time(start_time)
            
            # Generate visualization if query was successful and returned data
            visualization_result = None
            if query_result.success and query_result.execution_result and query_result.execution_result.data:
                try:
                    visualization_result = await self._generate_visualization_for_query(
                        query_result, natural_language_query, request_id
                    )
                    if visualization_result and visualization_result.get('status') == 'success':
                        self.service_stats['total_visualizations_generated'] += 1
                except Exception as e:
                    logger.warning(f"Visualization generation failed for query {request_id}: {e}")
                    visualization_result = {"status": "failed", "error": str(e)}
            
            result = {
                "success": query_result.success,
                "request_id": request_id,
                "original_query": natural_language_query,
                "sqlite_database_path": sqlite_database_path,
                "pgvector_database": pgvector_database,
                "query_processing": {
                    "metadata_matches": len(query_result.metadata_matches),
                    "sql_confidence": query_result.sql_result.confidence_score if query_result.sql_result else 0,
                    "generated_sql": query_result.sql_result.sql if query_result.sql_result else None,
                    "sql_explanation": query_result.sql_result.explanation if query_result.sql_result else None
                },
                "results": {
                    "row_count": query_result.execution_result.row_count if query_result.execution_result else 0,
                    "data": query_result.execution_result.data if query_result.execution_result else [],
                    "columns": getattr(query_result.execution_result, 'columns', []) if query_result.execution_result else []
                },
                "visualization": visualization_result,  # New: Visualization result
                "fallback_attempts": len(query_result.fallback_attempts),
                "processing_time_ms": processing_time,
                "error_message": query_result.error_message,
                "warnings": query_result.warnings or []
            }
            
            if result["success"]:
                logger.info(f"Query {request_id} completed successfully: {result['results']['row_count']} rows in {processing_time:.1f}ms")
                
                # Register MCP resource for successful query result if user_id provided
                if user_id:
                    try:
                        await self._register_query_result_resource(
                            query_id=request_id,
                            user_id=user_id,
                            query_result=result
                        )
                        logger.info(f"MCP resource registered for query result: {request_id}")
                    except Exception as e:
                        logger.warning(f"Failed to register query result MCP resource: {e}")
            else:
                logger.warning(f"Query {request_id} failed: {result['error_message']}")
                
            return result
            
        except Exception as e:
            processing_time = self._calculate_processing_time(start_time)
            logger.error(f"Query request {request_id} failed: {e}")
            
            return {
                "success": False,
                "request_id": request_id,
                "original_query": natural_language_query,
                "error_message": str(e),
                "processing_time_ms": processing_time
            }
    
    async def process_data_source_and_query(self,
                                          source_path: str,
                                          natural_language_query: str,
                                          database_config: Dict[str, Any] = None,
                                          source_type: Optional[str] = None,
                                          request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Convenience method: Combines both functions for end-to-end processing
        First ingests data source, then processes query
        
        Args:
            source_path: Path to data source
            natural_language_query: User's query
            database_config: Optional database config (ignored, uses auto-detected paths)
            source_type: Optional source type
            request_id: Optional request ID
            
        Returns:
            Combined result from both operations
        """
        if not request_id:
            request_id = f"combined_{int(datetime.now().timestamp())}"
            
        logger.info(f"Starting combined processing {request_id}")
        
        try:
            # Step 1: Ingest data source
            ingestion_result = await self.ingest_data_source(
                source_path, source_type, f"{request_id}_ingest"
            )
            
            if not ingestion_result["success"]:
                return {
                    "success": False,
                    "request_id": request_id,
                    "phase": "data_ingestion",
                    "error_message": ingestion_result["error_message"],
                    "ingestion_result": ingestion_result
                }
            
            # Step 2: Query the ingested data
            query_result = await self.query_with_language(
                natural_language_query,
                ingestion_result["sqlite_database_path"],
                ingestion_result["pgvector_database"],
                f"{request_id}_query"
            )
            
            # Combine results
            combined_result = {
                "success": query_result["success"],
                "request_id": request_id,
                "source_path": source_path,
                "natural_language_query": natural_language_query,
                "ingestion_result": ingestion_result,
                "query_result": query_result,
                "total_processing_time_ms": ingestion_result["processing_time_ms"] + query_result["processing_time_ms"],
                "total_cost_usd": ingestion_result.get("cost_usd", 0.0)
            }
            
            if combined_result["success"]:
                logger.info(f"Combined processing {request_id} completed successfully")
            else:
                combined_result["error_message"] = query_result.get("error_message", "Query processing failed")
                logger.warning(f"Combined processing {request_id} failed in query phase")
                
            return combined_result
            
        except Exception as e:
            logger.error(f"Combined processing {request_id} failed: {e}")
            return {
                "success": False,
                "request_id": request_id,
                "error_message": str(e),
                "phase": "combined_processing"
            }
    
    async def process_multiple_sources(self,
                                     sources: List[Dict[str, Any]], 
                                     concurrent_limit: int = 2) -> List[PipelineResult]:
        """
        Process multiple data sources (Steps 1-3 only)
        
        Args:
            sources: List of source configurations
            concurrent_limit: Maximum concurrent processing
            
        Returns:
            List of pipeline results
        """
        logger.info(f"Processing {len(sources)} data sources")
        
        results = await self.metadata_service.process_multiple_sources(
            sources, concurrent_limit
        )
        
        # Update stats
        successful_sources = sum(1 for r in results if r.success)
        self.service_stats['total_data_sources_processed'] += len(sources)
        self.service_stats['total_cost_usd'] += sum(r.pipeline_cost for r in results)
        
        logger.info(f"Batch source processing completed: {successful_sources}/{len(sources)} successful")
        
        return results
    
    async def search_available_data(self,
                                  search_query: str,
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search across all processed metadata
        
        Args:
            search_query: Natural language search query
            limit: Maximum results to return
            
        Returns:
            Search results
        """
        return await self.metadata_service.search_metadata(search_query, limit=limit)
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status and statistics"""
        try:
            # Get metadata service stats
            metadata_stats = self.metadata_service.get_pipeline_stats()
            
            # Get query service stats if available
            query_stats = {}
            if self.query_service:
                query_stats = await self.query_service.get_processing_insights()
            
            # Get database summary
            db_summary = await self.metadata_service.get_database_summary()
            
            return {
                'service_info': {
                    'service_name': self.service_name,
                    'database_name': self.database_name,
                    'query_service_initialized': self.query_service is not None
                },
                'service_stats': self.service_stats.copy(),
                'metadata_service': metadata_stats,
                'query_service': query_stats,
                'database_summary': db_summary,
                'recent_analytics': [
                    {
                        'request_id': result.request_id,
                        'success': result.success,
                        'processing_time_ms': result.total_processing_time_ms,
                        'cost_usd': result.total_cost_usd,
                        'created_at': result.created_at.isoformat(),
                        'error': result.error_message
                    }
                    for result in self.analytics_history[-10:]  # Last 10
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {
                'service_info': {
                    'service_name': self.service_name,
                    'database_name': self.database_name,
                    'error': str(e)
                }
            }
    
    def _calculate_processing_time(self, start_time: datetime) -> float:
        """Calculate processing time in milliseconds"""
        return (datetime.now() - start_time).total_seconds() * 1000
    
    async def _record_analytics_result(self, result: AnalyticsResult):
        """Record analytics result for tracking"""
        try:
            self.analytics_history.append(result)
            
            # Update stats
            self.service_stats['total_requests'] += 1
            if result.success:
                self.service_stats['successful_requests'] += 1
            else:
                self.service_stats['failed_requests'] += 1
            
            if result.metadata_pipeline:
                if result.metadata_pipeline.success:
                    self.service_stats['total_data_sources_processed'] += 1
                self.service_stats['total_cost_usd'] += result.metadata_pipeline.pipeline_cost
            
            if result.query_result and result.query_result.success:
                self.service_stats['total_queries_executed'] += 1
            
            # Keep only recent history
            if len(self.analytics_history) > 100:
                self.analytics_history = self.analytics_history[-100:]
                
        except Exception as e:
            logger.error(f"Failed to record analytics result: {e}")
    
    async def _get_available_metadata(self) -> Optional[SemanticMetadata]:
        """Get the most recent available semantic metadata"""
        try:
            # This is a simplified approach - in practice you might want to:
            # 1. Combine metadata from multiple sources
            # 2. Allow user to specify which metadata to use
            # 3. Cache metadata for performance
            
            pipeline_stats = self.metadata_service.get_pipeline_stats()
            recent_pipelines = pipeline_stats.get('recent_pipelines', [])
            
            # Find the most recent successful pipeline
            for pipeline_info in reversed(recent_pipelines):
                if pipeline_info['success']:
                    pipeline_result = self.metadata_service.get_pipeline_result(pipeline_info['pipeline_id'])
                    if pipeline_result and pipeline_result.semantic_metadata:
                        return pipeline_result.semantic_metadata
            
            logger.warning("No available semantic metadata found")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get available metadata: {e}")
            return None
    
    @classmethod
    def create_for_sqlite_testing(cls, 
                                 database_filename: str,
                                 user_id: Optional[str] = None) -> 'DataAnalyticsService':
        """
        Create Data Analytics Service configured for SQLite testing
        
        Args:
            database_filename: SQLite database filename
            user_id: Optional user ID for user-specific databases
            
        Returns:
            DataAnalyticsService configured for SQLite
        """
        # Create service instance
        service = cls(f"sqlite_{database_filename}")
        
        # Pre-configure for SQLite
        current_dir = Path(__file__).resolve()
        project_root = current_dir
        while project_root.name != "isA_MCP":
            project_root = project_root.parent
            if project_root == project_root.parent:
                break
        
        sqlite_dir = project_root / "resources" / "dbs" / "sqlite"
        
        if user_id:
            db_path = str(sqlite_dir / f"user_{user_id}_{database_filename}")
        else:
            db_path = str(sqlite_dir / database_filename)
        
        # Store SQLite config for easy initialization
        service._sqlite_config = {
            'type': 'sqlite',
            'database': db_path,
            'max_execution_time': 30,
            'max_rows': 10000
        }
        
        return service
    
    async def initialize_for_sqlite(self):
        """Initialize the service for SQLite if created with create_for_sqlite_testing"""
        if hasattr(self, '_sqlite_config'):
            await self.initialize_query_service(self._sqlite_config)
        else:
            raise Exception("Not configured for SQLite. Use create_for_sqlite_testing() first.")
    
    async def _register_data_source_resource(self,
                                           resource_id: str,
                                           user_id: int,
                                           result_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register MCP resource for data source ingestion result.
        
        Args:
            resource_id: Unique resource identifier
            user_id: User ID who owns the resource
            result_data: Ingestion result data
            
        Returns:
            Dict containing registration result
        """
        try:
            # Import the resource manager
            from resources.data_analytics_resource import data_analytics_resources
            
            # Prepare resource data for registration
            resource_data = {
                'source_path': result_data.get('source_path'),
                'sqlite_database_path': result_data.get('sqlite_database_path'),
                'pgvector_database': result_data.get('pgvector_database'),
                'processing_time_ms': result_data.get('processing_time_ms'),
                'cost_usd': result_data.get('cost_usd'),
                'created_at': result_data.get('created_at'),
                'metadata': result_data.get('metadata_pipeline', {}),
                'source_metadata': {
                    'service': 'DataAnalyticsService',
                    'database_name': self.database_name,
                    'ingestion_method': 'process_data_source'
                }
            }
            
            # Register the resource
            registration_result = await data_analytics_resources.register_analytics_resource(
                resource_id=resource_id,
                user_id=user_id,
                resource_data=resource_data
            )
            
            return registration_result
            
        except Exception as e:
            logger.error(f"Failed to register data source resource: {e}")
            return {
                'success': False,
                'error': str(e),
                'resource_id': resource_id,
                'user_id': user_id
            }
    
    async def _register_query_result_resource(self,
                                            query_id: str,
                                            user_id: int,
                                            query_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register MCP resource for query result.
        
        Args:
            query_id: Unique query identifier
            user_id: User ID who executed the query
            query_result: Query result data
            
        Returns:
            Dict containing registration result
        """
        try:
            # Import the resource manager
            from resources.data_analytics_resource import data_analytics_resources
            
            # Prepare query data for registration
            query_data = {
                'original_query': query_result.get('original_query'),
                'generated_sql': query_result.get('query_processing', {}).get('generated_sql'),
                'row_count': query_result.get('results', {}).get('row_count', 0),
                'processing_time_ms': query_result.get('processing_time_ms'),
                'sqlite_database_path': query_result.get('sqlite_database_path'),
                'pgvector_database': query_result.get('pgvector_database'),
                'sql_confidence': query_result.get('query_processing', {}).get('sql_confidence', 0),
                'metadata_matches': query_result.get('query_processing', {}).get('metadata_matches', 0),
                'fallback_attempts': query_result.get('fallback_attempts', 0)
            }
            
            # Register the query result
            registration_result = await data_analytics_resources.register_query_result(
                query_id=query_id,
                user_id=user_id,
                query_data=query_data
            )
            
            return registration_result
            
        except Exception as e:
            logger.error(f"Failed to register query result resource: {e}")
            return {
                'success': False,
                'error': str(e),
                'resource_id': query_id,
                'user_id': user_id
            }
    
    async def generate_visualization(self,
                                   query_result_data: Dict[str, Any],
                                   chart_type_hint: Optional[str] = None,
                                   export_formats: Optional[List[str]] = None,
                                   request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate visualization from query results
        
        Args:
            query_result_data: Query result data with columns and data
            chart_type_hint: Optional chart type preference (bar, line, pie, etc.)
            export_formats: Optional list of export formats (png, svg, json, etc.)
            request_id: Optional request identifier
        
        Returns:
            Visualization specification and metadata
        """
        start_time = datetime.now()
        
        if not request_id:
            request_id = f"viz_{int(start_time.timestamp())}"
        
        logger.info(f"Generating visualization for request {request_id}")
        
        try:
            # Extract data from query result
            data = query_result_data.get('data', [])
            columns = query_result_data.get('columns', [])
            
            if not data or not columns:
                return {
                    "success": False,
                    "request_id": request_id,
                    "error_message": "No data available for visualization",
                    "processing_time_ms": self._calculate_processing_time(start_time)
                }
            
            # Create execution result format expected by visualization service
            from .data_service.sql_executor import ExecutionResult
            execution_result = ExecutionResult(
                success=True,
                data=data,
                column_names=columns,
                row_count=len(data),
                execution_time_ms=0,
                sql_executed="Custom visualization request"
            )
            
            # Create query context
            from .data_service.query_matcher import QueryContext
            query_context = QueryContext(
                entities_mentioned=columns,
                attributes_mentioned=columns,
                operations=["select", "visualize"],
                filters=[],
                aggregations=[],
                temporal_references=[],
                business_intent="Create visualization from data",
                confidence_score=1.0
            )
            
            # Create semantic metadata
            semantic_metadata = self._create_basic_semantic_metadata(data, columns)
            
            # Map chart type hint if provided
            chart_type_enum = None
            if chart_type_hint:
                try:
                    from ..processors.data_processors.chart_generators.chart_base import ChartType
                    type_mapping = {
                        'bar': ChartType.BAR,
                        'line': ChartType.LINE,
                        'pie': ChartType.PIE,
                        'scatter': ChartType.SCATTER,
                        'area': ChartType.AREA,
                        'histogram': ChartType.HISTOGRAM,
                        'kpi': ChartType.BAR,  # Map KPI to BAR (matplotlib compatible)
                        'metric': ChartType.BAR  # Map metric to BAR (matplotlib compatible)
                    }
                    chart_type_enum = type_mapping.get(chart_type_hint.lower())
                    if chart_type_enum:
                        logger.info(f"Mapped chart type hint '{chart_type_hint}' to {chart_type_enum}")
                except Exception as e:
                    logger.warning(f"Invalid chart type hint: {chart_type_hint}, using auto-detection: {e}")
            
            # Map export formats if provided
            export_format_enums = None
            if export_formats:
                try:
                    from .data_service.data_visualization import ExportFormat
                    format_mapping = {
                        'png': ExportFormat.PNG,
                        'svg': ExportFormat.SVG,
                        'pdf': ExportFormat.PDF,
                        'json': ExportFormat.JSON,
                        'csv': ExportFormat.CSV
                    }
                    export_format_enums = [format_mapping.get(fmt.lower()) for fmt in export_formats if fmt.lower() in format_mapping]
                except Exception as e:
                    logger.warning(f"Invalid export formats: {export_formats}, using defaults")
            
            # Generate visualization
            visualization_result = await self.visualization_service.generate_visualization_spec(
                execution_result=execution_result,
                query_context=query_context,
                semantic_metadata=semantic_metadata,
                chart_type_hint=chart_type_enum,
                export_formats=export_format_enums or []
            )
            
            processing_time = self._calculate_processing_time(start_time)
            
            # Update stats
            if visualization_result.get('status') == 'success':
                self.service_stats['total_visualizations_generated'] += 1
            
            result = {
                "success": visualization_result.get('status') == 'success',
                "request_id": request_id,
                "visualization_result": visualization_result,
                "input_data_summary": {
                    "row_count": len(data),
                    "column_count": len(columns),
                    "columns": columns
                },
                "processing_time_ms": processing_time,
                "chart_type_used": chart_type_hint or "auto-detected",
                "export_formats_available": export_formats or ["png", "svg", "json"]
            }
            
            logger.info(f"Visualization {request_id} completed successfully in {processing_time:.1f}ms")
            return result
            
        except Exception as e:
            processing_time = self._calculate_processing_time(start_time)
            logger.error(f"Visualization generation {request_id} failed: {e}")
            
            return {
                "success": False,
                "request_id": request_id,
                "error_message": str(e),
                "processing_time_ms": processing_time
            }
    
    async def _generate_visualization_for_query(self,
                                              query_result: QueryResult,
                                              original_query: str,
                                              request_id: str) -> Optional[Dict[str, Any]]:
        """Generate visualization for query result"""
        try:
            if not query_result.execution_result or not query_result.execution_result.data:
                return None
            
            # Create query context from original query
            from .data_service.query_matcher import QueryContext
            query_context = QueryContext(
                entities_mentioned=getattr(query_result.execution_result, 'column_names', []),
                attributes_mentioned=getattr(query_result.execution_result, 'column_names', []),
                operations=["select", "analyze"],
                filters=[],
                aggregations=[],
                temporal_references=[],
                business_intent=original_query,
                confidence_score=0.8
            )
            
            # Get or create semantic metadata
            available_metadata = await self._get_available_metadata()
            if not available_metadata:
                available_metadata = self._create_basic_semantic_metadata(
                    query_result.execution_result.data,
                    query_result.execution_result.column_names
                )
            
            # Generate visualization
            visualization_result = await self.visualization_service.generate_visualization_spec(
                execution_result=query_result.execution_result,
                query_context=query_context,
                semantic_metadata=available_metadata
            )
            
            return visualization_result
            
        except Exception as e:
            logger.error(f"Failed to generate visualization for query {request_id}: {e}")
            return {"status": "error", "error_message": str(e)}
    
    def _create_basic_semantic_metadata(self, data: List[Dict], columns: List[str]):
        """Create basic semantic metadata from data"""
        try:
            # Analyze data types
            data_types = {}
            for col in columns:
                if data:
                    sample_value = data[0].get(col)
                    if isinstance(sample_value, (int, float)):
                        data_types[col] = "numeric"
                    elif isinstance(sample_value, str):
                        # Simple date detection
                        if any(date_word in col.lower() for date_word in ['date', 'time', 'created', 'updated']):
                            data_types[col] = "datetime"
                        else:
                            data_types[col] = "categorical"
                    else:
                        data_types[col] = "unknown"
            
            from .data_service.semantic_enricher import SemanticMetadata
            return SemanticMetadata(
                original_metadata={col: {"type": dt} for col, dt in data_types.items()},
                business_entities=[],
                semantic_tags={col: [data_types.get(col, "unknown")] for col in columns},
                data_patterns=[],
                business_rules=[],
                domain_classification={"domain": "data_analysis", "confidence": 0.5},
                confidence_scores={"overall": 0.5},
                ai_analysis={"context": "Visualization request"}
            )
            
        except Exception as e:
            logger.warning(f"Failed to create semantic metadata: {e}")
            # Return minimal metadata
            from .data_service.semantic_enricher import SemanticMetadata
            return SemanticMetadata(
                original_metadata={},
                business_entities=[],
                semantic_tags={},
                data_patterns=[],
                business_rules=[],
                domain_classification={},
                confidence_scores={},
                ai_analysis={}
            )


# Global service instances
_analytics_services = {}

def get_analytics_service(database_name: str = "default_analytics") -> DataAnalyticsService:
    """Get analytics service instance for a specific database"""
    global _analytics_services
    
    if database_name not in _analytics_services:
        _analytics_services[database_name] = DataAnalyticsService(database_name)
    
    return _analytics_services[database_name]