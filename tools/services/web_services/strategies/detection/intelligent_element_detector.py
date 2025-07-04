#!/usr/bin/env python
"""
Intelligent Element Detection System
Multi-strategy element detection combining CSS/XPath + AI Vision + Regex for precise coordinate positioning
Inspired by stacked AI model architecture for maximum accuracy
"""
import json
import asyncio
import tempfile
import os
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from pathlib import Path

from playwright.async_api import Page

from core.logging import get_logger
from core.isa_client import get_isa_client
from .vision_analyzer import VisionAnalyzer
from .selector_analyzer import SelectorAnalyzer

logger = get_logger(__name__)

class DetectionStrategy(Enum):
    """Element detection strategies in order of preference"""
    STACKED_AI = "stacked_ai"          # Highest accuracy - AI vision + coordinate analysis
    TRADITIONAL = "traditional"        # CSS/XPath selectors 
    VISION_ONLY = "vision_only"        # AI vision analysis only
    TEXT_PATTERN = "text_pattern"      # Text pattern matching
    FALLBACK = "fallback"             # Last resort generic patterns

class ElementType(Enum):
    """Types of UI elements that can be detected"""
    INPUT_TEXT = "input_text"
    INPUT_PASSWORD = "input_password"
    INPUT_EMAIL = "input_email"
    INPUT_SEARCH = "input_search"
    BUTTON_SUBMIT = "button_submit"
    BUTTON_GENERIC = "button_generic"
    LINK = "link"
    IMAGE = "image"
    FORM = "form"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"

class DetectionResult:
    """Result of intelligent element detection"""
    
    def __init__(self, element_type: ElementType, strategy: DetectionStrategy, 
                 x: float, y: float, width: float = 0, height: float = 0,
                 selector: str = "", confidence: float = 0.0, 
                 description: str = "", metadata: Dict[str, Any] = None):
        self.element_type = element_type
        self.strategy = strategy
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.selector = selector
        self.confidence = confidence
        self.description = description
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'element_type': self.element_type.value,
            'strategy': self.strategy.value,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'selector': self.selector,
            'confidence': self.confidence,
            'description': self.description,
            'metadata': self.metadata
        }

class IntelligentElementDetector:
    """Multi-strategy intelligent element detection with precise coordinate positioning"""
    
    def __init__(self):
        self.client = get_isa_client()
        self.vision_analyzer = VisionAnalyzer()
        self.selector_analyzer = SelectorAnalyzer()
        self.ui_service = None
        
        # Element type mappings for different scenarios
        self.login_element_map = {
            'username': ElementType.INPUT_TEXT,
            'email': ElementType.INPUT_EMAIL,
            'password': ElementType.INPUT_PASSWORD,
            'submit': ElementType.BUTTON_SUBMIT
        }
        
        # Confidence thresholds for different strategies
        self.confidence_thresholds = {
            DetectionStrategy.STACKED_AI: 0.8,
            DetectionStrategy.TRADITIONAL: 0.7,
            DetectionStrategy.VISION_ONLY: 0.6,
            DetectionStrategy.TEXT_PATTERN: 0.5,
            DetectionStrategy.FALLBACK: 0.3
        }
    
    async def detect_login_elements(self, page: Page, target_elements: List[str] = None) -> Dict[str, DetectionResult]:
        """
        Intelligent login form detection using multi-strategy approach
        
        Args:
            page: Playwright page object
            target_elements: List of element types to detect (default: ['username', 'password', 'submit'])
            
        Returns:
            Dictionary mapping element names to DetectionResult objects
        """
        if target_elements is None:
            target_elements = ['username', 'password', 'submit']
        
        logger.info(f"🧠 Starting intelligent login detection for elements: {target_elements}")
        
        results = {}
        
        # Strategy 1: Stacked AI Model (Highest Accuracy)
        try:
            logger.info("🎯 Attempting Stacked AI detection...")
            stacked_results = await self._detect_using_stacked_ai(page, target_elements, 'login')
            
            for element_name, result in stacked_results.items():
                if result.confidence >= self.confidence_thresholds[DetectionStrategy.STACKED_AI]:
                    results[element_name] = result
                    logger.info(f"   ✅ {element_name}: Stacked AI detection successful (confidence: {result.confidence:.2f})")
            
            # If we found all elements with high confidence, return early
            if len(results) >= len(target_elements):
                logger.info(f"🎉 Stacked AI detected all {len(results)} elements successfully")
                return results
                
        except Exception as e:
            logger.warning(f"⚠️ Stacked AI detection failed: {e}")
        
        # Strategy 2: Traditional Selectors (Fallback)
        missing_elements = [elem for elem in target_elements if elem not in results]
        if missing_elements:
            logger.info(f"🔍 Attempting traditional selector detection for missing elements: {missing_elements}")
            
            try:
                traditional_results = await self._detect_using_traditional(page, missing_elements)
                
                for element_name, result in traditional_results.items():
                    if element_name not in results and result.confidence >= self.confidence_thresholds[DetectionStrategy.TRADITIONAL]:
                        results[element_name] = result
                        logger.info(f"   ✅ {element_name}: Traditional detection successful")
                        
            except Exception as e:
                logger.warning(f"⚠️ Traditional detection failed: {e}")
        
        # Strategy 3: Vision-Only Analysis (Second Fallback)
        missing_elements = [elem for elem in target_elements if elem not in results]
        if missing_elements:
            logger.info(f"👁️ Attempting vision-only detection for missing elements: {missing_elements}")
            
            try:
                vision_results = await self._detect_using_vision_only(page, missing_elements)
                
                for element_name, result in vision_results.items():
                    if element_name not in results and result.confidence >= self.confidence_thresholds[DetectionStrategy.VISION_ONLY]:
                        results[element_name] = result
                        logger.info(f"   ✅ {element_name}: Vision-only detection successful")
                        
            except Exception as e:
                logger.warning(f"⚠️ Vision-only detection failed: {e}")
        
        # Strategy 4: Text Pattern Matching (Last Resort)
        missing_elements = [elem for elem in target_elements if elem not in results]
        if missing_elements:
            logger.info(f"📝 Attempting text pattern detection for missing elements: {missing_elements}")
            
            try:
                text_results = await self._detect_using_text_patterns(page, missing_elements)
                
                for element_name, result in text_results.items():
                    if element_name not in results:
                        results[element_name] = result
                        logger.info(f"   ✅ {element_name}: Text pattern detection successful")
                        
            except Exception as e:
                logger.warning(f"⚠️ Text pattern detection failed: {e}")
        
        logger.info(f"🎯 Intelligent detection completed: {len(results)}/{len(target_elements)} elements found")
        
        return results
    
    async def detect_search_elements(self, page: Page, target_elements: List[str] = None) -> Dict[str, DetectionResult]:
        """Intelligent search form detection"""
        if target_elements is None:
            target_elements = ['search_input', 'search_button']
        
        logger.info(f"🔍 Starting intelligent search detection for elements: {target_elements}")
        
        results = {}
        
        # Try stacked AI first
        try:
            stacked_results = await self._detect_using_stacked_ai(page, target_elements, 'search')
            for element_name, result in stacked_results.items():
                if result.confidence >= self.confidence_thresholds[DetectionStrategy.STACKED_AI]:
                    results[element_name] = result
                    
            if len(results) >= len(target_elements):
                return results
        except Exception as e:
            logger.warning(f"Stacked AI search detection failed: {e}")
        
        # Fallback to traditional methods
        missing_elements = [elem for elem in target_elements if elem not in results]
        if missing_elements:
            traditional_results = await self._detect_search_traditional(page, missing_elements)
            results.update(traditional_results)
        
        return results
    
    async def detect_generic_elements(self, page: Page, element_descriptions: List[str]) -> List[DetectionResult]:
        """
        Detect generic elements based on natural language descriptions
        
        Args:
            page: Playwright page object
            element_descriptions: List of natural language descriptions (e.g., "red submit button", "email input field")
            
        Returns:
            List of DetectionResult objects
        """
        logger.info(f"🎯 Starting generic element detection for: {element_descriptions}")
        
        results = []
        
        # Use stacked AI with natural language descriptions
        try:
            for description in element_descriptions:
                result = await self._detect_generic_element_ai(page, description)
                if result:
                    results.append(result)
                    logger.info(f"   ✅ Found element: {description}")
                else:
                    logger.warning(f"   ❌ Could not find element: {description}")
        except Exception as e:
            logger.error(f"Generic element detection failed: {e}")
        
        return results
    
    async def _detect_using_stacked_ai(self, page: Page, target_elements: List[str], context: str) -> Dict[str, DetectionResult]:
        """Use stacked AI model for high-precision element detection"""
        logger.info(f"🤖 Initializing stacked AI detection for {context} context...")
        
        # Take screenshot for analysis
        screenshot = await page.screenshot(full_page=False)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_file.write(screenshot)
            screenshot_path = tmp_file.name
        
        try:
            # Perform stacked AI analysis using ISA client
            result = await self.client.invoke(
                input_data={
                    "image_path": screenshot_path,
                    "target_elements": target_elements,
                    "context": context
                },
                task="vision",
                service_type="vision"
            )
            
            if result.get('success'):
                analysis_result = result.get('result', {})
            else:
                analysis_result = {"success": False, "error": result.get('error')}
            
            if not analysis_result.get("success"):
                logger.error(f"❌ Stacked AI analysis failed: {analysis_result}")
                return {}
            
            # Convert stacked AI results to DetectionResult objects
            return await self._convert_stacked_ai_results(analysis_result, target_elements, context)
            
        finally:
            # Clean up temporary file
            if os.path.exists(screenshot_path):
                os.unlink(screenshot_path)
    
    async def _detect_using_traditional(self, page: Page, target_elements: List[str]) -> Dict[str, DetectionResult]:
        """Use traditional CSS/XPath selectors for element detection"""
        logger.info(f"🔍 Using traditional selector detection...")
        
        results = {}
        
        # Use the existing selector analyzer
        traditional_results = await self.selector_analyzer.identify_login_elements(page)
        
        for element_name, element_data in traditional_results.items():
            if element_name in target_elements:
                element_type = self.login_element_map.get(element_name, ElementType.BUTTON_GENERIC)
                
                result = DetectionResult(
                    element_type=element_type,
                    strategy=DetectionStrategy.TRADITIONAL,
                    x=element_data.get('x', 0),
                    y=element_data.get('y', 0),
                    width=element_data.get('width', 0),
                    height=element_data.get('height', 0),
                    selector=element_data.get('selector', ''),
                    confidence=0.75,  # Traditional methods have good reliability
                    description=f"Traditional {element_name} detection",
                    metadata=element_data
                )
                
                results[element_name] = result
        
        return results
    
    async def _detect_using_vision_only(self, page: Page, target_elements: List[str]) -> Dict[str, DetectionResult]:
        """Use vision-only analysis for element detection"""
        logger.info(f"👁️ Using vision-only detection...")
        
        results = {}
        
        # Take screenshot
        screenshot = await page.screenshot(full_page=False)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_file.write(screenshot)
            screenshot_path = tmp_file.name
        
        try:
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze this webpage screenshot and identify the following UI elements: {', '.join(target_elements)}
            
            For each element found, provide:
            1. Element type and description
            2. Approximate center coordinates (x, y)
            3. Confidence level (0.0-1.0)
            
            Return results in JSON format:
            {{
                "elements": [
                    {{
                        "name": "element_name",
                        "type": "input/button/etc",
                        "x": 123,
                        "y": 456,
                        "confidence": 0.85,
                        "description": "brief description"
                    }}
                ]
            }}
            """
            
            # Analyze with ISA vision service
            result = await self.client.invoke(
                input_data={
                    "image_path": screenshot_path,
                    "prompt": analysis_prompt
                },
                task="vision",
                service_type="vision"
            )
            
            if result.get('success'):
                analysis_result = result.get('result', {})
            else:
                analysis_result = {}
            
            # Parse results
            analysis_text = analysis_result.get('text', '')
            
            try:
                import re
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    vision_data = json.loads(json_match.group())
                    
                    for element_info in vision_data.get('elements', []):
                        element_name = element_info.get('name')
                        if element_name in target_elements:
                            element_type = self.login_element_map.get(element_name, ElementType.BUTTON_GENERIC)
                            
                            result = DetectionResult(
                                element_type=element_type,
                                strategy=DetectionStrategy.VISION_ONLY,
                                x=element_info.get('x', 0),
                                y=element_info.get('y', 0),
                                confidence=element_info.get('confidence', 0.6),
                                description=element_info.get('description', ''),
                                metadata=element_info
                            )
                            
                            results[element_name] = result
            except Exception as parse_error:
                logger.warning(f"Failed to parse vision analysis: {parse_error}")
            
        finally:
            if os.path.exists(screenshot_path):
                os.unlink(screenshot_path)
        
        return results
    
    async def _detect_using_text_patterns(self, page: Page, target_elements: List[str]) -> Dict[str, DetectionResult]:
        """Use text pattern matching for element detection"""
        logger.info(f"📝 Using text pattern detection...")
        
        results = {}
        
        # Define text patterns for different element types
        text_patterns = {
            'username': ['username', 'user name', 'email', 'login', '用户名', '账号'],
            'password': ['password', 'pass', 'pwd', '密码'],
            'submit': ['login', 'sign in', 'submit', 'continue', '登录', '提交'],
            'search_input': ['search', 'find', 'query', '搜索'],
            'search_button': ['search', 'go', 'find', '搜索']
        }
        
        for element_name in target_elements:
            patterns = text_patterns.get(element_name, [])
            
            for pattern in patterns:
                try:
                    # Look for elements containing the pattern text
                    if element_name == 'submit' or 'button' in element_name:
                        # Search for buttons with text
                        element = page.locator(f'button:has-text("{pattern}"), input[value*="{pattern}" i]').first
                    else:
                        # Search for inputs with placeholder or label
                        element = page.locator(f'input[placeholder*="{pattern}" i], input[aria-label*="{pattern}" i]').first
                    
                    if await element.count() > 0:
                        bounding_box = await element.bounding_box()
                        if bounding_box:
                            element_type = self.login_element_map.get(element_name, ElementType.BUTTON_GENERIC)
                            
                            result = DetectionResult(
                                element_type=element_type,
                                strategy=DetectionStrategy.TEXT_PATTERN,
                                x=bounding_box['x'] + bounding_box['width'] / 2,
                                y=bounding_box['y'] + bounding_box['height'] / 2,
                                width=bounding_box['width'],
                                height=bounding_box['height'],
                                confidence=0.5,
                                description=f"Text pattern '{pattern}' match",
                                metadata={'pattern': pattern}
                            )
                            
                            results[element_name] = result
                            break
                            
                except Exception as e:
                    logger.debug(f"Text pattern '{pattern}' failed: {e}")
                    continue
        
        return results
    
    async def _convert_stacked_ai_results(self, analysis_result: Dict[str, Any], 
                                         target_elements: List[str], context: str) -> Dict[str, DetectionResult]:
        """Convert stacked AI analysis results to DetectionResult objects"""
        logger.info("🔄 Converting stacked AI results to detection objects...")
        
        results = {}
        
        final_output = analysis_result.get("final_output", {})
        action_plan = final_output.get("action_plan", {})
        ui_elements = final_output.get("ui_elements", {})
        automation_ready = final_output.get("automation_ready", {})
        
        confidence_base = automation_ready.get("confidence", 0.8)
        
        # Extract action steps with coordinates
        steps = action_plan.get("action_plan", [])
        
        for step in steps:
            action = step.get("action", "").lower()
            coords = step.get("actual_coordinates", step.get("target_coordinates", [0, 0]))
            description = step.get("description", "")
            
            # Map actions to element names
            element_name = None
            element_type = ElementType.BUTTON_GENERIC
            
            if action in ['type', 'fill']:
                if any(word in description.lower() for word in ['username', 'email', 'user']):
                    element_name = 'username'
                    element_type = ElementType.INPUT_TEXT
                elif any(word in description.lower() for word in ['password', 'pass']):
                    element_name = 'password'
                    element_type = ElementType.INPUT_PASSWORD
                elif any(word in description.lower() for word in ['search', 'query']):
                    element_name = 'search_input'
                    element_type = ElementType.INPUT_SEARCH
            elif action == 'click':
                if any(word in description.lower() for word in ['submit', 'login', 'sign']):
                    element_name = 'submit'
                    element_type = ElementType.BUTTON_SUBMIT
                elif any(word in description.lower() for word in ['search', 'find']):
                    element_name = 'search_button'
                    element_type = ElementType.BUTTON_GENERIC
            
            if element_name and element_name in target_elements and len(coords) >= 2:
                result = DetectionResult(
                    element_type=element_type,
                    strategy=DetectionStrategy.STACKED_AI,
                    x=int(coords[0]),
                    y=int(coords[1]),
                    confidence=confidence_base,
                    description=description,
                    metadata={
                        'action': action,
                        'step_index': len(results),
                        'ai_analysis': step
                    }
                )
                
                results[element_name] = result
                logger.info(f"   ✅ {element_name}: ({coords[0]}, {coords[1]}) - {description}")
        
        return results
    
    async def _detect_search_traditional(self, page: Page, target_elements: List[str]) -> Dict[str, DetectionResult]:
        """Traditional search element detection"""
        results = {}
        
        if 'search_input' in target_elements:
            # Search input selectors
            search_selectors = [
                'input[type="search"]',
                'input[name="search"]',
                'input[name="q"]',
                'input[placeholder*="search" i]'
            ]
            
            for selector in search_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        bounding_box = await element.bounding_box()
                        if bounding_box:
                            result = DetectionResult(
                                element_type=ElementType.INPUT_SEARCH,
                                strategy=DetectionStrategy.TRADITIONAL,
                                x=bounding_box['x'] + bounding_box['width'] / 2,
                                y=bounding_box['y'] + bounding_box['height'] / 2,
                                width=bounding_box['width'],
                                height=bounding_box['height'],
                                selector=selector,
                                confidence=0.75
                            )
                            results['search_input'] = result
                            break
                except:
                    continue
        
        if 'search_button' in target_elements:
            # Search button selectors
            button_selectors = [
                'button[type="submit"]',
                'button:has-text("Search")',
                'input[type="submit"]'
            ]
            
            for selector in button_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        bounding_box = await element.bounding_box()
                        if bounding_box:
                            result = DetectionResult(
                                element_type=ElementType.BUTTON_SUBMIT,
                                strategy=DetectionStrategy.TRADITIONAL,
                                x=bounding_box['x'] + bounding_box['width'] / 2,
                                y=bounding_box['y'] + bounding_box['height'] / 2,
                                width=bounding_box['width'],
                                height=bounding_box['height'],
                                selector=selector,
                                confidence=0.75
                            )
                            results['search_button'] = result
                            break
                except:
                    continue
        
        return results
    
    async def _detect_generic_element_ai(self, page: Page, description: str) -> Optional[DetectionResult]:
        """Detect a generic element using AI with natural language description"""
        try:
            # Take screenshot
            screenshot = await page.screenshot(full_page=False)
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(screenshot)
                screenshot_path = tmp_file.name
            
            try:
                analysis_prompt = f"""
                Find the UI element described as: "{description}"
                
                Analyze the screenshot and locate this element. Return the center coordinates and confidence level.
                
                Response format:
                {{
                    "found": true/false,
                    "x": center_x_coordinate,
                    "y": center_y_coordinate,
                    "confidence": 0.0-1.0,
                    "element_type": "button/input/link/etc",
                    "description": "what you found"
                }}
                """
                
                # Use ISA vision service
                result = await self.client.invoke(
                    input_data={
                        "image_path": screenshot_path,
                        "prompt": analysis_prompt
                    },
                    task="vision",
                    service_type="vision"
                )
                
                if result.get('success'):
                    analysis_result = result.get('result', {})
                else:
                    analysis_result = {}
                
                # Parse result
                analysis_text = analysis_result.get('text', '')
                
                import re
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    
                    if data.get('found') and data.get('confidence', 0) > 0.5:
                        # Map element type string to enum
                        element_type_str = data.get('element_type', 'generic').lower()
                        element_type = ElementType.BUTTON_GENERIC  # default
                        
                        if 'input' in element_type_str:
                            element_type = ElementType.INPUT_TEXT
                        elif 'button' in element_type_str:
                            element_type = ElementType.BUTTON_GENERIC
                        elif 'link' in element_type_str:
                            element_type = ElementType.LINK
                        
                        return DetectionResult(
                            element_type=element_type,
                            strategy=DetectionStrategy.VISION_ONLY,
                            x=data.get('x', 0),
                            y=data.get('y', 0),
                            confidence=data.get('confidence', 0.6),
                            description=data.get('description', description),
                            metadata={'original_description': description}
                        )
                
                return None
                
            finally:
                if os.path.exists(screenshot_path):
                    os.unlink(screenshot_path)
                    
        except Exception as e:
            logger.error(f"Generic element AI detection failed: {e}")
            return None
    
    async def close(self):
        """Clean up resources"""
        if self.ui_service:
            await self.ui_service.close()
        await self.vision_analyzer.close() if hasattr(self.vision_analyzer, 'close') else None