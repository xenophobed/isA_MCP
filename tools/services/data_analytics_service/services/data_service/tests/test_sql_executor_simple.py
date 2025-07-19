#!/usr/bin/env python3
"""
Simple test suite for SQL Executor service
Tests basic SQL execution functionality with SQLite
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, List, Any

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

from tools.services.data_analytics_service.services.data_service.sql_executor import (
    SQLExecutor, ExecutionResult, SQLGenerationResult
)

class TestSQLExecutorSimple:
    """Simple test suite for SQL Executor"""
    
    @pytest.fixture
    def sqlite_executor(self):
        """Create SQLite executor for testing"""
        config = {
            'type': 'sqlite',
            'database': ':memory:',  # In-memory SQLite for testing
            'max_execution_time': 30,
            'max_rows': 1000
        }
        return SQLExecutor(config)
    
    @pytest.fixture
    def sample_sql_result(self):
        """Create sample SQL generation result"""
        return SQLGenerationResult(
            sql="SELECT * FROM customers LIMIT 10",
            explanation="Simple customer query",
            confidence_score=0.9,
            complexity_level="simple",
            estimated_rows="10"
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, sqlite_executor):
        """Test SQL executor initialization"""
        assert sqlite_executor.db_type == 'sqlite'
        assert sqlite_executor.max_execution_time == 30
        assert sqlite_executor.max_rows == 1000
        assert len(sqlite_executor.fallback_strategies) > 0
    
    @pytest.mark.asyncio
    async def test_direct_sql_execution(self, sqlite_executor):
        """Test direct SQL execution"""
        # Mock database connection
        with patch.object(sqlite_executor, '_ensure_connection'):
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Mock successful execution
            mock_cursor.description = [('id', 'INTEGER')]
            mock_cursor.fetchall.return_value = [{'id': 1}]
            mock_conn.cursor.return_value = mock_cursor
            sqlite_executor.connection = mock_conn
            
            result = await sqlite_executor.execute_sql_directly("SELECT 1 as id")
            
            assert isinstance(result, ExecutionResult)
            assert result.success is True
            assert len(result.data) == 1
            assert result.data[0]['id'] == 1
    
    @pytest.mark.asyncio
    async def test_sql_execution_with_fallbacks(self, sqlite_executor, sample_sql_result):
        """Test SQL execution with fallback mechanisms"""
        with patch.object(sqlite_executor, '_ensure_connection'):
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Mock successful execution
            mock_cursor.description = [('customer_name', 'VARCHAR')]
            mock_cursor.fetchall.return_value = [{'customer_name': 'John Doe'}]
            mock_conn.cursor.return_value = mock_cursor
            sqlite_executor.connection = mock_conn
            
            result, fallback_attempts = await sqlite_executor.execute_sql_with_fallbacks(
                sample_sql_result,
                "Show customers"
            )
            
            assert isinstance(result, ExecutionResult)
            assert result.success is True
            assert len(fallback_attempts) == 0  # No fallbacks needed
    
    @pytest.mark.asyncio
    async def test_sqlite_executor_creation(self):
        """Test SQLite executor creation helper"""
        executor = SQLExecutor.create_sqlite_executor("test.db", "user123")
        
        assert executor.db_type == 'sqlite'
        assert 'test.db' in executor.database_config['database']
        assert executor.max_execution_time == 30
    
    @pytest.mark.asyncio
    async def test_error_handling(self, sqlite_executor, sample_sql_result):
        """Test error handling in SQL execution"""
        with patch.object(sqlite_executor, '_ensure_connection'):
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Mock execution failure
            mock_cursor.execute.side_effect = Exception("Table does not exist")
            mock_conn.cursor.return_value = mock_cursor
            sqlite_executor.connection = mock_conn
            
            result, fallback_attempts = await sqlite_executor.execute_sql_with_fallbacks(
                sample_sql_result,
                "Show customers"
            )
            
            # Should attempt fallbacks
            assert len(fallback_attempts) > 0
            assert isinstance(result, ExecutionResult)


# Test runner
if __name__ == '__main__':
    pytest.main([__file__, '-v'])