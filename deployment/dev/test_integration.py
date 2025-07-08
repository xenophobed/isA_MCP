#!/usr/bin/env python3
"""
集成测试脚本
测试 Auth0 和 Stripe 集成功能
"""

import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('deployment/dev/.env.user_service')

class IntegrationTester:
    def __init__(self):
        self.base_url = "http://localhost:8100/api/v1"
        self.test_token = None  # 需要从前端获取或生成测试 token
        
    def test_health_check(self):
        """测试健康检查端点"""
        print("🏥 测试健康检查...")
        try:
            response = requests.get(f"{self.base_url.replace('/api/v1', '')}/health")
            if response.status_code == 200:
                print("✅ 健康检查通过")
                print(f"   响应: {response.json()}")
                return True
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False
    
    def test_user_endpoints_without_auth(self):
        """测试无需认证的端点"""
        print("\n👤 测试用户端点（无认证）...")
        
        # 测试获取订阅计划
        try:
            response = requests.get(f"{self.base_url}/subscriptions/plans")
            if response.status_code == 200:
                print("✅ 获取订阅计划成功")
                plans = response.json()
                print(f"   可用计划: {list(plans.get('plans', {}).keys())}")
                return True
            else:
                print(f"❌ 获取订阅计划失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 获取订阅计划异常: {e}")
            return False
    
    def test_protected_endpoints(self):
        """测试需要认证的端点"""
        print("\n🔐 测试受保护端点...")
        
        headers = {"Authorization": "Bearer invalid-token"}
        
        # 测试获取用户信息
        try:
            response = requests.get(f"{self.base_url}/users/me", headers=headers)
            if response.status_code == 401:
                print("✅ 认证保护正常工作（返回 401）")
                return True
            else:
                print(f"❌ 认证保护异常: 期望 401，得到 {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 认证测试异常: {e}")
            return False
    
    def test_stripe_webhook_endpoint(self):
        """测试 Stripe Webhook 端点"""
        print("\n💳 测试 Stripe Webhook 端点...")
        
        # 模拟 Stripe webhook 数据
        mock_webhook_data = {
            "id": "evt_test_webhook",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_session",
                    "customer": "cus_test_customer",
                    "subscription": "sub_test_subscription",
                    "metadata": {
                        "auth0_user_id": "auth0|test_user",
                        "user_email": "test@example.com"
                    }
                }
            }
        }
        
        try:
            # 不使用真实签名，只测试端点可达性
            response = requests.post(
                f"{self.base_url}/webhooks/stripe",
                json=mock_webhook_data,
                headers={"stripe-signature": "test-signature"}
            )
            
            # 预期会返回 400（无效签名），这是正常的
            if response.status_code == 400:
                print("✅ Webhook 端点正常（拒绝无效签名）")
                return True
            else:
                print(f"❌ Webhook 端点异常: {response.status_code}")
                print(f"   响应: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Webhook 测试异常: {e}")
            return False
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "="*50)
        print("🧪 集成测试报告")
        print("="*50)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("无认证端点", self.test_user_endpoints_without_auth),
            ("认证保护", self.test_protected_endpoints),
            ("Webhook 端点", self.test_stripe_webhook_endpoint)
        ]
        
        results = {}
        for test_name, test_func in tests:
            results[test_name] = test_func()
        
        print(f"\n📊 测试结果:")
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅" if result else "❌"
            print(f"   {status} {test_name}")
        
        print(f"\n🎯 总体结果: {passed}/{total} 测试通过")
        
        if passed == total:
            print("🎉 所有测试通过！服务已准备就绪")
        else:
            print("⚠️  部分测试失败，请检查配置")
        
        return passed == total

def main():
    """主函数"""
    print("🚀 开始 User Service 集成测试...")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = IntegrationTester()
    success = tester.generate_test_report()
    
    if success:
        print("\n✅ 测试完成，服务正常运行")
        print("📝 下一步:")
        print("   1. 启动前端应用")
        print("   2. 测试 Auth0 登录流程")
        print("   3. 测试 Stripe 支付流程")
    else:
        print("\n❌ 测试失败，请检查服务配置")
        
    return success

if __name__ == "__main__":
    main()