#!/usr/bin/env python3
"""
真正的QuickApp系统测试
使用完整的AI分析 → 需求提取 → 动态代码生成 → 部署
"""

import sys
import os
import asyncio
import tempfile
import subprocess
import time
import requests
from datetime import datetime

# 设置路径
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

# 导入真正的QuickApp系统
from tools.services.terminal_service.services.organisms.quick_app_organism import QuickAppOrganism

class RealQuickAppTest:
    """真正的QuickApp系统测试"""
    
    def __init__(self):
        self.quickapp = QuickAppOrganism()
        self.result = None
        
    async def test_complete_system(self, description: str):
        """测试完整的QuickApp系统"""
        print("🚀 真正的QuickApp系统端到端测试")
        print("=" * 60)
        print(f"📝 用户需求: {description}")
        print()
        
        try:
            # 使用完整的QuickApp系统
            print("🤖 调用QuickApp Organism...")
            result = await self.quickapp.create_quick_app(description)
            
            self.result = result
            
            if result["success"]:
                print("🎉 QuickApp创建成功！")
                print("=" * 60)
                print(f"🌐 服务URL: {result['service_url']}")
                print(f"📱 应用名称: {result['app_name']}")
                print(f"⏱️  总耗时: {result.get('total_time_seconds', 0):.1f}秒")
                print(f"✅ 验证状态: {result.get('verification_passed', False)}")
                
                if 'quick_links' in result:
                    print("\n🔗 快捷链接:")
                    for name, url in result['quick_links'].items():
                        print(f"   {name}: {url}")
                
                # 显示工作流详情
                if 'workflow_details' in result:
                    print(f"\n📊 工作流统计:")
                    workflow = result['workflow_details']
                    print(f"   总阶段数: {workflow.get('total_stages', 0)}")
                    
                    print(f"\n🔍 各阶段执行情况:")
                    for i, (stage_name, stage_result) in enumerate(workflow.get('stage_results', []), 1):
                        status = "✅" if stage_result.get('success') else "❌"
                        print(f"   {i}. {status} {stage_name}")
                        
                        # 显示关键信息
                        if stage_name == "app_analysis" and stage_result.get('success'):
                            print(f"      - 应用类型: {stage_result.get('app_type', 'N/A')}")
                            print(f"      - 复杂度: {stage_result.get('complexity', 'N/A')}")
                            print(f"      - 技术栈: {stage_result.get('tech_stack', [])}")
                            
                        elif stage_name == "code_generation" and stage_result.get('success'):
                            print(f"      - 生成文件数: {stage_result.get('generated_files', 0)}")
                            print(f"      - 项目路径: {stage_result.get('project_path', 'N/A')}")
                            
                        elif stage_name == "deployment_preparation" and stage_result.get('success'):
                            print(f"      - 分配端口: {stage_result.get('allocated_port', 'N/A')}")
                            
                        elif stage_name == "service_deployment" and stage_result.get('success'):
                            print(f"      - 服务URL: {stage_result.get('service_url', 'N/A')}")
                
                # 测试生成的应用
                print(f"\n🧪 测试生成的应用...")
                await self.test_generated_app(result['service_url'])
                
                return result
                
            else:
                print(f"❌ QuickApp创建失败")
                print(f"   错误: {result.get('error', 'Unknown error')}")
                print(f"   失败阶段: {result.get('failed_stage', 'Unknown stage')}")
                print(f"   完成阶段数: {result.get('completed_stages', 0)}")
                return result
                
        except Exception as e:
            print(f"❌ 系统异常: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def test_generated_app(self, service_url: str):
        """测试生成的应用功能"""
        try:
            print(f"🔍 测试服务: {service_url}")
            
            # 测试主页
            try:
                response = requests.get(service_url, timeout=10)
                if response.status_code == 200:
                    print("   ✅ 主页访问正常")
                    content_length = len(response.text)
                    print(f"      页面大小: {content_length} 字符")
                    
                    # 检查是否包含动态内容
                    if "QuickApp" in response.text:
                        print("      ✅ 包含QuickApp标识")
                    if any(word in response.text for word in ["博客", "商城", "工具", "dashboard"]):
                        print("      ✅ 包含应用特定内容")
                else:
                    print(f"   ❌ 主页访问失败: {response.status_code}")
            except Exception as e:
                print(f"   ❌ 主页测试异常: {e}")
            
            # 测试健康检查
            try:
                health_response = requests.get(f"{service_url}/health", timeout=5)
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    print("   ✅ 健康检查正常")
                    print(f"      服务状态: {health_data.get('status', 'unknown')}")
                else:
                    print(f"   ❌ 健康检查失败: {health_response.status_code}")
            except Exception as e:
                print(f"   ❌ 健康检查异常: {e}")
            
            # 测试API信息
            try:
                api_response = requests.get(f"{service_url}/api/info", timeout=5)
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    print("   ✅ API信息正常")
                    print(f"      服务名称: {api_data.get('service_name', 'N/A')}")
                else:
                    print(f"   ⚠️  API信息: {api_response.status_code}")
            except Exception as e:
                print(f"   ⚠️  API信息测试: {e}")
                
        except Exception as e:
            print(f"❌ 应用测试异常: {e}")
    
    async def cleanup(self):
        """清理资源"""
        if self.result and self.result.get("success") and "app_name" in self.result:
            try:
                print(f"\n🧹 清理应用: {self.result['app_name']}")
                stop_result = await self.quickapp.stop_quick_app(self.result["app_name"])
                if stop_result["success"]:
                    print("   ✅ 应用已停止")
                else:
                    print(f"   ⚠️  停止失败: {stop_result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"   ❌ 清理异常: {e}")

async def test_different_apps():
    """测试不同类型的应用"""
    
    test_cases = [
        {
            "description": "创建一个个人博客网站，包含文章列表、文章详情、分类标签、搜索功能和评论系统",
            "name": "复杂博客系统"
        },
        {
            "description": "开发一个任务管理工具，支持任务创建、分配、进度跟踪和团队协作",
            "name": "任务管理工具"  
        },
        {
            "description": "构建一个简单的在线商店，展示商品、购物车和基本的订单管理",
            "name": "在线商店"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n" + "🧪" * 20 + f" 测试案例 {i} " + "🧪" * 20)
        print(f"📋 {test_case['name']}")
        
        test = RealQuickAppTest()
        try:
            result = await test.test_complete_system(test_case["description"])
            
            if result["success"]:
                print(f"\n⏰ 应用将运行30秒供测试...")
                await asyncio.sleep(30)
            else:
                print(f"\n❌ 测试案例 {i} 失败")
                
        except Exception as e:
            print(f"❌ 测试案例 {i} 异常: {e}")
            
        finally:
            await test.cleanup()
            
        print(f"\n" + "✅" * 20 + f" 案例 {i} 完成 " + "✅" * 20)

async def main():
    """主函数"""
    print("🚀 开始真正的QuickApp系统测试")
    print("🎯 目标: 验证AI分析 → 需求提取 → 动态代码生成 → 自动部署")
    
    try:
        await test_different_apps()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    finally:
        print("\n🏁 测试完成")

if __name__ == '__main__':
    asyncio.run(main())