#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Digital Asset Progress Context Module

Universal progress tracking for digital asset ingestion pipeline.
Provides standardized 4-stage progress reporting for all asset types.

Pipeline Stages:
1. Processing (25%) - Extract raw content from asset
2. AI Extraction (50%) - AI models analyze content
3. Embedding (75%) - Generate vector embeddings
4. Storing (100%) - Persist to storage systems

Supported Assets: PDF, PPT, DOCX, Image, Audio, Video, and future types
"""

from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class DigitalAssetProgressReporter:
    """
    Universal progress reporting for all digital asset types

    Provides a standardized 4-stage pipeline progress tracking:
    1. Processing (25%) - Extract raw content from asset
    2. AI Extraction (50%) - AI models analyze content
    3. Embedding (75%) - Generate vector embeddings
    4. Storing (100%) - Persist to storage systems

    Supports: PDF, PPT, DOCX, Image, Audio, Video, and future asset types

    Example:
        reporter = DigitalAssetProgressReporter(base_tool)

        # Create operation at start
        operation_id = await base_tool.create_progress_operation(metadata={...})

        # Stage 1: Processing
        await reporter.report_stage(operation_id, "processing", "pdf")

        # Stage 2: AI Extraction with granular progress
        for i in range(1, total_pages + 1):
            await reporter.report_granular_progress(operation_id, "extraction", "pdf", i, total_pages, "page")

        # Stage 3: Embedding
        await reporter.report_stage(operation_id, "embedding", "pdf")

        # Stage 4: Storing
        await reporter.report_storage_progress(operation_id, "pdf", "minio", "uploading")
        await reporter.report_storage_progress(operation_id, "pdf", "vector_db", "indexing")

        # Complete operation
        await base_tool.complete_progress_operation(operation_id, result={...})
    """

    # Ingestion pipeline stages (for store_knowledge)
    INGESTION_STAGES = {
        "processing": {"step": 1, "weight": 25, "label": "Processing"},
        "extraction": {"step": 2, "weight": 50, "label": "AI Extraction"},
        "embedding": {"step": 3, "weight": 75, "label": "Embedding"},
        "storing": {"step": 4, "weight": 100, "label": "Storing"}
    }

    # Retrieval pipeline stages (for search_knowledge)
    RETRIEVAL_STAGES = {
        "processing": {"step": 1, "weight": 25, "label": "Query Processing"},
        "embedding": {"step": 2, "weight": 50, "label": "Query Embedding"},
        "matching": {"step": 3, "weight": 75, "label": "Vector Matching"},
        "reranking": {"step": 4, "weight": 100, "label": "Reranking"}
    }

    # Generation pipeline stages (for knowledge_response)
    GENERATION_STAGES = {
        "processing": {"step": 1, "weight": 25, "label": "Query Analysis"},
        "retrieval": {"step": 2, "weight": 50, "label": "Context Retrieval"},
        "preparation": {"step": 3, "weight": 75, "label": "Context Preparation"},
        "generation": {"step": 4, "weight": 100, "label": "AI Generation"}
    }

    # Default to ingestion stages for backward compatibility
    STAGES = INGESTION_STAGES

    # Asset type display names
    ASSET_NAMES = {
        "pdf": "PDF",
        "ppt": "PowerPoint",
        "pptx": "PowerPoint",
        "doc": "Document",
        "docx": "Document",
        "image": "Image",
        "jpg": "Image",
        "jpeg": "Image",
        "png": "Image",
        "gif": "Image",
        "audio": "Audio",
        "mp3": "Audio",
        "wav": "Audio",
        "video": "Video",
        "mp4": "Video",
        "avi": "Video",
        "text": "Text",
        "document": "Document"
    }

    # Stage-specific prefixes for logging
    STAGE_PREFIXES = {
        "processing": "[PROC]",
        "extraction": "[EXTR]",
        "embedding": "[EMBD]",
        "storing": "[STOR]",
        "retrieval": "[RETR]",
        "matching": "[MATCH]",
        "reranking": "[RERANK]",
        "preparation": "[PREP]",
        "generation": "[GEN]"
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
        asset_type: str,
        sub_progress: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        pipeline_type: str = "ingestion"
    ):
        """
        Report progress for a pipeline stage using ProgressManager (NEW WAY)

        Args:
            operation_id: Operation ID for progress tracking (use ProgressManager)
            stage: Pipeline stage name (varies by pipeline_type)
            asset_type: Asset type - "pdf", "ppt", "image", "audio", "video", "query", etc.
            sub_progress: Optional granular progress within stage (e.g., "page 3/10")
            details: Optional additional details for logging
            pipeline_type: Type of pipeline - "ingestion", "retrieval", or "generation"

        Pipeline Types & Stages:
            ingestion: processing -> extraction -> embedding -> storing
            retrieval: processing -> embedding -> matching -> reranking
            generation: processing -> retrieval -> preparation -> generation

        Examples:
            # Ingestion (store_knowledge)
            await reporter.report_stage(operation_id, "processing", "pdf", pipeline_type="ingestion")
            -> Progress: 25% "Processing PDF" (via ProgressManager)

            # Retrieval (search_knowledge)
            await reporter.report_stage(operation_id, "matching", "query", "top 5 results", pipeline_type="retrieval")
            -> Progress: 75% "Vector Matching Query - top 5 results"

            # Generation (knowledge_response)
            await reporter.report_stage(operation_id, "generation", "query", pipeline_type="generation")
            -> Progress: 100% "AI Generation Query"

        Note: Client monitors progress via SSE: GET /progress/{operation_id}/stream
        """
        # Select the appropriate stage dictionary
        if pipeline_type == "retrieval":
            stages = self.RETRIEVAL_STAGES
        elif pipeline_type == "generation":
            stages = self.GENERATION_STAGES
        else:
            stages = self.INGESTION_STAGES

        if stage not in stages:
            logger.warning(f"Unknown stage '{stage}' for pipeline type '{pipeline_type}', skipping progress report")
            return

        stage_info = stages[stage]
        asset_name = self.ASSET_NAMES.get(asset_type.lower(), asset_type.upper())

        # Build progress message
        message = f"{stage_info['label']}"

        # For queries, don't add asset name redundantly
        if asset_type not in ["query", "text"]:
            message += f" {asset_name}"

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
        asset_type: str,
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
            asset_type: Asset type
            current: Current item number (1-indexed)
            total: Total number of items
            item_type: Type of item being processed (e.g., "page", "slide", "frame")
            pipeline_type: Type of pipeline

        Examples:
            # PDF page processing
            for i in range(1, total_pages + 1):
                await reporter.report_granular_progress(operation_id, "extraction", "pdf", i, total_pages, "page")
            -> Progress: 50% "AI Extraction - analyzing page 1/10"

            # Video frame processing
            for i in range(1, total_frames + 1):
                await reporter.report_granular_progress(operation_id, "extraction", "video", i, total_frames, "frame")
            -> Progress: 50% "AI Extraction - analyzing frame 50/500"

            # PPT slide processing
            for i in range(1, total_slides + 1):
                await reporter.report_granular_progress(operation_id, "extraction", "ppt", i, total_slides, "slide")
            -> Progress: 50% "AI Extraction - analyzing slide 1/20"
        """
        sub_progress = f"analyzing {item_type} {current}/{total}"
        await self.report_stage(operation_id, stage, asset_type, sub_progress, pipeline_type=pipeline_type)

    async def report_storage_progress(
        self,
        operation_id: Optional[str],
        asset_type: str,
        storage_target: str,
        status: str = "uploading",
        pipeline_type: str = "ingestion"
    ):
        """
        Report storage progress with specific targets

        Args:
            operation_id: Operation ID for progress tracking
            asset_type: Asset type
            storage_target: "minio", "vector_db", "neo4j", or "all"
            status: "uploading", "indexing", "completed"
            pipeline_type: Type of pipeline

        Examples:
            await reporter.report_storage_progress(operation_id, "pdf", "minio", "uploading")
            -> Progress: 100% "Storing PDF - uploading to MinIO"

            await reporter.report_storage_progress(operation_id, "pdf", "vector_db", "indexing")
            -> Progress: 100% "Storing PDF - indexing in Vector DB"

            await reporter.report_storage_progress(operation_id, "pdf", "neo4j", "completed")
            -> Progress: 100% "Storing PDF - completed in Neo4j Graph DB"
        """
        target_names = {
            "minio": "MinIO",
            "vector_db": "Vector DB",
            "neo4j": "Neo4j Graph DB",
            "all": "All Storage Systems"
        }

        target_name = target_names.get(storage_target, storage_target)
        sub_progress = f"{status} to {target_name}"

        await self.report_stage(operation_id, "storing", asset_type, sub_progress, pipeline_type=pipeline_type)

    async def report_batch_progress(
        self,
        operation_id: Optional[str],
        stage: str,
        asset_type: str,
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
            asset_type: Asset type
            batch_current: Current batch number
            batch_total: Total batches
            batch_type: Type of batch (e.g., "batch", "chunk", "segment")
            pipeline_type: Type of pipeline

        Example:
            await reporter.report_batch_progress(operation_id, "embedding", "pdf", 2, 5, "chunk batch")
            -> Progress: 75% "Embedding PDF - processing chunk batch 2/5"
        """
        sub_progress = f"processing {batch_type} {batch_current}/{batch_total}"
        await self.report_stage(operation_id, stage, asset_type, sub_progress, pipeline_type=pipeline_type)

    async def report_complete(
        self,
        asset_type: str,
        summary: Optional[Dict[str, Any]] = None
    ):
        """
        Report completion of entire pipeline

        Args:
            asset_type: Asset type
            summary: Optional summary statistics (e.g., pages processed, storage size)

        Example:
            await reporter.report_complete("pdf", {
                "pages": 10,
                "images": 5,
                "storage_mb": 2.4
            })
            -> "[DONE] PDF ingestion complete | {'pages': 10, 'images': 5, 'storage_mb': 2.4}"
        """
        asset_name = self.ASSET_NAMES.get(asset_type.lower(), asset_type.upper())
        message = f"[DONE] {asset_name} ingestion complete"

        if summary:
            message += f" | {summary}"

        logger.info(message)


class AssetTypeDetector:
    """
    Utility class to detect and normalize asset types from file paths or MIME types
    """

    EXTENSION_MAP = {
        # Documents
        ".pdf": "pdf",
        ".doc": "doc",
        ".docx": "docx",
        ".ppt": "ppt",
        ".pptx": "pptx",
        ".txt": "text",

        # Images
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".gif": "image",
        ".webp": "image",
        ".bmp": "image",
        ".svg": "image",

        # Audio
        ".mp3": "audio",
        ".wav": "audio",
        ".m4a": "audio",
        ".flac": "audio",
        ".ogg": "audio",

        # Video
        ".mp4": "video",
        ".avi": "video",
        ".mov": "video",
        ".mkv": "video",
        ".webm": "video"
    }

    @classmethod
    def detect_from_path(cls, file_path: str) -> str:
        """
        Detect asset type from file path

        Args:
            file_path: File path or name

        Returns:
            Asset type (e.g., "pdf", "image", "video")

        Example:
            AssetTypeDetector.detect_from_path("/path/to/doc.pdf") -> "pdf"
            AssetTypeDetector.detect_from_path("image.jpg") -> "image"
        """
        import os
        _, ext = os.path.splitext(file_path.lower())
        return cls.EXTENSION_MAP.get(ext, "document")

    @classmethod
    def normalize_asset_type(cls, content_type: str) -> str:
        """
        Normalize various content type formats to standard asset type

        Args:
            content_type: Content type string (e.g., "pdf", "image/jpeg", "document")

        Returns:
            Normalized asset type

        Example:
            AssetTypeDetector.normalize_asset_type("pdf") -> "pdf"
            AssetTypeDetector.normalize_asset_type("image/jpeg") -> "image"
            AssetTypeDetector.normalize_asset_type("document") -> "document"
        """
        content_type = content_type.lower()

        # Handle MIME types
        if "/" in content_type:
            mime_category = content_type.split("/")[0]
            if mime_category in ["image", "audio", "video"]:
                return mime_category
            if "pdf" in content_type:
                return "pdf"
            if "powerpoint" in content_type or "presentation" in content_type:
                return "ppt"
            if "word" in content_type or "document" in content_type:
                return "docx"

        # Direct mapping
        return content_type
