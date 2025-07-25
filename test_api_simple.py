#!/usr/bin/env python3
"""
Simple API Testing Script

Tests user service API endpoints that don't require authentication
"""

import asyncio
import json
import time
import httpx
from datetime import datetime, timedelta
import uuid


async def test_basic_endpoints():
    """Test basic endpoints that don't require auth"""
    base_url = "http://localhost:8100"
    
    print("🚀 Testing Basic API Endpoints...")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test root endpoint
        print("1. Testing Root Endpoint...")
        response = await client.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # Test health endpoint
        print("2. Testing Health Endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        print()
        
        # Test API docs endpoint
        print("3. Testing API Docs...")
        response = await client.get(f"{base_url}/docs")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print()
        
        # Test subscription plans (public endpoint)
        print("4. Testing Subscription Plans...")
        response = await client.get(f"{base_url}/api/v1/subscriptions/plans")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            plans = response.json()
            print(f"   Available Plans: {json.dumps(plans, indent=2)}")
        else:
            print(f"   Error: {response.text}")
        print()
        
        # Test security - endpoints should require auth
        print("5. Testing Authentication Requirements...")
        
        auth_required_endpoints = [
            "/api/v1/users/me",
            "/api/v1/users/auth0|test/usage",
            "/api/v1/users/auth0|test/sessions",
            "/api/v1/users/auth0|test/credits/balance"
        ]
        
        for endpoint in auth_required_endpoints:
            response = await client.get(f"{base_url}{endpoint}")
            print(f"   {endpoint}: {response.status_code} {'✅' if response.status_code == 401 else '❌'}")
        
        print()
        print("🎉 Basic API testing completed!")


if __name__ == "__main__":
    asyncio.run(test_basic_endpoints())