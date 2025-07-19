#!/usr/bin/env python3
"""
Step 1 Test: CSV Processor with customers_sample.csv
Processes CSV and stores in SQLite database
"""
import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.services.data_analytics_service.processors.data_processors.csv_processor import CSVProcessor

def test_csv_processor():
    print("🚀 Step 1: Testing CSV Processor with customers_sample.csv")
    print("=" * 60)
    
    # Get the customers_sample.csv file
    current_dir = Path(__file__).parent
    csv_file = current_dir / "tools/services/data_analytics_service/processors/data_processors/tests/customers_sample.csv"
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return None
        
    print(f"📁 Processing: {csv_file}")
    
    try:
        # Initialize CSV processor
        processor = CSVProcessor(str(csv_file))
        
        # Get full analysis with SQLite storage
        print("🔍 Running full analysis with SQLite storage...")
        analysis = processor.get_full_analysis_with_sqlite(save_to_sqlite=True)
        
        # Print summary
        print("\n📊 CSV Analysis Summary:")
        if "error" not in analysis:
            print(f"   📋 File: {analysis['file_info']['file_name']}")
            print(f"   📏 Size: {analysis['file_info']['file_size_mb']} MB")
            print(f"   📊 Rows: {analysis['structure']['total_rows']}")
            print(f"   📋 Columns: {analysis['structure']['total_columns']}")
            print(f"   🔍 Quality Score: {analysis['data_quality']['overall_quality_score']}")
            print(f"   🏷️  Domain: {analysis['patterns']['primary_domain']}")
            
            # SQLite info
            if "sqlite_database" in analysis and analysis["sqlite_database"].get("success"):
                sqlite_info = analysis["sqlite_database"]
                print(f"\n💾 SQLite Database:")
                print(f"   📁 Path: {sqlite_info['database_path']}")
                print(f"   📊 Table: {sqlite_info['table_name']}")
                print(f"   📋 Rows stored: {sqlite_info['row_count']}")
                print(f"   💾 DB Size: {sqlite_info['database_size_mb']} MB")
            
            print("\n✅ Step 1 (CSV Processor) completed successfully!")
        else:
            print(f"❌ Error: {analysis['error']}")
            
        return analysis
        
    except Exception as e:
        print(f"❌ CSV Processor failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_csv_processor()
    
    # Save results to file
    if result:
        output_file = Path(__file__).parent / "output_step1_csv_processor.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")