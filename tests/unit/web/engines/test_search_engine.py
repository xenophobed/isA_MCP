#!/usr/bin/env python3
"""
Test for Search Engine with Brave API
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
load_dotenv()

async def test_search_engine_basic():
    """Test basic search engine functionality"""
    print("🔍 Testing Search Engine with Brave API")
    print("=" * 50)
    
    try:
        # Import search engine
        from tools.services.web_services.engines import SearchEngine, SearchProvider, BraveSearchStrategy
        
        # Get API key
        brave_token = os.getenv('BRAVE_TOKEN')
        if not brave_token:
            print("❌ BRAVE_TOKEN not found in environment variables")
            return False
        
        print(f"✅ Found Brave API token: {brave_token[:10]}...")
        
        # Initialize search engine
        search_engine = SearchEngine()
        brave_strategy = BraveSearchStrategy(str(brave_token))
        search_engine.register_strategy(SearchProvider.BRAVE, brave_strategy)
        
        print("✅ Search engine initialized with Brave strategy")
        
        # Test basic search
        print("\n🔍 Testing basic search...")
        query = "Python web scraping best practices"
        results = await search_engine.search(query, count=5)
        
        print(f"✅ Search completed: {len(results)} results")
        
        # Display results
        for i, result in enumerate(results[:3]):
            print(f"\n📄 Result {i+1}:")
            print(f"   Title: {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Snippet: {result.snippet[:100]}...")
            print(f"   Score: {result.score}")
            print(f"   Provider: {result.provider}")
        
        # Clean up
        await search_engine.close()
        print("\n✅ Search engine test completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Search engine test failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Brave Search Engine Test...")
    
    result = asyncio.run(test_search_engine_basic())
    if result:
        print("\n🎉 Brave search test passed!")
    else:
        print("\n❌ Brave search test failed!")
    
    sys.exit(0 if result else 1)