#!/usr/bin/env python3
"""
测试完整的webhook流程
模拟从前端转发到后端的webhook请求
"""

import requests
import json
import hmac
import hashlib
import time

def create_stripe_signature(payload, secret):
    """创建Stripe webhook签名"""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"

def test_webhook_flow():
    """测试webhook流程"""
    
    # 模拟checkout.session.completed事件
    webhook_payload = {
        "id": "evt_test_webhook",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": "cus_test_123",
                "subscription": "sub_test_123",
                "metadata": {
                    "auth0_user_id": "google-oauth2|107896640181181053492",
                    "user_email": "test@example.com",
                    "plan_type": "pro"
                }
            }
        }
    }
    
    payload_str = json.dumps(webhook_payload)
    
    # 使用配置的webhook secret
    webhook_secret = "whsec_16534a5fe7a8a8a2571f134a73a04719eced92068217bfb6008620c9e88b03e6"
    signature = create_stripe_signature(payload_str, webhook_secret)
    
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": signature
    }
    
    print("=== 测试Webhook流程 ===")
    print(f"转发到: http://localhost:8100/api/v1/webhooks/stripe")
    print(f"Payload: {payload_str}")
    print(f"Signature: {signature}")
    
    try:
        # 直接测试后端webhook接口
        response = requests.post(
            "http://localhost:8100/api/v1/webhooks/stripe",
            data=payload_str,
            headers=headers,
            timeout=10
        )
        
        print(f"\n=== 响应结果 ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n=== 处理结果 ===")
            print(f"Success: {result.get('success', False)}")
            print(f"Event Type: {result.get('event_type', 'Unknown')}")
            print(f"User Updated: {result.get('user_updated', False)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_webhook_flow()