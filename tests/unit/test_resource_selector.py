#!/usr/bin/env python3
"""
Test for resource selector
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_resource_selector():
    """Test resource selector with ISA Model client"""
    print("🧪 TESTING RESOURCE SELECTOR")
    print("=" * 50)
    
    try:
        from resources.resource_selector import ResourceSelector
        
        print("📋 Test: Resource selector initialization")
        
        # Create resource selector
        selector = ResourceSelector()
        
        # Add some mock resource info
        selector.resources_info = {
            "memory://all": {
                "description": "Access all stored memories and information",
                "keywords": ["memory", "information", "stored", "data", "recall"]
            },
            "weather://cache": {
                "description": "Cached weather data and forecasts",
                "keywords": ["weather", "forecast", "temperature", "climate", "conditions"]
            },
            "monitoring://metrics": {
                "description": "System monitoring and performance metrics",
                "keywords": ["monitoring", "metrics", "performance", "system", "health"]
            }
        }
        
        print(f"   ✅ Resource selector created with {len(selector.resources_info)} resources")
        
        # Initialize (this will create embeddings)
        print("   Initializing embeddings...")
        await selector.initialize()
        
        print(f"   ✅ Embeddings initialized: {len(selector.embeddings_cache)} resources")
        
        # Test resource selection
        test_queries = [
            "What do I remember about this topic?",
            "What's the weather like?",
            "How is the system performing?"
        ]
        
        for query in test_queries:
            print(f"\n   🔍 Query: '{query}'")
            selected_resources = await selector.select_resources(query, max_resources=2)
            print(f"   📋 Selected resources: {selected_resources}")
        
        await selector.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        print(f"📋 Full traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🚀 Starting Resource Selector Test...")
    success = asyncio.run(test_resource_selector())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")