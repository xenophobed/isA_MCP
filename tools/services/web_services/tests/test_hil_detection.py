#!/usr/bin/env python3
"""
Test HIL (Human-in-Loop) Detection for Web Automation

Tests the two-action HIL model:
1. request_authorization - When Vault has credentials
2. ask_human - When Vault doesn't have credentials or CAPTCHA detected
"""

import asyncio
import json
from typing import Dict, Any


# Mock test scenarios
TEST_SCENARIOS = {
    "google_login_with_vault": {
        "description": "Google login page, Vault has credentials",
        "url": "https://accounts.google.com/signin",
        "task": "login to gmail",
        "user_id": "user123",
        "expected_action": "request_authorization",
        "expected_status": "authorization_required",
        "mock_detection": {
            "intervention_required": True,
            "intervention_type": "login",
            "provider": "google",
            "details": "Google OAuth login page detected",
            "confidence": 0.95
        },
        "mock_vault_has_creds": True
    },

    "google_login_no_vault": {
        "description": "Google login page, Vault has NO credentials",
        "url": "https://accounts.google.com/signin",
        "task": "login to gmail",
        "user_id": "user456",
        "expected_action": "ask_human",
        "expected_status": "credential_required",
        "mock_detection": {
            "intervention_required": True,
            "intervention_type": "login",
            "provider": "google",
            "details": "Google OAuth login page detected",
            "confidence": 0.95
        },
        "mock_vault_has_creds": False
    },

    "captcha_detection": {
        "description": "CAPTCHA detected (always ask_human)",
        "url": "https://www.google.com/search?q=test",
        "task": "search for test",
        "user_id": "user123",
        "expected_action": "ask_human",
        "expected_status": "human_required",
        "mock_detection": {
            "intervention_required": True,
            "intervention_type": "captcha",
            "provider": "recaptcha",
            "details": "reCAPTCHA v2 checkbox detected",
            "confidence": 0.98
        },
        "mock_vault_has_creds": None  # Vault not checked for CAPTCHA
    },

    "metamask_with_vault": {
        "description": "MetaMask connection, Vault has wallet",
        "url": "https://app.uniswap.org",
        "task": "connect wallet",
        "user_id": "user123",
        "expected_action": "request_authorization",
        "expected_status": "authorization_required",
        "mock_detection": {
            "intervention_required": True,
            "intervention_type": "wallet",
            "provider": "metamask",
            "details": "MetaMask connection popup detected",
            "confidence": 0.92
        },
        "mock_vault_has_creds": True
    },

    "metamask_no_vault": {
        "description": "MetaMask connection, Vault has NO wallet",
        "url": "https://app.uniswap.org",
        "task": "connect wallet",
        "user_id": "user789",
        "expected_action": "ask_human",
        "expected_status": "credential_required",
        "mock_detection": {
            "intervention_required": True,
            "intervention_type": "wallet",
            "provider": "metamask",
            "details": "MetaMask connection popup detected",
            "confidence": 0.92
        },
        "mock_vault_has_creds": False
    },

    "stripe_payment_with_vault": {
        "description": "Stripe payment page, Vault has payment method",
        "url": "https://checkout.stripe.com/pay/cs_test_xxx",
        "task": "complete payment",
        "user_id": "user123",
        "expected_action": "request_authorization",
        "expected_status": "authorization_required",
        "mock_detection": {
            "intervention_required": True,
            "intervention_type": "payment",
            "provider": "stripe",
            "details": "Stripe payment form detected",
            "confidence": 0.96
        },
        "mock_vault_has_creds": True
    },

    "no_intervention_needed": {
        "description": "Regular page, no HIL needed",
        "url": "https://www.wikipedia.org",
        "task": "search for python",
        "user_id": "user123",
        "expected_action": None,
        "expected_status": None,
        "mock_detection": {
            "intervention_required": False,
            "intervention_type": "none",
            "provider": None,
            "details": "Regular content page, no intervention needed",
            "confidence": 0.88
        },
        "mock_vault_has_creds": None
    }
}


def simulate_hil_detection(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate HIL detection based on test scenario

    This simulates what _check_hil_required() would return
    """
    detection = scenario["mock_detection"]

    if not detection["intervention_required"]:
        return {"hil_required": False}

    intervention_type = detection["intervention_type"]
    provider = detection["provider"]
    details = detection["details"]
    url = scenario["url"]

    # Simulate CAPTCHA (always ask_human)
    if intervention_type == "captcha":
        return {
            "hil_required": True,
            "status": "human_required",
            "action": "ask_human",
            "message": f"CAPTCHA detected. Please solve the CAPTCHA manually.",
            "data": {
                "intervention_type": "captcha",
                "url": url,
                "screenshot": "/tmp/mock_screenshot.png",
                "details": details,
                "instructions": "Please solve the CAPTCHA and notify when complete"
            }
        }

    # Simulate Login/Payment/Wallet
    vault_has_creds = scenario["mock_vault_has_creds"]

    if vault_has_creds:
        # Vault has credentials → request_authorization
        return {
            "hil_required": True,
            "status": "authorization_required",
            "action": "request_authorization",
            "message": f"Found stored credentials for {provider}. Do you authorize using them?",
            "data": {
                "auth_type": intervention_type,
                "provider": provider,
                "url": url,
                "credential_preview": {
                    "provider": provider,
                    "vault_id": f"vault_{provider}_123",
                    "stored_at": "2025-01-15T10:30:00Z"
                },
                "screenshot": "/tmp/mock_screenshot.png",
                "details": details
            }
        }
    else:
        # Vault has NO credentials → ask_human
        return {
            "hil_required": True,
            "status": "credential_required",
            "action": "ask_human",
            "message": f"No stored credentials found for {provider}. Please provide credentials.",
            "data": {
                "auth_type": intervention_type,
                "provider": provider,
                "url": url,
                "oauth_url": f"https://{provider}.com/oauth/authorize",
                "screenshot": "/tmp/mock_screenshot.png",
                "details": details,
                "instructions": "Please provide credentials or complete OAuth flow"
            }
        }


def test_scenario(scenario_name: str, scenario: Dict[str, Any]) -> bool:
    """Test a single HIL scenario"""
    print(f"\n{'='*80}")
    print(f"测试场景: {scenario_name}")
    print(f"描述: {scenario['description']}")
    print(f"{'='*80}")

    # Simulate HIL detection
    result = simulate_hil_detection(scenario)

    # Print result
    print(f"\n📤 HIL 响应:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Validate result
    if scenario["expected_action"] is None:
        # Expect no HIL
        if result.get("hil_required") == False:
            print(f"\n✅ 测试通过: 正确检测到无需 HIL")
            return True
        else:
            print(f"\n❌ 测试失败: 不应该触发 HIL")
            return False
    else:
        # Expect HIL
        actual_action = result.get("action")
        actual_status = result.get("status")

        if actual_action == scenario["expected_action"] and actual_status == scenario["expected_status"]:
            print(f"\n✅ 测试通过:")
            print(f"   - 动作: {actual_action} ✓")
            print(f"   - 状态: {actual_status} ✓")
            return True
        else:
            print(f"\n❌ 测试失败:")
            print(f"   - 期望动作: {scenario['expected_action']}")
            print(f"   - 实际动作: {actual_action}")
            print(f"   - 期望状态: {scenario['expected_status']}")
            print(f"   - 实际状态: {actual_status}")
            return False


def run_all_tests():
    """Run all HIL detection tests"""
    print("\n" + "="*80)
    print("🧪 HIL 检测测试套件")
    print("="*80)
    print("\n测试两种 HIL 动作:")
    print("1. request_authorization - Vault 有凭证时请求授权")
    print("2. ask_human - Vault 无凭证或遇到 CAPTCHA")

    results = {}

    for scenario_name, scenario in TEST_SCENARIOS.items():
        passed = test_scenario(scenario_name, scenario)
        results[scenario_name] = passed

    # Summary
    print(f"\n{'='*80}")
    print("📊 测试结果汇总")
    print(f"{'='*80}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"\n总测试数: {total}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"成功率: {passed/total*100:.1f}%")

    print(f"\n{'='*80}")
    print("详细结果:")
    print(f"{'='*80}")
    for scenario_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {scenario_name}")

    return passed == total


def demonstrate_agent_workflow():
    """Demonstrate how Agent should handle HIL responses"""
    print(f"\n{'='*80}")
    print("🤖 Agent HIL 处理示例")
    print(f"{'='*80}")

    # Example 1: request_authorization
    print(f"\n" + "-"*80)
    print("场景 1: request_authorization (Vault 有凭证)")
    print("-"*80)

    scenario = TEST_SCENARIOS["google_login_with_vault"]
    hil_response = simulate_hil_detection(scenario)

    print(f"\n1️⃣ Agent 收到 HIL 响应:")
    print(json.dumps({
        "action": hil_response["action"],
        "message": hil_response["message"],
        "credential_preview": hil_response["data"]["credential_preview"]
    }, indent=2, ensure_ascii=False))

    print(f"\n2️⃣ Agent 向用户确认:")
    print(f'   "我发现您的 Vault 中已经存储了 Google 账号凭证。')
    print(f'    需要我使用这个账号登录吗？"')

    print(f"\n3️⃣ 用户回复: \"是的，使用它\"")

    print(f"\n4️⃣ Agent 行动:")
    print(f"   - 从 Vault 获取完整凭证")
    print(f"   - 重新调用 web_automation（传入凭证）")
    print(f"   - 继续执行任务")

    # Example 2: ask_human
    print(f"\n" + "-"*80)
    print("场景 2: ask_human (Vault 无凭证)")
    print("-"*80)

    scenario = TEST_SCENARIOS["google_login_no_vault"]
    hil_response = simulate_hil_detection(scenario)

    print(f"\n1️⃣ Agent 收到 HIL 响应:")
    print(json.dumps({
        "action": hil_response["action"],
        "message": hil_response["message"],
        "oauth_url": hil_response["data"]["oauth_url"]
    }, indent=2, ensure_ascii=False))

    print(f"\n2️⃣ Agent 向用户说明:")
    print(f'   "检测到 Google 登录页面，但 Vault 中没有找到凭证。')
    print(f'    您可以：')
    print(f'    1. 点击 OAuth 授权按钮')
    print(f'    2. 手动输入账号密码"')

    print(f"\n3️⃣ 用户完成登录")

    print(f"\n4️⃣ Agent 行动:")
    print(f"   - 询问: \"是否将这个凭证保存到 Vault？\"")
    print(f"   - 用户同意 → 保存到 Vault")
    print(f"   - 继续执行任务")

    # Example 3: CAPTCHA
    print(f"\n" + "-"*80)
    print("场景 3: ask_human (CAPTCHA)")
    print("-"*80)

    scenario = TEST_SCENARIOS["captcha_detection"]
    hil_response = simulate_hil_detection(scenario)

    print(f"\n1️⃣ Agent 收到 HIL 响应:")
    print(json.dumps({
        "action": hil_response["action"],
        "message": hil_response["message"],
        "intervention_type": hil_response["data"]["intervention_type"]
    }, indent=2, ensure_ascii=False))

    print(f"\n2️⃣ Agent 向用户说明:")
    print(f'   "遇到 CAPTCHA 验证码，需要您手动解决。')
    print(f'    请在浏览器中完成验证后告诉我。"')

    print(f"\n3️⃣ 用户回复: \"已完成\"")

    print(f"\n4️⃣ Agent 行动:")
    print(f"   - 重新调用 web_automation 继续任务")


if __name__ == "__main__":
    # Run tests
    all_passed = run_all_tests()

    # Demonstrate Agent workflow
    demonstrate_agent_workflow()

    # Exit code
    print(f"\n{'='*80}")
    if all_passed:
        print("🎉 所有测试通过！")
        print("="*80)
        exit(0)
    else:
        print("❌ 部分测试失败")
        print("="*80)
        exit(1)
