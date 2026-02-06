#!/usr/bin/env python3
"""
Test script for text_generator.py
"""

import asyncio
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.intelligent_tools.language.text_generator import generate, text_generator

async def test_basic_generation():
    """Test basic text generation"""
    print("🧪 Test 1: Basic Text Generation")
    print("="*50)
    
    prompt = "What are the benefits of renewable energy?"
    
    try:
        result = await generate(prompt)
        
        print(f"📤 Prompt: {prompt}")
        print(f"📄 Generated Text:")
        print(result)
        print()
        print("✅ Basic generation PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Basic generation FAILED: {e}")
        return False

async def test_with_parameters():
    """Test generation with different parameters"""
    print("\n🧪 Test 2: Generation with Parameters")
    print("="*50)
    
    prompt = "Write a short story about a robot learning to paint."
    
    try:
        # Test with creative temperature
        creative_result = await generate(prompt, temperature=0.9, max_tokens=200)
        
        print(f"📤 Prompt: {prompt}")
        print(f"🎨 Creative Result (temp=0.9):")
        print(creative_result)
        print()
        
        # Test with conservative temperature
        conservative_result = await generate(prompt, temperature=0.1, max_tokens=200)
        
        print(f"🔒 Conservative Result (temp=0.1):")
        print(conservative_result)
        print()
        print("✅ Parameter testing PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Parameter testing FAILED: {e}")
        return False

async def test_class_usage():
    """Test using the TextGenerator class directly"""
    print("\n🧪 Test 3: Direct Class Usage")
    print("="*50)
    
    prompt = "Explain quantum computing in one paragraph."
    
    try:
        result = await text_generator.generate(prompt, temperature=0.5)
        
        print(f"📤 Prompt: {prompt}")
        print(f"📄 Class Result:")
        print(result)
        print()
        print("✅ Class usage PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Class usage FAILED: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Text Generator Tests...\n")
    
    tests = [
        test_basic_generation,
        test_with_parameters,
        test_class_usage
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
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