#!/usr/bin/env python3
"""
Test Step 2: image_analyzer Performance
"""

import asyncio
import time
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tools.services.intelligence_service.vision.image_analyzer import analyze as image_analyze

async def test_step2_image_analyzer():
    """Test Step 2: image_analyzer performance"""
    print("🧠 Testing Step 2: image_analyzer Performance")
    print("=" * 60)
    
    # First, get a screenshot from Step 1
    print("📸 Getting screenshot from Step 1...")
    from test_automation_step1 import test_step1_screenshot
    screenshot_path, step1_time = await test_step1_screenshot()
    
    if not screenshot_path:
        print("❌ Could not get screenshot from Step 1")
        return
    
    task = "find contact information"
    
    # Prepare the prompt (same as in service)
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
    
    try:
        print("🧠 Calling image_analyzer...")
        start_time = time.time()
        
        result = await image_analyze(
            image=screenshot_path,
            prompt=prompt,
            provider="openai"
        )
        
        analysis_time = time.time() - start_time
        print(f"✅ image_analyzer completed: {analysis_time:.2f} seconds")
        print(f"🎯 Analysis success: {result.success}")
        print(f"📝 Model used: {result.model_used}")
        print(f"⏱️ Processing time: {result.processing_time:.2f} seconds")
        
        # Parse response
        analysis_data = None
        if result.success:
            try:
                import re
                json_match = re.search(r'\\{[\\s\\S]*\\}', result.response)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                    print(f"📋 Page type: {analysis_data.get('page_type', 'unknown')}")
                    print(f"📋 Elements found: {len(analysis_data.get('required_elements', []))}")
                    print(f"📋 Confidence: {analysis_data.get('confidence', 'N/A')}")
                else:
                    print("⚠️ Could not parse JSON from response")
            except Exception as e:
                print(f"❌ JSON parsing failed: {e}")
        
        # Log results
        with open("automation_performance.log", "a") as f:
            f.write(f"STEP 2 PERFORMANCE:\n")
            f.write(f"image_analyzer time: {analysis_time:.2f}s\n")
            f.write(f"Processing time: {result.processing_time:.2f}s\n")
            f.write(f"Success: {result.success}\n")
            f.write(f"Model: {result.model_used}\n")
            f.write(f"Response length: {len(result.response) if result.response else 0}\n")
            if analysis_data:
                f.write(f"Page type: {analysis_data.get('page_type', 'unknown')}\\n")
                f.write(f"Elements found: {len(analysis_data.get('required_elements', []))}\\n")
            f.write(f"Response preview: {result.response[:200]}...\\n" if result.response else "No response\\n")
            f.write("-" * 40 + "\\n")
        
        return analysis_data, analysis_time
        
    except Exception as e:
        print(f"❌ Step 2 failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Log error
        with open("automation_performance.log", "a") as f:
            f.write(f"STEP 2 ERROR: {str(e)}\\n")
            f.write("-" * 40 + "\\n")
        
        return None, 0

if __name__ == "__main__":
    asyncio.run(test_step2_image_analyzer())