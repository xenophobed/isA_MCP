"""
OCR Extractor service using ISA Model Client for text extraction from images.
"""

import asyncio
from typing import List, Dict, Any, Optional
from isa_model.client import ISAModelClient


class OCRExtractor:
    """OCR text extraction service using ISA SuryaOCR model."""

    def __init__(self):
        """Initialize the OCR extractor with ISA Model Client."""
        self._client = None

    async def _get_client(self):
        """Lazy load ISA client"""
        if self._client is None:
            from core.clients.model_client import get_isa_client

            self._client = await get_isa_client()
        return self._client

    async def extract_text(
        self, image_path: str, languages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract text from an image using OCR.

        Args:
            image_path: Path to the image file
            languages: List of language codes (e.g., ["en", "zh"])

        Returns:
            Dictionary containing extraction results
        """
        if languages is None:
            languages = ["en"]

        try:
            client = await self._get_client()

            # Use vision API for OCR
            vision_response = await client.vision.completions.create(
                image=image_path,
                prompt=f"Extract text in languages: {', '.join(languages)}",
                model="isa-suryaocr",
                provider="isa",
            )

            # Parse response
            content = vision_response.choices[0].message.content
            try:
                import json

                response = json.loads(content) if isinstance(content, str) else content
                text_results = (
                    response.get("text_results", []) if isinstance(response, dict) else []
                )
            except:
                # If not JSON, treat entire content as extracted text
                text_results = [{"text": content}]
                total_text = " ".join([item.get("text", "") for item in text_results])

                return {
                    "success": True,
                    "text_results": text_results,
                    "total_text": total_text,
                    "total_characters": len(total_text),
                    "region_count": len(text_results),
                }
            else:
                return {"success": False, "error": result.get("error", "Unknown error occurred")}

        except Exception as e:
            return {"success": False, "error": f"OCR extraction failed: {str(e)}"}

    async def extract_with_confidence_filter(
        self, image_path: str, min_confidence: float = 0.5, languages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract text with confidence filtering.

        Args:
            image_path: Path to the image file
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            languages: List of language codes

        Returns:
            Dictionary containing filtered extraction results
        """
        result = await self.extract_text(image_path, languages)

        if not result["success"]:
            return result

        # Filter results by confidence
        filtered_results = [
            item for item in result["text_results"] if item.get("confidence", 0) >= min_confidence
        ]

        filtered_text = " ".join([item.get("text", "") for item in filtered_results])

        return {
            "success": True,
            "text_results": filtered_results,
            "total_text": filtered_text,
            "total_characters": len(filtered_text),
            "region_count": len(filtered_results),
            "confidence_threshold": min_confidence,
        }

    def print_results(self, result: Dict[str, Any]) -> None:
        """Print OCR extraction results in a formatted way."""
        if not result["success"]:
            print(f"OCR extraction failed: {result['error']}")
            return

        print(f"\nOCR extraction successful!")
        print(f"Extracted {result['region_count']} text regions")
        print(f"Total characters: {result['total_characters']}")

        # Show first few extracted texts
        text_results = result.get("text_results", [])
        for i, item in enumerate(text_results[:3]):
            confidence = item.get("confidence", 0)
            text = item.get("text", "")
            print(f"  Region {i+1}: '{text}' (confidence: {confidence:.3f})")

        if len(text_results) > 3:
            print(f"  ... and {len(text_results) - 3} more regions")


async def main():
    """Example usage of the OCR extractor."""
    extractor = OCRExtractor()

    # Example 1: Basic OCR extraction
    result = await extractor.extract_text("contract.png", languages=["en", "zh"])
    extractor.print_results(result)

    # Example 2: OCR with confidence filtering
    filtered_result = await extractor.extract_with_confidence_filter(
        "contract.png", min_confidence=0.8, languages=["en"]
    )
    print("\n--- Filtered Results (confidence >= 0.8) ---")
    extractor.print_results(filtered_result)


if __name__ == "__main__":
    asyncio.run(main())
