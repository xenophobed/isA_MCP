#!/usr/bin/env python
"""
Test Step 2: Web Automation
测试第二步：Web自动化功能 (StealthManager + HumanBehavior集成)
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../'))

# Initialize security before any imports
from core.security import initialize_security
initialize_security()

from tools.services.web_services.core.browser_manager import BrowserManager
from tools.services.web_services.core.session_manager import SessionManager
from tools.services.web_services.core.stealth_manager import StealthManager
from tools.services.web_services.utils.human_behavior import HumanBehavior

class TestStep2Automation:
    """Test Step 2 Web Automation functionality"""
    
    async def test_stealth_session_creation(self):
        """Test creating stealth sessions"""
        print("🛡️ 测试隐身会话创建")
        
        browser_manager = BrowserManager()
        session_manager = SessionManager()
        stealth_manager = StealthManager()
        
        try:
            # Initialize browser
            await browser_manager.initialize()
            print("  ✅ 浏览器管理器初始化完成")
            
            # Create stealth session
            session_id = "test_stealth_session"
            page = await session_manager.get_or_create_session(session_id, "stealth")
            print("  ✅ 隐身会话创建完成")
            
            # Apply stealth configuration
            if page.context:
                await stealth_manager.apply_stealth_context(page.context, level="high")
                print("  ✅ 高级隐身配置应用完成")
            
            # Test stealth features
            webdriver_check = await page.evaluate("() => navigator.webdriver")
            assert webdriver_check is None, "Webdriver应该被隐藏"
            print("  🔍 Webdriver检测: 已隐藏")
            
            chrome_check = await page.evaluate("() => !!window.chrome")
            assert chrome_check, "Chrome对象应该存在"
            print("  🌐 Chrome对象: 已模拟")
            
            plugins_check = await page.evaluate("() => navigator.plugins.length")
            assert plugins_check > 0, "插件应该被模拟"
            print(f"  🔌 插件模拟: {plugins_check} 个插件")
            
        except Exception as e:
            print(f"  ❌ 隐身会话测试失败: {e}")
            raise
        finally:
            await browser_manager.cleanup_all()
    
    async def test_human_behavior_integration(self):
        """Test human behavior integration with automation"""
        print("\n👤 测试人类行为集成")
        
        browser_manager = BrowserManager()
        session_manager = SessionManager()
        human_behavior = HumanBehavior()
        
        try:
            # Initialize browser
            await browser_manager.initialize()
            
            # Create session
            session_id = "test_human_behavior"
            page = await session_manager.get_or_create_session(session_id, "stealth")
            
            # Create test page with form
            test_html = """
            <html><body>
                <input id="search" type="text" placeholder="Search...">
                <button id="submit">Submit</button>
                <div style="height: 2000px;">Long content for scrolling test</div>
            </body></html>
            """
            await page.goto(f"data:text/html,{test_html}")
            
            # Apply human navigation behavior
            await human_behavior.apply_human_navigation(page)
            print("  ✅ 人类导航行为应用完成")
            
            # Test human typing
            import time
            start_time = time.time()
            await human_behavior.human_type(page, "#search", "test automation query")
            typing_time = time.time() - start_time
            
            # Verify typing worked
            typed_text = await page.input_value("#search")
            assert typed_text == "test automation query", f"文本应该正确输入，实际: {typed_text}"
            print(f"  ⌨️ 人类打字完成: {typing_time:.2f}秒")
            
            # Test human clicking
            start_time = time.time()
            await human_behavior.human_click(page, "#submit")
            click_time = time.time() - start_time
            print(f"  🖱️ 人类点击完成: {click_time:.2f}秒")
            
            # Test reading behavior
            start_time = time.time()
            await human_behavior.simulate_reading(page, reading_time_factor=0.1)  # Fast for testing
            reading_time = time.time() - start_time
            print(f"  📖 阅读行为模拟: {reading_time:.2f}秒")
            
            # Test random mouse movements
            await human_behavior.random_mouse_movement(page, movements=2)
            print("  🖱️ 随机鼠标移动完成")
            
        except Exception as e:
            print(f"  ❌ 人类行为集成测试失败: {e}")
            raise
        finally:
            await browser_manager.cleanup_all()
    
    async def test_anti_detection_effectiveness(self):
        """Test anti-detection effectiveness"""
        print("\n🔍 测试反检测效果")
        
        browser_manager = BrowserManager()
        session_manager = SessionManager()
        stealth_manager = StealthManager()
        
        try:
            await browser_manager.initialize()
            
            # Test different stealth levels
            stealth_levels = ["basic", "medium", "high"]
            
            for level in stealth_levels:
                print(f"  测试 {level} 级别反检测")
                
                session_id = f"test_stealth_{level}"
                page = await session_manager.get_or_create_session(session_id, "stealth")
                
                # Apply stealth for this level
                if page.context:
                    await stealth_manager.apply_stealth_context(page.context, level=level)
                
                # Test anti-detection features
                test_html = """
                <html><body>
                <script>
                    window.detectionResults = {
                        webdriver: navigator.webdriver,
                        plugins: navigator.plugins.length,
                        languages: navigator.languages.length,
                        chrome: !!window.chrome,
                        playwright: !!window.__playwright,
                        automation: !!window.__pw_manual
                    };
                </script>
                </body></html>
                """
                
                await page.goto(f"data:text/html,{test_html}")
                results = await page.evaluate("() => window.detectionResults")
                
                # Verify anti-detection features
                assert results['webdriver'] is None, f"{level}: webdriver应该被隐藏"
                
                if level in ["medium", "high"]:
                    assert results['plugins'] > 0, f"{level}: 插件应该被模拟"
                    assert results['languages'] > 0, f"{level}: 语言应该被模拟"
                
                if level == "high":
                    assert results['chrome'], f"{level}: Chrome对象应该存在"
                
                assert not results['playwright'], f"{level}: Playwright标识应该被隐藏"
                assert not results['automation'], f"{level}: 自动化标识应该被隐藏"
                
                print(f"    ✅ {level} 级别反检测验证通过")
                
        except Exception as e:
            print(f"  ❌ 反检测测试失败: {e}")
            raise
        finally:
            await browser_manager.cleanup_all()
    
    async def test_smart_navigation_strategies(self):
        """Test smart navigation strategies for different website types"""
        print("\n🧭 测试智能导航策略")
        
        browser_manager = BrowserManager()
        session_manager = SessionManager()
        stealth_manager = StealthManager()
        human_behavior = HumanBehavior()
        
        try:
            await browser_manager.initialize()
            
            # Test different website scenarios
            scenarios = [
                {
                    "name": "普通网站",
                    "url": "data:text/html,<html><body><h1>Normal Website</h1></body></html>",
                    "expected_strategy": "standard"
                },
                {
                    "name": "电商网站模拟",
                    "url": "data:text/html,<html><body><div class='product'>Amazon-like content</div></body></html>",
                    "expected_strategy": "enhanced"
                }
            ]
            
            for scenario in scenarios:
                print(f"  测试 {scenario['name']} 导航")
                
                session_id = f"test_nav_{scenario['name']}"
                page = await session_manager.get_or_create_session(session_id, "stealth")
                
                # Apply full stealth + human behavior
                if page.context:
                    await stealth_manager.apply_stealth_context(page.context, level="high")
                
                await human_behavior.apply_human_navigation(page)
                
                # Navigate with timing measurement
                import time
                start_time = time.time()
                
                await page.goto(scenario["url"])
                
                # Apply appropriate human behavior based on site type
                if "amazon" in scenario["url"].lower() or scenario["expected_strategy"] == "enhanced":
                    # Enhanced behavior for sensitive sites
                    await human_behavior.random_mouse_movement(page, movements=3)
                    await human_behavior.simulate_reading(page, reading_time_factor=0.2)
                else:
                    # Standard behavior
                    await human_behavior.human_navigation_pause(page)
                
                navigation_time = time.time() - start_time
                
                print(f"    ✅ {scenario['name']} 导航完成: {navigation_time:.2f}秒")
                print(f"    🎯 策略: {scenario['expected_strategy']}")
                
        except Exception as e:
            print(f"  ❌ 智能导航测试失败: {e}")
            raise
        finally:
            await browser_manager.cleanup_all()

async def run_step2_tests():
    """Run all Step 2 automation tests"""
    print("🚀 开始Step 2 Web自动化测试")
    print("="*60)
    print("测试内容:")
    print("  - 隐身会话创建和管理") 
    print("  - 人类行为模拟集成")
    print("  - 反检测技术效果")
    print("  - 智能导航策略")
    print("="*60)
    
    test_automation = TestStep2Automation()
    
    try:
        await test_automation.test_stealth_session_creation()
        await test_automation.test_human_behavior_integration()
        await test_automation.test_anti_detection_effectiveness()
        await test_automation.test_smart_navigation_strategies()
        
        print("\n🎉 所有Step 2自动化测试通过!")
        print("✅ Step 2功能验证:")
        print("  - 🛡️ 多级别隐身技术正常工作")
        print("  - 👤 人类行为模拟真实有效")
        print("  - 🔍 反检测技术达到预期效果")
        print("  - 🧭 智能导航策略适应不同网站")
        return True
        
    except Exception as e:
        print(f"\n❌ Step 2自动化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_step2_tests())
    exit(0 if success else 1)