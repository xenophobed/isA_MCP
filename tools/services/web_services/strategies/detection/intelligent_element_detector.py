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
    
    async def detect_link_elements(self, page: Page, target_links: List[str] = None) -> Dict[str, DetectionResult]:
        """
        Detect clickable link elements on the page
        
        Args:
            page: Playwright page object
            target_links: List of link descriptions or text content to find
            
        Returns:
            Dictionary mapping link identifiers to DetectionResult objects
        """
        logger.info(f"🔗 Starting intelligent link detection for: {target_links or 'all links'}")
        
        results = {}
        
        # Default target links if none provided
        if not target_links:
            target_links = ['product_links', 'navigation_links', 'action_links']
        
        # Try stacked AI first
        try:
            stacked_results = await self._detect_using_stacked_ai(page, target_links, 'links')
            for link_name, result in stacked_results.items():
                if result.confidence >= self.confidence_thresholds[DetectionStrategy.STACKED_AI]:
                    results[link_name] = result
                    
            if len(results) >= len(target_links):
                return results
        except Exception as e:
            logger.warning(f"Stacked AI link detection failed: {e}")
        
        # Fallback to traditional link detection
        missing_links = [link for link in target_links if link not in results]
        if missing_links:
            traditional_results = await self._detect_links_traditional(page, missing_links)
            results.update(traditional_results)
        
        return results
    
    async def _detect_links_traditional(self, page: Page, target_links: List[str]) -> Dict[str, DetectionResult]:
        """Use traditional selectors to detect links"""
        logger.info(f"🔍 Using traditional link detection for: {target_links}")
        
        results = {}
        
        # Common link selectors
        link_selectors = [
            'a[href]',  # All links with href
            'a[href^="http"]',  # External links
            'a[href^="/"]',  # Internal links
            'button[onclick*="location"]',  # Button links
            '[role="link"]',  # ARIA links
            '.link',  # Common link classes
            '.btn-link',
            '.nav-link'
        ]
        
        for link_name in target_links:
            try:
                # Try to find links based on text content or common patterns
                if 'product' in link_name.lower():
                    # Product-specific link patterns
                    selectors = [
                        'a[href*="product"]',
                        'a[href*="item"]', 
                        'a[href*="/p/"]',
                        '.product-link',
                        '[data-testid*="product"]'
                    ]
                elif 'navigation' in link_name.lower() or 'nav' in link_name.lower():
                    # Navigation link patterns
                    selectors = [
                        'nav a',
                        '.nav a',
                        '.navbar a',
                        '.menu a',
                        '[role="navigation"] a'
                    ]
                elif 'action' in link_name.lower():
                    # Action link patterns
                    selectors = [
                        'a.btn',
                        'a.button',
                        'a[role="button"]',
                        '.call-to-action a',
                        '.cta a'
                    ]
                else:
                    # Generic link detection
                    selectors = link_selectors
                
                # Find the first matching link
                for selector in selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.count() > 0:
                            bounding_box = await element.bounding_box()
                            if bounding_box:
                                # Get link text and href
                                text_content = await element.text_content() or ""
                                href = await element.get_attribute('href') or ""
                                
                                result = DetectionResult(
                                    element_type=ElementType.LINK,
                                    strategy=DetectionStrategy.TRADITIONAL,
                                    x=bounding_box['x'] + bounding_box['width'] / 2,
                                    y=bounding_box['y'] + bounding_box['height'] / 2,
                                    width=bounding_box['width'],
                                    height=bounding_box['height'],
                                    selector=selector,
                                    confidence=0.7,  # Traditional detection confidence
                                    description=f"Link: {text_content[:50]}...",
                                    metadata={
                                        'text': text_content,
                                        'href': href,
                                        'link_type': link_name
                                    }
                                )
                                results[link_name] = result
                                logger.info(f"   ✅ Found {link_name} via selector: {selector}")
                                break
                    except Exception as e:
                        logger.debug(f"Selector '{selector}' failed: {e}")
                        continue
                        
                if link_name not in results:
                    logger.warning(f"   ❌ Could not find {link_name}")
                    
            except Exception as e:
                logger.error(f"Failed to detect {link_name}: {e}")
        
        return results
    
    async def _detect_using_stacked_ai(self, page: Page, target_elements: List[str], context: str) -> Dict[str, DetectionResult]:
        """Use two-layer AI analysis: ISA Vision + OpenAI Vision for high-precision element detection"""
        logger.info(f"🤖 Initializing two-layer AI detection for {context} context...")
        
        # Take screenshot for analysis
        screenshot = await page.screenshot(full_page=False)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_file.write(screenshot)
            screenshot_path = tmp_file.name
        
        try:
            # Step 1: Use ISA Vision (OmniParser) to get all UI element coordinates
            logger.info("🎯 Step 1: Getting UI element coordinates with ISA OmniParser...")
            isa_result = await self.client.invoke(
                input_data=screenshot_path,
                task="detect_ui_elements",
                service_type="vision", 
                model="isa-omniparser-ui-detection",
                provider="isa"
            )
            
            if not isa_result.get("success"):
                logger.error(f"❌ ISA Vision detection failed: {isa_result}")
                return {}
            
            ui_elements = isa_result.get("result", {}).get("ui_elements", [])
            logger.info(f"📋 ISA detected {len(ui_elements)} UI elements for {context}")
            
            # Step 2: Use OpenAI Vision for semantic understanding 
            logger.info("🧠 Step 2: Getting semantic element mapping with OpenAI Vision...")
            semantic_result = await self._openai_semantic_analysis(screenshot_path, ui_elements, target_elements, context)
            
            if semantic_result:
                logger.info(f"✅ Two-layer {context} analysis completed successfully")
                return semantic_result
            else:
                logger.error(f"❌ Semantic analysis failed, falling back to ISA-only mapping")
                # Fallback to basic ISA mapping
                return await self._fallback_isa_mapping(ui_elements, target_elements, context)
            
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
        """Use ISA Vision-only analysis for element detection (no OpenAI semantic layer)"""
        logger.info(f"👁️ Using ISA vision-only detection...")
        
        results = {}
        
        # Take screenshot
        screenshot = await page.screenshot(full_page=False)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_file.write(screenshot)
            screenshot_path = tmp_file.name
        
        try:
            # Use ISA Vision (OmniParser) to get UI element coordinates
            result = await self.client.invoke(
                input_data=screenshot_path,
                task="detect_ui_elements",
                service_type="vision",
                model="isa-omniparser-ui-detection",
                provider="isa"
            )
            
            if result.get('success'):
                analysis_result = result.get('result', {})
            else:
                analysis_result = {}
            
            # Parse ISA UI detection results
            ui_elements = analysis_result.get("ui_elements", [])
            
            try:
                for element in ui_elements:
                    element_type_str = element.get('type', '').lower()
                    content = element.get('content', '')
                    center = element.get('center', [0, 0])
                    confidence = element.get('confidence', 0.6)
                    interactable = element.get('interactable', False)
                    
                    # Map to target elements
                    element_name = None
                    element_type = ElementType.BUTTON_GENERIC
                    
                    if 'input' in element_type_str:
                        if any(word in content.lower() for word in ['username', 'email', 'user']):
                            element_name = 'username'
                            element_type = ElementType.INPUT_TEXT
                        elif any(word in content.lower() for word in ['password', 'pass']):
                            element_name = 'password'
                            element_type = ElementType.INPUT_PASSWORD
                        elif any(word in content.lower() for word in ['search', 'query']):
                            element_name = 'search_input'
                            element_type = ElementType.INPUT_SEARCH
                    elif 'button' in element_type_str:
                        if any(word in content.lower() for word in ['submit', 'login', 'sign']):
                            element_name = 'submit'
                            element_type = ElementType.BUTTON_SUBMIT
                        elif any(word in content.lower() for word in ['search', 'find']):
                            element_name = 'search_button'
                            element_type = ElementType.BUTTON_GENERIC
                    
                    if element_name and element_name in target_elements and len(center) >= 2:
                        result = DetectionResult(
                            element_type=element_type,
                            strategy=DetectionStrategy.VISION_ONLY,
                            x=int(center[0]),
                            y=int(center[1]),
                            confidence=confidence,
                            description=f"{element_type_str}: {content}",
                            metadata={
                                'isa_type': element_type_str,
                                'content': content,
                                'interactable': interactable
                            }
                        )
                        
                        results[element_name] = result
                        
            except Exception as parse_error:
                logger.warning(f"Failed to parse ISA vision analysis: {parse_error}")
            
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
        """Convert ISA UI detection results to DetectionResult objects (legacy method, now unused)"""
        logger.warning("🔄 Using legacy _convert_stacked_ai_results method - this should be replaced by two-layer analysis")
        
        results = {}
        
        # Process ISA OmniParser UI detection format
        ui_elements = analysis_result.get("ui_elements", [])
        
        logger.info(f"📋 Processing {len(ui_elements)} detected UI elements...")
        
        for element in ui_elements:
            element_type_str = element.get('type', '').lower()
            content = element.get('content', '')
            center = element.get('center', [0, 0])
            confidence = element.get('confidence', 0.8)
            interactable = element.get('interactable', False)
            
            # Map ISA element types to our element names and types
            element_name = None
            element_type = ElementType.BUTTON_GENERIC
            
            # Match based on element type and content (basic mapping)
            if 'input' in element_type_str or 'textbox' in element_type_str:
                if any(word in content.lower() for word in ['username', 'email', 'user', 'login']):
                    element_name = 'username'
                    element_type = ElementType.INPUT_TEXT
                elif any(word in content.lower() for word in ['password', 'pass']):
                    element_name = 'password'
                    element_type = ElementType.INPUT_PASSWORD
                elif any(word in content.lower() for word in ['search', 'query', 'find']):
                    element_name = 'search_input'
                    element_type = ElementType.INPUT_SEARCH
            elif 'button' in element_type_str:
                if any(word in content.lower() for word in ['submit', 'login', 'sign in', 'log in']):
                    element_name = 'submit'
                    element_type = ElementType.BUTTON_SUBMIT
                elif any(word in content.lower() for word in ['search', 'find', 'go']):
                    element_name = 'search_button'
                    element_type = ElementType.BUTTON_GENERIC
            elif 'link' in element_type_str:
                # Handle different link categories
                if any(word in content.lower() for word in ['product', 'item', 'buy']):
                    element_name = 'product_links'
                elif any(word in content.lower() for word in ['nav', 'menu', 'home', 'about']):
                    element_name = 'navigation_links'
                else:
                    element_name = 'action_links'
                element_type = ElementType.LINK
            
            # Only add if we found a matching target element and it's interactable
            if element_name and element_name in target_elements and interactable and len(center) >= 2:
                result = DetectionResult(
                    element_type=element_type,
                    strategy=DetectionStrategy.VISION_ONLY,  # Changed from STACKED_AI since it's just ISA
                    x=int(center[0]),
                    y=int(center[1]),
                    confidence=confidence,
                    description=f"ISA-only: {element_type_str} - {content}",
                    metadata={
                        'isa_type': element_type_str,
                        'content': content,
                        'interactable': interactable,
                        'isa_element': element,
                        'source': 'isa_only_legacy'
                    }
                )
                
                results[element_name] = result
                logger.info(f"   ✅ {element_name}: ({center[0]}, {center[1]}) - {content} (confidence: {confidence:.3f})")
        
        logger.info(f"🎯 Mapped {len(results)} UI elements to target elements")
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
        """Detect a generic element using two-layer AI with natural language description"""
        try:
            # Take screenshot
            screenshot = await page.screenshot(full_page=False)
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(screenshot)
                screenshot_path = tmp_file.name
            
            try:
                # Step 1: Use ISA Vision to get all UI elements
                isa_result = await self.client.invoke(
                    input_data=screenshot_path,
                    task="detect_ui_elements",
                    service_type="vision",
                    model="isa-omniparser-ui-detection",
                    provider="isa"
                )
                
                if not isa_result.get('success'):
                    logger.error(f"❌ ISA Vision detection failed: {isa_result}")
                    return None
                
                ui_elements = isa_result.get("result", {}).get("ui_elements", [])
                
                # Step 2: Use OpenAI Vision for semantic understanding
                semantic_result = await self._openai_generic_element_analysis(screenshot_path, ui_elements, description)
                
                if semantic_result:
                    return semantic_result
                else:
                    # Fallback to ISA-only matching
                    return await self._fallback_generic_element_matching(ui_elements, description)
                
            finally:
                if os.path.exists(screenshot_path):
                    os.unlink(screenshot_path)
                    
        except Exception as e:
            logger.error(f"Generic element AI detection failed: {e}")
            return None
    
    async def _openai_semantic_analysis(self, screenshot_path: str, ui_elements: List[Dict], 
                                       target_elements: List[str], context: str) -> Dict[str, DetectionResult]:
        """Use OpenAI Vision to semantically map UI elements to target elements"""
        try:
            logger.info(f"🧠 Starting OpenAI semantic analysis for {context} elements...")
            
            # Prepare element coordinate information
            element_info = []
            for i, elem in enumerate(ui_elements):
                center = elem.get('center', [0, 0])
                content = elem.get('content', '')
                elem_type = elem.get('type', '')
                element_info.append(f"Element {i}: {elem_type} at ({center[0]}, {center[1]}) with content '{content}'")
            
            elements_text = "\n".join(element_info)
            
            # Create context-specific prompt
            if context == 'login':
                prompt = f"""Looking at this login page, I need you to map the detected UI elements to login form fields.

Here are the detected UI elements with their coordinates:
{elements_text}

Please identify which elements correspond to:
- username/email input field
- password input field  
- submit/login button

IMPORTANT: Respond ONLY with this JSON format, no other text:
{{
    "username": {{"element_index": X, "confidence": 0.9, "reasoning": "explanation"}},
    "password": {{"element_index": Y, "confidence": 0.9, "reasoning": "explanation"}},
    "submit": {{"element_index": Z, "confidence": 0.9, "reasoning": "explanation"}}
}}

Only include elements you are confident about (confidence > 0.7). Start your response with {{ and end with }}."""

            elif context == 'search':
                prompt = f"""Looking at this search page, I need you to map the detected UI elements to search form fields.

Here are the detected UI elements with their coordinates:
{elements_text}

Please identify which elements correspond to:
- search input field (text box where users type queries)
- search button (button to submit the search)

IMPORTANT: Respond ONLY with this JSON format, no other text:
{{
    "search_input": {{"element_index": X, "confidence": 0.9, "reasoning": "explanation"}},
    "search_button": {{"element_index": Y, "confidence": 0.9, "reasoning": "explanation"}}
}}

Only include elements you are confident about (confidence > 0.7). Start your response with {{ and end with }}."""

            else:
                # Generic context
                prompt = f"""Looking at this webpage, I need you to map the detected UI elements to the requested elements: {target_elements}.

Here are the detected UI elements with their coordinates:
{elements_text}

Please identify which elements correspond to the requested target elements.

IMPORTANT: Respond ONLY with this JSON format, no other text:
{{
    "element_name": {{"element_index": X, "confidence": 0.9, "reasoning": "explanation"}}
}}

Only include elements you are confident about (confidence > 0.7). Start your response with {{ and end with }}."""
            
            # Use OpenAI Vision service
            openai_result = await self.client.invoke(
                screenshot_path,
                "analyze", 
                "vision",
                prompt=prompt
            )
            
            if not openai_result.get("success"):
                logger.warning(f"⚠️ OpenAI semantic analysis failed: {openai_result}")
                return {}
            
            # Parse OpenAI response
            analysis_text = openai_result.get("result", {}).get("text", "")
            logger.info(f"🔍 OpenAI {context.title()} Response: {analysis_text[:200]}...")
            
            # Extract JSON from response
            import json
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if not json_match:
                logger.warning(f"⚠️ No JSON found in OpenAI response. Full response: {analysis_text}")
                return {}
            
            try:
                semantic_mapping = json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse JSON: {e}")
                return {}
            
            # Convert semantic mapping to DetectionResult objects
            results = {}
            
            for field_name, mapping in semantic_mapping.items():
                if mapping.get("confidence", 0) > 0.7:
                    element_index = mapping.get("element_index")
                    if 0 <= element_index < len(ui_elements):
                        element = ui_elements[element_index]
                        center = element.get('center', [0, 0])
                        
                        # Map field name to element type
                        element_type = self._map_field_to_element_type(field_name)
                        
                        result = DetectionResult(
                            element_type=element_type,
                            strategy=DetectionStrategy.STACKED_AI,
                            x=int(center[0]),
                            y=int(center[1]),
                            confidence=mapping.get('confidence', 0.8),
                            description=f"OpenAI semantic {context}: {mapping.get('reasoning', '')}",
                            metadata={
                                'field_name': field_name,
                                'isa_element': element,
                                'semantic_reasoning': mapping.get('reasoning', ''),
                                'source': 'openai_semantic'
                            }
                        )
                        
                        results[field_name] = result
                        logger.info(f"🎯 Mapped {field_name}: ({center[0]}, {center[1]}) - {mapping.get('reasoning', '')}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ OpenAI semantic analysis failed: {e}")
            return {}
    
    async def _fallback_isa_mapping(self, ui_elements: List[Dict], target_elements: List[str], 
                                   context: str) -> Dict[str, DetectionResult]:
        """Fallback ISA-only mapping when OpenAI semantic analysis fails"""
        try:
            logger.info(f"🔄 Using fallback ISA-only mapping for {context} elements...")
            
            results = {}
            
            for element in ui_elements:
                element_type_str = element.get('type', '').lower()
                content = element.get('content', '').lower()
                center = element.get('center', [0, 0])
                confidence = element.get('confidence', 0.8)
                interactable = element.get('interactable', False)
                
                if not interactable or len(center) < 2:
                    continue
                
                # Map based on content and type
                field_name = None
                element_type = ElementType.BUTTON_GENERIC
                
                if 'input' in element_type_str or 'textbox' in element_type_str:
                    if any(word in content for word in ['username', 'email', 'user', 'login']):
                        field_name = 'username'
                        element_type = ElementType.INPUT_TEXT
                    elif any(word in content for word in ['password', 'pass']):
                        field_name = 'password'
                        element_type = ElementType.INPUT_PASSWORD
                    elif any(word in content for word in ['search', 'query', 'find']):
                        field_name = 'search_input'
                        element_type = ElementType.INPUT_SEARCH
                elif 'button' in element_type_str:
                    if any(word in content for word in ['login', 'sign in', 'submit', 'log in']):
                        field_name = 'submit'
                        element_type = ElementType.BUTTON_SUBMIT
                    elif any(word in content for word in ['search', 'find', 'go']):
                        field_name = 'search_button'
                        element_type = ElementType.BUTTON_GENERIC
                
                if field_name and field_name in target_elements and field_name not in results:
                    result = DetectionResult(
                        element_type=element_type,
                        strategy=DetectionStrategy.VISION_ONLY,
                        x=int(center[0]),
                        y=int(center[1]),
                        confidence=confidence,
                        description=f"ISA fallback {context}: {element_type_str} - {content}",
                        metadata={
                            'field_name': field_name,
                            'isa_element': element,
                            'source': 'isa_fallback'
                        }
                    )
                    results[field_name] = result
                    logger.info(f"🔄 Fallback mapped {field_name}: ({center[0]}, {center[1]})")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ ISA fallback mapping failed: {e}")
            return {}
    
    async def _openai_generic_element_analysis(self, screenshot_path: str, ui_elements: List[Dict], 
                                             description: str) -> Optional[DetectionResult]:
        """Use OpenAI Vision to find a generic element by description"""
        try:
            # Prepare element coordinate information
            element_info = []
            for i, elem in enumerate(ui_elements):
                center = elem.get('center', [0, 0])
                content = elem.get('content', '')
                elem_type = elem.get('type', '')
                element_info.append(f"Element {i}: {elem_type} at ({center[0]}, {center[1]}) with content '{content}'")
            
            elements_text = "\n".join(element_info)
            
            prompt = f"""Looking at this webpage, I need you to find the UI element that matches this description: "{description}"

Here are the detected UI elements with their coordinates:
{elements_text}

Please identify which element best matches the description.

IMPORTANT: Respond ONLY with this JSON format, no other text:
{{
    "found": true/false,
    "element_index": X,
    "confidence": 0.9,
    "reasoning": "explanation of why this element matches"
}}

Only respond with found=true if you are confident (confidence > 0.7). Start your response with {{ and end with }}."""
            
            # Use OpenAI Vision service
            openai_result = await self.client.invoke(
                screenshot_path,
                "analyze", 
                "vision",
                prompt=prompt
            )
            
            if not openai_result.get("success"):
                logger.warning(f"⚠️ OpenAI generic element analysis failed: {openai_result}")
                return None
            
            # Parse OpenAI response
            analysis_text = openai_result.get("result", {}).get("text", "")
            logger.info(f"🔍 OpenAI Generic Response: {analysis_text[:200]}...")
            
            # Extract JSON from response
            import json
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if not json_match:
                logger.warning(f"⚠️ No JSON found in OpenAI response. Full response: {analysis_text}")
                return None
            
            try:
                result_data = json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse JSON: {e}")
                return None
            
            if result_data.get("found") and result_data.get("confidence", 0) > 0.7:
                element_index = result_data.get("element_index")
                if 0 <= element_index < len(ui_elements):
                    element = ui_elements[element_index]
                    center = element.get('center', [0, 0])
                    
                    # Determine element type from ISA detection
                    element_type_str = element.get('type', 'generic').lower()
                    element_type = ElementType.BUTTON_GENERIC  # default
                    
                    if 'input' in element_type_str:
                        element_type = ElementType.INPUT_TEXT
                    elif 'button' in element_type_str:
                        element_type = ElementType.BUTTON_GENERIC
                    elif 'link' in element_type_str:
                        element_type = ElementType.LINK
                    
                    return DetectionResult(
                        element_type=element_type,
                        strategy=DetectionStrategy.STACKED_AI,
                        x=int(center[0]),
                        y=int(center[1]),
                        confidence=result_data.get('confidence', 0.8),
                        description=f"OpenAI generic: {result_data.get('reasoning', description)}",
                        metadata={
                            'original_description': description,
                            'isa_element': element,
                            'semantic_reasoning': result_data.get('reasoning', ''),
                            'source': 'openai_semantic'
                        }
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ OpenAI generic element analysis failed: {e}")
            return None
    
    async def _fallback_generic_element_matching(self, ui_elements: List[Dict], 
                                               description: str) -> Optional[DetectionResult]:
        """Fallback method to find generic elements using content matching"""
        try:
            logger.info(f"🔄 Using fallback matching for generic element: {description}")
            
            description_lower = description.lower()
            best_match = None
            best_score = 0.0
            
            for element in ui_elements:
                element_type_str = element.get('type', '').lower()
                content = element.get('content', '').lower()
                center = element.get('center', [0, 0])
                confidence = element.get('confidence', 0.6)
                interactable = element.get('interactable', False)
                
                # Score based on description match
                score = 0.0
                
                # Check content match
                if content and any(word in content for word in description_lower.split()):
                    score += 0.5
                
                # Check type match
                if any(word in element_type_str for word in description_lower.split()):
                    score += 0.3
                    
                # Boost score for interactable elements
                if interactable:
                    score += 0.2
                
                # Weighted by confidence
                final_score = score * confidence
                
                if final_score > best_score and final_score > 0.3:  # Minimum threshold
                    best_score = final_score
                    best_match = element
            
            if best_match and len(best_match.get('center', [])) >= 2:
                # Map element type string to enum
                element_type_str = best_match.get('type', 'generic').lower()
                element_type = ElementType.BUTTON_GENERIC  # default
                
                if 'input' in element_type_str:
                    element_type = ElementType.INPUT_TEXT
                elif 'button' in element_type_str:
                    element_type = ElementType.BUTTON_GENERIC
                elif 'link' in element_type_str:
                    element_type = ElementType.LINK
                
                center = best_match.get('center', [0, 0])
                return DetectionResult(
                    element_type=element_type,
                    strategy=DetectionStrategy.VISION_ONLY,
                    x=int(center[0]),
                    y=int(center[1]),
                    confidence=best_score,
                    description=f"ISA fallback: {element_type_str} - {best_match.get('content', description)}",
                    metadata={
                        'original_description': description,
                        'isa_element': best_match,
                        'match_score': best_score,
                        'source': 'isa_fallback'
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Fallback generic element matching failed: {e}")
            return None
    
    def _map_field_to_element_type(self, field_name: str) -> ElementType:
        """Map field name to ElementType enum"""
        field_mapping = {
            'username': ElementType.INPUT_TEXT,
            'email': ElementType.INPUT_EMAIL,
            'password': ElementType.INPUT_PASSWORD,
            'submit': ElementType.BUTTON_SUBMIT,
            'search_input': ElementType.INPUT_SEARCH,
            'search_button': ElementType.BUTTON_GENERIC,
            'login': ElementType.BUTTON_SUBMIT
        }
        return field_mapping.get(field_name, ElementType.BUTTON_GENERIC)

    async def close(self):
        """Clean up resources"""
        if self.ui_service:
            await self.ui_service.close()
        await self.vision_analyzer.close() if hasattr(self.vision_analyzer, 'close') else None