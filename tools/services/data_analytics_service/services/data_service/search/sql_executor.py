#!/usr/bin/env python3
"""
SQL Executor - Step 5: SQL execution with fallback mechanisms
"""

import re
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import logging

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

from .query_matcher import QueryPlan, QueryContext
from ..management.metadata.semantic_enricher import SemanticMetadata
from .sql_generator import SQLGenerationResult

# Import professional DuckDB service
try:
    from resources.dbs.duckdb import (
        DuckDBService, 
        DuckDBServiceConfig,
        DuckDBResourceProvider
    )
    DUCKDB_SERVICE_AVAILABLE = True
except ImportError as e:
    DUCKDB_SERVICE_AVAILABLE = False
    # Create placeholder classes to avoid NameError
    class DuckDBService:
        pass
    class DuckDBServiceConfig:
        pass
    class DuckDBResourceProvider:
        pass

# Try basic DuckDB import as fallback
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

logger = logging.getLogger(__name__)

if not DUCKDB_SERVICE_AVAILABLE:
    logger.warning("Professional DuckDB service not available - using basic DuckDB support")

@dataclass
class ExecutionResult:
    """Result of SQL execution"""
    success: bool
    data: List[Dict[str, Any]]
    column_names: List[str]
    row_count: int
    execution_time_ms: float
    sql_executed: str
    error_message: Optional[str] = None
    warnings: List[str] = None

@dataclass
class FallbackAttempt:
    """Information about a fallback attempt"""
    attempt_number: int
    strategy: str
    sql_attempted: str
    success: bool
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None

@dataclass
class ExecutionPlan:
    """Complete execution plan with fallbacks"""
    primary_sql: str
    fallback_strategies: List[str]
    timeout_seconds: int
    max_rows: int
    validation_rules: List[str]

class SQLExecutor:
    """Step 5: SQL execution with intelligent fallback mechanisms"""
    
    def __init__(self, database_config: Dict[str, Any]):
        self.database_config = database_config
        self.connection = None
        self.db_type = database_config.get('type', 'postgresql').lower()
        self.max_execution_time = database_config.get('max_execution_time', 30)
        self.max_rows = database_config.get('max_rows', 10000)
        self.fallback_strategies = self._initialize_fallback_strategies()
        self.execution_history = []  # Store execution feedback for learning
        
        # Initialize professional DuckDB service if available and requested
        self.duckdb_service = None
        self.duckdb_resource_provider = None
        if self.db_type == 'duckdb' and DUCKDB_SERVICE_AVAILABLE:
            self._initialize_professional_duckdb_service()
        
    def initialize_connection(self):
        """Initialize database connection"""
        # Connection initialization logic can go here
        pass
    
    async def execute_sql_with_fallbacks(self, sql_generation_result: SQLGenerationResult,
                                        original_query: str = None) -> Tuple[ExecutionResult, List[FallbackAttempt]]:
        """
        Execute pre-generated SQL with fallback mechanisms
        
        Args:
            sql_generation_result: Pre-generated SQL from LLMSQLGenerator
            original_query: Original user query (for logging/feedback)
            
        Returns:
            Tuple of (execution result, fallback attempts)
        """
        fallback_attempts = []
        
        try:
            # Step 1: Execute the provided SQL
            logger.info(f"Executing SQL: {sql_generation_result.sql[:100]}...")
            execution_result = await self._execute_sql_with_timeout(
                sql_generation_result.sql, self.max_execution_time
            )
            
            if execution_result.success:
                logger.info(f"SQL executed successfully: {execution_result.row_count} rows")
                
                # Record successful execution for learning
                if original_query:
                    await self._record_execution_feedback(
                        original_query, sql_generation_result, execution_result, "success", ""
                    )
                
                return execution_result, fallback_attempts
            
            # Step 2: If primary SQL fails, try fallback strategies
            logger.warning(f"Primary SQL failed: {execution_result.error_message}")
            fallback_attempts.append(FallbackAttempt(
                attempt_number=0,
                strategy="primary_sql",
                sql_attempted=sql_generation_result.sql,
                success=False,
                error_message=execution_result.error_message
            ))
            
            # Try built-in fallback strategies for the SQL
            return await self._execute_with_sql_fallbacks(
                sql_generation_result.sql, fallback_attempts
            )
            
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            
            # Create a final fallback result
            return ExecutionResult(
                success=False,
                data=[],
                column_names=[],
                row_count=0,
                execution_time_ms=0.0,
                sql_executed=sql_generation_result.sql,
                error_message=str(e)
            ), fallback_attempts
    
    async def execute_query_plan_with_fallbacks(self, query_plan: QueryPlan, 
                                         query_context: QueryContext,
                                         semantic_metadata: SemanticMetadata) -> Tuple[ExecutionResult, List[FallbackAttempt]]:
        """
        Execute query with intelligent fallback mechanisms
        
        Args:
            query_plan: Generated query plan
            query_context: Original query context
            semantic_metadata: Available metadata
            
        Returns:
            Tuple of (execution result, fallback attempts)
        """
        fallback_attempts = []
        
        # Generate primary SQL
        primary_sql = self._generate_sql_from_plan(query_plan)
        
        # Create execution plan
        execution_plan = ExecutionPlan(
            primary_sql=primary_sql,
            fallback_strategies=self.fallback_strategies,
            timeout_seconds=self.max_execution_time,
            max_rows=self.max_rows,
            validation_rules=self._generate_validation_rules(query_plan)
        )
        
        # Attempt primary execution
        result = await self._execute_sql_with_timeout(primary_sql, execution_plan.timeout_seconds)
        
        if result.success:
            logger.info(f"Primary SQL executed successfully: {result.row_count} rows")
            return result, fallback_attempts
        
        # Record primary attempt as fallback
        fallback_attempts.append(FallbackAttempt(
            attempt_number=0,
            strategy="primary",
            sql_attempted=primary_sql,
            success=False,
            error_message=result.error_message
        ))
        
        # Try fallback strategies
        for i, strategy in enumerate(execution_plan.fallback_strategies):
            fallback_sql = await self._apply_fallback_strategy(
                strategy, primary_sql, query_plan, query_context, semantic_metadata, result.error_message
            )
            
            if fallback_sql and fallback_sql != primary_sql:
                logger.info(f"Trying fallback strategy {i+1}: {strategy}")
                
                fallback_result = await self._execute_sql_with_timeout(fallback_sql, execution_plan.timeout_seconds)
                
                fallback_attempts.append(FallbackAttempt(
                    attempt_number=i+1,
                    strategy=strategy,
                    sql_attempted=fallback_sql,
                    success=fallback_result.success,
                    error_message=fallback_result.error_message,
                    execution_time_ms=fallback_result.execution_time_ms
                ))
                
                if fallback_result.success:
                    logger.info(f"Fallback strategy '{strategy}' succeeded: {fallback_result.row_count} rows")
                    return fallback_result, fallback_attempts
        
        # All strategies failed
        logger.error("All execution strategies failed")
        return result, fallback_attempts
    
    async def validate_sql(self, sql: str, semantic_metadata: SemanticMetadata) -> Dict[str, Any]:
        """
        Validate SQL against available metadata
        
        Args:
            sql: SQL query to validate
            semantic_metadata: Available metadata for validation
            
        Returns:
            Validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }
        
        try:
            # Parse SQL to extract components
            sql_components = self._parse_sql_components(sql)
            
            # Validate table existence
            table_validation = self._validate_tables(sql_components['tables'], semantic_metadata)
            validation_result['errors'].extend(table_validation['errors'])
            validation_result['warnings'].extend(table_validation['warnings'])
            
            # Validate column existence
            column_validation = self._validate_columns(sql_components['columns'], semantic_metadata)
            validation_result['errors'].extend(column_validation['errors'])
            validation_result['warnings'].extend(column_validation['warnings'])
            
            # Validate joins
            join_validation = self._validate_joins(sql_components['joins'], semantic_metadata)
            validation_result['errors'].extend(join_validation['errors'])
            validation_result['warnings'].extend(join_validation['warnings'])
            
            # Performance warnings
            performance_warnings = self._check_performance_issues(sql, semantic_metadata)
            validation_result['warnings'].extend(performance_warnings)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(sql_components, semantic_metadata)
            validation_result['suggestions'].extend(suggestions)
            
            # Set overall validity
            validation_result['is_valid'] = len(validation_result['errors']) == 0
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"SQL parsing error: {str(e)}")
        
        return validation_result
    
    async def _execute_with_sql_fallbacks(self, primary_sql: str, 
                                        fallback_attempts: List[FallbackAttempt]) -> Tuple[ExecutionResult, List[FallbackAttempt]]:
        """
        Execute SQL with simple fallback strategies (timeout, retry, simplification)
        
        Args:
            primary_sql: The SQL that failed
            fallback_attempts: Existing fallback attempts
            
        Returns:
            Tuple of (execution result, updated fallback attempts)
        """
        try:
            # Strategy 1: Retry with increased timeout
            logger.info("Trying fallback: increased timeout")
            extended_timeout_result = await self._execute_sql_with_timeout(
                primary_sql, self.max_execution_time * 2
            )
            
            fallback_attempts.append(FallbackAttempt(
                attempt_number=len(fallback_attempts) + 1,
                strategy="extended_timeout",
                sql_attempted=primary_sql,
                success=extended_timeout_result.success,
                error_message=extended_timeout_result.error_message,
                execution_time_ms=extended_timeout_result.execution_time_ms
            ))
            
            if extended_timeout_result.success:
                return extended_timeout_result, fallback_attempts
            
            # Strategy 2: Add LIMIT if not present to prevent large result sets
            if 'LIMIT' not in primary_sql.upper() and 'TOP' not in primary_sql.upper():
                limited_sql = primary_sql.rstrip(';') + ' LIMIT 100;'
                logger.info("Trying fallback: adding LIMIT")
                
                limited_result = await self._execute_sql_with_timeout(
                    limited_sql, self.max_execution_time
                )
                
                fallback_attempts.append(FallbackAttempt(
                    attempt_number=len(fallback_attempts) + 1,
                    strategy="add_limit",
                    sql_attempted=limited_sql,
                    success=limited_result.success,
                    error_message=limited_result.error_message,
                    execution_time_ms=limited_result.execution_time_ms
                ))
                
                if limited_result.success:
                    return limited_result, fallback_attempts
            
            # Strategy 3: Simple retry (in case of temporary issues)
            logger.info("Trying fallback: simple retry")
            retry_result = await self._execute_sql_with_timeout(
                primary_sql, self.max_execution_time
            )
            
            fallback_attempts.append(FallbackAttempt(
                attempt_number=len(fallback_attempts) + 1,
                strategy="retry",
                sql_attempted=primary_sql,
                success=retry_result.success,
                error_message=retry_result.error_message,
                execution_time_ms=retry_result.execution_time_ms
            ))
            
            if retry_result.success:
                return retry_result, fallback_attempts
            
            # All fallbacks failed
            return ExecutionResult(
                success=False,
                data=[],
                column_names=[],
                row_count=0,
                execution_time_ms=0.0,
                sql_executed=primary_sql,
                error_message="All fallback strategies failed"
            ), fallback_attempts
            
        except Exception as e:
            logger.error(f"SQL fallback execution failed: {e}")
            return ExecutionResult(
                success=False,
                data=[],
                column_names=[],
                row_count=0,
                execution_time_ms=0.0,
                sql_executed=primary_sql,
                error_message=str(e)
            ), fallback_attempts
    
    async def execute_sql_directly(self, sql: str) -> ExecutionResult:
        """
        Execute SQL directly without any fallbacks - pure execution only
        
        Args:
            sql: SQL to execute
            
        Returns:
            Execution result
        """
        return await self._execute_sql_with_timeout(sql, self.max_execution_time)
    
    async def explain_query_plan(self, sql: str) -> Dict[str, Any]:
        """
        Get database query execution plan
        
        Args:
            sql: SQL query to explain
            
        Returns:
            Query execution plan information
        """
        try:
            await self._ensure_connection()
            
            # Generate EXPLAIN query based on database type
            if self.db_type == 'postgresql':
                explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
            elif self.db_type == 'mysql':
                explain_sql = f"EXPLAIN FORMAT=JSON {sql}"
            elif self.db_type == 'sqlite':
                explain_sql = f"EXPLAIN QUERY PLAN {sql}"
            else:
                explain_sql = f"EXPLAIN {sql}"
            
            if self.db_type == 'postgresql':
                cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = self.connection.cursor()
            
            cursor.execute(explain_sql)
            
            if self.db_type == 'postgresql':
                result = cursor.fetchall()
                return {'plan': result[0]['QUERY PLAN']}
            elif self.db_type == 'mysql':
                result = cursor.fetchall()
                return {'plan': result}
            elif self.db_type == 'sqlite':
                rows = cursor.fetchall()
                return {'plan': [dict(row) for row in rows]}
            else:
                rows = cursor.fetchall()
                return {'plan': [dict(zip([desc[0] for desc in cursor.description], row)) for row in rows]}
                
        except Exception as e:
            logger.error(f"Failed to explain query: {e}")
            return {'error': str(e)}
    
    async def optimize_query(self, sql: str, semantic_metadata: SemanticMetadata) -> Dict[str, Any]:
        """
        Suggest query optimizations
        
        Args:
            sql: Original SQL query
            semantic_metadata: Available metadata
            
        Returns:
            Optimization suggestions
        """
        optimizations = {
            'original_sql': sql,
            'optimized_sql': sql,
            'optimizations_applied': [],
            'performance_impact': 'unknown',
            'suggestions': []
        }
        
        try:
            # Apply optimization strategies
            optimized_sql = sql
            
            # Add LIMIT if missing
            if 'limit' not in sql.lower() and 'top' not in sql.lower():
                optimized_sql = self._add_limit_clause(optimized_sql)
                optimizations['optimizations_applied'].append('Added LIMIT clause')
            
            # Suggest indexes
            index_suggestions = self._suggest_indexes(sql, semantic_metadata)
            optimizations['suggestions'].extend(index_suggestions)
            
            # Optimize joins
            optimized_sql = self._optimize_joins(optimized_sql, semantic_metadata)
            if optimized_sql != sql:
                optimizations['optimizations_applied'].append('Optimized JOIN order')
            
            # Add WHERE optimizations
            optimized_sql = self._optimize_where_clause(optimized_sql, semantic_metadata)
            if optimized_sql != sql:
                optimizations['optimizations_applied'].append('Optimized WHERE clause')
            
            optimizations['optimized_sql'] = optimized_sql
            
            # Estimate performance impact
            if len(optimizations['optimizations_applied']) > 0:
                optimizations['performance_impact'] = 'positive'
            
        except Exception as e:
            logger.error(f"Failed to optimize query: {e}")
            optimizations['error'] = str(e)
        
        return optimizations
    
    async def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics and performance metrics"""
        try:
            await self._ensure_connection()
            
            stats = {
                'database_type': self.db_type,
                'connection_status': 'connected' if self.connection else 'disconnected',
                'database_info': {}
            }
            
            if self.connection:
                cursor = self.connection.cursor()
                
                if self.db_type == 'postgresql':
                    # Get PostgreSQL statistics
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    stats['database_info']['version'] = version
                    
                    cursor.execute("SELECT current_database()")
                    db_name = cursor.fetchone()[0]
                    stats['database_info']['database'] = db_name
                    
                elif self.db_type == 'mysql':
                    # Get MySQL statistics
                    cursor.execute("SELECT VERSION()")
                    version = cursor.fetchone()[0]
                    stats['database_info']['version'] = version
                    
                    cursor.execute("SELECT DATABASE()")
                    db_name = cursor.fetchone()[0]
                    stats['database_info']['database'] = db_name
                
                elif self.db_type == 'sqlite':
                    # Get SQLite statistics
                    cursor.execute("SELECT sqlite_version()")
                    version = cursor.fetchone()[0]
                    stats['database_info']['version'] = version
                    
                    # SQLite doesn't have a database name concept like other DBs
                    stats['database_info']['database'] = self.database_config.get('database', 'sqlite_db')
                    
                    # Get database size
                    cursor.execute("PRAGMA page_count")
                    page_count = cursor.fetchone()[0]
                    cursor.execute("PRAGMA page_size")
                    page_size = cursor.fetchone()[0]
                    stats['database_info']['size_bytes'] = page_count * page_size
                
                cursor.close()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get execution statistics: {e}")
            return {'error': str(e)}
    
    async def _execute_sql_with_timeout(self, sql: str, timeout_seconds: int) -> ExecutionResult:
        """Execute SQL with timeout and error handling"""
        start_time = datetime.now()
        
        try:
            await self._ensure_connection()
            
            # Set timeout (database-specific)
            if self.db_type == 'postgresql':
                cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = self.connection.cursor()
            
            # Execute query
            cursor.execute(sql)
            
            # Fetch results
            if cursor.description:
                # SELECT query
                rows = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                
                # Convert to list of dictionaries
                if self.db_type == 'postgresql':
                    data = [dict(row) for row in rows]
                elif self.db_type == 'sqlite':
                    data = [dict(row) for row in rows]  # sqlite3.Row objects
                else:
                    data = [dict(zip(column_names, row)) for row in rows]
                
                # Apply row limit
                if len(data) > self.max_rows:
                    data = data[:self.max_rows]
                    warnings = [f"Result truncated to {self.max_rows} rows"]
                else:
                    warnings = []
                
            else:
                # Non-SELECT query
                data = []
                column_names = []
                warnings = []
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            cursor.close()
            
            return ExecutionResult(
                success=True,
                data=data,
                column_names=column_names,
                row_count=len(data),
                execution_time_ms=execution_time,
                sql_executed=sql,
                warnings=warnings
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ExecutionResult(
                success=False,
                data=[],
                column_names=[],
                row_count=0,
                execution_time_ms=execution_time,
                sql_executed=sql,
                error_message=str(e)
            )
    
    async def _apply_fallback_strategy(self, strategy: str, original_sql: str, 
                                     query_plan: QueryPlan, query_context: QueryContext,
                                     semantic_metadata: SemanticMetadata, error_message: str) -> Optional[str]:
        """Apply a specific fallback strategy"""
        try:
            if strategy == "simplify_query":
                return self._simplify_query(original_sql, query_plan)
            
            elif strategy == "remove_joins":
                return self._remove_complex_joins(original_sql, query_plan)
            
            elif strategy == "add_limit":
                return self._add_limit_clause(original_sql)
            
            elif strategy == "table_fallback":
                return await self._try_alternative_tables(query_plan, semantic_metadata)
            
            elif strategy == "column_fallback":
                return self._try_alternative_columns(original_sql, query_plan, semantic_metadata)
            
            elif strategy == "syntax_correction":
                return self._correct_syntax_errors(original_sql, error_message)
            
            elif strategy == "basic_select":
                return self._generate_basic_select(query_plan)
            
            else:
                logger.warning(f"Unknown fallback strategy: {strategy}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to apply fallback strategy '{strategy}': {e}")
            return None
    
    def _generate_sql_from_plan(self, query_plan: QueryPlan) -> str:
        """Generate SQL from query plan"""
        sql_parts = []
        
        # SELECT clause
        if query_plan.aggregations:
            select_clause = f"SELECT {', '.join(query_plan.aggregations)}"
        elif query_plan.select_columns:
            select_clause = f"SELECT {', '.join(query_plan.select_columns)}"
        else:
            # Default to selecting all from first table
            first_table = query_plan.primary_tables[0] if query_plan.primary_tables else "table"
            select_clause = f"SELECT {first_table}.*"
        
        sql_parts.append(select_clause)
        
        # FROM clause
        if query_plan.primary_tables:
            from_clause = f"FROM {query_plan.primary_tables[0]}"
            sql_parts.append(from_clause)
        
        # JOIN clauses
        for join in query_plan.required_joins:
            join_clause = (f"{join.get('type', 'INNER').upper()} JOIN {join['right_table']} "
                          f"ON {join['left_table']}.{join['left_column']} = "
                          f"{join['right_table']}.{join['right_column']}")
            sql_parts.append(join_clause)
        
        # WHERE clause
        if query_plan.where_conditions:
            where_clause = f"WHERE {' AND '.join(query_plan.where_conditions)}"
            sql_parts.append(where_clause)
        
        # ORDER BY clause
        if query_plan.order_by:
            order_clause = f"ORDER BY {', '.join(query_plan.order_by)}"
            sql_parts.append(order_clause)
        
        # Add default LIMIT for safety
        sql_parts.append(f"LIMIT {self.max_rows}")
        
        return " ".join(sql_parts)
    
    def _simplify_query(self, sql: str, query_plan: QueryPlan) -> str:
        """Simplify complex query by removing optional parts"""
        # Remove subqueries
        simplified = re.sub(r'\([^)]*SELECT[^)]*\)', 'simplified_subquery', sql, flags=re.IGNORECASE)
        
        # Remove complex functions
        simplified = re.sub(r'\b(CASE\s+WHEN[^E]*END|COALESCE|NULLIF)\b', 'simple_value', simplified, flags=re.IGNORECASE)
        
        # Simplify aggregations
        simplified = re.sub(r'\bGROUP\s+BY\s+[^H]*?(?=\bHAVING|\bORDER|\bLIMIT|$)', '', simplified, flags=re.IGNORECASE)
        simplified = re.sub(r'\bHAVING\s+[^O]*?(?=\bORDER|\bLIMIT|$)', '', simplified, flags=re.IGNORECASE)
        
        return simplified.strip()
    
    def _remove_complex_joins(self, sql: str, query_plan: QueryPlan) -> str:
        """Remove complex joins, keep only the main table"""
        if not query_plan.primary_tables:
            return sql
        
        # Extract first table
        main_table = query_plan.primary_tables[0]
        
        # Generate simple SELECT from main table
        columns = query_plan.select_columns
        if columns:
            # Filter columns to only include those from main table
            main_table_columns = [col for col in columns if col.startswith(f"{main_table}.")]
            if not main_table_columns:
                main_table_columns = [f"{main_table}.*"]
        else:
            main_table_columns = [f"{main_table}.*"]
        
        simple_sql = f"SELECT {', '.join(main_table_columns)} FROM {main_table}"
        
        # Add simple WHERE conditions if any
        if query_plan.where_conditions:
            # Filter conditions to only include those for main table
            main_table_conditions = [cond for cond in query_plan.where_conditions 
                                   if main_table in cond or '.' not in cond]
            if main_table_conditions:
                simple_sql += f" WHERE {' AND '.join(main_table_conditions)}"
        
        simple_sql += f" LIMIT {self.max_rows}"
        
        return simple_sql
    
    def _add_limit_clause(self, sql: str) -> str:
        """Add LIMIT clause to query if missing"""
        if 'limit' not in sql.lower() and 'top' not in sql.lower():
            # Remove existing semicolon if present
            sql = sql.rstrip(';').strip()
            return f"{sql} LIMIT {min(1000, self.max_rows)}"
        return sql
    
    async def _try_alternative_tables(self, query_plan: QueryPlan, semantic_metadata: SemanticMetadata) -> Optional[str]:
        """Try alternative tables from metadata"""
        if not query_plan.primary_tables:
            return None
        
        # Get all available tables
        available_tables = [t['table_name'] for t in semantic_metadata.original_metadata.get('tables', [])]
        
        # Try using a different primary table
        for table in available_tables:
            if table not in query_plan.primary_tables:
                simple_sql = f"SELECT * FROM {table} LIMIT {min(100, self.max_rows)}"
                return simple_sql
        
        return None
    
    def _try_alternative_columns(self, sql: str, query_plan: QueryPlan, semantic_metadata: SemanticMetadata) -> str:
        """Try alternative column selections"""
        if not query_plan.primary_tables:
            return sql
        
        main_table = query_plan.primary_tables[0]
        
        # Get columns for the main table
        table_columns = []
        for col in semantic_metadata.original_metadata.get('columns', []):
            if col['table_name'] == main_table:
                table_columns.append(col['column_name'])
        
        if table_columns:
            # Select first few columns
            limited_columns = table_columns[:5]
            column_list = ', '.join([f"{main_table}.{col}" for col in limited_columns])
            return f"SELECT {column_list} FROM {main_table} LIMIT {self.max_rows}"
        else:
            return f"SELECT * FROM {main_table} LIMIT {self.max_rows}"
    
    def _correct_syntax_errors(self, sql: str, error_message: str) -> str:
        """Attempt to correct common syntax errors"""
        corrected = sql
        
        # Common corrections based on error messages
        if 'column' in error_message.lower() and 'does not exist' in error_message.lower():
            # Try to remove problematic column references
            corrected = re.sub(r'\b\w+\.\w+\b', '*', corrected)
        
        if 'table' in error_message.lower() and 'does not exist' in error_message.lower():
            # This is harder to fix automatically
            pass
        
        if 'syntax error' in error_message.lower():
            # Remove common problematic elements
            corrected = re.sub(r'\bWITH\s+[^S]*?(?=SELECT)', '', corrected, flags=re.IGNORECASE)
            corrected = re.sub(r'\bWINDOW\s+[^S]*?(?=SELECT|FROM)', '', corrected, flags=re.IGNORECASE)
        
        return corrected
    
    def _generate_basic_select(self, query_plan: QueryPlan) -> str:
        """Generate a very basic SELECT query"""
        if query_plan.primary_tables:
            table = query_plan.primary_tables[0]
            return f"SELECT * FROM {table} LIMIT 10"
        else:
            # Can't generate without a table
            return "SELECT 1 as test_query"
    
    async def _ensure_connection(self):
        """Ensure database connection is established"""
        if self.connection is None:
            await self._connect_to_database()
    
    async def _connect_to_database(self):
        """Connect to the database"""
        try:
            if self.db_type == 'postgresql' and PSYCOPG2_AVAILABLE:
                self.connection = psycopg2.connect(
                    host=self.database_config.get('host', 'localhost'),
                    port=self.database_config.get('port', 5432),
                    database=self.database_config.get('database'),
                    user=self.database_config.get('username'),
                    password=self.database_config.get('password')
                )
            
            elif self.db_type == 'mysql' and MYSQL_AVAILABLE:
                self.connection = mysql.connector.connect(
                    host=self.database_config.get('host', 'localhost'),
                    port=self.database_config.get('port', 3306),
                    database=self.database_config.get('database'),
                    user=self.database_config.get('username'),
                    password=self.database_config.get('password')
                )
            
            elif self.db_type == 'sqlserver' and PYODBC_AVAILABLE:
                connection_string = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.database_config.get('host')},"
                    f"{self.database_config.get('port', 1433)};"
                    f"DATABASE={self.database_config.get('database')};"
                    f"UID={self.database_config.get('username')};"
                    f"PWD={self.database_config.get('password')}"
                )
                self.connection = pyodbc.connect(connection_string)
            
            elif self.db_type == 'sqlite' and SQLITE_AVAILABLE:
                # SQLite database path should be provided in database_config['database']
                db_path = self.database_config.get('database')
                if not db_path:
                    raise Exception("SQLite database path not provided in config['database']")
                
                self.connection = sqlite3.connect(db_path)
                # Enable foreign key support
                self.connection.execute("PRAGMA foreign_keys = ON")
                # Set row factory for dict-like access
                self.connection.row_factory = sqlite3.Row
            
            elif self.db_type == 'duckdb':
                # DuckDB connection handled by professional service or fallback
                if self.duckdb_service:
                    logger.info("Using professional DuckDB service - connection managed internally")
                    return
                elif DUCKDB_AVAILABLE:
                    # Fallback to basic DuckDB connection
                    import duckdb
                    db_path = self.database_config.get('database', ':memory:')
                    self.connection = duckdb.connect(db_path)
                    logger.info(f"Connected to DuckDB database: {db_path}")
                    return
                else:
                    raise Exception("DuckDB not available - please install duckdb package")
            
            else:
                raise Exception(f"Database type {self.db_type} not supported or required packages not installed")
            
            logger.info(f"Connected to {self.db_type} database")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def _initialize_fallback_strategies(self) -> List[str]:
        """Initialize fallback strategies in order of preference"""
        return [
            "add_limit",
            "simplify_query",
            "remove_joins",
            "column_fallback",
            "table_fallback",
            "syntax_correction",
            "basic_select"
        ]
    
    def _generate_validation_rules(self, query_plan: QueryPlan) -> List[str]:
        """Generate validation rules for query execution"""
        return [
            "check_table_existence",
            "check_column_existence",
            "validate_join_conditions",
            "check_performance_impact"
        ]
    
    def _parse_sql_components(self, sql: str) -> Dict[str, List[str]]:
        """Parse SQL to extract tables, columns, joins etc."""
        components = {
            'tables': [],
            'columns': [],
            'joins': []
        }
        
        # Extract table names (simple regex - could be improved)
        table_pattern = r'\bFROM\s+(\w+)|JOIN\s+(\w+)'
        table_matches = re.findall(table_pattern, sql, re.IGNORECASE)
        for match in table_matches:
            table_name = match[0] or match[1]
            if table_name:
                components['tables'].append(table_name)
        
        # Extract column names (simple approach)
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        select_match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            columns_text = select_match.group(1)
            if '*' not in columns_text:
                # Parse individual columns
                columns = [col.strip() for col in columns_text.split(',')]
                components['columns'] = columns
        
        return components
    
    def _validate_tables(self, tables: List[str], semantic_metadata: SemanticMetadata) -> Dict[str, List[str]]:
        """Validate that tables exist in metadata"""
        result = {'errors': [], 'warnings': []}
        
        available_tables = [t['table_name'] for t in semantic_metadata.original_metadata.get('tables', [])]
        
        for table in tables:
            if table not in available_tables:
                result['errors'].append(f"Table '{table}' does not exist")
        
        return result
    
    def _validate_columns(self, columns: List[str], semantic_metadata: SemanticMetadata) -> Dict[str, List[str]]:
        """Validate that columns exist in metadata"""
        result = {'errors': [], 'warnings': []}
        
        available_columns = set()
        for col in semantic_metadata.original_metadata.get('columns', []):
            available_columns.add(f"{col['table_name']}.{col['column_name']}")
            available_columns.add(col['column_name'])
        
        for column in columns:
            if '.' in column:
                if column not in available_columns:
                    result['errors'].append(f"Column '{column}' does not exist")
            else:
                # Check if column exists in any table
                if column not in available_columns:
                    result['warnings'].append(f"Column '{column}' may not exist - consider specifying table")
        
        return result
    
    def _validate_joins(self, joins: List[str], semantic_metadata: SemanticMetadata) -> Dict[str, List[str]]:
        """Validate join conditions"""
        result = {'errors': [], 'warnings': []}
        
        # This would need more sophisticated SQL parsing
        # For now, just check if relationships exist in metadata
        relationships = semantic_metadata.original_metadata.get('relationships', [])
        
        if len(joins) > len(relationships):
            result['warnings'].append("More joins specified than known relationships")
        
        return result
    
    def _check_performance_issues(self, sql: str, semantic_metadata: SemanticMetadata) -> List[str]:
        """Check for potential performance issues"""
        warnings = []
        
        # Check for missing WHERE clause
        if 'where' not in sql.lower():
            warnings.append("Query has no WHERE clause - may return large result set")
        
        # Check for missing LIMIT
        if 'limit' not in sql.lower() and 'top' not in sql.lower():
            warnings.append("Query has no LIMIT clause - result set may be very large")
        
        # Check for SELECT *
        if 'select *' in sql.lower():
            warnings.append("SELECT * may return unnecessary columns")
        
        # Check for multiple joins
        join_count = len(re.findall(r'\bjoin\b', sql, re.IGNORECASE))
        if join_count > 3:
            warnings.append(f"Query has {join_count} joins - may impact performance")
        
        return warnings
    
    def _generate_suggestions(self, sql_components: Dict[str, List[str]], 
                            semantic_metadata: SemanticMetadata) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []
        
        # Suggest indexes
        if sql_components['tables']:
            suggestions.append(f"Consider adding indexes on frequently queried columns in {sql_components['tables'][0]}")
        
        # Suggest better column selection
        if len(sql_components['columns']) > 10:
            suggestions.append("Consider selecting fewer columns to improve performance")
        
        # Suggest partitioning for large tables
        large_tables = [t for t in semantic_metadata.original_metadata.get('tables', []) 
                       if t.get('record_count', 0) > 1000000]
        if large_tables:
            suggestions.append("Consider table partitioning for large tables")
        
        return suggestions
    
    def _suggest_indexes(self, sql: str, semantic_metadata: SemanticMetadata) -> List[str]:
        """Suggest database indexes for query optimization"""
        suggestions = []
        
        # Extract WHERE conditions
        where_pattern = r'WHERE\s+(.*?)(?:\s+ORDER|\s+GROUP|\s+LIMIT|$)'
        where_match = re.search(where_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if where_match:
            where_clause = where_match.group(1)
            # Simple extraction of column references
            column_pattern = r'\b(\w+\.\w+|\w+)\s*[=<>!]'
            columns = re.findall(column_pattern, where_clause)
            
            for column in columns[:3]:  # Limit suggestions
                suggestions.append(f"Consider adding index on {column}")
        
        return suggestions
    
    def _optimize_joins(self, sql: str, semantic_metadata: SemanticMetadata) -> str:
        """Optimize join order and conditions"""
        # This would require sophisticated SQL parsing and analysis
        # For now, return original SQL
        return sql
    
    def _optimize_where_clause(self, sql: str, semantic_metadata: SemanticMetadata) -> str:
        """Optimize WHERE clause conditions"""
        # Add basic optimizations like moving selective conditions first
        return sql
    
    @classmethod
    def create_sqlite_executor(cls, database_filename: str, user_id: Optional[str] = None) -> 'SQLExecutor':
        """
        DEPRECATED: Use create_duckdb_executor() instead for better performance
        
        Create SQL executor for SQLite database
        
        Args:
            database_filename: Name of the SQLite database file
            user_id: Optional user ID for user-specific databases
            
        Returns:
            SQLExecutor configured for the SQLite database
        """
        # Redirect to DuckDB for better performance
        logger.warning("create_sqlite_executor is deprecated. Using DuckDB instead for better performance.")
        
        # Use DuckDB with file-based storage
        db_path = f"{database_filename}.duckdb" if not database_filename.endswith('.duckdb') else database_filename
        if user_id:
            db_path = f"user_{user_id}_{db_path}"
        
        return cls.create_duckdb_executor(database_path=db_path)
    
    # ===== LLM Integration and Feedback Methods =====
    
    async def _record_execution_feedback(self, original_query: str, 
                                       llm_result: SQLGenerationResult,
                                       execution_result: ExecutionResult,
                                       feedback_type: str,
                                       user_feedback: str = ""):
        """Record execution feedback for learning"""
        feedback_record = {
            'timestamp': datetime.now().isoformat(),
            'original_query': original_query,
            'generated_sql': llm_result.sql,
            'llm_confidence': llm_result.confidence_score,
            'execution_success': execution_result.success,
            'execution_time_ms': execution_result.execution_time_ms,
            'row_count': execution_result.row_count,
            'error_message': execution_result.error_message,
            'feedback_type': feedback_type,  # 'success', 'failure', 'user_correction'
            'user_feedback': user_feedback
        }
        
        # Store in execution history
        self.execution_history.append(feedback_record)
        
        # Keep only recent history (last 1000 records)
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
        
        # Log for analysis
        logger.info(f"Recorded execution feedback: {feedback_type} for query: {original_query[:50]}...")
    
    async def learn_from_user_feedback(self, original_query: str, 
                                     generated_sql: str,
                                     corrected_sql: str,
                                     user_satisfaction: str):
        """Learn from user feedback and corrections"""
        try:
            # Record the correction
            feedback_record = {
                'timestamp': datetime.now().isoformat(),
                'original_query': original_query,
                'generated_sql': generated_sql,
                'corrected_sql': corrected_sql,
                'user_satisfaction': user_satisfaction,  # 'satisfied', 'partially_satisfied', 'unsatisfied'
                'learning_type': 'user_correction'
            }
            
            self.execution_history.append(feedback_record)
            
            # Learning mechanism implementation
            # Update pattern weights based on feedback
            if user_satisfaction == 'positive':
                self._reinforce_successful_pattern(sql_query, query_context)
            elif user_satisfaction == 'negative':
                self._penalize_failed_pattern(sql_query, query_context, corrected_sql)

            # Update confidence scoring model
            self._update_confidence_model(feedback_record)

            # Log for potential LLM fine-tuning
            self._log_for_finetuning(feedback_record)

            logger.info(f"Learned from user feedback: {user_satisfaction} (pattern weights updated)")
            
        except Exception as e:
            logger.error(f"Failed to process user feedback: {e}")
    
    async def get_execution_insights(self) -> Dict[str, Any]:
        """Get insights from execution history for continuous improvement"""
        if not self.execution_history:
            return {"message": "No execution history available"}
        
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for record in self.execution_history 
                                  if record.get('execution_success', False))
        
        # Calculate success rate
        success_rate = successful_executions / total_executions if total_executions > 0 else 0
        
        # Analyze common failure patterns
        failure_patterns = {}
        for record in self.execution_history:
            if not record.get('execution_success', True):
                error = record.get('error_message', 'Unknown error')
                failure_patterns[error] = failure_patterns.get(error, 0) + 1
        
        # Analyze average confidence vs success correlation
        confidence_success_correlation = 0
        if total_executions > 0:
            successful_records = [r for r in self.execution_history if r.get('execution_success')]
            if successful_records:
                avg_successful_confidence = sum(r.get('llm_confidence', 0) for r in successful_records) / len(successful_records)
                failed_records = [r for r in self.execution_history if not r.get('execution_success')]
                if failed_records:
                    avg_failed_confidence = sum(r.get('llm_confidence', 0) for r in failed_records) / len(failed_records)
                    confidence_success_correlation = avg_successful_confidence - avg_failed_confidence
        
        return {
            'total_executions': total_executions,
            'success_rate': success_rate,
            'common_failures': dict(list(failure_patterns.items())[:5]),  # Top 5 failures
            'confidence_success_correlation': confidence_success_correlation,
            'avg_execution_time': sum(r.get('execution_time_ms', 0) for r in self.execution_history) / total_executions if total_executions > 0 else 0,
            'recent_trend': self._calculate_recent_trend()
        }
    
    def _calculate_recent_trend(self) -> str:
        """Calculate recent performance trend"""
        if len(self.execution_history) < 10:
            return "insufficient_data"
        
        # Compare last 10 vs previous 10
        recent_10 = self.execution_history[-10:]
        previous_10 = self.execution_history[-20:-10] if len(self.execution_history) >= 20 else []
        
        recent_success_rate = sum(1 for r in recent_10 if r.get('execution_success', False)) / 10
        
        if not previous_10:
            return "improving" if recent_success_rate > 0.7 else "declining"
        
        previous_success_rate = sum(1 for r in previous_10 if r.get('execution_success', False)) / len(previous_10)
        
        if recent_success_rate > previous_success_rate + 0.1:
            return "improving"
        elif recent_success_rate < previous_success_rate - 0.1:
            return "declining"
        else:
            return "stable"
    
    async def _execute_with_traditional_fallbacks(self, failed_sql: str,
                                                query_context: QueryContext,
                                                semantic_metadata: SemanticMetadata,
                                                fallback_attempts: List[FallbackAttempt]) -> Tuple[ExecutionResult, List[FallbackAttempt]]:
        """Execute with traditional fallback strategies"""
        
        for i, strategy in enumerate(self.fallback_strategies):
            try:
                fallback_sql = await self._apply_fallback_strategy(
                    strategy, failed_sql, None, query_context, semantic_metadata, ""
                )
                
                if fallback_sql and fallback_sql != failed_sql:
                    logger.info(f"Trying fallback strategy {i+1}: {strategy}")
                    
                    result = await self._execute_sql_with_timeout(fallback_sql, self.max_execution_time)
                    
                    fallback_attempts.append(FallbackAttempt(
                        attempt_number=i+1,
                        strategy=strategy,
                        sql_attempted=fallback_sql,
                        success=result.success,
                        error_message=result.error_message,
                        execution_time_ms=result.execution_time_ms
                    ))
                    
                    if result.success:
                        logger.info(f"Fallback strategy '{strategy}' succeeded")
                        return result, fallback_attempts
                        
            except Exception as e:
                logger.error(f"Fallback strategy '{strategy}' failed: {e}")
        
        # All fallbacks failed
        error_result = ExecutionResult(
            success=False,
            data=[],
            column_names=[],
            row_count=0,
            execution_time_ms=0,
            sql_executed=failed_sql,
            error_message="All execution strategies failed"
        )
        
        return error_result, fallback_attempts
    
    async def _execute_with_query_plan_fallback(self, query_context: QueryContext,
                                              semantic_metadata: SemanticMetadata,
                                              fallback_attempts: List[FallbackAttempt]) -> Tuple[ExecutionResult, List[FallbackAttempt]]:
        """Fallback to traditional query plan generation"""
        
        try:
            # Create a basic query plan
            from query_matcher import QueryPlan
            
            # Get first available table
            tables = semantic_metadata.original_metadata.get('tables', [])
            if not tables:
                raise Exception("No tables available for query plan fallback")
            
            basic_plan = QueryPlan(
                primary_tables=[tables[0]['table_name']],
                required_joins=[],
                select_columns=[f"{tables[0]['table_name']}.*"],
                where_conditions=[],
                aggregations=[],
                order_by=[],
                confidence_score=0.3,
                alternative_plans=[]
            )
            
            # Execute with traditional method
            return await self.execute_query_with_fallbacks(
                basic_plan, query_context, semantic_metadata
            )
            
        except Exception as e:
            logger.error(f"Query plan fallback failed: {e}")
            
            error_result = ExecutionResult(
                success=False,
                data=[],
                column_names=[],
                row_count=0,
                execution_time_ms=0,
                sql_executed="",
                error_message=f"Complete fallback failure: {str(e)}"
            )
            
            return error_result, fallback_attempts
    
    # ===== Professional DuckDB Integration Methods =====
    
    def _initialize_professional_duckdb_service(self):
        """Initialize the professional DuckDB service with configuration"""
        try:
            # Import additional config classes
            from resources.dbs.duckdb import DatabaseConfig, PoolConfig, SecurityConfig
            
            # Create DuckDB service configuration with proper structure
            database_config = DatabaseConfig(
                database_path=self.database_config.get('database', ':memory:'),
                memory_limit=f"{self.database_config.get('max_memory_mb', 1024)}MB"
            )
            
            pool_config = PoolConfig(
                min_connections=1,
                max_connections=self.database_config.get('max_connections', 10),
                connection_timeout=self.database_config.get('connection_timeout', 30.0)
            )
            
            security_config = SecurityConfig(
                enable_security=self.database_config.get('enable_security', True)
            )
            
            duckdb_config = DuckDBServiceConfig(
                database=database_config,
                pool=pool_config,
                security=security_config
            )
            
            # Initialize the professional DuckDB service
            self.duckdb_service = DuckDBService(duckdb_config)
            
            # Initialize MCP resource provider for advanced data operations
            self.duckdb_resource_provider = DuckDBResourceProvider(self.duckdb_service)
            
            logger.info("Professional DuckDB service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize professional DuckDB service: {e}")
            self.duckdb_service = None
            self.duckdb_resource_provider = None
    
    async def _execute_duckdb_sql(self, sql: str, timeout_seconds: int, start_time: datetime) -> ExecutionResult:
        """Execute SQL using the professional DuckDB service"""
        try:
            if self.duckdb_service:
                # Use professional DuckDB service
                result = await self.duckdb_service.execute_query(
                    sql,
                    timeout=timeout_seconds,
                    max_rows=self.max_rows
                )
                
                if result['success']:
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    # Convert professional service result to ExecutionResult format
                    data = result['data']
                    column_names = result.get('columns', [])
                    
                    # Apply row limit if needed
                    warnings = []
                    if len(data) > self.max_rows:
                        data = data[:self.max_rows]
                        warnings.append(f"Result truncated to {self.max_rows} rows")
                    
                    return ExecutionResult(
                        success=True,
                        data=data,
                        column_names=column_names,
                        row_count=len(data),
                        execution_time_ms=execution_time,
                        sql_executed=sql,
                        warnings=warnings
                    )
                else:
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000
                    return ExecutionResult(
                        success=False,
                        data=[],
                        column_names=[],
                        row_count=0,
                        execution_time_ms=execution_time,
                        sql_executed=sql,
                        error_message=result.get('error', 'Unknown DuckDB error')
                    )
            
            elif DUCKDB_AVAILABLE and self.connection:
                # Fallback to basic DuckDB execution
                cursor = self.connection.cursor()
                cursor.execute(sql)
                
                # Fetch results
                if cursor.description:
                    rows = cursor.fetchall()
                    column_names = [desc[0] for desc in cursor.description]
                    data = [dict(zip(column_names, row)) for row in rows]
                    
                    # Apply row limit
                    warnings = []
                    if len(data) > self.max_rows:
                        data = data[:self.max_rows]
                        warnings.append(f"Result truncated to {self.max_rows} rows")
                    
                else:
                    data = []
                    column_names = []
                    warnings = []
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                cursor.close()
                
                return ExecutionResult(
                    success=True,
                    data=data,
                    column_names=column_names,
                    row_count=len(data),
                    execution_time_ms=execution_time,
                    sql_executed=sql,
                    warnings=warnings
                )
            
            else:
                raise Exception("No DuckDB connection available")
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return ExecutionResult(
                success=False,
                data=[],
                column_names=[],
                row_count=0,
                execution_time_ms=execution_time,
                sql_executed=sql,
                error_message=str(e)
            )
    
    async def execute_duckdb_data_wrangling(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute data wrangling operations using professional DuckDB service"""
        if not self.duckdb_resource_provider:
            return {
                'success': False,
                'error': 'Professional DuckDB service not available for data wrangling'
            }
        
        try:
            # Use the professional DuckDB resource provider for advanced operations
            results = []
            
            for operation in operations:
                op_type = operation.get('type')
                
                if op_type == 'load_data':
                    # Load data from file
                    result = await self.duckdb_resource_provider.load_data_from_file(
                        operation['file_path'],
                        operation.get('format', 'csv'),
                        operation.get('options', {})
                    )
                    results.append(result)
                
                elif op_type == 'transform':
                    # Execute transformation SQL
                    result = await self.duckdb_service.execute_query(
                        operation['sql'],
                        timeout=operation.get('timeout', self.max_execution_time)
                    )
                    results.append(result)
                
                elif op_type == 'export':
                    # Export results
                    result = await self.duckdb_resource_provider.export_query_results(
                        operation['sql'],
                        operation['output_path'],
                        operation.get('format', 'csv')
                    )
                    results.append(result)
            
            return {
                'success': True,
                'operations_completed': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"DuckDB data wrangling failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_duckdb_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from professional DuckDB service"""
        if not self.duckdb_service:
            return {'error': 'Professional DuckDB service not available'}
        
        try:
            return await self.duckdb_service.get_performance_metrics()
        except Exception as e:
            logger.error(f"Failed to get DuckDB performance metrics: {e}")
            return {'error': str(e)}
    
    @classmethod
    def create_duckdb_executor(cls, database_path: str = ':memory:', **kwargs) -> 'SQLExecutor':
        """Create SQL executor for DuckDB with professional service support
        
        Args:
            database_path: Path to DuckDB database file (defaults to in-memory)
            **kwargs: Additional configuration options
            
        Returns:
            SQLExecutor configured for DuckDB with professional service support
        """
        database_config = {
            'type': 'duckdb',
            'database': database_path,
            'max_execution_time': kwargs.get('max_execution_time', 30),
            'max_rows': kwargs.get('max_rows', 10000),
            'max_connections': kwargs.get('max_connections', 10),
            'connection_timeout': kwargs.get('connection_timeout', 30.0),
            'query_timeout': kwargs.get('query_timeout', 30.0),
            'max_memory_mb': kwargs.get('max_memory_mb', 1024),
            'enable_monitoring': kwargs.get('enable_monitoring', True),
        }

        return SQLExecutor(database_config)

    def _reinforce_successful_pattern(self, sql_query: str, query_context: Optional[Any]) -> None:
        """Reinforce successful SQL patterns"""
        # Extract pattern features
        if not hasattr(self, 'pattern_weights'):
            self.pattern_weights = {}

        # Simple pattern extraction (improve as needed)
        pattern_key = self._extract_pattern(sql_query)

        if pattern_key not in self.pattern_weights:
            self.pattern_weights[pattern_key] = 1.0

        # Increase weight for successful pattern
        self.pattern_weights[pattern_key] *= 1.1  # 10% increase
        logger.debug(f"Reinforced pattern '{pattern_key}': {self.pattern_weights[pattern_key]:.2f}")

    def _penalize_failed_pattern(self, sql_query: str, query_context: Optional[Any], corrected_sql: Optional[str]) -> None:
        """Penalize failed SQL patterns"""
        if not hasattr(self, 'pattern_weights'):
            self.pattern_weights = {}

        pattern_key = self._extract_pattern(sql_query)

        if pattern_key not in self.pattern_weights:
            self.pattern_weights[pattern_key] = 1.0

        # Decrease weight for failed pattern
        self.pattern_weights[pattern_key] *= 0.9  # 10% decrease
        logger.debug(f"Penalized pattern '{pattern_key}': {self.pattern_weights[pattern_key]:.2f}")

        # If corrected SQL provided, reinforce the correct pattern
        if corrected_sql:
            correct_pattern = self._extract_pattern(corrected_sql)
            if correct_pattern not in self.pattern_weights:
                self.pattern_weights[correct_pattern] = 1.0
            self.pattern_weights[correct_pattern] *= 1.2  # 20% increase for correction
            logger.debug(f"Learned correct pattern '{correct_pattern}': {self.pattern_weights[correct_pattern]:.2f}")

    def _extract_pattern(self, sql_query: str) -> str:
        """Extract SQL pattern for learning"""
        # Simple pattern: first 3 keywords
        keywords = []
        for word in sql_query.upper().split():
            if word in ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP', 'ORDER', 'LIMIT', 'HAVING']:
                keywords.append(word)
            if len(keywords) >= 3:
                break
        return '_'.join(keywords) if keywords else 'UNKNOWN'

    def _update_confidence_model(self, feedback_record: Dict[str, Any]) -> None:
        """Update confidence scoring model based on feedback"""
        if not hasattr(self, 'confidence_adjustments'):
            self.confidence_adjustments = {}

        pattern = feedback_record.get('sql_pattern', 'unknown')
        satisfaction = feedback_record.get('user_satisfaction')

        if pattern not in self.confidence_adjustments:
            self.confidence_adjustments[pattern] = 0.0

        # Adjust confidence based on feedback
        if satisfaction == 'positive':
            self.confidence_adjustments[pattern] += 0.05
        elif satisfaction == 'negative':
            self.confidence_adjustments[pattern] -= 0.05

        # Clamp between -0.3 and +0.3
        self.confidence_adjustments[pattern] = max(-0.3, min(0.3, self.confidence_adjustments[pattern]))

    def _log_for_finetuning(self, feedback_record: Dict[str, Any]) -> None:
        """Log feedback data for potential LLM fine-tuning"""
        # Store in finetuning_data list for later export
        if not hasattr(self, 'finetuning_data'):
            self.finetuning_data = []

        self.finetuning_data.append({
            'timestamp': feedback_record.get('timestamp'),
            'query_context': feedback_record.get('query_context'),
            'generated_sql': feedback_record.get('sql_query'),
            'corrected_sql': feedback_record.get('corrected_sql'),
            'satisfaction': feedback_record.get('user_satisfaction'),
            'error_type': feedback_record.get('error_type')
        })

        # Limit storage to last 1000 records
        if len(self.finetuning_data) > 1000:
            self.finetuning_data = self.finetuning_data[-1000:]

    @staticmethod
    def create_for_duckdb(database_path: str = ":memory:", **kwargs) -> 'SQLExecutor':
        """
        Create SQLExecutor configured for DuckDB

        Args:
            database_path: Path to DuckDB database or :memory: for in-memory
            **kwargs: Additional configuration options

        Returns:
            SQLExecutor configured for DuckDB with professional service support
        """
        database_config = {
            'type': 'duckdb',
            'database': database_path,
            'max_execution_time': kwargs.get('max_execution_time', 30),
            'max_rows': kwargs.get('max_rows', 10000),
            'max_connections': kwargs.get('max_connections', 10),
            'connection_timeout': kwargs.get('connection_timeout', 30.0),
            'query_timeout': kwargs.get('query_timeout', 30.0),
            'max_memory_mb': kwargs.get('max_memory_mb', 1024),
            'enable_monitoring': kwargs.get('enable_monitoring', True),
            'enable_security': kwargs.get('enable_security', True)
        }
        
        return cls(database_config)