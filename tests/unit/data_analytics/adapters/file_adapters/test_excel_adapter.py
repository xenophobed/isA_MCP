#!/usr/bin/env python3
"""
Unit tests for Excel adapter
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[6]
sys.path.insert(0, str(project_root))

from tests.unit.data_analytics.test_data.sample_data_generator import SampleDataGenerator
from tools.services.data_analytics_service.adapters.file_adapters.excel_adapter import ExcelAdapter
from tools.services.data_analytics_service.core.metadata_extractor import TableInfo, ColumnInfo

class TestExcelAdapter(unittest.TestCase):
    """Test cases for Excel adapter"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with sample data"""
        cls.data_generator = SampleDataGenerator()
        
        # Create test file configurations
        cls.file_configs = cls.data_generator.create_test_file_configs()
        cls.excel_config = cls.file_configs['excel']
        
        cls.adapter = ExcelAdapter()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        cls.data_generator.cleanup()
    
    def setUp(self):
        """Set up each test"""
        # Connect to test Excel file
        self.assertTrue(self.adapter.connect(self.excel_config))
    
    def tearDown(self):
        """Clean up after each test"""
        self.adapter.disconnect()
    
    def test_excel_file_loading(self):
        """Test Excel file loading functionality"""
        # Verify file is loaded
        self.assertIsNotNone(self.adapter.data)
        self.assertIsNotNone(self.adapter.sheet_data)
        self.assertGreater(len(self.adapter.sheet_names), 0)
        
        # Verify expected sheets exist
        expected_sheets = ['Import_Declarations', 'Export_Declarations', 'Company_Master', 'Product_Catalog']
        for sheet in expected_sheets:
            self.assertIn(sheet, self.adapter.sheet_names, f"Expected sheet {sheet} not found")
    
    def test_excel_file_info(self):
        """Test Excel file information"""
        file_info = self.adapter.get_file_info()
        
        self.assertIsInstance(file_info, dict)
        self.assertIn('file_path', file_info)
        self.assertIn('file_name', file_info)
        self.assertIn('file_size', file_info)
        self.assertIn('file_type', file_info)
        self.assertEqual(file_info['file_type'], 'excel')
    
    def test_excel_structure_analysis(self):
        """Test Excel structure analysis"""
        structure = self.adapter._analyze_structure()
        
        self.assertIsInstance(structure, dict)
        self.assertIn('total_sheets', structure)
        self.assertIn('sheet_names', structure)
        self.assertIn('sheets_info', structure)
        
        # Verify sheet count
        self.assertEqual(structure['total_sheets'], len(self.adapter.sheet_names))
        
        # Verify sheet info
        for sheet_name in self.adapter.sheet_names:
            self.assertIn(sheet_name, structure['sheets_info'])
            sheet_info = structure['sheets_info'][sheet_name]
            
            self.assertIn('rows', sheet_info)
            self.assertIn('columns', sheet_info)
            self.assertIn('column_names', sheet_info)
            self.assertIn('data_types', sheet_info)
            
            self.assertIsInstance(sheet_info['rows'], int)
            self.assertIsInstance(sheet_info['columns'], int)
            self.assertIsInstance(sheet_info['column_names'], list)
    
    def test_get_excel_tables(self):
        """Test getting Excel sheets as tables"""
        tables = self.adapter.get_tables()
        
        # Verify we get tables (sheets)
        self.assertIsInstance(tables, list)
        self.assertEqual(len(tables), len(self.adapter.sheet_names))
        
        # Verify table structure
        for table in tables:
            self.assertIsInstance(table, TableInfo)
            self.assertIn(table.table_name, self.adapter.sheet_names)
            self.assertEqual(table.schema_name, 'excel_file')
            self.assertEqual(table.table_type, 'SHEET')
            self.assertIsInstance(table.record_count, int)
            self.assertIsNotNone(table.business_category)
    
    def test_get_excel_columns(self):
        """Test getting Excel columns"""
        # Get all columns
        columns = self.adapter.get_columns()
        
        # Verify we get columns
        self.assertIsInstance(columns, list)
        self.assertGreater(len(columns), 0)
        
        # Verify column structure
        for column in columns:
            self.assertIsInstance(column, ColumnInfo)
            self.assertIn(column.table_name, self.adapter.sheet_names)
            self.assertIsNotNone(column.column_name)
            self.assertIsNotNone(column.data_type)
            self.assertIsInstance(column.is_nullable, bool)
            self.assertIsInstance(column.ordinal_position, int)
            self.assertIsNotNone(column.business_type)
        
        # Test specific sheet columns
        import_columns = self.adapter.get_columns('Import_Declarations')
        self.assertGreater(len(import_columns), 0)
        
        for column in import_columns:
            self.assertEqual(column.table_name, 'Import_Declarations')
    
    def test_excel_data_analysis(self):
        """Test Excel data analysis"""
        # Test with a specific sheet and column
        analysis = self.adapter.analyze_data_distribution('Import_Declarations', 'Total_Amount')
        
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
    
    def test_excel_sample_data(self):
        """Test getting Excel sample data"""
        sample_data = self.adapter.get_sample_data('Import_Declarations', 5)
        
        self.assertIsInstance(sample_data, list)
        
        if sample_data and not any('error' in record for record in sample_data):
            self.assertLessEqual(len(sample_data), 5)
            
            for record in sample_data:
                self.assertIsInstance(record, dict)
                # Should have some expected columns
                self.assertIn('Declaration_No', record)
                self.assertIn('Trade_Type', record)
    
    def test_excel_business_categorization(self):
        """Test Excel business categorization"""
        # Test sheet categorization
        import_category = self.adapter._categorize_sheet('Import_Declarations', self.adapter.sheet_data['Import_Declarations'])
        self.assertIsInstance(import_category, str)
        
        company_category = self.adapter._categorize_sheet('Company_Master', self.adapter.sheet_data['Company_Master'])
        self.assertEqual(company_category, 'reference')  # Should be categorized as reference data
    
    def test_excel_data_quality_score(self):
        """Test Excel data quality scoring"""
        for sheet_name, df in self.adapter.sheet_data.items():
            quality_score = self.adapter._calculate_data_quality_score(df)
            self.assertIsInstance(quality_score, float)
            self.assertGreaterEqual(quality_score, 0.0)
            self.assertLessEqual(quality_score, 1.0)
    
    def test_excel_key_column_identification(self):
        """Test Excel key column identification"""
        for sheet_name, df in self.adapter.sheet_data.items():
            key_columns = self.adapter._identify_key_columns(df)
            self.assertIsInstance(key_columns, list)
            self.assertLessEqual(len(key_columns), 3)  # Max 3 key columns
    
    def test_excel_column_business_types(self):
        """Test Excel column business type inference"""
        columns = self.adapter.get_columns('Company_Master')
        
        # Find specific columns and check their business types
        business_type_mapping = {}
        for column in columns:
            business_type_mapping[column.column_name] = column.business_type
        
        # Check some expected business types
        if 'Company_Code' in business_type_mapping:
            self.assertEqual(business_type_mapping['Company_Code'], 'identifier')
        
        if 'Company_Name' in business_type_mapping:
            self.assertEqual(business_type_mapping['Company_Name'], 'name')
        
        if 'Annual_Turnover' in business_type_mapping:
            self.assertEqual(business_type_mapping['Annual_Turnover'], 'amount')
    
    def test_excel_workbook_metadata(self):
        """Test Excel workbook metadata extraction"""
        workbook_metadata = self.adapter.get_workbook_metadata()
        
        self.assertIsInstance(workbook_metadata, dict)
        self.assertIn('file_info', workbook_metadata)
        self.assertIn('sheets', workbook_metadata)
        
        # Verify sheet metadata
        for sheet_name in self.adapter.sheet_names:
            if sheet_name in workbook_metadata['sheets']:
                sheet_meta = workbook_metadata['sheets'][sheet_name]
                self.assertIn('title', sheet_meta)
                self.assertIn('max_row', sheet_meta)
                self.assertIn('max_column', sheet_meta)
    
    def test_excel_validation(self):
        """Test Excel file validation"""
        validation_result = self.adapter.validate_file_structure()
        
        self.assertIsInstance(validation_result, dict)
        self.assertIn('valid', validation_result)
        self.assertIn('file_info', validation_result)
        self.assertIn('structure_analysis', validation_result)
        
        if validation_result['valid']:
            self.assertIn('data_quality', validation_result)
    
    def test_excel_quality_metrics(self):
        """Test Excel quality metrics computation"""
        metrics = {'total_sections': 0, 'total_columns': 0, 'total_rows': 0, 'empty_sections': 0, 'columns_with_nulls': 0}
        computed_metrics = self.adapter._compute_quality_metrics(metrics)
        
        self.assertIsInstance(computed_metrics, dict)
        self.assertIn('total_sections', computed_metrics)
        self.assertIn('total_columns', computed_metrics)
        self.assertIn('total_rows', computed_metrics)
        
        # Verify values make sense
        self.assertEqual(computed_metrics['total_sections'], len(self.adapter.sheet_names))
        self.assertGreater(computed_metrics['total_columns'], 0)
        self.assertGreater(computed_metrics['total_rows'], 0)
    
    def test_excel_data_summary(self):
        """Test Excel data summary generation"""
        summary = self.adapter._get_data_summary()
        
        self.assertIsInstance(summary, dict)
        self.assertIn('total_sheets', summary)
        self.assertIn('sheet_summaries', summary)
        
        self.assertEqual(summary['total_sheets'], len(self.adapter.sheet_names))
        
        # Verify sheet summaries
        for sheet_name in self.adapter.sheet_names:
            self.assertIn(sheet_name, summary['sheet_summaries'])
            sheet_summary = summary['sheet_summaries'][sheet_name]
            
            self.assertIn('rows', sheet_summary)
            self.assertIn('columns', sheet_summary)
            self.assertIn('data_types', sheet_summary)
            self.assertIn('memory_usage', sheet_summary)
    
    def test_excel_export_metadata(self):
        """Test Excel metadata export"""
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
        self.assertEqual(source_info['subtype'], 'excel')
        
        # Verify tables match sheets
        self.assertEqual(len(metadata['tables']), len(self.adapter.sheet_names))
    
    def test_excel_sheet_export(self):
        """Test exporting Excel sheet to CSV"""
        # This test assumes we can write to temp directory
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_file:
            csv_path = tmp_file.name
        
        try:
            success = self.adapter.export_sheet_to_csv('Import_Declarations', csv_path)
            self.assertTrue(success)
            
            # Verify file exists and has content
            from pathlib import Path
            csv_file = Path(csv_path)
            self.assertTrue(csv_file.exists())
            self.assertGreater(csv_file.stat().st_size, 0)
        finally:
            # Clean up
            try:
                Path(csv_path).unlink()
            except:
                pass

if __name__ == '__main__':
    unittest.main()