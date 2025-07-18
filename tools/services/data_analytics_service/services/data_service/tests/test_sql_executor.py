#!/usr/bin/env python3
"""
Test suite for SQL Executor - Step 5 of data analytics pipeline
Tests SQL execution with fallback mechanisms and real data scenarios
"""

import asyncio
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

from tools.services.data_analytics_service.services.data_service.sql_executor import (
    SQLExecutor, ExecutionResult, FallbackAttempt, ExecutionPlan
)
from tools.services.data_analytics_service.services.data_service.sql_generator import (
    SQLGenerationResult
)
from tools.services.data_analytics_service.services.data_service.query_matcher import (
    QueryContext, MetadataMatch, QueryPlan
)
from tools.services.data_analytics_service.services.data_service.semantic_enricher import (
    SemanticMetadata
)

class TestSQLExecutor:
    """Test suite for SQL Executor with real data scenarios and fallback mechanisms"""
    
    @pytest.fixture
    def database_config(self):
        """Create test database configuration"""
        return {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass',
            'max_execution_time': 30,
            'max_rows': 10000
        }
    
    @pytest.fixture
    def sample_semantic_metadata(self):
        """Create sample semantic metadata for testing"""
        return SemanticMetadata(
            original_metadata={
                'tables': [
                    {
                        'table_name': 'ecommerce_sales',
                        'table_comment': 'E-commerce sales transaction data',
                        'record_count': 5000
                    },
                    {
                        'table_name': 'customers',
                        'table_comment': 'Customer information',
                        'record_count': 1200
                    },
                    {
                        'table_name': 'products',
                        'table_comment': 'Product catalog',
                        'record_count': 800
                    }
                ],
                'columns': [
                    {
                        'table_name': 'ecommerce_sales',
                        'column_name': 'transaction_id',
                        'data_type': 'VARCHAR',
                        'column_comment': 'Unique transaction identifier'
                    },
                    {
                        'table_name': 'ecommerce_sales',
                        'column_name': 'customer_id',
                        'data_type': 'INTEGER',
                        'column_comment': 'Customer identifier'
                    },
                    {
                        'table_name': 'ecommerce_sales',
                        'column_name': 'total_amount',
                        'data_type': 'DECIMAL',
                        'column_comment': 'Total transaction amount'
                    },
                    {
                        'table_name': 'customers',
                        'column_name': 'customer_id',
                        'data_type': 'INTEGER',
                        'column_comment': 'Unique customer identifier'
                    },
                    {
                        'table_name': 'customers',
                        'column_name': 'customer_name',
                        'data_type': 'VARCHAR',
                        'column_comment': 'Customer full name'
                    }
                ],
                'relationships': [
                    {
                        'from_table': 'ecommerce_sales',
                        'from_column': 'customer_id',
                        'to_table': 'customers',
                        'to_column': 'customer_id'
                    }
                ]
            },
            business_entities=[],
            semantic_tags=['ecommerce', 'sales'],
            domain_classification={'primary_domain': 'ecommerce'},
            ai_analysis_summary="E-commerce sales data",
            confidence_score=0.85
        )
    
    @pytest.fixture
    def sample_query_plan(self):
        """Create sample query plan for testing"""
        return QueryPlan(
            primary_tables=['ecommerce_sales', 'customers'],
            required_joins=[{
                'type': 'inner',
                'left_table': 'ecommerce_sales',
                'right_table': 'customers',
                'left_column': 'customer_id',
                'right_column': 'customer_id',
                'confidence': 0.9
            }],
            select_columns=['customers.customer_name', 'ecommerce_sales.total_amount'],
            where_conditions=['ecommerce_sales.total_amount > 100'],
            aggregations=['SUM(ecommerce_sales.total_amount)'],
            order_by=['ecommerce_sales.total_amount DESC'],
            confidence_score=0.8,
            alternative_plans=[]
        )
    
    @pytest.fixture
    def sample_sql_generation_result(self):
        """Create sample SQL generation result"""
        return SQLGenerationResult(
            sql="SELECT c.customer_name, SUM(e.total_amount) as total_sales FROM ecommerce_sales e JOIN customers c ON e.customer_id = c.customer_id WHERE e.total_amount > 100 GROUP BY c.customer_name ORDER BY total_sales DESC LIMIT 1000;",
            explanation="Shows customers with their total sales over 100",
            confidence_score=0.9,
            complexity_level="medium",
            estimated_rows="500-1000"
        )
    
    @pytest.fixture
    def mock_database_connection(self):
        """Create mock database connection"""
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Mock successful query execution
        mock_cursor.description = [
            ('customer_name', 'VARCHAR'),
            ('total_sales', 'DECIMAL')
        ]
        mock_cursor.fetchall.return_value = [
            {'customer_name': 'John Doe', 'total_sales': 1500.00},
            {'customer_name': 'Jane Smith', 'total_sales': 1200.00},
            {'customer_name': 'Bob Johnson', 'total_sales': 800.00}
        ]
        
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn
    
    @pytest.fixture
    def sql_executor(self, database_config):
        """Create SQL executor instance"""
        return SQLExecutor(database_config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, sql_executor):
        """Test SQL executor initialization"""
        assert sql_executor.db_type == 'postgresql'
        assert sql_executor.max_execution_time == 30
        assert sql_executor.max_rows == 10000
        assert len(sql_executor.fallback_strategies) > 0
        assert sql_executor.execution_history == []
    
    @pytest.mark.asyncio
    async def test_successful_sql_execution(self, sql_executor, sample_sql_generation_result, mock_database_connection):
        """Test successful SQL execution"""
        
        # Mock database connection
        with patch.object(sql_executor, '_ensure_connection') as mock_ensure:
            sql_executor.connection = mock_database_connection
            
            result, fallback_attempts = await sql_executor.execute_sql_with_fallbacks(
                sample_sql_generation_result,
                "Show customers with high sales"
            )
            
            assert isinstance(result, ExecutionResult)
            assert result.success is True
            assert len(result.data) == 3
            assert result.row_count == 3
            assert len(result.column_names) == 2
            assert result.execution_time_ms >= 0
            assert len(fallback_attempts) == 0  # No fallbacks needed
    
    @pytest.mark.asyncio
    async def test_sql_execution_with_fallbacks(self, sql_executor, sample_sql_generation_result):
        """Test SQL execution with fallback mechanisms"""
        
        # Mock database connection that fails initially
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # First execution fails
        mock_cursor.execute.side_effect = [
            Exception("Table 'ecommerce_sales' doesn't exist"),  # Primary fails
            Exception("Timeout"),  # Extended timeout fails
            None  # Limited query succeeds
        ]
        
        # Setup successful fallback response
        mock_cursor.description = [('customer_name', 'VARCHAR')]
        mock_cursor.fetchall.return_value = [{'customer_name': 'John Doe'}]
        mock_conn.cursor.return_value = mock_cursor
        
        with patch.object(sql_executor, '_ensure_connection'):
            sql_executor.connection = mock_conn
            
            result, fallback_attempts = await sql_executor.execute_sql_with_fallbacks(
                sample_sql_generation_result,
                "Show customers with high sales"
            )
            
            # Should have attempted fallbacks
            assert len(fallback_attempts) >= 1
            
            # Should eventually succeed or provide meaningful error
            assert isinstance(result, ExecutionResult)
    
    @pytest.mark.asyncio
    async def test_execute_sql_directly(self, sql_executor, mock_database_connection):
        """Test direct SQL execution without fallbacks"""
        
        simple_sql = "SELECT * FROM customers LIMIT 10;"
        
        with patch.object(sql_executor, '_ensure_connection'):
            sql_executor.connection = mock_database_connection
            
            result = await sql_executor.execute_sql_directly(simple_sql)
            
            assert isinstance(result, ExecutionResult)
            assert result.sql_executed == simple_sql
            assert result.success is True
            assert len(result.data) == 3
    
    @pytest.mark.asyncio
    async def test_query_plan_execution(self, sql_executor, sample_query_plan, sample_semantic_metadata):
        """Test query plan execution with fallbacks"""
        
        query_context = QueryContext(
            entities_mentioned=['customers', 'sales'],
            attributes_mentioned=['name', 'amount'],
            operations=['select', 'join'],
            filters=[],
            aggregations=['sum'],
            temporal_references=[],
            business_intent='reporting',
            confidence_score=0.8
        )
        
        # Mock successful execution
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [('customer_name', 'VARCHAR'), ('total_sales', 'DECIMAL')]
        mock_cursor.fetchall.return_value = [
            {'customer_name': 'John Doe', 'total_sales': 1500.00}
        ]
        mock_conn.cursor.return_value = mock_cursor
        
        with patch.object(sql_executor, '_ensure_connection'):
            sql_executor.connection = mock_conn
            
            result, fallback_attempts = await sql_executor.execute_query_plan_with_fallbacks(
                sample_query_plan, query_context, sample_semantic_metadata
            )
            
            assert isinstance(result, ExecutionResult)
            assert result.success is True
            assert len(result.data) == 1
    
    @pytest.mark.asyncio
    async def test_sql_validation(self, sql_executor, sample_semantic_metadata):
        """Test SQL validation against metadata"""
        
        # Test valid SQL
        valid_sql = "SELECT customer_name FROM customers WHERE customer_id = 1"
        validation_result = await sql_executor.validate_sql(valid_sql, sample_semantic_metadata)
        
        assert validation_result['is_valid'] is True
        assert len(validation_result['errors']) == 0
        
        # Test invalid SQL
        invalid_sql = "SELECT * FROM nonexistent_table"
        validation_result = await sql_executor.validate_sql(invalid_sql, sample_semantic_metadata)
        
        assert validation_result['is_valid'] is False
        assert len(validation_result['errors']) > 0
    
    @pytest.mark.asyncio
    async def test_query_optimization(self, sql_executor, sample_semantic_metadata):
        """Test query optimization suggestions"""
        
        unoptimized_sql = "SELECT * FROM ecommerce_sales WHERE total_amount > 0"
        
        optimization_result = await sql_executor.optimize_query(unoptimized_sql, sample_semantic_metadata)
        
        assert isinstance(optimization_result, dict)
        assert 'original_sql' in optimization_result
        assert 'optimized_sql' in optimization_result
        assert 'optimizations_applied' in optimization_result
        assert 'suggestions' in optimization_result
        
        # Should suggest adding LIMIT
        assert 'LIMIT' in optimization_result['optimized_sql'].upper()
    
    @pytest.mark.asyncio
    async def test_explain_query_plan(self, sql_executor):
        """Test query execution plan explanation"""
        
        test_sql = "SELECT * FROM customers WHERE customer_id = 1"
        
        # Mock database connection for EXPLAIN
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {'QUERY PLAN': [{'Plan': {'Node Type': 'Seq Scan', 'Total Cost': 1.0}}]}
        ]
        mock_conn.cursor.return_value = mock_cursor
        
        with patch.object(sql_executor, '_ensure_connection'):
            sql_executor.connection = mock_conn
            
            plan_result = await sql_executor.explain_query_plan(test_sql)
            
            assert isinstance(plan_result, dict)
            assert 'plan' in plan_result
    
    @pytest.mark.asyncio
    async def test_execution_statistics(self, sql_executor):
        """Test execution statistics collection"""
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            ('PostgreSQL 13.0',),  # Version
            ('test_db',)  # Database name
        ]
        mock_conn.cursor.return_value = mock_cursor
        
        with patch.object(sql_executor, '_ensure_connection'):
            sql_executor.connection = mock_conn
            
            stats = await sql_executor.get_execution_statistics()
            
            assert isinstance(stats, dict)
            assert 'database_type' in stats
            assert stats['database_type'] == 'postgresql'
            assert 'connection_status' in stats
            assert 'database_info' in stats
    
    @pytest.mark.asyncio
    async def test_fallback_strategies(self, sql_executor, sample_query_plan, sample_semantic_metadata):
        """Test individual fallback strategies"""
        
        query_context = QueryContext(
            entities_mentioned=['customers'],
            attributes_mentioned=['name'],
            operations=['select'],
            filters=[], aggregations=[], temporal_references=[],
            business_intent='lookup', confidence_score=0.6
        )
        
        # Test simplify query
        complex_sql = "SELECT * FROM (SELECT customer_id FROM customers) c WHERE c.customer_id IN (SELECT customer_id FROM orders)"
        simplified_sql = sql_executor._simplify_query(complex_sql, sample_query_plan)
        assert simplified_sql != complex_sql
        assert len(simplified_sql) <= len(complex_sql)
        
        # Test remove joins
        join_sql = "SELECT * FROM customers c JOIN orders o ON c.customer_id = o.customer_id"
        no_join_sql = sql_executor._remove_complex_joins(join_sql, sample_query_plan)
        assert 'JOIN' not in no_join_sql.upper()
        
        # Test add limit
        no_limit_sql = "SELECT * FROM customers"
        limited_sql = sql_executor._add_limit_clause(no_limit_sql)
        assert 'LIMIT' in limited_sql.upper()
        
        # Test alternative tables
        alt_table_sql = await sql_executor._try_alternative_tables(sample_query_plan, sample_semantic_metadata)
        assert alt_table_sql is not None
        assert 'FROM' in alt_table_sql.upper()
        
        # Test alternative columns
        alt_col_sql = sql_executor._try_alternative_columns(
            "SELECT * FROM customers", sample_query_plan, sample_semantic_metadata
        )
        assert alt_col_sql is not None
        assert 'customers' in alt_col_sql.lower()
        
        # Test syntax correction
        syntax_error_sql = "SELECT * FROM customers WHERE"
        corrected_sql = sql_executor._correct_syntax_errors(
            syntax_error_sql, "syntax error near WHERE"
        )
        assert corrected_sql is not None
        
        # Test basic select generation
        basic_sql = sql_executor._generate_basic_select(sample_query_plan)
        assert basic_sql is not None
        assert 'SELECT' in basic_sql.upper()
    
    @pytest.mark.asyncio
    async def test_sql_generation_from_plan(self, sql_executor, sample_query_plan):
        """Test SQL generation from query plan"""
        
        generated_sql = sql_executor._generate_sql_from_plan(sample_query_plan)
        
        assert isinstance(generated_sql, str)
        assert 'SELECT' in generated_sql.upper()
        assert 'FROM' in generated_sql.upper()
        assert 'customers' in generated_sql.lower()
        assert 'ecommerce_sales' in generated_sql.lower()
        assert 'JOIN' in generated_sql.upper()
        assert 'LIMIT' in generated_sql.upper()
    
    @pytest.mark.asyncio
    async def test_execution_feedback_and_learning(self, sql_executor):
        """Test execution feedback recording and learning"""
        
        # Create sample execution results
        sql_result = SQLGenerationResult(
            sql="SELECT * FROM customers",
            explanation="Simple customer query",
            confidence_score=0.8,
            complexity_level="simple"
        )
        
        execution_result = ExecutionResult(
            success=True,
            data=[{'customer_name': 'John Doe'}],
            column_names=['customer_name'],
            row_count=1,
            execution_time_ms=50.0,
            sql_executed="SELECT * FROM customers"
        )
        
        # Record feedback
        await sql_executor._record_execution_feedback(
            "show customers", sql_result, execution_result, "success", ""
        )
        
        assert len(sql_executor.execution_history) == 1
        assert sql_executor.execution_history[0]['feedback_type'] == 'success'
        
        # Test user feedback learning
        await sql_executor.learn_from_user_feedback(
            "show customers",
            "SELECT * FROM customers",
            "SELECT customer_name FROM customers LIMIT 10",
            "satisfied"
        )
        
        assert len(sql_executor.execution_history) == 2
        assert sql_executor.execution_history[1]['learning_type'] == 'user_correction'
    
    @pytest.mark.asyncio
    async def test_execution_insights(self, sql_executor):
        """Test execution insights generation"""
        
        # Add some execution history
        sql_executor.execution_history = [
            {
                'execution_success': True,
                'llm_confidence': 0.9,
                'execution_time_ms': 100.0,
                'error_message': None
            },
            {
                'execution_success': False,
                'llm_confidence': 0.6,
                'execution_time_ms': 200.0,
                'error_message': 'Table not found'
            },
            {
                'execution_success': True,
                'llm_confidence': 0.8,
                'execution_time_ms': 150.0,
                'error_message': None
            }
        ]
        
        insights = await sql_executor.get_execution_insights()
        
        assert isinstance(insights, dict)
        assert 'total_executions' in insights
        assert insights['total_executions'] == 3
        assert 'success_rate' in insights
        assert insights['success_rate'] == 2/3
        assert 'common_failures' in insights
        assert 'confidence_success_correlation' in insights
        assert 'avg_execution_time' in insights
        assert 'recent_trend' in insights
    
    @pytest.mark.asyncio
    async def test_database_connection_types(self, database_config):
        """Test different database connection types"""
        
        # Test PostgreSQL
        pg_config = database_config.copy()
        pg_config['type'] = 'postgresql'
        pg_executor = SQLExecutor(pg_config)
        assert pg_executor.db_type == 'postgresql'
        
        # Test MySQL
        mysql_config = database_config.copy()
        mysql_config['type'] = 'mysql'
        mysql_executor = SQLExecutor(mysql_config)
        assert mysql_executor.db_type == 'mysql'
        
        # Test SQL Server
        sqlserver_config = database_config.copy()
        sqlserver_config['type'] = 'sqlserver'
        sqlserver_executor = SQLExecutor(sqlserver_config)
        assert sqlserver_executor.db_type == 'sqlserver'
    
    @pytest.mark.asyncio
    async def test_sql_component_parsing(self, sql_executor):
        """Test SQL component parsing"""
        
        complex_sql = """
        SELECT c.customer_name, o.order_date, SUM(o.total_amount) 
        FROM customers c 
        JOIN orders o ON c.customer_id = o.customer_id 
        WHERE o.order_date > '2023-01-01' 
        GROUP BY c.customer_name, o.order_date 
        ORDER BY SUM(o.total_amount) DESC
        """
        
        components = sql_executor._parse_sql_components(complex_sql)
        
        assert 'tables' in components
        assert 'columns' in components
        assert 'joins' in components
        
        # Should identify tables
        assert len(components['tables']) >= 2
        assert any('customers' in table for table in components['tables'])
        assert any('orders' in table for table in components['tables'])
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, sql_executor):
        """Test comprehensive error handling and recovery"""
        
        # Test with completely invalid SQL
        invalid_sql_result = SQLGenerationResult(
            sql="INVALID SQL SYNTAX",
            explanation="Invalid test",
            confidence_score=0.1,
            complexity_level="simple"
        )
        
        # Should handle gracefully
        result, fallback_attempts = await sql_executor.execute_sql_with_fallbacks(
            invalid_sql_result,
            "invalid query"
        )
        
        assert isinstance(result, ExecutionResult)
        assert result.success is False
        assert len(fallback_attempts) > 0
        assert result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_performance_warnings_and_suggestions(self, sql_executor, sample_semantic_metadata):
        """Test performance warnings and suggestions"""
        
        # Test performance issue detection
        performance_issues = [
            "SELECT * FROM large_table",  # SELECT *
            "SELECT name FROM customers",  # No WHERE clause
            "SELECT * FROM a JOIN b ON a.id = b.id JOIN c ON b.id = c.id JOIN d ON c.id = d.id"  # Many joins
        ]
        
        for sql in performance_issues:
            warnings = sql_executor._check_performance_issues(sql, sample_semantic_metadata)
            assert len(warnings) > 0
        
        # Test index suggestions
        sql_with_where = "SELECT * FROM customers WHERE customer_id = 1 AND email = 'test@example.com'"
        suggestions = sql_executor._suggest_indexes(sql_with_where, sample_semantic_metadata)
        assert len(suggestions) > 0
        assert any('index' in suggestion.lower() for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_safety(self, sql_executor):
        """Test concurrent execution safety"""
        
        # Test that multiple executions don't interfere
        sql_results = [
            SQLGenerationResult(
                sql="SELECT * FROM customers LIMIT 5",
                explanation="Test query 1",
                confidence_score=0.8,
                complexity_level="simple"
            ),
            SQLGenerationResult(
                sql="SELECT * FROM products LIMIT 5",
                explanation="Test query 2",
                confidence_score=0.8,
                complexity_level="simple"
            )
        ]
        
        # Mock database connections
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [('id', 'INTEGER')]
        mock_cursor.fetchall.return_value = [{'id': 1}]
        mock_conn.cursor.return_value = mock_cursor
        
        with patch.object(sql_executor, '_ensure_connection'):
            sql_executor.connection = mock_conn
            
            # Execute concurrently
            tasks = [
                sql_executor.execute_sql_with_fallbacks(sql_result, f"query {i}")
                for i, sql_result in enumerate(sql_results)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Both should complete successfully
            assert len(results) == 2
            for result in results:
                assert not isinstance(result, Exception)
                execution_result, fallback_attempts = result
                assert isinstance(execution_result, ExecutionResult)


class TestSQLExecutorIntegration:
    """Integration tests with real data scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_ecommerce_execution_flow(self):
        """Test complete ecommerce execution flow"""
        
        # Create realistic ecommerce scenario
        database_config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'ecommerce_db',
            'username': 'test_user',
            'password': 'test_pass',
            'max_execution_time': 30,
            'max_rows': 10000
        }
        
        executor = SQLExecutor(database_config)
        
        # Create realistic SQL generation result
        sql_result = SQLGenerationResult(
            sql="SELECT c.customer_name, COUNT(o.order_id) as order_count, SUM(o.total_amount) as total_spent FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_name ORDER BY total_spent DESC LIMIT 50;",
            explanation="Top customers by total spending with order counts",
            confidence_score=0.92,
            complexity_level="medium",
            estimated_rows="50"
        )
        
        # Mock successful execution
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [
            ('customer_name', 'VARCHAR'),
            ('order_count', 'INTEGER'),
            ('total_spent', 'DECIMAL')
        ]
        mock_cursor.fetchall.return_value = [
            {'customer_name': 'John Doe', 'order_count': 5, 'total_spent': 1250.00},
            {'customer_name': 'Jane Smith', 'order_count': 3, 'total_spent': 890.00},
            {'customer_name': 'Bob Johnson', 'order_count': 7, 'total_spent': 2100.00}
        ]
        mock_conn.cursor.return_value = mock_cursor
        
        with patch.object(executor, '_ensure_connection'):
            executor.connection = mock_conn
            
            result, fallback_attempts = await executor.execute_sql_with_fallbacks(
                sql_result,
                "Find top customers by spending"
            )
            
            # Verify comprehensive execution
            assert isinstance(result, ExecutionResult)
            assert result.success is True
            assert len(result.data) == 3
            assert result.row_count == 3
            assert len(result.column_names) == 3
            assert result.execution_time_ms >= 0
            assert len(fallback_attempts) == 0
            
            # Verify data integrity
            assert all('customer_name' in row for row in result.data)
            assert all('order_count' in row for row in result.data)
            assert all('total_spent' in row for row in result.data)
    
    @pytest.mark.asyncio
    async def test_customs_data_execution_scenario(self):
        """Test customs data execution with Chinese context"""
        
        database_config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'customs_db',
            'username': 'test_user',
            'password': 'test_pass',
            'max_execution_time': 60,
            'max_rows': 5000
        }
        
        executor = SQLExecutor(database_config)
        
        # Create customs SQL generation result
        sql_result = SQLGenerationResult(
            sql="SELECT c.company_name, COUNT(d.declaration_id) as declaration_count, SUM(d.rmb_amount) as total_value FROM companies c JOIN declarations d ON c.company_code = d.company_code WHERE d.rmb_amount > 1000000 GROUP BY c.company_name ORDER BY total_value DESC LIMIT 100;",
            explanation="åâ3¥Ñ…Ç100„ß¡",
            confidence_score=0.88,
            complexity_level="medium",
            estimated_rows="100"
        )
        
        # Mock customs data response
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [
            ('company_name', 'VARCHAR'),
            ('declaration_count', 'INTEGER'),
            ('total_value', 'DECIMAL')
        ]
        mock_cursor.fetchall.return_value = [
            {'company_name': '
w8	Plø', 'declaration_count': 12, 'total_value': 5800000.00},
            {'company_name': '¬Ûúãlø', 'declaration_count': 8, 'total_value': 3200000.00},
            {'company_name': 'ñ3ýE8', 'declaration_count': 15, 'total_value': 7500000.00}
        ]
        mock_conn.cursor.return_value = mock_cursor
        
        with patch.object(executor, '_ensure_connection'):
            executor.connection = mock_conn
            
            result, fallback_attempts = await executor.execute_sql_with_fallbacks(
                sql_result,
                "åâØÑ3¥"
            )
            
            # Verify customs data execution
            assert isinstance(result, ExecutionResult)
            assert result.success is True
            assert len(result.data) == 3
            assert all('company_name' in row for row in result.data)
            assert all('declaration_count' in row for row in result.data)
            assert all('total_value' in row for row in result.data)
            
            # Verify Chinese company names are preserved
            assert any('
w' in str(row['company_name']) for row in result.data)
            assert any('¬' in str(row['company_name']) for row in result.data)
            assert any('ñ3' in str(row['company_name']) for row in result.data)
    
    @pytest.mark.asyncio
    async def test_comprehensive_fallback_scenario(self):
        """Test comprehensive fallback scenario with multiple failures"""
        
        database_config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass',
            'max_execution_time': 30,
            'max_rows': 10000
        }
        
        executor = SQLExecutor(database_config)
        
        # Create complex SQL that will fail
        complex_sql_result = SQLGenerationResult(
            sql="SELECT * FROM (SELECT customer_id, SUM(amount) OVER (PARTITION BY customer_id ORDER BY date ROWS UNBOUNDED PRECEDING) as running_total FROM transactions WHERE date > '2023-01-01') t WHERE running_total > 10000;",
            explanation="Complex window function query",
            confidence_score=0.7,
            complexity_level="complex",
            estimated_rows="unknown"
        )
        
        # Mock multiple failure scenarios
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Simulate multiple failures followed by success
        failure_responses = [
            Exception("syntax error at or near 'WINDOW'"),  # Primary fails
            Exception("timeout"),  # Extended timeout fails
            None  # Limited query succeeds
        ]
        
        mock_cursor.execute.side_effect = failure_responses
        mock_cursor.description = [('customer_id', 'INTEGER'), ('amount', 'DECIMAL')]
        mock_cursor.fetchall.return_value = [
            {'customer_id': 1, 'amount': 500.00},
            {'customer_id': 2, 'amount': 750.00}
        ]
        mock_conn.cursor.return_value = mock_cursor
        
        with patch.object(executor, '_ensure_connection'):
            executor.connection = mock_conn
            
            result, fallback_attempts = await executor.execute_sql_with_fallbacks(
                complex_sql_result,
                "Complex analytical query"
            )
            
            # Should attempt multiple fallbacks
            assert len(fallback_attempts) >= 2
            
            # Should track all attempts
            assert all(isinstance(attempt, FallbackAttempt) for attempt in fallback_attempts)
            assert all(attempt.strategy is not None for attempt in fallback_attempts)
            assert all(attempt.sql_attempted is not None for attempt in fallback_attempts)
            
            # Final result should be meaningful
            assert isinstance(result, ExecutionResult)
            
            # Should have learned from the experience
            assert len(executor.execution_history) > 0


# Test runner
if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])