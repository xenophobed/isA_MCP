#!/usr/bin/env python
"""
Vision Analyzer for Web Services
Provides vision-guided web automation using AI models to understand page layouts
Integrated with stacked AI model for precise coordinate detection
"""
import json
import base64
import tempfile
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from playwright.async_api import Page

from core.logging import get_logger
from core.isa_client import get_isa_client
from ...utils.vision_cache_manager import get_vision_cache_manager

logger = get_logger(__name__)

class VisionAnalyzer:
    """Vision-guided web automation using AI models with stacked architecture"""
    
    def __init__(self):
        self.screenshots_path = Path("screenshots")
        self.screenshots_path.mkdir(exist_ok=True)
        self.monitoring_path = Path("monitoring")
        self.monitoring_path.mkdir(exist_ok=True)
        self.client = None
        self.cache_manager = get_vision_cache_manager()
        
        logger.info("✅ VisionAnalyzer initialized with cache management")
    
    async def identify_login_form(self, page: Page) -> Dict[str, Any]:
        """Identify login form elements using cached/pre-configured data or AI analysis"""
        try:
            url = page.url
            logger.info(f"🎯 Starting login form identification for: {url}")
            
            # Step 1: Check pre-configured sites first (fastest)
            preconfig_result = await self.cache_manager.get_preconfig_detection(url, 'login')
            if preconfig_result:
                logger.info("⚡ Using pre-configured login elements (instant)")
                return preconfig_result
            
            # Step 2: Check cache (fast)
            page_content = await page.content()
            cached_result = await self.cache_manager.get_cached_detection(
                url, 'login', page_content[:2000]  # Use first 2000 chars for cache validation
            )
            if cached_result:
                logger.info("💾 Using cached login elements (fast)")
                return cached_result
            
            # Step 3: Fallback to AI analysis (slow but accurate)
            logger.info("🤖 No cache/preconfig found, using AI analysis (slow)")
            
            # Take screenshot for analysis
            screenshot = await page.screenshot(full_page=False)
            logger.info(f"📸 Screenshot taken: {len(screenshot)} bytes")
            
            # Save screenshot temporarily
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(screenshot)
                screenshot_path = tmp_file.name
            
            logger.info(f"📁 Screenshot saved: {screenshot_path}")
            
            try:
                # Use stacked AI model for login analysis
                login_elements = await self._stacked_ai_login_analysis(screenshot_path)
                logger.info(f"🤖 Stacked AI analysis result: {login_elements}")
                
                if login_elements and len(login_elements) >= 2:
                    # Cache the successful result
                    await self.cache_manager.save_detection_result(
                        url, 'login', login_elements, 0.85, page_content[:2000]
                    )
                    logger.info(f"✅ Successfully identified and cached login elements: {len(login_elements)} elements")
                    return login_elements
                else:
                    logger.error("❌ Stacked AI failed to detect sufficient login elements")
                    raise Exception("Stacked AI detection failed - unable to identify login form")
                    
            finally:
                # Clean up temporary file
                if os.path.exists(screenshot_path):
                    os.unlink(screenshot_path)
                    logger.info("🧹 Cleaned up temporary screenshot")
            
        except Exception as e:
            logger.error(f"❌ Login form identification failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    async def _detect_login_elements_fallback(self, page: Page) -> Dict[str, str]:
        """Fallback method using traditional selectors"""
        login_elements = {}
        
        # Try to find username field
        username_selectors = [
            'input[type="email"]',
            'input[name="username"]',
            'input[name="email"]',
            'input[placeholder*="email" i]',
            'input[placeholder*="username" i]'
        ]
        
        for selector in username_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    login_elements['username'] = selector
                    break
            except:
                continue
        
        # Try to find password field
        password_selector = 'input[type="password"]'
        try:
            element = await page.query_selector(password_selector)
            if element:
                login_elements['password'] = password_selector
        except:
            pass
        
        # Try to find submit button
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
            'button:has-text("Log in")'
        ]
        
        for selector in submit_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    login_elements['submit'] = selector
                    break
            except:
                continue
        
        return login_elements if len(login_elements) >= 2 else {}
    
    async def _stacked_ai_login_analysis(self, screenshot_path: str) -> Dict[str, Any]:
        """Two-layer AI analysis: ISA Vision for coordinates + OpenAI Vision for semantics"""
        try:
            logger.info("🔧 Initializing two-layer AI analysis for login detection...")
            
            # Use ISA Model client for vision analysis
            if self.client is None:
                self.client = get_isa_client()
                logger.info(f"✅ ISA Model client initialized")
            
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
            logger.info(f"📋 ISA detected {len(ui_elements)} UI elements")
            
            # Step 2: Use OpenAI Vision for semantic understanding of login elements
            logger.info("🧠 Step 2: Getting semantic login element mapping with OpenAI Vision...")
            semantic_result = await self._openai_semantic_login_analysis(screenshot_path, ui_elements)
            
            if semantic_result:
                logger.info(f"✅ Two-layer analysis completed successfully")
                return semantic_result
            else:
                logger.error(f"❌ Semantic analysis failed, falling back to ISA-only mapping")
                # Fallback to basic ISA mapping
                return await self._fallback_isa_login_mapping(ui_elements)
                
        except Exception as e:
            logger.error(f"❌ Two-layer AI login analysis failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {}
    
    async def _openai_semantic_login_analysis(self, screenshot_path: str, ui_elements: List[Dict]) -> Dict[str, Any]:
        """Use OpenAI Vision to semantically map UI elements to login form fields"""
        try:
            logger.info("🧠 Starting OpenAI semantic analysis for login elements...")
            
            # Prepare element coordinate information
            element_info = []
            for i, elem in enumerate(ui_elements):
                center = elem.get('center', [0, 0])
                content = elem.get('content', '')
                elem_type = elem.get('type', '')
                element_info.append(f"Element {i}: {elem_type} at ({center[0]}, {center[1]}) with content '{content}'")
            
            elements_text = "\n".join(element_info)
            
            # Create semantic analysis prompt
            prompt = f"""Looking at this login page, I need you to map the detected UI elements to login form fields.

Here are the detected UI elements with their coordinates:
{elements_text}

Please identify which elements correspond to:
- Username/Email input field
- Password input field  
- Login/Submit button

IMPORTANT: Respond ONLY with this JSON format, no other text:
{{
    "username": {{"element_index": X, "confidence": 0.9, "reasoning": "explanation"}},
    "password": {{"element_index": Y, "confidence": 0.9, "reasoning": "explanation"}},
    "submit": {{"element_index": Z, "confidence": 0.9, "reasoning": "explanation"}}
}}

Only include elements you are confident about (confidence > 0.7). Start your response with {{ and end with }}."""
            
            # Use OpenAI Vision service (new unified task design)
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
            logger.info(f"🔍 OpenAI Response: {analysis_text[:200]}...")  # 打印前200字符
            
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
            
            # Convert semantic mapping to element references
            element_refs = {}
            for field_name, mapping in semantic_mapping.items():
                if mapping.get("confidence", 0) > 0.7:
                    element_index = mapping.get("element_index")
                    if 0 <= element_index < len(ui_elements):
                        element = ui_elements[element_index]
                        center = element.get('center', [0, 0])
                        
                        element_refs[field_name] = {
                            'type': 'coordinate',
                            'x': int(center[0]),
                            'y': int(center[1]),
                            'action': 'type' if field_name in ['username', 'password'] else 'click',
                            'description': f"OpenAI semantic: {mapping.get('reasoning', '')}",
                            'confidence': mapping.get('confidence', 0.8),
                            'source': 'openai_semantic',
                            'isa_element': element
                        }
                        logger.info(f"🎯 Mapped {field_name}: ({center[0]}, {center[1]}) - {mapping.get('reasoning', '')}")
            
            return element_refs if len(element_refs) >= 2 else {}
            
        except Exception as e:
            logger.error(f"❌ OpenAI semantic analysis failed: {e}")
            return {}
    
    async def _fallback_isa_login_mapping(self, ui_elements: List[Dict]) -> Dict[str, Any]:
        """Fallback ISA-only mapping when OpenAI semantic analysis fails"""
        try:
            logger.info("🔄 Using fallback ISA-only mapping for login elements...")
            
            element_refs = {}
            
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
                action = 'click'
                
                if 'input' in element_type_str or 'textbox' in element_type_str:
                    if any(word in content for word in ['username', 'email', 'user', 'login']):
                        field_name = 'username'
                        action = 'type'
                    elif any(word in content for word in ['password', 'pass']):
                        field_name = 'password'
                        action = 'type'
                elif 'button' in element_type_str:
                    if any(word in content for word in ['login', 'sign in', 'submit', 'log in']):
                        field_name = 'submit'
                        action = 'click'
                
                if field_name and field_name not in element_refs:
                    element_refs[field_name] = {
                        'type': 'coordinate',
                        'x': int(center[0]),
                        'y': int(center[1]),
                        'action': action,
                        'description': f"ISA fallback: {element_type_str} - {content}",
                        'confidence': confidence,
                        'source': 'isa_fallback',
                        'isa_element': element
                    }
                    logger.info(f"🔄 Fallback mapped {field_name}: ({center[0]}, {center[1]})")
            
            return element_refs
            
        except Exception as e:
            logger.error(f"❌ ISA fallback mapping failed: {e}")
            return {}
    
    async def identify_search_form(self, page: Page) -> Dict[str, Any]:
        """Identify search form elements using cached/pre-configured data or AI analysis"""
        try:
            url = page.url
            logger.info(f"🔍 Starting search form identification for: {url}")
            
            # Step 1: Check pre-configured sites first (fastest)
            preconfig_result = await self.cache_manager.get_preconfig_detection(url, 'search')
            if preconfig_result:
                logger.info("⚡ Using pre-configured search elements (instant)")
                return preconfig_result
            
            # Step 2: Check cache (fast)
            page_content = await page.content()
            cached_result = await self.cache_manager.get_cached_detection(
                url, 'search', page_content[:2000]
            )
            if cached_result:
                logger.info("💾 Using cached search elements (fast)")
                return cached_result
            
            # Step 3: Fallback to AI analysis (slow but accurate)
            logger.info("🤖 No cache/preconfig found, using AI analysis (slow)")
            
            # Take screenshot for analysis
            screenshot = await page.screenshot(full_page=False)
            logger.info(f"📸 Screenshot taken: {len(screenshot)} bytes")
            
            # Save screenshot temporarily
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(screenshot)
                screenshot_path = tmp_file.name
            
            logger.info(f"📁 Screenshot saved: {screenshot_path}")
            
            try:
                # Use hybrid UI analysis for search form detection
                search_elements = await self._hybrid_search_analysis(screenshot_path)
                logger.info(f"🤖 Hybrid search analysis result: {search_elements}")
                
                if search_elements and len(search_elements) >= 1:
                    # Cache the successful result
                    await self.cache_manager.save_detection_result(
                        url, 'search', search_elements, 0.80, page_content[:2000]
                    )
                    logger.info(f"✅ Successfully identified and cached search elements: {len(search_elements)} elements")
                    return search_elements
                else:
                    logger.warning("⚠️ Hybrid UI analysis found insufficient search elements, falling back to traditional selectors")
                    # Fallback to traditional selectors
                    fallback_elements = await self._detect_search_elements_fallback(page)
                    if fallback_elements:
                        # Cache fallback result with lower confidence
                        await self.cache_manager.save_detection_result(
                            url, 'search', fallback_elements, 0.60, page_content[:2000]
                        )
                    return fallback_elements
                    
            finally:
                # Clean up temporary file
                if os.path.exists(screenshot_path):
                    os.unlink(screenshot_path)
                    logger.info("🧹 Cleaned up temporary screenshot")
            
        except Exception as e:
            logger.error(f"❌ Search form identification failed: {e}")
            return {
                'input': 'input[type="search"], input[name*="search"], input[placeholder*="search" i]',
                'submit': 'button[type="submit"], button:has-text("Search"), input[type="submit"]'
            }
    
    async def _detect_search_elements_fallback(self, page: Page) -> Dict[str, str]:
        """Fallback method for search form detection"""
        search_elements = {}
        
        # Try to find search input
        search_selectors = [
            'input[type="search"]',
            'input[name="search"]',
            'input[name="q"]',
            'input[placeholder*="search" i]',
            'input[aria-label*="search" i]'
        ]
        
        for selector in search_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    search_elements['input'] = selector
                    break
            except:
                continue
        
        # Try to find search button
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Search")',
            'button[aria-label*="search" i]'
        ]
        
        for selector in submit_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    search_elements['submit'] = selector
                    break
            except:
                continue
        
        return search_elements if len(search_elements) >= 1 else {}
    
    async def _hybrid_search_analysis(self, screenshot_path: str) -> Dict[str, Any]:
        """Two-layer AI analysis for search form: ISA Vision + OpenAI Vision"""
        try:
            logger.info("🔧 Initializing two-layer AI analysis for search form...")
            
            # Use ISA Model client for vision analysis
            if self.client is None:
                self.client = get_isa_client()
                logger.info(f"✅ ISA Model client initialized")
            
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
            logger.info(f"📋 ISA detected {len(ui_elements)} UI elements for search")
            
            # Step 2: Use OpenAI Vision for semantic understanding of search elements
            logger.info("🧠 Step 2: Getting semantic search element mapping with OpenAI Vision...")
            semantic_result = await self._openai_semantic_search_analysis(screenshot_path, ui_elements)
            
            if semantic_result:
                logger.info(f"✅ Two-layer search analysis completed successfully")
                return semantic_result
            else:
                logger.error(f"❌ Semantic search analysis failed, falling back to ISA-only mapping")
                # Fallback to basic ISA mapping
                return await self._fallback_isa_search_mapping(ui_elements)
                
        except Exception as e:
            logger.error(f"❌ Two-layer search analysis failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {}
    
    async def _openai_semantic_search_analysis(self, screenshot_path: str, ui_elements: List[Dict]) -> Dict[str, Any]:
        """Use OpenAI Vision to semantically map UI elements to search form fields"""
        try:
            logger.info("🧠 Starting OpenAI semantic analysis for search elements...")
            
            # Prepare element coordinate information
            element_info = []
            for i, elem in enumerate(ui_elements):
                center = elem.get('center', [0, 0])
                content = elem.get('content', '')
                elem_type = elem.get('type', '')
                element_info.append(f"Element {i}: {elem_type} at ({center[0]}, {center[1]}) with content '{content}'")
            
            elements_text = "\n".join(element_info)
            
            # Create semantic analysis prompt
            prompt = f"""Looking at this search page, I need you to map the detected UI elements to search form fields.

Here are the detected UI elements with their coordinates:
{elements_text}

Please identify which elements correspond to:
- Search input field (text box where users type queries)
- Search button (button to submit the search)

IMPORTANT: Respond ONLY with this JSON format, no other text:
{{
    "search_input": {{"element_index": X, "confidence": 0.9, "reasoning": "explanation"}},
    "search_button": {{"element_index": Y, "confidence": 0.9, "reasoning": "explanation"}}
}}

Only include elements you are confident about (confidence > 0.7). Start your response with {{ and end with }}."""
            
            # Use OpenAI Vision service (new unified task design)
            openai_result = await self.client.invoke(
                screenshot_path,
                "analyze", 
                "vision",
                prompt=prompt
            )
            
            if not openai_result.get("success"):
                logger.warning(f"⚠️ OpenAI semantic search analysis failed: {openai_result}")
                return {}
            
            # Parse OpenAI response
            analysis_text = openai_result.get("result", {}).get("text", "")
            logger.info(f"🔍 OpenAI Search Response: {analysis_text[:200]}...")  # 打印前200字符
            
            # Extract JSON from response
            import json
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if not json_match:
                logger.warning(f"⚠️ No JSON found in OpenAI search response. Full response: {analysis_text}")
                return {}
            
            try:
                semantic_mapping = json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse search JSON: {e}")
                return {}
            
            # Convert semantic mapping to element references
            element_refs = {}
            
            # Map OpenAI field names to test expected names
            field_mapping = {
                'search_input': 'input',
                'search_button': 'submit'
            }
            
            for field_name, mapping in semantic_mapping.items():
                if mapping.get("confidence", 0) > 0.7:
                    element_index = mapping.get("element_index")
                    if 0 <= element_index < len(ui_elements):
                        element = ui_elements[element_index]
                        center = element.get('center', [0, 0])
                        
                        # Use mapped field name for consistency with tests
                        mapped_name = field_mapping.get(field_name, field_name)
                        
                        element_refs[mapped_name] = {
                            'type': 'coordinate',
                            'x': int(center[0]),
                            'y': int(center[1]),
                            'action': 'type' if field_name == 'search_input' else 'click',
                            'description': f"OpenAI semantic search: {mapping.get('reasoning', '')}",
                            'confidence': mapping.get('confidence', 0.8),
                            'source': 'openai_semantic',
                            'isa_element': element
                        }
                        logger.info(f"🎯 Mapped {mapped_name} ({field_name}): ({center[0]}, {center[1]}) - {mapping.get('reasoning', '')}")
            
            return element_refs if len(element_refs) >= 1 else {}
            
        except Exception as e:
            logger.error(f"❌ OpenAI semantic search analysis failed: {e}")
            return {}
    
    async def _fallback_isa_search_mapping(self, ui_elements: List[Dict]) -> Dict[str, Any]:
        """Fallback ISA-only mapping when OpenAI semantic search analysis fails"""
        try:
            logger.info("🔄 Using fallback ISA-only mapping for search elements...")
            
            element_refs = {}
            
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
                action = 'click'
                
                if 'input' in element_type_str or 'textbox' in element_type_str:
                    if any(word in content for word in ['search', 'query', 'find']) or content == '' or 'unanswerable' in content:
                        # Empty content might be search input
                        if 'input' not in element_refs:
                            field_name = 'input'  # Use test-expected name
                            action = 'type'
                elif 'button' in element_type_str:
                    if any(word in content for word in ['search', 'find', 'go', 'submit']) or 'google search' in content:
                        if 'submit' not in element_refs:
                            field_name = 'submit'  # Use test-expected name
                            action = 'click'
                
                if field_name and field_name not in element_refs:
                    element_refs[field_name] = {
                        'type': 'coordinate',
                        'x': int(center[0]),
                        'y': int(center[1]),
                        'action': action,
                        'description': f"ISA fallback search: {element_type_str} - {content}",
                        'confidence': confidence,
                        'source': 'isa_fallback',
                        'isa_element': element
                    }
                    logger.info(f"🔄 Fallback mapped {field_name}: ({center[0]}, {center[1]})")
            
            return element_refs
            
        except Exception as e:
            logger.error(f"❌ ISA fallback search mapping failed: {e}")
            return {}
    
    
    async def extract_search_results(self, page: Page) -> List[Dict[str, Any]]:
        """Extract search results from page"""
        try:
            # Generic search result extraction
            results = []
            
            # Try common search result selectors
            result_selectors = [
                'div[data-result-type]',
                '.search-result',
                '.result',
                'article',
                '[data-testid*="result"]'
            ]
            
            for selector in result_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        for element in elements[:10]:  # Limit to first 10 results
                            result = await self._extract_result_data(element)
                            if result:
                                results.append(result)
                        break
                except:
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to extract search results: {e}")
            return []
    
    async def _extract_result_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract data from a search result element"""
        try:
            # Extract title
            title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', '[data-testid*="title"]']
            title = ""
            for selector in title_selectors:
                try:
                    title_element = await element.query_selector(selector)
                    if title_element:
                        title = await title_element.inner_text()
                        break
                except:
                    continue
            
            # Extract URL
            url = ""
            try:
                link_element = await element.query_selector('a')
                if link_element:
                    url = await link_element.get_attribute('href')
            except:
                pass
            
            # Extract description
            description = ""
            try:
                desc_element = await element.query_selector('.description, .snippet, p')
                if desc_element:
                    description = await desc_element.inner_text()
            except:
                pass
            
            if title or url:
                return {
                    'title': title.strip(),
                    'url': url,
                    'description': description.strip()
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract result data: {e}")
            return None
    
    async def extract_google_results(self, page: Page, max_results: int) -> List[Dict[str, Any]]:
        """Extract Google search results"""
        try:
            results = []
            
            # Google-specific selectors
            result_elements = await page.query_selector_all('div[data-result-type="organic"] h3')
            
            for element in result_elements[:max_results]:
                try:
                    # Get the parent container
                    container = await element.evaluate_handle('el => el.closest("div[data-result-type]")')
                    
                    # Extract title
                    title = await element.inner_text()
                    
                    # Extract URL
                    link_element = await container.query_selector('a')
                    url = await link_element.get_attribute('href') if link_element else ""
                    
                    # Extract description
                    desc_element = await container.query_selector('[data-sncf]')
                    description = await desc_element.inner_text() if desc_element else ""
                    
                    results.append({
                        'title': title.strip(),
                        'url': url,
                        'description': description.strip(),
                        'source': 'google'
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to extract Google result: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to extract Google results: {e}")
            return []
    
    async def extract_bing_results(self, page: Page, max_results: int) -> List[Dict[str, Any]]:
        """Extract Bing search results"""
        try:
            results = []
            
            # Bing-specific selectors
            result_elements = await page.query_selector_all('.b_algo h2 a')
            
            for element in result_elements[:max_results]:
                try:
                    # Extract title and URL
                    title = await element.inner_text()
                    url = await element.get_attribute('href')
                    
                    # Get parent container for description
                    container = await element.evaluate_handle('el => el.closest(".b_algo")')
                    desc_element = await container.query_selector('.b_caption p')
                    description = await desc_element.inner_text() if desc_element else ""
                    
                    results.append({
                        'title': title.strip(),
                        'url': url,
                        'description': description.strip(),
                        'source': 'bing'
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to extract Bing result: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to extract Bing results: {e}")
            return []
    
    async def identify_download_links(self, page: Page) -> List[Dict[str, str]]:
        """Identify download links using vision analysis + traditional methods"""
        try:
            download_links = []
            
            # First try traditional selectors
            download_selectors = [
                'a[href$=".pdf"]',
                'a[href$=".doc"]',
                'a[href$=".docx"]',
                'a[href$=".zip"]',
                'a[href$=".exe"]',
                'a[download]',
                'a:has-text("Download")',
                'a:has-text("download")',
                'button:has-text("Download")'
            ]
            
            for selector in download_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        href = await element.get_attribute('href')
                        download_links.append({
                            'selector': selector,
                            'text': text.strip(),
                            'href': href or "",
                            'detection_method': 'traditional'
                        })
                except:
                    continue
            
            # If no traditional download links found, try vision analysis
            if not download_links:
                vision_links = await self._vision_based_download_detection(page)
                download_links.extend(vision_links)
            
            return download_links
            
        except Exception as e:
            logger.error(f"Failed to identify download links: {e}")
            return []
    
    async def analyze_ui_elements(self, page: Page, task_type: str = "ui_analysis") -> Dict[str, Any]:
        """Generic UI analysis using two-layer AI: ISA Vision + OpenAI Vision"""
        try:
            url = page.url
            logger.info(f"🔍 Starting two-layer UI analysis for task: {task_type} on {url}")
            
            # Step 1: Check pre-configured sites first (fastest)
            preconfig_result = await self.cache_manager.get_preconfig_detection(url, task_type)
            if preconfig_result:
                logger.info(f"⚡ Using pre-configured {task_type} elements (instant)")
                return {'ui_elements': preconfig_result}
            
            # Step 2: Check cache (fast)
            page_content = await page.content()
            cached_result = await self.cache_manager.get_cached_detection(
                url, task_type, page_content[:2000]
            )
            if cached_result:
                logger.info(f"💾 Using cached {task_type} elements (fast)")
                return cached_result
            
            # Step 3: Fallback to two-layer AI analysis (slow but accurate)
            logger.info(f"🤖 No cache/preconfig found, using two-layer AI analysis for {task_type} (slow)")
            
            # Take screenshot for analysis
            screenshot = await page.screenshot(full_page=False)
            logger.info(f"📸 Screenshot taken: {len(screenshot)} bytes")
            
            # Save screenshot temporarily
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(screenshot)
                screenshot_path = tmp_file.name
            
            logger.info(f"📁 Screenshot saved: {screenshot_path}")
            
            try:
                # Use two-layer AI analysis
                nav_elements = await self._two_layer_navigation_analysis(screenshot_path)
                logger.info(f"🤖 Two-layer navigation analysis result: {nav_elements}")
                
                if nav_elements:
                    # Cache the successful result
                    await self.cache_manager.save_detection_result(
                        url, task_type, nav_elements, 0.85, page_content[:2000]
                    )
                    logger.info(f"✅ Two-layer UI analysis completed and cached for task: {task_type}")
                    return nav_elements
                else:
                    logger.error(f"❌ Two-layer navigation analysis failed")
                    return {}
                
            finally:
                # Clean up temporary file
                if os.path.exists(screenshot_path):
                    os.unlink(screenshot_path)
                    logger.info("🧹 Cleaned up temporary screenshot")
            
        except Exception as e:
            logger.error(f"❌ UI analysis failed for task {task_type}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {}
    
    async def extract_page_content(self, page: Page, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content from page based on configuration"""
        try:
            content = {
                'title': await page.title(),
                'url': page.url,
                'timestamp': '',
                'content': '',
                'links': [],
                'images': []
            }
            
            # Extract main content
            if config.get('extract_text', True):
                content['content'] = await page.evaluate('''
                    () => {
                        const scripts = document.querySelectorAll('script, style');
                        scripts.forEach(el => el.remove());
                        return document.body.innerText || document.body.textContent || '';
                    }
                ''')
            
            # Extract links
            if config.get('extract_links', True):
                links = await page.evaluate('''
                    () => Array.from(document.querySelectorAll('a[href]')).map(el => ({
                        text: el.innerText.trim(),
                        href: el.href
                    }))
                ''')
                content['links'] = links
            
            # Extract images
            if config.get('extract_images', False):
                images = await page.evaluate('''
                    () => Array.from(document.querySelectorAll('img[src]')).map(el => ({
                        alt: el.alt,
                        src: el.src
                    }))
                ''')
                content['images'] = images
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to extract page content: {e}")
            return {}
    
    async def find_relevant_links(self, page: Page, config: Dict[str, Any]) -> List[str]:
        """Find relevant links for crawling based on configuration"""
        try:
            all_links = await page.evaluate('''
                () => Array.from(document.querySelectorAll('a[href]')).map(el => el.href)
            ''')
            
            # Filter links based on config
            relevant_links = []
            patterns = config.get('link_patterns', [])
            exclude_patterns = config.get('exclude_patterns', [])
            
            for link in all_links:
                # Basic filtering
                if link.startswith('mailto:') or link.startswith('tel:'):
                    continue
                
                # Pattern matching would go here
                # For now, return first 10 internal links
                if link.startswith(page.url.split('/')[0] + '//' + page.url.split('/')[2]):
                    relevant_links.append(link)
                    if len(relevant_links) >= 10:
                        break
            
            return relevant_links
            
        except Exception as e:
            logger.error(f"Failed to find relevant links: {e}")
            return []
    
    async def screenshot_exists(self, filepath: str) -> bool:
        """Check if screenshot file exists"""
        return Path(filepath).exists()
    
    async def compare_screenshots(self, previous_path: str, current_screenshot: bytes, config: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
        """Compare screenshots to detect changes"""
        try:
            # This would use actual image comparison
            # For now, return basic comparison
            previous_file = Path(previous_path)
            if not previous_file.exists():
                return True, {"message": "No previous screenshot to compare"}
            
            # Save current screenshot
            current_path = previous_path.replace('_previous', '_current')
            with open(current_path, 'wb') as f:
                f.write(current_screenshot)
            
            # Basic file size comparison (placeholder for actual image diff)
            previous_size = previous_file.stat().st_size
            current_size = len(current_screenshot)
            
            size_diff_percent = abs(current_size - previous_size) / previous_size * 100
            
            if size_diff_percent > config.get('change_threshold', 5):
                return True, {
                    "size_change_percent": size_diff_percent,
                    "previous_size": previous_size,
                    "current_size": current_size
                }
            
            return False, {"size_change_percent": size_diff_percent}
            
        except Exception as e:
            logger.error(f"Failed to compare screenshots: {e}")
            return False, {"error": str(e)}
    
    async def extract_monitoring_data(self, page: Page, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data for monitoring purposes"""
        try:
            monitoring_data = {
                'page_title': await page.title(),
                'url': page.url,
                'timestamp': '',
                'load_time': 0,
                'element_counts': {},
                'text_content': ''
            }
            
            # Extract element counts
            if config.get('monitor_elements', True):
                monitoring_data['element_counts'] = await page.evaluate('''
                    () => ({
                        total_elements: document.querySelectorAll('*').length,
                        links: document.querySelectorAll('a').length,
                        images: document.querySelectorAll('img').length,
                        forms: document.querySelectorAll('form').length,
                        buttons: document.querySelectorAll('button').length
                    })
                ''')
            
            # Extract specific text content for monitoring
            if config.get('monitor_text', False):
                selectors = config.get('text_selectors', ['body'])
                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            text = await element.inner_text()
                            monitoring_data['text_content'] += text + '\n'
                    except:
                        continue
            
            return monitoring_data
            
        except Exception as e:
            logger.error(f"Failed to extract monitoring data: {e}")
            return {}
    
    async def _convert_stacked_ai_to_elements(self, action_steps: List[Dict], ui_elements: Dict) -> Dict[str, Any]:
        """Convert stacked AI analysis results to element references with coordinates"""
        element_refs = {}
        
        logger.info("🎯 Converting stacked AI results to actionable element references")
        
        # Map action types to element keys
        action_map = {
            'type': ['username', 'email', 'user'],
            'fill': ['password', 'pass'],
            'click': ['submit', 'login', 'button']
        }
        
        for i, step in enumerate(action_steps):
            action = step.get("action", "").lower()
            coords = step.get("actual_coordinates", step.get("target_coordinates", [0, 0]))
            description = step.get("description", "")
            
            logger.info(f"📋 Step {i+1}: {action} at {coords} - {description}")
            
            # Determine element type based on action and description
            element_key = None
            if action in ['type', 'fill'] and any(word in description.lower() for word in ['username', 'email', 'user']):
                element_key = 'username'
            elif action in ['type', 'fill'] and any(word in description.lower() for word in ['password', 'pass']):
                element_key = 'password'
            elif action == 'click' and any(word in description.lower() for word in ['submit', 'login', 'button']):
                element_key = 'submit'
            
            if element_key and len(coords) >= 2:
                element_refs[element_key] = {
                    'type': 'coordinate',
                    'x': int(coords[0]),
                    'y': int(coords[1]),
                    'action': action,
                    'description': description,
                    'step_index': i
                }
                logger.info(f"📍 {element_key} field: ({coords[0]}, {coords[1]}) - {description}")
        
        # Also extract interactive elements for additional context
        interactive_elements = ui_elements.get("interactive_elements", [])
        logger.info(f"🔴 Found {len(interactive_elements)} interactive elements")
        
        # If we don't have enough elements from action plan, try interactive elements
        if len(element_refs) < 2 and interactive_elements:
            logger.info("⚠️ Attempting to extract elements from interactive_elements list")
            
            for elem in interactive_elements:
                elem_type = elem.get("type", "").lower()
                content = elem.get("content", "").lower()
                center = elem.get("center", [0, 0])
                
                if len(center) >= 2:
                    if elem_type == "input" and "username" not in element_refs:
                        if any(word in content for word in ['username', 'email', 'user']):
                            element_refs['username'] = {
                                'type': 'coordinate',
                                'x': int(center[0]),
                                'y': int(center[1]),
                                'action': 'type',
                                'description': f"Input field: {content}",
                                'source': 'interactive_elements'
                            }
                    elif elem_type == "input" and "password" not in element_refs:
                        if any(word in content for word in ['password', 'pass']):
                            element_refs['password'] = {
                                'type': 'coordinate',
                                'x': int(center[0]),
                                'y': int(center[1]),
                                'action': 'type',
                                'description': f"Input field: {content}",
                                'source': 'interactive_elements'
                            }
                    elif elem_type == "button" and "submit" not in element_refs:
                        if any(word in content for word in ['login', 'submit', 'sign in']):
                            element_refs['submit'] = {
                                'type': 'coordinate',
                                'x': int(center[0]),
                                'y': int(center[1]),
                                'action': 'click',
                                'description': f"Button: {content}",
                                'source': 'interactive_elements'
                            }
        
        # Validate that we found the essential elements
        if len(element_refs) < 2:
            logger.warning(f"⚠️ Insufficient elements found: {len(element_refs)} (need at least username + password or submit)")
            logger.error("❌ Stacked AI detection failed - insufficient elements detected")
            return {}
        
        logger.info(f"✅ Stacked AI conversion completed: {len(element_refs)} elements")
        for key, elem in element_refs.items():
            logger.info(f"   {key}: ({elem['x']}, {elem['y']}) - {elem['description']}")
        
        return element_refs
    
    async def _convert_search_ai_to_elements(self, action_steps: List[Dict], ui_elements: Dict) -> Dict[str, Any]:
        """Convert hybrid AI search analysis results to element references with coordinates"""
        element_refs = {}
        
        logger.info("🎯 Converting hybrid AI search results to actionable element references")
        
        for i, step in enumerate(action_steps):
            action = step.get("action", "").lower()
            coords = step.get("actual_coordinates", step.get("target_coordinates", [0, 0]))
            description = step.get("description", "")
            
            logger.info(f"📋 Step {i+1}: {action} at {coords} - {description}")
            
            # Determine element type based on action and description for search forms
            element_key = None
            if action in ['type', 'fill'] and any(word in description.lower() for word in ['search', 'query', 'find']):
                element_key = 'search_input'
            elif action == 'click' and any(word in description.lower() for word in ['search', 'submit', 'find', 'go']):
                element_key = 'search_button'
            
            if element_key and len(coords) >= 2:
                element_refs[element_key] = {
                    'type': 'coordinate',
                    'x': int(coords[0]),
                    'y': int(coords[1]),
                    'action': action,
                    'description': description,
                    'step_index': i
                }
                logger.info(f"📍 {element_key}: ({coords[0]}, {coords[1]}) - {description}")
        
        # Also extract interactive elements for additional context
        interactive_elements = ui_elements.get("interactive_elements", [])
        logger.info(f"🔴 Found {len(interactive_elements)} interactive elements")
        
        # If we don't have enough elements from action plan, try interactive elements
        if len(element_refs) < 1 and interactive_elements:
            logger.info("⚠️ Attempting to extract search elements from interactive_elements list")
            
            for elem in interactive_elements:
                elem_type = elem.get("type", "").lower()
                content = elem.get("content", "").lower()
                center = elem.get("center", [0, 0])
                
                if len(center) >= 2:
                    if elem_type == "input" and "search_input" not in element_refs:
                        if any(word in content for word in ['search', 'query', 'find']):
                            element_refs['search_input'] = {
                                'type': 'coordinate',
                                'x': int(center[0]),
                                'y': int(center[1]),
                                'action': 'type',
                                'description': f"Search input field: {content}",
                                'source': 'interactive_elements'
                            }
                    elif elem_type == "button" and "search_button" not in element_refs:
                        if any(word in content for word in ['search', 'submit', 'find', 'go']):
                            element_refs['search_button'] = {
                                'type': 'coordinate',
                                'x': int(center[0]),
                                'y': int(center[1]),
                                'action': 'click',
                                'description': f"Search button: {content}",
                                'source': 'interactive_elements'
                            }
        
        logger.info(f"✅ Hybrid AI search conversion completed: {len(element_refs)} elements")
        for key, elem in element_refs.items():
            logger.info(f"   {key}: ({elem['x']}, {elem['y']}) - {elem['description']}")
        
        return element_refs
    
    async def _convert_search_vision_to_selectors(self, page: Page, vision_data: Dict[str, Any]) -> Dict[str, str]:
        """Convert search vision analysis to actual CSS selectors"""
        selectors = {}
        
        # Search input selectors
        input_selectors = [
            'input[type="search"]',
            'input[name="search"]',
            'input[name="q"]',
            'input[placeholder*="search" i]',
            'input[aria-label*="search" i]'
        ]
        
        # Search button selectors
        button_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Search")',
            'button[aria-label*="search" i]'
        ]
        
        # Find working selectors
        for selector in input_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    selectors['input'] = selector
                    break
            except:
                continue
        
        for selector in button_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    selectors['submit'] = selector
                    break
            except:
                continue
        
        return selectors
    
    async def _vision_based_download_detection(self, page: Page) -> List[Dict[str, str]]:
        """Use two-layer AI analysis to detect download links: ISA Vision + OpenAI Vision"""
        try:
            # Take screenshot for analysis
            screenshot = await page.screenshot(full_page=False)
            
            # Save screenshot temporarily
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(screenshot)
                screenshot_path = tmp_file.name
            
            try:
                logger.info("🔧 Starting two-layer AI analysis for download detection...")
                
                # Use ISA Model client for vision analysis
                if self.client is None:
                    self.client = get_isa_client()
                    logger.info(f"✅ ISA Model client initialized")
                
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
                    return []
                
                ui_elements = isa_result.get("result", {}).get("ui_elements", [])
                logger.info(f"📋 ISA detected {len(ui_elements)} UI elements for download detection")
                
                # Step 2: Use OpenAI Vision for semantic understanding of download elements
                logger.info("🧠 Step 2: Getting semantic download element mapping with OpenAI Vision...")
                download_result = await self._openai_semantic_download_analysis(screenshot_path, ui_elements)
                
                if download_result:
                    logger.info(f"✅ Two-layer download analysis completed successfully")
                    return download_result
                else:
                    logger.error(f"❌ Semantic download analysis failed, falling back to ISA-only mapping")
                    # Fallback to basic ISA mapping
                    return await self._fallback_isa_download_mapping(ui_elements)
                
            finally:
                # Clean up temporary file
                if os.path.exists(screenshot_path):
                    os.unlink(screenshot_path)
            
        except Exception as e:
            logger.error(f"❌ Two-layer download detection failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
    
    async def _two_layer_navigation_analysis(self, screenshot_path: str) -> Dict[str, Any]:
        """Two-layer AI analysis for navigation elements: ISA Vision + OpenAI Vision"""
        try:
            logger.info("🔧 Initializing two-layer AI analysis for navigation elements...")
            
            # Use ISA Model client for vision analysis
            if self.client is None:
                self.client = get_isa_client()
                logger.info(f"✅ ISA Model client initialized")
            
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
            logger.info(f"📋 ISA detected {len(ui_elements)} UI elements for navigation")
            
            # Step 2: Use OpenAI Vision for semantic understanding of navigation elements
            logger.info("🧠 Step 2: Getting semantic navigation element mapping with OpenAI Vision...")
            semantic_result = await self._openai_semantic_navigation_analysis(screenshot_path, ui_elements)
            
            if semantic_result:
                logger.info(f"✅ Two-layer navigation analysis completed successfully")
                return {'ui_elements': semantic_result}
            else:
                logger.error(f"❌ Semantic navigation analysis failed, falling back to ISA-only mapping")
                # Fallback to basic ISA mapping
                fallback_result = await self._fallback_isa_navigation_mapping(ui_elements)
                return {'ui_elements': fallback_result} if fallback_result else {}
                
        except Exception as e:
            logger.error(f"❌ Two-layer navigation analysis failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {}
    
    async def _openai_semantic_navigation_analysis(self, screenshot_path: str, ui_elements: List[Dict]) -> Dict[str, Any]:
        """Use OpenAI Vision to semantically map UI elements to navigation elements"""
        try:
            logger.info("🧠 Starting OpenAI semantic analysis for navigation elements...")
            
            # Prepare element coordinate information
            element_info = []
            for i, elem in enumerate(ui_elements):
                center = elem.get('center', [0, 0])
                content = elem.get('content', '')
                elem_type = elem.get('type', '')
                element_info.append(f"Element {i}: {elem_type} at ({center[0]}, {center[1]}) with content '{content}'")
            
            elements_text = "\n".join(element_info)
            
            # Create semantic analysis prompt
            prompt = f"""Looking at this webpage, I need you to map the detected UI elements to navigation components.

Here are the detected UI elements with their coordinates:
{elements_text}

Please identify which elements correspond to:
- Navigation links (menu items, page links)
- Navigation buttons (clickable navigation elements)
- Logo or home link
- Navigation menu containers

IMPORTANT: Respond ONLY with this JSON format, no other text:
{{
    "navigation_links": [{{"element_index": X, "confidence": 0.9, "reasoning": "explanation"}}],
    "navigation_buttons": [{{"element_index": Y, "confidence": 0.9, "reasoning": "explanation"}}],
    "logo_link": {{"element_index": Z, "confidence": 0.9, "reasoning": "explanation"}},
    "menu_containers": [{{"element_index": W, "confidence": 0.9, "reasoning": "explanation"}}]
}}

Only include elements you are confident about (confidence > 0.7). Start your response with {{ and end with }}."""
            
            # Use OpenAI Vision service (new unified task design)
            openai_result = await self.client.invoke(
                screenshot_path,
                "analyze", 
                "vision",
                prompt=prompt
            )
            
            if not openai_result.get("success"):
                logger.warning(f"⚠️ OpenAI semantic navigation analysis failed: {openai_result}")
                return {}
            
            # Parse OpenAI response
            analysis_text = openai_result.get("result", {}).get("text", "")
            logger.info(f"🔍 OpenAI Navigation Response: {analysis_text[:200]}...")
            
            # Extract JSON from response
            import json
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if not json_match:
                logger.warning(f"⚠️ No JSON found in OpenAI navigation response. Full response: {analysis_text}")
                return {}
            
            try:
                semantic_mapping = json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse navigation JSON: {e}")
                return {}
            
            # Convert semantic mapping to element references
            element_refs = {
                'navigation_links': [],
                'navigation_buttons': [],
                'logo_link': None,
                'menu_containers': []
            }
            
            for category, mappings in semantic_mapping.items():
                if category in element_refs:
                    if isinstance(mappings, list):
                        for mapping in mappings:
                            if mapping.get("confidence", 0) > 0.7:
                                element_index = mapping.get("element_index")
                                if 0 <= element_index < len(ui_elements):
                                    element = ui_elements[element_index]
                                    center = element.get('center', [0, 0])
                                    
                                    element_data = {
                                        'type': 'coordinate',
                                        'x': int(center[0]),
                                        'y': int(center[1]),
                                        'action': 'click',
                                        'description': f"OpenAI semantic nav: {mapping.get('reasoning', '')}",
                                        'confidence': mapping.get('confidence', 0.8),
                                        'source': 'openai_semantic',
                                        'isa_element': element
                                    }
                                    element_refs[category].append(element_data)
                                    logger.info(f"🎯 Mapped {category}: ({center[0]}, {center[1]}) - {mapping.get('reasoning', '')}")
                    elif isinstance(mappings, dict) and mappings.get("confidence", 0) > 0.7:
                        element_index = mappings.get("element_index")
                        if 0 <= element_index < len(ui_elements):
                            element = ui_elements[element_index]
                            center = element.get('center', [0, 0])
                            
                            element_refs[category] = {
                                'type': 'coordinate',
                                'x': int(center[0]),
                                'y': int(center[1]),
                                'action': 'click',
                                'description': f"OpenAI semantic nav: {mappings.get('reasoning', '')}",
                                'confidence': mappings.get('confidence', 0.8),
                                'source': 'openai_semantic',
                                'isa_element': element
                            }
                            logger.info(f"🎯 Mapped {category}: ({center[0]}, {center[1]}) - {mappings.get('reasoning', '')}")
            
            return element_refs
            
        except Exception as e:
            logger.error(f"❌ OpenAI semantic navigation analysis failed: {e}")
            return {}
    
    async def _fallback_isa_navigation_mapping(self, ui_elements: List[Dict]) -> Dict[str, Any]:
        """Fallback ISA-only mapping when OpenAI semantic navigation analysis fails"""
        try:
            logger.info("🔄 Using fallback ISA-only mapping for navigation elements...")
            
            element_refs = {
                'navigation_links': [],
                'navigation_buttons': [],
                'logo_link': None,
                'menu_containers': []
            }
            
            for element in ui_elements:
                element_type_str = element.get('type', '').lower()
                content = element.get('content', '').lower()
                center = element.get('center', [0, 0])
                confidence = element.get('confidence', 0.8)
                interactable = element.get('interactable', False)
                
                if not interactable or len(center) < 2:
                    continue
                
                element_data = {
                    'type': 'coordinate',
                    'x': int(center[0]),
                    'y': int(center[1]),
                    'action': 'click',
                    'description': f"ISA fallback nav: {element_type_str} - {content}",
                    'confidence': confidence,
                    'source': 'isa_fallback',
                    'isa_element': element
                }
                
                # Categorize based on content and type
                if 'link' in element_type_str or 'a' in element_type_str:
                    if any(word in content for word in ['home', 'logo', 'brand']):
                        if element_refs['logo_link'] is None:
                            element_refs['logo_link'] = element_data
                            logger.info(f"🔄 Fallback mapped logo_link: ({center[0]}, {center[1]})")
                    else:
                        element_refs['navigation_links'].append(element_data)
                        logger.info(f"🔄 Fallback mapped navigation_link: ({center[0]}, {center[1]})")
                elif 'button' in element_type_str:
                    element_refs['navigation_buttons'].append(element_data)
                    logger.info(f"🔄 Fallback mapped navigation_button: ({center[0]}, {center[1]})")
                elif 'nav' in element_type_str or 'menu' in element_type_str:
                    element_refs['menu_containers'].append(element_data)
                    logger.info(f"🔄 Fallback mapped menu_container: ({center[0]}, {center[1]})")
            
            return element_refs
            
        except Exception as e:
            logger.error(f"❌ ISA fallback navigation mapping failed: {e}")
            return {}
    
    async def _openai_semantic_download_analysis(self, screenshot_path: str, ui_elements: List[Dict]) -> List[Dict[str, str]]:
        """Use OpenAI Vision to semantically identify download elements"""
        try:
            logger.info("🧠 Starting OpenAI semantic analysis for download elements...")
            
            # Prepare element coordinate information
            element_info = []
            for i, elem in enumerate(ui_elements):
                center = elem.get('center', [0, 0])
                content = elem.get('content', '')
                elem_type = elem.get('type', '')
                element_info.append(f"Element {i}: {elem_type} at ({center[0]}, {center[1]}) with content '{content}'")
            
            elements_text = "\n".join(element_info)
            
            # Create semantic analysis prompt
            prompt = f"""Looking at this webpage, I need you to identify download links and buttons.

Here are the detected UI elements with their coordinates:
{elements_text}

Please identify which elements are download-related (buttons or links for downloading files like PDF, DOC, ZIP, etc.).

IMPORTANT: Respond ONLY with this JSON format, no other text:
{{
    "download_elements": [
        {{"element_index": X, "confidence": 0.9, "file_type": "pdf", "reasoning": "explanation"}},
        {{"element_index": Y, "confidence": 0.9, "file_type": "unknown", "reasoning": "explanation"}}
    ]
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
                logger.warning(f"⚠️ OpenAI semantic download analysis failed: {openai_result}")
                return []
            
            # Parse OpenAI response
            analysis_text = openai_result.get("result", {}).get("text", "")
            logger.info(f"🔍 OpenAI Download Response: {analysis_text[:200]}...")
            
            # Extract JSON from response
            import json
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if not json_match:
                logger.warning(f"⚠️ No JSON found in OpenAI download response. Full response: {analysis_text}")
                return []
            
            try:
                semantic_mapping = json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse download JSON: {e}")
                return []
            
            # Convert semantic mapping to download links
            download_links = []
            download_elements = semantic_mapping.get('download_elements', [])
            
            for mapping in download_elements:
                if mapping.get("confidence", 0) > 0.7:
                    element_index = mapping.get("element_index")
                    if 0 <= element_index < len(ui_elements):
                        element = ui_elements[element_index]
                        center = element.get('center', [0, 0])
                        content = element.get('content', '')
                        
                        download_links.append({
                            'selector': f':has-text("{content}")',
                            'text': content,
                            'href': '',  # Would need to get from actual element
                            'detection_method': 'openai_semantic',
                            'file_type': mapping.get('file_type', 'unknown'),
                            'coordinates': center,
                            'confidence': mapping.get('confidence', 0.8),
                            'reasoning': mapping.get('reasoning', '')
                        })
                        logger.info(f"🎯 Mapped download element: ({center[0]}, {center[1]}) - {mapping.get('reasoning', '')}")
            
            return download_links
            
        except Exception as e:
            logger.error(f"❌ OpenAI semantic download analysis failed: {e}")
            return []
    
    async def _fallback_isa_download_mapping(self, ui_elements: List[Dict]) -> List[Dict[str, str]]:
        """Fallback ISA-only mapping for download elements"""
        try:
            logger.info("🔄 Using fallback ISA-only mapping for download elements...")
            
            download_links = []
            
            for element in ui_elements:
                element_type_str = element.get('type', '').lower()
                content = element.get('content', '').lower()
                center = element.get('center', [0, 0])
                confidence = element.get('confidence', 0.8)
                interactable = element.get('interactable', False)
                
                if not interactable or len(center) < 2:
                    continue
                
                # Look for download-related content
                if any(word in content for word in ['download', 'save', 'get', 'pdf', 'doc', 'zip', 'file']):
                    # Determine file type from content
                    file_type = 'unknown'
                    for ext in ['pdf', 'doc', 'docx', 'zip', 'exe', 'txt']:
                        if ext in content:
                            file_type = ext
                            break
                    
                    download_links.append({
                        'selector': f':has-text("{element.get("content", "")}")',
                        'text': element.get('content', ''),
                        'href': '',
                        'detection_method': 'isa_fallback',
                        'file_type': file_type,
                        'coordinates': center,
                        'confidence': confidence
                    })
                    logger.info(f"🔄 Fallback mapped download: ({center[0]}, {center[1]}) - {content}")
            
            return download_links
            
        except Exception as e:
            logger.error(f"❌ ISA fallback download mapping failed: {e}")
            return []
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get vision cache statistics"""
        return await self.cache_manager.get_cache_stats()
    
    async def close(self):
        """Close the vision analyzer and cleanup resources"""
        try:
            if self.client:
                await self.client.close()
                self.client = None
            logger.info("✅ VisionAnalyzer closed and resources cleaned up")
        except Exception as e:
            logger.error(f"❌ Error closing VisionAnalyzer: {e}")
    
    async def clear_vision_cache(self, detection_type: str = None) -> int:
        """Clear vision cache (optionally filtered by type)"""
        return await self.cache_manager.clear_cache(detection_type)
    
    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries"""
        return await self.cache_manager.cleanup_expired_cache()
    
    async def add_site_preconfig(self, domain: str, site_name: str,
                               login_elements: Dict[str, Any] = None,
                               search_elements: Dict[str, Any] = None,
                               special_selectors: Dict[str, Any] = None,
                               notes: str = ""):
        """Add new pre-configured site for faster detection"""
        await self.cache_manager.add_preconfig_site(
            domain, site_name, login_elements, search_elements, special_selectors, notes
        )
        logger.info(f"✅ Added pre-configuration for {site_name} ({domain})")
    
    async def understand_page_type(self, page: Page) -> Dict[str, Any]:
        """核心页面理解能力 - 分析页面类型和结构，决定后续操作策略"""
        try:
            url = page.url
            logger.info(f"🧠 Starting page understanding for: {url}")
            
            # Step 1: Check cache first (fastest)
            page_content = await page.content()
            cached_result = await self.cache_manager.get_cached_detection(
                url, 'page_understanding', page_content[:2000]
            )
            if cached_result:
                logger.info("💾 Using cached page understanding (fast)")
                return cached_result
            
            # Step 2: AI-powered page analysis (slow but accurate)
            logger.info("🤖 Analyzing page type with AI (slow)")
            
            # Take screenshot for analysis
            screenshot = await page.screenshot(full_page=False)
            
            # Save screenshot temporarily
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(screenshot)
                screenshot_path = tmp_file.name
            
            try:
                # Use OpenAI Vision for page understanding
                page_analysis = await self._analyze_page_with_openai(screenshot_path, url, page_content[:1000])
                
                if page_analysis and page_analysis.get('confidence', 0) > 0.7:
                    # Cache the successful result
                    await self.cache_manager.save_detection_result(
                        url, 'page_understanding', page_analysis, 
                        page_analysis.get('confidence', 0.8), page_content[:2000]
                    )
                    logger.info(f"✅ Page understanding completed: {page_analysis.get('page_type')} (confidence: {page_analysis.get('confidence'):.2f})")
                    return page_analysis
                else:
                    logger.warning("⚠️ AI page analysis failed, using fallback")
                    return await self._fallback_page_analysis(page)
                    
            finally:
                # Clean up temporary file
                if os.path.exists(screenshot_path):
                    os.unlink(screenshot_path)
            
        except Exception as e:
            logger.error(f"❌ Page understanding failed: {e}")
            # Return basic fallback
            return await self._fallback_page_analysis(page)
    
    async def _analyze_page_with_openai(self, screenshot_path: str, url: str, page_content_sample: str) -> Dict[str, Any]:
        """使用OpenAI Vision分析页面类型和结构"""
        try:
            # Initialize client if needed
            if self.client is None:
                self.client = get_isa_client()
            
            # Create analysis prompt
            prompt = f"""Analyze this webpage to understand its type and structure. Based on the screenshot and content, determine:

URL: {url}
Content sample: {page_content_sample[:500]}...

Please identify:
1. Primary page type (login, search_engine, content, ecommerce, social_media, navigation, form, error)
2. Current state (needs_login, ready_for_interaction, loading, content_loaded, form_ready)
3. Available actions (search, login, navigate, extract_content, fill_form, click_links)
4. Key elements visible (search_box, login_form, navigation_menu, content_area, product_listings)
5. Suggested next action based on typical user goals

IMPORTANT: Respond ONLY with this JSON format, no other text:
{{
    "page_type": "search_engine",
    "page_state": "ready_for_interaction", 
    "available_actions": ["search", "navigate"],
    "key_elements": ["search_box", "navigation_menu"],
    "suggested_action": "use_search_detection",
    "confidence": 0.95,
    "reasoning": "This appears to be a search engine homepage with visible search box"
}}

Start your response with {{ and end with }}."""

            # Call OpenAI Vision
            openai_result = await self.client.invoke(
                screenshot_path,
                "analyze",
                "vision", 
                prompt=prompt
            )
            
            if not openai_result.get("success"):
                logger.warning(f"⚠️ OpenAI page analysis failed: {openai_result}")
                return {}
            
            # Parse response
            analysis_text = openai_result.get("result", {}).get("text", "")
            logger.info(f"🔍 OpenAI Page Analysis: {analysis_text[:200]}...")
            
            # Extract JSON
            import json
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if not json_match:
                logger.warning(f"⚠️ No JSON found in page analysis response")
                return {}
            
            try:
                page_analysis = json.loads(json_match.group())
                
                # Validate required fields
                required_fields = ['page_type', 'page_state', 'available_actions', 'confidence']
                if all(field in page_analysis for field in required_fields):
                    return page_analysis
                else:
                    logger.warning(f"⚠️ Missing required fields in page analysis")
                    return {}
                    
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse page analysis JSON: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ OpenAI page analysis failed: {e}")
            return {}
    
    async def _fallback_page_analysis(self, page: Page) -> Dict[str, Any]:
        """基础页面分析fallback - 基于DOM和URL进行简单判断"""
        try:
            url = page.url.lower()
            title = await page.title()
            title_lower = title.lower()
            
            # Basic page type detection
            page_type = "content"  # default
            available_actions = ["extract_content"]
            key_elements = []
            suggested_action = "extract_content"
            
            # Login page detection
            if any(keyword in url for keyword in ['login', 'signin', 'auth']) or \
               any(keyword in title_lower for keyword in ['login', 'sign in', 'log in']):
                page_type = "login"
                available_actions = ["login"]
                key_elements = ["login_form"]
                suggested_action = "use_login_detection"
            
            # Search engine detection
            elif any(keyword in url for keyword in ['google.com', 'bing.com', 'search']) or \
                 any(keyword in title_lower for keyword in ['search', 'google', 'bing']):
                page_type = "search_engine"
                available_actions = ["search", "navigate"]
                key_elements = ["search_box"]
                suggested_action = "use_search_detection"
            
            # E-commerce detection
            elif any(keyword in url for keyword in ['amazon.com', 'ebay.com', 'shop', 'store']):
                page_type = "ecommerce"
                available_actions = ["search", "navigate", "extract_content"]
                key_elements = ["search_box", "product_listings"]
                suggested_action = "use_search_detection"
            
            # Social media detection
            elif any(keyword in url for keyword in ['twitter.com', 'facebook.com', 'reddit.com']):
                page_type = "social_media"
                available_actions = ["search", "navigate", "extract_content"]
                key_elements = ["search_box", "content_area"]
                suggested_action = "use_search_detection"
            
            return {
                "page_type": page_type,
                "page_state": "content_loaded",
                "available_actions": available_actions,
                "key_elements": key_elements,
                "suggested_action": suggested_action,
                "confidence": 0.6,  # Lower confidence for fallback
                "reasoning": f"Fallback analysis based on URL pattern and title",
                "source": "fallback_analysis"
            }
            
        except Exception as e:
            logger.error(f"❌ Fallback page analysis failed: {e}")
            return {
                "page_type": "unknown",
                "page_state": "unknown",
                "available_actions": ["extract_content"],
                "key_elements": [],
                "suggested_action": "extract_content",
                "confidence": 0.3,
                "reasoning": f"Analysis failed: {str(e)}",
                "source": "error_fallback"
            }

    async def close(self):
        """Clean up resources"""
        # Cache manager doesn't need explicit cleanup
        logger.info("🧹 VisionAnalyzer resources cleaned up")