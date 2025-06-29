#!/usr/bin/env python3
"""
Unit tests for metadata discovery service
"""

import unittest
import tempfile
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[5]
sys.path.insert(0, str(project_root))

from tests.unit.data_analytics.test_data.sample_data_generator import SampleDataGenerator
from tools.services.data_analytics_service.services.metadata_service import MetadataDiscoveryService
from tools.services.data_analytics_service.utils.error_handler import DataAnalyticsError

class TestMetadataDiscoveryService(unittest.TestCase):
    """Test cases for metadata discovery service"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with sample data"""
        cls.data_generator = SampleDataGenerator()
        
        # Create test configurations
        cls.db_config = cls.data_generator.create_test_database_config("sqlite")
        cls.file_configs = cls.data_generator.create_test_file_configs()
        
        cls.service = MetadataDiscoveryService()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        cls.data_generator.cleanup()
    
    def test_discover_database_metadata(self):
        """Test database metadata discovery"""
        # Test SQLite database discovery
        metadata = self.service.discover_database_metadata(self.db_config)
        
        # Verify basic structure
        self.assertIsInstance(metadata, dict)
        self.assertIn('source_info', metadata)
        self.assertIn('tables', metadata)
        self.assertIn('columns', metadata)
        self.assertIn('relationships', metadata)
        self.assertIn('indexes', metadata)
        self.assertIn('discovery_info', metadata)
        
        # Verify discovery info
        discovery_info = metadata['discovery_info']
        self.assertEqual(discovery_info['service'], 'MetadataDiscoveryService')
        self.assertEqual(discovery_info['source_type'], 'database')
        self.assertEqual(discovery_info['source_subtype'], 'sqlite')
        
        # Verify we have expected tables
        table_names = [t['table_name'] for t in metadata['tables']]
        expected_tables = ['customs_declaration', 'goods_detail', 'company', 'hs_code_ref']
        
        for expected_table in expected_tables:
            self.assertIn(expected_table, table_names)
        
        # Verify columns exist
        self.assertGreater(len(metadata['columns']), 0)
        
        # Verify relationships exist (foreign keys)
        if metadata['relationships']:
            for rel in metadata['relationships']:
                self.assertIn('from_table', rel)
                self.assertIn('to_table', rel)
                self.assertIn('constraint_type', rel)
    
    def test_discover_file_metadata_excel(self):
        """Test Excel file metadata discovery"""
        excel_config = self.file_configs['excel']
        metadata = self.service.discover_file_metadata(excel_config)
        
        # Verify basic structure
        self.assertIsInstance(metadata, dict)
        self.assertIn('source_info', metadata)
        self.assertIn('tables', metadata)
        self.assertIn('columns', metadata)
        self.assertIn('discovery_info', metadata)
        
        # Verify discovery info
        discovery_info = metadata['discovery_info']
        self.assertEqual(discovery_info['service'], 'MetadataDiscoveryService')
        self.assertEqual(discovery_info['source_type'], 'file')
        self.assertEqual(discovery_info['source_subtype'], 'excel')
        
        # Verify we have expected sheets as tables
        table_names = [t['table_name'] for t in metadata['tables']]
        expected_sheets = ['Import_Declarations', 'Export_Declarations', 'Company_Master', 'Product_Catalog']
        
        for expected_sheet in expected_sheets:
            self.assertIn(expected_sheet, table_names)
        
        # Verify columns exist
        self.assertGreater(len(metadata['columns']), 0)
    
    def test_discover_file_metadata_csv(self):
        """Test CSV file metadata discovery"""
        csv_config = self.file_configs['csv']
        metadata = self.service.discover_file_metadata(csv_config)
        
        # Verify basic structure
        self.assertIsInstance(metadata, dict)
        self.assertIn('source_info', metadata)
        self.assertIn('tables', metadata)
        self.assertIn('columns', metadata)
        self.assertIn('discovery_info', metadata)
        
        # Verify discovery info
        discovery_info = metadata['discovery_info']
        self.assertEqual(discovery_info['source_type'], 'file')
        self.assertEqual(discovery_info['source_subtype'], 'csv')
        
        # CSV should have exactly one table
        self.assertEqual(len(metadata['tables']), 1)
        
        # Verify columns exist
        self.assertGreater(len(metadata['columns']), 0)
        
        # Check for expected columns
        column_names = [c['column_name'] for c in metadata['columns']]
        expected_columns = ['transaction_id', 'customer_id', 'total_amount']
        
        for expected_col in expected_columns:
            self.assertIn(expected_col, column_names)
    
    def test_discover_multiple_sources(self):
        """Test discovering metadata from multiple sources"""
        sources = [
            {
                'name': 'test_database',
                **self.db_config
            },
            {
                'name': 'test_excel',
                **self.file_configs['excel']
            },
            {
                'name': 'test_csv',
                **self.file_configs['csv']
            }
        ]
        
        results = self.service.discover_multiple_sources(sources)
        
        # Verify structure
        self.assertIsInstance(results, dict)
        self.assertIn('sources', results)
        self.assertIn('errors', results)
        self.assertIn('summary', results)
        
        # Verify summary
        summary = results['summary']
        self.assertEqual(summary['total_sources'], 3)
        self.assertGreaterEqual(summary['successful'], 1)  # At least one should succeed
        
        # Verify successful sources
        sources_results = results['sources']
        self.assertGreater(len(sources_results), 0)
        
        for source_name, metadata in sources_results.items():
            self.assertIn('source_info', metadata)
            self.assertIn('tables', metadata)
            self.assertIn('columns', metadata)
    
    def test_compare_schemas(self):
        """Test schema comparison functionality"""
        # Get metadata from two sources
        db_metadata = self.service.discover_database_metadata(self.db_config)
        excel_metadata = self.service.discover_file_metadata(self.file_configs['excel'])
        
        # Compare schemas
        comparison = self.service.compare_schemas(db_metadata, excel_metadata)
        
        # Verify comparison structure
        self.assertIsInstance(comparison, dict)
        self.assertIn('comparison_time', comparison)
        self.assertIn('source1_info', comparison)
        self.assertIn('source2_info', comparison)
        self.assertIn('table_comparison', comparison)
        self.assertIn('column_comparison', comparison)
        self.assertIn('relationship_comparison', comparison)
        
        # Verify table comparison
        table_comp = comparison['table_comparison']
        self.assertIn('total_source1', table_comp)
        self.assertIn('total_source2', table_comp)
        self.assertIn('similarity_score', table_comp)
        self.assertIsInstance(table_comp['similarity_score'], (int, float))
        
        # Verify relationship comparison
        rel_comp = comparison['relationship_comparison']
        self.assertIn('total_source1', rel_comp)
        self.assertIn('total_source2', rel_comp)
        self.assertIn('similarity_score', rel_comp)
    
    def test_export_metadata_json(self):
        """Test exporting metadata to JSON"""
        metadata = self.service.discover_database_metadata(self.db_config)
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            success = self.service.export_metadata(metadata, output_path, 'json')
            self.assertTrue(success)
            
            # Verify file exists and contains valid JSON
            output_file = Path(output_path)
            self.assertTrue(output_file.exists())
            
            with open(output_path, 'r') as f:
                loaded_metadata = json.load(f)
            
            # Verify loaded metadata has same structure
            self.assertIn('source_info', loaded_metadata)
            self.assertIn('tables', loaded_metadata)
            self.assertIn('columns', loaded_metadata)
            
        finally:
            # Clean up
            try:
                Path(output_path).unlink()
            except:
                pass
    
    def test_export_metadata_csv(self):
        """Test exporting metadata to CSV"""
        metadata = self.service.discover_database_metadata(self.db_config)
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            success = self.service.export_metadata(metadata, output_path, 'csv')
            self.assertTrue(success)
            
            # Verify files exist
            tables_path = output_path.replace('.csv', '_tables.csv')
            columns_path = output_path.replace('.csv', '_columns.csv')
            
            self.assertTrue(Path(tables_path).exists())
            self.assertTrue(Path(columns_path).exists())
            
            # Verify files have content
            self.assertGreater(Path(tables_path).stat().st_size, 0)
            self.assertGreater(Path(columns_path).stat().st_size, 0)
            
        finally:
            # Clean up
            for path in [output_path, output_path.replace('.csv', '_tables.csv'), output_path.replace('.csv', '_columns.csv')]:
                try:
                    Path(path).unlink()
                except:
                    pass
    
    def test_get_summary_statistics(self):
        """Test getting summary statistics"""
        metadata = self.service.discover_database_metadata(self.db_config)
        summary = self.service.get_summary_statistics(metadata)
        
        # Verify summary structure
        self.assertIsInstance(summary, dict)
        self.assertIn('totals', summary)
        self.assertIn('table_statistics', summary)
        self.assertIn('column_statistics', summary)
        self.assertIn('relationship_statistics', summary)
        self.assertIn('data_quality_overview', summary)
        
        # Verify totals
        totals = summary['totals']
        self.assertIn('tables', totals)
        self.assertIn('columns', totals)
        self.assertIn('relationships', totals)
        
        self.assertIsInstance(totals['tables'], int)
        self.assertIsInstance(totals['columns'], int)
        self.assertIsInstance(totals['relationships'], int)
        
        # Verify table statistics
        table_stats = summary['table_statistics']
        if table_stats:
            self.assertIn('total_records', table_stats)
            self.assertIn('avg_records_per_table', table_stats)
        
        # Verify column statistics
        column_stats = summary['column_statistics']
        if column_stats:
            self.assertIn('total_columns', column_stats)
            self.assertIn('data_type_distribution', column_stats)
    
    def test_validation_errors(self):
        """Test validation and error handling"""
        # Test invalid database config
        invalid_db_config = {
            "type": "postgresql",
            # Missing required fields
        }
        
        with self.assertRaises(DataAnalyticsError):
            self.service.discover_database_metadata(invalid_db_config)
        
        # Test invalid file config
        invalid_file_config = {
            "file_path": "/nonexistent/file.csv"
        }
        
        with self.assertRaises(DataAnalyticsError):
            self.service.discover_file_metadata(invalid_file_config)
        
        # Test unsupported database type
        unsupported_db_config = {
            "type": "unsupported_db",
            "host": "localhost",
            "database": "test",
            "username": "user",
            "password": "pass"
        }
        
        with self.assertRaises(DataAnalyticsError):
            self.service.discover_database_metadata(unsupported_db_config)
    
    def test_file_type_detection(self):
        """Test automatic file type detection"""
        # Test Excel file
        excel_config_no_type = {
            "file_path": self.file_configs['excel']['file_path']
        }
        
        metadata = self.service.discover_file_metadata(excel_config_no_type)
        self.assertIn('discovery_info', metadata)
        self.assertEqual(metadata['discovery_info']['source_subtype'], 'excel')
        
        # Test CSV file
        csv_config_no_type = {
            "file_path": self.file_configs['csv']['file_path']
        }
        
        metadata = self.service.discover_file_metadata(csv_config_no_type)
        self.assertIn('discovery_info', metadata)
        self.assertEqual(metadata['discovery_info']['source_subtype'], 'csv')
    
    def test_schema_comparison_edge_cases(self):
        """Test schema comparison with edge cases"""
        # Compare same source with itself
        metadata = self.service.discover_database_metadata(self.db_config)
        comparison = self.service.compare_schemas(metadata, metadata)
        
        # Should have 100% similarity
        self.assertEqual(comparison['table_comparison']['similarity_score'], 1.0)
        self.assertEqual(comparison['relationship_comparison']['similarity_score'], 1.0)
        
        # Compare with empty metadata
        empty_metadata = {
            'source_info': {},
            'tables': [],
            'columns': [],
            'relationships': []
        }
        
        comparison = self.service.compare_schemas(metadata, empty_metadata)
        
        # Should have 0% similarity
        self.assertEqual(comparison['table_comparison']['similarity_score'], 0.0)
        self.assertEqual(comparison['relationship_comparison']['similarity_score'], 0.0)
    
    def test_metadata_service_configuration(self):
        """Test metadata service configuration and supported sources"""
        # Test supported databases
        self.assertIn('postgresql', self.service.supported_databases)
        self.assertIn('mysql', self.service.supported_databases)
        self.assertIn('sqlserver', self.service.supported_databases)
        
        # Test supported files
        self.assertIn('excel', self.service.supported_files)
        self.assertIn('csv', self.service.supported_files)
        
        # Test config manager is initialized
        self.assertIsNotNone(self.service.config_manager)
        
        # Test data validator is initialized
        self.assertIsNotNone(self.service.data_validator)

if __name__ == '__main__':
    unittest.main()