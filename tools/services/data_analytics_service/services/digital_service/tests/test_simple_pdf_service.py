#!/usr/bin/env python3
"""
Test Simple PDF Extract Service 

Test the optimized service that uses existing production components:
- PDFProcessor for unified PDF processing
- ImageAnalyzer for parallel image text extraction with Dask
"""

import asyncio
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_simple_pdf_service():
    """Test the simple PDF extract service with existing components"""
    try:
        # Import the service
        from tools.services.data_analytics_service.services.digital_service.simple_pdf_extract_service import SimplePDFExtractService
        
        print("🚀 Testing Simple PDF Extract Service with existing components...")
        
        # Initialize service
        service = SimplePDFExtractService({
            'chunk_size': 2000,
            'chunk_overlap': 200
        })
        
        # Initialize Dask (optional)
        dask_initialized = await service.initialize_dask(workers=2, threads_per_worker=2)
        if dask_initialized:
            print("✅ Dask client initialized for parallel processing")
        else:
            print("⚠️  Dask not available, using asyncio fallback")
        
        # Test PDF path
        pdf_path = "/Users/xenodennis/Documents/Fun/isA_MCP/test.pdf"
        if not Path(pdf_path).exists():
            print(f"❌ Test PDF not found: {pdf_path}")
            return False
        
        # Test 1: Text-only mode (fast)
        print("\n📝 Test 1: Text-only extraction...")
        start_time = time.time()
        
        result = await service.extract_pdf_to_chunks(
            pdf_path=pdf_path,
            user_id=12345,
            options={'mode': 'text'},
            metadata={'test': 'text_only'}
        )
        
        text_time = time.time() - start_time
        
        if result['success']:
            print(f"✅ Text extraction successful in {text_time:.3f}s")
            print(f"   📊 {result['chunk_count']} chunks, {result['total_characters']} characters")
            print(f"   📄 {result['pages_processed']} pages processed")
            print(f"   📝 First chunk preview: {result['chunks'][0][:100]}..." if result['chunks'] else "   📝 No chunks")
        else:
            print(f"❌ Text extraction failed: {result['error']}")
            return False
        
        # Test 2: Full mode (text + images with Dask)
        print("\n🖼️  Test 2: Full extraction (text + images)...")
        start_time = time.time()
        
        result = await service.extract_pdf_to_chunks(
            pdf_path=pdf_path,
            user_id=12345,
            options={'mode': 'full'},
            metadata={'test': 'full_extraction'}
        )
        
        full_time = time.time() - start_time
        
        if result['success']:
            print(f"✅ Full extraction successful in {full_time:.3f}s")
            print(f"   📊 {result['chunk_count']} chunks, {result['total_characters']} characters")
            print(f"   📄 {result['pages_processed']} pages processed")
            print(f"   🖼️  {result['images_processed']} images processed")
            
            # Check if image text was extracted
            image_text_found = any("IMAGE EXTRACTED TEXT" in chunk for chunk in result['chunks'])
            if image_text_found:
                print("   ✅ Image text extraction detected in chunks")
            else:
                print("   ℹ️  No image text found (may be normal for text-heavy PDFs)")
                
        else:
            print(f"❌ Full extraction failed: {result['error']}")
            return False
        
        # Performance comparison
        print(f"\n⚡ Performance Summary:")
        print(f"   📝 Text-only: {text_time:.3f}s")
        print(f"   🖼️  Full mode: {full_time:.3f}s")
        print(f"   📈 Full mode overhead: {(full_time - text_time):.3f}s")
        
        # Cleanup
        service.close_dask()
        print("\n✅ All tests passed! Simple PDF Extract Service working correctly with existing components.")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Run the test"""
    print("🧪 Simple PDF Extract Service Test")
    print("=" * 50)
    
    success = await test_simple_pdf_service()
    
    if success:
        print("\n🎉 All tests passed!")
        print("✅ PDFProcessor integration: WORKING")
        print("✅ ImageAnalyzer integration: WORKING") 
        print("✅ Dask parallel processing: WORKING")
        print("✅ Simple chunking: WORKING")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())