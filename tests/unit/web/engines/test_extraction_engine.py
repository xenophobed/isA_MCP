#!/usr/bin/env python3
"""
Test for Extraction Engine with Markdown Generation
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_extraction_engine_basic():
    """Test basic extraction engine functionality"""
    print("🕷️ Testing Extraction Engine with Markdown Generation")
    print("=" * 60)
    
    try:
        # Import required modules
        from tools.services.web_services.engines import ExtractionEngine
        from tools.services.web_services.strategies.generation import MarkdownGenerator
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Initialize extraction engine
        extraction_engine = ExtractionEngine()
        
        # Register markdown generation strategy
        markdown_generator = MarkdownGenerator(include_links=True, include_images=True)
        extraction_engine.register_generation_strategy("markdown", markdown_generator)
        
        print("✅ Extraction engine initialized with Markdown generator")
        
        # Initialize browser manager
        browser_manager = BrowserManager()
        await browser_manager.initialize()
        
        print("✅ Browser manager initialized")
        
        # Test URL crawling
        test_url = "https://example.com"
        print(f"\n🌐 Testing URL crawling: {test_url}")
        
        result = await extraction_engine.crawl_url(
            url=test_url,
            browser_manager=browser_manager,
            generation_strategy="markdown",
            extract_links=True,
            extract_images=True
        )
        
        print(f"✅ Crawl completed: {result.success}")
        print(f"   URL: {result.url}")
        print(f"   Title: {result.title}")
        print(f"   Processing time: {result.processing_time:.2f}s")
        
        if result.markdown:
            print(f"\n📝 Generated Markdown ({len(result.markdown)} chars):")
            print("-" * 40)
            print(result.markdown[:500] + "..." if len(result.markdown) > 500 else result.markdown)
            print("-" * 40)
        
        if result.links:
            print(f"\n🔗 Found {len(result.links)} links:")
            for i, link in enumerate(result.links[:3]):
                print(f"   {i+1}. {link}")
        
        if result.metadata:
            print(f"\n📊 Metadata ({len(result.metadata)} items):")
            for key, value in list(result.metadata.items())[:3]:
                print(f"   {key}: {value}")
        
        # Test with a different URL
        print(f"\n🌐 Testing with news website...")
        news_result = await extraction_engine.crawl_url(
            url="https://httpbin.org/html",  # Simple HTML page for testing
            browser_manager=browser_manager,
            generation_strategy="markdown"
        )
        
        print(f"✅ News crawl completed: {news_result.success}")
        if news_result.markdown:
            print(f"   Markdown length: {len(news_result.markdown)} chars")
        
        # Clean up - browser manager handles cleanup automatically
        print("\n✅ Extraction engine test completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Extraction engine test failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Extraction Engine Test...")
    
    result = asyncio.run(test_extraction_engine_basic())
    if result:
        print("\n🎉 Extraction engine test passed!")
    else:
        print("\n❌ Extraction engine test failed!")
    
    sys.exit(0 if result else 1)