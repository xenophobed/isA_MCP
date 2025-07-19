#!/usr/bin/env python3
"""
Step 7 Test: SQL Executor with customers_sample.csv SQLite database
Executes generated SQL with fallback mechanisms
"""
import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.services.data_analytics_service.processors.data_processors.metadata_extractor import extract_metadata
from tools.services.data_analytics_service.services.data_service.semantic_enricher import enrich_metadata
from tools.services.data_analytics_service.services.data_service.metadata_embedding import get_embedding_service
from tools.services.data_analytics_service.services.data_service.query_matcher import QueryMatcher
from tools.services.data_analytics_service.services.data_service.sql_generator import LLMSQLGenerator
from tools.services.data_analytics_service.services.data_service.sql_executor import SQLExecutor

async def test_sql_executor():
    print("🚀 Step 7: Testing SQL Executor with customers_sample.csv SQLite database")
    print("=" * 70)
    
    # Get the customers_sample.csv file
    current_dir = Path(__file__).parent
    csv_file = current_dir / "tools/services/data_analytics_service/processors/data_processors/tests/customers_sample.csv"
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return None
        
    print(f"📁 Processing: {csv_file}")
    
    try:
        # Step 1: Load semantic metadata and initialize services (from previous steps)
        print("📊 Step 1: Loading semantic metadata and initializing services...")
        raw_metadata = extract_metadata(str(csv_file))
        
        if "error" in raw_metadata:
            print(f"❌ Metadata extraction failed: {raw_metadata['error']}")
            return None
            
        semantic_metadata = await enrich_metadata(raw_metadata)
        print(f"   ✅ Semantic metadata loaded: {len(semantic_metadata.business_entities)} entities")
        
        # Initialize previous services
        embedding_service = get_embedding_service("customers_test_db")
        await embedding_service.initialize()
        query_matcher = QueryMatcher(embedding_service)
        sql_generator = LLMSQLGenerator()
        await sql_generator.initialize()
        
        # Step 2: Initialize SQL Executor for SQLite database
        print("🗃️  Step 2: Initializing SQL Executor for SQLite database...")
        
        # Use the SQLite database created in Step 1 (CSV processor)
        sql_executor = SQLExecutor.create_sqlite_executor("customers_sample.db")
        
        # Get execution statistics
        exec_stats = await sql_executor.get_execution_statistics()
        print(f"   🗃️  Database Type: {exec_stats.get('database_type', 'Unknown')}")
        print(f"   🔌 Connection Status: {exec_stats.get('connection_status', 'Unknown')}")
        if 'database_info' in exec_stats:
            db_info = exec_stats['database_info']
            print(f"   📊 Database: {db_info.get('database', 'N/A')}")
            if 'size_bytes' in db_info:
                size_mb = db_info['size_bytes'] / (1024 * 1024)
                print(f"   💾 Database Size: {size_mb:.2f} MB")
        
        # Step 3: Test SQL execution with various queries
        test_queries = [
            "Show me all customers from New York",
            "Find customers with gmail email addresses", 
            "List companies and their customer counts",
            "Get customer contact information for ID ALFKI",
            "Show me the first 10 customers ordered by name",
            "Find all customers in California"
        ]
        
        print(f"🔎 Step 3: Testing SQL execution for {len(test_queries)} queries...")
        
        execution_results = []
        
        for i, query in enumerate(test_queries):
            print(f"\n   Query {i+1}: '{query}'")
            start_time = asyncio.get_event_loop().time()
            
            try:
                # Step 3a: Generate SQL (from previous steps)
                query_context, metadata_matches = await query_matcher.match_query_to_metadata(
                    query, semantic_metadata
                )
                
                sql_generation_result = await sql_generator.generate_sql_from_context(
                    query_context, metadata_matches, semantic_metadata, query
                )
                
                print(f"      🛠️  Generated SQL: {sql_generation_result.sql}")
                print(f"      📊 LLM Confidence: {sql_generation_result.confidence_score:.2f}")
                
                # Step 3b: Execute SQL with fallbacks
                execution_result, fallback_attempts = await sql_executor.execute_sql_with_fallbacks(
                    sql_generation_result, query
                )
                
                end_time = asyncio.get_event_loop().time()
                total_duration = end_time - start_time
                
                print(f"      ⚡ Total Duration: {total_duration:.3f}s")
                print(f"      ✅ Execution Success: {execution_result.success}")
                print(f"      📈 Rows Returned: {execution_result.row_count}")
                print(f"      ⏱️  Execution Time: {execution_result.execution_time_ms:.1f}ms")
                
                if execution_result.success and execution_result.row_count > 0:
                    # Show sample of first few rows
                    sample_data = execution_result.data[:3]  # First 3 rows
                    print(f"      📋 Sample Results ({len(sample_data)} rows shown):")
                    for j, row in enumerate(sample_data):
                        # Show first few columns of each row
                        row_summary = {k: v for k, v in list(row.items())[:4]}
                        print(f"         Row {j+1}: {row_summary}")
                
                if execution_result.warnings:
                    print(f"      ⚠️  Warnings: {execution_result.warnings}")
                
                if not execution_result.success:
                    print(f"      ❌ Error: {execution_result.error_message}")
                
                if fallback_attempts:
                    print(f"      🔄 Fallback Attempts: {len(fallback_attempts)}")
                    for fb in fallback_attempts:
                        status = "✅" if fb.success else "❌"
                        print(f"         {status} {fb.strategy}: {fb.error_message or 'Success'}")
                
                # Step 3c: Validate SQL against schema
                validation_result = await sql_executor.validate_sql(sql_generation_result.sql, semantic_metadata)
                print(f"      🔍 SQL Validation: {'✅ Valid' if validation_result['is_valid'] else '❌ Invalid'}")
                if validation_result['errors']:
                    print(f"         Errors: {validation_result['errors'][:2]}")  # First 2 errors
                if validation_result['warnings']:
                    print(f"         Warnings: {validation_result['warnings'][:2]}")  # First 2 warnings
                
                # Store results
                execution_data = {
                    'query': query,
                    'total_duration': total_duration,
                    'sql_generation': {
                        'sql': sql_generation_result.sql,
                        'confidence': sql_generation_result.confidence_score,
                        'complexity': sql_generation_result.complexity_level
                    },
                    'execution_result': {
                        'success': execution_result.success,
                        'row_count': execution_result.row_count,
                        'execution_time_ms': execution_result.execution_time_ms,
                        'error_message': execution_result.error_message,
                        'warnings': execution_result.warnings,
                        'column_names': execution_result.column_names,
                        'sample_data': execution_result.data[:5] if execution_result.success else []  # First 5 rows
                    },
                    'fallback_attempts': [
                        {
                            'attempt_number': fb.attempt_number,
                            'strategy': fb.strategy,
                            'success': fb.success,
                            'error_message': fb.error_message,
                            'execution_time_ms': fb.execution_time_ms
                        }
                        for fb in fallback_attempts
                    ],
                    'validation': validation_result
                }
                
                execution_results.append(execution_data)
                
            except Exception as e:
                print(f"      ❌ Query execution failed: {e}")
                execution_results.append({
                    'query': query,
                    'total_duration': 0,
                    'execution_result': {
                        'success': False,
                        'error_message': str(e),
                        'row_count': 0
                    }
                })
        
        # Step 4: Test additional SQL Executor features
        print(f"\n🔧 Step 4: Testing additional SQL Executor features...")
        
        # Test direct SQL execution
        direct_sql = "SELECT COUNT(*) as total_customers FROM customers_sample"
        print(f"   🎯 Testing direct SQL execution: {direct_sql}")
        direct_result = await sql_executor.execute_sql_directly(direct_sql)
        print(f"      Result: {direct_result.data[0] if direct_result.success else direct_result.error_message}")
        
        # Test query optimization
        sample_sql = "SELECT * FROM customers_sample WHERE City = 'New York'"
        print(f"   ⚡ Testing query optimization...")
        optimization_result = await sql_executor.optimize_query(sample_sql, semantic_metadata)
        print(f"      Optimizations Applied: {optimization_result.get('optimizations_applied', [])}")
        print(f"      Optimized SQL: {optimization_result.get('optimized_sql', 'N/A')}")
        
        # Test query explanation
        print(f"   📖 Testing query explanation...")
        explain_result = await sql_executor.explain_query_plan(sample_sql)
        if 'error' not in explain_result:
            print(f"      Explain Plan Available: ✅")
        else:
            print(f"      Explain Plan Error: {explain_result['error']}")
        
        # Get final execution insights
        insights = await sql_executor.get_execution_insights()
        print(f"   📊 Execution Insights: {insights}")
        
        print("\n✅ Step 7 (SQL Executor) completed successfully!")
        
        # Prepare comprehensive results
        result = {
            'total_queries_tested': len(test_queries),
            'database_info': exec_stats,
            'execution_results': execution_results,
            'additional_features': {
                'direct_execution': {
                    'sql': direct_sql,
                    'success': direct_result.success,
                    'result': direct_result.data[0] if direct_result.success else None,
                    'error': direct_result.error_message
                },
                'query_optimization': optimization_result,
                'query_explanation': explain_result,
                'execution_insights': insights
            },
            'performance_summary': {
                'total_successful_executions': sum(1 for r in execution_results if r['execution_result']['success']),
                'total_failed_executions': sum(1 for r in execution_results if not r['execution_result']['success']),
                'average_execution_time_ms': sum(r['execution_result']['execution_time_ms'] for r in execution_results if r['execution_result']['success']) / max(1, sum(1 for r in execution_results if r['execution_result']['success'])),
                'total_rows_returned': sum(r['execution_result']['row_count'] for r in execution_results),
                'average_total_duration': sum(r['total_duration'] for r in execution_results) / len(execution_results),
                'fallback_usage': sum(1 for r in execution_results if r.get('fallback_attempts', [])),
                'validation_pass_rate': sum(1 for r in execution_results if r.get('validation', {}).get('is_valid', False)) / len(execution_results)
            }
        }
        
        return result
        
    except Exception as e:
        print(f"❌ SQL Executor failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Clean up resources
        if 'sql_generator' in locals():
            await sql_generator.close()

if __name__ == "__main__":
    result = asyncio.run(test_sql_executor())
    
    # Save results to file
    if result:
        output_file = Path(__file__).parent / "output_step7_sql_executor.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")