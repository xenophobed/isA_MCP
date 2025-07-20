#!/usr/bin/env python3
"""
Test Step 5: Execution + image_analyzer Performance
"""

import asyncio
import time
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tools.services.intelligence_service.vision.image_analyzer import analyze as image_analyze
from tools.services.web_services.services.web_automation_service import WebAutomationService

async def test_step5_execution():
    """Test Step 5: Execution + analysis performance"""
    print("⚡ Testing Step 5: Execution + Analysis Performance")
    print("=" * 60)
    
    # Get actions from Step 4
    print("🤖 Getting actions from Step 4...")
    from test_automation_step4 import test_step4_text_generator
    actions, step4_time = await test_step4_text_generator()
    
    if not actions:
        print("⚠️ No actions from Step 4, using fallback actions")
        actions = [
            {"action": "click", "x": 400, "y": 300},
            {"action": "type", "x": 400, "y": 300, "text": "contact"}
        ]
    
    task = "find contact information"
    service = WebAutomationService()
    
    try:
        # Setup browser and navigate
        print("🚀 Setting up browser...")
        await service._start_browser()
        await service.page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        
        # Execute actions
        print("⚡ Executing actions...")
        start_execution = time.time()
        
        execution_log = []
        for i, action in enumerate(actions):
            try:
                print(f"  Action {i+1}: {action.get('action', 'unknown')} at ({action.get('x', 0)}, {action.get('y', 0)})")
                
                if action.get('action') == 'click':
                    await service.page.mouse.click(action.get('x', 0), action.get('y', 0))
                    execution_log.append(f"Clicked at ({action.get('x', 0)}, {action.get('y', 0)})")
                    
                elif action.get('action') == 'type':
                    await service.page.mouse.click(action.get('x', 0), action.get('y', 0))
                    await asyncio.sleep(0.5)
                    await service.page.keyboard.type(action.get('text', ''))
                    execution_log.append(f"Typed '{action.get('text', '')}' at ({action.get('x', 0)}, {action.get('y', 0)})")
                    
                elif action.get('action') == 'press':
                    await service.page.keyboard.press(action.get('key', 'Enter'))
                    execution_log.append(f"Pressed {action.get('key', 'Enter')}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"  ❌ Action {i+1} failed: {e}")
                execution_log.append(f"Action {i+1} failed: {e}")
        
        # Wait for page changes
        await asyncio.sleep(3)
        execution_time = time.time() - start_execution
        print(f"✅ Action execution completed: {execution_time:.2f} seconds")
        
        # Take final screenshot
        print("📸 Taking final screenshot...")
        start_screenshot = time.time()
        final_screenshot = await service._take_screenshot("test_step5_final")
        screenshot_time = time.time() - start_screenshot
        print(f"✅ Final screenshot: {screenshot_time:.2f} seconds")
        
        # Analyze results with image_analyzer
        print("🧠 Analyzing results with image_analyzer...")
        start_analysis = time.time()
        
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
        
        analysis_time = time.time() - start_analysis
        print(f"✅ Result analysis: {analysis_time:.2f} seconds")
        print(f"🎯 Analysis success: {result_analysis.success}")
        
        # Parse analysis
        analysis_data = {"task_completed": False, "current_state": "Analysis failed"}
        if result_analysis.success:
            try:
                import re
                json_match = re.search(r'\\{[\\s\\S]*\\}', result_analysis.response)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                    print(f"📋 Task completed: {analysis_data.get('task_completed', False)}")
                    print(f"📋 Confidence: {analysis_data.get('confidence', 'N/A')}")
                    print(f"📋 Current state: {analysis_data.get('current_state', 'N/A')}")
            except Exception as e:
                print(f"❌ Analysis parsing failed: {e}")
        
        # Total Step 5 time
        total_time = execution_time + screenshot_time + analysis_time
        print(f"\\n📊 Step 5 Total Time: {total_time:.2f} seconds")
        
        # Log results
        with open("automation_performance.log", "a") as f:
            f.write(f"STEP 5 PERFORMANCE:\\n")
            f.write(f"Action execution: {execution_time:.2f}s\\n")
            f.write(f"Final screenshot: {screenshot_time:.2f}s\\n")
            f.write(f"Result analysis: {analysis_time:.2f}s\\n")
            f.write(f"Total Step 5: {total_time:.2f}s\\n")
            f.write(f"Actions executed: {len(actions)}\\n")
            f.write(f"Execution log: {execution_log}\\n")
            f.write(f"Analysis success: {result_analysis.success}\\n")
            f.write(f"Task completed: {analysis_data.get('task_completed', False)}\\n")
            f.write(f"Response preview: {result_analysis.response[:200]}...\\n" if result_analysis.response else "No response\\n")
            f.write("-" * 40 + "\\n")
        
        return analysis_data, total_time
        
    except Exception as e:
        print(f"❌ Step 5 failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Log error
        with open("automation_performance.log", "a") as f:
            f.write(f"STEP 5 ERROR: {str(e)}\\n")
            f.write("-" * 40 + "\\n")
        
        return None, 0
    
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(test_step5_execution())