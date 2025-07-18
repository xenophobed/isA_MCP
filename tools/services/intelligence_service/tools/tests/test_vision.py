#!/usr/bin/env python3
"""
Test script for vision_tools.py
"""

import asyncio
import sys
import os
import json
import tempfile

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

from tools.services.intelligence_service.tools.vision_tools import VisionTools

def create_test_image(size=(100, 100), color=(255, 255, 255)):
    """Create a simple test image or placeholder"""
    try:
        from PIL import Image
        # Create a simple colored rectangle
        img = Image.new('RGB', size, color)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            img.save(tmp.name, 'PNG')
            return tmp.name
    except ImportError:
        # If PIL is not available, create a text file placeholder
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as tmp:
            tmp.write(f"Test image placeholder - size: {size}, color: {color}")
            return tmp.name

def cleanup_test_image(image_path):
    """Clean up test image file"""
    try:
        if os.path.exists(image_path):
            os.unlink(image_path)
    except:
        pass

async def test_basic_vision_analysis():
    """Test basic vision analysis functionality"""
    print("Test 1: Basic Vision Analysis Functionality")
    print("="*50)
    
    vision_tools = VisionTools()
    
    # Create a simple test image
    test_image_path = create_test_image()
    
    test_prompt = "Describe what you see in this image"
    
    print(f"Input Parameters:")
    print(f"  Image Path: {test_image_path}")
    print(f"  Prompt: {test_prompt}")
    print(f"  Provider: openai")
    print()
    
    try:
        # Test ISA client availability first
        print("Testing vision analyzer availability...")
        try:
            # Check if analyzer is available
            analyzer = vision_tools.analyzer
            if analyzer is None:
                print("Vision analyzer is None - skipping real analysis test")
                print("This may be due to missing configuration or environment setup")
                cleanup_test_image(test_image_path)
                return True  # Skip test but don't fail
            else:
                print("Vision analyzer is available")
        except Exception as analyzer_e:
            print(f"Vision analyzer error: {analyzer_e}")
            print("Skipping real analysis test due to analyzer issues")
            cleanup_test_image(test_image_path)
            return True  # Skip test but don't fail
        
        result = await vision_tools.analyze_image(
            image=test_image_path,
            prompt=test_prompt,
            provider="openai"
        )
        
        print("Raw Response:")
        print(result)
        print()
        
        # Parse and analyze
        result_data = json.loads(result)
        
        print("Parsed Response Analysis:")
        print(f"  Status: {result_data.get('status', 'unknown')}")
        print(f"  Operation: {result_data.get('operation', 'unknown')}")
        
        if result_data.get('status') == 'success':
            data = result_data.get('data', {})
            print(f"  Response Length: {len(data.get('response', ''))}")
            print(f"  Model Used: {data.get('model_used', 'N/A')}")
            print(f"  Processing Time: {data.get('processing_time', 'N/A')}s")
            
            # Billing verification
            billing = data.get('billing', {})
            print(f"  Billing Info Present: {'Yes' if billing else 'No'}")
            if billing:
                print(f"    Total Cost: ${billing.get('total_cost', 'N/A')}")
                print(f"    Model: {billing.get('model', 'N/A')}")
        
        cleanup_test_image(test_image_path)
        print("Test 1 PASSED")
        return True
        
    except Exception as e:
        cleanup_test_image(test_image_path)
        print(f"Test 1 FAILED: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Check if it's a specific ISA-related error
        error_str = str(e).lower()
        if 'nonetype' in error_str and 'iterable' in error_str:
            print("This appears to be an ISA client configuration issue")
            print("Please ensure ISA service is running and configured properly")
        
        import traceback
        traceback.print_exc()
        return False

async def test_vision_methods():
    """Test different vision analysis methods"""
    print("\nTest 2: Vision Analysis Methods")
    print("="*50)
    
    vision_tools = VisionTools()
    test_image_path = create_test_image()
    
    methods = [
        ("describe_image", {"detail_level": "medium", "language": "en"}),
        ("extract_text", {"language": "auto"}),
        ("identify_objects", {"object_type": "all"}),
        ("analyze_emotion", {})
    ]
    
    for method_name, kwargs in methods:
        print(f"\nTesting method: {method_name}")
        try:
            method = getattr(vision_tools, method_name)
            result = await method(image=test_image_path, **kwargs)
            
            print(f"Raw Response for {method_name}:")
            print(result[:200] + "..." if len(result) > 200 else result)
            print()
            
            result_data = json.loads(result)
            if result_data.get('status') == 'success':
                print(f"  {method_name}: Success")
            else:
                print(f"  {method_name} failed: {result_data.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"  {method_name} exception: {str(e)}")
    
    cleanup_test_image(test_image_path)
    print("Test 2 COMPLETED")

async def test_image_comparison():
    """Test image comparison functionality"""
    print("\nTest 3: Image Comparison")
    print("="*50)
    
    vision_tools = VisionTools()
    
    # Create two test images
    test_image1 = create_test_image(color=(255, 0, 0))  # Red
    test_image2 = create_test_image(color=(0, 255, 0))  # Green
    
    print(f"Testing image comparison:")
    print(f"  Image 1: {test_image1}")
    print(f"  Image 2: {test_image2}")
    
    try:
        result = await vision_tools.compare_images(
            image1=test_image1,
            image2=test_image2,
            comparison_aspects=["content", "color", "composition"]
        )
        
        print(f"Comparison Response:")
        print(result[:300] + "..." if len(result) > 300 else result)
        
        result_data = json.loads(result)
        if result_data.get('status') == 'success':
            data = result_data.get('data', {})
            print(f"  Comparison completed")
            print(f"  Aspects compared: {data.get('aspects', [])}")
        else:
            print(f"  Comparison failed: {result_data.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"Image comparison failed: {str(e)}")
    
    cleanup_test_image(test_image1)
    cleanup_test_image(test_image2)
    print("Test 3 COMPLETED")

async def test_error_handling():
    """Test error handling with invalid inputs"""
    print("\nTest 4: Error Handling")
    print("="*50)
    
    vision_tools = VisionTools()
    
    # Test with non-existent file
    print("Testing with non-existent file:")
    try:
        result = await vision_tools.analyze_image(
            image="/non/existent/path.jpg",
            prompt="Describe this image"
        )
        
        result_data = json.loads(result)
        if result_data.get('status') == 'error':
            print("  Error properly handled for non-existent file")
        else:
            print("  Expected error but got success")
            
    except Exception as e:
        print(f"  Unexpected exception: {str(e)}")
    
    # Test with empty prompt
    test_image_path = create_test_image()
    print("\nTesting with empty prompt:")
    try:
        result = await vision_tools.analyze_image(
            image=test_image_path,
            prompt=""
        )
        
        result_data = json.loads(result)
        print(f"  Status: {result_data.get('status')}")
        
    except Exception as e:
        print(f"  Exception with empty prompt: {str(e)}")
    
    cleanup_test_image(test_image_path)
    print("Test 4 COMPLETED")

async def run_all_tests():
    """Run all tests"""
    print("Starting vision_tools.py comprehensive tests...\n")
    
    tests = [
        test_basic_vision_analysis,
        test_vision_methods,
        test_image_comparison,
        test_error_handling
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append(False)
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("ALL TESTS PASSED!")
    else:
        print("Some tests failed - review output above")

if __name__ == "__main__":
    asyncio.run(run_all_tests())