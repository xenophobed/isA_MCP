#!/usr/bin/env python
"""
Selector Analyzer for Web Services
Traditional CSS/XPath-based element identification with smart fallback strategies
Inspired by Crawl4AI's selector-based extraction approach
"""
import re
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from playwright.async_api import Page

from core.logging import get_logger

logger = get_logger(__name__)

class SelectorType(Enum):
    """Types of selectors supported"""
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    PLACEHOLDER = "placeholder"

class SelectorAnalyzer:
    """Traditional selector-based element analyzer with smart patterns"""
    
    def __init__(self):
        # Common login form patterns (inspired by Crawl4AI's schema-based extraction)
        self.login_patterns = {
            'username': {
                'css_selectors': [
                    'input[type="text"][name*="user" i]',
                    'input[type="text"][id*="user" i]', 
                    'input[type="text"][placeholder*="user" i]',
                    'input[type="email"]',
                    'input[name="username"]',
                    'input[name="email"]',
                    'input[name="login"]',
                    'input[id="username"]',
                    'input[id="email"]',
                    'input[id="user"]',
                    '#username', '#email', '#user', '#login',
                    '[name="user_name"]', '[name="user-name"]',
                    '[class*="username"]', '[class*="email"]'
                ],
                'xpath_selectors': [
                    '//input[@type="text" and contains(@name, "user")]',
                    '//input[@type="email"]',
                    '//input[contains(@placeholder, "username") or contains(@placeholder, "email")]'
                ],
                'text_patterns': [
                    r'username|email|user|login',
                    r'账号|用户名|邮箱'
                ]
            },
            'password': {
                'css_selectors': [
                    'input[type="password"]',
                    'input[name="password"]',
                    'input[name="passwd"]',
                    'input[name="pass"]',
                    'input[name="pwd"]',
                    'input[id="password"]',
                    'input[id="passwd"]',
                    'input[id="pass"]',
                    '#password', '#passwd', '#pass', '#pwd',
                    '[class*="password"]'
                ],
                'xpath_selectors': [
                    '//input[@type="password"]',
                    '//input[contains(@name, "pass")]',
                    '//input[contains(@placeholder, "password")]'
                ],
                'text_patterns': [
                    r'password|passwd|pass|pwd',
                    r'密码'
                ]
            },
            'submit': {
                'css_selectors': [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign In")',
                    'button:has-text("Log In")',
                    'button:has-text("Submit")',
                    '[value*="login" i]',
                    '[value*="sign in" i]',
                    '[value*="submit" i]',
                    '.login-button', '.signin-button', '.submit-button',
                    'form button:last-child',
                    'form input[type="button"]:last-child'
                ],
                'xpath_selectors': [
                    '//button[@type="submit"]',
                    '//input[@type="submit"]',
                    '//button[contains(text(), "Login") or contains(text(), "Sign") or contains(text(), "Submit")]',
                    '//form//button[last()]'
                ],
                'text_patterns': [
                    r'login|sign.?in|submit|continue',
                    r'登录|登陆|提交|继续'
                ]
            }
        }

    async def identify_login_elements(self, page: Page) -> Dict[str, Any]:
        """Identify login form elements using traditional selectors"""
        logger.info("🔍 Starting traditional selector-based login form identification")
        
        results = {}
        
        for element_type, patterns in self.login_patterns.items():
            logger.info(f"   Searching for {element_type} element...")
            
            # Try CSS selectors first
            element = await self._find_by_css_selectors(page, patterns['css_selectors'])
            if element:
                results[element_type] = element
                logger.info(f"   ✅ Found {element_type} via CSS selector")
                continue
            
            # Try XPath selectors
            element = await self._find_by_xpath_selectors(page, patterns['xpath_selectors'])
            if element:
                results[element_type] = element
                logger.info(f"   ✅ Found {element_type} via XPath selector")
                continue
            
            # Try text-based search as fallback
            element = await self._find_by_text_patterns(page, patterns['text_patterns'], element_type)
            if element:
                results[element_type] = element
                logger.info(f"   ✅ Found {element_type} via text pattern")
            else:
                logger.warning(f"   ❌ Could not find {element_type} element")
        
        logger.info(f"🎯 Traditional selector analysis completed. Found {len(results)}/3 elements")
        return results

    async def _find_by_css_selectors(self, page: Page, selectors: List[str]) -> Optional[Dict[str, Any]]:
        """Find element using CSS selectors"""
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    # Get element information
                    bounding_box = await element.bounding_box()
                    if bounding_box:
                        return {
                            'type': 'css_selector',
                            'selector': selector,
                            'x': bounding_box['x'] + bounding_box['width'] / 2,
                            'y': bounding_box['y'] + bounding_box['height'] / 2,
                            'width': bounding_box['width'],
                            'height': bounding_box['height']
                        }
            except Exception as e:
                logger.debug(f"CSS selector '{selector}' failed: {e}")
                continue
        return None

    async def _find_by_xpath_selectors(self, page: Page, selectors: List[str]) -> Optional[Dict[str, Any]]:
        """Find element using XPath selectors"""
        for selector in selectors:
            try:
                element = page.locator(f'xpath={selector}').first
                if await element.count() > 0:
                    bounding_box = await element.bounding_box()
                    if bounding_box:
                        return {
                            'type': 'xpath_selector', 
                            'selector': selector,
                            'x': bounding_box['x'] + bounding_box['width'] / 2,
                            'y': bounding_box['y'] + bounding_box['height'] / 2,
                            'width': bounding_box['width'],
                            'height': bounding_box['height']
                        }
            except Exception as e:
                logger.debug(f"XPath selector '{selector}' failed: {e}")
                continue
        return None

    async def _find_by_text_patterns(self, page: Page, patterns: List[str], element_type: str) -> Optional[Dict[str, Any]]:
        """Find element using text pattern matching"""
        for pattern in patterns:
            try:
                # For submit buttons, search by text content
                if element_type == 'submit':
                    element = page.locator(f'button:has-text("{pattern}")', has_text=re.compile(pattern, re.IGNORECASE)).first
                    if await element.count() > 0:
                        bounding_box = await element.bounding_box()
                        if bounding_box:
                            return {
                                'type': 'text_pattern',
                                'pattern': pattern,
                                'x': bounding_box['x'] + bounding_box['width'] / 2,
                                'y': bounding_box['y'] + bounding_box['height'] / 2,
                                'width': bounding_box['width'],
                                'height': bounding_box['height']
                            }
                
                # For input fields, search by placeholder or label
                else:
                    # Try placeholder attribute
                    element = page.locator(f'input[placeholder*="{pattern}" i]').first
                    if await element.count() > 0:
                        bounding_box = await element.bounding_box()
                        if bounding_box:
                            return {
                                'type': 'text_pattern',
                                'pattern': pattern,
                                'x': bounding_box['x'] + bounding_box['width'] / 2,
                                'y': bounding_box['y'] + bounding_box['height'] / 2,
                                'width': bounding_box['width'],
                                'height': bounding_box['height']
                            }
                            
            except Exception as e:
                logger.debug(f"Text pattern '{pattern}' failed: {e}")
                continue
        return None

    async def find_elements_by_schema(self, page: Page, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Find elements using a structured schema (Crawl4AI style)"""
        logger.info("🔍 Starting schema-based element extraction")
        
        results = {}
        base_selector = schema.get('baseSelector', 'body')
        fields = schema.get('fields', [])
        
        try:
            # Find base container
            container = page.locator(base_selector).first
            if await container.count() == 0:
                logger.warning(f"Base selector '{base_selector}' not found")
                return results
            
            # Extract each field
            for field in fields:
                field_name = field.get('name')
                field_selector = field.get('selector')
                field_type = field.get('type', 'text')
                
                if not field_name or not field_selector:
                    continue
                
                try:
                    element = container.locator(field_selector).first
                    if await element.count() > 0:
                        if field_type == 'coordinate':
                            bounding_box = await element.bounding_box()
                            if bounding_box:
                                results[field_name] = {
                                    'type': 'coordinate',
                                    'x': bounding_box['x'] + bounding_box['width'] / 2,
                                    'y': bounding_box['y'] + bounding_box['height'] / 2,
                                    'selector': field_selector
                                }
                        else:
                            # Extract text or other attributes
                            value = await element.text_content() if field_type == 'text' else await element.get_attribute('value')
                            results[field_name] = {
                                'type': field_type,
                                'value': value,
                                'selector': field_selector
                            }
                            
                        logger.info(f"   ✅ Extracted field '{field_name}'")
                    else:
                        logger.warning(f"   ❌ Field '{field_name}' not found with selector '{field_selector}'")
                        
                except Exception as e:
                    logger.error(f"   ❌ Error extracting field '{field_name}': {e}")
                    
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
        
        logger.info(f"🎯 Schema extraction completed. Found {len(results)} fields")
        return results

    def get_login_schema(self) -> Dict[str, Any]:
        """Get predefined login form schema"""
        return {
            "name": "Login Form",
            "baseSelector": "form, .login-form, #login-form, [class*='login'], [class*='signin']",
            "fields": [
                {
                    "name": "username",
                    "selector": "input[type='text'], input[type='email'], input[name*='user'], input[name*='email']",
                    "type": "coordinate"
                },
                {
                    "name": "password", 
                    "selector": "input[type='password']",
                    "type": "coordinate"
                },
                {
                    "name": "submit",
                    "selector": "button[type='submit'], input[type='submit'], button:has-text('Login'), button:has-text('Sign')",
                    "type": "coordinate"
                }
            ]
        }