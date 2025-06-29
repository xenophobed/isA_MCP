#!/usr/bin/env python3
"""
Data Analytics Tools for MCP Server
Provides the complete 5-step data analytics workflow
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger

# Import the 5-step workflow services
from tools.services.data_analytics_service.core.metadata_extractor import MetadataExtractor
from tools.services.data_analytics_service.services.semantic_enricher import SemanticEnricher
from tools.services.data_analytics_service.services.embedding_storage import EmbeddingStorage
from tools.services.data_analytics_service.services.query_matcher import QueryMatcher
from tools.services.data_analytics_service.services.llm_sql_generator import LLMSQLGenerator
from tools.services.data_analytics_service.services.sql_executor import SQLExecutor

logger = get_logger(__name__)

async def data_sourcing(
    source_type: str,
    source_config: Dict[str, Any],
    storage_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Complete data sourcing workflow: DB → VectorDB
    
    Steps:
    1. Metadata Extraction (Step 1)
    2. Semantic Enrichment (Step 2) 
    3. Embedding & Vector Storage (Step 3)
    
    Args:
        source_type: Type of data source ('database', 'file', etc.)
        source_config: Configuration for connecting to the data source
        storage_config: Optional vector database storage configuration
        
    Returns:
        Dictionary containing the complete sourcing results
    """
    try:
        # Security check
        security_manager = get_security_manager()
        if not security_manager.check_permission("data_analytics", SecurityLevel.MEDIUM):
            raise Exception("Insufficient permissions for data analytics operations")
        
        logger.info(f"🚀 Starting data sourcing workflow for {source_type}")
        
        workflow_results = {
            "workflow": "data_sourcing",
            "start_time": datetime.now().isoformat(),
            "source_type": source_type,
            "steps_completed": [],
            "step_results": {}
        }
        
        # === STEP 1: METADATA EXTRACTION ===
        logger.info("📋 Step 1: Extracting metadata from source")
        step1_start = datetime.now()
        
        metadata_extractor = MetadataExtractor()
        raw_metadata = await metadata_extractor.extract_metadata(source_type, source_config)
        
        step1_time = (datetime.now() - step1_start).total_seconds()
        workflow_results["steps_completed"].append("metadata_extraction")
        workflow_results["step_results"]["step1_metadata_extraction"] = {
            "execution_time_seconds": step1_time,
            "tables_discovered": len(raw_metadata.get("tables", [])),
            "columns_discovered": len(raw_metadata.get("columns", [])),
            "relationships_discovered": len(raw_metadata.get("relationships", [])),
            "status": "completed"
        }
        
        logger.info(f"✅ Step 1 completed in {step1_time:.2f}s - Found {len(raw_metadata.get('tables', []))} tables")
        
        # === STEP 2: SEMANTIC ENRICHMENT ===
        logger.info("🧠 Step 2: Enriching metadata with semantic meaning")
        step2_start = datetime.now()
        
        semantic_enricher = SemanticEnricher()
        semantic_metadata = await semantic_enricher.enrich_metadata(raw_metadata)
        
        step2_time = (datetime.now() - step2_start).total_seconds()
        workflow_results["steps_completed"].append("semantic_enrichment")
        workflow_results["step_results"]["step2_semantic_enrichment"] = {
            "execution_time_seconds": step2_time,
            "business_entities_identified": len(semantic_metadata.business_entities),
            "semantic_tags_created": len(semantic_metadata.semantic_tags),
            "data_patterns_found": len(semantic_metadata.data_patterns),
            "business_rules_inferred": len(semantic_metadata.business_rules),
            "domain_classification": semantic_metadata.domain_classification,
            "status": "completed"
        }
        
        logger.info(f"✅ Step 2 completed in {step2_time:.2f}s - Identified {len(semantic_metadata.business_entities)} business entities")
        
        # === STEP 3: EMBEDDING & VECTOR STORAGE ===
        logger.info("🔢 Step 3: Generating embeddings and storing in vector database")
        step3_start = datetime.now()
        
        # Use default storage config if not provided
        if storage_config is None:
            storage_config = {
                "vector_db_url": "postgresql://localhost:5432/vectordb",  # Default pgvector
                "collection_name": f"metadata_{source_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "embedding_model": "text-embedding-ada-002",
                "chunk_size": 500
            }
        
        embedding_storage = EmbeddingStorage(storage_config)
        await embedding_storage.initialize()
        
        storage_result = await embedding_storage.store_metadata_embeddings(semantic_metadata)
        
        step3_time = (datetime.now() - step3_start).total_seconds()
        workflow_results["steps_completed"].append("embedding_storage")
        workflow_results["step_results"]["step3_embedding_storage"] = {
            "execution_time_seconds": step3_time,
            "embeddings_generated": storage_result.get("embeddings_count", 0),
            "vectors_stored": storage_result.get("vectors_stored", 0),
            "collection_id": storage_result.get("collection_id"),
            "storage_config": storage_config,
            "status": "completed" if storage_result.get("success", False) else "failed"
        }
        
        logger.info(f"✅ Step 3 completed in {step3_time:.2f}s - Stored {storage_result.get('vectors_stored', 0)} vectors")
        
        # === WORKFLOW COMPLETION ===
        total_time = (datetime.now() - datetime.fromisoformat(workflow_results["start_time"])).total_seconds()
        workflow_results["end_time"] = datetime.now().isoformat()
        workflow_results["total_execution_time_seconds"] = total_time
        workflow_results["status"] = "success"
        
        logger.info(f"🎉 Data sourcing workflow completed successfully in {total_time:.2f}s")
        
        return {
            "status": "success",
            "workflow_results": workflow_results,
            "semantic_metadata": semantic_metadata,
            "storage_result": storage_result,
            "message": f"Data sourcing completed: {len(raw_metadata.get('tables', []))} tables processed and stored in vector database"
        }
        
    except Exception as e:
        logger.error(f"❌ Data sourcing workflow failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "workflow_results": workflow_results if 'workflow_results' in locals() else {},
            "message": "Data sourcing workflow failed"
        }

async def data_query(
    natural_query: str,
    source_connection: Dict[str, Any],
    storage_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Complete data query workflow: Query → Result
    
    Steps:
    4. Query Matching (Step 4)
    5. SQL Generation (Step 5) 
    6. SQL Execution (Step 6)
    
    Args:
        natural_query: Natural language query from user
        source_connection: Database connection config for executing final SQL
        storage_config: Vector database config to retrieve metadata
        
    Returns:
        Dictionary containing query results and execution details
    """
    try:
        # Security check
        security_manager = get_security_manager()
        if not security_manager.check_permission("data_analytics", SecurityLevel.MEDIUM):
            raise Exception("Insufficient permissions for data analytics operations")
        
        logger.info(f"🔍 Starting data query workflow: {natural_query[:100]}...")
        
        workflow_results = {
            "workflow": "data_query",
            "start_time": datetime.now().isoformat(),
            "natural_query": natural_query,
            "steps_completed": [],
            "step_results": {}
        }
        
        # Use default storage config if not provided
        if storage_config is None:
            storage_config = {
                "vector_db_url": "postgresql://localhost:5432/vectordb",
                "embedding_model": "text-embedding-ada-002"
            }
        
        # Initialize vector storage to retrieve semantic metadata
        embedding_storage = EmbeddingStorage(storage_config)
        await embedding_storage.initialize()
        
        # === STEP 4: QUERY MATCHING ===
        logger.info("🎯 Step 4: Matching query to metadata")
        step4_start = datetime.now()
        
        # Initialize query matcher
        query_matcher = QueryMatcher(embedding_storage)
        
        # Get semantic metadata from vector storage (simplified - in real implementation this would search vectors)
        # For now, we'll create a mock semantic metadata structure
        from tools.services.data_analytics_service.services.semantic_enricher import SemanticMetadata
        semantic_metadata = SemanticMetadata(
            original_metadata={"tables": [], "columns": []},
            business_entities=[],
            semantic_tags={},
            data_patterns=[],
            business_rules=[],
            domain_classification={"primary_domain": "general"},
            confidence_scores={}
        )
        
        # Match query to metadata
        query_context, metadata_matches = await query_matcher.match_query_to_metadata(
            natural_query, semantic_metadata
        )
        
        step4_time = (datetime.now() - step4_start).total_seconds()
        workflow_results["steps_completed"].append("query_matching")
        workflow_results["step_results"]["step4_query_matching"] = {
            "execution_time_seconds": step4_time,
            "business_intent": query_context.business_intent,
            "entities_identified": query_context.entities_mentioned,
            "attributes_identified": query_context.attributes_mentioned,
            "operations_identified": query_context.operations,
            "metadata_matches_count": len(metadata_matches),
            "confidence_score": query_context.confidence_score,
            "status": "completed"
        }
        
        logger.info(f"✅ Step 4 completed in {step4_time:.2f}s - Found {len(metadata_matches)} metadata matches")
        
        # === STEP 5: SQL GENERATION ===
        logger.info("⚙️ Step 5: Generating SQL from context")
        step5_start = datetime.now()
        
        # Initialize SQL generator
        sql_generator = LLMSQLGenerator()
        await sql_generator.initialize()
        
        # Generate SQL from query context
        sql_generation_result = await sql_generator.generate_sql_from_context(
            query_context=query_context,
            metadata_matches=metadata_matches,
            semantic_metadata=semantic_metadata,
            original_query=natural_query
        )
        
        step5_time = (datetime.now() - step5_start).total_seconds()
        workflow_results["steps_completed"].append("sql_generation")
        workflow_results["step_results"]["step5_sql_generation"] = {
            "execution_time_seconds": step5_time,
            "generated_sql": sql_generation_result.sql,
            "sql_explanation": sql_generation_result.explanation,
            "confidence_score": sql_generation_result.confidence_score,
            "complexity_level": sql_generation_result.complexity_level,
            "estimated_execution_time": sql_generation_result.estimated_execution_time,
            "estimated_rows": sql_generation_result.estimated_rows,
            "status": "completed"
        }
        
        logger.info(f"✅ Step 5 completed in {step5_time:.2f}s - Generated SQL with confidence {sql_generation_result.confidence_score}")
        
        # === STEP 6: SQL EXECUTION ===
        logger.info("▶️ Step 6: Executing SQL against database")
        step6_start = datetime.now()
        
        # Initialize SQL executor
        sql_executor = SQLExecutor(source_connection)
        
        # Execute the generated SQL
        execution_result, fallback_attempts = await sql_executor.execute_sql_with_fallbacks(
            sql_generation_result=sql_generation_result,
            original_query=natural_query
        )
        
        step6_time = (datetime.now() - step6_start).total_seconds()
        workflow_results["steps_completed"].append("sql_execution")
        workflow_results["step_results"]["step6_sql_execution"] = {
            "execution_time_seconds": step6_time,
            "sql_executed": execution_result.sql_executed,
            "execution_success": execution_result.success,
            "rows_returned": execution_result.row_count,
            "columns_returned": execution_result.column_names,
            "query_execution_time_ms": execution_result.execution_time_ms,
            "fallback_attempts": len(fallback_attempts),
            "error_message": execution_result.error_message,
            "status": "completed" if execution_result.success else "failed"
        }
        
        logger.info(f"✅ Step 6 completed in {step6_time:.2f}s - Query {'succeeded' if execution_result.success else 'failed'}")
        
        # === WORKFLOW COMPLETION ===
        total_time = (datetime.now() - datetime.fromisoformat(workflow_results["start_time"])).total_seconds()
        workflow_results["end_time"] = datetime.now().isoformat()
        workflow_results["total_execution_time_seconds"] = total_time
        workflow_results["status"] = "success" if execution_result.success else "partial_success"
        
        logger.info(f"🎉 Data query workflow completed in {total_time:.2f}s")
        
        return {
            "status": "success",
            "workflow_results": workflow_results,
            "query_context": query_context,
            "generated_sql": sql_generation_result.sql,
            "sql_explanation": sql_generation_result.explanation,
            "execution_result": {
                "success": execution_result.success,
                "data": execution_result.data,
                "column_names": execution_result.column_names,
                "row_count": execution_result.row_count,
                "execution_time_ms": execution_result.execution_time_ms,
                "error_message": execution_result.error_message
            },
            "fallback_attempts": [
                {
                    "attempt_number": attempt.attempt_number,
                    "strategy": attempt.strategy,
                    "success": attempt.success,
                    "error_message": attempt.error_message
                }
                for attempt in fallback_attempts
            ],
            "message": f"Query processed: {'Success' if execution_result.success else 'Failed'} - {execution_result.row_count} rows returned"
        }
        
    except Exception as e:
        logger.error(f"❌ Data query workflow failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "workflow_results": workflow_results if 'workflow_results' in locals() else {},
            "message": "Data query workflow failed"
        }

# Tool registration for MCP server
TOOLS = [
    {
        "name": "data_sourcing",
        "description": "Complete data sourcing workflow: Extract metadata → Enrich semantically → Store in vector database",
        "parameters": {
            "source_type": "Type of data source (database, file, etc.)",
            "source_config": "Configuration for connecting to the data source (connection details)",
            "storage_config": "Optional vector database storage configuration"
        }
    },
    {
        "name": "data_query",
        "description": "Complete data query workflow: Natural language query → SQL generation → Database execution",
        "parameters": {
            "natural_query": "Natural language query from user",
            "source_connection": "Database connection config for executing final SQL",
            "storage_config": "Optional vector database config to retrieve metadata"
        }
    }
]