#!/usr/bin/env python3
"""
Unit tests for PostgreSQL adapter
"""

import unittest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[6]
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.adapters.database_adapters.postgresql_adapter import PostgreSQLAdapter
from tools.services.data_analytics_service.core.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

class TestPostgreSQLAdapter(unittest.TestCase):
    """Test cases for PostgreSQL adapter"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        cls.adapter = PostgreSQLAdapter()
        
        # Test configuration - only run if PostgreSQL is available
        cls.test_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DB", "test_db"),
            "username": os.getenv("POSTGRES_USER", "test_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "test_pass"),
            "include_data_analysis": True,
            "sample_size": 100
        }
        
        # Check if PostgreSQL is available
        cls.postgres_available = cls._check_postgres_availability()
    
    @classmethod
    def _check_postgres_availability(cls):
        """Check if PostgreSQL is available for testing"""
        try:
            test_adapter = PostgreSQLAdapter()
            result = test_adapter.connect(cls.test_config)
            if result:
                test_adapter.disconnect()
            return result
        except Exception:
            return False
    
    def setUp(self):
        """Set up each test"""
        if not self.postgres_available:
            self.skipTest("PostgreSQL not available for testing")
        
        # Connect to test database
        self.assertTrue(self.adapter.connect(self.test_config))
        
        # Create test tables if they don't exist
        self._create_test_tables()
    
    def tearDown(self):
        """Clean up after each test"""
        if self.postgres_available:
            # Clean up test data
            self._cleanup_test_tables()
            self.adapter.disconnect()
    
    def _create_test_tables(self):
        """Create test tables for PostgreSQL testing"""
        try:
            # Create test table
            self.adapter._execute_query("""
                CREATE TABLE IF NOT EXISTS test_customers (
                    customer_id SERIAL PRIMARY KEY,
                    company_name VARCHAR(200) NOT NULL,
                    contact_email VARCHAR(100),
                    phone VARCHAR(20),
                    registration_date DATE,
                    credit_limit DECIMAL(15,2),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create related table
            self.adapter._execute_query("""
                CREATE TABLE IF NOT EXISTS test_orders (
                    order_id SERIAL PRIMARY KEY,
                    customer_id INTEGER REFERENCES test_customers(customer_id),
                    order_date DATE NOT NULL,
                    total_amount DECIMAL(12,2) NOT NULL,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    notes TEXT
                )
            """)
            
            # Insert sample data
            self.adapter._execute_query("""
                INSERT INTO test_customers (company_name, contact_email, phone, registration_date, credit_limit) 
                VALUES 
                ('Test Company A', 'test@companya.com', '123-456-7890', '2023-01-15', 50000.00),
                ('Test Company B', 'info@companyb.com', '987-654-3210', '2023-02-20', 75000.00),
                ('Test Company C', 'contact@companyc.com', '555-123-4567', '2023-03-10', 100000.00)
                ON CONFLICT DO NOTHING
            """)
            
            self.adapter._execute_query("""
                INSERT INTO test_orders (customer_id, order_date, total_amount, status) 
                VALUES 
                (1, '2023-06-01', 1500.00, 'COMPLETED'),
                (1, '2023-06-15', 2300.00, 'PENDING'),
                (2, '2023-06-10', 5000.00, 'COMPLETED'),
                (3, '2023-06-20', 750.00, 'CANCELLED')
                ON CONFLICT DO NOTHING
            """)
            
        except Exception as e:
            print(f"Warning: Could not create test tables: {e}")
    
    def _cleanup_test_tables(self):
        """Clean up test tables"""
        try:
            self.adapter._execute_query("DROP TABLE IF EXISTS test_orders CASCADE")
            self.adapter._execute_query("DROP TABLE IF EXISTS test_customers CASCADE")
        except Exception as e:
            print(f"Warning: Could not clean up test tables: {e}")
    
    def test_postgresql_connection(self):
        """Test PostgreSQL connection functionality"""
        # Test connection info
        self.assertTrue(self.adapter.test_connection())
        
        # Test database info
        db_info = self.adapter.get_database_info()
        self.assertIn("database_type", db_info)
        self.assertEqual(db_info["database_type"], "PostgreSQL")
        self.assertTrue(db_info["connected"])
    
    def test_get_postgresql_tables(self):
        """Test getting PostgreSQL table information"""
        tables = self.adapter.get_tables()
        
        # Verify we get tables
        self.assertIsInstance(tables, list)
        self.assertGreater(len(tables), 0)
        
        # Find our test tables
        table_names = [t.table_name for t in tables]
        self.assertIn('test_customers', table_names)
        self.assertIn('test_orders', table_names)
        
        # Verify table structure
        for table in tables:
            if table.table_name in ['test_customers', 'test_orders']:
                self.assertIsInstance(table, TableInfo)
                self.assertIsNotNone(table.table_name)
                self.assertEqual(table.schema_name, 'public')
                self.assertEqual(table.table_type, 'BASE TABLE')
                self.assertIsInstance(table.record_count, int)
    
    def test_get_postgresql_columns(self):
        """Test getting PostgreSQL column information"""
        # Get columns for specific table
        columns = self.adapter.get_columns('test_customers')
        
        # Verify we get columns
        self.assertIsInstance(columns, list)
        self.assertGreater(len(columns), 0)
        
        # Check for expected columns
        column_names = [c.column_name for c in columns]
        expected_columns = ['customer_id', 'company_name', 'contact_email', 'credit_limit', 'is_active']
        
        for expected_col in expected_columns:
            self.assertIn(expected_col, column_names)
        
        # Verify column structure
        for column in columns:
            if column.table_name == 'test_customers':
                self.assertIsInstance(column, ColumnInfo)
                self.assertEqual(column.table_name, 'test_customers')
                self.assertIsNotNone(column.column_name)
                self.assertIsNotNone(column.data_type)
                self.assertIsInstance(column.is_nullable, bool)
                self.assertIsInstance(column.ordinal_position, int)
    
    def test_get_postgresql_relationships(self):
        """Test getting PostgreSQL relationships"""
        relationships = self.adapter.get_relationships()
        
        # Verify relationships structure
        self.assertIsInstance(relationships, list)
        
        # Look for our test relationship
        test_relationship = None
        for rel in relationships:
            if rel.from_table == 'test_orders' and rel.to_table == 'test_customers':
                test_relationship = rel
                break
        
        if test_relationship:
            self.assertIsInstance(test_relationship, RelationshipInfo)
            self.assertEqual(test_relationship.from_table, 'test_orders')
            self.assertEqual(test_relationship.from_column, 'customer_id')
            self.assertEqual(test_relationship.to_table, 'test_customers')
            self.assertEqual(test_relationship.to_column, 'customer_id')
            self.assertEqual(test_relationship.constraint_type, 'FOREIGN KEY')
    
    def test_get_postgresql_indexes(self):
        """Test getting PostgreSQL indexes"""
        indexes = self.adapter.get_indexes('test_customers')
        
        # Verify indexes structure
        self.assertIsInstance(indexes, list)
        
        # Look for primary key index
        pk_index = None
        for idx in indexes:
            if idx.is_primary and idx.table_name == 'test_customers':
                pk_index = idx
                break
        
        if pk_index:
            self.assertIsInstance(pk_index, IndexInfo)
            self.assertTrue(pk_index.is_primary)
            self.assertTrue(pk_index.is_unique)
            self.assertIn('customer_id', pk_index.column_names)
    
    def test_postgresql_data_analysis(self):
        """Test PostgreSQL data distribution analysis"""
        # Test with numeric column
        analysis = self.adapter.analyze_data_distribution('test_customers', 'credit_limit')
        
        self.assertIsInstance(analysis, dict)
        
        if 'error' not in analysis:
            self.assertIn('total_count', analysis)
            self.assertIn('unique_count', analysis)
            self.assertIn('null_percentage', analysis)
            self.assertIn('sample_values', analysis)
            
            # Verify data types
            self.assertIsInstance(analysis['total_count'], int)
            self.assertIsInstance(analysis['unique_count'], int)
            self.assertIsInstance(analysis['null_percentage'], (int, float))
            self.assertIsInstance(analysis['sample_values'], list)
    
    def test_postgresql_sample_data(self):
        """Test getting PostgreSQL sample data"""
        sample_data = self.adapter.get_sample_data('test_customers', 3)
        
        self.assertIsInstance(sample_data, list)
        
        if sample_data and 'error' not in sample_data[0]:
            self.assertLessEqual(len(sample_data), 3)
            
            for record in sample_data:
                self.assertIsInstance(record, dict)
                self.assertIn('customer_id', record)
                self.assertIn('company_name', record)
    
    def test_postgresql_version(self):
        """Test getting PostgreSQL version"""
        version = self.adapter.get_database_version()
        self.assertIsInstance(version, str)
        self.assertIn('PostgreSQL', version)
    
    def test_postgresql_table_size(self):
        """Test getting PostgreSQL table size"""
        size_info = self.adapter.get_table_size('test_customers')
        
        self.assertIsInstance(size_info, dict)
        
        if 'error' not in size_info:
            self.assertIn('total_size', size_info)
            self.assertIn('table_size', size_info)
            self.assertIn('index_size', size_info)
    
    def test_postgresql_full_metadata_extraction(self):
        """Test complete metadata extraction for PostgreSQL"""
        metadata = self.adapter.extract_full_metadata(self.test_config)
        
        # Verify metadata structure
        self.assertIsInstance(metadata, dict)
        self.assertIn('source_info', metadata)
        self.assertIn('tables', metadata)
        self.assertIn('columns', metadata)
        self.assertIn('relationships', metadata)
        self.assertIn('indexes', metadata)
        
        # Verify our test tables are included
        table_names = [t['table_name'] for t in metadata['tables']]
        self.assertIn('test_customers', table_names)
        self.assertIn('test_orders', table_names)
        
        # Verify columns are included
        customer_columns = [c for c in metadata['columns'] if c['table_name'] == 'test_customers']
        self.assertGreater(len(customer_columns), 0)
        
        column_names = [c['column_name'] for c in customer_columns]
        self.assertIn('customer_id', column_names)
        self.assertIn('company_name', column_names)

if __name__ == '__main__':
    unittest.main()