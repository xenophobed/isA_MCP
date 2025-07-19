#!/usr/bin/env python3
"""
Step 2 Test: Metadata Extractor with customers_sample.csv
Extracts standardized metadata from CSV file
"""
import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.services.data_analytics_service.processors.data_processors.metadata_extractor import MetadataExtractor, extract_metadata

def test_metadata_extractor():
    print("🚀 Step 2: Testing Metadata Extractor with customers_sample.csv")
    print("=" * 60)
    
    # Get the customers_sample.csv file
    current_dir = Path(__file__).parent
    csv_file = current_dir / "tools/services/data_analytics_service/processors/data_processors/tests/customers_sample.csv"
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return None
        
    print(f"📁 Processing: {csv_file}")
    
    try:
        # Initialize metadata extractor
        extractor = MetadataExtractor()
        print(f"🔧 Supported sources: {extractor.get_supported_sources()}")
        
        # Extract metadata
        print("🔍 Extracting metadata...")
        metadata = extractor.extract_metadata(str(csv_file))
        
        # Print summary
        print("\n📊 Metadata Extraction Summary:")
        if "error" not in metadata:
            source_info = metadata.get('source_info', {})
            print(f"   📋 Source type: {source_info.get('type', 'unknown')}")
            print(f"   📊 Tables found: {len(metadata.get('tables', []))}")
            print(f"   📋 Columns found: {len(metadata.get('columns', []))}")
            
            # Show table info
            if metadata['tables']:
                table = metadata['tables'][0]
                print(f"   📊 Table: {table['table_name']}")
                print(f"   📋 Records: {table['record_count']}")
                print(f"   📏 Columns: {table['column_count']}")
            
            # Show column samples
            if metadata['columns']:
                print(f"\n📋 Column Analysis (first 5):")
                for i, col in enumerate(metadata['columns'][:5]):
                    print(f"   {i+1}. {col['column_name']} ({col['data_type']}) - {col['business_type']}")
            
            # Data quality
            if metadata['data_quality']:
                quality = metadata['data_quality']
                print(f"\n🔍 Data Quality:")
                print(f"   📊 Overall Score: {quality.get('overall_quality_score', 'N/A')}")
                print(f"   📋 Completeness: {quality.get('completeness_percentage', 'N/A')}%")
            
            # Business patterns
            if metadata['business_patterns']:
                patterns = metadata['business_patterns']
                print(f"\n🏷️  Business Patterns:")
                print(f"   📊 Primary Domain: {patterns.get('primary_domain', 'N/A')}")
                print(f"   📋 Confidence: {patterns.get('confidence', 'N/A')}")
            
            # Extraction info
            extraction_info = metadata.get('extraction_info', {})
            print(f"\n⏱️  Extraction Performance:")
            print(f"   📊 Duration: {extraction_info.get('extraction_duration_seconds', 'N/A')}s")
            print(f"   ✅ Success: {extraction_info.get('success', False)}")
            
            print("\n✅ Step 2 (Metadata Extractor) completed successfully!")
        else:
            print(f"❌ Error: {metadata['error']}")
            
        return metadata
        
    except Exception as e:
        print(f"❌ Metadata Extractor failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_metadata_extractor()
    
    # Save results to file
    if result:
        output_file = Path(__file__).parent / "output_step2_metadata_extractor.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")