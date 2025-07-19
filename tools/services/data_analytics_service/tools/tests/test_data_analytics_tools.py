#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for data_analytics_tools.py
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.services.data_analytics_service.tools.data_analytics_tools import DataAnalyticsTool

async def test_data_ingestion():
    """Test data ingestion functionality"""
    print("Test 1: Data Ingestion Functionality")
    print("="*50)
    
    analytics_tool = DataAnalyticsTool()
    
    # Get the test CSV file
    test_csv = Path(__file__).parent.parent.parent / "processors" / "data_processors" / "tests" / "customers_sample.csv"
    
    print(f"Input Parameters:")
    print(f"  Source Path: {test_csv}")
    print(f"  Database Name: test_ingestion_db")
    print(f"  Source Type: csv")
    print()
    
    if not test_csv.exists():
        print(f"ERROR: Test CSV file not found: {test_csv}")
        print("Please ensure the customers_sample.csv file exists")
        return False
    
    try:
        print("Testing data ingestion...")
        
        result = await analytics_tool.ingest_data_source(
            source_path=str(test_csv),
            database_name="test_ingestion_db",
            source_type="csv",
            request_id="test_ingestion_1"
        )
        
        print("Raw Response:")
        print(result)
        print()
        
        # Parse and analyze
        result_data = json.loads(result)
        
        print("Parsed Response Analysis:")
        print(f"  Status: {result_data.get('status', 'unknown')}")
        print(f"  Operation: {result_data.get('operation', 'unknown')}")
        
        if result_data.get('status') == 'success':
            data = result_data.get('data', {})
            print(f"  Request ID: {data.get('request_id', 'N/A')}")
            print(f"  SQLite Database Path: {data.get('sqlite_database_path', 'N/A')}")
            print(f"  pgvector Database: {data.get('pgvector_database', 'N/A')}")
            
            # Metadata pipeline verification
            pipeline = data.get('metadata_pipeline', {})
            print(f"  Tables Found: {pipeline.get('tables_found', 'N/A')}")
            print(f"  Columns Found: {pipeline.get('columns_found', 'N/A')}")
            print(f"  Business Entities: {pipeline.get('business_entities', 'N/A')}")
            print(f"  Semantic Tags: {pipeline.get('semantic_tags', 'N/A')}")
            print(f"  Embeddings Stored: {pipeline.get('embeddings_stored', 'N/A')}")
            print(f"  Search Ready: {pipeline.get('search_ready', 'N/A')}")
            
            # Performance metrics
            print(f"  Processing Time: {data.get('processing_time_ms', 'N/A')}ms")
            print(f"  Cost: ${data.get('cost_usd', 'N/A')}")
            
            # Verify key components
            if data.get('sqlite_database_path') and data.get('pgvector_database'):
                print("SUCCESS: Database paths generated successfully")
            else:
                print("WARNING: Missing database path information")
                
            if pipeline.get('embeddings_stored', 0) > 0:
                print("SUCCESS: Embeddings stored successfully")
            else:
                print("WARNING: No embeddings stored")
        else:
            print(f"ERROR: Ingestion failed: {result_data.get('message', 'Unknown error')}")
            return False
        
        print("Test 1 PASSED")
        return True
        
    except Exception as e:
        print(f"ERROR: Test 1 FAILED: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

async def test_query_processing():
    """Test query processing functionality"""
    print("\nTest 2: Query Processing Functionality")
    print("="*50)
    
    analytics_tool = DataAnalyticsTool()
    
    # First, we need to ingest some data
    test_csv = Path(__file__).parent.parent.parent / "processors" / "data_processors" / "tests" / "customers_sample.csv"
    
    if not test_csv.exists():
        print(f"ERROR: Test CSV file not found: {test_csv}")
        return False
    
    try:
        print("First ingesting test data...")
        
        # Ingest data first
        ingestion_result = await analytics_tool.ingest_data_source(
            source_path=str(test_csv),
            database_name="test_query_db",
            source_type="csv",
            request_id="test_query_ingestion"
        )
        
        ingestion_data = json.loads(ingestion_result)
        
        if ingestion_data.get('status') != 'success':
            print(f"ERROR: Data ingestion failed: {ingestion_data.get('message', 'Unknown error')}")
            return False
        
        sqlite_path = ingestion_data['data']['sqlite_database_path']
        pgvector_db = ingestion_data['data']['pgvector_database']
        
        print(f"SUCCESS: Data ingested successfully")
        print(f"  SQLite Path: {sqlite_path}")
        print(f"  pgvector DB: {pgvector_db}")
        
        # Test different queries
        test_queries = [
            "Show customers from China",
            "Find customers with gmail email addresses",
            "List all customers with their companies"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\nTesting Query {i}: {query}")
            
            result = await analytics_tool.query_with_language(
                natural_language_query=query,
                sqlite_database_path=sqlite_path,
                pgvector_database=pgvector_db,
                request_id=f"test_query_{i}"
            )
            
            print("Raw Response:")
            print(result)
            print()
            
            result_data = json.loads(result)
            
            print("Query Analysis:")
            print(f"  Status: {result_data.get('status', 'unknown')}")
            
            if result_data.get('status') == 'success':
                data = result_data.get('data', {})
                print(f"  Request ID: {data.get('request_id', 'N/A')}")
                print(f"  Original Query: {data.get('original_query', 'N/A')}")
                
                # Query processing details
                processing = data.get('query_processing', {})
                print(f"  Metadata Matches: {processing.get('metadata_matches', 'N/A')}")
                print(f"  SQL Confidence: {processing.get('sql_confidence', 'N/A')}")
                print(f"  Generated SQL: {processing.get('generated_sql', 'N/A')}")
                
                # Results
                results = data.get('results', {})
                print(f"  Row Count: {results.get('row_count', 'N/A')}")
                print(f"  Columns: {results.get('columns', 'N/A')}")
                
                # Performance
                print(f"  Processing Time: {data.get('processing_time_ms', 'N/A')}ms")
                print(f"  Fallback Attempts: {data.get('fallback_attempts', 'N/A')}")
                
                if results.get('row_count', 0) > 0:
                    print(f"SUCCESS: Query {i} returned results successfully")
                else:
                    print(f"WARNING: Query {i} returned no results (may be expected)")
            else:
                print(f"ERROR: Query {i} failed: {result_data.get('message', 'Unknown error')}")
        
        print("Test 2 COMPLETED")
        return True
        
    except Exception as e:
        print(f"ERROR: Test 2 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_end_to_end_processing():
    """Test end-to-end processing functionality"""
    print("\nTest 3: End-to-End Processing")
    print("="*50)
    
    analytics_tool = DataAnalyticsTool()
    
    test_csv = Path(__file__).parent.parent.parent / "processors" / "data_processors" / "tests" / "customers_sample.csv"
    test_query = "Show customers from China with their company information"
    
    print(f"Input Parameters:")
    print(f"  Source Path: {test_csv}")
    print(f"  Query: {test_query}")
    print(f"  Database Name: test_e2e_db")
    print()
    
    if not test_csv.exists():
        print(f"ERROR: Test CSV file not found: {test_csv}")
        return False
    
    try:
        print("Testing end-to-end processing...")
        
        result = await analytics_tool.process_data_source_and_query(
            source_path=str(test_csv),
            natural_language_query=test_query,
            database_name="test_e2e_db",
            source_type="csv",
            request_id="test_e2e_1"
        )
        
        print("Raw Response:")
        print(result)
        print()
        
        # Parse and analyze
        result_data = json.loads(result)
        
        print("End-to-End Analysis:")
        print(f"  Status: {result_data.get('status', 'unknown')}")
        print(f"  Operation: {result_data.get('operation', 'unknown')}")
        
        if result_data.get('status') == 'success':
            data = result_data.get('data', {})
            print(f"  Request ID: {data.get('request_id', 'N/A')}")
            print(f"  Source Path: {data.get('source_path', 'N/A')}")
            print(f"  Query: {data.get('natural_language_query', 'N/A')}")
            
            # Ingestion results
            ingestion = data.get('ingestion_result', {})
            if ingestion:
                print(f"  Ingestion Success: {ingestion.get('success', 'N/A')}")
                pipeline = ingestion.get('metadata_pipeline', {})
                print(f"  Tables Found: {pipeline.get('tables_found', 'N/A')}")
                print(f"  Embeddings Stored: {pipeline.get('embeddings_stored', 'N/A')}")
            
            # Query results
            query_result = data.get('query_result', {})
            if query_result:
                print(f"  Query Success: {query_result.get('success', 'N/A')}")
                if query_result.get('success'):
                    results = query_result.get('results', {})
                    print(f"  Result Rows: {results.get('row_count', 'N/A')}")
                    processing = query_result.get('query_processing', {})
                    print(f"  SQL Confidence: {processing.get('sql_confidence', 'N/A')}")
            
            # Overall metrics
            print(f"  Total Processing Time: {data.get('total_processing_time_ms', 'N/A')}ms")
            print(f"  Total Cost: ${data.get('total_cost_usd', 'N/A')}")
            
        else:
            print(f"ERROR: End-to-end processing failed: {result_data.get('message', 'Unknown error')}")
            return False
        
        print("Test 3 PASSED")
        return True
        
    except Exception as e:
        print(f"ERROR: Test 3 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_service_status():
    """Test service status functionality"""
    print("\nTest 4: Service Status")
    print("="*50)
    
    analytics_tool = DataAnalyticsTool()
    
    try:
        print("Testing service status retrieval...")
        
        result = await analytics_tool.get_service_status(
            database_name="test_status_db"
        )
        
        print("Raw Response:")
        print(result)
        print()
        
        # Parse and analyze
        result_data = json.loads(result)
        
        print("Status Analysis:")
        print(f"  Status: {result_data.get('status', 'unknown')}")
        print(f"  Operation: {result_data.get('operation', 'unknown')}")
        
        if result_data.get('status') == 'success':
            data = result_data.get('data', {})
            
            # Service info
            service_info = data.get('service_info', {})
            print(f"  Service Name: {service_info.get('service_name', 'N/A')}")
            print(f"  Database Name: {service_info.get('database_name', 'N/A')}")
            print(f"  Query Service Initialized: {service_info.get('query_service_initialized', 'N/A')}")
            
            # Service stats
            service_stats = data.get('service_stats', {})
            print(f"  Total Requests: {service_stats.get('total_requests', 'N/A')}")
            print(f"  Successful Requests: {service_stats.get('successful_requests', 'N/A')}")
            print(f"  Failed Requests: {service_stats.get('failed_requests', 'N/A')}")
            print(f"  Total Cost: ${service_stats.get('total_cost_usd', 'N/A')}")
            
            # Metadata service
            metadata_service = data.get('metadata_service', {})
            if metadata_service:
                pipeline_stats = metadata_service.get('pipeline_stats', {})
                print(f"  Total Pipelines: {pipeline_stats.get('total_pipelines', 'N/A')}")
                print(f"  Successful Pipelines: {pipeline_stats.get('successful_pipelines', 'N/A')}")
        else:
            print(f"ERROR: Status retrieval failed: {result_data.get('message', 'Unknown error')}")
            return False
        
        print("Test 4 PASSED")
        return True
        
    except Exception as e:
        print(f"ERROR: Test 4 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all tests"""
    print("Starting data_analytics_tools.py comprehensive tests...\n")
    
    tests = [
        test_data_ingestion,
        test_query_processing,
        test_end_to_end_processing,
        test_service_status
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"ERROR: Test failed with exception: {e}")
            results.append(False)
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    test_names = [
        "Data Ingestion",
        "Query Processing", 
        "End-to-End Processing",
        "Service Status"
    ]
    
    print("\nIndividual Test Results:")
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "PASSED" if result else "FAILED"
        print(f"  {i+1}. {name}: {status}")
    
    if passed == total:
        print("\nALL TESTS PASSED!")
        print("Data Analytics Tools are working correctly!")
    else:
        print("\nSome tests failed - review output above")
        print("Common issues:")
        print("   - Missing customers_sample.csv test file")
        print("   - Database connection or configuration issues")
        print("   - AI service dependencies not available")

if __name__ == "__main__":
    asyncio.run(run_all_tests())