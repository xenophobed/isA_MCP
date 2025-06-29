#!/usr/bin/env python3
"""
Unit tests for database base adapter
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parents[6]
sys.path.insert(0, str(project_root))

from tests.unit.data_analytics.test_data.sample_data_generator import SampleDataGenerator
from tests.unit.data_analytics.test_data.sqlite_adapter import SQLiteAdapter
from tools.services.data_analytics_service.core.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

class TestDatabaseBaseAdapter(unittest.TestCase):
    """Test cases for database base adapter functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with sample data"""
        cls.data_generator = SampleDataGenerator()
        cls.test_db_config = cls.data_generator.create_test_database_config("sqlite")
        cls.adapter = SQLiteAdapter()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        cls.data_generator.cleanup()
    
    def setUp(self):
        """Set up each test"""
        # Connect to test database
        self.assertTrue(self.adapter.connect(self.test_db_config))
    
    def tearDown(self):
        """Clean up after each test"""
        self.adapter.disconnect()
    
    def test_database_connection(self):
        """Test database connection functionality"""
        # Test successful connection
        self.assertTrue(self.adapter.test_connection())
        
        # Test database info
        db_info = self.adapter.get_database_info()
        self.assertIn("database_type", db_info)
        self.assertIn("connected", db_info)
        self.assertTrue(db_info["connected"])
    
    def test_get_tables(self):
        """Test getting table information"""
        tables = self.adapter.get_tables()
        
        # Verify we get tables
        self.assertIsInstance(tables, list)
        self.assertGreater(len(tables), 0)
        
        # Verify table structure
        for table in tables:
            self.assertIsInstance(table, TableInfo)
            self.assertIsNotNone(table.table_name)
            self.assertIsNotNone(table.schema_name)
            self.assertIsNotNone(table.table_type)
            self.assertIsInstance(table.record_count, int)
        
        # Check for expected tables
        table_names = [t.table_name for t in tables]
        expected_tables = ['customs_declaration', 'goods_detail', 'company', 'hs_code_ref']
        
        for expected_table in expected_tables:
            self.assertIn(expected_table, table_names, f"Expected table {expected_table} not found")
    
    def test_get_columns(self):
        """Test getting column information"""
        # Get all columns
        columns = self.adapter.get_columns()
        
        # Verify we get columns
        self.assertIsInstance(columns, list)
        self.assertGreater(len(columns), 0)
        
        # Verify column structure
        for column in columns:
            self.assertIsInstance(column, ColumnInfo)
            self.assertIsNotNone(column.table_name)
            self.assertIsNotNone(column.column_name)
            self.assertIsNotNone(column.data_type)
            self.assertIsInstance(column.is_nullable, bool)
            self.assertIsInstance(column.ordinal_position, int)
        
        # Test specific table columns
        customs_columns = self.adapter.get_columns('customs_declaration')
        customs_column_names = [c.column_name for c in customs_columns]
        
        expected_columns = ['decl_no', 'company_code', 'trade_date', 'trade_amount']
        for expected_col in expected_columns:
            self.assertIn(expected_col, customs_column_names, f"Expected column {expected_col} not found")
    
    def test_get_relationships(self):
        """Test getting relationship information"""
        relationships = self.adapter.get_relationships()
        
        # Verify relationships structure
        self.assertIsInstance(relationships, list)
        
        for relationship in relationships:
            self.assertIsInstance(relationship, RelationshipInfo)
            self.assertIsNotNone(relationship.constraint_name)
            self.assertIsNotNone(relationship.from_table)
            self.assertIsNotNone(relationship.from_column)
            self.assertIsNotNone(relationship.to_table)
            self.assertIsNotNone(relationship.to_column)
            self.assertEqual(relationship.constraint_type, 'FOREIGN KEY')
    
    def test_get_indexes(self):
        """Test getting index information"""
        indexes = self.adapter.get_indexes()
        
        # Verify indexes structure
        self.assertIsInstance(indexes, list)
        
        for index in indexes:
            self.assertIsInstance(index, IndexInfo)
            self.assertIsNotNone(index.index_name)
            self.assertIsNotNone(index.table_name)
            self.assertIsInstance(index.column_names, list)
            self.assertIsInstance(index.is_unique, bool)
            self.assertIsInstance(index.is_primary, bool)
    
    def test_analyze_data_distribution(self):
        """Test data distribution analysis"""
        # Test with a known column
        analysis = self.adapter.analyze_data_distribution('customs_declaration', 'trade_amount')
        
        # Verify analysis structure
        self.assertIsInstance(analysis, dict)
        
        if 'error' not in analysis:
            self.assertIn('total_count', analysis)
            self.assertIn('unique_count', analysis)
            self.assertIn('null_count', analysis)
            self.assertIn('null_percentage', analysis)
            self.assertIn('unique_percentage', analysis)
            self.assertIn('sample_values', analysis)
            
            # Verify data types
            self.assertIsInstance(analysis['total_count'], int)
            self.assertIsInstance(analysis['unique_count'], int)
            self.assertIsInstance(analysis['null_count'], int)
            self.assertIsInstance(analysis['null_percentage'], (int, float))
            self.assertIsInstance(analysis['unique_percentage'], (int, float))
            self.assertIsInstance(analysis['sample_values'], list)
    
    def test_get_sample_data(self):
        """Test getting sample data"""
        sample_data = self.adapter.get_sample_data('customs_declaration', 5)
        
        # Verify sample data structure
        self.assertIsInstance(sample_data, list)
        
        if sample_data and 'error' not in sample_data[0]:
            self.assertLessEqual(len(sample_data), 5)
            
            for record in sample_data:
                self.assertIsInstance(record, dict)
                # Should have key columns
                self.assertIn('decl_no', record)
                self.assertIn('company_code', record)
    
    def test_table_statistics(self):
        """Test table statistics functionality"""
        stats = self.adapter.get_table_statistics('customs_declaration')
        
        self.assertIsInstance(stats, dict)
        
        if 'error' not in stats:
            self.assertIn('total_rows', stats)
            self.assertIn('total_columns', stats)
            self.assertIsInstance(stats['total_rows'], int)
            self.assertIsInstance(stats['total_columns'], int)
            self.assertGreater(stats['total_columns'], 0)
    
    def test_table_schema(self):
        """Test getting complete table schema"""
        schema = self.adapter.get_table_schema('customs_declaration')
        
        self.assertIsInstance(schema, dict)
        
        if 'error' not in schema:
            self.assertIn('table', schema)
            self.assertIn('columns', schema)
            self.assertIn('indexes', schema)
            self.assertIn('relationships', schema)
            
            # Verify table info
            table_info = schema['table']
            self.assertIsInstance(table_info, dict)
            self.assertEqual(table_info['table_name'], 'customs_declaration')
            
            # Verify columns
            columns = schema['columns']
            self.assertIsInstance(columns, list)
            self.assertGreater(len(columns), 0)
    
    def test_table_validation(self):
        """Test table access validation"""
        # Test valid table
        self.assertTrue(self.adapter.validate_table_access('customs_declaration'))
        
        # Test invalid table
        self.assertFalse(self.adapter.validate_table_access('non_existent_table'))
    
    def test_table_count(self):
        """Test getting table count"""
        count = self.adapter.get_table_count()
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 4)  # We created 4 tables
    
    def test_table_names(self):
        """Test getting table names"""
        names = self.adapter.get_table_names()
        self.assertIsInstance(names, list)
        self.assertGreater(len(names), 0)
        
        expected_tables = ['customs_declaration', 'goods_detail', 'company', 'hs_code_ref']
        for expected_table in expected_tables:
            self.assertIn(expected_table, names)
    
    def test_column_names(self):
        """Test getting column names for a table"""
        columns = self.adapter.get_column_names('customs_declaration')
        self.assertIsInstance(columns, list)
        self.assertGreater(len(columns), 0)
        
        expected_columns = ['decl_no', 'company_code', 'trade_date']
        for expected_col in expected_columns:
            self.assertIn(expected_col, columns)
    
    def test_custom_query(self):
        """Test executing custom queries"""
        # Test simple query
        result = self.adapter.execute_custom_query("SELECT COUNT(*) as count FROM customs_declaration")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn('count', result[0])
        self.assertIsInstance(result[0]['count'], int)
    
    def test_extract_full_metadata(self):
        """Test complete metadata extraction"""
        metadata = self.adapter.extract_full_metadata(self.test_db_config)
        
        # Verify metadata structure
        self.assertIsInstance(metadata, dict)
        self.assertIn('source_info', metadata)
        self.assertIn('tables', metadata)
        self.assertIn('columns', metadata)
        self.assertIn('relationships', metadata)
        self.assertIn('indexes', metadata)
        
        # Verify source info
        source_info = metadata['source_info']
        self.assertIn('type', source_info)
        self.assertIn('total_tables', source_info)
        self.assertIn('total_columns', source_info)
        
        # Verify counts match
        self.assertEqual(source_info['total_tables'], len(metadata['tables']))
        self.assertEqual(source_info['total_columns'], len(metadata['columns']))
        
        # Verify business patterns exist
        if 'business_patterns' in metadata:
            patterns = metadata['business_patterns']
            self.assertIn('naming_conventions', patterns)
            self.assertIn('table_categories', patterns)

if __name__ == '__main__':
    unittest.main()