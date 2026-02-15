#!/usr/bin/env python
"""
Quick test to debug VLM matching issue
"""

import asyncio
import tempfile
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))

from tools.intelligent_tools.vision.ui_detector import UIDetector


async def test_vlm_matching():
    """Test VLM matching with simple case"""
    print("🧪 Testing VLM matching debug...")

    detector = UIDetector()

    # Create simple test image
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (400, 200), color="white")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except OSError:
            # Font file not found or cannot be loaded - use default font
            font = ImageFont.load_default()

        # Draw simple button
        draw.rectangle([50, 50, 150, 90], fill="blue", outline="darkblue", width=2)
        draw.text((80, 65), "Click", fill="white", font=font)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name, "PNG")
            test_path = tmp.name

    except ImportError:
        print("❌ PIL not available, creating minimal test")
        return

    try:
        # Simple requirements
        requirements = [
            {
                "element_name": "button",
                "element_purpose": "click button",
                "visual_description": "blue button",
                "interaction_type": "click",
            }
        ]

        # Run detection
        result = await detector.detect_ui_with_coordinates(
            screenshot=test_path, requirements=requirements
        )

        print(f"✅ Detection result:")
        print(f"   Success: {result.success}")
        print(f"   UI elements found: {len(result.ui_elements)}")
        print(f"   Element mappings: {len(result.element_mappings)}")
        print(f"   Error: {result.error}")

        if result.element_mappings:
            for name, mapping in result.element_mappings.items():
                print(f"   {name}: ({mapping['x']}, {mapping['y']}) - {mapping['action']}")

    finally:
        if os.path.exists(test_path):
            os.unlink(test_path)


if __name__ == "__main__":
    asyncio.run(test_vlm_matching())
