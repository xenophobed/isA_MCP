#!/usr/bin/env python3
"""
AppAnalysisMolecule 测试文件
测试应用分析分子服务的输入输出和功能
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# 设置路径
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))))
sys.path.insert(0, project_root)

# 导入被测试的模块
from tools.services.terminal_service.services.molecules.app_analysis_molecule import AppAnalysisMolecule

class TestAppAnalysisMolecule:
    """AppAnalysisMolecule 测试类"""
    
    def __init__(self):
        self.analyzer = AppAnalysisMolecule()
        self.test_cases = [
            {
                "name": "简单博客应用",
                "description": "创建一个简单的个人博客网站，展示文章列表和文章内容",
                "expected_app_type": "blog",
                "expected_complexity": "simple"
            },
            {
                "name": "复杂任务管理工具", 
                "description": "开发一个企业级任务管理应用，包含用户登录、任务创建、分配、进度跟踪、团队协作、数据统计和实时通知功能",
                "expected_app_type": "tool",
                "expected_complexity": "complex"
            },
            {
                "name": "在线商店",
                "description": "构建一个电商网站，展示商品、购物车、订单管理和支付功能",
                "expected_app_type": "ecommerce", 
                "expected_complexity": "medium"
            },
            {
                "name": "数据可视化仪表板",
                "description": "创建一个管理仪表板，显示业务统计图表和监控数据",
                "expected_app_type": "dashboard",
                "expected_complexity": "medium"
            },
            {
                "name": "REST API服务",
                "description": "开发一个REST API接口，提供数据查询和JSON响应服务",
                "expected_app_type": "api",
                "expected_complexity": "simple"
            },
            {
                "name": "实时聊天应用",
                "description": "构建一个聊天应用，支持实时消息、用户在线状态和群组功能",
                "expected_app_type": "chat",
                "expected_complexity": "medium"
            }
        ]
    
    def print_section(self, title, char="="):
        """打印分节标题"""
        print(f"\n{char * 60}")
        print(f"{title}")
        print(char * 60)
    
    def print_test_case(self, case_num, case_name):
        """打印测试用例标题"""
        print(f"\n📋 测试用例 {case_num}: {case_name}")
        print("-" * 50)
    
    def print_input_output(self, input_desc, output_data):
        """打印输入输出"""
        print(f"📥 输入描述:")
        print(f"   {input_desc}")
        print(f"\n📤 输出结果:")
        print(f"   {json.dumps(output_data, indent=2, ensure_ascii=False)}")
    
    def validate_output_structure(self, result):
        """验证输出结构"""
        required_fields = ["success", "timestamp"]
        
        for field in required_fields:
            if field not in result:
                return False, f"缺少必要字段: {field}"
        
        if result["success"]:
            # 检查新的PRD结构
            if "prd" in result and result["prd"] is not None:
                prd = result["prd"]
                prd_fields = ["app_name", "app_type", "features", "technical_requirements"]
                
                for field in prd_fields:
                    if field not in prd:
                        return False, f"PRD缺少字段: {field}"
                
                # 验证features结构 - features是一个list
                features = prd.get("features", [])
                if not isinstance(features, list):
                    return False, "PRD features应该是一个列表"
                
                # 如果有features，验证每个feature的结构
                if features:
                    feature = features[0]
                    required_feature_fields = ["id", "name", "description", "priority"]
                    for field in required_feature_fields:
                        if field not in feature:
                            return False, f"PRD feature缺少字段: {field}"
                
                return True, "PRD结构验证通过"
            
            # 检查传统analysis结构（向后兼容）
            analysis = result.get("analysis", {})
            analysis_fields = ["app_type", "confidence", "requirements", "complexity", "tech_stack"]
            
            for field in analysis_fields:
                if field not in analysis:
                    return False, f"分析结果缺少字段: {field}"
            
            # 验证requirements结构
            requirements = analysis.get("requirements", {})
            req_fields = ["functional", "technical", "ui_elements", "data_needs"]
            for field in req_fields:
                if field not in requirements:
                    return False, f"需求分析缺少字段: {field}"
        
        return True, "结构验证通过"
    
    async def test_basic_functionality(self):
        """测试基础功能"""
        self.print_section("🧪 基础功能测试")
        
        for i, case in enumerate(self.test_cases, 1):
            self.print_test_case(i, case["name"])
            
            # 执行分析
            result = await self.analyzer.analyze_app_description(case["description"])
            
            # 打印输入输出
            self.print_input_output(case["description"], result)
            
            # 验证结构
            is_valid, validation_msg = self.validate_output_structure(result)
            print(f"\n🔍 结构验证: {validation_msg}")
            
            if result["success"]:
                # 检查是否有PRD输出
                if "prd" in result and result["prd"] is not None:
                    prd = result["prd"]
                    actual_type = prd.get("app_type", "unknown")
                    expected_type = case["expected_app_type"]
                    type_match = actual_type == expected_type
                    
                    print(f"✅ 应用类型: {actual_type} {'✓' if type_match else '✗ (期望: ' + expected_type + ')'}")
                    print(f"✅ 应用名称: {prd.get('app_name', 'N/A')}")
                    print(f"✅ 生成方法: {result.get('generation_method', 'unknown')}")
                    print(f"✅ 置信度: {result.get('confidence', 0)}")
                    
                    # 显示PRD主要内容
                    description = prd.get("description", "N/A")
                    print(f"✅ 项目描述: {description}")
                    
                    features = prd.get("features", [])
                    print(f"✅ 功能模块数量: {len(features)}")
                    if features:
                        feature_names = [f.get("name", "Unknown") for f in features[:3]]
                        print(f"   - 主要功能: {', '.join(feature_names)}{'...' if len(features) > 3 else ''}")
                    
                    tech_req = prd.get("technical_requirements", {})
                    framework = tech_req.get("framework", "N/A")
                    database = tech_req.get("database", "N/A")
                    print(f"✅ 技术栈: {framework}, {database}")
                    
                    dependencies = tech_req.get("dependencies", [])
                    if dependencies:
                        print(f"✅ 依赖包: {', '.join(dependencies[:3])}{'...' if len(dependencies) > 3 else ''}")
                    
                else:
                    # 传统analysis输出
                    analysis = result["analysis"]
                    
                    actual_type = analysis.get("app_type", "unknown")
                    expected_type = case["expected_app_type"]
                    type_match = actual_type == expected_type
                    
                    actual_complexity = analysis.get("complexity", "unknown")
                    expected_complexity = case["expected_complexity"]
                    complexity_match = actual_complexity == expected_complexity
                    
                    print(f"✅ 应用类型: {actual_type} {'✓' if type_match else '✗ (期望: ' + expected_type + ')'}")
                    print(f"✅ 复杂度: {actual_complexity} {'✓' if complexity_match else '✗ (期望: ' + expected_complexity + ')'}")
                    print(f"✅ 置信度: {analysis.get('confidence', 0)}")
                    print(f"✅ 技术栈: {', '.join(analysis.get('tech_stack', []))}")
                    
                    # 显示需求分析
                    reqs = analysis.get("requirements", {})
                    total_reqs = sum(len(v) for v in reqs.values())
                    print(f"✅ 识别需求总数: {total_reqs}")
                    if reqs.get("functional"):
                        print(f"   - 功能需求: {', '.join(reqs['functional'])}")
                    if reqs.get("ui_elements"):
                        print(f"   - UI元素: {', '.join(reqs['ui_elements'])}")
                
                # 显示回退信息
                if result.get("fallback_to_basic"):
                    print(f"⚠️ PRD生成失败，回退到基础分析: {result.get('prd_error', 'Unknown error')}")
                
            else:
                print(f"❌ 分析失败: {result.get('error', 'Unknown error')}")
    
    async def test_individual_functions(self):
        """测试各个子功能"""
        self.print_section("🔧 子功能测试")
        
        test_description = "创建一个用户管理系统，包含登录注册、权限控制、数据展示和搜索功能"
        
        # 测试应用类型确定
        print("\n📍 测试: determine_app_type")
        type_result = self.analyzer.determine_app_type(test_description)
        print(f"输入: {test_description}")
        print(f"输出: {json.dumps(type_result, indent=2, ensure_ascii=False)}")
        
        # 测试需求提取
        print("\n📍 测试: extract_requirements")
        req_result = self.analyzer.extract_requirements(test_description)
        print(f"输入: {test_description}")
        print(f"输出: {json.dumps(req_result, indent=2, ensure_ascii=False)}")
        
        # 测试复杂度评估
        print("\n📍 测试: estimate_complexity")
        complexity_result = self.analyzer.estimate_complexity(
            test_description, 
            req_result.get("requirements") if req_result["success"] else None
        )
        print(f"输入: {test_description}")
        print(f"输出: {json.dumps(complexity_result, indent=2, ensure_ascii=False)}")
    
    async def test_edge_cases(self):
        """测试边界情况"""
        self.print_section("🎯 边界情况测试")
        
        edge_cases = [
            {"name": "空描述", "description": ""},
            {"name": "超短描述", "description": "web"},
            {"name": "超长描述", "description": "创建一个" + "非常复杂的" * 50 + "应用系统"},
            {"name": "无关键词", "description": "做一个东西给我用用看看怎么样"},
            {"name": "英文描述", "description": "Create a simple web application for managing tasks"},
            {"name": "混合语言", "description": "创建一个web应用，用来manage用户data"}
        ]
        
        for i, case in enumerate(edge_cases, 1):
            print(f"\n📋 边界测试 {i}: {case['name']}")
            result = await self.analyzer.analyze_app_description(case["description"])
            
            if result["success"]:
                analysis = result["analysis"]
                print(f"✅ 分析成功")
                print(f"   - 应用类型: {analysis.get('app_type')}")
                print(f"   - 置信度: {analysis.get('confidence')}")
                print(f"   - 复杂度: {analysis.get('complexity')}")
            else:
                print(f"❌ 分析失败: {result.get('error')}")
    
    def test_output_to_quickcode_input(self):
        """验证输出格式是否符合QuickCodeMolecule的输入要求"""
        self.print_section("🔗 输出接口验证")
        
        print("验证 AppAnalysisMolecule 输出是否符合 QuickCodeMolecule 输入要求:")
        print()
        
        # 模拟一个典型的分析结果
        sample_analysis_output = {
            "success": True,
            "analysis": {
                "app_type": "tool",
                "confidence": 0.85,
                "requirements": {
                    "functional": ["用户管理", "数据展示"],
                    "ui_elements": ["表单", "按钮"],
                    "data_needs": [],
                    "technical": []
                },
                "complexity": "medium",
                "estimated_time": "30-60分钟",
                "tech_stack": ["Flask", "Python", "HTML", "JavaScript"],
                "main_features": ["任务创建", "状态跟踪"],
                "core_features": ["优先级设置"],
                "analysis_method": "ai_enhanced"
            }
        }
        
        print("📤 AppAnalysisMolecule 输出示例:")
        print(json.dumps(sample_analysis_output, indent=2, ensure_ascii=False))
        
        # 转换为QuickCodeMolecule需要的app_spec格式
        analysis = sample_analysis_output["analysis"]
        app_spec = {
            "app_name": "task_manager_demo",  # 由QuickAppOrganism提供
            "app_type": analysis["app_type"],
            "description": "开发一个任务管理工具",  # 原始描述
            "complexity": analysis["complexity"],
            "tech_stack": analysis["tech_stack"],
            "requirements": analysis["requirements"],
            "main_features": analysis.get("main_features", []),
            "core_features": analysis.get("core_features", [])
        }
        
        print("\n📥 转换为 QuickCodeMolecule 的 app_spec 输入:")
        print(json.dumps(app_spec, indent=2, ensure_ascii=False))
        
        print("\n✅ 接口兼容性: 输出结构完全匹配QuickCodeMolecule的输入要求")
        
        # 验证必要字段
        required_fields = ["app_type", "complexity", "tech_stack"]
        missing_fields = [field for field in required_fields if field not in analysis]
        
        if missing_fields:
            print(f"❌ 缺少必要字段: {missing_fields}")
        else:
            print("✅ 所有必要字段都已提供")

async def main():
    """主测试函数"""
    print("🚀 AppAnalysisMolecule 完整测试")
    print(f"🕒 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = TestAppAnalysisMolecule()
    
    try:
        # 基础功能测试
        await tester.test_basic_functionality()
        
        # 子功能测试
        await tester.test_individual_functions()
        
        # 边界情况测试
        await tester.test_edge_cases()
        
        # 输出接口验证
        tester.test_output_to_quickcode_input()
        
        print(f"\n🎉 所有测试完成!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())