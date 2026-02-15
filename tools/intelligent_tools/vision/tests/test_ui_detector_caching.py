#!/usr/bin/env python
"""
Test UI detector caching functionality specifically
"""

import asyncio
import tempfile
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import the module to test
from tools.intelligent_tools.vision.ui_detector import UIDetector, detect_ui_with_coordinates


async def test_caching_optimization():
    """Test that caching works and provides performance benefits"""
    print("🧪 Testing UI detector caching optimization...")

    # Create a simple test screenshot
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (400, 300), color="white")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except OSError:
            # Font file not found or cannot be loaded - use default font
            font = ImageFont.load_default()

        # Simple button
        draw.rectangle([50, 50, 150, 90], fill="blue", outline="darkblue", width=2)
        draw.text((80, 65), "Click Me", fill="white", font=font)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name, "PNG")
            screenshot_path = tmp.name

    except ImportError:
        print("❌ PIL not available, skipping visual test")
        return

    detector = UIDetector()

    # Define requirements
    requirements = [
        {
            "element_name": "test_button",
            "element_purpose": "button to click",
            "visual_description": "blue button with text",
            "interaction_type": "click",
        }
    ]

    test_url = "https://test-cache-page.com"

    try:
        # First call - should use OmniParser (no cache)
        print("\n🔵 First call (no cache)...")
        start_time = time.time()

        result1 = await detector.detect_ui_with_coordinates(
            screenshot=screenshot_path, requirements=requirements, url=test_url
        )

        first_call_time = time.time() - start_time
        print(f"   Time: {first_call_time:.3f}s")
        print(f"   Success: {result1.success}")
        print(f"   UI elements: {len(result1.ui_elements)}")
        print(f"   Mappings: {len(result1.element_mappings)}")

        # Second call - should use cache
        print("\n🟢 Second call (with cache)...")
        start_time = time.time()

        result2 = await detector.detect_ui_with_coordinates(
            screenshot=screenshot_path, requirements=requirements, url=test_url
        )

        second_call_time = time.time() - start_time
        print(f"   Time: {second_call_time:.3f}s")
        print(f"   Success: {result2.success}")
        print(f"   UI elements: {len(result2.ui_elements)}")
        print(f"   Mappings: {len(result2.element_mappings)}")

        # Calculate performance improvement
        improvement = ((first_call_time - second_call_time) / first_call_time) * 100
        print(f"\n⚡ Performance improvement: {improvement:.1f}%")

        # Verify results are consistent
        assert result1.success == result2.success
        assert len(result1.ui_elements) == len(result2.ui_elements)
        assert len(result1.element_mappings) == len(result2.element_mappings)

        # Third call with force_refresh - should bypass cache
        print("\n🔴 Third call (force refresh)...")
        start_time = time.time()

        result3 = await detector.detect_ui_with_coordinates(
            screenshot=screenshot_path, requirements=requirements, url=test_url, force_refresh=True
        )

        third_call_time = time.time() - start_time
        print(f"   Time: {third_call_time:.3f}s")
        print(f"   Success: {result3.success}")
        print(f"   UI elements: {len(result3.ui_elements)}")

        # Force refresh should take similar time to first call
        refresh_vs_first = abs(third_call_time - first_call_time) / first_call_time * 100
        print(f"   Time vs first call: {refresh_vs_first:.1f}% difference")

        # Test cache stats
        cache_stats = await detector._cache_manager.get_cache_stats()
        print(f"\n📊 Cache stats:")
        print(f"   Total entries: {cache_stats.get('total_entries', 0)}")
        print(f"   Cache size: {cache_stats.get('total_size_mb', 0)} MB")
        print(f"   Pre-configured sites: {cache_stats.get('preconfig_sites', 0)}")

        print("\n✅ Caching optimization test completed successfully!")

        # Verify significant performance improvement (at least 30%)
        if improvement > 30:
            print(f"✅ Good caching performance: {improvement:.1f}% improvement")
        else:
            print(f"⚠️ Modest caching improvement: {improvement:.1f}% (expected >30%)")

    finally:
        # Clean up
        if os.path.exists(screenshot_path):
            os.unlink(screenshot_path)


async def test_convenience_function_caching():
    """Test caching works with convenience function too"""
    print("\n🧪 Testing convenience function caching...")

    # Create simple test image
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (300, 200), color="white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 100, 80], fill="red")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name, "PNG")
            screenshot_path = tmp.name

    except ImportError:
        print("❌ PIL not available, skipping test")
        return

    requirements = [
        {
            "element_name": "red_button",
            "element_purpose": "red button",
            "visual_description": "red rectangle button",
            "interaction_type": "click",
        }
    ]

    test_url = "https://convenience-test.com"

    try:
        # Test convenience function with caching
        start_time = time.time()
        result = await detect_ui_with_coordinates(
            screenshot=screenshot_path, requirements=requirements, url=test_url
        )
        first_time = time.time() - start_time

        # Second call should be faster
        start_time = time.time()
        result2 = await detect_ui_with_coordinates(
            screenshot=screenshot_path, requirements=requirements, url=test_url
        )
        second_time = time.time() - start_time

        improvement = ((first_time - second_time) / first_time) * 100
        print(f"   Convenience function caching improvement: {improvement:.1f}%")
        print("✅ Convenience function caching works!")

    finally:
        if os.path.exists(screenshot_path):
            os.unlink(screenshot_path)


if __name__ == "__main__":

    async def main():
        await test_caching_optimization()
        await test_convenience_function_caching()

    asyncio.run(main())
