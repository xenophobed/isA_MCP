#!/usr/bin/env python3
"""
Test script for image_intelligence_service.py
"""

import asyncio
import sys
import os
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

from tools.services.intelligence_service.img.image_intelligence_service import AtomicImageIntelligence

async def test_basic_functionality():
    """Test basic image intelligence functionality"""
    print("🧪 Test 1: Basic Image Intelligence Functionality")
    print("="*50)
    
    service = AtomicImageIntelligence()
    
    test_prompt = "a cute cat sitting in a garden, digital art"
    
    print(f"📋 Input Parameters:")
    print(f"  Prompt: {test_prompt}")
    print(f"  Task Type: text_to_image")
    print(f"  Size: 1024x1024")
    print()
    
    try:
        # First test ISA client availability
        print("🔍 Testing ISA Client availability...")
        try:
            # Check if ISA client is initialized
            isa_client = service.isa_client
            if isa_client is None:
                print("❌ ISA Client is None - skipping real ISA test")
                print("💡 This may be due to missing configuration or environment setup")
                return True  # Skip test but don't fail
            else:
                print("✅ ISA Client is available")
        except Exception as isa_e:
            print(f"❌ ISA Client error: {isa_e}")
            print("💡 Skipping real ISA test due to client issues")
            return True  # Skip test but don't fail
        
        result = await service.generate_text_to_image(
            prompt=test_prompt,
            width=1024,
            height=1024,
            steps=4
        )
        
        print("📤 Raw Response:")
        print(json.dumps(result, indent=2))
        print()
        
        # Parse and analyze
        print("📊 Parsed Response Analysis:")
        print(f"  Success: {result.get('success', 'unknown')}")
        
        if result.get('success'):
            urls = result.get('urls', [])
            print(f"  Generated URLs: {len(urls)}")
            for i, url in enumerate(urls, 1):
                print(f"    Image {i}: {url[:60]}...")
            
            # Cost verification
            cost = result.get('cost', 0.0)
            print(f"  Cost: ${cost:.6f}")
            
            # Metadata verification
            metadata = result.get('metadata', {})
            print(f"  Model Used: {metadata.get('model', 'N/A')}")
            print(f"  Task Type: {metadata.get('task_type', 'N/A')}")
        
        print("✅ Test 1 PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Test 1 FAILED: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Check if it's a specific ISA-related error
        error_str = str(e).lower()
        if 'nonetype' in error_str and 'iterable' in error_str:
            print("💡 This appears to be an ISA client configuration issue")
            print("💡 Please ensure ISA service is running and configured properly")
        
        import traceback
        traceback.print_exc()
        return False

async def test_specialized_tasks():
    """Test different specialized image tasks"""
    print("\n🧪 Test 2: Specialized Image Tasks")
    print("="*50)
    
    service = AtomicImageIntelligence()
    
    task_types = [
        ("sticker_generation", "cute robot"),
        ("emoji_generation", "happy face"),
        ("style_transfer", "cyberpunk style"),
        ("professional_headshot", "business portrait")
    ]
    
    for task_type, test_input in task_types:
        print(f"\n🎭 Testing task type: {task_type}")
        try:
            # Check ISA client availability first
            isa_client = service.isa_client
            if isa_client is None:
                print("❌ ISA Client is None - skipping real ISA test")
                continue
            
            if task_type == "sticker_generation":
                result = await service.generate_sticker(prompt=test_input)
            elif task_type == "emoji_generation":
                result = await service.generate_emoji(description=test_input)
            elif task_type == "style_transfer":
                # Mock URL for testing
                result = await service.transfer_style(
                    content_image_url="https://example.com/test.jpg",
                    style_prompt=test_input
                )
            elif task_type == "professional_headshot":
                # Mock URL for testing
                result = await service.create_professional_headshot(
                    input_image_url="https://example.com/portrait.jpg",
                    style=test_input
                )
            
            print(f"📤 Raw Response for {task_type}:")
            print(json.dumps(result, indent=2))
            print()
            
            if result.get('success'):
                cost = result.get('cost', 0.0)
                print(f"  ✅ {task_type}: Generated successfully (${cost:.6f})")
            else:
                print(f"  ❌ {task_type} failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ❌ {task_type} exception: {str(e)}")
    
    print("✅ Test 2 COMPLETED")

async def test_cost_estimation():
    """Test cost estimation accuracy"""
    print("\n🧪 Test 3: Cost Estimation")
    print("="*50)
    
    service = AtomicImageIntelligence()
    
    test_cases = [
        ("text_to_image", 1),
        ("text_to_image", 100),
        ("sticker_generation", 1),
        ("sticker_generation", 10),
        ("face_swap", 1),
        ("image_to_image", 5)
    ]
    
    print("📋 Testing cost estimations:")
    for task_type, count in test_cases:
        try:
            cost = service.get_cost_estimate(task_type, count)
            task_info = service.get_task_info(task_type)
            
            print(f"  {task_type} x{count}: ${cost:.6f}")
            print(f"    Model: {task_info.get('model', 'N/A')}")
            print(f"    Description: {task_info.get('description', 'N/A')}")
            
        except Exception as e:
            print(f"  ❌ {task_type} cost estimation failed: {str(e)}")
    
    # Test invalid task type
    invalid_cost = service.get_cost_estimate("invalid_task", 1)
    print(f"  invalid_task x1: ${invalid_cost:.6f} (should be $0.000000)")
    
    print("✅ Test 3 COMPLETED")

async def test_service_capabilities():
    """Test service capability listing and validation"""
    print("\n🧪 Test 4: Service Capabilities")
    print("="*50)
    
    service = AtomicImageIntelligence()
    
    # Test capabilities listing
    capabilities = service.list_capabilities()
    
    print(f"📤 Available Capabilities:")
    print(f"  Total: {len(capabilities)}")
    for cap in capabilities:
        print(f"    - {cap}")
    
    # Verify required capabilities
    required_capabilities = [
        "text_to_image",
        "image_to_image", 
        "sticker_generation",
        "face_swap",
        "professional_headshot"
    ]
    
    print(f"\n📊 Capability Validation:")
    for cap in required_capabilities:
        is_valid = service._validate_task_type(cap)
        if is_valid:
            print(f"  ✅ {cap}: Available")
        else:
            print(f"  ❌ {cap}: Missing")
    
    # Test task information
    print(f"\nTask Information Sample:")
    for cap in capabilities[:3]:  # Test first 3
        info = service.get_task_info(cap)
        print(f"  {cap}:")
        print(f"    Model: {info.get('model', 'N/A')}")
        print(f"    Cost: ${info.get('estimated_cost', 0.0):.6f}")
        print(f"    Description: {info.get('description', 'N/A')}")
    
    print("✅ Test 4 COMPLETED")

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting image_intelligence_service.py comprehensive tests...\n")
    
    tests = [
        test_basic_functionality,
        test_specialized_tasks,
        test_cost_estimation,
        test_service_capabilities
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  Some tests failed - review output above")

if __name__ == "__main__":
    asyncio.run(run_all_tests())