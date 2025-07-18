"""
Test suite for OCR Extractor service.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the parent directory to the path to import ocr_extractor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr_extractor import OCRExtractor


class TestOCRExtractor:
    """Test cases for OCR Extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create an OCR extractor instance for testing."""
        return OCRExtractor()
    
    @pytest.fixture
    def mock_client_response(self):
        """Mock successful client response."""
        return {
            "success": True,
            "result": {
                "text_results": [
                    {"text": "Hello World", "confidence": 0.95},
                    {"text": "Sample Text", "confidence": 0.88},
                    {"text": "OCR Test", "confidence": 0.72}
                ]
            }
        }
    
    @pytest.fixture
    def mock_error_response(self):
        """Mock error response."""
        return {
            "success": False,
            "error": "Failed to process image"
        }
    
    @pytest.mark.asyncio
    async def test_extract_text_success(self, extractor, mock_client_response):
        """Test successful text extraction."""
        with patch.object(extractor.client, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_client_response
            
            result = await extractor.extract_text("test_image.png", ["en"])
            
            assert result["success"] is True
            assert len(result["text_results"]) == 3
            assert result["total_text"] == "Hello World Sample Text OCR Test"
            assert result["total_characters"] == 32
            assert result["region_count"] == 3
            
            # Verify client was called with correct parameters
            mock_invoke.assert_called_once_with(
                input_data="test_image.png",
                task="extract",
                service_type="vision",
                model="isa-suryaocr",
                provider="isa",
                languages=["en"]
            )
    
    @pytest.mark.asyncio
    async def test_extract_text_default_language(self, extractor, mock_client_response):
        """Test extraction with default language."""
        with patch.object(extractor.client, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_client_response
            
            result = await extractor.extract_text("test_image.png")
            
            assert result["success"] is True
            mock_invoke.assert_called_once_with(
                input_data="test_image.png",
                task="extract",
                service_type="vision",
                model="isa-suryaocr",
                provider="isa",
                languages=["en"]
            )
    
    @pytest.mark.asyncio
    async def test_extract_text_failure(self, extractor, mock_error_response):
        """Test extraction failure handling."""
        with patch.object(extractor.client, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_error_response
            
            result = await extractor.extract_text("test_image.png")
            
            assert result["success"] is False
            assert "Failed to process image" in result["error"]
    
    @pytest.mark.asyncio
    async def test_extract_text_exception(self, extractor):
        """Test extraction with exception handling."""
        with patch.object(extractor.client, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.side_effect = Exception("Network error")
            
            result = await extractor.extract_text("test_image.png")
            
            assert result["success"] is False
            assert "OCR extraction failed: Network error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_extract_with_confidence_filter(self, extractor, mock_client_response):
        """Test confidence filtering functionality."""
        with patch.object(extractor.client, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_client_response
            
            result = await extractor.extract_with_confidence_filter(
                "test_image.png", 
                min_confidence=0.8,
                languages=["en"]
            )
            
            assert result["success"] is True
            assert len(result["text_results"]) == 2  # Only items with confidence >= 0.8
            assert result["total_text"] == "Hello World Sample Text"
            assert result["confidence_threshold"] == 0.8
    
    @pytest.mark.asyncio
    async def test_extract_with_confidence_filter_high_threshold(self, extractor, mock_client_response):
        """Test confidence filtering with high threshold."""
        with patch.object(extractor.client, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_client_response
            
            result = await extractor.extract_with_confidence_filter(
                "test_image.png", 
                min_confidence=0.9
            )
            
            assert result["success"] is True
            assert len(result["text_results"]) == 1  # Only items with confidence >= 0.9
            assert result["total_text"] == "Hello World"
    
    @pytest.mark.asyncio
    async def test_extract_with_confidence_filter_failure(self, extractor, mock_error_response):
        """Test confidence filtering when extraction fails."""
        with patch.object(extractor.client, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_error_response
            
            result = await extractor.extract_with_confidence_filter("test_image.png")
            
            assert result["success"] is False
            assert "Failed to process image" in result["error"]
    
    def test_print_results_success(self, extractor, capsys):
        """Test printing successful results."""
        result = {
            "success": True,
            "region_count": 3,
            "total_characters": 32,
            "text_results": [
                {"text": "Hello World", "confidence": 0.95},
                {"text": "Sample Text", "confidence": 0.88},
                {"text": "OCR Test", "confidence": 0.72}
            ]
        }
        
        extractor.print_results(result)
        captured = capsys.readouterr()
        
        assert "OCR extraction successful!" in captured.out
        assert "Extracted 3 text regions" in captured.out
        assert "Total characters: 32" in captured.out
        assert "Hello World" in captured.out
        assert "confidence: 0.950" in captured.out
    
    def test_print_results_failure(self, extractor, capsys):
        """Test printing failure results."""
        result = {
            "success": False,
            "error": "Test error message"
        }
        
        extractor.print_results(result)
        captured = capsys.readouterr()
        
        assert "OCR extraction failed: Test error message" in captured.out
    
    def test_print_results_many_regions(self, extractor, capsys):
        """Test printing results with many regions."""
        text_results = [
            {"text": f"Text {i}", "confidence": 0.8} for i in range(5)
        ]
        
        result = {
            "success": True,
            "region_count": 5,
            "total_characters": 35,
            "text_results": text_results
        }
        
        extractor.print_results(result)
        captured = capsys.readouterr()
        
        assert "... and 2 more regions" in captured.out


if __name__ == "__main__":
    pytest.main([__file__])