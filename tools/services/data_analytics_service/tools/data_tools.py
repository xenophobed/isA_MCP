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
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

from core.logging import get_logger
from tools.base_tool import BaseTool
from tools.services.data_analytics_service.tools.context import DataProgressReporter

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
    elif hasattr(obj, "value"):  # Enum with value
        return obj.value
    elif hasattr(obj, "name"):  # Enum with name
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
        ctx: Optional[Context] = None,
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
                    "operation": "data_ingest",
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
                    "operation": "data_ingest",
                },
            )

        try:
            from pathlib import Path

            from tools.services.data_analytics_service.services.data_service.preprocessor.preprocessor_service import (
                get_preprocessor_service,
            )
            from tools.services.data_analytics_service.services.data_service.storage.data_storage_service import (
                DataStorageService,
            )
            from tools.services.data_analytics_service.tools.context import (
                DataSourceDetector,
            )

            # Generate dataset name if not provided
            if not dataset_name:
                dataset_name = Path(source_path).stem

            # Detect data source type
            data_source_type = DataSourceDetector.detect_from_path(source_path)

            # Log start and report Stage 1: Processing
            await data_tool.log_info(
                ctx, f"Starting data ingestion for user {user_id}: {source_path}"
            )
            await data_tool.progress_reporter.report_stage(
                operation_id,
                "processing",
                data_source_type,
                f"loading {dataset_name}",
                pipeline_type="ingestion",
            )

            logger.info(f"Starting data ingestion for user {user_id}: {source_path}")

            # Initialize services
            preprocessor = get_preprocessor_service(user_id)
            storage_service = DataStorageService()

            # Step 1: Preprocess data
            pipeline_result = await preprocessor.process_data_source(source_path)

            if not pipeline_result.success:
                error_msg = (
                    f"Preprocessing failed: {str(pipeline_result.error_message)}"
                )
                await data_tool.log_error(ctx, error_msg)
                await data_tool.fail_progress_operation(operation_id, error_msg)
                error_response = {
                    "status": "error",
                    "action": "data_ingest",
                    "error": error_msg,
                    "data": {"user_id": str(user_id)},
                    "timestamp": datetime.now().isoformat(),
                }
                return json.dumps(error_response, ensure_ascii=False)

            # Report data statistics
            await data_tool.progress_reporter.report_data_stats(
                operation_id,
                "processing",
                data_source_type,
                rows=pipeline_result.rows_detected,
                columns=pipeline_result.columns_detected,
                quality_score=pipeline_result.data_quality_score,
                pipeline_type="ingestion",
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
                    "timestamp": datetime.now().isoformat(),
                }
                return json.dumps(error_response, ensure_ascii=False)

            # Step 3: Store to MinIO Parquet directly (user's bucket)
            await data_tool.log_info(
                ctx, f"Storing data to MinIO Parquet: {dataset_name}"
            )
            await data_tool.progress_reporter.report_storage_progress(
                operation_id, data_source_type, "minio", "uploading"
            )

            storage_success = False
            parquet_path = None
            minio_bucket = (
                "user-data"  # User's data bucket (MinIO will add user prefix)
            )

            try:
                # Store directly to MinIO using isa-common client
                import io

                from isa_common.minio_client import MinIOClient

                # Convert DataFrame to parquet bytes
                parquet_buffer = io.BytesIO()
                cleaned_df.write_parquet(parquet_buffer)
                parquet_buffer.seek(0)  # Reset to beginning
                parquet_data = parquet_buffer.read()  # Read all data

                logger.info(f"Parquet data prepared: {len(parquet_data)} bytes")

                # Create MinIO client with user_id for proper bucket handling
                minio_client = MinIOClient(
                    host="isa-minio-grpc",
                    port=50051,
                    user_id=user_id,  # ✅ CRITICAL: user_id needed for bucket operations
                )
                logger.info(f"MinIO client created for user: {user_id}")

                with minio_client:
                    # Create user bucket if needed
                    if not minio_client.bucket_exists(minio_bucket):
                        minio_client.create_bucket(minio_bucket)
                        logger.info(f"Created MinIO bucket: {minio_bucket}")

                    # Generate object path with date partitioning
                    now = datetime.now()
                    object_path = f"{user_id}/datasets/{dataset_name}/{now.strftime('%Y/%m/%d')}/{dataset_name}_{now.strftime('%H%M%S')}.parquet"

                    # Upload to MinIO (use put_object with size parameter like storage_service)
                    import io

                    success = minio_client.put_object(
                        bucket_name=minio_bucket,
                        object_key=object_path,
                        data=io.BytesIO(parquet_data),
                        size=len(parquet_data),
                    )

                    if not success:
                        raise Exception(f"MinIO put_object returned False")

                    parquet_path = object_path  # Store relative path (bucket will be added separately)
                    storage_success = True

                    logger.info(
                        f"MinIO upload successful: {minio_bucket}/{object_path}"
                    )

            except Exception as storage_error:
                error_msg = f"MinIO storage failed: {str(storage_error)}"
                logger.error(error_msg)
                await data_tool.fail_progress_operation(operation_id, error_msg)
                error_response = {
                    "status": "error",
                    "action": "data_ingest",
                    "error": error_msg,
                    "data": {"user_id": str(user_id)},
                    "timestamp": datetime.now().isoformat(),
                }
                return json.dumps(error_response, ensure_ascii=False)

            logger.info(f"Data stored to MinIO: {minio_bucket}/{parquet_path}")

            # Step 4: Store metadata to metadata store for querying
            # Stage 2: Extraction - Metadata extraction and semantic enrichment
            await data_tool.log_info(
                ctx, "Starting metadata extraction and semantic enrichment"
            )
            await data_tool.progress_reporter.report_stage(
                operation_id,
                "extraction",
                data_source_type,
                "extracting metadata",
                pipeline_type="ingestion",
            )

            logger.info("STEP4: Storing metadata for future querying...")
            metadata_success = False
            metadata_embeddings_count = 0

            try:
                # Simplified: Direct async call in current event loop
                from tools.services.data_analytics_service.processors.data_processors.management.metadata.metadata_extractor import (
                    extract_metadata,
                )
                from tools.services.data_analytics_service.services.data_service.management.metadata.metadata_embedding import (
                    get_embedding_service,
                )
                from tools.services.data_analytics_service.services.data_service.management.metadata.semantic_enricher import (
                    AISemanticEnricher,
                )

                logger.info(f"STEP4: Extracting metadata from {source_path}")
                # Step 1: Extract metadata
                raw_metadata = extract_metadata(source_path, "csv")

                # Add storage path to metadata for query execution
                # parquet_path is the object path: "user_id/datasets/name/YYYY/MM/DD/file.parquet"
                # Actual MinIO bucket includes prefix: user-{user_id}-{bucket_name}
                actual_bucket_name = f"user-{user_id}-user-data"
                raw_metadata["storage_info"] = {
                    "storage_type": "parquet",
                    "minio_bucket": actual_bucket_name,  # Full bucket name with prefix
                    "minio_object": parquet_path,  # Object path within bucket
                    "full_path": f"{actual_bucket_name}/{parquet_path}",
                    "dataset_name": dataset_name,
                }

                logger.info(
                    f"STEP4: Storage info - bucket: user-data, object: {parquet_path}"
                )

                if "error" in raw_metadata:
                    logger.warning(
                        f"STEP4: Metadata extraction failed: {raw_metadata['error']}"
                    )
                else:
                    logger.info(f"STEP4: Metadata extracted successfully")

                    # Step 2: Semantic enrichment
                    logger.info("STEP4: Performing semantic enrichment...")
                    await data_tool.progress_reporter.report_stage(
                        operation_id,
                        "extraction",
                        data_source_type,
                        "AI semantic enrichment",
                        pipeline_type="ingestion",
                    )

                    enricher = AISemanticEnricher()
                    semantic_metadata = await enricher.enrich_metadata(raw_metadata)
                    logger.info(
                        f"STEP4: Semantic enrichment completed - {len(semantic_metadata.business_entities)} entities, {len(semantic_metadata.semantic_tags)} tags"
                    )

                    # Preserve storage_info in semantic metadata for embeddings
                    if not hasattr(semantic_metadata, "storage_info"):
                        semantic_metadata.storage_info = raw_metadata.get(
                            "storage_info", {}
                        )

                    # Stage 3: Embedding - Generate vector embeddings
                    await data_tool.log_info(ctx, "Generating vector embeddings")
                    await data_tool.progress_reporter.report_stage(
                        operation_id,
                        "embedding",
                        data_source_type,
                        "generating embeddings",
                        pipeline_type="ingestion",
                    )

                    # Step 3: Store embeddings with storage path information
                    logger.info("STEP4: Storing embeddings to database...")
                    embedding_service = await get_embedding_service(f"user_{user_id}")

                    # Pass storage info to embedding service
                    storage_results = await embedding_service.store_semantic_metadata(
                        semantic_metadata,
                        storage_path=parquet_path,
                        dataset_name=dataset_name,
                    )

                    metadata_embeddings_count = storage_results.get(
                        "stored_embeddings", 0
                    )
                    failed_count = storage_results.get("failed_embeddings", 0)

                    if metadata_embeddings_count > 0:
                        metadata_success = True
                        logger.info(
                            f"STEP4: Metadata stored successfully: {metadata_embeddings_count} embeddings (failed: {failed_count})"
                        )

                        # Report embedding progress with granular details
                        await data_tool.progress_reporter.report_stage(
                            operation_id,
                            "embedding",
                            data_source_type,
                            f"{metadata_embeddings_count} embeddings created",
                            pipeline_type="ingestion",
                        )
                    else:
                        logger.warning(
                            f"STEP4: No embeddings were stored (failed: {failed_count})"
                        )

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
                    "quality_score": pipeline_result.data_quality_score,
                },
                pipeline_type="ingestion",
            )

            # Complete progress operation
            await data_tool.complete_progress_operation(
                operation_id,
                result={
                    "rows": pipeline_result.rows_detected,
                    "columns": pipeline_result.columns_detected,
                    "embeddings": metadata_embeddings_count,
                },
            )

            await data_tool.log_info(
                ctx, f"Data ingestion completed successfully: {dataset_name}"
            )

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
                "operation_id": str(
                    operation_id
                ),  # ✅ Return operation_id for SSE monitoring
                "message": "Data ingestion and metadata storage completed successfully",
            }

            # Use weather_tools pattern - direct json.dumps (bypass BaseTool)
            response = {
                "status": "success",
                "action": "data_ingest",
                "data": success_result,
                "timestamp": datetime.now().isoformat(),
            }

            return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            # Fail progress operation on error
            if "operation_id" in locals():
                await data_tool.fail_progress_operation(operation_id, str(e))
            logger.error(f"Data ingestion failed: {str(e)}")
            await data_tool.log_error(ctx, f"Data ingestion failed: {str(e)}")
            # Use weather_tools pattern for error too
            error_response = {
                "status": "error",
                "action": "data_ingest",
                "error": f"Data ingestion failed: {str(e)}",
                "data": {"user_id": str(user_id)},
                "timestamp": datetime.now().isoformat(),
            }
            return json.dumps(error_response, ensure_ascii=False)

    @mcp.tool()
    async def get_pipeline_status(
        user_id: str, pipeline_id: str = None, ctx: Optional[Context] = None
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
            from tools.services.data_analytics_service.services.data_service.preprocessor.preprocessor_service import (
                get_preprocessor_service,
            )

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
                        "message": f"Pipeline {pipeline_id} status retrieved",
                    }

                    response = {
                        "status": "success",
                        "action": "get_pipeline_status",
                        "data": status_data,
                        "timestamp": datetime.now().isoformat(),
                    }
                    return json.dumps(response, ensure_ascii=False)
                else:
                    error_response = {
                        "status": "error",
                        "action": "get_pipeline_status",
                        "error": f"Pipeline {pipeline_id} not found",
                        "data": {"user_id": str(user_id)},
                        "timestamp": datetime.now().isoformat(),
                    }
                    return json.dumps(error_response, ensure_ascii=False)
            else:
                stats = preprocessor_service.get_pipeline_statistics()

                # Convert stats to clean format
                stats_data = {
                    "success": True,
                    "user_id": str(user_id),
                    "total_pipelines": int(stats.get("total_pipelines", 0)),
                    "successful_pipelines": int(stats.get("successful_pipelines", 0)),
                    "failed_pipelines": int(stats.get("failed_pipelines", 0)),
                    "average_quality_score": float(
                        stats.get("average_quality_score", 0.0)
                    ),
                    "message": f"Pipeline statistics for user {user_id}",
                }

                response = {
                    "status": "success",
                    "action": "get_pipeline_status",
                    "data": stats_data,
                    "timestamp": datetime.now().isoformat(),
                }
                return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            error_response = {
                "status": "error",
                "action": "get_pipeline_status",
                "error": f"Failed to get pipeline status: {str(e)}",
                "data": {"user_id": str(user_id)},
                "timestamp": datetime.now().isoformat(),
            }
            return json.dumps(error_response, ensure_ascii=False)

    @mcp.tool()
    async def data_search(
        user_id: str,
        search_query: str = None,
        # Progress monitoring (optional)
        operation_id: Optional[str] = None,
        # Context (will be injected by FastMCP)
        ctx: Optional[Context] = None,
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
                    "operation": "data_search",
                }
            )
        else:
            # Use client-provided operation_id
            await data_tool.create_progress_operation(
                operation_id=operation_id,
                metadata={
                    "user_id": user_id,
                    "search_query": search_query or "all_datasets",
                    "operation": "data_search",
                },
            )

        try:
            from tools.services.data_analytics_service.services.data_service.management.metadata.metadata_embedding import (
                get_embedding_service,
            )

            # Stage 1: Query Processing
            await data_tool.log_info(ctx, f"Starting dataset search for user {user_id}")
            await data_tool.progress_reporter.report_stage(
                operation_id,
                "processing",
                "query",
                "analyzing search query" if search_query else "listing all datasets",
                pipeline_type="search",
            )

            logger.info(f"Searching datasets for user {user_id}")

            # Get embedding service for user (same as used in data_ingest)
            embedding_service = await get_embedding_service(f"user_{user_id}")

            # Get database summary by checking embeddings in Qdrant
            try:
                # Use Qdrant to count embeddings
                from isa_common.qdrant_client import QdrantClient

                qdrant = QdrantClient(
                    host="isa-qdrant-grpc",
                    port=50062,
                    user_id=f"metadata-user_{user_id}",
                )

                # Search for all points matching this database_source
                with qdrant:
                    search_result = qdrant.search_with_filter(
                        embedding_service.collection_name,
                        [0.0] * embedding_service.vector_dimension,  # Dummy vector
                        filter_conditions={
                            "must": [
                                {
                                    "field": "database_source",
                                    "match": {"keyword": f"user_{user_id}"},
                                }
                            ]
                        },
                        limit=100,  # Get up to 100 to count
                        with_payload=False,
                    )
                total_embeddings = len(search_result) if search_result else 0
                logger.info(
                    f"Qdrant check: found {total_embeddings} embeddings for user_{user_id}"
                )
            except Exception as e:
                logger.warning(f"Could not query Qdrant embeddings: {str(e)}")
                total_embeddings = 0

            # Search for specific metadata if query provided
            search_results = []
            if search_query:
                # Stage 2: Query Embedding
                await data_tool.progress_reporter.report_stage(
                    operation_id,
                    "embedding",
                    "query",
                    "generating query embedding",
                    pipeline_type="search",
                )

                try:
                    # Stage 3: Similarity Matching
                    await data_tool.progress_reporter.report_stage(
                        operation_id,
                        "matching",
                        "query",
                        "searching vector database",
                        pipeline_type="search",
                    )

                    # Use embedding service to search - correct method and parameters
                    search_results_raw = (
                        await embedding_service.search_similar_entities(
                            query=search_query,
                            entity_type=None,
                            limit=20,
                            similarity_threshold=0.1,
                        )
                    )
                    # Convert SearchResult objects to dicts
                    search_results = []
                    for result in search_results_raw:
                        search_results.append(
                            {
                                "entity_name": result.entity_name,
                                "entity_type": result.entity_type,
                                "similarity_score": result.similarity_score,
                                "content": result.content,
                            }
                        )
                except Exception as e:
                    logger.warning(f"Search failed: {str(e)}")
                    await data_tool.log_error(ctx, f"Search failed: {str(e)}")
                    search_results = []

            # Stage 4: Result Ranking
            await data_tool.progress_reporter.report_stage(
                operation_id,
                "ranking",
                "query",
                f"{len(search_results)} results found",
                pipeline_type="search",
            )

            # Report completion
            await data_tool.progress_reporter.report_complete(
                "query",
                {
                    "total_embeddings": total_embeddings,
                    "results_found": len(search_results),
                    "query": search_query or "all datasets",
                },
                pipeline_type="search",
            )

            # Complete progress operation
            await data_tool.complete_progress_operation(
                operation_id,
                result={
                    "total_embeddings": total_embeddings,
                    "results_found": len(search_results),
                },
            )

            await data_tool.log_info(
                ctx, f"Search completed: {len(search_results)} results found"
            )

            result = {
                "success": True,
                "user_id": str(user_id),
                "search_query": str(search_query) if search_query else "all_datasets",
                "database_summary": {
                    "database_name": f"user_{user_id}",
                    "total_embeddings": total_embeddings,
                    "service_status": "active",
                    "ai_services": {"embedding": "text-embedding-3-small"},
                },
                "pipeline_info": {
                    "total_processed_sources": 1 if total_embeddings > 0 else 0,
                    "total_pipelines": 1 if total_embeddings > 0 else 0,
                    "successful_pipelines": 1 if total_embeddings > 0 else 0,
                    "recent_pipelines": [],
                },
                "search_results": search_results[:10] if search_results else [],
                "search_count": len(search_results),
                "recommendations": [],
                "timestamp": datetime.now().isoformat(),
            }

            # Add recommendations based on available data
            if result["database_summary"]["total_embeddings"] == 0:
                result["recommendations"].append(
                    "No datasets found. Use data_ingest to add data first."
                )
            elif result["pipeline_info"]["total_processed_sources"] > 0:
                result["recommendations"].append(
                    f"Found {result['pipeline_info']['total_processed_sources']} data sources. Use data_query to explore them."
                )

            if search_query and result["search_count"] == 0:
                result["recommendations"].append(
                    f"No results for '{search_query}'. Try broader search terms."
                )

            result["message"] = (
                f"Found {result['database_summary']['total_embeddings']} metadata entities and {result['pipeline_info']['total_processed_sources']} data sources"
            )
            result["operation_id"] = str(
                operation_id
            )  # ✅ Return operation_id for SSE monitoring

            response = {
                "status": "success",
                "action": "data_search",
                "data": result,
                "timestamp": datetime.now().isoformat(),
            }

            return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            # Fail progress operation on error
            if "operation_id" in locals():
                await data_tool.fail_progress_operation(operation_id, str(e))
            logger.error(f"Data search failed: {str(e)}")
            await data_tool.log_error(ctx, f"Data search failed: {str(e)}")
            error_response = {
                "status": "error",
                "action": "data_search",
                "error": f"Data search failed: {str(e)}",
                "data": {"user_id": str(user_id)},
                "timestamp": datetime.now().isoformat(),
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
        ctx: Optional[Context] = None,
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
                    "operation": "data_query",
                }
            )
        else:
            # Use client-provided operation_id
            await data_tool.create_progress_operation(
                operation_id=operation_id,
                metadata={
                    "user_id": user_id,
                    "query": natural_language_query[:100],
                    "operation": "data_query",
                },
            )

        try:
            # Stage 1: Query Analysis
            await data_tool.log_info(
                ctx, f"Starting data query for user {user_id}: {natural_language_query}"
            )
            await data_tool.progress_reporter.report_stage(
                operation_id,
                "processing",
                "query",
                "analyzing natural language query",
                pipeline_type="query",
            )

            logger.info(
                f"Processing data query for user {user_id}: {natural_language_query}"
            )

            # Import available services
            # DataEDAService imported later if needed (requires pandas)
            from tools.services.data_analytics_service.services.data_service.management.metadata.metadata_embedding import (
                get_embedding_service,
            )
            from tools.services.data_analytics_service.services.data_service.management.metadata.semantic_enricher import (
                SemanticMetadata,
            )
            from tools.services.data_analytics_service.services.data_service.visualization.data_visualization import (
                DataVisualizationService,
            )

            result = {
                "success": False,
                "user_id": str(user_id),
                "original_query": str(natural_language_query),
                "timestamp": datetime.now().isoformat(),
                "services_used": [],
                "execution_times": {},
            }

            # Step 1: Check available data using embedding service (same as data_ingest)
            service_start = datetime.now()
            embedding_service = await get_embedding_service(f"user_{user_id}")

            # Check if embeddings exist for this user in Qdrant
            try:
                # Use Qdrant to check for embeddings
                from isa_common.qdrant_client import QdrantClient

                qdrant = QdrantClient(
                    host="isa-qdrant-grpc",
                    port=50062,
                    user_id=f"metadata-user_{user_id}",
                )

                # Search for any points matching this database_source
                with qdrant:
                    search_result = qdrant.search_with_filter(
                        embedding_service.collection_name,
                        [0.0] * embedding_service.vector_dimension,  # Dummy vector
                        filter_conditions={
                            "must": [
                                {
                                    "field": "database_source",
                                    "match": {"keyword": f"user_{user_id}"},
                                }
                            ]
                        },
                        limit=1,
                        with_payload=False,
                    )
                has_data = len(search_result) > 0 if search_result else False
                logger.info(
                    f"Qdrant check: found {len(search_result) if search_result else 0} embeddings for user_{user_id}"
                )
            except Exception as e:
                logger.warning(f"Could not check embeddings in Qdrant: {str(e)}")
                has_data = False

            if not has_data:
                error_response = {
                    "status": "error",
                    "action": "data_query",
                    "error": "No datasets found. Please use data_ingest first.",
                    "data": result,
                    "timestamp": datetime.now().isoformat(),
                }
                return json.dumps(error_response, ensure_ascii=False)

            result["services_used"].append("embedding_service")
            result["execution_times"]["metadata_check"] = (
                datetime.now() - service_start
            ).total_seconds()

            # Stage 2: Data Retrieval
            await data_tool.progress_reporter.report_stage(
                operation_id,
                "retrieval",
                "query",
                "searching for relevant data",
                pipeline_type="query",
            )

            # Step 2: Search and retrieve data using embedding service
            service_start = datetime.now()

            # Search metadata to find relevant data
            search_results_raw = await embedding_service.search_similar_entities(
                natural_language_query,
                entity_type=None,
                limit=10,
                similarity_threshold=0.1,
            )

            # Convert to list of dicts
            search_results = []
            for result_obj in search_results_raw:
                search_results.append(
                    {
                        "entity_name": result_obj.entity_name,
                        "entity_type": result_obj.entity_type,
                        "similarity_score": result_obj.similarity_score,
                        "content": result_obj.content,
                    }
                )

            if not search_results:
                error_response = {
                    "status": "error",
                    "action": "data_query",
                    "error": f"No relevant data found for query: '{natural_language_query}'",
                    "data": result,
                    "timestamp": datetime.now().isoformat(),
                }
                return json.dumps(error_response, ensure_ascii=False)

            # Step 2.5: Extract storage path from search results - prioritize dataset names
            storage_path = None
            table_name = None
            dataset_name = None

            # First pass: look for dataset name in metadata content
            for search_result in search_results:
                content = search_result.get("content_preview", "")
                if "dataset" in content.lower():
                    # Try to extract dataset name from content patterns
                    if "Dataset:" in content:
                        dataset_part = (
                            content.split("Dataset:")[1].split(",")[0].strip()
                        )
                        if (
                            dataset_part and len(dataset_part) > 3
                        ):  # Avoid too short names
                            dataset_name = dataset_part
                            logger.info(
                                f"Found dataset name in content: {dataset_name}"
                            )
                            break
                    elif "dataset_name" in content.lower():
                        # Look for dataset_name patterns
                        parts = content.split()
                        for i, part in enumerate(parts):
                            if "dataset" in part.lower() and i + 1 < len(parts):
                                candidate = parts[i + 1].strip(",:")
                                if len(candidate) > 3:
                                    dataset_name = candidate
                                    logger.info(
                                        f"Found dataset name via pattern: {dataset_name}"
                                    )
                                    break
                        if dataset_name:
                            break

            # Second pass: look for table entities
            if not dataset_name:
                for search_result in search_results:
                    if search_result["entity_type"] == "table":
                        table_name = search_result["entity_name"]
                        break

                if not table_name:
                    # Final fallback: use first result
                    table_name = (
                        search_results[0]["entity_name"].split(".")[0]
                        if "." in search_results[0]["entity_name"]
                        else search_results[0]["entity_name"]
                    )

            # Use dataset name for storage lookup, fallback to table name
            lookup_name = dataset_name if dataset_name else table_name
            logger.info(
                f"Using lookup name: {lookup_name} (found dataset: {dataset_name}, table: {table_name})"
            )

            # Query Qdrant to get actual storage_path from metadata
            try:
                logger.info(
                    f"Querying Qdrant for storage_path metadata for user_{user_id}..."
                )

                # Search for table entity to get storage path from metadata
                from isa_common.qdrant_client import QdrantClient

                qdrant_client = QdrantClient(
                    host="isa-qdrant-grpc",
                    port=50062,
                    user_id=f"metadata-user_{user_id}",
                )

                with qdrant_client:
                    # Search for table entities - get multiple results and sort by newest
                    logger.info(
                        f"Searching for table entities in collection: {embedding_service.collection_name}"
                    )
                    table_results = qdrant_client.search_with_filter(
                        embedding_service.collection_name,
                        [0.0] * embedding_service.vector_dimension,
                        filter_conditions={
                            "must": [
                                {
                                    "field": "database_source",
                                    "match": {"keyword": f"user_{user_id}"},
                                },
                                {"field": "entity_type", "match": {"keyword": "table"}},
                            ]
                        },
                        limit=10,  # Get multiple to find the newest
                        with_payload=True,
                    )

                    # Sort by updated_at or created_at to get the newest entry
                    if table_results and len(table_results) > 1:
                        logger.info(
                            f"Found {len(table_results)} table entities, sorting by timestamp"
                        )
                        table_results = sorted(
                            table_results,
                            key=lambda x: x.get("payload", {}).get("updated_at")
                            or x.get("payload", {}).get("created_at")
                            or "",
                            reverse=True,  # Newest first
                        )
                        logger.info(
                            f"Using newest table entity: {table_results[0].get('payload', {}).get('entity_name')}"
                        )

                logger.info(
                    f"Qdrant search returned {len(table_results) if table_results else 0} results"
                )

                if table_results and len(table_results) > 0:
                    row = table_results[0].get("payload", {})
                    logger.info(f"Payload keys: {list(row.keys())}")

                    # Try to get storage_path from metadata
                    metadata = row.get("metadata", {})
                    logger.info(
                        f"Metadata type: {type(metadata)}, value preview: {str(metadata)[:200]}"
                    )

                    # Parse metadata if it's a string (could be JSON or Go map format)
                    if isinstance(metadata, str):
                        try:
                            import json

                            metadata = json.loads(metadata)
                            logger.info("Parsed metadata from JSON string")
                        except:
                            # Try parsing Go map format: "map[key1:value1 key2:value2]"
                            try:
                                if metadata.startswith("map[") and metadata.endswith(
                                    "]"
                                ):
                                    map_content = metadata[
                                        4:-1
                                    ]  # Remove "map[" and "]"
                                    metadata = {}

                                    # Simple parser for Go map format
                                    import re

                                    # Match key:value pairs, handling nested structures
                                    pairs = re.findall(
                                        r"(\w+):([^\s\[]+(?:\[[^\]]*\])?)", map_content
                                    )
                                    for key, value in pairs:
                                        # Remove brackets from list values
                                        if value.startswith("[") and value.endswith(
                                            "]"
                                        ):
                                            value = (
                                                value[1:-1].split()
                                                if value != "[]"
                                                else []
                                            )
                                        metadata[key] = value

                                    logger.info(
                                        f"Parsed metadata from Go map format, keys: {list(metadata.keys())}"
                                    )
                                else:
                                    logger.warning(
                                        f"Unknown metadata format: {metadata[:100]}"
                                    )
                                    metadata = {}
                            except Exception as parse_error:
                                logger.warning(
                                    f"Failed to parse metadata: {parse_error}"
                                )
                                metadata = {}

                    # Debug: log what we found
                    logger.info(
                        f"Found table metadata keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'not a dict'}"
                    )

                    # First try storage_info (most reliable)
                    storage_info = metadata.get("storage_info", {})
                    logger.info(
                        f"Storage info found: {bool(storage_info)}, keys: {list(storage_info.keys()) if storage_info else 'None'}"
                    )
                    if storage_info:
                        # Get bucket and object (may be bare bucket name or already prefixed)
                        bucket = storage_info.get("minio_bucket", "analytics-data")
                        object_name = storage_info.get("minio_object")

                        # Normalize bucket for MinIO prefixing:
                        # MinIO may create buckets with a user prefix "user-{user_id}-{bucket}".
                        # If metadata contains a bare bucket name (e.g., "user-data"), add the user prefix.
                        try:
                            if bucket and not bucket.startswith("user-") and user_id:
                                normalized_bucket = f"user-{user_id}-{bucket}"
                                logger.info(
                                    f"Normalized MinIO bucket from metadata: '{bucket}' → '{normalized_bucket}'"
                                )
                                bucket = normalized_bucket
                            else:
                                logger.info(
                                    f"Using MinIO bucket from metadata: '{bucket}'"
                                )
                        except Exception:
                            # If anything goes wrong during normalization, fall back to original bucket value
                            logger.warning(
                                "Failed to normalize MinIO bucket; using raw metadata value"
                            )

                        # IMPORTANT: Also update lookup_name with actual dataset_name from storage_info
                        stored_dataset_name = storage_info.get("dataset_name")
                        if stored_dataset_name:
                            lookup_name = stored_dataset_name
                            logger.info(
                                f"Updated lookup_name from storage_info: {lookup_name}"
                            )

                        if object_name:
                            # Construct full path (object_name already contains the full path within the bucket)
                            storage_path = object_name
                            logger.info(
                                f"Found storage path from storage_info: bucket={bucket}, object={object_name}"
                            )
                        else:
                            # Try full_path as fallback
                            storage_path = storage_info.get("full_path")
                            logger.info(
                                f"Found storage path from full_path: {storage_path}"
                            )

                    # Fallback to old metadata format (direct fields in Go map)
                    if not storage_path:
                        storage_path = metadata.get("storage_path") or metadata.get(
                            "full_path"
                        )
                        if storage_path:
                            logger.info(
                                f"Found storage path from metadata.storage_path: {storage_path}"
                            )

                            # Also try to get dataset_name to update lookup_name
                            stored_dataset_name = metadata.get("dataset_name")
                            if stored_dataset_name:
                                lookup_name = stored_dataset_name
                                logger.info(
                                    f"Updated lookup_name from metadata.dataset_name: {lookup_name}"
                                )

                    # No storage path found in metadata - this shouldn't happen with new ingestion
                    if not storage_path:
                        logger.error(
                            f"No storage_path in metadata for {lookup_name}. Data might be from old ingestion."
                        )
                        error_response = {
                            "status": "error",
                            "action": "data_query",
                            "error": f"Storage path not found in metadata. Please re-ingest the dataset '{lookup_name}'.",
                            "data": result,
                            "timestamp": datetime.now().isoformat(),
                        }
                        return json.dumps(error_response, ensure_ascii=False)
                else:
                    # Fallback: construct path from lookup name
                    storage_path = f"analytics-data/default_user/{lookup_name}.parquet"

            except Exception as e:
                logger.warning(f"Could not get storage path from metadata: {str(e)}")
                storage_path = f"analytics-data/default_user/{lookup_name if 'lookup_name' in locals() else 'sales_data'}.parquet"

            logger.info(f"STEP3: Loading data from MinIO: {storage_path}")

            # Stage 3: Query Execution
            await data_tool.progress_reporter.report_stage(
                operation_id,
                "execution",
                "query",
                "loading and executing query on Parquet data",
                pipeline_type="query",
            )

            # Step 3: Query Parquet directly from MinIO using DuckDB
            from tools.services.data_analytics_service.services.data_service.search.sql_executor import (
                ExecutionResult,
            )

            try:
                from isa_common.duckdb_client import DuckDBClient

                # bucket and object_name were already extracted from metadata earlier
                # object_name is stored in storage_path variable
                object_name = storage_path

                logger.info(
                    f"STEP3: Querying Parquet from MinIO: bucket={bucket}, object={object_name}"
                )

                # Create DuckDB gRPC client (with user_id for bucket prefixing)
                duckdb_client = DuckDBClient(
                    host="isa-duckdb-grpc", port=50052, user_id=user_id
                )
                logger.info(f"STEP3: DuckDB gRPC client initialized for user {user_id}")

                # Create or get a temporary database for querying
                # Database name: query_db_{user_id}
                database_id = None
                with duckdb_client:
                    # Try to create a database (or reuse existing)
                    try:
                        db_info = duckdb_client.create_database(
                            f"query_db_{user_id}",
                            minio_bucket=bucket,
                            metadata={"purpose": "data_query", "user_id": user_id},
                        )
                        database_id = db_info.get("database_id")
                        logger.info(f"STEP3: Created query database: {database_id}")
                    except Exception as db_create_error:
                        # Database might already exist, list and find it
                        logger.warning(
                            f"STEP3: Database creation failed (might exist): {db_create_error}"
                        )
                        dbs = duckdb_client.list_databases()
                        query_db = next(
                            (
                                db
                                for db in dbs
                                if db.get("name") == f"query_db_{user_id}"
                            ),
                            None,
                        )
                        if query_db:
                            database_id = query_db.get("database_id")
                            logger.info(
                                f"STEP3: Reusing existing query database: {database_id}"
                            )
                        else:
                            raise Exception("Could not create or find query database")

                # Query MinIO file directly using DuckDB
                logger.info(
                    f"STEP3: Executing DuckDB query_minio_file: database_id={database_id}, bucket={bucket}, object={object_name}"
                )

                # Execute query using DuckDB gRPC client - query MinIO directly
                with duckdb_client:
                    # Query the Parquet file from MinIO (zero-copy)
                    query_result = duckdb_client.query_minio_file(
                        database_id,
                        bucket,
                        object_name,
                        file_format="parquet",
                        limit=100,
                    )

                # Convert result
                logger.info(
                    f"STEP3: Query result type: {type(query_result)}, length: {len(query_result) if isinstance(query_result, list) else 'N/A'}"
                )

                if isinstance(query_result, list):
                    # Result is already a list of dicts
                    data_rows = query_result
                    column_names = list(data_rows[0].keys()) if data_rows else []
                else:
                    # Fallback to old format
                    data_rows = query_result.get("rows", [])
                    column_names = query_result.get("columns", [])

                # Generate SQL description for display
                sql_description = f"SELECT * FROM '{bucket}/{object_name}' LIMIT 100"

                execution_result = ExecutionResult(
                    success=True,
                    data=data_rows,
                    column_names=column_names,
                    row_count=len(data_rows),
                    execution_time_ms=100.0,
                    sql_executed=sql_description,
                )

                logger.info(
                    f"STEP3: Query executed successfully - {len(data_rows)} REAL rows returned from Parquet"
                )
                await data_tool.log_info(
                    ctx, f"Query executed successfully: {len(data_rows)} rows returned"
                )

            except Exception as query_error:
                logger.error(f"STEP3: Failed to query Parquet: {str(query_error)}")
                logger.error(f"STEP3: Error type: {type(query_error).__name__}")
                if "storage_path" in locals():
                    logger.error(f"STEP3: Storage path attempted: {storage_path}")
                if "bucket" in locals() and "object_name" in locals():
                    logger.error(f"STEP3: Bucket: {bucket}, Object: {object_name}")
                if "temp_path" in locals():
                    logger.error(f"STEP3: Temp file: {temp_path}")
                    logger.error(
                        f"STEP3: Temp file exists: {os.path.exists(temp_path)}"
                    )
                    logger.error(
                        f"STEP3: Temp file size: {os.path.getsize(temp_path) if os.path.exists(temp_path) else 'N/A'}"
                    )
                if "sql" in locals():
                    logger.error(f"STEP3: SQL attempted: {sql}")
                if "duckdb_client" in locals():
                    logger.error(f"STEP3: DuckDB client type: {type(duckdb_client)}")
                    logger.error(
                        f"STEP3: DuckDB client initialized: {duckdb_client is not None}"
                    )
                import traceback

                logger.error(f"STEP3: Full traceback: {traceback.format_exc()}")

                # Try a simple DuckDB test to isolate the issue
                if "duckdb_client" in locals():
                    try:
                        with duckdb_client:
                            test_result = duckdb_client.execute_query(
                                "memory", "SELECT 1 as test_value"
                            )
                        logger.info(
                            f"STEP3: DuckDB basic test successful: {test_result}"
                        )
                    except Exception as test_error:
                        logger.error(
                            f"STEP3: DuckDB basic test failed: {str(test_error)}"
                        )

                # Return the actual error in the fallback for debugging
                result["debug_info"] = {
                    "error_type": type(query_error).__name__,
                    "error_message": str(query_error),
                    "temp_file_exists": os.path.exists(temp_path)
                    if "temp_path" in locals()
                    else False,
                    "sql_attempted": sql if "sql" in locals() else "SQL not generated",
                }
                logger.warning("STEP3: Falling back to metadata results")

                # Fallback to metadata results (ONLY on exception)
                extracted_data = []
                for i, search_result in enumerate(search_results[:10]):
                    extracted_data.append(
                        {
                            "entity_name": search_result.get(
                                "entity_name", f"entity_{i}"
                            ),
                            "entity_type": search_result.get("entity_type", "unknown"),
                            "similarity_score": search_result.get(
                                "similarity_score", 0.0
                            ),
                            "content_preview": str(search_result.get("content", ""))[
                                :100
                            ],
                        }
                    )

                execution_result = ExecutionResult(
                    success=True,
                    data=extracted_data,
                    column_names=[
                        "entity_name",
                        "entity_type",
                        "similarity_score",
                        "content_preview",
                    ],
                    row_count=len(extracted_data),
                    execution_time_ms=100.0,
                    sql_executed=f"-- Fallback: Semantic search results --",
                )

            result["sql_executed"] = execution_result.sql_executed
            result["rows_returned"] = execution_result.row_count
            result["columns_returned"] = len(execution_result.column_names)
            result["services_used"].extend(["minio_storage", "duckdb_query"])
            result["execution_times"]["data_query"] = (
                datetime.now() - service_start
            ).total_seconds()
            result["data_source"] = storage_path

            # Stage 4: Visualization
            visualization_spec = None
            if include_visualization and execution_result.data:
                await data_tool.progress_reporter.report_stage(
                    operation_id,
                    "visualization",
                    "query",
                    "generating chart specifications",
                    pipeline_type="query",
                )

                try:
                    service_start = datetime.now()

                    from tools.services.data_analytics_service.services.data_service.search.query_matcher import (
                        QueryContext,
                    )

                    # Dynamically extract entities from search results
                    entities_mentioned = []
                    attributes_mentioned = []

                    for search_result in search_results:
                        entity_name = search_result.get("entity_name", "")
                        entity_type = search_result.get("entity_type", "")

                        if entity_type == "table":
                            entities_mentioned.append(entity_name)
                        elif entity_type in ["column", "semantic_tags"]:
                            # Extract column name (e.g., "sales_data.product" -> "product")
                            if "." in entity_name:
                                attr = entity_name.split(".")[-1]
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
                    if any(
                        word in query_lower
                        for word in ["show", "display", "get", "list"]
                    ):
                        operations.append("select")
                    if any(word in query_lower for word in ["filter", "where", "only"]):
                        operations.append("filter")
                    if any(word in query_lower for word in ["sort", "order", "top"]):
                        operations.append("sort")

                    # Detect aggregations
                    if any(
                        word in query_lower
                        for word in [
                            "total",
                            "sum",
                            "count",
                            "average",
                            "mean",
                            "max",
                            "min",
                        ]
                    ):
                        if "total" in query_lower or "sum" in query_lower:
                            aggregations.append("sum")
                        if "count" in query_lower:
                            aggregations.append("count")
                        if "average" in query_lower or "mean" in query_lower:
                            aggregations.append("avg")
                        if "max" in query_lower:
                            aggregations.append("max")
                        if "min" in query_lower:
                            aggregations.append("min")

                    # Detect temporal references
                    if any(
                        word in query_lower
                        for word in [
                            "date",
                            "time",
                            "year",
                            "month",
                            "day",
                            "recent",
                            "last",
                        ]
                    ):
                        temporal_refs.append("temporal")

                    # Create dynamic query context
                    query_context = QueryContext(
                        entities_mentioned=entities_mentioned or ["data"],
                        attributes_mentioned=attributes_mentioned or ["value"],
                        operations=operations or ["select"],
                        filters=filters,
                        aggregations=aggregations,
                        temporal_references=temporal_refs,
                        business_intent=natural_language_query,
                        confidence_score=0.8,
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
                        ai_analysis={"source": "mock"},
                    )

                    visualization_service = DataVisualizationService()
                    viz_result = (
                        await visualization_service.generate_visualization_spec(
                            execution_result, query_context, semantic_metadata
                        )
                    )

                    if viz_result.get("status") == "success":
                        # Convert visualization spec to JSON-serializable format
                        viz_spec = viz_result["visualization"]
                        visualization_spec = _make_json_serializable(viz_spec)

                        result["services_used"].append("visualization_service")
                        result["execution_times"]["visualization"] = (
                            datetime.now() - service_start
                        ).total_seconds()
                        result["visualization_ready"] = True
                    else:
                        result["visualization_errors"] = viz_result.get(
                            "error", "Visualization failed"
                        )

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
                    from tools.services.data_analytics_service.services.data_service.analytics.data_eda import (
                        DataEDAService,
                    )

                    # Create temporary CSV for EDA
                    df = pl.DataFrame(execution_result.data)
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".csv", delete=False
                    ) as temp_file:
                        df.write_csv(temp_file.name)
                        temp_path = temp_file.name

                    # Run EDA analysis
                    eda_service = DataEDAService(file_path=temp_path)
                    analytics_insights = eda_service.get_quick_insights()

                    result["services_used"].append("analytics_service")
                    result["execution_times"]["analytics"] = (
                        datetime.now() - service_start
                    ).total_seconds()
                    result["analytics_ready"] = True

                    # Cleanup
                    import os

                    os.unlink(temp_path)

                except Exception as e:
                    result["analytics_errors"] = f"Analytics failed: {str(e)}"

            # Final result
            result.update(
                {
                    "success": True,
                    "query_data": {
                        "data": execution_result.data,
                        "column_names": execution_result.column_names,
                        "total_rows": execution_result.row_count,
                    },
                    "visualization": visualization_spec,
                    "analytics_insights": analytics_insights,
                    "total_execution_time": sum(result["execution_times"].values()),
                    "message": f"Query processed using {len(result['services_used'])} services",
                }
            )

            # Report completion
            await data_tool.progress_reporter.report_complete(
                "query",
                {
                    "rows_returned": execution_result.row_count,
                    "services_used": len(result["services_used"]),
                    "execution_time": result["total_execution_time"],
                    "visualization_ready": result.get("visualization_ready", False),
                },
                pipeline_type="query",
            )

            # Complete progress operation
            await data_tool.complete_progress_operation(
                operation_id,
                result={
                    "rows_returned": execution_result.row_count,
                    "execution_time": result["total_execution_time"],
                },
            )

            await data_tool.log_info(
                ctx,
                f"Query completed successfully: {execution_result.row_count} rows returned",
            )

            result["operation_id"] = str(
                operation_id
            )  # ✅ Return operation_id for SSE monitoring

            response = {
                "status": "success",
                "action": "data_query",
                "data": result,
                "timestamp": datetime.now().isoformat(),
            }

            return json.dumps(response, ensure_ascii=False)

        except Exception as e:
            # Fail progress operation on error
            if "operation_id" in locals():
                await data_tool.fail_progress_operation(operation_id, str(e))
            logger.error(f"Data query failed: {str(e)}")
            await data_tool.log_error(ctx, f"Data query failed: {str(e)}")
            error_response = {
                "status": "error",
                "action": "data_query",
                "error": f"Data query failed: {str(e)}",
                "data": {"user_id": str(user_id), "query": str(natural_language_query)},
                "timestamp": datetime.now().isoformat(),
            }
            return json.dumps(error_response, ensure_ascii=False)

    logger.info("=" * 60)
    logger.info("Data Tools Registration Complete")
    logger.info("=" * 60)
    logger.info("Registered 4 MCP tools:")
    logger.info("  1. data_ingest - Complete data ingestion pipeline")
    logger.info("  2. get_pipeline_status - Pipeline status and statistics")
    logger.info("  3. data_search - Semantic similarity search")
    logger.info("  4. data_query - Natural language query execution")
    logger.info("=" * 60)
