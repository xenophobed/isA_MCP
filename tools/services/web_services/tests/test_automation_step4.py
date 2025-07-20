#!/usr/bin/env python3
"""
Test Step 4: text_generator Performance
"""

import asyncio
import time
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tools.services.intelligence_service.language.text_generator import generate_playwright_actions

async def test_step4_text_generator():
    """Test Step 4: text_generator performance"""
    print("🤖 Testing Step 4: text_generator Performance")
    print("=" * 60)
    
    # Get UI result from Step 3
    print("🎯 Getting UI detection results from Step 3...")
    from test_automation_step3 import test_step3_ui_detector
    ui_result, step3_time = await test_step3_ui_detector()
    
    if not ui_result:
        print("❌ Could not get UI detection results")
        return
    
    task = "find contact information"
    
    # Prepare elements info (same as in service)
    elements_info = ""
    if ui_result.element_mappings:
        for name, mapping in ui_result.element_mappings.items():
            elements_info += f"- {name}: ({mapping.get('x', 0)}, {mapping.get('y', 0)}) - action: {mapping.get('action', 'click')}\\n"
    else:
        elements_info = "- No elements detected\\n"
    
    # Extract input text (simplified version)
    input_text = "contact"  # Simplified for this test
    
    # Prepare prompt (same as in service)
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
    
    try:
        print("🤖 Calling text_generator...")
        start_time = time.time()
        
        action_text = await generate_playwright_actions(
            prompt=prompt,
            temperature=0.3
        )
        
        generation_time = time.time() - start_time
        print(f"✅ text_generator completed: {generation_time:.2f} seconds")
        print(f"📝 Response length: {len(action_text) if action_text else 0}")
        
        # Parse actions (same as in service)
        actions = []
        try:
            import re
            json_match = re.search(r'\\[[\\s\\S]*\\]', action_text)
            if json_match:
                actions = json.loads(json_match.group())
                print(f"🎭 Actions parsed: {len(actions)}")
                for i, action in enumerate(actions):
                    print(f"   {i+1}. {action.get('action', 'unknown')} at ({action.get('x', 'N/A')}, {action.get('y', 'N/A')})")
            else:
                print("⚠️ Could not parse JSON from response")
        except Exception as e:
            print(f"❌ Action parsing failed: {e}")
        
        # Log results
        with open("automation_performance.log", "a") as f:
            f.write(f"STEP 4 PERFORMANCE:\\n")
            f.write(f"text_generator time: {generation_time:.2f}s\\n")
            f.write(f"Response length: {len(action_text) if action_text else 0}\\n")
            f.write(f"Actions generated: {len(actions)}\\n")
            f.write(f"Elements info: {elements_info}")
            f.write(f"Prompt length: {len(prompt)}\\n")
            f.write(f"Response preview: {action_text[:200]}...\\n" if action_text else "No response\\n")
            if actions:
                f.write(f"Actions: {actions}\\n")
            f.write("-" * 40 + "\\n")
        
        return actions, generation_time
        
    except Exception as e:
        print(f"❌ Step 4 failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Log error
        with open("automation_performance.log", "a") as f:
            f.write(f"STEP 4 ERROR: {str(e)}\\n")
            f.write("-" * 40 + "\\n")
        
        return [], 0

if __name__ == "__main__":
    asyncio.run(test_step4_text_generator())