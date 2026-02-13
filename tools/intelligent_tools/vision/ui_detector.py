#!/usr/bin/env python
"""
UI Detector - UI element detection with coordinates

Provides specialized functionality for detecting UI elements in screenshots
with precise coordinates, element annotation, and requirement matching.
Atomic function for Step 3 of web automation workflow.

Includes vision caching to optimize OmniParser usage - if we've visited a page
before, we reuse cached UI elements and only run VLM matching for requirements.
"""

import asyncio
import tempfile
import os
import json
import hashlib
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from .helper.vision_cache_manager import get_vision_cache_manager

logger = get_logger(__name__)


class UIElementType(Enum):
    """Types of UI elements"""

    BUTTON = "button"
    INPUT = "input"
    LINK = "link"
    IMAGE = "image"
    TEXT = "text"
    MENU = "menu"
    FORM = "form"
    TABLE = "table"
    DIALOG = "dialog"
    SEARCH_BOX = "search_box"
    NAVIGATION = "navigation"
    CONTENT = "content"
    UNKNOWN = "unknown"


@dataclass
class UIElement:
    """Detected UI element with coordinates"""

    element_id: Optional[str]
    element_type: UIElementType
    description: str
    x: int
    y: int
    width: int = 0
    height: int = 0
    text_content: Optional[str] = None
    clickable: bool = False
    interactive: bool = False
    confidence: float = 0.0
    attributes: Dict[str, Any] = None


@dataclass
class UIDetectionResult:
    """UI detection result with coordinates"""

    ui_elements: List[Dict[str, Any]]  # Raw OmniParser elements
    annotated_image_path: Optional[str]
    element_mappings: Dict[str, Dict[str, Any]]  # Requirement -> coordinate mappings
    success: bool = True
    error: Optional[str] = None
    processing_time: float = 0.0


class UIDetector:
    """UI element detection with coordinates - atomic function for Step 3"""

    def __init__(self):
        self._client = None
        self._cache_manager = get_vision_cache_manager()
        logger.debug("UIDetector initialized with vision caching")

    async def _get_client(self):
        """Lazy load ISA client following pattern"""
        if self._client is None:
            from core.clients.model_client import get_isa_client

            self._client = await get_isa_client()
        return self._client

    async def detect_ui_with_coordinates(
        self,
        screenshot: Union[str, bytes],
        requirements: List[Dict[str, str]],
        url: Optional[str] = None,
        force_refresh: bool = False,
    ) -> UIDetectionResult:
        """
        Main atomic function: Detect UI elements with coordinates

        Args:
            screenshot: Screenshot to analyze
            requirements: List of required UI elements from Step 2
                         [{"element_name": "search_input", "element_purpose": "...", ...}]
            url: Optional URL for cache optimization (avoids redundant OmniParser calls)
            force_refresh: Force OmniParser detection even if cached results exist

        Returns:
            UIDetectionResult with UI elements and coordinate mappings
        """
        try:
            start_time = asyncio.get_event_loop().time()

            # Prepare image
            image_path = await self._prepare_image_input(screenshot)

            try:
                # Generate cache context for the image content
                image_hash = await self._get_image_hash(image_path)
                cache_context = {"image_hash": image_hash}

                # Step 3.1: Get UI elements (with caching optimization)
                ui_elements = None
                cache_hit = False

                if not force_refresh and url:
                    # Try to get cached UI elements first
                    logger.info("🎯 Step 3.1a: Checking for cached UI elements...")
                    cached_elements = await self._cache_manager.get_cached_detection(
                        url=url,
                        detection_type="ui_elements",
                        page_content=image_hash,
                        additional_context=cache_context,
                    )

                    if cached_elements:
                        ui_elements = cached_elements.get("ui_elements", [])
                        cache_hit = True
                        logger.info(f"✅ Using cached UI elements ({len(ui_elements)} elements)")

                if not ui_elements:
                    # No cache hit - use OmniParser
                    logger.info("🎯 Step 3.1b: Getting UI elements with OmniParser...")
                    ui_elements = await self._get_ui_elements_with_omniparser(image_path)

                    # Cache the result if we have a URL and good elements
                    if url and ui_elements:
                        await self._cache_manager.save_detection_result(
                            url=url,
                            detection_type="ui_elements",
                            elements={"ui_elements": ui_elements},
                            confidence=0.9,  # High confidence for OmniParser results
                            page_content=image_hash,
                            additional_context=cache_context,
                        )
                        logger.info(f"💾 Cached {len(ui_elements)} UI elements for future use")

                if not ui_elements:
                    return UIDetectionResult(
                        ui_elements=[],
                        annotated_image_path=None,
                        element_mappings={},
                        success=False,
                        error="No UI elements detected by OmniParser",
                    )

                # Step 3.2: Create annotated image (always needed for VLM matching)
                logger.info("🎯 Step 3.2: Creating annotated image...")
                annotated_image_path = await self._create_annotated_image(image_path, ui_elements)

                # Step 3.3: Match requirements with annotated image (VLM always runs)
                logger.info("🎯 Step 3.3: Matching requirements with UI elements...")
                element_mappings = await self._match_requirements_with_elements(
                    annotated_image_path, ui_elements, requirements
                )

                processing_time = asyncio.get_event_loop().time() - start_time

                cache_status = "🟢 CACHED" if cache_hit else "🔵 FRESH"
                logger.info(f"✅ UI detection completed in {processing_time:.2f}s [{cache_status}]")
                return UIDetectionResult(
                    ui_elements=ui_elements,
                    annotated_image_path=annotated_image_path,
                    element_mappings=element_mappings,
                    success=True,
                    processing_time=processing_time,
                )

            finally:
                # Clean up temp image if created from bytes
                if isinstance(screenshot, bytes) and os.path.exists(image_path):
                    try:
                        os.unlink(image_path)
                    except:
                        pass

        except Exception as e:
            processing_time = (
                asyncio.get_event_loop().time() - start_time if "start_time" in locals() else 0
            )
            logger.error(f"❌ UI detection failed: {e}")
            return UIDetectionResult(
                ui_elements=[],
                annotated_image_path=None,
                element_mappings={},
                success=False,
                error=str(e),
                processing_time=processing_time,
            )

    async def _prepare_image_input(self, image: Union[str, bytes]) -> str:
        """Prepare image input - convert bytes to temp file if needed"""
        if isinstance(image, str):
            return image
        elif isinstance(image, bytes):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(image)
                return tmp.name
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    async def _get_image_hash(self, image_path: str) -> str:
        """Generate hash of image content for cache validation"""
        try:
            with open(image_path, "rb") as f:
                # Read first 64KB for hash (sufficient for most images)
                content = f.read(65536)
                return hashlib.md5(content).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"⚠️ Failed to hash image: {e}")
            return "unknown"

    async def _get_ui_elements_with_omniparser(self, image_path: str) -> List[Dict[str, Any]]:
        """Get UI elements using OmniParser"""
        try:
            client = await self._get_client()

            # Use vision API for UI detection
            vision_response = await client.vision.completions.create(
                image=image_path,
                prompt="Detect and describe all UI elements",
                model="isa-omniparser-ui-detection",
                provider="isa",
            )

            # Parse the response - for ISA provider, it may return structured data
            content = vision_response.choices[0].message.content

            # Try to parse as JSON if it's structured
            try:
                import json

                ui_data = json.loads(content) if isinstance(content, str) else content
                ui_elements = ui_data.get("ui_elements", []) if isinstance(ui_data, dict) else []
            except:
                logger.warning("Could not parse UI elements as JSON, returning empty list")
                ui_elements = []
            logger.info(f"📋 OmniParser found {len(ui_elements)} UI elements")

            return ui_elements

        except Exception as e:
            logger.error(f"❌ OmniParser call failed: {e}")
            return []

    async def _create_annotated_image(self, image_path: str, ui_elements: List[Dict]) -> str:
        """Create annotated image with numbered bounding boxes"""
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Open image
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)

            # Try to load font
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
            except:
                font = ImageFont.load_default()

            # Draw numbered boxes
            for i, elem in enumerate(ui_elements):
                bbox = elem.get("bbox", [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox

                    # Draw red bounding box
                    draw.rectangle([x1, y1, x2, y2], outline="red", width=3)

                    # Draw number label
                    label = str(i)
                    label_bbox = draw.textbbox((0, 0), label, font=font)
                    label_width = label_bbox[2] - label_bbox[0]
                    label_height = label_bbox[3] - label_bbox[1]

                    label_x = x1
                    label_y = max(0, y1 - label_height - 5)

                    draw.rectangle(
                        [label_x, label_y, label_x + label_width + 8, label_y + label_height + 4],
                        fill="red",
                        outline="red",
                    )
                    draw.text((label_x + 4, label_y + 2), label, fill="white", font=font)

            # Save annotated image
            annotated_path = image_path.replace(".png", "_annotated.png")
            image.save(annotated_path)
            logger.info(f"📸 Annotated image saved: {annotated_path}")

            return annotated_path

        except Exception as e:
            logger.error(f"❌ Failed to create annotated image: {e}")
            return image_path  # Return original if failed

    async def _match_requirements_with_elements(
        self, annotated_image_path: str, ui_elements: List[Dict], requirements: List[Dict[str, str]]
    ) -> Dict[str, Dict[str, Any]]:
        """Match requirements with UI elements using VLM on annotated image"""
        try:
            # Prepare element summary
            element_summary = ""
            for i, elem in enumerate(ui_elements):
                center = elem.get("center", [0, 0])
                content = elem.get("content", "")
                elem_type = elem.get("type", "")
                element_summary += f"Element {i}: {elem_type} at {center} - '{content}'\\n"

            # Prepare requirements text
            requirements_text = ""
            for req in requirements:
                requirements_text += (
                    f"NEED: {req.get('element_name')} - {req.get('element_purpose')}\\n"
                )
                requirements_text += f"  Visual: {req.get('visual_description', '')}\\n"
                requirements_text += f"  Action: {req.get('interaction_type', '')}\\n\\n"

            # Create improved matching prompt
            prompt = f"""TASK: Match UI requirements with numbered elements in this annotated screenshot.

REQUIREMENTS:
{requirements_text}

ELEMENTS (with numbers in red boxes):
{element_summary}

Return ONLY this JSON format with actual element numbers:

{{"""

            # Build simpler JSON structure
            for i, req in enumerate(requirements):
                element_name = req.get("element_name", f"element_{i}")
                prompt += f'\n  "{element_name}": {{"element_index": 0, "confidence": 0.9}}'
                if i < len(requirements) - 1:
                    prompt += ","

            prompt += "\n}\n\nReplace 0 with actual element numbers. JSON only!"

            # Call VLM with annotated image using new vision API
            client = await self._get_client()

            vision_response = await client.vision.completions.create(
                image=annotated_image_path, prompt=prompt, model="gpt-4.1", provider="openai"
            )

            result = {"success": True, "result": vision_response.choices[0].message.content}

            if not result.get("success"):
                logger.error(f"❌ VLM matching failed: {result}")
                return {}

            # Parse response
            response_text = ""
            if "result" in result:
                result_data = result["result"]
                if isinstance(result_data, dict):
                    response_text = result_data.get("text", str(result_data))
                else:
                    response_text = str(result_data)

            # Extract JSON with multiple strategies
            import re

            # Strategy 1: Look for JSON block with proper braces
            json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response_text, re.DOTALL)

            if not json_match:
                # Strategy 2: Look for any content between braces
                json_match = re.search(r"\{.*?\}", response_text, re.DOTALL)

            if not json_match:
                # Strategy 3: Try to find JSON-like content
                json_match = re.search(r"(\{[\s\S]*\})", response_text)

            if not json_match:
                logger.warning("⚠️ No JSON found in VLM matching response")
                logger.warning(f"VLM Response: {response_text[:200]}...")
                return {}

            json_text = json_match.group()
            logger.info(f"📋 Extracted JSON: {json_text[:100]}...")

            try:
                matches = json.loads(json_text)

                # Convert to coordinate mappings
                element_mappings = {}
                for req in requirements:
                    element_name = req.get("element_name", "")
                    interaction_type = req.get("interaction_type", "click")

                    if element_name in matches:
                        match_info = matches[element_name]
                        elem_idx = match_info.get("element_index")

                        if 0 <= elem_idx < len(ui_elements):
                            element = ui_elements[elem_idx]
                            center = element.get("center", [0, 0])

                            # Determine action type
                            action = "click"
                            if (
                                "type" in interaction_type.lower()
                                or "input" in element_name.lower()
                            ):
                                action = "type"
                            elif (
                                "click" in interaction_type.lower()
                                or "button" in element_name.lower()
                            ):
                                action = "click"

                            element_mappings[element_name] = {
                                "x": center[0],
                                "y": center[1],
                                "action": action,
                                "confidence": match_info.get("confidence", 0.8),
                                "reasoning": match_info.get("reasoning", ""),
                                "element": element,
                            }

                            logger.info(
                                f"✅ Matched {element_name}: Element {elem_idx} at ({center[0]}, {center[1]})"
                            )

                return element_mappings

            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse VLM matching JSON: {e}")
                logger.warning(f"Raw JSON text: {json_text}")
                logger.warning(f"Full VLM response: {response_text}")
                return {}

        except Exception as e:
            logger.error(f"❌ Requirements matching failed: {e}")
            return {}

    # Convenience method for simpler element annotation
    async def annotate_ui_elements(
        self, screenshot: Union[str, bytes], save_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Convenience method: Create annotated image with all UI elements

        Args:
            screenshot: Screenshot to annotate
            save_path: Optional path to save annotated image

        Returns:
            Path to annotated image or None if failed
        """
        try:
            image_path = await self._prepare_image_input(screenshot)

            try:
                # Get UI elements
                ui_elements = await self._get_ui_elements_with_omniparser(image_path)

                if not ui_elements:
                    return None

                # Create annotated image
                annotated_path = await self._create_annotated_image(image_path, ui_elements)

                # Copy to specified path if provided
                if save_path and annotated_path:
                    import shutil

                    shutil.copy2(annotated_path, save_path)
                    return save_path

                return annotated_path

            finally:
                # Clean up temp image if created from bytes
                if isinstance(screenshot, bytes) and os.path.exists(image_path):
                    try:
                        os.unlink(image_path)
                    except:
                        pass

        except Exception as e:
            logger.error(f"❌ UI annotation failed: {e}")
            return None


# Global instance for easy import and usage
ui_detector = UIDetector()


# Convenience functions
async def detect_ui_with_coordinates(
    screenshot: Union[str, bytes],
    requirements: List[Dict[str, str]],
    url: Optional[str] = None,
    force_refresh: bool = False,
) -> UIDetectionResult:
    """Convenience function for UI detection with coordinates"""
    return await ui_detector.detect_ui_with_coordinates(
        screenshot, requirements, url, force_refresh
    )


async def annotate_ui_elements(
    screenshot: Union[str, bytes], save_path: Optional[str] = None
) -> Optional[str]:
    """Convenience function for UI element annotation"""
    return await ui_detector.annotate_ui_elements(screenshot, save_path)
