#!/usr/bin/env python3
"""
Test for tool selector
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_tool_selector():
    """Test tool selector with ISA Model client"""
    print("🧪 TESTING TOOL SELECTOR")
    print("=" * 50)
    
    try:
        from tools.core.tool_selector import ToolSelector
        
        print("📋 Test: Tool selector initialization")
        
        # Create tool selector
        selector = ToolSelector()
        
        # Add some mock tool info
        selector.tools_info = {
            "generate_image": {
                "description": "Generate images from text prompts using AI",
                "keywords": ["image", "generate", "ai", "picture", "art"]
            },
            "search_web": {
                "description": "Search the web for information",
                "keywords": ["search", "web", "internet", "find", "lookup"]
            },
            "analyze_data": {
                "description": "Analyze data and create reports",
                "keywords": ["data", "analyze", "report", "statistics", "chart"]
            }
        }
        
        print(f"   ✅ Tool selector created with {len(selector.tools_info)} tools")
        
        # Initialize (this will create embeddings)
        print("   Initializing embeddings...")
        await selector.initialize()
        
        print(f"   ✅ Embeddings initialized: {len(selector.embeddings_cache)} tools")
        
        # Test tool selection
        test_queries = [
            "I want to create a picture",
            "Help me find information online",
            "Analyze my sales data"
        ]
        
        for query in test_queries:
            print(f"\n   🔍 Query: '{query}'")
            selected_tools = await selector.select_tools(query, max_tools=2)
            print(f"   📋 Selected tools: {selected_tools}")
        
        await selector.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        print(f"📋 Full traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🚀 Starting Tool Selector Test...")
    success = asyncio.run(test_tool_selector())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")