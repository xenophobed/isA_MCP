#!/usr/bin/env python3
"""
DuckDB Data Importer for Test Plan Service (Version 2)

A cleaner, modular implementation using separate importer classes.
"""

import logging
import sys
from pathlib import Path

# Add current directory and base path to sys.path for imports
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_path))

# Import config and modular importers
from config import config

# Handle relative imports for direct execution
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from importers import (
        SchemaManager,
        PICSImporter,
        TestCaseImporter,
        TestMappingImporter,
        SpecificationDiscovery
    )
else:
    from .importers import (
        SchemaManager,
        PICSImporter,
        TestCaseImporter,
        TestMappingImporter,
        SpecificationDiscovery
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestPlanDuckDBImporter:
    """Main coordinator for test plan data import"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the main importer
        
        Args:
            db_path: Path to DuckDB database file (defaults to config setting)
        """
        # Set up base path
        current_file = Path(__file__).resolve()
        self.base_path = current_file.parent.parent.parent
        
        # Use config path or provided path
        if db_path is None:
            self.db_path = Path(config.duckdb_absolute_path)
        else:
            self.db_path = Path(db_path)
        
        # Initialize components
        self.schema_manager = SchemaManager(str(self.db_path))
        self.pics_importer = PICSImporter(str(self.db_path))
        self.test_importer = TestCaseImporter(str(self.db_path))
        self.mapping_importer = TestMappingImporter(str(self.db_path))
        self.spec_discovery = SpecificationDiscovery(self.base_path)
        
        logger.info(f"Initialized TestPlanDuckDBImporter")
        logger.info(f"Database (from config): {self.db_path}")
        logger.info(f"Base path: {self.base_path}")
    
    def close(self):
        """Close all database connections"""
        self.schema_manager.close()
        self.pics_importer.close()
        self.test_importer.close()
        self.mapping_importer.close()
        logger.info("All connections closed")
    
    def create_schema(self):
        """Create database schema"""
        self.schema_manager.create_schema()
    
    def import_pics_reference(self, template_path: str = None):
        """Import PICS reference data from template"""
        self.pics_importer.import_reference_from_template(template_path)
    
    def import_customer_pics(self, project_id: str, customer_excel: str):
        """Import customer-specific PICS data"""
        # First create project if it doesn't exist
        self.schema_manager.execute("""
            INSERT OR REPLACE INTO projects (project_id, project_name, customer_name)
            VALUES (?, ?, ?)
        """, (project_id, f"{project_id} Project", "Customer"))
        self.schema_manager.commit()
        
        # Import customer PICS
        self.pics_importer.import_customer_pics(project_id, customer_excel)
    
    def import_specification_subset(self, max_specs: int = 3):
        """
        Import a limited subset of specifications for testing
        
        Args:
            max_specs: Maximum number of specifications to import
        """
        # Discover specifications
        specs = self.spec_discovery.auto_discover_specifications()
        
        # Import only a subset for testing
        test_specs = specs[:max_specs]
        logger.info(f"Importing {len(test_specs)} specifications for testing")
        
        for spec_info in test_specs:
            try:
                logger.info(f"\n📋 Processing {spec_info['spec_id']}: {spec_info['spec_name']}")
                
                # Import test cases and conditions
                self.test_importer.import_specification_data(spec_info)
                
                # Extract and import test mappings
                spec_id = spec_info['spec_id']
                spec_full_name = spec_info['spec_full_name']
                
                # Get test cases for mapping extraction
                test_cases = self.test_importer.fetch_all(
                    "SELECT test_id, clause, title FROM test_cases WHERE spec_id = ?",
                    (spec_id,)
                )
                test_case_dicts = [
                    {'test_id': tc[0], 'clause': tc[1], 'title': tc[2]}
                    for tc in test_cases
                ]
                
                # Import mappings if applicable
                if spec_full_name.endswith('-2'):
                    self.mapping_importer.extract_and_import_mappings(
                        spec_id, spec_full_name, test_case_dicts
                    )
                
            except Exception as e:
                logger.error(f"Failed to import specification {spec_info['spec_id']}: {e}")
                import traceback
                traceback.print_exc()
    
    def import_specifications_full(self):
        """Import all 3GPP specifications (full version)"""
        # Discover specifications
        specs = self.spec_discovery.auto_discover_specifications()
        
        # Import each specification
        for spec_info in specs:
            try:
                # Import test cases and conditions
                self.test_importer.import_specification_data(spec_info)
                
                # Extract and import test mappings
                spec_id = spec_info['spec_id']
                spec_full_name = spec_info['spec_full_name']
                
                # Get test cases for mapping extraction
                test_cases = self.test_importer.fetch_all(
                    "SELECT test_id, clause, title FROM test_cases WHERE spec_id = ?",
                    (spec_id,)
                )
                test_case_dicts = [
                    {'test_id': tc[0], 'clause': tc[1], 'title': tc[2]}
                    for tc in test_cases
                ]
                
                # Import mappings if applicable
                if spec_full_name.endswith('-2'):
                    self.mapping_importer.extract_and_import_mappings(
                        spec_id, spec_full_name, test_case_dicts
                    )
                
            except Exception as e:
                logger.error(f"Failed to import specification {spec_info['spec_id']}: {e}")
    
    def run_quick_test(self):
        """Run a quick test with limited data"""
        logger.info("\n" + "🧪 " * 20)
        logger.info("  RUNNING QUICK TEST IMPORT")
        logger.info("🧪 " * 20)
        
        # 1. Create schema
        self.create_schema()
        
        # 2. Import PICS reference data
        self.import_pics_reference()
        
        # 3. Import subset of specifications
        self.import_specification_subset(max_specs=2)
        
        # 4. Import test customer data if available
        test_customer_file = self.base_path / "data_source/test_cases/Interlab_EVO_Feature_Spreadsheet_PDX-256_PDX-256_PICS_All_2025-09-20_18_58_46.xlsx"
        if test_customer_file.exists():
            self.import_customer_pics('PDX-256', str(test_customer_file))
        
        # 5. Verify import
        self.verify_import()
        
        logger.info("\n✅ Quick test import completed successfully!")
    
    def run_full_import(self):
        """Run complete data import pipeline"""
        logger.info("\n" + "🚀 " * 20)
        logger.info("  STARTING FULL DATA IMPORT TO DUCKDB (V2)")
        logger.info("🚀 " * 20)
        
        # 1. Create schema
        self.create_schema()
        
        # 2. Import PICS reference data
        self.import_pics_reference()
        
        # 3. Import all 3GPP specifications
        self.import_specifications_full()
        
        # 4. Import test customer data if available
        test_customer_file = self.base_path / "data_source/test_cases/Interlab_EVO_Feature_Spreadsheet_PDX-256_PDX-256_PICS_All_2025-09-20_18_58_46.xlsx"
        if test_customer_file.exists():
            self.import_customer_pics('PDX-256', str(test_customer_file))
        
        # 5. Verify import
        self.verify_import()
        
        logger.info("\n✅ Full data import completed successfully!")
    
    def verify_import(self):
        """Verify imported data"""
        logger.info("\n" + "=" * 70)
        logger.info("VERIFYING IMPORTED DATA")
        logger.info("=" * 70)
        
        # Check specifications
        result = self.schema_manager.fetch_all("SELECT spec_id, spec_name FROM specifications")
        logger.info(f"Specifications: {len(result)} records")
        for spec_id, spec_name in result[:5]:  # Show first 5
            logger.info(f"  - {spec_id}: {spec_name}")
        
        # Check PICS reference
        result = self.schema_manager.fetch_one("SELECT COUNT(*) FROM pics_reference")
        logger.info(f"PICS reference items: {result[0] if result else 0} records")
        
        # Check by type
        result = self.schema_manager.fetch_all(
            "SELECT item_type, COUNT(*) FROM pics_reference GROUP BY item_type"
        )
        for item_type, count in result:
            logger.info(f"  - {item_type}: {count} items")
        
        # Check test cases
        result = self.schema_manager.fetch_all(
            "SELECT spec_id, COUNT(*) FROM test_cases GROUP BY spec_id"
        )
        total_tests = sum(count for _, count in result)
        logger.info(f"Test cases: {total_tests} total across {len(result)} specifications")
        
        # Check conditions
        result = self.schema_manager.fetch_one("SELECT COUNT(*) FROM conditions")
        logger.info(f"Conditions: {result[0] if result else 0} records")
        
        # Check test mappings
        result = self.schema_manager.fetch_one("SELECT COUNT(*) FROM test_mappings")
        logger.info(f"Test mappings: {result[0] if result else 0} records")
        
        # Check project PICS if any
        result = self.schema_manager.fetch_one("SELECT COUNT(*) FROM project_pics")
        if result and result[0] > 0:
            logger.info(f"Project PICS: {result[0]} records")
            
            # Show support summary
            result = self.schema_manager.fetch_all("""
                SELECT pr.item_type, COUNT(*) as total,
                       SUM(CASE WHEN pp.supported THEN 1 ELSE 0 END) as supported
                FROM project_pics pp
                JOIN pics_reference pr ON pp.pics_id = pr.pics_id
                GROUP BY pr.item_type
            """)
            logger.info("  Project PICS support by type:")
            for item_type, total, supported in result:
                logger.info(f"    {item_type}: {supported}/{total} supported")
        
        logger.info("\n✅ Data import verification complete")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Plan Data Importer v2')
    parser.add_argument('--quick', action='store_true', help='Run quick test with limited data')
    parser.add_argument('--db', type=str, help='Database file path')
    
    args = parser.parse_args()
    
    importer = TestPlanDuckDBImporter(args.db)
    try:
        if args.quick:
            importer.run_quick_test()
        else:
            importer.run_full_import()
    finally:
        importer.close()


if __name__ == "__main__":
    main()