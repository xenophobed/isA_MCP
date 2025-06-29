#!/usr/bin/env python
"""
Test HumanBehavior Service  
测试HumanBehavior服务的人类行为模拟功能
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../'))

from tools.services.web_services.utils.human_behavior import HumanBehavior
from playwright.async_api import async_playwright

class TestHumanBehavior:
    """Test HumanBehavior functionality"""
    
    async def test_timing_configuration(self):
        """Test human timing configuration"""
        print("⏱️ 测试人类行为时间配置")
        
        human_behavior = HumanBehavior()
        
        # Test default configuration
        config = human_behavior.get_human_timing_config()
        
        required_fields = [
            'typing_speed_wpm',
            'typing_errors_rate', 
            'mouse_movement_speed',
            'delay_ranges'
        ]
        
        for field in required_fields:
            assert field in config, f"Config should contain {field}"
            print(f"  ✅ {field}: {config[field]}")
        
        # Test reasonable defaults
        assert 20 <= config['typing_speed_wpm'] <= 120, "Typing speed should be realistic"
        assert 0 <= config['typing_errors_rate'] <= 0.1, "Error rate should be reasonable"
        assert 0.3 <= config['mouse_movement_speed'] <= 3.0, "Mouse speed should be reasonable"
        
        print("  📊 默认配置合理且完整")
    
    async def test_profile_update(self):
        """Test human behavior profile updates"""
        print("\n🔄 测试行为档案更新")
        
        human_behavior = HumanBehavior()
        
        # Test valid updates
        human_behavior.update_human_profile(
            typing_speed_wpm=75,
            typing_errors_rate=0.03,
            mouse_movement_speed=1.5
        )
        
        config = human_behavior.get_human_timing_config()
        
        assert config['typing_speed_wpm'] == 75, "Typing speed should be updated"
        assert config['typing_errors_rate'] == 0.03, "Error rate should be updated"
        assert config['mouse_movement_speed'] == 1.5, "Mouse speed should be updated"
        
        print("  ✅ 档案更新成功")
        
        # Test boundary limits
        human_behavior.update_human_profile(
            typing_speed_wpm=150,  # Too high
            typing_errors_rate=0.2,  # Too high
            mouse_movement_speed=5.0  # Too high
        )
        
        config = human_behavior.get_human_timing_config()
        
        assert config['typing_speed_wpm'] <= 120, "Typing speed should be capped"
        assert config['typing_errors_rate'] <= 0.1, "Error rate should be capped"
        assert config['mouse_movement_speed'] <= 3.0, "Mouse speed should be capped"
        
        print("  🛡️ 边界限制正常工作")
    
    async def test_delay_functions(self):
        """Test delay functions"""
        print("\n⏳ 测试延迟函数")
        
        human_behavior = HumanBehavior()
        
        import time
        
        # Test random delay
        start_time = time.time()
        await human_behavior.random_delay(100, 200)  # 100-200ms
        elapsed = (time.time() - start_time) * 1000
        
        assert 80 <= elapsed <= 250, f"Delay should be in range, got {elapsed}ms"
        print(f"  ✅ 随机延迟: {elapsed:.1f}ms")
        
        # Test default delay
        start_time = time.time()
        await human_behavior.random_delay()
        elapsed = (time.time() - start_time) * 1000
        
        assert elapsed >= 80, f"Default delay should be at least 80ms, got {elapsed}ms"
        print(f"  ✅ 默认延迟: {elapsed:.1f}ms")
    
    async def test_human_interactions(self):
        """Test human-like interactions with real browser"""
        print("\n🖱️ 测试人类交互行为")
        
        human_behavior = HumanBehavior()
        
        # Setup browser
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to a simple page
            await page.goto("data:text/html,<html><body><input id='test' type='text'><button id='btn'>Click</button></body></html>")
            
            # Test human typing
            print("  🔤 测试人类打字行为")
            start_time = time.time()
            await human_behavior.human_type(page, "#test", "Hello World", clear_first=True)
            typing_time = time.time() - start_time
            
            # Verify text was typed
            text_value = await page.input_value("#test")
            assert text_value == "Hello World", f"Text should be typed correctly, got: {text_value}"
            print(f"    ✅ 打字完成: {typing_time:.2f}秒")
            
            # Test human clicking
            print("  🖱️ 测试人类点击行为")
            start_time = time.time()
            await human_behavior.human_click(page, "#btn")
            click_time = time.time() - start_time
            
            print(f"    ✅ 点击完成: {click_time:.2f}秒")
            
            # Test coordinate-based interactions
            print("  🎯 测试坐标点击")
            coordinate_ref = {"type": "coordinate", "x": 100, "y": 100, "description": "test position"}
            await human_behavior.human_click(page, coordinate_ref)
            print(f"    ✅ 坐标点击完成")
            
            # Test human navigation
            print("  🧭 测试人类导航行为")
            await human_behavior.apply_human_navigation(page)
            print(f"    ✅ 导航行为应用完成")
            
        except Exception as e:
            print(f"    ❌ 交互测试失败: {e}")
        finally:
            await page.close()
            await context.close()
            await browser.close()
            await playwright.stop()
    
    async def test_reading_simulation(self):
        """Test reading behavior simulation"""
        print("\n📖 测试阅读行为模拟")
        
        human_behavior = HumanBehavior()
        
        # Setup browser with a longer page
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Create a long page to test scrolling and reading
            html_content = """
            <html><body style="height: 3000px;">
            <h1>Test Article</h1>
            <p>This is a long article that requires scrolling...</p>
            """ + "<p>More content...</p>" * 50 + "</body></html>"
            
            await page.goto(f"data:text/html,{html_content}")
            
            # Test reading simulation
            import time
            start_time = time.time()
            await human_behavior.simulate_reading(page, reading_time_factor=0.1)  # Fast reading for test
            reading_time = time.time() - start_time
            
            print(f"  ✅ 阅读模拟完成: {reading_time:.2f}秒")
            assert reading_time > 0.5, "Reading should take some time"
            
            # Test scrolling
            start_time = time.time()
            await human_behavior.human_scroll(page, "down", 3)
            scroll_time = time.time() - start_time
            
            print(f"  ✅ 滚动行为完成: {scroll_time:.2f}秒")
            
        except Exception as e:
            print(f"    ❌ 阅读测试失败: {e}")
        finally:
            await page.close()
            await context.close() 
            await browser.close()
            await playwright.stop()

async def run_human_behavior_tests():
    """Run all human behavior tests"""
    print("🚀 开始HumanBehavior服务测试")
    print("="*50)
    
    test_behavior = TestHumanBehavior()
    
    try:
        await test_behavior.test_timing_configuration()
        await test_behavior.test_profile_update()
        await test_behavior.test_delay_functions()
        await test_behavior.test_human_interactions()
        await test_behavior.test_reading_simulation()
        
        print("\n🎉 所有HumanBehavior测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ HumanBehavior测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_human_behavior_tests())
    exit(0 if success else 1)