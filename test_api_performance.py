#!/usr/bin/env python3
"""
API Performance Testing Script

Tests response times, concurrent requests, and load capacity
"""

import asyncio
import time
import httpx
import statistics
from typing import List, Dict
import json


class PerformanceTester:
    def __init__(self, base_url: str = "http://localhost:8100"):
        self.base_url = base_url
        self.results = []
    
    async def single_request_test(self, endpoint: str, method: str = "GET") -> Dict:
        """Test single request performance"""
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(f"{self.base_url}{endpoint}")
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                
                return {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": response.status_code,
                    "response_time_ms": response_time,
                    "success": 200 <= response.status_code < 300
                }
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                return {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": 0,
                    "response_time_ms": response_time,
                    "success": False,
                    "error": str(e)
                }
    
    async def concurrent_requests_test(self, endpoint: str, num_requests: int = 10) -> Dict:
        """Test concurrent requests performance"""
        print(f"📊 Testing {num_requests} concurrent requests to {endpoint}...")
        
        tasks = []
        for _ in range(num_requests):
            task = self.single_request_test(endpoint)
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Calculate statistics
        response_times = [r["response_time_ms"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "endpoint": endpoint,
            "num_requests": num_requests,
            "total_time_ms": (end_time - start_time) * 1000,
            "success_rate": success_count / num_requests,
            "avg_response_time_ms": statistics.mean(response_times),
            "median_response_time_ms": statistics.median(response_times),
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times),
            "std_dev_ms": statistics.stdev(response_times) if len(response_times) > 1 else 0,
            "requests_per_second": num_requests / ((end_time - start_time))
        }
    
    async def load_test_increasing(self, endpoint: str) -> List[Dict]:
        """Test with increasing load"""
        print(f"🔄 Load testing {endpoint} with increasing concurrent requests...")
        
        load_levels = [1, 5, 10, 20, 50]
        results = []
        
        for load in load_levels:
            print(f"   Testing with {load} concurrent requests...")
            result = await self.concurrent_requests_test(endpoint, load)
            results.append(result)
            
            # Brief pause between tests
            await asyncio.sleep(1)
        
        return results
    
    async def response_size_test(self, endpoints: List[str]) -> List[Dict]:
        """Test response sizes and times"""
        print("📏 Testing response sizes and content...")
        
        results = []
        async with httpx.AsyncClient() as client:
            for endpoint in endpoints:
                start_time = time.time()
                try:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    end_time = time.time()
                    
                    content_length = len(response.content)
                    response_time = (end_time - start_time) * 1000
                    
                    results.append({
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response_time_ms": response_time,
                        "content_length_bytes": content_length,
                        "content_type": response.headers.get("content-type", "unknown"),
                        "throughput_bytes_per_ms": content_length / response_time if response_time > 0 else 0
                    })
                    
                except Exception as e:
                    results.append({
                        "endpoint": endpoint,
                        "error": str(e),
                        "status_code": 0
                    })
        
        return results
    
    def analyze_performance_trends(self, load_test_results: List[Dict]) -> Dict:
        """Analyze performance trends across different loads"""
        loads = [r["num_requests"] for r in load_test_results]
        avg_times = [r["avg_response_time_ms"] for r in load_test_results]
        rps = [r["requests_per_second"] for r in load_test_results]
        success_rates = [r["success_rate"] for r in load_test_results]
        
        return {
            "performance_degradation": {
                "response_time_increase_factor": max(avg_times) / min(avg_times) if min(avg_times) > 0 else "N/A",
                "max_successful_load": max([loads[i] for i, sr in enumerate(success_rates) if sr >= 0.95], default=0),
                "peak_rps": max(rps),
                "scalability_score": min(success_rates) * 100  # Percentage
            },
            "load_vs_performance": [
                {
                    "concurrent_requests": loads[i],
                    "avg_response_time_ms": avg_times[i],
                    "requests_per_second": rps[i],
                    "success_rate": success_rates[i]
                }
                for i in range(len(loads))
            ]
        }
    
    async def run_comprehensive_performance_test(self):
        """Run all performance tests"""
        print("🚀 Starting Comprehensive Performance Testing...")
        print("=" * 60)
        
        # Test endpoints
        test_endpoints = [
            "/",
            "/health",
            "/api/v1/subscriptions/plans",
            "/docs"
        ]
        
        # 1. Single request baseline
        print("1. Baseline Performance Test...")
        baseline_results = []
        for endpoint in test_endpoints:
            result = await self.single_request_test(endpoint)
            baseline_results.append(result)
            print(f"   {endpoint}: {result['response_time_ms']:.2f}ms")
        
        print()
        
        # 2. Response size analysis
        response_size_results = await self.response_size_test(test_endpoints)
        
        print("   Response Size Analysis:")
        for result in response_size_results:
            if "error" not in result:
                print(f"   {result['endpoint']}: {result['content_length_bytes']} bytes, "
                      f"{result['response_time_ms']:.2f}ms")
        
        print()
        
        # 3. Concurrent request tests
        print("2. Concurrent Request Performance...")
        concurrent_results = {}
        
        # Test health endpoint with different loads
        health_load_results = await self.load_test_increasing("/health")
        concurrent_results["/health"] = health_load_results
        
        # Test root endpoint
        root_concurrent = await self.concurrent_requests_test("/", 20)
        print(f"   Root endpoint (20 concurrent): {root_concurrent['avg_response_time_ms']:.2f}ms avg, "
              f"{root_concurrent['requests_per_second']:.1f} RPS")
        
        print()
        
        # 4. Performance trend analysis
        print("3. Performance Trend Analysis...")
        health_trends = self.analyze_performance_trends(health_load_results)
        
        print(f"   Max Successful Load: {health_trends['performance_degradation']['max_successful_load']} concurrent requests")
        print(f"   Peak RPS: {health_trends['performance_degradation']['peak_rps']:.1f}")
        print(f"   Scalability Score: {health_trends['performance_degradation']['scalability_score']:.1f}%")
        print(f"   Response Time Degradation: {health_trends['performance_degradation']['response_time_increase_factor']:.2f}x")
        
        print()
        
        # 5. Error handling performance
        print("4. Error Handling Performance...")
        error_endpoint_result = await self.concurrent_requests_test("/nonexistent", 10)
        print(f"   404 Error Handling: {error_endpoint_result['avg_response_time_ms']:.2f}ms avg")
        
        # Generate comprehensive report
        report = {
            "test_timestamp": time.time(),
            "baseline_performance": baseline_results,
            "response_size_analysis": response_size_results,
            "concurrent_performance": concurrent_results,
            "performance_trends": health_trends,
            "error_handling": error_endpoint_result,
            "summary": {
                "fastest_endpoint": min(baseline_results, key=lambda x: x.get("response_time_ms", float('inf'))),
                "slowest_endpoint": max(baseline_results, key=lambda x: x.get("response_time_ms", 0)),
                "total_tests_run": len(baseline_results) + len(health_load_results) + 2
            }
        }
        
        # Save report
        with open("performance_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print("=" * 60)
        print("🎉 Performance testing completed!")
        print(f"📊 Report saved to: performance_test_report.json")
        print()
        print("📈 Performance Summary:")
        print(f"   Fastest Response: {report['summary']['fastest_endpoint']['endpoint']} "
              f"({report['summary']['fastest_endpoint']['response_time_ms']:.2f}ms)")
        print(f"   Slowest Response: {report['summary']['slowest_endpoint']['endpoint']} "
              f"({report['summary']['slowest_endpoint']['response_time_ms']:.2f}ms)")
        print(f"   Peak Performance: {health_trends['performance_degradation']['peak_rps']:.1f} RPS")
        
        return report


async def main():
    """Main test execution"""
    tester = PerformanceTester()
    await tester.run_comprehensive_performance_test()


if __name__ == "__main__":
    asyncio.run(main())