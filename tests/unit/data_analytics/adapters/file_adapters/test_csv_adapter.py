#!/usr/bin/env python3
"""
Unit tests for CSV adapter
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[6]
sys.path.insert(0, str(project_root))

from tests.unit.data_analytics.test_data.sample_data_generator import SampleDataGenerator
from tools.services.data_analytics_service.adapters.file_adapters.csv_adapter import CSVAdapter
from tools.services.data_analytics_service.core.metadata_extractor import TableInfo, ColumnInfo

class TestCSVAdapter(unittest.TestCase):
    """Test cases for CSV adapter"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with sample data"""
        cls.data_generator = SampleDataGenerator()
        
        # Create test file configurations
        cls.file_configs = cls.data_generator.create_test_file_configs()
        cls.csv_config = cls.file_configs['csv']
        
        cls.adapter = CSVAdapter()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        cls.data_generator.cleanup()
    
    def setUp(self):
        """Set up each test"""
        # Connect to test CSV file
        self.assertTrue(self.adapter.connect(self.csv_config))
    
    def tearDown(self):
        """Clean up after each test"""
        self.adapter.disconnect()
    
    def test_csv_file_loading(self):
        """Test CSV file loading functionality"""
        # Verify file is loaded
        self.assertIsNotNone(self.adapter.data)
        self.assertIsNotNone(self.adapter.dataframe)
        self.assertIsNotNone(self.adapter.csv_info)
        
        # Verify CSV info
        csv_info = self.adapter.csv_info
        self.assertIn('delimiter', csv_info)
        self.assertIn('encoding', csv_info)
        self.assertIn('has_header', csv_info)
        self.assertIn('total_rows', csv_info)
        self.assertIn('total_columns', csv_info)
        
        # Verify delimiter detection
        self.assertEqual(csv_info['delimiter'], ',')  # Should detect comma delimiter
        
        # Verify data is loaded
        self.assertGreater(csv_info['total_rows'], 0)
        self.assertGreater(csv_info['total_columns'], 0)
    
    def test_csv_file_info(self):
        """Test CSV file information"""
        file_info = self.adapter.get_file_info()
        
        self.assertIsInstance(file_info, dict)
        self.assertIn('file_path', file_info)
        self.assertIn('file_name', file_info)
        self.assertIn('file_size', file_info)
        self.assertIn('file_type', file_info)
        self.assertEqual(file_info['file_type'], 'csv')
    
    def test_csv_structure_analysis(self):
        """Test CSV structure analysis"""
        structure = self.adapter._analyze_structure()
        
        self.assertIsInstance(structure, dict)
        self.assertIn('csv_info', structure)
        self.assertIn('rows', structure)
        self.assertIn('columns', structure)
        self.assertIn('column_names', structure)
        self.assertIn('data_types', structure)
        self.assertIn('empty_rows', structure)
        self.assertIn('empty_columns', structure)
        self.assertIn('duplicate_rows', structure)
        self.assertIn('memory_usage', structure)
        
        # Verify structure makes sense
        self.assertIsInstance(structure['rows'], int)
        self.assertIsInstance(structure['columns'], int)
        self.assertIsInstance(structure['column_names'], list)
        self.assertIsInstance(structure['data_types'], dict)
        self.assertGreater(structure['rows'], 0)
        self.assertGreater(structure['columns'], 0)
    
    def test_get_csv_tables(self):
        """Test getting CSV as table"""
        tables = self.adapter.get_tables()
        
        # CSV should return exactly one table
        self.assertIsInstance(tables, list)
        self.assertEqual(len(tables), 1)
        
        # Verify table structure
        table = tables[0]
        self.assertIsInstance(table, TableInfo)
        self.assertIsNotNone(table.table_name)
        self.assertEqual(table.schema_name, 'csv_file')
        self.assertEqual(table.table_type, 'CSV')
        self.assertIsInstance(table.record_count, int)
        self.assertGreater(table.record_count, 0)
        self.assertIsNotNone(table.business_category)
    
    def test_get_csv_columns(self):
        """Test getting CSV columns"""
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
            self.assertIsNotNone(column.business_type)
        
        # Check for expected columns from our sample data
        column_names = [c.column_name for c in columns]
        expected_columns = ['transaction_id', 'customer_id', 'product_code', 'total_amount']
        
        for expected_col in expected_columns:
            self.assertIn(expected_col, column_names, f"Expected column {expected_col} not found")
    
    def test_csv_data_analysis(self):
        """Test CSV data analysis"""
        # Test with a numeric column
        analysis = self.adapter.analyze_data_distribution('sample_transactions', 'total_amount')
        
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
    
    def test_csv_sample_data(self):
        """Test getting CSV sample data"""
        sample_data = self.adapter.get_sample_data('sample_transactions', 5)
        
        self.assertIsInstance(sample_data, list)
        
        if sample_data and not any('error' in record for record in sample_data):
            self.assertLessEqual(len(sample_data), 5)
            
            for record in sample_data:
                self.assertIsInstance(record, dict)
                # Should have expected columns
                self.assertIn('transaction_id', record)
                self.assertIn('customer_id', record)
                self.assertIn('total_amount', record)
    
    def test_csv_business_categorization(self):
        """Test CSV business categorization"""
        category = self.adapter._categorize_csv_content()
        self.assertIsInstance(category, str)
        
        # Our sample data should be categorized appropriately
        # The sample contains transaction data
        expected_categories = ['transaction', 'data', 'customer']
        self.assertIn(category, expected_categories)
    
    def test_csv_data_quality_score(self):
        """Test CSV data quality scoring"""
        quality_score = self.adapter._calculate_data_quality_score()
        
        self.assertIsInstance(quality_score, float)
        self.assertGreaterEqual(quality_score, 0.0)
        self.assertLessEqual(quality_score, 1.0)
    
    def test_csv_key_column_identification(self):
        """Test CSV key column identification"""
        key_columns = self.adapter._identify_key_columns()
        
        self.assertIsInstance(key_columns, list)
        self.assertLessEqual(len(key_columns), 3)  # Max 3 key columns
        
        # transaction_id should be identified as a key column
        if key_columns:
            self.assertIn('transaction_id', key_columns)
    
    def test_csv_column_business_types(self):
        """Test CSV column business type inference"""
        columns = self.adapter.get_columns()
        
        # Find specific columns and check their business types
        business_type_mapping = {}
        for column in columns:
            business_type_mapping[column.column_name] = column.business_type
        
        # Check some expected business types
        if 'transaction_id' in business_type_mapping:
            self.assertEqual(business_type_mapping['transaction_id'], 'identifier')
        
        if 'customer_id' in business_type_mapping:
            self.assertEqual(business_type_mapping['customer_id'], 'identifier')
        
        if 'total_amount' in business_type_mapping:
            self.assertEqual(business_type_mapping['total_amount'], 'amount')
        
        if 'transaction_date' in business_type_mapping:
            self.assertEqual(business_type_mapping['transaction_date'], 'datetime')
    
    def test_csv_delimiter_detection(self):
        """Test CSV delimiter detection"""
        # Our test file should have comma delimiter
        self.assertEqual(self.adapter.delimiter, ',')
        
        # Verify delimiter is correctly stored in csv_info
        self.assertEqual(self.adapter.csv_info['delimiter'], ',')
    
    def test_csv_encoding_detection(self):
        """Test CSV encoding detection"""
        # Should detect encoding
        self.assertIsNotNone(self.adapter.encoding)
        self.assertIsInstance(self.adapter.encoding, str)
        
        # Common encodings
        common_encodings = ['utf-8', 'ascii', 'latin-1', 'cp1252']
        self.assertIn(self.adapter.encoding.lower(), [enc.lower() for enc in common_encodings])
    
    def test_csv_header_detection(self):
        """Test CSV header detection"""
        has_header = self.adapter.csv_info['has_header']
        self.assertIsInstance(has_header, bool)
        
        # Our sample data should have headers
        self.assertTrue(has_header)
    
    def test_csv_validation(self):
        """Test CSV file validation"""
        validation_result = self.adapter.validate_file_structure()
        
        self.assertIsInstance(validation_result, dict)
        self.assertIn('valid', validation_result)
        self.assertIn('file_info', validation_result)
        self.assertIn('structure_analysis', validation_result)
        
        if validation_result['valid']:
            self.assertIn('data_quality', validation_result)
    
    def test_csv_quality_metrics(self):
        """Test CSV quality metrics computation"""
        metrics = {'total_sections': 0, 'total_columns': 0, 'total_rows': 0, 'empty_sections': 0, 'columns_with_nulls': 0}
        computed_metrics = self.adapter._compute_quality_metrics(metrics)
        
        self.assertIsInstance(computed_metrics, dict)
        self.assertIn('total_sections', computed_metrics)
        self.assertIn('total_columns', computed_metrics)
        self.assertIn('total_rows', computed_metrics)
        self.assertIn('encoding', computed_metrics)
        self.assertIn('delimiter', computed_metrics)
        
        # Verify values make sense
        self.assertEqual(computed_metrics['total_sections'], 1)  # CSV has one section
        self.assertGreater(computed_metrics['total_columns'], 0)
        self.assertGreater(computed_metrics['total_rows'], 0)
    
    def test_csv_data_summary(self):
        """Test CSV data summary generation"""
        summary = self.adapter._get_data_summary()
        
        self.assertIsInstance(summary, dict)
        self.assertIn('rows', summary)
        self.assertIn('columns', summary)
        self.assertIn('data_types', summary)
        self.assertIn('memory_usage', summary)
        self.assertIn('csv_properties', summary)
        self.assertIn('data_quality', summary)
        
        # Verify CSV properties
        csv_props = summary['csv_properties']
        self.assertIn('delimiter', csv_props)
        self.assertIn('encoding', csv_props)
        self.assertIn('has_header', csv_props)
        
        # Verify data quality metrics
        data_quality = summary['data_quality']
        self.assertIn('null_percentage', data_quality)
        self.assertIn('duplicate_percentage', data_quality)
    
    def test_csv_value_counts(self):
        """Test CSV value counts functionality"""
        # Test with a categorical column
        value_counts = self.adapter.get_value_counts('status', 5)
        
        self.assertIsInstance(value_counts, dict)
        
        if value_counts:
            # Should have reasonable counts
            for value, count in value_counts.items():
                self.assertIsInstance(count, (int, float))
                self.assertGreater(count, 0)
    
    def test_csv_export_metadata(self):
        """Test CSV metadata export"""
        metadata = self.adapter.export_metadata_to_dict()
        
        self.assertIsInstance(metadata, dict)
        self.assertIn('source_info', metadata)
        self.assertIn('file_info', metadata)
        self.assertIn('tables', metadata)
        self.assertIn('columns', metadata)
        self.assertIn('structure_analysis', metadata)
        
        # Verify source info
        source_info = metadata['source_info']
        self.assertEqual(source_info['type'], 'file')
        self.assertEqual(source_info['subtype'], 'csv')
        
        # Should have exactly one table
        self.assertEqual(len(metadata['tables']), 1)
    
    def test_csv_filtered_export(self):
        """Test exporting filtered CSV data"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_file:
            csv_path = tmp_file.name
        
        try:
            # Test basic export
            success = self.adapter.export_filtered_data(csv_path)
            self.assertTrue(success)
            
            # Verify file exists and has content
            from pathlib import Path
            csv_file = Path(csv_path)
            self.assertTrue(csv_file.exists())
            self.assertGreater(csv_file.stat().st_size, 0)
            
            # Test filtered export
            filter_conditions = {'status': 'COMPLETED'}
            success = self.adapter.export_filtered_data(csv_path, filter_conditions)
            self.assertTrue(success)
            
        finally:
            # Clean up
            try:
                Path(csv_path).unlink()
            except:
                pass

if __name__ == '__main__':
    unittest.main()