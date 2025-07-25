#!/usr/bin/env python3
"""
Comprehensive User API Testing Script

Tests all user service API endpoints with real data
Includes performance, security, and functionality tests
"""

import asyncio
import json
import time
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid


class UserAPITester:
    def __init__(self, base_url: str = "http://localhost:8100", auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token or self._generate_test_token()
        self.test_results = []
        self.performance_metrics = []
        
    def _generate_test_token(self) -> str:
        """Generate a test JWT token for testing"""
        # For testing purposes, we'll use a simple mock token
        # In real scenario, this would be a valid Auth0 JWT
        return "test_jwt_token_for_api_testing"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for API requests"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request and measure performance"""
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(f"{self.base_url}{endpoint}", headers=self._get_headers())
                elif method.upper() == "POST":
                    response = await client.post(f"{self.base_url}{endpoint}", headers=self._get_headers(), json=data)
                elif method.upper() == "PUT":
                    response = await client.put(f"{self.base_url}{endpoint}", headers=self._get_headers(), json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(f"{self.base_url}{endpoint}", headers=self._get_headers())
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                # Record performance metric
                self.performance_metrics.append({
                    "endpoint": endpoint,
                    "method": method,
                    "response_time_ms": response_time,
                    "status_code": response.status_code,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Try to parse JSON response
                try:
                    response_data = response.json()
                except:
                    response_data = {"text": response.text}
                
                return {
                    "status_code": response.status_code,
                    "data": response_data,
                    "response_time_ms": response_time,
                    "success": 200 <= response.status_code < 300
                }
                
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                return {
                    "status_code": 0,
                    "data": {"error": str(e)},
                    "response_time_ms": response_time,
                    "success": False
                }
    
    async def test_health_endpoints(self):
        """Test health and basic endpoints"""
        print("🏥 Testing Health Endpoints...")
        
        # Test root endpoint
        result = await self._make_request("GET", "/")
        self.test_results.append({
            "test": "Root Endpoint",
            "endpoint": "/",
            "result": result,
            "expected": "service info"
        })
        
        # Test health endpoint
        result = await self._make_request("GET", "/health")
        self.test_results.append({
            "test": "Health Check",
            "endpoint": "/health",
            "result": result,
            "expected": "healthy status"
        })
        
        print(f"✅ Health endpoints tested - Root: {result['status_code']}")
    
    async def test_user_management_apis(self):
        """Test user management endpoints"""
        print("👤 Testing User Management APIs...")
        
        # Test data for user creation
        test_user_data = {
            "email": "test.user@example.com",
            "name": "Test User API"
        }
        
        # Test ensure user exists
        result = await self._make_request("POST", "/api/v1/users/ensure", test_user_data)
        self.test_results.append({
            "test": "Ensure User Exists",
            "endpoint": "/api/v1/users/ensure",
            "result": result,
            "expected": "user created or found"
        })
        
        # Test get current user info
        result = await self._make_request("GET", "/api/v1/users/me")
        self.test_results.append({
            "test": "Get Current User",
            "endpoint": "/api/v1/users/me",
            "result": result,
            "expected": "user information"
        })
        
        print(f"✅ User management APIs tested")
    
    async def test_usage_records_apis(self):
        """Test usage records endpoints with real data"""
        print("📊 Testing Usage Records APIs...")
        
        # Test user ID (using Auth0 format)
        test_user_id = "auth0|test123456789"
        
        # Test data for usage recording
        usage_data = {
            "user_id": test_user_id,
            "session_id": str(uuid.uuid4()),
            "trace_id": str(uuid.uuid4()),
            "endpoint": "/api/chat/completion",
            "event_type": "ai_chat",
            "credits_charged": 5.5,
            "cost_usd": 0.011,
            "calculation_method": "gpt4_pricing",
            "tokens_used": 1250,
            "prompt_tokens": 800,
            "completion_tokens": 450,
            "model_name": "gpt-4",
            "provider": "openai",
            "tool_name": "chat_service",
            "operation_name": "generate_response",
            "billing_metadata": {
                "request_id": str(uuid.uuid4()),
                "billing_tier": "pro"
            },
            "request_data": {
                "temperature": 0.7,
                "max_tokens": 500,
                "system_prompt": "You are a helpful assistant"
            },
            "response_data": {
                "message": "Generated response content",
                "finish_reason": "stop"
            }
        }
        
        # Test record usage
        result = await self._make_request("POST", f"/api/v1/users/{test_user_id}/usage", usage_data)
        self.test_results.append({
            "test": "Record Usage",
            "endpoint": f"/api/v1/users/{test_user_id}/usage",
            "result": result,
            "expected": "usage recorded successfully"
        })
        
        # Test get usage history
        result = await self._make_request("GET", f"/api/v1/users/{test_user_id}/usage?limit=10&offset=0")
        self.test_results.append({
            "test": "Get Usage History",
            "endpoint": f"/api/v1/users/{test_user_id}/usage",
            "result": result,
            "expected": "usage history list"
        })
        
        # Test get usage statistics
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()
        result = await self._make_request("GET", f"/api/v1/users/{test_user_id}/usage/stats?start_date={start_date}&end_date={end_date}")
        self.test_results.append({
            "test": "Get Usage Statistics",
            "endpoint": f"/api/v1/users/{test_user_id}/usage/stats",
            "result": result,
            "expected": "usage statistics"
        })
        
        print(f"✅ Usage Records APIs tested")
    
    async def test_session_management_apis(self):
        """Test session management endpoints"""
        print("🗣️ Testing Session Management APIs...")
        
        test_user_id = "auth0|test123456789"
        
        # Test data for session creation
        session_data = {
            "user_id": test_user_id,
            "title": "API Test Chat Session",
            "metadata": {
                "source": "api_test",
                "type": "chat_session",
                "client_info": "test_suite_v1.0"
            }
        }
        
        # Test create session
        result = await self._make_request("POST", f"/api/v1/users/{test_user_id}/sessions", session_data)
        self.test_results.append({
            "test": "Create Session",
            "endpoint": f"/api/v1/users/{test_user_id}/sessions",
            "result": result,
            "expected": "session created"
        })
        
        # Extract session ID for further tests
        session_id = None
        if result["success"] and "data" in result["data"]:
            session_id = result["data"]["data"].get("session_id")
        
        # Test get user sessions
        result = await self._make_request("GET", f"/api/v1/users/{test_user_id}/sessions?active_only=true&limit=5")
        self.test_results.append({
            "test": "Get User Sessions",
            "endpoint": f"/api/v1/users/{test_user_id}/sessions",
            "result": result,
            "expected": "sessions list"
        })
        
        if session_id:
            # Test update session status
            result = await self._make_request("PUT", f"/api/v1/sessions/{session_id}/status", {"status": "active"})
            self.test_results.append({
                "test": "Update Session Status",
                "endpoint": f"/api/v1/sessions/{session_id}/status",
                "result": result,
                "expected": "status updated"
            })
            
            # Test add session message
            message_data = {
                "role": "user",
                "content": "Hello, this is a test message from the API test suite. How are you today?",
                "message_type": "chat",
                "tokens_used": 15,
                "cost_usd": 0.001
            }
            result = await self._make_request("POST", f"/api/v1/sessions/{session_id}/messages", message_data)
            self.test_results.append({
                "test": "Add Session Message",
                "endpoint": f"/api/v1/sessions/{session_id}/messages",
                "result": result,
                "expected": "message added"
            })
            
            # Test get session messages
            result = await self._make_request("GET", f"/api/v1/sessions/{session_id}/messages?limit=10")
            self.test_results.append({
                "test": "Get Session Messages",
                "endpoint": f"/api/v1/sessions/{session_id}/messages",
                "result": result,
                "expected": "messages list"
            })
        
        print(f"✅ Session Management APIs tested")
    
    async def test_credit_transaction_apis(self):
        """Test credit transaction endpoints"""
        print("💰 Testing Credit Transaction APIs...")
        
        test_user_id = "auth0|test123456789"
        
        # Test get credit balance
        result = await self._make_request("GET", f"/api/v1/users/{test_user_id}/credits/balance")
        self.test_results.append({
            "test": "Get Credit Balance",
            "endpoint": f"/api/v1/users/{test_user_id}/credits/balance",
            "result": result,
            "expected": "current balance"
        })
        
        # Test recharge credits
        recharge_data = {
            "amount": 100.0,
            "description": "API Test Credit Recharge",
            "reference_id": f"test_recharge_{int(time.time())}"
        }
        result = await self._make_request("POST", f"/api/v1/users/{test_user_id}/credits/recharge", recharge_data)
        self.test_results.append({
            "test": "Recharge Credits",
            "endpoint": f"/api/v1/users/{test_user_id}/credits/recharge",
            "result": result,
            "expected": "credits recharged"
        })
        
        # Test consume credits
        consume_data = {
            "amount": 10.5,
            "description": "API Test Credit Consumption",
            "usage_record_id": 1
        }
        result = await self._make_request("POST", f"/api/v1/users/{test_user_id}/credits/consume", consume_data)
        self.test_results.append({
            "test": "Consume Credits",
            "endpoint": f"/api/v1/users/{test_user_id}/credits/consume",
            "result": result,
            "expected": "credits consumed"
        })
        
        # Test get transaction history
        result = await self._make_request("GET", f"/api/v1/users/{test_user_id}/credits/transactions?limit=10&transaction_type=consume")
        self.test_results.append({
            "test": "Get Transaction History",
            "endpoint": f"/api/v1/users/{test_user_id}/credits/transactions",
            "result": result,
            "expected": "transaction history"
        })
        
        print(f"✅ Credit Transaction APIs tested")
    
    async def test_security_aspects(self):
        """Test security aspects of the API"""
        print("🔒 Testing Security Aspects...")
        
        # Test without authorization header
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/v1/users/me")
            self.test_results.append({
                "test": "No Auth Header",
                "endpoint": "/api/v1/users/me",
                "result": {
                    "status_code": response.status_code,
                    "success": response.status_code == 401
                },
                "expected": "401 Unauthorized"
            })
        
        # Test with invalid token
        invalid_headers = {"Authorization": "Bearer invalid_token", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/v1/users/me", headers=invalid_headers)
            self.test_results.append({
                "test": "Invalid Auth Token",
                "endpoint": "/api/v1/users/me",
                "result": {
                    "status_code": response.status_code,
                    "success": response.status_code == 401
                },
                "expected": "401 Unauthorized"
            })
        
        # Test SQL injection attempt (should be blocked by validation)
        malicious_data = {
            "user_id": "'; DROP TABLE users; --",
            "endpoint": "/test",
            "event_type": "malicious"
        }
        result = await self._make_request("POST", "/api/v1/users/test/usage", malicious_data)
        self.test_results.append({
            "test": "SQL Injection Protection",
            "endpoint": "/api/v1/users/test/usage",
            "result": result,
            "expected": "request blocked or validated"
        })
        
        print(f"✅ Security aspects tested")
    
    async def run_performance_tests(self):
        """Run performance tests"""
        print("⚡ Running Performance Tests...")
        
        # Test concurrent requests
        tasks = []
        for i in range(10):
            task = self._make_request("GET", "/health")
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000
        avg_response_time = sum(r["response_time_ms"] for r in results) / len(results)
        
        self.test_results.append({
            "test": "Concurrent Requests (10)",
            "endpoint": "/health",
            "result": {
                "total_time_ms": total_time,
                "avg_response_time_ms": avg_response_time,
                "success_rate": sum(1 for r in results if r["success"]) / len(results),
                "success": avg_response_time < 1000  # Less than 1 second average
            },
            "expected": "fast concurrent processing"
        })
        
        print(f"✅ Performance tests completed - Avg response time: {avg_response_time:.2f}ms")
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate performance analysis report"""
        if not self.performance_metrics:
            return {"error": "No performance data collected"}
        
        # Group by endpoint
        by_endpoint = {}
        for metric in self.performance_metrics:
            endpoint = metric["endpoint"]
            if endpoint not in by_endpoint:
                by_endpoint[endpoint] = []
            by_endpoint[endpoint].append(metric["response_time_ms"])
        
        # Calculate statistics
        performance_summary = {}
        for endpoint, times in by_endpoint.items():
            performance_summary[endpoint] = {
                "avg_response_time_ms": sum(times) / len(times),
                "min_response_time_ms": min(times),
                "max_response_time_ms": max(times),
                "total_requests": len(times)
            }
        
        return {
            "summary": performance_summary,
            "total_requests": len(self.performance_metrics),
            "test_duration": "full_test_suite"
        }
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test["result"].get("success", False))
        
        return {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "test_results": self.test_results,
            "performance_report": self.generate_performance_report(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Comprehensive API Testing...")
        print("=" * 60)
        
        await self.test_health_endpoints()
        await self.test_user_management_apis()
        await self.test_usage_records_apis()
        await self.test_session_management_apis()
        await self.test_credit_transaction_apis()
        await self.test_security_aspects()
        await self.run_performance_tests()
        
        print("=" * 60)
        print("🎉 All tests completed!")
        
        # Generate and save report
        report = self.generate_test_report()
        
        # Save report to file
        with open("user_api_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Test Report:")
        print(f"   Total Tests: {report['test_summary']['total_tests']}")
        print(f"   Passed: {report['test_summary']['passed_tests']}")
        print(f"   Failed: {report['test_summary']['failed_tests']}")
        print(f"   Success Rate: {report['test_summary']['success_rate']:.1f}%")
        print(f"   Report saved to: user_api_test_report.json")
        
        return report


async def main():
    """Main test execution"""
    tester = UserAPITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())