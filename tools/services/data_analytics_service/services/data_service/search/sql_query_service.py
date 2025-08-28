#!/usr/bin/env python3
"""
SQL Query Service - Steps 4-6 of data analytics pipeline
Combines query matching, SQL generation, and SQL execution
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .query_matcher import QueryMatcher, QueryContext, MetadataMatch, QueryPlan
from .sql_generator import LLMSQLGenerator, SQLGenerationResult
from .sql_executor import SQLExecutor, ExecutionResult, FallbackAttempt
from ..management.metadata.semantic_enricher import SemanticMetadata
from ..management.metadata.metadata_embedding import AIMetadataEmbeddingService

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Complete query processing result"""
    success: bool
    original_query: str
    query_context: Optional[QueryContext]
    metadata_matches: List[MetadataMatch]
    query_plan: Optional[QueryPlan]
    sql_result: Optional[SQLGenerationResult]
    execution_result: Optional[ExecutionResult]
    fallback_attempts: List[FallbackAttempt]
    processing_time_ms: float
    error_message: Optional[str] = None
    warnings: List[str] = None

class SQLQueryService:
    """
    SQL Query processing service - Steps 4-6 of data analytics pipeline
    
    Orchestrates query processing pipeline:
    Step 4: Query context extraction and metadata matching
    Step 5: SQL generation using AI  
    Step 6: SQL execution with fallback mechanisms
    
    Note: This service expects semantic metadata to already be processed and stored
    by MetadataStoreService (Steps 1-3)
    """
    
    def __init__(self, database_config: Dict[str, Any], database_name: str = "default_query_db"):
        """
        Initialize SQL query service
        
        Args:
            database_config: Database connection configuration
            database_name: Database name for embedding service
        """
        self.database_config = database_config
        self.database_name = database_name
        
        # Initialize service components
        self.embedding_service = None
        self.query_matcher = None
        self.sql_generator = None
        self.sql_executor = None
        
        self.processing_history = []
        
    async def initialize(self):
        """Initialize all service components"""
        try:
            # Initialize embedding service with database name
            from ..management.metadata.metadata_embedding import get_embedding_service
            self.embedding_service = get_embedding_service(self.database_name)
            await self.embedding_service.initialize()
            
            # Initialize query matcher
            self.query_matcher = QueryMatcher(self.embedding_service)
            
            # Initialize SQL generator
            self.sql_generator = LLMSQLGenerator()
            await self.sql_generator.initialize()
            
            # Initialize SQL executor
            self.sql_executor = SQLExecutor(self.database_config)
            
            logger.info("SQL Query Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQL Query Service: {e}")
            raise
    
    async def process_query(self, 
                          natural_language_query: str,
                          semantic_metadata: SemanticMetadata,
                          user_context: Optional[Dict[str, Any]] = None) -> QueryResult:
        """
        Process complete natural language query to SQL execution
        
        Args:
            natural_language_query: User's natural language query
            semantic_metadata: Available database metadata
            user_context: Optional user context for personalization
            
        Returns:
            Complete query processing result
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing query: {natural_language_query[:100]}...")
            
            # Step 1: Extract query context and find metadata matches
            query_context, metadata_matches = await self.query_matcher.match_query_to_metadata(
                natural_language_query, semantic_metadata
            )
            
            if not metadata_matches:
                return QueryResult(
                    success=False,
                    original_query=natural_language_query,
                    query_context=query_context,
                    metadata_matches=[],
                    query_plan=None,
                    sql_result=None,
                    execution_result=None,
                    fallback_attempts=[],
                    processing_time_ms=self._calculate_processing_time(start_time),
                    error_message="No matching metadata found for the query",
                    warnings=["Consider checking if the requested data exists in the database"]
                )
            
            # Step 2: Generate query plan
            query_plan = await self.query_matcher.generate_query_plan(
                query_context, metadata_matches, semantic_metadata
            )
            
            # Step 3: Generate SQL using AI
            sql_result = await self.sql_generator.generate_sql_from_context(
                query_context, metadata_matches, semantic_metadata, natural_language_query
            )
            
            # Step 4: Execute SQL with fallback mechanisms
            execution_result, fallback_attempts = await self.sql_executor.execute_sql_with_fallbacks(
                sql_result, natural_language_query
            )
            
            # Calculate processing time
            processing_time = self._calculate_processing_time(start_time)
            
            # Create result
            result = QueryResult(
                success=execution_result.success,
                original_query=natural_language_query,
                query_context=query_context,
                metadata_matches=metadata_matches,
                query_plan=query_plan,
                sql_result=sql_result,
                execution_result=execution_result,
                fallback_attempts=fallback_attempts,
                processing_time_ms=processing_time,
                error_message=execution_result.error_message if not execution_result.success else None,
                warnings=execution_result.warnings or []
            )
            
            # Record processing history
            await self._record_processing_result(result)
            
            logger.info(f"Query processed successfully: {execution_result.row_count} rows in {processing_time:.1f}ms")
            return result
            
        except Exception as e:
            processing_time = self._calculate_processing_time(start_time)
            logger.error(f"Query processing failed: {e}")
            
            return QueryResult(
                success=False,
                original_query=natural_language_query,
                query_context=None,
                metadata_matches=[],
                query_plan=None,
                sql_result=None,
                execution_result=None,
                fallback_attempts=[],
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    async def process_query_with_plan(self,
                                    query_plan: QueryPlan,
                                    query_context: QueryContext,
                                    semantic_metadata: SemanticMetadata,
                                    original_query: str) -> QueryResult:
        """
        Process query using pre-generated query plan
        
        Args:
            query_plan: Pre-generated query plan
            query_context: Query context
            semantic_metadata: Available metadata
            original_query: Original natural language query
            
        Returns:
            Query processing result
        """
        start_time = datetime.now()
        
        try:
            # Generate SQL from plan
            sql_result = await self.sql_generator.generate_sql_from_plan(
                query_plan, query_context, semantic_metadata, original_query
            )
            
            # Execute SQL
            execution_result, fallback_attempts = await self.sql_executor.execute_sql_with_fallbacks(
                sql_result, original_query
            )
            
            processing_time = self._calculate_processing_time(start_time)
            
            result = QueryResult(
                success=execution_result.success,
                original_query=original_query,
                query_context=query_context,
                metadata_matches=[],  # Not applicable for plan-based processing
                query_plan=query_plan,
                sql_result=sql_result,
                execution_result=execution_result,
                fallback_attempts=fallback_attempts,
                processing_time_ms=processing_time,
                error_message=execution_result.error_message if not execution_result.success else None
            )
            
            await self._record_processing_result(result)
            return result
            
        except Exception as e:
            processing_time = self._calculate_processing_time(start_time)
            
            return QueryResult(
                success=False,
                original_query=original_query,
                query_context=query_context,
                metadata_matches=[],
                query_plan=query_plan,
                sql_result=None,
                execution_result=None,
                fallback_attempts=[],
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    async def validate_and_optimize_query(self,
                                        natural_language_query: str,
                                        semantic_metadata: SemanticMetadata) -> Dict[str, Any]:
        """
        Validate and optimize a query without executing it
        
        Args:
            natural_language_query: User's query
            semantic_metadata: Available metadata
            
        Returns:
            Validation and optimization results
        """
        try:
            # Extract context and generate SQL
            query_context, metadata_matches = await self.query_matcher.match_query_to_metadata(
                natural_language_query, semantic_metadata
            )
            
            if not metadata_matches:
                return {
                    'valid': False,
                    'error': 'No matching metadata found',
                    'suggestions': ['Check if the requested data exists in the database']
                }
            
            # Generate SQL
            sql_result = await self.sql_generator.generate_sql_from_context(
                query_context, metadata_matches, semantic_metadata, natural_language_query
            )
            
            # Validate SQL
            validation_result = await self.sql_executor.validate_sql(
                sql_result.sql, semantic_metadata
            )
            
            # Get optimization suggestions
            optimization_result = await self.sql_executor.optimize_query(
                sql_result.sql, semantic_metadata
            )
            
            return {
                'valid': validation_result['is_valid'],
                'generated_sql': sql_result.sql,
                'sql_explanation': sql_result.explanation,
                'confidence_score': sql_result.confidence_score,
                'validation_errors': validation_result['errors'],
                'validation_warnings': validation_result['warnings'],
                'optimization_suggestions': optimization_result['suggestions'],
                'optimized_sql': optimization_result['optimized_sql'],
                'metadata_matches': len(metadata_matches),
                'query_complexity': sql_result.complexity_level
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'suggestions': ['Check query syntax and available data']
            }
    
    async def get_processing_insights(self) -> Dict[str, Any]:
        """Get insights from query processing history"""
        if not self.processing_history:
            return {"message": "No processing history available"}
        
        total_queries = len(self.processing_history)
        successful_queries = sum(1 for result in self.processing_history if result['success'])
        
        # Calculate success rate
        success_rate = successful_queries / total_queries if total_queries > 0 else 0
        
        # Average processing time
        avg_processing_time = sum(r['processing_time_ms'] for r in self.processing_history) / total_queries
        
        # Common failure patterns
        failure_patterns = {}
        for result in self.processing_history:
            if not result['success'] and result.get('error_message'):
                error = result['error_message']
                failure_patterns[error] = failure_patterns.get(error, 0) + 1
        
        # Fallback usage analysis
        fallback_usage = sum(r['fallback_count'] for r in self.processing_history)
        
        return {
            'total_queries': total_queries,
            'success_rate': success_rate,
            'avg_processing_time_ms': avg_processing_time,
            'common_failures': dict(list(failure_patterns.items())[:5]),
            'fallback_usage_rate': fallback_usage / total_queries if total_queries > 0 else 0,
            'recent_performance': self._calculate_recent_performance()
        }
    
    async def learn_from_feedback(self,
                                original_query: str,
                                generated_sql: str,
                                corrected_sql: str,
                                user_satisfaction: str):
        """Learn from user feedback to improve future queries"""
        try:
            # Pass feedback to SQL executor for learning
            await self.sql_executor.learn_from_user_feedback(
                original_query, generated_sql, corrected_sql, user_satisfaction
            )
            
            # Record feedback in processing history
            feedback_record = {
                'timestamp': datetime.now().isoformat(),
                'type': 'user_feedback',
                'original_query': original_query,
                'generated_sql': generated_sql,
                'corrected_sql': corrected_sql,
                'satisfaction': user_satisfaction
            }
            
            self.processing_history.append(feedback_record)
            
            logger.info(f"Recorded user feedback: {user_satisfaction}")
            
        except Exception as e:
            logger.error(f"Failed to process user feedback: {e}")
    
    def _calculate_processing_time(self, start_time: datetime) -> float:
        """Calculate processing time in milliseconds"""
        return (datetime.now() - start_time).total_seconds() * 1000
    
    async def _record_processing_result(self, result: QueryResult):
        """Record query processing result for analysis"""
        try:
            processing_record = {
                'timestamp': datetime.now().isoformat(),
                'success': result.success,
                'processing_time_ms': result.processing_time_ms,
                'query_length': len(result.original_query),
                'metadata_matches': len(result.metadata_matches),
                'fallback_count': len(result.fallback_attempts),
                'sql_confidence': result.sql_result.confidence_score if result.sql_result else 0,
                'result_rows': result.execution_result.row_count if result.execution_result else 0,
                'error_message': result.error_message
            }
            
            self.processing_history.append(processing_record)
            
            # Keep only recent history (last 1000 records)
            if len(self.processing_history) > 1000:
                self.processing_history = self.processing_history[-1000:]
                
        except Exception as e:
            logger.error(f"Failed to record processing result: {e}")
    
    def _calculate_recent_performance(self) -> str:
        """Calculate recent performance trend"""
        if len(self.processing_history) < 10:
            return "insufficient_data"
        
        # Compare last 10 vs previous 10
        recent_10 = self.processing_history[-10:]
        previous_10 = self.processing_history[-20:-10] if len(self.processing_history) >= 20 else []
        
        recent_success_rate = sum(1 for r in recent_10 if r.get('success', False)) / 10
        
        if not previous_10:
            return "improving" if recent_success_rate > 0.7 else "declining"
        
        previous_success_rate = sum(1 for r in previous_10 if r.get('success', False)) / len(previous_10)
        
        if recent_success_rate > previous_success_rate + 0.1:
            return "improving"
        elif recent_success_rate < previous_success_rate - 0.1:
            return "declining"
        else:
            return "stable"
    
    @classmethod
    def create_for_sqlite(cls, database_filename: str, user_id: Optional[str] = None) -> 'SQLQueryService':
        """
        Create SQL query service for SQLite database
        
        Args:
            database_filename: SQLite database filename
            user_id: Optional user ID for user-specific databases
            
        Returns:
            SQLQueryService configured for SQLite
        """
        # Create SQLite configuration
        from pathlib import Path
        
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
        
        database_config = {
            'type': 'sqlite',
            'database': db_path,
            'max_execution_time': 30,
            'max_rows': 10000
        }
        
        return cls(database_config)