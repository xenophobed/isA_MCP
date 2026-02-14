#!/usr/bin/env python
"""
Image Analyzer - Generic VLM atomic function

Provides a pure atomic VLM wrapper that takes any image + any prompt
and returns whatever output the prompt requests. Completely generic
and reusable for any vision language model task.
"""

import asyncio
import tempfile
import os
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ImageAnalysisResult:
    """Generic image analysis result"""

    response: str
    model_used: str
    processing_time: float = 0.0
    success: bool = True
    error: Optional[str] = None


class ImageAnalyzer:
    """Generic VLM atomic function - takes image + prompt, returns response"""

    def __init__(self):
        self._client = None
        logger.debug("ImageAnalyzer initialized")

    async def _get_client(self):
        """Lazy load ISA client following text_generator pattern"""
        if self._client is None:
            from core.clients.model_client import get_isa_client

            self._client = await get_isa_client()
        return self._client

    async def analyze(
        self,
        image: Union[str, bytes],
        prompt: str,
        model: Optional[str] = "gpt-4.1-nano",
        provider: str = "openai",
        response_format: str = "text",
    ) -> ImageAnalysisResult:
        """
        Generic VLM analysis function - completely atomic

        Args:
            image: Image to analyze (file path or bytes)
            prompt: Any prompt requesting any kind of analysis
            model: Optional model specification (defaults to provider default)
            provider: Provider to use ("openai", "isa", etc.)
            response_format: Expected response format hint

        Returns:
            ImageAnalysisResult with raw model response
        """
        try:
            start_time = asyncio.get_event_loop().time()

            # Handle image input - convert to path if needed
            image_path = await self._prepare_image_input(image)

            try:
                # Call ISA client using new vision API
                client = await self._get_client()

                vision_response = await client.vision.completions.create(
                    image=image_path, prompt=prompt, model=model, provider=provider
                )

                processing_time = asyncio.get_event_loop().time() - start_time

                # Extract description from response (using ISA Model .text attribute)
                description = vision_response.text

                result = {"success": True, "result": description}

                if not description:
                    logger.error(f"❌ VLM analysis returned empty result")
                    return ImageAnalysisResult(
                        response="",
                        model_used=model or "unknown",
                        processing_time=processing_time,
                        success=False,
                        error=error_msg,
                    )

                # Extract response text
                response_text = ""
                model_used = model or "unknown"

                if "result" in result:
                    result_data = result["result"]
                    if isinstance(result_data, dict):
                        response_text = result_data.get("text", str(result_data))
                        model_used = result_data.get("model", model or "unknown")
                    else:
                        response_text = str(result_data)

                logger.info(
                    f"✅ VLM analysis completed in {processing_time:.2f}s with {model_used}"
                )

                return ImageAnalysisResult(
                    response=response_text,
                    model_used=model_used,
                    processing_time=processing_time,
                    success=True,
                )

            finally:
                # Clean up temporary image file if created
                if isinstance(image, bytes) and os.path.exists(image_path):
                    try:
                        os.unlink(image_path)
                    except OSError:
                        pass

        except Exception as e:
            processing_time = (
                asyncio.get_event_loop().time() - start_time if "start_time" in locals() else 0
            )
            logger.error(f"❌ Image analysis failed: {e}")
            return ImageAnalysisResult(
                response="",
                model_used=model or "unknown",
                processing_time=processing_time,
                success=False,
                error=str(e),
            )

    async def _prepare_image_input(self, image: Union[str, bytes]) -> str:
        """Prepare image input - convert bytes to temp file if needed"""
        if isinstance(image, str):
            # Already a file path
            return image
        elif isinstance(image, bytes):
            # Create temporary file for bytes
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(image)
                return tmp.name
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")


# Global instance for easy import and usage
image_analyzer = ImageAnalyzer()


# Convenience functions
async def analyze(image: Union[str, bytes], prompt: str, **kwargs) -> ImageAnalysisResult:
    """Convenience function for generic image analysis"""
    return await image_analyzer.analyze(image, prompt, **kwargs)
