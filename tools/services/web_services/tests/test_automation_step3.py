#!/usr/bin/env python3
"""
Test Step 3: ui_detector Performance
"""

import asyncio
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tools.services.intelligence_service.vision.ui_detector import detect_ui_with_coordinates

async def test_step3_ui_detector():
    """Test Step 3: ui_detector performance"""
    print("🎯 Testing Step 3: ui_detector Performance")
    print("=" * 60)
    
    # Get screenshot and analysis from previous steps
    print("📸 Getting screenshot and analysis from previous steps...")
    from test_automation_step2 import test_step2_image_analyzer
    analysis_data, step2_time = await test_step2_image_analyzer()
    
    # We need to get the screenshot path - let's get it from step 1 again
    from test_automation_step1 import test_step1_screenshot
    screenshot_path, _ = await test_step1_screenshot()
    
    if not screenshot_path:
        print("❌ Could not get screenshot")
        return
    
    # Prepare requirements (use analysis data or fallback)
    if analysis_data and analysis_data.get('required_elements'):
        requirements = analysis_data['required_elements']
        print(f"📋 Using {len(requirements)} elements from Step 2 analysis")
    else:
        print("⚠️ Using fallback requirements")
        requirements = [{
            "element_name": "target_element",
            "element_purpose": "element to interact with",
            "visual_description": "interactive element",
            "interaction_type": "click"
        }]
    
    try:
        print("🎯 Calling ui_detector...")
        start_time = time.time()
        
        ui_result = await detect_ui_with_coordinates(
            screenshot=screenshot_path,
            requirements=requirements
        )
        
        detection_time = time.time() - start_time
        print(f"✅ ui_detector completed: {detection_time:.2f} seconds")
        print(f"🎯 Detection success: {ui_result.success}")
        print(f"📍 Elements mapped: {len(ui_result.element_mappings) if ui_result.element_mappings else 0}")
        print(f"🔍 UI elements found: {len(ui_result.ui_elements) if ui_result.ui_elements else 0}")
        
        if ui_result.success:
            print("📍 Element mappings:")
            for name, mapping in ui_result.element_mappings.items():
                print(f"   - {name}: ({mapping.get('x', 'N/A')}, {mapping.get('y', 'N/A')}) -> {mapping.get('action', 'N/A')}")
        else:
            print(f"❌ UI detection error: {ui_result.error}")
        
        # Log results
        with open("automation_performance.log", "a") as f:
            f.write(f"STEP 3 PERFORMANCE:\\n")
            f.write(f"ui_detector time: {detection_time:.2f}s\\n")
            f.write(f"Success: {ui_result.success}\\n")
            f.write(f"Elements mapped: {len(ui_result.element_mappings) if ui_result.element_mappings else 0}\\n")
            f.write(f"UI elements found: {len(ui_result.ui_elements) if ui_result.ui_elements else 0}\\n")
            if ui_result.element_mappings:
                f.write(f"Mappings: {ui_result.element_mappings}\\n")
            if ui_result.error:
                f.write(f"Error: {ui_result.error}\\n")
            f.write("-" * 40 + "\\n")
        
        return ui_result, detection_time
        
    except Exception as e:
        print(f"❌ Step 3 failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Log error
        with open("automation_performance.log", "a") as f:
            f.write(f"STEP 3 ERROR: {str(e)}\\n")
            f.write("-" * 40 + "\\n")
        
        return None, 0

if __name__ == "__main__":
    asyncio.run(test_step3_ui_detector())