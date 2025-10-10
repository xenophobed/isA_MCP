#!/usr/bin/env python3
"""
Data Initialization Service

Extracts PICS, applicability, and conditions from 3GPP documents
and stores them directly in DuckDB instead of temporary JSON files.
"""

import logging
import json
import polars as pl
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import existing extractors - use importlib for modules with dashes
import importlib.util
import sys

# Import docs extractor
docs_extractor_path = Path(__file__).parent / "extractor" / "3gpp-2-docs-extractor.py"
docs_spec = importlib.util.spec_from_file_location("docs_extractor", docs_extractor_path)
docs_extractor = importlib.util.module_from_spec(docs_spec)
docs_spec.loader.exec_module(docs_extractor)

# Import pics extractor
pics_extractor_path = Path(__file__).parent / "extractor" / "3gpp-2-pics-extractor.py"
pics_spec = importlib.util.spec_from_file_location("pics_extractor", pics_extractor_path)
pics_extractor = importlib.util.module_from_spec(pics_spec)
pics_spec.loader.exec_module(pics_extractor)

# Import storage components
from .store.importers import (
    SchemaManager,
    PICSImporter, 
    TestCaseImporter,
    SpecificationDiscovery
)
from config import config

logger = logging.getLogger(__name__)


class DataInitializationService:
    """Service for extracting and initializing 3GPP data to DuckDB"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the data initialization service
        
        Args:
            db_path: Path to DuckDB database file (defaults to config setting)
        """
        self.db_path = db_path or config.duckdb_absolute_path
        
        # Initialize storage components
        self.schema_manager = SchemaManager(self.db_path)
        self.pics_importer = PICSImporter(self.db_path)
        self.test_importer = TestCaseImporter(self.db_path)
        
        # Set up paths
        self.base_path = Path(__file__).parent.parent
        self.data_source_path = self.base_path / "data_source"
        
        logger.info(f"Data initialization service initialized")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Data source: {self.data_source_path}")
    
    def initialize_schema(self):
        """Create or update database schema"""
        logger.info("Initializing database schema...")
        self.schema_manager.create_schema()
        logger.info("Database schema initialized successfully")
    
    def extract_and_store_pics(self, document_path: str, specification_id: str) -> Dict[str, Any]:
        """
        Extract PICS data from 3GPP document and store directly to DuckDB
        
        Args:
            document_path: Path to 3GPP document
            specification_id: Specification identifier (e.g., '36521-2')
            
        Returns:
            Dictionary with extraction results and statistics
        """
        logger.info(f"Extracting PICS from {document_path} for spec {specification_id}")
        
        try:
            # Extract PICS using existing extractor
            pics_extractor_instance = pics_extractor.Enhanced3GPP2PICSExtractor()
            pics_result = pics_extractor_instance.extract_all_specs_to_excel()
            pics_data = pics_result.get("extracted_specs", {})
            
            if not pics_data:
                logger.warning(f"No PICS data extracted from {document_path}")
                return {"status": "no_data", "pics_count": 0}
            
            # Transform to DuckDB format using Polars
            pics_df = self._transform_pics_to_df(pics_data, specification_id)
            
            # Store directly to DuckDB
            stored_count = self._store_pics_to_db(pics_df)
            
            logger.info(f"Successfully stored {stored_count} PICS items for {specification_id}")
            
            return {
                "status": "success",
                "specification_id": specification_id,
                "pics_count": stored_count,
                "extraction_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to extract and store PICS: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pics_count": 0
            }
    
    def extract_and_store_test_cases(self, document_path: str, specification_id: str) -> Dict[str, Any]:
        """
        Extract test cases, applicability, and conditions from 3GPP document
        and store directly to DuckDB
        
        Args:
            document_path: Path to 3GPP document
            specification_id: Specification identifier (e.g., '36521-2')
            
        Returns:
            Dictionary with extraction results and statistics
        """
        logger.info(f"Extracting test cases from {document_path} for spec {specification_id}")
        
        try:
            # Extract test data using existing extractor
            docs_extractor_instance = docs_extractor.ApplicabilityExtractor(document_path)
            test_data = docs_extractor_instance.extract_data()
            
            if not test_data:
                logger.warning(f"No test data extracted from {document_path}")
                return {"status": "no_data", "test_cases": 0, "conditions": 0}
            
            # Transform to DuckDB format using Polars
            test_cases_df, conditions_df = self._transform_test_data_to_df(test_data, specification_id)
            
            # Store directly to DuckDB
            test_count = self._store_test_cases_to_db(test_cases_df)
            condition_count = self._store_conditions_to_db(conditions_df)
            
            logger.info(f"Successfully stored {test_count} test cases and {condition_count} conditions for {specification_id}")
            
            return {
                "status": "success", 
                "specification_id": specification_id,
                "test_cases": test_count,
                "conditions": condition_count,
                "extraction_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to extract and store test cases: {e}")
            return {
                "status": "error",
                "error": str(e),
                "test_cases": 0,
                "conditions": 0
            }
    
    def process_document_batch(self, document_paths: List[str]) -> Dict[str, Any]:
        """
        Process multiple 3GPP documents in batch
        
        Args:
            document_paths: List of paths to 3GPP documents
            
        Returns:
            Dictionary with batch processing results
        """
        logger.info(f"Starting batch processing of {len(document_paths)} documents")
        
        results = {
            "total_documents": len(document_paths),
            "successful": 0,
            "failed": 0,
            "documents": []
        }
        
        for doc_path in document_paths:
            try:
                # Extract specification ID from document path/name
                spec_id = self._extract_spec_id_from_path(doc_path)
                
                # Process both PICS and test cases for each document
                pics_result = self.extract_and_store_pics(doc_path, spec_id)
                test_result = self.extract_and_store_test_cases(doc_path, spec_id)
                
                doc_result = {
                    "document_path": doc_path,
                    "specification_id": spec_id,
                    "pics_result": pics_result,
                    "test_result": test_result
                }
                
                if pics_result["status"] == "success" or test_result["status"] == "success":
                    results["successful"] += 1
                    doc_result["overall_status"] = "success"
                else:
                    results["failed"] += 1
                    doc_result["overall_status"] = "failed"
                
                results["documents"].append(doc_result)
                
            except Exception as e:
                logger.error(f"Failed to process document {doc_path}: {e}")
                results["failed"] += 1
                results["documents"].append({
                    "document_path": doc_path,
                    "overall_status": "error",
                    "error": str(e)
                })
        
        logger.info(f"Batch processing complete: {results['successful']} successful, {results['failed']} failed")
        return results
    
    def validate_and_deduplicate(self) -> Dict[str, Any]:
        """
        Validate stored data and remove duplicates
        
        Returns:
            Dictionary with validation and deduplication results
        """
        logger.info("Starting data validation and deduplication")
        
        validation_results = {
            "pics_validation": self._validate_pics_data(),
            "test_cases_validation": self._validate_test_cases_data(), 
            "conditions_validation": self._validate_conditions_data(),
            "deduplication": self._deduplicate_data()
        }
        
        logger.info("Data validation and deduplication completed")
        return validation_results
    
    def _transform_pics_to_df(self, pics_data: Dict, specification_id: str) -> pl.DataFrame:
        """Transform PICS data to Polars DataFrame for DuckDB storage"""
        records = []
        
        for pics_id, pics_info in pics_data.items():
            record = {
                "pics_id": pics_id,
                "specification": specification_id,
                "description": pics_info.get("description", ""),
                "item_type": pics_info.get("type", "feature"),
                "band_info": json.dumps(pics_info.get("band_info")) if pics_info.get("band_info") else None,
                "allowed_values": pics_info.get("allowed_values", ""),
                "default_value": pics_info.get("default_value", ""),
                "status": "active"
            }
            records.append(record)
        
        return pl.DataFrame(records)
    
    def _transform_test_data_to_df(self, test_data: Dict, specification_id: str) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Transform test data to Polars DataFrames for DuckDB storage"""
        
        # Transform test cases
        test_records = []
        condition_records = []
        
        if "test_cases" in test_data:
            for test_case in test_data["test_cases"]:
                test_record = {
                    "test_id": test_case.get("test_id", ""),
                    "spec_id": specification_id,
                    "clause": test_case.get("clause", ""),
                    "title": test_case.get("title", ""),
                    "release": test_case.get("release", ""),
                    "applicability_condition": test_case.get("applicability_condition", ""),
                    "applicability_comment": test_case.get("applicability_comment", ""),
                    "specific_ics": test_case.get("specific_ics", ""),
                    "specific_ixit": test_case.get("specific_ixit", ""),
                    "num_executions": test_case.get("num_executions", "1"),
                    "release_other_rat": test_case.get("release_other_rat", ""),
                    "standard": specification_id,
                    "version": test_case.get("version", "")
                }
                test_records.append(test_record)
        
        # Transform conditions
        if "conditions" in test_data:
            for condition in test_data["conditions"]:
                condition_record = {
                    "condition_id": condition.get("condition_id", ""),
                    "spec_id": specification_id,
                    "condition_type": condition.get("type", "Other"),
                    "definition": condition.get("definition", ""),
                    "table_index": condition.get("table_index", 0),
                    "raw_data": json.dumps(condition)
                }
                condition_records.append(condition_record)
        
        test_cases_df = pl.DataFrame(test_records) if test_records else pl.DataFrame()
        conditions_df = pl.DataFrame(condition_records) if condition_records else pl.DataFrame()
        
        return test_cases_df, conditions_df
    
    def _store_pics_to_db(self, pics_df: pl.DataFrame) -> int:
        """Store PICS DataFrame to DuckDB"""
        if pics_df.is_empty():
            return 0
        
        # Convert to records and insert row by row for compatibility
        records = pics_df.to_dicts()
        
        for record in records:
            self.schema_manager.execute("""
                INSERT OR REPLACE INTO pics_reference 
                (pics_id, specification, description, item_type, band_info, allowed_values, default_value, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("pics_id"),
                record.get("specification"),  
                record.get("description"),
                record.get("item_type"),
                record.get("band_info"),
                record.get("allowed_values"),
                record.get("default_value"),
                record.get("status")
            ))
        
        self.schema_manager.commit()
        return len(pics_df)
    
    def _store_test_cases_to_db(self, test_cases_df: pl.DataFrame) -> int:
        """Store test cases DataFrame to DuckDB"""
        if test_cases_df.is_empty():
            return 0
        
        records = test_cases_df.to_dicts()
        
        for record in records:
            self.schema_manager.execute("""
                INSERT OR REPLACE INTO test_cases 
                (test_id, spec_id, clause, title, release, applicability_condition, 
                 applicability_comment, specific_ics, specific_ixit, num_executions, 
                 release_other_rat, standard, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("test_id"),
                record.get("spec_id"),
                record.get("clause"),
                record.get("title"),
                record.get("release"),
                record.get("applicability_condition"),
                record.get("applicability_comment"),
                record.get("specific_ics"),
                record.get("specific_ixit"),
                record.get("num_executions"),
                record.get("release_other_rat"),
                record.get("standard"),
                record.get("version")
            ))
        
        self.schema_manager.commit()
        return len(test_cases_df)
    
    def _store_conditions_to_db(self, conditions_df: pl.DataFrame) -> int:
        """Store conditions DataFrame to DuckDB"""
        if conditions_df.is_empty():
            return 0
        
        records = conditions_df.to_dicts()
        
        for record in records:
            self.schema_manager.execute("""
                INSERT OR REPLACE INTO conditions 
                (condition_id, spec_id, condition_type, definition, table_index, raw_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.get("condition_id"),
                record.get("spec_id"),
                record.get("condition_type"),
                record.get("definition"),
                record.get("table_index"),
                record.get("raw_data")
            ))
        
        self.schema_manager.commit()
        return len(conditions_df)
    
    def _extract_spec_id_from_path(self, document_path: str) -> str:
        """Extract specification ID from document path"""
        path = Path(document_path)
        
        # Try to extract from filename (e.g., "36521-2.docx" -> "36521-2")
        name = path.stem
        if name.startswith("3gpp_"):
            name = name[5:]  # Remove "3gpp_" prefix
        
        # Extract spec pattern like "36521-2"
        import re
        match = re.search(r'(\d{5}-\d)', name)
        if match:
            return match.group(1)
        
        # Fallback to filename
        return name
    
    def _validate_pics_data(self) -> Dict[str, Any]:
        """Validate PICS data in database"""
        result = self.schema_manager.fetch_one("SELECT COUNT(*) FROM pics_reference")
        total_pics = result[0] if result else 0
        
        # Check for missing required fields
        result = self.schema_manager.fetch_one(
            "SELECT COUNT(*) FROM pics_reference WHERE pics_id IS NULL OR pics_id = ''"
        )
        invalid_pics = result[0] if result else 0
        
        return {
            "total_pics": total_pics,
            "invalid_pics": invalid_pics,
            "valid_pics": total_pics - invalid_pics,
            "validation_passed": invalid_pics == 0
        }
    
    def _validate_test_cases_data(self) -> Dict[str, Any]:
        """Validate test cases data in database"""
        result = self.schema_manager.fetch_one("SELECT COUNT(*) FROM test_cases")
        total_tests = result[0] if result else 0
        
        result = self.schema_manager.fetch_one(
            "SELECT COUNT(*) FROM test_cases WHERE test_id IS NULL OR test_id = ''"
        )
        invalid_tests = result[0] if result else 0
        
        return {
            "total_test_cases": total_tests,
            "invalid_test_cases": invalid_tests,
            "valid_test_cases": total_tests - invalid_tests,
            "validation_passed": invalid_tests == 0
        }
    
    def _validate_conditions_data(self) -> Dict[str, Any]:
        """Validate conditions data in database"""
        result = self.schema_manager.fetch_one("SELECT COUNT(*) FROM conditions")
        total_conditions = result[0] if result else 0
        
        result = self.schema_manager.fetch_one(
            "SELECT COUNT(*) FROM conditions WHERE condition_id IS NULL OR condition_id = ''"
        )
        invalid_conditions = result[0] if result else 0
        
        return {
            "total_conditions": total_conditions,
            "invalid_conditions": invalid_conditions,
            "valid_conditions": total_conditions - invalid_conditions,
            "validation_passed": invalid_conditions == 0
        }
    
    def _deduplicate_data(self) -> Dict[str, Any]:
        """Remove duplicate records from all tables"""
        dedup_results = {}
        
        # Deduplicate PICS
        before_pics = self.schema_manager.fetch_one("SELECT COUNT(*) FROM pics_reference")[0]
        self.schema_manager.execute("""
            CREATE OR REPLACE TABLE pics_reference AS 
            SELECT DISTINCT * FROM pics_reference
        """)
        after_pics = self.schema_manager.fetch_one("SELECT COUNT(*) FROM pics_reference")[0]
        dedup_results["pics_removed"] = before_pics - after_pics
        
        # Deduplicate test cases
        before_tests = self.schema_manager.fetch_one("SELECT COUNT(*) FROM test_cases")[0]
        self.schema_manager.execute("""
            CREATE OR REPLACE TABLE test_cases AS 
            SELECT DISTINCT * FROM test_cases
        """)
        after_tests = self.schema_manager.fetch_one("SELECT COUNT(*) FROM test_cases")[0]
        dedup_results["test_cases_removed"] = before_tests - after_tests
        
        # Deduplicate conditions
        before_conditions = self.schema_manager.fetch_one("SELECT COUNT(*) FROM conditions")[0]
        self.schema_manager.execute("""
            CREATE OR REPLACE TABLE conditions AS 
            SELECT DISTINCT * FROM conditions
        """)
        after_conditions = self.schema_manager.fetch_one("SELECT COUNT(*) FROM conditions")[0]
        dedup_results["conditions_removed"] = before_conditions - after_conditions
        
        self.schema_manager.commit()
        
        return dedup_results
    
    def close(self):
        """Close all database connections"""
        self.schema_manager.close()
        self.pics_importer.close()
        self.test_importer.close()
        logger.info("Data initialization service closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Main entry point for testing"""
    logging.basicConfig(level=logging.INFO)
    
    with DataInitializationService() as service:
        # Initialize schema
        service.initialize_schema()
        
        # Example usage - process a single document
        # doc_path = "/path/to/3gpp_document.docx"
        # result = service.extract_and_store_pics(doc_path, "36521-2")
        # print("PICS extraction result:", result)
        
        # result = service.extract_and_store_test_cases(doc_path, "36521-2") 
        # print("Test cases extraction result:", result)
        
        # Validate and deduplicate
        validation_result = service.validate_and_deduplicate()
        print("Validation result:", validation_result)


if __name__ == "__main__":
    main()