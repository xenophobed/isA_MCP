#!/usr/bin/env python3

import os
import sys
import asyncio
import pandas as pd
import numpy as np
from pathlib import Path

# Add the services directory to the path
sys.path.append('.')

# Import the GPP extractor directly
import importlib.util
spec = importlib.util.spec_from_file_location("gpp_2_docs_extractor", "services/extractor/3gpp-2-docs-extractor.py")
gpp_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gpp_module)
ApplicabilityExtractor = gpp_module.ApplicabilityExtractor

def find_working_2_docx_files():
    """Find all -2 docx files that are likely to work"""
    base_path = Path("data_source/3GPP")
    working_files = []
    
    # Known working files from previous tests
    known_working = [
        "data_source/3GPP/TS 34.229-2/34229-2-f20/34229-2-f20.docx",
        "data_source/3GPP/TS 36.521-2/36521-2-i80/36521-2-i80.docx", 
        "data_source/3GPP/TS 36.521-3/36521-3-i10/36521-3-i10.docx",
        "data_source/3GPP/TS 36.523-2/36523-2-i40/36523-2-i40.docx",
        "data_source/3GPP/TS 38.508-2/38508-2-j00/38508-2-j00.docx",
        "data_source/3GPP/TS 37.571-2/37571-2-h40/37571-2-h40.docx",
        "data_source/3GPP/TS 38.523-2/38523-2-j12/38523-2-j12.docx"
    ]
    
    for file_path in known_working:
        if os.path.exists(file_path):
            working_files.append(file_path)
    
    print(f"Found {len(working_files)} working -2 docx files")
    for f in working_files:
        print(f"  {f}")
    
    return working_files

async def test_working_files():
    """Test extraction from working -2 files"""
    print("🚀 Testing working -2 docx files...")
    
    working_files = find_working_2_docx_files()
    extractor = ApplicabilityExtractor()
    
    results = {}
    successful_extractions = 0
    
    for file_path in working_files:
        print(f"\n📄 Testing: {file_path}")
        try:
            result = await extractor.extract(file_path)
            
            test_cases = len(result.get('test_cases', []))
            c_conditions = len(result.get('c_conditions', []))
            pics_conditions = len(result.get('pics_conditions', []))
            
            results[file_path] = {
                'test_cases': test_cases,
                'c_conditions': c_conditions, 
                'pics_conditions': pics_conditions,
                'total': test_cases + c_conditions + pics_conditions
            }
            
            if results[file_path]['total'] > 0:
                successful_extractions += 1
                print(f"✅ Success: {test_cases} tests, {c_conditions} C-conditions, {pics_conditions} PICS")
            else:
                print(f"⚠️  No data extracted")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results[file_path] = {'error': str(e)}
    
    print(f"\n📊 Summary: {successful_extractions}/{len(working_files)} files successfully extracted")
    
    # Show successful extractions
    successful_files = [f for f, r in results.items() if 'total' in r and r['total'] > 0]
    print(f"\n✅ Successfully extracted from {len(successful_files)} files:")
    for f in successful_files:
        r = results[f]
        print(f"  {os.path.basename(f)}: {r['test_cases']} tests, {r['c_conditions']} C-cond, {r['pics_conditions']} PICS")
    
    return results

def analyze_interlab_coverage():
    """Analyze what's in the Interlab template"""
    interlab_path = "data_source/test_cases/Interlab_EVO_Feature_Spreadsheet_Template_All_20250920.xlsx"
    
    if not os.path.exists(interlab_path):
        print(f"❌ Interlab template not found: {interlab_path}")
        return
    
    print(f"\n📋 Analyzing Interlab template: {interlab_path}")
    
    # Read all sheets
    xl_file = pd.ExcelFile(interlab_path)
    sheets = xl_file.sheet_names
    
    print(f"📄 Found {len(sheets)} sheets:")
    
    gpp_sheets = []
    for sheet in sheets:
        if '3GPP' in sheet or 'TS' in sheet:
            gpp_sheets.append(sheet)
            print(f"  ✅ 3GPP: {sheet}")
        else:
            print(f"  📋 Other: {sheet}")
    
    print(f"\n🎯 3GPP sheets: {len(gpp_sheets)}")
    
    # Extract 3GPP standards from sheet names
    standards = set()
    for sheet in gpp_sheets:
        # Extract standard number like 36.521, 38.523, etc.
        import re
        match = re.search(r'(\d+\.\d+)', sheet)
        if match:
            standards.add(match.group(1))
    
    print(f"📋 Unique 3GPP standards in Interlab: {sorted(standards)}")
    print(f"📊 Total: {len(standards)} standards")
    
    return list(standards)

def compare_coverage():
    """Compare our data source coverage with Interlab template"""
    print("\n" + "="*80)
    print("📊 COVERAGE COMPARISON")
    print("="*80)
    
    # Get Interlab standards
    interlab_standards = analyze_interlab_coverage()
    
    # Get our available standards
    our_standards = set()
    base_path = Path("data_source/3GPP")
    
    for ts_dir in base_path.glob("TS *"):
        if ts_dir.is_dir():
            # Extract standard number from directory name like "TS 36.521-2"
            import re
            match = re.search(r'TS\s+(\d+\.\d+)', ts_dir.name)
            if match:
                our_standards.add(match.group(1))
    
    print(f"\n📁 Our data source standards: {sorted(our_standards)}")
    print(f"📊 Total: {len(our_standards)} standards")
    
    # Find overlap
    overlap = set(interlab_standards) & our_standards
    missing_from_us = set(interlab_standards) - our_standards
    extra_in_us = our_standards - set(interlab_standards)
    
    print(f"\n🎯 COMPARISON RESULTS:")
    print(f"✅ Standards we have that match Interlab: {len(overlap)}")
    print(f"❌ Standards in Interlab we don't have: {len(missing_from_us)}")
    print(f"➕ Extra standards we have: {len(extra_in_us)}")
    
    coverage_percentage = (len(overlap) / len(interlab_standards)) * 100 if interlab_standards else 0
    print(f"📊 Coverage percentage: {coverage_percentage:.1f}%")
    
    if missing_from_us:
        print(f"\n❌ Missing from our data source:")
        for std in sorted(missing_from_us):
            print(f"  - {std}")
    
    if extra_in_us:
        print(f"\n➕ Extra in our data source:")
        for std in sorted(extra_in_us):
            print(f"  - {std}")

async def main():
    print("="*80)
    print("🚀 Working -2 Documents Test & Coverage Analysis")
    print("="*80)
    
    # Test working files
    results = await test_working_files()
    
    # Analyze coverage
    compare_coverage()
    
    print("\n" + "="*80)
    print("✅ Analysis Complete!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())