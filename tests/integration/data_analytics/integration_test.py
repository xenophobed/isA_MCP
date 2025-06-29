#!/usr/bin/env python3
"""
Integration tests for data analytics service
Tests the complete workflow from data source to analysis results
"""

import unittest
import asyncio
import tempfile
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root))

from tests.unit.data_analytics.test_data.sample_data_generator import SampleDataGenerator
from tools.services.data_analytics_service.services.metadata_service import MetadataDiscoveryService
from tools.data_analytics_tools import metadata_discovery, data_understanding, compare_schemas

class TestDataAnalyticsIntegration(unittest.TestCase):
    """Integration tests for complete data analytics workflows"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with sample data"""
        cls.data_generator = SampleDataGenerator()
        
        # Create comprehensive test data
        cls.db_config = cls.data_generator.create_test_database_config("sqlite")
        cls.file_configs = cls.data_generator.create_test_file_configs()
        
        cls.service = MetadataDiscoveryService()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        cls.data_generator.cleanup()
    
    def test_complete_database_analysis_workflow(self):
        """Test complete workflow: discovery -> understanding -> export"""
        # Step 1: Metadata Discovery
        db_metadata = self.service.discover_database_metadata(self.db_config)
        
        # Verify discovery results
        self.assertIn('source_info', db_metadata)
        self.assertIn('tables', db_metadata)
        self.assertIn('columns', db_metadata)
        self.assertGreater(len(db_metadata['tables']), 0)
        self.assertGreater(len(db_metadata['columns']), 0)
        
        # Step 2: Data Understanding (synchronous version for testing)
        from tools.data_analytics_tools import _analyze_data_quality_patterns, _infer_business_rules
        
        # Analyze data quality patterns
        quality_analysis = _analyze_data_quality_patterns(db_metadata)
        self.assertIn('overall_score', quality_analysis)
        self.assertIn('quality_issues', quality_analysis)
        
        # Infer business rules
        business_rules = _infer_business_rules(db_metadata)
        self.assertIsInstance(business_rules, list)
        
        # Step 3: Export results
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            export_path = tmp_file.name
        
        try:
            success = self.service.export_metadata(db_metadata, export_path, 'json')
            self.assertTrue(success)
            
            # Verify exported file
            export_file = Path(export_path)
            self.assertTrue(export_file.exists())
            self.assertGreater(export_file.stat().st_size, 0)
            
            # Verify content can be loaded back
            with open(export_path, 'r') as f:
                loaded_data = json.load(f)
            
            self.assertEqual(len(loaded_data['tables']), len(db_metadata['tables']))
            self.assertEqual(len(loaded_data['columns']), len(db_metadata['columns']))
        
        finally:
            Path(export_path).unlink(missing_ok=True)
    
    def test_complete_file_analysis_workflow(self):
        """Test complete workflow for file analysis"""
        excel_config = self.file_configs['excel']
        
        # Step 1: Metadata Discovery
        file_metadata = self.service.discover_file_metadata(excel_config)
        
        # Verify discovery results
        self.assertIn('source_info', file_metadata)
        self.assertIn('tables', file_metadata)  # Sheets as tables
        self.assertIn('columns', file_metadata)
        
        # Verify we have expected Excel sheets
        table_names = [t['table_name'] for t in file_metadata['tables']]
        expected_sheets = ['Import_Declarations', 'Export_Declarations', 'Company_Master', 'Product_Catalog']
        
        for expected_sheet in expected_sheets:
            self.assertIn(expected_sheet, table_names)
        
        # Step 2: Get summary statistics
        summary = self.service.get_summary_statistics(file_metadata)
        
        self.assertIn('totals', summary)
        self.assertIn('table_statistics', summary)
        self.assertIn('column_statistics', summary)
        
        # Verify totals
        totals = summary['totals']
        self.assertEqual(totals['tables'], len(file_metadata['tables']))
        self.assertEqual(totals['columns'], len(file_metadata['columns']))
        
        # Step 3: Analyze business patterns
        if 'business_patterns' in file_metadata:
            patterns = file_metadata['business_patterns']
            self.assertIn('naming_conventions', patterns)
            self.assertIn('table_categories', patterns)
    
    def test_multi_source_discovery_and_comparison(self):
        """Test discovering from multiple sources and comparing them"""
        # Step 1: Discover from multiple sources
        sources = [
            {
                'name': 'database_source',
                **self.db_config
            },
            {
                'name': 'excel_source',
                **self.file_configs['excel']
            },
            {
                'name': 'csv_source',
                **self.file_configs['csv']
            }
        ]
        
        multi_results = self.service.discover_multiple_sources(sources)
        
        # Verify multi-source results
        self.assertIn('sources', multi_results)
        self.assertIn('errors', multi_results)
        self.assertIn('summary', multi_results)
        
        # Should have successful results
        self.assertGreater(len(multi_results['sources']), 0)
        
        # Step 2: Compare schemas between sources
        if len(multi_results['sources']) >= 2:
            source_names = list(multi_results['sources'].keys())
            source1_metadata = multi_results['sources'][source_names[0]]
            source2_metadata = multi_results['sources'][source_names[1]]
            
            comparison = self.service.compare_schemas(source1_metadata, source2_metadata)
            
            # Verify comparison results
            self.assertIn('comparison_time', comparison)
            self.assertIn('table_comparison', comparison)
            self.assertIn('column_comparison', comparison)
            self.assertIn('relationship_comparison', comparison)
            
            # Verify similarity scores
            table_comp = comparison['table_comparison']
            self.assertIn('similarity_score', table_comp)
            self.assertIsInstance(table_comp['similarity_score'], (int, float))
            self.assertGreaterEqual(table_comp['similarity_score'], 0.0)
            self.assertLessEqual(table_comp['similarity_score'], 1.0)
    
    def test_error_handling_and_recovery(self):
        """Test error handling throughout the workflow"""
        # Test with invalid database config
        invalid_db_config = {
            "type": "postgresql",
            "host": "nonexistent.host.com",
            "database": "nonexistent_db",
            "username": "fake_user",
            "password": "fake_pass",
            "port": 12345
        }
        
        # Should handle error gracefully
        try:
            self.service.discover_database_metadata(invalid_db_config)
            self.fail("Should have raised an exception for invalid config")
        except Exception as e:
            # Should be a meaningful error
            self.assertIsInstance(e, Exception)
            self.assertIn("Failed to discover", str(e))
        
        # Test with invalid file config
        invalid_file_config = {
            "file_path": "/nonexistent/path/file.xlsx"
        }
        
        try:
            self.service.discover_file_metadata(invalid_file_config)
            self.fail("Should have raised an exception for invalid file")
        except Exception as e:
            self.assertIsInstance(e, Exception)
    
    def test_data_quality_assessment_workflow(self):
        """Test data quality assessment across sources"""
        # Get metadata from database
        db_metadata = self.service.discover_database_metadata(self.db_config)
        
        # Assess data quality
        from tools.services.data_analytics_service.utils.data_validator import DataValidator
        validator = DataValidator()
        
        # Validate metadata structure
        is_valid, errors = validator.validate_metadata_structure(db_metadata)
        self.assertTrue(is_valid, f"Metadata should be valid: {errors}")
        
        # Check data consistency
        consistency_report = validator.check_data_consistency(db_metadata)
        self.assertIn('consistent', consistency_report)
        self.assertIn('issues', consistency_report)
        self.assertIn('warnings', consistency_report)
        
        # Get summary statistics
        summary = self.service.get_summary_statistics(db_metadata)
        self.assertIn('data_quality_overview', summary)
        
        quality_overview = summary['data_quality_overview']
        if 'avg_data_quality_score' in quality_overview:
            self.assertIsInstance(quality_overview['avg_data_quality_score'], (int, float))
            self.assertGreaterEqual(quality_overview['avg_data_quality_score'], 0.0)
            self.assertLessEqual(quality_overview['avg_data_quality_score'], 1.0)
    
    def test_configuration_and_customization(self):
        """Test configuration management and customization"""
        from tools.services.data_analytics_service.utils.config_manager import ConfigManager
        
        # Test with custom configuration
        config_manager = ConfigManager()
        
        # Create custom database config
        custom_db_config = config_manager.create_database_connection_config(
            db_type="sqlite",
            host="localhost",
            database=self.db_config['database'],
            username="test",
            password="test",
            include_data_analysis=True,
            sample_size=500
        )
        
        # Test discovery with custom config
        metadata = self.service.discover_database_metadata(custom_db_config)
        self.assertIsNotNone(metadata)
        
        # Test file config creation
        custom_file_config = config_manager.create_file_config(
            file_path=self.file_configs['csv']['file_path'],
            file_type="csv",
            include_data_analysis=True
        )
        
        file_metadata = self.service.discover_file_metadata(custom_file_config)
        self.assertIsNotNone(file_metadata)
    
    def test_performance_and_scalability(self):
        """Test performance characteristics and scalability"""
        import time
        
        # Measure discovery time
        start_time = time.time()
        metadata = self.service.discover_database_metadata(self.db_config)
        discovery_time = time.time() - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(discovery_time, 30.0, "Discovery should complete within 30 seconds")
        
        # Verify we got reasonable amount of data
        self.assertGreater(len(metadata['tables']), 0)
        self.assertGreater(len(metadata['columns']), 0)
        
        # Test summary statistics performance
        start_time = time.time()
        summary = self.service.get_summary_statistics(metadata)
        summary_time = time.time() - start_time
        
        self.assertLess(summary_time, 5.0, "Summary should complete within 5 seconds")
        self.assertIsNotNone(summary)
    
    def test_export_formats_and_compatibility(self):
        """Test different export formats and compatibility"""
        metadata = self.service.discover_database_metadata(self.db_config)
        
        # Test JSON export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_file:
            json_path = json_file.name
        
        try:
            success = self.service.export_metadata(metadata, json_path, 'json')
            self.assertTrue(success)
            
            # Verify JSON is valid
            with open(json_path, 'r') as f:
                loaded_json = json.load(f)
            self.assertIsInstance(loaded_json, dict)
            
        finally:
            Path(json_path).unlink(missing_ok=True)
        
        # Test CSV export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as csv_file:
            csv_path = csv_file.name
        
        try:
            success = self.service.export_metadata(metadata, csv_path, 'csv')
            self.assertTrue(success)
            
            # Should create multiple CSV files
            tables_csv = csv_path.replace('.csv', '_tables.csv')
            columns_csv = csv_path.replace('.csv', '_columns.csv')
            
            self.assertTrue(Path(tables_csv).exists())
            self.assertTrue(Path(columns_csv).exists())
            
        finally:
            for path in [csv_path, csv_path.replace('.csv', '_tables.csv'), csv_path.replace('.csv', '_columns.csv')]:
                Path(path).unlink(missing_ok=True)
    
    def test_end_to_end_realistic_scenario(self):
        """Test end-to-end realistic data analysis scenario"""
        # Scenario: Analyze a database and Excel file, compare them, and generate insights
        
        # Step 1: Discover database metadata
        print("Step 1: Discovering database metadata...")
        db_metadata = self.service.discover_database_metadata(self.db_config)
        self.assertGreater(len(db_metadata['tables']), 0)
        
        # Step 2: Discover Excel metadata
        print("Step 2: Discovering Excel metadata...")
        excel_metadata = self.service.discover_file_metadata(self.file_configs['excel'])
        self.assertGreater(len(excel_metadata['tables']), 0)
        
        # Step 3: Generate summaries
        print("Step 3: Generating summaries...")
        db_summary = self.service.get_summary_statistics(db_metadata)
        excel_summary = self.service.get_summary_statistics(excel_metadata)
        
        self.assertIn('totals', db_summary)
        self.assertIn('totals', excel_summary)
        
        # Step 4: Compare schemas
        print("Step 4: Comparing schemas...")
        comparison = self.service.compare_schemas(db_metadata, excel_metadata)
        
        self.assertIn('table_comparison', comparison)
        self.assertIn('similarity_score', comparison['table_comparison'])
        
        # Step 5: Export comprehensive report
        print("Step 5: Exporting comprehensive report...")
        
        comprehensive_report = {
            "analysis_type": "end_to_end_comparison",
            "database_analysis": {
                "metadata": db_metadata,
                "summary": db_summary
            },
            "excel_analysis": {
                "metadata": excel_metadata,
                "summary": excel_summary
            },
            "comparison": comparison,
            "insights": {
                "total_data_sources": 2,
                "total_tables": db_summary['totals']['tables'] + excel_summary['totals']['tables'],
                "total_columns": db_summary['totals']['columns'] + excel_summary['totals']['columns'],
                "schema_similarity": comparison['table_comparison']['similarity_score']
            }
        }
        
        # Export comprehensive report
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as report_file:
            report_path = report_file.name
        
        try:
            with open(report_path, 'w') as f:
                json.dump(comprehensive_report, f, indent=2, default=str)
            
            # Verify report
            self.assertTrue(Path(report_path).exists())
            
            with open(report_path, 'r') as f:
                loaded_report = json.load(f)
            
            self.assertIn('analysis_type', loaded_report)
            self.assertIn('insights', loaded_report)
            self.assertEqual(loaded_report['analysis_type'], 'end_to_end_comparison')
            
            print(f"✅ End-to-end analysis completed successfully!")
            print(f"   📊 Analyzed {loaded_report['insights']['total_data_sources']} data sources")
            print(f"   📋 Found {loaded_report['insights']['total_tables']} tables total")
            print(f"   📝 Found {loaded_report['insights']['total_columns']} columns total")
            print(f"   🔗 Schema similarity: {loaded_report['insights']['schema_similarity']:.2%}")
        
        finally:
            Path(report_path).unlink(missing_ok=True)

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)