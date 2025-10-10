#!/usr/bin/env python
"""
Web Automation Service - 5-Step Atomic Workflow
Input: url + task description
Output: new url + task results

5-Step Atomic Workflow:
1. Playwright Screenshot
2. image_analyzer (Screen Understanding) 
3. ui_detector (UI Detection + Coordinates)
4. text_generator (Action Reasoning)
5. Playwright Execution + image_analyzer (Result Analysis)
"""

import json
import tempfile
import os
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page

from core.logging import get_logger

# Import atomic functions
from tools.services.intelligence_service.vision.image_analyzer import analyze as image_analyze
from tools.services.intelligence_service.vision.ui_detector import detect_ui_with_coordinates
from tools.services.intelligence_service.language.text_generator import generate_playwright_actions

# Import enhanced action executor
from tools.services.web_services.core.action_executor import get_action_executor

logger = get_logger(__name__)


class WebAutomationService:
    """5-Step Atomic Workflow Web Automation Service"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.action_executor = get_action_executor()
        logger.info("✅ WebAutomationService initialized with enhanced action executor")
    
    async def execute_task(self, url: str, task: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Execute automation task using 5-step atomic workflow

        Args:
            url: Target URL
            task: Task description, e.g. "search airpods"
            user_id: User identifier for credential lookup

        Returns:
            Dict containing results
        """
        try:
            logger.info(f"🚀 Starting 5-step atomic workflow: {task} on {url}")

            # Initialize browser
            await self._start_browser()

            # Navigate to target page and wait for load
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("⏳ Page loaded, waiting for full render...")
            await asyncio.sleep(3)
            
            # Wait for page to be fully interactive
            try:
                await self.page.wait_for_load_state("networkidle", timeout=8000)
                print("✅ Page fully loaded and ready")
            except:
                print("⚠️ Page load timeout, but continuing...")
                await asyncio.sleep(2)
            
            # STEP 1: Playwright Screenshot
            print("📸 Step 1: Taking initial screenshot...")
            screenshot_path = await self._take_screenshot("step1_initial")
            print(f"✅ Step 1 Complete: {screenshot_path}")

            # HIL Detection: Check if human intervention is needed
            hil_check = await self._check_hil_required(screenshot_path, url, user_id)
            if hil_check.get("hil_required"):
                logger.info(f"🤚 HIL required: {hil_check.get('reason')}")
                return hil_check

            # STEP 2: Screen Understanding with image_analyzer
            print("🧠 Step 2: Screen understanding with image_analyzer...")
            page_analysis = await self._step2_screen_understanding(screenshot_path, task)
            print(f"✅ Step 2 Complete: Found {len(page_analysis.get('required_elements', []))} required elements")
            
            # STEP 3: UI Detection with ui_detector
            print("🎯 Step 3: UI detection with ui_detector...")
            ui_result = await self._step3_ui_detection(screenshot_path, page_analysis)
            print(f"✅ Step 3 Complete: Mapped {len(ui_result.element_mappings)} elements")
            
            # STEP 4: Action Reasoning with text_generator
            print("🤖 Step 4: Action reasoning with text_generator...")
            actions = await self._step4_action_reasoning(ui_result, task, page_analysis)
            print(f"✅ Step 4 Complete: Generated {len(actions)} actions")
            
            # STEP 5: Playwright Execution + Result Analysis
            print("⚡ Step 5: Playwright execution and result analysis...")
            execution_result = await self._step5_execution_and_analysis(actions, task)
            print(f"✅ Step 5 Complete: {execution_result['summary']}")
            
            return {
                "success": True,
                "initial_url": url,
                "final_url": self.page.url,
                "task": task,
                "workflow_results": {
                    "step1_screenshot": screenshot_path,
                    "step2_analysis": page_analysis,
                    "step3_ui_detection": len(ui_result.element_mappings),
                    "step4_actions": actions,
                    "step5_execution": execution_result
                },
                "result_description": execution_result['analysis']
            }
            
        except Exception as e:
            logger.error(f"❌ 5-step workflow failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "initial_url": url,
                "task": task
            }
        finally:
            await self._cleanup()
    
    async def _start_browser(self):
        """Start browser for automation"""
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = await context.new_page()
    
    async def _take_screenshot(self, name: str) -> str:
        """Take screenshot and save to temp file"""
        screenshot = await self.page.screenshot()
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(screenshot)
            return tmp.name
    
    async def _step2_screen_understanding(self, screenshot_path: str, task: str) -> Dict[str, Any]:
        """Step 2: Screen understanding using image_analyzer atomic function"""
        try:
            print("🧠 Step 2: Analyzing page content and task requirements...")
            
            # Use image_analyzer atomic function for screen understanding
            prompt = f"""Analyze this webpage screenshot to understand what UI elements are needed for this task: {task}

Provide a JSON response with:
1. Page analysis and suitability
2. Required UI elements for the task
3. Interaction strategy

Return JSON format:
{{
    "page_suitable": true/false,
    "page_type": "search_page/form/ecommerce/etc",
    "required_elements": [
        {{
            "element_name": "search_input",
            "element_purpose": "input field for search query",
            "visual_description": "white input field with placeholder",
            "interaction_type": "click_and_type"
        }}
    ],
    "interaction_strategy": "step-by-step plan",
    "confidence": 0.9
}}"""
            
            # Call image_analyzer atomic function
            result = await image_analyze(
                image=screenshot_path,
                prompt=prompt,
                provider="openai"
            )
            
            if result.success:
                # Parse JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', result.response)
                if json_match:
                    analysis = json.loads(json_match.group())
                    logger.info(f"📋 Page analysis: {analysis.get('page_type', 'unknown')}")
                    return analysis
            
            # Fallback: basic task analysis
            return self._basic_task_analysis(task)
            
        except Exception as e:
            logger.error(f"❌ Step 2 failed: {e}")
            return self._basic_task_analysis(task)
    
    async def _step3_ui_detection(self, screenshot_path: str, page_analysis: Dict[str, Any]):
        """Step 3: UI detection using ui_detector atomic function"""
        try:
            print("🎯 Step 3: Detecting UI elements and mapping coordinates...")
            
            # Extract requirements from Step 2 analysis
            requirements = page_analysis.get('required_elements', [])
            
            if not requirements:
                logger.warning("No requirements from Step 2, using task fallback")
                requirements = [{
                    "element_name": "target_element",
                    "element_purpose": "element to interact with",
                    "visual_description": "interactive element",
                    "interaction_type": "click"
                }]
            
            # Call ui_detector atomic function
            ui_result = await detect_ui_with_coordinates(
                screenshot=screenshot_path,
                requirements=requirements
            )
            
            if ui_result.success:
                logger.info(f"📍 UI detection found {len(ui_result.element_mappings)} element mappings")
                return ui_result
            else:
                logger.error(f"❌ UI detection failed: {ui_result.error}")
                return ui_result
                
        except Exception as e:
            logger.error(f"❌ Step 3 failed: {e}")
            # Return empty result
            from tools.services.intelligence_service.vision.ui_detector import UIDetectionResult
            return UIDetectionResult(
                ui_elements=[],
                annotated_image_path=None,
                element_mappings={},
                success=False,
                error=str(e)
            )
    
    async def _step4_action_reasoning(self, ui_result, task: str, page_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Step 4: Action reasoning using text_generator atomic function"""
        try:
            print("🤖 Step 4: Generating Playwright actions...")
            
            # Prepare context for action generation
            elements_info = ""
            for name, mapping in ui_result.element_mappings.items():
                elements_info += f"- {name}: ({mapping['x']}, {mapping['y']}) - action: {mapping['action']}\n"
            
            # Extract input text for typing actions
            input_text = self._extract_input_text(task)
            
            prompt = f"""Generate Playwright automation actions for this task: {task}

Available UI elements with coordinates:
{elements_info}

Input text to type: "{input_text}"

Available action types:
- click: Click element (supports coordinates, selector, text, xpath)
- type: Type text (supports clear_first, press_enter)
- select: Select dropdown option (by value, label, or index)
- checkbox: Check/uncheck/toggle checkbox
- scroll: Scroll page or element (direction, amount)
- hover: Hover over element
- wait: Wait for conditions (selector, text, url, timeout)
- navigate: Navigate browser (goto, back, forward, reload)
- press: Press keyboard key (Enter, Tab, Escape, etc.)

Generate a JSON list of actions. Examples:
[
    {{"action": "click", "x": 400, "y": 200}},
    {{"action": "type", "text": "search query", "x": 400, "y": 200, "clear_first": true}},
    {{"action": "select", "selector": "#country", "value": "US"}},
    {{"action": "checkbox", "label": "Agree to terms", "action": "check"}},
    {{"action": "scroll", "direction": "down", "amount": 500}},
    {{"action": "wait", "wait_for": "selector", "selector": ".results"}},
    {{"action": "press", "key": "Enter"}}
]

Generate appropriate actions for: {task}
Return only the JSON array."""
            
            # Call text_generator atomic function
            action_text = await generate_playwright_actions(
                prompt=prompt,
                temperature=0.3  # Lower temperature for consistent actions
            )
            
            # Parse actions from response
            import re
            json_match = re.search(r'\[[\s\S]*\]', action_text)
            if json_match:
                actions = json.loads(json_match.group())
                logger.info(f"🎭 Generated {len(actions)} Playwright actions")
                return actions
            
            # Fallback: create basic actions from ui_result
            return self._create_fallback_actions(ui_result, input_text)
            
        except Exception as e:
            logger.error(f"❌ Step 4 failed: {e}")
            return self._create_fallback_actions(ui_result, self._extract_input_text(task))
    
    async def _step5_execution_and_analysis(self, actions: List[Dict[str, Any]], task: str) -> Dict[str, Any]:
        """Step 5: Execute actions using enhanced ActionExecutor and analyze results"""
        try:
            print("⚡ Step 5: Executing enhanced actions and analyzing results...")
            
            # Execute actions using ActionExecutor
            execution_result = await self.action_executor.execute_action_sequence(
                page=self.page,
                actions=actions,
                delay_between_actions=1000,  # 1 second between actions
                stop_on_error=False  # Continue even if an action fails
            )
            
            # Build execution log from results
            execution_log = []
            for i, result in enumerate(execution_result['results']):
                if result.get('success'):
                    action_type = result.get('action_type', 'unknown')
                    method = result.get('method', '')
                    execution_log.append(f"Action {i+1} ({action_type}): Success via {method}")
                else:
                    execution_log.append(f"Action {i+1} failed: {result.get('error', 'Unknown error')}")
            
            print(f"  Executed {execution_result['executed']}/{execution_result['total_actions']} actions")
            print(f"  Success: {execution_result['successful']}, Failed: {execution_result['failed']}")
            
            # Wait for page changes after all actions
            await asyncio.sleep(2)
            
            # Take final screenshot and analyze results
            final_screenshot = await self._take_screenshot("step5_final")
            
            # Use image_analyzer to analyze results
            result_prompt = f"""Analyze this final screenshot to determine if the task was completed successfully.

Original task: {task}
Actions executed: {len(actions)} actions

Look for:
1. Did the task complete successfully?
2. Are there visible results/changes?
3. What is the current state of the page?

Return JSON:
{{
    "task_completed": true/false,
    "success_indicators": ["list of success signs"],
    "current_state": "description of page state",
    "confidence": 0.9
}}"""
            
            result_analysis = await image_analyze(
                image=final_screenshot,
                prompt=result_prompt,
                provider="openai"
            )
            
            # Parse analysis
            analysis_data = {"task_completed": False, "current_state": "Analysis failed"}
            if result_analysis.success:
                import re
                json_match = re.search(r'\{[\s\S]*\}', result_analysis.response)
                if json_match:
                    analysis_data = json.loads(json_match.group())
            
            return {
                "actions_executed": execution_result['executed'],
                "actions_successful": execution_result['successful'],
                "actions_failed": execution_result['failed'],
                "execution_log": execution_log,
                "execution_details": execution_result,
                "final_screenshot": final_screenshot,
                "analysis": result_analysis.response if result_analysis.success else "Analysis failed",
                "task_completed": analysis_data.get("task_completed", False),
                "summary": f"Executed {execution_result['executed']} actions ({execution_result['successful']} successful) - {'Task Complete' if analysis_data.get('task_completed') else 'Needs Review'}"
            }
            
        except Exception as e:
            logger.error(f"❌ Step 5 failed: {e}")
            return {
                "actions_executed": 0,
                "execution_log": [f"Execution failed: {e}"],
                "analysis": f"Execution failed: {e}",
                "task_completed": False,
                "summary": "Execution failed"
            }
    
    def _basic_task_analysis(self, task: str) -> Dict[str, Any]:
        """Fallback task analysis when image_analyzer fails"""
        task_lower = task.lower()
        
        if any(word in task_lower for word in ['search', 'find', 'look']):
            return {
                "page_suitable": True,
                "page_type": "search",
                "required_elements": [
                    {
                        "element_name": "search_input",
                        "element_purpose": "search input field",
                        "visual_description": "search input box",
                        "interaction_type": "click_and_type"
                    },
                    {
                        "element_name": "search_button",
                        "element_purpose": "search submit button",
                        "visual_description": "search button",
                        "interaction_type": "click"
                    }
                ],
                "interaction_strategy": "click input, type query, click search",
                "confidence": 0.7
            }
        
        return {
            "page_suitable": True,
            "page_type": "generic",
            "required_elements": [
                {
                    "element_name": "target_element",
                    "element_purpose": "element to interact with",
                    "visual_description": "interactive element",
                    "interaction_type": "click"
                }
            ],
            "interaction_strategy": "click element",
            "confidence": 0.5
        }
    
    def _create_fallback_actions(self, ui_result, input_text: str) -> List[Dict[str, Any]]:
        """Create fallback actions from UI detection results"""
        actions = []
        
        for element_name, mapping in ui_result.element_mappings.items():
            if mapping['action'] == 'type':
                actions.append({
                    "action": "click",
                    "element": element_name,
                    "x": mapping['x'],
                    "y": mapping['y']
                })
                actions.append({
                    "action": "type",
                    "element": element_name,
                    "x": mapping['x'],
                    "y": mapping['y'],
                    "text": input_text
                })
            else:
                actions.append({
                    "action": "click",
                    "element": element_name,
                    "x": mapping['x'],
                    "y": mapping['y']
                })
        
        return actions
    
    def _extract_input_text(self, task: str) -> str:
        """Extract text to input from task description"""
        import re

        # Look for quoted text
        match = re.search(r'["\'](.*?)["\']', task)
        if match:
            return match.group(1)

        # Look for text after action words
        patterns = [
            r'search\s+(?:for\s+)?(.+)',
            r'find\s+(.+)',
            r'look\s+for\s+(.+)',
            r'type\s+(.+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fallback: last word
        words = task.strip().split()
        return words[-1] if words else "search"

    async def _check_hil_required(self, screenshot_path: str, url: str, user_id: str) -> Dict[str, Any]:
        """
        Check if Human-in-Loop intervention is required

        Detects:
        1. Login pages → request_authorization or ask_human
        2. CAPTCHA → ask_human
        3. Payment confirmation → request_authorization
        4. Wallet connection → request_authorization or ask_human

        Returns HIL response if needed, otherwise returns {"hil_required": False}
        """
        try:
            # Use image_analyzer to detect page type
            detection_prompt = """Analyze this screenshot to detect if human intervention is needed.

Check for:
1. Login page (username/password fields, social login buttons)
2. CAPTCHA or verification challenge
3. Payment confirmation page (credit card, PayPal, etc.)
4. Wallet connection (MetaMask, Coinbase, etc.)
5. Cookie consent or age verification

Return JSON:
{
    "intervention_required": true/false,
    "intervention_type": "login|captcha|payment|wallet|verification|none",
    "provider": "google|facebook|metamask|stripe|etc",
    "details": "description of what's needed",
    "confidence": 0.9
}"""

            result = await image_analyze(
                image=screenshot_path,
                prompt=detection_prompt,
                provider="openai"
            )

            if not result.success:
                return {"hil_required": False}

            # Parse detection result
            import re
            json_match = re.search(r'\{[\s\S]*\}', result.response)
            if not json_match:
                return {"hil_required": False}

            detection = json.loads(json_match.group())

            if not detection.get("intervention_required"):
                return {"hil_required": False}

            intervention_type = detection.get("intervention_type", "unknown")
            provider = detection.get("provider", "unknown")
            details = detection.get("details", "Human intervention required")

            # Handle each intervention type with appropriate HIL action
            if intervention_type == "captcha":
                # CAPTCHA always requires ask_human (can't automate)
                return {
                    "hil_required": True,
                    "status": "human_required",
                    "action": "ask_human",
                    "message": f"CAPTCHA detected. Please solve the CAPTCHA manually.",
                    "data": {
                        "intervention_type": "captcha",
                        "url": url,
                        "screenshot": screenshot_path,
                        "details": details,
                        "instructions": "Please solve the CAPTCHA and notify when complete"
                    }
                }

            elif intervention_type == "login":
                # Login: check Vault for credentials
                return await self._handle_login_hil(provider, url, user_id, screenshot_path, details)

            elif intervention_type == "payment":
                # Payment: check Vault for payment method
                return await self._handle_payment_hil(provider, url, user_id, screenshot_path, details)

            elif intervention_type == "wallet":
                # Wallet: check Vault for wallet credentials
                return await self._handle_wallet_hil(provider, url, user_id, screenshot_path, details)

            elif intervention_type == "verification":
                # Age verification, cookie consent → ask_human
                return {
                    "hil_required": True,
                    "status": "human_required",
                    "action": "ask_human",
                    "message": f"Verification required: {details}",
                    "data": {
                        "intervention_type": "verification",
                        "url": url,
                        "screenshot": screenshot_path,
                        "details": details
                    }
                }

            return {"hil_required": False}

        except Exception as e:
            logger.error(f"HIL detection failed: {e}")
            return {"hil_required": False}

    async def _handle_login_hil(self, provider: str, url: str, user_id: str, screenshot: str, details: str) -> Dict[str, Any]:
        """Handle login page HIL - check Vault and return appropriate action"""
        # Check if credentials exist in Vault
        vault_has_creds = await self._check_vault_credentials(user_id, "social", provider)

        if vault_has_creds:
            # Vault has credentials → request_authorization
            return {
                "hil_required": True,
                "status": "authorization_required",
                "action": "request_authorization",
                "message": f"Found stored credentials for {provider}. Do you authorize using them for login?",
                "data": {
                    "auth_type": "social",
                    "provider": provider,
                    "url": url,
                    "credential_preview": {
                        "provider": provider,
                        "vault_id": vault_has_creds.get("vault_id"),
                        "stored_at": vault_has_creds.get("created_at")
                    },
                    "screenshot": screenshot,
                    "details": details
                }
            }
        else:
            # No credentials → ask_human
            oauth_url = self._get_oauth_url(provider, url)
            return {
                "hil_required": True,
                "status": "credential_required",
                "action": "ask_human",
                "message": f"No stored credentials found for {provider}. Please provide login credentials.",
                "data": {
                    "auth_type": "social",
                    "provider": provider,
                    "url": url,
                    "oauth_url": oauth_url,
                    "screenshot": screenshot,
                    "details": details,
                    "instructions": "Please click the OAuth button or enter credentials manually"
                }
            }

    async def _handle_payment_hil(self, provider: str, url: str, user_id: str, screenshot: str, details: str) -> Dict[str, Any]:
        """Handle payment page HIL"""
        vault_has_creds = await self._check_vault_credentials(user_id, "payment", provider)

        if vault_has_creds:
            return {
                "hil_required": True,
                "status": "authorization_required",
                "action": "request_authorization",
                "message": f"Payment authorization required for {provider}. Use stored payment method?",
                "data": {
                    "auth_type": "payment",
                    "provider": provider,
                    "url": url,
                    "credential_preview": {
                        "provider": provider,
                        "vault_id": vault_has_creds.get("vault_id"),
                        "last_used": vault_has_creds.get("created_at")
                    },
                    "screenshot": screenshot,
                    "details": details
                }
            }
        else:
            return {
                "hil_required": True,
                "status": "credential_required",
                "action": "ask_human",
                "message": f"No payment method found for {provider}. Please add payment details.",
                "data": {
                    "auth_type": "payment",
                    "provider": provider,
                    "url": url,
                    "screenshot": screenshot,
                    "details": details,
                    "instructions": "Please enter payment information or connect payment service"
                }
            }

    async def _handle_wallet_hil(self, provider: str, url: str, user_id: str, screenshot: str, details: str) -> Dict[str, Any]:
        """Handle wallet connection HIL"""
        vault_has_creds = await self._check_vault_credentials(user_id, "wallet", provider)

        if vault_has_creds:
            return {
                "hil_required": True,
                "status": "authorization_required",
                "action": "request_authorization",
                "message": f"Wallet connection required for {provider}. Use stored wallet?",
                "data": {
                    "auth_type": "wallet",
                    "provider": provider,
                    "url": url,
                    "credential_preview": {
                        "provider": provider,
                        "vault_id": vault_has_creds.get("vault_id"),
                        "wallet_type": provider
                    },
                    "screenshot": screenshot,
                    "details": details
                }
            }
        else:
            return {
                "hil_required": True,
                "status": "credential_required",
                "action": "ask_human",
                "message": f"No wallet found for {provider}. Please connect your wallet.",
                "data": {
                    "auth_type": "wallet",
                    "provider": provider,
                    "url": url,
                    "screenshot": screenshot,
                    "details": details,
                    "instructions": "Please connect your wallet via browser extension"
                }
            }

    async def _check_vault_credentials(self, user_id: str, auth_type: str, provider: str) -> Optional[Dict[str, Any]]:
        """Check if credentials exist in Vault Service"""
        try:
            import httpx
            vault_service_url = "http://localhost:8214"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{vault_service_url}/api/v1/vault/secrets",
                    headers={"X-User-Id": user_id},
                    params={"tags": f"{auth_type},{provider}"}
                )

                if response.status_code == 200:
                    vault_data = response.json()
                    secrets = vault_data.get("items", [])
                    if secrets:
                        return secrets[0]  # Return first matching credential

        except Exception as e:
            logger.warning(f"Vault check failed: {e}")

        return None

    def _get_oauth_url(self, provider: str, current_url: str) -> Optional[str]:
        """Generate OAuth URL for provider (simplified - would need real implementation)"""
        # This is a placeholder - real implementation would construct proper OAuth URLs
        oauth_patterns = {
            "google": "https://accounts.google.com/o/oauth2/v2/auth",
            "facebook": "https://www.facebook.com/v12.0/dialog/oauth",
            "github": "https://github.com/login/oauth/authorize",
            "twitter": "https://twitter.com/i/oauth2/authorize"
        }
        return oauth_patterns.get(provider.lower())

    async def _cleanup(self):
        """Cleanup browser resources"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.browser:
                await self.browser.close()
                self.browser = None
        except:
            pass
    
    async def close(self):
        """Close service"""
        await self._cleanup()
        logger.info("✅ WebAutomationService closed")