#!/usr/bin/env python3
"""
Unit tests for SQLExecutor - Step 5 of the analytics workflow
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from tools.services.data_analytics_service.core.sql_executor import (
    SQLExecutor, ExecutionResult, FallbackAttempt, ExecutionPlan
)
from tools.services.data_analytics_service.core.query_matcher import QueryPlan, QueryContext
from tools.services.data_analytics_service.core.semantic_enricher import SemanticMetadata


@pytest.fixture
def database_config():
    """Sample database configuration"""
    return {
        'type': 'postgresql',
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'username': 'test_user',
        'password': 'test_pass',
        'max_execution_time': 30,
        'max_rows': 1000
    }


@pytest.fixture
def sql_executor(database_config):
    """Create SQLExecutor instance"""
    return SQLExecutor(database_config)


@pytest.fixture
def sample_query_plan():
    """Sample query plan for testing"""
    return QueryPlan(
        primary_tables=['customers'],
        required_joins=[],
        select_columns=['customers.customer_id', 'customers.email'],
        where_conditions=['customers.active = true'],
        aggregations=[],
        order_by=['customers.created_at DESC'],
        confidence_score=0.8,
        alternative_plans=[]
    )


@pytest.fixture
def sample_query_context():
    """Sample query context for testing"""
    return QueryContext(
        entities_mentioned=['customers'],
        attributes_mentioned=['email'],
        operations=['select'],
        filters=[{'type': 'text', 'field': 'active', 'operator': 'equals', 'value': 'true'}],
        aggregations=[],
        temporal_references=[],
        business_intent='lookup',
        confidence_score=0.8
    )


@pytest.fixture
def sample_semantic_metadata():
    """Sample semantic metadata for testing"""
    return SemanticMetadata(
        original_metadata={
            'tables': [
                {
                    'table_name': 'customers',
                    'table_type': 'table',
                    'record_count': 1000
                }
            ],
            'columns': [
                {
                    'table_name': 'customers',
                    'column_name': 'customer_id',
                    'data_type': 'integer',
                    'is_nullable': False
                },
                {
                    'table_name': 'customers',
                    'column_name': 'email',
                    'data_type': 'varchar',
                    'is_nullable': False
                }
            ],
            'relationships': []
        },
        business_entities=[],
        semantic_tags={},
        data_patterns=[],
        business_rules=[],
        domain_classification={},
        confidence_scores={}
    )


class TestSQLExecutor:
    """Test cases for SQLExecutor"""
    
    def test_initialization(self, sql_executor, database_config):
        """Test SQLExecutor initialization"""
        assert sql_executor is not None
        assert sql_executor.database_config == database_config
        assert sql_executor.db_type == 'postgresql'
        assert sql_executor.max_execution_time == 30
        assert sql_executor.max_rows == 1000
        assert isinstance(sql_executor.fallback_strategies, list)
        assert len(sql_executor.fallback_strategies) > 0
    
    def test_generate_sql_from_plan_basic(self, sql_executor, sample_query_plan):
        """Test basic SQL generation from query plan"""
        sql = sql_executor._generate_sql_from_plan(sample_query_plan)
        
        assert 'SELECT' in sql.upper()
        assert 'customers.customer_id' in sql
        assert 'customers.email' in sql
        assert 'FROM customers' in sql
        assert 'WHERE customers.active = true' in sql
        assert 'ORDER BY customers.created_at DESC' in sql
        assert 'LIMIT' in sql.upper()
    
    def test_generate_sql_from_plan_with_joins(self, sql_executor):
        """Test SQL generation with joins"""
        plan_with_joins = QueryPlan(
            primary_tables=['customers', 'orders'],
            required_joins=[
                {
                    'type': 'inner',
                    'left_table': 'customers',
                    'right_table': 'orders',
                    'left_column': 'customer_id',
                    'right_column': 'customer_id'
                }
            ],
            select_columns=['customers.email', 'orders.total'],
            where_conditions=[],
            aggregations=[],
            order_by=[],
            confidence_score=0.8,
            alternative_plans=[]
        )
        
        sql = sql_executor._generate_sql_from_plan(plan_with_joins)
        
        assert 'INNER JOIN orders' in sql
        assert 'ON customers.customer_id = orders.customer_id' in sql
    
    def test_generate_sql_from_plan_with_aggregations(self, sql_executor):
        """Test SQL generation with aggregations"""
        plan_with_agg = QueryPlan(
            primary_tables=['customers'],
            required_joins=[],
            select_columns=[],
            where_conditions=[],
            aggregations=['COUNT(*)', 'SUM(orders.total)'],
            order_by=[],
            confidence_score=0.8,
            alternative_plans=[]
        )
        
        sql = sql_executor._generate_sql_from_plan(plan_with_agg)
        
        assert 'COUNT(*)' in sql
        assert 'SUM(orders.total)' in sql
    
    def test_simplify_query(self, sql_executor, sample_query_plan):
        """Test query simplification"""
        complex_sql = """
        SELECT customers.*, 
               CASE WHEN orders.total > 100 THEN 'high' ELSE 'low' END as category,
               (SELECT COUNT(*) FROM orders WHERE customer_id = customers.customer_id) as order_count
        FROM customers 
        LEFT JOIN orders ON customers.customer_id = orders.customer_id
        GROUP BY customers.customer_id
        HAVING COUNT(orders.order_id) > 5
        """
        
        simplified = sql_executor._simplify_query(complex_sql, sample_query_plan)
        
        # Should remove complex parts
        assert 'CASE WHEN' not in simplified
        assert 'SELECT COUNT(*)' not in simplified  # Subqueries removed
        assert 'GROUP BY' not in simplified
        assert 'HAVING' not in simplified
    
    def test_remove_complex_joins(self, sql_executor, sample_query_plan):
        """Test removing complex joins"""
        complex_sql = """
        SELECT c.email, o.total, p.name
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        """
        
        simplified = sql_executor._remove_complex_joins(complex_sql, sample_query_plan)
        
        # Should only keep main table
        assert 'FROM customers' in simplified
        assert 'JOIN' not in simplified
        assert 'customers.*' in simplified or 'customers.customer_id' in simplified
    
    def test_add_limit_clause(self, sql_executor):
        """Test adding LIMIT clause"""
        sql_without_limit = "SELECT * FROM customers WHERE active = true"
        sql_with_limit = sql_executor._add_limit_clause(sql_without_limit)
        
        assert 'LIMIT' in sql_with_limit.upper()
        assert '1000' in sql_with_limit  # Should use max_rows
    
    def test_add_limit_clause_existing(self, sql_executor):
        """Test not adding LIMIT when already exists"""
        sql_with_limit = "SELECT * FROM customers LIMIT 50"
        result = sql_executor._add_limit_clause(sql_with_limit)
        
        # Should not modify
        assert result == sql_with_limit
    
    def test_correct_syntax_errors(self, sql_executor):
        """Test syntax error correction"""
        # Test column error correction
        sql_with_error = "SELECT customers.invalid_column, orders.total FROM customers"
        error_msg = "column customers.invalid_column does not exist"
        
        corrected = sql_executor._correct_syntax_errors(sql_with_error, error_msg)
        
        # Should replace problematic column references
        assert 'invalid_column' not in corrected or '*' in corrected
    
    def test_generate_basic_select(self, sql_executor, sample_query_plan):
        """Test generating basic SELECT query"""
        basic_sql = sql_executor._generate_basic_select(sample_query_plan)
        
        assert 'SELECT * FROM customers' in basic_sql
        assert 'LIMIT' in basic_sql.upper()
    
    def test_generate_basic_select_no_tables(self, sql_executor):
        """Test generating basic SELECT with no tables"""
        empty_plan = QueryPlan([], [], [], [], [], [], 0.5, [])
        basic_sql = sql_executor._generate_basic_select(empty_plan)
        
        assert 'SELECT 1 as test_query' in basic_sql
    
    @pytest.mark.asyncio
    async def test_try_alternative_tables(self, sql_executor, sample_query_plan, sample_semantic_metadata):
        """Test trying alternative tables"""
        alt_sql = await sql_executor._try_alternative_tables(sample_query_plan, sample_semantic_metadata)
        
        # Should return a simple query with available table
        if alt_sql:
            assert 'SELECT * FROM' in alt_sql
            assert 'LIMIT' in alt_sql.upper()
    
    def test_try_alternative_columns(self, sql_executor, sample_query_plan, sample_semantic_metadata):
        """Test trying alternative columns"""
        original_sql = "SELECT customers.invalid_column FROM customers"
        
        alt_sql = sql_executor._try_alternative_columns(original_sql, sample_query_plan, sample_semantic_metadata)
        
        assert 'FROM customers' in alt_sql
        assert 'customer_id' in alt_sql or 'email' in alt_sql  # Should use available columns
    
    def test_parse_sql_components(self, sql_executor):
        """Test SQL component parsing"""
        sql = """
        SELECT customers.email, orders.total
        FROM customers
        JOIN orders ON customers.customer_id = orders.customer_id
        WHERE customers.active = true
        """
        
        components = sql_executor._parse_sql_components(sql)
        
        assert 'customers' in components['tables']
        assert 'orders' in components['tables']
        assert len(components['columns']) > 0
    
    def test_validate_tables(self, sql_executor, sample_semantic_metadata):
        """Test table validation"""
        tables = ['customers', 'invalid_table']
        result = sql_executor._validate_tables(tables, sample_semantic_metadata)
        
        assert len(result['errors']) == 1
        assert 'invalid_table' in result['errors'][0]
    
    def test_validate_columns(self, sql_executor, sample_semantic_metadata):
        """Test column validation"""
        columns = ['customers.email', 'customers.invalid_column', 'email']
        result = sql_executor._validate_columns(columns, sample_semantic_metadata)
        
        # Should have error for invalid column
        assert len(result['errors']) > 0 or len(result['warnings']) > 0
    
    def test_check_performance_issues(self, sql_executor, sample_semantic_metadata):
        """Test performance issue detection"""
        # SQL with performance issues
        problematic_sql = "SELECT * FROM customers JOIN orders JOIN products JOIN categories"
        warnings = sql_executor._check_performance_issues(problematic_sql, sample_semantic_metadata)
        
        assert len(warnings) > 0
        # Should warn about SELECT *, no WHERE, multiple joins
        assert any('SELECT *' in warning for warning in warnings)
        assert any('WHERE' in warning for warning in warnings)
    
    def test_suggest_indexes(self, sql_executor, sample_semantic_metadata):
        """Test index suggestions"""
        sql = "SELECT * FROM customers WHERE customers.email = 'test@example.com'"
        suggestions = sql_executor._suggest_indexes(sql, sample_semantic_metadata)
        
        if suggestions:
            assert any('email' in suggestion for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_validate_sql(self, sql_executor, sample_semantic_metadata):
        """Test SQL validation"""
        sql = "SELECT customers.email FROM customers WHERE customers.active = true"
        
        validation = await sql_executor.validate_sql(sql, sample_semantic_metadata)
        
        assert 'is_valid' in validation
        assert 'errors' in validation
        assert 'warnings' in validation
        assert 'suggestions' in validation
        assert isinstance(validation['is_valid'], bool)
    
    @pytest.mark.asyncio
    async def test_optimize_query(self, sql_executor, sample_semantic_metadata):
        """Test query optimization"""
        sql = "SELECT * FROM customers"
        
        optimization = await sql_executor.optimize_query(sql, sample_semantic_metadata)
        
        assert 'original_sql' in optimization
        assert 'optimized_sql' in optimization
        assert 'optimizations_applied' in optimization
        assert 'suggestions' in optimization
        
        # Should add LIMIT
        assert 'LIMIT' in optimization['optimized_sql'].upper()
        assert 'Added LIMIT clause' in optimization['optimizations_applied']


class TestExecutionResult:
    """Test cases for ExecutionResult dataclass"""
    
    def test_execution_result_success(self):
        """Test successful ExecutionResult creation"""
        result = ExecutionResult(
            success=True,
            data=[{'id': 1, 'name': 'test'}],
            column_names=['id', 'name'],
            row_count=1,
            execution_time_ms=100.5,
            sql_executed="SELECT * FROM test"
        )
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.row_count == 1
        assert result.execution_time_ms == 100.5
    
    def test_execution_result_failure(self):
        """Test failed ExecutionResult creation"""
        result = ExecutionResult(
            success=False,
            data=[],
            column_names=[],
            row_count=0,
            execution_time_ms=50.0,
            sql_executed="SELECT * FROM invalid_table",
            error_message="Table does not exist"
        )
        
        assert result.success is False
        assert result.error_message == "Table does not exist"
        assert len(result.data) == 0


class TestFallbackAttempt:
    """Test cases for FallbackAttempt dataclass"""
    
    def test_fallback_attempt_creation(self):
        """Test FallbackAttempt creation"""
        attempt = FallbackAttempt(
            attempt_number=1,
            strategy="simplify_query",
            sql_attempted="SELECT * FROM customers",
            success=True,
            execution_time_ms=75.0
        )
        
        assert attempt.attempt_number == 1
        assert attempt.strategy == "simplify_query"
        assert attempt.success is True
        assert attempt.execution_time_ms == 75.0


class TestExecutionPlan:
    """Test cases for ExecutionPlan dataclass"""
    
    def test_execution_plan_creation(self):
        """Test ExecutionPlan creation"""
        plan = ExecutionPlan(
            primary_sql="SELECT * FROM customers",
            fallback_strategies=["simplify_query", "add_limit"],
            timeout_seconds=30,
            max_rows=1000,
            validation_rules=["check_table_existence"]
        )
        
        assert plan.primary_sql == "SELECT * FROM customers"
        assert len(plan.fallback_strategies) == 2
        assert plan.timeout_seconds == 30
        assert plan.max_rows == 1000


@pytest.mark.asyncio
class TestSQLExecutorAsync:
    """Async test cases for SQLExecutor"""
    
    async def test_execute_sql_with_timeout_mock(self, sql_executor):
        """Test SQL execution with mocked database"""
        # Mock the connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [(1, 'test'), (2, 'test2')]
        
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        
        sql_executor.connection = mock_connection
        sql_executor.db_type = 'postgresql'
        
        result = await sql_executor._execute_sql_with_timeout("SELECT * FROM test", 30)
        
        assert result.success is True
        assert len(result.data) == 2
        assert result.column_names == ['id', 'name']
        assert result.row_count == 2
    
    async def test_execute_sql_with_timeout_error(self, sql_executor):
        """Test SQL execution with error"""
        # Mock the connection to raise an error
        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = Exception("Connection failed")
        
        sql_executor.connection = mock_connection
        
        result = await sql_executor._execute_sql_with_timeout("SELECT * FROM test", 30)
        
        assert result.success is False
        assert result.error_message == "Connection failed"
        assert len(result.data) == 0
    
    async def test_apply_fallback_strategy(self, sql_executor, sample_query_plan, sample_query_context, sample_semantic_metadata):
        """Test applying different fallback strategies"""
        original_sql = "SELECT * FROM customers WHERE complex_condition = true"
        
        # Test simplify_query strategy
        simplified = await sql_executor._apply_fallback_strategy(
            "simplify_query", original_sql, sample_query_plan, 
            sample_query_context, sample_semantic_metadata, "syntax error"
        )
        assert simplified is not None
        
        # Test add_limit strategy
        with_limit = await sql_executor._apply_fallback_strategy(
            "add_limit", original_sql, sample_query_plan,
            sample_query_context, sample_semantic_metadata, "no error"
        )
        assert with_limit is not None
        assert 'LIMIT' in with_limit.upper()
        
        # Test basic_select strategy
        basic = await sql_executor._apply_fallback_strategy(
            "basic_select", original_sql, sample_query_plan,
            sample_query_context, sample_semantic_metadata, "table error"
        )
        assert basic is not None
        assert 'SELECT' in basic.upper()
    
    async def test_unknown_fallback_strategy(self, sql_executor, sample_query_plan, sample_query_context, sample_semantic_metadata):
        """Test handling unknown fallback strategy"""
        result = await sql_executor._apply_fallback_strategy(
            "unknown_strategy", "SELECT * FROM test", sample_query_plan,
            sample_query_context, sample_semantic_metadata, "error"
        )
        
        assert result is None


@pytest.mark.asyncio
class TestSQLExecutorIntegration:
    """Integration tests for SQLExecutor"""
    
    async def test_full_execution_workflow_mock(self, sql_executor, sample_query_plan, sample_query_context, sample_semantic_metadata):
        """Test complete execution workflow with mocks"""
        # Mock successful execution
        async def mock_execute_sql(sql, timeout):
            return ExecutionResult(
                success=True,
                data=[{'id': 1, 'name': 'test'}],
                column_names=['id', 'name'],
                row_count=1,
                execution_time_ms=100.0,
                sql_executed=sql
            )
        
        sql_executor._execute_sql_with_timeout = mock_execute_sql
        
        result, attempts = await sql_executor.execute_query_with_fallbacks(
            sample_query_plan, sample_query_context, sample_semantic_metadata
        )
        
        assert result.success is True
        assert len(attempts) == 0  # No fallbacks needed
        assert result.row_count == 1
    
    async def test_full_execution_workflow_with_fallbacks(self, sql_executor, sample_query_plan, sample_query_context, sample_semantic_metadata):
        """Test execution workflow with fallbacks"""
        call_count = 0
        
        async def mock_execute_sql_with_failure(sql, timeout):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call fails
                return ExecutionResult(
                    success=False,
                    data=[],
                    column_names=[],
                    row_count=0,
                    execution_time_ms=50.0,
                    sql_executed=sql,
                    error_message="Syntax error"
                )
            else:
                # Fallback succeeds
                return ExecutionResult(
                    success=True,
                    data=[{'id': 1}],
                    column_names=['id'],
                    row_count=1,
                    execution_time_ms=75.0,
                    sql_executed=sql
                )
        
        sql_executor._execute_sql_with_timeout = mock_execute_sql_with_failure
        
        result, attempts = await sql_executor.execute_query_with_fallbacks(
            sample_query_plan, sample_query_context, sample_semantic_metadata
        )
        
        assert result.success is True  # Should succeed with fallback
        assert len(attempts) > 0  # Should have fallback attempts
        assert attempts[0].strategy == "primary"
        assert attempts[0].success is False


if __name__ == '__main__':
    pytest.main([__file__])