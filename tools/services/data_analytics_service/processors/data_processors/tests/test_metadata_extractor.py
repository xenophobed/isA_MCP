#!/usr/bin/env python3
"""
Test for Metadata Extractor Service
Simple test using CSV input to get metadata output
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata_extractor import MetadataExtractor, extract_metadata

def test_csv_metadata_extraction():
    """Test metadata extraction from CSV file"""
    
    # Get test file paths
    test_dir = Path(__file__).parent
    csv_file = test_dir / "customers_sample.csv"
    
    if not csv_file.exists():
        print(f"❌ Test file not found: {csv_file}")
        return False
    
    print(f"🧪 Testing metadata extraction from: {csv_file.name}")
    
    # Test 1: Using convenience function
    print("\n📋 Test 1: Using convenience function")
    metadata = extract_metadata(str(csv_file))
    
    if "error" in metadata:
        print(f"❌ Error: {metadata['error']}")
        return False
    
    print("✅ Metadata extraction successful!")
    print(f"   📊 Tables: {len(metadata.get('tables', []))}")
    print(f"   📋 Columns: {len(metadata.get('columns', []))}")
    print(f"   🎯 Source type: {metadata.get('extraction_info', {}).get('source_type')}")
    
    # Test 2: Using MetadataExtractor class
    print("\n📋 Test 2: Using MetadataExtractor class")
    extractor = MetadataExtractor()
    metadata2 = extractor.extract_metadata(str(csv_file))
    
    if "error" in metadata2:
        print(f"❌ Error: {metadata2['error']}")
        return False
    
    print("✅ Class-based extraction successful!")
    
    # Test 3: Check metadata structure
    print("\n📋 Test 3: Checking metadata structure")
    
    required_keys = ['source_info', 'tables', 'columns', 'extraction_info']
    for key in required_keys:
        if key in metadata:
            print(f"   ✅ {key}: Present")
        else:
            print(f"   ❌ {key}: Missing")
            return False
    
    # Test 4: Check table info
    print("\n📋 Test 4: Checking table information")
    if metadata.get('tables'):
        table = metadata['tables'][0]
        print(f"   📊 Table name: {table.get('table_name')}")
        print(f"   📊 Record count: {table.get('record_count')}")
        print(f"   📊 Column count: {table.get('column_count')}")
    
    # Test 5: Check column info
    print("\n📋 Test 5: Checking column information")
    columns = metadata.get('columns', [])
    if columns:
        print(f"   📋 Total columns: {len(columns)}")
        for i, col in enumerate(columns[:3]):  # Show first 3 columns
            print(f"   📋 Column {i+1}: {col.get('column_name')} ({col.get('data_type')}) - {col.get('business_type')}")
    
    # Test 6: Check data quality
    print("\n📋 Test 6: Checking data quality")
    quality = metadata.get('data_quality', {})
    if quality:
        print(f"   📈 Overall quality score: {quality.get('overall_quality_score')}")
        print(f"   📈 Completeness: {quality.get('completeness_percentage')}%")
    
    # Test 7: Check business patterns
    print("\n📋 Test 7: Checking business patterns")
    patterns = metadata.get('business_patterns', {})
    if patterns:
        domain_scores = patterns.get('domain_scores', {})
        primary_domain = patterns.get('primary_domain', 'unknown')
        print(f"   🎯 Primary domain: {primary_domain}")
        print(f"   🎯 Domain scores: {domain_scores}")
    
    # Test 8: Sample data
    print("\n📋 Test 8: Checking sample data")
    sample_data = metadata.get('sample_data', [])
    if sample_data:
        print(f"   📄 Sample records: {len(sample_data)}")
        if sample_data:
            first_record = sample_data[0]
            print(f"   📄 First record keys: {list(first_record.keys())}")
    
    print("\n🎉 All tests passed! Metadata extraction working correctly.")
    return True

def test_save_metadata():
    """Test saving metadata to file"""
    print("\n📋 Test: Saving metadata to file")
    
    test_dir = Path(__file__).parent
    csv_file = test_dir / "customers_sample.csv"
    output_file = test_dir / "test_metadata_output.json"
    
    # Extract metadata
    extractor = MetadataExtractor()
    metadata = extractor.extract_metadata(str(csv_file))
    
    # Save metadata
    success = extractor.save_metadata(metadata, str(output_file))
    
    if success and output_file.exists():
        print(f"✅ Metadata saved successfully to: {output_file.name}")
        
        # Verify saved file
        with open(output_file, 'r') as f:
            saved_data = json.load(f)
        
        if saved_data.get('extraction_info', {}).get('success'):
            print("✅ Saved metadata is valid")
        else:
            print("❌ Saved metadata appears invalid")
            return False
        
        # Clean up
        output_file.unlink()
        print("✅ Test file cleaned up")
        return True
    else:
        print("❌ Failed to save metadata")
        return False

def show_sample_output():
    """Show a sample of the metadata output"""
    print("\n📋 Sample Metadata Output Structure:")
    
    test_dir = Path(__file__).parent
    csv_file = test_dir / "customers_sample.csv"
    
    if not csv_file.exists():
        print("❌ Test file not found")
        return
    
    metadata = extract_metadata(str(csv_file))
    
    # Create a simplified view for display
    sample_output = {
        "extraction_info": metadata.get('extraction_info', {}),
        "source_info": metadata.get('source_info', {}),
        "tables": metadata.get('tables', [])[:1],  # Just first table
        "columns": metadata.get('columns', [])[:3],  # Just first 3 columns
        "data_quality": metadata.get('data_quality', {}),
        "business_patterns": metadata.get('business_patterns', {}),
        "sample_data": metadata.get('sample_data', [])[:2]  # Just first 2 records
    }
    
    print(json.dumps(sample_output, indent=2, default=str))

if __name__ == "__main__":
    print("🧪 Testing Metadata Extractor Service")
    print("=" * 50)
    
    # Run tests
    success = test_csv_metadata_extraction()
    
    if success:
        print("\n" + "=" * 50)
        success2 = test_save_metadata()
        
        if success2:
            print("\n" + "=" * 50)
            show_sample_output()
            
            print("\n" + "=" * 50)
            print("🎉 All tests completed successfully!")
            print("\n💡 Usage examples:")
            print("   from metadata_extractor import extract_metadata")
            print("   metadata = extract_metadata('path/to/file.csv')")
            print("   print(metadata['tables'])")
        else:
            print("\n❌ Save test failed")
    else:
        print("\n❌ Main test failed")