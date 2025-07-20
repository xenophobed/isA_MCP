#!/usr/bin/env python3
"""
Test Step 1: Playwright Screenshot Performance
"""

import asyncio
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tools.services.web_services.services.web_automation_service import WebAutomationService

async def test_step1_screenshot():
    """Test Step 1: Screenshot performance"""
    print("📸 Testing Step 1: Playwright Screenshot Performance")
    print("=" * 60)
    
    service = WebAutomationService()
    
    try:
        # Browser startup timing
        print("🚀 Starting browser...")
        start_browser = time.time()
        await service._start_browser()
        browser_time = time.time() - start_browser
        print(f"✅ Browser startup: {browser_time:.2f} seconds")
        
        # Page navigation timing
        print("🌐 Navigating to page...")
        start_nav = time.time()
        await service.page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        nav_time = time.time() - start_nav
        print(f"✅ Page navigation: {nav_time:.2f} seconds")
        
        # Page load waiting
        print("⏳ Waiting for page to render...")
        start_wait = time.time()
        await asyncio.sleep(3)
        try:
            await service.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            await asyncio.sleep(2)
        wait_time = time.time() - start_wait
        print(f"✅ Page load wait: {wait_time:.2f} seconds")
        
        # Screenshot timing
        print("📸 Taking screenshot...")
        start_screenshot = time.time()
        screenshot_path = await service._take_screenshot("test_step1")
        screenshot_time = time.time() - start_screenshot
        print(f"✅ Screenshot capture: {screenshot_time:.2f} seconds")
        print(f"📁 Screenshot saved: {screenshot_path}")
        
        # Total Step 1 time
        total_time = browser_time + nav_time + wait_time + screenshot_time
        print(f"\n📊 Step 1 Total Time: {total_time:.2f} seconds")
        
        # Log results
        with open("automation_performance.log", "a") as f:
            f.write(f"STEP 1 PERFORMANCE:\n")
            f.write(f"Browser startup: {browser_time:.2f}s\n")
            f.write(f"Page navigation: {nav_time:.2f}s\n")
            f.write(f"Page load wait: {wait_time:.2f}s\n")
            f.write(f"Screenshot: {screenshot_time:.2f}s\n")
            f.write(f"Total Step 1: {total_time:.2f}s\n")
            f.write(f"Screenshot path: {screenshot_path}\n")
            f.write("-" * 40 + "\n")
        
        return screenshot_path, total_time
        
    except Exception as e:
        print(f"❌ Step 1 failed: {e}")
        return None, 0
    
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(test_step1_screenshot())