#!/usr/bin/env python3
"""
Data Analytics Tools for MCP Server
Provides the complete 5-step data analytics workflow
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger

# Import the 5-step workflow services
# Temporarily commented out due to PyMuPDF dependency in document_adapter
# from tools.services.data_analytics_service.core.metadata_extractor import MetadataExtractor
# from tools.services.data_analytics_service.services.semantic_enricher import SemanticEnricher
# from tools.services.data_analytics_service.services.embedding_storage import EmbeddingStorage
# from tools.services.data_analytics_service.services.query_matcher import QueryMatcher
# from tools.services.data_analytics_service.services.llm_sql_generator import LLMSQLGenerator
# from tools.services.data_analytics_service.services.sql_executor import SQLExecutor
# from tools.services.data_analytics_service.services.data_visualization import DataVisualizationService

logger = get_logger(__name__)

def register_data_analytics_tools(mcp):
    """Register data analytics tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def data_sourcing(
        source_type: str,
        source_config: Dict[str, Any],
        storage_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Complete data sourcing workflow: DB -> VectorDB
        
        Steps:
        1. Metadata Extraction (Step 1)
        2. Semantic Enrichment (Step 2) 
        3. Embedding & Vector Storage (Step 3)
        
        Args:
            source_type: Type of data source ('database', 'file', etc.)
            source_config: Configuration for connecting to the data source
            storage_config: Optional vector database storage configuration
            
        Returns:
            JSON string containing the complete sourcing results
            
        Keywords: data, sourcing, metadata, analytics, extraction, enrichment, embedding, vector
        Category: data
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
            
            response = {
                "status": "success",
                "action": "data_sourcing",
                "data": {
                    "workflow_results": workflow_results,
                    "semantic_metadata": {
                        "business_entities": semantic_metadata.business_entities,
                        "semantic_tags": semantic_metadata.semantic_tags,
                        "data_patterns": semantic_metadata.data_patterns,
                        "business_rules": semantic_metadata.business_rules,
                        "domain_classification": semantic_metadata.domain_classification
                    },
                    "storage_result": storage_result,
                    "message": f"Data sourcing completed: {len(raw_metadata.get('tables', []))} tables processed and stored in vector database"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Data sourcing completed: {len(raw_metadata.get('tables', []))} tables processed")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "data_sourcing",
                "data": {
                    "source_type": source_type,
                    "error": str(e),
                    "workflow_results": workflow_results if 'workflow_results' in locals() else {},
                    "message": "Data sourcing workflow failed"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Data sourcing failed: {e}")
            return json.dumps(error_response)

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def data_query(
        natural_query: str,
        source_connection: Dict[str, Any],
        storage_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Complete data query workflow: Query -> Result
        
        Steps:
        4. Query Matching (Step 4)
        5. SQL Generation (Step 5) 
        6. SQL Execution (Step 6)
        
        Args:
            natural_query: Natural language query from user
            source_connection: Database connection config for executing final SQL
            storage_config: Vector database config to retrieve metadata
            
        Returns:
            JSON string containing query results and execution details
            
        Keywords: query, sql, natural language, database, analytics, matching, generation, execution
        Category: data
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
            
            # === STEP 7: DATA VISUALIZATION ===
            logger.info("📊 Step 7: Generating visualization specification")
            step7_start = datetime.now()
            
            # Initialize visualization service
            viz_service = DataVisualizationService()
            
            # Generate visualization spec
            viz_result = await viz_service.generate_visualization_spec(
                execution_result=execution_result,
                query_context=query_context,
                semantic_metadata=semantic_metadata,
                preferred_library="chartjs"  # Default to Chart.js
            )
            
            step7_time = (datetime.now() - step7_start).total_seconds()
            workflow_results["steps_completed"].append("data_visualization")
            workflow_results["step_results"]["step7_data_visualization"] = {
                "execution_time_seconds": step7_time,
                "visualization_type": viz_result.get("visualization", {}).get("type", "unknown"),
                "chart_library": viz_result.get("visualization", {}).get("library", "unknown"),
                "confidence_score": viz_result.get("visualization", {}).get("confidence_score", 0.0),
                "insights_count": len(viz_result.get("visualization", {}).get("insights", [])),
                "alternatives_count": len(viz_result.get("alternatives", [])),
                "status": "completed" if viz_result.get("status") == "success" else "failed"
            }
            
            logger.info(f"✅ Step 7 completed in {step7_time:.2f}s - Generated {viz_result.get('visualization', {}).get('type', 'unknown')} visualization")
            
            # === WORKFLOW COMPLETION ===
            total_time = (datetime.now() - datetime.fromisoformat(workflow_results["start_time"])).total_seconds()
            workflow_results["end_time"] = datetime.now().isoformat()
            workflow_results["total_execution_time_seconds"] = total_time
            workflow_results["status"] = "success" if execution_result.success else "partial_success"
            
            logger.info(f"🎉 Data query workflow completed in {total_time:.2f}s")
            
            response = {
                "status": "success",
                "action": "data_query",
                "data": {
                    "workflow_results": workflow_results,
                    "query_context": {
                        "business_intent": query_context.business_intent,
                        "entities_mentioned": query_context.entities_mentioned,
                        "attributes_mentioned": query_context.attributes_mentioned,
                        "operations": query_context.operations,
                        "confidence_score": query_context.confidence_score
                    },
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
                    "visualization": viz_result.get("visualization", {}),
                    "visualization_alternatives": viz_result.get("alternatives", []),
                    "data_insights": viz_result.get("visualization", {}).get("insights", []),
                    "fallback_attempts": [
                        {
                            "attempt_number": attempt.attempt_number,
                            "strategy": attempt.strategy,
                            "success": attempt.success,
                            "error_message": attempt.error_message
                        }
                        for attempt in fallback_attempts
                    ],
                    "message": f"Query processed: {'Success' if execution_result.success else 'Failed'} - {execution_result.row_count} rows returned with {viz_result.get('visualization', {}).get('type', 'unknown')} visualization"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Data query completed: {execution_result.row_count} rows returned")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "data_query",
                "data": {
                    "natural_query": natural_query,
                    "error": str(e),
                    "workflow_results": workflow_results if 'workflow_results' in locals() else {},
                    "message": "Data query workflow failed"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Data query failed: {e}")
            return json.dumps(error_response)

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def generate_visualization(
        data: List[Dict[str, Any]],
        columns: List[str],
        chart_type_hint: Optional[str] = None,
        preferred_library: str = "chartjs",
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Generate visualization specification from raw data
        
        Args:
            data: List of data records
            columns: Column names 
            chart_type_hint: Optional chart type suggestion
            preferred_library: React chart library preference
            title: Optional custom title
            description: Optional custom description
            
        Returns:
            JSON string containing visualization specification
            
        Keywords: visualization, chart, graph, plot, react, data, render, display
        Category: visualization
        """
        try:
            # Security check
            security_manager = get_security_manager()
            if not security_manager.check_permission("data_analytics", SecurityLevel.MEDIUM):
                raise Exception("Insufficient permissions for data analytics operations")
            
            logger.info(f"🎨 Generating visualization for {len(data)} records")
            
            # Create mock query context for standalone visualization
            from tools.services.data_analytics_service.services.query_matcher import QueryContext
            from tools.services.data_analytics_service.services.semantic_enricher import SemanticMetadata
            from tools.services.data_analytics_service.services.sql_executor import ExecutionResult
            from tools.services.data_analytics_service.services.data_visualization import ChartType
            
            query_context = QueryContext(
                business_intent=title or "Data Visualization",
                entities_mentioned=[],
                attributes_mentioned=columns,
                operations=["visualize"],
                confidence_score=0.8
            )
            
            semantic_metadata = SemanticMetadata(
                original_metadata={"tables": [], "columns": []},
                business_entities=[],
                semantic_tags={},
                data_patterns=[],
                business_rules=[],
                domain_classification={"primary_domain": "general"},
                confidence_scores={}
            )
            
            execution_result = ExecutionResult(
                success=True,
                data=data,
                column_names=columns,
                row_count=len(data),
                execution_time_ms=0.0,
                sql_executed="N/A"
            )
            
            # Initialize visualization service
            viz_service = DataVisualizationService()
            
            # Convert chart type hint
            chart_type = None
            if chart_type_hint:
                try:
                    chart_type = ChartType(chart_type_hint.lower())
                except ValueError:
                    logger.warning(f"Invalid chart type hint: {chart_type_hint}")
            
            # Generate visualization spec
            viz_result = await viz_service.generate_visualization_spec(
                execution_result=execution_result,
                query_context=query_context,
                semantic_metadata=semantic_metadata,
                preferred_library=preferred_library,
                chart_type_hint=chart_type
            )
            
            # Override title and description if provided
            if title and viz_result.get("visualization"):
                viz_result["visualization"]["title"] = title
            if description and viz_result.get("visualization"):
                viz_result["visualization"]["description"] = description
            
            logger.info(f"✅ Generated {viz_result.get('visualization', {}).get('type', 'unknown')} visualization")
            
            response = {
                "status": "success",
                "action": "generate_visualization",
                "data": {
                    "visualization": viz_result.get("visualization", {}),
                    "alternatives": viz_result.get("alternatives", []),
                    "insights": viz_result.get("visualization", {}).get("insights", []),
                    "data_summary": viz_result.get("data_summary", {}),
                    "message": f"Generated {viz_result.get('visualization', {}).get('type', 'unknown')} visualization for {len(data)} records"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Generated {viz_result.get('visualization', {}).get('type', 'unknown')} visualization for {len(data)} records")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "generate_visualization",
                "data": {
                    "error": str(e),
                    "visualization": {},
                    "message": "Visualization generation failed"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Visualization generation failed: {e}")
            return json.dumps(error_response)

logger.info("Data analytics tools registered successfully")