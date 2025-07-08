#!/usr/bin/env python3
"""
Batch Knowledge Graph Builder Service

Handles large-scale knowledge graph construction from multiple files/documents.
Provides intelligent batching, progress tracking, and error recovery.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from core.logging import get_logger
from tools.base_service import BaseService
from .file_processor import get_file_processor
from .neo4j_graphrag_client import get_neo4j_graphrag_client

logger = get_logger(__name__)

@dataclass
class BatchProgress:
    """Progress tracking for batch operations."""
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    start_time: datetime
    current_time: datetime
    estimated_completion: Optional[datetime] = None
    current_item: Optional[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        return (self.processed_items / self.total_items * 100) if self.total_items > 0 else 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return (self.successful_items / self.processed_items * 100) if self.processed_items > 0 else 0
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        return (self.current_time - self.start_time).total_seconds()
    
    def estimate_completion(self):
        """Estimate completion time based on current progress."""
        if self.processed_items > 0 and self.processed_items < self.total_items:
            avg_time_per_item = self.elapsed_time / self.processed_items
            remaining_items = self.total_items - self.processed_items
            remaining_seconds = avg_time_per_item * remaining_items
            self.estimated_completion = self.current_time + datetime.timedelta(seconds=remaining_seconds)

class BatchBuilder(BaseService):
    """
    Service for building knowledge graphs from large batches of files/documents.
    
    Features:
    - Intelligent batching and concurrency control
    - Progress tracking and reporting
    - Error recovery and retry mechanisms
    - Memory management for large datasets
    - Incremental updates
    """
    
    def __init__(self, 
                 max_concurrent_files: int = 5,
                 max_concurrent_extractions: int = 3,
                 batch_size: int = 10,
                 retry_attempts: int = 3):
        """
        Initialize batch builder.
        
        Args:
            max_concurrent_files: Max concurrent file processing
            max_concurrent_extractions: Max concurrent knowledge extractions  
            batch_size: Number of files to process in each batch
            retry_attempts: Number of retry attempts for failed operations
        """
        super().__init__("BatchBuilder")
        self.max_concurrent_files = max_concurrent_files
        self.max_concurrent_extractions = max_concurrent_extractions
        self.batch_size = batch_size
        self.retry_attempts = retry_attempts
        
        self.file_processor = get_file_processor()
        self.progress_callbacks: List[Callable[[BatchProgress], None]] = []
        
    def add_progress_callback(self, callback: Callable[[BatchProgress], None]):
        """Add a progress callback function."""
        self.progress_callbacks.append(callback)
    
    async def build_from_directory(self,
                                  directory_path: str,
                                  recursive: bool = True,
                                  file_patterns: Optional[List[str]] = None,
                                  graph_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Build knowledge graph from all files in a directory.
        
        Args:
            directory_path: Directory containing files
            recursive: Whether to process subdirectories
            file_patterns: File patterns to include
            graph_name: Optional name for the knowledge graph
            
        Returns:
            Build results and statistics
        """
        try:
            logger.info(f"Starting directory knowledge graph build: {directory_path}")
            
            # Process directory to get file list
            file_data = await self.file_processor.process_directory(
                directory_path=directory_path,
                recursive=recursive,
                file_patterns=file_patterns
            )
            
            # Filter successful file processing
            valid_files = [f for f in file_data if 'error' not in f and f.get('content')]
            
            if not valid_files:
                return {
                    "status": "error",
                    "message": "No valid files found for processing",
                    "directory": directory_path,
                    "files_found": len(file_data),
                    "valid_files": 0
                }
            
            # Convert to documents format
            documents = []
            for file_info in valid_files:
                documents.append({
                    "id": file_info["file_id"],
                    "content": file_info["content"],
                    "metadata": {
                        "filename": file_info["filename"],
                        "file_path": file_info.get("file_path"),
                        "file_size": file_info.get("file_size"),
                        "file_extension": file_info.get("file_extension"),
                        "processed_time": file_info.get("processed_time"),
                        "chunks": file_info.get("chunks", []),
                        **file_info.get("metadata", {})
                    }
                })
            
            # Build knowledge graph from documents
            result = await self.build_from_documents(
                documents=documents,
                graph_name=graph_name or f"directory_{Path(directory_path).name}"
            )
            
            # Add directory-specific information
            result["source_directory"] = directory_path
            result["files_processed"] = len(valid_files)
            result["files_failed"] = len(file_data) - len(valid_files)
            
            return result
            
        except Exception as e:
            logger.error(f"Directory build failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "directory": directory_path
            }
    
    async def build_from_file_list(self,
                                  file_paths: List[str],
                                  graph_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Build knowledge graph from a list of file paths.
        
        Args:
            file_paths: List of file paths to process
            graph_name: Optional name for the knowledge graph
            
        Returns:
            Build results and statistics
        """
        try:
            logger.info(f"Starting file list knowledge graph build: {len(file_paths)} files")
            
            # Step 1: Process files
            file_process_start = datetime.now()
            logger.info(f"📄 开始文件处理阶段...")
            file_data = await self.file_processor.process_batch(
                file_paths=file_paths,
                max_concurrent=self.max_concurrent_files
            )
            file_process_time = (datetime.now() - file_process_start).total_seconds()
            logger.info(f"✅ 文件处理完成: {file_process_time:.2f}秒")
            
            # Filter successful file processing
            valid_files = [f for f in file_data if 'error' not in f and f.get('content')]
            
            logger.info(f"📊 文件处理结果: {len(valid_files)}/{len(file_data)} 文件成功处理")
            
            if not valid_files:
                return {
                    "status": "error",
                    "message": "No valid files found for processing",
                    "files_provided": len(file_paths),
                    "valid_files": 0
                }
            
            # Step 2: Convert to documents format
            convert_start = datetime.now()
            logger.info(f"🔄 转换文档格式...")
            documents = []
            total_content_size = 0
            
            for file_info in valid_files:
                content = file_info.get("content", "")
                total_content_size += len(content)
                documents.append({
                    "id": file_info["file_id"],
                    "content": content,
                    "metadata": {
                        "filename": file_info["filename"],
                        "file_path": file_info.get("file_path"),
                        "file_size": file_info.get("file_size"),
                        "processed_time": file_info.get("processed_time"),
                        "chunks": file_info.get("chunks", []),
                        **file_info.get("metadata", {})
                    }
                })
            
            convert_time = (datetime.now() - convert_start).total_seconds()
            logger.info(f"✅ 文档转换完成: {convert_time:.2f}秒")
            logger.info(f"📝 总内容大小: {total_content_size:,} 字符 ({total_content_size/(1024*1024):.1f} MB)")
            
            # Step 3: Build knowledge graph
            build_start = datetime.now()
            logger.info(f"🧠 开始知识图谱构建...")
            result = await self.build_from_documents(
                documents=documents,
                graph_name=graph_name or "file_list_graph"
            )
            build_time = (datetime.now() - build_start).total_seconds()
            logger.info(f"✅ 知识图谱构建完成: {build_time:.2f}秒")
            
            # Add file list specific information
            result["files_provided"] = len(file_paths)
            result["files_processed"] = len(valid_files)
            result["files_failed"] = len(file_paths) - len(valid_files)
            
            return result
            
        except Exception as e:
            logger.error(f"File list build failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "files_provided": len(file_paths)
            }
    
    async def build_from_documents(self,
                                  documents: List[Dict[str, Any]],
                                  graph_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Build knowledge graph from a list of documents.
        
        Args:
            documents: List of documents with 'id', 'content', and optional 'metadata'
            graph_name: Optional name for the knowledge graph
            
        Returns:
            Build results and statistics
        """
        start_time = datetime.now()
        
        try:
            # Initialize GraphRAG client
            graphrag_client = await get_neo4j_graphrag_client()
            if not graphrag_client:
                return {
                    "status": "error",
                    "message": "Neo4j GraphRAG client not available",
                    "documents_provided": len(documents)
                }
            
            # Initialize progress tracking
            progress = BatchProgress(
                total_items=len(documents),
                processed_items=0,
                successful_items=0,
                failed_items=0,
                start_time=start_time,
                current_time=start_time
            )
            
            logger.info(f"Starting knowledge graph build from {len(documents)} documents")
            logger.info(f"⚙️  批处理设置: batch_size={self.batch_size}, max_concurrent={self.max_concurrent_extractions}")
            
            # Process documents in batches
            batch_results = []
            successful_extractions = 0
            total_entities = 0
            total_relationships = 0
            
            for i in range(0, len(documents), self.batch_size):
                batch = documents[i:i + self.batch_size]
                batch_start_time = datetime.now()
                batch_num = i//self.batch_size + 1
                total_batches = (len(documents)-1)//self.batch_size + 1
                
                logger.info(f"🔄 处理批次 {batch_num}/{total_batches} (文档 {i+1}-{min(i+len(batch), len(documents))})")
                
                # 分析当前批次的内容大小
                batch_content_size = sum(len(doc.get("content", "")) for doc in batch)
                logger.info(f"📊 当前批次内容: {batch_content_size:,} 字符 ({batch_content_size/1024:.1f} KB)")
                
                # Process batch with concurrency control
                semaphore = asyncio.Semaphore(self.max_concurrent_extractions)
                
                async def process_document_with_semaphore(doc):
                    async with semaphore:
                        return await self._process_document_with_retry(graphrag_client, doc)
                
                # Process batch
                batch_tasks = [process_document_with_semaphore(doc) for doc in batch]
                batch_extraction_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process batch results
                for j, result in enumerate(batch_extraction_results):
                    doc = batch[j]
                    progress.current_item = doc.get("id", "unknown")
                    progress.processed_items += 1
                    progress.current_time = datetime.now()
                    
                    if isinstance(result, Exception):
                        progress.failed_items += 1
                        error_msg = f"Document {doc.get('id')}: {str(result)}"
                        progress.errors.append(error_msg)
                        logger.error(error_msg)
                        
                        batch_results.append({
                            "document_id": doc.get("id"),
                            "status": "failed",
                            "error": str(result)
                        })
                    else:
                        progress.successful_items += 1
                        successful_extractions += 1
                        total_entities += result.get("entities_stored", 0)
                        total_relationships += result.get("relationships_stored", 0)
                        
                        batch_results.append({
                            "document_id": doc.get("id"),
                            "status": "success",
                            "entities_stored": result.get("entities_stored", 0),
                            "relationships_stored": result.get("relationships_stored", 0)
                        })
                    
                    # Update progress estimate
                    progress.estimate_completion()
                    
                    # Call progress callbacks
                    for callback in self.progress_callbacks:
                        try:
                            callback(progress)
                        except Exception as e:
                            logger.warning(f"Progress callback failed: {e}")
                
                batch_time = (datetime.now() - batch_start_time).total_seconds()
                logger.info(f"Batch completed in {batch_time:.2f}s - {len([r for r in batch_extraction_results if not isinstance(r, Exception)])}/{len(batch)} successful")
            
            # Final statistics
            total_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "status": "success" if progress.failed_items == 0 else "partial_success",
                "graph_name": graph_name or f"batch_graph_{start_time.strftime('%Y%m%d_%H%M%S')}",
                "build_summary": {
                    "total_documents": len(documents),
                    "successful_documents": progress.successful_items,
                    "failed_documents": progress.failed_items,
                    "success_rate": progress.success_rate,
                    "total_entities_created": total_entities,
                    "total_relationships_created": total_relationships,
                    "total_build_time_seconds": total_time,
                    "average_time_per_document": total_time / len(documents) if len(documents) > 0 else 0
                },
                "batch_results": batch_results,
                "errors": progress.errors[:20],  # Limit error list
                "progress": asdict(progress),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Knowledge graph build completed: {progress.successful_items}/{len(documents)} documents processed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Batch build failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "documents_provided": len(documents),
                "build_time_seconds": (datetime.now() - start_time).total_seconds()
            }
    
    async def _process_document_with_retry(self, graphrag_client, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document with retry logic."""
        last_exception = None
        doc_id = document.get("id", "unknown")
        content = document.get("content", "")
        content_size = len(content)
        
        logger.info(f"📄 开始处理文档 {doc_id}: {content_size:,} 字符")
        doc_start_time = datetime.now()
        
        for attempt in range(self.retry_attempts):
            try:
                metadata = document.get("metadata", {})
                
                if not content.strip():
                    logger.info(f"   ⚠️  文档 {doc_id} 内容为空，跳过")
                    return {"entities_stored": 0, "relationships_stored": 0}
                
                # Extract and store knowledge
                extraction_start = datetime.now()
                logger.info(f"   🧠 执行知识提取 (尝试 {attempt + 1}/{self.retry_attempts})")
                
                result = await graphrag_client.extract_and_store_from_text(
                    text=content,
                    source_id=doc_id,
                    chunk_id=metadata.get("chunk_id")
                )
                
                extraction_time = (datetime.now() - extraction_start).total_seconds()
                total_time = (datetime.now() - doc_start_time).total_seconds()
                processing_rate = content_size / total_time if total_time > 0 else 0
                
                logger.info(f"   ✅ 文档 {doc_id} 完成: {total_time:.2f}秒")
                logger.info(f"      🏷️  实体: {result.get('entities_stored', 0)}个")
                logger.info(f"      🔗 关系: {result.get('relationships_stored', 0)}个")
                logger.info(f"      ⚡ 提取耗时: {extraction_time:.2f}秒")
                logger.info(f"      🚀 处理速度: {processing_rate:.0f} 字符/秒")
                
                return result
                
            except Exception as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"Document {document.get('id')} failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Document {document.get('id')} failed after {self.retry_attempts} attempts: {e}")
        
        raise last_exception or Exception("Unknown error in document processing")
    
    async def get_build_status(self, graph_name: str) -> Dict[str, Any]:
        """Get status information for a previously built graph."""
        try:
            graphrag_client = await get_neo4j_graphrag_client()
            if not graphrag_client:
                return {"status": "error", "message": "Neo4j not available"}
            
            # Get graph statistics
            stats = await graphrag_client.neo4j_client.get_graph_statistics(graph_name)
            
            return {
                "status": "success",
                "graph_name": graph_name,
                "statistics": stats,
                "last_checked": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get build status: {e}")
            return {
                "status": "error",
                "message": str(e),
                "graph_name": graph_name
            }
    
    async def incremental_update(self,
                                new_documents: List[Dict[str, Any]],
                                graph_name: str) -> Dict[str, Any]:
        """
        Perform incremental update to existing knowledge graph.
        
        Args:
            new_documents: New documents to add
            graph_name: Name of existing graph to update
            
        Returns:
            Update results
        """
        try:
            logger.info(f"Starting incremental update for graph '{graph_name}' with {len(new_documents)} new documents")
            
            # Build knowledge from new documents
            result = await self.build_from_documents(
                documents=new_documents,
                graph_name=graph_name  # Use same graph name to add to existing
            )
            
            result["update_type"] = "incremental"
            result["new_documents_added"] = len(new_documents)
            
            return result
            
        except Exception as e:
            logger.error(f"Incremental update failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "graph_name": graph_name,
                "new_documents": len(new_documents)
            }

# Global instance
_batch_builder = None

def get_batch_builder(**kwargs) -> BatchBuilder:
    """Get or create the global batch builder instance."""
    global _batch_builder
    if _batch_builder is None:
        _batch_builder = BatchBuilder(**kwargs)
    return _batch_builder