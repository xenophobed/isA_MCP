#!/usr/bin/env python3
"""
Test PDF Processor

Tests the PDF processor functionality including:
- Text extraction from PDF pages
- Image extraction from PDF pages  
- Metadata extraction
- Structure analysis
- Unified processing workflow
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add the parent directories to path so we can import the processor
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir.parent))  # Add the processors directory

from pdf_processor import PDFProcessor

async def test_pdf_processor():
    """Test the PDF processor with test.pdf"""
    
    # Initialize processor
    processor = PDFProcessor()
    
    # Test PDF path - check multiple possible locations
    possible_paths = [
        project_root / "test.pdf",
        project_root / "tools" / "test.pdf", 
        Path("/Users/xenodennis/Documents/Fun/isA_MCP/test.pdf")
    ]
    
    test_pdf_path = None
    for path in possible_paths:
        if path.exists():
            test_pdf_path = str(path)
            break
    
    print(f"Testing PDF processor with: {test_pdf_path}")
    
    if test_pdf_path is None:
        print("ERROR: test.pdf not found in any expected location!")
        print("Checked paths:")
        for path in possible_paths:
            print(f"  - {path}")
        return None
    
    print(f"PDF exists: {os.path.exists(test_pdf_path)}")
    
    print("\n" + "="*60)
    print("PDF PROCESSOR CAPABILITIES")
    print("="*60)
    capabilities = processor.get_capabilities()
    for key, value in capabilities.items():
        print(f"{key}: {value}")
    
    print("\n" + "="*60)
    print("TEST 1: PDF METADATA EXTRACTION")
    print("="*60)
    
    metadata_result = await processor.extract_pdf_metadata(test_pdf_path)
    if metadata_result.get('success'):
        print(" Metadata extraction successful")
        print(f"   Pages: {metadata_result.get('page_count')}")
        print(f"   File size: {metadata_result.get('file_size')} bytes")
        print(f"   Title: {metadata_result.get('title')}")
        print(f"   Author: {metadata_result.get('author')}")
        print(f"   Encrypted: {metadata_result.get('is_encrypted')}")
    else:
        print("L Metadata extraction failed")
        print(f"   Error: {metadata_result.get('error')}")
    
    print("\n" + "="*60)
    print("TEST 2: PDF STRUCTURE ANALYSIS")
    print("="*60)
    
    structure_result = await processor.analyze_pdf_structure(test_pdf_path)
    if structure_result.get('success'):
        print(" Structure analysis successful")
        print(f"   Total pages: {structure_result.get('total_pages')}")
        for page_info in structure_result.get('page_info', []):
            print(f"   Page {page_info['page_number']}: {page_info['width']}x{page_info['height']}, "
                  f"Text: {page_info['has_text']}, Images: {page_info['has_images']}")
    else:
        print("L Structure analysis failed")
        print(f"   Error: {structure_result.get('error')}")
    
    print("\n" + "="*60)
    print("TEST 3: NATIVE PDF TEXT EXTRACTION")
    print("="*60)
    
    text_result = await processor.extract_native_pdf_text(test_pdf_path)
    if text_result.get('success'):
        print(" Text extraction successful")
        print(f"   Extraction method: {text_result.get('extraction_method')}")
        print(f"   Processing time: {text_result.get('processing_time'):.2f}s")
        print(f"   Total pages: {len(text_result.get('pages', []))}")
        print(f"   Total text length: {len(text_result.get('full_text', ''))}")
        print(f"   Text blocks: {len(text_result.get('text_blocks', []))}")
        
        # Show first 200 characters of extracted text
        full_text = text_result.get('full_text', '')
        if full_text:
            print(f"   First 200 chars: {full_text[:200]}...")
        else:
            print("   No text extracted")
    else:
        print("L Text extraction failed")
        print(f"   Error: {text_result.get('error')}")
    
    print("\n" + "="*60)
    print("TEST 4: PDF IMAGE INFO EXTRACTION")
    print("="*60)
    
    image_info_result = await processor.extract_pdf_images_info(test_pdf_path)
    if image_info_result.get('success'):
        print(" Image info extraction successful")
        print(f"   Total images: {image_info_result.get('total_images')}")
        for img in image_info_result.get('images', []):
            print(f"   Page {img['page_number']}, Image {img['image_index']}: "
                  f"{img['width']}x{img['height']}")
    else:
        print("L Image info extraction failed")
        print(f"   Error: {image_info_result.get('error')}")
    
    print("\n" + "="*60)
    print("TEST 5: PDF IMAGE EXTRACTION (WITH DATA)")
    print("="*60)
    
    image_extraction_result = await processor.extract_pdf_images(test_pdf_path)
    if image_extraction_result.get('success'):
        print(" Image extraction successful")
        print(f"   Total images extracted: {image_extraction_result.get('total_images')}")
        for img in image_extraction_result.get('images', []):
            print(f"   Page {img['page_number']}, Image {img['image_index']}: "
                  f"{img['width']}x{img['height']}, {img['size_bytes']} bytes")
            # Show first 50 chars of base64 data
            img_data = img.get('image_data', '')
            if img_data:
                print(f"   Data preview: {img_data[:50]}...")
    else:
        print("L Image extraction failed")
        print(f"   Error: {image_extraction_result.get('error')}")
    
    print("\n" + "="*60)
    print("TEST 6: UNIFIED PDF PROCESSING")
    print("="*60)
    
    unified_result = await processor.process_pdf_unified(test_pdf_path, {
        'extract_text': True,
        'extract_images': True,
        'extract_tables': True
    })
    
    if unified_result.get('success'):
        print(" Unified processing successful")
        print(f"   Total pages: {unified_result.get('total_pages')}")
        
        # Text results
        text_extraction = unified_result.get('text_extraction', {})
        if text_extraction:
            print(f"   Text extraction: {text_extraction.get('extraction_method')}")
            print(f"   Total text length: {len(text_extraction.get('full_text', ''))}")
            print(f"   Text blocks: {len(text_extraction.get('text_blocks', []))}")
        
        # Image results
        image_analysis = unified_result.get('image_analysis', {})
        if image_analysis:
            print(f"   Total images: {image_analysis.get('total_images')}")
            print(f"   Pages needing vision: {image_analysis.get('pages_needing_vision')}")
            
            # Show vision analysis requirements
            for vision in image_analysis.get('vision_analyses', []):
                print(f"   Page {vision['page_number']} needs vision analysis: {vision['analysis_reason']}")
        
        # Table results  
        table_extraction = unified_result.get('table_extraction', {})
        if table_extraction:
            print(f"   Total tables detected: {table_extraction.get('total_tables')}")
    else:
        print("L Unified processing failed")
        print(f"   Error: {unified_result.get('error')}")
    
    print("\n" + "="*60)
    print("EXPECTED RESULTS SUMMARY")
    print("="*60)
    print("The PDF processor should be able to:")
    print(" Extract all text content from PDF pages")
    print(" Extract images as base64-encoded data URLs")
    print(" Provide metadata about the PDF")
    print(" Analyze PDF structure (page dimensions, content types)")
    print(" Detect and extract tables (basic text-based detection)")
    print(" Handle both text-based and image-based PDF content")
    print(" Provide unified processing combining all extraction methods")
    
    return {
        'metadata': metadata_result,
        'structure': structure_result, 
        'text': text_result,
        'image_info': image_info_result,
        'image_extraction': image_extraction_result,
        'unified': unified_result
    }

async def main():
    """Main test function"""
    print("Starting PDF Processor Tests...")
    print("="*60)
    
    try:
        results = await test_pdf_processor()
        
        # Save results to JSON file for further analysis
        results_file = Path(__file__).parent / "pdf_processor_test_results.json"
        with open(results_file, 'w') as f:
            # Convert any non-serializable objects to strings
            serializable_results = {}
            for key, value in results.items():
                try:
                    json.dumps(value)
                    serializable_results[key] = value
                except:
                    serializable_results[key] = str(value)
            
            json.dump(serializable_results, f, indent=2)
        
        print(f"\n Test results saved to: {results_file}")
        
    except Exception as e:
        print(f"L Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())