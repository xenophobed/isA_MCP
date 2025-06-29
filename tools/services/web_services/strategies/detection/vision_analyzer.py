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
from isa_model.inference import AIFactory

logger = get_logger(__name__)

class VisionAnalyzer:
    """Vision-guided web automation using AI models with stacked architecture"""
    
    def __init__(self):
        self.screenshots_path = Path("screenshots")
        self.screenshots_path.mkdir(exist_ok=True)
        self.monitoring_path = Path("monitoring")
        self.monitoring_path.mkdir(exist_ok=True)
        self.ai_factory = AIFactory()
        self.ui_service = None
    
    async def identify_login_form(self, page: Page) -> Dict[str, Any]:
        """Identify login form elements using stacked AI model for precise coordinate detection"""
        try:
            logger.info("🎯 Starting stacked AI model login form identification")
            
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
                    logger.info(f"✅ Successfully identified login elements via stacked AI: {len(login_elements)} elements")
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
            logger.error(f"❌ Stacked AI login form identification failed: {e}")
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
        """Use stacked AI model for login form analysis similar to demo test"""
        try:
            logger.info("🔧 Initializing stacked AI UI analysis service...")
            
            # Create UI analysis service like in the demo
            if self.ui_service is None:
                self.ui_service = self.ai_factory.get_ui_analysis(task_type="login")
                logger.info(f"✅ UI analysis service created: {type(self.ui_service)}")
            
            # Invoke the stacked model analysis
            logger.info("🤖 Starting stacked AI analysis...")
            result = await self.ui_service.invoke({
                "image_path": screenshot_path
            })
            
            logger.info(f"📊 Stacked AI analysis completed")
            logger.info(f"🔍 Result structure: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            
            if not result.get("success"):
                logger.error(f"❌ Stacked AI analysis failed: {result}")
                return {}
            
            # Extract the analysis results similar to demo
            final_output = result.get("final_output", {})
            action_plan = final_output.get("action_plan", {})
            ui_elements = final_output.get("ui_elements", {})
            automation_ready = final_output.get("automation_ready", {})
            
            logger.info(f"🎯 Analysis results:")
            logger.info(f"   Page type: {automation_ready.get('page_type', 'unknown')}")
            logger.info(f"   Automation ready: {automation_ready.get('ready', False)}")
            logger.info(f"   Confidence: {automation_ready.get('confidence', 0):.2f}")
            
            # Extract action steps with coordinates
            steps = action_plan.get("action_plan", [])
            logger.info(f"🚀 Found {len(steps)} action steps")
            
            # Convert stacked AI results to element references
            element_refs = await self._convert_stacked_ai_to_elements(steps, ui_elements)
            
            if element_refs and len(element_refs) >= 2:
                logger.info(f"✅ Successfully converted to {len(element_refs)} element references")
                return element_refs
            else:
                logger.error(f"❌ Insufficient elements extracted from stacked AI: {len(element_refs)}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Stacked AI login analysis failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {}
    
    async def identify_search_form(self, page: Page) -> Dict[str, str]:
        """Identify search form elements"""
        try:
            # Take screenshot for analysis
            screenshot = await page.screenshot(full_page=False)
            
            # Use traditional selectors as fallback
            search_elements = await self._detect_search_elements_fallback(page)
            
            if not search_elements:
                # Vision-based detection would go here
                search_elements = await self._vision_based_search_detection(screenshot, page)
            
            return search_elements
            
        except Exception as e:
            logger.error(f"Failed to identify search form: {e}")
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
    
    async def _vision_based_search_detection(self, screenshot: bytes, page: Page) -> Dict[str, str]:
        """Vision-based search form detection using AIFactory vision service"""
        try:
            # Get vision service
            vision = AIFactory().get_vision()
            
            # Analyze screenshot for search form elements
            analysis_prompt = """
            Analyze this webpage screenshot and identify search form elements.
            Look for:
            1. Search input fields
            2. Search buttons or submit buttons
            3. Search-related UI elements
            
            Return your findings in this JSON format:
            {
                "search_form_found": true/false,
                "search_input": "description of search input field location",
                "search_button": "description of search button location",
                "confidence": 0.0-1.0
            }
            """
            
            # Save screenshot temporarily for vision analysis
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(screenshot)
                temp_path = tmp_file.name
            
            try:
                result = await vision.analyze_image(
                    image=temp_path,
                    prompt=analysis_prompt
                )
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            await vision.close()
            
            # Parse AI response to extract form selectors
            analysis_text = result.get('text', '')
            logger.info(f"Vision search analysis: {analysis_text[:200]}...")
            
            # Try to extract JSON from response
            try:
                import re
                json_match = re.search(r'\{[^{}]*\}', analysis_text)
                if json_match:
                    import json
                    vision_data = json.loads(json_match.group())
                    
                    if vision_data.get('search_form_found') and vision_data.get('confidence', 0) > 0.6:
                        # Convert vision descriptions to actual selectors
                        selectors = await self._convert_search_vision_to_selectors(page, vision_data)
                        return selectors
            except Exception as parse_error:
                logger.warning(f"Failed to parse search vision analysis: {parse_error}")
            
            return {}
            
        except Exception as e:
            logger.error(f"Vision-based search detection failed: {e}")
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
        """Use vision analysis to detect download links"""
        try:
            # Take screenshot for analysis
            screenshot = await page.screenshot(full_page=False)
            
            # Get vision service
            vision = AIFactory().get_vision()
            
            # Analyze screenshot for download elements
            analysis_prompt = """
            Analyze this webpage screenshot and identify download links or buttons.
            Look for:
            1. Download buttons or links
            2. File download icons
            3. Text like "Download", "Get", "Save", etc.
            4. PDF, DOC, ZIP, or other file format indicators
            
            Return your findings in this JSON format:
            {
                "downloads_found": true/false,
                "download_elements": [
                    {
                        "text": "visible text of download element",
                        "type": "button/link",
                        "file_type": "pdf/doc/zip/etc or unknown"
                    }
                ],
                "confidence": 0.0-1.0
            }
            """
            
            # Save screenshot temporarily for vision analysis
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(screenshot)
                temp_path = tmp_file.name
            
            try:
                result = await vision.analyze_image(
                    image=temp_path,
                    prompt=analysis_prompt
                )
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            await vision.close()
            
            # Parse AI response
            analysis_text = result.get('text', '')
            logger.info(f"Vision download analysis: {analysis_text[:200]}...")
            
            # Try to extract JSON and find corresponding elements
            try:
                import re
                json_match = re.search(r'\{[^{}]*\}', analysis_text)
                if json_match:
                    import json
                    vision_data = json.loads(json_match.group())
                    
                    if vision_data.get('downloads_found') and vision_data.get('confidence', 0) > 0.6:
                        download_links = []
                        
                        # Try to find elements based on vision descriptions
                        for element_data in vision_data.get('download_elements', []):
                            text = element_data.get('text', '')
                            if text:
                                # Try to find element with similar text
                                selector = f':has-text("{text}")'
                                try:
                                    elements = await page.query_selector_all(selector)
                                    for element in elements[:1]:  # Take first match
                                        href = await element.get_attribute('href')
                                        download_links.append({
                                            'selector': selector,
                                            'text': text,
                                            'href': href or '',
                                            'detection_method': 'vision',
                                            'file_type': element_data.get('file_type', 'unknown')
                                        })
                                except:
                                    continue
                        
                        return download_links
            except Exception as parse_error:
                logger.warning(f"Failed to parse vision download analysis: {parse_error}")
            
            return []
            
        except Exception as e:
            logger.error(f"Vision-based download detection failed: {e}")
            return []