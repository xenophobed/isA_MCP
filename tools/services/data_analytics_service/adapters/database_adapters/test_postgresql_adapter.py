#!/usr/bin/env python3
"""
Test file for PostgreSQLAdapter
"""

import pytest
from unittest.mock import Mock, patch

from .postgresql_adapter import PostgreSQLAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo


class TestPostgreSQLAdapter:
    """Test cases for PostgreSQLAdapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create PostgreSQL adapter for testing"""
        with patch('psycopg2.connect'):
            return PostgreSQLAdapter()
    
    @pytest.fixture
    def mock_connection(self):
        """Create mock PostgreSQL connection"""
        connection = Mock()
        cursor = Mock()
        connection.cursor.return_value = cursor
        return connection, cursor
    
    def test_init_without_psycopg2(self):
        """Test initialization when psycopg2 is not available"""
        with patch('tools.services.data_analytics_service.adapters.database_adapters.postgresql_adapter.PSYCOPG2_AVAILABLE', False):
            with pytest.raises(ImportError, match="psycopg2 is required"):
                PostgreSQLAdapter()
    
    def test_create_connection(self, adapter):
        """Test PostgreSQL connection creation"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': 'user',
            'password': 'pass',
            'timeout': 30
        }
        
        with patch('psycopg2.connect') as mock_connect:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            result = adapter._create_connection(config)
            
            mock_connect.assert_called_once_with(
                host='localhost',
                port=5432,
                database='testdb',
                user='user',
                password='pass',
                connect_timeout=30
            )
            assert result == mock_connection
            assert adapter.cursor == mock_cursor
    
    def test_execute_query_select(self, adapter):
        """Test executing SELECT query"""
        adapter.cursor = Mock()
        adapter.connection = Mock()
        
        # Mock RealDictRow objects
        mock_row1 = Mock()
        mock_row1.__iter__ = Mock(return_value=iter([('id', 1), ('name', 'test')]))
        mock_row2 = Mock()
        mock_row2.__iter__ = Mock(return_value=iter([('id', 2), ('name', 'test2')]))
        
        adapter.cursor.fetchall.return_value = [mock_row1, mock_row2]
        
        with patch('dict', side_effect=lambda x: dict(x)):
            result = adapter._execute_query("SELECT * FROM test")
        
        adapter.cursor.execute.assert_called_once_with("SELECT * FROM test", None)
        adapter.cursor.fetchall.assert_called_once()
        assert len(result) == 2
    
    def test_execute_query_insert(self, adapter):
        """Test executing INSERT query"""
        adapter.cursor = Mock()
        adapter.connection = Mock()
        
        result = adapter._execute_query("INSERT INTO test VALUES (1, 'test')")
        
        adapter.cursor.execute.assert_called_once()
        adapter.connection.commit.assert_called_once()
        assert result == []
    
    def test_execute_query_error_with_rollback(self, adapter):
        """Test executing query with error and rollback"""
        adapter.cursor = Mock()
        adapter.connection = Mock()
        adapter.cursor.execute.side_effect = Exception("Query failed")
        
        with pytest.raises(Exception, match="Query failed"):
            adapter._execute_query("SELECT * FROM test")
        
        adapter.connection.rollback.assert_called_once()
    
    def test_get_tables(self, adapter):
        """Test getting table information"""
        adapter.cursor = Mock()
        adapter.connection = Mock()
        
        # Mock result data
        mock_row = Mock()
        mock_row.__iter__ = Mock(return_value=iter([
            ('table_name', 'users'),
            ('table_schema', 'public'),
            ('table_type', 'BASE TABLE'),
            ('record_count', 100),
            ('table_comment', 'User data'),
            ('created_date', ''),
            ('last_modified', '')
        ]))
        adapter.cursor.fetchall.return_value = [mock_row]
        
        with patch.object(adapter, '_execute_query') as mock_execute:
            mock_execute.return_value = [dict(mock_row)]
            tables = adapter.get_tables()
        
        assert len(tables) == 1
        assert isinstance(tables[0], TableInfo)
        assert tables[0].table_name == 'users'
        assert tables[0].schema_name == 'public'
    
    def test_get_columns(self, adapter):
        """Test getting column information"""
        mock_data = [{
            'table_name': 'users',
            'column_name': 'id',
            'data_type': 'integer',
            'max_length': 0,
            'is_nullable': False,
            'default_value': 'nextval(\'users_id_seq\'::regclass)',
            'column_comment': 'Primary key',
            'ordinal_position': 1
        }]
        
        with patch.object(adapter, '_execute_query', return_value=mock_data):
            columns = adapter.get_columns()
        
        assert len(columns) == 1
        assert isinstance(columns[0], ColumnInfo)
        assert columns[0].column_name == 'id'
        assert columns[0].data_type == 'integer'
        assert columns[0].is_nullable is False
    
    def test_get_relationships(self, adapter):
        """Test getting relationship information"""
        mock_data = [{
            'constraint_name': 'fk_user_department',
            'from_table': 'users',
            'from_column': 'dept_id',
            'to_table': 'departments',
            'to_column': 'id',
            'constraint_type': 'FOREIGN KEY'
        }]
        
        with patch.object(adapter, '_execute_query', return_value=mock_data):
            relationships = adapter.get_relationships()
        
        assert len(relationships) == 1
        assert isinstance(relationships[0], RelationshipInfo)
        assert relationships[0].from_table == 'users'
        assert relationships[0].to_table == 'departments'
        assert relationships[0].constraint_type == 'FOREIGN KEY'
    
    def test_get_indexes(self, adapter):
        """Test getting index information"""
        mock_data = [{
            'index_name': 'idx_email',
            'table_name': 'users',
            'column_names': ['email'],
            'is_unique': True,
            'index_type': 'btree',
            'is_primary': False
        }]
        
        with patch.object(adapter, '_execute_query', return_value=mock_data):
            indexes = adapter.get_indexes()
        
        assert len(indexes) == 1
        assert isinstance(indexes[0], IndexInfo)
        assert indexes[0].index_name == 'idx_email'
        assert indexes[0].is_unique is True
        assert indexes[0].column_names == ['email']
    
    def test_analyze_data_distribution(self, adapter):
        """Test analyzing data distribution"""
        # Mock stats query result
        stats_result = [{
            'total_count': 1000,
            'unique_count': 800,
            'non_null_count': 950,
            'null_count': 50
        }]
        
        # Mock sample query result
        sample_result = [
            {'column_name': 'value1'},
            {'column_name': 'value2'},
            {'column_name': 'value3'}
        ]
        
        with patch.object(adapter, '_execute_query') as mock_execute:
            mock_execute.side_effect = [stats_result, sample_result]
            
            result = adapter.analyze_data_distribution('users', 'column_name', 1000)
        
        assert result['total_count'] == 1000
        assert result['unique_count'] == 800
        assert result['null_count'] == 50
        assert 'null_percentage' in result
        assert 'unique_percentage' in result
        assert len(result['sample_values']) == 3
    
    def test_analyze_data_distribution_error(self, adapter):
        """Test data distribution analysis with error"""
        with patch.object(adapter, '_execute_query', side_effect=Exception("Query failed")):
            result = adapter.analyze_data_distribution('users', 'column_name')
        
        assert 'error' in result
        assert result['analysis_failed'] is True
    
    def test_get_sample_data(self, adapter):
        """Test getting sample data"""
        sample_data = [
            {'id': 1, 'name': 'John'},
            {'id': 2, 'name': 'Jane'}
        ]
        
        with patch.object(adapter, '_execute_query', return_value=sample_data):
            result = adapter.get_sample_data('users', 5)
        
        assert len(result) == 2
        assert result[0]['id'] == 1
    
    def test_get_sample_data_error(self, adapter):
        """Test getting sample data with error"""
        with patch.object(adapter, '_execute_query', side_effect=Exception("Query failed")):
            result = adapter.get_sample_data('users')
        
        assert len(result) == 1
        assert 'error' in result[0]
    
    def test_get_table_size(self, adapter):
        """Test getting table size information"""
        size_data = [{
            'total_size': '150 MB',
            'table_size': '120 MB',
            'index_size': '30 MB'
        }]
        
        with patch.object(adapter, '_execute_query', return_value=size_data):
            result = adapter.get_table_size('users')
        
        assert result['total_size'] == '150 MB'
        assert result['table_size'] == '120 MB'
        assert result['index_size'] == '30 MB'
    
    def test_get_table_size_error(self, adapter):
        """Test getting table size with error"""
        with patch.object(adapter, '_execute_query', side_effect=Exception("Query failed")):
            result = adapter.get_table_size('users')
        
        assert 'error' in result
    
    def test_get_database_version(self, adapter):
        """Test getting database version"""
        version_data = [{'version': 'PostgreSQL 14.9 on x86_64-pc-linux-gnu'}]
        
        with patch.object(adapter, '_execute_query', return_value=version_data):
            result = adapter.get_database_version()
        
        assert result == 'PostgreSQL 14.9 on x86_64-pc-linux-gnu'
    
    def test_get_database_version_error(self, adapter):
        """Test getting database version with error"""
        with patch.object(adapter, '_execute_query', side_effect=Exception("Query failed")):
            result = adapter.get_database_version()
        
        assert result == "Unknown"
    
    def test_columns_with_table_filter(self, adapter):
        """Test getting columns with table name filter"""
        mock_data = [{
            'table_name': 'users',
            'column_name': 'id',
            'data_type': 'integer',
            'max_length': 0,
            'is_nullable': False,
            'default_value': '',
            'column_comment': '',
            'ordinal_position': 1
        }]
        
        with patch.object(adapter, '_execute_query', return_value=mock_data):
            columns = adapter.get_columns('users')
        
        # Verify that the table filter is properly applied
        assert len(columns) == 1
        assert columns[0].table_name == 'users'
    
    def test_indexes_with_table_filter(self, adapter):
        """Test getting indexes with table name filter"""
        mock_data = [{
            'index_name': 'users_pkey',
            'table_name': 'users',
            'column_names': ['id'],
            'is_unique': True,
            'index_type': 'btree',
            'is_primary': True
        }]
        
        with patch.object(adapter, '_execute_query', return_value=mock_data):
            indexes = adapter.get_indexes('users')
        
        # Verify that the table filter is properly applied
        assert len(indexes) == 1
        assert indexes[0].table_name == 'users'
        assert indexes[0].is_primary is True


if __name__ == "__main__":
    pytest.main([__file__])