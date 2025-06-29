#!/usr/bin/env python
"""
快速运行所有Web服务测试
Quick Test Runner for All Web Services Tests
"""
import asyncio
import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

class WebTestRunner:
    """Web服务测试运行器"""
    
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()
    
    async def run_test_file(self, test_file, test_name):
        """运行单个测试文件"""
        print(f"\n🧪 运行测试: {test_name}")
        print("-" * 50)
        
        try:
            start_time = time.time()
            
            # Import and run the test
            if test_file == "tools/test_web_search.py":
                # 运行多个测试函数
                from tools.test_web_search import test_simple_search, test_with_filters, test_error_handling
                try:
                    await test_simple_search()
                    await test_with_filters()
                    await test_error_handling()
                    success = True
                except Exception:
                    success = False
            elif test_file == "tools/test_web_automation.py":
                from tools.test_web_automation import run_step2_tests
                success = await run_step2_tests()
            elif test_file == "tools/test_web_crawl_extract.py":
                from tools.test_web_crawl_extract import test_crawl_extract_tool
                try:
                    await test_crawl_extract_tool()
                    success = True
                except Exception:
                    success = False
            elif test_file == "tools/test_web_crawl_stealth.py":
                from tools.test_web_crawl_stealth import main as stealth_main
                try:
                    await stealth_main()
                    success = True
                except Exception:
                    success = False
            elif test_file == "tools/test_web_synthesis.py":
                from tools.test_web_synthesis import main as synthesis_main
                try:
                    await synthesis_main()
                    success = True
                except Exception:
                    success = False
            elif test_file == "services/test_stealth_manager.py":
                from services.test_stealth_manager import run_stealth_tests
                success = await run_stealth_tests()
            elif test_file == "services/test_human_behavior.py":
                from services.test_human_behavior import run_human_behavior_tests
                success = await run_human_behavior_tests()
            else:
                print(f"⚠️ 跳过测试文件: {test_file} (需要手动适配)")
                success = None
            
            duration = time.time() - start_time
            
            if success is True:
                print(f"✅ {test_name} 测试通过 ({duration:.1f}秒)")
                status = "PASS"
            elif success is False:
                print(f"❌ {test_name} 测试失败 ({duration:.1f}秒)")
                status = "FAIL"
            else:
                print(f"⚠️ {test_name} 测试跳过 ({duration:.1f}秒)")
                status = "SKIP"
            
            self.test_results.append({
                "name": test_name,
                "file": test_file,
                "status": status,
                "duration": duration
            })
            
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {test_name} 测试异常: {str(e)} ({duration:.1f}秒)")
            self.test_results.append({
                "name": test_name,
                "file": test_file,
                "status": "ERROR",
                "duration": duration,
                "error": str(e)
            })
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行所有Web服务测试")
        print("=" * 60)
        
        # 定义测试执行顺序（从简单到复杂）
        test_suite = [
            ("services/test_stealth_manager.py", "StealthManager服务测试"),
            ("services/test_human_behavior.py", "HumanBehavior服务测试"),
            ("tools/test_web_search.py", "Step 1: Web搜索测试"),
            ("tools/test_web_automation.py", "Step 2: Web自动化测试"),
            ("tools/test_web_crawl_extract.py", "Step 3: 爬取提取测试"),
            ("tools/test_web_crawl_stealth.py", "Step 3: 增强隐身测试"),
            ("tools/test_web_synthesis.py", "Step 4: 合成生成测试"),
        ]
        
        # 运行所有测试
        for test_file, test_name in test_suite:
            try:
                await self.run_test_file(test_file, test_name)
                # 测试间短暂延迟，避免API限制
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                print(f"\n⚠️ 用户中断测试运行")
                break
            except Exception as e:
                print(f"\n❌ 运行 {test_name} 时发生严重错误: {e}")
                continue
    
    def generate_summary(self):
        """生成测试总结"""
        total_time = time.time() - self.start_time
        
        print(f"\n📊 测试总结")
        print("=" * 60)
        
        # 统计结果
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        errors = sum(1 for r in self.test_results if r["status"] == "ERROR")
        skipped = sum(1 for r in self.test_results if r["status"] == "SKIP")
        
        print(f"总测试数: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"💥 错误: {errors}")
        print(f"⚠️ 跳过: {skipped}")
        
        if total > 0:
            success_rate = (passed / (total - skipped)) * 100 if (total - skipped) > 0 else 0
            print(f"🎯 成功率: {success_rate:.1f}%")
        
        print(f"⏱️ 总耗时: {total_time:.1f}秒")
        
        # 详细结果
        print(f"\n📋 详细结果:")
        for result in self.test_results:
            status_icon = {
                "PASS": "✅",
                "FAIL": "❌", 
                "ERROR": "💥",
                "SKIP": "⚠️"
            }.get(result["status"], "❓")
            
            print(f"{status_icon} {result['name']} ({result['duration']:.1f}s)")
            if "error" in result:
                print(f"   错误: {result['error']}")
        
        # 性能统计
        if self.test_results:
            avg_time = sum(r["duration"] for r in self.test_results) / len(self.test_results)
            print(f"\n⚡ 平均测试时间: {avg_time:.1f}秒")
        
        return success_rate >= 80 if total > 0 else False

async def main():
    """主函数"""
    print("🌟 Web服务架构完整测试套件")
    print("测试真实的API调用、浏览器操作和LLM处理")
    
    runner = WebTestRunner()
    
    try:
        await runner.run_all_tests()
        success = runner.generate_summary()
        
        if success:
            print(f"\n🎉 所有测试运行完成！整体测试通过")
            return 0
        else:
            print(f"\n⚠️ 部分测试失败，请检查上面的详细信息")
            return 1
            
    except Exception as e:
        print(f"\n💥 测试运行器发生严重错误: {e}")
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n⚠️ 测试被用户中断")
        sys.exit(130)