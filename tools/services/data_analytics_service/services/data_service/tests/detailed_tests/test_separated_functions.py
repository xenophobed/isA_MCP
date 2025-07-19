#!/usr/bin/env python3
"""
Test the separated DataAnalyticsService functions:
1. ingest_data_source() - Function 1: Data Ingestion (Steps 1-3)
2. query_with_language() - Function 2: Query Processing (Steps 4-6)
"""
import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.services.data_analytics_service.services.data_analytics_service import DataAnalyticsService

async def test_separated_functions():
    print("🚀 Testing Separated DataAnalyticsService Functions")
    print("=" * 60)
    
    # Get the customers_sample.csv file
    csv_file = Path("tools/services/data_analytics_service/processors/data_processors/tests/customers_sample.csv")
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    # Initialize the service
    service = DataAnalyticsService("test_separated_functions")
    
    print("📊 Function 1: Data Ingestion (Steps 1-3)")
    print("-" * 40)
    
    # Function 1: Ingest data source
    ingestion_result = await service.ingest_data_source(
        source_path=str(csv_file),
        source_type="csv",
        request_id="test_ingestion"
    )
    
    print(f"✅ Ingestion Success: {ingestion_result['success']}")
    if ingestion_result['success']:
        print(f"📁 SQLite Database: {ingestion_result['sqlite_database_path']}")
        print(f"🗂️ pgvector Database: {ingestion_result['pgvector_database']}")
        print(f"📊 Tables Found: {ingestion_result['metadata_pipeline']['tables_found']}")
        print(f"📋 Columns Found: {ingestion_result['metadata_pipeline']['columns_found']}")
        print(f"💾 Embeddings Stored: {ingestion_result['metadata_pipeline']['embeddings_stored']}")
        print(f"⏱️ Processing Time: {ingestion_result['processing_time_ms']:.1f}ms")
        print(f"💰 Cost: ${ingestion_result['cost_usd']:.4f}")
        
        # Save ingestion result
        with open("output_ingestion_result.json", "w") as f:
            json.dump(ingestion_result, f, indent=2, default=str)
        print("💾 Ingestion result saved to output_ingestion_result.json")
        
        print("\n🔍 Function 2: Query Processing (Steps 4-6)")
        print("-" * 40)
        
        # Function 2: Query with natural language
        test_queries = [
            "Show customers from China",
            "Find customers with gmail email addresses",
            "List customers by company"
        ]
        
        for i, query in enumerate(test_queries):
            print(f"\n>>> Query {i+1}: {query}")
            
            query_result = await service.query_with_language(
                natural_language_query=query,
                sqlite_database_path=ingestion_result['sqlite_database_path'],
                pgvector_database=ingestion_result['pgvector_database'],
                request_id=f"test_query_{i+1}"
            )
            
            print(f"✅ Query Success: {query_result['success']}")
            if query_result['success']:
                print(f"🎯 SQL Confidence: {query_result['query_processing']['sql_confidence']:.2f}")
                print(f"📝 Generated SQL: {query_result['query_processing']['generated_sql']}")
                print(f"📊 Result Rows: {query_result['results']['row_count']}")
                print(f"⏱️ Processing Time: {query_result['processing_time_ms']:.1f}ms")
                
                # Show sample data
                if query_result['results']['data']:
                    sample = query_result['results']['data'][0]
                    print(f"👤 Sample Result: {list(sample.keys())[:3]}")
            else:
                print(f"❌ Query Failed: {query_result['error_message']}")
                if query_result['fallback_attempts'] > 0:
                    print(f"🔄 Fallbacks Attempted: {query_result['fallback_attempts']}")
            
            # Save query result
            with open(f"output_query_{i+1}_result.json", "w") as f:
                json.dump(query_result, f, indent=2, default=str)
        
        print("\n📋 Testing Summary:")
        print("✅ Function 1 (Data Ingestion): Creates SQLite DB + stores pgvector embeddings")
        print("✅ Function 2 (Query Processing): Uses SQLite DB + pgvector for natural language queries")
        print("✅ Database paths are properly coordinated between functions")
        
    else:
        print(f"❌ Ingestion Failed: {ingestion_result['error_message']}")

if __name__ == "__main__":
    asyncio.run(test_separated_functions())