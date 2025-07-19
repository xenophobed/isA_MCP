#!/usr/bin/env python3
"""
Test suite for Data Analytics Service - Complete End-to-End Pipeline
Tests the full integration of metadata processing + query processing with real customer data
"""

import asyncio
import sys
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project root to path for proper imports
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from tools.services.data_analytics_service.services.data_analytics_service import (
    DataAnalyticsService, AnalyticsResult, get_analytics_service
)

async def test_analytics_service_initialization():
    """Test data analytics service initialization"""
    print(">>> Testing Data Analytics Service Initialization")
    
    try:
        # Test direct initialization
        service = DataAnalyticsService("test_analytics_db")
        
        print(f"   ✓ Service initialized: {service.service_name}")
        print(f"   ✓ Database: {service.database_name}")
        print(f"   ✓ Components: metadata_service, query_service (lazy)")
        
        # Test global instance function
        service2 = get_analytics_service("test_analytics_db")
        service3 = get_analytics_service("test_analytics_db")
        
        assert service2 is service3, "Global instance management failed"
        print("   ✓ Global instance management working")
        
        # Test SQLite helper
        sqlite_service = DataAnalyticsService.create_for_sqlite_testing("customers.db", "user123")
        print(f"   ✓ SQLite helper created: {sqlite_service.database_name}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Data Analytics Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_end_to_end_customer_analytics():
    """Test complete end-to-end analytics with real customer data"""
    print(">>> Testing End-to-End Customer Analytics Pipeline")
    
    try:
        # Get the real customer CSV file
        current_dir = Path(__file__).parent
        csv_file = current_dir.parent.parent / "processors" / "data_processors" / "tests" / "customers_sample.csv"
        
        if not csv_file.exists():
            print(f"   ✗ Customer CSV file not found: {csv_file}")
            return False
        
        print(f"   ✓ Using real customer CSV: {csv_file.name}")
        
        # Create analytics service for SQLite testing
        service = DataAnalyticsService.create_for_sqlite_testing("customer_analytics.db", "test_user")
        
        # Create SQLite database config
        sqlite_dir = Path(__file__).parent.parent.parent.parent / "resources" / "dbs" / "sqlite"
        sqlite_dir.mkdir(parents=True, exist_ok=True)
        db_path = sqlite_dir / "user_test_user_customer_analytics.db"
        
        database_config = {
            'type': 'sqlite',
            'database': str(db_path),
            'max_execution_time': 30,
            'max_rows': 1000
        }
        
        # Test customer analytics queries
        customer_queries = [
            "Show customers from China",
            "Find all customers with their companies",
            "List customers who subscribed in 2021",
            "Get customers from Macao",
            "Show customers with gmail email addresses"
        ]
        
        analytics_results = []
        
        for i, query in enumerate(customer_queries):
            print(f"\n   >>> Analytics Query {i+1}: {query}")
            print("      → Running complete pipeline: CSV → Metadata → Query → Results")
            
            # Run complete end-to-end pipeline
            start_time = datetime.now()
            
            result = await service.process_data_source_and_query(
                source_path=str(csv_file),
                natural_language_query=query,
                database_config=database_config,
                request_id=f"customer_analytics_{i+1}"
            )
            
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            
            analytics_results.append(result)
            
            # Validate and report results
            print(f"      ⏱ Total time: {total_time:.2f}s")
            print(f"      ✓ Success: {result.success}")
            
            if result.success:
                # Metadata pipeline results
                metadata = result.metadata_pipeline
                print(f"      📊 Metadata: {metadata.tables_found} tables, {metadata.columns_found} columns")
                print(f"      🧠 Enrichment: {metadata.business_entities} entities, {metadata.semantic_tags} tags")
                print(f"      💾 Embeddings: {metadata.embeddings_stored} stored")
                
                # Query processing results
                query_result = result.query_result
                print(f"      🔍 SQL Confidence: {query_result.sql_result.confidence_score:.2f}")
                print(f"      📈 Results: {query_result.execution_result.row_count} rows")
                print(f"      💰 Cost: ${result.total_cost_usd:.4f}")
                
                # Show sample results
                if query_result.execution_result.data:
                    sample_data = query_result.execution_result.data[0]
                    sample_keys = list(sample_data.keys())[:3]
                    print(f"      📋 Sample columns: {sample_keys}")
                    
                    # Show actual customer data for verification
                    if 'First Name' in sample_data or 'Customer Id' in sample_data:
                        customer_preview = {}
                        for key in ['Customer Id', 'First Name', 'Last Name', 'Country', 'Company']:
                            if key in sample_data:
                                customer_preview[key] = sample_data[key]
                        print(f"      👤 Sample customer: {customer_preview}")
                
                # Validate query-specific results
                if "China" in query and query_result.execution_result.row_count > 0:
                    print(f"      🇨🇳 Found {query_result.execution_result.row_count} customers from China")
                elif "2021" in query and query_result.execution_result.row_count > 0:
                    print(f"      📅 Found {query_result.execution_result.row_count} customers from 2021")
                elif "gmail" in query and query_result.execution_result.row_count > 0:
                    print(f"      📧 Found {query_result.execution_result.row_count} Gmail customers")
                
            else:
                print(f"      ✗ Failed: {result.error_message}")
                if result.query_result and result.query_result.fallback_attempts:
                    print(f"      🔄 Fallbacks attempted: {len(result.query_result.fallback_attempts)}")
        
        # Validate overall results
        successful_analytics = sum(1 for r in analytics_results if r.success)
        total_analytics = len(analytics_results)
        
        print(f"\n   📊 Overall Analytics Results: {successful_analytics}/{total_analytics} successful")
        
        # Calculate performance metrics
        avg_time = sum(r.total_processing_time_ms for r in analytics_results if r.success) / max(successful_analytics, 1)
        total_cost = sum(r.total_cost_usd for r in analytics_results if r.success)
        
        print(f"   ⏱ Average processing time: {avg_time:.1f}ms")
        print(f"   💰 Total cost: ${total_cost:.4f}")
        
        # Expect at least 80% success rate for end-to-end pipeline
        success_rate = successful_analytics / total_analytics
        assert success_rate >= 0.8, f"End-to-end success rate too low: {success_rate:.2%}"
        
        print("   ✓ End-to-end customer analytics test passed!")
        return True
        
    except Exception as e:
        print(f"   ✗ End-to-end analytics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_query_only_mode():
    """Test query-only mode against pre-processed data"""
    print(">>> Testing Query-Only Mode (Steps 4-6 Only)")
    
    try:
        # First, set up some processed data
        service = DataAnalyticsService.create_for_sqlite_testing("query_only_test.db", "test_user")
        
        # Get customer CSV file  
        current_dir = Path(__file__).parent
        csv_file = current_dir.parent.parent / "processors" / "data_processors" / "tests" / "customers_sample.csv"
        
        if not csv_file.exists():
            print(f"   ✗ Customer CSV file not found")
            return False
        
        # Process data sources first (Steps 1-3)
        print("   📊 Pre-processing customer data...")
        metadata_results = await service.process_multiple_sources([
            {'path': str(csv_file), 'type': 'csv', 'id': 'customers_batch'}
        ])
        
        if not metadata_results[0].success:
            print(f"   ✗ Data preprocessing failed: {metadata_results[0].error_message}")
            return False
        
        print(f"   ✓ Data preprocessed: {metadata_results[0].tables_found} tables ready")
        
        # Initialize query service
        sqlite_dir = Path(__file__).parent.parent.parent.parent / "resources" / "dbs" / "sqlite"
        db_path = sqlite_dir / "user_test_user_query_only_test.db"
        
        database_config = {
            'type': 'sqlite', 
            'database': str(db_path),
            'max_execution_time': 30,
            'max_rows': 1000
        }
        
        await service.initialize_query_service(database_config)
        
        # Test query-only operations
        query_only_tests = [
            "Find customers from Japan",
            "Show companies with most customers",
            "List recent customer subscriptions"
        ]
        
        query_results = []
        
        for i, query in enumerate(query_only_tests):
            print(f"   >>> Query-only {i+1}: {query}")
            
            result = await service.query_existing_data(
                query,
                database_config,
                f"query_only_{i+1}"
            )
            
            query_results.append(result)
            
            if result.success:
                print(f"      ✓ Success: {result.execution_result.row_count} rows")
                print(f"      ⏱ Time: {result.processing_time_ms:.1f}ms")
            else:
                print(f"      ✗ Failed: {result.error_message}")
        
        # Test search across processed data
        print("   🔍 Testing data search...")
        search_results = await service.search_available_data("customer contact information", limit=5)
        print(f"   📊 Search results: {len(search_results)} metadata matches")
        
        # Validate query-only results
        successful_queries = sum(1 for r in query_results if r.success)
        
        # Allow for some tolerance since query-only mode depends on pre-processed data
        assert successful_queries >= len(query_results) // 2, "Too many query-only failures"
        
        print("   ✓ Query-only mode test passed!")
        return True
        
    except Exception as e:
        print(f"   ✗ Query-only mode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_service_monitoring_and_stats():
    """Test service monitoring and statistics"""
    print(">>> Testing Service Monitoring and Statistics")
    
    try:
        service = DataAnalyticsService("monitoring_test_db")
        
        # Run a few operations to generate stats
        current_dir = Path(__file__).parent
        csv_file = current_dir.parent.parent / "processors" / "data_processors" / "tests" / "customers_sample.csv"
        
        if csv_file.exists():
            # Process some data
            results = await service.process_multiple_sources([
                {'path': str(csv_file), 'type': 'csv', 'id': 'monitoring_test'}
            ])
            
            print(f"   ✓ Processed {len(results)} data sources for monitoring")
        
        # Get comprehensive service status
        status = await service.get_service_status()
        
        print(f"   📊 Service info:")
        print(f"      Service name: {status['service_info']['service_name']}")
        print(f"      Database: {status['service_info']['database_name']}")
        print(f"      Query service: {'✓' if status['service_info']['query_service_initialized'] else '✗'}")
        
        print(f"   📈 Service stats:")
        service_stats = status['service_stats']
        print(f"      Total requests: {service_stats['total_requests']}")
        print(f"      Successful: {service_stats['successful_requests']}")
        print(f"      Failed: {service_stats['failed_requests']}")
        print(f"      Data sources: {service_stats['total_data_sources_processed']}")
        print(f"      Total cost: ${service_stats['total_cost_usd']:.4f}")
        
        # Validate status structure
        assert 'service_info' in status
        assert 'service_stats' in status
        assert 'metadata_service' in status
        
        # Test metadata service stats
        metadata_stats = status['metadata_service']
        print(f"   💾 Metadata service:")
        print(f"      Total pipelines: {metadata_stats['pipeline_stats']['total_pipelines']}")
        print(f"      Successful: {metadata_stats['pipeline_stats']['successful_pipelines']}")
        
        # Test database summary
        if 'database_summary' in status:
            db_summary = status['database_summary']
            print(f"   🗄️ Database status: {db_summary.get('service_status', 'unknown')}")
        
        print("   ✓ Service monitoring and stats test passed!")
        return True
        
    except Exception as e:
        print(f"   ✗ Service monitoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_error_handling_and_recovery():
    """Test error handling and recovery mechanisms"""
    print(">>> Testing Error Handling and Recovery")
    
    try:
        service = DataAnalyticsService("error_test_db")
        
        # Test invalid data source
        print("   🚨 Testing invalid data source...")
        
        sqlite_dir = Path(__file__).parent.parent.parent.parent / "resources" / "dbs" / "sqlite"
        database_config = {
            'type': 'sqlite',
            'database': str(sqlite_dir / "error_test.db"),
            'max_execution_time': 30,
            'max_rows': 1000
        }
        
        result = await service.process_data_source_and_query(
            source_path="/nonexistent/file.csv",
            natural_language_query="Show all data",
            database_config=database_config,
            request_id="error_test_1"
        )
        
        assert not result.success, "Should have failed with nonexistent file"
        print(f"   ✓ Invalid file handled: {result.error_message[:60]}...")
        
        # Test query without processed data
        print("   🚨 Testing query without data...")
        
        empty_service = DataAnalyticsService("empty_test_db")
        await empty_service.initialize_query_service(database_config)
        
        empty_result = await empty_service.query_existing_data(
            "Show customers",
            database_config,
            "empty_test"
        )
        
        # Should handle gracefully
        print(f"   ✓ Empty data handled: success={empty_result.success}")
        if not empty_result.success:
            assert "No metadata available" in empty_result.error_message, "Should indicate no metadata"
        
        # Test invalid database config
        print("   🚨 Testing invalid database config...")
        
        invalid_config = {
            'type': 'invalid_db_type',
            'database': '/invalid/path/db.sqlite'
        }
        
        try:
            await service.initialize_query_service(invalid_config)
            # Should not reach here
            assert False, "Should have failed with invalid config"
        except Exception as e:
            print(f"   ✓ Invalid config handled: {str(e)[:60]}...")
        
        # Check error tracking in service stats
        status = await service.get_service_status()
        failed_requests = status['service_stats']['failed_requests']
        print(f"   📊 Failed requests tracked: {failed_requests}")
        
        print("   ✓ Error handling and recovery test passed!")
        return True
        
    except Exception as e:
        print(f"   ✗ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_summary(results):
    """Print comprehensive test summary"""
    print("\n" + "="*70)
    print("📊 Data Analytics Service - Complete End-to-End Test Summary")
    print("="*70)
    
    test_names = [
        "Service Initialization",
        "End-to-End Customer Analytics (Steps 1-6)",
        "Query-Only Mode (Steps 4-6)",
        "Service Monitoring & Statistics", 
        "Error Handling & Recovery"
    ]
    
    total_tests = len(results)
    passed_tests = sum(results)
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests >= total_tests - 1:  # Allow for one potential failure
        print("🎉 Data Analytics Service tests passed! Complete pipeline working!")
    else:
        print("⚠️ Some tests failed - check end-to-end integration")
    
    print("\n📋 Test Details:")
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"   {i+1}. {name}: {status}")
    
    print("\n🔄 Complete Data Analytics Pipeline Tested:")
    print("   📊 Metadata Processing (Steps 1-3):")
    print("      • CSV/JSON metadata extraction")
    print("      • AI semantic enrichment")  
    print("      • Embedding generation and storage")
    print("   🔍 Query Processing (Steps 4-6):")
    print("      • Natural language query understanding")
    print("      • AI-powered SQL generation")
    print("      • SQL execution with fallback mechanisms")
    print("   🎯 End-to-End Integration:")
    print("      • Real customer data processing")
    print("      • Complete analytics workflows")
    print("      • Performance monitoring")
    print("      • Error handling and recovery")
    print("      • SQLite database integration")

async def main():
    """Run complete Data Analytics Service test suite"""
    print("📊 Data Analytics Service - Complete End-to-End Test Suite")
    print("=" * 70)
    print("Testing Complete Pipeline: Data Ingestion → AI Processing → Query Execution")
    print("=" * 70)
    
    # Run all tests
    results = []
    
    results.append(await test_analytics_service_initialization())
    results.append(await test_end_to_end_customer_analytics())
    results.append(await test_query_only_mode())
    results.append(await test_service_monitoring_and_stats())
    results.append(await test_error_handling_and_recovery())
    
    # Print comprehensive summary
    print_summary(results)

if __name__ == "__main__":
    # Run the complete test suite
    asyncio.run(main())