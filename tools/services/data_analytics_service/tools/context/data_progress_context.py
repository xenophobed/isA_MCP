#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Analytics Progress Context Module

Universal progress tracking for data analytics pipeline operations.
Provides standardized 4-stage progress reporting for all data operations.

Pipeline Stages:
1. Processing (25%) - Data preprocessing and validation
2. Extraction (50%) - Metadata extraction and semantic enrichment
3. Embedding (75%) - Vector embedding generation
4. Storing (100%) - Storage to MinIO/pgvector

Supported Operations: data_ingest, data_search, data_query
"""

from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class DataProgressReporter:
    """
    Universal progress reporting for all data analytics operations
    
    Provides standardized 4-stage pipeline progress tracking:
    1. Processing (25%) - Data preprocessing, loading, validation
    2. Extraction (50%) - Metadata extraction, semantic enrichment
    3. Embedding (75%) - Vector embedding generation
    4. Storing (100%) - Storage to MinIO Parquet, pgvector, metadata store
    
    Supports: data_ingest, data_search, data_query operations
    
    Example:
        reporter = DataProgressReporter(base_tool)

        # Create operation at start
        operation_id = await base_tool.create_progress_operation(metadata={...})

        # Stage 1: Processing
        await reporter.report_stage(operation_id, "processing", "csv", pipeline_type="ingestion")

        # Stage 2: Extraction with granular progress
        await reporter.report_stage(operation_id, "extraction", "csv", "semantic enrichment")

        # Stage 3: Embedding
        await reporter.report_granular_progress(operation_id, "embedding", "csv", 50, 100, "embedding")

        # Stage 4: Storing
        await reporter.report_storage_progress(operation_id, "csv", "minio", "uploading")
        await reporter.report_storage_progress(operation_id, "csv", "vector_db", "indexing")

        # Complete operation
        await base_tool.complete_progress_operation(operation_id, result={...})
    """
    
    # Ingestion pipeline stages (for data_ingest)
    INGESTION_STAGES = {
        "processing": {"step": 1, "weight": 25, "label": "Processing Data"},
        "extraction": {"step": 2, "weight": 50, "label": "Metadata Extraction"},
        "embedding": {"step": 3, "weight": 75, "label": "Vector Embedding"},
        "storing": {"step": 4, "weight": 100, "label": "Storing Data"}
    }
    
    # Search pipeline stages (for data_search)
    SEARCH_STAGES = {
        "processing": {"step": 1, "weight": 25, "label": "Query Processing"},
        "embedding": {"step": 2, "weight": 50, "label": "Query Embedding"},
        "matching": {"step": 3, "weight": 75, "label": "Similarity Matching"},
        "ranking": {"step": 4, "weight": 100, "label": "Result Ranking"}
    }
    
    # Query pipeline stages (for data_query)
    QUERY_STAGES = {
        "processing": {"step": 1, "weight": 25, "label": "Query Analysis"},
        "retrieval": {"step": 2, "weight": 50, "label": "Data Retrieval"},
        "execution": {"step": 3, "weight": 75, "label": "Query Execution"},
        "visualization": {"step": 4, "weight": 100, "label": "Visualization"}
    }
    
    # Default to ingestion stages for backward compatibility
    STAGES = INGESTION_STAGES
    
    # Data source type display names
    DATA_SOURCE_NAMES = {
        "csv": "CSV",
        "parquet": "Parquet",
        "json": "JSON",
        "excel": "Excel",
        "sql": "SQL Database",
        "api": "API",
        "streaming": "Stream",
        "dataset": "Dataset",
        "query": "Query"
    }
    
    # Stage-specific prefixes for logging
    STAGE_PREFIXES = {
        "processing": "[PROC]",
        "extraction": "[EXTR]",
        "embedding": "[EMBD]",
        "storing": "[STOR]",
        "retrieval": "[RETR]",
        "matching": "[MATCH]",
        "ranking": "[RANK]",
        "execution": "[EXEC]",
        "visualization": "[VIZ]"
    }
    
    def __init__(self, base_tool: BaseTool):
        """
        Initialize progress reporter
        
        Args:
            base_tool: BaseTool instance for accessing Context methods
        """
        self.base_tool = base_tool
    
    async def report_stage(
        self,
        operation_id: Optional[str],
        stage: str,
        data_source_type: str,
        sub_progress: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        pipeline_type: str = "ingestion"
    ):
        """
        Report progress for a pipeline stage using ProgressManager (NEW WAY)

        Args:
            operation_id: Operation ID for progress tracking (use ProgressManager)
            stage: Pipeline stage name (varies by pipeline_type)
            data_source_type: Data source type - "csv", "parquet", "json", "query", etc.
            sub_progress: Optional granular progress within stage (e.g., "row 1000/5000")
            details: Optional additional details for logging
            pipeline_type: Type of pipeline - "ingestion", "search", or "query"

        Pipeline Types & Stages:
            ingestion: processing -> extraction -> embedding -> storing
            search: processing -> embedding -> matching -> ranking
            query: processing -> retrieval -> execution -> visualization

        Examples:
            # Ingestion (data_ingest)
            await reporter.report_stage(operation_id, "processing", "csv", pipeline_type="ingestion")
            -> Progress: 25% "Processing Data CSV" (via ProgressManager)

            # Search (data_search)
            await reporter.report_stage(operation_id, "matching", "query", "top 10 results", pipeline_type="search")
            -> Progress: 75% "Similarity Matching - top 10 results"

            # Query (data_query)
            await reporter.report_stage(operation_id, "execution", "query", "DuckDB SQL", pipeline_type="query")
            -> Progress: 75% "Query Execution - DuckDB SQL"

        Note: Client monitors progress via SSE: GET /progress/{operation_id}/stream
        """
        # Select the appropriate stage dictionary
        if pipeline_type == "search":
            stages = self.SEARCH_STAGES
        elif pipeline_type == "query":
            stages = self.QUERY_STAGES
        else:
            stages = self.INGESTION_STAGES

        if stage not in stages:
            logger.warning(f"Unknown stage '{stage}' for pipeline type '{pipeline_type}', skipping progress report")
            return

        stage_info = stages[stage]
        source_name = self.DATA_SOURCE_NAMES.get(data_source_type.lower(), data_source_type.upper())

        # Build progress message
        message = f"{stage_info['label']}"

        # For queries, don't add source name redundantly
        if data_source_type not in ["query"]:
            message += f" {source_name}"

        if sub_progress:
            message += f" - {sub_progress}"

        # Report using ProgressManager (NEW WAY)
        if operation_id:
            await self.base_tool.update_progress_operation(
                operation_id,
                progress=float(stage_info["weight"]),  # 0-100
                current=stage_info["step"],
                total=4,
                message=message
            )

        # Also log for debugging
        prefix = self.STAGE_PREFIXES.get(stage, "[INFO]")
        log_msg = f"{prefix} Stage {stage_info['step']}/4 ({stage_info['weight']}%): {message}"
        if details:
            log_msg += f" | {details}"

        logger.info(log_msg)
    
    async def report_granular_progress(
        self,
        operation_id: Optional[str],
        stage: str,
        data_source_type: str,
        current: int,
        total: int,
        item_type: str = "item",
        pipeline_type: str = "ingestion"
    ):
        """
        Report granular progress within a stage (for loops/batches)

        This is useful for long-running operations that process multiple items.

        Args:
            operation_id: Operation ID for progress tracking
            stage: Current pipeline stage
            data_source_type: Data source type
            current: Current item number (1-indexed)
            total: Total number of items
            item_type: Type of item being processed (e.g., "row", "embedding", "chunk")
            pipeline_type: Type of pipeline

        Examples:
            # CSV row processing
            for i in range(1, total_rows + 1):
                await reporter.report_granular_progress(operation_id, "processing", "csv", i, total_rows, "row")
            -> Progress: 25% "Processing Data CSV - processing row 1000/5000"

            # Embedding generation
            for i in range(1, total_embeddings + 1):
                await reporter.report_granular_progress(operation_id, "embedding", "csv", i, total_embeddings, "embedding")
            -> Progress: 75% "Vector Embedding - processing embedding 50/100"

            # Query result processing
            for i in range(1, total_results + 1):
                await reporter.report_granular_progress(operation_id, "matching", "query", i, total_results, "result", "search")
            -> Progress: 75% "Similarity Matching - processing result 5/10"
        """
        sub_progress = f"processing {item_type} {current}/{total}"
        await self.report_stage(operation_id, stage, data_source_type, sub_progress, pipeline_type=pipeline_type)
    
    async def report_storage_progress(
        self,
        operation_id: Optional[str],
        data_source_type: str,
        storage_target: str,
        status: str = "uploading",
        pipeline_type: str = "ingestion"
    ):
        """
        Report storage progress with specific targets

        Args:
            operation_id: Operation ID for progress tracking
            data_source_type: Data source type
            storage_target: "minio", "vector_db", "metadata_store", or "all"
            status: "uploading", "indexing", "completed"
            pipeline_type: Type of pipeline

        Examples:
            await reporter.report_storage_progress(operation_id, "csv", "minio", "uploading")
            -> Progress: 100% "Storing Data CSV - uploading to MinIO"

            await reporter.report_storage_progress(operation_id, "csv", "vector_db", "indexing")
            -> Progress: 100% "Storing Data CSV - indexing in Vector DB"

            await reporter.report_storage_progress(operation_id, "parquet", "metadata_store", "completed")
            -> Progress: 100% "Storing Data Parquet - completed in Metadata Store"
        """
        target_names = {
            "minio": "MinIO",
            "vector_db": "Vector DB",
            "metadata_store": "Metadata Store",
            "duckdb": "DuckDB",
            "all": "All Storage Systems"
        }

        target_name = target_names.get(storage_target, storage_target)
        sub_progress = f"{status} to {target_name}"

        await self.report_stage(operation_id, "storing", data_source_type, sub_progress, pipeline_type=pipeline_type)
    
    async def report_batch_progress(
        self,
        operation_id: Optional[str],
        stage: str,
        data_source_type: str,
        batch_current: int,
        batch_total: int,
        batch_type: str = "batch",
        pipeline_type: str = "ingestion"
    ):
        """
        Report batch processing progress

        Useful for parallel/concurrent processing scenarios.

        Args:
            operation_id: Operation ID for progress tracking
            stage: Pipeline stage
            data_source_type: Data source type
            batch_current: Current batch number
            batch_total: Total batches
            batch_type: Type of batch (e.g., "batch", "chunk", "partition")
            pipeline_type: Type of pipeline

        Example:
            await reporter.report_batch_progress(operation_id, "embedding", "csv", 2, 5, "chunk batch")
            -> Progress: 75% "Vector Embedding CSV - processing chunk batch 2/5"
        """
        sub_progress = f"processing {batch_type} {batch_current}/{batch_total}"
        await self.report_stage(operation_id, stage, data_source_type, sub_progress, pipeline_type=pipeline_type)
    
    async def report_data_stats(
        self,
        operation_id: Optional[str],
        stage: str,
        data_source_type: str,
        rows: Optional[int] = None,
        columns: Optional[int] = None,
        quality_score: Optional[float] = None,
        pipeline_type: str = "ingestion"
    ):
        """
        Report data statistics during processing

        Args:
            operation_id: Operation ID for progress tracking
            stage: Current pipeline stage
            data_source_type: Data source type
            rows: Number of rows processed
            columns: Number of columns detected
            quality_score: Data quality score (0.0-1.0)
            pipeline_type: Type of pipeline

        Example:
            await reporter.report_data_stats(operation_id, "processing", "csv", rows=5000, columns=12, quality_score=0.95)
            -> Progress: 25% "Processing Data CSV - 5000 rows, 12 columns, quality: 0.95"
        """
        stats = []
        if rows is not None:
            stats.append(f"{rows} rows")
        if columns is not None:
            stats.append(f"{columns} columns")
        if quality_score is not None:
            stats.append(f"quality: {quality_score:.2f}")

        sub_progress = ", ".join(stats) if stats else None
        await self.report_stage(operation_id, stage, data_source_type, sub_progress, pipeline_type=pipeline_type)
    
    async def report_complete(
        self,
        data_source_type: str,
        summary: Optional[Dict[str, Any]] = None,
        pipeline_type: str = "ingestion"
    ):
        """
        Report completion of entire pipeline

        Args:
            data_source_type: Data source type
            summary: Optional summary statistics (e.g., rows processed, storage size)
            pipeline_type: Type of pipeline

        Example:
            await reporter.report_complete("csv", {
                "rows": 5000,
                "columns": 12,
                "storage_mb": 2.4,
                "embeddings": 100
            })
            -> "[DONE] CSV ingestion complete | {'rows': 5000, 'columns': 12, 'storage_mb': 2.4, 'embeddings': 100}"
        """
        source_name = self.DATA_SOURCE_NAMES.get(data_source_type.lower(), data_source_type.upper())

        if pipeline_type == "search":
            message = f"[DONE] {source_name} search complete"
        elif pipeline_type == "query":
            message = f"[DONE] {source_name} query complete"
        else:
            message = f"[DONE] {source_name} ingestion complete"

        if summary:
            message += f" | {summary}"

        logger.info(message)


class DataSourceDetector:
    """
    Utility class to detect and normalize data source types from file paths or extensions
    """
    
    EXTENSION_MAP = {
        # Structured data
        ".csv": "csv",
        ".tsv": "csv",
        ".parquet": "parquet",
        ".pq": "parquet",
        
        # JSON formats
        ".json": "json",
        ".jsonl": "json",
        ".ndjson": "json",
        
        # Excel formats
        ".xlsx": "excel",
        ".xls": "excel",
        ".xlsm": "excel",
        
        # Database dumps
        ".sql": "sql",
        ".db": "sql",
        ".sqlite": "sql",
        
        # Other formats
        ".xml": "xml",
        ".avro": "avro",
        ".orc": "orc"
    }
    
    @classmethod
    def detect_from_path(cls, file_path: str) -> str:
        """
        Detect data source type from file path
        
        Args:
            file_path: File path or name
        
        Returns:
            Data source type (e.g., "csv", "parquet", "json")
        
        Example:
            DataSourceDetector.detect_from_path("/path/to/data.csv") -> "csv"
            DataSourceDetector.detect_from_path("data.parquet") -> "parquet"
        """
        import os
        _, ext = os.path.splitext(file_path.lower())
        return cls.EXTENSION_MAP.get(ext, "dataset")
    
    @classmethod
    def normalize_source_type(cls, source_type: str) -> str:
        """
        Normalize various source type formats to standard type
        
        Args:
            source_type: Source type string (e.g., "csv", "text/csv", "dataset")
        
        Returns:
            Normalized source type
        
        Example:
            DataSourceDetector.normalize_source_type("csv") -> "csv"
            DataSourceDetector.normalize_source_type("text/csv") -> "csv"
            DataSourceDetector.normalize_source_type("dataset") -> "dataset"
        """
        source_type = source_type.lower()
        
        # Handle MIME types
        if "/" in source_type:
            if "csv" in source_type:
                return "csv"
            if "json" in source_type:
                return "json"
            if "excel" in source_type or "spreadsheet" in source_type:
                return "excel"
            if "parquet" in source_type:
                return "parquet"
        
        # Direct mapping
        return source_type





