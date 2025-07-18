#!/usr/bin/env python
"""
测试增强版视觉分析器的动态适应能力
"""
import asyncio
from core.logging import get_logger
from tools.services.web_services.core.web_service_manager import get_web_service_manager
from tools.services.web_services.strategies.detection.enhanced_vision_analyzer import EnhancedVisionAnalyzer

logger = get_logger(__name__)

class EnhancedVisionTester:
    def __init__(self):
        self.web_manager = None
        self.enhanced_analyzer = EnhancedVisionAnalyzer()
        
    async def test_reddit_dynamic_search(self):
        """测试Reddit的动态搜索检测"""
        print("🚀 测试增强版视觉分析器 - Reddit动态搜索")
        print("=" * 60)
        
        try:
            # 初始化
            self.web_manager = await get_web_service_manager()
            browser_manager = self.web_manager.get_browser_manager()
            await browser_manager.initialize()
            
            # 获取页面
            page = await browser_manager.get_page("stealth")
            await page.goto("https://www.reddit.com", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            print(f"✅ 页面加载完成: {page.url}")
            
            # 第一步：深度页面理解
            print("\n🧠 第一步：深度页面理解")
            print("-" * 30)
            
            deep_analysis = await self.enhanced_analyzer.understand_page_deeply(page)
            
            print(f"📋 页面分析结果:")
            print(f"   页面类型: {deep_analysis.get('page_type', 'unknown')}")
            print(f"   主要目的: {deep_analysis.get('primary_purpose', 'unknown')}")
            print(f"   UI模式: {deep_analysis.get('ui_patterns', {})}")
            print(f"   可用操作: {deep_analysis.get('available_actions', [])}")
            print(f"   交互流程: {deep_analysis.get('interaction_flow', [])}")
            
            if 'search_analysis' in deep_analysis:
                search_info = deep_analysis['search_analysis']
                print(f"   搜索分析:")
                print(f"     输入类型: {search_info.get('search_input_type', 'unknown')}")
                print(f"     触发方式: {search_info.get('search_trigger', 'unknown')}")
                print(f"     位置: {search_info.get('search_location', 'unknown')}")
                print(f"     功能: {search_info.get('search_features', [])}")
            
            print(f"   建议策略: {deep_analysis.get('detection_strategy', 'unknown')}")
            print(f"   建议操作: {deep_analysis.get('suggested_action', 'unknown')}")
            print(f"   置信度: {deep_analysis.get('confidence', 0):.2f}")
            print(f"   推理: {deep_analysis.get('reasoning', 'unknown')}")
            
            # 第二步：自适应搜索检测
            print("\n🔍 第二步：自适应搜索检测")
            print("-" * 30)
            
            search_elements = await self.enhanced_analyzer.adaptive_search_detection(page, deep_analysis)
            
            print(f"📋 搜索元素检测结果:")
            for elem_name, elem_data in search_elements.items():
                print(f"   {elem_name}:")
                print(f"     类型: {elem_data.get('type', 'unknown')}")
                print(f"     坐标: ({elem_data.get('x', 0)}, {elem_data.get('y', 0)})")
                print(f"     操作: {elem_data.get('action', 'unknown')}")
                print(f"     交互方式: {elem_data.get('interaction_method', 'unknown')}")
                print(f"     描述: {elem_data.get('description', 'unknown')}")
                print(f"     置信度: {elem_data.get('confidence', 0):.2f}")
                print(f"     来源: {elem_data.get('source', 'unknown')}")
            
            # 第三步：执行动态搜索
            print("\n🎯 第三步：执行动态搜索")
            print("-" * 30)
            
            if search_elements:
                success = await self._execute_dynamic_search(page, search_elements, deep_analysis)
                if success:
                    print("✅ 动态搜索执行成功！")
                    
                    # 保存结果截图
                    await page.screenshot(path="enhanced_search_results.png", full_page=True)
                    print("📸 搜索结果截图已保存: enhanced_search_results.png")
                else:
                    print("❌ 动态搜索执行失败")
            else:
                print("❌ 未找到搜索元素")
            
            print("\n" + "=" * 60)
            print("🏁 增强版视觉分析器测试完成")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            
        finally:
            # 清理资源
            try:
                await self.enhanced_analyzer.close()
                if self.web_manager:
                    await self.web_manager.cleanup()
                print("🧹 资源清理完成")
            except Exception as e:
                print(f"清理错误: {e}")
    
    async def _execute_dynamic_search(self, page, search_elements: dict, page_analysis: dict) -> bool:
        """根据页面分析结果执行动态搜索"""
        try:
            search_query = "airpod 4 anc"
            
            # 获取搜索策略
            search_trigger = page_analysis.get('search_analysis', {}).get('search_trigger', 'unknown')
            interaction_flow = page_analysis.get('interaction_flow', [])
            
            print(f"🎯 使用搜索策略: {search_trigger}")
            print(f"🎯 交互流程: {interaction_flow}")
            
            # 查找搜索输入框
            search_input = None
            for key in ['input', 'search_input']:
                if key in search_elements:
                    search_input = search_elements[key]
                    break
            
            if not search_input:
                print("❌ 未找到搜索输入框")
                return False
            
            print(f"🎯 找到搜索输入框: ({search_input.get('x')}, {search_input.get('y')})")
            
            # 执行搜索
            if search_trigger == 'enter_key':
                # 仅使用回车键的搜索
                print("⌨️ 使用回车键搜索模式")
                
                # 点击搜索框
                await page.mouse.click(search_input['x'], search_input['y'])
                await page.wait_for_timeout(1000)
                print(f"✅ 点击搜索框: ({search_input['x']}, {search_input['y']})")
                
                # 输入搜索内容
                await page.keyboard.type(search_query)
                await page.wait_for_timeout(1000)
                print(f"✅ 输入搜索内容: {search_query}")
                
                # 按回车键
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(5000)
                print("✅ 按下回车键")
                
            elif search_trigger == 'button_click':
                # 需要点击按钮的搜索
                print("🔘 使用按钮点击搜索模式")
                
                # 点击搜索框
                await page.mouse.click(search_input['x'], search_input['y'])
                await page.wait_for_timeout(1000)
                
                # 输入搜索内容
                await page.keyboard.type(search_query)
                await page.wait_for_timeout(1000)
                
                # 查找搜索按钮
                search_button = search_elements.get('submit') or search_elements.get('search_button')
                if search_button:
                    await page.mouse.click(search_button['x'], search_button['y'])
                    await page.wait_for_timeout(5000)
                    print("✅ 点击搜索按钮")
                else:
                    print("⚠️ 未找到搜索按钮，尝试回车键")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(5000)
            
            # 检查搜索结果
            current_url = page.url
            print(f"📋 搜索后URL: {current_url}")
            
            if 'search' in current_url.lower() or search_query.replace(' ', '') in current_url:
                print("✅ URL变化确认搜索成功")
                return True
            else:
                print("❌ URL未变化，搜索可能失败")
                return False
                
        except Exception as e:
            print(f"❌ 动态搜索执行失败: {e}")
            return False

async def main():
    """主函数"""
    tester = EnhancedVisionTester()
    await tester.test_reddit_dynamic_search()

if __name__ == "__main__":
    asyncio.run(main())