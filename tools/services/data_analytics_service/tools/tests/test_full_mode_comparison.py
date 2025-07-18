#!/usr/bin/env python3
"""
Test Graph Analytics Tools - Full Mode vs Text Mode Performance Comparison

This test compares:
1. Text mode (fast, default) - ~17 seconds
2. Full mode (with Dask image processing) - ? seconds

Tests:
- Dask parallel image processing
- Image text extraction working
- Performance difference
- Image integration with text
"""

import asyncio
import sys
import json
import logging
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def log_timing(step_name: str, start_time: float) -> float:
    """Log timing for a step and return current time"""
    current_time = time.time()
    elapsed = current_time - start_time
    print(f"⏱️  {step_name}: {elapsed:.2f}s")
    return current_time

async def test_mode_comparison():
    """Test both text and full modes for performance comparison"""
    test_start_time = time.time()
    print(f"🚀 Graph Analytics Tools Mode Comparison - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("Testing text mode vs full mode (with Dask image processing)")
    print("=" * 80)
    
    try:
        # Import the tool
        from tools.services.data_analytics_service.tools.graph_analytics_tools import GraphAnalyticsTool
        
        tool = GraphAnalyticsTool()
        test_pdf = "/Users/xenodennis/Documents/Fun/isA_MCP/test.pdf"
        test_user_id = 88888
        
        print(f"📄 Test PDF: {test_pdf}")
        print(f"👤 Test User: {test_user_id}")
        
        # Test 1: Text Mode (Baseline)
        print("\n" + "=" * 80)
        print("🔬 TEST 1: TEXT MODE (Baseline - Fast)")
        print("=" * 80)
        
        text_mode_start = time.time()
        print(f"🚀 Starting text mode processing at {datetime.now().strftime('%H:%M:%S')}...")
        
        text_result = await tool.process_pdf_to_knowledge_graph(
            pdf_path=test_pdf,
            user_id=test_user_id,
            source_metadata={
                'test': 'text_mode_comparison',
                'domain': 'medical_report'
            },
            options={
                'mode': 'text'  # Fast text-only mode
            }
        )
        
        text_mode_time = log_timing("TEXT MODE - Complete Processing", text_mode_start)
        
        # Parse text mode results
        text_data = json.loads(text_result)
        if text_data.get('status') == 'success':
            text_info = text_data.get('data', {})
            text_pdf_info = text_info.get('pdf_processing', {})
            text_kg_info = text_info.get('knowledge_graph', {})
            
            print("📊 TEXT MODE Results:")
            print(f"  📝 PDF: {text_pdf_info.get('pages_processed')} pages, {text_pdf_info.get('total_characters')} chars, {text_pdf_info.get('chunks_created')} chunks")
            print(f"  🧠 KG: {text_kg_info.get('entities_count')} entities, {text_kg_info.get('relationships_count')} relationships")
            print(f"  ⏱️  Times: PDF {text_pdf_info.get('extraction_time'):.2f}s, KG {text_kg_info.get('processing_time'):.2f}s")
            print(f"  🎯 TOTAL TEXT MODE: {(text_mode_time - text_mode_start):.2f}s")
        else:
            print(f"❌ Text mode failed: {text_data.get('message')}")
            return False
        
        # Test 2: Full Mode (With Dask Image Processing)
        print("\n" + "=" * 80)
        print("🔬 TEST 2: FULL MODE (With Dask Image Processing)")
        print("=" * 80)
        
        full_mode_start = time.time()
        print(f"🚀 Starting full mode processing at {datetime.now().strftime('%H:%M:%S')}...")
        print("🖼️  This will extract and process images using Dask parallel processing...")
        
        full_result = await tool.process_pdf_to_knowledge_graph(
            pdf_path=test_pdf,
            user_id=test_user_id + 1,  # Different user to avoid conflicts
            source_metadata={
                'test': 'full_mode_comparison',
                'domain': 'medical_report'
            },
            options={
                'mode': 'full'  # Full mode with image processing
            }
        )
        
        full_mode_time = log_timing("FULL MODE - Complete Processing", full_mode_start)
        
        # Parse full mode results
        full_data = json.loads(full_result)
        if full_data.get('status') == 'success':
            full_info = full_data.get('data', {})
            full_pdf_info = full_info.get('pdf_processing', {})
            full_kg_info = full_info.get('knowledge_graph', {})
            
            print("📊 FULL MODE Results:")
            print(f"  📝 PDF: {full_pdf_info.get('pages_processed')} pages, {full_pdf_info.get('total_characters')} chars, {full_pdf_info.get('chunks_created')} chunks")
            print(f"  🖼️  Images: {full_pdf_info.get('images_processed', 0)} images processed")
            print(f"  🧠 KG: {full_kg_info.get('entities_count')} entities, {full_kg_info.get('relationships_count')} relationships")
            print(f"  ⏱️  Times: PDF {full_pdf_info.get('extraction_time'):.2f}s, KG {full_kg_info.get('processing_time'):.2f}s")
            print(f"  🎯 TOTAL FULL MODE: {(full_mode_time - full_mode_start):.2f}s")
        else:
            print(f"❌ Full mode failed: {full_data.get('message')}")
            return False
        
        # Performance Comparison
        print("\n" + "=" * 80)
        print("📊 PERFORMANCE COMPARISON")
        print("=" * 80)
        
        text_total = text_mode_time - text_mode_start
        full_total = full_mode_time - full_mode_start
        performance_ratio = full_total / text_total
        time_difference = full_total - text_total
        
        print(f"⚡ TEXT MODE (baseline):  {text_total:.1f} seconds")
        print(f"🖼️  FULL MODE (+ images): {full_total:.1f} seconds")
        print(f"📈 Performance Ratio:    {performance_ratio:.1f}x slower")
        print(f"⏱️  Time Difference:      +{time_difference:.1f} seconds")
        
        # Character comparison
        text_chars = text_pdf_info.get('total_characters', 0)
        full_chars = full_pdf_info.get('total_characters', 0)
        char_increase = full_chars - text_chars
        images_processed = full_pdf_info.get('images_processed', 0)
        
        print(f"\n📝 CONTENT ANALYSIS:")
        print(f"  Text Mode Characters:  {text_chars:,}")
        print(f"  Full Mode Characters:  {full_chars:,}")
        print(f"  Character Increase:    +{char_increase:,} ({((char_increase/text_chars)*100):.1f}% more)")
        print(f"  Images Processed:      {images_processed}")
        print(f"  Avg chars per image:   {char_increase//max(images_processed,1):,}")
        
        # Entity/Relationship comparison
        text_entities = text_kg_info.get('entities_count', 0)
        full_entities = full_kg_info.get('entities_count', 0)
        text_relations = text_kg_info.get('relationships_count', 0)
        full_relations = full_kg_info.get('relationships_count', 0)
        
        print(f"\n🧠 KNOWLEDGE GRAPH COMPARISON:")
        print(f"  Text Mode:  {text_entities} entities, {text_relations} relationships")
        print(f"  Full Mode:  {full_entities} entities, {full_relations} relationships")
        print(f"  Difference: +{full_entities - text_entities} entities, +{full_relations - text_relations} relationships")
        
        # Dask/Image Processing Analysis
        print(f"\n🖼️  DASK IMAGE PROCESSING ANALYSIS:")
        if images_processed > 0:
            print(f"  ✅ Dask image processing: WORKING")
            print(f"  ✅ Image text extraction: WORKING")
            print(f"  📊 Images processed: {images_processed}")
            print(f"  🎯 Characters from images: {char_increase:,}")
            
            # Estimate image processing time
            pdf_time_diff = full_pdf_info.get('extraction_time', 0) - text_pdf_info.get('extraction_time', 0)
            print(f"  ⏱️  Image processing time: ~{pdf_time_diff:.1f}s")
            print(f"  📈 Average time per image: ~{pdf_time_diff/max(images_processed,1):.1f}s")
        else:
            print(f"  ⚠️  No images were processed - PDF may be text-only")
            print(f"  💡 Try with a PDF that contains charts, diagrams, or scanned content")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if performance_ratio < 2:
            print(f"  ✅ Full mode performance acceptable (less than 2x slower)")
        elif performance_ratio < 5:
            print(f"  ⚠️  Full mode moderate overhead ({performance_ratio:.1f}x slower)")
        else:
            print(f"  🚨 Full mode significant overhead ({performance_ratio:.1f}x slower)")
        
        if images_processed > 0:
            print(f"  🎯 Use FULL mode when: PDFs contain charts, diagrams, scanned content")
            print(f"  ⚡ Use TEXT mode when: PDFs are primarily text-based")
        else:
            print(f"  ⚡ This PDF appears text-only - TEXT mode is optimal")
            print(f"  🧪 Test FULL mode with image-heavy PDFs for better comparison")
        
        # Final Assessment
        total_test_time = time.time() - test_start_time
        print(f"\n🎉 COMPARISON COMPLETE in {total_test_time:.1f} seconds!")
        print(f"✅ Both modes working correctly")
        print(f"✅ Dask parallel processing {'verified' if images_processed > 0 else 'ready (no images in test PDF)'}")
        print(f"✅ Performance baseline established")
        
        return True
        
    except Exception as e:
        total_test_time = time.time() - test_start_time
        print(f"❌ Comparison test failed after {total_test_time:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the comparison test"""
    print(f"🧪 Graph Analytics Tools Mode Comparison - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Comparing text mode vs full mode (with Dask image processing)\n")
    
    success = await test_mode_comparison()
    
    if success:
        print(f"\n✨ SUCCESS: Mode comparison completed!")
        print("✨ Both text and full modes working correctly!")
        print("✨ Performance baseline established!")
    else:
        print(f"\n❌ FAILURE: Mode comparison failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())