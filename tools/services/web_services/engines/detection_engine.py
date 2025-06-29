#!/usr/bin/env python
"""
Detection Engine for Web Services
Coordinates different element detection strategies for optimal accuracy
"""
import asyncio
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from playwright.async_api import Page

from core.logging import get_logger
from ..strategies.detection.vision_analyzer import VisionAnalyzer
from ..strategies.detection.selector_analyzer import SelectorAnalyzer
from ..strategies.detection.intelligent_element_detector import IntelligentElementDetector

logger = get_logger(__name__)

class DetectionMode(Enum):
    """Detection operation modes"""
    FAST = "fast"           # Traditional selectors only
    BALANCED = "balanced"   # Traditional + AI fallback
    ACCURATE = "accurate"   # Full multi-strategy detection
    AI_ONLY = "ai_only"    # AI-powered detection only

class DetectionEngine:
    """Main detection engine that coordinates different detection strategies"""
    
    def __init__(self, mode: DetectionMode = DetectionMode.BALANCED):
        self.mode = mode
        self.vision_analyzer = VisionAnalyzer()
        self.selector_analyzer = SelectorAnalyzer()
        self.intelligent_detector = IntelligentElementDetector()
        
        logger.info(f"Detection Engine initialized in {mode.value} mode")
    
    async def detect_login_elements(self, page: Page, target_elements: List[str] = None) -> Dict[str, Any]:
        """
        Detect login form elements using the configured strategy
        
        Args:
            page: Playwright page object
            target_elements: List of elements to detect (default: ['username', 'password', 'submit'])
            
        Returns:
            Dictionary of detected elements with coordinates and metadata
        """
        if target_elements is None:
            target_elements = ['username', 'password', 'submit']
        
        logger.info(f"🎯 Starting login detection for: {target_elements} (mode: {self.mode.value})")
        
        if self.mode == DetectionMode.FAST:
            return await self._fast_detection(page, target_elements, 'login')
        elif self.mode == DetectionMode.BALANCED:
            return await self._balanced_detection(page, target_elements, 'login')
        elif self.mode == DetectionMode.ACCURATE:
            return await self._accurate_detection(page, target_elements, 'login')
        elif self.mode == DetectionMode.AI_ONLY:
            return await self._ai_only_detection(page, target_elements, 'login')
        else:
            return await self._balanced_detection(page, target_elements, 'login')
    
    async def detect_search_elements(self, page: Page, target_elements: List[str] = None) -> Dict[str, Any]:
        """Detect search form elements"""
        if target_elements is None:
            target_elements = ['search_input', 'search_button']
        
        logger.info(f"🔍 Starting search detection for: {target_elements} (mode: {self.mode.value})")
        
        if self.mode == DetectionMode.FAST:
            return await self._fast_detection(page, target_elements, 'search')
        elif self.mode == DetectionMode.BALANCED:
            return await self._balanced_detection(page, target_elements, 'search')
        elif self.mode == DetectionMode.ACCURATE:
            return await self._accurate_detection(page, target_elements, 'search')
        elif self.mode == DetectionMode.AI_ONLY:
            return await self._ai_only_detection(page, target_elements, 'search')
        else:
            return await self._balanced_detection(page, target_elements, 'search')
    
    async def detect_generic_elements(self, page: Page, element_descriptions: List[str]) -> List[Dict[str, Any]]:
        """Detect elements based on natural language descriptions"""
        logger.info(f"🎯 Generic element detection: {element_descriptions}")
        
        # Always use intelligent detector for generic elements
        results = await self.intelligent_detector.detect_generic_elements(page, element_descriptions)
        return [result.to_dict() for result in results]
    
    async def _fast_detection(self, page: Page, target_elements: List[str], context: str) -> Dict[str, Any]:
        """Fast detection using traditional selectors only"""
        logger.info("⚡ Using fast detection (traditional selectors)")
        
        if context == 'login':
            return await self.selector_analyzer.identify_login_elements(page)
        elif context == 'search':
            return await self._detect_search_traditional(page, target_elements)
        else:
            return {}
    
    async def _balanced_detection(self, page: Page, target_elements: List[str], context: str) -> Dict[str, Any]:
        """Balanced detection: traditional first, AI fallback"""
        logger.info("⚖️ Using balanced detection (traditional + AI fallback)")
        
        # Try traditional first
        if context == 'login':
            results = await self.selector_analyzer.identify_login_elements(page)
        elif context == 'search':
            results = await self._detect_search_traditional(page, target_elements)
        else:
            results = {}
        
        # If we found all elements, return
        if len(results) >= len(target_elements):
            logger.info(f"✅ Traditional detection found all {len(results)} elements")
            return results
        
        # Otherwise, use AI for missing elements
        missing_elements = [elem for elem in target_elements if elem not in results]
        logger.info(f"🤖 Using AI fallback for missing elements: {missing_elements}")
        
        try:
            if context == 'login':
                ai_results = await self.vision_analyzer.identify_login_form(page)
            else:
                ai_results = await self.vision_analyzer.identify_search_form(page)
            
            # Merge results
            for elem_name, elem_data in ai_results.items():
                if elem_name in missing_elements:
                    results[elem_name] = elem_data
        except Exception as e:
            logger.warning(f"AI fallback failed: {e}")
        
        return results
    
    async def _accurate_detection(self, page: Page, target_elements: List[str], context: str) -> Dict[str, Any]:
        """Most accurate detection using full intelligent detector"""
        logger.info("🎯 Using accurate detection (full multi-strategy)")
        
        if context == 'login':
            detection_results = await self.intelligent_detector.detect_login_elements(page, target_elements)
        elif context == 'search':
            detection_results = await self.intelligent_detector.detect_search_elements(page, target_elements)
        else:
            return {}
        
        # Convert DetectionResult objects to dictionaries
        results = {}
        for elem_name, detection_result in detection_results.items():
            results[elem_name] = detection_result.to_dict()
        
        return results
    
    async def _ai_only_detection(self, page: Page, target_elements: List[str], context: str) -> Dict[str, Any]:
        """AI-only detection using vision analyzer"""
        logger.info("🤖 Using AI-only detection")
        
        try:
            if context == 'login':
                return await self.vision_analyzer.identify_login_form(page)
            elif context == 'search':
                return await self.vision_analyzer.identify_search_form(page)
            else:
                return {}
        except Exception as e:
            logger.error(f"AI-only detection failed: {e}")
            return {}
    
    async def _detect_search_traditional(self, page: Page, target_elements: List[str]) -> Dict[str, Any]:
        """Traditional search element detection"""
        results = {}
        
        if 'search_input' in target_elements:
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
                            results['search_input'] = {
                                'type': 'css_selector',
                                'selector': selector,
                                'x': bounding_box['x'] + bounding_box['width'] / 2,
                                'y': bounding_box['y'] + bounding_box['height'] / 2,
                                'width': bounding_box['width'],
                                'height': bounding_box['height']
                            }
                            break
                except:
                    continue
        
        if 'search_button' in target_elements:
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
                            results['search_button'] = {
                                'type': 'css_selector',
                                'selector': selector,
                                'x': bounding_box['x'] + bounding_box['width'] / 2,
                                'y': bounding_box['y'] + bounding_box['height'] / 2,
                                'width': bounding_box['width'],
                                'height': bounding_box['height']
                            }
                            break
                except:
                    continue
        
        return results
    
    def set_mode(self, mode: DetectionMode):
        """Change detection mode"""
        self.mode = mode
        logger.info(f"Detection mode changed to: {mode.value}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            'mode': self.mode.value,
            'strategies_available': ['vision', 'selector', 'intelligent'],
            'initialized': True
        }
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.intelligent_detector.close()
            logger.info("Detection engine cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")