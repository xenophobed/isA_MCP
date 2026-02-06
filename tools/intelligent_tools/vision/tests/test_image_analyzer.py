#!/usr/bin/env python
"""
Comprehensive tests for image_analyzer atomic function

Tests the generic VLM wrapper functionality with real images and real VLM calls.
No mocks - uses actual ISA client and real image analysis.
"""

import asyncio
import tempfile
import os
import sys
from typing import Dict, Any

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

# Import the module to test
from tools.intelligent_tools.vision.image_analyzer import ImageAnalyzer, ImageAnalysisResult, analyze


class TestImageAnalyzer:
    """Test suite for ImageAnalyzer atomic function with real data"""
    
    def __init__(self):
        """Initialize test suite"""
        self.analyzer = ImageAnalyzer()
        self.test_images = {}
        
    def _create_test_image(self, image_type: str) -> str:
        """Create different types of test images"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            if image_type == "simple_color":
                # Simple colored square
                img = Image.new('RGB', (200, 200), color='red')
                
            elif image_type == "with_text":
                # Image with text
                img = Image.new('RGB', (400, 200), color='white')
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
                except:
                    font = ImageFont.load_default()
                draw.text((50, 80), "HELLO WORLD", fill='black', font=font)
                
            elif image_type == "ui_elements":
                # Mock UI elements
                img = Image.new('RGB', (600, 400), color='lightgray')
                draw = ImageDraw.Draw(img)
                
                # Draw button
                draw.rectangle([50, 50, 150, 100], fill='blue', outline='darkblue', width=2)
                draw.text((75, 70), "Button", fill='white')
                
                # Draw input field
                draw.rectangle([200, 50, 400, 100], fill='white', outline='gray', width=2)
                draw.text((210, 70), "Search...", fill='gray')
                
                # Draw link
                draw.text((50, 150), "Click here", fill='blue')
                
            elif image_type == "complex_scene":
                # Complex scene with multiple elements
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)
                
                # Header
                draw.rectangle([0, 0, 800, 80], fill='darkblue')
                draw.text((20, 30), "Website Header", fill='white')
                
                # Navigation
                nav_items = ["Home", "About", "Contact"]
                for i, item in enumerate(nav_items):
                    x = 500 + i * 80
                    draw.text((x, 30), item, fill='white')
                
                # Content area
                draw.rectangle([50, 120, 750, 500], fill='lightblue', outline='gray')
                draw.text((70, 150), "Main Content Area", fill='black')
                
            else:  # default
                img = Image.new('RGB', (100, 100), color='green')
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                img.save(tmp.name, 'PNG')
                return tmp.name
                
        except ImportError:
            # Fallback: create minimal PNG
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                # Write minimal PNG header
                tmp.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
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
    
    async def test_analyze_simple_color_image(self):
        """Test analyze with simple colored image"""
        print("\n🧪 Testing simple color image analysis...")
        
        # Create test image
        image_path = self._create_test_image("simple_color")
        self.test_images["simple_color"] = image_path
        
        try:
            result = await self.analyzer.analyze(
                image=image_path,
                prompt="Describe the color and shape you see in this image",
                provider="openai"
            )
            
            # Verify result structure
            assert isinstance(result, ImageAnalysisResult)
            assert result.success is True, f"Analysis failed: {result.error}"
            assert result.response is not None and len(result.response) > 0
            assert result.processing_time > 0
            
            print(f"✅ Success: {result.response}")
            print(f"   Model: {result.model_used}")
            print(f"   Time: {result.processing_time:.3f}s")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
    
    async def test_analyze_text_image(self):
        """Test analyze with image containing text"""
        print("\n🧪 Testing text extraction from image...")
        
        # Create image with text
        image_path = self._create_test_image("with_text")
        self.test_images["with_text"] = image_path
        
        try:
            result = await self.analyzer.analyze(
                image=image_path,
                prompt="Extract and read all text visible in this image",
                provider="openai"
            )
            
            assert isinstance(result, ImageAnalysisResult)
            assert result.success is True, f"Analysis failed: {result.error}"
            assert result.response is not None
            
            print(f"✅ Text extraction result: {result.response}")
            print(f"   Model: {result.model_used}")
            print(f"   Time: {result.processing_time:.3f}s")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
    
    async def test_analyze_ui_elements(self):
        """Test analyze with UI elements detection"""
        print("\n🧪 Testing UI elements analysis...")
        
        # Create UI elements image
        image_path = self._create_test_image("ui_elements")
        self.test_images["ui_elements"] = image_path
        
        try:
            result = await self.analyzer.analyze(
                image=image_path,
                prompt="Identify and describe all UI elements in this image, including buttons, input fields, and links",
                provider="openai"
            )
            
            assert isinstance(result, ImageAnalysisResult)
            assert result.success is True, f"Analysis failed: {result.error}"
            assert result.response is not None
            
            print(f"✅ UI analysis result: {result.response}")
            print(f"   Model: {result.model_used}")
            print(f"   Time: {result.processing_time:.3f}s")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
    
    async def test_analyze_with_bytes_input(self):
        """Test analyze with bytes input instead of file path"""
        print("\n🧪 Testing bytes input analysis...")
        
        # Create test image and read as bytes
        image_path = self._create_test_image("simple_color")
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Clean up original file
        os.unlink(image_path)
        
        try:
            result = await self.analyzer.analyze(
                image=image_bytes,
                prompt="What color is this image?",
                provider="openai"
            )
            
            assert isinstance(result, ImageAnalysisResult)
            assert result.success is True, f"Analysis failed: {result.error}"
            assert result.response is not None
            
            print(f"✅ Bytes analysis result: {result.response}")
            print(f"   Model: {result.model_used}")
            print(f"   Time: {result.processing_time:.3f}s")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
    
    async def test_analyze_different_prompts(self):
        """Test analyze with various prompt types"""
        print("\n🧪 Testing different prompt types...")
        
        # Create complex scene image
        image_path = self._create_test_image("complex_scene")
        self.test_images["complex_scene"] = image_path
        
        test_prompts = [
            "Describe the overall layout and structure of this webpage",
            "Count how many interactive elements are visible", 
            "What is the main color scheme used?",
            "List all text content you can see"
        ]
        
        for i, prompt in enumerate(test_prompts):
            try:
                print(f"\n   Testing prompt {i+1}: {prompt[:50]}...")
                
                result = await self.analyzer.analyze(
                    image=image_path,
                    prompt=prompt,
                    provider="openai"
                )
                
                assert isinstance(result, ImageAnalysisResult)
                assert result.success is True, f"Analysis failed: {result.error}"
                assert result.response is not None
                
                print(f"   ✅ Response: {result.response[:100]}...")
                
            except Exception as e:
                print(f"   ❌ Prompt {i+1} failed: {e}")
                raise
    
    async def test_analyze_invalid_image_input(self):
        """Test analyze with invalid image input"""
        print("\n🧪 Testing invalid image input...")
        
        try:
            result = await self.analyzer.analyze(
                image=12345,  # Invalid type
                prompt="Test prompt"
            )
            
            # Should fail gracefully
            assert isinstance(result, ImageAnalysisResult)
            assert result.success is False
            assert "Unsupported image type" in result.error
            
            print(f"✅ Correctly handled invalid input: {result.error}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
    
    async def test_convenience_function(self):
        """Test the convenience analyze function"""
        print("\n🧪 Testing convenience function...")
        
        # Create test image
        image_path = self._create_test_image("simple_color")
        self.test_images["convenience"] = image_path
        
        try:
            result = await analyze(
                image=image_path,
                prompt="What do you see?",
                provider="openai"
            )
            
            assert isinstance(result, ImageAnalysisResult)
            assert result.success is True, f"Analysis failed: {result.error}"
            assert result.response is not None
            
            print(f"✅ Convenience function works: {result.response}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise


# Test runner
async def run_all_tests():
    """Run all image_analyzer tests with real VLM calls"""
    print("🧪 Running comprehensive image_analyzer tests with real data...\n")
    
    tester = TestImageAnalyzer()
    
    try:
        # Run all tests
        await tester.test_analyze_simple_color_image()
        await tester.test_analyze_text_image()
        await tester.test_analyze_ui_elements()
        await tester.test_analyze_with_bytes_input()
        await tester.test_analyze_different_prompts()
        await tester.test_analyze_invalid_image_input()
        await tester.test_convenience_function()
        
        print("\n🎉 All image_analyzer tests completed successfully!")
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        raise
        
    finally:
        # Cleanup
        tester.cleanup_test_images()
        print("🧹 Cleaned up test images")


if __name__ == "__main__":
    print("🚀 Starting image_analyzer atomic function tests...")
    asyncio.run(run_all_tests())