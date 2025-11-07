#!/usr/bin/env python3
"""
Image Processor - Professional Photo Management with AI Vision

Uses isa-model vision API to:
1. Generate rich image descriptions (for embedding/search)
2. Extract AI-based categories and tags (for professional photo management)

Clean, simple, focused on AI-powered photo understanding.
"""

import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    AI-powered image processor using vision models.

    Capabilities:
    - Rich image description generation (for embedding)
    - AI-based category detection (portrait, landscape, product, etc.)
    - Smart tag generation (objects, scenes, mood, style)
    - Professional photo metadata extraction
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._vision_client = None

        # Vision model settings
        self.vision_model = self.config.get('vision_model', 'gpt-4.1-nano')
        self.vision_provider = self.config.get('vision_provider', 'openai')

        logger.info("✅ AI Image Processor initialized (vision-based)")

    async def _get_vision_client(self):
        """Lazy load AsyncISAModel client using core wrapper"""
        if self._vision_client is None:
            from core.clients.model_client import get_isa_client
            self._vision_client = await get_isa_client()
        return self._vision_client

    async def analyze_image(self, image_input: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze image and return description + metadata for professional photo management.

        Args:
            image_input: Image source - can be:
                - Local file path: "/path/to/image.jpg"
                - URL: "https://example.com/image.jpg"
                - Base64 encoded: "data:image/jpeg;base64,/9j/4AAQ..." or just the base64 string
            options: Analysis options (optional)

        Returns:
            {
                'success': bool,
                'description': str,  # Rich description for embedding
                'ocr_text': str,     # Extracted text if any
                'metadata': {
                    'categories': List[str],  # AI-detected categories
                    'tags': List[str],        # AI-generated tags
                    'mood': str,              # Image mood/tone
                    'style': str,             # Photography style
                    'quality_score': float,   # Image quality assessment
                    'has_people': bool,       # Contains people
                    'has_text': bool,         # Contains text
                    'dominant_colors': List[str],  # Main colors
                    'composition': str        # Composition type
                },
                'processing_time': float
            }
        """
        start_time = time.time()
        logger.info(f"[IMG_ANALYZE] Starting analysis for: {image_input[:100]}...")

        try:
            options = options or {}

            # Detect input type and validate
            input_type = self._detect_image_input_type(image_input)
            logger.info(f"[IMG_ANALYZE] Detected input type: {input_type}")

            if input_type == 'local_file':
                # Validate local file exists
                if not Path(image_input).exists():
                    logger.error(f"[IMG_ANALYZE] File not found: {image_input}")
                    return {
                        'success': False,
                        'error': f'Image file not found: {image_input}',
                        'description': '',
                        'metadata': {}
                    }
                logger.info(f"[IMG_ANALYZE] Local file validated: {image_input}")
            elif input_type == 'url':
                logger.info(f"[IMG_ANALYZE] Processing URL: {image_input}")
            elif input_type == 'base64':
                logger.info(f"[IMG_ANALYZE] Processing base64 encoded image (length: {len(image_input)})")
            else:
                logger.error(f"[IMG_ANALYZE] Unknown input type")
                return {
                    'success': False,
                    'error': f'Invalid image input format',
                    'description': '',
                    'metadata': {}
                }

            logger.info(f"[IMG_ANALYZE] Getting vision client...")
            # Get AsyncISAModel client
            client = await self._get_vision_client()
            logger.info(f"[IMG_ANALYZE] Vision client obtained: {client is not None}")

            # Craft comprehensive prompt for professional photo management
            analysis_prompt = self._build_photo_analysis_prompt()

            logger.info(f"[IMG_ANALYZE] Calling vision API with model={self.vision_model}, provider={self.vision_provider}")
            # Call vision API using AsyncISAModel
            # The vision API supports file paths, URLs, and base64
            vision_result = await client.vision.completions.create(
                image=image_input,
                prompt=analysis_prompt,
                model=self.vision_model,
                provider=self.vision_provider
            )
            logger.info(f"[IMG_ANALYZE] Vision API returned: {vision_result is not None}, has_text={hasattr(vision_result, 'text') if vision_result else False}")

            if not vision_result or not hasattr(vision_result, 'text'):
                logger.error(f"[IMG_ANALYZE] Vision analysis returned empty result")
                return {
                    'success': False,
                    'error': 'Vision analysis returned empty result',
                    'description': '',
                    'metadata': {}
                }

            # Parse vision model response (JSON format)
            parsed_result = self._parse_vision_response(vision_result.text)

            processing_time = time.time() - start_time

            return {
                'success': True,
                'description': parsed_result.get('description', ''),
                'ocr_text': parsed_result.get('ocr_text', ''),
                'metadata': {
                    'categories': parsed_result.get('categories', []),
                    'tags': parsed_result.get('tags', []),
                    'mood': parsed_result.get('mood', ''),
                    'style': parsed_result.get('style', ''),
                    'quality_score': parsed_result.get('quality_score', 0.0),
                    'has_people': parsed_result.get('has_people', False),
                    'has_text': parsed_result.get('has_text', False),
                    'dominant_colors': parsed_result.get('dominant_colors', []),
                    'composition': parsed_result.get('composition', '')
                },
                'processing_time': processing_time,
                'model_used': getattr(vision_result, 'model', self.vision_model)
            }

        except Exception as e:
            import traceback
            logger.error(f"[IMG_ANALYZE] Image analysis failed: {e}")
            logger.error(f"[IMG_ANALYZE] Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'description': '',
                'metadata': {},
                'processing_time': time.time() - start_time
            }

    def _detect_image_input_type(self, image_input: str) -> str:
        """
        Detect the type of image input.

        Args:
            image_input: Image input string

        Returns:
            'url', 'base64', or 'local_file'
        """
        # Check for URL
        if image_input.startswith('http://') or image_input.startswith('https://'):
            return 'url'

        # Check for base64 (data URI or raw base64)
        if image_input.startswith('data:image'):
            return 'base64'

        # Check if it looks like base64 (long string with base64 chars, no path separators)
        if len(image_input) > 100 and '/' not in image_input[:50] and '\\' not in image_input[:50]:
            # Likely base64
            return 'base64'

        # Default to local file path
        return 'local_file'

    def _build_photo_analysis_prompt(self) -> str:
        """
        Build comprehensive prompt for professional photo analysis.

        Returns structured JSON with all metadata needed for photo management.
        """
        return """Analyze this image as a professional photo management AI. Provide a comprehensive analysis in JSON format.

Return ONLY valid JSON (no markdown, no code blocks) with this exact structure:

{
  "description": "A detailed, rich description of the image content, suitable for search and embedding. Be specific about subjects, actions, setting, lighting, and notable visual elements. 2-4 sentences.",
  "ocr_text": "Any visible text extracted from the image (empty string if none)",
  "categories": ["Primary category from: portrait, landscape, cityscape, nature, wildlife, product, food, architecture, abstract, event, sports, travel, art, document, screenshot, other"],
  "tags": ["Relevant tags: objects, subjects, actions, colors, mood, style, location type, time of day, weather, etc. 5-15 tags"],
  "mood": "Overall mood/emotion: cheerful, dramatic, peaceful, energetic, melancholic, professional, casual, festive, mysterious, etc.",
  "style": "Photography style: professional, casual, artistic, documentary, commercial, vintage, modern, minimalist, etc.",
  "quality_score": 0.85,
  "has_people": true,
  "has_text": false,
  "dominant_colors": ["color1", "color2", "color3"],
  "composition": "Composition type: centered, rule-of-thirds, symmetrical, leading-lines, frame-in-frame, golden-ratio, etc."
}

Important:
- Make description rich and searchable
- Choose the single most appropriate category
- Generate 5-15 relevant, specific tags
- Assess quality objectively (0.0-1.0)
- Identify dominant 2-4 colors by name
- Return ONLY the JSON object, nothing else"""

    def _parse_vision_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse vision model JSON response.

        Args:
            response_text: Raw response from vision model

        Returns:
            Parsed metadata dictionary
        """
        try:
            # Clean response (remove markdown code blocks if present)
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                # Remove markdown code blocks
                lines = cleaned.split('\n')
                cleaned = '\n'.join(line for line in lines if not line.startswith('```'))

            # Parse JSON
            parsed = json.loads(cleaned)

            # Validate and normalize
            return {
                'description': parsed.get('description', ''),
                'ocr_text': parsed.get('ocr_text', ''),
                'categories': parsed.get('categories', []),
                'tags': parsed.get('tags', []),
                'mood': parsed.get('mood', ''),
                'style': parsed.get('style', ''),
                'quality_score': float(parsed.get('quality_score', 0.0)),
                'has_people': bool(parsed.get('has_people', False)),
                'has_text': bool(parsed.get('has_text', False)),
                'dominant_colors': parsed.get('dominant_colors', []),
                'composition': parsed.get('composition', '')
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse vision response as JSON: {e}")
            logger.error(f"Response was: {response_text[:500]}")

            # Fallback: use raw response as description
            return {
                'description': response_text[:500],  # Use first 500 chars as description
                'ocr_text': '',
                'categories': ['other'],
                'tags': [],
                'mood': '',
                'style': '',
                'quality_score': 0.5,
                'has_people': False,
                'has_text': False,
                'dominant_colors': [],
                'composition': ''
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing vision response: {e}")
            return {
                'description': '',
                'ocr_text': '',
                'categories': [],
                'tags': [],
                'mood': '',
                'style': '',
                'quality_score': 0.0,
                'has_people': False,
                'has_text': False,
                'dominant_colors': [],
                'composition': ''
            }


# Convenience function for backward compatibility
async def analyze_image(image_input: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function for image analysis

    Args:
        image_input: Image source (URL, base64, or local file path)
        config: Optional configuration
    """
    processor = ImageProcessor(config)
    return await processor.analyze_image(image_input)
