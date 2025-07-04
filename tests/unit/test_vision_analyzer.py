#!/usr/bin/env python3
"""
Test for vision analyzer
"""
import asyncio
import sys
import os
import tempfile
from PIL import Image

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_vision_analyzer():
    """Test vision analyzer with ISA Model client"""
    print("🧪 TESTING VISION ANALYZER")
    print("=" * 50)
    
    try:
        from tools.services.web_services.strategies.detection.vision_analyzer import VisionAnalyzer
        
        print("📋 Test: Vision analyzer initialization")
        
        # Create vision analyzer
        analyzer = VisionAnalyzer()
        
        print(f"   ✅ Vision analyzer created")
        
        # Create a mock screenshot for testing
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            # Create a simple test image
            img = Image.new('RGB', (800, 600), color='white')
            img.save(tmp_file.name)
            screenshot_path = tmp_file.name
        
        print(f"   📸 Created test screenshot: {screenshot_path}")
        
        # Test stacked AI login analysis
        print("   Testing stacked AI login analysis...")
        result = await analyzer._stacked_ai_login_analysis(screenshot_path)
        
        print(f"   ✅ Analysis completed successfully")
        print(f"   📊 Result type: {type(result)}")
        if isinstance(result, dict):
            print(f"   📊 Result keys: {list(result.keys())}")
        
        # Clean up
        os.unlink(screenshot_path)
        print("   🧹 Cleaned up test file")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        print(f"📋 Full traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🚀 Starting Vision Analyzer Test...")
    success = asyncio.run(test_vision_analyzer())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")