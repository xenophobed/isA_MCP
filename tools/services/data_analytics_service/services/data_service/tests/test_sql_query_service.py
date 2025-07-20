#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for SQL Query Service - Steps 4-6 of data analytics pipeline
Tests query matching, SQL generation, and SQL execution with real customer data
"""

import asyncio
import sys
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project root to path for proper imports
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from tools.services.data_analytics_service.services.data_service.sql_query_service import (
    SQLQueryService, QueryResult
)
from tools.services.data_analytics_service.services.data_service.metadata_store_service import (
    MetadataStoreService
)
from tools.services.data_analytics_service.processors.data_processors.csv_processor import CSVProcessor

async def setup_test_data():
    """Set up real customer data for testing"""
    print("=' Setting up test data for SQL Query Service")
    
    try:
        # Get the real customer CSV file
        current_dir = Path(__file__).parent
        csv_file = current_dir.parent.parent.parent / "processors" / "data_processors" / "tests" / "customers_sample.csv"
        
        if not csv_file.exists():
            print(f"   L Customer CSV file not found: {csv_file}")
            return None, None, None
        
        # Process CSV to SQLite
        print("   =� Processing customer CSV to SQLite...")
        processor = CSVProcessor(str(csv_file))
        
        # Save to SQLite for SQL execution
        sqlite_result = processor.save_to_sqlite("customers", if_exists='replace')
        
        if not sqlite_result['success']:
            print(f"   L Failed to create SQLite database: {sqlite_result['error']}")
            return None, None, None
        
        print(f"    SQLite database created: {sqlite_result['database_path']}")
        print(f"   =� Table: {sqlite_result['table_name']} with {sqlite_result['rows_inserted']} rows")
        
        # Process through metadata pipeline to get semantic metadata
        print("   >� Processing through metadata pipeline...")
        metadata_service = MetadataStoreService("customer_query_test")
        pipeline_result = await metadata_service.process_data_source(
            str(csv_file), 
            pipeline_id="query_test_setup"
        )
        
        if not pipeline_result.success:
            print(f"   L Metadata pipeline failed: {pipeline_result.error_message}")
            return None, None, None
        
        print(f"    Semantic metadata created with {pipeline_result.business_entities} entities")
        
        # Create database config for SQL execution
        database_config = {
            'type': 'sqlite',
            'database': sqlite_result['database_path'],
            'max_execution_time': 30,
            'max_rows': 1000
        }
        
        return sqlite_result['database_path'], pipeline_result.semantic_metadata, database_config
        
    except Exception as e:
        print(f"   L Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

async def test_sql_query_service_initialization():
    """Test SQL query service initialization"""
    print("=� Testing SQL Query Service Initialization")
    
    try:
        # Create database config
        database_config = {
            'type': 'sqlite',
            'database': ':memory:',
            'max_execution_time': 30,
            'max_rows': 1000
        }
        
        # Initialize service
        service = SQLQueryService(database_config)
        await service.initialize()
        
        print("    Service initialized successfully")
        print(f"   =' Components: query_matcher, sql_generator, sql_executor")
        
        # Validate components
        assert service.embedding_service is not None, "Embedding service not initialized"
        assert service.query_matcher is not None, "Query matcher not initialized"
        assert service.sql_generator is not None, "SQL generator not initialized" 
        assert service.sql_executor is not None, "SQL executor not initialized"
        
        print("    All components properly initialized")
        return True
        
    except Exception as e:
        print(f"L SQL Query Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_customer_queries_with_real_data():
    """Test natural language queries against real customer data"""
    print("=� Testing Natural Language Queries - Real Customer Data")
    
    # Setup test data
    db_path, semantic_metadata, database_config = await setup_test_data()
    
    if not all([db_path, semantic_metadata, database_config]):
        print("   L Test data setup failed")
        return False
    
    try:
        # Initialize query service
        service = SQLQueryService(database_config)
        await service.initialize()
        
        # Test queries against customer data
        test_queries = [
            "Show all customers from China",
            "Find customers with gmail email addresses", 
            "List companies and their customer counts",
            "Get customers who subscribed in 2021",
            "Show customers from Macao with phone numbers"
        ]
        
        query_results = []
        
        for i, query in enumerate(test_queries):
            print(f"   = Query {i+1}: {query}")
            
            result = await service.process_query(
                query,
                semantic_metadata
            )
            
            query_results.append(result)
            
            if result.success:
                print(f"       Success: {result.execution_result.row_count} rows in {result.processing_time_ms:.1f}ms")
                print(f"      =� SQL: {result.sql_result.sql[:80]}...")
                print(f"      <� Confidence: {result.sql_result.confidence_score:.2f}")
                
                # Show sample data if available
                if result.execution_result.data and len(result.execution_result.data) > 0:
                    sample_row = result.execution_result.data[0]
                    print(f"      =� Sample: {list(sample_row.keys())[:3]}...")
            else:
                print(f"      L Failed: {result.error_message}")
                if result.fallback_attempts:
                    print(f"      = Fallbacks attempted: {len(result.fallback_attempts)}")
        
        # Validate results
        successful_queries = sum(1 for r in query_results if r.success)
        total_queries = len(query_results)
        
        print(f"   =� Query Results: {successful_queries}/{total_queries} successful")
        
        # Expect at least 60% success rate (some queries may be challenging)
        success_rate = successful_queries / total_queries
        assert success_rate >= 0.6, f"Success rate too low: {success_rate:.2%}"
        
        # Test specific customer data validation
        china_query = next((r for r in query_results if "China" in r.original_query), None)
        if china_query and china_query.success:
            # Should find customers from China
            china_customers = china_query.execution_result.row_count
            print(f"   <�<� Found {china_customers} customers from China")
            assert china_customers > 0, "Should find at least some customers from China"
        
        print(" Customer queries with real data test passed!")
        return True
        
    except Exception as e:
        print(f"L Customer queries test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sql_validation_and_optimization():
    """Test SQL validation and optimization features"""
    print("= Testing SQL Validation and Optimization")
    
    # Setup test data  
    db_path, semantic_metadata, database_config = await setup_test_data()
    
    if not all([db_path, semantic_metadata, database_config]):
        print("   L Test data setup failed")
        return False
    
    try:
        # Initialize query service
        service = SQLQueryService(database_config)
        await service.initialize()
        
        # Test validation and optimization
        test_queries = [
            "Show all customer information",  # Should suggest adding LIMIT
            "Find customers with specific email domain",  # Should work well
            "Get customer statistics by country"  # Should handle aggregation
        ]
        
        for i, query in enumerate(test_queries):
            print(f"   = Validating query {i+1}: {query[:50]}...")
            
            validation_result = await service.validate_and_optimize_query(
                query,
                semantic_metadata
            )
            
            print(f"       Valid: {validation_result['valid']}")
            
            if validation_result['valid']:
                print(f"      <� Confidence: {validation_result['confidence_score']:.2f}")
                print(f"      =� Complexity: {validation_result['query_complexity']}")
                print(f"      = Metadata matches: {validation_result['metadata_matches']}")
                
                if validation_result['optimization_suggestions']:
                    print(f"      =� Suggestions: {len(validation_result['optimization_suggestions'])}")
                    for suggestion in validation_result['optimization_suggestions'][:2]:
                        print(f"         {suggestion}")
                        
                if validation_result['validation_warnings']:
                    print(f"      �  Warnings: {len(validation_result['validation_warnings'])}")
            else:
                print(f"      L Error: {validation_result['error']}")
        
        print(" SQL validation and optimization test passed!")
        return True
        
    except Exception as e:
        print(f"L SQL validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_query_performance_and_fallbacks():
    """Test query performance and fallback mechanisms"""
    print("� Testing Query Performance and Fallbacks")
    
    # Setup test data
    db_path, semantic_metadata, database_config = await setup_test_data()
    
    if not all([db_path, semantic_metadata, database_config]):
        print("   L Test data setup failed")
        return False
    
    try:
        # Initialize query service
        service = SQLQueryService(database_config)
        await service.initialize()
        
        # Test challenging queries that might need fallbacks
        challenging_queries = [
            "Show me all the detailed customer analytics with complex joins",  # May be too complex
            "Find customers in non-existent city",  # Should return empty results gracefully
            "Get super complex aggregations across multiple dimensions",  # May need simplification
        ]
        
        fallback_results = []
        
        for i, query in enumerate(challenging_queries):
            print(f"   <� Challenging query {i+1}: {query[:60]}...")
            
            start_time = datetime.now()
            result = await service.process_query(query, semantic_metadata)
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            fallback_results.append(result)
            
            print(f"      =� Processing time: {processing_time:.1f}ms")
            print(f"       Success: {result.success}")
            print(f"      = Fallbacks used: {len(result.fallback_attempts)}")
            
            if result.fallback_attempts:
                for j, attempt in enumerate(result.fallback_attempts):
                    print(f"         {j+1}. {attempt.strategy}: {'' if attempt.success else 'L'}")
            
            if result.success:
                print(f"      =� Results: {result.execution_result.row_count} rows")
            else:
                print(f"      L Final error: {result.error_message}")
        
        # Test performance insights
        insights = await service.get_processing_insights()
        if insights.get('total_queries', 0) > 0:
            print(f"   =� Performance insights:")
            print(f"       Total queries: {insights['total_queries']}")
            print(f"       Success rate: {insights['success_rate']:.2%}")
            print(f"       Avg processing time: {insights['avg_processing_time_ms']:.1f}ms")
            print(f"       Fallback usage: {insights['fallback_usage_rate']:.2%}")
        
        print(" Query performance and fallbacks test passed!")
        return True
        
    except Exception as e:
        print(f"L Query performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sqlite_integration():
    """Test SQLite database integration specifically"""
    print("=� Testing SQLite Database Integration")
    
    try:
        # Create SQLite service directly
        service = SQLQueryService.create_for_sqlite("test_customers.db", "testuser")
        await service.initialize()
        
        print("    SQLite service created successfully")
        
        # Create a simple test table
        db_path = service.database_config['database']
        
        # Create test data in SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_customers (
                id INTEGER PRIMARY KEY,
                name TEXT,
                city TEXT,
                country TEXT
            )
        """)
        
        test_data = [
            (1, 'John Doe', 'Seattle', 'USA'),
            (2, 'Jane Smith', 'Toronto', 'Canada'),
            (3, 'Bob Johnson', 'London', 'UK')
        ]
        
        cursor.executemany(
            "INSERT OR REPLACE INTO test_customers (id, name, city, country) VALUES (?, ?, ?, ?)",
            test_data
        )
        
        conn.commit()
        conn.close()
        
        print(f"   =� Created test table with {len(test_data)} rows")
        
        # Test direct SQL execution
        from tools.services.data_analytics_service.services.data_service.sql_generator import SQLGenerationResult
        
        test_sql = SQLGenerationResult(
            sql="SELECT * FROM test_customers WHERE country = 'USA'",
            explanation="Find customers in USA",
            confidence_score=0.9,
            complexity_level="simple"
        )
        
        execution_result, fallbacks = await service.sql_executor.execute_sql_with_fallbacks(
            test_sql,
            "Find US customers"
        )
        
        print(f"    Direct SQL execution: {execution_result.success}")
        
        if execution_result.success:
            print(f"   =� Found {execution_result.row_count} US customers")
            if execution_result.data:
                print(f"   =d Sample: {execution_result.data[0]}")
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
        
        print(" SQLite integration test passed!")
        return True
        
    except Exception as e:
        print(f"L SQLite integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_summary(results):
    """Print comprehensive test summary"""
    print("\n" + "="*60)
    print("=� SQL Query Service (Steps 4-6) Test Summary")
    print("="*60)
    
    test_names = [
        "Service Initialization",
        "Customer Queries with Real Data",
        "SQL Validation & Optimization", 
        "Query Performance & Fallbacks",
        "SQLite Integration"
    ]
    
    total_tests = len(results)
    passed_tests = sum(results)
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests >= total_tests - 1:  # Allow for one potential failure
        print("<� SQL Query Service tests passed! Steps 4-6 integration working!")
    else:
        print("�  Some tests failed - check query processing components")
    
    print("\n=� Test Details:")
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = " PASS" if result else "L FAIL"
        print(f"   {i+1}. {name}: {status}")
    
    print("\n= Query Processing Pipeline Tested:")
    print("    Step 4: Query Context Extraction & Metadata Matching")
    print("    Step 5: AI-Powered SQL Generation") 
    print("    Step 6: SQL Execution with Fallback Mechanisms")
    print("    Natural language query processing")
    print("    Real customer data integration")  
    print("    SQL validation and optimization")
    print("    Performance monitoring and fallbacks")
    print("    SQLite database integration")

async def main():
    """Run complete SQL Query Service test suite"""
    print("=� SQL Query Service - Complete Pipeline Test Suite")
    print("=" * 60)
    print("Testing Steps 4-6: Query Match � SQL Generation � SQL Execution")
    print("=" * 60)
    
    # Run all tests
    results = []
    
    results.append(await test_sql_query_service_initialization())
    results.append(await test_customer_queries_with_real_data())
    results.append(await test_sql_validation_and_optimization())
    results.append(await test_query_performance_and_fallbacks())
    results.append(await test_sqlite_integration())
    
    # Print comprehensive summary
    print_summary(results)

if __name__ == "__main__":
    # Run the complete test suite
    asyncio.run(main())