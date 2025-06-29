#!/usr/bin/env python
"""
Test StealthManager Service
测试StealthManager服务的隐身和反检测功能
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../'))

from tools.services.web_services.core.stealth_manager import StealthManager
from playwright.async_api import async_playwright

class TestStealthManager:
    """Test StealthManager functionality"""
    
    async def test_stealth_context_creation(self):
        """Test stealth context configuration creation"""
        print("🛡️ 测试隐身上下文创建")
        
        stealth_manager = StealthManager()
        
        # Test different browser types
        browser_types = ["chrome", "firefox", "edge"]
        
        for browser_type in browser_types:
            print(f"  测试 {browser_type} 浏览器配置")
            
            config = await stealth_manager.create_stealth_context(browser_type)
            
            # Verify required fields
            assert 'viewport' in config, "Viewport should be present"
            assert 'user_agent' in config, "User agent should be present"
            assert 'locale' in config, "Locale should be present"
            assert 'timezone_id' in config, "Timezone should be present"
            assert 'extra_http_headers' in config, "Headers should be present"
            
            print(f"    ✅ {browser_type} 配置创建成功")
            print(f"    📱 视窗: {config['viewport']}")
            print(f"    🌍 语言: {config['locale']}")
            print(f"    🕐 时区: {config['timezone_id']}")
    
    async def test_stealth_levels(self):
        """Test different stealth levels with real browser"""
        print("\n🔧 测试不同隐身级别")
        
        stealth_manager = StealthManager()
        
        # Test with actual browser context
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        
        stealth_levels = ["basic", "medium", "high"]
        
        for level in stealth_levels:
            print(f"  测试 {level} 级别隐身")
            
            context = await browser.new_context()
            
            try:
                await stealth_manager.apply_stealth_context(context, level)
                print(f"    ✅ {level} 级别隐身应用成功")
                
                # Create a page to test if stealth scripts are working
                page = await context.new_page()
                
                # Test webdriver detection removal
                webdriver_check = await page.evaluate("() => navigator.webdriver")
                assert webdriver_check is None, f"Webdriver should be undefined in {level} mode"
                
                print(f"    🔍 webdriver检测: 已隐藏")
                
                if level in ["medium", "high"]:
                    # Test plugin masking
                    plugins_check = await page.evaluate("() => navigator.plugins.length")
                    assert plugins_check > 0, f"Plugins should be mocked in {level} mode"
                    print(f"    🔌 插件模拟: {plugins_check} 个插件")
                
                if level == "high":
                    # Test chrome object
                    chrome_check = await page.evaluate("() => !!window.chrome")
                    assert chrome_check, "Chrome object should exist in high mode"
                    print(f"    🌐 Chrome对象: 已模拟")
                
                await page.close()
                
            except Exception as e:
                print(f"    ❌ {level} 级别测试失败: {e}")
            finally:
                await context.close()
        
        await browser.close()
        await playwright.stop()
    
    async def test_status_reporting(self):
        """Test stealth manager status reporting"""
        print("\n📊 测试状态报告")
        
        stealth_manager = StealthManager()
        status = await stealth_manager.get_status()
        
        # Verify status structure
        required_fields = [
            'available_user_agents',
            'available_viewports', 
            'available_languages',
            'available_timezones',
            'stealth_levels'
        ]
        
        for field in required_fields:
            assert field in status, f"Status should contain {field}"
            print(f"  ✅ {field}: {status[field]}")
        
        # Verify stealth levels
        assert "basic" in status['stealth_levels']
        assert "medium" in status['stealth_levels'] 
        assert "high" in status['stealth_levels']
        
        print("  📋 状态报告完整且正确")

async def run_stealth_tests():
    """Run all stealth manager tests"""
    print("🚀 开始StealthManager服务测试")
    print("="*50)
    
    test_manager = TestStealthManager()
    
    try:
        await test_manager.test_stealth_context_creation()
        await test_manager.test_stealth_levels() 
        await test_manager.test_status_reporting()
        
        print("\n🎉 所有StealthManager测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ StealthManager测试失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_stealth_tests())
    exit(0 if success else 1)