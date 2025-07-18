#!/usr/bin/env python
"""
Test web crawl BS4 (traditional extraction) method specifically
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tools.services.web_services.services.web_crawl_service import WebCrawlService

async def test_bs4_traditional_extraction():
    """Test that BS4 traditional extraction method works"""
    print("🧪 Testing web crawl BS4 traditional extraction...")
    
    service = WebCrawlService()
    
    # Test with a simple, static website that should work with BS4
    test_urls = [
        "https://httpbin.org/html",  # Simple HTML page  
        "https://example.com",       # Very basic page
    ]
    
    for url in test_urls:
        print(f"\n🔍 Testing {url}...")
        
        try:
            # Test if can extract traditionally
            can_extract = await service._can_extract_traditionally(url)
            print(f"   Can extract traditionally: {can_extract}")
            
            if can_extract:
                # Test traditional extraction
                result = await service._traditional_extraction_path(url, "extract main content")
                
                print(f"   Traditional extraction result:")
                print(f"     Success: {result.get('success', False)}")
                print(f"     Method: {result.get('method', 'unknown')}")
                print(f"     Content length: {len(str(result.get('content', '')))}")
                
                if result.get('filtered_content'):
                    print(f"     Filtered content length: {len(str(result['filtered_content']))}")
                
                if result.get('content'):
                    content_preview = str(result['content'])[:200] + "..." if len(str(result['content'])) > 200 else str(result['content'])
                    print(f"     Content preview: {content_preview}")
                
            else:
                print("   ❌ Traditional extraction not suitable for this URL")
                
        except Exception as e:
            print(f"   ❌ Error testing {url}: {e}")
    
    print("\n🧪 Testing full web crawl service (hybrid approach)...")
    
    # Test the full service which should choose appropriate method
    test_url = "https://httpbin.org/html"
    
    try:
        result = await service.crawl_and_analyze(test_url, "extract all content")
        
        print(f"   Crawl result:")
        print(f"     Success: {result.get('success', False)}")
        print(f"     URL: {result.get('url', 'unknown')}")
        print(f"     Extraction method: {result.get('extraction_method', 'unknown')}")
        print(f"     Has result: {'result' in result}")
        
        if result.get('result'):
            extraction_result = result['result']
            print(f"     Result method: {extraction_result.get('method', 'unknown')}")
            print(f"     Result success: {extraction_result.get('success', False)}")
            
        print("✅ Full web crawl service test completed")
        
    except Exception as e:
        print(f"   ❌ Error in full crawl test: {e}")

async def test_can_extract_traditionally_logic():
    """Test the logic for determining if traditional extraction can be used"""
    print("\n🧪 Testing traditional extraction decision logic...")
    
    service = WebCrawlService()
    
    # Test various URL types
    test_cases = [
        ("https://httpbin.org/html", "Simple HTML - should be traditional"),
        ("https://example.com", "Basic static site - should be traditional"), 
        ("https://github.com", "Modern site - might be VLM"),
        ("https://invalid-domain-12345.com", "Invalid domain - should handle gracefully")
    ]
    
    for url, description in test_cases:
        print(f"\n🔍 Testing: {description}")
        print(f"   URL: {url}")
        
        try:
            can_extract = await service._can_extract_traditionally(url)
            print(f"   Can extract traditionally: {can_extract}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    async def main():
        await test_bs4_traditional_extraction()
        await test_can_extract_traditionally_logic()
        
    asyncio.run(main())