#!/usr/bin/env python
"""
Comprehensive tests for ui_detector atomic function

Tests the UI detection and coordinate mapping functionality with real images
and real ISA client calls. No mocks - uses actual OmniParser and VLM analysis.
"""

import asyncio
import tempfile
import os
import sys
from typing import Dict, Any, List

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))

# Import the module to test
from tools.intelligent_tools.vision.ui_detector import (
    UIDetector,
    UIDetectionResult,
    detect_ui_with_coordinates,
    annotate_ui_elements,
)


class TestUIDetector:
    """Test suite for UIDetector atomic function with real data"""

    def __init__(self):
        """Initialize test suite"""
        self.detector = UIDetector()
        self.test_images = {}

    def _create_test_screenshot(self, ui_type: str) -> str:
        """Create different types of UI test screenshots"""
        try:
            from PIL import Image, ImageDraw, ImageFont

            if ui_type == "search_page":
                # Create search page mockup
                img = Image.new("RGB", (800, 600), color="white")
                draw = ImageDraw.Draw(img)

                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
                    large_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
                except:
                    font = ImageFont.load_default()
                    large_font = font

                # Header
                draw.rectangle([0, 0, 800, 80], fill="#4285f4")
                draw.text((20, 30), "Search Engine", fill="white", font=large_font)

                # Search bar
                draw.rectangle([200, 200, 600, 240], fill="white", outline="gray", width=2)
                draw.text((210, 215), "Enter search query...", fill="gray", font=font)

                # Search button
                draw.rectangle([620, 200, 720, 240], fill="#4285f4", outline="darkblue", width=2)
                draw.text((650, 215), "Search", fill="white", font=font)

                # Navigation links
                nav_links = ["Images", "Videos", "News", "Maps"]
                for i, link in enumerate(nav_links):
                    x = 50 + i * 100
                    draw.text((x, 120), link, fill="blue", font=font)

                # Results area
                draw.rectangle([50, 280, 750, 550], fill="#f8f9fa", outline="lightgray")
                draw.text((60, 300), "Search results will appear here", fill="gray", font=font)

            elif ui_type == "form_page":
                # Create form page mockup
                img = Image.new("RGB", (600, 500), color="white")
                draw = ImageDraw.Draw(img)

                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
                    title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
                except:
                    font = ImageFont.load_default()
                    title_font = font

                # Title
                draw.text((50, 30), "Contact Form", fill="black", font=title_font)

                # Name field
                draw.text((50, 80), "Name:", fill="black", font=font)
                draw.rectangle([50, 100, 400, 130], fill="white", outline="gray", width=1)

                # Email field
                draw.text((50, 150), "Email:", fill="black", font=font)
                draw.rectangle([50, 170, 400, 200], fill="white", outline="gray", width=1)

                # Message field
                draw.text((50, 220), "Message:", fill="black", font=font)
                draw.rectangle([50, 240, 400, 320], fill="white", outline="gray", width=1)

                # Submit button
                draw.rectangle([50, 350, 150, 380], fill="green", outline="darkgreen", width=2)
                draw.text((80, 360), "Submit", fill="white", font=font)

                # Cancel button
                draw.rectangle([170, 350, 270, 380], fill="red", outline="darkred", width=2)
                draw.text((200, 360), "Cancel", fill="white", font=font)

            elif ui_type == "ecommerce_page":
                # Create e-commerce page mockup
                img = Image.new("RGB", (900, 700), color="white")
                draw = ImageDraw.Draw(img)

                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
                    title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
                except:
                    font = ImageFont.load_default()
                    title_font = font

                # Header with search
                draw.rectangle([0, 0, 900, 60], fill="#232f3e")
                draw.text((20, 20), "ShopSite", fill="white", font=title_font)

                # Search bar in header
                draw.rectangle([300, 15, 600, 45], fill="white", outline="gray", width=1)
                draw.text((310, 25), "Search products...", fill="gray", font=font)

                # Search button
                draw.rectangle([610, 15, 680, 45], fill="orange", outline="darkorange", width=2)
                draw.text((630, 25), "Search", fill="white", font=font)

                # Cart button
                draw.rectangle([750, 15, 850, 45], fill="green", outline="darkgreen", width=2)
                draw.text((780, 25), "Cart (2)", fill="white", font=font)

                # Product image placeholder
                draw.rectangle([50, 100, 300, 300], fill="lightgray", outline="gray", width=2)
                draw.text((120, 190), "Product Image", fill="black", font=font)

                # Product details
                draw.text((350, 120), "Amazing Product", fill="black", font=title_font)
                draw.text((350, 150), "Price: $99.99", fill="black", font=font)
                draw.text((350, 180), "In Stock", fill="green", font=font)

                # Quantity selector
                draw.text((350, 220), "Quantity:", fill="black", font=font)
                draw.rectangle([420, 215, 470, 245], fill="white", outline="gray", width=1)
                draw.text((435, 225), "1", fill="black", font=font)

                # Add to cart button
                draw.rectangle([350, 270, 500, 310], fill="orange", outline="darkorange", width=2)
                draw.text((390, 285), "Add to Cart", fill="white", font=font)

                # Buy now button
                draw.rectangle([520, 270, 650, 310], fill="red", outline="darkred", width=2)
                draw.text((560, 285), "Buy Now", fill="white", font=font)

            else:  # simple_ui
                # Simple UI with basic elements
                img = Image.new("RGB", (400, 300), color="white")
                draw = ImageDraw.Draw(img)

                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
                except:
                    font = ImageFont.load_default()

                # Simple button
                draw.rectangle([50, 50, 150, 90], fill="blue", outline="darkblue", width=2)
                draw.text((80, 65), "Click Me", fill="white", font=font)

                # Input field
                draw.rectangle([50, 120, 300, 150], fill="white", outline="gray", width=1)
                draw.text((60, 130), "Type here...", fill="gray", font=font)

                # Link
                draw.text((50, 180), "Learn More", fill="blue", font=font)

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                img.save(tmp.name, "PNG")
                return tmp.name

        except ImportError:
            # Fallback: create minimal PNG
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00d\x00\x00\x00d\x08\x02\x00\x00\x00\xff\x80\x02\x03"
                )
                return tmp.name

    def cleanup_test_images(self):
        """Clean up all test images"""
        for path in self.test_images.values():
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except:
                    pass
        self.test_images.clear()

    async def test_simple_ui_detection(self):
        """Test UI detection with simple UI elements"""
        print("\n🧪 Testing simple UI detection...")

        # Create simple UI screenshot
        screenshot_path = self._create_test_screenshot("simple_ui")
        self.test_images["simple_ui"] = screenshot_path

        # Define requirements for simple UI
        requirements = [
            {
                "element_name": "click_button",
                "element_purpose": "button to click",
                "visual_description": "blue button with text",
                "interaction_type": "click",
            },
            {
                "element_name": "text_input",
                "element_purpose": "input field for text",
                "visual_description": "white input field with placeholder",
                "interaction_type": "type",
            },
        ]

        try:
            result = await self.detector.detect_ui_with_coordinates(
                screenshot=screenshot_path, requirements=requirements
            )

            # Verify result structure
            assert isinstance(result, UIDetectionResult)
            assert result.success is True, f"UI detection failed: {result.error}"
            assert len(result.ui_elements) > 0, "No UI elements detected"
            assert result.annotated_image_path is not None
            assert os.path.exists(result.annotated_image_path)

            print(f"✅ Detected {len(result.ui_elements)} UI elements")
            print(f"   Annotated image: {result.annotated_image_path}")
            print(f"   Element mappings: {len(result.element_mappings)}")
            print(f"   Processing time: {result.processing_time:.3f}s")

            # Verify element mappings
            for element_name, mapping in result.element_mappings.items():
                assert "x" in mapping and "y" in mapping
                assert mapping["x"] > 0 and mapping["y"] > 0
                print(f"   {element_name}: ({mapping['x']}, {mapping['y']}) - {mapping['action']}")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    async def test_search_page_detection(self):
        """Test UI detection with search page elements"""
        print("\n🧪 Testing search page UI detection...")

        # Create search page screenshot
        screenshot_path = self._create_test_screenshot("search_page")
        self.test_images["search_page"] = screenshot_path

        # Define requirements for search functionality
        requirements = [
            {
                "element_name": "search_input",
                "element_purpose": "search query input field",
                "visual_description": "white rectangular input field with placeholder text",
                "interaction_type": "click_and_type",
            },
            {
                "element_name": "search_button",
                "element_purpose": "submit search query",
                "visual_description": "blue button with Search text",
                "interaction_type": "click",
            },
            {
                "element_name": "images_link",
                "element_purpose": "navigate to images search",
                "visual_description": "blue text link saying Images",
                "interaction_type": "click",
            },
        ]

        try:
            result = await self.detector.detect_ui_with_coordinates(
                screenshot=screenshot_path, requirements=requirements
            )

            assert isinstance(result, UIDetectionResult)
            assert result.success is True, f"UI detection failed: {result.error}"
            assert len(result.ui_elements) > 0

            print(f"✅ Search page detection successful")
            print(f"   Found {len(result.ui_elements)} UI elements")
            print(f"   Mapped {len(result.element_mappings)} requirements")

            # Check if we found the key elements
            expected_elements = ["search_input", "search_button"]
            for element in expected_elements:
                if element in result.element_mappings:
                    mapping = result.element_mappings[element]
                    print(f"   {element}: ({mapping['x']}, {mapping['y']}) - {mapping['action']}")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    async def test_form_page_detection(self):
        """Test UI detection with form elements"""
        print("\n🧪 Testing form page UI detection...")

        # Create form page screenshot
        screenshot_path = self._create_test_screenshot("form_page")
        self.test_images["form_page"] = screenshot_path

        # Define requirements for form interaction
        requirements = [
            {
                "element_name": "name_field",
                "element_purpose": "input field for name",
                "visual_description": "white input field under Name label",
                "interaction_type": "click_and_type",
            },
            {
                "element_name": "email_field",
                "element_purpose": "input field for email",
                "visual_description": "white input field under Email label",
                "interaction_type": "click_and_type",
            },
            {
                "element_name": "submit_button",
                "element_purpose": "submit the form",
                "visual_description": "green button with Submit text",
                "interaction_type": "click",
            },
        ]

        try:
            result = await self.detector.detect_ui_with_coordinates(
                screenshot=screenshot_path, requirements=requirements
            )

            assert isinstance(result, UIDetectionResult)
            assert result.success is True, f"UI detection failed: {result.error}"

            print(f"✅ Form detection successful")
            print(f"   Processing time: {result.processing_time:.3f}s")

            # Verify form elements mapping
            for element_name, mapping in result.element_mappings.items():
                print(f"   {element_name}: ({mapping['x']}, {mapping['y']}) - {mapping['action']}")

                # Verify coordinates are reasonable for form layout
                assert mapping["x"] > 0 and mapping["y"] > 0
                assert mapping["x"] < 600 and mapping["y"] < 500  # Within image bounds

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    async def test_ecommerce_page_detection(self):
        """Test UI detection with e-commerce elements"""
        print("\n🧪 Testing e-commerce page UI detection...")

        # Create e-commerce page screenshot
        screenshot_path = self._create_test_screenshot("ecommerce_page")
        self.test_images["ecommerce_page"] = screenshot_path

        # Define requirements for e-commerce interaction
        requirements = [
            {
                "element_name": "product_search",
                "element_purpose": "search for products",
                "visual_description": "white search input in header",
                "interaction_type": "click_and_type",
            },
            {
                "element_name": "add_to_cart",
                "element_purpose": "add product to shopping cart",
                "visual_description": "orange button with Add to Cart text",
                "interaction_type": "click",
            },
            {
                "element_name": "cart_button",
                "element_purpose": "view shopping cart",
                "visual_description": "green button with Cart text in header",
                "interaction_type": "click",
            },
        ]

        try:
            result = await self.detector.detect_ui_with_coordinates(
                screenshot=screenshot_path, requirements=requirements
            )

            assert isinstance(result, UIDetectionResult)
            assert result.success is True, f"UI detection failed: {result.error}"

            print(f"✅ E-commerce detection successful")
            print(f"   Found {len(result.ui_elements)} total UI elements")
            print(f"   Mapped {len(result.element_mappings)} requirements")

            # Verify e-commerce specific elements
            for element_name, mapping in result.element_mappings.items():
                print(f"   {element_name}: ({mapping['x']}, {mapping['y']}) - {mapping['action']}")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    async def test_bytes_input_detection(self):
        """Test UI detection with image bytes input"""
        print("\n🧪 Testing UI detection with bytes input...")

        # Create screenshot and read as bytes
        screenshot_path = self._create_test_screenshot("simple_ui")
        with open(screenshot_path, "rb") as f:
            screenshot_bytes = f.read()

        # Clean up original file
        os.unlink(screenshot_path)

        requirements = [
            {
                "element_name": "button",
                "element_purpose": "clickable button",
                "visual_description": "blue button",
                "interaction_type": "click",
            }
        ]

        try:
            result = await self.detector.detect_ui_with_coordinates(
                screenshot=screenshot_bytes, requirements=requirements
            )

            assert isinstance(result, UIDetectionResult)
            assert result.success is True, f"UI detection failed: {result.error}"

            print(f"✅ Bytes input detection successful")
            print(f"   Processing time: {result.processing_time:.3f}s")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    async def test_annotate_ui_elements_function(self):
        """Test the annotate_ui_elements convenience function"""
        print("\n🧪 Testing UI annotation function...")

        # Create test screenshot
        screenshot_path = self._create_test_screenshot("form_page")
        self.test_images["annotation"] = screenshot_path

        try:
            annotated_path = await self.detector.annotate_ui_elements(screenshot=screenshot_path)

            assert annotated_path is not None
            assert os.path.exists(annotated_path)
            assert annotated_path.endswith("_annotated.png")

            print(f"✅ UI annotation successful")
            print(f"   Annotated image: {annotated_path}")

            # Clean up annotated image
            if os.path.exists(annotated_path):
                os.unlink(annotated_path)

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    async def test_convenience_function(self):
        """Test the convenience detect_ui_with_coordinates function"""
        print("\n🧪 Testing convenience function...")

        # Create test screenshot
        screenshot_path = self._create_test_screenshot("simple_ui")
        self.test_images["convenience"] = screenshot_path

        requirements = [
            {
                "element_name": "test_button",
                "element_purpose": "test button",
                "visual_description": "blue button",
                "interaction_type": "click",
            }
        ]

        try:
            result = await detect_ui_with_coordinates(
                screenshot=screenshot_path, requirements=requirements
            )

            assert isinstance(result, UIDetectionResult)
            assert result.success is True, f"UI detection failed: {result.error}"

            print(f"✅ Convenience function works")
            print(f"   Processing time: {result.processing_time:.3f}s")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    async def test_vlm_matching_debug(self):
        """Debug test for VLM matching JSON issue"""
        print("\n🧪 Testing VLM matching debug (single button)...")

        # Create simple UI screenshot with one button
        screenshot_path = self._create_test_screenshot("simple_ui")
        self.test_images["vlm_debug"] = screenshot_path

        # Single simple requirement
        requirements = [
            {
                "element_name": "button",
                "element_purpose": "click button",
                "visual_description": "blue button",
                "interaction_type": "click",
            }
        ]

        try:
            result = await self.detector.detect_ui_with_coordinates(
                screenshot=screenshot_path, requirements=requirements
            )

            print(f"🔍 Debug result:")
            print(f"   Success: {result.success}")
            print(f"   UI elements: {len(result.ui_elements)}")
            print(f"   Element mappings: {len(result.element_mappings)}")
            print(f"   Error: {result.error}")

            if result.ui_elements:
                print(f"   First element: {result.ui_elements[0]}")

            if result.element_mappings:
                for name, mapping in result.element_mappings.items():
                    print(f"   Mapping {name}: {mapping}")
            else:
                print("   ⚠️ No element mappings found - VLM matching failed")

        except Exception as e:
            print(f"❌ Debug test failed: {e}")
            raise

    async def test_invalid_input_handling(self):
        """Test UI detection with invalid inputs"""
        print("\n🧪 Testing invalid input handling...")

        requirements = [
            {
                "element_name": "test",
                "element_purpose": "test",
                "visual_description": "test",
                "interaction_type": "click",
            }
        ]

        try:
            # Test with invalid image type
            result = await self.detector.detect_ui_with_coordinates(
                screenshot=12345, requirements=requirements  # Invalid type
            )

            assert isinstance(result, UIDetectionResult)
            assert result.success is False
            assert "Unsupported image type" in result.error

            print(f"✅ Correctly handled invalid input: {result.error}")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise


# Test runner
async def run_all_tests():
    """Run all ui_detector tests with real ISA client calls"""
    print("🧪 Running comprehensive ui_detector tests with real data...\n")

    tester = TestUIDetector()

    try:
        # Run debug test first
        await tester.test_vlm_matching_debug()

        # Run all tests
        await tester.test_simple_ui_detection()
        await tester.test_search_page_detection()
        await tester.test_form_page_detection()
        await tester.test_ecommerce_page_detection()
        await tester.test_bytes_input_detection()
        await tester.test_annotate_ui_elements_function()
        await tester.test_convenience_function()
        await tester.test_invalid_input_handling()

        print("\n🎉 All ui_detector tests completed successfully!")

    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        raise

    finally:
        # Cleanup
        tester.cleanup_test_images()
        print("🧹 Cleaned up test images")


if __name__ == "__main__":
    print("🚀 Starting ui_detector atomic function tests...")
    asyncio.run(run_all_tests())
