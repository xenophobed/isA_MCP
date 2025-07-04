#!/usr/bin/env python3
"""
Test for simplified image generation tool
"""
import json
import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_image_generation():
    """Test image generation by calling isa_model directly"""
    print("🧪 TESTING IMAGE GENERATION DIRECTLY")
    print("=" * 50)
    
    try:
        # Import ISA Model client directly
        from core.isa_client import get_isa_client
        
        print("📋 Test 1: Text-to-Image (t2i) generation using ISA Model client")
        print("   Prompt: 'A beautiful sunset over mountains'")
        print("   Getting ISA Model client...")
        
        # Get ISA Model client
        client = get_isa_client()
        print(f"   ✅ Client obtained: {type(client).__name__}")
        
        # Generate image
        print("   Generating image...")
        result = await client.invoke(
            input_data="A beautiful sunset over mountains",
            task="generate_image",
            service_type="image",
            parameters={
                "width": 512,
                "height": 512
            }
        )
        
        print(f"   Result type: {type(result)}")
        print(f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Extract data from ISA Model result
        if result.get('success'):
            result_data = result.get('result', {})
            image_urls = result_data.get('urls', [])
            if isinstance(image_urls, str):
                image_urls = [image_urls]
        else:
            image_urls = []
        
        cost = result.get('result', {}).get('cost_usd', 0.0)
        count = len(image_urls)
        
        print(f"   ✅ Generated {count} image(s)")
        print(f"   💰 Cost: ${cost}")
        print(f"   📊 URLs found: {len(image_urls)}")
        
        for i, url in enumerate(image_urls):
            print(f"   🔗 URL {i+1}: {url}")
        
        print(f"\n📄 Full result:")
        print(f"   {result}")
        
        # Test 2: Test our MCP tool function
        print(f"\n📋 Test 2: MCP tool function")
        from tools.image_gen_tools import register_image_gen_tools
        
        # Mock security manager
        class MockSecurityManager:
            def security_check(self, func):
                return func
            def require_authorization(self, level):
                def decorator(func):
                    return func
                return decorator
        
        # Mock the security manager
        import tools.image_gen_tools
        original_get_security_manager = tools.image_gen_tools.get_security_manager
        tools.image_gen_tools.get_security_manager = lambda: MockSecurityManager()
        
        # Create mock MCP and register tools
        class MockMCP:
            def __init__(self):
                self.tools = {}
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator
        
        mock_mcp = MockMCP()
        register_image_gen_tools(mock_mcp)
        tools.image_gen_tools.get_security_manager = original_get_security_manager
        
        # Test the MCP tool
        generate_image_tool = mock_mcp.tools.get('generate_image')
        if generate_image_tool:
            print("   Calling MCP generate_image tool...")
            mcp_result_json = await generate_image_tool(
                prompt="A simple test image",
                image_type="t2i",
                width=512,
                height=512
            )
            mcp_result = json.loads(mcp_result_json)
            print(f"   MCP tool status: {mcp_result.get('status')}")
            if mcp_result.get('status') == 'success':
                mcp_urls = mcp_result.get('data', {}).get('image_urls', [])
                print(f"   ✅ MCP tool generated {len(mcp_urls)} image(s)")
                for i, url in enumerate(mcp_urls):
                    print(f"   🔗 MCP URL {i+1}: {url}")
            else:
                print(f"   ❌ MCP tool error: {mcp_result.get('data', {}).get('error')}")
        
        return len(image_urls) > 0
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        print(f"📋 Full traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🚀 Starting Image Generation Test...")
    success = asyncio.run(test_image_generation())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")