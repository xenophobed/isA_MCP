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

logger = get_logger(__name__)


class WebAutomationService:
    """5-Step Atomic Workflow Web Automation Service"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        logger.info("✅ WebAutomationService initialized with 5-step atomic workflow")
    
    async def execute_task(self, url: str, task: str) -> Dict[str, Any]:
        """
        Execute automation task using 5-step atomic workflow
        
        Args:
            url: Target URL
            task: Task description, e.g. "search airpods"
            
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

Generate a JSON list of actions in this format:
[
    {{
        "action": "click",
        "element": "element_name",
        "x": 400,
        "y": 200
    }},
    {{
        "action": "type",
        "element": "element_name", 
        "x": 400,
        "y": 200,
        "text": "text to type"
    }}
]

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
        """Step 5: Execute Playwright actions and analyze results"""
        try:
            print("⚡ Step 5: Executing actions and analyzing results...")
            
            # Execute each action
            execution_log = []
            for i, action in enumerate(actions):
                try:
                    print(f"  Action {i+1}: {action['action']} at ({action.get('x', 0)}, {action.get('y', 0)})")
                    
                    if action['action'] == 'click':
                        await self.page.mouse.click(action['x'], action['y'])
                        execution_log.append(f"Clicked at ({action['x']}, {action['y']})")
                        
                    elif action['action'] == 'type':
                        # Click first, then type
                        await self.page.mouse.click(action['x'], action['y'])
                        await asyncio.sleep(0.5)
                        await self.page.keyboard.type(action.get('text', ''))
                        execution_log.append(f"Typed '{action.get('text', '')}' at ({action['x']}, {action['y']})")
                        
                    elif action['action'] == 'press':
                        await self.page.keyboard.press(action.get('key', 'Enter'))
                        execution_log.append(f"Pressed {action.get('key', 'Enter')}")
                    
                    # Wait between actions
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Action {i+1} failed: {e}")
                    execution_log.append(f"Action {i+1} failed: {e}")
            
            # Wait for page changes
            await asyncio.sleep(3)
            
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
                "actions_executed": len(actions),
                "execution_log": execution_log,
                "final_screenshot": final_screenshot,
                "analysis": result_analysis.response if result_analysis.success else "Analysis failed",
                "task_completed": analysis_data.get("task_completed", False),
                "summary": f"Executed {len(actions)} actions - {'Success' if analysis_data.get('task_completed') else 'Unclear'}"
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