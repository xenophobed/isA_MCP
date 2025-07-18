#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from tools.services.data_analytics_service.services.data_service.metadata_store_service import MetadataStoreService
import tempfile
import csv

async def test_complete_pipeline():
    print("🚀 Testing Complete 1-2-3 Pipeline with Real Database")
    
    service = MetadataStoreService('test_pipeline_db')
    
    # Create realistic test CSV
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    csv_data = [
        ['customer_id', 'order_total', 'product_category', 'purchase_date', 'shipping_state'],
        ['CUST001', '149.99', 'electronics', '2024-01-15', 'CA'],
        ['CUST002', '89.50', 'books', '2024-01-16', 'NY'],
        ['CUST003', '299.99', 'clothing', '2024-01-17', 'TX'],
        ['CUST004', '199.00', 'electronics', '2024-01-18', 'FL'],
        ['CUST005', '45.75', 'home_garden', '2024-01-19', 'WA']
    ]
    csv.writer(temp_file).writerows(csv_data)
    temp_file.close()
    
    print(f"📁 Created test CSV: {Path(temp_file.name).name}")
    print("📊 Data: 5 customer orders with categories and locations")
    
    try:
        print("\n🔄 Running complete 3-step pipeline...")
        result = await service.process_data_source(temp_file.name, pipeline_id='complete_test')
        
        print(f"\n📋 PIPELINE RESULTS:")
        print(f"Success: {result.success}")
        print(f"Pipeline ID: {result.pipeline_id}")
        print(f"Total Duration: {result.total_duration:.2f}s")
        print(f"Cost: ${result.pipeline_cost:.4f}")
        
        print(f"\n📊 STEP 1 - METADATA EXTRACTION:")
        print(f"Duration: {result.extraction_duration:.2f}s")
        print(f"Tables Found: {result.tables_found}")
        print(f"Columns Found: {result.columns_found}")
        
        print(f"\n🧠 STEP 2 - AI SEMANTIC ENRICHMENT:")
        print(f"Duration: {result.enrichment_duration:.2f}s")
        print(f"Business Entities: {result.business_entities}")
        print(f"Semantic Tags: {result.semantic_tags}")
        print(f"AI Analysis Source: {result.ai_analysis_source}")
        
        print(f"\n💾 STEP 3 - EMBEDDING STORAGE:")
        print(f"Duration: {result.storage_duration:.2f}s")
        print(f"Embeddings Stored: {result.embeddings_stored}")
        print(f"Search Ready: {result.search_ready}")
        
        # Validate each step
        step1_ok = result.tables_found > 0 and result.columns_found > 0
        step2_ok = result.business_entities > 0 and result.ai_analysis_source != 'error'
        step3_ok = result.embeddings_stored > 0 and result.search_ready
        
        print(f"\n✅ VALIDATION:")
        print(f"Step 1 (Extraction): {'✅ PASS' if step1_ok else '❌ FAIL'}")
        print(f"Step 2 (Enrichment): {'✅ PASS' if step2_ok else '❌ FAIL'}")
        print(f"Step 3 (Storage): {'✅ PASS' if step3_ok else '❌ FAIL'}")
        print(f"Overall Pipeline: {'✅ PASS' if result.success else '❌ FAIL'}")
        
        if result.error_message:
            print(f"\n⚠️ Error: {result.error_message}")
            
    finally:
        Path(temp_file.name).unlink()
        print(f"\n🧹 Cleaned up test file")

if __name__ == "__main__":
    asyncio.run(test_complete_pipeline())