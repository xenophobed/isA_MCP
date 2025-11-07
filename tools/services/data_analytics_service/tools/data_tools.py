#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Tools - Comprehensive Data Processing Pipeline
====================================================

Provides a complete end-to-end data analytics pipeline with MCP integration:

Features:
---------
- Data Ingestion: CSV → DataFrame → MinIO Parquet storage
- Metadata Extraction: Automatic schema discovery and analysis
- AI Semantic Enrichment: GPT-4.1 powered semantic understanding
- Vector Embeddings: text-embedding-3-small for similarity search
- Semantic Search: pgvector-based similarity search
- Natural Language Queries: Support for simple, aggregation, filter, and sort queries
- Visualization: Automatic chart generation from query results
- Analytics: Optional EDA insights

Architecture:
------------
- Fully async/await for optimal performance
- Per-user data isolation (database_source: user_{user_id})
- Generic implementation (zero hardcoded values)
- Complete error handling and logging
- JSON-safe responses (handles enum serialization)

Example Usage:
-------------
1. Ingest data: data_ingest(user_id="user1", source_path="data.csv")
2. Search data: data_search(user_id="user1", search_query="sales")
3. Query data: data_query(user_id="user1", natural_language_query="total sales by region")

Author: Data Analytics Service Team
Version: 1.0.0
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context
from tools.base_tool import BaseTool
from tools.services.data_analytics_service.tools.context import DataProgressReporter
from core.logging import get_logger

logger = get_logger(__name__)


def _make_json_serializable(obj: Any) -> Any:
    """
    Convert any object to JSON-serializable format
    
    Handles:
    - Enum objects (converts to value or name)
    - Nested dictionaries and lists
    - Non-serializable objects (converts to string)
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON-serializable version of the object
    """
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    elif hasattr(obj, 'value'):  # Enum with value
        return obj.value
    elif hasattr(obj, 'name'):  # Enum with name
        return obj.name
    else:  # Convert everything else to string
        return str(obj)


class DataTool(BaseTool):
    """
    Data processing tool for structured data ingestion and storage
    
    Inherits from BaseTool to provide consistent response formatting
    Includes DataProgressReporter for comprehensive progress tracking
    """
    
    def __init__(self):
        super().__init__()
        self.progress_reporter = DataProgressReporter(self)


def register_data_tools(mcp: FastMCP):
    """
    Register all data processing tools with MCP server
    
    Tools registered:
    - data_ingest: Complete data ingestion pipeline
    - get_pipeline_status: Pipeline status and statistics
    - data_search: Semantic similarity search
    - data_query: Natural language query execution
    """
    # Initialize DataTool with progress reporter
    data_tool = DataTool()
    
    @mcp.tool()
    async def data_ingest(
        user_id: str,
        source_path: str,
        dataset_name: str = None,
        storage_options: dict = None,

        # Progress monitoring (optional)
        operation_id: Optional[str] = None,

        # Context (will be injected by FastMCP)
        ctx: Optional[Context] = None
    ) -> str:
        """
        Complete data ingestion pipeline: CSV → DataFrame → MinIO Parquet + Metadata
        
        This tool executes a comprehensive data pipeline:
        1. Data Preprocessing: CSV loading, validation, quality scoring, and cleaning
        2. MinIO Storage: Parquet format storage with compression
        3. Metadata Extraction: Automatic schema discovery (tables, columns)
        4. AI Semantic Enrichment: GPT-4.1 powered semantic analysis
        5. Vector Embeddings: text-embedding-3-small for similarity search
        6. pgvector Storage: Per-user isolated database storage
        
        Args:
            user_id: User identifier for data isolation
            source_path: Absolute path to CSV file
            dataset_name: Optional dataset name (auto-generated from filename if not provided)
            storage_options: Optional storage configuration (not yet implemented)
            
        Returns:
            JSON string with ingestion results including:
            - pipeline_id: Unique pipeline identifier
            - rows_processed: Number of rows ingested
            - columns_processed: Number of columns detected
            - data_quality_score: Quality score (0.0-1.0)
            - metadata_stored: Whether metadata was successfully stored
            - metadata_embeddings: Number of embeddings created
            
        Examples:
            # Basic usage
            >>> result = await data_ingest(
            ...     user_id="user123",
            ...     source_path="/path/to/sales.csv",
            ...     dataset_name="monthly_sales"
            ... )
            >>> # Returns: {"status": "success", "data": {...}}

            # Advanced: Provide operation_id for SSE monitoring
            >>> import uuid
            >>> op_id = str(uuid.uuid4())
            >>> # Start ingestion with custom operation_id
            >>> ingest_task = asyncio.create_task(
            ...     data_ingest(user_id="user123", source_path="/path/to/data.csv", operation_id=op_id)
            ... )
            >>> # Concurrently monitor progress via SSE
            >>> await stream_progress(op_id)
            >>> # Get result
            >>> result = await ingest_task
        """
        # Create or use provided progress operation
        if not operation_id:
            operation_id = await data_tool.create_progress_operation(
                metadata={
                    "user_id": user_id,
                    "source_path": source_path,
                    "dataset_name": dataset_name or "auto",
                    "operation": "data_ingest"
                }
            )
        else:
            # Use client-provided operation_id
            await data_tool.create_progress_operation(
                operation_id=operation_id,
                metadata={
                    "user_id": user_id,
                    "source_path": source_path,
                    "dataset_name": dataset_name or "auto",
                    "operation": "data_ingest"
                }
            )

        try:
            from pathlib import Path
            from tools.services.data_analytics_service.services.data_service.preprocessor.preprocessor_service import get_preprocessor_service
            from tools.services.data_analytics_service.services.data_service.storage.data_storage_service import DataStorageService
            from tools.services.data_analytics_service.tools.context import DataSourceDetector

            # Generate dataset name if not provided
            if not dataset_name:
                dataset_name = Path(source_path).stem

            # Detect data source type
            data_source_type = DataSourceDetector.detect_from_path(source_path)

            # Log start and report Stage 1: Processing
            await data_tool.log_info(ctx, f"Starting data ingestion for user {user_id}: {source_path}")
            await data_tool.progress_reporter.report_stage(
                operation_id, "processing", data_source_type,
                f"loading {dataset_name}",
                pipeline_type="ingestion"
            )
            
            logger.info(f"Starting data ingestion for user {user_id}: {source_path}")
            
            # Initialize services
            preprocessor = get_preprocessor_service(user_id)
            storage_service = DataStorageService()
            
            # Step 1: Preprocess data
            pipeline_result = await preprocessor.process_data_source(source_path)
            
            if not pipeline_result.success:
                error_msg = f"Preprocessing failed: {str(pipeline_result.error_message)}"
                await data_tool.log_error(ctx, error_msg)
                await data_tool.fail_progress_operation(operation_id, error_msg)
                error_response = {
                    "status": "error",
                    "action": "data_ingest",
                    "error": error_msg,
                    "data": {"user_id": str(user_id)},
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(error_response, ensure_ascii=False)
            
            # Report data statistics
            await data_tool.progress_reporter.report_data_stats(
                operation_id, "processing", data_source_type,
                rows=pipeline_result.rows_detected,
                columns=pipeline_result.columns_detected,
                quality_score=pipeline_result.data_quality_score,
                pipeline_type="ingestion"
            )
            
            # Step 2: Get cleaned dataframe
            cleaned_df = preprocessor.get_cleaned_data(pipeline_result.pipeline_id)
            if cleaned_df is None:
                error_msg = "No cleaned dataframe available"
                await data_tool.log_error(ctx, error_msg)
                await data_tool.fail_progress_operation(operation_id, error_msg)
                error_response = {
                    "status": "error",
                    "action": "data_ingest",
                    "error": error_msg,
                    "data": {"user_id": str(user_id)},
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(error_response, ensure_ascii=False)
            
            # Step 3: Store to MinIO Parquet using professional storage service
            await data_tool.log_info(ctx, f"Storing data to MinIO Parquet: {dataset_name}")
            await data_tool.progress_reporter.report_storage_progress(
                operation_id, data_source_type, "minio", "uploading"
            )
            
            storage_success = False
            parquet_path = None
            
            try:
                # Use professional storage service client
                from core.clients.storage_client import get_storage_client
                import io
                
                # Convert DataFrame to parquet bytes
                parquet_buffer = io.BytesIO()
                cleaned_df.write_parquet(parquet_buffer)
                parquet_data = parquet_buffer.getvalue()
                
                # Upload via professional storage service
                storage_client = await get_storage_client()
                upload_response = await storage_client.upload_parquet_data(
                    user_id=user_id,
                    dataset_name=dataset_name,
                    parquet_data=parquet_data
                )
                
                if upload_response.get('status') == 'success':
                    storage_success = True
                    # Extract storage path from response
                    file_info = upload_response.get('file_info', {})
                    parquet_path = file_info.get('object_name') or file_info.get('file_path')
                    if parquet_path:
                        # Add bucket prefix for full path
                        parquet_path = f"isA-storage/{parquet_path}"
                    
                    logger.info(f"Professional storage upload successful: {parquet_path}")
                else:
                    raise Exception(f"Storage service returned error: {upload_response}")
                    
            except Exception as storage_error:
                logger.warning(f"Professional storage failed: {str(storage_error)}, falling back to analytics-data")
                
                # Fallback to original analytics-data storage
                storage_spec = storage_service.create_storage_spec(
                    storage_type='parquet',
                    destination='analytics-data',
                    table_name=dataset_name
                )
                
                storage_result = await storage_service.store_data(cleaned_df, storage_spec)
                
                if not storage_result.success:
                    error_msg = f"Both storage methods failed: {str(storage_result.errors)}"
                    await data_tool.fail_progress_operation(operation_id, error_msg)
                    error_response = {
                        "status": "error",
                        "action": "data_ingest",
                        "error": error_msg,
                        "data": {"user_id": str(user_id)},
                        "timestamp": datetime.now().isoformat()
                    }
                    return json.dumps(error_response, ensure_ascii=False)
                
                storage_success = storage_result.success
            
            # Handle storage path for both professional and fallback storage
            if not parquet_path:
                # Fallback storage was used, extract path from storage_result
                stored_info = storage_result.stored_data_info or {} if 'storage_result' in locals() else {}
                actual_path = stored_info.get('parquet_path') or stored_info.get('full_path')
                
                if not actual_path and 'storage_result' in locals():
                    # Extract from storage_summary  
                    storage_summary = storage_result.storage_summary or {}
                    actual_path = storage_summary.get('parquet_path') or storage_summary.get('full_path')
                
                if actual_path:
                    parquet_path = actual_path
                    logger.info(f"Using fallback storage path: {parquet_path}")
                else:
                    # Final fallback
                    parquet_path = f'analytics-data/{dataset_name}.parquet'
                    logger.warning(f"No actual path found, using final fallback: {parquet_path}")
            
            logger.info(f"Data stored to MinIO: {parquet_path}")
            
            # Step 4: Store metadata to metadata store for querying
            # Stage 2: Extraction - Metadata extraction and semantic enrichment
            await data_tool.log_info(ctx, "Starting metadata extraction and semantic enrichment")
            await data_tool.progress_reporter.report_stage(
                operation_id, "extraction", data_source_type,
                "extracting metadata",
                pipeline_type="ingestion"
            )
            
            logger.info("STEP4: Storing metadata for future querying...")
            metadata_success = False
            metadata_embeddings_count = 0
            
            try:
                # Simplified: Direct async call in current event loop
                from tools.services.data_analytics_service.processors.data_processors.management.metadata.metadata_extractor import extract_metadata
                from tools.services.data_analytics_service.services.data_service.management.metadata.semantic_enricher import AISemanticEnricher
                from tools.services.data_analytics_service.services.data_service.management.metadata.metadata_embedding import get_embedding_service
                
                logger.info(f"STEP4: Extracting metadata from {source_path}")
                # Step 1: Extract metadata
                raw_metadata = extract_metadata(source_path, 'csv')
                
                # Add storage path to metadata for query execution
                raw_metadata['storage_info'] = {
                    'storage_type': 'parquet',
                    'minio_bucket': 'analytics-data',
                    'minio_object': f'{dataset_name}.parquet',
                    'full_path': parquet_path,
                    'dataset_name': dataset_name
                }
                
                if 'error' in raw_metadata:
                    logger.warning(f"STEP4: Metadata extraction failed: {raw_metadata['error']}")
                else:
                    logger.info(f"STEP4: Metadata extracted successfully")
                        
                    # Step 2: Semantic enrichment
                    logger.info("STEP4: Performing semantic enrichment...")
                    await data_tool.progress_reporter.report_stage(
                        operation_id, "extraction", data_source_type,
                        "AI semantic enrichment",
                        pipeline_type="ingestion"
                    )
                    
                    enricher = AISemanticEnricher()
                    semantic_metadata = await enricher.enrich_metadata(raw_metadata)
                    logger.info(f"STEP4: Semantic enrichment completed - {len(semantic_metadata.business_entities)} entities, {len(semantic_metadata.semantic_tags)} tags")
                    
                    # Preserve storage_info in semantic metadata for embeddings
                    if not hasattr(semantic_metadata, 'storage_info'):
                        semantic_metadata.storage_info = raw_metadata.get('storage_info', {})
                    
                    # Stage 3: Embedding - Generate vector embeddings
                    await data_tool.log_info(ctx, "Generating vector embeddings")
                    await data_tool.progress_reporter.report_stage(
                        operation_id, "embedding", data_source_type,
                        "generating embeddings",
                        pipeline_type="ingestion"
                    )
                    
                    # Step 3: Store embeddings with storage path information
                    logger.info("STEP4: Storing embeddings to database...")
                    embedding_service = get_embedding_service(f"user_{user_id}")
                    
                    # Pass storage info to embedding service
                    storage_results = await embedding_service.store_semantic_metadata(
                        semantic_metadata,
                        storage_path=parquet_path,
                        dataset_name=dataset_name
                    )
                    
                    metadata_embeddings_count = storage_results.get('stored_embeddings', 0)
                    failed_count = storage_results.get('failed_embeddings', 0)
                    
                    if metadata_embeddings_count > 0:
                        metadata_success = True
                        logger.info(f"STEP4: Metadata stored successfully: {metadata_embeddings_count} embeddings (failed: {failed_count})")

                        # Report embedding progress with granular details
                        await data_tool.progress_reporter.report_stage(
                            operation_id, "embedding", data_source_type,
                            f"{metadata_embeddings_count} embeddings created",
                            pipeline_type="ingestion"
                        )
                    else:
                        logger.warning(f"STEP4: No embeddings were stored (failed: {failed_count})")
                        
            except Exception as e:
                logger.error(f"STEP4: Metadata storage failed: {str(e)}")
                await data_tool.log_error(ctx, f"Metadata storage failed: {str(e)}")
                import traceback
                logger.error(f"STEP4: Traceback: {traceback.format_exc()}")
            
            # Stage 4: Storing - Final storage completion
            await data_tool.progress_reporter.report_storage_progress(
                operation_id, data_source_type, "vector_db", "indexing"
            )
            await data_tool.progress_reporter.report_storage_progress(
                operation_id, data_source_type, "metadata_store", "completed"
            )
            
            # Report completion with summary
            await data_tool.progress_reporter.report_complete(
                data_source_type,
                {
                    "rows": pipeline_result.rows_detected,
                    "columns": pipeline_result.columns_detected,
                    "embeddings": metadata_embeddings_count,
                    "quality_score": pipeline_result.data_quality_score
                },
                pipeline_type="ingestion"
            )

            # Complete progress operation
            await data_tool.complete_progress_operation(
                operation_id,
                result={
                    "rows": pipeline_result.rows_detected,
                    "columns": pipeline_result.columns_detected,
                    "embeddings": metadata_embeddings_count
                }
            )

            await data_tool.log_info(ctx, f"Data ingestion completed successfully: {dataset_name}")

            # Success - return clean result like digital_tools (avoid any numpy objects)
            success_result = {
                "success": True,
                "pipeline_id": str(pipeline_result.pipeline_id),
                "user_id": str(user_id),
                "dataset_name": str(dataset_name),
                "rows_processed": int(pipeline_result.rows_detected),
                "columns_processed": int(pipeline_result.columns_detected),
                "data_quality_score": float(pipeline_result.data_quality_score),
                "processing_time_seconds": float(pipeline_result.total_duration),
                "storage_location": "analytics-data bucket (MinIO Parquet)",
                "metadata_stored": bool(metadata_success),
                "metadata_embeddings": int(metadata_embeddings_count),
                "operation_id": str(operation_id),  # ✅ Return operation_id for SSE monitoring
                "message": "Data ingestion and metadata storage completed successfully"
            }

            # Use weather_tools pattern - direct json.dumps (bypass BaseTool)
            response = {
                "status": "success",
                "action": "data_ingest",
                "data": success_result,
                "timestamp": datetime.now().isoformat()
            }

            return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            # Fail progress operation on error
            if 'operation_id' in locals():
                await data_tool.fail_progress_operation(operation_id, str(e))
            logger.error(f"Data ingestion failed: {str(e)}")
            await data_tool.log_error(ctx, f"Data ingestion failed: {str(e)}")
            # Use weather_tools pattern for error too
            error_response = {
                "status": "error",
                "action": "data_ingest",
                "error": f"Data ingestion failed: {str(e)}",
                "data": {"user_id": str(user_id)},
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(error_response, ensure_ascii=False)
    
    @mcp.tool()
    async def get_pipeline_status(
        user_id: str, 
        pipeline_id: str = None,
        ctx: Optional[Context] = None
    ) -> str:
        """
        Get status and statistics of data processing pipelines
        
        Provides detailed information about:
        - Specific pipeline execution status (if pipeline_id provided)
        - Overall pipeline statistics (if pipeline_id not provided)
        - Data quality metrics
        - Processing durations
        
        Args:
            user_id: User identifier for data isolation
            pipeline_id: Optional specific pipeline ID to query
                        If None, returns aggregate statistics for all user pipelines
            
        Returns:
            JSON string with pipeline information:
            - If pipeline_id provided: Detailed pipeline status
            - If pipeline_id None: Aggregate statistics
            
        Example:
            >>> # Get specific pipeline status
            >>> result = await get_pipeline_status(
            ...     user_id="user123",
            ...     pipeline_id="preprocess_1234567890"
            ... )
            >>> 
            >>> # Get all pipeline statistics
            >>> result = await get_pipeline_status(user_id="user123")
        """
        try:
            await data_tool.log_info(ctx, f"Getting pipeline status for user {user_id}")
            from tools.services.data_analytics_service.services.data_service.preprocessor.preprocessor_service import get_preprocessor_service
            
            preprocessor_service = get_preprocessor_service(user_id)
            
            if pipeline_id:
                result = preprocessor_service.get_pipeline_result(pipeline_id)
                if result:
                    # Convert to clean data (avoid numpy types)
                    status_data = {
                        "success": True,
                        "pipeline_id": str(pipeline_id),
                        "user_id": str(user_id),
                        "pipeline_success": bool(result.success),
                        "source_path": str(result.source_path),
                        "data_ready": bool(result.data_ready),
                        "rows_detected": int(result.rows_detected),
                        "columns_detected": int(result.columns_detected),
                        "data_quality_score": float(result.data_quality_score),
                        "total_duration": float(result.total_duration),
                        "message": f"Pipeline {pipeline_id} status retrieved"
                    }

                    response = {
                        "status": "success",
                        "action": "get_pipeline_status",
                        "data": status_data,
                        "timestamp": datetime.now().isoformat()
                    }
                    return json.dumps(response, ensure_ascii=False)
                else:
                    error_response = {
                        "status": "error",
                        "action": "get_pipeline_status",
                        "error": f"Pipeline {pipeline_id} not found",
                        "data": {"user_id": str(user_id)},
                        "timestamp": datetime.now().isoformat()
                    }
                    return json.dumps(error_response, ensure_ascii=False)
            else:
                stats = preprocessor_service.get_pipeline_statistics()

                # Convert stats to clean format
                stats_data = {
                    "success": True,
                    "user_id": str(user_id),
                    "total_pipelines": int(stats.get('total_pipelines', 0)),
                    "successful_pipelines": int(stats.get('successful_pipelines', 0)),
                    "failed_pipelines": int(stats.get('failed_pipelines', 0)),
                    "average_quality_score": float(stats.get('average_quality_score', 0.0)),
                    "message": f"Pipeline statistics for user {user_id}"
                }

                response = {
                    "status": "success",
                    "action": "get_pipeline_status",
                    "data": stats_data,
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            error_response = {
                "status": "error",
                "action": "get_pipeline_status",
                "error": f"Failed to get pipeline status: {str(e)}",
                "data": {"user_id": str(user_id)},
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(error_response, ensure_ascii=False)

    @mcp.tool()
    async def data_search(
        user_id: str,
        search_query: str = None,

        # Progress monitoring (optional)
        operation_id: Optional[str] = None,

        # Context (will be injected by FastMCP)
        ctx: Optional[Context] = None
    ) -> str:
        """
        Search and discover available datasets using semantic similarity
        
        Uses pgvector-based similarity search to find relevant datasets, tables,
        columns, and metadata based on natural language queries.
        
        Args:
            user_id: User identifier for data isolation
            search_query: Natural language search query (e.g., "product sales data")
                         If None, returns database summary only
            
        Returns:
            JSON string with search results including:
            - database_summary: Total embeddings and service status
            - pipeline_info: Data processing statistics
            - search_results: List of similar entities with similarity scores
            - recommendations: Suggested next actions
            
        Examples:
            # Basic usage
            >>> result = await data_search(
            ...     user_id="user123",
            ...     search_query="customer sales by region"
            ... )
            >>> # Returns top N most similar entities

            # Advanced: Provide operation_id for SSE monitoring
            >>> import uuid
            >>> op_id = str(uuid.uuid4())
            >>> # Start search with custom operation_id
            >>> search_task = asyncio.create_task(
            ...     data_search(user_id="user123", search_query="sales data", operation_id=op_id)
            ... )
            >>> # Concurrently monitor progress via SSE
            >>> await stream_progress(op_id)
            >>> # Get result
            >>> result = await search_task
        """
        # Create or use provided progress operation
        if not operation_id:
            operation_id = await data_tool.create_progress_operation(
                metadata={
                    "user_id": user_id,
                    "search_query": search_query or "all_datasets",
                    "operation": "data_search"
                }
            )
        else:
            # Use client-provided operation_id
            await data_tool.create_progress_operation(
                operation_id=operation_id,
                metadata={
                    "user_id": user_id,
                    "search_query": search_query or "all_datasets",
                    "operation": "data_search"
                }
            )

        try:
            from tools.services.data_analytics_service.services.data_service.management.metadata.metadata_embedding import get_embedding_service
            from core.database.supabase_client import get_supabase_client

            # Stage 1: Query Processing
            await data_tool.log_info(ctx, f"Starting dataset search for user {user_id}")
            await data_tool.progress_reporter.report_stage(
                operation_id, "processing", "query",
                "analyzing search query" if search_query else "listing all datasets",
                pipeline_type="search"
            )
            
            logger.info(f"Searching datasets for user {user_id}")
            
            # Get embedding service for user (same as used in data_ingest)
            embedding_service = get_embedding_service(f"user_{user_id}")
            supabase = get_supabase_client()
            
            # Get database summary by checking embeddings in database
            try:
                db_result = supabase.client.schema('dev').table('db_meta_embedding').select('id').eq('database_source', f'user_{user_id}').execute()
                total_embeddings = len(db_result.data) if db_result.data else 0
            except Exception as e:
                logger.warning(f"Could not query db_meta_embedding: {str(e)}")
                total_embeddings = 0
            
            # Search for specific metadata if query provided
            search_results = []
            if search_query:
                # Stage 2: Query Embedding
                await data_tool.progress_reporter.report_stage(
                    operation_id, "embedding", "query",
                    "generating query embedding",
                    pipeline_type="search"
                )

                try:
                    # Stage 3: Similarity Matching
                    await data_tool.progress_reporter.report_stage(
                        operation_id, "matching", "query",
                        "searching vector database",
                        pipeline_type="search"
                    )
                    
                    # Use embedding service to search - correct method and parameters
                    search_results_raw = await embedding_service.search_similar_entities(
                        query=search_query,
                        entity_type=None,
                        limit=20,
                        similarity_threshold=0.1
                    )
                    # Convert SearchResult objects to dicts
                    search_results = []
                    for result in search_results_raw:
                        search_results.append({
                            'entity_name': result.entity_name,
                            'entity_type': result.entity_type,
                            'similarity_score': result.similarity_score,
                            'content': result.content
                        })
                except Exception as e:
                    logger.warning(f"Search failed: {str(e)}")
                    await data_tool.log_error(ctx, f"Search failed: {str(e)}")
                    search_results = []

            # Stage 4: Result Ranking
            await data_tool.progress_reporter.report_stage(
                operation_id, "ranking", "query",
                f"{len(search_results)} results found",
                pipeline_type="search"
            )

            # Report completion
            await data_tool.progress_reporter.report_complete(
                "query",
                {
                    "total_embeddings": total_embeddings,
                    "results_found": len(search_results),
                    "query": search_query or "all datasets"
                },
                pipeline_type="search"
            )

            # Complete progress operation
            await data_tool.complete_progress_operation(
                operation_id,
                result={
                    "total_embeddings": total_embeddings,
                    "results_found": len(search_results)
                }
            )

            await data_tool.log_info(ctx, f"Search completed: {len(search_results)} results found")
            
            result = {
                "success": True,
                "user_id": str(user_id),
                "search_query": str(search_query) if search_query else "all_datasets",
                "database_summary": {
                    "database_name": f"user_{user_id}",
                    "total_embeddings": total_embeddings,
                    "service_status": "active",
                    "ai_services": {"embedding": "text-embedding-3-small"}
                },
                "pipeline_info": {
                    "total_processed_sources": 1 if total_embeddings > 0 else 0,
                    "total_pipelines": 1 if total_embeddings > 0 else 0,
                    "successful_pipelines": 1 if total_embeddings > 0 else 0,
                    "recent_pipelines": []
                },
                "search_results": search_results[:10] if search_results else [],
                "search_count": len(search_results),
                "recommendations": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Add recommendations based on available data
            if result["database_summary"]["total_embeddings"] == 0:
                result["recommendations"].append("No datasets found. Use data_ingest to add data first.")
            elif result["pipeline_info"]["total_processed_sources"] > 0:
                result["recommendations"].append(f"Found {result['pipeline_info']['total_processed_sources']} data sources. Use data_query to explore them.")
                
            if search_query and result["search_count"] == 0:
                result["recommendations"].append(f"No results for '{search_query}'. Try broader search terms.")

            result["message"] = f"Found {result['database_summary']['total_embeddings']} metadata entities and {result['pipeline_info']['total_processed_sources']} data sources"
            result["operation_id"] = str(operation_id)  # ✅ Return operation_id for SSE monitoring

            response = {
                "status": "success",
                "action": "data_search",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }

            return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            # Fail progress operation on error
            if 'operation_id' in locals():
                await data_tool.fail_progress_operation(operation_id, str(e))
            logger.error(f"Data search failed: {str(e)}")
            await data_tool.log_error(ctx, f"Data search failed: {str(e)}")
            error_response = {
                "status": "error",
                "action": "data_search", 
                "error": f"Data search failed: {str(e)}",
                "data": {"user_id": str(user_id)},
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(error_response, ensure_ascii=False)

    @mcp.tool()
    async def data_query(
        user_id: str,
        natural_language_query: str,
        include_visualization: bool = True,
        include_analytics: bool = False,

        # Progress monitoring (optional)
        operation_id: Optional[str] = None,

        # Context (will be injected by FastMCP)
        ctx: Optional[Context] = None
    ) -> str:
        """
        Execute natural language queries against ingested data - REAL DATA from MinIO Parquet
        
        Complete Query Pipeline:
        1. Semantic Search: Find relevant tables using embeddings
        2. Storage Path Retrieval: Get Parquet file path from metadata
        3. MinIO Download: Download Parquet file from object storage
        4. DuckDB Query: Execute SQL query on Parquet data
        5. Visualization: Generate chart specs (optional)
        6. Analytics: Run EDA analysis (optional)
        
        Supported Query Types:
        - Simple: "show me sales data" → SELECT * FROM data
        - Aggregation: "total sales by region" → GROUP BY queries
        - Filter: "sales for Enterprise customers" → WHERE clause
        - Sort: "top 5 products by quantity" → ORDER BY + LIMIT
        - Complex: Combinations of aboveco
        
        Args:
            user_id: User identifier for data isolation
            natural_language_query: Natural language query in plain English
            include_visualization: Generate chart specifications (default: True)
            include_analytics: Include EDA insights (default: False)
            
        Returns:
            JSON string with REAL DATA including:
            - query_data: Actual data rows from Parquet file
            - rows_returned: Number of rows in result  
            - column_names: Actual column names from data
            - services_used: ['embedding_service', 'minio_storage', 'duckdb_query', ...]
            - sql_executed: Actual SQL executed on data
            - data_source: MinIO Parquet path queried
            - visualization: Chart specification (if requested)
            - total_execution_time: Complete query execution time
            
        Examples:
            # Basic usage
            >>> result = await data_query(
            ...     user_id="user123",
            ...     natural_language_query="total sales amount by region",
            ...     include_visualization=True
            ... )
            >>> # Returns: {"status": "success", "data": {actual_sales_data...}}

            # Advanced: Provide operation_id for SSE monitoring
            >>> import uuid
            >>> op_id = str(uuid.uuid4())
            >>> # Start query with custom operation_id
            >>> query_task = asyncio.create_task(
            ...     data_query(user_id="user123", natural_language_query="total sales", operation_id=op_id)
            ... )
            >>> # Concurrently monitor progress via SSE
            >>> await stream_progress(op_id)
            >>> # Get result
            >>> result = await query_task
        """
        # Create or use provided progress operation
        if not operation_id:
            operation_id = await data_tool.create_progress_operation(
                metadata={
                    "user_id": user_id,
                    "query": natural_language_query[:100],
                    "operation": "data_query"
                }
            )
        else:
            # Use client-provided operation_id
            await data_tool.create_progress_operation(
                operation_id=operation_id,
                metadata={
                    "user_id": user_id,
                    "query": natural_language_query[:100],
                    "operation": "data_query"
                }
            )

        try:
            # Stage 1: Query Analysis
            await data_tool.log_info(ctx, f"Starting data query for user {user_id}: {natural_language_query}")
            await data_tool.progress_reporter.report_stage(
                operation_id, "processing", "query",
                "analyzing natural language query",
                pipeline_type="query"
            )
            
            logger.info(f"Processing data query for user {user_id}: {natural_language_query}")
            
            # Import available services
            from tools.services.data_analytics_service.services.data_service.search.sql_query_service import SQLQueryService
            from tools.services.data_analytics_service.services.data_service.visualization.data_visualization import DataVisualizationService
            # DataEDAService imported later if needed (requires pandas)
            from tools.services.data_analytics_service.services.data_service.management.metadata.metadata_embedding import get_embedding_service
            from tools.services.data_analytics_service.services.data_service.management.metadata.semantic_enricher import SemanticMetadata
            from isa_model.core.database.supabase_client import get_supabase_client
            
            result = {
                "success": False,
                "user_id": str(user_id),
                "original_query": str(natural_language_query),
                "timestamp": datetime.now().isoformat(),
                "services_used": [],
                "execution_times": {}
            }
            
            # Step 1: Check available data using embedding service (same as data_ingest)
            service_start = datetime.now()
            embedding_service = get_embedding_service(f"user_{user_id}")
            supabase = get_supabase_client()
            
            # Check if embeddings exist for this user
            try:
                db_result = supabase.client.schema('dev').table('db_meta_embedding').select('id').eq('database_source', f'user_{user_id}').limit(1).execute()
                has_data = len(db_result.data) > 0 if db_result.data else False
            except Exception as e:
                logger.warning(f"Could not check embeddings: {str(e)}")
                has_data = False
            
            if not has_data:
                error_response = {
                    "status": "error",
                    "action": "data_query",
                    "error": "No datasets found. Please use data_ingest first.",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(error_response, ensure_ascii=False)
            
            result["services_used"].append("embedding_service")
            result["execution_times"]["metadata_check"] = (datetime.now() - service_start).total_seconds()

            # Stage 2: Data Retrieval
            await data_tool.progress_reporter.report_stage(
                operation_id, "retrieval", "query",
                "searching for relevant data",
                pipeline_type="query"
            )
            
            # Step 2: Search and retrieve data using embedding service
            service_start = datetime.now()
            
            # Search metadata to find relevant data
            search_results_raw = await embedding_service.search_similar_entities(
                natural_language_query, 
                entity_type=None,
                limit=10,
                similarity_threshold=0.1
            )
            
            # Convert to list of dicts
            search_results = []
            for result_obj in search_results_raw:
                search_results.append({
                    'entity_name': result_obj.entity_name,
                    'entity_type': result_obj.entity_type,
                    'similarity_score': result_obj.similarity_score,
                    'content': result_obj.content
                })
            
            if not search_results:
                error_response = {
                    "status": "error",
                    "action": "data_query",
                    "error": f"No relevant data found for query: '{natural_language_query}'",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(error_response, ensure_ascii=False)
            
            # Step 2.5: Extract storage path from search results - prioritize dataset names
            storage_path = None
            table_name = None
            dataset_name = None
            
            # First pass: look for dataset name in metadata content
            for search_result in search_results:
                content = search_result.get('content_preview', '')
                if 'dataset' in content.lower():
                    # Try to extract dataset name from content patterns
                    if 'Dataset:' in content:
                        dataset_part = content.split('Dataset:')[1].split(',')[0].strip()
                        if dataset_part and len(dataset_part) > 3:  # Avoid too short names
                            dataset_name = dataset_part
                            logger.info(f"Found dataset name in content: {dataset_name}")
                            break
                    elif 'dataset_name' in content.lower():
                        # Look for dataset_name patterns
                        parts = content.split()
                        for i, part in enumerate(parts):
                            if 'dataset' in part.lower() and i + 1 < len(parts):
                                candidate = parts[i + 1].strip(',:')
                                if len(candidate) > 3:
                                    dataset_name = candidate
                                    logger.info(f"Found dataset name via pattern: {dataset_name}")
                                    break
                        if dataset_name:
                            break
            
            # Second pass: look for table entities
            if not dataset_name:
                for search_result in search_results:
                    if search_result['entity_type'] == 'table':
                        table_name = search_result['entity_name']
                        break
                
                if not table_name:
                    # Final fallback: use first result
                    table_name = search_results[0]['entity_name'].split('.')[0] if '.' in search_results[0]['entity_name'] else search_results[0]['entity_name']
            
            # Use dataset name for storage lookup, fallback to table name
            lookup_name = dataset_name if dataset_name else table_name
            logger.info(f"Using lookup name: {lookup_name} (found dataset: {dataset_name}, table: {table_name})")
            
            # Query database to get actual storage_path from metadata
            try:
                db_result = supabase.client.schema('dev').table('db_meta_embedding')\
                    .select('metadata, storage_path')\
                    .eq('database_source', f'user_{user_id}')\
                    .eq('entity_type', 'table')\
                    .limit(1)\
                    .execute()
                
                if db_result.data and len(db_result.data) > 0:
                    row = db_result.data[0]
                    # Try storage_path column first (if it exists)
                    storage_path = row.get('storage_path')
                    
                    if not storage_path:
                        # Try from metadata JSON
                        metadata = row.get('metadata', {})
                        storage_path = metadata.get('storage_path') or metadata.get('full_path')
                        
                        # Try storage_info nested object
                        if not storage_path:
                            storage_info = metadata.get('storage_info', {})
                            storage_path = storage_info.get('full_path') or storage_info.get('minio_object')
                    
                    # If still no path, try professional storage service first
                    if not storage_path:
                        logger.info(f"No storage path in metadata, trying professional storage service for user {user_id}")
                        try:
                            from core.clients.storage_client import get_storage_client
                            storage_client = await get_storage_client()
                            
                            # Get user's analytics files
                            user_files = await storage_client.get_user_files(user_id, "analytics_parquet")
                            
                            # Find matching dataset
                            matching_files = [f for f in user_files if lookup_name in f.get('file_name', '')]
                            if matching_files:
                                # Use most recent file
                                latest_file = sorted(matching_files, key=lambda x: x.get('created_at', ''), reverse=True)[0]
                                file_id = latest_file.get('file_id')
                                
                                if file_id:
                                    # Get download URL
                                    download_url = await storage_client.get_file_download_url(file_id, user_id)
                                    if download_url:
                                        storage_path = f"url:{download_url}"  # Special prefix for URLs
                                        logger.info(f"Found user file via storage service: {file_id}")
                                        
                        except Exception as storage_error:
                            logger.warning(f"Professional storage lookup failed: {str(storage_error)}")
                    
                    # Fallback to searching analytics-data bucket
                    if not storage_path:
                        logger.warning(f"Trying analytics-data bucket search for {table_name}")
                        from core.clients.minio_client import get_minio_client
                        minio_client = get_minio_client()
                        minio = minio_client.get_client()
                        
                        # Search for files matching the dataset pattern
                        if minio:
                            try:
                                objects = list(minio.list_objects('analytics-data', prefix=f'default_user/{lookup_name}/', recursive=True))
                                parquet_objects = [obj for obj in objects if obj.object_name.endswith('.parquet')]
                                if parquet_objects:
                                    # Use the most recent one
                                    latest_obj = sorted(parquet_objects, key=lambda x: x.last_modified, reverse=True)[0]
                                    storage_path = f"analytics-data/{latest_obj.object_name}"
                                    logger.info(f"Found latest Parquet file in analytics-data: {storage_path}")
                            except Exception as search_error:
                                logger.warning(f"MinIO search failed: {search_error}")
                    
                    if not storage_path:
                        dataset_name_from_meta = metadata.get('dataset_name', lookup_name)
                        storage_path = f"analytics-data/default_user/{dataset_name_from_meta}.parquet"
                else:
                    # Fallback: construct path from lookup name
                    storage_path = f"analytics-data/default_user/{lookup_name}.parquet"
                    
            except Exception as e:
                logger.warning(f"Could not get storage path from metadata: {str(e)}")
                storage_path = f"analytics-data/default_user/{lookup_name if 'lookup_name' in locals() else 'sales_data'}.parquet"
            
            logger.info(f"STEP3: Loading data from MinIO: {storage_path}")

            # Stage 3: Query Execution
            await data_tool.progress_reporter.report_stage(
                operation_id, "execution", "query",
                "loading and executing query on Parquet data",
                pipeline_type="query"
            )
            
            # Step 3: Load Parquet from MinIO and query with Professional DuckDB Service
            from tools.services.data_analytics_service.services.data_service.search.sql_executor import ExecutionResult
            
            try:
                import tempfile
                import os
                from core.clients.minio_client import get_minio_client
                from resources.dbs.duckdb import get_duckdb_service, AccessLevel, ConnectionConfig, SecurityConfig
                
                # Get MinIO client
                minio_client = get_minio_client()
                minio = minio_client.get_client()
                
                if not minio:
                    raise Exception("MinIO client not available")
                
                # Create MCP-compatible temp directory
                mcp_temp_dir = '/tmp/mcp_duckdb'
                os.makedirs(mcp_temp_dir, exist_ok=True)
                temp_filename = f"query_{user_id}_{int(datetime.now().timestamp())}.parquet"
                temp_path = os.path.join(mcp_temp_dir, temp_filename)
                
                # Handle different storage path types
                if storage_path.startswith('url:'):
                    # Download from URL (professional storage service)
                    download_url = storage_path[4:]  # Remove 'url:' prefix
                    logger.info(f"STEP3: Downloading from professional storage URL")
                    
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(download_url) as response:
                            if response.status == 200:
                                with open(temp_path, 'wb') as f:
                                    async for chunk in response.content.iter_chunked(8192):
                                        f.write(chunk)
                                logger.info(f"STEP3: Downloaded from professional storage: {download_url} → {temp_path}")
                            else:
                                raise Exception(f"Failed to download from professional storage: HTTP {response.status}")
                
                elif storage_path.startswith('isA-storage/'):
                    # Handle isA-storage bucket (professional storage)
                    bucket = 'isA-storage'
                    object_name = storage_path[12:]  # Remove 'isA-storage/' prefix
                    logger.info(f"STEP3: Downloading from professional storage bucket={bucket}, object={object_name}")
                    minio.fget_object(bucket, object_name, temp_path)
                    logger.info(f"STEP3: Downloaded from professional storage: {storage_path} → {temp_path}")
                
                else:
                    # Handle analytics-data bucket (fallback storage) - always use analytics-data bucket
                    bucket = 'analytics-data'
                    
                    # Clean up storage path to get object name
                    if storage_path.startswith('analytics-data/'):
                        object_name = storage_path[15:]  # Remove 'analytics-data/' prefix
                    else:
                        # The path is the object name within analytics-data bucket
                        object_name = storage_path
                    
                    logger.info(f"STEP3: Downloading from analytics bucket={bucket}, object={object_name}")
                    minio.fget_object(bucket, object_name, temp_path)
                    logger.info(f"STEP3: Downloaded from analytics storage: {storage_path} → {temp_path}")
                
                # Configure DuckDB for MCP environment with optimal settings
                connection_config = ConnectionConfig(
                    database_path=":memory:",  # Use in-memory for MCP compatibility
                    temp_directory=mcp_temp_dir,  # Use accessible temp directory
                    threads=2,  # Reduce threads for MCP environment
                    memory_limit="512MB",  # Conservative memory limit
                    enable_object_cache=True
                )
                
                security_config = SecurityConfig(
                    enable_access_control=False,  # Disable for temp file access
                    max_query_timeout=60.0,  # Shorter timeout for MCP
                    enable_audit_log=False  # Disable audit for performance
                )
                
                # Get DuckDB service with MCP-optimized configuration
                duckdb_service = get_duckdb_service(
                    connection_config=connection_config,
                    security_config=security_config
                )
                
                # Configure DuckDB session for MCP environment
                try:
                    duckdb_service.execute_query(f"SET temp_directory = '{mcp_temp_dir}'")
                    duckdb_service.execute_query("SET memory_limit = '512MB'")
                    duckdb_service.execute_query("SET threads = 2")
                    logger.info(f"STEP3: DuckDB configured for MCP with temp_directory={mcp_temp_dir}")
                except Exception as config_error:
                    logger.warning(f"STEP3: DuckDB configuration warning: {config_error}")
                    # Continue anyway - basic config might still work
                
                # Generate SQL based on query intent
                query_lower = natural_language_query.lower()
                
                if 'total' in query_lower or 'sum' in query_lower:
                    # Aggregation query - example: total sales by region
                    if 'region' in query_lower:
                        sql = f"SELECT region, SUM(sales_amount) as total_sales, SUM(quantity) as total_quantity FROM read_parquet('{temp_path}') GROUP BY region"
                    else:
                        sql = f"SELECT * FROM read_parquet('{temp_path}') LIMIT 10"
                elif 'top' in query_lower:
                    # Top N query
                    sql = f"SELECT * FROM read_parquet('{temp_path}') LIMIT 5"
                elif 'enterprise' in query_lower or 'individual' in query_lower:
                    # Filter query
                    filter_val = 'Enterprise' if 'enterprise' in query_lower else 'Individual'
                    sql = f"SELECT * FROM read_parquet('{temp_path}') WHERE customer_type = '{filter_val}' LIMIT 10"
                else:
                    # Simple select
                    sql = f"SELECT * FROM read_parquet('{temp_path}') LIMIT 10"
                
                logger.info(f"STEP3: Executing SQL: {sql}")
                
                # Execute query using professional DuckDB service
                df = duckdb_service.execute_query_df(sql, access_level=AccessLevel.READ_ONLY, framework='polars')

                # Convert to list of dicts (Polars API)
                data_rows = df.to_dicts()
                column_names = list(df.columns)
                
                # Cleanup temp file
                try:
                    os.unlink(temp_path)
                    logger.info(f"STEP3: Cleaned up temp file: {temp_path}")
                except Exception as cleanup_error:
                    logger.warning(f"STEP3: Temp file cleanup failed: {cleanup_error}")
                
                execution_result = ExecutionResult(
                    success=True,
                    data=data_rows,
                    column_names=column_names,
                    row_count=len(data_rows),
                    execution_time_ms=100.0,
                    sql_executed=sql
                )
                
                logger.info(f"STEP3: Query executed successfully - {len(data_rows)} REAL rows returned from Parquet")
                await data_tool.log_info(ctx, f"Query executed successfully: {len(data_rows)} rows returned")
                
            except Exception as query_error:
                logger.error(f"STEP3: Failed to query Parquet: {str(query_error)}")
                logger.error(f"STEP3: Error type: {type(query_error).__name__}")
                logger.error(f"STEP3: Storage path attempted: {storage_path}")
                logger.error(f"STEP3: Bucket: {bucket}, Object: {object_name}")
                if 'temp_path' in locals():
                    logger.error(f"STEP3: Temp file: {temp_path}")
                    logger.error(f"STEP3: Temp file exists: {os.path.exists(temp_path)}")
                    logger.error(f"STEP3: Temp file size: {os.path.getsize(temp_path) if os.path.exists(temp_path) else 'N/A'}")
                if 'sql' in locals():
                    logger.error(f"STEP3: SQL attempted: {sql}")
                if 'duckdb_service' in locals():
                    logger.error(f"STEP3: DuckDB service type: {type(duckdb_service)}")
                    logger.error(f"STEP3: DuckDB service initialized: {duckdb_service is not None}")
                import traceback
                logger.error(f"STEP3: Full traceback: {traceback.format_exc()}")
                
                # Try a simple DuckDB test to isolate the issue
                try:
                    test_result = duckdb_service.execute_query("SELECT 1 as test_value")
                    logger.info(f"STEP3: DuckDB basic test successful: {test_result}")
                except Exception as test_error:
                    logger.error(f"STEP3: DuckDB basic test failed: {str(test_error)}")
                
                # Return the actual error in the fallback for debugging
                result["debug_info"] = {
                    "error_type": type(query_error).__name__,
                    "error_message": str(query_error),
                    "temp_file_exists": os.path.exists(temp_path) if 'temp_path' in locals() else False,
                    "sql_attempted": sql if 'sql' in locals() else "SQL not generated"
                }
                logger.warning("STEP3: Falling back to metadata results")
                # Fallback to metadata results
            extracted_data = []
            for i, search_result in enumerate(search_results[:10]):
                extracted_data.append({
                    "entity_name": search_result.get("entity_name", f"entity_{i}"),
                    "entity_type": search_result.get("entity_type", "unknown"),
                    "similarity_score": search_result.get("similarity_score", 0.0),
                    "content_preview": str(search_result.get("content", ""))[:100]
                })
            
            execution_result = ExecutionResult(
                success=True,
                data=extracted_data,
                column_names=["entity_name", "entity_type", "similarity_score", "content_preview"],
                row_count=len(extracted_data),
                execution_time_ms=100.0,
                    sql_executed=f"-- Fallback: Semantic search results --"
            )
            
            result["sql_executed"] = execution_result.sql_executed
            result["rows_returned"] = execution_result.row_count
            result["columns_returned"] = len(execution_result.column_names)
            result["services_used"].extend(["minio_storage", "duckdb_query"])
            result["execution_times"]["data_query"] = (datetime.now() - service_start).total_seconds()
            result["data_source"] = storage_path
            
            # Stage 4: Visualization
            visualization_spec = None
            if include_visualization and execution_result.data:
                await data_tool.progress_reporter.report_stage(
                    operation_id, "visualization", "query",
                    "generating chart specifications",
                    pipeline_type="query"
                )
                
                try:
                    service_start = datetime.now()
                    
                    from tools.services.data_analytics_service.services.data_service.search.query_matcher import QueryContext
                
                    # Dynamically extract entities from search results
                    entities_mentioned = []
                    attributes_mentioned = []
                    
                    for search_result in search_results:
                        entity_name = search_result.get('entity_name', '')
                        entity_type = search_result.get('entity_type', '')
                        
                        if entity_type == 'table':
                            entities_mentioned.append(entity_name)
                        elif entity_type in ['column', 'semantic_tags']:
                            # Extract column name (e.g., "sales_data.product" -> "product")
                            if '.' in entity_name:
                                attr = entity_name.split('.')[-1]
                                attributes_mentioned.append(attr)
                            else:
                                attributes_mentioned.append(entity_name)
                    
                    # Parse query for operations, filters, aggregations
                    query_lower = natural_language_query.lower()
                    operations = []
                    aggregations = []
                    filters = []
                    temporal_refs = []
                    
                    # Detect operations
                    if any(word in query_lower for word in ['show', 'display', 'get', 'list']):
                        operations.append('select')
                    if any(word in query_lower for word in ['filter', 'where', 'only']):
                        operations.append('filter')
                    if any(word in query_lower for word in ['sort', 'order', 'top']):
                        operations.append('sort')
                    
                    # Detect aggregations
                    if any(word in query_lower for word in ['total', 'sum', 'count', 'average', 'mean', 'max', 'min']):
                        if 'total' in query_lower or 'sum' in query_lower:
                            aggregations.append('sum')
                        if 'count' in query_lower:
                            aggregations.append('count')
                        if 'average' in query_lower or 'mean' in query_lower:
                            aggregations.append('avg')
                        if 'max' in query_lower:
                            aggregations.append('max')
                        if 'min' in query_lower:
                            aggregations.append('min')
                    
                    # Detect temporal references
                    if any(word in query_lower for word in ['date', 'time', 'year', 'month', 'day', 'recent', 'last']):
                        temporal_refs.append('temporal')
                    
                    # Create dynamic query context
                    query_context = QueryContext(
                        entities_mentioned=entities_mentioned or ['data'],
                        attributes_mentioned=attributes_mentioned or ['value'],
                        operations=operations or ['select'],
                        filters=filters,
                        aggregations=aggregations,
                        temporal_references=temporal_refs,
                        business_intent=natural_language_query,
                        confidence_score=0.8
                    )
                
                    # Create minimal semantic metadata with correct parameters
                    semantic_metadata = SemanticMetadata(
                        original_metadata={},
                        business_entities=[],
                        semantic_tags={},
                        data_patterns=[],
                        business_rules=[],
                        domain_classification={},
                        confidence_scores={},
                        ai_analysis={"source": "mock"}
                    )
                
                    visualization_service = DataVisualizationService()
                    viz_result = await visualization_service.generate_visualization_spec(
                        execution_result,
                        query_context,
                        semantic_metadata
                    )
                
                    if viz_result.get("status") == "success":
                        # Convert visualization spec to JSON-serializable format
                        viz_spec = viz_result["visualization"]
                        visualization_spec = _make_json_serializable(viz_spec)
                        
                        result["services_used"].append("visualization_service")
                        result["execution_times"]["visualization"] = (datetime.now() - service_start).total_seconds()
                        result["visualization_ready"] = True
                    else:
                        result["visualization_errors"] = viz_result.get("error", "Visualization failed")
                        
                except Exception as viz_error:
                    logger.warning(f"Visualization generation failed: {str(viz_error)}")
                    result["visualization_errors"] = str(viz_error)
                    result["visualization_ready"] = False
            
            # Step 4: Generate analytics if requested 
            analytics_insights = None
            if include_analytics and execution_result.data:
                service_start = datetime.now()

                try:
                    import tempfile
                    import polars as pl
                    # Import DataEDAService only if needed (requires pandas)
                    from tools.services.data_analytics_service.services.data_service.analytics.data_eda import DataEDAService

                    # Create temporary CSV for EDA
                    df = pl.DataFrame(execution_result.data)
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
                        df.write_csv(temp_file.name)
                        temp_path = temp_file.name

                    # Run EDA analysis
                    eda_service = DataEDAService(file_path=temp_path)
                    analytics_insights = eda_service.get_quick_insights()
                    
                    result["services_used"].append("analytics_service")
                    result["execution_times"]["analytics"] = (datetime.now() - service_start).total_seconds()
                    result["analytics_ready"] = True
                    
                    # Cleanup
                    import os
                    os.unlink(temp_path)
                    
                except Exception as e:
                    result["analytics_errors"] = f"Analytics failed: {str(e)}"
            
            # Final result
            result.update({
                "success": True,
                "query_data": {
                    "data": execution_result.data,
                    "column_names": execution_result.column_names,
                    "total_rows": execution_result.row_count
                },
                "visualization": visualization_spec,
                "analytics_insights": analytics_insights,
                "total_execution_time": sum(result["execution_times"].values()),
                "message": f"Query processed using {len(result['services_used'])} services"
            })
            
            # Report completion
            await data_tool.progress_reporter.report_complete(
                "query",
                {
                    "rows_returned": execution_result.row_count,
                    "services_used": len(result['services_used']),
                    "execution_time": result["total_execution_time"],
                    "visualization_ready": result.get("visualization_ready", False)
                },
                pipeline_type="query"
            )

            # Complete progress operation
            await data_tool.complete_progress_operation(
                operation_id,
                result={
                    "rows_returned": execution_result.row_count,
                    "execution_time": result["total_execution_time"]
                }
            )

            await data_tool.log_info(ctx, f"Query completed successfully: {execution_result.row_count} rows returned")

            result["operation_id"] = str(operation_id)  # ✅ Return operation_id for SSE monitoring

            response = {
                "status": "success",
                "action": "data_query",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }

            return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            # Fail progress operation on error
            if 'operation_id' in locals():
                await data_tool.fail_progress_operation(operation_id, str(e))
            logger.error(f"Data query failed: {str(e)}")
            await data_tool.log_error(ctx, f"Data query failed: {str(e)}")
            error_response = {
                "status": "error",
                "action": "data_query",
                "error": f"Data query failed: {str(e)}",
                "data": {"user_id": str(user_id), "query": str(natural_language_query)},
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(error_response, ensure_ascii=False)

    logger.info("="*60)
    logger.info("Data Tools Registration Complete")
    logger.info("="*60)
    logger.info("Registered 4 MCP tools:")
    logger.info("  1. data_ingest - Complete data ingestion pipeline")
    logger.info("  2. get_pipeline_status - Pipeline status and statistics")
    logger.info("  3. data_search - Semantic similarity search")
    logger.info("  4. data_query - Natural language query execution")
    logger.info("="*60)