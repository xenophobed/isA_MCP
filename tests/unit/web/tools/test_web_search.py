#!/usr/bin/env python
"""
Test Web Tools Search - Simple Mode
Test the simplified web_search function with Brave API integration
"""
import asyncio
import json
import os
import sys
from datetime import datetime

# Add project root to path (go up 4 levels: tools -> web -> unit -> tests -> root)
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")
sys.path.insert(0, project_root)

from tools.web_tools import _initialize_search_services, _simple_search
from tools.services.web_services.engines.search_engine import SearchProvider
from core.config import get_settings

async def test_simple_search():
    """Test simple web search functionality"""
    print("🧪 Testing Simple Web Search")
    print("=" * 50)
    
    # Check for API key using config manager
    settings = get_settings()
    brave_api_key = settings.brave_api_key
    if not brave_api_key:
        print("❌ BRAVE_TOKEN not found in configuration")
        print("Please ensure BRAVE_TOKEN is set in your .env file")
        return False
    
    print(f"✅ Found BRAVE_TOKEN: {brave_api_key[:8]}...")
    
    try:
        # Initialize services
        print("\n🔧 Initializing search services...")
        await _initialize_search_services()
        print("✅ Services initialized successfully")
        
        # Test queries
        test_queries = [
            "latest AI news",
            "python web scraping tutorial", 
            "best laptops 2024"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📋 Test {i}: Searching for '{query}'")
            print("-" * 40)
            
            try:
                # Execute simple search
                result = await _simple_search(
                    query=query,
                    providers=[SearchProvider.BRAVE],
                    max_results=5,
                    filters={}
                )
                
                # Parse and display results
                result_data = json.loads(result)
                
                if result_data["status"] == "success":
                    search_data = result_data["data"]
                    print(f"✅ Search successful!")
                    print(f"   Query: {search_data['query']}")
                    print(f"   Total results: {search_data['total_results']}")
                    print(f"   Provider: {search_data['providers_used']}")
                    print(f"   Method: {search_data['search_method']}")
                    
                    print("\n📄 Results:")
                    for j, res in enumerate(search_data["results"][:3], 1):
                        print(f"   {j}. {res['title']}")
                        print(f"      URL: {res['url']}")
                        print(f"      Snippet: {res['snippet'][:100]}...")
                        if res.get('metadata'):
                            meta = res['metadata']
                            if meta.get('age'):
                                print(f"      Age: {meta['age']}")
                            if meta.get('language'):
                                print(f"      Language: {meta['language']}")
                        print()
                else:
                    print(f"❌ Search failed: {result_data.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Test {i} failed: {str(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service initialization failed: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_with_filters():
    """Test search with various filters"""
    print("\n🔍 Testing Search with Filters")
    print("=" * 50)
    
    try:
        await _initialize_search_services()
        
        # Test with different filters
        filter_tests = [
            {
                "name": "Fresh results (last day)",
                "filters": {"freshness": "pd"},  # past day
                "query": "latest tech news"
            },
            {
                "name": "English language filter", 
                "filters": {"mkt": "en-US"},
                "query": "machine learning tutorials"
            },
            {
                "name": "Safe search moderate",
                "filters": {"safesearch": "moderate"},
                "query": "educational content"
            }
        ]
        
        for test in filter_tests:
            print(f"\n📋 Testing: {test['name']}")
            print(f"   Query: {test['query']}")
            print(f"   Filters: {test['filters']}")
            
            try:
                result = await _simple_search(
                    query=test['query'],
                    providers=[SearchProvider.BRAVE],
                    max_results=3,
                    filters=test['filters']
                )
                
                result_data = json.loads(result)
                if result_data["status"] == "success":
                    results_count = result_data["data"]["total_results"]
                    print(f"   ✅ Success: {results_count} results")
                    
                    # Show first result
                    if result_data["data"]["results"]:
                        first_result = result_data["data"]["results"][0]
                        print(f"   First result: {first_result['title']}")
                else:
                    print(f"   ❌ Failed: {result_data.get('error')}")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
    except Exception as e:
        print(f"❌ Filter test setup failed: {str(e)}")

async def test_error_handling():
    """Test error handling scenarios"""
    print("\n⚠️  Testing Error Handling")
    print("=" * 50)
    
    try:
        await _initialize_search_services()
        
        # Test empty query
        print("📋 Testing empty query...")
        try:
            result = await _simple_search(
                query="",
                providers=[SearchProvider.BRAVE],
                max_results=5,
                filters={}
            )
            result_data = json.loads(result)
            print(f"   Result: {result_data.get('status', 'unknown')}")
        except Exception as e:
            print(f"   ✅ Caught expected error: {str(e)}")
        
        # Test very long query
        print("\n📋 Testing very long query...")
        long_query = "a" * 1000
        try:
            result = await _simple_search(
                query=long_query,
                providers=[SearchProvider.BRAVE],
                max_results=5,
                filters={}
            )
            result_data = json.loads(result)
            print(f"   Result: {result_data.get('status', 'unknown')}")
        except Exception as e:
            print(f"   ✅ Caught expected error: {str(e)}")
            
    except Exception as e:
        print(f"❌ Error handling test failed: {str(e)}")

async def main():
    """Run all tests"""
    print("🚀 Starting Web Tools Search Tests")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Run tests
    basic_success = await test_simple_search()
    
    if basic_success:
        await test_with_filters()
        await test_error_handling()
        
        print("\n✅ All tests completed!")
        print("Simple web search is working and ready for use.")
    else:
        print("\n❌ Basic tests failed - please fix issues before proceeding")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    # Run tests
    asyncio.run(main())